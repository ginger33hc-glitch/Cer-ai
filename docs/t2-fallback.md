# Local T2 fallback

Cooke K6 remains the primary spherical calculator. Timeouts, connection failures,
HTTP service failures (including 408/429/5xx), and unusable responses fall back to local T2. Explicit LT
requests and HTTP 400/422 validation failures retain the existing correction flow.
Prior LASIK/PRK/RK routes bypass both standard formulas.

T2's calculation core is ported from Tim Cooke's MIT-licensed implementation:
https://github.com/timothylcooke/iolcalculator.com
Commit: 3606e8351cf32b82e3c9df78b93c5e9843e884ee
Files: src/api/IolFormula/T2Formula.ts, src/api/Settings.ts,
src/tests/test-formula.test.ts. License: iol_module/THIRD_PARTY_T2_LICENSE.txt.
Original publication: https://pubmed.ncbi.nlm.nih.gov/21029888/

Inputs use the existing anterior K index 1.3375, axial length, and catalog optical
A-constant. No LT is estimated or required. The existing ACD-derived target is
retained. Candidate powers remain 6–30 D in 0.5 D increments, matching K6's
request. Seven adjacent candidates are returned, with exactly one closest to
target marked. A target outside the computed power-range refractions is rejected
instead of presenting an endpoint as a successful match. Published implementation
input limits and finite results are checked. These are implementation limits,
not claims of clinical validation throughout those ranges.

Results record spherical_formula and fallback_reason. T2 is explicitly labeled
in both languages; optional ESCRS transfer remains available for either eye.
The existing experimental toric calculation can use T2's spherical power and
predicted refraction as its anchor. It retains its TEST_ONLY status: T2 itself
is not a toric formula and this does not clinically validate the hybrid model.

The 12 upstream reference outputs are numerical regression checks, not an
independent clinical validation. Route tests cover outages, normal K6 success,
post-refractive exclusions, validation errors, LT omission, both eyes, bounds,
and toric provenance. Catalog constants have not been optimized for T2 using
local postoperative outcomes.
