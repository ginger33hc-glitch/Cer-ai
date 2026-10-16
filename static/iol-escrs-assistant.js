/* Build transfers only from the completed, per-eye canonical power plans. */
(() => {
  "use strict";
  const modelNames = {
    "acrysof-single-sa60at":"AcrySof SA60AT",
    "acrysof-ultrasert-au00t0":"AcrySof AU00T0",
    "acrysof-three-piece-ma60ac":"AcrySof MA60AC",
    "acrysof-vivity-dft015":"AcrySof IQ Vivity DFT015",
    "clareon-mono-sy60wf":"Clareon SY60WF",
    "acrysof-iq-sn60wf":"AcrySof SN60WF",
    "clareon-panoptix-cnwtt0":"Clareon PanOptix CNWTT0",
    "clareon-toric-cnw0t8":"Clareon Toric CNW0T2-T9",
    "clareon-panoptix-toric-cnwtt3":"Clareon PanOptix Toric CNWTT2-6",
    "clareon-vivity-toric-cnwet2":"Clareon Vivity Toric CNWET2-T6/CCWET2-T6",
    "tecnis-mono-toric-zct375":"ZCT",
    "tecnis-eyhance-toric-diu525":"DIU",
    "tecnis-odyssey-toric-drt150":"DRT",
    "tecnis-puresee-toric-det150":"DET",
    "tecnis-puresee-den00v":"DEN00V",
    "tecnis-odyssey-drn00v":"DRN00V",
    "tecnis-multifocal-zlb00":"ZLB00"
  };
  function buildPayload({plans,loadedEyes,catalog,patientName,age,sex,surgeon}) {
    const initials = String(patientName || "").trim().split(/\s+/u).filter(Boolean).map(word => [...word][0].toLocaleUpperCase("tr")).join("");
    if (!initials || !surgeon || !Number.isInteger(age) || age < 1 || age > 120) throw new Error("Review the patient name, age and signed-in doctor before ESCRS transfer.");
    if (!["Male","Female"].includes(sex)) throw new Error("Review biological sex before transfer.");
    if (!Array.isArray(loadedEyes) || loadedEyes.some(side => !["OD","OS"].includes(side)) || new Set(loadedEyes).size !== loadedEyes.length) throw new Error("Invalid eye assignment.");
    if (!loadedEyes.length || loadedEyes.some(side => !plans[side])) throw new Error("Calculate both eyes before transferring a bilateral case to ESCRS.");
    const payload = {version:1,initials,age,sex,surgeon,eyes:{}};
    for (const side of loadedEyes) {
      const plan = plans[side], lens = catalog.find(item => item.id === plan.selected_lens_id);
      if (!lens || plan.inputs?.eye !== side || plan.inputs.biological_sex !== sex) throw new Error("The current patient and eye data differ from the calculation. Recalculate before transfer.");
      if (!modelNames[lens.id]) throw new Error("This lens has no verified ESCRS model mapping. No substitute will be selected.");
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
  function request(action,payload,timeout=1500) {
    return new Promise((resolve,reject) => {
      const id = crypto.randomUUID();
      const timer = setTimeout(() => {window.removeEventListener("message",receive); reject(new Error("Install the CER-AI ESCRS Assistant, then reload this page for full automatic transfer."));},timeout);
      function receive(event) {
        if (event.source !== window || event.origin !== location.origin || event.data?.channel !== "CERAI_ESCRS_RESPONSE" || event.data.id !== id) return;
        clearTimeout(timer); window.removeEventListener("message",receive);
        event.data.ok ? resolve(event.data) : reject(new Error(event.data.error || "ESCRS assistant could not open the transfer."));
      }
      window.addEventListener("message",receive);
      window.postMessage({channel:"CERAI_ESCRS_REQUEST",id,action,payload},location.origin);
    });
  }
  async function transfer(data) {
    await request("PING");
    const response = await fetch("/auth/me",{credentials:"same-origin",cache:"no-store"});
    if (!response.ok) throw new Error("Sign in again to identify the surgeon for ESCRS.");
    const identity = await response.json();
    const payload = buildPayload({...data,surgeon:identity.user?.display_name});
    await request("TRANSFER",payload,10000);
  }
  window.CERAI_ESCRS_ASSISTANT = {buildPayload,transfer};
})();
