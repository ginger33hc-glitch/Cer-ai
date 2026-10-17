(() => {
  'use strict';
  const tr=text=>window.CERAI_I18N?.translate(text) || text;
  const base='/iol/escrs-session/'+document.body.dataset.session;
  const status=document.getElementById('status'), input=document.getElementById('keyboard');
  let remaining=0, ended=false, busy=false;
  async function request(path,body) {
    const response=await fetch(base+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    const result=await response.json();
    if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Session request failed.');
    return result;
  }
  async function send(body) {
    if(busy||ended)return;
    busy=true;status.textContent='';
    try {await request('/input',body);if(body.kind==='text')input.value='';}
    catch(error){status.textContent=tr(error.message);}
    finally{busy=false;}
  }
  document.getElementById('send').addEventListener('click',()=>{if(input.value)send({kind:'text',text:input.value});});
  document.querySelectorAll('[data-key]').forEach(button=>button.addEventListener('click',()=>send({kind:'key',key:button.dataset.key})));
  document.getElementById('close').addEventListener('click',async()=>{try{await request('/close',{});ended=true;document.getElementById('viewer').src='about:blank';status.textContent=tr('Session ended.');}catch(error){status.textContent=tr(error.message);}});
  request('/status').then(result=>{
    const url=new URL(result.viewer_url);
    if(url.protocol!=='https:'||!['www.browserbase.com','browserbase.com'].includes(url.hostname))throw new Error('Invalid session viewer.');
    document.getElementById('viewer').src=url.href;remaining=result.seconds_remaining;const expires=Date.now()+remaining*1000;
    const timer=setInterval(()=>{remaining=Math.max(0,Math.ceil((expires-Date.now())/1000));document.getElementById('timer').textContent=Math.floor(remaining/60)+':'+String(remaining%60).padStart(2,'0');if(!remaining||ended){clearInterval(timer);ended=true;document.getElementById('viewer').src='about:blank';status.textContent=tr('Session ended.');}},1000);
  }).catch(error=>{status.textContent=tr(error.message);});
})();
