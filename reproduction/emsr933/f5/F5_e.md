# F5-e: inverse-barometer response at the SFINCS open boundary (facts only)
Generated 2026-10-09 13:33 UTC by `f5_e_ib.py` from existing outputs; no model was re-run. IB = -dp/(rho g), rho = 1025.0 kg/m3, g = 9.81 m/s2; references: first forcing step, 1013.25 hPa, gapres from sfincs.inp. SFINCS writes `zs` = NaN where a cell is dry (verified per run, row 'NaN = dry check'). Every number below is copied from `F5_e.json`.

## Run 1: Pineios / Storm Daniel (EMSR692) enhanced, model_author_ref
| Item | Value |
|---|---|
| sfincs.inp keywords present | baro=1, pavbnd=1, gapres=101200.0, zsini=0, rhow=1024.0, tspinup=0.0, tref=20230827 000000, tstart=20230903 000000, tstop=20230911 000000, epsg=32634, netampfile=press_2d.nc, netamuamvfile=wind_2d.nc, netamprfile=precip_2d.nc |
| sfincs.inp keywords ABSENT | bndfile, bzsfile, bzifile, netbndbzsbzifile |
| water-level boundary file (bnd/bzs/bzi) | exists in folder: False (matching files: none); sfincs_map.nc `inp` attrs: bndfile=none, bzsfile=none, bzifile=none, netbndbzsbzifile=none, bndtype=1, pavbnd=1.0, baro=1 |
| SFINCS run log | Warning! Boundary cells found in mask without boundary points from bnd file. Setting water level at 0.0 m at mask boundary cells.; Wind                 : yes; Atmospheric pressure : yes; Precipitation        : yes |
| mask counts | msk=1: 261815, msk=2: 650, msk=3: 0, msk=0: 94511 (active 262465 of 356976) |
| map output / NaN = dry check | 193 steps, 2023-09-03T00:00 to 2023-09-11T00:00, step 3600.0 s; at t0 finite msk=1 cells = 131, msk=1 cells with zb<0 = 131, identical sets: True |
| msk=2 cells: zb (m), wet/dry | zb min 0.0, mean 0.0, max 0.0 (0 cells zb<0, 650 cells zb=0; 650 on outer grid edge); cells ever wet (finite zs): 0, never wet: 650; output times with all msk=2 NaN: 193 of 193 |
| msk=2 zsmax (maximum over each dtmaxout = 86400 s window, 8 windows) | finite 0 of 5200 cell-windows; min None, max None m |
| zs at msk=2 cells (m) | NaN at every cell and every output time (no wet boundary cell at any output hour); first/min/max/time-of-min/max undefined; deviation from initial undefined (upper bound: level <= zb at all times) |
| MSLP forcing file | press_2d.nc: `barometric_pressure` [Pa], 6x6 nodes, EPSG 32634 (model EPSG 32634), dx 23774.36 m, dy -23774.36 m, source msl regular_ll 0.25 deg; 193 steps, time axis identical to map: True, NaNs 0; forcing nodes span x 555696.46-674568.27, y 4325542.19-4444414.01 m vs model grid x 571682.0-671582.0, y 4351515.0-4431915.0 m ('domain minimum' below = over the forcing nodes) |
| MSLP domain minimum (hPa) | first 1017.69 -> min 1006.4 at 2023-09-05T02:00 (x=674568.27, y=4325542.19), max 1018.53; expected IB 0.112 m rel. first, 0.068 m rel. 1013.25, 0.056 m rel. gapres 1012.0 |
| MSLP mean at msk=2 locations (hPa) | first 1018.01 -> min 1007.76 at 2023-09-05T03:00, max 1018.83 (6 forcing nodes, nearest-node distance 3061.37-16315.05 m, same CRS); expected IB 0.102 m rel. first, 0.055 m rel. 1013.25, 0.042 m rel. gapres |
| observed dzs at msk=2 at MSLP min (2023-09-05T03:00) | wet cells at t: 0 of 650; dzs wet-cell mean None m, cellwise mean/min/max None/None/None m, largest-excursion cell None m; run-wide mean dzs range [None, None] m; expected 0.102 m (rel. first) / 0.055 m (rel. 1013.25) |
| first interior row (msk=1 cells touching msk=2) | 654 cells, zb 0.0..0.0 m; wet at t0 0, at MSLP min 654; zs at MSLP min: wet-mean 0.02 m, cellwise 0.01..0.203 m; dzs vs t0 (cells wet at both) mean/min/max None/None/None m (0 cells > 1 cm); wet-mean zs series min 0.0 (2023-09-03T20:00), max 0.0316 (2023-09-07T12:00) m; expected local IB rel. first mean 0.102 m |
| interior sea cells (msk=1 & zb<0) at MSLP min | 131 cells, zb -2.908..-0.002 m, wet at t: 131; dzs wet-mean 0.864 m, cellwise mean/min/max 0.864/0.373/1.809 m (131 cells > 1 cm); expected local IB rel. first mean 0.1 m (min 0.1, max 0.11); wet-mean zs series first 0.0, min -0.0 (2023-09-03T20:00), max 1.1707 (2023-09-07T13:00) m, i.e. +58.0 h relative to the MSLP min, when boundary MSLP was 1018.11 hPa (expected IB -0.001 m) |
| 6-hourly checkpoints (t: boundary MSLP hPa / expected IB m / first-row wet-mean zs m (wet cells) / interior-sea wet-mean zs m) | 2023-09-03T12:00: 1017.44 / 0.006 / None (0) / 0.0; 2023-09-04T00:00: 1012.85 / 0.051 / 0.006 (654) / 0.005; 2023-09-04T12:00: 1013.03 / 0.049 / 0.011 (654) / 0.473; 2023-09-05T00:00: 1008.5 / 0.095 / 0.014 (654) / 0.778 (full list in JSON) |
| pavbnd acted at the boundary (per data)? | False: all 650 msk==2 cells have zb = 0.0 m and zs = NaN (dry) at all 193 hourly outputs; zsmax NaN in all 5200 cell-windows (never wet within any dtmaxout = 86400 s window). The imposed boundary level therefore never exceeded 0.0 m, while the IB expected at the MSLP minimum is 0.102 m (rel. first step) / 0.055 m (rel. 1013.25 hPa). |

## Run 2a: Valencia (EMSR773) as-run, NHESS/runs/valencia_emsr773/model
| Item | Value |
|---|---|
| sfincs.inp keywords present | baro=1, pavbnd=1, gapres=101200.0, zsini=0, rhow=1024.0, tspinup=0.0, tref=20241024 000000, tstart=20241027 000000, tstop=20241101 000000, epsg=32630, netampfile=press_2d.nc, netamuamvfile=wind_2d.nc, netamprfile=precip_2d.nc |
| sfincs.inp keywords ABSENT | bndfile, bzsfile, bzifile, netbndbzsbzifile |
| water-level boundary file (bnd/bzs/bzi) | exists in folder: False (matching files: none); sfincs_map.nc `inp` attrs: bndfile=none, bzsfile=none, bzifile=none, netbndbzsbzifile=none, bndtype=1, pavbnd=1.0, baro=1 |
| SFINCS run log | Warning! Boundary cells found in mask without boundary points from bnd file. Setting water level at 0.0 m at mask boundary cells.; Wind                 : yes; Atmospheric pressure : yes; Precipitation        : yes |
| mask counts | msk=1: 520194, msk=2: 1233, msk=3: 0, msk=0: 152214 (active 521427 of 673641) |
| map output / NaN = dry check | 121 steps, 2024-10-27T00:00 to 2024-11-01T00:00, step 3600.0 s; at t0 finite msk=1 cells = 12207, msk=1 cells with zb<0 = 12207, identical sets: True |
| msk=2 cells: zb (m), wet/dry | zb min -1.347, mean -0.019, max 0.0 (21 cells zb<0, 1212 cells zb=0; 1233 on outer grid edge); cells ever wet (finite zs): 21, never wet: 1212; output times with all msk=2 NaN: 0 of 121 |
| msk=2 zsmax (maximum over each dtmaxout = 86400 s window, 5 windows) | finite 105 of 6165 cell-windows; min 0.0, max 0.0 m |
| zs at wet msk=2 cells (m) | mean: first 0.0 (2024-10-27T00:00), min 0.0 (2024-10-27T00:00), max 0.0 (2024-10-27T00:00); largest-excursion cell n=0, m=616, x=741565.0, y=4324474.0, zb=-1.133: first 0.0, min 0.0 (2024-10-27T00:00), max 0.0 (2024-10-27T00:00), range 0.0; max abs dev from initial 0.0 m; differs > 1 cm: False; all finite values exactly 0: True |
| MSLP forcing file | press_2d.nc: `barometric_pressure` [Pa], 6x7 nodes, EPSG 32630 (model EPSG 32630), dx 24371.81 m, dy -24371.81 m, source msl regular_ll 0.25 deg; 121 steps, time axis identical to map: True, NaNs 0; forcing nodes span x 654905.84-776764.88, y 4288839.73-4435070.58 m vs model grid x 679915.0-764015.0, y 4324424.0-4404524.0 m ('domain minimum' below = over the forcing nodes) |
| MSLP domain minimum (hPa) | first 1014.97 -> min 1011.15 at 2024-10-29T17:00 (x=654905.84, y=4288839.73), max 1020.83; expected IB 0.038 m rel. first, 0.021 m rel. 1013.25, 0.008 m rel. gapres 1012.0 |
| MSLP mean at msk=2 locations (hPa) | first 1015.27 -> min 1012.43 at 2024-10-30T03:00, max 1021.7 (5 forcing nodes, nearest-node distance 6224.84-16801.49 m, same CRS); expected IB 0.028 m rel. first, 0.008 m rel. 1013.25, -0.004 m rel. gapres |
| observed dzs at msk=2 at MSLP min (2024-10-30T03:00) | wet cells at t: 21 of 1233; dzs wet-cell mean 0.0 m, cellwise mean/min/max 0.0/0.0/0.0 m, largest-excursion cell 0.0 m; run-wide mean dzs range [0.0, 0.0] m; expected 0.028 m (rel. first) / 0.008 m (rel. 1013.25) |
| first interior row (msk=1 cells touching msk=2) | 1241 cells, zb -1.386..0.67 m; wet at t0 26, at MSLP min 1241; zs at MSLP min: wet-mean 0.011 m, cellwise -0.009..0.68 m; dzs vs t0 (cells wet at both) mean/min/max 0.006/-0.009/0.117 m (2 cells > 1 cm); wet-mean zs series min 0.0 (2024-10-27T00:00), max 0.0258 (2024-10-30T23:00) m; expected local IB rel. first mean 0.028 m |
| interior sea cells (msk=1 & zb<0) at MSLP min | 12207 cells, zb -12.735..-0.0 m, wet at t: 12207; dzs wet-mean 2.523 m, cellwise mean/min/max 2.523/-0.055/6.397 m (12117 cells > 1 cm); expected local IB rel. first mean 0.024 m (min 0.009, max 0.03); wet-mean zs series first -0.0, min -0.0 (2024-10-27T00:00), max 2.7451 (2024-10-29T22:00) m, i.e. -5.0 h relative to the MSLP min, when boundary MSLP was 1012.84 hPa (expected IB 0.024 m) |
| 6-hourly checkpoints (t: boundary MSLP hPa / expected IB m / first-row wet-mean zs m (wet cells) / interior-sea wet-mean zs m) | 2024-10-27T12:00: 1016.78 / -0.015 / 0.007 (1241) / 0.017; 2024-10-28T00:00: 1018.74 / -0.034 / 0.011 (1241) / 0.033; 2024-10-28T12:00: 1019.88 / -0.046 / 0.011 (1241) / 0.048; 2024-10-29T00:00: 1020.14 / -0.048 / 0.009 (1241) / 0.059 (full list in JSON) |
| pavbnd acted at the boundary (per data)? | False: 21 of 1233 msk==2 cells are wet; their zs is exactly 0.0 at every output time (max |dzs| from initial 0.0 m); zsmax at the wet cells min 0.0 / max 0.0 m over every dtmaxout = 86400 s window, versus expected IB 0.028 m (rel. first) / 0.008 m (rel. 1013.25 hPa). |

## Run 2b: Valencia (EMSR773) 164-mm re-run, R1_verification/task_valencia_anchor/rerun_v164/model
| Item | Value |
|---|---|
| sfincs.inp keywords present | baro=1, pavbnd=1, gapres=101200.0, zsini=0, rhow=1024.0, tspinup=0.0, tref=20241024 000000, tstart=20241027 000000, tstop=20241101 000000, epsg=32630, netampfile=press_2d.nc, netamuamvfile=wind_2d.nc, netamprfile=precip_2d.nc |
| sfincs.inp keywords ABSENT | bndfile, bzsfile, bzifile, netbndbzsbzifile |
| water-level boundary file (bnd/bzs/bzi) | exists in folder: False (matching files: none); sfincs_map.nc `inp` attrs: bndfile=none, bzsfile=none, bzifile=none, netbndbzsbzifile=none, bndtype=1, pavbnd=1.0, baro=1 |
| SFINCS run log | Warning! Boundary cells found in mask without boundary points from bnd file. Setting water level at 0.0 m at mask boundary cells.; Wind                 : yes; Atmospheric pressure : yes; Precipitation        : yes |
| mask counts | msk=1: 520194, msk=2: 1233, msk=3: 0, msk=0: 152214 (active 521427 of 673641) |
| map output / NaN = dry check | 121 steps, 2024-10-27T00:00 to 2024-11-01T00:00, step 3600.0 s; at t0 finite msk=1 cells = 12207, msk=1 cells with zb<0 = 12207, identical sets: True |
| msk=2 cells: zb (m), wet/dry | zb min -1.347, mean -0.019, max 0.0 (21 cells zb<0, 1212 cells zb=0; 1233 on outer grid edge); cells ever wet (finite zs): 21, never wet: 1212; output times with all msk=2 NaN: 0 of 121 |
| msk=2 zsmax (maximum over each dtmaxout = 86400 s window, 5 windows) | finite 105 of 6165 cell-windows; min 0.0, max 0.0 m |
| zs at wet msk=2 cells (m) | mean: first 0.0 (2024-10-27T00:00), min 0.0 (2024-10-27T00:00), max 0.0 (2024-10-27T00:00); largest-excursion cell n=0, m=616, x=741565.0, y=4324474.0, zb=-1.133: first 0.0, min 0.0 (2024-10-27T00:00), max 0.0 (2024-10-27T00:00), range 0.0; max abs dev from initial 0.0 m; differs > 1 cm: False; all finite values exactly 0: True |
| MSLP forcing file | press_2d.nc: `barometric_pressure` [Pa], 6x7 nodes, EPSG 32630 (model EPSG 32630), dx 24371.81 m, dy -24371.81 m, source msl regular_ll 0.25 deg; 121 steps, time axis identical to map: True, NaNs 0; forcing nodes span x 654905.84-776764.88, y 4288839.73-4435070.58 m vs model grid x 679915.0-764015.0, y 4324424.0-4404524.0 m ('domain minimum' below = over the forcing nodes) |
| MSLP domain minimum (hPa) | first 1014.97 -> min 1011.15 at 2024-10-29T17:00 (x=654905.84, y=4288839.73), max 1020.83; expected IB 0.038 m rel. first, 0.021 m rel. 1013.25, 0.008 m rel. gapres 1012.0 |
| MSLP mean at msk=2 locations (hPa) | first 1015.27 -> min 1012.43 at 2024-10-30T03:00, max 1021.7 (5 forcing nodes, nearest-node distance 6224.84-16801.49 m, same CRS); expected IB 0.028 m rel. first, 0.008 m rel. 1013.25, -0.004 m rel. gapres |
| observed dzs at msk=2 at MSLP min (2024-10-30T03:00) | wet cells at t: 21 of 1233; dzs wet-cell mean 0.0 m, cellwise mean/min/max 0.0/0.0/0.0 m, largest-excursion cell 0.0 m; run-wide mean dzs range [0.0, 0.0] m; expected 0.028 m (rel. first) / 0.008 m (rel. 1013.25) |
| first interior row (msk=1 cells touching msk=2) | 1241 cells, zb -1.386..0.67 m; wet at t0 26, at MSLP min 1241; zs at MSLP min: wet-mean 0.009 m, cellwise -0.009..0.68 m; dzs vs t0 (cells wet at both) mean/min/max 0.002/-0.009/0.029 m (2 cells > 1 cm); wet-mean zs series min 0.0 (2024-10-27T00:00), max 0.0127 (2024-11-01T00:00) m; expected local IB rel. first mean 0.028 m |
| interior sea cells (msk=1 & zb<0) at MSLP min | 12207 cells, zb -12.735..-0.0 m, wet at t: 12207; dzs wet-mean 1.712 m, cellwise mean/min/max 1.712/-0.032/5.87 m (12116 cells > 1 cm); expected local IB rel. first mean 0.024 m (min 0.009, max 0.03); wet-mean zs series first -0.0, min -0.0 (2024-10-27T00:00), max 1.7299 (2024-10-30T06:00) m, i.e. +3.0 h relative to the MSLP min, when boundary MSLP was 1013.72 hPa (expected IB 0.015 m) |
| 6-hourly checkpoints (t: boundary MSLP hPa / expected IB m / first-row wet-mean zs m (wet cells) / interior-sea wet-mean zs m) | 2024-10-27T12:00: 1016.78 / -0.015 / 0.007 (1241) / 0.017; 2024-10-28T00:00: 1018.74 / -0.034 / 0.011 (1241) / 0.033; 2024-10-28T12:00: 1019.88 / -0.046 / 0.011 (1241) / 0.048; 2024-10-29T00:00: 1020.14 / -0.048 / 0.009 (1241) / 0.059 (full list in JSON) |
| pavbnd acted at the boundary (per data)? | False: 21 of 1233 msk==2 cells are wet; their zs is exactly 0.0 at every output time (max |dzs| from initial 0.0 m); zsmax at the wet cells min 0.0 / max 0.0 m over every dtmaxout = 86400 s window, versus expected IB 0.028 m (rel. first) / 0.008 m (rel. 1013.25 hPa). |
| identity with Run 2a (md5) | byte-identical files: ['sfincs.inp', 'press_2d.nc']; sfincs_map.nc differs (181959003 vs 179898560 bytes) |

## Files read (read-only; sizes and md5 in F5_e.json)
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\sfincs.inp`
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\sfincs_log.txt`
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\sfincs_map.nc`
- `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\press_2d.nc`
- `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\sfincs.inp`
- `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\sfincs_log.txt`
- `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\sfincs_map.nc`
- `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\press_2d.nc`
- `D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\sfincs.inp`
- `D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\sfincs_stdout.txt`
- `D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\sfincs_map.nc`
- `D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\press_2d.nc`
- Inspected manually before scripting (no numbers taken from them): `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\hydromt.log`, `D:\ELKAK\implementation\pineios_sfincs_enhanced\model_author_ref\sfincs.src`, `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\hydromt.log`, `D:\ELKAK\ELKAK2\NHESS\runs\valencia_emsr773\model\sfincs.src`, `D:\ELKAK\ELKAK2\NHESS\R1_verification\task_valencia_anchor\rerun_v164\model\sfincs.src`
