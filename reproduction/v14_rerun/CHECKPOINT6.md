# Checkpoint 6 — CODE-14: D7 scope + fix (harness v1.4.1), re-runs, Table S3 + row 16, D5 provenance, branch plan

Generated 2026-10-20T11:36:35Z by `checkpoint6_tables.py`. Fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a`. Tag `v1.4.1` = commit `the commit that adds this block (git rev-parse v1.4.1; the tag was re-pointed from 1d0ba4c, see timing.md)`. Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside. **Read first: the v1.4.1 Pineios rows use the frozen configuration under the fixed sampler, which injects the Pineios main stem at the Titarisios point (D8, 1128.8 m³/s peak); they are the faithful output of the frozen config, not a recommended canonical until the author decides D8 (the labelled diagnostic row shows the alternative).**

## A. D7 scope (no runs; `code14/d7_scope.{json,md}`, `scripts/d7_scope.py`)

| runs (identical sfincs.dis) | GloFAS axis | point | written min / max / mean (m³/s) | what was written | nearest cell @ named point: peak (cell) | window-max cell (the sampler's rule): peak (cell) |
|---|---|---|---|---|---|---|
| pineios_enhanced, pineios_r2_220, pineios_r2_295, pineios_r2_510, pineios_cn_on, pineios_raw_imerg, PUB pineios_sfincs_enhanced, PUB bias_sweep/pineios | ascending | pineios_trikala | 11.59 / 11.59 / 11.59 | FALLBACK constant = domain mean 11.589 | 9.07 (21.74, 39.61) | 371.39 (21.84, 39.51) |
|  |  | pineios_kalambaka | 11.59 / 11.59 / 11.59 | FALLBACK constant = domain mean 11.589 | 0.52 (21.64, 39.71) | 2.10 (21.64, 39.61) |
|  |  | titarisios | 11.59 / 11.59 / 11.59 | FALLBACK constant = domain mean 11.589 | 24.41 (22.44, 39.71) | 1128.80 (22.44, 39.81) |
|  |  | enipeas | 11.59 / 11.59 / 11.59 | FALLBACK constant = domain mean 11.589 | 118.40 (22.34, 39.31) | 118.40 (22.34, 39.31) |
| pineios_timevarying_q, pineios_qinf5, PUB pineios_sfincs_v3, PUB pineios_sfincs_v4 | ascending | pineios_trikala | 0.03 / 1.38 / 0.32 | nearest cell @ injection point, hourly linear (audit rebuild) | 9.07 (21.74, 39.61) | 371.39 (21.84, 39.51) |
|  |  | pineios_kalambaka | 0.02 / 0.40 / 0.09 | nearest cell @ injection point, hourly linear (audit rebuild) | 0.52 (21.64, 39.71) | 2.10 (21.64, 39.61) |
|  |  | titarisios | 0.25 / 24.41 / 3.78 | nearest cell @ named point, hourly linear | 24.41 (22.44, 39.71) | 1128.80 (22.44, 39.81) |
|  |  | enipeas | 0.33 / 118.40 / 33.46 | nearest cell @ named point, hourly linear | 118.40 (22.34, 39.31) | 118.40 (22.34, 39.31) |
| strymonas_enhanced, strymonas_enhanced_postD6, strymonas_abl_cnoff_q, strymonas_leadin7d, PUB emsr122_sfincs_v3 | descending | kerkini_outlet | 130.97 / 640.34 / 303.08 | window-max series, step-filled (the sampler, order-agnostic) | 635.59 (23.375, 41.025) | 640.34 (23.475, 40.975) |
|  |  | angitis | 49.34 / 96.81 / 70.79 | window-max series, step-filled (the sampler, order-agnostic) | 88.31 (23.925, 40.975) | 96.81 (23.825, 40.925) |
| strymonas_v1_prefix_src, PUB emsr122_sfincs_enhanced | descending | kerkini_outlet | 119.88 / 618.50 / 290.12 | window-max series, step-filled (the sampler, order-agnostic) | 1.34 (23.175, 41.075) | 618.50 (23.275, 41.125) |
|  |  | angitis | 49.34 / 96.81 / 70.79 | window-max series, step-filled (the sampler, order-agnostic) | 88.31 (23.925, 40.975) | 96.81 (23.825, 40.925) |
| valencia_enhanced_164, valencia_raw_imerg, PUB NHESS valencia rerun_v164 | descending | magro | 14.13 / 42.69 / 23.17 | window-max series, step-filled (the sampler, order-agnostic) | 41.15 (-0.675, 39.175) | 42.69 (-0.625, 39.125) |
|  |  | jucar | 23.50 / 88.81 / 46.22 | window-max series, step-filled (the sampler, order-agnostic) | 90.38 (-0.325, 39.175) | 88.81 (-0.275, 39.175) |
|  |  | turia | 4.45 / 239.72 / 73.58 | window-max series, step-filled (the sampler, order-agnostic) | 237.25 (-0.525, 39.525) | 239.72 (-0.475, 39.525) |
| emilia_enhanced_8aoi, PUB NHESS emilia_emsr664 | descending | lamone | 3.78 / 188.22 / 61.51 | window-max series, step-filled (the sampler, order-agnostic) | 71.69 (11.875, 44.225) | 188.22 (11.975, 44.325) |
|  |  | senio | 3.31 / 166.06 / 54.38 | window-max series, step-filled (the sampler, order-agnostic) | 83.22 (11.825, 44.275) | 166.06 (11.925, 44.275) |
|  |  | montone | 3.31 / 166.06 / 54.38 | window-max series, step-filled (the sampler, order-agnostic) | 82.06 (11.975, 44.175) | 166.06 (11.925, 44.275) |
|  |  | ronco | 4.38 / 171.19 / 51.85 | window-max series, step-filled (the sampler, order-agnostic) | 8.50 (12.025, 44.125) | 171.19 (12.075, 44.225) |
|  |  | savio | 4.09 / 147.53 / 44.24 | window-max series, step-filled (the sampler, order-agnostic) | 32.12 (12.075, 44.075) | 147.53 (12.175, 44.075) |
| PUB emsr122_sfincs_v4 | descending | kerkini_outlet | 119.88 / 618.50 / 290.12 | OTHER series (matches no candidate) | 635.59 (23.375, 41.025) | 640.34 (23.475, 40.975) |
|  |  | angitis | 49.34 / 96.81 / 70.79 | window-max series, step-filled (the sampler, order-agnostic) | 88.31 (23.925, 40.975) | 96.81 (23.825, 40.925) |

Affected (constant fallback written): 8 of 25 R3-on model directories — every pipeline Pineios run (published canonical, published R2-510 sweep, v1.4.0 `pineios_enhanced`, `pineios_r2_220/295/510`, `pineios_cn_on`, `pineios_raw_imerg`). The published v3/v4 and v1.4.0 `pineios_timevarying_q` / `pineios_qinf5` carry the audit rebuild. Strymonas (5), Valencia (2), Emilia (1): the sampler's window-max series (correct). Crete: R3 off.

## B. D7 fix — harness v1.4.1 (`skill/scripts/prep_q_at_outlets.py`, `tests/test_prep_q_sampler.py`)

- Window-max cell rule kept, coordinate masks instead of the label slice (order-agnostic, inclusive, 1e-4° edge tolerance), `NoChannelError` instead of the domain-mean fallback, duplicate-cell report, optional per-point `window_deg`, `q_outlet_cells.json` provenance.
- Real-data regression (`code14/d7_sampler_regression.json`): byte-identical `q_outlet.csv` and `sfincs.dis` for 8 runs (strymonas_enhanced, strymonas_enhanced_postD6, strymonas_abl_cnoff_q, strymonas_v1_prefix_src, strymonas_leadin7d, valencia_enhanced_164, valencia_raw_imerg, emilia_enhanced_8aoi); the Pineios runs get column peaks 371.39 / 2.10 / 1128.80 / 118.40 m³/s (combined hourly peak 1620.7) in place of the constant.
- Fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a`; tests: full suite 151 OK (python -m unittest discover -s tests, 162 s, 2026-10-20T11:31Z-11:34Z, log D:/ELKAK/implementation/v14/_logs/unittest_full_code14_final.log).

## C. v1.4.1 re-runs of the affected runs — four columns (v1.3 published / v1.4.0 / v1.4.1 / Δ = v1.4.1 − v1.4.0)

| run | label | CSI v1.3 publ. | CSI v1.4.0 | CSI v1.4.1 | ΔCSI | HR v1.4.0 → v1.4.1 (Δ) | FAR v1.4.0 → v1.4.1 (Δ) | B v1.4.0 → v1.4.1 (Δ) | GSS v1.4.0 → v1.4.1 | TP/FP/FN v1.4.1 | wet km² v1.4.0 → v1.4.1 | SFINCS s v1.4.1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pineios_enhanced_v141 | canonical enhanced | 0.456 | 0.495 | **0.496** | +0.002 | 0.898 → 0.903 (+0.004) | 0.476 → 0.476 (-0.000) | 1.71 → 1.72 (+0.01) | 0.262 → 0.263 | 60494/54880/6513 | 2585 → 2596 | 2349.728 |
| pineios_r2_220_v141 | R2 sweep Pineios target 220 mm | 0.475 | 0.505 | **0.511** | +0.006 | 0.831 → 0.843 (+0.012) | 0.438 → 0.435 (-0.002) | 1.48 → 1.49 (+0.01) | 0.292 → 0.299 | 56502/43553/10505 | 2229 → 2251 | 2052.998 |
| pineios_r2_295_v141 | R2 sweep Pineios target 295 mm | 0.466 | 0.501 | **0.504** | +0.003 | 0.867 → 0.873 (+0.007) | 0.457 → 0.456 (-0.001) | 1.59 → 1.61 (+0.01) | 0.279 → 0.282 | 58522/49034/8485 | 2405 → 2420 | 2325.05 |
| pineios_r2_510_v141 | R2 sweep Pineios target 510 mm | 0.446 | 0.486 | **0.487** | +0.001 | 0.920 → 0.922 (+0.002) | 0.492 → 0.492 (+0.000) | 1.81 → 1.81 (+0.00) | 0.244 → 0.245 | 61777/59826/5230 | 2729 → 2736 | 1878.321 |
| pineios_cn_on_v141 | §4.1.2 (ii) / §6.2: Pineios CN-on (HSG-B, AMC-II) | — | 0.505 | **0.508** | +0.002 | 0.882 → 0.888 (+0.006) | 0.458 → 0.458 (-0.000) | 1.63 → 1.64 (+0.01) | 0.281 → 0.283 | 59510/50249/7497 | 2455 → 2470 | 2222.802 |
| pineios_raw_imerg_v141 | §5: Pineios raw IMERG (no R2) | — | 0.502 | **0.514** | +0.012 | 0.775 → 0.795 (+0.020) | 0.412 → 0.407 (-0.005) | 1.32 → 1.34 (+0.02) | 0.303 → 0.316 | 53241/36562/13766 | 1987 → 2021 | 1796.934 |
| pineios_qinf5_v141 | §5.2: constant infiltration qinf = 5 mm/h on the time-varyin | 0.456 | 0.472 | **0.483** | +0.011 | 0.814 → 0.834 (+0.020) | 0.471 → 0.466 (-0.005) | 1.54 → 1.56 (+0.02) | 0.247 → 0.258 | 55893/48827/11114 | 2323 → 2356 | 1727.477 |

D8 diagnostic (never canonical) `pineios_enhanced_v141_d8titarisios`: Titarisios sampled at (22.24, 39.71) (window ±0.05°, column peak 42.85 m³/s) instead of the main-stem cell: CSI 0.496 HR 0.901 FAR 0.476 B 1.72 GSS 0.263 (TP/FP/FN 60393/54772/6614); vs the v1.4.1 canonical Δ CSI -0.000 HR -0.002 FAR -0.000 B -0.00; wet 2591 km² vs 2596; SFINCS 1922.775 s.

### Cross-event tables with the v1.4.1 Pineios canonical (`phase4/cross_event_v14_v141.{json,md}`; other events unchanged)


Every number below is read from the JSON named in `cross_event_v14_v141.json` → `events.<run>.sources`. Scores at h > 0.10 m unless stated; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides. Crete = the Tzermiado per-AOI block (tier 1); no union score.

## Table 9 equivalent — strict and fuzzy (r = 1) skill, enhanced runs

| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.3 | HR v1.4 | FAR v1.3 | FAR v1.4 | B v1.3 | B v1.4 | GSS v1.4 | fuzzy r=1 CSI v1.3 | fuzzy r=1 CSI v1.4 | eval km² v1.4 | obs km² v1.4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.1: pineios_enhanced_v141] | 0.456 | **0.496** | 0.947 | 0.903 | 0.532 | 0.476 | 2.02 | 1.72 | 0.263 | 0.426 | 0.461 | 4506.7 | 1507.7 |
| Mandra (EMSR257) | 0.106 | **0.157** | 0.873 | 0.760 | 0.892 | 0.835 | 8.11 | 4.61 | 0.067 | 0.159 | 0.208 | 86.9 | 8.8 |
| Strymonas (EMSR122) | 0.182 | **0.334** | 0.322 | 0.921 | 0.705 | 0.657 | 1.09 | 2.68 | 0.272 | 0.247 | 0.410 | 1196.2 | 104.2 |
| Valencia (EMSR773) | 0.094 | **0.144** | 0.989 | 0.939 | 0.906 | 0.855 | 10.52 | 6.46 | 0.078 | 0.086 | 0.111 | 2709.5 | 195.8 |
| Emilia-R. (EMSR664) | 0.240 | **0.251** | 0.921 | 0.850 | 0.755 | 0.737 | 3.75 | 3.23 | 0.096 | 0.327 | 0.330 | 3148.0 | 567.9 |
| Crete Tzermiado (EMSR933, tier 1) | — | **0.221** | — | 0.988 | — | 0.778 | — | 4.45 | 0.169 | — | 0.195 | 176.9 | 11.3 |

## Table 10 equivalent — enhanced minus baseline (same harness, same mask)

| Event | baseline CSI v1.4 | enhanced CSI v1.4 | ΔCSI v1.4 | ΔHR v1.4 | ΔFAR v1.4 | ΔB v1.4 | ΔCSI v1.3 publ. | ΔHR v1.3 | ΔFAR v1.3 |
|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.1: pineios_enhanced_v141] | 0.543 | 0.496 | -0.046 | +0.063 | +0.081 | +0.33 | -0.061 | +0.124 | +0.114 |
| Mandra (EMSR257) | 0.138 | 0.157 | +0.018 | +0.511 | +0.072 | +3.56 | +0.026 | +0.473 | -0.017 |
| Strymonas (EMSR122) | 0.207 | 0.334 | +0.127 | +0.512 | -0.049 | +1.29 | -0.022 | -0.054 | +0.012 |
| Crete Tzermiado (EMSR933, tier 1) | 0.343 | 0.221 | -0.122 | +0.201 | +0.156 | +2.37 | — | — | — |

## Table 13 equivalent — held-out events

| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.4 | FAR v1.4 | B v1.4 | GSS v1.4 | obs km² | eval km² | note |
|---|---|---|---|---|---|---|---|---|---|
| Valencia (EMSR773) | 0.094 | **0.144** | 0.939 | 0.855 | 6.46 | 0.078 | 195.8 | 2709.5 | AOI union |
| Emilia-R. (EMSR664) | 0.240 | **0.251** | 0.850 | 0.737 | 3.23 | 0.096 | 567.9 | 3148.0 | AOI union |
| Crete Tzermiado (EMSR933, tier 1) | — | **0.221** | 0.988 | 0.778 | 4.45 | 0.169 | 11.3 | 176.9 | per-AOI Tzermiado (tier 1) |

## Table 14 equivalent — base-rate-robust skill (v1.4; v1.3 published in brackets)

| Event | CSI | SEDI | PSS | B | CSI* (threshold) | B* |
|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.1: pineios_enhanced_v141] | 0.496 (0.456) | 0.671 (0.636) | 0.491 (0.423) | 1.72 (2.02) | 0.535 (h>0.25m) [0.515] | 1.25 [1.18] |
| Mandra (EMSR257) | 0.157 (0.106) | 0.456 (0.362) | 0.325 (0.227) | 4.61 (8.11) | 0.159 (h>0.25m) [0.106] | 2.71 [8.11] |
| Strymonas (EMSR122) | 0.334 (0.182) | 0.884 (0.426) | 0.753 (0.249) | 2.68 (1.09) | 0.435 (h>0.50m) [0.189] | 1.95 [1.16] |
| Valencia (EMSR773) | 0.144 (0.094) | 0.706 (0.658) | 0.509 (0.352) | 6.46 (10.52) | 0.242 (h>0.50m) [0.170] | 3.09 [5.51] |
| Emilia-R. (EMSR664) | 0.251 (0.240) | 0.475 (0.460) | 0.326 (0.281) | 3.23 (3.75) | 0.303 (h>0.50m) [0.319] | 1.49 [2.03] |
| Crete Tzermiado (EMSR933, tier 1) | 0.221 (—) | 0.909 (—) | 0.753 (—) | 4.45 (—) | 0.365 (h>0.50m) [—] | 2.28 [—] |

## Threshold sweep (v1.4, enhanced): CSI at 0.05 / 0.10 / 0.25 / 0.50 m; fuzzy r = 0..3; one-sided r = 1

| Event | 0.05 | 0.10 | 0.25 | 0.50 | r=0 | r=1 | r=2 | r=3 | model-oriented r=1 | obs-oriented r=1 | truth buffer −20 / 0 / +20 m | time-matched (to latest acq) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.1: pineios_enhanced_v141] | 0.446 | 0.496 | 0.535 | 0.508 | 0.496 | 0.461 | 0.460 | 0.480 | 0.539 | 0.392 | 0.483 / 0.496 / 0.505 | 0.496 |
| Mandra (EMSR257) | 0.141 | 0.157 | 0.159 | 0.143 | 0.157 | 0.208 | 0.257 | 0.305 | 0.221 | 0.126 | 0.086 / 0.157 / 0.194 | 0.157 |
| Strymonas (EMSR122) | 0.329 | 0.334 | 0.356 | 0.435 | 0.334 | 0.410 | 0.460 | 0.499 | 0.413 | 0.293 | 0.307 / 0.334 / 0.348 | 0.334 |
| Valencia (EMSR773) | 0.114 | 0.144 | 0.191 | 0.242 | 0.144 | 0.111 | 0.114 | 0.127 | 0.166 | 0.090 | 0.135 / 0.144 / 0.149 | 0.144 |
| Emilia-R. (EMSR664) | 0.227 | 0.251 | 0.285 | 0.303 | 0.251 | 0.330 | 0.413 | 0.486 | 0.358 | 0.202 | 0.222 / 0.251 / 0.268 | 0.251 |
| Crete Tzermiado (EMSR933, tier 1) | 0.159 | 0.221 | 0.303 | 0.365 | 0.221 | 0.195 | 0.190 | 0.194 | 0.340 | 0.115 | union: 0.044 / 0.074 / 0.087 | union: 0.074 |

## D. Loose ends

### Table S3 equivalent — evaluation-mask sensitivity, v1.4 mask as the reference (`code14/table_s3_v14.{json,md}`)

| Event | mask | area km² | CSI | HR | FAR | B | GSS | published S3 CSI (v1.3 mask) |
|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) | Active mask (no AOI) | 4956 | 0.468 | 0.898 | 0.506 | 1.82 | 0.252 | 0.347 |
|  | AOI-union (v1.4 reference) | 4507 | 0.495 | 0.898 | 0.476 | 1.71 | 0.262 | 0.456 |
|  | AOI-union + 1 km | 4575 | 0.490 | 0.898 | 0.481 | 1.73 | 0.260 | 0.44 |
|  | AOI-union − 1 km | 4414 | 0.499 | 0.898 | 0.471 | 1.70 | 0.262 | 0.471 |
| Mandra (EMSR257) | Active mask (no AOI) | 280 | 0.070 | 0.760 | 0.928 | 10.60 | 0.041 | 0.031 |
|  | AOI-union (v1.4 reference) | 87 | 0.157 | 0.760 | 0.835 | 4.61 | 0.067 | 0.106 |
|  | AOI-union + 1 km | 122 | 0.123 | 0.760 | 0.872 | 5.92 | 0.058 | 0.071 |
|  | AOI-union − 1 km | 48 | 0.198 | 0.770 | 0.789 | 3.65 | 0.076 | 0.149 |
| Strymonas (EMSR122) | Active mask (no AOI) | 3985 | 0.318 | 0.921 | 0.673 | 2.82 | 0.300 | 0.157 |
|  | AOI-union (v1.4 reference) | 1196 | 0.334 | 0.921 | 0.657 | 2.68 | 0.272 | 0.183 |
|  | AOI-union + 1 km | 1279 | 0.331 | 0.921 | 0.659 | 2.70 | 0.274 | 0.182 |
|  | AOI-union − 1 km | 1109 | 0.336 | 0.922 | 0.654 | 2.67 | 0.269 | 0.185 |
| Valencia (EMSR773) | Active mask (no AOI) | 2915 | 0.139 | 0.939 | 0.860 | 6.70 | 0.077 | — |
|  | AOI-union (v1.4 reference) | 2710 | 0.144 | 0.939 | 0.855 | 6.46 | 0.078 | — |
|  | AOI-union + 1 km | 2723 | 0.144 | 0.939 | 0.855 | 6.48 | 0.078 | — |
|  | AOI-union − 1 km | 2692 | 0.144 | 0.939 | 0.854 | 6.44 | 0.078 | — |
| Emilia-R. (EMSR664) | Active mask (no AOI) | 5007 | 0.176 | 0.850 | 0.819 | 4.68 | 0.074 | — |
|  | AOI-union (v1.4 reference) | 3148 | 0.251 | 0.850 | 0.737 | 3.23 | 0.096 | — |
|  | AOI-union + 1 km | 3435 | 0.238 | 0.850 | 0.752 | 3.43 | 0.094 | — |
|  | AOI-union − 1 km | 2823 | 0.258 | 0.859 | 0.731 | 3.19 | 0.094 | — |

### MANIFEST row 16 — Mandra v3 post-hoc mask restriction, recreated on the v1.4 build (`scripts/mandra_v3_maskrestrict_v14.py`)

- Mask edit: 76992 cells deactivated by the published v3 edit; v1.4 active 117667 → 69660 cells (294.2 → 174.2 km²; boundary cells 3253 → 1141); index file kept.

| column | CSI | HR | FAR | B | GSS | TP/FP/FN |
|---|---|---|---|---|---|---|
| v1.3 published (S2 text) | 0.083 | 0.775 | — | 9.08 | — | — |
| v1.3 output re-scored, published mask | 0.083 | 0.775 | 0.915 | 9.08 | 0.004 | 2787/29847/808 |
| v1.3 output re-scored, new mask | 0.103 | 0.775 | 0.893 | 7.26 | 0.006 | 2734/22888/794 |
| v1.4 canonical Mandra (unrestricted, for reference) | 0.157 | 0.760 | 0.835 | 4.61 | 0.067 | 2682/13587/846 |
| **v1.4.1 build + published mask edit** | **0.099** | 0.719 | 0.898 | 7.02 | 0.001 | 2537/22222/991 |

SFINCS 1435.642 s (published 1906.7 s); published-text check (CSI/HR at 3 dp on the re-scored published mask): True / True.

## E. D5 provenance (meteo-grid corner vs centre)

**Finding (2026-10-20): D5 is already reported upstream, by the SFINCS maintainer, the day we diagnosed it. No public issue was opened or commented from our side; no D5 reproducer is needed.**

Searched: the Deltares/SFINCS and Deltares/hydromt_sfincs issue trackers (title/body search for netamp, netampr, netamuamv, meteo grid, half cell, cell centre/corner, lower-left), the SFINCS release notes (v2.0.0 … v2.4.0 Galibier), the SFINCS manual (input/forcing page) and the hydromt_sfincs release notes.

- **Deltares/SFINCS issue #386** — "NetCDF gridded meteo (netamuamv, netamp, netampr) applied half a grid cell to the north-east", opened 2026-10-19 by *Leynse* (T. Leijnse, SFINCS developer), **open**, no comments, no linked PR. It states exactly our D5 mechanism: the NetCDF readers in `sfincs_ncinput.F90` set `x_llcorner = x(1)`, `y_llcorner = y(1)` (the first coordinate values, which per CF and as written by HydroMT-SFINCS are cell *centres*), the interpolation in `sfincs_meteo.f90` treats them as the lower-left *corner* and adds half a cell, "so the whole wind, pressure and rain field is applied half a meteo grid cell to the north-east". Found during the "potential error sweep" (issue #375, opened 2026-10-08, milestone **2026.02 release**); not fixed there "because it changes results for every model with netCDF gridded meteo". Proposed fix: subtract half a cell in the three NetCDF readers (ASCII path unchanged); the author asks the maintainers to confirm that all supported producers write cell centres and whether y may be stored descending. Our independent evidence (`docs/AUDIT.md`, IB shortfall diagnosis, 2026-10-19T08:14Z): sampling the pressure grid half a netamp cell off reproduces the modelled Pineios boundary level exactly (RMSE 0.0000 m, r = 1.0000); registered as D5 (report only, not changed in v1.4).
- **hydromt_sfincs:** no issue or PR on the registration of the meteo grid. Related only: PR #261 (x/y dimension naming for SFINCS meteo NetCDF, merged 2025-06-12), PR #348 (buffer for clipping meteo datasets, merged 2026-03-24), the v2.0.0-rc2 note "variables in netcdf forcing files compliant with SFINCS kernel conventions" (#316).
- **Manual:** the forcing page does not define the meaning of the NetCDF meteo x/y (only the ASCII header shows `x_llcorner`/`y_llcorner`, unexplained) and points to HydroMT-SFINCS for creating the files.
- **Release notes:** no SFINCS release mentions the offset; v2.4.0 Galibier (2026-06-15) is the latest release and is affected (the issue post-dates it).
- **D6 cross-check while there:** the curve-number sink is Deltares/SFINCS issue #253 (D. Eilander, 2025-12-18; closed 2026-02-11 via PR #254 by Leynse; workaround `storecumprcp = 1`), release note v2.4.0 "Fixed bug with Curve Number infiltration if storecumprcp = 0 (default)". `reproduction/v14_harness/reproducer_D6.md` now carries these references (status paragraph); it stays a private draft.

Consequences for the record: D5 keeps its status (known upstream, unfixed in any release; harness v1.4 compensates in the forcing-file writer, `tests/test_meteo_alignment_v14.py`). If the author wishes, the only useful private contribution is a confirmation of #386 with our exact-reproduction check; nothing else to send. The `reproducer_D5_D6.md` extension was not written because the condition ("if unreported") is not met.

Sources: [SFINCS issue #386](https://github.com/Deltares/SFINCS/issues/386) · [SFINCS issue #375](https://github.com/Deltares/SFINCS/issues/375) · [SFINCS issue #253](https://github.com/Deltares/SFINCS/issues/253) · [SFINCS releases](https://github.com/Deltares/SFINCS/releases) · [SFINCS manual, forcing](https://sfincs.readthedocs.io/en/latest/input_forcing.html) · [hydromt_sfincs releases](https://github.com/Deltares/hydromt_sfincs/releases) · [hydromt_sfincs issues (meteo search)](https://github.com/Deltares/hydromt_sfincs/issues?q=meteo)

## F. Branch reconciliation plan (no push)

**Why `fix/harness-v1.4` shares no history with `main` (facts from `git`, 2026-10-20):**

- Local `main` (checked out in `D:/ELKAK/sfincs-mediterranean-floods`) is a 4-commit history rooted at `6fc4672` "Initial release: SFINCS Mediterranean flood reproduction pipeline" → `23a8ec7` rename → `5c58b2f` R2 (Kerkini src fix) → `f6e7c01` R1 (machine-local override + preflight), all created locally in June 2026. It was never pushed: `git merge-base main fix/harness-v1.4` is empty.
- `fix/harness-v1.4` descends from the **published** history: root `269125c` "Add files via upload" (2026-05-29, the GitHub web upload = tags `v.0.0.1` / `v1.0.0`) → `86b7690` v1.1.0 → `738fa3d` v1.2.0 → `ccd423a` **v1.3.0 = `origin/main`** (github.com/vaspapa79/sfincs-mediterranean-flood.git; `git ls-remote` on 2026-10-20 still shows `refs/heads/main` = `ccd423a`, nothing newer) → 33 harness commits (`513ce5a` … `70c2bfb` = `v1.4.0`, `9ffbb95`, `eb66116` = D7 fix, …). The worktree was created from `origin/main`, so the branch is an ordinary fast-forward descendant of the published v1.3.0, not an orphan; the orphan is local `main`.
- Local `main` contributes nothing the branch lacks: `git diff --name-status fix/harness-v1.4 main` shows no file that exists only in `main`; against `v1.3.0` it is *older* (25 files, 1683 deletions: it lacks `docs/FREEZE_EVIDENCE.md`, `docs/REPRODUCIBILITY.md`, `docs/frozen_rule_R.md`, `reports/*.json`, the Valencia/Emilia YAMLs, `validation/score_fuzzy_onesided.py`, `validation/truth_uncertainty.py`). R1/R2 are present on the branch (`_common._load_machine_override`, the relocated Kerkini source in the example YAML).
- The main checkout's working tree is dirty: 9 tracked files modified (its tree is close to v1.3.0: vs `v1.3.0` only README.md and validate_event_v2.py differ materially) and untracked `CLAUDE.md`, `docs/` (AUDIT.md, CODEBASE_MAP.md, VALIDATION_FINDINGS.md, `_sources/`, `bias_sensitivity/` — the R2-sweep CSVs that `phase1.py` reads by absolute path —, cn_diagnostic.*, fuzzy_onesided.*, grid_matched_baseline.md, independent_truth.md, truth_uncertainty.*), `export/sfincs_bundle/`, `figures/`, `validation/{skill_scores,test_skill_scores,score_fuzzy_onesided,truth_uncertainty}.py`. Four of those paths are tracked on the branch — `docs/AUDIT.md` (the main-checkout copy, 373 lines, is an older strict subset of the branch's 519-line file: `diff` shows no line unique to the copy), `validation/skill_scores.py`, `validation/score_fuzzy_onesided.py`, `validation/truth_uncertainty.py` (the three copies are byte-identical to the branch) — so a plain `git checkout` of the branch in that directory would be refused until they are moved aside; none of them carries content the branch lacks.

**Proposal (nothing executed, nothing pushed):** the "fast-forward" case applies in substance — `main` has no commits beyond v1.3.0 in content, and v1.3.0 → v1.4.1 is a true fast-forward from the published `origin/main`.

1. In the main checkout: `git branch archive/local-main-2026-06 main` (keeps the four local commits and their tags-less history), then `git add -A && git commit -m "archive: local pre-GitHub working tree as of 2026-10-20"` **on that archive branch** (`git switch archive/local-main-2026-06` first) so the dirty tree and the untracked docs/figures/export are preserved verbatim with provenance; `export/sfincs_bundle` and `docs/_sources` may instead be moved to `D:/ELKAK/deliverables/` if the author prefers them outside git (they are not part of the publishable repo).
2. `git branch -f main fix/harness-v1.4` (local `main` := v1.4.1; equivalently `git switch -C main fix/harness-v1.4`), `git branch --set-upstream-to=origin/main main`. The worktree `.worktrees/emsr933-crete` keeps working on `fix/harness-v1.4` (a branch cannot be checked out twice); after the switch, `fix/harness-v1.4` can be deleted or kept as a pointer — recommendation: keep until the Zenodo release is cut.
3. Restore what the harness needs from the archive into the new `main` tree as tracked files: `docs/bias_sensitivity/*.csv` (R2 sweep CSVs; `phase1.py` BIAS_CSV path then becomes repo-relative — one-line change), `figures/fig_rain_bias_spatial.py` (+ png); decide per file for CODEBASE_MAP.md / VALIDATION_FINDINGS.md / cn_diagnostic / independent_truth / grid_matched_baseline (the branch's `docs/AUDIT.md` already links to several of them by name: §3 of AUDIT.md refers to `bias_sensitivity/`, `grid_matched_baseline.md`, `independent_truth.md`, `cn_diagnostic.md`, `truth_uncertainty.md` — all currently missing on the branch, so these should be committed on `main` in the same step).
4. Publish-time (author): `git push origin main --follow-tags` would move the GitHub `main` from v1.3.0 to v1.4.1 as a fast-forward and add tags `v1.4.0` and `v1.4.1` (annotated); nothing is force-pushed, v1.3.0 stays reachable. The CITATION.cff version bump and `.zenodo.json` are a separate release commit. Note the remote repository name (`sfincs-mediterranean-flood`, singular) still differs from CITATION.cff / README (`sfincs-mediterranean-floods`).

If the author prefers to keep the local-main commits in the published graph instead, the alternative is `git merge --allow-unrelated-histories -s ours archive/local-main-2026-06` on `main` (records the archive as an ancestor without changing the tree); both tags are preserved either way. Not recommended: it adds four commits whose tree is a stale subset.

## Figures (v1.4.1 products beside the v1.4.0 ones, `phase4/figures/`)

- `fig10_skill_v14_v141.png`
- `fig11_sweeps_v14_v141.png`
- `map_pineios_cn_on_v141_v14.png`
- `map_pineios_enhanced_v141_d8titarisios_v14.png`
- `map_pineios_enhanced_v141_v14.png`
- `map_pineios_qinf5_v141_v14.png`
- `map_pineios_r2_220_v141_v14.png`
- `map_pineios_r2_295_v141_v14.png`
- `map_pineios_r2_510_v141_v14.png`
- `map_pineios_raw_imerg_v141_v14.png`
- `rain_pineios_enhanced_v141_v14.png`
- `map_mandra_v3_maskrestrict_v14.png`

## NUMBER_MAP.md

`reproduction/v14_rerun/NUMBER_MAP.md`: 79 entries; v1.4.1 column present, 20 entries differ from v1.4.0; 0 pending.

## Timing (phase-6 records)

| run | start UTC | end UTC | SFINCS s | published SFINCS s |
|---|---|---|---|---|
| mandra_v3_maskrestrict | 2026-10-20T09:09:00Z | 2026-10-20T09:33:15Z | 1435.642 | 1906.7 |
| pineios_cn_on_v141 | 2026-10-20T09:35:21Z | 2026-10-20T10:17:31Z | 2222.802 | None |
| pineios_enhanced_v141_d8titarisios | 2026-10-20T10:53:52Z | 2026-10-20T11:31:10Z | 1922.775 | None |
| pineios_enhanced_v141 | 2026-10-20T08:47:10Z | 2026-10-20T09:35:20Z | 2349.728 | 1456.2 |
| pineios_qinf5_v141 | 2026-10-20T10:17:31Z | 2026-10-20T10:53:52Z | 1727.477 | 1012.6 |
| pineios_r2_220_v141 | 2026-10-20T09:35:20Z | 2026-10-20T10:16:33Z | 2052.998 | None |
| pineios_r2_295_v141 | 2026-10-20T08:47:21Z | 2026-10-20T09:35:21Z | 2325.05 | None |
| pineios_r2_510_v141 | 2026-10-20T10:16:33Z | 2026-10-20T10:53:34Z | 1878.321 | 1371.7 |
| pineios_raw_imerg_v141 | 2026-10-20T10:53:34Z | 2026-10-20T11:30:49Z | 1796.934 | None |

Tests: full suite 151 OK (python -m unittest discover -s tests, 162 s, 2026-10-20T11:31Z-11:34Z, log D:/ELKAK/implementation/v14/_logs/unittest_full_code14_final.log).
