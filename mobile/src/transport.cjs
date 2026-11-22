'use strict';
const CERAI='https://cer-ai.com', ESCRS='https://iolcalculator.escrs.org/';
function trustedCerai(url, onlyIol=false) {
  try {const u=new URL(url);return u.protocol==='https:' && ['cer-ai.com','www.cer-ai.com'].includes(u.hostname) && !u.port && (!onlyIol || u.pathname==='/iol');} catch{return false;}
}
function trustedEscrs(url) {try {const u=new URL(url);return u.origin==='https://iolcalculator.escrs.org';}catch{return false;}}
function parseRequest(raw,url) {
  if(!trustedCerai(url,true) || typeof raw!=='string' || raw.length>25000)return null;
  let m;try{m=JSON.parse(raw);}catch{return null;}
  if(m.channel!=='CERAI_ESCRS_REQUEST' || typeof m.id!=='string' || m.id.length>100 || !['PING','TRANSFER'].includes(m.action))return null;
  if(m.action==='TRANSFER' && (!m.payload || m.payload.version!==1 || !m.payload.eyes || !Object.keys(m.payload.eyes).length || Object.keys(m.payload.eyes).some(s=>!['OD','OS'].includes(s))))return null;
  return m;
}
// Inject only into the top-level CER-AI IOL document. No patient data in the URL.
const bridge=`(()=>{if(window.top!==window || !['https://cer-ai.com','https://www.cer-ai.com'].includes(location.origin) || location.pathname!=='/iol' || window.__ceraiMobileBridge)return;window.__ceraiMobileBridge=true;window.addEventListener('message',event=>{if(event.source!==window || event.origin!==location.origin || event.data?.channel!=='CERAI_ESCRS_REQUEST')return;window.ReactNativeWebView.postMessage(JSON.stringify(event.data));});})();true;`;
function responseScript(id,result) {return `(()=>{if(!['https://cer-ai.com','https://www.cer-ai.com'].includes(location.origin) || location.pathname!=='/iol')return;window.postMessage(${JSON.stringify({channel:'CERAI_ESCRS_RESPONSE',id,...result})},location.origin);})();true;`;}
function transferScript(adapter,payload,id) {
  return `(()=>{if(window.top!==window || location.origin!=='https://iolcalculator.escrs.org' || location.pathname!=='/' || window.__ceraiTransferRunning)return;window.__ceraiTransferRunning=true;${adapter}\nPromise.resolve().then(()=>CeraiEscrsAdapter.run(${JSON.stringify(payload)})).then(()=>window.ReactNativeWebView.postMessage(JSON.stringify({channel:'CERAI_MOBILE_STATUS',id:${JSON.stringify(id)},ok:true})),error=>window.ReactNativeWebView.postMessage(JSON.stringify({channel:'CERAI_MOBILE_STATUS',id:${JSON.stringify(id)},ok:false,error:String(error.message).slice(0,500)}))).finally(()=>{window.__ceraiTransferRunning=false;});})();true;`;
}
module.exports={CERAI,ESCRS,trustedCerai,trustedEscrs,parseRequest,bridge,responseScript,transferScript};
