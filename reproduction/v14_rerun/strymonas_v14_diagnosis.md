# Strymonas v3 enhanced — v1.3 vs v1.4 water balance (2026-10-19T10:07:12Z)

Discharge (identical sfincs.dis/src in both: True): 452.6 Mm³ over the 14-day forcing window, 311.9 Mm³ inside the simulated week (Kerkini outlet / Angitis [261.8, 50.1]; peaks [640.34, 96.81] m³/s).

| quantity | v1.3 published | v1.4 |
|---|---|---|
| active cells | 207374 | 185824 |
| msk = 2 cells | 346 | 802 |
| max water volume on land zb > 0 (Mm³) | 52.5 | 314.8 |
| volume on the grid at the end (Mm³) | 33.4 | 330.2 |
| wet area h_max > 0.10 m (km²) | 145.3 | 313.5 |
| rain: domain mean / on land (mm, Mm³) | 97.1 / 436.0 | 48.6 / 218.0 |
| water on land, daily (Mm³) | [0.0, 23.2, 26.8, 22.5, 15.0, 12.7, 11.8, 10.9] | [0.0, 103.8, 187.7, 234.0, 267.8, 292.7, 307.8, 314.8] |
| depth at the pool centre (E 727.1, N 4535.0 km; zb 2.55 m), daily (m) | [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] | [0.0, 0.0, 0.55, 1.59, 2.12, 2.33, 2.41, 2.46] |
| end-of-run wet km² at zb 0–2 m | 10.9 | 40.7 |
| end-of-run wet km² at zb 2–5 m | 4.8 | 65.7 |
| end-of-run wet km² at zb 5–10 m | 4.3 | 50.4 |
| end-of-run wet km² at zb 10–20 m | 3.2 | 99.3 |

## Isolation experiments (copies of the models with one change; no scoring)

| experiment | change | V_land max / end (Mm³) | wet h > 0.10 m at the end (km²) | SFINCS s |
|---|---|---|---|---|
| E1_v14_zsini0 (base: strymonas_enhanced) | inp zsini=0 | 314.8 / 314.8 | 270.0 | 600.5 |
| E2_v14_publishedrain (base: strymonas_enhanced) | precip_2d.nc from emsr122_sfincs_v3 | 52.5 / 10.9 | 31.3 | 199.8 |
| E3_v13_zsini_dry (base: emsr122_sfincs_v3) | inp zsini=-9999 | 52.5 / 10.9 | 42.7 | 505.8 |
| E4_v13_plusIB (base: emsr122_sfincs_v3) | inp pavbnd=101325; inp bndfile=sfincs.bnd; inp bzsfile=sfincs.bzs; file sfincs.bnd from strymonas_enhanced; file sfincs.bzs from strymonas_enhanced | 52.5 / 10.9 | 45.2 | 179.4 |
| E5_v14_unalignedwindpress (base: strymonas_enhanced) | file press_2d.nc from emsr122_sfincs_v3; file wind_2d.nc from emsr122_sfincs_v3 | 314.8 / 314.8 | 265.7 | 204.0 |
| E6_v14_noIB (base: strymonas_enhanced) | inp pavbnd=1; inp drop bndfile; inp drop bzsfile | 314.8 / 314.8 | 265.5 | 212.1 |
