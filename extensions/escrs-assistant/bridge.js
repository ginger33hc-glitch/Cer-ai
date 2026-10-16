/* Only user-initiated transfers from CER-AI's IOL page enter the extension. */
"use strict";
window.addEventListener("message", async event => {
  if (event.source !== window || event.origin !== location.origin) return;
  const message = event.data;
  if (!message || message.channel !== "CERAI_ESCRS_REQUEST" || typeof message.id !== "string") return;
  if (!["PING", "TRANSFER"].includes(message.action)) return;
  let result;
  try {
    result = message.action === "PING" ? {ok:true, version:1} :
      await chrome.runtime.sendMessage({action:"TRANSFER", payload:message.payload});
  } catch (_) { result = {ok:false, error:"ESCRS assistant could not open the transfer."}; }
  window.postMessage({channel:"CERAI_ESCRS_RESPONSE", id:message.id, ...result}, location.origin);
});
