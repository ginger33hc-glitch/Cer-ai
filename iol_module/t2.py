"""Local T2 spherical refraction calculation (anterior K index 1.3375).

Ported from Tim Cooke's MIT-licensed iolcalculator.com at
3606e8351cf32b82e3c9df78b93c5e9843e884ee, T2Formula.calculate.
See THIRD_PARTY_T2_LICENSE.txt. Not a post-refractive or toric formula.
"""
from math import isfinite


def predicted_refraction(al: float, k1: float, k2: float, a_constant: float, power: float) -> float:
    """Return spectacle-plane refraction at the source's 12 mm vertex distance."""
    values = ((al, 13, 40), (k1, 32, 57), (k2, 32, 57),
              (a_constant, 101, 129), (power, -20, 80))
    if any(not isfinite(v) or not low <= v <= high for v, low, high in values):
        raise ValueError("Measurements are outside the published T2 implementation limits.")
    mean_k = (k1 + k2) / 2
    k0 = 333 / 337.5 * mean_k
    elp = (-10.32566272 + 0.326300537 * al + 0.135332269 * mean_k
           + 0.62467 * a_constant - 68.747 - 3.336)
    corrected_al = 0.97971 * al + 0.65696
    try:
        result = 1000 / (1000 / (1336 / (1336 / (1336 / (corrected_al - elp) - power) + elp) - k0) + 12)
    except (ZeroDivisionError, OverflowError) as exc:
        raise ValueError("T2 cannot calculate these measurements.") from exc
    if not isfinite(result):
        raise ValueError("T2 returned a non-finite refraction.")
    return result


def predictions(al: float, k1: float, k2: float, a_constant: float, target: float) -> list[dict[str, object]]:
    # Preserve the existing clinic power range used in the K6 request.
    rows = [{"IOL": half / 2, "Rx": predicted_refraction(al, k1, k2, a_constant, half / 2)}
            for half in range(12, 61)]
    if not isfinite(target) or not min(p["Rx"] for p in rows) <= target <= max(p["Rx"] for p in rows):
        raise ValueError("T2 target lies outside the available 6–30 D lens power range.")
    best = min(range(len(rows)), key=lambda i: abs(rows[i]["Rx"] - target))
    start = max(0, min(best - 3, len(rows) - 7))
    for i, row in enumerate(rows):
        row["IsBestOption"] = i == best
    return rows[start:start + 7]
