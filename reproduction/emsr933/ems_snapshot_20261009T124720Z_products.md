# EMSR933 released-product metadata (snapshot 2026-10-09T12:47:20Z)

EMS eventTime 2026-10-01T07:00:00 UTC; lag = post-event acquisition − eventTime. Areas: union in EPSG:32634. Source of sensor/date: the package's own `source_v1` table (matched by observedEventA.dmg_src_id); identical to the API `images[]` record.

| AOI | product | id | post-event source (date, time, res.) | lag h | obs polygons | obs km² | by notation (km²) | event types | not-analysed km² | AOI km² | other layers |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 Kastelli | DEL_MONIT01 | 2962 | Legion 06/10/2026 T10:47:00Z (1.2 m) | 123.8 | 88 | 0.242 | {"Flood trace": 0.1438, "Flooded area": 0.0982} | 5-Flood | 45.298 | 252.53 | floodDepthA, imageFootprintA, modelledEventA, notAnalysedA |
| 03 Tzermiado | DEL | 2955 | Sentinel-1 04/10/2026 T16:22:00Z (20.0 m) | 81.4 | 13 | 3.2192 | {"Flooded area": 3.2192} | 5-Flood | 0.0 | 174.41 | floodDepthA, imageFootprintA, modelledEventA |
| 03 Tzermiado | DEL_MONIT02 | 2959 | GeoEye-1 08/10/2026 T09:02:00Z (2.0 m) | 170.0 | 618 | 3.7807 | {"Flood trace": 1.2533, "Flooded area": 2.5274} | 5-Flood | 0.0 | 174.41 | floodDepthA, imageFootprintA, maximumFloodExtentA, modelledEventA |
| 04 Agios Ioannis | DEL_MONIT01 | 2957 | WorldView-3 06/10/2026 T10:46:00Z (1.6 m) | 123.8 | 30 | 0.0325 | {"Flood trace": 0.0325} | 5-Flood | 0.0 | 59.26 | imageFootprintA |
| 06 Agios Nikolaos | DEL_MONIT01 | 2960 | Legion 08/10/2026 T08:55:00Z (2.0 m) | 169.9 | 11 | 0.0593 | {"Flood trace": 0.0575, "Not Applicable": 0.0017} | 5-Flood, 6-Mass Movement | 0.0 | 116.18 | imageFootprintA |
| 07 Omalos | DEL_MONIT01 | 2964 | Legion 06/10/2026 T10:45:00Z (1.6 m) | 123.8 | 63 | 0.0506 | {"Flooded area": 0.0506} | 5-Flood | 30.047 | 266.31 | floodDepthA, imageFootprintA, modelledEventA, notAnalysedA |

Not released at the snapshot:

- AOI01 Kastelli DEL (id 2948): status N — Because of remote sensing limitations; image Sentinel-1 2026-10-04T16:22:00
- AOI02 Irakleio DEL (id 2952): status N — Because of remote sensing limitations; image Sentinel-1 2026-10-04T16:22:00
- AOI02 Irakleio DEL_MONIT01 (id 2963): status N — Because of remote sensing limitations; image Legion 2026-10-06T10:47:00
- AOI03 Tzermiado DEL_MONIT01 (id 2956): status N — Because of no change of situation detected; image Sentinel-1 2026-10-05T04:23:00
- AOI03 Tzermiado GRA (id 2965): status I; expected 2026-10-09T21:00:00; image Legion 2026-10-09T09:32:00
- AOI04 Agios Ioannis DEL (id 2949): status N — Because of remote sensing limitations; image ICEYE 2026-10-04T23:16:00
- AOI05 Anogeia DEL (id 2951): status N — Because of remote sensing limitations; image Sentinel-1 2026-10-04T16:22:00
- AOI05 Anogeia DEL_MONIT01 (id 2961): status N — Because of remote sensing limitations; image GeoEye-1 2026-10-08T09:48:00
- AOI06 Agios Nikolaos DEL (id 2950): status N — Because of remote sensing limitations; image Sentinel-1 2026-10-05T04:23:00
- AOI07 Omalos DEL (id 2954): status N — Because of remote sensing limitations; image Sentinel-1 2026-10-04T16:21:00
- AOI08 Monastiraki DEL (id 2953): status N — Because of remote sensing limitations; image ICEYE 2026-10-04T23:16:00
- AOI08 Monastiraki DEL_MONIT01 (id 2958): status N — Because of remote sensing limitations; image WorldView-3 2026-10-06T10:46:00
