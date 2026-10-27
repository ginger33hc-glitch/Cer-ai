"""Resumable, doctor-owned IOL uploads and detached source processing."""
import asyncio
import hashlib
import logging
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, StrictInt
import operational_security as security
import user_access

CHUNK_BYTES = 512 * 1024
TTL_SECONDS = 1800
MAX_ACTIVE_JOBS = 4
MAX_JOBS = 32
log = logging.getLogger(__name__)


class Source(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    size: StrictInt = Field(gt=0, le=security.MAX_FILE_BYTES)
    type: str = Field(pattern=r'^image/', max_length=100)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class Submission(BaseModel):
    request_id: str = Field(min_length=1, max_length=160)
    patient_name: str = Field(min_length=1, max_length=200)
    files: list[Source] = Field(min_length=3, max_length=5)


def install(core, process_sources):
    jobs = {}
    # The async routes and tasks share one event loop; no await occurs in mutations.
    def prune():
        for key, job in list(jobs.items()):
            if job['expires'] <= monotonic() and job['state'] not in {'READING','ARCHIVING'}:
                jobs.pop(key, None)

    def owned(job_id):
        principal = user_access.require_current_principal()
        prune()
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(410, 'IOL job expired or the server restarted. Select the images again.')
        if job['owner'] != principal.user_id:
            raise HTTPException(403, 'This IOL assessment belongs to another doctor.')
        return job

    def snapshot(job):
        result={'job_id':job['id'],'status':job['state'],'completed':job['completed'],
                'total':len(job['files']),'offsets':job['offsets'],
                'elapsed_seconds':int(monotonic()-job['created'])}
        if job['state']=='COMPLETED':
            result['result']=job['result']
        if job['state']=='FAILED':
            result.update(detail=job['error'],http_status=job['http_status'])
        return result

    async def expire(job):
        await asyncio.sleep(TTL_SECONDS)
        if job['state'] in {'READING','ARCHIVING'}:
            await asyncio.sleep(900)
        jobs.pop(job['id'],None)

    async def run(job, principal):
        job['state']='READING'
        def progress(state, completed):
            job.update(state=state,completed=completed)
            log.info('IOL job %s stage=%s completed=%s',job['id'],state,completed)
        try:
            payloads=[(bytes(data),source.name) for data,source in zip(job['data'],job['files'])]
            job['data']=[]
            result=await asyncio.wait_for(process_sources(payloads,principal,job['request_id'],job['patient_name'],progress),timeout=900)
            job.update(state='COMPLETED',result=result)
            log.info('IOL job %s completed',job['id'])
        except HTTPException as exc:
            job.update(state='FAILED',error=exc.detail,http_status=exc.status_code)
        except asyncio.TimeoutError:
            job.update(state='FAILED',error='Image reading exceeded the processing time limit. Please retry.',http_status=504)
        except Exception:
            log.warning('IOL job %s failed during processing',job['id'])
            job.update(state='FAILED',error='IOL image processing failed. Please retry.',http_status=502)
        finally:
            job['data']=[]

    @core.app.post('/iol/jobs',status_code=202)
    async def create(payload: Submission):
        principal=user_access.require_current_principal()
        prune()
        if len(payload.files) not in {3,5} or sum(f.size for f in payload.files)>security.MAX_TOTAL_UPLOAD_BYTES:
            raise HTTPException(422,'Upload 3 images for one eye or 5 for both eyes within the upload size limit.')
        for job in jobs.values():
            if job['owner']==principal.user_id and job['request_id']==payload.request_id:
                if job['manifest']!=payload.model_dump():
                    raise HTTPException(409,'The images or patient changed. Select the images again.')
                return snapshot(job)
        if any(j['owner']==principal.user_id and j['state'] in {'READING','ARCHIVING'} for j in jobs.values()):
            raise HTTPException(429,'An IOL assessment is already running. Resume that assessment first.')
        # A new selection replaces this doctor's unfinished upload, never a running read.
        for key, previous in list(jobs.items()):
            if previous['owner']==principal.user_id and previous['state']=='UPLOADING':
                previous['state']='CANCELLED'
                previous['data']=[]
                previous['expiry_task'].cancel()
                jobs.pop(key)
        if sum(j['state'] not in {'FAILED','COMPLETED'} for j in jobs.values())>=MAX_ACTIVE_JOBS or len(jobs)>=MAX_JOBS:
            raise HTTPException(429,'IOL assessment capacity is busy. Please retry shortly.')
        check=getattr(core,'_cerai_assert_demo_credit',None)
        if callable(check): check(principal.user_id)
        job={'id':uuid4().hex,'owner':principal.user_id,'request_id':payload.request_id,
             'patient_name':payload.patient_name,'manifest':payload.model_dump(),'files':payload.files,
             'data':[bytearray() for _ in payload.files],'offsets':[0]*len(payload.files),
             'state':'UPLOADING','completed':0,'created':monotonic(),'expires':monotonic()+TTL_SECONDS}
        jobs[job['id']]=job
        job['expiry_task']=asyncio.create_task(expire(job))
        log.info('IOL job %s created images=%s',job['id'],len(payload.files))
        return snapshot(job)

    @core.app.put('/iol/jobs/{job_id}/images/{index}')
    async def upload(job_id: str,index: int,request: Request,offset: int=0):
        job=owned(job_id)
        if job['state']!='UPLOADING' or index<0 or index>=len(job['files']) or offset<0:
            raise HTTPException(409,'Invalid upload state.')
        chunk=bytearray()
        async for part in request.stream():
            chunk.extend(part)
            if len(chunk)>CHUNK_BYTES:
                raise HTTPException(413,'Upload chunk is too large.')
        if not chunk:
            raise HTTPException(422,'Empty upload chunk.')
        # Recheck after receiving: another request may have advanced this image.
        if job['state']!='UPLOADING': raise HTTPException(409,'Upload already completed.')
        data=job['data'][index]
        if offset<len(data):
            if data[offset:offset+len(chunk)]!=chunk:
                raise HTTPException(409,'Upload content mismatch.')
        elif offset==len(data) and len(data)+len(chunk)<=job['files'][index].size:
            data.extend(chunk)
            job['offsets'][index]=len(data)
        else:
            raise HTTPException(409,'Upload offset mismatch.')
        return {'offset':len(data)}

    @core.app.post('/iol/jobs/{job_id}/start',status_code=202)
    async def start(job_id: str):
        principal=user_access.require_current_principal()
        job=owned(job_id)
        if job['state']!='UPLOADING': return snapshot(job)
        if any(len(data)!=f.size or hashlib.sha256(data).hexdigest()!=f.sha256 for data,f in zip(job['data'],job['files'])):
            raise HTTPException(409,'Images are incomplete or failed integrity verification. Resume upload.')
        job['state']='READING'
        job['task']=asyncio.create_task(run(job,principal))
        return snapshot(job)

    @core.app.get('/iol/jobs/{job_id}')
    async def status(job_id: str):
        return snapshot(owned(job_id))
