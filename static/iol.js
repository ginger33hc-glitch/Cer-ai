(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const astigmatismThreshold = Number(document.querySelector("[data-astigmatism-threshold]").dataset.astigmatismThreshold);
  if (!Number.isFinite(astigmatismThreshold) || astigmatismThreshold <= 0) {
    $("extractButton").disabled = true;
    $("extractStatus").textContent = window.CERAI_I18N?.translate("Page configuration could not be loaded. Please reload the page.") || "Page configuration could not be loaded. Please reload the page.";
    return;
  }
  const requiresRegularity = difference => difference > astigmatismThreshold;
  const originals = {OD:null, OS:null};
  const pentacamByEye = {OD:null, OS:null};
  const corneaBackByEye = {OD:null, OS:null};
  const incisionOverrides = {OD:null, OS:null};
  const posteriorFields = ["k1_d","k2_d","k1_axis_deg","k2_axis_deg"];
  const controllers = new Map();
  const powerPlans = {OD:null, OS:null};
  let loadedEyes = [];
  let caseVersion = 0;
  let workflowBusy = false;
  function incompleteFields(form) {
    return [...form.elements].filter(field => field.willValidate && !field.validity.valid);
  }
  function revealRequiredField(field) {
    for (let parent = field.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === "DETAILS") parent.open = true;
    }
    field.classList.add("field-attention");
    field.scrollIntoView({block:"center", behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"});
    field.focus({preventScroll:true});
  }
  function updateWorkflowRequirements(eyes) {
    const panel = $("workflowRequirements");
    const fields = eyes.length ? [
      ...incompleteFields($("patientForm")).map(field => ({field, eye:null})),
      ...loadedEyes.flatMap(eye => controllers.get(eye).incompleteFields().map(field => ({field, eye})))
    ] : [];
    panel.hidden = !fields.length;
    const list = $("workflowRequirementList");
    list.replaceChildren();
    fields.forEach(({field, eye}) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button"; button.className = "requirement-link";
      const label = tr(field.labels?.[0]?.textContent || "Required information is incomplete or invalid.");
      button.textContent = `${eye ? eye + " — " : ""}${label}`;
      button.addEventListener("click", () => revealRequiredField(field));
      item.appendChild(button); list.appendChild(item);
    });
  }
  function escrsTransferPayload() {
    if (!loadedEyes.length) throw new Error("Read the source images before transferring to ESCRS.");
    const measurements = Object.fromEntries(loadedEyes.map(eye => [eye, controllers.get(eye).transferMeasurements()]));
    return {
      biological_sex: $("biologicalSex").value,
      right_eye: measurements.OD || null,
      left_eye: measurements.OS || null
    };
  }

  function posteriorAxesConflict(back) {
    return Number.isFinite(back?.k1_axis_deg) && Number.isFinite(back?.k2_axis_deg) &&
      (back.k1_axis_deg < 0 || back.k1_axis_deg > 180 || back.k2_axis_deg < 0 || back.k2_axis_deg > 180 ||
       Math.abs(((back.k2_axis_deg - back.k1_axis_deg + 180) % 180) - 90) > 5);
  }

  function syncWorkflow() {
    const eyes = loadedEyes.map(eye => controllers.get(eye));
    $("reviewStage").hidden = !eyes.length;
    $("recommendAll").disabled = workflowBusy || !eyes.length || !eyes.every(controller => controller.readyToRecommend());
    const recommended = eyes.length && eyes.every(controller => controller.recommendationShown());
    $("calculationActions").hidden = !recommended;
    $("calculateAll").disabled = workflowBusy || !recommended;
    $("escrsTransferAll").hidden = !loadedEyes.length;
    $("escrsTransferAll").disabled = workflowBusy;
    $("extractButton").disabled = workflowBusy;
    $("sourceImages").disabled = workflowBusy;
    updateWorkflowRequirements(eyes);
    window.CERAI_IOL_REPORT?.setCase(!workflowBusy && loadedEyes.length && loadedEyes.every(eye => powerPlans[eye]) ? {
      assessment_request_id: iolAssessmentRequestId,
      patient_name: $("patientName").value.trim(), patient_age_years: Number($("patientAge").value),
      eyes: loadedEyes.map(eye => controllers.get(eye).reportSnapshot())
    } : null);
  }
  let lensCatalog = [];
  let iolAssessmentRequestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  const tr = value => window.CERAI_I18N?.translate(value) ?? String(value ?? "");
  const warningLabel = code => ({
    WARN_OCULAR_FINDINGS_NOT_ASSESSED:"Ocular pathology was not assessed by CER-AI; left to surgeon assessment. Lens categories reflect optical measurements and preferences only, not clinical suitability.",
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
    WARN_PUPIL_SMALL_SURGEON_REVIEW:"Pupil below 2.00 mm: surgeon review required; multifocal is not automatically excluded.",
    WARN_PUPIL_LARGE_SURGEON_REVIEW:"Pupil above 4.00 mm: surgeon review required; multifocal is not automatically excluded.",
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
    let recommendationShown = false;
    let version = 0;
    let regularityAttentionPending = false;
    $("eye").value = eye;
    $("eyeHeading").textContent = tr(eye === "OD" ? "OD — Right eye" : "OS — Left eye");
    root.hidden = true;
    document.getElementById("eyePanels").appendChild(fragment);
    const recommendationRoot = document.createElement("section");
    recommendationRoot.hidden = true;
    const recommendationHeading = $("eyeHeading").cloneNode(true);
    recommendationHeading.removeAttribute("id");
    recommendationRoot.append(recommendationHeading, $("result"), $("powerSection"));
    let assessmentPayload = null;
    const pupilReview = document.createElement("div");
    pupilReview.className = "warning"; pupilReview.hidden = true;
    const pupilChoice = document.createElement("select");
    pupilChoice.id = eye + "-pupilMultifocalChoice";
    const pupilLabel = document.createElement("label");
    pupilLabel.htmlFor = pupilChoice.id;
    pupilLabel.textContent = tr("Pupil diameter is outside the 2–4 mm target. Visual performance may be affected. Do you still want a multifocal lens?");
    for (const [value, label] of [["", "Select surgeon decision"], ["yes", "Yes — allow multifocal selection"], ["no", "No — continue with other eligible lenses"]]) {
      const option = document.createElement("option"); option.value = value; option.textContent = tr(label); pupilChoice.appendChild(option);
    }
    pupilReview.append(pupilLabel, pupilChoice);
    $("powerSection").prepend(pupilReview);
    const pupilReviewRequired = () => Boolean(recommendation?.eligible_categories?.includes("MULTIFOCAL") &&
      recommendation.warning_codes?.some(code => ["WARN_PUPIL_SMALL_SURGEON_REVIEW", "WARN_PUPIL_LARGE_SURGEON_REVIEW"].includes(code)));
    pupilChoice.addEventListener("change", () => { invalidate(false); populateLenses(); });
    document.getElementById("recommendationPanels").appendChild(recommendationRoot);
    const calculationRoot = document.createElement("section");
    calculationRoot.hidden = true;
    const calculationHeading = recommendationHeading.cloneNode(true);
    const retryPowerButton = document.createElement("button");
    retryPowerButton.type = "button"; retryPowerButton.hidden = true;
    retryPowerButton.textContent = tr("Recalculate");
    retryPowerButton.addEventListener("click", async () => {
      if (workflowBusy) return;
      workflowBusy = true; syncWorkflow(); retryPowerButton.disabled = true;
      try { await calculate(); }
      finally { workflowBusy = false; syncWorkflow(); retryPowerButton.disabled = false; }
    });
    calculationRoot.append(calculationHeading, $("lensThicknessField"), retryPowerButton, $("powerStatus"), $("powerResult"));
    document.getElementById("calculationPanels").appendChild(calculationRoot);
    const notesRoot = document.createElement("section");
    notesRoot.hidden = true;
    const notesHeading = recommendationHeading.cloneNode(true);
    const notesContent = document.createElement("div");
    notesRoot.append(notesHeading, notesContent);
    document.getElementById("calculationNotePanels").appendChild(notesRoot);
    function showCalculationNotes(html = "") {
      notesContent.innerHTML = html;
      notesRoot.hidden = !html;
      document.getElementById("calculationNotes").hidden =
        ![...document.getElementById("calculationNotePanels").children].some(panel => !panel.hidden);
    }

    // Posterior completion precedes lens selection and calculation.
    $("iolForm").appendChild($("backCompletion"));
  const kDifference = () => $("k1").value === "" || $("k2").value === "" ? NaN : Math.abs(Number($("k2").value) - Number($("k1").value));

  function updateAstigmatism() {
    const difference = kDifference();
    $("kDifference").value = Number.isFinite(difference) ? `${difference.toFixed(2)} D` : "";
    const required = requiresRegularity(difference);
    const becameRequired = required && !$("astigType").required;
    $("astigTypeField").hidden = !required;
    $("incisionAdvice").hidden = !Number.isFinite(difference) || required;
    if (!required && $("astigType").value !== "IRREGULAR") $("astigType").value = "";
    $("astigType").required = required;
    const unresolved = required && !$("astigType").value;
    if (becameRequired && unresolved) regularityAttentionPending = true;
    if (!unresolved) regularityAttentionPending = false;
    $("astigTypeField").classList.toggle("required-attention", unresolved);
    $("astigType").setAttribute("aria-invalid", String(unresolved));
    $("astigType").setAttribute("aria-describedby", $("astigTypeHelp").id);
    $("astigTypeHelp").hidden = !unresolved;
    $("astigTypeHelp").textContent = unresolved ? tr("K difference: {difference} D (> {threshold} D). Select regular or irregular astigmatism to continue.")
      .replace("{difference}", difference.toFixed(2)).replace("{threshold}", astigmatismThreshold.toFixed(2)) : "";
    if (!unresolved) $("astigType").classList.remove("field-attention");
    $("incisionField").hidden = !required;
    $("siaField").hidden = !required;
    $("siaAxisField").hidden = !required;
    $("incisionAxis").required = required;
    $("sia").required = required;
    if (required) {
      $("incisionAxis").value = incisionOverrides[$("eye").value] ?? 180;
      $("siaAxis").value = $("incisionAxis").value;
      $("sia").value = "0.25";
    }
  }
  function focusMissingRegularity() {
    if (!$("astigType").required || $("astigType").value) return false;
    regularityAttentionPending = false;
    revealRequiredField($("astigType"));
    return true;
  }

  function populateEye() {
    const eye = $("eye").value;
    const bio = originals[eye];
    const pentacam = pentacamByEye[eye];
    $("acd").value = Number.isFinite(bio?.acd_mm) ? bio.acd_mm : "";
    $("acd").readOnly = Number.isFinite(bio?.acd_mm);
    if (bio) {
      setIfPresent("al", bio.axial_length_mm); setIfPresent("k1", bio.k1_d);
      setIfPresent("k1Axis", bio.k1_axis_deg); setIfPresent("k2", bio.k2_d);
      setIfPresent("k2Axis", bio.k2_axis_deg); setIfPresent("lensThickness", bio.lens_thickness_mm);
      $("alMarker").textContent = bio.axial_length_edited_marker ? "IOLMaster printed an edited-value (*) marker; retained for visibility." : "";
      $("al").readOnly = Number.isFinite(bio.axial_length_mm); $("k1Axis").readOnly = Number.isFinite(bio.k1_axis_deg); $("k2Axis").readOnly = Number.isFinite(bio.k2_axis_deg);
    }
    if (pentacam) {
      setIfPresent("hoa", pentacam.total_corneal_hoa_4mm_um); setIfPresent("kappa", pentacam.angle_kappa_mm);
      setIfPresent("alpha", pentacam.angle_alpha_mm); setIfPresent("pupil3d", pentacam.pupil_dia_3d_mm);
      setIfPresent("cct", pentacam.cct_pachy_vertex_um); setIfPresent("wtw", pentacam.hwtw_mm);
      $("cct").readOnly = Number.isFinite(pentacam.cct_pachy_vertex_um); $("wtw").readOnly = Number.isFinite(pentacam.hwtw_mm);
    }
    const back = corneaBackByEye[eye];
    const conflict = posteriorAxesConflict(back);
    let missing = false;
    posteriorFields.forEach(key => {
      const otherAxis = key === "k1_axis_deg" ? "k2_axis_deg" : "k1_axis_deg";
      const unread = !Number.isFinite(back?.[key]) &&
        (!key.endsWith("axis_deg") || (!Number.isFinite(back?.[otherAxis]) && key === "k2_axis_deg"));
      $("back_field_"+key).hidden = !(unread || conflict);
      $("back_"+key).value = Number.isFinite(back?.[key]) ? back[key] : "";
      missing ||= unread;
    });
    $("backCompletion").hidden = !back || !(missing || conflict);
    $("backReviewStatus").textContent = conflict ? tr("Cornea Back K axes must be approximately orthogonal.") : "";
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

  $("priorSurgery").addEventListener("change", () => {
    $("historyField").hidden = !["MYOPIC_LASIK_PRK","HYPEROPIC_LASIK_PRK"].includes($("priorSurgery").value);
    $("priorSurgerySummary").textContent = tr("Previous corneal surgery (LASIK/PRK/RK)") + ($("priorSurgery").value === "NONE" ? "" : ` — ${$("priorSurgery").selectedOptions[0].textContent}`);
  });
  $("k1").addEventListener("input", updateAstigmatism); $("k2").addEventListener("input", updateAstigmatism); $("k2Axis").addEventListener("input", updateAstigmatism);
  ["k1", "k2"].forEach(id => $(id).addEventListener("change", () => {
    if (regularityAttentionPending) focusMissingRegularity();
  }));
  $("astigType").addEventListener("change", updateAstigmatism);
  function populateLenses() {
    const eligible = new Set(recommendation.eligible_categories || []);
    pupilReview.hidden = !pupilReviewRequired();
    if (pupilReviewRequired() && pupilChoice.value !== "yes") eligible.delete("MULTIFOCAL");
    const toric = recommendation.toric_evaluation_required;
    const options = lensCatalog.filter(lens => eligible.has(lens.category) && (toric ? lens.subtype?.toLowerCase().includes("toric") : !lens.subtype?.toLowerCase().includes("toric")));
    const lensPrompt = recommendation.recommendation_scope === "OPTICAL_ONLY" ? "Select an optical candidate for surgeon review" : "Select an eligible lens";
    $("selectedLens").innerHTML = `<option value="">${tr(lensPrompt)}</option>` + options.map(lens => {
      const route = toric ? (lens.embedded_toric_supported ? " — embedded prototype (TEST ONLY)" : " — external toric verification required") : "";
      return `<option value="${lens.id}">${lens.name} — ${lens.category} — A ${lens.a_constant.toFixed(1)}${route}</option>`;
    }).join("");
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
      astigmatism_type: $("astigType").value || null, ocular_findings_assessment: "NOT_ASSESSED",
      retina_status: null, macular_pathology_present: null, glaucoma_status: null, ocular_surface_status: null,
      post_treatment_measurements_stable: null
    };
    $("evaluateButton").disabled = true; status.textContent = "Applying canonical IOL rules…";
    try {
      const response = await fetch("/iol/evaluate", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
      const data = await response.json(); if (!response.ok) throw new Error(errorMessage(data)); if (requestVersion !== version) return false; recommendation = data;
      assessmentPayload = payload;
      pupilChoice.value = "";
      $("warnings").innerHTML = (data.warning_codes || []).filter(v => v !== "WARN_OCULAR_FINDINGS_NOT_ASSESSED").map(v => `<div class="warning">${tr(warningLabel(v))}</div>`).join("");
      $("reasons").replaceChildren(...(data.clinical_explanation || []).filter(v => !v.startsWith("Ocular pathology was not assessed by CER-AI;")).map(value => { const p=document.createElement("p"); p.className="reason"; p.textContent=tr(value); return p; }));
      $("legal").textContent = tr(data.legal_notice); $("result").hidden = false; $("recommendation").textContent = ""; $("eligible").replaceChildren();
      status.textContent = tr("Images evaluated. Continue to lens recommendation."); return true;
    } catch (error) { if (requestVersion !== version) return false; status.textContent = error.message || "Recommendation could not be generated."; status.classList.add("error"); return false; }
    finally { $("evaluateButton").disabled = false; }
  }
  async function recommend() {
    invalidate(false);
    const requestVersion = version;
    const status = $("evaluationStatus");
    if (!recommendation) return false;
    const data = recommendation;
    try {
      const opticalOnly = data.recommendation_scope === "OPTICAL_ONLY";
      $("recommendation").textContent = opticalOnly
        ? `${tr("Optical IOL candidate — surgeon assessment required")}: ${tr(data.formatted_recommendation)}`
        : tr(`Recommended IOL: ${data.formatted_recommendation}`);
      $("eligible").innerHTML = (data.eligible_categories || []).map(v => `<span class="pill">${opticalOnly ? `${tr("Optical candidate")}: ${tr(v)}` : tr(`Eligible: ${v}`)}</span>`).join("");
      if (!lensCatalog.length) { const lenses = await fetch("/iol/lenses", {credentials:"same-origin"}); const body = await lenses.json(); if (!lenses.ok) throw new Error(errorMessage(body)); lensCatalog = body.lenses || []; }
      if (requestVersion !== version) return false; recommendationShown = true; recommendationRoot.hidden = false; populateLenses(); $("powerSection").hidden = false; updateAstigmatism(); status.textContent = "Recommendation generated. Select the lens for Stage 2."; return true;
    } catch (error) {
      if (requestVersion !== version) return false;
      status.textContent = error.message || tr("Recommendation could not be generated.");
      status.classList.add("error"); return false;
    }
  }
  async function calculate() {
    const requestVersion = version;
    powerPlans[eye] = null;
    syncWorkflow();
    calculationRoot.hidden = false;
    $("powerResult").replaceChildren();
    showCalculationNotes();
    const missingLens = !$("selectedLens").value;
    if (missingLens) {
      $("powerStatus").textContent = `${eye}: ${tr("Select a clinic lens.")}`;
      $("powerStatus").className = "status error";
      $("selectedLens").reportValidity();
      return false;
    }
    if (!recommendation || !recommendationShown) { $("powerStatus").textContent = tr("Evaluate this eye before calculating its lens power."); return false; }
    if (pupilReviewRequired() && !pupilChoice.value) {
      $("powerStatus").textContent = tr("Select surgeon decision"); pupilChoice.focus(); return false;
    }
    if (!document.getElementById("patientForm").reportValidity() || !$("iolForm").reportValidity()) return false;
    const status = $("powerStatus"); status.className="status"; const difference = kDifference();
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
      prior_corneal_surgery:$("priorSurgery").value, historical_data_available:$("historicalData").value === "true", incision_axis_deg:requiresRegularity(difference)?numberOrNull("incisionAxis"):null, sia_d:requiresRegularity(difference)?numberOrNull("sia"):null, sia_axis_deg:requiresRegularity(difference)?numberOrNull("siaAxis"):null,
      cct_um:numberOrNull("cct"), lens_thickness_mm:numberOrNull("lensThickness"), wtw_mm:numberOrNull("wtw"), posterior_cornea:posteriorInput,
      clinical_assessment:assessmentPayload, pupil_multifocal_confirmed:pupilReviewRequired() && pupilChoice.value === "yes"};
    if (!payload.selected_lens_id) { status.textContent="Select a clinic lens."; status.classList.add("error"); return; }
    $("powerButton").disabled=true; status.textContent="Determining the canonical calculation route…";
    try {
      const response=await fetch("/iol/power/plan",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); const data=await response.json(); if (requestVersion !== version) return false;
      if (!response.ok) {
        if (Array.isArray(data.detail) && data.detail.some(error => error.loc?.includes("posterior_cornea"))) {
          $("backCompletion").hidden = false;
          posteriorFields.forEach(key => {$("back_field_"+key).hidden = false;});
          $("backReviewStatus").textContent = errorMessage(data);
          $("backCompletion").scrollIntoView({block:"center"});
        }
        throw new Error(errorMessage(data));
      }
      powerPlans[eye] = data;
      $("backReviewStatus").textContent = "";
      const formula = data.spherical_formula === "T2" ? "T2" : "Cooke K6";
      let notes=`<div class="warning"><strong>${tr(data.calculator_name)}</strong><br>${tr(data.predictions?.length ? `${formula} calculation completed.` : data.message)}</div>`;
      let html = data.predictions?.length ? "" : `<div class="warning">${tr(data.message)}</div>`;
      if (data.fallback_reason) notes += `<div class="warning">${tr("Cooke K6 unavailable. Calculated locally with T2. You may transfer values to ESCRS for comparison.")}</div>`;
      $("lensThicknessField").hidden = !data.required_inputs?.includes("lens_thickness_mm");
      retryPowerButton.hidden = $("lensThicknessField").hidden;
      if (data.required_inputs?.includes("lens_thickness_mm")) {
        html += `<div class="warning">${tr("Cooke K6 requires measured lens thickness for this calculation. Enter LT or continue at ESCRS if unavailable.")}</div>`;
        $("lensThickness").focus();
      }
      html+=`<p><span>Target refraction</span>: ${Number(data.target_refraction_d).toFixed(2)} D (<span>locked</span>)</p>`;
      if(data.second_formula_required) notes+=`<div class="warning"><span>Second modern formula verification required</span> (AL ${Number(data.inputs.axial_length_mm).toFixed(2)} mm). <span>Use ESCRS where available and verify all values manually.</span></div>`;
      const toricRoute = data.route === "MANUFACTURER_TORIC";
      if(toricRoute && data.predictions?.length) notes += `<div class="warning">${tr(data.message)}</div>`;
      if(toricRoute && data.toric_candidates?.length) {
        const fmt = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
        const candidates = data.toric_candidates.filter(c => /^[A-Z0-9 .\/-]+$/.test(c.model));
        const reference = lensCatalog.find(lens => lens.id === data.selected_lens_id)?.manufacturer_reference;
        if (reference?.note) {
          const note = tr(reference.note).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
          notes += `<p>${note}</p>`;
        }
        notes += `<div class="warning"><strong>TEST ONLY — unvalidated toric optical prototype.</strong> Independently check the source readings, model availability, implantation axis, and residual with the manufacturer's calculator before any clinical use.</div>`;
        html += `<h3>Embedded toric calculation — ${fmt(candidates[0]?.spherical_equivalent_iol_d)} D ${formula} <span>spherical equivalent</span></h3>`;
        html += `<div class="recommendation">${fmt(candidates[0]?.spherical_equivalent_iol_d)} D · ${candidates[0]?.model ?? "—"} · ${fmt(candidates[0]?.marker_axis_deg, 1)}° marker axis</div>`;
        html += `<p>Predicted residual cylinder: ${fmt(candidates[0]?.residual_spectacle_cylinder_d)} D at ${fmt(candidates[0]?.residual_spectacle_axis_deg, 1)}° (prototype estimate).</p>`;
        html += `<div style="overflow-x:auto"><table class="table"><thead><tr><th>Model</th><th>IOL cylinder</th><th>Marker axis</th><th>Predicted residual cylinder</th></tr></thead><tbody>${candidates.map(c => `<tr><td>${c.model}</td><td>${fmt(c.cylinder_iol_d)} D</td><td>${fmt(c.marker_axis_deg, 1)}°</td><td>${fmt(c.residual_spectacle_cylinder_d)} D at ${fmt(c.residual_spectacle_axis_deg, 1)}°</td></tr>`).join("")}</tbody></table></div>`;
      } else if(toricRoute) html += `<div class="warning"><strong>No embedded toric model or axis available.</strong> ${data.toric_status === "INPUTS_INCOMPLETE" ? "Upload the same-eye Pentacam 4 Maps Refractive image and verify Pachy Vertex." : (data.toric_status === "UNSUPPORTED" ? "No validated embedded model series for this lens. Use the manufacturer calculator and ESCRS for independent verification." : "Review source measurements and the selected lens family.")}</div>`;
      if(data.predictions?.length){html+=`<h3>${tr(toricRoute ? `Stage 1 — ${formula} spherical power` : `${formula} power`)}</h3><table class="table"><thead><tr><th>IOL power</th><th>Predicted refraction</th><th>Selection</th></tr></thead><tbody>${data.predictions.map(p=>`<tr><td>${Number(p.IOL ?? p.iol_power).toFixed(2)}</td><td>${Number(p.Rx ?? p.predicted_refraction).toFixed(2)}</td><td>${p.IsBestOption ? tr("Closest to target") : ""}</td></tr>`).join("")}</tbody></table>`;}
      if(data.calculator_url) html+=`<a class="external" target="_blank" rel="noopener noreferrer" href="${data.calculator_url}">Optional manufacturer toric calculator comparison</a>`;
      $("powerResult").innerHTML=html; showCalculationNotes(notes); status.textContent=tr(data.calculation_status.replaceAll("_"," "));
      return true;
    } catch(error){if(requestVersion !== version) return false; status.textContent=error.message||"Power route could not be completed.";status.classList.add("error");return false;}
    finally{$("powerButton").disabled=false; syncWorkflow();}
  }

    function invalidate(category = true) {
      version++;
      powerPlans[eye] = null;
      if ($("lensThicknessField").hidden) calculationRoot.hidden = true;
      $("powerResult").replaceChildren();
      showCalculationNotes();
      $("powerStatus").textContent = "";
      if (category) {
        assessmentPayload = null; pupilChoice.value = ""; pupilReview.hidden = true;
        calculationRoot.hidden = true; retryPowerButton.hidden = true; $("lensThicknessField").hidden = true;
        recommendation = null;
        recommendationShown = false;
        recommendationRoot.hidden = true;
        $("result").hidden = true;
        $("powerSection").hidden = true;
        $("evaluationStatus").textContent = "";
      }
      syncWorkflow();
    }
    const invalidateFromEvent = event => {
      if (event.target.validity?.valid) event.target.classList.remove("field-attention");
      invalidate(!$("powerSection").contains(event.target) && !$("backCompletion").contains(event.target) && !$("lensThicknessField").contains(event.target));
    };
    [root, recommendationRoot, calculationRoot].forEach(panel => {
      panel.addEventListener("input", invalidateFromEvent);
      panel.addEventListener("change", invalidateFromEvent);
    });
    $("iolForm").addEventListener("submit", event => { event.preventDefault(); runLoadedEyes("recommend"); });
    $("powerButton").addEventListener("click", calculate);
    return {
      evaluate, recommend, calculate, invalidate,
      evaluated: () => recommendation !== null,
      recommendationShown: () => recommendationShown,
      readyToRecommend: () => $("iolForm").checkValidity(),
      incompleteFields: () => incompleteFields($("iolForm")),
      focusMissingRegularity,
      readyToCalculate: () => recommendationShown && Boolean($("selectedLens").value),
      transferMeasurements: () => ({
        axial_length_mm:numberOrNull("al"), acd_mm:numberOrNull("acd"),
        k1_d:numberOrNull("k1"), k2_d:numberOrNull("k2"),
        k1_axis_deg:numberOrNull("k1Axis"), k2_axis_deg:numberOrNull("k2Axis"),
        prior_corneal_surgery:$("priorSurgery").value || null,
        cct_um:numberOrNull("cct"), lens_thickness_mm:numberOrNull("lensThickness"), wtw_mm:numberOrNull("wtw")
      }),
      reportSnapshot: () => ({eye, plan: powerPlans[eye], recommendation}),
      reset() {
        invalidate();
        root.hidden = true; recommendationRoot.hidden = true; calculationRoot.hidden = true;
        $("iolForm").reset();
        root.querySelectorAll("input").forEach(node => { node.readOnly = false; });
        $("eye").value = eye;
        ["kDifference", "sia", "siaAxis"].forEach(id => { $(id).readOnly = true; });
        $("selectedLens").replaceChildren();
        $("priorSurgery").value = "NONE"; $("historicalData").value = "false";
        $("historyField").hidden = true; $("priorSurgeryPanel").open = false;
        $("priorSurgerySummary").textContent = tr("Previous corneal surgery (LASIK/PRK/RK)");
        regularityAttentionPending = false;
        $("astigType").required = false;
        $("astigType").removeAttribute("aria-invalid");
        $("astigTypeHelp").hidden = true;
        $("astigTypeField").classList.remove("required-attention");
        root.querySelectorAll(".field-attention").forEach(field => field.classList.remove("field-attention"));
        $("backCompletion").hidden = true;
        $("lensThicknessField").hidden = true; $("lensThickness").value = "";
        $("alMarker").textContent = "";
      },
      populate() { root.hidden = false; populateEye(); }
    };
  }

  function clearSourceCase() {
    caseVersion++;
    loadedEyes = [];
    for (const eye of ["OD", "OS"]) {
      originals[eye] = null; pentacamByEye[eye] = null; corneaBackByEye[eye] = null; incisionOverrides[eye] = null; powerPlans[eye] = null;
      controllers.get(eye)?.reset();
    }
    syncWorkflow();
    $("bothStatus").textContent = "";
  }
  ["OD", "OS"].forEach(eye => controllers.set(eye, createEyeController(eye)));
  $("patientForm").addEventListener("submit", event => event.preventDefault());
  $("patientForm").addEventListener("input", event => {
    if (event.target.validity?.valid) event.target.classList.remove("field-attention");
    if (event.target.id !== "sourceImages") controllers.forEach(controller => controller.invalidate());
  });
  $("patientForm").addEventListener("change", event => {
    if (event.target.validity?.valid) event.target.classList.remove("field-attention");
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
    if (workflowBusy) return;
    clearSourceCase();
    workflowBusy = true; syncWorkflow();
    $("extractButton").disabled = true; $("sourceImages").disabled = true; $("patientName").readOnly = true;
    status.textContent = tr("Transcribing source-locked fields…");
    try {
      const data = await window.CERAI_IOL_JOBS.extract({files, patientName:surgeonPatientName, requestId:iolAssessmentRequestId, onProgress:text => { status.textContent = text; }});
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
      // Evaluate complete eyes immediately; missing regularity stays with the surgeon.
      if (document.getElementById("patientForm").checkValidity()) {
        await Promise.allSettled(loadedEyes.filter(eye => controllers.get(eye).readyToRecommend()).map(eye => controllers.get(eye).evaluate()));
      }
      syncWorkflow();
      const nameReview = data.identity.source_name_review_required ? tr(" The surgeon-entered patient name was retained. Check the patient names printed on the source reports.") : "";
      status.textContent = tr("Images read. Complete any missing fields, then continue to lens recommendation.") + nameReview + (unreadable.length ? " " + unreadable.join(", ") : "");
    } catch (error) { if (error.restartRequired) iolAssessmentRequestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`; clearSourceCase(); status.textContent = error.message || tr("Image transcription failed."); status.classList.add("error"); }
    finally {
      workflowBusy = false; $("patientName").readOnly = false; syncWorkflow();
      // Focus the first unresolved eye once, after all source panels are ready.
      loadedEyes.some(eye => controllers.get(eye).focusMissingRegularity());
    }
  });
  async function runLoadedEyes(method) {
    const requestCaseVersion = caseVersion;
    if (workflowBusy || !loadedEyes.length || !$("patientForm").reportValidity()) return;
    if (method === "recommend" && !loadedEyes.every(eye => controllers.get(eye).readyToRecommend())) return;
    if (method === "evaluate") controllers.forEach(controller => controller.invalidate());
    workflowBusy = true; syncWorkflow();
    $("bothStatus").textContent = tr("Processing loaded eyes…");
    try {
      const results = await Promise.allSettled(loadedEyes.map(async eye => {
        const controller = controllers.get(eye);
        if (method === "recommend" && !controller.evaluated() && !await controller.evaluate()) return false;
        return controller[method]();
      }));
      if (requestCaseVersion !== caseVersion) return;
      $("bothStatus").textContent = tr(results.every(result => result.status === "fulfilled" && result.value === true)
        ? (method === "recommend"
          ? "Recommendation generated. Select the lens for Stage 2."
          : "Completed. Review the separate OD and OS results below.")
        : "Review each eye's status and complete any missing fields.");
    } finally { workflowBusy = false; syncWorkflow(); }
  }
  $("escrsTransferAll").addEventListener("click", async () => {
    const button = $("escrsTransferAll"), status = $("escrsTransferStatus");
    let payload;
    try { payload = escrsTransferPayload(); }
    catch (error) {status.textContent = tr(error.message);return;}
    const tab = window.open("about:blank", "_blank");
    if (tab) tab.opener = null;
    button.disabled = true;
    try {
      const response = await fetch("/iol/escrs-transfer", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
      const result = await response.json();
      if (!response.ok) throw new Error(errorMessage(result));
      if (tab) tab.location.replace(result.escrs_url); else window.location.assign(result.escrs_url);
      status.textContent = tr("Measurements transferred. Select the lens and surgical settings in ESCRS.");
    } catch (error) {if (tab) tab.close();status.textContent = tr(error.message);}
    finally {syncWorkflow();}
  });
  $("recommendAll").addEventListener("click", () => runLoadedEyes("recommend"));
  $("calculateAll").addEventListener("click", () => runLoadedEyes("calculate"));
})();
