# EMSR933 input-data availability — window 2026-09-27 … 2026-10-07

Checked 2026-10-09T12:51:44Z (`data_availability_20261009T125144Z.json`); ERA5T probe `era5t_probe_20261009T125219Z.json`. bbox W,S,E,N = [23.4, 34.8, 26.4, 35.7].

| input | product | status for the window | evidence |
|---|---|---|---|
| precipitation (R1) | IMERG **Late** Run V07 half-hourly `GPM_3IMERGHHL` | 528/528 granules; suffix V07C; per day [48] | CMR search; first `3B-HHR-L.MS.MRG.3IMERG.20260927-S000000-E002959.0000.V07C.HDF5` |
| precipitation (R1) | IMERG **Final** Run V07 `GPM_3IMERGHH` | 0/528 granules | CMR search |
| meteo (baseline rain, R6 wind/MSLP) | ERA5 single levels (CDS) | requestable 2026-09-27 … 2026-10-03; **not yet: 2026-10-04, 2026-10-05, 2026-10-06, 2026-10-07**; catalogue extent end 2026-10-03T00:00:00+00:00 | CDS constraints + catalogue |
| ERA5 vs ERA5T | expver per day | 2026-09-27: 0005; 2026-09-28: 0005; 2026-09-29: 0005; 2026-09-30: 0005; 2026-10-01: 0005; 2026-10-02: 0005; 2026-10-03: 0005 | one-point retrieval |
| upstream Q (R3, if triggered) | GloFAS v4 `intermediate` (EWDS) | 2026-09-27 … 2026-10-06 | EWDS constraints |
| | GloFAS v4 `consolidated` / v5 | none for Sep–Oct 2026 | EWDS constraints |
| | pipeline request vocabulary (`hyear/hmonth`) | REJECTED HTTP 422: b'{"type":"invalid pa… | EWDS constraints |
| DEM | Copernicus GLO-30 (AWS) | N34E023:200, N34E024:200, N34E025:200, N34E026:200, N35E023:200, N35E024:200, N35E025:200, N35E026:200 | HTTP HEAD |
| land cover | ESA WorldCover 2021 v200 (AWS) | _N33E021:200, _N33E024:200 | HTTP HEAD |
