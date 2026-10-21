# Injected discharge vs rain / observed-flood volumes, harness v1.4.2 (CODE-15 D) — generated 2026-10-21T09:10:38Z by `reproduction/v14_rerun/scripts/d_volumes_v142.py`

Volumes over the simulated window (tstart..tstop); injected = trapezoid integral of the sfincs.dis columns SFINCS read; rain = netampr rates integrated per forcing cell and weighted by the active model area each forcing cell covers.

### pineios_enhanced — simulated window 2023-09-03 00:00 → 2023-09-11 00:00 UTC

| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |
|---|---|---|---|---|
| pineios_trikala | 11.59 | 11.59 | 8.01 | z_b None m, None m, None km² |
| pineios_kalambaka | 11.59 | 11.59 | 8.01 | z_b None m, None m, None km² |
| titarisios | 11.59 | 11.59 | 8.01 | z_b None m, None m, None km² |
| enipeas | 11.59 | 11.59 | 8.01 | z_b None m, None m, None km² |
| **total injected** | combined peak 46.36 | | **32.04** | |

Rain on the active domain (5033 km²) in the window: **2237.1 × 10⁶ m³** (mean depth 444 mm, max cell 872 mm; `precip_2d.nc`, 384 steps of 0.50 h). Injected / rain = **1.4 %**. Modelled flood (hmax > 0.1 m): 2790 km², 3491.4 × 10⁶ m³ of water standing at hmax.

### pineios_enhanced_v141 — simulated window 2023-09-03 00:00 → 2023-09-11 00:00 UTC

| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |
|---|---|---|---|---|
| pineios_trikala | 371.39 | 129.29 | 89.67 | z_b None m, None m, None km² |
| pineios_kalambaka | 2.10 | 1.07 | 0.74 | z_b None m, None m, None km² |
| titarisios | 1128.80 | 551.67 | 382.42 | z_b None m, None m, None km² |
| enipeas | 118.40 | 62.05 | 43.01 | z_b None m, None m, None km² |
| **total injected** | combined peak 1620.66 | | **515.84** | |

Rain on the active domain (5033 km²) in the window: **2237.1 × 10⁶ m³** (mean depth 444 mm, max cell 872 mm; `precip_2d.nc`, 384 steps of 0.50 h). Injected / rain = **23.1 %**. Modelled flood (hmax > 0.1 m): 2802 km², 3914.0 × 10⁶ m³ of water standing at hmax.

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

### strymonas_enhanced_postD6_v142 — simulated window 2015-03-28 00:00 → 2015-04-04 00:00 UTC

| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |
|---|---|---|---|---|
| kerkini_outlet | 640.34 | 432.42 | 261.84 | z_b 14.4 m, 451 m, 1.22 km² |
| angitis | 96.81 | 82.79 | 50.11 | z_b 19.11 m, 406 m, 155.23 km² |
| **total injected** | combined peak 737.15 | | **311.94** | |

Rain on the active domain (4181 km²) in the window: **23.9 × 10⁶ m³** (mean depth 6 mm, max cell 16 mm; `precip_2d.nc`, 336 steps of 0.50 h). Injected / rain = **1303.2 %**. Modelled flood (hmax > 0.1 m): 322 km², 416.8 × 10⁶ m³ of water standing at hmax.

### valencia_enhanced_164_v142 — simulated window 2024-10-27 00:00 → 2024-11-01 00:00 UTC

| source | injected peak m³/s | mean m³/s | volume 10⁶ m³ | injection cell (snap): z_b m, moved m, D8 km² |
|---|---|---|---|---|
| magro | 18.70 | 9.39 | 4.07 | z_b 274.67 m, 976 m, 5.69 km² |
| jucar | 88.81 | 58.41 | 25.28 | z_b 2.95 m, 961 m, 2183.77 km² |
| turia | 239.72 | 113.60 | 49.21 | z_b 109.69 m, 934 m, 6.07 km² |
| **total injected** | combined peak 347.23 | | **78.57** | |

Rain on the active domain (2981 km²) in the window: **313.1 × 10⁶ m³** (mean depth 105 mm, max cell 264 mm; `precip_2d.nc`, 240 steps of 0.50 h). Injected / rain = **25.1 %**. Modelled flood (hmax > 0.1 m): 1354 km², 1216.8 × 10⁶ m³ of water standing at hmax.
