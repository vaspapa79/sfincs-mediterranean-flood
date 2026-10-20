# Checkpoint 6 — CODE-14: D7 scope + fix (harness v1.4.1), re-runs, Table S3 + row 16, D5 provenance, branch plan

Generated 2026-10-20T09:13:49Z by `checkpoint6_tables.py`. Fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a`. Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside. **Read first: the v1.4.1 Pineios rows use the frozen configuration under the fixed sampler, which injects the Pineios main stem at the Titarisios point (D8, 1128.8 m³/s peak); they are the faithful output of the frozen config, not a recommended canonical until the author decides D8 (the labelled diagnostic row shows the alternative).**

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
- Fix commit `eb661162b2e82ea01ac0c04f8c91442fd2b0c08a`; tests: see AUDIT.md.

## C. v1.4.1 re-runs of the affected runs — four columns (v1.3 published / v1.4.0 / v1.4.1 / Δ = v1.4.1 − v1.4.0)

| run | label | CSI v1.3 publ. | CSI v1.4.0 | CSI v1.4.1 | ΔCSI | HR v1.4.0 → v1.4.1 (Δ) | FAR v1.4.0 → v1.4.1 (Δ) | B v1.4.0 → v1.4.1 (Δ) | GSS v1.4.0 → v1.4.1 | TP/FP/FN v1.4.1 | wet km² v1.4.0 → v1.4.1 | SFINCS s v1.4.1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pineios_enhanced_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_enhanced: canonica | — | 0.495 | pending | | | | | | | | |
| pineios_r2_220_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_r2_220: R2 sweep P | 0.475 | 0.505 | pending | | | | | | | | |
| pineios_r2_295_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_r2_295: R2 sweep P | 0.466 | 0.501 | pending | | | | | | | | |
| pineios_r2_510_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_r2_510: R2 sweep P | 0.446 | 0.486 | pending | | | | | | | | |
| pineios_cn_on_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_cn_on: §4.1.2 (ii) | — | 0.505 | pending | | | | | | | | |
| pineios_raw_imerg_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_raw_imerg: §5: Pin | — | 0.502 | pending | | | | | | | | |
| pineios_qinf5_v141 | v1.4.1 (D7 sampler fix) re-run of pineios_qinf5: §5.2: const | 0.456 | 0.472 | pending | | | | | | | | |

D8 diagnostic `pineios_enhanced_v141_d8titarisios`: pending.

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

pending

## E. D5 provenance (meteo-grid corner vs centre)

pending

## F. Branch reconciliation plan (no push)

pending

## Figures (v1.4.1 products beside the v1.4.0 ones, `phase4/figures/`)

none yet

## NUMBER_MAP.md

`reproduction/v14_rerun/NUMBER_MAP.md`: 79 entries; 1 pending.

## Timing (phase-6 records)

| run | start UTC | end UTC | SFINCS s | published SFINCS s |
|---|---|---|---|---|
| pineios_cn_on_v141 | 2026-10-20T08:43:09Z | None | None | None |
| pineios_enhanced_v141_d8titarisios | 2026-10-20T08:43:09Z | None | None | None |
| pineios_enhanced_v141 | 2026-10-20T08:43:08Z | None | None | 1456.2 |
| pineios_qinf5_v141 | 2026-10-20T08:43:09Z | None | None | 1012.6 |
| pineios_r2_220_v141 | 2026-10-20T08:43:08Z | None | None | None |
| pineios_r2_295_v141 | 2026-10-20T08:43:08Z | None | None | None |
| pineios_r2_510_v141 | 2026-10-20T08:43:09Z | None | None | 1371.7 |
| pineios_raw_imerg_v141 | 2026-10-20T08:43:09Z | None | None | None |

Pending v1.4.1 re-runs: pineios_enhanced, pineios_r2_220, pineios_r2_295, pineios_r2_510, pineios_cn_on, pineios_raw_imerg, pineios_qinf5.
