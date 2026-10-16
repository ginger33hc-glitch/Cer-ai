"use strict";
const target = "https://iolcalculator.escrs.org/";
function syntheticCase() {
  const eye = {toric:true,axial_length_mm:23.5,acd_mm:3.1,k1_d:42.5,k2_d:44,k1_axis_deg:15,k2_axis_deg:105,cct_um:550,lens_thickness_mm:4.3,wtw_mm:11.8,incision_axis_deg:180,sia_d:0.25,target_refraction_d:-0.25,a_constant:119.1,prior_corneal_surgery:"NONE",manufacturer_matches:["Alcon"],lens_matches:["Clareon PanOptix Toric CNWTT2-6"]};
  return {version:1,surgeon:"CER-AI SYNTHETIC TEST",initials:"TEST",age:61,sex:"Female",eyes:{OD:eye,OS:{...eye,toric:false,axial_length_mm:24.2,acd_mm:3.6,k1_d:43,k2_d:44.5,k1_axis_deg:170,k2_axis_deg:80,cct_um:540,lens_thickness_mm:4.1,wtw_mm:12,target_refraction_d:-0.5,a_constant:119.3,manufacturer_matches:["Johnson and Johnson Vision"],lens_matches:["DEN00V"]}}};
}
const ttl = 10 * 60 * 1000;
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  (async () => {
    const url = new URL(sender.url || "https://invalid.invalid");
    if (["TRANSFER","SELF_TEST"].includes(message.action)) {
      const selfTest = message.action === "SELF_TEST";
      if (selfTest && sender.url !== chrome.runtime.getURL("test.html")) throw new Error("Invalid test source");
      if (!selfTest && (!sender.tab || url.protocol !== "https:" || !["cer-ai.com", "www.cer-ai.com"].includes(url.hostname) || url.pathname !== "/iol")) throw new Error("Invalid source");
      const p = selfTest ? syntheticCase() : message.payload;
      if (!p || p.version !== 1 || JSON.stringify(p).length > 24000) throw new Error("Invalid transfer");
      const records = await chrome.storage.session.get(null);
      await chrome.storage.session.remove(Object.keys(records).filter(key => records[key].expires < Date.now()));
      // Session-only memory; no patient data in URLs, disk storage, or logs.
      const tab = await chrome.tabs.create({url:"about:blank", active:true});
      await chrome.storage.session.set({[String(tab.id)]:{payload:p, expires:Date.now()+ttl}});
      await chrome.tabs.update(tab.id, {url:target});
      return {ok:true};
    }
    if (message.action === "RECEIVE") {
      if (!sender.tab || url.origin !== new URL(target).origin || url.pathname !== "/") throw new Error("Invalid destination");
      const key = String(sender.tab.id), record = (await chrome.storage.session.get(key))[key];
      await chrome.storage.session.remove(key);
      return record && record.expires > Date.now() ? {ok:true,payload:record.payload} : {ok:false};
    }
    throw new Error("Invalid action");
  })().then(respond, () => respond({ok:false,error:"ESCRS assistant could not open the transfer."}));
  return true;
});
chrome.tabs.onRemoved.addListener(id => chrome.storage.session.remove(String(id)));
