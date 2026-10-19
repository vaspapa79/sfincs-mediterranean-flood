# Checkpoint 4 — Phase 1 of the harness-v1.4 re-run (generated 2026-10-19T12:35:08Z by `checkpoint4_tables.py`)

Commits: D5 `8ccabb03f5f2164be5b52c0633aac1bfff0d73ca` (2026-10-19T08:57:24Z); evaluation-mask exclusion `c6f39fad46b8a71b0172d1b19809d875f415ccd6` (2026-10-19T09:04:55Z). Scores at h > 0.10 m, strict, evaluation universe = msk > 0 ∩ AOI union (published) or minus the exclusion (new mask = WorldCover 80 at the cell centre ∪ v1.4 open sea, removed from model and truth).

## D5 proof
D5 proof (`reproduction/v14_harness/D5_synthetic_results.json` 2026-10-19T08:55:37Z, `pineios_slice_d5_result.json` 2026-10-19T08:54:50Z): (i) linear pressure gradient, boundary zs vs (101325 − p)/(ρg) at the cell centres — aligned RMSE 0.0000 m (max 0.0000), unaligned control RMSE 0.0995 m (meteo cell 25.4 km); (iii) 30-min IMERG pulse on one cell — aligned centroid offset +0.1/-0.5 m, relative RMSE 0.00002, share inside the written footprint 0.657 (expected 0.657); unaligned +5018/-5017 m (half of the 10.0-km cell east and south), share 0.375; (ii) one-day Pineios slice with aligned grids: modelled − expected (bilinear at the true centres) mean -0.00000 m, RMSE 0.00000 m, max 0.00002 m, r 1.0000, fit slope 1.0000 (CODE-12 before: mean -0.0056, RMSE 0.0066, r 0.9836) — the IB-shortfall item is closed, explained by D5.

## D6 — curve-number sink (report only)
**D6 (new, report only; `reproduction/v14_harness/D6_CN_SINK.md`)**: SFINCS v2.3.0 curve-number infiltration ('cna', the `setup_cn_infiltration` route) adds the infiltration increment to `cuminf` only when `storecumprcp = 1` (`sfincs_infiltration.f90:107`; default 0, `sfincs_input.f90:219,439-441`) while `cumprcp` always accumulates (`sfincs_meteo.f90:1266`) and the volume has no floor (`sfincs_continuity.f90:~535`): past Ia = 0.2 S a cell removes the whole cumulative infiltration every time step — an unbounded sink for rain and inflow. Synthetic closed plain (`D6_cn_sink_check.json` 2026-10-19T10:02:43Z; CN 76, 30 mm rain + 20 m³/s for 12 h): end volume 0 m³ with storecumprcp 0 vs 1062676 m³ with 1 (expected 1062364; ratio 1.0003). Strymonas v3 enhanced (`D6_strymonas_sink_cells.json` 2026-10-19T10:03:05Z, inputs only): cells past Ia by the end 1904.9 km² (40.8%) with the published rain vs 244.1 km² (5.8%) with the v1.4 rain; Serres-plain window 27.5% vs 1.3%. Water on land, peak/end (`strymonas_v14_diagnosis.json` 2026-10-19T10:07:12Z): published 52.5/10.9 Mm³, v1.4 314.8/314.8 Mm³ for 311.9 Mm³ of discharge in the simulated week; isolation runs on copies: E1_v14_zsini0 314.8/314.8; E2_v14_publishedrain 52.5/10.9; E3_v13_zsini_dry 52.5/10.9; E4_v13_plusIB 52.5/10.9; E5_v14_unalignedwindpress 314.8/314.8; E6_v14_noIB 314.8/314.8. The v1.4 Strymonas enhanced score below still contains the sink and is not a valid v1.4 number; the fix (v1.4 `storecumprcp = 1` with CN) awaits the author's decision.

## Strymonas EMSR122 (v3 canonical)

Exclusion (`masks/strymonas_exclusion.tif`, 2026-10-19T09:06:58Z): open sea 22427 cells (504.6075 km²; v1.4 build vs published gis symmetric difference 0 cells), WC80 29501 (663.7725 km², of which land 7906), union 30333 (682.4925 km²) on the whole grid.

| run | metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 new − v1.3 published) | of which mask | of which harness |
|---|---|---|---|---|---|---|---|
| strymonas_baseline | CSI | 0.204 | 0.197 | 0.207 | +0.003 | -0.007 | +0.009 |
| strymonas_baseline | HR | 0.377 | 0.367 | 0.410 | +0.033 | -0.010 | +0.043 |
| strymonas_baseline | FAR | 0.692 | 0.701 | 0.706 | +0.013 | +0.008 | +0.005 |
| strymonas_baseline | B | 1.22 | 1.22 | 1.39 | +0.17 | +0.00 | +0.17 |
| strymonas_baseline | GSS | 0.155 | 0.148 | 0.155 | -0.000 | -0.007 | +0.007 |
| strymonas_baseline | TP / FP / FN cells | 1784 / 4011 / 2953 | 1698 / 3972 / 2935 | 1899 / 4551 / 2734 | | | |
| strymonas_baseline | eval km² / observed km² | 1222.7 / 106.6 | 1196.2 / 104.2 | 1196.2 / 104.2 | | | |
| strymonas_baseline | modelled wet in eval km² | 130.4 | 127.6 | 145.1 | | | |
| strymonas_baseline | fuzzy r=1 CSI | 0.231 | 0.226 | 0.229 | -0.002 | -0.005 | +0.003 |
| strymonas_baseline | excluded in eval / observed removed | — | 1175 cells (26.4 km²) / 104 cells (2.34 km²) | same mask | | | |
| strymonas_baseline | active cells / msk=2 / bnd points | 207374 / 346 / 0 | | 185824 / ring 877 / 19 | | | |
| strymonas_baseline | SFINCS wall-clock s | 256.5 (published) | | 145.146 | | | |
| strymonas_enhanced (pre-D6, invalid) | CSI | 0.182 | 0.180 | 0.333 | +0.151 | -0.002 | +0.153 |
| strymonas_enhanced (pre-D6, invalid) | HR | 0.322 | 0.319 | 0.906 | +0.584 | -0.003 | +0.587 |
| strymonas_enhanced (pre-D6, invalid) | FAR | 0.705 | 0.708 | 0.655 | -0.049 | +0.003 | -0.053 |
| strymonas_enhanced (pre-D6, invalid) | B | 1.09 | 1.09 | 2.63 | +1.54 | +0.00 | +1.53 |
| strymonas_enhanced (pre-D6, invalid) | GSS | 0.136 | 0.134 | 0.272 | +0.136 | -0.002 | +0.138 |
| strymonas_enhanced (pre-D6, invalid) | TP / FP / FN cells | 1526 / 3639 / 3211 | 1480 / 3587 / 3153 | 4198 / 7980 / 435 | | | |
| strymonas_enhanced (pre-D6, invalid) | eval km² / observed km² | 1222.7 / 106.6 | 1196.2 / 104.2 | 1196.2 / 104.2 | | | |
| strymonas_enhanced (pre-D6, invalid) | modelled wet in eval km² | 116.2 | 114.0 | 274.0 | | | |
| strymonas_enhanced (pre-D6, invalid) | fuzzy r=1 CSI | 0.247 | 0.242 | 0.404 | +0.157 | -0.005 | +0.162 |
| strymonas_enhanced (pre-D6, invalid) | excluded in eval / observed removed | — | 1175 cells (26.4 km²) / 104 cells (2.34 km²) | same mask | | | |
| strymonas_enhanced (pre-D6, invalid) | active cells / msk=2 / bnd points | 207374 / 346 / 0 | | 185824 / ring 877 / 19 | | | |
| strymonas_enhanced (pre-D6, invalid) | SFINCS wall-clock s | 109.2 (published) | | 168.394 | | | |
| strymonas_enhanced (pre-D6, invalid) | **D6** | sink on 41% of the area | (same output) | sink on 6% — **pre-D6, invalid** (re-run in CHECKPOINT4b.md) | | | |

False alarms of the published v1.3 enhanced run (3639 cells, 81.88 km², published mask, h > 0.10 m): on open sea 0 (0.0%), on WC80 52 (1.4%; land part 52), on inland zb < 0 17 (0.5%); union of the three 55 (1.5%). Observed cells inside WC80 ∪ open sea: 104 (TP there 46).

## Mandra EMSR257

Exclusion (`masks/mandra_exclusion.tif`, 2026-10-19T09:13:49Z): open sea 48187 cells (120.4675 km²; v1.4 build vs published gis symmetric difference 0 cells), WC80 49792 (124.48 km², of which land 1976), union 50163 (125.4075 km²) on the whole grid.

| run | metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 new − v1.3 published) | of which mask | of which harness |
|---|---|---|---|---|---|---|---|
| mandra_baseline | CSI | 0.080 | 0.152 | 0.138 | +0.059 | +0.072 | -0.014 |
| mandra_baseline | HR | 0.400 | 0.389 | 0.249 | -0.151 | -0.011 | -0.140 |
| mandra_baseline | FAR | 0.910 | 0.800 | 0.763 | -0.147 | -0.109 | -0.037 |
| mandra_baseline | B | 4.43 | 1.95 | 1.05 | -3.38 | -2.49 | -0.90 |
| mandra_baseline | GSS | 0.008 | 0.081 | 0.084 | +0.076 | +0.073 | +0.003 |
| mandra_baseline | TP / FP / FN cells | 1439 / 14499 / 2156 | 1372 / 5498 / 2156 | 879 / 2829 / 2649 | | | |
| mandra_baseline | eval km² / observed km² | 109.7 / 9.0 | 86.9 / 8.8 | 86.9 / 8.8 | | | |
| mandra_baseline | modelled wet in eval km² | 39.8 | 17.2 | 9.3 | | | |
| mandra_baseline | fuzzy r=1 CSI | 0.139 | 0.198 | 0.171 | +0.032 | +0.059 | -0.027 |
| mandra_baseline | excluded in eval / observed removed | — | 9109 cells (22.8 km²) / 67 cells (0.17 km²) | same mask | | | |
| mandra_baseline | active cells / msk=2 / bnd points | 162335 / 453 / 0 | | 117667 / ring 3519 / 31 | | | |
| mandra_baseline | SFINCS wall-clock s | 546.6 (published) | | 112.521 | | | |
| mandra_enhanced | CSI | 0.106 | 0.150 | 0.157 | +0.051 | +0.044 | +0.007 |
| mandra_enhanced | HR | 0.873 | 0.871 | 0.760 | -0.113 | -0.002 | -0.111 |
| mandra_enhanced | FAR | 0.892 | 0.847 | 0.835 | -0.057 | -0.046 | -0.012 |
| mandra_enhanced | B | 8.11 | 5.69 | 4.61 | -3.50 | -2.43 | -1.08 |
| mandra_enhanced | GSS | 0.028 | 0.056 | 0.067 | +0.039 | +0.029 | +0.011 |
| mandra_enhanced | TP / FP / FN cells | 3140 / 26028 / 455 | 3073 / 16989 / 455 | 2682 / 13587 / 846 | | | |
| mandra_enhanced | eval km² / observed km² | 109.7 / 9.0 | 86.9 / 8.8 | 86.9 / 8.8 | | | |
| mandra_enhanced | modelled wet in eval km² | 72.9 | 50.2 | 40.7 | | | |
| mandra_enhanced | fuzzy r=1 CSI | 0.159 | 0.205 | 0.208 | +0.049 | +0.045 | +0.003 |
| mandra_enhanced | excluded in eval / observed removed | — | 9109 cells (22.8 km²) / 67 cells (0.17 km²) | same mask | | | |
| mandra_enhanced | active cells / msk=2 / bnd points | 162335 / 453 / 0 | | 117667 / ring 3519 / 31 | | | |
| mandra_enhanced | SFINCS wall-clock s | 1097.8 (published) | | 398.702 | | | |

False alarms of the published v1.3 enhanced run (26028 cells, 65.07 km², published mask, h > 0.10 m): on open sea 8757 (33.6%), on WC80 8989 (34.5%; land part 282), on inland zb < 0 81 (0.3%); union of the three 9111 (35.0%). Observed cells inside WC80 ∪ open sea: 67 (TP there 67).

## Pineios EMSR692 (baseline = grid-matched)

Exclusion (`masks/pineios_exclusion.tif`, 2026-10-19T09:23:47Z): open sea 39490 cells (888.525 km²; v1.4 build vs published gis symmetric difference 0 cells), WC80 42200 (949.5 km², of which land 2711), union 42201 (949.5225 km²) on the whole grid.

| run | metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 new − v1.3 published) | of which mask | of which harness |
|---|---|---|---|---|---|---|---|
| pineios_baseline_gridmatched | CSI | 0.517 | 0.543 | 0.543 | +0.026 | +0.026 | -0.000 |
| pineios_baseline_gridmatched | HR | 0.823 | 0.823 | 0.840 | +0.017 | -0.001 | +0.017 |
| pineios_baseline_gridmatched | FAR | 0.418 | 0.385 | 0.395 | -0.023 | -0.033 | +0.010 |
| pineios_baseline_gridmatched | B | 1.42 | 1.34 | 1.39 | -0.03 | -0.08 | +0.05 |
| pineios_baseline_gridmatched | GSS | 0.319 | 0.351 | 0.347 | +0.028 | +0.032 | -0.005 |
| pineios_baseline_gridmatched | TP / FP / FN cells | 55561 / 39972 / 11943 | 55118 / 34551 / 11889 | 56285 / 36737 / 10722 | | | |
| pineios_baseline_gridmatched | eval km² / observed km² | 4642.3 / 1518.8 | 4506.7 / 1507.7 | 4506.7 / 1507.7 | | | |
| pineios_baseline_gridmatched | modelled wet in eval km² | 2149.5 | 2017.6 | 2093.0 | | | |
| pineios_baseline_gridmatched | fuzzy r=1 CSI | 0.509 | 0.524 | 0.518 | +0.010 | +0.015 | -0.005 |
| pineios_baseline_gridmatched | excluded in eval / observed removed | — | 6029 cells (135.7 km²) / 497 cells (11.18 km²) | same mask | | | |
| pineios_baseline_gridmatched | active cells / msk=2 / bnd points | 262465 / 650 / 0 | | 223703 / ring 728 / 12 | | | |
| pineios_baseline_gridmatched | SFINCS wall-clock s | 1006.4 (published) | | 979.893 | | | |
| pineios_enhanced | CSI | 0.456 | 0.473 | 0.495 | +0.039 | +0.017 | +0.022 |
| pineios_enhanced | HR | 0.947 | 0.946 | 0.898 | -0.048 | -0.000 | -0.048 |
| pineios_enhanced | FAR | 0.532 | 0.514 | 0.476 | -0.056 | -0.018 | -0.039 |
| pineios_enhanced | B | 2.02 | 1.95 | 1.71 | -0.31 | -0.07 | -0.24 |
| pineios_enhanced | GSS | 0.201 | 0.218 | 0.262 | +0.060 | +0.017 | +0.044 |
| pineios_enhanced | TP / FP / FN cells | 63910 / 72693 / 3594 | 63422 / 67194 / 3585 | 60201 / 54666 / 6806 | | | |
| pineios_enhanced | eval km² / observed km² | 4642.3 / 1518.8 | 4506.7 / 1507.7 | 4506.7 / 1507.7 | | | |
| pineios_enhanced | modelled wet in eval km² | 3073.6 | 2938.9 | 2584.5 | | | |
| pineios_enhanced | fuzzy r=1 CSI | 0.426 | 0.436 | 0.461 | +0.034 | +0.009 | +0.025 |
| pineios_enhanced | excluded in eval / observed removed | — | 6029 cells (135.7 km²) / 497 cells (11.18 km²) | same mask | | | |
| pineios_enhanced | active cells / msk=2 / bnd points | 262465 / 650 / 0 | | 223703 / ring 728 / 12 | | | |
| pineios_enhanced | SFINCS wall-clock s | 1456.2 (published) | | 1575.937 | | | |

False alarms of the published v1.3 enhanced run (72693 cells, 1635.59 km², published mask, h > 0.10 m): on open sea 3430 (4.7%), on WC80 5498 (7.6%; land part 2069), on inland zb < 0 22 (0.0%); union of the three 5514 (7.6%). Observed cells inside WC80 ∪ open sea: 497 (TP there 488).

Quick-look PNGs: `reproduction/v14_rerun/quicklook/<run>_v14_hmax.png`. Timing: `reproduction/emsr933/timing.md`.
The 'v1.3 as published' column re-scores the published outputs with the unchanged validator; for all six runs the contingency tables are identical to the committed records (reproduction/val_json/{strymonas_v3,strymonas_base,mandra_enh,mandra_base,pineios_enh}.json, grid_matched_baseline/baseline_rescore.json).
Tests: 82 green (python -m unittest discover -s tests, 97 s, 2026-10-19T10:19:21Z-10:20:59Z).
