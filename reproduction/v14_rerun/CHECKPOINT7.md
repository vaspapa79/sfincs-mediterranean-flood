# Checkpoint 7 — CODE-15: D8 source-point resolution (harness v1.4.2), final re-runs, volumes, branch reconciliation — the number freeze

Generated 2026-10-20T16:30:45Z by `checkpoint7_tables.py`. Fix commit `b15896ac9607c4a2fc8d76be33919d78a12cde7b`. Tag `v1.4.2` = commit `the commit that adds this block (git rev-parse v1.4.2; hash recorded in timing.md)`. Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside; the v1.4.1 column is the v1.4.1 re-run where one exists, otherwise the v1.4.0 record (identical sampling for those runs).

## A. D8 source-point scope (no runs; `code15/d8_scope.{json,md}`, `scripts/d8_scope.py`; river membership from the GloFAS v4 static maps)

| event | point | YAML (sampling; injection) | ±0.1° rule cell → network cell, river [km²], peak | injection cell z_b / msk | lowest-z_b active channel cell within 1 km | flags |
|---|---|---|---|---|---|---|
| pineios | pineios_trikala | (21.77, 39.56); (21.86, 39.56) | (21.84, 39.51) → (21.875, 39.525), Pineios [2073.0], 371.39 | 97.77 / 1 | (21.8668, 39.5673) z_b 95.79, 998 m, D8 1.8 km² | (v) nested; (iii) injection cell off-channel (D8 upstream area 0.02 vs 1.8 km² within 1 km) |
| pineios | pineios_kalambaka | (21.63, 39.7); (21.86, 39.7) | (21.64, 39.61) → (21.675, 39.625), — [23.8], 2.1 | inactive (DEM 413.5) / None | (21.8649, 39.693) z_b 382.16, 884 m, D8 100.84 km² | (i) GloFAS cell is not on the Pineios; (v) nested; (v) nested; (iv) window clipped by the file edge (west); (iii) injection cell inactive (msk None, DEM 413.5 m) |
| pineios | titarisios | (22.42, 39.71); (22.42, 39.71) | (22.44, 39.81) → (22.475, 39.825), Pineios [8993.1], 1128.8 | 64.55 / 1 | (22.4234, 39.7132) z_b 61.69, 454 m, D8 4.88 km² | (i) GloFAS cell is not on the Titarisios; (vi) the injection point never drains through the Titarisios |
| pineios | enipeas | (22.39, 39.3); (22.39, 39.33) | (22.34, 39.31) → (22.375, 39.325), Enipeas [887.2], 118.4 | 136.25 / 1 | (22.3826, 39.3339) z_b 131.28, 772 m, D8 648.63 km² | (v) nested; (iii) injection cell off-channel (D8 upstream area 0.02 vs 648.81 km² within 1 km) |
| strymonas | kerkini_outlet | (23.3991, 41.0289); (23.3991, 41.0289) | (23.475, 40.975) → (23.475, 40.975), Strymonas [13018.4], 640.344 | 13.86 / 1 | (23.399, 41.0262) z_b 13.45, 301 m, D8 1.06 km² | (iii) injection cell off-channel (D8 upstream area 0.07 vs 1.53 km² within 1 km) |
| strymonas | angitis | (23.92, 41.0); (23.92, 41.0) | (23.825, 40.925) → (23.825, 40.925), Angitis [2379.1], 96.812 | 21.05 / 1 | (23.9116, 40.9982) z_b 19.04, 736 m, D8 1808.33 km² | (iii) injection cell off-channel (D8 upstream area 0.09 vs 1810.19 km² within 1 km) |
| strymonas | kerkini_outlet@v1_prefix_src | (23.2, 41.08); (23.2, 41.08) | (23.275, 41.125) → (23.275, 41.125), Strymonas [11922.4], 618.5 | 192.31 / 1 | (23.2031, 41.0882) z_b 157.13, 947 m, D8 90.49 km² | (v) nested; (iii) injection cell off-channel (D8 upstream area 12.85 vs 90.49 km² within 1 km) |
| valencia | magro | (-0.68, 39.2); (-0.68, 39.2) | (-0.625, 39.125) → (-0.625, 39.125), Jucar [17127.5], 42.688 | inactive (DEM 384.6) / None | (-0.69, 39.2041) z_b 274.67, 976 m, D8 5.69 km² | (i) GloFAS cell is not on the Magro; (v) nested; (iii) injection cell inactive (msk None, DEM 384.6 m) |
| valencia | jucar | (-0.34, 39.16); (-0.34, 39.16) | (-0.275, 39.175) → (-0.275, 39.175), Jucar [21422.1], 88.809 | 4.13 / 1 | (-0.3293, 39.1577) z_b 2.95, 961 m, D8 2183.63 km² | (iii) injection cell off-channel (D8 upstream area 0.01 vs 2183.63 km² within 1 km) |
| valencia | turia | (-0.55, 39.52); (-0.55, 39.52) | (-0.475, 39.525) → (-0.475, 39.525), Turia [6104.8], 239.719 | 164.0 / 1 | (-0.5513, 39.5283) z_b 109.69, 934 m, D8 6.07 km² | (iii) injection cell off-channel (D8 upstream area 0.01 vs 6.07 km² within 1 km) |
| emilia | lamone | (11.9, 44.24); (11.9, 44.24) | (11.975, 44.325) → (11.975, 44.325), Lamone [688.9], 188.219 | 66.81 / 1 | (11.8924, 44.2448) z_b 46.22, 807 m, D8 188.91 km² | (iii) injection cell off-channel (D8 upstream area 0.05 vs 188.91 km² within 1 km) |
| emilia | senio | (11.83, 44.27); (11.83, 44.27) | (11.925, 44.275) → (11.925, 44.275), Lamone [600.2], 166.062 | 129.22 / 1 | (11.8206, 44.275) z_b 88.19, 931 m, D8 2.9 km² | (ii) shares the GloFAS cell with montone; (i) GloFAS cell is not on the Senio; (v) nested; (iii) injection cell off-channel (D8 upstream area 0.02 vs 2.9 km² within 1 km); (vi) the injection point never drains through the Senio |
| emilia | montone | (11.98, 44.18); (11.98, 44.18) | (11.925, 44.275) → (11.925, 44.275), Lamone [600.2], 166.062 | 119.46 / 1 | (11.9779, 44.1886) z_b 60.09, 970 m, D8 0.27 km² | (ii) shares the GloFAS cell with senio; (i) GloFAS cell is not on the Montone; (v) nested; (iii) injection cell off-channel (D8 upstream area 0.05 vs 0.47 km² within 1 km) |
| emilia | ronco | (12.03, 44.13); (12.03, 44.13) | (12.075, 44.225) → (12.075, 44.225), Ronco [623.9], 171.188 | 213.85 / 1 | (12.0316, 44.1386) z_b 97.93, 961 m, D8 6.71 km² | (iii) injection cell off-channel (D8 upstream area 0.02 vs 6.71 km² within 1 km) |
| emilia | savio | (12.1, 44.06); (12.1, 44.06) | (12.175, 44.075) → (12.175, 44.075), Savio [557.8], 147.531 | 349.22 / 1 | (12.0875, 44.0601) z_b 114.71, 999 m, D8 45.29 km² | (iii) injection cell off-channel (D8 upstream area 0.02 vs 45.29 km² within 1 km); (vi) the injection point never drains through the Savio |

15 of 15 points carry at least one flag (full text in `code15/d8_scope.md`). Pineios lattice offset test: best shift `rows+0_cols+1` ({'river_points_on_small_cells': 0, 'dry_points_on_river_cells': 0}) against the containing cell {'river_points_on_small_cells': 12, 'dry_points_on_river_cells': 7}.

### Resolved v1.4.2 source points (`code15/source_points_v142.{json,md}`, resolved 2026-10-20T12:42:30Z; the single source of the v1.4.2 configs)

| event | point | sampling (lon, lat, ±window) | injection (lon, lat) | inject | network cell, river, km², peak | change |
|---|---|---|---|---|---|---|
| pineios | pineios_trikala | (21.77, 39.56, ±0.1°) | (21.86, 39.56) | True | (21.875, 39.525), Pineios, 2073.0, 371.39 | none (sampling + injection as frozen; the build-time snap applies) |
| pineios | pineios_kalambaka | (21.63, 39.7, ±0.1°) | (21.86, 39.7) | False | (21.575, 39.725), Pineios, 927.7, 40.78 | inject: false — the extended lattice gives the Pineios at Kalambaka (928 km2), nested upstream of the Trikala cell (2073 km2, same river): injecting both would … |
| pineios | titarisios | (22.24, 39.71, ±0.05°) | (22.42, 39.71) | True | (22.275, 39.725), Titarisios, 1685.0, 42.85 | sampling point moved to the Titarisios' last lattice cell (22.24, 39.71) with a one-cell window (CODE-15 B(1), author's prescription); injection point unchanged |
| pineios | enipeas | (22.39, 39.3, ±0.1°) | (22.39, 39.33) | True | (22.375, 39.325), Enipeas, 887.2, 118.4 | none |
| strymonas | kerkini_outlet | (23.3991, 41.0289, ±0.1°) | (23.3991, 41.0289) | True | (23.475, 40.975), Strymonas, 13018.4, 640.34 | none |
| strymonas | angitis | (23.92, 41.0, ±0.1°) | (23.92, 41.0) | True | (23.825, 40.925), Angitis, 2379.1, 211.47 | none |
| valencia | magro | (-0.475, 39.225, ±0.02°) | (-0.68, 39.2) | True | (-0.475, 39.225), Magro, 1647.9, 18.7 | sampling point moved to the Magro's own last cell before the Jucar (-0.475, 39.225; 1648 km2) with a one-cell window — the frozen window resolved to the Jucar b… |
| valencia | jucar | (-0.34, 39.16, ±0.1°) | (-0.34, 39.16) | True | (-0.275, 39.175), Jucar, 21422.1, 88.81 | none |
| valencia | turia | (-0.55, 39.52, ±0.1°) | (-0.55, 39.52) | True | (-0.475, 39.525), Turia, 6104.8, 239.72 | none |
| valencia | | | | | nested injected cells: magro ⊂ jucar | left as is (reported) |
| emilia | lamone | (11.9, 44.24, ±0.1°) | (11.9, 44.24) | True | (11.975, 44.325), Lamone, 688.9, 188.22 | none |
| emilia | senio | (11.875, 44.375, ±0.02°) | (11.84865, 44.31073) | True | (11.875, 44.375), Senio, 266.4, 62.44 | sampling point moved to the Senio's own last cell (11.875, 44.375; 266 km2) with a one-cell window — the frozen point (11.83, 44.27) lies in the Lamone valley a… |
| emilia | montone | (11.98, 44.18, ±0.05°) | (11.98, 44.18) | True | (12.025, 44.225), Montone, 467.4, 131.94 | one-cell window: resolves to the Montone at Forli (12.025, 44.225; 467 km2) instead of the Lamone at Faenza; injection unchanged |
| emilia | ronco | (12.03, 44.13, ±0.1°) | (12.03, 44.13) | True | (12.075, 44.225), Ronco, 623.9, 171.19 | none |
| emilia | savio | (12.1, 44.06, ±0.1°) | (12.19969, 44.09076) | True | (12.175, 44.075), Savio, 557.8, 147.53 | sampling unchanged (the Savio south of Cesena, 558 km2); injection moved to the Savio channel (lowest-z_b active channel cell inside the footprint of the Savio … |

## B. D8 fix — harness v1.4.2 (`skill/scripts/{prep_q_at_outlets,build_model,download_glofas,download_glofas_openmeteo,glofas_area,source_snap}.py`)

- (1) per-point windows / cells (`window_deg`, `inject`) from the ledger; (2) request area covering every sampling window (`glofas_area.request_area`, lattice anchored, explicit point count), Pineios lattice re-downloaded (every frozen cell identical, Kalambaka window unclipped); (3) build-time snap `source_snap.snap_source` (lowest-z_b active channel cell within 1 km, channel = D8 upstream area ≥ ½ the largest within the radius; no active cell = hard error; `model/sfincs_src_snap.json`); (4) `DuplicateCellError` under harness v1.4. v1.3 unchanged.
- Fix commit `b15896ac9607c4a2fc8d76be33919d78a12cde7b`; tests: full suite Ran 174 tests, OK (python -m unittest discover -s tests, log D:/ELKAK/implementation/v14/_logs/unittest_full_code15_final.log).

## C. v1.4.2 re-runs — four columns (v1.3 published / v1.4.1 / v1.4.2 / Δ = v1.4.2 − v1.4.1)

| run | event | CSI v1.3 publ. | CSI v1.4.1 (src) | CSI v1.4.2 | ΔCSI | HR v1.4.1 → v1.4.2 (Δ) | FAR (Δ) | B (Δ) | GSS v1.4.1 → v1.4.2 | TP/FP/FN v1.4.2 | wet km² v1.4.1 → v1.4.2 | SFINCS s v1.4.2 | injected peaks m³/s (v1.4.2) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pineios_enhanced_v142 | pineios | 0.456 | 0.496 (pineios_enhanced_v141) | **0.496** | -0.000 | 0.903 → 0.901 (-0.002) | 0.476 → 0.475 (-0.000) | 1.72 → 1.72 (-0.00) | 0.263 → 0.263 | 60367/54722/6640 | 2596 → 2590 | 2343.231 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_r2_220_v142 | pineios | 0.475 | 0.511 (pineios_r2_220_v141) | **0.507** | -0.004 | 0.843 → 0.835 (-0.008) | 0.435 → 0.437 (+0.002) | 1.49 → 1.48 (-0.01) | 0.299 → 0.294 | 55973/43428/11034 | 2251 → 2237 | 2219.386 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_r2_295_v142 | pineios | 0.466 | 0.504 (pineios_r2_295_v141) | **0.503** | -0.001 | 0.873 → 0.870 (-0.004) | 0.456 → 0.456 (+0.000) | 1.61 → 1.60 (-0.01) | 0.282 → 0.280 | 58283/48849/8724 | 2420 → 2410 | 1498.655 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_r2_510_v142 | pineios | 0.446 | 0.487 (pineios_r2_510_v141) | **0.487** | -0.000 | 0.922 → 0.921 (-0.001) | 0.492 → 0.492 (-0.000) | 1.81 → 1.81 (-0.00) | 0.245 → 0.245 | 61700/59709/5307 | 2736 → 2732 | 1773.444 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_cn_on_v142 | pineios | — | 0.508 (pineios_cn_on_v141) | **0.507** | -0.001 | 0.888 → 0.885 (-0.003) | 0.458 → 0.458 (-0.000) | 1.64 → 1.63 (-0.01) | 0.283 → 0.282 | 59309/50056/7698 | 2470 → 2461 | 1919.078 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_raw_imerg_v142 | pineios | — | 0.514 (pineios_raw_imerg_v141) | **0.507** | -0.007 | 0.795 → 0.782 (-0.012) | 0.407 → 0.410 (+0.003) | 1.34 → 1.33 (-0.01) | 0.316 → 0.308 | 52414/36444/14593 | 2021 → 1999 | 1442.39 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_qinf5_v142 | pineios | 0.456 | 0.483 (pineios_qinf5_v141) | **0.476** | -0.006 | 0.834 → 0.823 (-0.011) | 0.466 → 0.469 (+0.003) | 1.56 → 1.55 (-0.01) | 0.258 → 0.252 | 55131/48727/11876 | 2356 → 2337 | 1052.313 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| pineios_timevarying_q_v142 | pineios | 0.456 | 0.495 (pineios_timevarying_q) | **0.496** | +0.001 | 0.898 → 0.901 (+0.003) | 0.476 → 0.475 (-0.000) | 1.71 → 1.72 (+0.00) | 0.262 → 0.263 | 60367/54722/6640 | 2584 → 2590 | 1609.743 | pineios_trikala 371.4, pineios_kalambaka 40.8 (not injected), titarisios 42.9, enipeas 118.4 |
| emilia_enhanced_8aoi_v142 | emilia | 0.240 | 0.251 (emilia_enhanced_8aoi) | **0.253** | +0.002 | 0.850 → 0.852 (+0.002) | 0.737 → 0.735 (-0.002) | 3.23 → 3.22 (-0.01) | 0.096 → 0.098 | 21507/59690/3733 | 1834 → 1827 | 1750.337 | lamone 188.2, senio 62.4, montone 131.9, ronco 171.2, savio 147.5 |
| valencia_enhanced_164_v142 | valencia | 0.094 | 0.144 (valencia_enhanced_164) | **0.144** | +0.000 | 0.939 → 0.939 (+0.000) | 0.855 → 0.855 (-0.000) | 6.46 → 6.46 (-0.00) | 0.078 → 0.078 | 18381/108091/1200 | 1265 → 1265 | 1443.678 | magro 18.7, jucar 88.8, turia 239.7 |
| valencia_raw_imerg_v142 | valencia | 0.105 | 0.163 (valencia_raw_imerg) | **0.163** | +0.000 | 0.864 → 0.864 (+0.000) | 0.832 → 0.832 (-0.000) | 5.16 → 5.16 (-0.00) | 0.100 → 0.100 | 16923/84036/2658 | 1010 → 1010 | 2294.351 | magro 18.7, jucar 88.8, turia 239.7 |
| strymonas_enhanced_postD6_v142 | strymonas | 0.182 | 0.334 (strymonas_enhanced_postD6) | **0.334** | +0.000 | 0.921 → 0.921 (+0.000) | 0.657 → 0.656 (-0.000) | 2.68 → 2.68 (-0.00) | 0.272 → 0.272 | 4269/8153/364 | 280 → 279 | 371.69 | kerkini_outlet 640.3, angitis 96.8 |
| strymonas_abl_cnoff_q_v142 | strymonas | 0.239 | 0.295 (strymonas_abl_cnoff_q) | **0.295** | +0.000 | 0.936 → 0.936 (+0.000) | 0.699 → 0.699 (-0.000) | 3.11 → 3.11 (-0.00) | 0.229 → 0.229 | 4336/10077/297 | 324 → 324 | 247.551 | kerkini_outlet 640.3, angitis 96.8 |
| strymonas_leadin7d_v142 | strymonas | — | 0.255 (strymonas_leadin7d) | **0.255** | -0.000 | 0.959 → 0.959 (+0.000) | 0.742 → 0.742 (+0.000) | 3.72 → 3.72 (+0.00) | 0.185 → 0.185 | 4442/12777/191 | 387 → 387 | 1790.814 | kerkini_outlet 640.3, angitis 96.8 |
| strymonas_v1_prefix_src_v142 | strymonas | 0.170 | 0.325 (strymonas_v1_prefix_src) | **0.325** | -0.000 | 0.911 → 0.911 (+0.000) | 0.664 → 0.664 (+0.000) | 2.71 → 2.71 (+0.00) | 0.263 → 0.263 | 4220/8355/413 | 283 → 283 | 207.616 | kerkini_outlet 618.5, angitis 96.8 |

Determinism check: `pineios_timevarying_q_v142` has the same configuration as `pineios_enhanced_v142` (the audit rebuild hook is superseded by the pipeline's own series); identical TP/FP/FN/TN: **True**.

### Cross-event tables with the v1.4.2 canonical runs (`phase4/cross_event_v14_v142.{json,md}`)


Every number below is read from the JSON named in `cross_event_v14_v142.json` → `events.<run>.sources`. Scores at h > 0.10 m unless stated; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides. Crete = the Tzermiado per-AOI block (tier 1); no union score.

## Table 9 equivalent — strict and fuzzy (r = 1) skill, enhanced runs

| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.3 | HR v1.4 | FAR v1.3 | FAR v1.4 | B v1.3 | B v1.4 | GSS v1.4 | fuzzy r=1 CSI v1.3 | fuzzy r=1 CSI v1.4 | eval km² v1.4 | obs km² v1.4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.2: pineios_enhanced_v142] | 0.456 | **0.496** | 0.947 | 0.901 | 0.532 | 0.475 | 2.02 | 1.72 | 0.263 | 0.426 | 0.461 | 4506.7 | 1507.7 |
| Mandra (EMSR257) | 0.106 | **0.157** | 0.873 | 0.760 | 0.892 | 0.835 | 8.11 | 4.61 | 0.067 | 0.159 | 0.208 | 86.9 | 8.8 |
| Strymonas (EMSR122) [v1.4.2: strymonas_enhanced_postD6_v142] | 0.182 | **0.334** | 0.322 | 0.921 | 0.705 | 0.656 | 1.09 | 2.68 | 0.272 | 0.247 | 0.410 | 1196.2 | 104.2 |
| Valencia (EMSR773) [v1.4.2: valencia_enhanced_164_v142] | 0.094 | **0.144** | 0.989 | 0.939 | 0.906 | 0.855 | 10.52 | 6.46 | 0.078 | 0.086 | 0.111 | 2709.5 | 195.8 |
| Emilia-R. (EMSR664) [v1.4.2: emilia_enhanced_8aoi_v142] | 0.240 | **0.253** | 0.921 | 0.852 | 0.755 | 0.735 | 3.75 | 3.22 | 0.098 | 0.327 | 0.330 | 3148.0 | 567.9 |
| Crete Tzermiado (EMSR933, tier 1) | — | **0.221** | — | 0.988 | — | 0.778 | — | 4.45 | 0.169 | — | 0.195 | 176.9 | 11.3 |

## Table 10 equivalent — enhanced minus baseline (same harness, same mask)

| Event | baseline CSI v1.4 | enhanced CSI v1.4 | ΔCSI v1.4 | ΔHR v1.4 | ΔFAR v1.4 | ΔB v1.4 | ΔCSI v1.3 publ. | ΔHR v1.3 | ΔFAR v1.3 |
|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.2: pineios_enhanced_v142] | 0.543 | 0.496 | -0.047 | +0.061 | +0.081 | +0.33 | -0.061 | +0.124 | +0.114 |
| Mandra (EMSR257) | 0.138 | 0.157 | +0.018 | +0.511 | +0.072 | +3.56 | +0.026 | +0.473 | -0.017 |
| Strymonas (EMSR122) [v1.4.2: strymonas_enhanced_postD6_v142] | 0.207 | 0.334 | +0.127 | +0.512 | -0.049 | +1.29 | -0.022 | -0.054 | +0.012 |
| Crete Tzermiado (EMSR933, tier 1) | 0.343 | 0.221 | -0.122 | +0.201 | +0.156 | +2.37 | — | — | — |

## Table 13 equivalent — held-out events

| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.4 | FAR v1.4 | B v1.4 | GSS v1.4 | obs km² | eval km² | note |
|---|---|---|---|---|---|---|---|---|---|
| Valencia (EMSR773) [v1.4.2: valencia_enhanced_164_v142] | 0.094 | **0.144** | 0.939 | 0.855 | 6.46 | 0.078 | 195.8 | 2709.5 | AOI union |
| Emilia-R. (EMSR664) [v1.4.2: emilia_enhanced_8aoi_v142] | 0.240 | **0.253** | 0.852 | 0.735 | 3.22 | 0.098 | 567.9 | 3148.0 | AOI union |
| Crete Tzermiado (EMSR933, tier 1) | — | **0.221** | 0.988 | 0.778 | 4.45 | 0.169 | 11.3 | 176.9 | per-AOI Tzermiado (tier 1) |

## Table 14 equivalent — base-rate-robust skill (v1.4; v1.3 published in brackets)

| Event | CSI | SEDI | PSS | B | CSI* (threshold) | B* |
|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.2: pineios_enhanced_v142] | 0.496 (0.456) | 0.670 (0.636) | 0.490 (0.423) | 1.72 (2.02) | 0.534 (h>0.25m) [0.515] | 1.24 [1.18] |
| Mandra (EMSR257) | 0.157 (0.106) | 0.456 (0.362) | 0.325 (0.227) | 4.61 (8.11) | 0.159 (h>0.25m) [0.106] | 2.71 [8.11] |
| Strymonas (EMSR122) [v1.4.2: strymonas_enhanced_postD6_v142] | 0.334 (0.182) | 0.884 (0.426) | 0.753 (0.249) | 2.68 (1.09) | 0.436 (h>0.50m) [0.189] | 1.95 [1.16] |
| Valencia (EMSR773) [v1.4.2: valencia_enhanced_164_v142] | 0.144 (0.094) | 0.707 (0.658) | 0.509 (0.352) | 6.46 (10.52) | 0.242 (h>0.50m) [0.170] | 3.09 [5.51] |
| Emilia-R. (EMSR664) [v1.4.2: emilia_enhanced_8aoi_v142] | 0.253 (0.240) | 0.482 (0.460) | 0.332 (0.281) | 3.22 (3.75) | 0.305 (h>0.50m) [0.319] | 1.46 [2.03] |
| Crete Tzermiado (EMSR933, tier 1) | 0.221 (—) | 0.909 (—) | 0.753 (—) | 4.45 (—) | 0.365 (h>0.50m) [—] | 2.28 [—] |

## Threshold sweep (v1.4, enhanced): CSI at 0.05 / 0.10 / 0.25 / 0.50 m; fuzzy r = 0..3; one-sided r = 1

| Event | 0.05 | 0.10 | 0.25 | 0.50 | r=0 | r=1 | r=2 | r=3 | model-oriented r=1 | obs-oriented r=1 | truth buffer −20 / 0 / +20 m | time-matched (to latest acq) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) [v1.4.2: pineios_enhanced_v142] | 0.445 | 0.496 | 0.534 | 0.503 | 0.496 | 0.461 | 0.460 | 0.480 | 0.538 | 0.392 | 0.482 / 0.496 / 0.504 | 0.496 |
| Mandra (EMSR257) | 0.141 | 0.157 | 0.159 | 0.143 | 0.157 | 0.208 | 0.257 | 0.305 | 0.221 | 0.126 | 0.086 / 0.157 / 0.194 | 0.157 |
| Strymonas (EMSR122) [v1.4.2: strymonas_enhanced_postD6_v142] | 0.329 | 0.334 | 0.356 | 0.436 | 0.334 | 0.410 | 0.460 | 0.500 | 0.413 | 0.293 | 0.307 / 0.334 / 0.348 | 0.334 |
| Valencia (EMSR773) [v1.4.2: valencia_enhanced_164_v142] | 0.114 | 0.144 | 0.191 | 0.242 | 0.144 | 0.111 | 0.114 | 0.127 | 0.166 | 0.090 | 0.135 / 0.144 / 0.149 | 0.144 |
| Emilia-R. (EMSR664) [v1.4.2: emilia_enhanced_8aoi_v142] | 0.228 | 0.253 | 0.292 | 0.305 | 0.253 | 0.330 | 0.414 | 0.486 | 0.360 | 0.202 | 0.224 / 0.253 / 0.270 | 0.253 |
| Crete Tzermiado (EMSR933, tier 1) | 0.159 | 0.221 | 0.303 | 0.365 | 0.221 | 0.195 | 0.190 | 0.194 | 0.340 | 0.115 | union: 0.044 / 0.074 / 0.087 | union: 0.074 |

## D. Injected discharge vs rain / observed flood volumes (`code15/d_volumes_v142.{json,md}`)


Volumes over the simulated window (tstart..tstop); injected = trapezoid integral of the sfincs.dis columns SFINCS read; rain = netampr rates integrated per forcing cell and weighted by the active model area each forcing cell covers.

### pineios_enhanced_v142 — simulated window 2023-09-03 00:00 → 2023-09-11 00:00 UTC

| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |
|---|---|---|---|---|
| pineios_trikala | 371.39 | 129.29 | 89.67 | z_b 95.79 m, 998 m, 1.91 km² |
| titarisios | 42.85 | 24.39 | 16.89 | z_b 61.69 m, 454 m, 4.88 km² |
| enipeas | 118.40 | 62.05 | 43.01 | z_b 130.87 m, 863 m, 336.62 km² |
| pineios_kalambaka (sampled, not injected) | 40.78 | — | — | cell (21.54, 39.71) |
| **total injected** | combined peak 532.64 | | **149.57** | |

Rain on the active domain (5033 km²) in the window: **2237.1 × 10⁶ m³** (mean depth 444 mm, max cell 872 mm; `precip_2d.nc`, 384 steps of 0.50 h). Injected / rain = **6.7 %**. Modelled flood (hmax > 0.1 m): 2795 km², 3565.4 × 10⁶ m³ of water standing at hmax.

### emilia_enhanced_8aoi_v142 — simulated window 2023-05-14 00:00 → 2023-05-22 00:00 UTC

| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |
|---|---|---|---|---|
| lamone | 188.22 | 97.93 | 67.86 | z_b 46.22 m, 807 m, 188.98 km² |
| senio | 62.44 | 36.25 | 25.11 | z_b 29.4 m, 808 m, 284.56 km² |
| montone | 131.94 | 65.69 | 45.52 | z_b 62.98 m, 921 m, 0.5 km² |
| ronco | 171.19 | 85.20 | 59.05 | z_b 101.38 m, 832 m, 6.32 km² |
| savio | 147.53 | 72.68 | 50.37 | z_b 47.17 m, 750 m, 97.49 km² |
| **total injected** | combined peak 698.94 | | **247.91** | |

Rain on the active domain (5163 km²) in the window: **669.8 × 10⁶ m³** (mean depth 130 mm, max cell 160 mm; `precip_2d.nc`, 384 steps of 0.50 h). Injected / rain = **37.0 %**. Modelled flood (hmax > 0.1 m): 2782 km², 2032.5 × 10⁶ m³ of water standing at hmax.

Observed flood (EMS, inside the evaluation mask): 567.9 km². Proxies: modelled volume inside the observed extent 502.2 × 10⁶ m³ (mean modelled hmax there 0.88 m); nominal 0.5 m 283.9, 1.0 m 567.9 × 10⁶ m³. Total injected / proxy: 49 % (modelled), 87 % (0.5 m), 44 % (1.0 m).

## E. Branch reconciliation (F_branch_plan.md executed; no push)

**Branch reconciliation executed per `code14/F_branch_plan.md` (CODE-15 E, 2026-10-20; nothing pushed).**

1. **Archive of the local `main`** — in the main checkout (`D:/ELKAK/sfincs-mediterranean-floods`): `git switch -c archive/local-main-2026-06` from `main` (= `f6e7c01`, the orphan June-2026 history), then `git add -A` + commit **`f3be3a2`** "archive: local pre-GitHub working tree as of 2026-10-20": the nine modified tracked files and every untracked file of that checkout (CLAUDE.md, docs/ incl. `_sources/` and `bias_sensitivity/`, export/sfincs_bundle/, figures/, the four validation scripts) preserved verbatim; files matched by `.gitignore` (`*.tif` etc.) are not included. The checkout stays on the archive branch until step 3.
2. **Linked docs restored onto the publishable lineage** — in the worktree, `git checkout archive/local-main-2026-06 -- CLAUDE.md docs/CODEBASE_MAP.md docs/VALIDATION_FINDINGS.md docs/bias_sensitivity docs/cn_diagnostic.{csv,md} docs/fuzzy_onesided.{json,md} docs/grid_matched_baseline.md docs/independent_truth.md docs/truth_uncertainty.md docs/truth_uncertainty_buffer.csv figures/fig_rain_bias_spatial.{png,py}` (the files `docs/AUDIT.md` links to, plus the R2-sweep CSVs that `phase1.py` reads — its `BIAS_CSV` path is now repo-relative) committed with the CODE-15 records on `fix/harness-v1.4`, so `main := fix/harness-v1.4` carries them without a separate commit. Not restored (kept in the archive branch only, outside the publishable repo): `export/sfincs_bundle/` (the S1 depth-service bundle scripts; also in the 2026-10-01 tar) and `docs/_sources/` (manuscript sources); the archive's `docs/AUDIT.md` copy is an older strict subset of the branch file; the validation script copies are byte-identical to the branch.

## Figures (v1.4.2 products beside the earlier ones, `phase4/figures/`)

- `fig10_skill_v14_v142.png`
- `fig11_sweeps_v14_v142.png`
- `map_emilia_enhanced_8aoi_v142_v14.png`
- `map_pineios_cn_on_v142_v14.png`
- `map_pineios_enhanced_v142_v14.png`
- `map_pineios_qinf5_v142_v14.png`
- `map_pineios_r2_220_v142_v14.png`
- `map_pineios_r2_295_v142_v14.png`
- `map_pineios_r2_510_v142_v14.png`
- `map_pineios_raw_imerg_v142_v14.png`
- `map_pineios_timevarying_q_v142_v14.png`
- `map_strymonas_abl_cnoff_q_v142_v14.png`
- `map_strymonas_enhanced_postD6_v142_v14.png`
- `map_strymonas_leadin7d_v142_v14.png`
- `map_strymonas_v1_prefix_src_v142_v14.png`
- `map_valencia_enhanced_164_v142_v14.png`
- `map_valencia_raw_imerg_v142_v14.png`

## NUMBER_MAP.md

`reproduction/v14_rerun/NUMBER_MAP.md`: 79 entries; v1.4.2 column present, 37 entries differ from v1.4.1; 1 pending.

## Timing (phase-7 records)

| run | start UTC | end UTC | SFINCS s | published SFINCS s |
|---|---|---|---|---|
| emilia_enhanced_8aoi_v142 | 2026-10-20T12:46:27Z | 2026-10-20T13:24:33Z | 1750.337 | 754.7 |
| pineios_cn_on_v142 | 2026-10-20T12:48:43Z | 2026-10-20T14:10:30Z | 1919.078 | None |
| pineios_enhanced_v142 | 2026-10-20T12:46:27Z | 2026-10-20T13:58:49Z | 2343.231 | 1456.2 |
| pineios_qinf5_v142 | 2026-10-20T15:06:13Z | 2026-10-20T15:51:28Z | 1052.313 | 1012.6 |
| pineios_r2_220_v142 | 2026-10-20T13:58:49Z | 2026-10-20T14:56:56Z | 2219.386 | None |
| pineios_r2_295_v142 | 2026-10-20T14:56:56Z | 2026-10-20T15:46:04Z | 1498.655 | None |
| pineios_r2_510_v142 | 2026-10-20T15:46:04Z | 2026-10-20T16:26:01Z | 1773.444 | 1371.7 |
| pineios_raw_imerg_v142 | 2026-10-20T14:10:30Z | 2026-10-20T15:06:13Z | 1442.39 | None |
| pineios_timevarying_q_v142 | 2026-10-20T15:51:28Z | 2026-10-20T16:27:10Z | 1609.743 | 2116.0 |
| strymonas_abl_cnoff_q_v142 | 2026-10-20T14:53:31Z | 2026-10-20T14:58:59Z | 247.551 | 232.5 |
| strymonas_enhanced_postD6_v142 | 2026-10-20T14:39:31Z | 2026-10-20T14:53:31Z | 371.69 | 109.2 |
| strymonas_leadin7d_v142 | 2026-10-20T14:58:59Z | 2026-10-20T15:35:02Z | 1790.814 | None |
| strymonas_v1_prefix_src_v142 | 2026-10-20T15:35:02Z | 2026-10-20T15:45:13Z | 207.616 | 219.6 |
| valencia_enhanced_164_v142 | 2026-10-20T13:24:33Z | 2026-10-20T13:58:45Z | 1443.678 | 2230.7 |
| valencia_raw_imerg_v142 | 2026-10-20T13:58:45Z | 2026-10-20T14:39:31Z | 2294.351 | None |

Tests: full suite Ran 174 tests, OK (python -m unittest discover -s tests, log D:/ELKAK/implementation/v14/_logs/unittest_full_code15_final.log).
