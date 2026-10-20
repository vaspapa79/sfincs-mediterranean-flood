# Reference-data (truth) uncertainty — B3

EMS SAR positional spec used for the polygon buffer: **±20 m** (upper bound of the ~10–20 m Sentinel-1 positional uncertainty informing the EMS interpretation; manuscript Sec 3.5). All from stored `sfincs_map.nc` + EMS polygons (no SFINCS re-run). Strymonas scored vs the author-reference output (0.183/0.328).

## (a) Polygon positional uncertainty — CSI range

The observed EMS extent is eroded / dilated by ~the EMS positional spec (±20 m). Because that distance is sub-grid (cells 50–150 m), the buffer is applied in the raster domain: obs is rasterised onto a ~20 m fine grid, eroded/dilated by one fine cell, then down-sampled to the model grid (any-sub-cell-wet rule), and scored strict h>0.10 m on the canonical mask. The CSI range is the band attributable to truth-polygon position; it is **much smaller** than the Sec 8 AOI-mask ±1 km band (which moves the evaluation domain, not the truth boundary).

| Event | CSI erode −20 m | CSI metric (0) | CSI dilate +20 m | CSI range (±half) |
|---|--:|--:|--:|--:|
| Pineios EMSR692 (v1 enhanced) | 0.441 | 0.456 | 0.465 | 0.441–0.465 (±0.012) |
| Strymonas EMSR122 (v3) | 0.176 | 0.183 | 0.183 | 0.176–0.183 (±0.003) |
| Mandra EMSR257 (v1 enhanced) | 0.056 | 0.106 | 0.137 | 0.056–0.137 (±0.041) |

## (b) EMS acquisition vs modelled peak

EMS product type + SAR/optical acquisition datetime (UTC) per observed product, vs the modelled time of peak flooded area / peak depth from `sfincs_map.nc`.

### Pineios EMSR692 (v1 enhanced)
- Modelled sim window: 2023-09-03 00:00 → 2023-09-11 00:00 UTC
- **Modelled peak flooded area**: 2023-09-05 02:00 UTC (3567.4 km²); peak max-depth: 2023-09-10 10:00 UTC (60.73 m)

| Observed product | Type | AOI | Sensor | Acquisition (UTC) | Offset peak−acq |
|---|---|---|---|---|--:|
| EMSR692_AOI01_DEL_MONIT01_v3 | DELINEATION-MONIT | AOI01 | Sentinel-1 | 2023-09-06 04:39 | -26.7 h (-1.1 d) |
| EMSR692_AOI01_DEL_MONIT02_v4 | DELINEATION-MONIT | AOI01 | Sentinel-1 | 2023-09-07 16:24 | -62.4 h (-2.6 d) |
| EMSR692_AOI01_DEL_MONIT03_v3 | DELINEATION-MONIT | AOI01 | WorldView-3 | 2023-09-09 09:31 | -103.5 h (-4.3 d) |
| EMSR692_AOI05_DEL_MONIT01_v2 | DELINEATION-MONIT | AOI05 | GeoEye-1 | 2023-09-11 09:42 | -151.7 h (-6.3 d) |
| EMSR692_AOI03_DEL_MONIT01_v3 | DELINEATION-MONIT | AOI03 | SPOT-6-7 | 2023-09-12 08:53 | -174.9 h (-7.3 d) |
| EMSR692_AOI04_DEL_MONIT01_v3 | DELINEATION-MONIT | AOI04 | SPOT-6-7 | 2023-09-12 08:53 | -174.9 h (-7.3 d) |
| EMSR692_AOI05_DEL_MONIT02_v3 | DELINEATION-MONIT | AOI05 | SPOT-6-7 | 2023-09-12 08:54 | -174.9 h (-7.3 d) |
| EMSR692_AOI02_DEL_MONIT01_v3 | DELINEATION-MONIT | AOI02 | SPOT-6-7 | 2023-09-12 08:54 | -174.9 h (-7.3 d) |
| EMSR692_AOI02_DEL_MONIT02_v2 | DELINEATION-MONIT | AOI02 | SPOT-6-7 | 2023-09-14 08:38 | -222.6 h (-9.3 d) |
| EMSR692_AOI03_DEL_MONIT02_v2 | DELINEATION-MONIT | AOI03 | SPOT-6-7 | 2023-09-14 08:38 | -222.6 h (-9.3 d) |
| EMSR692_AOI04_DEL_MONIT02_v2 | DELINEATION-MONIT | AOI04 | SPOT-6-7 | 2023-09-14 08:38 | -222.6 h (-9.3 d) |
| EMSR692_AOI05_DEL_MONIT03_v3 | DELINEATION-MONIT | AOI05 | WorldView-3 | 2023-09-14 09:16 | -223.3 h (-9.3 d) |
| EMSR692_AOI02_DEL_MONIT03_v3 | DELINEATION-MONIT | AOI02 | SPOT-6-7 | 2023-09-15 09:19 | -247.3 h (-10.3 d) |
| EMSR692_AOI03_DEL_MONIT03_v2 | DELINEATION-MONIT | AOI03 | SPOT-6-7 | 2023-09-15 09:19 | -247.3 h (-10.3 d) |
| EMSR692_AOI03_DEL_MONIT04_v2 | DELINEATION-MONIT | AOI03 | SPOT-6-7 | 2023-09-17 09:04 | -295.1 h (-12.3 d) |
| EMSR692_AOI04_DEL_MONIT03_v3 | DELINEATION-MONIT | AOI04 | SPOT-6-7 | 2023-09-17 09:04 | -295.1 h (-12.3 d) |
| EMSR692_AOI02_DEL_MONIT04_v2 | DELINEATION-MONIT | AOI02 | SPOT-6-7 | 2023-09-17 09:05 | -295.1 h (-12.3 d) |
| EMSR692_AOI05_DEL_MONIT04_v2 | DELINEATION-MONIT | AOI05 | SPOT-6-7 | 2023-09-17 09:05 | -295.1 h (-12.3 d) |
| EMSR692_AOI05_DEL_MONIT05_v2 | DELINEATION-MONIT | AOI05 | WorldView-2 | 2023-09-18 10:08 | -320.1 h (-13.3 d) |
| EMSR692_AOI03_DEL_MONIT05_v2 | DELINEATION-MONIT | AOI03 | WorldView-2 | 2023-09-19 09:33 | -343.6 h (-14.3 d) |
| EMSR692_AOI04_DEL_MONIT04_v2 | DELINEATION-MONIT | AOI04 | WorldView-2 | 2023-09-19 09:33 | -343.6 h (-14.3 d) |
| EMSR692_AOI02_DEL_MONIT05_v2 | DELINEATION-MONIT | AOI02 | WorldView-2 | 2023-09-19 09:34 | -343.6 h (-14.3 d) |
| EMSR692_AOI06_DEL_MONIT01_v3 | DELINEATION-MONIT | AOI06 | GeoEye-1 | 2023-09-22 09:46 | -415.8 h (-17.3 d) |
| EMSR692_AOI07_DEL_MONIT01_v2 | DELINEATION-MONIT | AOI07 | GeoEye-1 | 2023-09-22 09:46 | -415.8 h (-17.3 d) |

Acquisitions span 2023-09-06 04:39 → 2023-09-22 09:46 (16.2 d, 19 overpass time(s)). Modelled peak is -26.7 h (-1.1 d) from the **first** overpass. Note: the observed extent is a union over these acquisitions, so a single model-snapshot offset is only indicative.

### Strymonas EMSR122 (v3)
- Modelled sim window: 2015-03-28 00:00 → 2015-04-04 00:00 UTC
- **Modelled peak flooded area**: 2015-03-28 13:00 UTC (100.6 km²); peak max-depth: 2015-03-28 13:00 UTC (5.57 m)

| Observed product | Type | AOI | Sensor | Acquisition (UTC) | Offset peak−acq |
|---|---|---|---|---|--:|
| EMSR122_01STRYMONAS_DELINEATION_OVERVIEW-MONIT01_v2 | DELINEATION-MONIT | 01STRYMONAS | Sentinel-1 (DELINEATION) | 2015-03-29 00:00 | -11.0 h (-0.5 d) |
| EMSR122_02BALTOTOPI_DELINEATION_OVERVIEW-MONIT01_v1 | DELINEATION-MONIT | 02BALTOTOPI | Sentinel-1 (DELINEATION) | 2015-03-29 00:00 | -11.0 h (-0.5 d) |
| EMSR122_03ACHINOS_DELINEATION_OVERVIEW-MONIT01_v2 | DELINEATION-MONIT | 03ACHINOS | Sentinel-1 (DELINEATION) | 2015-03-29 00:00 | -11.0 h (-0.5 d) |
| EMSR122_04MAVROTHALASSA_DELINEATION_OVERVIEW-MONIT01_v2 | DELINEATION-MONIT | 04MAVROTHALASSA | Sentinel-1 (DELINEATION) | 2015-03-29 00:00 | -11.0 h (-0.5 d) |
| EMSR122_03ACHINOS_DELINEATION_OVERVIEW-MONIT02_v1 | DELINEATION-MONIT | 03ACHINOS | Sentinel-1 (DELINEATION) | 2015-04-01 00:00 | -83.0 h (-3.5 d) |
| EMSR122_04MAVROTHALASSA_DELINEATION_OVERVIEW-MONIT02_v1 | DELINEATION-MONIT | 04MAVROTHALASSA | Sentinel-1 (DELINEATION) | 2015-04-01 00:00 | -83.0 h (-3.5 d) |
| EMSR122_01STRYMONAS_DELINEATION_OVERVIEW-MONIT03_v1 | DELINEATION-MONIT | 01STRYMONAS | Sentinel-1 (DELINEATION) | 2015-04-02 00:00 | -107.0 h (-4.5 d) |

Acquisitions span 2015-03-29 00:00 → 2015-04-02 00:00 (4.0 d, 3 overpass time(s)). Modelled peak is -11.0 h (-0.5 d) from the **first** overpass. Note: the observed extent is a union over these acquisitions, so a single model-snapshot offset is only indicative.

### Mandra EMSR257 (v1 enhanced)
- Modelled sim window: 2017-11-13 00:00 → 2017-11-18 00:00 UTC
- **Modelled peak flooded area**: 2017-11-15 05:00 UTC (223.0 km²); peak max-depth: 2017-11-17 14:00 UTC (20.19 m)

| Observed product | Type | AOI | Sensor | Acquisition (UTC) | Offset peak−acq |
|---|---|---|---|---|--:|
| EMSR257_01MANDRA_02GRADING_MAP_v2 | GRADING | 01MANDRA | Pleiades-1A-1B | 2017-11-20 09:41 | -124.7 h (-5.2 d) |
| EMSR257_02NEAPERAMOS_02GRADING_MAP_v2 | GRADING | 02NEAPERAMOS | Pleiades-1A-1B | 2017-11-20 09:41 | -124.7 h (-5.2 d) |
| EMSR257_03LAKKAKALOGIROU_02GRADING_MAP_v1 | GRADING | 03LAKKAKALOGIROU | Pleiades-1A-1B | 2017-11-20 09:41 | -124.7 h (-5.2 d) |

Acquisitions span 2017-11-20 09:41 → 2017-11-20 09:41 (0.0 d, 1 overpass time(s)). Modelled peak is -124.7 h (-5.2 d) from the **first** overpass. Note: the observed extent is a union over these acquisitions, so a single model-snapshot offset is only indicative.

## (c) all_touched=True extent inflation (V4 disclosure)

Polygons are burned with `all_touched=True` (any cell the polygon touches is set wet), which enlarges both the observed extent and the AOI mask by up to ~half a cell along each boundary vs centroid rasterisation (`all_touched=False`). For Methods disclosure:

| Event | cell (m) | obs wet aT=T (km²) | aT=F (km²) | obs inflation | AOI aT=T (km²) | aT=F (km²) | AOI inflation |
|---|--:|--:|--:|--:|--:|--:|--:|
| Pineios EMSR692 (v1 enhanced) | 150 | 1518.840 | 1290.375 | +17.7% | 4642.3 | 4630.6 | +0.3% |
| Strymonas EMSR122 (v3) | 150 | 106.582 | 70.043 | +52.2% | 1222.7 | 1215.3 | +0.6% |
| Mandra EMSR257 (v1 enhanced) | 50 | 8.988 | 4.942 | +81.8% | 109.7 | 108.2 | +1.4% |

The inflation scales with the perimeter-to-area ratio: largest (relative) for the small, fragmented GRADING/observed extents and smaller for the broad AOI masks. This is a known, disclosed bias in the validation rasterisation (finding V4); it affects all runs identically and slightly favours hit rate over FAR.
