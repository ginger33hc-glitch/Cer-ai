"""Procedure-independent screening using existing canonical tomography rules.

This is a CER-AI screening policy, not a validated diagnostic probability model.
ERSS surgical total and procedure-specific PS3 allowances are not calculated.
"""

from dataclasses import asdict

from .bad import BADContext, evaluate_bad
from .disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS,
    PASS_WITH_CAUTION,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
)
from .erss import erss_disposition, erss_topography_points
from .nice import nice_disposition, score_nice
from .ps3 import evaluate_ps3
from ps3_policy import defers_all_procedures
from .rules import erss_topography_category

SCREENING_POLICY_VERSION = "CER-AI-KC-1.0"
SCREENING_LABELS = {
    PASS: "NEGATIVE",
    CAUTION: "SUSPICIOUS",
    PASS_WITH_CAUTION: "SUSPICIOUS",
    STOP_DEFER: "POSITIVE",
    ASSESSMENT_INCOMPLETE: "NOT_ASSESSABLE",
}


def evaluate_keratoconus(inp):
    """Reuse tomography components only; never manufacture a surgical plan."""
    bad = evaluate_bad(
        inp.final_bad_d,
        context=BADContext(
            df=inp.bad_df,
            db=inp.bad_db,
            dp=inp.bad_dp,
            dt=inp.bad_dt,
            da=inp.bad_da,
            artmax_um=inp.artmax_um,
            ppi_min=inp.ppi_min,
            ppi_avg=inp.ppi_avg,
            ppi_max=inp.ppi_max,
        ),
    )
    bad_status = {"NORMAL": PASS, "SUSPICIOUS": CAUTION, "ABNORMAL": STOP_DEFER}.get(
        bad.classification, ASSESSMENT_INCOMPLETE
    )
    category = erss_topography_category(
        inp.i_s_d, inp.derived_srax_deg, inp.srax_gt20_confirmed
    )
    topography_points = erss_topography_points(category)
    topography_status = erss_disposition(topography_points)
    nice = score_nice(
        inp.nice_k2_d, inp.nice_central_pachy_um, inp.nice_b_ele_th_um, inp.i_s_d
    )
    nice_status = nice_disposition(nice["total"])
    ps3 = (
        evaluate_ps3(inp.ps3_eye, inp.ps3_inter_eye)
        if inp.ps3_eye is not None
        else None
    )
    # The common PS3 defer rule is >=1 High or >=2 Moderate. A lone
    # Moderate is suspicious without selecting a LASIK/PRK/SMILE pathway.
    ps3_status = (
        ASSESSMENT_INCOMPLETE
        if ps3 is None or not ps3.complete
        else STOP_DEFER
        if defers_all_procedures(ps3.moderate_count, ps3.high_count)
        else CAUTION
        if ps3.moderate_count
        else PASS
    )
    findings = (
        DecisionFinding(
            "topography",
            topography_status,
            f"I-S/SRAX: {category}; topography component {topography_points!r} (not an ERSS total)",
        ),
        DecisionFinding(
            "bad_d",
            bad_status,
            f"Final BAD-D {inp.final_bad_d!r}: {bad.classification}",
        ),
        DecisionFinding("nice", nice_status, f"NICE total: {nice['total']!r}"),
        DecisionFinding(
            "ps3",
            ps3_status,
            f"PS3: {ps3.high_count if ps3 else 0} High / {ps3.moderate_count if ps3 else 0} Moderate",
        ),
    )
    missing = []
    if bad_status == ASSESSMENT_INCOMPLETE:
        missing.append("BAD_D")
    if topography_status == ASSESSMENT_INCOMPLETE:
        missing.append("I_S / front-map SRAX confirmation")
    missing.extend(nice["missing"])
    missing.extend(f"PS3: {key}" for key in (ps3.missing_keys if ps3 else ("eye",)))
    final = finalize_disposition(findings, incomplete_first=True)
    # Incomplete screening must not be presented as a completed negative or positive.
    status = final.status
    return {
        "status": status,
        "screening_result": SCREENING_LABELS[status],
        "findings": [asdict(finding) for finding in findings],
        "missing": list(dict.fromkeys(missing)),
        "bad_d": {
            "classification": bad.classification,
            "value": bad.final_d,
            "context": asdict(bad.context),
        },
        "topography": {"category": category, "points": topography_points},
        "nice": nice,
        "ps3": asdict(ps3) if ps3 is not None else None,
    }
