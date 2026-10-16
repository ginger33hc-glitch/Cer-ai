/* Independent DOM adapter. No remote code, formula calculation or automatic submit. */
"use strict";
(() => {
  const norm = value => String(value ?? "").replace(/\*/g, "").replace(/\s+/g, " ").trim().toLowerCase();
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function until(check, message, timeout = 8000) {
    const end = Date.now() + timeout;
    while (Date.now() < end) { const value = check(); if (value) return value; await pause(100); }
    throw new Error(message);
  }
  function field(root, name) {
    const found = [...root.querySelectorAll('input, [role="combobox"]')].filter(input =>
      input.type !== "hidden" && (norm(input.getAttribute("aria-label")) === norm(name) ||
      [...(input.labels || [])].some(label => norm(label.textContent) === norm(name))));
    if (found.length !== 1) throw new Error(`Cannot identify ${name} unambiguously.`);
    return found[0];
  }
  const valueOf = control => typeof control.value === "string" ? control.value : control.textContent.trim();
  function eyeRoot(side) {
    const heading = [...document.querySelectorAll("h5")].filter(h => norm(h.textContent) === (side === "OD" ? "od right" : "os left"));
    if (heading.length !== 1) return null;
    const root = heading[0].closest(".mud-paper");
    return root && root.querySelectorAll("h5").length === 1 ? root : null;
  }
  async function fill(root, name, value) {
    if (value === null || value === undefined) return;
    let input = field(root(), name);
    if (input.disabled || input.readOnly) throw new Error(`${name} is not editable.`);
    input.focus();
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, String(value));
    input.dispatchEvent(new Event("input", {bubbles:true}));
    input.dispatchEvent(new Event("change", {bubbles:true}));
    input.blur();
    await pause(300);
    input = field(root(), name);
    const same = value === "" ? input.value === "" : input.type === "number" ? input.value !== "" && Number(input.value) === Number(value) : input.value === String(value);
    if (!same) throw new Error(`${name} did not retain the transferred value.`);
  }
  async function toggle(root, name, value) {
    const input = field(root(), name);
    if (input.checked !== value) {
      input.click();
      await until(() => field(root(), name).checked === value, `${name} did not change.`);
      await pause(400);
    }
  }
  async function select(root, name, expected) {
    const input = field(root(), name);
    if (expected.some(value => norm(value) === norm(valueOf(input)))) return valueOf(input);
    if (input.disabled) throw new Error(`${name} is disabled.`);
    // Both MudSelect and MudAutocomplete open on mousedown on the input
    // control. A synthetic click alone never reaches those handlers.
    input.dispatchEvent(new MouseEvent("mousedown", {button:0,bubbles:true}));
    const options = await until(() => {
      const items = [...document.querySelectorAll('[role="option"]')].filter(e => e.getClientRects().length);
      return items.length ? items : null;
    }, `${name} options did not load.`);
    const matches = options.filter(e => expected.some(value => norm(e.textContent) === norm(value)));
    if (matches.length !== 1) {
      input.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape",code:"Escape",bubbles:true}));
      throw new Error(`No exact, unique ${name} match for ${expected.join(" / ")}. No substitute selected.`);
    }
    const chosen = matches[0].textContent.trim();
    matches[0].click();
    await until(() => norm(valueOf(field(root(), name))) === norm(chosen), `${name} selection was not retained.`);
    await pause(400);
    return chosen;
  }
  function validate(p) {
    if (!p || p.version !== 1 || typeof p.surgeon !== "string" || !p.surgeon.trim() || typeof p.initials !== "string" || !p.initials.trim()) throw new Error("Surgeon and patient initials are required.");
    if (!Number.isInteger(p.age) || p.age < 1 || p.age > 120 || !["Male","Female"].includes(p.sex)) throw new Error("Review age and sex in CER-AI.");
    if (!p.eyes || !Object.keys(p.eyes).length || Object.keys(p.eyes).some(k => !["OD","OS"].includes(k))) throw new Error("Invalid eye assignment.");
    for (const [side,e] of Object.entries(p.eyes)) {
      if (!e || typeof e.toric !== "boolean" || !Array.isArray(e.lens_matches) || !e.lens_matches.length || !Array.isArray(e.manufacturer_matches) || !e.manufacturer_matches.length) throw new Error(`${side}: lens mapping is missing.`);
      for (const [key,min,max] of [["axial_length_mm",12,38],["acd_mm",0.1,10],["k1_d",30,60],["k2_d",30,60],["target_refraction_d",-20,20]]) {
        if (!Number.isFinite(e[key]) || e[key] < min || e[key] > max) throw new Error(`${side}: invalid ${key}.`);
      }
      for (const [key,min,max] of [["lens_thickness_mm",1,8],["cct_um",200,900],["wtw_mm",5,20]]) {
        if (e[key] != null && (!Number.isFinite(e[key]) || e[key] < min || e[key] > max)) throw new Error(`${side}: invalid ${key}.`);
      }
      if (e.cct_um != null && !Number.isInteger(e.cct_um)) throw new Error(`${side}: CCT must use whole micrometres.`);
      if ([...e.lens_matches,...e.manufacturer_matches].some(v => typeof v !== "string" || !v.trim() || v.length > 200)) throw new Error(`${side}: invalid lens mapping.`);
      if (e.k1_d > e.k2_d) throw new Error(`${side}: K1 exceeds K2.`);
      if (!Number.isFinite(e.a_constant) || e.a_constant < 100 || e.a_constant > 130) throw new Error(`${side}: invalid lens constant.`);
      if (e.prior_corneal_surgery !== "NONE") throw new Error(`${side}: post-refractive automatic transfer requires a separately validated mapping.`);
      if (e.toric) for (const [key,max] of [["k1_axis_deg",180],["k2_axis_deg",180],["incision_axis_deg",180],["sia_d",5]]) {
        if (!Number.isFinite(e[key]) || e[key] < 0 || e[key] > max) throw new Error(`${side}: invalid ${key}.`);
      }
    }
    return p;
  }
  async function run(payload) {
    const p = validate(payload);
    await until(() => eyeRoot("OD") && eyeRoot("OS"), "ESCRS form is not ready. Complete any terms dialog yourself, then retry.", 30000);
    if ([...document.querySelectorAll('[role="dialog"]')].some(e => e.getClientRects().length)) throw new Error("Close the ESCRS dialog yourself, then retry.");
    for (const side of ["OD","OS"]) {
      const root = eyeRoot(side);
      if (!p.eyes[side] && field(root,"AL").value !== "") throw new Error(`${side}: the unused eye is not empty. Open a new transfer from CER-AI.`);
      if (p.eyes[side] && field(root,"Keratoconus").checked) throw new Error(`${side}: keratoconus mode is not supported by this transfer.`);
    }
    const whole = () => document;
    await fill(whole,"Surgeon",p.surgeon);
    await fill(whole,"Patient Initials",p.initials);
    await fill(whole,"Age",p.age);
    await select(whole,"Gender",[p.sex]);
    await fill(whole,"Id",p.patient_id || "");
    const selected = {}, cookeConstants = {};
    for (const side of ["OD","OS"]) {
      const e = p.eyes[side]; if (!e) continue;
      const root = () => eyeRoot(side);
      await toggle(root,"Toric",e.toric);
      await toggle(root,"Post LASIK/PRK/RK",false);
      await toggle(root,"Argos (SoS) AL",false);
      await select(root,"Index",["1.3375"]);
      await select(root,"Manufacturer",e.manufacturer_matches);
      selected[side] = await select(root,"Select IOL",e.lens_matches);
      for (const [label,key] of [["AL","axial_length_mm"],["ACD","acd_mm"],["LT","lens_thickness_mm"],["CCT","cct_um"],["WTW","wtw_mm"],["K1","k1_d"],["K2","k2_d"],["Target Refraction","target_refraction_d"]]) await fill(root,label,e[key] ?? "");
      // Other formulas retain their own ESCRS model-specific constants (e.g. pACD).
      if (!e.toric) {
        const cooke = [...root().querySelectorAll("input")].some(i => [...(i.labels || [])].some(l => norm(l.textContent) === "cooke a-constant"));
        if (cooke) { await fill(root,"Cooke A-Constant",e.a_constant); cookeConstants[side] = e.a_constant; }
      }
      if (e.toric) for (const [label,key] of [["K1 axis","k1_axis_deg"],["K2 axis","k2_axis_deg"],["Incision","incision_axis_deg"],["SIA","sia_d"]]) await fill(root,label,e[key]);
    }
    // All values are read back after both eyes, catching later re-renders/overwrites.
    for (const [side,e] of Object.entries(p.eyes)) {
      const root = eyeRoot(side);
      if (norm(field(root,"Select IOL").value) !== norm(selected[side]) || field(root,"Toric").checked !== e.toric) throw new Error(`${side}: lens/mode read-back failed.`);
      if (!e.manufacturer_matches.some(v => norm(v) === norm(valueOf(field(root,"Manufacturer")))) || norm(valueOf(field(root,"Index"))) !== "1.3375") throw new Error(`${side}: manufacturer/index read-back failed.`);
      if (field(root,"Post LASIK/PRK/RK").checked || field(root,"Argos (SoS) AL").checked || field(root,"Keratoconus").checked) throw new Error(`${side}: unexpected calculation mode.`);
      if (cookeConstants[side] !== undefined && Number(field(root,"Cooke A-Constant").value) !== cookeConstants[side]) throw new Error(`${side}: Cooke constant read-back failed.`);
      const checks = [["AL","axial_length_mm"],["ACD","acd_mm"],["K1","k1_d"],["K2","k2_d"],["Target Refraction","target_refraction_d"],["LT","lens_thickness_mm"],["CCT","cct_um"],["WTW","wtw_mm"]];
      if (e.toric) checks.push(["K1 axis","k1_axis_deg"],["K2 axis","k2_axis_deg"],["Incision","incision_axis_deg"],["SIA","sia_d"]);
      for (const [label,key] of checks) {
        if (e[key] === null || e[key] === undefined) {
          if (field(root,label).value !== "") throw new Error(`${side}: ${label} should be empty.`);
          continue;
        }
        if (field(root,label).value === "" || Number(field(root,label).value) !== e[key]) throw new Error(`${side}: ${label} read-back failed.`);
      }
    }
    for (const [label,value] of [["Surgeon",p.surgeon],["Patient Initials",p.initials],["Age",String(p.age)],["Gender",p.sex],["Id",p.patient_id || ""]]) {
      if (norm(valueOf(field(document,label))) !== norm(value)) throw new Error(`${label} read-back failed.`);
    }
    return selected;
  }
  globalThis.CeraiEscrsAdapter = {run,validate,norm};
})();
