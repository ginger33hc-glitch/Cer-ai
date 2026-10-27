"""Isolated local Chromium sessions; authenticated live viewer, no browser vendor."""
from concurrent.futures import Future, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
import base64
import math
import os
from pathlib import Path
from queue import Queue, Empty, Full
import shutil
import subprocess
from tempfile import TemporaryDirectory
from threading import Event, Lock, Thread
from time import monotonic, sleep
from uuid import uuid4

from fastapi import Body, HTTPException
from fastapi.responses import HTMLResponse, Response
from websockets.sync.client import connect
from .escrs_browserbase import CDP, _prepare, _command, _KEYS

ROOT = Path(__file__).resolve().parents[1]
VIEWER_SECONDS = 900
PREPARE_SECONDS = 125
WIDTH, HEIGHT = 420, 820
_lock = Lock()
_sessions = {}


def executable():
    return shutil.which(os.environ.get('CERAI_CHROMIUM_EXECUTABLE', 'chromium'))


@dataclass
class Session:
    user_id: str
    view_id: str = field(default_factory=lambda: uuid4().hex)
    ready: Future = field(default_factory=Future)
    stop: Event = field(default_factory=Event)
    commands: Queue = field(default_factory=lambda: Queue(maxsize=8))
    expires: float = 0


def _owned(view_id, user_id):
    with _lock:
        record = _sessions.get(view_id)
    if record is None or record.stop.is_set() or not record.ready.done():
        raise HTTPException(410, 'This ESCRS session has ended.')
    if record.user_id != user_id:
        raise HTTPException(403, 'This ESCRS session belongs to another user.')
    if monotonic() >= record.expires:
        record.stop.set()
        raise HTTPException(410, 'This ESCRS session has ended.')
    return record


def _dispatch(cdp, page, command):
    if command['kind'] in {'text', 'key'}:
        return _command(cdp, page, command)
    host = cdp.call('Runtime.evaluate', {'expression':'location.hostname','returnByValue':True}, page)
    if host.get('result', {}).get('value') != 'iolcalculator.escrs.org':
        raise HTTPException(409, 'Return to the ESCRS calculator.')
    if command['kind'] == 'fields':
        result = cdp.call('Runtime.evaluate', {'expression':"""(() => {
          window.__ceraiFieldCounter = window.__ceraiFieldCounter || 0;
          return [...document.querySelectorAll('input,textarea')].filter(e =>
            !e.disabled && !e.readOnly && !['checkbox','radio','button','submit','file','hidden'].includes(e.type)
          ).map(e => {
            const r=e.getBoundingClientRect();
            if(!e.dataset.ceraiField)e.dataset.ceraiField=String(++window.__ceraiFieldCounter);
            return {id:e.dataset.ceraiField,value:e.value,type:e.type,x:r.x,y:r.y,width:r.width,height:r.height};
          }).filter(r=>r.width>0 && r.height>0 && r.y>=0 && r.y+r.height<=820 && r.x>=0 && r.x+r.width<=420);
        })()""", 'returnByValue':True}, page)
        return result.get('result', {}).get('value', [])
    if command['kind'] == 'edit':
        import json
        expression = """(() => {const e=document.querySelector('[data-cerai-field="'+ID+'"]');
          if(!e || !e.matches('input,textarea') || e.disabled || e.readOnly)return false;
          e.focus();return document.activeElement===e;})()""".replace('ID',json.dumps(command['field']))
        focused=cdp.call('Runtime.evaluate', {'expression':expression,'returnByValue':True}, page)
        if focused.get('result',{}).get('value') is not True:
            raise HTTPException(409, 'Select the field again.')
        cdp.call('Input.dispatchKeyEvent', {'type':'keyDown','key':'a','code':'KeyA','windowsVirtualKeyCode':65,'modifiers':2}, page)
        cdp.call('Input.dispatchKeyEvent', {'type':'keyUp','key':'a','code':'KeyA','windowsVirtualKeyCode':65,'modifiers':2}, page)
        if command['text']:
            cdp.call('Input.insertText', {'text':command['text']}, page)
        else:
            _command(cdp, page, {'kind':'key','key':'Backspace'})
        return
    if command['kind'] == 'frame':
        return cdp.call('Page.captureScreenshot', {'format':'jpeg','quality':65}, page)['data']
    if command['kind'] == 'pdf':
        return cdp.call('Page.printToPDF', {'printBackground':True}, page)['data']
    if command['kind'] == 'click':
        for event in ('mousePressed', 'mouseReleased'):
            cdp.call('Input.dispatchMouseEvent', {'type':event,'x':command['x'],'y':command['y'],
                                                'button':'left','clickCount':1}, page)
    elif command['kind'] == 'scroll':
        cdp.call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':WIDTH/2,'y':HEIGHT/2,
                                            'deltaX':0,'deltaY':command['delta']}, page)


def _worker(record, case):
    process = None
    try:
        with TemporaryDirectory(prefix='cerai-escrs-') as profile:
            try:
                process = subprocess.Popen([executable(), '--headless=new', '--no-sandbox',
                    '--disable-dev-shm-usage', '--disable-background-networking', '--no-first-run',
                    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
                    '--user-data-dir='+profile, 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                deadline = monotonic()+20
                port_file = Path(profile)/'DevToolsActivePort'
                while not port_file.exists():
                    if process.poll() is not None or monotonic() >= deadline or record.stop.is_set():
                        raise RuntimeError('Chromium unavailable')
                    sleep(.1)
                lines = port_file.read_text().splitlines()
                port = int(lines[0])
                if not 0 < port < 65536 or not lines[1].startswith('/devtools/browser/'):
                    raise ValueError('Invalid local debugging endpoint')
                with connect(f'ws://127.0.0.1:{port}'+lines[1], open_timeout=10,
                             close_timeout=2, max_size=16*1024*1024) as socket:
                    cdp = CDP(socket)
                    page = _prepare(cdp, case)
                    cdp.call('Emulation.setDeviceMetricsOverride', {'width':WIDTH,'height':HEIGHT,
                             'deviceScaleFactor':1,'mobile':True}, page)
                    if record.stop.is_set():
                        raise TimeoutError('Cancelled')
                    record.expires = monotonic()+VIEWER_SECONDS
                    cdp.deadline = record.expires
                    record.ready.set_result({'escrs_url':'/iol/escrs-local/'+record.view_id,
                        'verified':True,'provider':'local','viewer_limit_seconds':VIEWER_SECONDS})
                    while not record.stop.is_set() and monotonic() < record.expires:
                        try:
                            command, receipt = record.commands.get(timeout=.25)
                        except Empty:
                            continue
                        try:
                            result = _dispatch(cdp, page, command)
                            receipt.set_result(result)
                        except Exception:
                            receipt.set_exception(HTTPException(409, 'ESCRS input or display could not be confirmed.'))
            finally:
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
    except Exception:
        if not record.ready.done():
            record.ready.set_exception(HTTPException(502, 'Local ESCRS transfer could not be verified.'))
    finally:
        record.stop.set()
        with _lock:
            _sessions.pop(record.view_id, None)
        while True:
            try:
                _, receipt = record.commands.get_nowait()
            except Empty:
                break
            if not receipt.done():
                receipt.set_exception(HTTPException(410, 'This ESCRS session has ended.'))


def create_local_transfer(case, user_id):
    if not executable():
        raise HTTPException(503, 'Local Chromium is unavailable.')
    record = Session(user_id)
    with _lock:
        if len(_sessions) >= 2 or any(s.user_id == user_id for s in _sessions.values()):
            raise HTTPException(429, 'An ESCRS session is active. Close it before retrying.')
        _sessions[record.view_id] = record
    Thread(target=_worker, args=(record, case), daemon=True).start()
    try:
        return record.ready.result(timeout=PREPARE_SECONDS)
    except FutureTimeout:
        record.stop.set()
        raise HTTPException(504, 'ESCRS session preparation timed out.') from None


def _request(record, command):
    receipt = Future()
    try:
        record.commands.put_nowait((command, receipt))
    except Full:
        raise HTTPException(429, 'Please wait for the previous input.') from None
    try:
        return receipt.result(timeout=10)
    except FutureTimeout:
        # End the session rather than apply unconfirmed commands later.
        record.stop.set()
        raise HTTPException(504, 'Input could not be confirmed.') from None


def _input(payload):
    kind = payload.get('kind')
    def number(key, low, high):
        value = payload.get(key)
        return type(value) in (int, float) and math.isfinite(value) and low <= value <= high
    if kind == 'edit' and isinstance(payload.get('field'),str) and payload['field'].isdigit() and len(payload['field'])<=8 and isinstance(payload.get('text'),str) and len(payload['text'])<=500:
        return {'kind':kind,'field':payload['field'],'text':payload['text']}
    if kind == 'text' and isinstance(payload.get('text'), str) and 0 < len(payload['text']) <= 500:
        return {'kind':kind,'text':payload['text']}
    if kind == 'key' and payload.get('key') in _KEYS:
        return {'kind':kind,'key':payload['key']}
    if kind == 'click' and number('x',0,WIDTH) and number('y',0,HEIGHT):
        return {'kind':kind,'x':payload['x'],'y':payload['y']}
    if kind == 'scroll' and number('delta',-1600,1600):
        return {'kind':kind,'delta':payload['delta']}
    raise HTTPException(422, 'Invalid ESCRS input.')


def install(core):
    import user_access
    def owned(view_id):
        return _owned(view_id, user_access.require_current_principal().user_id)

    @core.app.get('/iol/escrs-local/{view_id}', include_in_schema=False)
    def viewer(view_id: str):
        record = owned(view_id)
        from .ui import version_asset_urls
        html = (ROOT/'static/iol-escrs-local.html').read_text().replace('__VIEW_ID__', record.view_id)
        return HTMLResponse(version_asset_urls(html), headers={'Cache-Control':'no-store'})

    @core.app.get('/iol/escrs-local/{view_id}/status')
    def status(view_id: str):
        record = owned(view_id)
        return {'seconds_remaining':max(0,int(record.expires-monotonic()))}

    @core.app.get('/iol/escrs-local/{view_id}/fields')
    def fields(view_id: str):
        return _request(owned(view_id), {'kind':'fields'})

    @core.app.get('/iol/escrs-local/{view_id}/frame')
    def frame(view_id: str):
        data = _request(owned(view_id), {'kind':'frame'})
        return Response(base64.b64decode(data), media_type='image/jpeg', headers={'Cache-Control':'no-store'})

    @core.app.get('/iol/escrs-local/{view_id}/pdf')
    def pdf(view_id: str):
        data = _request(owned(view_id), {'kind':'pdf'})
        return Response(base64.b64decode(data), media_type='application/pdf',
                        headers={'Cache-Control':'no-store','Content-Disposition':'attachment; filename="ESCRS.pdf"'})

    @core.app.post('/iol/escrs-local/{view_id}/input')
    def keyboard(view_id: str, payload: dict = Body(...)):
        record = owned(view_id)
        _request(record, _input(payload))
        return {'status':'sent'}

    @core.app.post('/iol/escrs-local/{view_id}/close')
    def close(view_id: str):
        owned(view_id).stop.set()
        return {'status':'closing'}
