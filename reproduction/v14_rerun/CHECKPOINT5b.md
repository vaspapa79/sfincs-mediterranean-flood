# Checkpoint 5b — harness v1.4 consolidated: cross-event tables, sensitivities, NUMBER_MAP, figures, Crete, timing

Generated 2026-10-20T05:11:48Z by `checkpoint5b_tables.py`. Tag `v1.4.0` = commit `the commit that adds this block (git rev-parse v1.4.0; hash recorded in timing.md)`. Scores at h > 0.10 m, strict, new mask (AOI ∩ active minus WorldCover 80 ∪ open sea, both sides); v1.3 as published beside. Crete = Tzermiado tier-1 block.

## 1. Cross-event tables (Tables 9 / 10 / 13 / 14 equivalents; `phase4/cross_event_v14.{json,md}`)


Every number below is read from the JSON named in `cross_event_v14.json` → `events.<run>.sources`. Scores at h > 0.10 m unless stated; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides. Crete = the Tzermiado per-AOI block (tier 1); no union score.

## Table 9 equivalent — strict and fuzzy (r = 1) skill, enhanced runs

| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.3 | HR v1.4 | FAR v1.3 | FAR v1.4 | B v1.3 | B v1.4 | GSS v1.4 | fuzzy r=1 CSI v1.3 | fuzzy r=1 CSI v1.4 | eval km² v1.4 | obs km² v1.4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) | 0.456 | **0.495** | 0.947 | 0.898 | 0.532 | 0.476 | 2.02 | 1.71 | 0.262 | 0.426 | 0.461 | 4506.7 | 1507.7 |
| Mandra (EMSR257) | 0.106 | **0.157** | 0.873 | 0.760 | 0.892 | 0.835 | 8.11 | 4.61 | 0.067 | 0.159 | 0.208 | 86.9 | 8.8 |
| Strymonas (EMSR122) | 0.182 | **0.334** | 0.322 | 0.921 | 0.705 | 0.657 | 1.09 | 2.68 | 0.272 | 0.247 | 0.410 | 1196.2 | 104.2 |
| Valencia (EMSR773) | 0.094 | **0.144** | 0.989 | 0.939 | 0.906 | 0.855 | 10.52 | 6.46 | 0.078 | 0.086 | 0.111 | 2709.5 | 195.8 |
| Emilia-R. (EMSR664) | 0.240 | **0.251** | 0.921 | 0.850 | 0.755 | 0.737 | 3.75 | 3.23 | 0.096 | 0.327 | 0.330 | 3148.0 | 567.9 |
| Crete Tzermiado (EMSR933, tier 1) | — | **0.221** | — | 0.988 | — | 0.778 | — | 4.45 | 0.169 | — | 0.195 | 176.9 | 11.3 |

## Table 10 equivalent — enhanced minus baseline (same harness, same mask)

| Event | baseline CSI v1.4 | enhanced CSI v1.4 | ΔCSI v1.4 | ΔHR v1.4 | ΔFAR v1.4 | ΔB v1.4 | ΔCSI v1.3 publ. | ΔHR v1.3 | ΔFAR v1.3 |
|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) | 0.543 | 0.495 | -0.048 | +0.058 | +0.081 | +0.33 | -0.061 | +0.124 | +0.114 |
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
| Pineios (EMSR692) | 0.495 (0.456) | 0.667 (0.636) | 0.488 (0.423) | 1.71 (2.02) | 0.531 (h>0.25m) [0.515] | 1.23 [1.18] |
| Mandra (EMSR257) | 0.157 (0.106) | 0.456 (0.362) | 0.325 (0.227) | 4.61 (8.11) | 0.159 (h>0.25m) [0.106] | 2.71 [8.11] |
| Strymonas (EMSR122) | 0.334 (0.182) | 0.884 (0.426) | 0.753 (0.249) | 2.68 (1.09) | 0.435 (h>0.50m) [0.189] | 1.95 [1.16] |
| Valencia (EMSR773) | 0.144 (0.094) | 0.706 (0.658) | 0.509 (0.352) | 6.46 (10.52) | 0.242 (h>0.50m) [0.170] | 3.09 [5.51] |
| Emilia-R. (EMSR664) | 0.251 (0.240) | 0.475 (0.460) | 0.326 (0.281) | 3.23 (3.75) | 0.303 (h>0.50m) [0.319] | 1.49 [2.03] |
| Crete Tzermiado (EMSR933, tier 1) | 0.221 (—) | 0.909 (—) | 0.753 (—) | 4.45 (—) | 0.365 (h>0.50m) [—] | 2.28 [—] |

## Threshold sweep (v1.4, enhanced): CSI at 0.05 / 0.10 / 0.25 / 0.50 m; fuzzy r = 0..3; one-sided r = 1

| Event | 0.05 | 0.10 | 0.25 | 0.50 | r=0 | r=1 | r=2 | r=3 | model-oriented r=1 | obs-oriented r=1 | truth buffer −20 / 0 / +20 m | time-matched (to latest acq) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) | 0.445 | 0.495 | 0.531 | 0.495 | 0.495 | 0.461 | 0.460 | 0.480 | 0.536 | 0.392 | 0.482 / 0.495 / 0.503 | 0.495 |
| Mandra (EMSR257) | 0.141 | 0.157 | 0.159 | 0.143 | 0.157 | 0.208 | 0.257 | 0.305 | 0.221 | 0.126 | 0.086 / 0.157 / 0.194 | 0.157 |
| Strymonas (EMSR122) | 0.329 | 0.334 | 0.356 | 0.435 | 0.334 | 0.410 | 0.460 | 0.499 | 0.413 | 0.293 | 0.307 / 0.334 / 0.348 | 0.334 |
| Valencia (EMSR773) | 0.114 | 0.144 | 0.191 | 0.242 | 0.144 | 0.111 | 0.114 | 0.127 | 0.166 | 0.090 | 0.135 / 0.144 / 0.149 | 0.144 |
| Emilia-R. (EMSR664) | 0.227 | 0.251 | 0.285 | 0.303 | 0.251 | 0.330 | 0.413 | 0.486 | 0.358 | 0.202 | 0.222 / 0.251 / 0.268 | 0.251 |
| Crete Tzermiado (EMSR933, tier 1) | 0.159 | 0.221 | 0.303 | 0.365 | 0.221 | 0.195 | 0.190 | 0.194 | 0.340 | 0.115 | union: 0.044 / 0.074 / 0.087 | union: 0.074 |

## 2. Sensitivity tables (v1.4; labelled, never canonical)

### R2 anchor sweeps (Mandra 95/140/200/255 mm; Pineios 220/295/400/510 mm)

| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mandra_r2_95 | R2 sweep Mandra target 95 mm | 0.162 | 0.628 | 0.821 | 3.50 | 0.078 | 30.9 | 0.104 | — | 4.062 | 2837.585 |
| mandra_r2_140 | R2 sweep Mandra target 140 mm | 0.159 | 0.690 | 0.829 | 4.04 | 0.071 | 35.7 | 0.106 | — | 5.986 | 3157.719 |
| mandra_enhanced |  | 0.157 | 0.760 | 0.835 | 4.61 | 0.067 | 40.7 | — | — | 8.551 | 398.702 |
| mandra_r2_255 | R2 sweep Mandra target 255 mm | 0.157 | 0.812 | 0.838 | 5.00 | 0.065 | 44.1 | 0.104 | — | 10.903 | 1691.389 |
| pineios_r2_220 | R2 sweep Pineios target 220 mm | 0.505 | 0.831 | 0.438 | 1.48 | 0.292 | 2229.4 | 0.475 | — | 1.499 | 2043.759 |
| pineios_r2_295 | R2 sweep Pineios target 295 mm | 0.501 | 0.867 | 0.457 | 1.59 | 0.279 | 2404.5 | 0.466 | — | 2.009 | 3641.185 |
| pineios_enhanced |  | 0.495 | 0.898 | 0.476 | 1.71 | 0.262 | 2584.5 | — | — | 2.725 | 1575.937 |
| pineios_r2_510 | R2 sweep Pineios target 510 mm | 0.486 | 0.920 | 0.492 | 1.81 | 0.244 | 2728.9 | 0.446 | — | 3.474 | 4198.593 |

### Pineios audit rows

| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pineios_enhanced |  | 0.495 | 0.898 | 0.476 | 1.71 | 0.262 | 2584.5 | — | — | 2.725 | 1575.937 |
| pineios_timevarying_q | S2 Pineios v3 / §4.1.1: time-varying GloFAS Q audit (dis + src rebuilt | 0.495 | 0.898 | 0.476 | 1.71 | 0.262 | 2584.1 | 0.456 | — | 2.725 | 3446.777 |
| pineios_qinf5 | §5.2: constant infiltration qinf = 5 mm/h on the time-varying-Q build  | 0.472 | 0.814 | 0.471 | 1.54 | 0.247 | 2322.6 | 0.456 | — | 2.725 | 2591.246 |
| pineios_cn_on | §4.1.2 (ii) / §6.2: Pineios CN-on (HSG-B, AMC-II) | 0.505 | 0.882 | 0.458 | 1.63 | 0.281 | 2455.0 | text: modelled_wet_km2 38, observed_km2 1519 | 73.2 | 2.725 | 2191.432 |
| pineios_raw_imerg | §5: Pineios raw IMERG (no R2) | 0.502 | 0.775 | 0.412 | 1.32 | 0.303 | 1987.2 | text: watershed_mean_mm 141, modelled_wet_km2_upper 40 | — | — | 3215.574 |

### Mandra curve-number rows (S1) + Manning test

| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mandra_enhanced |  | 0.157 | 0.760 | 0.835 | 4.61 | 0.067 | 40.7 | — | — | 8.551 | 398.702 |
| mandra_cn_a15 | S1 row 1: HSG-A AMC-II (CN = 15 test) — pervious classes CN 15 | 0.109 | 0.257 | 0.840 | 1.61 | 0.043 | 14.2 | text: mean_cn 42, total_wet_km2 0.77, tp_01mandra 0, csi 0.031, hr | 33.7 | 8.551 | 300.373 |
| mandra_cn_a58 | S1 row 2: HSG-A AMC-II (CN = 58 test) — pervious classes CN 58 | 0.158 | 0.645 | 0.827 | 3.73 | 0.072 | 32.9 | text: mean_cn 65, total_wet_km2 0.77, tp_01mandra 0, csi 0.031, hr | 66.0 | 8.551 | 3071.646 |
| mandra_cn_b_default | S1 row 3: HSG-B AMC-II (default lookup) | 0.158 | 0.699 | 0.831 | 4.13 | 0.070 | 36.4 | text: mean_cn 80, total_wet_km2 0.77, tp_01mandra 0, csi 0.031, hr | 75.0 | 8.551 | 2182.423 |
| mandra_cn_d_amc3 | S1 row 4: HSG-D AMC-III (post-fire, saturated) — TR-55 HSG-D lookup, A | 0.156 | 0.753 | 0.835 | 4.57 | 0.067 | 40.3 | text: mean_cn 97, total_wet_km2 111, tp_01mandra 0, csi 0.01, hr 0 | 93.0 | 8.551 | 2568.228 |
| mandra_cn_d_amc3_manning080 | S1 prose: Manning test, built-up n 0.012 -> 0.080 at the HSG-D AMC-III | 0.153 | 0.812 | 0.841 | 5.11 | 0.061 | 45.1 | text: total_wet_km2_n080 115.8, total_wet_km2_n012 110.8 | 93.0 | 8.551 | 498.728 |

### Strymonas: ablations, v1 source, lead-in

| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| strymonas_baseline |  | 0.207 | 0.410 | 0.706 | 1.39 | 0.155 | 145.1 | — | — | — | 145.146 |
| strymonas_enhanced_postD6 |  | 0.334 | 0.921 | 0.657 | 2.68 | 0.272 | 279.7 | — | — | — | 190.166 |
| strymonas_abl_cnoff_q | Table 12 row 3: CN off + Q | 0.295 | 0.936 | 0.699 | 3.11 | 0.229 | 324.3 | 0.239 | — | — | 915.726 |
| strymonas_abl_qoff_cn | Table 12 row 4: CN on + Q off | 0.011 | 0.011 | 0.495 | 0.02 | 0.009 | 2.4 | 0.016 | 74.9 | — | 220.273 |
| strymonas_v1_prefix_src | Table 8 'Enhanced v1' / S2 Strymonas v1: pre-fix kerkini_outlet {23.2, | 0.325 | 0.911 | 0.664 | 2.71 | 0.263 | 282.9 | 0.170 | 74.9 | — | 238.315 |
| strymonas_leadin7d | sensitivity: 7-day lead-in simulated (tstart = tref = 2015-03-21), CN  | 0.255 | 0.959 | 0.742 | 3.72 | 0.185 | 387.3 | — | 74.9 | — | 4491.846 |

### Valencia raw IMERG

| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| valencia_enhanced_164 |  | 0.144 | 0.939 | 0.855 | 6.46 | 0.078 | 1265.2 | — | — | 1.941 | 1396.242 |
| valencia_raw_imerg | §4.4.2 / §5.3 / S3.1: Valencia raw IMERG (no R2) | 0.163 | 0.864 | 0.832 | 5.16 | 0.100 | 1010.0 | 0.105 | — | — | 1531.571 |

### Crete sensitivities (tier-1 Tzermiado block)

| run | label | CSI | HR | FAR | B | GSS | modelled wet km² | published (v1.3) CSI | mean CN (active) | R2 factor | SFINCS s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| crete_baseline | Stage 2 baseline: ERA5(T) rain-on-grid, no wind/IB, R2 off | 0.343 | 0.788 | 0.622 | 2.08 | 0.303 | 23.46 (obs 11.26) | — | — | — | 8370.847 |
| crete_canonical_r2on | Stage 3 canonical: IMERG Late, R2 on (anchor 447.8 mm Tzermiado, facto | 0.221 | 0.988 | 0.778 | 4.45 | 0.169 | 50.14 (obs 11.26) | — | — | 1.014 | 10946.466 |
| crete_sens_r2off | sensitivity (a): R2 off — raw IMERG Late | 0.222 | 0.988 | 0.777 | 4.44 | 0.169 | 49.97 (obs 11.26) | — | — | — | 11927.463 |
| crete_sens_anchor_224 | sensitivity (b): anchor sweep target 224 mm | 0.265 | 0.972 | 0.733 | 3.64 | 0.215 | 40.99 (obs 11.26) | — | — | 0.507 | 9972.139 |
| crete_sens_anchor_336 | sensitivity (b): anchor sweep target 336 mm | 0.241 | 0.985 | 0.758 | 4.08 | 0.189 | 45.89 (obs 11.26) | — | — | 0.761 | 11377.458 |
| crete_sens_anchor_582 | sensitivity (b): anchor sweep target 582 mm | 0.206 | 0.990 | 0.793 | 4.79 | 0.152 | 53.97 (obs 11.26) | — | — | 1.318 | 13014.583 |
| crete_sens_karst_q1914 | sensitivity (c): karst bracket, constant infiltration qinf = 1.914 mm/ | 0.228 | 0.988 | 0.771 | 4.31 | 0.176 | 48.54 (obs 11.26) | — | — | 1.014 | 6236.934 |

## 3. NUMBER_MAP.md

`reproduction/v14_rerun/NUMBER_MAP.md`: 75 entries (table rows, figure captions, sentences), 0 still pending. Every entry: location → R5 value → v1.4 value → source JSON → text lines.

## 4. Figures regenerated (PNG + CSV data behind each, `phase4/figures/`)

- `fig10_skill_v14.png` (+ `fig10_skill_v14.csv`)
- `fig11_sweeps_v14.png` (+ `fig11_sweeps_v14.csv`)
- `map_crete_baseline_island_v14.png` (+ `map_crete_baseline_island_v14.csv`)
- `map_crete_baseline_v14.png` (+ `map_crete_baseline_v14.csv`)
- `map_crete_canonical_r2on_island_v14.png` (+ `map_crete_canonical_r2on_island_v14.csv`)
- `map_crete_canonical_r2on_v14.png` (+ `map_crete_canonical_r2on_v14.csv`)
- `map_crete_sens_anchor_224_island_v14.png` (+ `map_crete_sens_anchor_224_island_v14.csv`)
- `map_crete_sens_anchor_224_v14.png` (+ `map_crete_sens_anchor_224_v14.csv`)
- `map_crete_sens_anchor_336_island_v14.png` (+ `map_crete_sens_anchor_336_island_v14.csv`)
- `map_crete_sens_anchor_336_v14.png` (+ `map_crete_sens_anchor_336_v14.csv`)
- `map_crete_sens_anchor_582_island_v14.png` (+ `map_crete_sens_anchor_582_island_v14.csv`)
- `map_crete_sens_anchor_582_v14.png` (+ `map_crete_sens_anchor_582_v14.csv`)
- `map_crete_sens_karst_q1914_island_v14.png` (+ `map_crete_sens_karst_q1914_island_v14.csv`)
- `map_crete_sens_karst_q1914_v14.png` (+ `map_crete_sens_karst_q1914_v14.csv`)
- `map_crete_sens_r2off_island_v14.png` (+ `map_crete_sens_r2off_island_v14.csv`)
- `map_crete_sens_r2off_v14.png` (+ `map_crete_sens_r2off_v14.csv`)
- `map_emilia_enhanced_8aoi_v14.png` (+ `map_emilia_enhanced_8aoi_v14.csv`)
- `map_mandra_baseline_v14.png` (+ `map_mandra_baseline_v14.csv`)
- `map_mandra_enhanced_v14.png` (+ `map_mandra_enhanced_v14.csv`)
- `map_pineios_baseline_gridmatched_v14.png` (+ `map_pineios_baseline_gridmatched_v14.csv`)
- `map_pineios_enhanced_v14.png` (+ `map_pineios_enhanced_v14.csv`)
- `map_pineios_qinf5_v14.png` (+ `map_pineios_qinf5_v14.csv`)
- `map_pineios_raw_imerg_v14.png` (+ `map_pineios_raw_imerg_v14.csv`)
- `map_pineios_timevarying_q_v14.png` (+ `map_pineios_timevarying_q_v14.csv`)
- `map_strymonas_baseline_v14.png` (+ `map_strymonas_baseline_v14.csv`)
- `map_strymonas_enhanced_postD6_v14.png` (+ `map_strymonas_enhanced_postD6_v14.csv`)
- `map_strymonas_leadin7d_v14.png` (+ `map_strymonas_leadin7d_v14.csv`)
- `map_valencia_enhanced_164_v14.png` (+ `map_valencia_enhanced_164_v14.csv`)
- `map_valencia_raw_imerg_v14.png` (+ `map_valencia_raw_imerg_v14.csv`)
- `rain_crete_canonical_r2on_v14.png` (data: the rain series CSV / cross_event JSON)
- `rain_emilia_enhanced_8aoi_v14.png` (data: the rain series CSV / cross_event JSON)
- `rain_mandra_enhanced_v14.png` (data: the rain series CSV / cross_event JSON)
- `rain_pineios_enhanced_v14.png` (data: the rain series CSV / cross_event JSON)
- `rain_strymonas_enhanced_postD6_v14.png` (data: the rain series CSV / cross_event JSON)
- `rain_valencia_enhanced_164_v14.png` (data: the rain series CSV / cross_event JSON)

## 5. Crete EMSR933 (rule_ledger.md §8; truth frozen at the post-closure snapshot)

Truth: snapshot 2026-10-19T13:34:37Z (activation closed True), 7 released packages, AOIs without product ['02', '05', '08']; tier 1 = AOI03 Tzermiado (DEL S1 4 Oct 16:22 UTC ∪ DEL_MONIT02 GeoEye 8 Oct 09:02; the GRA released after the cut-off is dropped by the delineation-first rule); tier 2 = 01/04/06/07 km² only; tier 3 = 02/05/08 excluded; no union score.
- **crete_baseline** (SFINCS 8370.847 s, end 2026-10-19T16:44:39Z): Tzermiado h>0.05m: CSI 0.294 HR 0.881 FAR 0.694 B 2.88; h>0.10m: CSI 0.343 HR 0.788 FAR 0.622 B 2.08; h>0.25m: CSI 0.302 HR 0.459 FAR 0.532 B 0.98; h>0.50m: CSI 0.270 HR 0.346 FAR 0.449 B 0.63; CSI* 0.343 at h>0.10m (B* 2.08); SEDI 0.847 PSS 0.700; fuzzy r=1 0.297; observed 11.26 km², modelled 23.46 km² of 176.9 km²; peak hmax 14.7 m.
  tier 2 (observed vs modelled km² at h > 0.10 m): AOI01 Kastelli 1.780 vs 26.070; AOI04 Agios Ioannis 0.410 vs 1.090; AOI06 Agios Nikolaos 0.230 vs 9.050; AOI07 Omalos 0.650 vs 16.640
- **crete_canonical_r2on** (SFINCS 10946.466 s, end 2026-10-19T20:21:12Z): Tzermiado h>0.05m: CSI 0.159 HR 0.992 FAR 0.840 B 6.22; h>0.10m: CSI 0.221 HR 0.988 FAR 0.778 B 4.45; h>0.25m: CSI 0.303 HR 0.961 FAR 0.693 B 3.13; h>0.50m: CSI 0.365 HR 0.877 FAR 0.615 B 2.28; CSI* 0.365 at h>0.50m (B* 2.28); SEDI 0.909 PSS 0.753; fuzzy r=1 0.195; observed 11.26 km², modelled 50.14 km² of 176.9 km²; peak hmax 20.0 m.
  tier 2 (observed vs modelled km² at h > 0.10 m): AOI01 Kastelli 1.780 vs 69.530; AOI04 Agios Ioannis 0.410 vs 9.590; AOI06 Agios Nikolaos 0.230 vs 20.460; AOI07 Omalos 0.650 vs 26.430
- rainfall vs NOA stations (`phase5/crete_rain_vs_noa.json`, window 2026-09-29T21:00 → 2026-10-04T21:00): anogeia NOA 682 / raw IMERG 173 / R2 175 / ERA5 126 mm; asigonia NOA 385 / raw IMERG 36 / R2 37 / ERA5 219 mm; askyfou NOA 511 / raw IMERG 239 / R2 242 / ERA5 172 mm; fourfouras NOA 442 / raw IMERG 370 / R2 375 / ERA5 139 mm; ierapetra NOA 95 / raw IMERG 355 / R2 360 / ERA5 5 mm; kampoi NOA 171 / raw IMERG 141 / R2 143 / ERA5 246 mm; kandanos NOA 300 / raw IMERG 138 / R2 140 / ERA5 37 mm; potamoi NOA 442 / raw IMERG 232 / R2 235 / ERA5 37 mm; samaria NOA 867 / raw IMERG 240 / R2 243 / ERA5 100 mm; samariagorge NOA 632 / raw IMERG 205 / R2 208 / ERA5 172 mm; sebronas NOA 455 / raw IMERG 119 / R2 121 / ERA5 192 mm; sitia NOA 103 / raw IMERG 126 / R2 128 / ERA5 21 mm; tzermiado NOA 448 / raw IMERG 232 / R2 235 / ERA5 37 mm

## 6. Timing (from the run records; `reproduction/emsr933/timing.md` has the event log)

| run | start UTC | end UTC | SFINCS s | published SFINCS s |
|---|---|---|---|---|
| mandra_cn_a15 | 2026-10-19T17:04:37Z | 2026-10-19T17:16:57Z | 300.373 | None |
| mandra_cn_a58 | 2026-10-19T17:16:57Z | 2026-10-19T18:28:40Z | 3071.646 | None |
| mandra_cn_b_default | 2026-10-19T18:28:40Z | 2026-10-19T19:20:02Z | 2182.423 | None |
| mandra_cn_d_amc3_manning080 | 2026-10-19T20:13:23Z | 2026-10-19T20:30:17Z | 498.728 | None |
| mandra_cn_d_amc3 | 2026-10-19T19:20:02Z | 2026-10-19T20:13:23Z | 2568.228 | None |
| mandra_r2_140 | 2026-10-19T15:17:20Z | 2026-10-19T16:27:49Z | 3157.719 | None |
| mandra_r2_255 | 2026-10-19T16:27:49Z | 2026-10-19T17:04:37Z | 1691.389 | 798.5 |
| mandra_r2_95 | 2026-10-19T15:15:16Z | 2026-10-19T15:17:20Z | 2837.585 | None |
| pineios_cn_on | 2026-10-19T13:33:29Z | 2026-10-19T14:27:14Z | 2191.432 | None |
| pineios_qinf5 | 2026-10-19T19:25:41Z | 2026-10-19T20:33:05Z | 2591.246 | 1012.6 |
| pineios_r2_220 | 2026-10-19T14:21:18Z | 2026-10-19T15:05:02Z | 2043.759 | None |
| pineios_r2_295 | 2026-10-19T15:05:02Z | 2026-10-19T17:11:32Z | 3641.185 | None |
| pineios_r2_510 | 2026-10-19T17:17:30Z | 2026-10-19T19:25:41Z | 4198.593 | 1371.7 |
| pineios_raw_imerg | 2026-10-19T14:27:14Z | 2026-10-19T16:31:44Z | 3215.574 | None |
| pineios_timevarying_q | 2026-10-19T17:09:48Z | 2026-10-19T19:05:28Z | 3446.777 | 2116.0 |
| strymonas_abl_cnoff_q | 2026-10-19T13:33:29Z | 2026-10-19T13:55:25Z | 915.726 | 232.5 |
| strymonas_abl_qoff_cn | 2026-10-19T13:55:25Z | 2026-10-19T14:16:41Z | 220.273 | 110.8 |
| strymonas_leadin7d | 2026-10-19T21:56:00Z | 2026-10-19T23:30:01Z | 4491.846 | None |
| strymonas_v1_prefix_src | 2026-10-19T14:16:41Z | 2026-10-19T14:23:02Z | 238.315 | 219.6 |
| valencia_raw_imerg | 2026-10-19T16:31:44Z | 2026-10-19T17:09:48Z | 1531.571 | None |
| crete_baseline | 2026-10-19T13:54:38Z | 2026-10-19T16:44:39Z | 8370.847 | None |
| crete_canonical_r2on | 2026-10-19T16:44:39Z | 2026-10-19T20:21:12Z | 10946.466 | None |
| crete_sens_anchor_224 | 2026-10-19T23:54:04Z | 2026-10-20T03:06:20Z | 9972.139 | None |
| crete_sens_anchor_336 | 2026-10-19T20:51:57Z | 2026-10-20T00:24:07Z | 11377.458 | None |
| crete_sens_anchor_582 | 2026-10-20T00:24:07Z | 2026-10-20T04:25:09Z | 13014.583 | None |
| crete_sens_karst_q1914 | 2026-10-20T03:06:20Z | 2026-10-20T05:10:42Z | 6236.934 | None |
| crete_sens_r2off | 2026-10-19T20:21:56Z | 2026-10-19T23:54:04Z | 11927.463 | None |

Activation → validated canonical hindcast: 2026-10-04T11:02:00Z → 2026-10-19T20:21:12Z = **15.39 days** (18.56 days after the event time 2026-10-01T07:00:00Z); the interval includes the harness-v1.4 rebuild (CODE-12/13, GO-C, GO-D6) and the wait for ERA5T; see timing.md.

Tests: full suite 138 OK (python -m unittest discover -s tests, 3177 s under the Crete runs, 2026-10-20T03:46Z-04:39Z, log D:/ELKAK/implementation/v14/_logs/unittest_full_0346.log).
