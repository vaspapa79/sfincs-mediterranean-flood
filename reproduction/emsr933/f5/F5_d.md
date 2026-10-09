# F5-d: rainfall depth written to the SFINCS forcing (as-run models) - facts only

Source: `f5_d_volume.py` -> `F5_d.json` (every number below is copied from the JSON; ratios to 3 decimals). Totals in mm as spatial means over the stated cells. `pc` = piecewise-constant forward sum(rate x dt) over stamps T0 <= t < T1 (SFINCS amprblock=1; an IMERG stamp is the start of its 30-min slot); `trap` = trapezoidal over T0 <= t <= T1; `incl` = inclusive-stamp sum x dt (the bias_correct_imerg.py rule). dt = 0.5 h (30-min stamps) in every file.
Model files: variable `Precipitation`(time,y,x), units mm/h, projected UTM grid (hydromt nearest-index resample of IMERG, ~9.5-10 km cells); IMERG files: `precip`(time,latitude,longitude), mm/h, 0.1 deg lat/lon. Every build's hydromt.log records `setup_precip_forcing_from_grid.cumulative_input: True, time_label: right` (hydromt_sfincs 1.2.2) for this mm/h input, which divides the rate by 0.5 h and shifts the series one frame earlier. sfincs_map.nc has storecumprcp=0 and no rainfall variable; sfincs.log prints no rainfall total; `precip_2d.nc` is the only on-disk record of the rain SFINCS read.

## Pineios / Storm Daniel (EMSR692), enhanced
`sfincs.inp`: tref 20230827 000000, tstart 20230903 000000, tstop 20230911 000000, `netamprfile = precip_2d.nc`, dtwnd 1800.0, EPSG 32634. Event window 2023-09-04T00:00 -> 2023-09-08T00:00 UTC; bbox (lon/lat) [22.0, 39.4, 22.95, 40.0].

| quantity | model precip_2d (written) | IMERG bias-corrected | IMERG raw |
|---|---|---|---|
| grid | 13x15 cells, 9462.8 m, WGS 84 / UTM zone 34N | 11x16 cells, 0.1 deg | 11x16 cells, 0.1 deg |
| time: first / last / step / count | 2023-09-03T00:00:00 / 2023-09-11T00:00:00 / 30 min / 385 | 2023-08-27T00:00:00 / 2023-09-11T00:00:00 / 30 min / 721 | 2023-08-27T00:00:00 / 2023-09-11T00:00:00 / 30 min / 721 (calendar attr `julian`, decoded as standard) |
| event window, domain mean (all cells) [n cells] | 746.90 pc / 746.93 trap [195] | 376.40 pc / 376.43 trap [176] | 138.15 pc / 138.16 trap [176] |
| event window, bbox mean [n cells] | 783.12 pc / 783.18 trap [58] | 398.27 pc / 398.30 trap [60] | 146.18 pc / 146.19 trap [60] |
| event window, mean over SFINCS grid rectangle [n cells] | 790.82 pc / 790.88 trap [99] | 395.84 pc / 395.88 trap [84] | 145.28 pc / 145.30 trap [84] |
| event window, active-cell-weighted mean (msk>0: 262465 cells) | 834.14 pc / 834.21 trap | - | - |
| whole file, domain mean (n stamps) | 751.44 pc / 751.44 trap (385) | 380.44 pc / 380.44 trap (721) | 141.37 pc / 141.37 trap (721) |
| whole file, bbox mean | 789.64 pc / 789.64 trap | 402.42 pc / 402.42 trap | 149.23 pc / 149.23 trap |
| bias window per attr 09-04T00:00 -> 09-08T23:30, bbox mean, incl rule (n stamps) | 787.12 (240) | 400.00 (240); attr: x2.725 -> 400 mm | 146.81 |

Ratios, model precip_2d (written) (event window, pc): model/IMERG-bc domain **1.984**, bbox **1.966**, grid-rect 1.998; model/IMERG-raw domain **5.406**, bbox **5.357**. Model bbox / 400 mm: **1.958** (trap 1.958), active-weighted / 400: 2.085, bias-window incl / 400: 1.968 (IMERG-bc: 1.0); Model bbox / 380 mm: **2.061** (trap 2.061), active-weighted / 380: 2.195, bias-window incl / 380: 2.071 (IMERG-bc: 1.053);
Pointwise, model precip_2d (written) (nearest IMERG cell; 191/195 precip_2d cells inside the IMERG extent, the 4 outside hold max 0.0 mm/h): model(t) = 2 x IMERG-bc(t+30 min) for **97.90%** of 30469 cell-time pairs; the 639 others come from 4 cells whose centre lies 0.0003-0.0023 deg from an IMERG cell edge: 639 equal 2 x an adjacent IMERG cell (zero-valued neighbours included), 59 have model = 0, 0 lie on the grid's outer ring (overlapping counts); depth share of these pairs 2.10%; sum(model)/sum(2 x IMERG-bc) over all pairs = **1.0006**; without the 30-min shift only 1.90% match. Last model frame max 0.000 mm/h.
Model / raw-IMERG per-frame median factor, model precip_2d (written) (shift +30 min): **5.449** for 240 frames 09-03T23:30..09-08T23:00; **1.0** for 2 frames 09-10T00:30..09-10T01:00; 2.0 for 57 frames; 83 frames with no raw rain (undefined); single frames: 1.0@09-03T17:30, 1.0@09-09T15:30.
Duplicate model folder: `D:\ELKAK\implementation\pineios_sfincs_enhanced\model\precip_2d.nc` Precipitation array identical to model_author_ref = True.

## Mandra (EMSR257), enhanced
`sfincs.inp`: tref 20171112 000000, tstart 20171113 000000, tstop 20171118 000000, `netamprfile = precip_2d.nc`, dtwnd 1800.0, EPSG 32634. Event window 2017-11-14T00:00 -> 2017-11-16T00:00 UTC; bbox (lon/lat) [23.4, 38.05, 23.55, 38.15].

| quantity | model precip_2d (written) | IMERG bias-corrected | IMERG raw |
|---|---|---|---|
| grid | 8x6 cells, 10007.8 m, WGS 84 / UTM zone 34N | 7x7 cells, 0.1 deg | 7x7 cells, 0.1 deg |
| time: first / last / step / count | 2017-11-13T00:00:00 / 2017-11-18T00:00:00 / 30 min / 241 | 2017-11-12T00:00:00 / 2017-11-18T00:00:00 / 30 min / 289 | 2017-11-12T00:00:00 / 2017-11-18T00:00:00 / 30 min / 289 (calendar attr `julian`, decoded as standard) |
| event window, domain mean (all cells) [n cells] | 254.34 pc / 254.34 trap [48] | 125.03 pc / 125.03 trap [49] | 14.62 pc / 14.62 trap [49] |
| event window, bbox mean [n cells] | 447.74 pc / 447.74 trap [1] | 200.00 pc / 200.00 trap [4] | 23.39 pc / 23.39 trap [4] |
| event window, mean over SFINCS grid rectangle [n cells] | 362.82 pc / 362.82 trap [9] | 180.59 pc / 180.59 trap [9] | 21.12 pc / 21.12 trap [9] |
| event window, active-cell-weighted mean (msk>0: 162335 cells) | 331.97 pc / 331.97 trap | - | - |
| whole file, domain mean (n stamps) | 456.24 pc / 456.23 trap (241) | 228.26 pc / 228.25 trap (289) | 117.84 pc / 117.84 trap (289) |
| whole file, bbox mean | 668.81 pc / 668.81 trap | 310.08 pc / 310.08 trap | 133.46 pc / 133.46 trap |
| bias window per attr 11-14T00:00 -> 11-15T23:30, bbox mean, incl rule (n stamps) | 447.74 (96) | 200.00 (96); attr: x8.551 -> 200 mm | 23.39 |

Ratios, model precip_2d (written) (event window, pc): model/IMERG-bc domain **2.034**, bbox **2.239**, grid-rect 2.009; model/IMERG-raw domain **17.394**, bbox **19.143**. Model bbox / 200 mm: **2.239** (trap 2.239), active-weighted / 200: 1.66, bias-window incl / 200: 2.239 (IMERG-bc: 1.0);
Pointwise, model precip_2d (written) (nearest IMERG cell; 48/48 precip_2d cells inside the IMERG extent): model(t) = 2 x IMERG-bc(t+30 min) for **100.00%** of 3667 cell-time pairs; no exceptions; sum(model)/sum(2 x IMERG-bc) over all pairs = **1.0**; without the 30-min shift only 1.55% match. Last model frame max 0.000 mm/h.
Model / raw-IMERG per-frame median factor, model precip_2d (written) (shift +30 min): **17.102** for 50 frames 11-14T12:30..11-15T13:00; **17.102** for 13 frames 11-15T17:00..11-15T23:00; 2.0 for 99 frames; 78 frames with no raw rain (undefined).
Duplicate model folder: `D:\ELKAK\implementation\mandra_sfincs_enhanced\model\precip_2d.nc` Precipitation array identical to model_author_ref = True.

## Valencia (EMSR773): as-run 350-mm anchor and 164-mm re-run (rerun_v164)
`sfincs.inp` (byte-identical in both model folders): tref 20241024 000000, tstart 20241027 000000, tstop 20241101 000000, `netamprfile = precip_2d.nc`, dtwnd 1800.0, EPSG 32630. Event window 2024-10-29T00:00 -> 2024-10-30T00:00 UTC; bbox (lon/lat) [-0.75, 39.33, -0.3, 39.55].

| quantity | 350-mm run precip_2d | 164-mm re-run precip_2d | IMERG bias-corrected | IMERG raw |
|---|---|---|---|---|
| grid | 14x13 cells, 9747.6 m, WGS 84 / UTM zone 30N | 14x13 cells, 9747.6 m, WGS 84 / UTM zone 30N | 14x16 cells, 0.1 deg | 14x16 cells, 0.1 deg |
| time: first / last / step / count | 2024-10-27T00:00:00 / 2024-11-01T00:00:00 / 30 min / 241 | 2024-10-27T00:00:00 / 2024-11-01T00:00:00 / 30 min / 241 | 2024-10-24T00:00:00 / 2024-11-01T00:00:00 / 30 min / 385 | 2024-10-24T00:00:00 / 2024-11-01T00:00:00 / 30 min / 385 (calendar attr `julian`, decoded as standard) |
| event window, domain mean (all cells) [n cells] | 354.52 pc / 354.51 trap [182] | 166.12 pc / 166.11 trap [182] | 175.21 pc / 175.26 trap [224] | 42.29 pc / 42.30 trap [224] |
| event window, bbox mean [n cells] | 677.50 pc / 677.43 trap [12] | 317.46 pc / 317.42 trap [12] | 350.00 pc / 349.84 trap [15] | 84.48 pc / 84.44 trap [15] |
| event window, mean over SFINCS grid rectangle [n cells] | 432.84 pc / 432.81 trap [64] | 202.82 pc / 202.80 trap [64] | 208.77 pc / 208.53 trap [80] | 50.39 pc / 50.33 trap [80] |
| event window, active-cell-weighted mean (msk>0: 521427 cells) | 301.49 pc / 301.44 trap | 141.27 pc / 141.25 trap | - | - |
| whole file, domain mean (n stamps) | 383.73 pc / 383.70 trap (241) | 195.30 pc / 195.28 trap (241) | 212.05 pc / 211.95 trap (385) | 78.84 pc / 78.74 trap (385) |
| whole file, bbox mean | 688.39 pc / 688.37 trap | 328.34 pc / 328.32 trap | 371.73 pc / 371.73 trap | 106.21 pc / 106.21 trap |
| bias window per attr 10-29T00:00 -> 10-30T00:00, bbox mean, incl rule (n stamps) | 677.50 (49) | 317.46 (49) | 350.00 (49); attr: x4.143 -> 350 mm | 84.48 |

Ratios, 350-mm run precip_2d (event window, pc): model/IMERG-bc domain **2.023**, bbox **1.936**, grid-rect 2.073; model/IMERG-raw domain **8.384**, bbox **8.02**. Model bbox / 350 mm: **1.936** (trap 1.936), active-weighted / 350: 0.861, bias-window incl / 350: 1.936 (IMERG-bc: 1.0); Model bbox / 164 mm: **4.131** (trap 4.131), active-weighted / 164: 1.838, bias-window incl / 164: 4.131 (IMERG-bc: 2.134);
Ratios, 164-mm re-run precip_2d (event window, pc): model/IMERG-bc domain **0.948**, bbox **0.907**, grid-rect 0.971; model/IMERG-raw domain **3.928**, bbox **3.758**. Model bbox / 164 mm: **1.936** (trap 1.936), active-weighted / 164: 0.861, bias-window incl / 164: 1.936 (IMERG-bc: 2.134); Model bbox / 350 mm: **0.907** (trap 0.907), active-weighted / 350: 0.404, bias-window incl / 350: 0.907 (IMERG-bc: 1.0);
Pointwise, 350-mm run precip_2d (nearest IMERG cell; 182/182 precip_2d cells inside the IMERG extent): model(t) = 2 x IMERG-bc(t+30 min) for **95.13%** of 10919 cell-time pairs; the 532 others come from 8 cells whose centre lies 0.0001-0.025 deg from an IMERG cell edge: 246 equal 2 x an adjacent IMERG cell (zero-valued neighbours included), 450 have model = 0, 415 lie on the grid's outer ring (overlapping counts); depth share of these pairs 1.41%; sum(model)/sum(2 x IMERG-bc) over all pairs = **0.9901**; without the 30-min shift only 2.19% match. Last model frame max 0.000 mm/h.
Model / raw-IMERG per-frame median factor, 350-mm run precip_2d (shift +30 min): **8.286** for 49 frames 10-28T23:30..10-29T23:30; 2.0 for 146 frames; 43 frames with no raw rain (undefined); single frames: 1.0@10-28T04:30, 1.0@10-28T05:30.
Pointwise, 164-mm re-run precip_2d (nearest IMERG cell; 182/182 precip_2d cells inside the IMERG extent): model(t) = 2 x IMERG-bc(t+30 min) for **58.17%** of 10919 cell-time pairs; the 4567 others come from 182 cells: 207 equal 2 x an adjacent IMERG cell (zero-valued neighbours included), 450 have model = 0, 1411 lie on the grid's outer ring (overlapping counts); depth share of these pairs 85.11%; sum(model)/sum(2 x IMERG-bc) over all pairs = **0.5039**; without the 30-min shift only 1.77% match. Last model frame max 0.000 mm/h.
Model / raw-IMERG per-frame median factor, 164-mm re-run precip_2d (shift +30 min): **3.883** for 48 frames 10-29T00:00..10-29T23:30; 2.0 for 145 frames; 43 frames with no raw rain (undefined); single frames: 1.0@10-28T04:30, 1.0@10-28T05:30, 8.286@10-28T23:30, 0.937@10-30T00:00.
164-mm re-run precip_2d / 350-mm run precip_2d, per-frame median ratio: **0.4686** for 49 frames 10-29T00:00..10-30T00:00; 1.0 on every other frame with rain.
Note: rerun_v164/ holds no data/ folder and no imerg nc; the 350-mm run's imerg_valencia.nc (x4.143 -> 350 mm) and imerg_valencia.raw.nc are the only IMERG inputs on disk for Valencia.

## Files read (all opened read-only; size, sha256 prefix)
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\`: sfincs.inp (1614 B, b2b5a0ae94f7), precip_2d.nc (320888 B, 9072228ba3dc), sfincs_map.nc (136916034 B)
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\model\`: precip_2d.nc (320887 B, 8db4a0a7112b)
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\data\`: imerg_pineios.nc (532392 B, 48abe957cbd5), imerg_pineios.raw.nc (534463 B, 21a53e3fc9fa)
- `D:\ELKAK\implementation\mandra_sfincs_enhanced\model_author_ref\`: sfincs.inp (1568 B, 82b57767affa), precip_2d.nc (64093 B, cf98bea9094a), sfincs_map.nc (59521254 B)
- `D:\ELKAK\implementation\mandra_sfincs_enhanced\model\`: precip_2d.nc (64092 B, 6a122ae3b10a)
- `D:\ELKAK\implementation\mandra_sfincs_enhanced\data\`: imerg_mandra.nc (77996 B, 11eb246e8b09), imerg_mandra.raw.nc (81298 B, fc53a3e2ac6e)
- `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\`: sfincs.inp (1614 B, 66e48c788124), precip_2d.nc (193372 B, abb981e2f4f2), sfincs_map.nc (179898560 B)
- `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\data\`: imerg_valencia.nc (367080 B, 8bd9f12cfa12), imerg_valencia.raw.nc (369614 B, 8faee5162261)
- `D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\`: sfincs.inp (1614 B, 66e48c788124), precip_2d.nc (193372 B, c42bee92ea85), sfincs_map.nc (181959003 B)
- Also read (text, grep only, outside this script): `hydromt.log` and `sfincs.log` in each of the four model folders listed above (setup_precip_forcing_from_grid.* lines; process list), and `D:\ELKAK\.claude\skills\sfincs-flood-reproduction\scripts\bias_correct_imerg.py` (the rule for `incl`). sfincs_map.nc was read for `msk`, `x`, `y` only.
