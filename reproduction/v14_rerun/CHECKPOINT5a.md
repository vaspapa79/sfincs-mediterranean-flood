# Checkpoint 5a — Phase 3 under harness v1.4 (+ D6 where curve numbers are on): ablations, S2 variant, R2 sweeps, the eight C2 runs, Pineios audit rows, lead-in sensitivity

Generated 2026-10-19T23:37:07Z by `checkpoint5a_tables.py` from `reproduction/v14_rerun/results/*.json`. Scores at h > 0.10 m, strict; new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides. Run configs: `configs/<run>.yaml` (= the committed example + harness_version v1.4 + the overrides stated in each header).

## Group a — Table 12 ablations (Strymonas; CN on rows under D6)

### strymonas_abl_cnoff_q — Table 12 row 3: CN off + Q

- config: overrides: {"infiltration": {"enabled": false}}
- frozen author config `abl_cnoff.yaml` identical outside env/paths: True

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.239 | 0.249 | **0.295** | +0.056 (mask +0.010) |
| HR | 0.950 | 0.949 | **0.936** | -0.014 (mask -0.001) |
| FAR | 0.758 | 0.748 | **0.699** | -0.059 (mask -0.010) |
| B | 3.93 | 3.76 | **3.11** | -0.82 (mask -0.17) |
| GSS | 0.167 | 0.178 | **0.229** | +0.062 (mask +0.011) |
| TP / FP / FN | 4498 / 14112 / 239 | 4395 / 13041 / 238 | 4336 / 10079 / 297 | |
| fuzzy r=1 CSI | 0.236 | 0.239 | 0.296 | +0.060 |
| modelled wet in eval km² | 418.7 | 392.3 | 324.3 | |
| published record reproduced | True (strymonas_v4_cnoff_qon.json) | | | |
| vs the v1.4 canonical (strymonas_enhanced_postD6) | | | CSI 0.334 → 0.295 (-0.039); HR 0.921 → 0.936; B 2.68 → 3.11; wet 279.7 → 324.3 km² | |
| SFINCS wall-clock s (published) | | | 915.726 (232.5) | |

### strymonas_abl_qoff_cn — Table 12 row 4: CN on + Q off

- config: overrides: {"upstream_q": {"enabled": false}}
- frozen author config `abl_qoff.yaml` identical outside env/paths: True
- curve numbers realised: raster clip mean 73.4, active cells 74.9, msk = 1 74.8 (S mean 88.4 mm)
- the printed Q-off output did not survive (inventory 3a); the 2026-06-19 re-run repro_abl/qoff reproduced the printed numbers (inventory 3c)

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.016 | 0.012 | **0.011** | -0.005 (mask -0.004) |
| HR | 0.016 | 0.012 | **0.011** | -0.005 (mask -0.004) |
| FAR | 0.183 | 0.053 | **0.495** | +0.312 (mask -0.130) |
| B | 0.02 | 0.01 | **0.02** | +0.00 (mask -0.01) |
| GSS | 0.014 | 0.011 | **0.009** | -0.005 (mask -0.004) |
| TP / FP / FN | 76 / 17 / 4661 | 54 / 3 / 4579 | 53 / 52 / 4580 | |
| fuzzy r=1 CSI | 0.027 | 0.021 | 0.020 | -0.007 |
| modelled wet in eval km² | 2.1 | 1.3 | 2.4 | |
| published record reproduced | True (strymonas_v4_qoff.json) | | | |
| vs the v1.4 canonical (strymonas_enhanced_postD6) | | | CSI 0.334 → 0.011 (-0.322); HR 0.921 → 0.011; B 2.68 → 0.02; wet 279.7 → 2.4 km² | |
| SFINCS wall-clock s (published) | | | 220.273 (110.8) | |

## Group b — S2 variant: Strymonas v1, pre-audit Kerkini source

### strymonas_v1_prefix_src — Table 8 'Enhanced v1' / S2 Strymonas v1: pre-fix kerkini_outlet {23.2, 41.08}

- config: overrides: {"upstream_q": {"src_points": [{"name": "kerkini_outlet", "lon": 23.2, "lat": 41.08}, {"name": "angitis", "lon": 23.92, "lat": 41.0}]}}
- curve numbers realised: raster clip mean 73.4, active cells 74.9, msk = 1 74.8 (S mean 88.4 mm)

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.170 | 0.168 | **0.325** | +0.155 (mask -0.002) |
| HR | 0.210 | 0.207 | **0.911** | +0.701 (mask -0.002) |
| FAR | 0.527 | 0.528 | **0.664** | +0.138 (mask +0.002) |
| B | 0.44 | 0.44 | **2.71** | +2.27 (mask -0.00) |
| GSS | 0.143 | 0.142 | **0.263** | +0.119 (mask -0.002) |
| TP / FP / FN | 994 / 1106 / 3743 | 961 / 1077 / 3672 | 4220 / 8354 / 413 | |
| fuzzy r=1 CSI | 0.186 | 0.181 | 0.392 | +0.206 |
| modelled wet in eval km² | 47.2 | 45.9 | 282.9 | |
| published record reproduced | True (strymonas_v1.json) | | | |
| vs the v1.4 canonical (strymonas_enhanced_postD6) | | | CSI 0.334 → 0.325 (-0.009); HR 0.921 → 0.911; B 2.68 → 2.71; wet 279.7 → 282.9 km² | |
| SFINCS wall-clock s (published) | | | 238.315 (219.6) | |

## Group c — R2 anchor sweeps

### mandra_r2_95 — R2 sweep Mandra target 95 mm

- config: overrides: {"rain_bias_correct": {"target_mm": 95}}
- R2 scaling factor realised at run time: ×4.062 (published ×4.062)
- validation/records regenerated with --resume after the stream crashed at the validation step (model output untouched)

| metric | published (mandra.csv target 95) | v1.3 rescored, new mask | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | 0.104 | — (no output survives) | **0.162** | +0.058 |
| HR | 0.754 | — (no output survives) | **0.628** | -0.125 |
| FAR | 0.892 | — (no output survives) | **0.821** | -0.072 |
| B | 6.99 | — (no output survives) | **3.50** | -3.49 |
| GSS | 0.027 | — (no output survives) | **0.078** | +0.050 |
| TP / FP / FN | — / — / — | | 2217 / 10143 / 1311 | |
| modelled wet in eval km² | | | 30.9 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.162 (+0.005); HR 0.760 → 0.628; B 4.61 → 3.50; wet 40.7 → 30.9 km² | |
| SFINCS wall-clock s (published) | | | 2837.585 (None) | |

### mandra_r2_140 — R2 sweep Mandra target 140 mm

- config: overrides: {"rain_bias_correct": {"target_mm": 140}}
- R2 scaling factor realised at run time: ×5.986 (published ×5.986)

| metric | published (mandra.csv target 140) | v1.3 rescored, new mask | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | 0.106 | — (no output survives) | **0.159** | +0.052 |
| HR | 0.824 | — (no output survives) | **0.690** | -0.135 |
| FAR | 0.891 | — (no output survives) | **0.829** | -0.062 |
| B | 7.58 | — (no output survives) | **4.04** | -3.54 |
| GSS | 0.028 | — (no output survives) | **0.071** | +0.042 |
| TP / FP / FN | — / — / — | | 2434 / 11827 / 1094 | |
| modelled wet in eval km² | | | 35.7 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.159 (+0.002); HR 0.760 → 0.690; B 4.61 → 4.04; wet 40.7 → 35.7 km² | |
| SFINCS wall-clock s (published) | | | 3157.719 (None) | |

### mandra_r2_255 — R2 sweep Mandra target 255 mm

- config: overrides: {"rain_bias_correct": {"target_mm": 255}}
- R2 scaling factor realised at run time: ×10.903 (published ×10.903)

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.104 | 0.145 | **0.157** | +0.052 (mask +0.041) |
| HR | 0.893 | 0.891 | **0.812** | -0.081 (mask -0.002) |
| FAR | 0.894 | 0.852 | **0.838** | -0.057 (mask -0.042) |
| B | 8.46 | 6.03 | **5.00** | -3.46 (mask -2.42) |
| GSS | 0.025 | 0.050 | **0.065** | +0.040 (mask +0.025) |
| TP / FP / FN | 3211 / 27187 / 384 | 3144 / 18145 / 384 | 2864 / 14772 / 664 | |
| fuzzy r=1 CSI | 0.158 | 0.202 | 0.207 | +0.049 |
| modelled wet in eval km² | 76.0 | 53.2 | 44.1 | |
| published record reproduced | True (mandra.csv target 255) | | | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.157 (-0.000); HR 0.760 → 0.812; B 4.61 → 5.00; wet 40.7 → 44.1 km² | |
| SFINCS wall-clock s (published) | | | 1691.389 (798.5) | |

### pineios_r2_220 — R2 sweep Pineios target 220 mm

- config: overrides: {"rain_bias_correct": {"target_mm": 220}}
- R2 scaling factor realised at run time: ×1.499 (published ×1.499)
- validation/records regenerated with --resume after the stream crashed at the validation step (model output untouched)

| metric | published (pineios.csv target 220) | v1.3 rescored, new mask | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | 0.475 | — (no output survives) | **0.505** | +0.029 |
| HR | 0.902 | — (no output survives) | **0.831** | -0.071 |
| FAR | 0.499 | — (no output survives) | **0.438** | -0.061 |
| B | 1.80 | — (no output survives) | **1.48** | -0.32 |
| GSS | 0.239 | — (no output survives) | **0.292** | +0.053 |
| TP / FP / FN | — / — / — | | 55711 / 43374 / 11296 | |
| modelled wet in eval km² | | | 2229.4 | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.505 (+0.010); HR 0.898 → 0.831; B 1.71 → 1.48; wet 2584.5 → 2229.4 km² | |
| SFINCS wall-clock s (published) | | | 2043.759 (None) | |

### pineios_r2_295 — R2 sweep Pineios target 295 mm

- config: overrides: {"rain_bias_correct": {"target_mm": 295}}
- R2 scaling factor realised at run time: ×2.009 (published ×2.009)

| metric | published (pineios.csv target 295) | v1.3 rescored, new mask | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | 0.466 | — (no output survives) | **0.501** | +0.035 |
| HR | 0.926 | — (no output survives) | **0.867** | -0.060 |
| FAR | 0.516 | — (no output survives) | **0.457** | -0.059 |
| B | 1.91 | — (no output survives) | **1.59** | -0.32 |
| GSS | 0.221 | — (no output survives) | **0.279** | +0.058 |
| TP / FP / FN | — / — / — | | 58065 / 48803 / 8942 | |
| modelled wet in eval km² | | | 2404.5 | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.501 (+0.007); HR 0.898 → 0.867; B 1.71 → 1.59; wet 2584.5 → 2404.5 km² | |
| SFINCS wall-clock s (published) | | | 3641.185 (None) | |

### pineios_r2_510 — R2 sweep Pineios target 510 mm

- config: overrides: {"rain_bias_correct": {"target_mm": 510}}
- R2 scaling factor realised at run time: ×3.474 (published ×3.474)

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.446 | 0.462 | **0.486** | +0.040 (mask +0.016) |
| HR | 0.959 | 0.959 | **0.920** | -0.040 (mask -0.000) |
| FAR | 0.545 | 0.529 | **0.492** | -0.053 (mask -0.016) |
| B | 2.11 | 2.04 | **1.81** | -0.30 (mask -0.07) |
| GSS | 0.184 | 0.199 | **0.244** | +0.060 (mask +0.015) |
| TP / FP / FN | 64754 / 77674 / 2750 | 64264 / 72174 / 2743 | 61617 / 59668 / 5390 | |
| fuzzy r=1 CSI | 0.418 | 0.427 | 0.450 | +0.032 |
| modelled wet in eval km² | 3204.6 | 3069.9 | 2728.9 | |
| published record reproduced | True (pineios.csv target 510) | | | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.486 (-0.008); HR 0.898 → 0.920; B 1.71 → 1.81; wet 2584.5 → 2728.9 km² | |
| SFINCS wall-clock s (published) | | | 4198.593 (1371.7) | |

## Group d — The eight C2 runs (relabelled curve numbers) and the Pineios audit rows

### mandra_cn_a15 — S1 row 1: HSG-A AMC-II (CN = 15 test) — pervious classes CN 15

- config: overrides: {"infiltration": {"enabled": true, "hsg": "A", "amc": 2, "cn_lookup": {"10": 15, "20": 15, "30": 15, "40": 15, "60": 15, "90": 15, "95": 15, "100": 15, "50": 88, "70": 99, "80": 99}}}
- curve numbers realised: raster clip mean 48.7, active cells 33.7, msk = 1 31.8 (S mean 1088.4 mm)
- R2 scaling factor realised at run time: ×8.551
- published (text): NHESS supplement R5, Table S1 (Configuration | mean CN | Total wet km2 | TP (01MANDRA) | CSI | HR | FAR) row 1 → mean_cn 42, total_wet_km2 0.77, tp_01mandra 0, csi 0.031, hr 0.032, far 0.42

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.109** | |
| HR | | | **0.257** | |
| FAR | | | **0.840** | |
| B | | | **1.61** | |
| GSS | | | **0.043** | |
| TP / FP / FN | | | 905 / 4768 / 2623 | |
| modelled wet in eval km² | | | 14.2 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.109 (-0.048); HR 0.760 → 0.257; B 4.61 → 1.61; wet 40.7 → 14.2 km² | |
| 01MANDRA (S1 column) | TP 0 | | TP 475, CSI 0.130 | |
| SFINCS wall-clock s (published) | | | 300.373 (None) | |

### mandra_cn_a58 — S1 row 2: HSG-A AMC-II (CN = 58 test) — pervious classes CN 58

- config: overrides: {"infiltration": {"enabled": true, "hsg": "A", "amc": 2, "cn_lookup": {"10": 58, "20": 58, "30": 58, "40": 58, "60": 58, "90": 58, "95": 58, "100": 58, "50": 88, "70": 99, "80": 99}}}
- curve numbers realised: raster clip mean 74.0, active cells 66.0, msk = 1 65.0 (S mean 145.3 mm)
- R2 scaling factor realised at run time: ×8.551
- published (text): NHESS supplement R5, Table S1 (Configuration | mean CN | Total wet km2 | TP (01MANDRA) | CSI | HR | FAR) row 2 → mean_cn 65, total_wet_km2 0.77, tp_01mandra 0, csi 0.031, hr 0.032, far 0.42

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.158** | |
| HR | | | **0.645** | |
| FAR | | | **0.827** | |
| B | | | **3.73** | |
| GSS | | | **0.072** | |
| TP / FP / FN | | | 2275 / 10896 / 1253 | |
| modelled wet in eval km² | | | 32.9 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.158 (+0.001); HR 0.760 → 0.645; B 4.61 → 3.73; wet 40.7 → 32.9 km² | |
| 01MANDRA (S1 column) | TP 0 | | TP 770, CSI 0.133 | |
| SFINCS wall-clock s (published) | | | 3071.646 (None) | |

### mandra_cn_b_default — S1 row 3: HSG-B AMC-II (default lookup)

- config: overrides: {"infiltration": {"enabled": true}}
- curve numbers realised: raster clip mean 80.2, active cells 75.0, msk = 1 74.3 (S mean 89.8 mm)
- R2 scaling factor realised at run time: ×8.551
- published (text): NHESS supplement R5, Table S1 (Configuration | mean CN | Total wet km2 | TP (01MANDRA) | CSI | HR | FAR) row 3 → mean_cn 80, total_wet_km2 0.77, tp_01mandra 0, csi 0.031, hr 0.032, far 0.42

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.158** | |
| HR | | | **0.699** | |
| FAR | | | **0.831** | |
| B | | | **4.13** | |
| GSS | | | **0.070** | |
| TP / FP / FN | | | 2465 / 12113 / 1063 | |
| modelled wet in eval km² | | | 36.4 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.158 (+0.001); HR 0.760 → 0.699; B 4.61 → 4.13; wet 40.7 → 36.4 km² | |
| 01MANDRA (S1 column) | TP 0 | | TP 801, CSI 0.131 | |
| SFINCS wall-clock s (published) | | | 2182.423 (None) | |

### mandra_cn_d_amc3 — S1 row 4: HSG-D AMC-III (post-fire, saturated) — TR-55 HSG-D lookup, AMC III

- config: overrides: {"infiltration": {"enabled": true, "hsg": "D", "amc": 3, "cn_lookup": {"10": 79, "20": 77, "30": 84, "40": 89, "50": 93, "60": 94, "70": 99, "80": 99, "90": 90, "95": 90, "100": 85}}}
- curve numbers realised: raster clip mean 94.6, active cells 93.0, msk = 1 92.8 (S mean 19.3 mm)
- R2 scaling factor realised at run time: ×8.551
- published (text): NHESS supplement R5, Table S1 (Configuration | mean CN | Total wet km2 | TP (01MANDRA) | CSI | HR | FAR) row 4 → mean_cn 97, total_wet_km2 111, tp_01mandra 0, csi 0.01, hr 0.036, far 0.99

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.156** | |
| HR | | | **0.753** | |
| FAR | | | **0.835** | |
| B | | | **4.57** | |
| GSS | | | **0.067** | |
| TP / FP / FN | | | 2656 / 13456 / 872 | |
| modelled wet in eval km² | | | 40.3 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.156 (-0.000); HR 0.760 → 0.753; B 4.61 → 4.57; wet 40.7 → 40.3 km² | |
| 01MANDRA (S1 column) | TP 0 | | TP 834, CSI 0.126 | |
| SFINCS wall-clock s (published) | | | 2568.228 (None) | |

### mandra_cn_d_amc3_manning080 — S1 prose: Manning test, built-up n 0.012 -> 0.080 at the HSG-D AMC-III configuration

- config: overrides: {"infiltration": {"enabled": true, "hsg": "D", "amc": 3, "cn_lookup": {"10": 79, "20": 77, "30": 84, "40": 89, "50": 93, "60": 94, "70": 99, "80": 99, "90": 90, "95": 90, "100": 85}}}; paths.manning_lookup -> manning_lookup_builtup_0.080.csv (class 50 built-up n = 0.08)
- curve numbers realised: raster clip mean 94.6, active cells 93.0, msk = 1 92.8 (S mean 19.3 mm)
- R2 scaling factor realised at run time: ×8.551
- published (text): NHESS supplement R5, S1 prose: no measurable change in per-area true positives or in total wet area (115.8 vs. 110.8 km2 at CN = 97) → total_wet_km2_n080 115.8, total_wet_km2_n012 110.8

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.153** | |
| HR | | | **0.812** | |
| FAR | | | **0.841** | |
| B | | | **5.11** | |
| GSS | | | **0.061** | |
| TP / FP / FN | | | 2863 / 15179 / 665 | |
| modelled wet in eval km² | | | 45.1 | |
| vs the v1.4 canonical (mandra_enhanced) | | | CSI 0.157 → 0.153 (-0.004); HR 0.760 → 0.812; B 4.61 → 5.11; wet 40.7 → 45.1 km² | |
| 01MANDRA (S1 column) | TP — | | TP 969, CSI 0.128 | |
| SFINCS wall-clock s (published) | | | 498.728 (None) | |

### pineios_cn_on — §4.1.2 (ii) / §6.2: Pineios CN-on (HSG-B, AMC-II)

- config: overrides: {"infiltration": {"enabled": true}}
- curve numbers realised: raster clip mean 76.9, active cells 73.2, msk = 1 73.1 (S mean 95.1 mm)
- R2 scaling factor realised at run time: ×2.725
- published (text): NHESS manuscript R5 §4.1.2 (ii): collapsed the flood to ~38 km2 (against 1519 km2 observed) → modelled_wet_km2 38, observed_km2 1519

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.505** | |
| HR | | | **0.882** | |
| FAR | | | **0.458** | |
| B | | | **1.63** | |
| GSS | | | **0.281** | |
| TP / FP / FN | | | 59106 / 50005 / 7901 | |
| modelled wet in eval km² | | | 2455.0 | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.505 (+0.010); HR 0.898 → 0.882; B 1.71 → 1.63; wet 2584.5 → 2455.0 km² | |
| SFINCS wall-clock s (published) | | | 2191.432 (None) | |

### pineios_raw_imerg — §5: Pineios raw IMERG (no R2)

- config: overrides: {"rain_bias_correct": {"enabled": false}}
- forcing: imerg_pineios.raw.nc -> imerg_pineios.nc (rain_bias_correct disabled; the D1 rate/label convention is applied at build time)
- published (text): NHESS manuscript R5 §5: raw IMERG recovers only 141 mm and bounds the flood below 40 km2 → watershed_mean_mm 141, modelled_wet_km2_upper 40

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.502** | |
| HR | | | **0.775** | |
| FAR | | | **0.412** | |
| B | | | **1.32** | |
| GSS | | | **0.303** | |
| TP / FP / FN | | | 51932 / 36386 / 15075 | |
| modelled wet in eval km² | | | 1987.2 | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.502 (+0.008); HR 0.898 → 0.775; B 1.71 → 1.32; wet 2584.5 → 1987.2 km² | |
| SFINCS wall-clock s (published) | | | 3215.574 (None) | |

### valencia_raw_imerg — §4.4.2 / §5.3 / S3.1: Valencia raw IMERG (no R2)

- config: overrides: {"rain_bias_correct": {"enabled": false}}
- forcing: imerg_valencia.raw.nc -> imerg_valencia.nc (rain_bias_correct disabled; the D1 rate/label convention is applied at build time)
- published (text): NHESS manuscript R5 §4.4.2: The uncorrected raw-IMERG run scores CSI = 0.105 → csi 0.105

| metric | published (S1_EMSR773_valencia_raw_IMERG_metrics.json) | v1.3 rescored, new mask | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | 0.105 | — (no output survives) | **0.163** | +0.058 |
| HR | 0.966 | — (no output survives) | **0.864** | -0.102 |
| FAR | 0.895 | — (no output survives) | **0.832** | -0.062 |
| TP / FP / FN | 19353 / 164114 / 676 | | 16921 / 84082 / 2660 | |
| modelled wet in eval km² | | | 1010.0 | |
| vs the v1.4 canonical (valencia_enhanced_164) | | | CSI 0.144 → 0.163 (+0.019); HR 0.939 → 0.864; B 6.46 → 5.16; wet 1265.2 → 1010.0 km² | |
| SFINCS wall-clock s (published) | | | 1531.571 (None) | |

### pineios_timevarying_q — S2 Pineios v3 / §4.1.1: time-varying GloFAS Q audit (dis + src rebuilt after the build)

- discharge rebuilt from GloFAS (nearest cell at the injection point, hourly linear, src on the lowest-zb cell within ±10 cells): pineios_trikala peak 1.38 m³/s (shift +1478/-236 m), pineios_kalambaka peak 0.40 m³/s (shift +727/-1374 m), titarisios peak 24.41 m³/s (shift -17/+1555 m), enipeas peak 118.40 m³/s (shift -1547/+421 m); combined peak 135.0 m³/s; pipeline file was constant 11.59 m³/s at every source
- R2 scaling factor realised at run time: ×2.725

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.456 | 0.473 | **0.495** | +0.039 (mask +0.017) |
| HR | 0.947 | 0.946 | **0.898** | -0.048 (mask -0.000) |
| FAR | 0.532 | 0.514 | **0.476** | -0.056 (mask -0.018) |
| B | 2.02 | 1.95 | **1.71** | -0.31 (mask -0.07) |
| GSS | 0.201 | 0.218 | **0.262** | +0.060 (mask +0.017) |
| TP / FP / FN | 63907 / 72692 / 3597 | 63419 / 67193 / 3588 | 60191 / 54657 / 6816 | |
| fuzzy r=1 CSI | 0.426 | 0.436 | 0.461 | +0.034 |
| modelled wet in eval km² | 3073.5 | 2938.8 | 2584.1 | |
| published record reproduced | True (pineios_v3_recheck.json) | | | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.495 (-0.000); HR 0.898 → 0.898; B 1.71 → 1.71; wet 2584.5 → 2584.1 km² | |
| SFINCS wall-clock s (published) | | | 3446.777 (2116.0) | |

### pineios_qinf5 — §5.2: constant infiltration qinf = 5 mm/h on the time-varying-Q build (as the published v4 run)

- discharge rebuilt from GloFAS (nearest cell at the injection point, hourly linear, src on the lowest-zb cell within ±10 cells): pineios_trikala peak 1.38 m³/s (shift +1478/-236 m), pineios_kalambaka peak 0.40 m³/s (shift +727/-1374 m), titarisios peak 24.41 m³/s (shift -17/+1555 m), enipeas peak 118.40 m³/s (shift -1547/+421 m); combined peak 135.0 m³/s; pipeline file was constant 11.59 m³/s at every source
- sfincs.inp patch after the build: {'qinf': 'replaced'}
- R2 scaling factor realised at run time: ×2.725

| metric | v1.3 as published | v1.3 rescored, new mask | v1.4, new mask | Δ (v1.4 − published) |
|---|---|---|---|---|
| CSI | 0.456 | 0.474 | **0.472** | +0.015 (mask +0.017) |
| HR | 0.929 | 0.929 | **0.814** | -0.115 (mask -0.000) |
| FAR | 0.527 | 0.509 | **0.471** | -0.056 (mask -0.018) |
| B | 1.96 | 1.89 | **1.54** | -0.42 (mask -0.07) |
| GSS | 0.206 | 0.223 | **0.247** | +0.041 (mask +0.018) |
| TP / FP / FN | 62708 / 69872 / 4796 | 62238 / 64400 / 4769 | 54574 / 48653 / 12433 | |
| fuzzy r=1 CSI | 0.430 | 0.439 | 0.467 | +0.037 |
| modelled wet in eval km² | 2983.0 | 2849.4 | 2322.6 | |
| published record reproduced | True (pineios_v4_qinf5.json) | | | |
| vs the v1.4 canonical (pineios_enhanced) | | | CSI 0.495 → 0.472 (-0.023); HR 0.898 → 0.814; B 1.71 → 1.54; wet 2584.5 → 2322.6 km² | |
| SFINCS wall-clock s (published) | | | 2591.246 (1012.6) | |

## Group e — Strymonas lead-in sensitivity (7 forcing days simulated)

### strymonas_leadin7d — sensitivity: 7-day lead-in simulated (tstart = tref = 2015-03-21), CN on

- config: overrides: {"window": {"spinup_days": 0, "pre_event_days": 10, "post_event_days": 3}}
- curve numbers realised: raster clip mean 73.4, active cells 74.9, msk = 1 74.8 (S mean 88.4 mm)

| metric | published (text, see below) | v1.3 rescored | v1.4, new mask | Δ |
|---|---|---|---|---|
| CSI | | | **0.255** | |
| HR | | | **0.959** | |
| FAR | | | **0.742** | |
| B | | | **3.72** | |
| GSS | | | **0.185** | |
| TP / FP / FN | | | 4442 / 12773 / 191 | |
| modelled wet in eval km² | | | 387.3 | |
| vs the v1.4 canonical (strymonas_enhanced_postD6) | | | CSI 0.334 → 0.255 (-0.078); HR 0.921 → 0.959; B 2.68 → 3.72; wet 279.7 → 387.3 km² | |
| hmax restricted to the canonical window 2015-03-28 → 2015-04-04 (time_matched_scores.py --window) | | | CSI 0.278 HR 0.955 FAR 0.719 B 3.40 | |
| SFINCS wall-clock s (published) | | | 4491.846 (None) | |

## D7 — new defect, report only (no fix without the author's go)

`skill/scripts/prep_q_at_outlets.py` samples GloFAS with `sel(latitude=slice(lat + 0.1, lat − 0.1))`; the Pineios GloFAS file has an ASCENDING latitude axis (39.11 → 40.21), so the slice is empty for every source and the script falls back to the domain-mean discharge: `q_outlet.csv` = 11.589 m³/s at all four sources and every hour (the published canonical run, the Phase-1 v1.4 run and every pipeline Pineios run of Phase 3 carry this constant; the Strymonas, Valencia and Emilia files are descending and sample correctly; Crete has R3 off). The supplement's S2 Pineios row already states that the v1 discharge was constant ("an ingestion placeholder") and that the time-varying audit returns identical metrics; the v1.4 audit row (pineios_timevarying_q) is the time-varying counterpart under v1.4, built outside the pipeline by `rebuild_pineios_q.py` (the CODE-8 audit method). Fix candidate for the author: make the sampler order-agnostic (boolean coordinate masks) and warn instead of silently falling back.

Tests: new/touched modules 50 green (test_phase3_rebuild_q, test_skill_scores, test_time_matched_scores, test_rain_diagnostics, test_truth_buffer_scores, test_validator_light_loader, test_crete_rain_vs_noa, test_d6_cn_bookkeeping.RenderD6, test_eval_exclusion; unittest 2026-10-19T23:4xZ); full suite before the v1.4.0 tag.

