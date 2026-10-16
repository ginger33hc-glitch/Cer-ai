"use strict";
(async () => {
  const response = await chrome.runtime.sendMessage({action:"RECEIVE"});
  if (!response?.ok) return;
  let payload = response.payload;
  const panel = document.createElement("section"), message = document.createElement("p"), retry = document.createElement("button");
  panel.setAttribute("aria-label","CER-AI transfer status");
  panel.style.cssText = "position:fixed;bottom:12px;left:12px;right:12px;z-index:2147483647;background:#fff;border:2px solid #2563eb;border-radius:8px;padding:12px;color:#111;font:14px system-ui;box-shadow:0 2px 14px #0003";
  message.style.margin = "0 0 8px"; retry.textContent = "Retry / Yeniden dene";
  panel.append(message,retry); document.body.append(panel);
  async function start() {
    retry.disabled = true; message.textContent = "CER-AI → ESCRS: Filling and checking values / Değerler doldurulup kontrol ediliyor…";
    try {
      await CeraiEscrsAdapter.run(payload);
      message.textContent = "Transfer checked. Review all fields, lens constants and PCA method, then calculate yourself. / Aktarım kontrol edildi. Tüm alanları, lens sabitlerini ve PCA yöntemini inceleyip hesaplamayı başlatın.";
      payload = null; retry.remove();
      const close = document.createElement("button"); close.textContent = "Close / Kapat"; close.onclick = () => panel.remove(); panel.append(close);
    } catch (e) {
      message.textContent = "Transfer incomplete — do not calculate yet / Aktarım eksik — henüz hesaplamayın: " + e.message;
      retry.disabled = false;
    }
  }
  retry.addEventListener("click",start);
  await start();
  setTimeout(() => {payload = null; retry.remove();},600000);
})();
