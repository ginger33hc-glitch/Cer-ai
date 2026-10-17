"""Five-minute, owner-scoped Browserbase handoffs using the canonical ESCRS adapter."""
from __future__ import annotations

from concurrent.futures import Future, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from queue import Queue, Empty, Full
from threading import Event, Lock, Thread
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4, UUID

from fastapi import Body, HTTPException
from fastapi.responses import HTMLResponse
from websockets.sync.client import connect

VIEWER_SECONDS = 300
PREPARE_SECONDS = 125
API = 'https://api.browserbase.com/v1/sessions'
ROOT = Path(__file__).resolve().parents[1]
_lock = Lock()
_sessions = {}
_KEYS = {'Enter':13, 'Tab':9, 'Backspace':8, 'ArrowLeft':37, 'ArrowUp':38, 'ArrowRight':39, 'ArrowDown':40}


@dataclass
class Session:
    user_id: str
    view_id: str = field(default_factory=lambda: uuid4().hex)
    ready: Future = field(default_factory=Future)
    stop: Event = field(default_factory=Event)
    commands: Queue = field(default_factory=lambda: Queue(maxsize=8))
    expires: float = 0
    viewer_url: str = ''


def _api(path='', body=None):
    token = os.environ.get('BROWSERBASE_API_KEY', '').strip()
    if not token:
        raise HTTPException(503, 'Browserbase is not configured.')
    request = Request(API + path, data=None if body is None else json.dumps(body).encode(),
                      headers={'X-BB-API-Key':token, 'Content-Type':'application/json'})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read(1024 * 1024))


def _provider_url(value, *, websocket=False):
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if (parsed.scheme != ('wss' if websocket else 'https') or parsed.port not in {None,443}
            or parsed.username or parsed.password
            or not (host == 'browserbase.com' or host.endswith('.browserbase.com'))):
        raise ValueError('Invalid Browserbase endpoint')
    return value


class CDP:
    def __init__(self, socket):
        self.socket, self.counter = socket, 0
        self.deadline = monotonic() + PREPARE_SECONDS

    def call(self, method, params=None, session_id=None):
        self.counter += 1
        command = {'id':self.counter, 'method':method, 'params':params or {}}
        if session_id:
            command['sessionId'] = session_id
        self.socket.send(json.dumps(command))
        deadline = min(self.deadline, monotonic()+100)
        while monotonic() < deadline:
            result = json.loads(self.socket.recv(timeout=max(.1,deadline-monotonic())))
            if result.get('id') == self.counter:
                if 'error' in result:
                    raise ValueError('Browser command failed')
                return result.get('result', {})
        raise TimeoutError('Browser command timed out')


def _prepare(cdp, case):
    target = cdp.call('Target.createTarget', {'url':'about:blank'})['targetId']
    session_id = cdp.call('Target.attachToTarget', {'targetId':target,'flatten':True})['sessionId']
    cdp.call('Page.navigate', {'url':'https://iolcalculator.escrs.org/'}, session_id)
    while monotonic() < cdp.deadline:
        try:
            state = cdp.call('Runtime.evaluate', {'expression':"location.hostname === 'iolcalculator.escrs.org' && document.readyState !== 'loading'",'returnByValue':True},session_id)
        except ValueError:
            sleep(.2)
            continue
        if state.get('result',{}).get('value') is True:
            break
        sleep(.2)
    payload = case.model_dump(mode='json', exclude={'terms_accepted','data_transfer_accepted','consent_version','provider'})
    adapter = (ROOT / 'extensions/escrs-assistant/adapter.js').read_text()
    expression = '''(async () => {
      const until = async (fn) => {const end=Date.now()+45000; while(Date.now()<end){const x=fn();if(x)return x;await new Promise(r=>setTimeout(r,100));}throw new Error('Page unavailable');};
      const terms=await until(()=>[...document.querySelectorAll('button')].find(b=>b.textContent.trim().toUpperCase()==='I AGREE'));
      terms.click();await until(()=>document.querySelector('input'));
    ''' + adapter + '\nreturn await globalThis.CeraiEscrsAdapter.run(' + json.dumps(payload) + ');})()'
    result = cdp.call('Runtime.evaluate', {'expression':expression,'awaitPromise':True,'returnByValue':True}, session_id)
    selected = result.get('result', {}).get('value')
    expected = {side:eye.lens_matches[0] for side,eye in case.eyes.items()}
    if result.get('exceptionDetails') or selected != expected:
        raise ValueError('ESCRS model readback failed')
    return session_id


def _command(cdp, session_id, command):
    page = cdp.call('Runtime.evaluate', {'expression':'({host:location.hostname,editable:!!document.activeElement && (((document.activeElement.matches("input,textarea") && !document.activeElement.disabled && !document.activeElement.readOnly) || document.activeElement.isContentEditable))})','returnByValue':True},session_id)
    state = page.get('result',{}).get('value',{})
    if state.get('host') != 'iolcalculator.escrs.org' or not state.get('editable'):
        raise HTTPException(409, 'Tap an editable ESCRS field first.')
    if command['kind'] == 'text':
        cdp.call('Input.insertText', {'text':command['text']},session_id)
    else:
        key=command['key']
        for event in ('keyDown','keyUp'):
            cdp.call('Input.dispatchKeyEvent', {'type':event,'key':key,'windowsVirtualKeyCode':_KEYS[key]},session_id)


def _worker(record, case):
    provider_id = None
    project = None
    try:
        options = {'timeout':PREPARE_SECONDS+VIEWER_SECONDS, 'keepAlive':False, 'proxies':False,
                   'browserSettings':{'recordSession':False,'logSession':False,'solveCaptchas':False,
                                      'viewport':{'width':420,'height':820}}}
        project = os.environ.get('BROWSERBASE_PROJECT_ID','').strip()
        if project:
            options['projectId'] = project
        created = _api(body=options)
        provider_id = str(UUID(created['id']))
        project = created.get('projectId') or project
        connection = _provider_url(created['connectUrl'],websocket=True)
        with connect(connection,open_timeout=10,close_timeout=2,ping_interval=15,max_size=1024*1024) as socket:
            cdp = CDP(socket)
            session_id = _prepare(cdp,case)
            debug = _api('/'+provider_id+'/debug')
            pages = [page for page in debug.get('pages',[]) if urlsplit(page.get('url','')).hostname == 'iolcalculator.escrs.org']
            if len(pages) != 1:
                raise ValueError('Cannot identify the verified ESCRS viewer')
            record.viewer_url = _provider_url(pages[0]['debuggerFullscreenUrl'])
            if urlsplit(record.viewer_url).hostname not in {'www.browserbase.com','browserbase.com'}:
                raise ValueError('Invalid viewer host')
            if record.stop.is_set():
                raise TimeoutError('Cancelled')
            record.expires = monotonic()+VIEWER_SECONDS
            cdp.deadline = record.expires
            record.ready.set_result({'escrs_url':'/iol/escrs-session/'+record.view_id,
                                     'verified':True,'provider':'browserbase','viewer_limit_seconds':VIEWER_SECONDS})
            while not record.stop.is_set() and monotonic() < record.expires:
                try:
                    command, receipt = record.commands.get(timeout=.25)
                except Empty:
                    continue
                try:
                    if receipt.cancelled():
                        continue
                    _command(cdp,session_id,command)
                    receipt.set_result({'status':'sent'})
                except Exception:
                    receipt.set_exception(HTTPException(409,'Tap an editable ESCRS field and retry.'))
    except Exception as exc:
        if not record.ready.done():
            if isinstance(exc, HTTPError) and exc.code in {402,429}:
                record.ready.set_exception(HTTPException(503,'Browserbase quota or capacity is unavailable.'))
            else:
                record.ready.set_exception(HTTPException(502,'Browserbase ESCRS transfer could not be verified.'))
    finally:
        record.stop.set()
        if provider_id:
            try:
                _api('/'+provider_id, {'status':'REQUEST_RELEASE', **({'projectId':project} if project else {})})
            except Exception:
                pass  # Provider absolute timeout still bounds the session.
        with _lock:
            _sessions.pop(record.view_id,None)


def create_browserbase_transfer(case, user_id):
    if not os.environ.get('BROWSERBASE_API_KEY','').strip():
        raise HTTPException(503,'Browserbase is not configured.')
    record = Session(user_id)
    with _lock:
        if len(_sessions) >= 2 or any(s.user_id==user_id for s in _sessions.values()):
            raise HTTPException(429,'An ESCRS session is active. Close it before retrying.')
        _sessions[record.view_id] = record
    Thread(target=_worker,args=(record,case),daemon=True).start()
    try:
        return record.ready.result(timeout=PREPARE_SECONDS)
    except FutureTimeout:
        record.stop.set()
        raise HTTPException(504,'ESCRS session preparation timed out.') from None


def _owned(view_id, user_id):
    with _lock:
        record = _sessions.get(view_id)
    if record is None or record.stop.is_set() or not record.ready.done():
        raise HTTPException(410,'This ESCRS session has ended.')
    if record.user_id != user_id:
        raise HTTPException(403,'This ESCRS session belongs to another user.')
    if monotonic() >= record.expires:
        record.stop.set()
        raise HTTPException(410,'This ESCRS session has ended.')
    return record


def install(core):
    import user_access

    @core.app.get('/iol/escrs-session/{view_id}',include_in_schema=False)
    def viewer(view_id: str):
        principal = user_access.require_current_principal()
        record = _owned(view_id,principal.user_id)
        html = (ROOT/'static/iol-escrs-session.html').read_text().replace('__VIEW_ID__',record.view_id)
        from .ui import version_asset_urls
        return HTMLResponse(version_asset_urls(html),headers={'Cache-Control':'no-store'})

    @core.app.get('/iol/escrs-session/{view_id}/status')
    def status(view_id: str):
        record = _owned(view_id,user_access.require_current_principal().user_id)
        return {'viewer_url':record.viewer_url,'seconds_remaining':max(0,int(record.expires-monotonic()))}

    @core.app.post('/iol/escrs-session/{view_id}/input')
    def keyboard(view_id: str,payload: dict=Body(...)):
        record = _owned(view_id,user_access.require_current_principal().user_id)
        kind = payload.get('kind')
        if kind == 'text' and isinstance(payload.get('text'),str) and 0 < len(payload['text']) <= 500:
            command={'kind':kind,'text':payload['text']}
        elif kind == 'key' and payload.get('key') in _KEYS:
            command={'kind':kind,'key':payload['key']}
        else:
            raise HTTPException(422,'Enter text or select a supported key.')
        receipt=Future()
        try:
            record.commands.put_nowait((command,receipt))
        except Full:
            raise HTTPException(429,'Please wait for the previous input.') from None
        try:
            return receipt.result(timeout=5)
        except FutureTimeout:
            raise HTTPException(504,'Input could not be confirmed.') from None

    @core.app.post('/iol/escrs-session/{view_id}/close')
    def close(view_id: str):
        _owned(view_id,user_access.require_current_principal().user_id).stop.set()
        return {'status':'closing'}
