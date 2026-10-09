
---

## 8. EMSR933 Crete (CODE-10) — prospective held-out event, PROVISIONAL (activation open)
Append-only ledger for the third held-out event; every value is generated from the JSON records named in
`reproduction/emsr933/` by `reproduction/emsr933/scripts/stage0_summary.py` (nothing retyped). Provisional until the
Stage-5 final-products cut-off.

### EMSR933 Crete — Stage 0 provenance (CODE-10, prospective held-out event)
Branch `emsr933-crete` (worktree `.worktrees/emsr933-crete`, base v1.3.0 `ccd423a`), commit `6a5e64b`. Records in `reproduction/emsr933/`.
- EMS API snapshot **2026-10-09T12:47:20Z** = provisional truth cut-off: `ems_api_snapshot_20261009T124720Z.json` (31606 B, sha256 `0aa29458ad5eae8449a0b28d4ab386a4104e180b9f05ca5f0cb919f2077f6b94`); API `https://mapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR933`.
- Activation (from snapshot JSON): eventTime `2026-10-01T07:00:00` UTC, activationTime `2026-10-04T11:02:00` UTC, Flood/Flash flood, closed=False.
- Released packages at the cut-off (6; product id · post-event source per package `source_v1` · observed km² union EPSG:32634):
  - AOI01 Kastelli DEL_MONIT01 id 2962 · Legion 06/10/2026 T10:47:00Z (1.2 m) · obs 0.242 km² (88 polys; {"Flood trace": 0.1438, "Flooded area": 0.0982}) · zip sha256 `bbe7fe84c5f21fdf…`
  - AOI03 Tzermiado DEL id 2955 · Sentinel-1 04/10/2026 T16:22:00Z (20.0 m) · obs 3.2192 km² (13 polys; {"Flooded area": 3.2192}) · zip sha256 `14789be38b4ded67…`
  - AOI03 Tzermiado DEL_MONIT02 id 2959 · GeoEye-1 08/10/2026 T09:02:00Z (2.0 m) · obs 3.7807 km² (618 polys; {"Flood trace": 1.2533, "Flooded area": 2.5274}) · zip sha256 `07ae2fb6f7f1bf0c…`
  - AOI04 Agios Ioannis DEL_MONIT01 id 2957 · WorldView-3 06/10/2026 T10:46:00Z (1.6 m) · obs 0.0325 km² (30 polys; {"Flood trace": 0.0325}) · zip sha256 `24339cffc56c67fe…`
  - AOI06 Agios Nikolaos DEL_MONIT01 id 2960 · Legion 08/10/2026 T08:55:00Z (2.0 m) · obs 0.0593 km² (11 polys; {"Flood trace": 0.0575, "Not Applicable": 0.0017}) · zip sha256 `a989df1406ee5f90…`
  - AOI07 Omalos DEL_MONIT01 id 2964 · Legion 06/10/2026 T10:45:00Z (1.6 m) · obs 0.0506 km² (63 polys; {"Flooded area": 0.0506}) · zip sha256 `4e1f5386648915e6…`
  - Not released: AOI01 DEL N; AOI02 DEL N; AOI02 DEL_MONIT01 N; AOI03 DEL_MONIT01 N; AOI03 GRA I; AOI04 DEL N; AOI05 DEL N; AOI05 DEL_MONIT01 N; AOI06 DEL N; AOI07 DEL N; AOI08 DEL N; AOI08 DEL_MONIT01 N
- Availability (2026-10-09T12:51:44Z): IMERG Late V07 528/528 (V07C); IMERG Final 0; ERA5 requestable to 2026-10-03 (ERA5T per probe: 2026-09-27=0005, 2026-09-28=0005, 2026-09-29=0005, 2026-09-30=0005, 2026-10-01=0005, 2026-10-02=0005, 2026-10-03=0005); GloFAS v4 intermediate to 2026-10-06.
- Preflight 2026-10-09T12:44:09Z: OK (hydromt 0.10.1, hydromt_sfincs 1.2.2, numpy 2.4.6, GDAL 3.12.2).
