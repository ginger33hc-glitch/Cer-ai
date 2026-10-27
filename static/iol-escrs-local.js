(() => {
  'use strict';
  const base='/iol/escrs-local/'+document.body.dataset.session;
  const screen=document.getElementById('screen'), status=document.getElementById('status');
  const viewport=document.getElementById('viewport'), fields=document.getElementById('fields');
  let ended=false, frameURL=null, chain=Promise.resolve(), editing=false, pointer=null;
  async function request(path,body) {
    const response=await fetch(base+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    if(!response.ok){if([401,403,410].includes(response.status))finish();throw new Error('Bağlantı tamamlanamadı ('+response.status+')');}
    return response;
  }
  function finish(){ended=true;viewport.hidden=true;if(frameURL)URL.revokeObjectURL(frameURL);status.textContent='Oturum sona erdi';}
  function send(body){
    chain=chain.then(async()=>{if(!ended)await request('/input',body);}).catch(error=>{status.textContent=error.message;});
    return chain;
  }
  function showFields(items){
    if(editing)return;
    fields.replaceChildren();
    for(const f of items){
      const input=document.createElement('input');input.className='field';input.value=f.value;
      input.setAttribute('aria-label','ESCRS form alanı');input.autocomplete='off';
      input.inputMode=f.type==='number'?'decimal':'text';
      Object.assign(input.style,{left:(f.x/420*100)+'%',top:(f.y/820*100)+'%',width:(f.width/420*100)+'%',height:(f.height/820*100)+'%'});
      input.onfocus=()=>{editing=true;};
      input.oninput=()=>send({kind:'edit',field:f.id,text:input.value});
      input.onblur=()=>{chain.finally(()=>{editing=false;});};
      input.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();send({kind:'key',key:'Enter'});input.blur();}};
      fields.appendChild(input);
    }
  }
  async function refresh(){
    if(ended)return;
    try {
      await chain;
      const response=await request('/frame'), blob=await response.blob();
      if(ended)return;
      const next=URL.createObjectURL(blob), previous=frameURL;
      screen.src=next;frameURL=next;if(previous)URL.revokeObjectURL(previous);
      if(!editing){const data=await (await request('/fields')).json();showFields(data);}
      status.textContent='';
    }catch(error){status.textContent=error.message;}
    if(!ended)setTimeout(refresh,400);
  }
  viewport.addEventListener('pointerdown',event=>{
    pointer={id:event.pointerId,x:event.clientX,y:event.clientY,lastY:event.clientY,moved:false,field:event.target.classList.contains('field')};
    if(!pointer.field)viewport.setPointerCapture(event.pointerId);
  });
  viewport.addEventListener('pointermove',event=>{
    if(!pointer||pointer.id!==event.pointerId)return;
    const delta=(pointer.lastY-event.clientY)*420/viewport.clientWidth;
    if(Math.abs(event.clientY-pointer.y)>6){pointer.moved=true;if(document.activeElement?.classList.contains('field'))document.activeElement.blur();viewport.setPointerCapture(event.pointerId);}
    if(pointer.moved&&Math.abs(delta)>8){send({kind:'scroll',delta:Math.max(-1600,Math.min(1600,delta))});pointer.lastY=event.clientY;}
  });
  viewport.addEventListener('pointerup',event=>{
    if(!pointer||pointer.id!==event.pointerId)return;
    if(!pointer.moved&&!pointer.field){const r=screen.getBoundingClientRect();send({kind:'click',x:(event.clientX-r.left)*420/r.width,y:(event.clientY-r.top)*820/r.height});}
    pointer=null;
  });
  viewport.addEventListener('pointercancel',()=>{pointer=null;});
  viewport.addEventListener('wheel',event=>{event.preventDefault();send({kind:'scroll',delta:Math.max(-1600,Math.min(1600,event.deltaY))});},{passive:false});
  document.getElementById('pdf').href=base+'/pdf';
  document.getElementById('close').onclick=async()=>{try{await chain;await request('/close',{});finish();if(window.opener&&!window.opener.closed)window.close();else window.location.assign('/iol');}catch(error){status.textContent=error.message;}};
  window.addEventListener('pagehide',()=>{if(!ended)navigator.sendBeacon(base+'/close',new Blob(['{}'],{type:'application/json'}));});
  request('/status').then(r=>r.json()).then(data=>{
    const expires=Date.now()+data.seconds_remaining*1000;refresh();
    const timer=setInterval(()=>{const left=Math.max(0,Math.ceil((expires-Date.now())/1000));document.getElementById('timer').textContent=Math.floor(left/60)+':'+String(left%60).padStart(2,'0');if(!left||ended){clearInterval(timer);finish();}},1000);
  }).catch(error=>{status.textContent=error.message;});
})();
