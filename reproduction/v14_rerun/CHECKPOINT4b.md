# Checkpoint 4b — D6 adopted; Strymonas enhanced re-run under v1.4 + D6; Phase 2 (Valencia 164 mm, Emilia 8-AOI)

Generated 2026-10-19T13:00:31Z by `checkpoint4b_tables.py`. Commits: D6 `47354293d770c56b1ff8fc7b7fe92491da3bfeca` (2026-10-19T12:54:21Z); bias-box CLI fix `e33eacb6184213ef0f90def423659fefcd3261b2` (2026-10-19T12:05:51Z). Scores at h > 0.10 m, strict; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides.

## D6 tests
D6 tests (`tests/test_d6_cn_bookkeeping.py`, metrics `reproduction/v14_harness/D6_test_metrics.json`): (i) closed CN-76 plain, 30 mm rain + 20 m³/s for 12 h through the v1.4 pipeline path: end volume / expected = 1.00029 (1062676 of 1062364 m³; tolerance 0.1 %); v1.3 control 0.0000. (ii) 180 mm in three daily bursts (rain 180.0 mm = 2.24 S, 9588 cells × 96 hourly maps): max F = I − Ia = 53.86 mm ≤ S = 80.21 mm; smallest hourly increment of cumulative infiltration +0.0000 mm (monotone); max(cuminf − cumprcp) +0.0000 mm; max |cuminf − SCS curve| 0.0017 mm. (iii) without curve numbers the flag leaves zs and zsmax bit-identical — synthetic: True / True; Mandra enhanced v1.4 event (`D6_invariance_mandra.json`, 2026-10-19T12:31:24Z, reference infiltration type 'none'): zs bit-identical True (max diff 0.0 m), zsmax True; the flag only adds cuminf, cumprcp to the map file.

Tests: 101 green (python -m unittest discover -s tests, 158 s, 2026-10-19T12:51:26Z-12:54:05Z).

D6 provenance (`reproduction/v14_harness/D6_CN_SINK.md` §1, §6): verbatim v2.3.0 source lines; upstream, SFINCS lists the issue in its known issues since 2026-04-02 (`e394b7f02e`) with the same workaround, the v2.4.0 Galibier release (2026-06-15) still carries it although its notes say fixed, and `main` forces the flag for 'cna'/'cnb' since `360c1592ee` (2026-07-15); no release contains the fix yet. `reproducer_D6.md` drafted for a private note to Deltares (not sent, no public issue).

## Strymonas v3 enhanced (curve numbers on): pre-D6 kept, v1.4 + D6 added

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4 pre-D6, invalid | v1.4, new mask | Δ (v1.4 − v1.3 published) | of which mask | of which harness |
|---|---|---|---|---|---|---|---|
| CSI | 0.182 | 0.180 | 0.333 | **0.334** | +0.151 | -0.002 | +0.154 |
| HR | 0.322 | 0.319 | 0.906 | **0.921** | +0.599 | -0.003 | +0.602 |
| FAR | 0.705 | 0.708 | 0.655 | **0.657** | -0.048 | +0.003 | -0.051 |
| B | 1.09 | 1.09 | 2.63 | **2.68** | +1.59 | +0.00 | +1.59 |
| GSS | 0.136 | 0.134 | 0.272 | **0.272** | +0.136 | -0.002 | +0.139 |
| TP / FP / FN cells | 1526 / 3639 / 3211 | 1480 / 3587 / 3153 | 4198 / 7980 / 435 | 4269 / 8162 / 364 | | | |
| fuzzy r=1 CSI | 0.247 | 0.242 | 0.404 | 0.410 | +0.163 | -0.005 | +0.167 |
| modelled wet in eval km² | 116.2 | 114.0 | 274.0 | 279.7 | | | |
| eval km² / observed km² | 1222.7 / 106.6 | 1196.2 / 104.2 | | 1196.2 / 104.2 | | | |
| excluded in eval / observed removed | — | 1175 cells (26.4 km²) / 104 cells (2.34 km²) | | same mask | | | |

Sink check (`strymonas_postD6_balance.json`, 2026-10-19T12:59:48Z): cells whose cumulative infiltration exceeds the SCS abstraction or the cumulative rain by > 0.1 mm: 0 (0.00%); max excess 0.0000 mm. Cells past Ia: 10844 (5.8%) — they now produce runoff instead of swallowing water.
Water balance 2015-03-28 → 2015-04-04 (sub-grid volumes, Mm³): rain 25.45, infiltration 24.85, rain runoff 0.59; discharge in 311.94 (Kerkini / Angitis [261.84, 50.11]); storage at the end 271.15 (max 271.15 at 2015-04-04 00:00), of which in the floodplain window 268.28; net outflow through the coastal boundary 41.38. Daily storage: {'2015-03-28': 0.0, '2015-03-29': 56.9, '2015-03-30': 117.3, '2015-03-31': 171.3, '2015-04-01': 211.9, '2015-04-02': 241.1, '2015-04-03': 260.4, '2015-04-04': 271.2}.

**Physical reading.** With the sink gone, the modelled Strymonas flood is discharge-driven, not rain-driven. In the simulated week the two GloFAS inflows deliver 311.9 Mm³ (Kerkini outlet 261.8, Angitis 50.1). The domain receives only 25.4 Mm³ of rain (6.1 mm on average; most of the event rain falls in the 7-day forcing lead-in, which is not simulated), and the curve number absorbs 24.9 Mm³ of it, leaving 0.6 Mm³ of rain runoff, 0.2 % of what reaches the surface. Of those 312.5 Mm³, 271.1 Mm³ (87 %) are still on the land at the end, 268.3 Mm³ of them in the Serres floodplain window, and storage still grows by 10.8 Mm³ on the last day; the remaining 41.4 Mm³ (13 %) leave through the Amfipoli gorge to the Strymonian Gulf. The plain fills like a reservoir faster than the gorge drains it, which is why the run reaches a high hit rate together with a frequency bias well above 1. In the published run the same discharge disappeared in the 41 % of the domain that the curve-number sink had made absorbing (D6_CN_SINK.md).

## Valencia EMSR773, R2 anchored to 164 mm

Exclusion (`masks/valencia_exclusion.tif`): open sea 225179 cells (2251.79 km²; vs the published grid's sea 0 cells differ), WorldCover 80 219298 (2192.98 km², land part 4875), union 230054 cells.
Published record check: re-scoring the published output reproduces `R1_verification/task_valencia_anchor/_scoring/score_v164.json` exactly: True (TP/FP/FN/TN 19808/190968/221/109040).

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − v1.3 published) | of which mask | of which harness |
|---|---|---|---|---|---|---|
| CSI | 0.094 | 0.119 | **0.144** | +0.050 | +0.025 | +0.025 |
| HR | 0.989 | 0.989 | **0.939** | -0.050 | -0.000 | -0.050 |
| FAR | 0.906 | 0.881 | **0.855** | -0.051 | -0.026 | -0.026 |
| B | 10.52 | 8.27 | **6.46** | -4.06 | -2.25 | -1.81 |
| GSS | 0.033 | 0.051 | **0.078** | +0.044 | +0.017 | +0.027 |
| TP / FP / FN cells | 19808 / 190968 / 221 | 19360 / 142656 / 221 | 18381 / 108134 / 1200 | | | |
| fuzzy r=1 CSI | 0.086 | 0.100 | 0.111 | +0.025 | +0.014 | +0.011 |
| modelled wet in eval km² | 2107.8 | 1620.2 | 1265.2 | | | |
| eval km² / observed km² | 3200.4 / 200.3 | 2709.5 / 195.8 | 2709.5 / 195.8 | | | |
| excluded in eval / observed removed | — | 49085 cells (490.9 km²) / 448 cells (4.48 km²) | same mask | | | |
| active cells v1.4 / ring / SFINCS s | | | 298115 / 1867 / 1396.242 (published 2230.7) | | | |

False alarms of the published run (190968 cells, 1909.68 km²): open sea 23.2%, WorldCover 80 25.3% (land part 2.1%), inland zb < 0 0.4%; union 25.7%.

## Emilia-Romagna EMSR664, 8-AOI truth

Exclusion (`masks/emilia_exclusion.tif`): open sea 74774 cells (1682.415 km²; vs the published grid's sea 0 cells differ), WorldCover 80 73218 (1647.405 km², land part 8484), union 83258 cells.
Published record check: re-scoring the published output reproduces `R1_verification/task_emilia_aoi/_scoring/emilia_rescore.json (full_8aoi)` exactly: True (TP/FP/FN/TN 24247/74529/2091/42082).

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − v1.3 published) | of which mask | of which harness |
|---|---|---|---|---|---|---|
| CSI | 0.240 | 0.237 | **0.251** | +0.011 | -0.004 | +0.015 |
| HR | 0.921 | 0.918 | **0.850** | -0.071 | -0.003 | -0.068 |
| FAR | 0.755 | 0.758 | **0.737** | -0.018 | +0.004 | -0.021 |
| B | 3.75 | 3.79 | **3.23** | -0.52 | +0.04 | -0.56 |
| GSS | 0.073 | 0.073 | **0.096** | +0.022 | -0.000 | +0.023 |
| TP / FP / FN cells | 24247 / 74529 / 2091 | 23162 / 72623 / 2078 | 21455 / 60073 / 3785 | | | |
| fuzzy r=1 CSI | 0.327 | 0.320 | 0.330 | +0.002 | -0.007 | +0.009 |
| modelled wet in eval km² | 2222.5 | 2155.2 | 1834.4 | | | |
| eval km² / observed km² | 3216.4 / 592.6 | 3148.0 / 567.9 | 3148.0 / 567.9 | | | |
| excluded in eval / observed removed | — | 3040 cells (68.4 km²) / 1098 cells (24.70 km²) | same mask | | | |
| active cells v1.4 / ring / SFINCS s | | | 229434 / 3243 / 1180.21 (published 754.7) | | | |

False alarms of the published run (74529 cells, 1676.9 km²): open sea 1.0%, WorldCover 80 2.4% (land part 1.5%), inland zb < 0 8.7%; union 10.4%.

Quick-looks: `reproduction/v14_rerun/quicklook/{strymonas_enhanced_postD6,valencia_enhanced_164,emilia_enhanced_8aoi}_v14_hmax.png`.
