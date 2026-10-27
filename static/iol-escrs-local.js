(() => {
  'use strict';
  // Keep one request in flight; collapse only adjacent, unsent operations.
  // Click/key barriers retain order and every edit retains its final value.
  class InputQueue {
    constructor(deliver, changed) {this.deliver=deliver;this.changed=changed;this.pending=[];this.running=null;}
    get busy(){return !!this.running || this.pending.length>0;}
    send(body){
      const last=this.pending[this.pending.length-1];
      if(last && body.kind==='edit' && last.kind==='edit' && last.field===body.field)last.text=body.text;
      else if(last && body.kind==='scroll' && last.kind==='scroll')last.delta+=body.delta;
      else this.pending.push({...body});
      if(!this.running)this.running=Promise.resolve().then(()=>this.flush());
      return this.running;
    }
    async flush(){
      try {
        while(this.pending.length){
          const body=this.pending.shift();
          if(body.kind==='scroll'){
            const total=body.delta;body.delta=Math.max(-1600,Math.min(1600,total));
            if(total!==body.delta)this.pending.unshift({kind:'scroll',delta:total-body.delta});
            if(!body.delta)continue;
          }
          await this.deliver(body);this.changed();
        }
      } catch(error){this.pending.length=0;throw error;}
      finally {this.running=null;}
    }
    drain(){return this.running || Promise.resolve();}
  }
  if(typeof module!=='undefined' && module.exports){module.exports=InputQueue;return;}
  const base='/iol/escrs-local/'+document.body.dataset.session;
  const screen=document.getElementById('screen'), status=document.getElementById('status');
  const viewport=document.getElementById('viewport');
  let ended=false, frameURL=null, pointer=null, refreshTimer=null, refreshing=false, lastAction=0;
  async function request(path,body) {
    const response=await fetch(base+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    if(!response.ok){if([401,403,410].includes(response.status))finish();throw new Error('Bağlantı tamamlanamadı ('+response.status+')');}
    return response;
  }
  function finish(){ended=true;viewport.hidden=true;if(frameURL)URL.revokeObjectURL(frameURL);status.textContent='Oturum sona erdi';}
  function wake(){
    lastAction=Date.now();
    if(!refreshing && !ended){clearTimeout(refreshTimer);refreshTimer=setTimeout(refresh,0);}
  }
  const inputQueue=new InputQueue(async body=>{if(!ended)await request('/input',body);},wake);
  function send(body){
    lastAction=Date.now();
    return inputQueue.send(body).catch(error=>{status.textContent=error.message;throw error;});
  }
  function enqueue(body){send(body).catch(()=>{});}
  async function refresh(){
    if(ended || refreshing)return;
    refreshing=true;
    try {
      const response=await request('/frame'), blob=await response.blob();
      if(ended)return;
      const next=URL.createObjectURL(blob), previous=frameURL;
      screen.src=next;frameURL=next;if(previous)URL.revokeObjectURL(previous);
      status.textContent='';
    }catch(error){status.textContent=error.message;}
    refreshing=false;
    if(!ended)refreshTimer=setTimeout(refresh,Date.now()-lastAction<1200?80:800);
  }
  viewport.addEventListener('pointerdown',event=>{
    pointer={id:event.pointerId,x:event.clientX,y:event.clientY,lastY:event.clientY,moved:false};
    viewport.setPointerCapture(event.pointerId);
  });
  viewport.addEventListener('pointermove',event=>{
    if(!pointer||pointer.id!==event.pointerId)return;
    const delta=(pointer.lastY-event.clientY)*420/viewport.clientWidth;
    if(Math.abs(event.clientY-pointer.y)>6){pointer.moved=true;viewport.setPointerCapture(event.pointerId);}
    if(pointer.moved&&Math.abs(delta)>8){enqueue({kind:'scroll',delta:Math.max(-1600,Math.min(1600,delta))});pointer.lastY=event.clientY;}
  });
  viewport.addEventListener('pointerup',event=>{
    if(!pointer||pointer.id!==event.pointerId)return;
    if(!pointer.moved){const r=screen.getBoundingClientRect();enqueue({kind:'click',x:(event.clientX-r.left)*420/r.width,y:(event.clientY-r.top)*820/r.height});}
    pointer=null;
  });
  viewport.addEventListener('pointercancel',()=>{pointer=null;});
  viewport.addEventListener('wheel',event=>{event.preventDefault();enqueue({kind:'scroll',delta:Math.max(-1600,Math.min(1600,event.deltaY))});},{passive:false});
  document.getElementById('pdf').href=base+'/pdf';
  document.getElementById('close').onclick=async()=>{try{await inputQueue.drain();await request('/close',{});finish();if(window.opener&&!window.opener.closed)window.close();else window.location.assign('/iol');}catch(error){status.textContent=error.message;}};
  window.addEventListener('pagehide',()=>{if(!ended)navigator.sendBeacon(base+'/close',new Blob(['{}'],{type:'application/json'}));});
  request('/status').then(r=>r.json()).then(data=>{
    const expires=Date.now()+data.seconds_remaining*1000;refresh();
    const timer=setInterval(()=>{const left=Math.max(0,Math.ceil((expires-Date.now())/1000));document.getElementById('timer').textContent=Math.floor(left/60)+':'+String(left%60).padStart(2,'0');if(!left||ended){clearInterval(timer);finish();}},1000);
  }).catch(error=>{status.textContent=error.message;});
})();
