# as_run record — emsr122_sfincs_v3 (Strymonas, headline run)

Frozen record of the **canonical Strymonas headline run** behind the manuscript value
**CSI 0.183 / HR 0.328** (h > 0.10 m vs Copernicus EMS EMSR122). This is the `v3` run that
**fixes the Kerkini upstream-discharge source location** — without this fix the model reproduces
the *un-corrected* Strymonas (≈ CSI 0.170, peak depth ~12 m), **not** the headline.

Recovered 2026-06-12 from `implementation/emsr122_sfincs_v3/model/` and committed here to close
finding **R2** (see `docs/VALIDATION_FINDINGS.md`). Absolute paths below are frozen as-run records
from the author machine (`vaspapa`) — drive reproduction from `skill/examples/` via `prep_inputs.py`,
not from these files directly.

## The R2 src fix (the only delta from `emsr122_sfincs_enhanced`)

`src` **point 1 — kerkini_outlet** relocated; point 2 (angitis) unchanged.

| src point | `.orig` (broken) UTM34N | `v3` (fixed) UTM34N | lon/lat (fixed) |
|-----------|-------------------------|---------------------|-----------------|
| 1 kerkini | `684805.76 / 4549969.94` | `701692.00 / 4544737.00` | `23.3991 / 41.0289` |
| 2 angitis | `745591.46 / 4542864.67` | `745591.46 / 4542864.67` | `23.92 / 41.00` |

The fix moves the discharge injection off a 171 m DEM cell onto a ~12 m valley-floor cell,
which is why peak depth drops 12.2 m → 5.6 m and CSI rises 0.170 → 0.183.
The corresponding source edit is `skill/examples/emsr122_strymonas_enhanced.yaml`
`upstream_q.src_points[0].kerkini_outlet = {lon: 23.3991, lat: 41.0289}`.

## sfincs.inp excerpt (as run)

```
mmax = 690 ; nmax = 611 ; dx = dy = 150 ; x0 = 650467.0 ; y0 = 4495912.0
rotation = 0 ; epsg = 32634
tref = 20150321 000000 ; tstart = 20150328 000000 ; tstop = 20150404 000000
pavbnd = 1 ; baro = 1 ; gapres = 101200.0
scsfile = sfincs.scs   (SCS-CN infiltration, HSG=B, AMC=II)
srcfile = sfincs.src ; disfile = sfincs.dis   (upstream Q: kerkini + angitis)
netamprfile = precip_2d.nc (IMERG)   netampfile = press_2d.nc / netamuamvfile = wind_2d.nc (ERA5)
```

## Files in this record
- `sfincs_build.yml` — HydroMT build config (identical to `emsr122_sfincs_enhanced`; IMERG precip,
  ERA5 wind/MSLP, CN infiltration, `pavbnd: 1`).
- `data_catalog.yml` — data sources (copdem30, ESA WorldCover, ERA5, IMERG, GloFAS, CN raster).
- `sfincs.src` — the **two corrected** source coordinates (kerkini fixed, angitis unchanged).
