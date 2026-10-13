/* PDF transport and user-initiated sharing. Clinical results are not recalculated. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const tr = text => window.CERAI_I18N?.translate(text) ?? text;
  let snapshot = null, key = "", generation = 0, request = null, pdfUrl = null, pdfFile = null;
  const buttons = ["iolReportOpen", "iolReportPrint", "iolReportShare", "iolReportDownload"];
  function release() {
    request?.abort(); request = null;
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    pdfUrl = null; pdfFile = null;
    buttons.forEach(id => { $(id).disabled = true; });
  }
  function status(message, error = false) {
    $("iolReportStatus").textContent = tr(message);
    $("iolReportStatus").classList.toggle("error", error);
  }
  async function prepare(payload, token) {
    request = new AbortController();
    $("iolReportRetry").hidden = true;
    status("Preparing the one-page PDF…");
    try {
      const response = await fetch("/iol/report/pdf", {method:"POST", credentials:"same-origin",
        headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload), signal:request.signal});
      if (!response.ok) throw new Error("Report could not be prepared. Review the results and retry.");
      if (!(response.headers.get("content-type") || "").includes("application/pdf")) throw new Error("Report could not be prepared. Review the results and retry.");
      const blob = await response.blob();
      if (token !== generation) return;
      pdfUrl = URL.createObjectURL(blob);
      pdfFile = new File([blob], "cerai-iol-report.pdf", {type:"application/pdf"});
      buttons.forEach(id => { $(id).disabled = false; });
      status("One-page PDF ready. Contains patient information.");
    } catch (error) {
      if (token !== generation || error.name === "AbortError") return;
      status("Report could not be prepared. Review the results and retry.", true);
      $("iolReportRetry").hidden = false;
    }
  }
  function setCase(value) {
    const payload = value ? {...value, locale:document.documentElement.lang === "tr" ? "tr" : "en"} : null;
    const nextKey = payload ? JSON.stringify(payload) : "";
    if (nextKey === key) return;
    snapshot = value ? JSON.parse(JSON.stringify(value)) : null;
    key = nextKey; generation++; release();
    $("iolReportSection").hidden = !payload;
    if (payload) void prepare(payload, generation);
  }
  function download() {
    if (!pdfUrl) return;
    const link = document.createElement("a"); link.href = pdfUrl; link.download = "cerai-iol-report.pdf";
    document.body.appendChild(link); link.click(); link.remove();
  }
  function openPdf(print = false) {
    if (!pdfUrl) return;
    const viewer = window.open(pdfUrl, "_blank");
    if (!viewer) { status("Allow pop-ups to open the PDF, or download it.", true); return; }
    viewer.opener = null;
    if (print) {
      // Native PDF viewers differ on mobile; their own Print command remains available.
      viewer.addEventListener("load", () => { try { viewer.focus(); viewer.print(); } catch (_) { /* Native viewer controls. */ } }, {once:true});
      status("PDF opened for printing. If needed, use the PDF viewer's Print command.");
    }
  }
  $("iolReportOpen").addEventListener("click", () => openPdf());
  $("iolReportPrint").addEventListener("click", () => openPdf(true));
  $("iolReportDownload").addEventListener("click", download);
  $("iolReportShare").addEventListener("click", async () => {
    if (!pdfFile) return;
    const token = generation;
    if (!navigator.canShare?.({files:[pdfFile]}) || !navigator.share) {
      download(); status("File sharing is unavailable in this browser. PDF downloaded for sharing."); return;
    }
    try {
      // File was prepared before this click, preserving native user activation.
      await navigator.share({files:[pdfFile], title:"CER-AI IOL"});
    } catch (error) {
      if (token !== generation || error.name === "AbortError") return;
      status("Sharing could not be completed. You can download the PDF.", true);
    }
  });
  $("iolReportRetry").addEventListener("click", () => {
    const retry = snapshot; key = ""; setCase(retry);
  });
  new MutationObserver(() => { if (snapshot) setCase(snapshot); }).observe(document.documentElement, {attributes:true, attributeFilter:["lang"]});
  window.addEventListener("pagehide", () => { generation++; release(); key = ""; });
  window.addEventListener("pageshow", event => { if (event.persisted && snapshot) setCase(snapshot); });
  window.CERAI_IOL_REPORT = {setCase};
})();
