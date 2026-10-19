"""Base-rate-robust skill scores from a pixel contingency table.

Strict CSI at a fixed depth threshold penalises over-prediction, so it understates
skill for the convective/coastal events whose frequency bias is large (B = 5-12).
These two scores are reported alongside B (never instead of it — a large B is an
operational false-alarm cost in its own right, even where the flood is correctly
located):

  * Symmetric Extremal Dependence Index (SEDI) — Ferro & Stephenson (2011),
    Weather and Forecasting 26, 699-713. Conditional-discrimination measure whose
    value does not degenerate as the base rate (wet fraction) tends to zero:

        SEDI = [ln F - ln H - ln(1-F) + ln(1-H)]
               ---------------------------------          ... manuscript Eq (10)
               [ln F + ln H + ln(1-F) + ln(1-H)]

  * Peirce Skill Score (PSS), a.k.a. Hanssen-Kuipers / true skill statistic:

        PSS = H - F                                       ... manuscript Eq (11)

  with, from the contingency table (TP hits, FP false alarms, FN misses, TN
  correct negatives):

        H = TP / (TP + FN)      hit rate (probability of detection, POD)
        F = FP / (FP + TN)      false-alarm RATE (probability of false detection)

IMPORTANT — F is the false-alarm RATE (POFD), conditioned on observed-dry cells.
It is NOT the false-alarm RATIO FAR = FP / (TP + FP), which is conditioned on
predicted-wet cells and is reported separately by the validator. The two are
routinely confused; substituting FAR for F changes every score (see
test_skill_scores.py::TestPofdIsNotFar). Both are exposed here so callers can be
explicit about which they mean.

Properties these scores are relied on for, locked by the unit tests:
  * no skill (H == F)      -> SEDI = 0,  PSS = 0
  * perfect (H=1, F=0)     -> SEDI -> 1, PSS = 1
  * SEDI and PSS depend on the contingency table ONLY through H and F, so they are
    invariant to the base rate at fixed (H, F).

Run the tests with:  python -m unittest discover -s validation -v
"""
from __future__ import annotations

import math

__all__ = ["hit_rate", "pofd", "far", "sedi", "pss", "skill_scores"]

# SEDI's logs are undefined at H or F in {0, 1}; clamp only to keep the score
# finite in degenerate corners. The clamp is inert for every event in the paper
# (all H, F lie well inside the open interval) — asserted in the unit tests.
_EPS = 1e-9


def hit_rate(tp: int, fn: int) -> float:
    """H = TP/(TP+FN) — hit rate / probability of detection. NaN if no observed wet."""
    d = tp + fn
    return (tp / d) if d else float("nan")


def pofd(fp: int, tn: int) -> float:
    """F = FP/(FP+TN) — false-alarm RATE (probability of false detection).

    Conditioned on observed-DRY cells. This is the F of Eq (10)/(11).
    """
    d = fp + tn
    return (fp / d) if d else float("nan")


def far(tp: int, fp: int) -> float:
    """FAR = FP/(TP+FP) — false-alarm RATIO, conditioned on predicted-WET cells.

    Reported for completeness; NOT used by sedi() or pss().
    """
    d = tp + fp
    return (fp / d) if d else float("nan")


def _clamp(x: float) -> float:
    return min(max(x, _EPS), 1.0 - _EPS)


def sedi(h: float, f: float) -> float:
    """Symmetric Extremal Dependence Index from H and F — manuscript Eq (10)."""
    hc, fc = _clamp(h), _clamp(f)
    num = math.log(fc) - math.log(hc) - math.log(1 - fc) + math.log(1 - hc)
    den = math.log(fc) + math.log(hc) + math.log(1 - fc) + math.log(1 - hc)
    return num / den


def pss(h: float, f: float) -> float:
    """Peirce Skill Score from H and F — manuscript Eq (11)."""
    return h - f


def skill_scores(tp: int, fp: int, fn: int, tn: int) -> dict:
    """SEDI/PSS (+ the H, F, FAR they derive from) for one contingency table."""
    h = hit_rate(tp, fn)
    f = pofd(fp, tn)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "hit_rate": h,
        "pofd": f,
        "far": far(tp, fp),
        "sedi": sedi(h, f),
        "pss": pss(h, f),
    }
