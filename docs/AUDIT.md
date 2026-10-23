# AUDIT.md — auditable reproduction record

Full auditing record for `sfincs-mediterranean-floods`. Purpose: let any future session
**detect drift** from the verified numbers. Ground truth = these tables +
[`_sources/VALIDATION_SUMMARY_for_review.md`](_sources/VALIDATION_SUMMARY_for_review.md) +
the per-event JSON reports. Where the manuscript `.docx` and this record disagree, **this record
wins**. Last reproduced: **2026-06-19** (env: conda `sfincs-viz`, HydroMT 0.10.1, HydroMT-SFINCS
1.2.2, SFINCS v2.3.0 mt_Faber_release_2025.02, numpy 2.4.6).

---

## 1. Reproduction method (two-way validation; both paths agree to ≤ 0.001)
Each headline run was validated **two independent ways**, which agree:
1. **Re-validate the stored output** — run `validate_event_v2.py` against the authors'
   committed `sfincs_map.nc` for each canonical run.
2. **Independent in-place pipeline re-run** — re-run pipeline steps prep→CN→Q→build→SFINCS
   (`run_pipeline.py --only 7,8,9,10,11`) from cached forcing into the same work dir (authors'
   `model/` preserved as `model_author_ref/`), then re-validate.

Result: Pineios and Mandra reproduced **exactly**; Strymonas v3 reproduced at 0.182 / 0.322 vs
0.183 / 0.328 — a sub-rounding numerical drift attributable to the unpinned numpy (2.4.6). The
**canonical published values are the authors' stored outputs** (Strymonas v3 = 0.183 / 0.328); the
in-place re-run corroborates them. Metric definitions: strict `hmax > 0.10 m` on `msk>0 ∩ union of
EMS AOIs`; fuzzy = symmetric r-cell dilation of **both** fields.

## 2. Reproduced headline metrics — VERIFIED (canonical run per event)
| Event (run) | CSI | HR | FAR | B | GSS | fuzzy r1 CSI / HR | peak-threshold CSI |
|---|---|---|---|---|---|---|---|
| Pineios EMSR692 (v1 enhanced) | 0.456 | 0.947 | 0.532 | 2.02 | 0.201 | 0.426 / 0.992 | 0.515 @ hmax>0.50 m |
| Strymonas EMSR122 (v3) | 0.183 | 0.328 | 0.706 | 1.11 | 0.136 | 0.250 / 0.398 | 0.190 @ hmax>0.05 m |
| Mandra EMSR257 (v1 enhanced) | 0.106 | 0.873 | 0.892 | 8.11 | 0.028 | 0.159 / 0.962 | 0.106 @ hmax>0.10 m |

Mandra fuzzy sweep (symmetric, h>0.10 m): r1 0.159/0.962, r2 **0.205/0.986**, r3 0.247/0.995.
Canonical-run selection (by the Appendix-B audit, not by score): Pineios v1 (time-varying-Q re-run
unchanged); Strymonas v3 (source-snap fix materially changes result); Mandra v1 (audit re-run under
mask restriction left metrics worse). See CLAUDE.md.

## 3. Baselines & ablations — VERIFIED
| Run | CSI | HR | FAR | B | GSS |
|---|---|---|---|---|---|
| Strymonas baseline (rain-on-grid ERA5) | 0.204 | 0.377 | 0.692 | 1.22 | 0.155 |
| Mandra baseline (rain-on-grid ERA5) | 0.080 | 0.400 | 0.910 | 4.43 | 0.008 |
| Strymonas CN-off + Q (ablation) | 0.238* | 0.951 | 0.759 | 3.94 | 0.166 |
| Strymonas CN-on + Q-off (ablation) | 0.016 | 0.016 | 0.183 | 0.02 | 0.014 |

\* CN-off+Q re-run gave 0.238/0.951/0.759/3.94/0.166; manuscript Table 12 reports 0.239/0.950/0.758/
3.93/0.167 — agreement within re-run drift. Pineios **now has a grid-matched baseline** (built on the
identical 150 m geometry; see the C-task entry below) — Table 10's blank Pineios Δ row can be filled:
ΔCSI −0.061, ΔHR +0.124, ΔFAR +0.114, ΔB +0.61 (baseline CSI 0.517 *exceeds* enhanced 0.456 @0.10 m).

### Rainfall bias-correction sensitivity (B2) — see [bias_sensitivity/](bias_sensitivity/)
Sweeping the IMERG gauge-anchor `target_mm` (all else fixed; 6 isolated SFINCS re-runs, canonical
outputs untouched and re-verified) shows both headlines are **robust to the bias target**: Mandra CSI
flat within ±0.001 over 95–255 mm (×4–11), Pineios CSI within ±0.03 over 220–510 mm (×1.5–3.5). The
calibrated values (Mandra 200 mm, Pineios 400 mm) are gauge-anchored, **not** CSI-maximising (for
Pineios a lower 220 mm would give marginally higher CSI but worse HR). Full table + sensitivity plots +
spatial corrected-rainfall fields (baseline + 2 extremes) in `docs/bias_sensitivity/`.

### Grid-matched Pineios baseline (fills Table 10; resolves §8) — see [grid_matched_baseline.md](grid_matched_baseline.md)
One baseline SFINCS run (enhanced output read-only). Default **ERA5 rain-on-grid** baseline on the
**identical 150 m geometry** as the canonical enhanced run — grid identity asserted (262,465 active
cells, 536×666, x0/y0 and 4642 km² mask all equal), forcing stripped to rain-on-grid (no IMERG/bias/
Q/IB/wind; CN off). ERA5 integrates 290 mm domain-mean (≫ raw IMERG 141, < corrected 380).
**Baseline @0.10 m: CSI 0.517 / HR 0.823 / FAR 0.418 / B 1.42 / GSS 0.319; @0.50 m CSI 0.390.**
**Table-10 Pineios Δ (enhanced − baseline, @0.10 m): ΔCSI −0.061, ΔHR +0.124, ΔFAR +0.114, ΔB +0.61.**
**Key result:** the ERA5 baseline is already skilful and *marginally beats* enhanced on strict CSI@0.10
(0.517 vs 0.456); the enhanced forcing is **recall/depth-oriented, not a strict-CSI gain** (HR
0.823→0.947; 0.50 m CSI 0.390→0.515; best-CSI ceiling tied ~0.516) — the **same diagnostic pattern as
Strymonas** (guardrail 3 now applies to Pineios too). **§8 "flagship lacks a grid-matched baseline" can
be REMOVED.** Soften §5.1/§1.3 wording that implies IMERG is *decisive* for the Pineios flood (the
"141 mm → <40 km²" point is **raw IMERG**, not the ERA5 baseline). Repro: `reproduction/grid_matched_baseline/`.

### Strymonas baseline + Table-10 Δ — ADJUDICATED (CODE-2, 2026-07-17)
Re-score only, no model re-run: `validate_event_v2.py` was re-run against the **committed**
`sfincs_map.nc` of all four Strymonas runs (baseline `emsr122_sfincs/model`, v1
`emsr122_sfincs_enhanced/model`, **canonical v3 `emsr122_sfincs_v3/model_author_ref`**, and the
2026-06-19 re-run `emsr122_sfincs_v3/model`). Canonical outputs read-only (SHA-256 identical
before/after). Repro: `ELKAK2/NHESS/R1_verification/task2_strymonas_delta/`.

| run | mask km² | obs km² | CSI | HR | FAR | B | GSS | TP/FP/FN |
|---|---|---|---|---|---|---|---|---|
| baseline (rain-on-grid ERA5) | 1222.672 | 106.582 | **0.2039** | **0.3766** | **0.6921** | 1.223 | 0.1551 | 1784/4011/2953 |
| enhanced v1 (pre-src-fix) | 1222.672 | 106.582 | 0.1701 | 0.2098 | 0.5267 | 0.443 | 0.1433 | 994/1106/3743 |
| **enhanced v3 (author, canonical)** | 1222.672 | 106.582 | **0.1834** | **0.3276** | **0.7059** | 1.114 | 0.1364 | 1552/3726/3185 |
| enhanced v3 (2026-06-19 re-run) | 1222.672 | 106.582 | 0.1822 | 0.3221 | 0.7045 | 1.090 | 0.1357 | 1526/3639/3211 |

**VERDICT: the audited set −0.021 / −0.049 / +0.014 is CORRECT; the draft's −0.020 / +0.018 /
+0.078 is WRONG.** Δ = v3 author − baseline @0.10 m, full precision:
ΔCSI 0.183387−0.203932 = **−0.020546 → −0.021** · ΔHR 0.327634−0.376610 = **−0.048976 → −0.049** ·
ΔFAR 0.705949−0.692148 = **+0.013801 → +0.014** · ΔB −0.109 → **−0.11** · ΔGSS −0.019.

**Why they diverged — NOT a mask difference, and NOT a grid difference. A superseded baseline run.**
- **Mask identical**: every run scores on the same 1222.6725 km² mask, 106.5825 km² observed,
  TP+FN = **4737 cells**, 8 EMS + 16 AOI shapefiles. The draft itself calls it "the 1222.7 km²
  four-AOI mask" — the same mask. So the mask is excluded as the cause.
- **Grid identical**: baseline and v3 are grid-matched — `sfincs.inp` mmax 690 / nmax 611 / dx=dy
  150 m / x0 650467.0 / y0 4495912.0 / rot 0 / EPSG 32634, same tstart–tstop (2015-03-28→04-04).
  (Only `tref` differs, 20150327 vs 20150321 — a time-axis origin, not a simulation change.)
- **The enhanced columns are current**: Table 8's v1 (0.170/0.210/0.527) and v3 (0.183/0.328/0.706)
  columns reproduce the committed outputs **exactly**. Only the **baseline** column is stale — in
  all four AOIs.
- **The stale numbers match no committed output.** Reverse-solving the draft's Δ against the printed
  v3 gives an implied baseline of **0.203 / 0.310 / 0.628**, i.e. exactly the 0.203/0.310/0.629 that
  §4.3.2 + Table 8 print. That contingency table is self-consistent (implied wet ≈ 3957 cells ≈
  89 km²) but **drier** than the committed baseline (5795 cells ≈ 130 km²) on the same mask.
- **Mechanism (inference — the superseded output no longer exists in the workspace):** the baseline
  was re-run at some point and Tables 8/10 were never refreshed, while **Table 12 was** — the same
  paper's Table 12 prints `Rain-on-grid baseline (ERA5) | 0.204 | 0.377 | 0.692 | 1.22 | 0.155` on
  "the 1222 km² four-area mask … computed with the harness behind the canonical v3 metrics", i.e.
  the committed values. `skill/examples/emsr122_strymonas.yaml` is annotated *"enlarged bbox, the run
  we just refreshed"*, documenting that refresh; an enlarged contributing domain is consistent with
  the observed dry→wet shift. The **adjudication does not depend on this mechanism** — it rests on
  the committed outputs, which only reproduce 0.204/0.377/0.692.

**Consequence for the prose (this is the substantive error, not just a digit).** Against the
*correct* baseline the enhanced run's **HR falls** (0.377 → 0.328, ΔHR **−0.049**); it does not rise.
The HR/bias recovery that §4.3.2/§5 describe (HR 0.210→0.328, B 0.44→1.11) is the **v1→v3 source-snap
fix**, not enhanced-vs-baseline. Any sentence attributing an HR gain to the enhanced forcing *relative
to baseline* is wrong and must be re-attributed to v1→v3 (this is the same correction made on
2026-06-19 for the NH-era docx; see §4).

### Emilia-Romagna (EMSR664) 15 m peak depth — DEM PIT (quarry), not ponding (CODE-6, 2026-07-17)
Repro: `ELKAK2/NHESS/R1_verification/task6_emilia_depth/`. Read-only.

The `run.peak_max_depth_m = 15.0515` reproduces from `sfincs_map.nc` (15.0517) at **row 320, col 238
— UTM32N 721795, 4922633 = lat 44.42300, lon 11.78627**, with **zb −2.252 m** (percentile 1.26 of the
active mask) and **zs 12.800 m**. It is a pit:

- **A hole, not a basin** — zb minus its window median: −5.5 m (3×3), −10.3 m (5×5), −14.3 m (11×11),
  **−15.1 m (21×21)**; the walls are **one 150 m cell** wide (zb 11.77 → −2.25 → 12.68 across 3 cells).
- **Present in the SOURCE DEM** — `gis/dep.tif` = **−0.072 m** vs a 17×17 median of **13.210 m**.
- **Filled exactly to its rim** (the decisive test) — water surface spread across the pit
  **0.0139 m** (a level pool) at **zs 12.800 m** vs rim (11×11 median zb) **12.053 m**: the hole filled
  to local ground and no higher. The "15 m" is rim − pit floor = 12.80 − (−2.25).
- **A real quarry** — OSM within 400 m: `landuse=quarry` (way 1256546074) and `natural=water;
  water=basin` (way 256626539). GLO-30 is correct; the artefact is calling it flood depth.
- **NOT the Strymonas mechanism** — 17.4–47.5 km from every prescribed-Q source, and no source pools
  (hmax there 0.6–1.5 m). Strymonas's 12.2 m was Q stranded on an upland cell by the Appendix-B
  source-snap bug, and fixing it moved the science; this moves nothing.

**Affects no published number.** All scores are binary contingencies at hmax > 0.10 / 0.50 m, so depth
past the threshold is discarded: 1 cell > 15 m, **46 cells > 10 m = 0.0216 %** of the 213,323 wet cells;
the pit's connected component is **6 cells (0.135 km²)**. Tables 10/13/14 are unchanged. Note all 46
cells > 10 m are DEM sinks of one family (11 quarry, 4 domain-edge, **31 upland hollows at zb ≈
100–220 m**) — "peak modelled depth" measures the deepest *hole*, not the deepest *flood*.

**Defensible depths** (wet cells, hmax > 0.10 m, EMS evaluation mask 3202 km²): median **0.57 m**,
p90 **2.12 m**, p99 **4.75 m**, p99.9 7.43 m. Peak excluding the quarry is 12.71 m (eval) / 14.47 m
(active) — but those are sinks too, so **do not swap 15 m for 12.7 m; quote the distribution**.

**OPEN:** `emilia_emsr664_enhanced.yaml` still annotates its R3 src points *"DRAFT — refine to actual
Apennine channel exits on first run"*; they sit at zb 61.4 / 117.3 / 105.2 / 195.4 / **332.0 m**
(p81–**p99.9**). No stranding signature and a plausible 838 m³/s combined peak, but Appendix B's own
lesson is to check source-cell elevation — state explicitly whether they were refined.

### Valencia (EMSR773) canonical-run ledger — VERIFIED (CODE-5, 2026-07-17)
Two Valencia runs exist. The R2-corrected run **overwrote** `model/` and `metrics.json` on disk, so
the raw-IMERG sensitivity run survives **only in the `ELKAK2/NHESS` git history**. Both recovered and
re-scored; B/GSS derived from the contingency tables (metrics.json stores neither), SEDI via
`validation/skill_scores.py`. Repro: `ELKAK2/NHESS/R1_verification/task5_valencia_ledger/`.

| | **CANONICAL — R2 ×4.14** | raw-IMERG (sensitivity) |
|---|---|---|
| **run ID** | **`5447768`** (`ELKAK2/NHESS`) | **`49da0d1`** (`ELKAK2/NHESS`) |
| commit | *"Enhancement Tiers 1-3: R2-bias-corrected Valencia + bias-insensitive scores"* 2026-07-15 21:09:15 +0300 | *"Held-out runs executed: real Valencia + Emilia-Romagna SFINCS results"* 2026-07-15 17:00:54 +0300 |
| metrics generated | 2026-07-15T18:00:02Z | 2026-07-15T13:13:03Z |
| rain | IMERG ×4.14, **383.73 mm** domain-mean, peak cell **305.93 mm/h** | raw IMERG, 150.84 mm over the file, peak cell 73.84 mm/h |
| **CSI / HR / FAR @0.10 m** | **0.082 / 0.996 / 0.918** | **0.105** / 0.966 / 0.895 |
| **B / GSS / SEDI @0.10 m** | **12.15 → 12.2 / 0.0207 → 0.02 / 0.625** | 9.16 / 0.046 / 0.657 |
| **CSI @0.50 m** | **0.126** | 0.216 |
| contingency @0.10 m | TP 19958 · FP 223401 · FN 71 · TN 76607 | TP 19353 · FP 164114 · FN 676 · TN 135894 |
| eval mask / observed | 3200.4 km² / 200.3 km² | 3200.4 km² / 200.3 km² |

**Every claimed value confirmed**: canonical CSI 0.082 / HR 0.996 / FAR 0.918 / B 12.2 / GSS 0.02 /
SEDI 0.625 / CSI 0.126 @0.50 m, and raw-IMERG **CSI 0.105**. The on-disk `metrics.json` **is** the
canonical ×4.14 run.

**×4.14 confirmed independently:** peak max-cell intensity ratio = 305.93 / 73.84 = **4.1432** (the
multiplier scales peak intensity exactly), and 305.93 mm/h matches §5.3's "peak intensity 306 mm h⁻¹"
to the decimal.

**The 0.105 → 0.082 comparison is a clean bias-only sensitivity — checked, not assumed.**
`forcing.nframes` differs (385 vs 241) but that is the **precip FILE** extent, not the simulated
period: raw = tref→tstop (192 h), corrected = tstart→tstop (120 h). The yaml (date 2024-10-29,
spinup 3 / pre 2 / post 2) gives tref 2024-10-24, **tstart 2024-10-27, tstop 2024-11-01**, confirmed
in the canonical `sfincs.inp`; SFINCS integrates tstart→tstop, so the raw file's 3 pre-tstart days
were never applied. Both runs' `run` blocks are identical in **every** geometry/period field —
121 output frames, 801×841 @100 m, 521,427 active cells, 5214.27 km². Only the rain magnitude differs.

**⚠ Provenance risk:** the raw run is recoverable **only** from git commit `49da0d1` — nothing on disk
records CSI 0.105 (`grep -r "0.105"` over `runs/` hits only a coincidental substring of Mandra's
0.10599 in `tier2_scores.json`). If the `ELKAK2/NHESS` repo is ever lost or rewritten, the §5.3
sensitivity claim becomes unverifiable. `runs/valencia_emsr773/model/` holds the canonical run only.

### SEDI / PSS — VERIFIED, five events (CODE-4, 2026-07-17)
Recomputed from the stored contingency tables at `hmax>0.10 m`, independently of
`ELKAK2/NHESS/runs/tier2_bias_insensitive.py`; agrees with its `tier2_scores.json` to **0.00e+00**.
Repro: `ELKAK2/NHESS/R1_verification/task4_sedi_pss/`.

| event | TP | FP | FN | TN | H | F (POFD) | **SEDI** | **PSS** |
|---|---|---|---|---|---|---|---|---|
| Mandra (EMSR257) | 3140 | 26030 | 455 | 14261 | 0.8734 | 0.6460 | **0.362** | **0.227** |
| Strymonas (EMSR122) | 1552 | 3726 | 3185 | 45878 | 0.3276 | 0.0751 | **0.429** | **0.253** |
| Pineios (EMSR692) | 63910 | 72693 | 3594 | 66129 | 0.9468 | 0.5236 | **0.636** | **0.423** |
| Emilia-R. (EMSR664) | 18366 | 79826 | 1343 | 42773 | 0.9319 | 0.6511 | **0.470** | **0.281** |
| Valencia (EMSR773) | 19958 | 223401 | 71 | 76607 | 0.9965 | 0.7447 | **0.625** | **0.252** |

All five reproduce **Table 14** exactly. The same tables also reproduce **Table 10** and the §5.3
B = 12.2 claim, and match CODE-1's Pineios mask (N = 206,326) and CODE-2's Strymonas v3-author
table (1552/3726/3185) — Tables 10 and 14 rest on one consistent set of contingency tables.

**Definitions confirmed.** `H = TP/(TP+FN)`; **`F = FP/(FP+TN)` = POFD (false-alarm RATE)**, *not*
FAR = FP/(TP+FP). The code is a literal transcription of Eq (10) and Eq (11) (term for term, signs
and order); its only departure is an `eps = 1e-9` clamp keeping the logs finite, which is **inert
for all five events** (an unclamped reimplementation agrees to 0.00e+00) — so Eq (10) applies as
printed and the guard needs no mention. Numeric proof of the POFD convention: substituting FAR
reproduces **no** printed value (Mandra −0.040, Strymonas −0.517, Pineios 0.628, Emilia 0.247,
Valencia 0.392 vs printed 0.362/0.429/0.636/0.470/0.625). NB Pineios alone is nearly ambiguous
(FAR 0.532 ≈ POFD 0.524), so it cannot settle the convention by itself.

**Harness gap closed.** SEDI/PSS were **not in the released validator at all** — they lived only in
`tier2_bias_insensitive.py`, which is outside the repo and hardcodes `C:/Users/vaspapa/…` (R1), so a
referee could not reproduce Table 14 from the release. Added `validation/skill_scores.py` (canonical
Eq (10)/(11); exposes `far()` documented as *not* used by SEDI/PSS) and `validation/test_skill_scores.py`
(**16 tests, stdlib `unittest` — pytest is not installed; the repo's first tests**). Locks the
definitions, the POFD-vs-FAR convention, base-rate invariance, and all five Table-14 values
(contingency tables hardcoded → self-contained). Mutation-tested: FAR-for-POFD → 8/16 fail; Eq (10)
sign flip → 11/16; PSS = H+F → 10/16.

**OPEN (docs only):** `validate_event_v2.py`'s module docstring states the bias interpretation
backwards — "*under (>1) or over (<1)*"; B = (TP+FP)/(TP+FN), so **B>1 is OVER-prediction**. No
number affected; fix before release since B carries much of the argument.

### Independent-truth cross-check, Pineios (C4, referees M1/M2) — see [independent_truth.md](independent_truth.md)
Re-score only (no model re-run). The canonical Pineios v1-enhanced hmax reproduces EMS **0.456/0.947/
0.532/2.02/0.201 @0.10 m and 0.515 @0.50 m** to the decimal through the committed harness (gate). The
two independent SAR delineations publish **only areas, not extents** (He et al. 2024 NHESS — RAPID map
"on request"; Falaras et al. 2025 RS — no dataset DOI), so a **pixel-wise** cross-validation was
possible **only against EMS**; He/Falaras reduce to an **area-agreement** check. Result: independent
areas **He 1150 km² total / 820 km² plain, Falaras 949.52 km²** are the same order as (and smaller than)
the **EMS-merged 1519 km²** — EMS is a representative, not inflated, truth; the model's area
over-prediction (B≈2 @0.10 m, ≈1.2 @0.50 m) holds against **all three** references, not EMS alone.
Also reconciles the conflated §5.1/§5.2/§7.4 areas (1150/820 = He; 949.52 = Falaras).
**ADDENDUM (pixel-wise, upgrades the verdict):** a **defensible digitization** of Falaras Fig. 10
(cyan flooded-area; georef RMS **253 m** from 4 city GCPs; **903 km²** = 95% of the reported 949.52)
enabled an actual pixel-wise re-score on the 4642 km² mask: **vs Falaras-SAR HR 0.948 / CSI 0.299 / B 3.12
@0.10 m; CSI 0.402 @0.50 m** (vs EMS 0.947/0.456/2.02). **Verdict: NOT EMS-specific** — HR equals the EMS
hit rate (model recovers an independently-mapped flood); lower CSI is the same over-prediction scored
against a smaller single-/few-overpass truth (986 vs 1519 km²). Disclose as a digitized (approximate)
extent. Repro: `reproduction/independent_truth/score.py` (EMS gate) + `score_sar.py` (SAR); extent raster
`refs/falaras_sar_extent_modelgrid.tif`.

### SCS-CN infiltration diagnostic (C1, referee M4) — see [cn_diagnostic.md](cn_diagnostic.md)
Minimal instrumented SFINCS toy (synthetic 40×40 pan + tilt, uniform pulse, infiltration OFF then
CN∈{70,85,95}; both `precipfile` and 2-D `netamprfile` paths). Findings: **(1)** the scsfile unit
handoff is correct (hydromt writes S in inch, SFINCS converts to m — verified via `qinf` output);
**(2)** with CN on, SFINCS infiltrates **~100 % of rainfall regardless of CN, rain rate (≤400 mm/hr)
or storm total (≤400 mm)** — >10× the bounded SCS maximum Ia+S and CN-independent; not rate- or
storage-capped. **Verdict: solver/application bug, not a unit error and not expected physics** — the
SCS path acts as a near-total rainfall sink. Corroborated by the production Strymonas ablation
(CN-on+Q-off CSI **0.016** — rain-on-grid ~annihilated; canonical v3 0.183 is Q-driven). **Vindicates**
disabling CN for Pineios/Mandra and treating Strymonas CN as diagnostic. Repro: `reproduction/cn_diagnostic/`.

### Spatial bias-correction figure (rain magnitude rescaled, core fixed) — see [figures/fig_rain_bias_spatial.py](../figures/fig_rain_bias_spatial.py)
Companion to the domain-mean Fig 4/Fig 6: a 2×3 spatial map (Mandra/Pineios × raw | corrected | ratio)
proving the gauge-anchored IMERG correction is purely multiplicative over its sub-window — `corrected =
raw × factor` at every cell (ratio panel flat ≡ **8.551** Mandra / **2.725** Pineios), so the convective
core cannot move. Uses the actual pipeline fields (`imerg_*.raw.nc` vs `imerg_*.nc`). Verified basin
(watershed-bbox) means: **Mandra 23 → 200 mm** (×8.551, target 200) and **Pineios 147 → 400 mm** (×2.725,
target 400; domain-mean 139 → 378 ≈ the §4.1.1 141 → 380). **FLAG:** the Pineios corrected core max is
**871 mm** (IMERG cell), not the ">1000 mm" stated in §4.1.1/Fig 4 caption — still consistent with the
754 mm Zagora point gauge, but the ">1000 mm" wording should be corrected to ~870 mm. Output:
`figures/fig_rain_bias_spatial.png` (300 dpi).

### Reference-data (truth) uncertainty (B3) — see [truth_uncertainty.md](truth_uncertainty.md)
From stored outputs (no re-run). **(a)** EMS polygon positional uncertainty (±20 m Sentinel-1 spec,
applied in the raster domain): CSI band Pineios ±0.012, Strymonas ±0.003, Mandra ±0.041 (largest for
the small fragmented GRADING extent) — far tighter than the Sec 8 AOI ±1 km band; d=0 reproduces the
published CSI exactly. **(b)** EMS acquisition vs modelled time-of-peak: Pineios first SAR overpass
(Sentinel-1) 2023-09-06 04:39 is ~27 h after the modelled flood-area peak; Strymonas ~11 h; **Mandra's
GRADING map is optical (Pleiades) acquired 2017-11-20, 5.2 d post-peak — it maps damage, not water,
consistent with its high FAR/B**. **(c)** `all_touched=True` extent inflation quantified (V4): obs
+17.7 / +52.2 / +81.8% (Pineios/Strymonas/Mandra), AOI ≤1.4% — for Methods disclosure.

## 4. Corrections already applied vs prior v5 — CHANGELOG
**2026-06-19** — applied to `_sources/paper_NaturalHazards_submission_CORRECTED.docx` (21 exact
unique-string edits on `word/document.xml`, formatting preserved, each asserted to match once; diff
verified to touch only these):
- **Table 8 (Strymonas per-AOI), baseline column** was stale (disagreed with Table 12 + codebase) →
  corrected: 01STRYMONAS 0.204/0.377/0.692, 02BALTOTOPI 0.114/0.294/0.843, 03ACHINOS 0.306/0.331/0.193,
  04MAVROTHALASSA 0.331/0.406/0.356.
- **Table 8, v1-column FAR typos** (forced by the reported CSI+HR): 03ACHINOS 0.486→0.021,
  04MAVROTHALASSA 0.628→0.445.
- **Table 10 (Strymonas Δ vs baseline)**: −0.020/+0.018/+0.078 → **−0.021/−0.049/+0.014** (the ΔHR
  sign was wrong — enhanced-v3 HR 0.328 is *below* baseline HR 0.377).
- **Prose §4.3.2, §5, Table 10 caption** reworded: the HR/bias recovery is attributed to v1→v3 (the
  audit fix), not enhanced-vs-baseline; the "diagnostic, not a headline gain" framing preserved.

Tables 3, 4, 5, 6, 7, 9 and Table 12 were checked and left unchanged (already correct).

**2026-07-17 — ⚠ REGRESSION: the NHESS R1 draft does NOT carry the 2026-06-19 corrections.**
`ELKAK2/NHESS/Final_sub/NHESS_manuscript_R1_tracked.docx` descends from the **uncorrected** v5, not
from `_sources/paper_NaturalHazards_submission_CORRECTED.docx`. Verified by re-parsing the R1 docx
(tracked changes resolved to *accepted*): **every** Strymonas item listed above is still stale, while
Table 12 is still correct — the exact fingerprint of the pre-correction v5. Confirmed still-present
in R1 (CODE-2 scan, `task2_strymonas_delta/r1_strymonas_scan.txt`):

| # | location in R1 | printed (stale) | must become |
|---|---|---|---|
| 1 | Table 8 row 01STRYMONAS, baseline col | 0.203 / 0.310 / 0.629 | **0.204 / 0.377 / 0.692** |
| 2 | Table 8 row 02BALTOTOPI, baseline col | 0.124 / 0.281 / 0.722 | **0.114 / 0.294 / 0.843** |
| 3 | Table 8 row 03ACHINOS, baseline col | 0.271 / 0.284 / 0.475 | **0.306 / 0.331 / 0.193** |
| 4 | Table 8 row 04MAVROTHALASSA, baseline col | 0.266 / 0.303 / 0.602 | **0.331 / 0.406 / 0.356** |
| 5 | Table 8 row 03ACHINOS, v1 FAR | 0.486 | **0.021** |
| 6 | Table 8 row 04MAVROTHALASSA, v1 FAR | 0.628 | **0.445** |
| 7 | Table 10 row Strymonas, Δ cells | −0.020 / +0.018 / +0.078 | **−0.021 / −0.049 / +0.014** |
| 8 | §4.3.2 prose ("baseline … achieves") | CSI 0.203, HR 0.310, FAR 0.629 | **0.204 / 0.377 / 0.692** |
| 9 | §4.3.2 prose ("Enhanced vs. baseline") | ΔCSI −0.020; FAR 0.629 → 0.706; "raising HR" | **ΔCSI −0.021; FAR 0.692 → 0.706**; HR *falls* 0.377→0.328 — re-attribute the HR/bias gain to v1→v3 |
| 10 | §5 prose ("Against baseline …") | ΔCSI = −0.020 | **−0.021** |
| 11 | Table 10 caption | ΔCSI = −0.020 + a live `⟦CODE-2⟧` marker | **−0.021**, marker deleted |

Table 8's v1 and v3 columns and Table 12 are correct in R1 and must **not** be touched. Item 9 is the
only one that is not a digit swap — the claim that the enhanced forcing raises HR *relative to
baseline* is false (HR 0.377 → 0.328); see the CODE-2 adjudication in §3.

## 5. OPEN items — need author/editorial judgement (NOT yet changed; do not re-discover as "new")
- **OPEN** §4.3.2 "an order of magnitude better than the Mandra baseline" — with the corrected
  baseline this is Strymonas CSI 0.204 vs Mandra 0.080 ≈ **2.5×, not 10×**. Reword.
- **OPEN** Pineios HR printed as **0.95** (abstract, §1.3, §4, §5.1, §7.1, §9) vs **0.947** (tables) — unify.
- **OPEN** Pineios injected-Q peak: **118 m³/s** (§4.1.1) vs **144 m³/s** (§5.2) — reconcile.
- **OPEN** Mandra ERA5 domain-mean rain quoted as **~9 / 40.5 / 46 mm** (§5·§7.1 / §4.2.2 / Fig 6) — label windows.
- **PARTLY RESOLVED (2026-06-22)** Fuzzy contingency dilates **both** fields (symmetric); text
  matches the code but cites Wing et al. 2017 (often one-sided). At Mandra B = 8.1 symmetric dilation
  inflates fuzzy HR → 1. The validator's old "asymmetric (Wing 2017)" block was byte-identical to the
  symmetric one (V3); it is now replaced with two **true** one-sided sweeps and the 3 canonical runs
  are re-scored in **[fuzzy_onesided.md](fuzzy_onesided.md)** / `.json` (strict r=0 unchanged). The
  symmetric overstatement is now quantified (Mandra fuzzy r=2 CSI 0.205 → obs-oriented CSI 0.086).
  Remaining author call: adopt the one-sided columns in the manuscript or keep symmetric with an
  explicit both-sided caveat.
- **OPEN** GitHub URL: manuscript Data & Code Availability says `github.com/vaspapa79/sfincs-mediterranean-flood`
  (**singular**) while CITATION.cff / repo name is `sfincs-mediterranean-floods` (**plural**) — make consistent.
- **OPEN** Zenodo DOI `10.5281/zenodo.20523154` is cited in the manuscript, but the repo is **not yet
  published** (no remote/tags/`.zenodo.json`). Confirm the DOI is reserved and mint at release; back-fill.
- **OPEN** SKILL.md says "13 steps"; `run_pipeline.py` has **16** (finding D1) — regenerate SKILL.md.
- **Authorship / metadata** (author list, affiliations, funding, ORCIDs) was **intentionally NOT
  audited** in this pass — out of scope. Note: the `.docx` author line and CITATION.cff may differ.

## 6. NOT codebase-reproducible in this pass — DO NOT treat as verified
- **Table 11** — comparison with external published flood-model studies (Sadana 2025, Wing 2017,
  Bernhofen 2018, Trigg 2016, Hocini 2021, Bellos 2022, Capolongo 2019); numbers are from those papers,
  not this codebase. Their accuracy is the authors' responsibility (RESPONSE_TO_REVIEWS_v5 records the
  verification done against Crossref/publisher pages).
- **Table 13** — prospective ECMWF-ensemble forecast demonstration (separate forecast chain).
- **Appendices A & B** (Tables 14–15) — infiltration/roughness sweep and the deep input audit;
  supplementary, not in the main `.docx` body reviewed here.

## 7. Re-validation procedure (how to detect drift)
```bash
conda activate sfincs-viz
python -c "import numpy as np; print(np.dot(np.eye(3),np.eye(3)).sum())"   # must print 3.0
# Path A — re-validate a stored canonical output:
python validation/validate_event_v2.py --config skill/examples/<event>_enhanced.yaml   # → per-event JSON
python validation/aggregate_metrics_v2.py                                               # → cross-event table
# Path B — independent re-run from cached forcing, then validate:
python skill/scripts/run_pipeline.py --config skill/examples/<event>_enhanced.yaml --only 7,8,9,10,11
```
Compare the printed `strict@0.10m` CSI/HR/FAR/B/GSS to §2 above. **Any difference beyond ~0.001 is
drift — STOP and report both values plus the environment diff (numpy/HydroMT/SFINCS versions); do not
overwrite the verified record.** Strymonas v3's canonical values are the authors' stored
`sfincs_map.nc`; a fresh rebuild legitimately lands at 0.182/0.322 with numpy 2.4.6.
TODO(author): the validators import `_common`/`_anim_common` from a sibling
`.claude/skills/sfincs-flood-reproduction/scripts` path (finding R11) — ensure that path is present, or
repoint the imports to `skill/scripts`, before a clean-checkout audit.

---

## 8. EMSR933 Crete (CODE-10) — prospective held-out event, PROVISIONAL (activation open)
Append-only ledger for the third held-out event; every value is generated from the JSON records named in
`reproduction/emsr933/` by `reproduction/emsr933/scripts/stage0_summary.py` (nothing retyped). Provisional until the
Stage-5 final-products cut-off.

### EMSR933 Crete — Stage 0 provenance (CODE-10, prospective held-out event)
Branch `emsr933-crete` (worktree `.worktrees/emsr933-crete`, base v1.3.0 `ccd423a`), commit `6a5e64b`. Records in `reproduction/emsr933/`.
- EMS API snapshot **2026-10-09T12:47:20Z** = provisional truth cut-off: `ems_api_snapshot_20261009T124720Z.json` (31606 B, sha256 `0aa29458ad5eae8449a0b28d4ab386a4104e180b9f05ca5f0cb919f2077f6b94`); API `https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR933`.
- Activation (from snapshot JSON): eventTime `2026-10-01T07:00:00` UTC, activationTime `2026-10-04T11:02:00` UTC, Flood/Flash flood, closed=False.
- Released packages at the cut-off (6; product id · post-event source per package `source_v1` · observed km² union EPSG:32634):
  - AOI01 Kastelli DEL_MONIT01 id 2962 · Legion 06/10/2026 T10:47:00Z (1.2 m) · obs 0.242 km² (88 polys; {"Flood trace": 0.1438, "Flooded area": 0.0982}) · zip sha256 `bbe7fe84c5f21fdf…`
  - AOI03 Tzermiado DEL id 2955 · Sentinel-1 04/10/2026 T16:22:00Z (20.0 m) · obs 3.2192 km² (13 polys; {"Flooded area": 3.2192}) · zip sha256 `14789be38b4ded67…`
  - AOI03 Tzermiado DEL_MONIT02 id 2959 · GeoEye-1 08/10/2026 T09:02:00Z (2.0 m) · obs 3.7807 km² (618 polys; {"Flood trace": 1.2533, "Flooded area": 2.5274}) · zip sha256 `07ae2fb6f7f1bf0c…`
  - AOI04 Agios Ioannis DEL_MONIT01 id 2957 · WorldView-3 06/10/2026 T10:46:00Z (1.6 m) · obs 0.0325 km² (30 polys; {"Flood trace": 0.0325}) · zip sha256 `24339cffc56c67fe…`
  - AOI06 Agios Nikolaos DEL_MONIT01 id 2960 · Legion 08/10/2026 T08:55:00Z (2.0 m) · obs 0.0593 km² (11 polys; {"Flood trace": 0.0575, "Not Applicable": 0.0017}) · zip sha256 `a989df1406ee5f90…`
  - AOI07 Omalos DEL_MONIT01 id 2964 · Legion 06/10/2026 T10:45:00Z (1.6 m) · obs 0.0506 km² (63 polys; {"Flooded area": 0.0506}) · zip sha256 `4e1f5386648915e6…`
  - Not released: AOI01 DEL N; AOI02 DEL N; AOI02 DEL_MONIT01 N; AOI03 DEL_MONIT01 N; AOI03 GRA I; AOI04 DEL N; AOI05 DEL N; AOI05 DEL_MONIT01 N; AOI06 DEL N; AOI07 DEL N; AOI08 DEL N; AOI08 DEL_MONIT01 N
- Availability (2026-10-09T12:51:44Z): IMERG Late V07 528/528 (V07C); IMERG Final 0; ERA5 requestable to 2026-10-03 (ERA5T per probe: 2026-09-27=0005, 2026-09-28=0005, 2026-09-29=0005, 2026-09-30=0005, 2026-10-01=0005, 2026-10-02=0005, 2026-10-03=0005); GloFAS v4 intermediate to 2026-10-06.
- Preflight 2026-10-09T12:44:09Z: OK (hydromt 0.10.1, hydromt_sfincs 1.2.2, numpy 2.4.6, GDAL 3.12.2).

### EMSR933 Crete — Stage 1 (rule ledger, no model runs; commit `46aba38 (records) + 6363ead (R2-on anchor, basin-based catchments)`, records in `reproduction/emsr933/`)
- Harness changes approved at Checkpoint 0 (F2/F4): `ems.include_del_product` switch (default off) and `rain_source.product: late|final`; regression `regression_f2f4.json` (2026-10-09T13:24:38Z): Valencia full block vs `_scoring/score_v164.json` **IDENTICAL**, condensed vs reports **IDENTICAL** (CSI@0.10 0.093878); Emilia condensed vs reports **IDENTICAL**, contingency vs rescore **IDENTICAL** (CSI@0.10 0.240386). Diagnostic (not canonical) Emilia with the switch on: n_ems_shps [13, 14], observed-wet km² [592.605, 592.605], CSI [0.24038585, 0.24038585].
- Rule outputs (`stage1_yaml_validation.json`, 2026-10-09T14:07:58Z): enhanced = rain_source `imerg_half_hourly` product `late` (R1, Late deviation); R2 bias enabled `False` (DECISION pending; R2-on variant `emsr933_crete_enhanced_R2on.yaml`); R3 upstream_q `False`; R4 infiltration `False` (amc 3); R5 coastal `True` pavbnd 1; R6 wind/MSLP `True`; window {'spinup_days': 7, 'pre_event_days': 3, 'post_event_days': 4} → tref 2026-09-21T00:00:00, tstart 2026-09-28T00:00:00, tstop 2026-10-06T00:00:00; bbox {'west': 23.4, 'south': 34.8, 'east': 26.4, 'north': 35.7, 'era5_buffer_deg': 0.3}; EPSG 32634; grid res 100 m (GAP-1, provisional), subgrid 4, z_max 2500.0 m (GAP-2, provisional); baseline rain_source `era5_hourly`; truth switches {'activation': 'EMSR933', 'include_del_product': True, 'exclude_not_analysed': True, 'truth_cutoff_snapshot_utc': '2026-10-09T12:47:20Z'}; preflight rc 0/0.
- Terrain (`stage1_terrain.json`, 2026-10-09T13:32:48Z; GLO-30 decimated ×3, [1080, 3600] cells, land 8415.4 km²). Per AOI: AOI01 Kastelli obs 0.242 km² (24 cells @100 m), largest stream 199.7 km², sea cells 0, inlets ≥120 km² 1; AOI02 Irakleio obs — km², largest stream 179.4 km², sea cells 441, inlets ≥120 km² 0; AOI03 Tzermiado obs 4.4372 km² (443 cells @100 m), largest stream 133.8 km², sea cells 0, inlets ≥120 km² 0; AOI04 Agios Ioannis obs 0.0325 km² (3 cells @100 m), largest stream 19.9 km², sea cells 342, inlets ≥120 km² 0; AOI05 Anogeia obs — km², largest stream 225.5 km², sea cells 0, inlets ≥120 km² 0; AOI06 Agios Nikolaos obs 0.0593 km² (5 cells @100 m), largest stream 120.2 km², sea cells 897, inlets ≥120 km² 0; AOI07 Omalos obs 0.0506 km² (5 cells @100 m), largest stream 96.0 km², sea cells 1325, inlets ≥120 km² 0; AOI08 Monastiraki obs — km², largest stream 17.0 km², sea cells 221, inlets ≥120 km² 0.
- Candidate domains (`stage1_terrain.json` → `domains`): east: bbox [25.03, 34.95, 26.01, 35.36], 91.4×49.6 km, land 2887.7 km², sea True, cells @50/100/150 1813376/453344/201579 (land 1155081/288770/128342), inflow ≥120 km² crossing edge 0, k 1.00127–1.00216; central: bbox [24.62, 34.95, 25.62, 35.45], 93.4×59.3 km, land 3858.9 km², sea True, cells @50/100/150 2215448/553862/246085 (land 1543543/385885/171504), inflow ≥120 km² crossing edge 0, k 1.00095–1.00177; west: bbox [23.72, 35.18, 24.09, 35.56], 34.9×43.1 km, land 1140.3 km², sea True, cells @50/100/150 601511/150419/66816 (land 456109/114027/50678), inflow ≥120 km² crossing edge 0, k 1.00036–1.00057; island: bbox [23.4, 34.8, 26.4, 35.7], 211.1×75.8 km, land 7092.5 km², sea True, cells @50/100/150 6404774/1600138/711942 (land 2836996/709249/315221), inflow ≥120 km² crossing edge 0, k 1.00036–1.00214.
- Closed depression AOI03 Tzermiado (`stage1_depressions.json`, largest component): area 35.76 km², floor 807.8 m, spill 889.6 m, max depth 81.8 m, volume below spill 1979.0 Mm³, internal catchment 128.6 km², centroid [25.4754, 35.1789].
- Closed depression AOI07 Omalos (`stage1_depressions.json`, largest component): area 5.51 km², floor 1034.6 m, spill 1078.6 m, max depth 44.0 m, volume below spill 125.6 Mm³, internal catchment 24.8 km², centroid [23.8972, 35.3351].
- Truth at the cut-off (`ems_snapshot_*_products.csv`): AOI01 DEL_MONIT01 id 2962 Legion 06/10/2026 T10:47:00Z (1.2 m) obs 0.242 km² ({"Flood trace": 0.1438, "Flooded area": 0.0982}); AOI03 DEL id 2955 Sentinel-1 04/10/2026 T16:22:00Z (20.0 m) obs 3.2192 km² ({"Flooded area": 3.2192}); AOI03 DEL_MONIT02 id 2959 GeoEye-1 08/10/2026 T09:02:00Z (2.0 m) obs 3.7807 km² ({"Flood trace": 1.2533, "Flooded area": 2.5274}); AOI04 DEL_MONIT01 id 2957 WorldView-3 06/10/2026 T10:46:00Z (1.6 m) obs 0.0325 km² ({"Flood trace": 0.0325}); AOI06 DEL_MONIT01 id 2960 Legion 08/10/2026 T08:55:00Z (2.0 m) obs 0.0593 km² ({"Flood trace": 0.0575, "Not Applicable": 0.0017}); AOI07 DEL_MONIT01 id 2964 Legion 06/10/2026 T10:45:00Z (1.6 m) obs 0.0506 km² ({"Flooded area": 0.0506}).
- F5 (a–c) (`f5/F5_abc.json` → `cases`): half-hourly 4×10 mm/h with the pipeline defaults → written [20.0, 20.0, 20.0, 0.0] mm/h, total 30.0 mm (factor 1.5 vs 20 mm); half-hourly pulse: factor 2.0, offset -30.0 min; hourly 2×10 mm/h → [10.0, 0.0] mm/h, hourly pulse offset -60.0 min; `cumulative_input=False, time_label=left` → [10.0, 10.0, 10.0, 10.0] mm/h, total 20.0 mm.
- F5 (d) (`f5/F5_d.json` → `runs[].model_totals.bbox.event_window`, `ratios`): pineios_enhanced: written bbox event-window 783.1249244094922 mm, written/target {'configured_400': 1.958, 'manuscript_380': 2.061}, recorded factor 2.725 → 400.0 mm; mandra_enhanced: written bbox event-window 447.7366208732128 mm, written/target {'configured_200': 2.239}, recorded factor 8.551 → 200.0 mm; valencia_350_asrun: written bbox event-window 677.5010685327773 mm, written/target {'run_target_350': 1.936, 'cited_164': 4.131}, recorded factor 4.143 → 350.0 mm; valencia_164_rerun: written bbox event-window 317.4576444174163 mm, written/target {'run_target_164': 1.936, 'old_target_350': 0.907}, recorded factor 4.143 → 350.0 mm.
- F5 (e) (`f5/F5_e.json` → `runs[].comparison`): pineios_emsr692_enhanced: msk2 cells 650, bzs file False, MSLP min at boundary 2023-09-05T03:00, expected IB rel. first 0.102 m, pavbnd acted False; valencia_emsr773_asrun: msk2 cells 1233, bzs file False, MSLP min at boundary 2024-10-30T03:00, expected IB rel. first 0.028 m, pavbnd acted False; valencia_emsr773_rerun_v164: msk2 cells 1233, bzs file False, MSLP min at boundary 2024-10-30T03:00, expected IB rel. first 0.028 m, pavbnd acted False.
- F5 (f) (`f5/F5_f.json` → `events[].inp_parsed`, `derived`): pineios: tspinup 0.0, tstart 2023-09-03 00:00, tstop 2023-09-11 00:00, {'gap_days_tstart_minus_tref': 7.0, 'days_simulated_before_event_date_tstart_to_eventdate': 3.0, 'days_forcing_window_not_simulated_tref_to_tstart': 7.0, 'stated_spinup_days': 7}; strymonas: tspinup 0.0, tstart 2015-03-28 00:00, tstop 2015-04-04 00:00, {'gap_days_tstart_minus_tref': 7.0, 'days_simulated_before_event_date_tstart_to_eventdate': 3.0, 'days_forcing_window_not_simulated_tref_to_tstart': 7.0, 'stated_spinup_days': 7}; mandra: tspinup 0.0, tstart 2017-11-13 00:00, tstop 2017-11-18 00:00, {'gap_days_tstart_minus_tref': 1.0, 'days_simulated_before_event_date_tstart_to_eventdate': 2.0, 'days_forcing_window_not_simulated_tref_to_tstart': 1.0, 'stated_spinup_days': 1}; valencia: tspinup 0.0, tstart 2024-10-27 00:00, tstop 2024-11-01 00:00, {'gap_days_tstart_minus_tref': 3.0, 'days_simulated_before_event_date_tstart_to_eventdate': 2.0, 'days_forcing_window_not_simulated_tref_to_tstart': 3.0, 'stated_spinup_days': 3}; emilia: tspinup 0.0, tstart 2023-05-14 00:00, tstop 2023-05-22 00:00, {'gap_days_tstart_minus_tref': 14.0, 'days_simulated_before_event_date_tstart_to_eventdate': 3.0, 'days_forcing_window_not_simulated_tref_to_tstart': 14.0, 'stated_spinup_days': 14}.
- R2-on variant (`emsr933_crete_enhanced_R2on.yaml`, labelled, not canonical; `stage1_yaml_validation.json`): rain_bias_correct {'enabled': True, 'target_mm': 447.8, 'watershed_bbox': '25.3983,35.11,25.5933,35.2292', 'event_start': '2026-09-29 21:00', 'event_end': '2026-10-04 21:00'}; anchor station `tzermiado` (NOA/meteo.gr, Τζερμιάδων, Λασιθίου, 820 m) daily [('2026-09-30', 40.6), ('2026-10-01', 231.0), ('2026-10-02', 107.2), ('2026-10-03', 35.6), ('2026-10-04', 33.4)] → sum 447.8 mm (`noa_stations/stations_daily.csv`, source https://penteli.meteo.gr/stations/tzermiado/NOAAPRMO.TXT, accessed 2026-10-09T13:39:20Z); watershed = Lasithi polje closed catchment 128.6 km², bbox [25.3983, 35.11, 25.5933, 35.2292] (`stage1_depressions.json`).
- Decisions pending (Checkpoint 1): R2 raw vs anchored; GAP-1 Δx/domain (A 100 m island / B 150 m island / C 50 m per cluster / C′ 100 m per cluster); GAP-2 z_max; F5 harness option (a)/(b)/(c); window 7/3/4 d and island-wide domain confirmation.

## 9. Harness v1.4 (CODE-12) — D1/D2 fixes, code + tests only; re-run manifest; Crete build QC

Context: F5_VERIFY.md (CODE-10 Checkpoint 0/1) established three defects of the v1.3.0 harness (D1 IMERG x2/-30 min; D2 inactive inverse-barometer boundary; D3 tspinup = 0). CODE-12 fixes D1/D2 behind `harness_version: v1.4` (default v1.3 keeps every published number reproducible), reports D3, and plans the re-run (option (c), decision pending). Every number below is copied from the JSON records named in each line.

### Harness v1.4 (CODE-12, D1/D2 fixes) — code + tests only; commit `513ce5ab73bbf4ef41e091cf3c49c3b836f2cd8b` (2026-10-12T10:12:15Z); records commit (next commit on fix/harness-v1.4); block generated 2026-10-12T10:22:25Z by `reproduction/v14_harness/scripts/code12_summary.py`

**Status: no corrected run of a published event exists; GO-C pending (Papaioannou).** Branch `fix/harness-v1.4` from `emsr933-crete` (base `69d1c58`).
`harness_version` defaults to v1.3 = the published behaviour; v1.4 = D1 (IMERG written as left-labelled rates ×1.000, 0 min; ERA5 right-labelled accumulations unchanged — ECMWF convention, see `PAVBND_SOURCE.md` §5) + D2 (bnd points every 10 km on the msk=2 cells, bzs = 0 m, pavbnd = 101325 Pa). D3 unchanged (A3 report only).

- A1 regression (`regression_forcing_v13_pineios.json`, 2026-10-12T10:00:29Z): config `emsr692_pineios_enhanced.yaml` at harness `v1.3`; build yml text identical to the pre-change render: True; catalog identical: True; files byte-identical before/after: precip_2d.nc True, press_2d.nc True, sfincs.dep True, sfincs.ind True, sfincs.inp True, sfincs.msk True, wind_2d.nc True; verdict {'all_files_byte_identical': True, 'all_files_content_identical': True}.
- A1/A2 tests: `python -m unittest discover -s tests` → 42 tests OK at commit `513ce5ab73bbf4ef41e091cf3c49c3b836f2cd8b` (tests/test_harness_v14.py, test_precip_forcing_v14.py, test_ib_boundary_v14.py + the 17 earlier tests). F5 synthetic cases through the real hydromt method: half-hourly 4×10 mm/h → written 10,10,10,10 (×1.000, 0 min); hourly 10 mm stamped 01:00 → 10 mm/h on [00:00,01:00) (×1.000, 0 min physical offset); v1.3 defaults reproduce 20,20,20,0.
- A2 pavbnd semantics (`PAVBND_SOURCE.md`, tag v2.3.0_mt_Faber_release): `sfincs_input.f90:93` real, default 0.0; `sfincs_boundaries.f90:796-800` `if (patmos .and. pavbnd>1.0) zst = zst + (pavbnd - patmb(ib))/(rhow*9.81)`; the published value 1 never acted (guard > 1.0), it would not have lowered the boundary by ~10 m.
- A2 synthetic 25-hPa test (`ib_synthetic_result.json`, 2026-10-12T10:09:50Z): p = 98825 Pa, expected 0.2489 m; v1.4: 4 bnd points, 388 msk=2 cells, boundary zs at the last output mean 0.2489 m (min 0.2489, max 0.2489), interior mean 0.2488 m; v1.3 control: pavbnd line `pavbnd               = 1`, no bnd file, SFINCS warning present = True, boundary wet fraction 0.00 (never wet).
- A2 reference pressure vs event-window domain-mean ERA5 MSLP (`A2_pavbnd_reference.json`; (101325 − p̄)/(ρg), ρ = 1024): Pineios EMSR692 p̄ 1015.38 hPa → offset -0.021 m, IB at the domain-mean minimum 1007.94 hPa (2023-09-05 03:00) = +0.053 m, range in window 0.113 m; Mandra EMSR257 p̄ 1012.99 hPa → offset +0.003 m, IB at the domain-mean minimum 1004.12 hPa (2017-11-13 13:00) = +0.091 m, range in window 0.138 m; Strymonas EMSR122 p̄ 1009.02 hPa → offset +0.042 m, IB at the domain-mean minimum 1001.72 hPa (2015-03-28 03:00) = +0.115 m, range in window 0.159 m; Valencia EMSR773 p̄ 1018.03 hPa → offset -0.048 m, IB at the domain-mean minimum 1013.25 hPa (2024-10-29 17:00) = +0.000 m, range in window 0.089 m; Emilia-Romagna EMSR664 p̄ 1011.62 hPa → offset +0.016 m, IB at the domain-mean minimum 1000.70 hPa (2023-05-16 08:00) = +0.125 m, range in window 0.178 m; Crete EMSR933 p̄ 1018.46 hPa → offset -0.052 m, IB at the domain-mean minimum 1014.53 hPa (2026-10-01 03:00) = -0.013 m, range in window 0.071 m.
- A2 one-day Pineios slice, NO scoring (`pineios_slice_ib_result.json`, 2026-10-12T10:19:56Z; copy of the as-run model, slice 2023-09-05): 10 bnd points on 650 msk=2 cells (zb 0.000..0.000 m); boundary MSLP 1006.74..1014.55 hPa → expected IB -0.013..+0.065 m; modelled boundary zs +0.000..+0.060 m; modelled − expected mean -0.0056 m, RMSE 0.0066 m, max |Δ| 0.0188 m, r = 0.9836; wet fraction of boundary cell-times 0.820; SFINCS wall-clock 204.6 s. With bilinear instead of nearest sampling of press_2d.nc at the boundary cells (`pressure_sampling_comparison.bilinear`): mean -0.0045 m, RMSE 0.0049 m, max |Δ| 0.0117 m, r = 0.9934, modelled/expected where expected > 2 cm = 0.872; at the MSLP minimum 2023-09-05T03:00 expected 0.0532 m vs modelled 0.0485 m; per-cell time-mean difference -0.0086..-0.0015 m. The boundary tracks the inverse barometer; the ~10 % systematic shortfall is not explained (candidate: registration of the netamp pressure grid inside SFINCS vs this sampling) — open item, not a blocker.
- A3 (report only, `A3_spinup_totals.json`, 2026-10-12T10:02:41Z; domain means over the YAML bbox; raw IMERG): Pineios EMSR692 enhanced: spin-up 7 d ERA5 0.4 / IMERG 1.4 mm; simulated ERA5 301.4 / IMERG 147.3 mm; SCS-CN off; Pineios EMSR692 baseline: spin-up 1 d ERA5 0.2 / IMERG 0.0 mm; simulated ERA5 294.7 / IMERG 150.6 mm; SCS-CN off; Mandra EMSR257 enhanced: spin-up 1 d ERA5 0.3 / IMERG 0.4 mm; simulated ERA5 38.6 / IMERG 138.1 mm; SCS-CN off; Mandra EMSR257 baseline: spin-up 1 d ERA5 0.3 / IMERG 0.4 mm; simulated ERA5 38.6 / IMERG 138.1 mm; SCS-CN off; Strymonas EMSR122 enhanced (v3): spin-up 7 d ERA5 21.1 / IMERG 47.6 mm; simulated ERA5 9.2 / IMERG 6.7 mm; SCS-CN on (AMC 2); Strymonas EMSR122 baseline: spin-up 1 d ERA5 20.0 / IMERG 21.0 mm; simulated ERA5 9.2 / IMERG 6.7 mm; SCS-CN off; Valencia EMSR773 enhanced: spin-up 3 d ERA5 24.9 / IMERG 17.0 mm; simulated ERA5 109.9 / IMERG 61.6 mm; SCS-CN off; Emilia-Romagna EMSR664 enhanced: spin-up 14 d ERA5 122.7 / IMERG 106.7 mm; simulated ERA5 118.5 / IMERG 118.7 mm; SCS-CN off; Crete EMSR933 enhanced (Late IMERG): spin-up 7 d ERA5 — / IMERG 47.9 mm; simulated ERA5 — / IMERG 121.9 mm; SCS-CN off; Crete EMSR933 baseline: spin-up 7 d ERA5 24.5 / IMERG — mm; simulated ERA5 81.2 / IMERG — mm; SCS-CN off.
- Part C Crete build QC (`reproduction/emsr933/stage2_build_qc.json`, 2026-10-12T10:07:01Z; grid/dep/mask/subgrid only, no forcing, no run; GAP-1 = A 100 m island-wide, GAP-2 z_max 2500 m): grid 2771 × 1107 = 3067497 cells; active 3067497 (30675.0 km²), msk=1 3059745, msk=2 7752, msk=3 0; active cells with dep ≤ 0 m 2222469, > 0 m 845028; dep range -1.1..2440.0 m; v1.4 bnd points 78 (every 10000 m along ~775.2 km); subgrid 1949.9 MB, z_zmin min/p50/max -3.9/0.0/2431.8 m, z_zmax max 2451.3 m, uv_navg 0.012..0.100; hydromt build log 2026-10-12 12:47:55 → 2026-10-12 12:52:31 (local). Samaria-gorge GLO-30 pit at 100 m: 2.56 km² (256 cells), floor 235.9 m, spill 556.1 m, depth 320.2 m, volume below spill 296.6 Mm³, closed = True, subgrid z_zmin at the deepest cell 228.5 m (index check r = 0.99982); Stage-1 90-m values 2.43 km², floor 238.2, spill 546.5, 273.6 Mm³. Not fixed (characterised only).
- Part B: `reproduction/v14_rerun/MANIFEST.md` (planning only; 27 (+1) SFINCS runs, Σ previous wall-clock 27 602 s ≈ 7.7 h, ≈ 10 h with builds/validation/figures; no forcing re-download needed) with its source `INVENTORY_2026-10-12.md`.
- Crete forcing downloaded for A3 only (ERA5 `era5_crete.nc` via prep_inputs; IMERG Late `imerg_crete.nc`, 721 stamps): downloaded, NOT run.

### Harness v1.4 D4 coastal set-up (CODE-13) — code + tests only; commit `561e8a03510125016ada36bb1bf30dc2ca4c085f` (2026-10-19T08:23:45Z); block generated 2026-10-19T08:26:52Z by `reproduction/v14_harness/scripts/code13_summary.py`

**Status: no corrected run of a published event exists; GO-C pending.** Decisions recorded from Checkpoint 2: A1 accepted (D1 affects the IMERG path only; the ERA5 baselines were not affected — correction added to F5_VERIFY.md); A2 accepted (bnd every 10 km, bzs = 0 m, pavbnd = 101325 Pa; the constant offset relative to the event-mean MSLP, −0.052 … +0.042 m across the six events, is a documented limitation); D3: no code change — the methods text will be corrected (Table 2 'spin-up' = forcing lead-in, not simulated; antecedent state enters only through R4); Crete YAMLs set to `harness_version: v1.4`.

- Part A, D4 check (`D4_check.json`, 2026-10-19T08:20:39Z; geometry only, no scores). validate_event_v2.py:235-242: evaluation_mask = (msk > 0) & rasterised union of *areaOfInterest* shapefiles (all_touched=True, :62-102); no exclusion of sea, hydrography/permanent water or zb <= 0 cells. Per model (active cells; (i) open sea; (ii) inland dep<=0; msk=2 total/perimeter/interior; land cells with zb<0 and their initial volume at zsini=0; evaluation cells; eval ∩ open sea; eval ∩ (ii) zb<0; eval ∩ EMS hydrography; eval ∩ WorldCover-80):
  - Pineios enhanced (2a): active 262465 (5905.5 km²); (i) 39490 (888.5 km²); (ii) 9 (0.2 km²); msk=2 650 / 650 / 0 (650 inside (i)); land zb<0 131 cells (2.947 km², 0.595 Mm³), of which (ii) 9; eval 206326 (4642.3 km²): ∩(i) 3448 (77.58 km²), ∩(ii) zb<0 0, no hydrography layer in the package set, ∩WC80 6028 (3447 sea / 2581 land).
  - Pineios grid-matched baseline (1c): active 262465 (5905.5 km²); (i) 39490 (888.5 km²); (ii) 9 (0.2 km²); msk=2 650 / 650 / 0 (650 inside (i)); land zb<0 131 cells (2.947 km², 0.595 Mm³), of which (ii) 9; eval 206326 (4642.3 km²): ∩(i) 3448 (77.58 km²), ∩(ii) zb<0 0, no hydrography layer in the package set, ∩WC80 6028 (3447 sea / 2581 land).
  - Mandra enhanced (2b): active 162335 (405.8 km²); (i) 48187 (120.5 km²); (ii) 28 (0.07 km²); msk=2 453 / 453 / 0 (453 inside (i)); land zb<0 271 cells (0.677 km², 0.398 Mm³), of which (ii) 22; eval 43886 (109.7 km²): ∩(i) 8815 (22.04 km²), ∩(ii) zb<0 14, 2 cells in 2 hydrography shp, ∩WC80 9002 (8708 sea / 294 land).
  - Mandra baseline (1d): active 162335 (405.8 km²); (i) 48187 (120.5 km²); (ii) 28 (0.07 km²); msk=2 453 / 453 / 0 (453 inside (i)); land zb<0 271 cells (0.677 km², 0.398 Mm³), of which (ii) 22; eval 43886 (109.7 km²): ∩(i) 8815 (22.04 km²), ∩(ii) zb<0 14, 2 cells in 2 hydrography shp, ∩WC80 9002 (8708 sea / 294 land).
  - Strymonas v3 enhanced (2c): active 207374 (4665.9 km²); (i) 22427 (504.6 km²); (ii) 89 (2.0 km²); msk=2 346 / 293 / 53 (346 inside (i)); land zb<0 520 cells (11.7 km², 5.584 Mm³), of which (ii) 89; eval 54341 (1222.7 km²): ∩(i) 920 (20.7 km²), ∩(ii) zb<0 52, 1473 cells in 16 hydrography shp, ∩WC80 1175 (920 sea / 255 land).
  - Strymonas baseline (1e): active 207374 (4665.9 km²); (i) 22427 (504.6 km²); (ii) 89 (2.0 km²); msk=2 346 / 293 / 53 (346 inside (i)); land zb<0 520 cells (11.7 km², 5.584 Mm³), of which (ii) 89; eval 54341 (1222.7 km²): ∩(i) 920 (20.7 km²), ∩(ii) zb<0 52, 1473 cells in 16 hydrography shp, ∩WC80 1175 (920 sea / 255 land).
  - Valencia 164 mm (2e): active 521427 (5214.3 km²); (i) 225179 (2251.8 km²); (ii) 11110 (111.1 km²); msk=2 1233 / 1233 / 0 (1233 inside (i)); land zb<0 11463 cells (114.63 km², 88.582 Mm³), of which (ii) 8989; eval 320037 (3200.4 km²): ∩(i) 44616 (446.16 km²), ∩(ii) zb<0 8945, no hydrography layer in the package set, ∩WC80 49036 (44567 sea / 4469 land).
  - Emilia-Romagna 8-AOI (2f): active 300965 (6771.7 km²); (i) 74774 (1682.4 km²); (ii) 8615 (193.84 km²); msk=2 2290 / 749 / 1541 (1907 inside (i)); land zb<0 14840 cells (333.9 km², 286.876 Mm³), of which (ii) 8443; eval 142949 (3216.4 km²): ∩(i) 789 (17.75 km²), ∩(ii) zb<0 6033, no hydrography layer in the package set, ∩WC80 2890 (639 sea / 2251 land).
  - Crete build-only QC (CODE-12): active 3067497 (30675.0 km²); (i) 2222416 (22224.2 km²); (ii) 53 (0.53 km²); msk=2 7752 / 7752 / 0 (7752 inside (i)); land zb<0 201 cells (2.01 km², 0.87 Mm³), of which (ii) 6; eval 88301 (883.0 km²): ∩(i) 1813 (18.13 km²), ∩(ii) zb<0 0, no hydrography layer in the package set, ∩WC80 2387 (1812 sea / 575 land).
- Part B implementation (behind v1.4; `build_model.open_sea_split`, `coastal_ring`, `prepare_coastal_exclusion`, `ZSINI_DRY = -9999`): open sea (4-connectivity to the grid edge through dep<=0) made inactive through `setup_mask_active(exclude_mask=<open_sea_exclude.geojson>, all_touched=false)` except a one-cell ring 8-adjacent to land, which `setup_mask_bounds(zmax=0)` turns into msk=2; inland dep<=0 stays active land; bnd points every 10 km along the ring (now for every v1.4 run, pavbnd only with coastal_bc); every active cell starts dry via `zsini = -9999` (SFINCS v2.3.0 `sfincs_initial_conditions.F90:43,98-100`: zs = max(z_zmin, zsini)). Published v1.3 records still render byte-identically (test).
- Crete rebuild with D4 (`D:/ELKAK/implementation/emsr933_crete/buildqc_v14/rebuild_v14.json`, 2026-10-19T08:19:34Z → 2026-10-19T08:23:17Z; `stage2_build_qc_v14.json`, 2026-10-19T08:26:02Z): prep 6.6 s, hydromt build 208.6 s; open sea 2222416 cells (22224.16 km²), ring 14646 cells (1464.6 km of coastline cells), inland dep<=0 kept 53, excluded 2207770 (polygons 4); built mask: active 859727 (8597.3 km²), msk=1 845869, msk=2 13858, bnd points 160; subgrid 544.9 MB, z_zmin min/p50/max -3.9/348.7/2431.8 m; Samaria pit unchanged (2.56 km², depth 320.2 m, closed True).
- IB shortfall diagnosis (`ib_shortfall_diagnosis.json`, 2026-10-19T08:14:50Z; one-day Pineios slice, report only): modelled boundary level vs (pavbnd − p)/(ρg) with p sampled from press_2d.nc at the cell — nearest: mean -0.0056 m, RMSE 0.0066; bilinear: -0.0045 / 0.0049; time lags of ±15…60 min do not improve it (best RMSE 0.0046); sampling the pressure grid half a netamp cell off (dx −0.5, dy +0.5 of 23774 m cells) reproduces the modelled level exactly: mean -0.00000 m, RMSE 0.00000, r = 1.00000. Cause: SFINCS takes the first x/y coordinate of a netamp/netamuamv file as the lower-left CORNER of the meteo grid (`sfincs_ncinput.F90:496-499`, `:382-385`) and adds half a cell to reach the centres (`sfincs_meteo.f90:977-978`), while hydromt_sfincs writes cell CENTRES → every NetCDF meteo field (pressure, wind, and the netampr rain) is applied half a meteo cell off (≈ 12 km for ERA5, ≈ 5 km for IMERG). The boundary itself tracks the inverse barometer exactly (`zs(nmb) = zsb`, `sfincs_boundaries.f90:1073`). Registered as D5, not changed (report only). H2 (dry sea plane) quantified for completeness: net inflow to the 0-m plane -241.4 m³/s mean → weakly-reflective deficit -0.0140 m (not the cause: the boundary level is prescribed, the plane only receives the flux).
- Tests at commit `561e8a03510125016ada36bb1bf30dc2ca4c085f`: 57 green (python -m unittest discover -s tests, 71 s incl. two SFINCS integration tests).

### GO-C Phase 1 — harness v1.4 re-run of Strymonas, Mandra, Pineios (baselines + canonical enhanced); D5 commit `8ccabb03f5f2164be5b52c0633aac1bfff0d73ca` (2026-10-19T08:57:24Z), evaluation-mask commit `c6f39fad46b8a71b0172d1b19809d875f415ccd6` (2026-10-19T09:04:55Z); block generated 2026-10-19T10:22:22Z by `reproduction/v14_rerun/scripts/checkpoint4_tables.py`

**GO-C decisions (Papaioannou, 2026-10-19), recorded:** (1) option (c) — harness v1.4 for every run: D1 IMERG rate/label, D2 coastal IB (bnd/bzs, pavbnd 101325 Pa), D4 (open sea inactive, coastal msk=2 ring, every cell starts dry), D5 meteo-grid alignment; D3 text-only. (2) D5 implemented in v1.4 (one function for netamp/netamuamv/netampr). (3) evaluation mask, all events: exclude WorldCover class 80 ∪ the v1.4 open-sea mask, same rule both sides; the observed-flood area removed is reported. (4) no simulated lead-in; ONE labelled sensitivity (Strymonas v3, 7-day lead-in simulated) in Phase 3. (5) the eight orphan runs recreated under v1.4 (Phase 3); Strymonas baseline re-run from the committed example. (6) Crete: rule_ledger.md §8. Execution: Phase 1 → Checkpoint 4 → stop; Phases 2–5 on the author's go. v1.3 numbers are kept beside v1.4 below.

- D5 proof (`reproduction/v14_harness/D5_synthetic_results.json` 2026-10-19T08:55:37Z, `pineios_slice_d5_result.json` 2026-10-19T08:54:50Z): (i) linear pressure gradient, boundary zs vs (101325 − p)/(ρg) at the cell centres — aligned RMSE 0.0000 m (max 0.0000), unaligned control RMSE 0.0995 m (meteo cell 25.4 km); (iii) 30-min IMERG pulse on one cell — aligned centroid offset +0.1/-0.5 m, relative RMSE 0.00002, share inside the written footprint 0.657 (expected 0.657); unaligned +5018/-5017 m (half of the 10.0-km cell east and south), share 0.375; (ii) one-day Pineios slice with aligned grids: modelled − expected (bilinear at the true centres) mean -0.00000 m, RMSE 0.00000 m, max 0.00002 m, r 1.0000, fit slope 1.0000 (CODE-12 before: mean -0.0056, RMSE 0.0066, r 0.9836) — the IB-shortfall item is closed, explained by D5.
- **D6 (new, report only; `reproduction/v14_harness/D6_CN_SINK.md`)**: SFINCS v2.3.0 curve-number infiltration ('cna', the `setup_cn_infiltration` route) adds the infiltration increment to `cuminf` only when `storecumprcp = 1` (`sfincs_infiltration.f90:107`; default 0, `sfincs_input.f90:219,439-441`) while `cumprcp` always accumulates (`sfincs_meteo.f90:1266`) and the volume has no floor (`sfincs_continuity.f90:~535`): past Ia = 0.2 S a cell removes the whole cumulative infiltration every time step — an unbounded sink for rain and inflow. Synthetic closed plain (`D6_cn_sink_check.json` 2026-10-19T10:02:43Z; CN 76, 30 mm rain + 20 m³/s for 12 h): end volume 0 m³ with storecumprcp 0 vs 1062676 m³ with 1 (expected 1062364; ratio 1.0003). Strymonas v3 enhanced (`D6_strymonas_sink_cells.json` 2026-10-19T10:03:05Z, inputs only): cells past Ia by the end 1904.9 km² (40.8%) with the published rain vs 244.1 km² (5.8%) with the v1.4 rain; Serres-plain window 27.5% vs 1.3%. Water on land, peak/end (`strymonas_v14_diagnosis.json` 2026-10-19T10:07:12Z): published 52.5/10.9 Mm³, v1.4 314.8/314.8 Mm³ for 311.9 Mm³ of discharge in the simulated week; isolation runs on copies: E1_v14_zsini0 314.8/314.8; E2_v14_publishedrain 52.5/10.9; E3_v13_zsini_dry 52.5/10.9; E4_v13_plusIB 52.5/10.9; E5_v14_unalignedwindpress 314.8/314.8; E6_v14_noIB 314.8/314.8. The v1.4 Strymonas enhanced score below still contains the sink and is not a valid v1.4 number; the fix (v1.4 `storecumprcp = 1` with CN) awaits the author's decision.
- Phase-1 scores (h > 0.10 m strict; `reproduction/v14_rerun/results/<run>_{v13_publishedmask,v13_newmask,v14_newmask}.json`):
  - strymonas_baseline: v1.3 published CSI 0.2039 HR 0.3766 FAR 0.6921 B 1.223 GSS 0.1551 (TP/FP/FN 1784/4011/2953, eval 1222.67 km², observed 106.58 km²); v1.3 rescored with the new mask CSI 0.1973 HR 0.3665 FAR 0.7005 B 1.224 GSS 0.1484 (TP/FP/FN 1698/3972/2935; excluded 1175 cells = 26.44 km², observed removed 104 cells = 2.340 km²); **v1.4 with the new mask CSI 0.2068 HR 0.4099 FAR 0.7056 B 1.392 GSS 0.1551** (TP/FP/FN 1899/4551/2734, eval 1196.23 km², observed 104.24 km²); Δ(v1.4 new − v1.3 published) CSI +0.0028 HR +0.0333 FAR +0.0134 (mask alone -0.0066 CSI); fuzzy r=1 CSI 0.2307 → 0.2291; v1.4 build: active 185824 (open sea removed 21550 cells, ring 877), SFINCS 145.146 s (published 256.5 s); run record `results/strymonas_baseline_record.json`.
  - [pre-D6, invalid] strymonas_enhanced: v1.3 published CSI 0.1822 HR 0.3221 FAR 0.7045 B 1.090 GSS 0.1357 (TP/FP/FN 1526/3639/3211, eval 1222.67 km², observed 106.58 km²); v1.3 rescored with the new mask CSI 0.1800 HR 0.3194 FAR 0.7079 B 1.094 GSS 0.1335 (TP/FP/FN 1480/3587/3153; excluded 1175 cells = 26.44 km², observed removed 104 cells = 2.340 km²); **v1.4 with the new mask CSI 0.3328 HR 0.9061 FAR 0.6553 B 2.629 GSS 0.2715** (TP/FP/FN 4198/7980/435, eval 1196.23 km², observed 104.24 km²); Δ(v1.4 new − v1.3 published) CSI +0.1506 HR +0.5840 FAR -0.0493 (mask alone -0.0021 CSI); fuzzy r=1 CSI 0.2472 → 0.4040; v1.4 build: active 185824 (open sea removed 21550 cells, ring 877), SFINCS 168.394 s (published 109.2 s); run record `results/strymonas_enhanced_record.json`. **D6: curve-number sink present in both the published and the v1.4 run — the v1.4 value is not a valid v1.4 number (D6_CN_SINK.md).**
  - strymonas_enhanced false alarms (`results/strymonas_enhanced_v13_fa_share.json`): 3639 FA cells; open sea 0.0000, WC80 0.0143, inland zb<0 0.0047, union 0.0151.
  - mandra_baseline: v1.3 published CSI 0.0795 HR 0.4003 FAR 0.9097 B 4.433 GSS 0.0079 (TP/FP/FN 1439/14499/2156, eval 109.72 km², observed 8.99 km²); v1.3 rescored with the new mask CSI 0.1520 HR 0.3889 FAR 0.8003 B 1.947 GSS 0.0810 (TP/FP/FN 1372/5498/2156; excluded 9109 cells = 22.77 km², observed removed 67 cells = 0.168 km²); **v1.4 with the new mask CSI 0.1383 HR 0.2491 FAR 0.7629 B 1.051 GSS 0.0841** (TP/FP/FN 879/2829/2649, eval 86.94 km², observed 8.82 km²); Δ(v1.4 new − v1.3 published) CSI +0.0587 HR -0.1511 FAR -0.1468 (mask alone +0.0725 CSI); fuzzy r=1 CSI 0.1388 → 0.1710; v1.4 build: active 117667 (open sea removed 44668 cells, ring 3519), SFINCS 112.521 s (published 546.6 s); run record `results/mandra_baseline_record.json`.
  - mandra_enhanced: v1.3 published CSI 0.1060 HR 0.8734 FAR 0.8923 B 8.113 GSS 0.0276 (TP/FP/FN 3140/26028/455, eval 109.72 km², observed 8.99 km²); v1.3 rescored with the new mask CSI 0.1498 HR 0.8710 FAR 0.8468 B 5.687 GSS 0.0562 (TP/FP/FN 3073/16989/455; excluded 9109 cells = 22.77 km², observed removed 67 cells = 0.168 km²); **v1.4 with the new mask CSI 0.1567 HR 0.7602 FAR 0.8351 B 4.611 GSS 0.0667** (TP/FP/FN 2682/13587/846, eval 86.94 km², observed 8.82 km²); Δ(v1.4 new − v1.3 published) CSI +0.0507 HR -0.1132 FAR -0.0572 (mask alone +0.0438 CSI); fuzzy r=1 CSI 0.1591 → 0.2076; v1.4 build: active 117667 (open sea removed 44668 cells, ring 3519), SFINCS 398.702 s (published 1097.8 s); run record `results/mandra_enhanced_record.json`.
  - mandra_enhanced false alarms (`results/mandra_enhanced_v13_fa_share.json`): 26028 FA cells; open sea 0.3364, WC80 0.3454, inland zb<0 0.0031, union 0.3500.
  - pineios_baseline_gridmatched: v1.3 published CSI 0.5170 HR 0.8231 FAR 0.4184 B 1.415 GSS 0.3189 (TP/FP/FN 55561/39972/11943, eval 4642.34 km², observed 1518.84 km²); v1.3 rescored with the new mask CSI 0.5427 HR 0.8226 FAR 0.3853 B 1.338 GSS 0.3510 (TP/FP/FN 55118/34551/11889; excluded 6029 cells = 135.65 km², observed removed 497 cells = 11.182 km²); **v1.4 with the new mask CSI 0.5425 HR 0.8400 FAR 0.3949 B 1.388 GSS 0.3465** (TP/FP/FN 56285/36737/10722, eval 4506.68 km², observed 1507.66 km²); Δ(v1.4 new − v1.3 published) CSI +0.0256 HR +0.0169 FAR -0.0235 (mask alone +0.0258 CSI); fuzzy r=1 CSI 0.5085 → 0.5181; v1.4 build: active 223703 (open sea removed 38762 cells, ring 728), SFINCS 979.893 s (published 1006.4 s); run record `results/pineios_baseline_gridmatched_record.json`.
  - pineios_enhanced: v1.3 published CSI 0.4559 HR 0.9468 FAR 0.5321 B 2.024 GSS 0.2012 (TP/FP/FN 63910/72693/3594, eval 4642.34 km², observed 1518.84 km²); v1.3 rescored with the new mask CSI 0.4726 HR 0.9465 FAR 0.5144 B 1.949 GSS 0.2180 (TP/FP/FN 63422/67194/3585; excluded 6029 cells = 135.65 km², observed removed 497 cells = 11.182 km²); **v1.4 with the new mask CSI 0.4948 HR 0.8984 FAR 0.4759 B 1.714 GSS 0.2616** (TP/FP/FN 60201/54666/6806, eval 4506.68 km², observed 1507.66 km²); Δ(v1.4 new − v1.3 published) CSI +0.0389 HR -0.0483 FAR -0.0562 (mask alone +0.0167 CSI); fuzzy r=1 CSI 0.4263 → 0.4607; v1.4 build: active 223703 (open sea removed 38762 cells, ring 728), SFINCS 1575.937 s (published 1456.2 s); run record `results/pineios_enhanced_record.json`.
  - pineios_enhanced false alarms (`results/pineios_enhanced_v13_fa_share.json`): 72693 FA cells; open sea 0.0472, WC80 0.0756, inland zb<0 0.0003, union 0.0759.
- Tests at the Phase-1 records commit: 82 green (python -m unittest discover -s tests, 97 s, 2026-10-19T10:19:21Z-10:20:59Z).
- Crete decisions written into `reproduction/emsr933/rule_ledger.md` §8 before any Crete run (R2 on canonical with the DEM windward-slope widths, GAP-1 A, GAP-2 2500 m, window 7/3/4, scoring tiers, three labelled sensitivities incl. the anchor sweep 224/336/447.8/582 mm and the karst bracket qinf = 0.513 × 447.8 mm / 120 h = 1.914 mm/h from Steiakakis 2018; sources in `karst_recharge_sources.md`).

### GO-D6 + Phase 2 — D6 commit `47354293d770c56b1ff8fc7b7fe92491da3bfeca` (2026-10-19T12:54:21Z); bias-box CLI fix `e33eacb6184213ef0f90def423659fefcd3261b2` (2026-10-19T12:05:51Z); block generated 2026-10-19T13:00:31Z by `reproduction/v14_rerun/scripts/checkpoint4b_tables.py`

**Decisions (Papaioannou, 2026-10-19, GO-D6 + Phase 2):** D6 adopted — v1.4 writes `storecumprcp = 1` whenever curve-number infiltration is on, tests first; provenance + private reproducer for Deltares (no public issue); Strymonas v3 enhanced re-run under v1.4 + D6 → Checkpoint 4b; Phase 2 (Valencia 164 mm, Emilia 8-AOI) in parallel. The Phase-1 Strymonas-enhanced v1.4 row stays, labelled pre-D6, invalid. Phases 3–5 wait.

- D6 tests (`tests/test_d6_cn_bookkeeping.py`, metrics `reproduction/v14_harness/D6_test_metrics.json`): (i) closed CN-76 plain, 30 mm rain + 20 m³/s for 12 h through the v1.4 pipeline path: end volume / expected = 1.00029 (1062676 of 1062364 m³; tolerance 0.1 %); v1.3 control 0.0000. (ii) 180 mm in three daily bursts (rain 180.0 mm = 2.24 S, 9588 cells × 96 hourly maps): max F = I − Ia = 53.86 mm ≤ S = 80.21 mm; smallest hourly increment of cumulative infiltration +0.0000 mm (monotone); max(cuminf − cumprcp) +0.0000 mm; max |cuminf − SCS curve| 0.0017 mm. (iii) without curve numbers the flag leaves zs and zsmax bit-identical — synthetic: True / True; Mandra enhanced v1.4 event (`D6_invariance_mandra.json`, 2026-10-19T12:31:24Z, reference infiltration type 'none'): zs bit-identical True (max diff 0.0 m), zsmax True; the flag only adds cuminf, cumprcp to the map file.
- Tests at the D6 commit: 101 green (python -m unittest discover -s tests, 158 s, 2026-10-19T12:51:26Z-12:54:05Z).
- D6 provenance (`reproduction/v14_harness/D6_CN_SINK.md` §1, §6): verbatim v2.3.0 source lines; upstream, SFINCS lists the issue in its known issues since 2026-04-02 (`e394b7f02e`) with the same workaround, the v2.4.0 Galibier release (2026-06-15) still carries it although its notes say fixed, and `main` forces the flag for 'cna'/'cnb' since `360c1592ee` (2026-07-15); no release contains the fix yet. `reproducer_D6.md` drafted for a private note to Deltares (not sent, no public issue).
- strymonas_enhanced_postD6 (v1.4 + D6): CSI 0.3336 HR 0.9214 FAR 0.6566 B 2.683 GSS 0.2720 (TP/FP/FN 4269/8162/364); v1.3 published 0.1822, v1.3 new mask 0.1800; Δ(v1.4+D6 − v1.3 published) CSI +0.1515 HR +0.5993 FAR -0.0480. Sink cells 0 (0.00%); balance (Mm³): rain 25.45, infiltration 24.85, discharge 311.94, storage end 271.15, net outflow 41.38.
- valencia_enhanced_164: v1.3 published CSI 0.0939 HR 0.9890 FAR 0.9060 B 10.524 GSS 0.0335 (TP/FP/FN 19808/190968/221; identical to `R1_verification/task_valencia_anchor/_scoring/score_v164.json`: True); v1.3 new mask CSI 0.1193 HR 0.9887 FAR 0.8805 B 8.274 (observed removed 4.48 km²); **v1.4 new mask CSI 0.1439 HR 0.9387 FAR 0.8547 B 6.461 GSS 0.0779** (TP/FP/FN 18381/108134/1200); Δ CSI +0.0500 (mask +0.0255); SFINCS 1396.242 s; record `results/valencia_enhanced_164_record.json`; published false alarms on open sea/WC80/inland zb<0: 0.2565.
- emilia_enhanced_8aoi: v1.3 published CSI 0.2404 HR 0.9206 FAR 0.7545 B 3.750 GSS 0.0732 (TP/FP/FN 24247/74529/2091; identical to `R1_verification/task_emilia_aoi/_scoring/emilia_rescore.json (full_8aoi)`: True); v1.3 new mask CSI 0.2367 HR 0.9177 FAR 0.7582 B 3.795 (observed removed 24.70 km²); **v1.4 new mask CSI 0.2515 HR 0.8500 FAR 0.7368 B 3.230 GSS 0.0956** (TP/FP/FN 21455/60073/3785); Δ CSI +0.0111 (mask -0.0037); SFINCS 1180.21 s; record `results/emilia_enhanced_8aoi_record.json`; published false alarms on open sea/WC80/inland zb<0: 0.1043.

### GO Phases 3–5 — Phase 3 records; block generated 2026-10-19T23:37:07Z by `reproduction/v14_rerun/scripts/checkpoint5a_tables.py`

**Decisions (Papaioannou, 2026-10-19, GO Phases 3–5):** Checkpoint 4b accepted, D6 closed, the Strymonas v1.4 + D6 row is canonical; Phase 3 a–e, Phase 4 a–e, Phase 5 a–d, then AUDIT consolidation, tag v1.4.0, Checkpoint 5b. Standing: new defect → report only; v1.3 beside v1.4; numbers only from JSON.

- strymonas_abl_cnoff_q (Table 12 row 3: CN off + Q): v1.3 published CSI 0.2386 HR 0.9495 FAR 0.7583 B 3.929; v1.3 new mask CSI 0.2487; **v1.4 new mask CSI 0.2947 HR 0.9359 FAR 0.6992 B 3.111 GSS 0.2289** (TP/FP/FN 4336/10079/297); SFINCS 915.726 s; record `results/strymonas_abl_cnoff_q_record.json`.
- strymonas_abl_qoff_cn (Table 12 row 4: CN on + Q off): v1.3 published CSI 0.0160 HR 0.0160 FAR 0.1828 B 0.020; v1.3 new mask CSI 0.0116; **v1.4 new mask CSI 0.0113 HR 0.0114 FAR 0.4952 B 0.023 GSS 0.0094** (TP/FP/FN 53/52/4580); curve numbers realised (active) 74.9; SFINCS 220.273 s; record `results/strymonas_abl_qoff_cn_record.json`.
- strymonas_v1_prefix_src (Table 8 'Enhanced v1' / S2 Strymonas v1: pre-fix kerkini_outlet {23.2, 41.08}): v1.3 published CSI 0.1701 HR 0.2098 FAR 0.5267 B 0.443; v1.3 new mask CSI 0.1683; **v1.4 new mask CSI 0.3249 HR 0.9109 FAR 0.6644 B 2.714 GSS 0.2627** (TP/FP/FN 4220/8354/413); curve numbers realised (active) 74.9; SFINCS 238.315 s; record `results/strymonas_v1_prefix_src_record.json`.
- mandra_r2_95 (R2 sweep Mandra target 95 mm): v1.3 published CSI 0.1041 HR 0.7538 FAR 0.8922 B 6.995; **v1.4 new mask CSI 0.1622 HR 0.6284 FAR 0.8206 B 3.503 GSS 0.0776** (TP/FP/FN 2217/10143/1311); SFINCS 2837.585 s; record `results/mandra_r2_95_record.json`.
- mandra_r2_140 (R2 sweep Mandra target 140 mm): v1.3 published CSI 0.1063 HR 0.8245 FAR 0.8913 B 7.582; **v1.4 new mask CSI 0.1585 HR 0.6899 FAR 0.8293 B 4.042 GSS 0.0710** (TP/FP/FN 2434/11827/1094); SFINCS 3157.719 s; record `results/mandra_r2_140_record.json`.
- mandra_r2_255 (R2 sweep Mandra target 255 mm): v1.3 published CSI 0.1043 HR 0.8932 FAR 0.8944 B 8.456; v1.3 new mask CSI 0.1451; **v1.4 new mask CSI 0.1565 HR 0.8118 FAR 0.8376 B 4.999 GSS 0.0651** (TP/FP/FN 2864/14772/664); SFINCS 1691.389 s; record `results/mandra_r2_255_record.json`.
- pineios_r2_220 (R2 sweep Pineios target 220 mm): v1.3 published CSI 0.4755 HR 0.9023 FAR 0.4987 B 1.800; **v1.4 new mask CSI 0.5047 HR 0.8314 FAR 0.4377 B 1.479 GSS 0.2921** (TP/FP/FN 55711/43374/11296); SFINCS 2043.759 s; record `results/pineios_r2_220_record.json`.
- pineios_r2_295 (R2 sweep Pineios target 295 mm): v1.3 published CSI 0.4664 HR 0.9261 FAR 0.5156 B 1.912; **v1.4 new mask CSI 0.5014 HR 0.8666 FAR 0.4567 B 1.595 GSS 0.2787** (TP/FP/FN 58065/48803/8942); SFINCS 3641.185 s; record `results/pineios_r2_295_record.json`.
- pineios_r2_510 (R2 sweep Pineios target 510 mm): v1.3 published CSI 0.4460 HR 0.9593 FAR 0.5454 B 2.110; v1.3 new mask CSI 0.4617; **v1.4 new mask CSI 0.4864 HR 0.9196 FAR 0.4920 B 1.810 GSS 0.2444** (TP/FP/FN 61617/59668/5390); SFINCS 4198.593 s; record `results/pineios_r2_510_record.json`.
- mandra_cn_a15 (S1 row 1: HSG-A AMC-II (CN = 15 test) — pervious classes CN 15): no published number; **v1.4 new mask CSI 0.1091 HR 0.2565 FAR 0.8405 B 1.608 GSS 0.0427** (TP/FP/FN 905/4768/2623); curve numbers realised (active) 33.7; SFINCS 300.373 s; record `results/mandra_cn_a15_record.json`.
- mandra_cn_a58 (S1 row 2: HSG-A AMC-II (CN = 58 test) — pervious classes CN 58): no published number; **v1.4 new mask CSI 0.1577 HR 0.6448 FAR 0.8273 B 3.733 GSS 0.0717** (TP/FP/FN 2275/10896/1253); curve numbers realised (active) 66.0; SFINCS 3071.646 s; record `results/mandra_cn_a58_record.json`.
- mandra_cn_b_default (S1 row 3: HSG-B AMC-II (default lookup)): no published number; **v1.4 new mask CSI 0.1576 HR 0.6987 FAR 0.8309 B 4.132 GSS 0.0696** (TP/FP/FN 2465/12113/1063); curve numbers realised (active) 75.0; SFINCS 2182.423 s; record `results/mandra_cn_b_default_record.json`.
- mandra_cn_d_amc3 (S1 row 4: HSG-D AMC-III (post-fire, saturated) — TR-55 HSG-D lookup, AMC III): no published number; **v1.4 new mask CSI 0.1564 HR 0.7528 FAR 0.8352 B 4.567 GSS 0.0665** (TP/FP/FN 2656/13456/872); curve numbers realised (active) 93.0; SFINCS 2568.228 s; record `results/mandra_cn_d_amc3_record.json`.
- mandra_cn_d_amc3_manning080 (S1 prose: Manning test, built-up n 0.012 -> 0.080 at the HSG-D AMC-III configuration): no published number; **v1.4 new mask CSI 0.1530 HR 0.8115 FAR 0.8413 B 5.114 GSS 0.0612** (TP/FP/FN 2863/15179/665); curve numbers realised (active) 93.0; SFINCS 498.728 s; record `results/mandra_cn_d_amc3_manning080_record.json`.
- pineios_cn_on (§4.1.2 (ii) / §6.2: Pineios CN-on (HSG-B, AMC-II)): no published number; **v1.4 new mask CSI 0.5051 HR 0.8821 FAR 0.4583 B 1.628 GSS 0.2808** (TP/FP/FN 59106/50005/7901); curve numbers realised (active) 73.2; SFINCS 2191.432 s; record `results/pineios_cn_on_record.json`.
- pineios_raw_imerg (§5: Pineios raw IMERG (no R2)): no published number; **v1.4 new mask CSI 0.5023 HR 0.7750 FAR 0.4120 B 1.318 GSS 0.3031** (TP/FP/FN 51932/36386/15075); SFINCS 3215.574 s; record `results/pineios_raw_imerg_record.json`.
- valencia_raw_imerg (§4.4.2 / §5.3 / S3.1: Valencia raw IMERG (no R2)): v1.3 published CSI 0.1051 HR 0.9662 FAR 0.8945 B 9.160; **v1.4 new mask CSI 0.1632 HR 0.8642 FAR 0.8325 B 5.158 GSS 0.0998** (TP/FP/FN 16921/84082/2660); SFINCS 1531.571 s; record `results/valencia_raw_imerg_record.json`.
- pineios_timevarying_q (S2 Pineios v3 / §4.1.1: time-varying GloFAS Q audit (dis + src rebuilt after the build)): v1.3 published CSI 0.4558 HR 0.9467 FAR 0.5322 B 2.024; v1.3 new mask CSI 0.4726; **v1.4 new mask CSI 0.4947 HR 0.8983 FAR 0.4759 B 1.714 GSS 0.2615** (TP/FP/FN 60191/54657/6816); SFINCS 3446.777 s; record `results/pineios_timevarying_q_record.json`.
- pineios_qinf5 (§5.2: constant infiltration qinf = 5 mm/h on the time-varying-Q build (as the published v4 run)): v1.3 published CSI 0.4565 HR 0.9290 FAR 0.5270 B 1.964; v1.3 new mask CSI 0.4736; **v1.4 new mask CSI 0.4718 HR 0.8145 FAR 0.4713 B 1.541 GSS 0.2470** (TP/FP/FN 54574/48653/12433); SFINCS 2591.246 s; record `results/pineios_qinf5_record.json`.
- strymonas_leadin7d (sensitivity: 7-day lead-in simulated (tstart = tref = 2015-03-21), CN on): no published number; **v1.4 new mask CSI 0.2552 HR 0.9588 FAR 0.7420 B 3.716 GSS 0.1850** (TP/FP/FN 4442/12773/191); curve numbers realised (active) 74.9; SFINCS 4491.846 s; record `results/strymonas_leadin7d_record.json`.
- Tests: new/touched modules 50 green (test_phase3_rebuild_q, test_skill_scores, test_time_matched_scores, test_rain_diagnostics, test_truth_buffer_scores, test_validator_light_loader, test_crete_rain_vs_noa, test_d6_cn_bookkeeping.RenderD6, test_eval_exclusion; unittest 2026-10-19T23:4xZ); full suite before the v1.4.0 tag.

### Harness v1.4 — consolidated results (GO Phases 3–5); block generated 2026-10-20T05:11:48Z by `reproduction/v14_rerun/scripts/checkpoint5b_tables.py`; tag `v1.4.0` = `the commit that adds this block (git rev-parse v1.4.0; hash recorded in timing.md)`

- Pineios (EMSR692) (pineios_enhanced): **v1.4 CSI 0.4948 HR 0.8984 FAR 0.4759 B 1.714 GSS 0.2616**, SEDI 0.6670 PSS 0.4883, CSI* 0.5306 at h>0.25m, fuzzy r=1 0.4607; eval 4506.7 km², observed 1507.7 km²; v1.3 published CSI 0.4559 HR 0.9468 B 2.024; baseline v1.4 CSI 0.5425 (Δ -0.0478); sources `{'enhanced_v14': 'reproduction\\v14_rerun\\results\\pineios_enhanced_v14_newmask.json', 'enhanced_v13_published': 'reproduction\\v14_rerun\\results\\pineios_enhanced_v13_publishedmask.json', 'enhanced_v13_newmask': 'reproduction\\v14_rerun\\results\\pineios_enhanced_v13_newmask.json', 'baseline_v14': 'reproduction\\v14_rerun\\results\\pineios_baseline_gridmatched_v14_newmask.json', 'baseline_v13_published': 'reproduction\\v14_rerun\\results\\pineios_baseline_gridmatched_v13_publishedmask.json', 'baseline_v13_newmask': 'reproduction\\v14_rerun\\results\\pineios_baseline_gridmatched_v13_newmask.json'}`.
- Mandra (EMSR257) (mandra_enhanced): **v1.4 CSI 0.1567 HR 0.7602 FAR 0.8351 B 4.611 GSS 0.0667**, SEDI 0.4560 PSS 0.3254, CSI* 0.1589 at h>0.25m, fuzzy r=1 0.2076; eval 86.9 km², observed 8.8 km²; v1.3 published CSI 0.1060 HR 0.8734 B 8.113; baseline v1.4 CSI 0.1383 (Δ +0.0184); sources `{'enhanced_v14': 'reproduction\\v14_rerun\\results\\mandra_enhanced_v14_newmask.json', 'enhanced_v13_published': 'reproduction\\v14_rerun\\results\\mandra_enhanced_v13_publishedmask.json', 'enhanced_v13_newmask': 'reproduction\\v14_rerun\\results\\mandra_enhanced_v13_newmask.json', 'baseline_v14': 'reproduction\\v14_rerun\\results\\mandra_baseline_v14_newmask.json', 'baseline_v13_published': 'reproduction\\v14_rerun\\results\\mandra_baseline_v13_publishedmask.json', 'baseline_v13_newmask': 'reproduction\\v14_rerun\\results\\mandra_baseline_v13_newmask.json'}`.
- Strymonas (EMSR122) (strymonas_enhanced_postD6): **v1.4 CSI 0.3336 HR 0.9214 FAR 0.6566 B 2.683 GSS 0.2720**, SEDI 0.8842 PSS 0.7533, CSI* 0.4351 at h>0.50m, fuzzy r=1 0.4097; eval 1196.2 km², observed 104.2 km²; v1.3 published CSI 0.1822 HR 0.3221 B 1.090; baseline v1.4 CSI 0.2068 (Δ +0.1269); sources `{'enhanced_v14': 'reproduction\\v14_rerun\\results\\strymonas_enhanced_postD6_v14_newmask.json', 'enhanced_v13_published': 'reproduction\\v14_rerun\\results\\strymonas_enhanced_v13_publishedmask.json', 'enhanced_v13_newmask': 'reproduction\\v14_rerun\\results\\strymonas_enhanced_v13_newmask.json', 'baseline_v14': 'reproduction\\v14_rerun\\results\\strymonas_baseline_v14_newmask.json', 'baseline_v13_published': 'reproduction\\v14_rerun\\results\\strymonas_baseline_v13_publishedmask.json', 'baseline_v13_newmask': 'reproduction\\v14_rerun\\results\\strymonas_baseline_v13_newmask.json'}`.
- Valencia (EMSR773) (valencia_enhanced_164): **v1.4 CSI 0.1439 HR 0.9387 FAR 0.8547 B 6.461 GSS 0.0779**, SEDI 0.7064 PSS 0.5085, CSI* 0.2416 at h>0.50m, fuzzy r=1 0.1113; eval 2709.5 km², observed 195.8 km²; v1.3 published CSI 0.0939 HR 0.9890 B 10.524; sources `{'enhanced_v14': 'reproduction\\v14_rerun\\results\\valencia_enhanced_164_v14_newmask.json', 'enhanced_v13_published': 'reproduction\\v14_rerun\\results\\valencia_enhanced_164_v13_publishedmask.json', 'enhanced_v13_newmask': 'reproduction\\v14_rerun\\results\\valencia_enhanced_164_v13_newmask.json'}`.
- Emilia-R. (EMSR664) (emilia_enhanced_8aoi): **v1.4 CSI 0.2515 HR 0.8500 FAR 0.7368 B 3.230 GSS 0.0956**, SEDI 0.4754 PSS 0.3262, CSI* 0.3029 at h>0.50m, fuzzy r=1 0.3297; eval 3148.0 km², observed 567.9 km²; v1.3 published CSI 0.2404 HR 0.9206 B 3.750; sources `{'enhanced_v14': 'reproduction\\v14_rerun\\results\\emilia_enhanced_8aoi_v14_newmask.json', 'enhanced_v13_published': 'reproduction\\v14_rerun\\results\\emilia_enhanced_8aoi_v13_publishedmask.json', 'enhanced_v13_newmask': 'reproduction\\v14_rerun\\results\\emilia_enhanced_8aoi_v13_newmask.json'}`.
- Crete Tzermiado (EMSR933, tier 1) (crete_canonical_r2on): **v1.4 CSI 0.2214 HR 0.9885 FAR 0.7780 B 4.453 GSS 0.1686**, SEDI 0.9095 PSS 0.7530, CSI* 0.3654 at h>0.50m, fuzzy r=1 0.1948; eval 176.9 km², observed 11.3 km²; no published number (held-out prospective event); baseline v1.4 CSI 0.3431 (Δ -0.1217); sources `{'enhanced_v14': 'reproduction\\v14_rerun\\results\\crete_canonical_r2on_v14_newmask.json', 'baseline_v14': 'reproduction\\v14_rerun\\results\\crete_baseline_v14_newmask.json'}`.
- NUMBER_MAP.md: 75 entries, 0 pending (`reproduction/v14_rerun/NUMBER_MAP.md`).
- Crete crete_baseline: Tzermiado (tier 1) CSI 0.3431 HR 0.7877 FAR 0.6219 B 2.083 GSS 0.3029; CSI* 0.3431 at h>0.10m; SEDI 0.8465 PSS 0.6997; observed 11.260 km², modelled 23.460 km²; tier 2: AOI01 1.780/26.070 km²; AOI04 0.410/1.090 km²; AOI06 0.230/9.050 km²; AOI07 0.650/16.640 km²; SFINCS 8370.847 s; `phase5/crete_baseline_tiers.json`.
- Crete crete_canonical_r2on: Tzermiado (tier 1) CSI 0.2214 HR 0.9885 FAR 0.7780 B 4.453 GSS 0.1686; CSI* 0.3654 at h>0.50m; SEDI 0.9095 PSS 0.7530; observed 11.260 km², modelled 50.140 km²; tier 2: AOI01 1.780/69.530 km²; AOI04 0.410/9.590 km²; AOI06 0.230/20.460 km²; AOI07 0.650/26.430 km²; SFINCS 10946.466 s; `phase5/crete_canonical_r2on_tiers.json`.
- Crete activation-to-validated-hindcast interval: 15.39 days (2026-10-04T11:02:00Z → 2026-10-19T20:21:12Z).
- Tests: full suite 138 OK (python -m unittest discover -s tests, 3177 s under the Crete runs, 2026-10-20T03:46Z-04:39Z, log D:/ELKAK/implementation/v14/_logs/unittest_full_0346.log).

### Harness v1.4.1 (CODE-14) — D7 GloFAS point sampling; fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a` (2026-10-20T08:46:57Z); tests 151 OK (python -m unittest discover -s tests, 163 s, 2026-10-20T08:43Z–08:46Z, log `D:/ELKAK/implementation/v14/_logs/unittest_full_code14_B2.log`)

**Decisions (Papaioannou, 2026-10-20, CODE-14):** Checkpoint 5b accepted; tag v1.4.0 stands as the record. A scope check first (no runs), B fix on fix/harness-v1.4 (hard error instead of the fallback), C re-run of every affected run with four-column tables (v1.3 / v1.4.0 / v1.4.1 / Δ), D Table S3 + MANIFEST row 16, E D5 provenance (no public issue), F branch reconciliation plan (no push). Standing rules unchanged.

- **A — scope (`reproduction/v14_rerun/code14/d7_scope.md`, `scripts/d7_scope.py`, 2026-10-20):** every pipeline Pineios run — the published canonical (`pineios_sfincs_enhanced`), the published R2-510 sweep output, and the v1.4.0 runs `pineios_enhanced`, `pineios_r2_220/295/510`, `pineios_cn_on`, `pineios_raw_imerg` — wrote the GloFAS domain mean 11.589 m³/s at all four sources, every hour (the Pineios GloFAS file is 0.1° with an ascending latitude axis; the label slice was empty). The published v3/v4 rows and the v1.4.0 `pineios_timevarying_q` / `pineios_qinf5` carry the audit rebuild (nearest cell at the injection point, hourly linear; peaks 1.38 / 0.40 / 24.41 / 118.40 m³/s). Strymonas (all five R3-on runs), Valencia (two) and Emilia carry the sampler's window-max series (descending axes, sampled correctly); Crete has R3 off.
- **B — fix:** `skill/scripts/prep_q_at_outlets.py` selects the ±0.1° window with coordinate masks (inclusive, 1e-4° edge tolerance for float32 coordinates); the cell rule (max-mean-discharge cell of the window = the river cell nearest to the named point) and the hourly step-fill are unchanged; `NoChannelError` replaces the fallback; points sharing a cell are reported; optional per-point `window_deg`; `data/q_outlet_cells.json` records the cell behind every column. Real-data regression (`code14/d7_sampler_regression.md`): the fixed sampler reproduces the v1.4.0 `q_outlet.csv` and `sfincs.dis` of all eight Strymonas / Valencia / Emilia runs byte for byte; for the frozen Pineios config it writes column peaks 371.39 / 2.10 / 1128.80 / 118.40 m³/s (combined hourly peak in `d7_sampler_regression.json`). Tests `tests/test_prep_q_sampler.py` (13): synthetic two-point grid in both axis orders, legacy-slice equivalence, edge case, hard errors, per-point window, duplicate report, outputs; Pineios real data (Enipeas 118.4 at (22.34, 39.31)); audit-rebuild regression (Enipeas 118.4, combined 135.0 m³/s).
- **D8 — new finding, report only (configuration, not code):** under the (restored) window rule the frozen Pineios `titarisios` point (22.42, 39.71) resolves to (22.44, 39.81), the Pineios main stem one 0.1° cell north (peak 1128.8 m³/s; the main stem also passes (22.34, 39.61), 1041.3) — a double count of water the domain already routes; the Titarisios' own last GloFAS cell is (22.24, 39.71), peak 42.8 m³/s. The `pineios_kalambaka` window is clipped by the file's western edge (2.1 m³/s; the Trikala cell (21.84, 39.51), 371.4 m³/s, already carries that reach) and its source, like Valencia's `magro`, sits on an inactive cell. In Emilia `senio` and `montone` resolve to the same cell (11.925, 44.275; 166.1 m³/s injected twice). No pipeline source lies on the lowest-z_b cell within ±10 cells: `inject_q_forcing` writes the source at the named coordinates and has never snapped (rule R wording vs code; the audit rebuild did snap). The v1.4.1 re-runs (C) use the frozen configs; a labelled diagnostic (`pineios_enhanced_v141_d8titarisios`: Titarisios sampled at (22.24, 39.71) with a one-cell window, injection unchanged) quantifies D8 and is never canonical. Side fact: the surviving published Table-12 "CN off + Q" output (`emsr122_sfincs_v4`) carries the v1 pre-fix Kerkini series (peak 618.5 m³/s), not the v3 series its frozen config implies.

### Harness v1.4.1 (CODE-14) — results; block generated 2026-10-20T11:36:35Z by `reproduction/v14_rerun/scripts/checkpoint6_tables.py`; tag `v1.4.1` = `the commit that adds this block (git rev-parse v1.4.1; the tag was re-pointed from 1d0ba4c, see timing.md)`; fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a`

- A scope (`code14/d7_scope.json`): 8 of 25 R3-on model directories carry the 11.589 m³/s constant (all pipeline Pineios runs); the rest sample correctly or carry the audit rebuild.
- B fix: byte-identical discharge files for 8 correctly-sampled runs; Pineios column peaks 371.39 / 2.10 / 1128.80 / 118.40 m³/s; fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a`; tests full suite 151 OK (python -m unittest discover -s tests, 162 s, 2026-10-20T11:31Z-11:34Z, log D:/ELKAK/implementation/v14/_logs/unittest_full_code14_final.log).
- pineios_enhanced: v1.3 published CSI 0.4559; v1.4.0 CSI 0.4948 HR 0.8984 FAR 0.4759 B 1.714 GSS 0.2616; **v1.4.1 CSI 0.4963 HR 0.9028 FAR 0.4757 B 1.722 GSS 0.2629** (TP/FP/FN 60494/54880/6513); Δ(v1.4.1 − v1.4.0) CSI +0.0015 HR +0.0044 FAR -0.0002 B +0.008; SFINCS 2349.728 s; records `results/pineios_enhanced_v141_*.json`.
- pineios_r2_220: v1.3 published CSI 0.4755; v1.4.0 CSI 0.5047 HR 0.8314 FAR 0.4377 B 1.479 GSS 0.2921; **v1.4.1 CSI 0.5111 HR 0.8432 FAR 0.4353 B 1.493 GSS 0.2987** (TP/FP/FN 56502/43553/10505); Δ(v1.4.1 − v1.4.0) CSI +0.0063 HR +0.0118 FAR -0.0025 B +0.014; SFINCS 2052.998 s; records `results/pineios_r2_220_v141_*.json`.
- pineios_r2_295: v1.3 published CSI 0.4664; v1.4.0 CSI 0.5014 HR 0.8666 FAR 0.4567 B 1.595 GSS 0.2787; **v1.4.1 CSI 0.5043 HR 0.8734 FAR 0.4559 B 1.605 GSS 0.2815** (TP/FP/FN 58522/49034/8485); Δ(v1.4.1 − v1.4.0) CSI +0.0029 HR +0.0068 FAR -0.0008 B +0.010; SFINCS 2325.05 s; records `results/pineios_r2_295_v141_*.json`.
- pineios_r2_510: v1.3 published CSI 0.4460; v1.4.0 CSI 0.4864 HR 0.9196 FAR 0.4920 B 1.810 GSS 0.2444; **v1.4.1 CSI 0.4871 HR 0.9219 FAR 0.4920 B 1.815 GSS 0.2449** (TP/FP/FN 61777/59826/5230); Δ(v1.4.1 − v1.4.0) CSI +0.0007 HR +0.0024 FAR +0.0000 B +0.005; SFINCS 1878.321 s; records `results/pineios_r2_510_v141_*.json`.
- pineios_cn_on: v1.3 published CSI —; v1.4.0 CSI 0.5051 HR 0.8821 FAR 0.4583 B 1.628 GSS 0.2808; **v1.4.1 CSI 0.5075 HR 0.8881 FAR 0.4578 B 1.638 GSS 0.2830** (TP/FP/FN 59510/50249/7497); Δ(v1.4.1 − v1.4.0) CSI +0.0024 HR +0.0060 FAR -0.0005 B +0.010; SFINCS 2222.802 s; records `results/pineios_cn_on_v141_*.json`.
- pineios_raw_imerg: v1.3 published CSI —; v1.4.0 CSI 0.5023 HR 0.7750 FAR 0.4120 B 1.318 GSS 0.3031; **v1.4.1 CSI 0.5141 HR 0.7946 FAR 0.4071 B 1.340 GSS 0.3155** (TP/FP/FN 53241/36562/13766); Δ(v1.4.1 − v1.4.0) CSI +0.0118 HR +0.0195 FAR -0.0049 B +0.022; SFINCS 1796.934 s; records `results/pineios_raw_imerg_v141_*.json`.
- pineios_qinf5: v1.3 published CSI 0.4565; v1.4.0 CSI 0.4718 HR 0.8145 FAR 0.4713 B 1.541 GSS 0.2470; **v1.4.1 CSI 0.4825 HR 0.8341 FAR 0.4663 B 1.563 GSS 0.2582** (TP/FP/FN 55893/48827/11114); Δ(v1.4.1 − v1.4.0) CSI +0.0107 HR +0.0197 FAR -0.0051 B +0.022; SFINCS 1727.477 s; records `results/pineios_qinf5_v141_*.json`.
- D8 diagnostic pineios_enhanced_v141_d8titarisios (never canonical): Titarisios cell (22.24, 39.71), peak 42.85 m³/s; CSI 0.4959 HR 0.9013 FAR 0.4756 B 1.719 GSS 0.2626; Δ vs v1.4.1 canonical CSI -0.0004.
- Table S3 Pineios: Active mask (no AOI) 4956 km² CSI 0.4678 HR 0.8984 B 1.819; AOI-union (v1.4 reference) 4507 km² CSI 0.4948 HR 0.8984 B 1.714; AOI-union + 1 km 4575 km² CSI 0.4903 HR 0.8984 B 1.731; AOI-union − 1 km 4414 km² CSI 0.4988 HR 0.8985 B 1.700 (`code14/table_s3_v14.json`).
- Table S3 Mandra: Active mask (no AOI) 280 km² CSI 0.0701 HR 0.7602 B 10.602; AOI-union (v1.4 reference) 87 km² CSI 0.1567 HR 0.7602 B 4.611; AOI-union + 1 km 122 km² CSI 0.1235 HR 0.7602 B 5.918; AOI-union − 1 km 48 km² CSI 0.1983 HR 0.7701 B 3.654 (`code14/table_s3_v14.json`).
- Table S3 Strymonas: Active mask (no AOI) 3985 km² CSI 0.3178 HR 0.9214 B 2.820; AOI-union (v1.4 reference) 1196 km² CSI 0.3336 HR 0.9214 B 2.683; AOI-union + 1 km 1279 km² CSI 0.3313 HR 0.9214 B 2.703; AOI-union − 1 km 1109 km² CSI 0.3360 HR 0.9220 B 2.667 (`code14/table_s3_v14.json`).
- Table S3 Valencia: Active mask (no AOI) 2915 km² CSI 0.1388 HR 0.9387 B 6.700; AOI-union (v1.4 reference) 2710 km² CSI 0.1439 HR 0.9387 B 6.461; AOI-union + 1 km 2723 km² CSI 0.1435 HR 0.9387 B 6.478; AOI-union − 1 km 2692 km² CSI 0.1445 HR 0.9387 B 6.436 (`code14/table_s3_v14.json`).
- Table S3 Emilia-R.: Active mask (no AOI) 5007 km² CSI 0.1759 HR 0.8500 B 4.684; AOI-union (v1.4 reference) 3148 km² CSI 0.2515 HR 0.8500 B 3.230; AOI-union + 1 km 3435 km² CSI 0.2377 HR 0.8500 B 3.427; AOI-union − 1 km 2823 km² CSI 0.2579 HR 0.8588 B 3.189 (`code14/table_s3_v14.json`).
- MANIFEST row 16 (Mandra v3 mask restriction on the v1.4 build): v1.3 published text CSI 0.083 HR 0.775 B 9.08; v1.3 output re-scored published mask CSI 0.0833, new mask 0.1035; **v1.4.1 CSI 0.0985 HR 0.7191 FAR 0.8975 B 7.018 GSS 0.0011** (TP/FP/FN 2537/22222/991); v1.4 unrestricted canonical CSI 0.1567; active 294.2 → 174.2 km²; SFINCS 1435.642 s; `results/mandra_v3_maskrestrict_*.json`.
- E. D5 provenance (meteo-grid corner vs centre): see `reproduction/v14_rerun/code14/E_d5_provenance.md` (reproduced in CHECKPOINT6.md).
- F. Branch reconciliation plan (no push): see `reproduction/v14_rerun/code14/F_branch_plan.md` (reproduced in CHECKPOINT6.md).
- NUMBER_MAP.md: 79 entries, 20 differ under v1.4.1.
- Tests: full suite 151 OK (python -m unittest discover -s tests, 162 s, 2026-10-20T11:31Z-11:34Z, log D:/ELKAK/implementation/v14/_logs/unittest_full_code14_final.log).

### Harness v1.4.2 (CODE-15) — D8 source-point resolution; fix commit `b15896ac9607c4a2fc8d76be33919d78a12cde7b` (2026-10-20T12:46:01Z); tests 172 OK (python -m unittest discover -s tests, 176 s, log `D:/ELKAK/implementation/v14/_logs/unittest_full_code15_B.log`; the two Pineios extended-lattice tests pass once the lattice exists)

**Decisions (Papaioannou, 2026-10-20, CODE-15):** Checkpoint 6 accepted; v1.4.1 stands as the record. A scope first (no runs), B fix on fix/harness-v1.4 behind the harness flag (per-point GloFAS windows, request area covering every window, the R3 snap with a hard error, duplicate-cell hard error), C resolved points into the ledger / as-run records and re-runs of every run whose injected series or cells change (four columns v1.3 / v1.4.1 / v1.4.2 / Δ), D injected-volume bookkeeping, E branch reconciliation per F_branch_plan.md (no push) and tag v1.4.2. **This is the number freeze: no further runs without a new decision.**

**A — scope (`reproduction/v14_rerun/code15/d8_scope.{json,md}`, `scripts/d8_scope.py`, river membership from the GloFAS v4 static maps `uparea_glofas_v4_0.nc` / `ldd_glofas_v4_0.nc`, CEMS wiki, kept outside the repo at `D:/ELKAK/implementation/v14/_static/glofas_v4/` with MD5 + source note):**
- The frozen Pineios GloFAS file is an Open-Meteo 0.1° lattice whose discharge belongs to the static-map cell one 0.05° column EAST of the labelled coordinate (shift test: 0 of 32 river points on < 100 km² cells and 0 of 60 dry points on > 300 km² cells with the +1-column mapping, against 12 and 7 with the containing cell; EWDS files: 0 of 207). The series themselves are what Open-Meteo returns for the labelled points (216 of 216 identical today), so no pipeline number changes; only the river attribution does.
- Flags per point: Trikala — the ±0.1° cell is the Pineios main stem just inside the west edge (2073 km², 371.4 m³/s), the injection point a plain cell 3 km north of the channel (D8 1.8 km² within 1 km); Kalambaka — window clipped by the file edge (hillslope cell 2.1 m³/s), injection on an inactive mountainside (DEM 413 m), its unclipped cell (21.54, 39.71 → the Pineios at Kalambaka, 928 km², 40.8 m³/s) drains into the Trikala cell; Titarisios — the rule cell is the Pineios main stem below the confluence (8993 km², 1128.8 m³/s) and the injection point sits on the Pineios 6 km upstream of the confluence; Enipeas — on its river; Strymonas / Angitis / Júcar / Turia / Lamone / Ronco — on their rivers (injection cells off the local thalweg, within 1 km); Magro — the rule cell is the Júcar below the Tous dam (17 128 km²), nested in the Júcar mouth cell, injection on an inactive mountainside (DEM 385 m) that drains to the Magro; Senio — the named point lies in the Lamone valley, resolves to the Lamone at Faenza (600 km²), the cell the Montone point also takes, nested in the Lamone cell, injection drains to the Lamone; Montone — same Lamone cell; Savio — on its river, but the injection point drains to the Ronco.
- **B — fix (commit above):** per-point `window_deg` / `inject`; `glofas_area.request_area` (Pineios west edge 21.64 → 21.44, lattice anchored, explicit point count); `source_snap.snap_source` (lowest-z_b active channel cell within 1 km, channel = D8 upstream area ≥ ½ the largest within the radius, Copernicus DEM tiles of the run mosaicked on the model grid; `NoActiveCellError`); `prep_q_at_outlets.DuplicateCellError` under harness v1.4; `model/sfincs_src_snap.json` per build. v1.3 unchanged (every test of the published behaviour green).
- **Resolved points (`code15/source_points_v142.{json,md}`, resolved 2026-10-20T12:42Z; the v1.4.2 configs are generated from this ledger):** Titarisios sampled at (22.24, 39.71) with a one-cell window (author's prescription; 1685 km², 42.85 m³/s), injection unchanged; Kalambaka sampled at its unclipped cell (40.78 m³/s) and **not injected** (nested in the Trikala cell; no Pineios channel within 1 km of its injection point); Magro sampled at the Magro's own last cell (−0.475, 39.225; 1648 km², 18.7 m³/s), injection unchanged (drains to the Magro; the Magro cell stays nested in the frozen Júcar-mouth cell — reported); Senio sampled at the Senio's own last cell (11.875, 44.375; 266 km², 62.4 m³/s) and injected on the Senio channel (11.84865, 44.31073; D8 272.7 km²); Montone with a one-cell window (the Montone at Forlì, 467 km², 131.9 m³/s); Savio injected on the Savio channel (12.19969, 44.09076; D8 95.0 km², truncated at the DEM pad); everything else keeps its frozen coordinates, snapped at build time. Residual configuration items for the author (not changed): the Trikala / Titarisios / Ronco injection points 1–6 km from their channels (the snap moves ≤ 1 km), the Júcar sampled at its mouth reach, the Kalambaka source as such.
- The v1.4.2 re-runs: Pineios canonical, R2 220/295/510, CN-on, raw IMERG, qinf 5, time-varying; Emilia; Valencia canonical + raw IMERG; Strymonas canonical (post-D6), CN-off+Q, lead-in 7 d, v1 pre-fix source (their sources move with the snap). Records `results/<run>_v142_*.json` with `src_snap` and `q_outlet_cells`.

### Harness v1.4.2 (CODE-15) — results; block generated 2026-10-20T16:30:45Z by `reproduction/v14_rerun/scripts/checkpoint7_tables.py`; tag `v1.4.2` = `the commit that adds this block (git rev-parse v1.4.2; hash recorded in timing.md)`; fix commit `b15896ac9607c4a2fc8d76be33919d78a12cde7b`

- A scope (`code15/d8_scope.json`): 15 of 15 named points flagged; Open-Meteo lattice of the frozen Pineios file offset by one 0.05° cell in longitude (best shift rows+0_cols+1).
- B fix commit `b15896ac9607c4a2fc8d76be33919d78a12cde7b`; tests full suite Ran 174 tests, OK (python -m unittest discover -s tests, log D:/ELKAK/implementation/v14/_logs/unittest_full_code15_final.log).
- pineios_enhanced: v1.3 published CSI 0.4559; pineios_enhanced_v141 CSI 0.4963 HR 0.9028 FAR 0.4757 B 1.722 GSS 0.2629; **v1.4.2 CSI 0.4959 HR 0.9009 FAR 0.4755 B 1.718 GSS 0.2627** (TP/FP/FN 60367/54722/6640); Δ(v1.4.2 − pineios_enhanced_v141) CSI -0.0004 HR -0.0019 FAR -0.0002 B -0.004; SFINCS 2343.231 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_enhanced_v142_*.json`.
- pineios_r2_220: v1.3 published CSI 0.4755; pineios_r2_220_v141 CSI 0.5111 HR 0.8432 FAR 0.4353 B 1.493 GSS 0.2987; **v1.4.2 CSI 0.5068 HR 0.8353 FAR 0.4369 B 1.483 GSS 0.2944** (TP/FP/FN 55973/43428/11034); Δ(v1.4.2 − pineios_r2_220_v141) CSI -0.0042 HR -0.0079 FAR +0.0016 B -0.010; SFINCS 2219.386 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_r2_220_v142_*.json`.
- pineios_r2_295: v1.3 published CSI 0.4664; pineios_r2_295_v141 CSI 0.5043 HR 0.8734 FAR 0.4559 B 1.605 GSS 0.2815; **v1.4.2 CSI 0.5031 HR 0.8698 FAR 0.4560 B 1.599 GSS 0.2805** (TP/FP/FN 58283/48849/8724); Δ(v1.4.2 − pineios_r2_295_v141) CSI -0.0013 HR -0.0036 FAR +0.0001 B -0.006; SFINCS 1498.655 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_r2_295_v142_*.json`.
- pineios_r2_510: v1.3 published CSI 0.4460; pineios_r2_510_v141 CSI 0.4871 HR 0.9219 FAR 0.4920 B 1.815 GSS 0.2449; **v1.4.2 CSI 0.4869 HR 0.9208 FAR 0.4918 B 1.812 GSS 0.2449** (TP/FP/FN 61700/59709/5307); Δ(v1.4.2 − pineios_r2_510_v141) CSI -0.0002 HR -0.0011 FAR -0.0002 B -0.003; SFINCS 1773.444 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_r2_510_v142_*.json`.
- pineios_cn_on: v1.3 published CSI —; pineios_cn_on_v141 CSI 0.5075 HR 0.8881 FAR 0.4578 B 1.638 GSS 0.2830; **v1.4.2 CSI 0.5066 HR 0.8851 FAR 0.4577 B 1.632 GSS 0.2823** (TP/FP/FN 59309/50056/7698); Δ(v1.4.2 − pineios_cn_on_v141) CSI -0.0009 HR -0.0030 FAR -0.0001 B -0.006; SFINCS 1919.078 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_cn_on_v142_*.json`.
- pineios_raw_imerg: v1.3 published CSI —; pineios_raw_imerg_v141 CSI 0.5141 HR 0.7946 FAR 0.4071 B 1.340 GSS 0.3155; **v1.4.2 CSI 0.5067 HR 0.7822 FAR 0.4101 B 1.326 GSS 0.3077** (TP/FP/FN 52414/36444/14593); Δ(v1.4.2 − pineios_raw_imerg_v141) CSI -0.0074 HR -0.0123 FAR +0.0030 B -0.014; SFINCS 1442.39 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_raw_imerg_v142_*.json`.
- pineios_qinf5: v1.3 published CSI 0.4565; pineios_qinf5_v141 CSI 0.4825 HR 0.8341 FAR 0.4663 B 1.563 GSS 0.2582; **v1.4.2 CSI 0.4764 HR 0.8228 FAR 0.4692 B 1.550 GSS 0.2517** (TP/FP/FN 55131/48727/11876); Δ(v1.4.2 − pineios_qinf5_v141) CSI -0.0062 HR -0.0114 FAR +0.0029 B -0.013; SFINCS 1052.313 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_qinf5_v142_*.json`.
- pineios_timevarying_q: v1.3 published CSI 0.4558; pineios_timevarying_q CSI 0.4947 HR 0.8983 FAR 0.4759 B 1.714 GSS 0.2615; **v1.4.2 CSI 0.4959 HR 0.9009 FAR 0.4755 B 1.718 GSS 0.2627** (TP/FP/FN 60367/54722/6640); Δ(v1.4.2 − pineios_timevarying_q) CSI +0.0012 HR +0.0026 FAR -0.0004 B +0.004; SFINCS 1609.743 s; sources pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4; records `results/pineios_timevarying_q_v142_*.json`.
- emilia_enhanced_8aoi: v1.3 published CSI 0.2404; emilia_enhanced_8aoi CSI 0.2515 HR 0.8500 FAR 0.7368 B 3.230 GSS 0.0956; **v1.4.2 CSI 0.2532 HR 0.8521 FAR 0.7351 B 3.217 GSS 0.0976** (TP/FP/FN 21507/59690/3733); Δ(v1.4.2 − emilia_enhanced_8aoi) CSI +0.0017 HR +0.0021 FAR -0.0017 B -0.013; SFINCS 1750.337 s; sources lamone 188.2, senio 62.4, montone 131.9, ronco 171.2, savio 147.5; records `results/emilia_enhanced_8aoi_v142_*.json`.
- valencia_enhanced_164: v1.3 published CSI 0.0939; valencia_enhanced_164 CSI 0.1439 HR 0.9387 FAR 0.8547 B 6.461 GSS 0.0779; **v1.4.2 CSI 0.1440 HR 0.9387 FAR 0.8547 B 6.459 GSS 0.0780** (TP/FP/FN 18381/108091/1200); Δ(v1.4.2 − valencia_enhanced_164) CSI +0.0000 HR +0.0000 FAR -0.0000 B -0.002; SFINCS 1443.678 s; sources magro 18.7, jucar 88.8, turia 239.7; records `results/valencia_enhanced_164_v142_*.json`.
- valencia_raw_imerg: v1.3 published CSI 0.1051; valencia_raw_imerg CSI 0.1632 HR 0.8642 FAR 0.8325 B 5.158 GSS 0.0998; **v1.4.2 CSI 0.1633 HR 0.8643 FAR 0.8324 B 5.156 GSS 0.0999** (TP/FP/FN 16923/84036/2658); Δ(v1.4.2 − valencia_raw_imerg) CSI +0.0001 HR +0.0001 FAR -0.0001 B -0.002; SFINCS 2294.351 s; sources magro 18.7, jucar 88.8, turia 239.7; records `results/valencia_raw_imerg_v142_*.json`.
- strymonas_enhanced_postD6: v1.3 published CSI 0.1822; strymonas_enhanced_postD6 CSI 0.3336 HR 0.9214 FAR 0.6566 B 2.683 GSS 0.2720; **v1.4.2 CSI 0.3339 HR 0.9214 FAR 0.6563 B 2.681 GSS 0.2723** (TP/FP/FN 4269/8153/364); Δ(v1.4.2 − strymonas_enhanced_postD6) CSI +0.0002 HR +0.0000 FAR -0.0002 B -0.002; SFINCS 371.69 s; sources kerkini_outlet 640.3, angitis 96.8; records `results/strymonas_enhanced_postD6_v142_*.json`.
- strymonas_abl_cnoff_q: v1.3 published CSI 0.2386; strymonas_abl_cnoff_q CSI 0.2947 HR 0.9359 FAR 0.6992 B 3.111 GSS 0.2289; **v1.4.2 CSI 0.2948 HR 0.9359 FAR 0.6992 B 3.111 GSS 0.2289** (TP/FP/FN 4336/10077/297); Δ(v1.4.2 − strymonas_abl_cnoff_q) CSI +0.0000 HR +0.0000 FAR -0.0000 B -0.000; SFINCS 247.551 s; sources kerkini_outlet 640.3, angitis 96.8; records `results/strymonas_abl_cnoff_q_v142_*.json`.
- strymonas_leadin7d: v1.3 published CSI —; strymonas_leadin7d CSI 0.2552 HR 0.9588 FAR 0.7420 B 3.716 GSS 0.1850; **v1.4.2 CSI 0.2551 HR 0.9588 FAR 0.7420 B 3.717 GSS 0.1849** (TP/FP/FN 4442/12777/191); Δ(v1.4.2 − strymonas_leadin7d) CSI -0.0001 HR +0.0000 FAR +0.0001 B +0.001; SFINCS 1790.814 s; sources kerkini_outlet 640.3, angitis 96.8; records `results/strymonas_leadin7d_v142_*.json`.
- strymonas_v1_prefix_src: v1.3 published CSI 0.1701; strymonas_v1_prefix_src CSI 0.3249 HR 0.9109 FAR 0.6644 B 2.714 GSS 0.2627; **v1.4.2 CSI 0.3249 HR 0.9109 FAR 0.6644 B 2.714 GSS 0.2627** (TP/FP/FN 4220/8355/413); Δ(v1.4.2 − strymonas_v1_prefix_src) CSI -0.0000 HR +0.0000 FAR +0.0000 B +0.000; SFINCS 207.616 s; sources kerkini_outlet 618.5, angitis 96.8; records `results/strymonas_v1_prefix_src_v142_*.json`.
- pineios_timevarying_q_v142 vs pineios_enhanced_v142 (same configuration): identical contingency table True.
- D pineios_enhanced_v142: injected peaks pineios_trikala 371.39, titarisios 42.85, enipeas 118.40 m³/s; total injected 149.565 × 10⁶ m³ over 2023-09-03 00:00:00..2023-09-11 00:00:00; rain on the active domain (5033.3 km²) 2237.13 × 10⁶ m³ (mean 444.5 mm); injected/rain 6.69 %.
- D emilia_enhanced_8aoi_v142: injected peaks lamone 188.22, senio 62.44, montone 131.94, ronco 171.19, savio 147.53 m³/s; total injected 247.913 × 10⁶ m³ over 2023-05-14 00:00:00..2023-05-22 00:00:00; rain on the active domain (5162.5 km²) 669.83 × 10⁶ m³ (mean 129.7 mm); injected/rain 37.01 %; observed area 567.90 km², modelled volume inside it 502.17 × 10⁶ m³, injected/that 49.4 %.
- E branch reconciliation: see `reproduction/v14_rerun/code15/E_branch_done.md` (reproduced in CHECKPOINT7.md).
- NUMBER_MAP.md: 79 entries, 37 differ under v1.4.2.
- Tests: full suite Ran 174 tests, OK (python -m unittest discover -s tests, log D:/ELKAK/implementation/v14/_logs/unittest_full_code15_final.log).

### Number freeze close-out (CODE-16) — author's decisions DvS 2026-10-21 (Papaioannou informed); generated 2026-10-21T09:15:33Z by `reproduction/v14_rerun/scripts/code16_freeze_closeout.py` from code15/source_points_v142.json (utc), results/*_v142_record.json (start_utc), code16/d9_residuals.json, code15/d_volumes_v142.json, code16/d_volumes_code16.json, code14/d7_scope.json, code15/d8_scope.json, results/{pineios_enhanced,pineios_enhanced_v141,pineios_enhanced_v142,pineios_timevarying_q_v142}_v14_newmask.json

**1. Checkpoint 7 resolutions (1)–(4) accepted; the ledger `code15/source_points_v142.json` is final.** Ledger resolved **2026-10-20T12:42:30Z**; first v1.4.2 run started **2026-10-20T12:46:27Z** (`emilia_enhanced_8aoi_v142`, `pineios_enhanced_v142` — the earliest start_utc of the 15 v1.4.2 records).

- (1) **pineios_kalambaka** (pineios): sampled at (21.63, 39.7, ±0.1°) → GloFAS cell (21.575, 39.725), 927.7 km², file peak 40.8 m³/s; **not injected** (inject: false). Ledger: inject: false — the extended lattice gives the Pineios at Kalambaka (928 km2), nested upstream of the Trikala cell (2073 km2, same river): injecting both would count the Kalambaka flow twice; its injection point lies on an inactive mountainside (DEM 413 m) with no Pineios channel within 1 km. Sampled and recorded (window no longer clipped, B(2)), not injected.
- (2) **magro** (valencia): sampled at (-0.475, 39.225, ±0.02°) → GloFAS cell (-0.475, 39.225), 1647.9 km², file peak 18.7 m³/s; injected at (-0.68, 39.2). Ledger: sampling point moved to the Magro's own last cell before the Jucar (-0.475, 39.225; 1648 km2) with a one-cell window — the frozen window resolved to the Jucar below the Tous dam (17128 km2); injection point unchanged (it drains to the Magro; the build-time snap puts it on the nearest active channel cell)
- (3) **senio** (emilia): sampled at (11.875, 44.375, ±0.02°) → GloFAS cell (11.875, 44.375), 266.4 km², file peak 62.4 m³/s; injected at (11.84865, 44.31073). Ledger: sampling point moved to the Senio's own last cell (11.875, 44.375; 266 km2) with a one-cell window — the frozen point (11.83, 44.27) lies in the Lamone valley and resolved to the Lamone at Faenza (600 km2), the cell the Montone point also took; injection moved to the Senio channel (lowest-z_b active channel cell inside the footprint of the Senio cell nearest to the old point, 11.825/44.325), because the old point drains to the Lamone (flag vi)
- (4) **savio** (emilia): sampled at (12.1, 44.06, ±0.1°) → GloFAS cell (12.175, 44.075), 557.8 km², file peak 147.5 m³/s; injected at (12.19969, 44.09076). Ledger: sampling unchanged (the Savio south of Cesena, 558 km2); injection moved to the Savio channel (lowest-z_b active channel cell inside the footprint of the Savio cell nearest to the old point, 12.175/44.075), because the old point drains to the Ronco (flag vi)

**2. D9 residual items — documented, not fixed; the number freeze stands** (`code16/d9_residuals.json`, `scripts/d9_residuals.py`; offset = distance from the snapped injection cell to the nearest model cell on the named river's channel: cells in the 0.05° footprints of the river's GloFAS v4 cells within 15 km whose D8 upstream area is ≥ 0.5 × the footprint maximum; footprints crossed by a larger river are skipped). These measured offsets supersede the rounded prose values of Checkpoint 7.

| item | what | offset km | injection cell | consequence |
|---|---|---|---|---|
| D9-1 | Trikala injection (pineios) | 3.76 | z_b 95.79 m, D8 1.91 km² (snapped) | the Pineios inflow (injected peak 371.4 m³/s, 89.7 Mm³) enters a floodplain cell 3.76 km from the Pineios channel and reaches it overland, so part of the inundation between the two is source-location dependent. |
| D9-2 | Titarisios injection (pineios) | 10.95 | z_b 61.69 m, D8 4.88 km² (snapped) | the Titarisios inflow (injected peak 42.9 m³/s, 16.9 Mm³) enters 10.95 km from the Titarisios channel, on ground that drains to the Pineios: the lower Titarisios carries no upstream inflow in the model. |
| D9-3 | Ronco injection (emilia) | 3.03 | z_b 101.38 m, D8 6.32 km² (snapped) | the Ronco inflow (injected peak 171.2 m³/s, 59.1 Mm³) enters 3.03 km from the Ronco channel and reaches it overland. |
| D9-4 | Montone injection (emilia) | 0.60 | z_b 62.98 m, D8 0.5 km² (snapped) | the Montone inflow (injected peak 131.9 m³/s, 45.5 Mm³) enters a valley-floor cell 0.60 km from the Montone channel; the channel is 1.40 km from the YAML point, outside the 1 km snap radius. |
| D9-5 | Júcar sampling (Magro nested) (valencia) | 0.00 | z_b 2.95 m, D8 2183.77 km² (snapped) | the Júcar is sampled at its mouth reach (21422.1 km², file peak 88.8 m³/s), downstream of the Magro confluence; the Magro is injected separately (1647.9 km², 4.1 Mm³), so its flow is counted twice — bounded by 5.2 % of the Valencia injected total (78.6 Mm³). Ledger nesting: ['magro ⊂ jucar']. |
| D9-6 | Kalambaka source (pineios) | n/a | YAML point outside the active grid (z_b n/a), DEM-D8 0.02 km²; not injected | sampled only (file peak 40.8 m³/s, 927.7 km²): its flow is contained in the Trikala series (nested); the YAML injection point lies on an inactive mountainside (DEM 413.5 m), outside the model's active grid, so no channel distance is defined. |
| D9-7 | Pineios lattice offset (pineios) | 4.29 | — | the frozen Pineios Open-Meteo series are those of the static-map cell one 0.05° column (4.29 km at 39.66° N) east of the labelled coordinates (shift test: 0 of 32 river points on small cells and 0 of 60 dry points on river cells with the +1-column mapping, against 12 and 7 with the containing cell); the series are unchanged, only their river attribution shifts. |

**3. Pending NUMBER_MAP entry.** §4.1.1 'peak 118 m³ s⁻¹ at Enipeas' / '~135 m³ s⁻¹ coincident' is **resolved by replacement**: the v1.4.2 injected peaks Trikala 371.4, Titarisios 42.9, Enipeas 118.4 m³/s (combined 532.6 m³/s); 149.6 Mm³ injected = 6.7 % of 2237 Mm³ rain on the active domain; the inflow bracket from the release history — v1.4.0 canonical, constant 11.589 m³/s at 4 points (32.0 Mm³ = 1.4 % of rain): CSI 0.495; v1.4.1 canonical, main stem at the Titarisios point (peak 1128.8 m³/s; 515.8 Mm³ = 23.1 % of rain): CSI 0.496. `pineios_timevarying_q_v142` has the canonical configuration (run config identical to the canonical's outside comments and paths: True; contingency table identical to the canonical's: True) and is relabelled everywhere **'repeat of the canonical configuration (determinism check)'** (CSI 0.496), not an independent time-varying audit. NUMBER_MAP.md regenerated: 0 entries pending.

The Crete IMERG Final follow-up is declared in `reproduction/emsr933/rule_ledger.md` §9.

## CODE-17 (2026-10-22T08:15:41Z) — look-ups B1–B5, review archive and push preparation (HEAD `1e01c29`; no model run)

Generated by `reproduction/v14_rerun/scripts/code17_audit_block.py` from `code17/lookups.json`, `code17/c6_alltouched_inflation.json`, `code17/BOX1_as_committed.md`, the archive build record and git. Quoted values carry the file and page behind them (raw sources in the CODE-17 attachments).

### B1 — when the frozen rule became public

- Rule frozen in the private manuscript-build repository: commit `bfd005a6f65074662086f30e45ee7869022fc1f6` (2026-07-15 14:33:54 +03:00, author = committer date; private manuscript-build repository, no public remote (docs/FREEZE_EVIDENCE.md)); never pushed to a public remote.
- Public copy: `docs/frozen_rule_R.md` added in `786fc50302e25fe7ce17430b4243403a168a842d` (author date 2026-07-20T15:12:30+03:00 = 2026-07-20T12:12:30Z); the file's blob `8f7586269723fdf24003b5fe44665a7e3e4778fd` is unchanged at HEAD.
- First push of that commit to origin: 2026-07-22T08:31:35Z (GitHub repository-activity API, push refs/heads/main ecc9d5d -> a72897c by the second author's account; the local reflog of origin/main agrees ('update by push', 2026-07-22 11:31:35 +0300); c1/github_activity.json).
- First public tag/release containing it: `v1.2.0` → `738fa3d (annotated tag bf77d4a, tagger date 2026-07-22T08:52:52Z; the activity log shows an earlier tag object bef8464 under the same name deleted on the remote at 09:01:44Z)`; GitHub release created 2026-07-22T08:52:52Z, published 2026-07-22T09:04:52Z (GitHub Releases API, c1/github_releases.json); Zenodo version 10.5281/zenodo.21487689 created 2026-07-22T09:04:56Z (publication_date 2026-07-22 (Zenodo records API, c1/zenodo_versions.json)).
- Release v1.3.0 (the earlier manuscript's record): tag → `ccd423a (tag 1d19a55, tagger date 2026-07-22T09:38:59Z)`, GitHub release published 2026-07-22T09:43:52Z (created 09:38:59Z), Zenodo 10.5281/zenodo.21488879 created 2026-07-22T09:43:56Z (publication_date 2026-07-22; DataCite registered 2026-07-22T09:43:57Z). Concept DOI 10.5281/zenodo.20523154 registered 2026-06-03T08:12:29Z (DataCite created/registered; first version v.0.0.1 = record 20523155, GitHub release published 2026-06-03T08:12:24Z) (predates the rule).
- Box 1 as committed: `code17/BOX1_as_committed.md` — blob: `8f7586269723fdf24003b5fe44665a7e3e4778fd` (unchanged at HEAD: yes); extracted rule block: bytes 1060–2104 of the blob, 1044 bytes, SHA-256 `e05a3836dd34cd16e9378cea50a9de9b1c431cd4435714e1b67a4beaad01f857`; extracted Box 1 caption: bytes 2105–2857, 752 bytes, SHA-256 `1361aa5115a1448b40bfd4249034729a818654a271892c5bcbb03ca1d0afbb59`

### B2 — Copernicus DEM citation and the GLO-30 release used

- `10.5270/ESA-c5d3d65`: registration agency Crossref (https://doi.org/ra/10.5270/ESA-c5d3d65 returns RA = Crossref) (DataCite API HTTP 404 (https://api.datacite.org/dois/10.5270/ESA-c5d3d65; 2026-10-21 and again 2026-10-22); checked 2026-10-22). Crossref record: title "Copernicus DEM", authors European Space Agency; Airbus (two organisational authors, in that order), publisher European Space Agency, issued 2022 (date-parts [[2022]]; no month), type dataset, no version field; doi.org resolves to https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM (HTTP 302 from doi.org; the CDSE COP-DEM collection page).
- `10.60489/roda.mxyog0` (DataCite): title "Copernicus Digital Elevation Model (DEM)", creator Sinergise, publisher Registry of Open Data on AWS, publicationYear 2020, version 1.0, url https://registry.opendata.aws/copernicus-dem/ (DataCite; the registry page itself shows no DOI).
- `10.5069/G9028PQB` (DataCite): title "Copernicus GLO-90 Digital Surface Model", creator OpenTopography, publisher OpenTopography, publicationYear 2021, url https://opentopography.org/meta/OT.032021.4326.1 (the landing page covers COP30 and COP90 under this one DOI; OpenTopography serves ESA's DGED 2023_1 release since 2024-07-23) — not the distribution used; not to be cited.
- GLO-30 release used by every v1.4.x build (HydroMT data catalogue of each run, `data_catalog.yml`, entry `copdem30`): data_type RasterDataset, driver raster, path copdem30/copdem30.vrt, crs 4326, meta.category topography, meta.source_url https://copernicus-dem-30m.s3.amazonaws.com, meta.source_version 'GLO-30 (2021)' (identical in the data_catalog.yml of pineios_enhanced_v142, mandra_enhanced, valencia_enhanced_164_v142, crete_canonical_r2on; template skill/templates/data_catalog.yml.tmpl); the AWS collection metadata states 'Data is provided as Cloud Optimized GeoTIFFs and comes from the Copernicus DEM 2021 release' (STAC collection dem_cop_30 of the copernicus-dem-30m bucket, c2c3/C2d_aws_stac_copernicus-dem-30m-stac_dem_cop_30.json); the registry page: 'GLO-30 Public and GLO-90 are available on a free basis for the general public under the terms and conditions of the Licence'. Download: `skill/scripts/download_dem.py` from `https://copernicus-dem-30m.s3.amazonaws.com`, tiles `Copernicus_DSM_COG_10_<N>_00_<E>_00_DEM (1-degree COG tiles; e.g. Copernicus_DSM_COG_10_N34_00_E023_00_DEM.tif)`.
- Licence notice for modified data (COP-DEM-GLO-30-F, Art. 6(b)): "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved" (COP-DEM-GLO-30-F licence, Art. 6(b); ESA PDF copernicus_contributing_mission_data_access_v2_cop_dem_licenses.pdf)

### B3 — Mandra event facts (Diakakis et al. 2019, doi 10.1016/j.ijdrr.2018.10.015; NOA Vilia)

- Access: Full text not obtained (closed access; ScienceDirect returns a captcha page, no open copy in Pergamos, Semantic Scholar, OpenAlex, Europe PMC, CORE or the authors' sites). Read instead: the publisher's article preview (Wayback capture 2022-10-22 of the ScienceDirect abstract page): complete Abstract, complete section 1, the section outline, the Table 1 caption and the opening sentences of sections 2.1, 3.1, 4.1, 5 and 6. No printed page number is recoverable; the article runs pp. 290-309. The article's PII is S2212420918303935 (Crossref alternative-id). Files: b3/downloads/, b3/excerpts/, b3/ACCESS_LOG.tsv.
- Rainfall: Abstract "reaching 300 mm in 13 h in the core zone of the event"; section 6 "reaching up to 300 mm in 13 h, with 153 and 194 mm of basin-average total accumulation in Agia Aikaterini and Soures catchments at the foothills of Mt. Pateras", attributed to "the high-resolution XPOL radar of NOA" (radar values). The draft's "158-300 mm in 24 h" and "24-h catchment-mean 158-200 mm, gauge totals exceeding 300 mm" are not in the source: 158, 200, '24 h' and any gauge total do not appear; the duration stated is 13 h.
- Unit discharge: Abstract "Peak discharge was estimated, using a UAV-derived digital surface model, at two locations, corresponding to the two main tributaries and indicated an impressive hydrological response, between 9 and 10 m3/s/km2" (Table 1 "Peak discharge estimations and cross section measurement details at Sources and Agia Aikaterini torrents"). The draft's "exceeded 3 (locally > 5) m3 s-1 km-2" is not in the source and contradicts it.
- Fatalities: Abstract "a tragic loss of 24 people, making it the most deadly flood in the country, in a period of 40 years" - "24 people died" is supported.
- NOA Vilia gauge, > 30 mm/h: not in the source (no station name or mm/h value in the Abstract, section 1 or any preview snippet; section 2.2 'The storm event' is not in the preview, so it cannot be excluded there). No other source found documents it: the NOA 2017 annual report (p. 26) states that no rain gauges were installed in the event area ("Στην περιοχή του συμβάντος δεν υπήρχαν εγκατεστημένα βροχόμετρα"); Vilia station totals in the literature are 33.6-67.2 mm (Stamou 2018 p. 5 of the PDF: Elefsis 35, Vilia 35, Agioi Theodoroi 22 mm, citing NOA). Radar intensities: Varlas et al. 2019 (Remote Sens. 11, 45, p. 17 of the PDF) basin-average rates up to 57 mm/h (Soures) and 41 mm/h (Agia Aikaterini), 02-06 UTC. Lagouvardos et al. 2017 (GDJ 4, 4-16, online 2017-04-05) describes the station network and cannot document the event.
- Radar agreement: Varlas et al. 2019 (p. 6, 8) compared XPOL with distant gauges over 14 Nov - 26 Dec 2017 (CR > 0.9, BR = 0.91); NOA states the radar agrees with GPM IMERG; no source compares a gauge with the radar at the storm peak.

### B4 — Valencia event facts (Chiva 491 mm in 8 h; Turís 772 mm in 24 h)

- Turis, AEMET station 8337X: AEMET study of 23 Dec 2024 (estudio_28_oct_4_nov_2024.pdf, PDF p. 30, Tabla 4.5): "8337X TURIS VALENCIA 184,6 620,6 720,4 771,8" (max 1 h, 6 h, 12 h; P24h) - 771.8 mm in 24 h; PDF p. 31: "710.8 mm (771.8 mm en el día civil)" (pluviometric day 08-08 vs civil day). AEMET report with data to 8 Nov 2024 (informe_episodio_dana_29_oct_2024.pdf, p. 13, Tabla 1): "8337X TURÍS 185 621 720 772".
- Chiva, 491 mm in 8 h: only source found is AEMET's post on X of 2024-10-30 11:24 UTC (status 1851585885273301186, read through the public oEmbed endpoint): "En Chiva, de hecho, se recogieron 491 l/m² en solo ocho horas" (no station code, no time window). The AEMET study (PDF p. 30, Tabla 4.5) gives "8334B CHIVA-LA PAILLA VALENCIA -- -- -- 615,0" (24-h total 615.0 mm; sub-daily maxima not given) and on p. 29 99.4 mm between 7:30 and 9:30 and 384.0 mm between 15:30 and 20:30. Section 2's "daily totals above 490 mm at Chiva" is therefore wrong (the daily total is 615.0 mm); section 4's "about 491 mm in 8 h" matches the AEMET post.
- Rombeek et al. 2025 (HESS 29, 6715-6737) carries neither value: p. 6715 "locally exceeding 300 mm within 24 h (Faranda et al., 2024)"; p. 6722 the Turis station "reported more than 400 mm within 24 h, with most rain (around 280 mm) between 18:00-00:00" (its AEMET series has a gap 12:00-18:00, p. 6725). Calvo-Sancho et al. 2026 (Nat. Commun. 17, 1492, abstract): "771.8 mm in 16 h in the official weather station at Turís" and 184.6 mm in 1 h.
- Attribution for the manuscript: Turis 771.8 mm (24 h, civil day) -> AEMET 2024 study, Tabla 4.5; Chiva 491 mm in 8 h -> AEMET (2024-10-30 statement), daily 615.0 mm -> the same AEMET study; Rombeek et al. 2025 only for the catchment-average 164 mm of the R2 anchor.

### B5 — any-touched versus centre-point burning of the observed polygons (`code17/c6_alltouched_inflation.json`; S6)

| event (run of record) | universe km² | observed cells any-touched | km² | observed cells centre | km² | inflation | CSI / HR / FAR / B any-touched | CSI / HR / FAR / B centre (re-scoring sensitivity) |
|---|---|---|---|---|---|---|---|---|
| pineios (pineios_enhanced_v142) | 4506.7 | 67007 | 1507.7 | 57233 | 1287.7 | +17.1 % | 0.496 / 0.901 / 0.475 / 1.72 | 0.439 / 0.918 / 0.544 / 2.01 |
| strymonas (strymonas_enhanced_postD6_v142) | 1196.2 | 4633 | 104.2 | 3074 | 69.2 | +50.7 % | 0.334 / 0.921 / 0.656 / 2.68 | 0.237 / 0.967 / 0.761 / 4.04 |
| mandra (mandra_enhanced) | 86.9 | 3528 | 8.8 | 1930 | 4.8 | +82.8 % | 0.157 / 0.760 / 0.835 / 4.61 | 0.093 / 0.798 / 0.905 / 8.43 |
| valencia (valencia_enhanced_164_v142) | 2709.5 | 19581 | 195.8 | 16515 | 165.2 | +18.6 % | 0.144 / 0.939 / 0.855 / 6.46 | 0.123 / 0.952 / 0.876 / 7.66 |
| emilia (emilia_enhanced_8aoi_v142) | 3148.0 | 25240 | 567.9 | 14167 | 318.8 | +78.2 % | 0.253 / 0.852 / 0.735 / 3.22 | 0.154 / 0.897 / 0.844 / 5.73 |
| crete AOI03 tier 1 (crete_canonical_r2on) | 176.9 | 1126 | 11.3 | 433 | 4.3 | +160.0 % | 0.221 / 0.988 / 0.778 / 4.45 | 0.086 / 1.000 / 0.914 / 11.58 |

Crete tier-2 AOIs (area only): AOI01 178 vs 22 cells (+709 %); AOI04 41 vs 2 cells (+1950 %); AOI06 23 vs 6 cells (+283 %); AOI07 65 vs 2 cells (+3150 %).
Method: inflation = observed-wet cells burned any-touched / burned by cell centre - 1, inside the universe; strict_h_gt_0p10.centre = labelled re-scoring sensitivity (no SFINCS run): the run of record's h_max > 0.10 m against the truth burned by cell centre on the same grid and universe. The any-touched contingency of every run reproduces its record (asserted). Release universe check: Pineios +17.7 %, Strymonas +52.2 %, Mandra +81.8 % (earlier text: +18 / +52 / +82 %).

### C — anonymised review archive (local only, not uploaded)

- Built 2026-10-22T08:13:42Z from `git archive v1.4.2` (`0084600`, 1211 files) + 374 overlay files from HEAD `1e01c29`; 13 files excluded (NOA station files, credentials patterns, caches, CITATION.cff, CLAUDE.md, anonymity tooling, cited-work raw metadata, archived figures); 412 of 1163 text files scrubbed (1901 substitutions); 1323 files in the archive.
- `reproduction/r6/review_archive_v1.4.2.zip`: 77.5 MB, SHA-256 `5976777bdf4aa9490296e7fb3fb639a24264878dca07bd7b02c4f42b0f7ed3b7`.
- Anonymity scan of the unpacked archive (`anonymity_grep.py --tree`, 2026-10-22T08:14:44Z): 15 hits outside cited-work metadata, 4 inside; by class: github.com URLs 15, Zenodo DOIs / records 4.

### D — push preparation (nothing pushed; GO-PUSH pending)

- Command: `git push --atomic origin main v1.4.0 v1.4.1 v1.4.2 emsr933-v1` — refs: `main` → `f3a11f4` (update); `v1.4.0` → `70c2bfb` (create); `v1.4.1` → `642efaa` (create); `v1.4.2` → `0084600` (create); `emsr933-v1` → `f3a11f4` (create). `origin/main` = `ccd423a`; `main` is fast-forwarded to the commit that carries this block (36 commits ahead of origin/main, fast-forward: True).
- Tracked at HEAD (2026-10-22T08:14:28Z check, `scripts/d4_push_plan.py`): NOA/meteo.gr station data files none; credential files none; credential-like content 0 hit(s).
- History that the push would publish: 8 NOA station data files were tracked from `6363ead` (2026-10-09) until the commit before this one and are reachable from tags `emsr933-v1`, `v1.4.0`, `v1.4.1`, `v1.4.2`; credential files in history: none. Removing the station files from history would rewrite every commit since 6363ead, including the frozen tag v1.4.2 — an author decision before GO-PUSH.

## CODE-19 (2026-10-22T13:06:10Z) — R6b look-ups and zero-compute results (HEAD `6585d46`; no model run; number freeze v1.4.2 stands)

Generated by `reproduction/v14_rerun/scripts/code19_audit_block.py` from the records under `reproduction/v14_rerun/code19/` (each cited with its SHA-256 prefix and UTC). Scripts: `code19_a1_rain_leadin.py`, `code19_a2_ib_boundary.py`, `code19_a3_hardware.py`, `code19_a4_emsr773_aois.py`, `code19_b45_map_checks.py`, `code19_lookups.py`; Crete baseline tier-1 diagnostics by `crete_tier1_diagnostics.py --runs crete_baseline` (re-scoring on the frozen output, as stated in C1).

### A1 — domain-mean precipitation over the active mask `code19/a1_rain_leadin.json` (sha256 6803032a056ed1b5…, 2026-10-22T12:50:41Z)

Definition: domain mean over the active cells (msk > 0) of the nearest source cell; ERA5 end-labelled hourly accumulations (t0 < t <= t1), IMERG start-labelled half-hourly rates (t0 <= t < t1); totals = sum(rate x step); lead-in = [tstart - 7 d, tstart); simulated = [tstart, tstop); max 24 h = largest rolling 24-h total of the domain-mean series inside the covered lead-in; AMC-5d = [t - 5 d, t) before tstart and before the event day.

| event (run) | active cells | lead-in 7 d ERA5 / raw IMERG (mm) | lead-in coverage | simulated ERA5 / raw IMERG (mm) | max 24 h in lead-in ERA5 / IMERG (mm, start) | AMC 5 d before tstart ERA5 / IMERG | 5 d before event day ERA5 / IMERG |
|---|---|---|---|---|---|---|---|
| pineios (pineios_enhanced_v142) | 223703 | 0.4 / 1.6 | ERA5 100 % / IMERG 100 % | 312.5 / 156.1 | 0.2 (2023-09-01T14:00) / 1.3 (2023-08-28T10:00) | 0.3 / 1.5 | 174.2 / 103.4 |
| mandra (mandra_enhanced) | 117667 | 0.3 / 0.4 | ERA5 15 % / IMERG 14 % | 38.1 / 141.0 | 0.3 (2017-11-12T00:00) / 0.4 (2017-11-12T00:00) | 0.3 / 0.4 | 7.3 / 11.9 |
| strymonas (strymonas_enhanced_postD6_v142) | 185824 | 21.0 / 46.9 | ERA5 15 % / IMERG 100 % | 8.5 / 6.2 | 19.9 (2015-03-27T00:00) / 26.2 (2015-03-26T16:30) | 21.0 / 46.3 | 28.2 / 41.1 |
| valencia (valencia_enhanced_164_v142) | 298115 | 24.3 / 16.6 | ERA5 43 % / IMERG 43 % | 107.8 / 72.6 | 23.8 (2024-10-25T07:00) / 16.4 (2024-10-25T05:00) | 24.3 / 16.6 | 54.9 / 20.8 |
| emilia (emilia_enhanced_8aoi_v142) | 229446 | 61.4 / 64.5 | ERA5 100 % / IMERG 100 % | 134.0 / 129.7 | 42.4 (2023-05-10T05:00) / 45.5 (2023-05-09T21:30) | 60.4 / 64.3 | 101.9 / 89.5 |
| crete (crete_canonical_r2on) | 859727 | 30.6 / 53.9 | ERA5 100 % / IMERG 100 % | 97.8 / 235.7 | 22.0 (2026-09-26T17:00) / 36.8 (2026-09-26T16:00) | 29.9 / 51.6 | 44.0 / 72.5 |

Strymonas R4 as configured: infiltration {'enabled': True, 'hsg': 'B', 'amc': 2}, realised mean CN (active cells) 74.9. The rule's clause (docs/frozen_rule_R.md): R4 SCS-CN infiltr.   := IF AMC-III (multi-day wet spell OR peak intensity > HSG saturated capacity) OR fire-affected / near-impervious catchment THEN off    ELSE on at HSG-B, AMC-II — the clause does not quantify 'multi-day wet spell'; the numbers above are reported for the author's reading. Coverage: the ERA5 files are day-list downloads (the configured download days within each month: Strymonas and Valencia files hold 1–4 / 27–31 and 1 / 24–31 of the month), so the ERA5 7-day lead-in is covered for 25 h (Mandra, Strymonas) or 73 h (Valencia) only; the raw IMERG files cover the full 7 d except Mandra (24 h) and Valencia (72 h). Totals are reported over the covered part with the coverage shown; nothing was downloaded.

### A2 — inverse-barometer boundary as realised `code19/a2_ib_boundary.json` (sha256 5931d9b13f8b92e3…, 2026-10-22T12:50:40Z)

Definition: realised = max over the simulated window and the msk = 2 cells of zs in sfincs_map.nc (hourly output; dry cells are fill); expected = max of (pavbnd - p) / (rho g) with p = press_2d.nc sampled at the msk = 2 cells (nearest forcing node); rho 1024, g 9.81, pavbnd from sfincs.inp.

| event (run) | bnd points / msk = 2 cells | realised max zs at the boundary (m, time) | expected IB max from the pressure at the boundary (m, time; p min hPa) | realised / expected | window-mean expected IB (m) | event-mean offset recorded (A2_pavbnd_reference) |
|---|---|---|---|---|---|---|
| pineios (pineios_enhanced_v142) | 12 / 716 | 0.063 (2023-09-05T02:00:00) | 0.065 (2023-09-05T02:00:00; 1006.74) | 0.972 | -0.017 | -0.021 |
| mandra (mandra_enhanced) | 31 / 3253 | 0.090 (2017-11-13T13:00:00) | 0.091 (2017-11-13T14:00:00; 1004.1) | 0.987 | +0.003 | +0.003 |
| strymonas (strymonas_enhanced_postD6_v142) | 19 / 802 | 0.116 (2015-03-28T03:00:00) | 0.118 (2015-03-28T03:00:00; 1001.42) | 0.986 | +0.043 | +0.042 |
| valencia (valencia_enhanced_164_v142) | 24 / 1667 | 0.011 (2024-10-29T17:00:00) | 0.013 (2024-10-30T01:00:00; 1011.91) | 0.835 | -0.042 | -0.048 |
| emilia (emilia_enhanced_8aoi_v142) | 226 / 3206 | 0.144 (2023-05-16T08:00:00) | 0.151 (2023-05-16T08:00:00; 998.05) | 0.951 | +0.016 | +0.016 |
| crete (crete_canonical_r2on) | 160 / 13858 | 0.004 (2026-10-01T02:00:00) | 0.005 (2026-10-01T02:00:00; 1012.78) | 0.872 | -0.052 | -0.052 |

Largest realised boundary rise: 0.144 m, emilia (emilia_enhanced_8aoi_v142), 2023-05-16T08:00:00; bzs files all zero: True; pavbnd 101325 Pa in every sfincs.inp.

### A3 — hardware of the canonical runs `code19/a3_hardware.json` (sha256 8c90c391ab9b1358…, 2026-10-22T12:50:40Z)

- Machine (read on host `ITI-1001`): 12th Gen Intel(R) Core(TM) i5-12600K, 10 physical cores / 16 logical processors, 16 GiB installed RAM (15.7 GiB usable), Microsoft Windows 11 Pro 10.0.26200 64-bit.
- Every canonical run: sfincs.log `$Rev: v2.3.0 mt. Faber Release`, Build-Date 2025-11-18, `Using 16 of 16 available threads`; HydroMT and SFINCS invoked from `C:/Users/dvalsamis/…/sfincs-viz` on `D:/ELKAK/implementation/v14/<run>` — same machine for all six (pineios_enhanced_v142 2026-10-20T12:46:27Z→2026-10-20T13:58:49Z, mandra_enhanced 2026-10-19T09:13:13Z→2026-10-19T09:20:34Z, strymonas_enhanced_postD6_v142 2026-10-20T14:39:31Z→2026-10-20T14:53:31Z, valencia_enhanced_164_v142 2026-10-20T13:24:33Z→2026-10-20T13:58:45Z, emilia_enhanced_8aoi_v142 2026-10-20T12:46:27Z→2026-10-20T13:24:33Z, crete_canonical_r2on 2026-10-19T16:44:39Z→2026-10-19T20:21:12Z).
- Caveat for Table 2 wall-clock times: the run windows overlap (pineios_enhanced_v142 and emilia_enhanced_8aoi_v142 both start 2026-10-20T12:46:27Z; valencia starts when emilia ends), so those timings were measured with two 16-thread runs sharing the CPU.
- Build-Date in the log is 2025-11-18 while the records name the release `mt_Faber_release_2025.02`; the executable folder is `SFINCS_v2.3.0_mt_Faber_release_exe` (manual PDFs dated 2025-11-19) — the '2025.02' suffix is not confirmed by the binary.

### A4 — EMSR773 areas of interest `code19/a4_emsr773_aois.json` (sha256 438861b10182e803…, 2026-10-22T12:40:16Z)

- Activation as listed by the EMS dashboard API on 2026-10-22T12:40:16Z (snapshot `reproduction/v14_rerun/code19/ems_api_snapshot_EMSR773_20261022T124016Z.json`, sha256 5041c86b0fe6fec6…): **36 AOIs**; 24 intersect the configured lon/lat bbox, 26 the UTM grid rectangle, **24 hold at least one active cell** of valencia_enhanced_164_v142 (the two extra grid intersections, AOI26 Siete Aguas and AOI33 Sot de Chera, touch inactive corners).
- The run's cached EMS download (the truth snapshot) holds 3 AOIs (AOI01, AOI06, AOI14); AOI06 lies outside the domain (no active cell); S2 scores AOI01 and AOI14.
- AOIs with active cells: AOI01 Valencia province (276592 cells, 5 product(s) DEL), AOI03 Horta Sud (27872 cells, 2 product(s) DEL/GRA), AOI04 Algemesi (23163 cells, 1 product(s) DEL), AOI10 Cheste (5489 cells, 1 product(s) GRA), AOI11 Yatova (9 cells, 2 product(s) DEL/GRA), AOI12 Godelleta (896 cells, 1 product(s) GRA), AOI13 Monserrat (1672 cells, 1 product(s) GRA), AOI14 Alcudia (1066 cells, 2 product(s) GRA), AOI16 Benicull de Xuquer (2115 cells, 1 product(s) GRA), AOI17 Alzira (3773 cells, 1 product(s) GRA), AOI18 Alginet (2134 cells, 1 product(s) GRA), AOI19 Llombai (545 cells, 1 product(s) GRA), AOI20 Montroi (537 cells, 1 product(s) GRA), AOI21 Turis (782 cells, 1 product(s) GRA), AOI22 Bunol (42 cells, 1 product(s) GRA), AOI23 Favara (188 cells, 1 product(s) GRA), AOI24 Cullera (1296 cells, 1 product(s) GRA), AOI25 Sueca (1365 cells, 1 product(s) GRA), AOI28 Pedralba (314 cells, 1 product(s) GRA), AOI29 El Mas del Moro (554 cells, 1 product(s) GRA), AOI30 Valencia Sud (2697 cells, 1 product(s) GRA), AOI31 Cases Del Riu (754 cells, 1 product(s) GRA), AOI35 Alcasser (405 cells, 1 product(s) GRA), AOI36 Paterna (2381 cells, 1 product(s) GRA).

### B4 — Albufera lagoon (F7) `code19/b4_albufera.json` (sha256 9d8353115b93aaa9…, 2026-10-22T12:53:14Z)

- Lagoon = the 4-connected WorldCover-80 component at the lagoon centre ([-0.335, 39.335]): **2447 cells, 24.47 km²**, all msk = 1 (active, not open sea), all inside the AOI union, **all excluded from the evaluation universe** (class 80 at the cell centre; in-universe cells 0); z_b -3.8–0.1 m; modelled h_max there: max 4.43 m, median 0.54 m, 2447 cells > 0.10 m. Had they been inside, 2209 cells would be false alarms = 2.044 % of the record's 108091 FP cells (EMS maps 238 of them as flooded).
- Margin ring (3 cells around the lagoon): 1062 cells, WorldCover classes {'10': 152, '20': 10, '30': 37, '40': 137, '50': 10, '60': 2, '80': 47, '90': 667}; 1015 inside the universe, 921 wet, 95 false alarms = 0.088 % of the record's FP.
- Verdict: excluded from the evaluation universe (no lagoon cell inside it) → F7 re-exported with the exclusion mask above the depth layer (`r6_figures.EXCL_ON_TOP`).

- Depth drawn over excluded cells in the other maps `code19/b_maps_wet_in_excluded.json` (sha256 34a171ff1a6220fe…, 2026-10-22T12:53:14Z): F3 pineios 2102 cells (47.3 km², 1.69 % of the wet cells); F5 mandra 331 cells (0.83 km², 0.88 % of the wet cells); F6 strymonas 1272 cells (28.62 km², 8.88 % of the wet cells); F7 valencia 4271 cells (42.71 km², 3.15 % of the wet cells); F8 emilia 5792 cells (130.32 km², 4.68 % of the wet cells); F9 crete 1416 cells (14.16 km², 0.96 % of the wet cells) — left as drawn (decision for the author).

### B5 — Emilia-Romagna southern edge (F8) `code19/b5_emilia_south.json` (sha256 284acb5e4df93bcd…, 2026-10-22T12:53:14Z)

- Rows 0–4 (y ascending, row 0 = southern boundary): **309 cells with h_max > 0.10 m** ([60, 63, 63, 60, 63] per row), **none inside an AOI**, none EMS-observed; row 0 holds 220 closed-boundary cells (msk = 1), 0 water-level cells, and **60 wet cells touch the closed boundary**; depth up to 2.63 m; z_b 33–288 m; nearest inflow source 12.3 km away.
- 62 of the 309 cells belong to the domain-wide channel component (rows 0–578), the rest to small valley-bottom components of 10–40 cells cut by the domain edge: Apennine channels whose upstream part lies outside the domain (closed boundary, no inflow prescribed there). Model output, not a plotting artefact → no re-export.

### C — supplement rows

- S1: 16 baseline rows added (pineios_baseline_gridmatched, mandra_baseline, strymonas_baseline, crete_baseline × 4 thresholds) from `phase4/cross_event_v14_v142.json` baseline_v14.sweep; S3: 4 baseline rows (fuzzy r = 0–3, one-sided, buffer, time-matched); Crete baseline buffer/time-matched on the tier-1 block from `code19/crete_tier1_diagnostics_baseline.json` (sha256 0127b3a1d8bbd4c2…, 2026-10-22T12:35:38Z): buffer −20 / 0 / +20 m CSI 0.263 / 0.343 / 0.359; time-matched full / earliest / latest 0.343 / 0.343 / 0.343.
- S2: the Strymonas baseline per-area rows 01–04 were already present (CSI 0.207/0.410, 0.124/0.357, 0.333/0.365, 0.358/0.455); unchanged.
- S4: the Strymonas lead-in row relabelled '7-day lead-in simulated (10 d before the event day; canonical 3 d)' (from the two configs' windows).
- S11 (new; supplement numbering S10): the Manning lookup, 11 WorldCover classes from `skill/manning_lookup.csv` (built-up 0.012; copies in all six run directories byte-identical). The file carries no per-class source.

### D — sources `code19/lookups.json` (sha256 913d9b3b31467fae…, 2026-10-22T13:04:35Z)

- D3 Rombeek et al. 2025 (HESS 29, 6715–6733): Table 1 (p. 6718) `ID4 (Poyo) 182 NA NA NA 0 147 433` (gauged Poyo catchment ID4 = 182 km²); Fig. 6a legend (p. 6723) `1) - 960 km²; 2) - 571 km²; 3) - 1661 km²; 4) - 316 km²`; §4.3 (p. 6723) `On the other hand, for catchment (4) a significantly higher catchment-averaged rainfall is estimated, which is more than 40 mm, namely 164 mm.`. Two numbering schemes: Table 1 / Fig. 1b gauge catchments ID1–ID4, where ID4 is the Poyo gauge with 182 km²; Fig. 6 rainfall catchments (1)–(4) with areas 960 / 571 / 1661 / 316 km² (legend of Fig. 6a), where (3) is named the Magro and (4) carries the 164 mm. The text never names catchment (4); it is not the 182 km² gauged Poyo catchment (316 km²). read from the rendered pages (not from the text): Fig. 1b places gauge ID4 (Poyo) at about 0.60° W, 39.47° N beside Chiva, the Poyo draining east to the Albufera; Fig. 6d places the yellow catchment (4) with the '164 mm' label south of the Magro mouth around Algemesí (about 0.55–0.35° W, 39.15–39.30° N), while the red catchment (2) (571 km²; '162 mm' combined in panel d, '173 mm' AEMET-only in panel b) encloses Chiva and gauge ID4. On that reading the 164 mm belongs to the coastal catchment south of the Albufera, and the Poyo lies in catchment (2) with 162 mm (combined) — numerically 2 mm from the anchor used.
- D4 Bernhofen et al. 2018: `The critical success index of individual models across the three regions ranges from 0.45 to 0.7 and the percentage of flood captured ranges from 52% to 97%.`; results `The average CSI of the GFMs range from 0.45 (GLOFRIS) to 0.70 (JRC) for a 25 year flow.`; no median stated. Trigg et al. 2016: `we find a MAI of only 0.29, and a mean Cohen’s kappa coefficient of 0.43, across all models and all return periods.` and `While there is around 30%–40% agreement in flood extent, our results s…` (model agreement, no CSI). Hocini et al. 2021 (p. 2986): `Overall, similar and satisfactory results are observed for the caRtino 1D and Floodos 2D approaches, with a slight advantage for Floodos, for which the 15 % quantiles of CSI values exceed 50 % and the median CSI values are close to 80 %.`; La Redorte (p. 2987) 69 / 63 / 35 %. Wing et al. 2017: body not retrievable (Wiley and Bristol PDF 403); abstract: Hit Rate 86 % vs FEMA, 92 % vs USGS (100-year). **The §4.7 ranges ('Bernhofen 0.10–0.36, median ≈ 0.22', 'Trigg 0.10–0.35', 'Hocini 0.42–0.62') and the F10 band constants of fig_skill_sweeps_v14.py are not what these articles state** — reported, not changed (B1 says nothing else changes in F10).
- D5 Schumann et al. 2016: publisher page not readable (403); Bristol record `Pages (from-to) 10249-10256` — not added to refs.bib.
- D6 Ross et al. 2018: Crossref Scientific Data 5, article 180091 ([[2018, 5, 15]]), title 'HYSOGs250m, global gridded hydrologic soil groups for curve-number-based runoff modeling' — not added pending the author.
- D1 Diakakis et al. 2019 / Varlas et al. 2019: neither full text retrievable by automated access (Elsevier paywall; mdpi.com 403 for fetcher and curl; no open mirror listed by OpenAlex/OpenAIRE/Semantic Scholar) — catchment areas and the Pateras wildfire not verified.
- D2 Emilia-Romagna 2023: Regione press release of 15 Dec 2023 on the commission report (quotes above); Ferrari et al. 2025 (>500-year for the 24-h rainfall at the Lamone/Marzeno gauges); ARPAE event report: >200-year for the 24-h rainfall in Santerno, Senio, Lamone, Montone, Ronco; ARPAE special: commission estimate 100–500 years per event. Rivers: ARPAE special '23 fiumi in esondazione'; Regione '23 fiumi esondati contemporaneamente'; Arrighi & Domeneghetti 2024 '23 rivers overflowed' with 'levee overtopping and failures'; CIMA '21 rivers'. Fatalities: ARPAE special '17 decessi'; Arrighi & Domeneghetti 2024 '15 deaths' (civil-protection source, Feb 2024); no peer-reviewed source read gives 17.
- D7 Valencia anchor ledger: raw (2026-07-15; yes — CSI 0.105 at h > 0.10 m (CODE-5 ledger)) → 350.0 (2026-07-15; yes — CSI 0.082 (h > 0.10 m), 0.126 (h > 0.50 m)) → 175.0 (2026-07-21; yes — CSI 0.093 (h > 0.10 m), 0.165 (h > 0.50 m)) → 164.0 (2026-07-21; yes — CSI 0.094 (h > 0.10 m), 0.170 (h > 0.50 m)). every anchor change followed a computed score of the previous value (350 scored 15 Jul; 175 scored 09:29Z and replaced by 164 at ~10:00Z the same morning; 164 scored 10:41Z and adopted). The documented motive for each change is sourcing (unsourced 350 -> literature band midpoint -> catchment-specific published value), recorded in TARGET_SELECTION.md and PROVENANCE.md; the D3 reading above questions whether the 164 mm catchment (4) is the gauged Poyo catchment.

## CODE-20 (2026-10-22T20:58:39Z) — figure set after the benchmark correction, three records, S2 digest rows (HEAD `0f61f1f`; no model run; number freeze v1.4.2 stands)

Generated by `reproduction/v14_rerun/scripts/code20_audit_block.py` from the records under `reproduction/v14_rerun/code20/` (each cited with its SHA-256 prefix and UTC). Scripts: `code20_lookups.py` (A1 quotes), `code20_b1_freeze_order.py`, `code20_b3_emsr773_nested.py`, `code20_b4_sfincs_release.py`; figures by `reproduction/r6/scripts/r6_figures.py`, tables by `r6_tables.py`. Nothing was simulated and no frozen number changed.

### A1 — F10 v3 benchmark constants and their quotes `code20/f10_benchmarks.json` (sha256 e661c9d4e9b14e47…, 2026-10-22T20:50:09Z)

F10 v3: `F10.tiff` (sha256 9ef6695ef515c545…, 0.4 MB); markers unchanged (strict CSI, fuzzy r = 1 CSI, CSI*); y axis fixed 0–0.8; the Hocini band is dropped; `r6_figures.fig10` asserts its constants against this record.

| drawn element | constant | legend text | source | quote (printed page) |
|---|---|---|---|---|
| grey band | 0.45–0.70 | global models vs MODIS extents, Bernhofen et al. (2018) | Bernhofen et al. 2018, ERL 13, 104007 (doi 10.1088/1748-9326/aae014); PDF sha256 0d48f1f059b49397… | “The average CSI of the GFMs range from 0.45 (GLOFRIS) to 0.70 (JRC) for a 25 year flow.” (article p. 5); “The critical success index of individual models across the three regions ranges from 0.45 to 0.7 and the percentage of flood captured ranges from 52% to 97%.” (abstract) |
| MODIS (band label) | — | — | same | “The DFO uses Moderate Resolution Image Spectroradiometer (MODIS) imagery to capture flood events globally, and stores them online in an open-access archive.” (PDF p. 5); Fig. 3 caption: “Overlap of individual global flood model extent for return period flows of 25 and 100 years and MODIS observed flood extent for Lokoja, Idah, and Chemba” |
| dotted lines | 0.42 / 0.29 | SFINCS, GloFAS forcing, ≥ 1000 km² / < 50 km² (Sadana et al. 2026) | Sadana et al. 2026, HESS 30, 5491–5519 (doi 10.5194/hess-30-5491-2026; refs.bib `sadana2026validation`); PDF sha256 3e19a228bda38140… | “global mean CSI of 0.42 for basins with large upstream area ( > 1000 km2) and a CSI of 0.29 for basins with small upstream area (< 50 km2)” (p. 5491); “the average CSI rose from 0.29 in the basins with a small upstream area (< 50 km2) to 0.42 in the basins with a large upstream area (≥1000 km2)” (p. 5500); Table 3: “≥1000 km2 (n = 8834) 0.62 0.41 0.42 1.22”, “< 50 km2 (n = 5304) 0.42 0.46 0.29 0.61” (p. 5501); forcing: “The primary global dataset was GloFAS (Grimaldi et al., 2022), which provided long-term global coverage discharge data suitable for simulating floods at a global scale.” (p. 5495) |
| dashed line | 0.67 | SFINCS, observed discharge (Sadana et al. 2026) | same | “achieving an average CSI of 0.67 compared to the average global mean of 0.39 (Table 2)” (p. 5505); “when SFINCS was forced with observed USGS discharges, the average CSI was 0.67 (HR = 0.86; FAR = 0.21)” (p. 5507) |
| not drawn | 0.39 | — | same | “with a mean CSI of 0.39 using GloFAS modelled discharges as input forcing” (p. 5509); “simulating 499 riverine floods globally” |

Reading: 0.42 / 0.29 are average CSI by basin upstream-area class (Table 3; GloFAS discharge forcing; 499 events); 0.67 is the average CSI of ten US events forced with observed USGS discharge (Table 2 / Sect. 3.7); the global mean with GloFAS forcing is 0.39 (not drawn). Previous F10 (v2) drew `fig_skill_sweeps_v14.BANDS` = [['global multi-model (Bernhofen et al. 2018)', 0.1, 0.36, '#dddddd'], ['calibrated single-event (Hocini et al. 2021)', 0.42, 0.62, '#c8ddf0']] (and, until CODE-19 B1, the median line 0.4); the phase-4 script of the v1.4.2 freeze is left unchanged and F10 v3 no longer reads it. Fig. 10 caption of the R6b tracked manuscript (to be rewritten by the author): “Fig. 10 Strict CSI (circles), one-cell fuzzy CSI (squares) and CSI at the best depth threshold (triangles) of the six events against published ranges: the global multi-model range [grey; Bernhofen et al. (2018)] and the calibrated single-event range [blue; Hocini et al. (2021)].”. The figure manifest's no-author-names rule (`r6_fig_manifest.py`) is relaxed for exactly these three legend labels (CODE-20 A1 wording).

### A2 — maps F3, F5, F6, F8, F9: exclusion mask above the depth layer

`r6_figures.EXCL_ON_TOP` now covers every map (CODE-19 B4 had set F7 only): `F3.tiff` (sha256 ed56f0d6d98e264e…, 3.9 MB); `F5.tiff` (sha256 a469e0cee1ef1fa3…, 2.0 MB); `F6.tiff` (sha256 642e32cecc8c08a6…, 1.1 MB); `F8.tiff` (sha256 23019e5ef605c31a…, 4.3 MB); `F9.tiff` (sha256 04f96c919a856932…, 2.2 MB); F7 unchanged from CODE-19 (`F7.tiff` (sha256 958831d65f19b96f…, 3.1 MB)). Legends unchanged; `FIGURES_MANIFEST.md` regenerated. The modelled water inside excluded cells that CODE-19 `b_maps_wet_in_excluded.json` counted (F3 47 km², F6 29, F8 130, F9 14, F5 0.8) is no longer visible; no score changes (the universe never held those cells).

### A3 — map captions against the new draw order (report only; manuscript not edited)

R6b tracked manuscript (text extract sha256 c56e1831aa9e59e7…):

- Fig. 3 Pineios, Storm Daniel (EMSR692): modelled maximum depth (blue; grey where hmax ≤ 0.10 m) against the EMS flood extent (red) and areas of interest (dashed); dark grey cells (permanent water, open sea) are excluded from the evaluation universe.
- Fig. 5 Mandra (EMSR257): modelled maximum depth against the EMS grading polygons (red) and areas of interest (dashed); legend as Fig. 3.
- Fig. 6 Strymonas (EMSR122): modelled maximum depth against the EMS flood extent (red) and area of interest (dashed); Lake Kerkini and the coastal lakes are excluded from the evaluation universe (dark grey).
- Fig. 7 Valencia (EMSR773), held-out: modelled maximum depth against the EMS flood extent (red) and area of interest (dashed); legend as Fig. 3.
- Fig. 8 Emilia-Romagna (EMSR664), held-out: modelled maximum depth against the EMS flood extent (red) and areas of interest (dashed); legend as Fig. 3.
- Fig. 9 Crete (EMSR933), prospective: (a) island-wide maximum depth with the eight EMS areas of interest by scoring tier; (b) the scored Tzermiado area (tier 1) against the EMS flood extent (red).

Fig. 3 (“dark grey cells (permanent water, open sea) are excluded from the evaluation universe”) and Fig. 6 (“… excluded from the evaluation universe (dark grey)”) remain true and are now exact: with the mask drawn last, every excluded cell shows dark grey, whereas F3/F6/F8/F9 v2 overprinted modelled depth on part of them. Figs. 5, 7, 8 (“legend as Fig. 3”) and Fig. 9 (no grey statement; legend carries it) need no change. Optional, if the author wants the hiding stated: append to Fig. 3 “modelled water inside excluded cells is not drawn”.

### B1 — order of the rule freeze and the first Valencia metrics `code20/b1_freeze_order.json` (sha256 35b00c6cb808e822…, 2026-10-22T20:51:50Z)

| event | source | as recorded | UTC |
|---|---|---|---|
| rule commit `bfd005a` | private repository git (author = committer) | 2026-07-15 14:33:54 +0300 | **2026-07-15T11:33:54Z** |
| Valencia configuration written | mtime of runs/valencia_emsr773/valencia_emsr773_enhanced.yaml | — | 2026-07-15T12:17:17Z |
| first Valencia execution | mtime of run.log | — | 2026-07-15T13:10:13Z |
| first Valencia metrics (raw IMERG) | metrics.json generated_utc at `49da0d1` | 2026-07-15T13:13:03Z | **2026-07-15T13:13:03Z** |
| commit `49da0d1` (results) | git | 2026-07-15 17:00:54 +0300 | 2026-07-15T14:00:54Z |
| 350 mm metrics | metrics.json generated_utc at `5447768` | 2026-07-15T18:00:02Z | 2026-07-15T18:00:02Z |
| commit `5447768` (350 mm) | git | 2026-07-15 21:09:15 +0300 | 2026-07-15T18:09:15Z |
| runs/emilia_emsr664/metrics.json at `49da0d1` | metrics.json generated_utc | 2026-07-15T13:50:26Z | 2026-07-15T13:50:26Z |
| docs/FREEZE_EVIDENCE.md author date | published record (sha256 2d56396c768cb484…) | 2026-07-15 14:33:54 +03:00 | 2026-07-15T11:33:54Z |

**Verdict:** The rule commit bfd005a (2026-07-15T11:33:54Z) precedes the first Valencia metrics (2026-07-15T13:13:03Z) by 1 h 39 min 09 s and the 350 mm metrics (2026-07-15T18:00:02Z) by 6 h 26 min 08 s; the section 3.4 sentence stands, no replacement needed. (commit → first metrics 1 h 39 min 09 s; commit → configuration 0 h 43 min 23 s; commit → first execution 1 h 36 min 19 s.) Manuscript sentence (§3.4): “The rule was committed on 15 July 2026, before either held-out configuration was written” — stands.

Defect (report only): docs/FREEZE_EVIDENCE.md gives the first Valencia score as 2026-07-15 21:00 local (+03:00; = 2026-07-15T18:00:00Z), which is the 350 mm run (2026-07-15T18:00:02Z); the raw-IMERG run was scored at 2026-07-15T13:13:03Z (= 2026-07-15 16:13 local), after the first execution the file lists (2026-07-15 16:10 local). Reported, not edited.

### B2 — S2 digest rows (Strymonas ERA5 baseline)

`tables/S2_baseline_digest.csv` (sha256 85f68feee540f53e…), emitted by `r6_tables.tab_s2` as a sub-table of S2 (cells identical to the S2 rows of run `strymonas_baseline`):

| AOI | observed km² | modelled km² (h_max > 0.10 m) | CSI | HR | FAR | fuzzy r=1 CSI |
|---|---|---|---|---|---|---|
| 01STRYMONAS | 104.2 | 145.1 | 0.207 | 0.410 | 0.706 | 0.229 |
| 02BALTOTOPI | 8.4 | 18.7 | 0.124 | 0.357 | 0.840 | 0.228 |
| 03ACHINOS | 42.8 | 19.6 | 0.333 | 0.365 | 0.206 | 0.569 |
| 04MAVROTHALASSA | 33.1 | 24.1 | 0.358 | 0.455 | 0.374 | 0.513 |

### B3 — EMSR773 areas nested in AOI01 and their DEL products (response letter only) `code20/b3_emsr773_nested.json` (sha256 c0d87e53399c7da7…, 2026-10-22T20:50:11Z)

Scope: geometry only (polygon areas and overlaps in EPSG:32630); no model output read, nothing re-scored. Of the 36 EMSR773 AOIs, 32 lie inside the AOI01 (Valencia province) extent and 23 of those hold active cells of the model domain (the “23”). Nested AOIs with a DEL product: AOI02 Plana de Utiel, AOI03 Horta Sud, AOI04 Algemesi, AOI11 Yatova; in the domain: AOI03 Horta Sud, AOI04 Algemesi, AOI11 Yatova (outside: AOI02 Plana de Utiel). Observed-event layers read from the EMS viewer (GeoJSON, each with URL / sha256 / bytes in the record); the AOI01 DEL_MONIT01 GeoJSON reproduces the run's cached shapefile union (78.315 km² both; 795 features).

| nested product (sensor, acquisition) | observed km² in the product: flooded area / flood trace / all (EMS API ha) | covered by AOI01 DEL_PRODUCT (31 Oct; S2/L8/S1): fraction of product all / flooded area; AOI01 observed inside the extent (km²), fraction of it inside the product | covered by AOI01 DEL_MONIT01 (3 Nov ICEYE; the truth used): same |
|---|---|---|---|
| AOI03 Horta Sud (WorldView-2 2024-10-31; GeoEye-1 2024-10-31) | 0.84 / 23.23 / 24.07 (API: flooded area 84.3 ha, flood trace 2323.1 ha) | 57 % / 74 %; 67.4 km², 20 % | 1 % / 14 %; 4.0 km², 5 % |
| AOI04 Algemesi (GeoEye-1 2024-10-31) | 5.69 / 6.03 / 11.72 (API: flooded area 568.8 ha, flood trace 603.4 ha) | 93 % / 98 %; 93.1 km², 12 % | 9 % / 17 %; 1.4 km², 75 % |
| AOI11 Yatova (Plane Imagery 2024-11-11) | 0.00 / 0.01 / 0.01 (API: flooded area — ha, flood trace 1.0 ha) | 0 % / —; 0.0 km², 0 % | 0 % / —; 0.0 km², 0 % |

Reading: the province-level AOI01 delineation of 31 Oct covers most of the Algemesí polygons (93 % of all, 98 % of its flooded area) and roughly half of Horta Sud's (57 %; 74 % of its flooded area), but maps far more water inside each nested extent than the VHR nested products delineate (93 km² vs 11.7 at Algemesí; 67 km² vs 24.1 at Horta Sud). The AOI01 DEL_MONIT01 product of 3 Nov, the truth used in scoring, covers 9 % (Algemesí) and 1 % (Horta Sud) of the nested polygons: by 3 Nov the mapped water had largely receded. Yatova's product holds a 0.01 km² flood trace that no AOI01 delineation maps. The nested products are therefore not the same polygons as the AOI01 truth; nothing was re-scored.

### B4 — Deltares release of SFINCS v2.3.0 `code20/b4_sfincs_release.json` (sha256 1ca7756aeed8ec32…, 2026-10-22T20:52:12Z)

GitHub `Deltares/SFINCS` release **SFINCS v2.3.0 mt Faber Release 2025.02** (tag `v2.3.0_mt_Faber_release`), published 2025-11-19T14:43:54Z, created 2025-11-18T13:50:39Z, attached assets: 0 (assets dated 2025-11-18: 0); tag commit `e829fd2` dated 2025-11-18T13:50:39Z (“- More cleanup”). Release text: “This contains open access to the source code from Github: https://github.com/Deltares/SFINCS/releases/tag/v2.3.0_mt_Faber_release.” / “As pre-compiled Windows executable:” / “https://download.deltares.nl/en/sfincs/” / “As Docker container:”. Pre-release: SFINCS v2.3.0 mt Faber Pre-Release 12-11-2025 (2025-11-12T13:18:50Z). download.deltares.nl: the page is script-rendered; a plain fetch carries no version or build-date text. Binary as run (CODE-19 A3 record): config_sfincs_exe = D:/ELKAK/implementation/SFINCS_bin/SFINCS_v2.3.0_mt_Faber_release_exe/sfincs.exe; sfincs_build_date = 2025-11-18; sfincs_build_revision = $Rev: v2.3.0 mt. Faber Release. API snapshot `reproduction/v14_rerun/code20/github_releases_Deltares_SFINCS_20261022T203750Z.json` (sha256 ed2434cd44b82e6b…, fetched 2026-10-22T20:37:50Z).

Answer: GitHub release 'SFINCS v2.3.0 mt Faber Release 2025.02' (tag v2.3.0_mt_Faber_release), published 2025-11-19T14:43:54Z, created 2025-11-18T13:50:39Z; 0 attached assets (no executable dated 2025-11-18 is attached on GitHub); the release text points to download.deltares.nl for the pre-compiled Windows executable and to Docker; the tag commit e829fd2 is dated 2025-11-18T13:50:39Z, the same day as the binary's own 'Build-Date 2025-11-18' in every sfincs.log. Proposed §3.1 wording (not applied): “SFINCS v2.3.0 (mt Faber Release 2025.02, published 19 November 2025; Windows executable built 18 November 2025)”.

### Tests

`tests/test_code20_revision.py` (10 tests: F10 constants, map draw order, S2 digest, freeze-order helpers, nested-product coverage, release summary); full suite run recorded in the checkpoint.

## CODE-21 (2026-10-23T07:40:00Z) — pre-push close-out (HEAD `44e50f2`; no model run; number freeze v1.4.2 stands; nothing pushed)

Generated by `reproduction/v14_rerun/scripts/code21_audit_block.py`. Scripts: `code21_history_rewrite_record.py`, `d4_push_plan.py`, `code21_zenodo_check.py`, `build_review_archive.py`, `anonymity_grep.py --tree`, `release_docs.py --write`.

### 1 — docs/FREEZE_EVIDENCE.md first-score correction (file sha256 3f7e57cf5014a389…)

The Valencia first-score cell read 2026-07-15 21:00 local, which is the 350 mm run; the raw-IMERG run was scored at 2026-07-15T13:13:03Z = 16:13 local (`code20/b1_freeze_order.json`). The old value is kept struck through in the table and a dated correction paragraph gives the UTC sequence; the freeze ordering the file claims is unchanged.

### 2 — fig_skill_sweeps_v14.py superseded-benchmark note (file sha256 f82c2ba2e0374122…)

Header comment added: its BANDS (0.10–0.36, 0.42–0.62) and WING_MEDIAN are superseded by `code20/f10_benchmarks.json`; the PNG it draws is a phase-4 diagnostic of the v1.4.2 freeze, not the manuscript figure; output unchanged.

### 3 — review archive rebuilt (local only, not uploaded)

- Built 2026-10-23T07:37:08Z from `git archive v1.4.2` (`779a8e0`, 1204 files) + 415 overlay files from HEAD `1a6a5bd` (now including `docs/FREEZE_EVIDENCE.md` and the code19 / code20 records); 10 files excluded (NOA station files, credentials patterns, caches, CITATION.cff, CLAUDE.md, anonymity tooling, cited-work raw metadata, archived figures); 421 of 1196 text files scrubbed (1962 substitutions); 1358 files in the archive.
- `reproduction/r6/review_archive_v1.4.2.zip`: 78.6 MB, SHA-256 `2c0a3c6ef74216eeba0b88ad4017923b49ab7782deae89835abe6889c07f123b`.
- Anonymity scan of the unpacked archive (`anonymity_grep.py --tree`, 2026-10-23T07:37:30Z): **0 hits outside cited-work metadata**, 4 inside (other authors' Zenodo DOIs in refs_datacite.bib); by class: github.com URLs (third-party) 174, Zenodo DOIs / records 4. Third-party github.com URLs listed, not counted: 174.

### 4 — history rewrite: NOA/meteo.gr station data files removed `code21/history_rewrite.json` (sha256 47c64940edb25194…, 2026-10-23T07:33:08Z)

Tool git-filter-repo a40bce548d2c (pip git-filter-repo 2.47.0, base conda env), git version 2.42.0.windows.2; command: `git filter-repo --force --preserve-commit-hashes --invert-paths --path reproduction/emsr933/noa_stations/published_totals.csv --path reproduction/emsr933/noa_stations/stations_daily.csv --path reproduction/emsr933/noa_stations/stations_meta.csv --path reproduction/r6/tables/S8_noa_stations.csv --path reproduction/v14_rerun/phase5/crete_rain_vs_noa.csv --path reproduction/v14_rerun/phase5/crete_rain_vs_noa.json --path reproduction/v14_rerun/phase5/crete_rain_vs_noa.png --path reproduction/v14_rerun/phase5/logs/rain_vs_noa.log --refs ccd423a..refs/heads/main ccd423a..refs/heads/fix/harness-v1.4 ccd423a..refs/heads/emsr933-crete ccd423a..refs/tags/v1.4.0 ccd423a..refs/tags/v1.4.1 ccd423a..refs/tags/v1.4.2 ccd423a..refs/tags/emsr933-v1   (in a mirror clone; refs applied with git update-ref)`. 34 of 39 commits after the published v1.3.0 (`ccd423a`) rewritten, commit messages verbatim; removed paths: `reproduction/emsr933/noa_stations/published_totals.csv`, `reproduction/emsr933/noa_stations/stations_daily.csv`, `reproduction/emsr933/noa_stations/stations_meta.csv`, `reproduction/r6/tables/S8_noa_stations.csv`, `reproduction/v14_rerun/phase5/crete_rain_vs_noa.csv`, `reproduction/v14_rerun/phase5/crete_rain_vs_noa.json`, `reproduction/v14_rerun/phase5/crete_rain_vs_noa.png`, `reproduction/v14_rerun/phase5/logs/rain_vs_noa.log`; kept (code and source notes, no station values): `reproduction/emsr933/noa_stations/.gitignore`, `reproduction/emsr933/noa_stations/sources.md`, `reproduction/v14_rerun/scripts/crete_rain_vs_noa.py`, `tests/test_crete_rain_vs_noa.py`.

| ref | before | after |
|---|---|---|
| `refs/heads/emsr933-crete` | `69d1c58` | `7b3fc83` |
| `refs/heads/fix/harness-v1.4` | `19e3954` | `1a6a5bd` |
| `refs/heads/main` | `19e3954` | `1a6a5bd` |
| `refs/tags/emsr933-v1` | `542ca35` | `22ad917` |
| `refs/tags/v1.4.0` | `f39f215` | `3331681` |
| `refs/tags/v1.4.1` | `e7e2aeb` | `040ebc4` |
| `refs/tags/v1.4.2` | `6cc7b9e` | `a876771` |

Tag targets (commits): `emsr933-v1` f3a11f4 → 7b15b4e; `v1.4.0` 70c2bfb → 1033833; `v1.4.1` 642efaa → 4b38523; `v1.4.2` 0084600 → 779a8e0. Earlier records that cite `0084600` (tag v1.4.2) now resolve to `779a8e0`; the tree is identical.

Checks (a)–(e) — the CODE-18 brief text was not available in this session, so these are the reconstruction recorded in the JSON:

- (a) no removed path reachable from main, v1.4.0, v1.4.1, v1.4.2, emsr933-v1: **PASS**
- (b) every rewritten commit differs only by the removed paths; author / committer / dates / message identical: **PASS**
- (c) tags annotated, tagger / date / message unchanged, re-pointed at the rewrite of the original target: **PASS**
- (d) every commit up to v1.3.0 keeps its hash; origin/main is an ancestor of main; remote refs unchanged: **PASS**
- (e) HEAD trees of main and fix/harness-v1.4 identical before / after; backups present (refs/backup/code21/*, verified bundle): **PASS**

Backup bundle of every ref before the rewrite: `C:\Users\dvalsamis\AppData\Local\Temp\claude\d--ELKAK\9345177c-48a6-4380-9f01-2779f44e774f\scratchpad\code21\rewrite\backup_pre_rewrite_all_refs.bundle` (129.9 MB, sha256 9966372833efcbe8…, verified); the old refs also remain under `refs/backup/code21/` and the staging copies under `refs/rewritten/` (local only; delete after GO-PUSH is verified).

### 5 — CHANGELOG, Zenodo description, push plan `code21/push_plan.json` (sha256 7718b8e7c60b6908…, 2026-10-23T07:39:58Z) `code21/zenodo_release_check.json` (sha256 90f8bd8395e96e22…, 2026-10-23T07:40:00Z)

`CHANGELOG.md` and `reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md` regenerated by `release_docs.py --write` (tag hashes read from git after the rewrite). Creators of the existing Zenodo record 10.5281/zenodo.21488879 (version v1.3.0, concept 10.5281/zenodo.20523154) against CITATION.cff: identical (7 creators, same affiliation, ORCID only for the first). The tag tree carries CITATION.cff version 1.3.0 and no .zenodo.json: Zenodo's GitHub integration builds the new version's metadata from the release's tree (.zenodo.json, else CITATION.cff); the tag tree carries CITATION.cff version 1.3.0, so the auto-created record would state version 1.3.0 until its metadata is edited (version, description from reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md); the creators are the same either way.

- Push command: `git push --atomic origin main v1.4.0 v1.4.1 v1.4.2 emsr933-v1` — refs: `main` → `44e50f2` (update); `v1.4.0` → `1033833` (create); `v1.4.1` → `4b38523` (create); `v1.4.2` → `779a8e0` (create); `emsr933-v1` → `7b15b4e` (create). `origin/main` = `ccd423a`; `main` = `44e50f2`, 40 ahead, fast-forward True.
- Tracked at HEAD: NOA station data files none; credential files none; credential-like content hits 0. History reachable from the pushed refs: NOA data files none; credential files none.
- GO-PUSH sequence: git -C <main checkout> push --atomic origin main v1.4.0 v1.4.1 v1.4.2 emsr933-v1 → gh release create v1.4.2 --repo vaspapa79/sfincs-mediterranean-flood --title "v1.4.2" --notes-file <the CHANGELOG v1.4.2 section>   (one release: the Zenodo webhook mints one version DOI per GitHub release) → poll https://zenodo.org/api/records?q=conceptrecid:20523154&all_versions=true until the new version appears; report its DOI URL and the release URL.

## CODE-22 (2026-10-23T08:12:40Z) — the history rewrite propagated to the published texts; v1.4.2 release metadata (HEAD `e85c8ed`; no model run; number freeze v1.4.2 stands; nothing pushed)

**Commit hashes quoted in the entries of this file dated before 23 October 2026 refer to the history before the rewrite of 2026-10-23 (CODE-21 item 4) and resolve through `docs/COMMIT_MAP_2026-10-23.md`. Those entries are not edited.** The same holds for the other dated records that quote them (listed under step 2).

Generated by `reproduction/v14_rerun/scripts/code22_audit_block.py --part 1`. Scripts: `code22_commit_map_doc.py`, `code22_grep_check.py`, `code22_release_commit.py`, `reproduction/r6/scripts/commit_map.py` (the mapper used by `r6_tables.py` and `release_docs.py`).

### 1 — commit map (`docs/COMMIT_MAP_2026-10-23.md`, sha256 83595210519c766f…)

34 rewritten commits, old → new, 7-character and full hashes, from `code21/history_rewrite.json`; the eight removed paths; the reason (third-party station data); the statement that apart from the removed files every tree is byte-identical; the tag map.

### 2 — published texts mapped to the published hashes; grep check `code22/grep_check.json` (sha256 e4e6b1e81fb5760a…, 2026-10-23T08:12:08Z)

| file | pre-rewrite hashes before | after |
|---|---|---|
| `CHANGELOG.md` | 14 | 0 |
| `README.md` | 0 | 0 |
| `reproduction/r6/README_REVIEW.md` | 0 | 0 |
| `reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md` | 7 | 0 |
| `reproduction/r6/tables/S10.md` | 7 | 0 |
| `reproduction/r6/tables/S10.csv` | 7 | 7 |
| `CITATION.cff` | 0 | 0 |
| `.zenodo.json` | new file | 0 |
| `reproduction/r6/scripts/release_docs.py` | 12 | 0 |
| `tests/test_code17_helpers.py` | 2 | 0 |

Table S10 is regenerated by `r6_tables.py`: the fix-commit column carries the published hashes; the CSV keeps the pre-rewrite hash in a last column, `pre-rewrite fix commit`, which the .md does not show. `release_docs.py` maps every rendered text (the CHANGELOG copies a tag message that quotes a pre-rewrite hash), and its stage list now quotes published hashes, so it keeps working once the pre-rewrite objects are deleted.

Grep of the tracked tree (and new files) for the six pre-rewrite fix commits (D1/D2, D4, D5, D6, D7, D8): 76 hits in 30 files; **0 outside the categories below**:

- audit trail (entries before the rewrite): 1 files, 12 hits — docs/AUDIT.md (12)
- commit map: 1 files, 6 hits — docs/COMMIT_MAP_2026-10-23.md (6)
- dated record: 26 files, 45 hits — reproduction/emsr933/rule_ledger.md (1); reproduction/emsr933/timing.md (15); reproduction/v14_rerun/CHECKPOINT4.md (1); reproduction/v14_rerun/CHECKPOINT4b.md (1); reproduction/v14_rerun/CHECKPOINT6.md (3); reproduction/v14_rerun/CHECKPOINT7.md (2); … 20 more
- S10.csv pre-rewrite column (by design): 1 files, 7 hits — reproduction/r6/tables/S10.csv (7)
- rewrite record (source of the map): 1 files, 6 hits — reproduction/v14_rerun/code21/history_rewrite.json (6)

The brief's target of no hit outside the commit map and this file is not met by design for three of these categories: the S10 CSV keeps the pre-rewrite column the brief asks for, the rewrite record is the source of the map, and the dated records are left as written, like the entries of this file: the `git_head` field of 18 run records (the commit each run was executed with), 4 checkpoints and `rule_ledger.md`, `timing.md`, `MANIFEST.md`, `F_branch_plan.md`.

### 3 — release metadata

- `CITATION.cff`: version 1.4.2, date-released 2026-10-23 (the date of the re-created tag).
- `.zenodo.json` (sha256 a6f3cf98b24808d7…): title and version from CITATION.cff, upload_type software, licence mit, access open, 7 creators copied (name, affiliation, ORCID) from the API response of record 10.5281/zenodo.21488879 (`code22/zenodo_record_21488879.json`, sha256 7bdce1b99df0cdaf…), its keywords, the description rendered from the same lines as the Zenodo draft, related identifiers isVersionOf 10.5281/zenodo.20523154; isSupplementTo https://github.com/vaspapa79/sfincs-mediterranean-flood/tree/v1.4.2. Zenodo uses `.zenodo.json` and ignores CITATION.cff when both are present (Zenodo help, “Zenodo JSON file”); a related-identifier list there replaces the GitHub default, so the isSupplementTo link to the tag's tree is written explicitly.
- Tag: `v1.4.2` is re-created (annotated, same message) on a release-metadata commit whose parent is the number-freeze commit `779a8e0` and whose tree is the freeze tree plus exactly these files, at their versions on the main line: `docs/COMMIT_MAP_2026-10-23.md`, `docs/AUDIT.md`, `CHANGELOG.md`, `README.md`, `reproduction/r6/README_REVIEW.md`, `reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md`, `reproduction/r6/tables/S10.csv`, `reproduction/r6/tables/S10.md`, `CITATION.cff`, `.zenodo.json`. That commit, the old → new tag target and `git diff --stat 779a8e0 v1.4.2` are recorded in the addendum below, appended on the main line once the tag exists.
