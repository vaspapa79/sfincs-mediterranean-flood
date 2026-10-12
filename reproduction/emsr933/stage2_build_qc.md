# EMSR933 Crete — build QC (CODE-12 Part C, no forcing, no run), 2026-10-12T10:07:01Z

Model: `D:\ELKAK\implementation\emsr933_crete\buildqc\model` — grid 2771 x 1107 = 3,067,497 cells @ 100 m (EPSG:32634); GAP-1 = A (100 m island-wide), GAP-2 z_max = 2500 m; tref/tstart/tstop 2026-09-21 00:00:00 / 2026-09-28 00:00:00 / 2026-10-06 00:00:00.

| quantity | value |
|---|---|
| active cells (msk >= 1) | 3,067,497 (30,675.0 km²) |
| msk = 1 interior / msk = 2 water-level boundary / msk = 3 | 3,059,745 / 7,752 / 0 |
| active cells with dep <= 0 m (GLO-30 sea plane) / > 0 m | 2,222,469 / 845,028 |
| dep range of active cells | -1.1 .. 2440.0 m |
| msk = 2 cells: dep range / cells at exactly 0 m | 0.00 .. 0.00 m / 7,752 |
| water-level bnd points (v1.4, every 10000 m) | 78 along ~775.2 km of msk = 2 cells; bzs = 0 m; pavbnd = 101325 Pa |
| subgrid file | 1949.9 MB, np 3,067,497, npuv 6,131,116, 10 levels |
| subgrid z_zmin min / p50 / max | -3.9 / 0.0 / 2431.8 m |
| subgrid z_zmax min / p50 / max | -1.0 / 0.0 / 2451.3 m |
| subgrid z_volmax p50 / max | 0 / 1693416 m³ |
| subgrid uv_navg (Manning) min / p50 / max | 0.012 / 0.020 / 0.100 |
| hydromt build log span (local time) | 2026-10-12 12:47:55 -> 2026-10-12 12:52:31 |

## Samaria-gorge GLO-30 pit at model resolution (characterised, NOT fixed)

| grid | area km² | cells | floor m | spill m | max depth m | volume below spill Mm³ | closed in dep? |
|---|---|---|---|---|---|---|---|
| GLO-30 @ 90 m (Stage 1) | 2.43 | 347 | 238.2 | 546.5 | 308.3 | 273.6 | yes |
| model dep @ 100 m | 2.56 | 256 | 235.9 | 556.1 | 320.2 | 296.6 | True |

Deepest 100-m cell 23.9609 E / 35.2829 N; subgrid z_zmin there: 228.5 m; 256 of 256 pit cells are active. closed depression in the model dep (filled surface > floor): rain-on-grid runoff reaching these cells ponds up to the spill level — SFINCS has no karst/sinkhole drainage; not modified (Part C: characterise only).
