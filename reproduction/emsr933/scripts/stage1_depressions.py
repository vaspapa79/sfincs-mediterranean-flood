"""CODE-10 Stage 1a addendum — closed depressions per AOI, resolved into connected components.

The aggregate depression statistics in stage1_terrain.py mix the karst poljes (Lasithi/Tzermiado,
Omalos) with deep but tiny pits in gorges (GLO-30 artefacts). Here every connected region with
fill depth > 0.5 m inside each AOI box is labelled; the three largest by area are reported with
area, floor (lowest DEM), spill level (filled surface), max depth, storage volume below the spill
level, centroid, and the internal catchment draining to the region (region + upstream area at
its inlet cells in the depression-filled flow network). Same 90-m GLO-30 grid and sea masking as
stage1_terrain.py. Facts only.

Usage: python -I stage1_depressions.py --event-root D:/ELKAK/implementation/emsr933_crete --out-dir <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage1_terrain import (ISLAND, DECIM, read_dem, cell_area_km2, rasterize, rc_to_lonlat,  # noqa: E402
                            latest)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-root", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    import pyflwdir
    from scipy import ndimage
    from shapely import wkt as swkt

    t0 = dt.datetime.now(dt.timezone.utc)
    manifest = json.loads(latest(a.out_dir, "ems_snapshot_*_manifest.json").read_text(encoding="utf-8"))
    dem, transform, shape = read_dem(a.event_root / "data/copdem30/copdem30.vrt")
    carea2d = np.repeat(cell_area_km2(transform, shape)[:, None], shape[1], axis=1)
    land = np.isfinite(dem) & (dem > 0)
    dem_h = np.where(land, dem, -9999.0).astype("float32")
    filled, _ = pyflwdir.dem.fill_depressions(dem_h, nodata=-9999.0, max_depth=-1.0, outlets="edge")
    depth = np.where(land, filled - dem_h, 0.0)
    flw = pyflwdir.from_dem(data=dem_h, nodata=-9999.0, max_depth=-1.0, transform=transform,
                            latlon=True, outlets="edge")
    uparea = flw.upstream_area(unit="km2"); uparea = np.where(uparea < 0, np.nan, uparea).ravel()
    idxs_ds = flw.idxs_ds.astype(np.int64)
    landf = land.ravel()

    rep = {"utc": t0.strftime("%Y-%m-%dT%H:%M:%SZ"), "grid_m_approx": [round(transform.a * 111320 * np.cos(np.radians(35.25))), round(-transform.e * 111320)],
           "depth_threshold_m": 0.5, "aois": []}
    for ao in sorted(manifest["aois"], key=lambda x: x["number"]):
        m = rasterize(swkt.loads(ao["extent_wkt"]), transform, shape)
        lab, nlab = ndimage.label((depth > 0.5) & m & land, structure=np.ones((3, 3)))
        comps = []
        for i in range(1, nlab + 1):
            cm = lab == i
            area = float(carea2d[cm].sum())
            comps.append((area, i, cm))
        comps.sort(key=lambda t: -t[0])
        rows = []
        for area, i, cm in comps[:3]:
            d = depth[cm]; j = int(np.argmax(d)); rr, cc = np.where(cm)
            vol_m3 = float((d * carea2d[cm] * 1e6).sum())
            cmf = cm.ravel(); idx_out = np.where(~cmf & landf)[0]; ds_out = idxs_ds[idx_out]
            inl = idx_out[(ds_out != idx_out) & cmf[ds_out]]
            catch = area + float(np.nansum(uparea[inl]))
            r0, c0 = rr[j], cc[j]
            rows.append({"area_km2": round(area, 2), "max_depth_m": round(float(d.max()), 1),
                         "floor_m": round(float(dem[r0, c0]), 1), "spill_level_m": round(float(filled[r0, c0]), 1),
                         "volume_below_spill_Mm3": round(vol_m3 / 1e6, 1),
                         "deepest_cell_lonlat": rc_to_lonlat(transform, r0, c0),
                         "centroid_lonlat": rc_to_lonlat(transform, float(rr.mean()), float(cc.mean())),
                         "internal_catchment_km2": round(catch, 1), "n_inlets": int(inl.size),
                         "n_cells_90m": int(cm.sum())})
        rep["aois"].append({"number": ao["number"], "name": ao["name"], "n_components": int(nlab),
                            "total_km2_depth_gt_0p5": round(float(carea2d[(depth > 0.5) & m & land].sum()), 2),
                            "largest_components": rows})
    out = a.out_dir / "stage1_depressions.json"
    out.write_text(json.dumps(rep, indent=2, default=float), encoding="utf-8")
    L = [f"# EMSR933 Stage 1a — closed depressions per AOI (connected components, depth > 0.5 m), {rep['utc']}", "",
         "| AOI | name | n comp. | total km² | rank | area km² | floor m | spill m | max depth m | volume below spill Mm³ | internal catchment km² | centroid lon/lat |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rep["aois"]:
        for k, c in enumerate(r["largest_components"], 1):
            L.append(f"| {r['number']:02d} | {r['name']} | {r['n_components']} | {r['total_km2_depth_gt_0p5']} | {k} | {c['area_km2']} | "
                     f"{c['floor_m']} | {c['spill_level_m']} | {c['max_depth_m']} | {c['volume_below_spill_Mm3']} | {c['internal_catchment_km2']} | "
                     f"{c['centroid_lonlat'][0]}/{c['centroid_lonlat'][1]} |")
    (a.out_dir / "stage1_depressions.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L)); print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
