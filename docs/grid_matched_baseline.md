# docs/grid_matched_baseline.md — Pineios grid-matched baseline (fills Table 10, targets §8)

**Objective.** Fill the intentionally-blank Pineios row of Table 10 (baseline-vs-enhanced Δ). The flagship enhanced run (CSI 0.456) had no grid-matched baseline — the only rain-on-grid Pineios run used a different 100 m grid — so the §8 limitation "flagship lacks a grid-matched baseline" stood. Here a default **ERA5 rain-on-grid** baseline is run on the **identical 150 m geometry** as the canonical enhanced run, scored through the committed harness against the same EMS reference and 4642 km² mask. One baseline SFINCS run; the enhanced canonical output was read-only.

## 0. Gates (both passed)

- **(a)** Enhanced `sfincs_map.nc` re-scored on the 4642 km² mask reproduces **CSI 0.456 / HR 0.947 / FAR 0.532 / B 2.02 / GSS 0.201 @0.10 m** and **CSI 0.515 @0.50 m** to the decimal (see independent_truth.md gate).
- **(b)** Enhanced grid: **666×536 @150 m, 4× sub-grid, 262,465 active cells**, eval mask **4642 km²** (206,326 cells). _(Note: AUDIT/task said "611×690" — that is the **Strymonas** grid; Pineios is 666×536. The 262,465 active-cell figure is correct for Pineios.)_

## 1. Baseline config — what was stripped, and the asserted grid identity

Cloned the enhanced EMSR692 build and changed **only the forcing**, to the same lossless rain-on-grid recipe as the committed Mandra/Strymonas baselines:

| block | enhanced | grid-matched baseline |
|---|---|---|
| precipitation | bias-corrected IMERG (×2.725 → 380 mm) | **raw ERA5 rain-on-grid** (`precip: era5_hourly`) |
| gauge bias-correction | on (target 400 mm) | **off** |
| GloFAS-Q injection | 4 reach points | **off** (no src/dis) |
| inverse barometer / wind+MSLP | pavbnd=1 + ERA5 wind+pressure | **off** (pavbnd=0, static sea zsini=0) |
| SCS-CN infiltration | off (lossless) | **off** (lossless — matches enhanced AND the C1 finding) |

**Kept byte-identical:** domain bbox [21.84,39.31,22.99,40.02], 150 m base grid + 4× sub-grid, GLO-30 DEM, WorldCover Manning lookup, active mask, window (tref 2023-08-27, tstart 09-03, tstop 09-11; 7-day antecedent), and the EMS reference + 4642 km² AOI-union mask.

**Grid-identity assertion (baseline build vs STEP 0b):**

| quantity | enhanced | baseline | match |
|---|---|---|---|
| active cells | 262,465 | 262,465 | YES |
| grid n×m | 536×666 | 536×666 | YES |
| x0 / y0 | 571682.0 / 4351515.0 | 571682.0 / 4351515.0 | YES |
| eval mask | 4642 km² | 4642 km² | YES |

**Forcing cross-check:** the baseline integrates **290 mm domain-mean** ERA5 precipitation over the 03–11 Sep window (consistent with the manuscript's 331 mm *convective-core* domain-mean; the difference is core-subset vs full-domain). That is **≫ raw IMERG's 141 mm** and **< the corrected 380 mm** — a substantial baseline rainfall, so the Δ outcome is not pre-judged.

## 2. Baseline contingency (same harness, same 4642 km² mask)

| threshold | CSI | HR | FAR | B | GSS |
|---|---|---|---|---|---|
| hmax>0.10 m | **0.517** | 0.823 | 0.418 | 1.42 | 0.319 |
| hmax>0.50 m | 0.390 | 0.439 | 0.222 | 0.56 | 0.270 |

One-sided fuzzy r=1 (±150 m): tolerant **HR 0.970** (dilate model) / tolerant **CSI 0.539** (dilate obs). Baseline wet area: 2149 km² (>0.10 m), 856 km² (>0.50 m) vs EMS observed 1519 km².

## 3. Table-10 Pineios Δ row (enhanced − baseline, @0.10 m)

| metric | baseline | enhanced | **Δ** |
|---|---|---|---|
| CSI | 0.517 | 0.456 | **-0.061** |
| HR  | 0.823 | 0.947 | **+0.124** |
| FAR | 0.418 | 0.532 | **+0.114** |
| B   | 1.42 | 2.02 | **+0.61** |
| GSS | 0.319 | 0.201 | **-0.118** |

## 4. Verdict — honest interpretation

**The enhanced forcing is NOT a strict-CSI gain on the flagship; it is recall- and depth-oriented.** The grid-matched ERA5 baseline is already skilful — at the canonical 0.10 m threshold it scores **CSI 0.517**, *marginally above* the enhanced **0.456** (ΔCSI **-0.061**), with lower over-prediction (B 1.42 vs 2.02). What the enhanced forcing (bias-corrected IMERG + wind + IB + Q) buys is **recall and depth**, not headline CSI:

- **HR +0.124** (0.823 → 0.947): the enhanced run recovers ~95 % of the observed extent vs ~82 % for the baseline — it floods more area (2149 → 3074 km²), trading precision (FAR +0.114, B +0.61) for recall.
- **deep-flood skill:** at 0.50 m the enhanced CSI is 0.515 vs the baseline's 0.390 — the deeper, gauge-anchored flood wins decisively at the higher threshold.
- **CSI ceiling unchanged:** best-over-thresholds CSI is ~0.517 (baseline @0.10 m) vs ~0.515 (enhanced @0.50 m) — essentially tied. The enhanced forcing does **not raise the achievable CSI ceiling**; it relocates the skill to a deeper, higher-recall flood.

This is the **same diagnostic (not headline-gain) pattern as Strymonas** (AUDIT guardrail 3): enhanced forcing does not beat the baseline on strict CSI; its value is recall/physical realism.

## 5. Manuscript actions

**§8 limitation — can be REMOVED.** "The flagship lacks a grid-matched baseline" is now resolved; replace it with the measured Δ and the recall-vs-precision framing above.

**Sentences to soften (they currently overstate the rainfall upgrade on Pineios):**
- §5.1 / Fig. 4: "raw IMERG captures only 141 mm … bounds the flood below 40 km²" — keep, but make explicit this is **raw IMERG**, *not* the ERA5 baseline. The ERA5 rain-on-grid baseline (290 mm) produces a **competitive flood (CSI 0.517)** — the IMERG correction does not rescue a failed baseline, it deepens an already-skilful one.
- §1.3 contribution wording: any claim that gauge-anchored IMERG is *decisive* for the Pineios flood should be re-scoped to *recall/depth* (HR +0.124, 0.50 m CSI 0.390→0.515), not strict CSI.

**Table 10 — Pineios row (fill the blank cells):**

> Pineios Δ (enhanced − baseline, @0.10 m): ΔCSI **-0.061**, ΔHR **+0.124**, ΔFAR **+0.114**, ΔB **+0.61** (baseline 0.517/0.823/0.418/1.42; enhanced 0.456/0.947/0.532/2.02).

**Drop-in note for §4.1 / §5.1:**

> A grid-matched ERA5 rain-on-grid baseline on the identical 150 m wide-Thessaly geometry (262,465 active cells, 4642 km² mask) yields CSI 0.517 / HR 0.823 / B 1.42 at hmax>0.10 m. The enhanced forcing therefore does not raise the strict-CSI ceiling on Pineios (ΔCSI −0.061) but increases hit rate (+0.124, to 0.947) and deep-flood skill (0.50 m CSI 0.390→0.515) at the cost of more false positives (B 1.42→2.02) — the enhanced gain on the flagship is recall- and depth-oriented, the same diagnostic role established for Strymonas, not a headline strict-CSI improvement.

---
_One baseline SFINCS run; enhanced output read-only. Build: `reproduction/grid_matched_baseline/work/sfincs_build.yml`; score+Δ: `score_baseline.py`; numbers in `baseline_rescore.json`. Harness = committed `validate_event_v2` functions; all_touched=True (committed convention, matches the 0.456 baseline)._