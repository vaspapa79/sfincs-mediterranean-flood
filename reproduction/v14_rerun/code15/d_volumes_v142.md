# Injected discharge vs rain / observed-flood volumes, harness v1.4.2 (CODE-15 D) — generated 2026-10-20T16:30:44Z by `reproduction/v14_rerun/scripts/d_volumes_v142.py`

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
