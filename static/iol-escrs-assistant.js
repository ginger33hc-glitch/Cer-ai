/* Build transfers only from the completed, per-eye canonical power plans. */
(() => {
  "use strict";

  function buildPayload({plans,loadedEyes,catalog,patientName,age,sex,surgeon,modelNames}) {
    const initials = String(patientName || "").trim().split(/\s+/u).filter(Boolean).map(word => [...word][0].toLocaleUpperCase("tr")).join("");
    if (!initials || !surgeon || !Number.isInteger(age) || age < 1 || age > 120) throw new Error("Review the patient name, age and signed-in doctor before ESCRS transfer.");
    if (!["Male","Female"].includes(sex)) throw new Error("Review biological sex before transfer.");
    if (!Array.isArray(loadedEyes) || loadedEyes.some(side => !["OD","OS"].includes(side)) || new Set(loadedEyes).size !== loadedEyes.length) throw new Error("Invalid eye assignment.");
    if (!loadedEyes.length || loadedEyes.some(side => !plans[side])) throw new Error("Calculate both eyes before transferring a bilateral case to ESCRS.");
    const payload = {version:1,initials,age,sex,surgeon,eyes:{}};
    for (const side of loadedEyes) {
      const plan = plans[side], lens = catalog.find(item => item.id === plan.selected_lens_id);
      if (!lens || plan.inputs?.eye !== side || plan.inputs.biological_sex !== sex) throw new Error("The current patient and eye data differ from the calculation. Recalculate before transfer.");
      if (!modelNames || !modelNames[lens.id]) throw new Error("This lens has no verified ESCRS model mapping. No substitute will be selected.");
      const toric = plan.route === "MANUFACTURER_TORIC";
      if (toric && !String(lens.subtype || "").toLowerCase().includes("toric")) throw new Error("Select the intended toric lens family and recalculate before automatic transfer.");
      const fields = ["axial_length_mm","acd_mm","k1_d","k2_d","k1_axis_deg","k2_axis_deg","cct_um","lens_thickness_mm","wtw_mm","incision_axis_deg","sia_d","prior_corneal_surgery"];
      const eye = Object.fromEntries(fields.map(key => [key,plan.inputs[key] ?? null]));
      Object.assign(eye,{toric,target_refraction_d:plan.target_refraction_d,a_constant:plan.a_constant,
        lens_id:lens.id,lens_matches:[modelNames[lens.id]],
        manufacturer_matches:[lens.manufacturer === "Johnson & Johnson" ? "Johnson and Johnson Vision" : lens.manufacturer]});
      payload.eyes[side] = eye;
    }
    return payload;
  }
  async function transfer(data, onProgress = () => {}, sessionWindow = null, consentAlreadyAccepted = false) {
    const tr = text => window.CERAI_I18N?.translate ? window.CERAI_I18N.translate(text) : text;
    try {
      onProgress("Checking surgeon identity and ESCRS configuration…");
      const [identityResponse,configResponse] = await Promise.all([
        fetch("/auth/me",{credentials:"same-origin",cache:"no-store"}),
        fetch("/iol/escrs-cloud-config",{credentials:"same-origin",cache:"no-store"})
      ]);
      if (!identityResponse.ok) throw new Error("Sign in again to identify the surgeon for ESCRS.");
      const config = await configResponse.json();
      if (!configResponse.ok || !config.enabled) throw new Error("ESCRS cloud transfer is unavailable.");
      const identity = await identityResponse.json();
      const provider = config.provider || "browserless";
      if (!["browserless","browserbase"].includes(provider)) throw new Error("Invalid ESCRS provider.");
      const disclosure = tr("This transfer sends patient initials, age, biological sex, eye measurements, previous corneal surgery, selected lens, target refraction and the signed-in surgeon name to {provider} cloud browsers and the ESCRS IOL Calculator. These data remain potentially identifiable. Full patient names and source images are not sent. Continue only if authorized to disclose these data to both services.").replace("{provider}",provider === "browserbase" ? "Browserbase" : "Browserless");
      if (!consentAlreadyAccepted && !window.confirm(disclosure + "\n\n" + tr("I accept the ESCRS calculator terms for this calculation: https://iolcalculator.escrs.org/Resources/ESCRS_IOL_Calculator_Terms_of_Use.pdf"))) { if (sessionWindow && !sessionWindow.closed) sessionWindow.close(); return false; }
      onProgress("Validating completed IOL plans and lens mappings…");
      const payload = buildPayload({...data,surgeon:identity.user?.display_name,modelNames:config.models});
      onProgress("Starting ESCRS cloud transfer…");
      const response = await fetch("/iol/escrs-cloud-transfer",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({...payload,terms_accepted:true,data_transfer_accepted:true,consent_version:"ESCRS-CLOUD-2026-10-17-V2",provider})});
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 422 && Array.isArray(result.detail)) {
          const consentError = result.detail.some(item => (item.loc || []).some(field => ["terms_accepted","data_transfer_accepted","consent_version"].includes(field)));
          throw new Error(tr(consentError
            ? "This page is out of date. Reload CER-AI and accept the current ESCRS data-transfer disclosure."
            : "Review the patient details and eye measurements before ESCRS transfer. The transfer was not started."));
        }
        throw new Error(typeof result.detail === "string" ? result.detail : tr("ESCRS cloud transfer could not be verified."));
      }
      onProgress("ESCRS session created. Opening the session…");
      const url = new URL(result.escrs_url, window.location?.origin || "https://cer-ai.com");
      const valid = provider === "browserbase"
        ? url.origin === window.location.origin && /^\/iol\/escrs-session\/[a-f0-9]{32}$/.test(url.pathname)
        : ["production-sfo.browserless.io","production-ams.browserless.io","production-lon.browserless.io"].includes(url.hostname) && url.pathname.includes("/live/");
      if (url.protocol !== "https:" || !valid) throw new Error("Invalid ESCRS cloud session address.");
      if (sessionWindow) {
        if (sessionWindow.closed) throw new Error("ESCRS window was closed. Retry the transfer.");
        sessionWindow.location.replace(url.href);
      } else {
        // Keep the calculation and busy button visible until a validated session is ready.
        window.location.assign(url.href);
      }
      return true;
    } catch(error) { if (sessionWindow && !sessionWindow.closed) sessionWindow.close(); throw error; }
  }
  window.CERAI_ESCRS_ASSISTANT = {buildPayload,transfer};
})();
