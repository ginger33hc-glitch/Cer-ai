(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const originals = {OD:null, OS:null};
  const pentacamByEye = {OD:null, OS:null};
  const corneaBackByEye = {OD:null, OS:null};
  const incisionOverrides = {OD:null, OS:null};
  const posteriorFields = ["k1_d","k2_d","k1_axis_deg","k2_axis_deg"];
  const controllers = new Map();
  let loadedEyes = [];
  let caseVersion = 0;
  let lensCatalog = [];
  let iolAssessmentRequestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  const tr = value => window.CERAI_I18N?.translate(value) ?? String(value ?? "");
  const warningLabel = code => ({
    WARN_RETINA_SIGNIFICANT:"Significant retinal disease: multifocal IOL excluded.",
    WARN_RETINA_MILD:"Mild retinal disease requires surgeon review.",
    WARN_MACULAR_PATHOLOGY:"Macular pathology: multifocal IOL excluded.",
    WARN_GLAUCOMA_PRESENT:"Definite glaucoma: multifocal IOL excluded.",
    WARN_GLAUCOMA_SUSPECT:"Glaucoma suspect: multifocal IOL requires caution.",
    WARN_OCULAR_SURFACE_MODERATE:"Moderate active ocular-surface disease: multifocal IOL excluded.",
    WARN_OCULAR_SURFACE_SIGNIFICANT:"Significant active ocular-surface disease: multifocal IOL excluded.",
    WARN_OCULAR_SURFACE_MILD:"Mild ocular-surface disease requires optimization and review.",
    WARN_HOA_HIGH:"High total corneal HOA: multifocal IOL excluded.",
    WARN_HOA_MODERATE:"Moderate total corneal HOA requires caution.",
    WARN_KAPPA_HIGH:"High angle kappa: multifocal IOL excluded.",
    WARN_ALPHA_HIGH:"High angle alpha: multifocal IOL excluded.",
    WARN_PUPIL_TOO_SMALL:"Pupil diameter below 2.00 mm: multifocal IOL excluded.",
    WARN_PUPIL_TOO_LARGE:"Pupil diameter above 4.00 mm: multifocal IOL excluded.",
    WARN_IRREGULAR_ASTIGMATISM:"Irregular astigmatism: multifocal IOL excluded.",
  })[code] || code;

  function errorMessage(data) {
    if (typeof data.detail === "string") return tr(data.detail);
    if (!Array.isArray(data.detail)) return tr("Required information is incomplete or invalid.");
    const turkish = document.documentElement.lang === "tr";
    const labels = {
      patient_name:["Patient name","Hasta adı"], biological_sex:["Biological sex","Cinsiyet"],
      eye:["Eye","Göz"], selected_lens_id:["Clinic lens family","Klinik lens ailesi"],
      axial_length_mm:["Axial length (mm)","Aksiyel uzunluk (mm)"], acd_mm:["ACD (mm)","ACD (mm)"],
      k1_d:["K1 (D)","K1 (D)"], k2_d:["K2 (D)","K2 (D)"],
      k1_axis_deg:["K1 axis (°)","K1 aksı (°)"], k2_axis_deg:["K2 axis (°)","K2 aksı (°)"],
      lens_thickness_mm:["Lens thickness (mm)","Lens kalınlığı (mm)"],
      wtw_mm:["HWTW (mm)","HWTW (mm)"], cct_um:["Pachy Vertex (µm)","Pachy Vertex (µm)"],
      astigmatism_type:["Astigmatism regularity","Astigmatizmanın düzenliliği"],
      incision_axis_deg:["Incision axis (°)","Kesi aksı (°)"], sia_d:["SIA (D)","SIA (D)"],
      sia_axis_deg:["SIA axis (°)","SIA aksı (°)"],
      posterior_cornea:["Cornea Back","Arka kornea"],
    };
    return data.detail.map(error => {
      const path = (error.loc || []).filter(part => part !== "body");
      const field = path.map(part => labels[part]?.[turkish ? 1 : 0] || String(part)).join(" / ");
      let message = String(error.msg || "Invalid value").replace(/^Value error, /, "");
      if (turkish) {
        const bounds = error.ctx || {};
        if (error.type === "missing") message = "Bu alan zorunludur.";
        else if (error.type === "greater_than_equal") message = `En az ${bounds.ge} olmalıdır.`;
        else if (error.type === "greater_than") message = `${bounds.gt} değerinden büyük olmalıdır.`;
        else if (error.type === "less_than_equal") message = `En fazla ${bounds.le} olmalıdır.`;
        else if (error.type === "less_than") message = `${bounds.lt} değerinden küçük olmalıdır.`;
        else if (["float_parsing", "float_type", "int_parsing", "int_type", "finite_number"].includes(error.type)) message = "Geçerli bir sayı girilmelidir.";
        else if (["enum", "literal_error"].includes(error.type)) message = `Geçerli bir seçenek seçilmelidir: ${bounds.expected || ""}`;
        else if (error.type === "string_too_short") message = `En az ${bounds.min_length} karakter girilmelidir.`;
        else message = tr(message);
      }
      return field ? `${field}: ${message}` : message;
    }).join("\n") || tr("Required information is incomplete or invalid.");
  }

  function createEyeController(eye) {
    const fragment = document.getElementById("eyeTemplate").content.cloneNode(true);
    const root = fragment.querySelector(".eye-workspace");
    const controls = new Map();
    root.querySelectorAll("[id]").forEach(node => { controls.set(node.id, node); node.id = `${eye}-${node.id}`; });
    root.querySelectorAll("label[for]").forEach(node => { node.htmlFor = `${eye}-${node.htmlFor}`; });
    const $ = id => controls.get(id) || document.getElementById(id);
    const numberOrNull = id => $(id).value === "" ? null : Number($(id).value);
    const setIfPresent = (id, value) => { if (value !== null && value !== undefined) $(id).value = value; };
    let recommendation = null;
    let version = 0;
    $("eye").value = eye;
    $("eyeHeading").textContent = tr(eye === "OD" ? "OD — Right eye" : "OS — Left eye");
    root.hidden = true;
    document.getElementById("eyePanels").appendChild(fragment);
  const kDifference = () => $("k1").value === "" || $("k2").value === "" ? NaN : Math.abs(Number($("k2").value) - Number($("k1").value));

  function updateAstigmatism() {
    const difference = kDifference();
    $("kDifference").value = Number.isFinite(difference) ? `${difference.toFixed(2)} D` : "";
    const required = difference >= 1;
    $("astigType").required = required;
    $("incisionField").hidden = !required;
    $("siaField").hidden = !required;
    $("siaAxisField").hidden = !required;
    $("incisionAxis").required = required;
    $("sia").required = required;
    if (required) {
      const steep = numberOrNull("k2Axis");
      $("incisionAxis").value = incisionOverrides[$("eye").value] ?? (steep === null ? "" : steep);
      $("siaAxis").value = $("incisionAxis").value;
      $("sia").value = "0.25";
    }
  }

  function populateEye() {
    const eye = $("eye").value;
    const bio = originals[eye];
    const pentacam = pentacamByEye[eye];
    if (bio) {
      setIfPresent("al", bio.axial_length_mm); setIfPresent("k1", bio.k1_d);
      setIfPresent("k1Axis", bio.k1_axis_deg); setIfPresent("k2", bio.k2_d);
      setIfPresent("k2Axis", bio.k2_axis_deg); setIfPresent("lensThickness", bio.lens_thickness_mm);
      if (!pentacam) setIfPresent("acd", bio.acd_mm);
      $("alMarker").textContent = bio.axial_length_edited_marker ? "IOLMaster printed an edited-value (*) marker; retained for visibility." : "";
      $("al").readOnly = Number.isFinite(bio.axial_length_mm); $("k1Axis").readOnly = Number.isFinite(bio.k1_axis_deg); $("k2Axis").readOnly = Number.isFinite(bio.k2_axis_deg);
    }
    if (pentacam) {
      setIfPresent("hoa", pentacam.total_corneal_hoa_4mm_um); setIfPresent("kappa", pentacam.angle_kappa_mm);
      setIfPresent("alpha", pentacam.angle_alpha_mm); setIfPresent("pupil3d", pentacam.pupil_dia_3d_mm);
      setIfPresent("cct", pentacam.cct_pachy_vertex_um); setIfPresent("wtw", pentacam.hwtw_mm);
      setIfPresent("acd", pentacam.acd_internal_mm);
      $("cct").readOnly = Number.isFinite(pentacam.cct_pachy_vertex_um); $("wtw").readOnly = Number.isFinite(pentacam.hwtw_mm);
      $("acd").readOnly = Number.isFinite(pentacam.acd_internal_mm);
    }
    const back = corneaBackByEye[eye];
    let missing = false;
    posteriorFields.forEach(key => {
      const otherAxis = key === "k1_axis_deg" ? "k2_axis_deg" : "k1_axis_deg";
      const unread = !Number.isFinite(back?.[key]) &&
        (!key.endsWith("axis_deg") || (!Number.isFinite(back?.[otherAxis]) && key === "k2_axis_deg"));
      $("back_field_"+key).hidden = !unread;
      $("back_"+key).value = Number.isFinite(back?.[key]) ? back[key] : "";
      missing ||= unread;
    });
    $("backCompletion").hidden = !back || !missing;
    updateAstigmatism();
  }

  $("incisionAxis").addEventListener("input", () => {
    incisionOverrides[$("eye").value] = numberOrNull("incisionAxis");
    $("siaAxis").value = $("incisionAxis").value;
    $("powerResult").replaceChildren();
  });
  root.querySelectorAll("[data-back-sign]").forEach(button => button.addEventListener("click", () => {
    const input = $(button.dataset.target);
    const magnitude = input.value.trim().replace(/^[+−–-]/, "");
    input.value = button.dataset.backSign + magnitude;
    input.dispatchEvent(new Event("input", {bubbles:true}));
  }));
  posteriorFields.forEach(key => $("back_"+key).addEventListener("input", () => $("powerResult").replaceChildren()));

  $("surface").addEventListener("change", () => { $("stableField").hidden = $("surface").value !== "RESOLVED_AFTER_TREATMENT"; });
  $("priorSurgery").addEventListener("change", () => { $("historyField").hidden = !["MYOPIC_LASIK_PRK","HYPEROPIC_LASIK_PRK"].includes($("priorSurgery").value); });
  $("k1").addEventListener("input", updateAstigmatism); $("k2").addEventListener("input", updateAstigmatism); $("k2Axis").addEventListener("input", updateAstigmatism);
  function populateLenses() {
    const eligible = new Set(recommendation.eligible_categories || []);
    const toric = recommendation.toric_evaluation_required;
    const options = lensCatalog.filter(lens => eligible.has(lens.category) && (!toric || lens.subtype?.toLowerCase().includes("toric")));
    $("selectedLens").innerHTML = `<option value="">Select an eligible lens</option>` + options.map(lens => `<option value="${lens.id}">${lens.name} — ${lens.category} — A ${lens.a_constant.toFixed(1)}</option>`).join("");
  }

  function escrsTransferPayload(data) {
    const inputs = data.inputs;
    return {
      biological_sex: inputs.biological_sex, eye: inputs.eye,
      axial_length_mm: inputs.axial_length_mm, acd_internal_mm: inputs.acd_internal_mm,
      k1_d: inputs.k1_d, k2_d: inputs.k2_d,
      cct_um: inputs.cct_um ?? null, lens_thickness_mm: inputs.lens_thickness_mm ?? null,
      wtw_mm: inputs.wtw_mm ?? null
    };
  }

  async function evaluate() {
    const requestVersion = version; const status = $("evaluationStatus"); status.className = "status";
    if (!loadedEyes.includes(eye)) { status.textContent = "The operative eye must come from a readable Pentacam Cataract Pre-Op report."; status.classList.add("error"); return; }
    if (!document.getElementById("patientForm").reportValidity() || !$("iolForm").reportValidity()) return false;
    const source = originals[eye];
    const originalK1 = source?.k1_d ?? Number($("k1").value); const originalK2 = source?.k2_d ?? Number($("k2").value);
    const payload = {
      patient_name: $("patientName").value, patient_age_years: Number($("patientAge").value), eye,
      near_demand: $("nearDemand").value, night_driving: $("nightDriving").value, halo_tolerance: $("haloTolerance").value,
      total_corneal_hoa_4mm_um: Number($("hoa").value), angle_kappa_mm: Number($("kappa").value), angle_alpha_mm: Number($("alpha").value), pentacam_pupil_3d_mm: Number($("pupil3d").value),
      iolm500_k1_d: originalK1, iolm500_k1_axis_deg: Number($("k1Axis").value), iolm500_k2_d: originalK2, iolm500_k2_axis_deg: Number($("k2Axis").value),
      iolm500_measurement_source: source ? "IOLMASTER_500_EXTRACTED" : "SURGEON_ENTERED_UNREADABLE",
      surgeon_k1_d: Number($("k1").value) === originalK1 ? null : Number($("k1").value), surgeon_k2_d: Number($("k2").value) === originalK2 ? null : Number($("k2").value),
      astigmatism_type: $("astigType").value || null, retina_status: $("retina").value, macular_pathology_present: $("macular").value === "true", glaucoma_status: $("glaucoma").value, ocular_surface_status: $("surface").value,
      post_treatment_measurements_stable: $("surface").value === "RESOLVED_AFTER_TREATMENT" ? $("stable").value === "true" : null
    };
    $("evaluateButton").disabled = true; status.textContent = "Applying canonical IOL rules…";
    try {
      const response = await fetch("/iol/evaluate", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
      const data = await response.json(); if (!response.ok) throw new Error(errorMessage(data)); if (requestVersion !== version) return false; recommendation = data;
      $("recommendation").textContent = tr(`Recommended IOL: ${data.formatted_recommendation}`);
      $("eligible").innerHTML = (data.eligible_categories || []).map(v => `<span class="pill">${tr(`Eligible: ${v}`)}</span>`).join("");
      $("warnings").innerHTML = (data.warning_codes || []).map(v => `<div class="warning">${tr(warningLabel(v))}</div>`).join("");
      $("reasons").replaceChildren(...(data.clinical_explanation || []).map(value => { const p=document.createElement("p"); p.className="reason"; p.textContent=tr(value); return p; }));
      $("legal").textContent = tr(data.legal_notice); $("result").hidden = false;
      if (!lensCatalog.length) { const lenses = await fetch("/iol/lenses", {credentials:"same-origin"}); const body = await lenses.json(); if (!lenses.ok) throw new Error(errorMessage(body)); lensCatalog = body.lenses || []; }
      if (requestVersion !== version) return false; populateLenses(); $("powerSection").hidden = false; updateAstigmatism(); status.textContent = "Recommendation generated. Select the lens for Stage 2."; return true;
    } catch (error) { if (requestVersion !== version) return false; status.textContent = error.message || "Recommendation could not be generated."; status.classList.add("error"); return false; }
    finally { $("evaluateButton").disabled = false; }
  }
  async function calculate() {
    const requestVersion = version;
    if (!recommendation) { $("powerStatus").textContent = tr("Evaluate this eye before calculating its lens power."); return false; }
    if (!document.getElementById("patientForm").reportValidity() || !$("iolForm").reportValidity()) return false;
    const status = $("powerStatus"); status.className="status"; const difference = kDifference();
    const al = numberOrNull("al");
    if (al !== null && al < 22 && (numberOrNull("lensThickness") === null || numberOrNull("wtw") === null)) {
      const missing = [];
      if (numberOrNull("lensThickness") === null) missing.push(tr("Lens thickness (mm)"));
      if (numberOrNull("wtw") === null) missing.push(tr("HWTW (mm)"));
      status.textContent = `${tr("Short eye (AL < 22.00 mm): Cooke K6 and the embedded toric calculation require")} ${missing.join(" + ")}. ${tr("Enter the missing measured value(s) before calculating.")}`;
      status.classList.add("error");
      const firstMissing = numberOrNull("lensThickness") === null ? $("lensThickness") : $("wtw");
      firstMissing.focus();
      return false;
    }
    const corneaBack = corneaBackByEye[$("eye").value];
    if (corneaBack) posteriorFields.forEach(key => {
      if (!$("back_field_"+key).hidden) {
        const value = $("back_"+key).value.trim().replace(/−|–/g, "-").replace(",", ".");
        corneaBack[key] = value && Number.isFinite(Number(value)) ? Number(value) : null;
      }
    });
    const posteriorInput = corneaBack && ["k1_d","k2_d"].every(key => Number.isFinite(corneaBack[key])) &&
      ["k1_axis_deg","k2_axis_deg"].some(key => Number.isFinite(corneaBack[key])) ? {
      eye:$("eye").value, source:"PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
      ...Object.fromEntries(posteriorFields.filter(key => Number.isFinite(corneaBack[key])).map(key => [key, corneaBack[key]]))
    } : null;
    const payload = {patient_name:$("patientName").value, biological_sex:$("biologicalSex").value, eye:$("eye").value, selected_lens_id:$("selectedLens").value,
      axial_length_mm:Number($("al").value), acd_mm:Number($("acd").value), k1_d:Number($("k1").value), k1_axis_deg:Number($("k1Axis").value), k2_d:Number($("k2").value), k2_axis_deg:Number($("k2Axis").value), astigmatism_type:$("astigType").value || null,
      prior_corneal_surgery:$("priorSurgery").value, historical_data_available:$("historicalData").value === "true", incision_axis_deg:difference>=1?numberOrNull("incisionAxis"):null, sia_d:difference>=1?numberOrNull("sia"):null, sia_axis_deg:difference>=1?numberOrNull("siaAxis"):null,
      cct_um:numberOrNull("cct"), lens_thickness_mm:numberOrNull("lensThickness"), wtw_mm:numberOrNull("wtw"), posterior_cornea:posteriorInput};
    if (!payload.selected_lens_id) { status.textContent="Select a clinic lens."; status.classList.add("error"); return; }
    $("powerButton").disabled=true; status.textContent="Determining the canonical calculation route…";
    try {
      const response=await fetch("/iol/power/plan",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); const data=await response.json(); if(!response.ok) throw new Error(errorMessage(data)); if (requestVersion !== version) return false;
      let html=`<div class="warning"><strong>${tr(data.calculator_name)}</strong><br>${tr(data.message)}</div>`;
      html+=`<p><span>ACD target</span>: ${Number(data.target_refraction_d).toFixed(2)} D (<span>locked</span>)</p>`;
      if(data.second_formula_required) html+=`<div class="warning"><span>Second modern formula verification required</span> (AL ${Number(data.inputs.axial_length_mm).toFixed(2)} mm). <span>Use ESCRS where available and verify all values manually.</span></div>`;
      if(data.escrs_url) html+=`<a class="external" target="_blank" rel="noopener noreferrer" href="${data.escrs_url}">Go to ESCRS Calculator</a><button id="${eye}-escrsTransfer" class="external" type="button">Transfer values to ESCRS</button>`;
      const toricRoute = data.route === "MANUFACTURER_TORIC";
      if(toricRoute && data.toric_candidates?.length) {
        const fmt = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
        const candidates = data.toric_candidates.filter(c => /^[A-Z0-9]+$/.test(c.model));
        html += `<div class="warning"><strong>TEST ONLY — unvalidated toric optical prototype.</strong> Independently check the source readings, model availability, implantation axis, and residual with the manufacturer's calculator before any clinical use.</div>`;
        html += `<h3>Embedded toric calculation — ${fmt(candidates[0]?.spherical_equivalent_iol_d)} D K6 spherical equivalent</h3>`;
        html += `<div class="recommendation">${candidates[0]?.model ?? "—"} · ${fmt(candidates[0]?.marker_axis_deg, 1)}° marker axis</div>`;
        html += `<p>Predicted residual cylinder: ${fmt(candidates[0]?.residual_spectacle_cylinder_d)} D at ${fmt(candidates[0]?.residual_spectacle_axis_deg, 1)}° (prototype estimate).</p>`;
        html += `<div style="overflow-x:auto"><table class="table"><thead><tr><th>Model</th><th>IOL cylinder</th><th>Marker axis</th><th>Predicted residual cylinder</th></tr></thead><tbody>${candidates.map(c => `<tr><td>${c.model}</td><td>${fmt(c.cylinder_iol_d)} D</td><td>${fmt(c.marker_axis_deg, 1)}°</td><td>${fmt(c.residual_spectacle_cylinder_d)} D at ${fmt(c.residual_spectacle_axis_deg, 1)}°</td></tr>`).join("")}</tbody></table></div>`;
      } else if(toricRoute) html += `<div class="warning"><strong>No embedded toric model or axis available.</strong> ${data.toric_status === "INPUTS_INCOMPLETE" ? "Upload the same-eye Pentacam 4 Maps Refractive image and verify Pachy Vertex." : "Review source measurements and the selected lens family."}</div>`;
      if(data.predictions?.length){html+=`<h3>${toricRoute?"Stage 1 — Cooke K6 spherical power":"Cooke K6 power"}</h3><table class="table"><thead><tr><th>IOL power</th><th>Predicted refraction</th><th>Selection</th></tr></thead><tbody>${data.predictions.map(p=>`<tr><td>${Number(p.IOL ?? p.iol_power).toFixed(2)}</td><td>${Number(p.Rx ?? p.predicted_refraction).toFixed(2)}</td><td>${p.IsBestOption ? "K6 best option" : ""}</td></tr>`).join("")}</tbody></table>`;}
      if(data.calculator_url) html+=`<a class="external" target="_blank" rel="noopener noreferrer" href="${data.calculator_url}">Optional manufacturer toric calculator comparison</a>`;
      $("powerResult").innerHTML=html; status.textContent=tr(data.calculation_status.replaceAll("_"," "));
      if(data.escrs_url) root.querySelector(`#${eye}-escrsTransfer`).addEventListener("click", async () => {
        const button = root.querySelector(`#${eye}-escrsTransfer`);
        const escrsWindow = window.open("about:blank", "_blank");
        if (escrsWindow) escrsWindow.opener = null;
        button.disabled = true; status.className = "status";
        status.textContent = "Creating a secure, de-identified ESCRS transfer…";
        try {
          const response = await fetch("/iol/escrs-transfer", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(escrsTransferPayload(data))});
          const transfer = await response.json(); if(!response.ok) throw new Error(errorMessage(transfer));
          if (escrsWindow) escrsWindow.location.replace(transfer.escrs_url);
          else window.location.assign(transfer.escrs_url);
          status.textContent = "Biometry transferred to ESCRS. Verify every imported value before calculation.";
        } catch(error) {
          if (escrsWindow) escrsWindow.close();
          status.textContent = error.message || "ESCRS transfer could not be completed."; status.classList.add("error");
        } finally { button.disabled = false; }
      });
      return true;
    } catch(error){if(requestVersion !== version) return false; status.textContent=error.message||"Power route could not be completed.";status.classList.add("error");return false;}
    finally{$("powerButton").disabled=false;}
  }

    function invalidate(category = true) {
      version++;
      $("powerResult").replaceChildren();
      $("powerStatus").textContent = "";
      if (category) {
        recommendation = null;
        $("result").hidden = true;
        $("powerSection").hidden = true;
        $("evaluationStatus").textContent = "";
      }
    }
    root.addEventListener("input", event => invalidate(!$("powerSection").contains(event.target) && !$("backCompletion").contains(event.target)));
    root.addEventListener("change", event => invalidate(!$("powerSection").contains(event.target) && !$("backCompletion").contains(event.target)));
    $("iolForm").addEventListener("submit", event => { event.preventDefault(); evaluate(); });
    $("powerButton").addEventListener("click", calculate);
    return {
      evaluate, calculate, invalidate,
      reset() {
        invalidate();
        root.hidden = true;
        $("iolForm").reset();
        root.querySelectorAll("input").forEach(node => { node.readOnly = false; });
        $("eye").value = eye;
        ["kDifference", "sia", "siaAxis"].forEach(id => { $(id).readOnly = true; });
        $("selectedLens").replaceChildren();
        $("priorSurgery").value = "NONE"; $("historicalData").value = "false";
        $("stableField").hidden = true; $("historyField").hidden = true;
        $("backCompletion").hidden = true;
        $("alMarker").textContent = "";
      },
      populate() { root.hidden = false; populateEye(); }
    };
  }

  function clearSourceCase() {
    caseVersion++;
    loadedEyes = [];
    for (const eye of ["OD", "OS"]) {
      originals[eye] = null; pentacamByEye[eye] = null; corneaBackByEye[eye] = null; incisionOverrides[eye] = null;
      controllers.get(eye)?.reset();
    }
    $("evaluateAll").disabled = true; $("calculateAll").disabled = true;
    $("bothStatus").textContent = "";
  }
  ["OD", "OS"].forEach(eye => controllers.set(eye, createEyeController(eye)));
  $("patientForm").addEventListener("submit", event => event.preventDefault());
  $("patientForm").addEventListener("input", event => {
    if (event.target.id !== "sourceImages") controllers.forEach(controller => controller.invalidate());
  });
  $("patientForm").addEventListener("change", event => {
    if (event.target.id !== "sourceImages") controllers.forEach(controller => controller.invalidate());
  });
  $("sourceImages").addEventListener("change", () => {
    iolAssessmentRequestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    clearSourceCase();
    const files = [...$("sourceImages").files];
    $("selectedFiles").textContent = files.length ? `Selected images (${files.length}): ${files.map(file => file.name).join(", ")}` : "";
    $("extractStatus").textContent = "";
  });
  $("extractButton").addEventListener("click", async () => {
    const files = [...$("sourceImages").files];
    const status = $("extractStatus"); status.className = "status";
    const surgeonPatientName = $("patientName").value.trim();
    if (!surgeonPatientName) { status.textContent = tr("Enter the patient name before extracting source images."); return; }
    if (files.length !== 3 && files.length !== 5) { status.textContent = tr("Upload 3 images for one eye or 5 for both eyes: Cataract Pre-Op and 4 Maps Refractive for each eye, plus one shared IOLMaster 500 report."); return; }
    const form = new FormData(); files.forEach(file => form.append("images", file)); form.append("patient_name", surgeonPatientName); form.append("assessment_request_id", iolAssessmentRequestId);
    clearSourceCase();
    $("extractButton").disabled = true; $("sourceImages").disabled = true; $("patientName").readOnly = true;
    status.textContent = tr("Transcribing source-locked fields…");
    try {
      const response = await fetch("/iol/extract", {method:"POST", body:form, credentials:"same-origin"});
      const data = await response.json(); if (!response.ok) throw new Error(errorMessage(data));
      const eyes = data.identity?.eye === "BOTH" ? data.identity.eyes : [data.identity?.eye];
      if (!data.identity?.patient_name || !eyes?.length || eyes.some(eye => !["OD","OS"].includes(eye))) throw new Error("Source identity verification failed. Check the source reports.");
      const unreadable = [];
      for (const source of data.sources || []) {
        const item = source.extraction || {};
        if ($("patientAge").value === "" && Number.isFinite(item.patient_age_years)) $("patientAge").value = item.patient_age_years;
        if (item.document_type === "PENTACAM_CATARACT_PREOP" && eyes.includes(item.eye)) pentacamByEye[item.eye] = item.pentacam || {};
        if (item.document_type === "PENTACAM_4_MAPS_REFRACTIVE" && eyes.includes(item.eye)) corneaBackByEye[item.eye] = item.cornea_back || {};
        if (item.document_type === "IOLMASTER_500_BIOMETRY") eyes.forEach(eye => { originals[eye] = item.iolmaster500?.[eye] || null; });
        (item.unreadable_fields || []).forEach(field => unreadable.push(`${source.filename}: ${field}`));
      }
      if (eyes.some(eye => !pentacamByEye[eye] || !corneaBackByEye[eye] || !originals[eye])) throw new Error("Source identity verification failed. Check the source reports.");
      $("patientName").value = surgeonPatientName;
      loadedEyes = ["OD","OS"].filter(eye => eyes.includes(eye));
      loadedEyes.forEach(eye => controllers.get(eye).populate());
      $("evaluateAll").disabled = false; $("calculateAll").disabled = false;
      const nameReview = data.identity.source_name_review_required ? tr(" The surgeon-entered patient name was retained. Check the patient names printed on the source reports.") : "";
      status.textContent = tr("Reports extracted. Review each eye separately before evaluation.") + nameReview + (unreadable.length ? " " + unreadable.join(", ") : "");
    } catch (error) { clearSourceCase(); status.textContent = error.message || tr("Image transcription failed."); status.classList.add("error"); }
    finally { $("extractButton").disabled = false; $("sourceImages").disabled = false; $("patientName").readOnly = false; }
  });
  async function runLoadedEyes(method) {
    const requestCaseVersion = caseVersion;
    if (!loadedEyes.length || !$("patientForm").reportValidity()) return;
    $("evaluateAll").disabled = true; $("calculateAll").disabled = true;
    $("bothStatus").textContent = tr("Processing loaded eyes…");
    try {
      const results = await Promise.allSettled(loadedEyes.map(eye => controllers.get(eye)[method]()));
      if (requestCaseVersion !== caseVersion) return;
      $("bothStatus").textContent = tr(results.every(result => result.status === "fulfilled" && result.value === true)
        ? "Completed. Review the separate OD and OS results below."
        : "Review each eye's status and complete any missing fields.");
    } finally { if (requestCaseVersion === caseVersion) { $("evaluateAll").disabled = !loadedEyes.length; $("calculateAll").disabled = !loadedEyes.length; } }
  }
  $("evaluateAll").addEventListener("click", () => runLoadedEyes("evaluate"));
  $("calculateAll").addEventListener("click", () => runLoadedEyes("calculate"));
})();
