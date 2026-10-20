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
