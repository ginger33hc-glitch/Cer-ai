(() => {
  'use strict';
  const base='/iol/escrs-local/'+document.body.dataset.session;
  const screen=document.getElementById('screen'), status=document.getElementById('status');
  const input=document.getElementById('keyboard');
  let ended=false, busy=false, frameURL=null, expires=0;
  async function request(path,body) {
    const response=await fetch(base+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    if(!response.ok){if([401,403,410].includes(response.status))finish();throw new Error('Oturum isteği başarısız / Session request failed ('+response.status+')');}
    return response;
  }
  function finish(){ended=true;screen.hidden=true;screen.removeAttribute('src');if(frameURL)URL.revokeObjectURL(frameURL);status.textContent='Oturum sona erdi / Session ended';}
  async function refresh(){
    if(ended)return;
    try {
      const response=await request('/frame');
      const blob=await response.blob();
      if(ended)return;
      const next=URL.createObjectURL(blob), previous=frameURL;
      screen.src=next;frameURL=next;if(previous)URL.revokeObjectURL(previous);
      status.textContent='';
    }catch(error){status.textContent=error.message;}
    if(!ended)setTimeout(refresh,800);
  }
  async function send(body){
    if(busy||ended)return;busy=true;
    try{await request('/input',body);if(body.kind==='text')input.value='';status.textContent='';}
    catch(error){status.textContent=error.message;}finally{busy=false;}
  }
  screen.addEventListener('click',event=>{const r=screen.getBoundingClientRect();send({kind:'click',x:(event.clientX-r.left)*420/r.width,y:(event.clientY-r.top)*820/r.height});});
  screen.addEventListener('wheel',event=>{event.preventDefault();send({kind:'scroll',delta:Math.max(-1600,Math.min(1600,event.deltaY))});},{passive:false});
  document.querySelectorAll('[data-scroll]').forEach(b=>b.onclick=()=>send({kind:'scroll',delta:Number(b.dataset.scroll)}));
  document.querySelectorAll('[data-key]').forEach(b=>b.onclick=()=>send({kind:'key',key:b.dataset.key}));
  document.getElementById('send').onclick=()=>{if(input.value)send({kind:'text',text:input.value});};
  document.getElementById('pdf').href=base+'/pdf';
  document.getElementById('close').onclick=async()=>{try{await request('/close',{});finish();if(window.opener&&!window.opener.closed)window.close();else window.location.assign('/iol');}catch(error){status.textContent=error.message;}};
  window.addEventListener('pagehide',()=>{if(!ended)navigator.sendBeacon(base+'/close',new Blob(['{}'],{type:'application/json'}));});
  request('/status').then(r=>r.json()).then(data=>{
    expires=Date.now()+data.seconds_remaining*1000;refresh();
    const timer=setInterval(()=>{const left=Math.max(0,Math.ceil((expires-Date.now())/1000));document.getElementById('timer').textContent=Math.floor(left/60)+':'+String(left%60).padStart(2,'0');if(!left||ended){clearInterval(timer);finish();}},1000);
  }).catch(error=>{status.textContent=error.message;});
})();
