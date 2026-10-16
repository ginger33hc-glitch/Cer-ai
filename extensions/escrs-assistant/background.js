"use strict";
const target = "https://iolcalculator.escrs.org/";
const ttl = 10 * 60 * 1000;
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  (async () => {
    const url = new URL(sender.url || "https://invalid.invalid");
    if (message.action === "TRANSFER") {
      if (!sender.tab || url.protocol !== "https:" || !["cer-ai.com", "www.cer-ai.com"].includes(url.hostname) || url.pathname !== "/iol") throw new Error("Invalid source");
      const p = message.payload;
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
