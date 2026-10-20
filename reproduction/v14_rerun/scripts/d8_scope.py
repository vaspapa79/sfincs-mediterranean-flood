"""CODE-15 A (2026-10-20) — D8 source-point scope, no model runs. For every R3-on event (Pineios, Strymonas, Valencia, Emilia;
the canonical v1.4 run config of each) and every named point: YAML coordinate -> GloFAS cell chosen by the +-0.1 deg max-mean
rule (lon/lat, river, peak) -> model cell where the source is injected (lon/lat, z_b, active?) -> the lowest-z_b active channel
cell within 1 km of the YAML (injection) point. Flags: (i) the GloFAS cell belongs to another river, (ii) two points share a
cell, (iii) the injection cell is inactive or off-channel, (iv) the GloFAS window is clipped by the file edge; plus (v) the
GloFAS cell is nested upstream of another point's cell (its discharge counted twice) and (vi) the injection point drains to
another river than the one named.

River membership is decided on the GloFAS v4 network itself (CEMS static maps: upstream area + local drain direction, 0.05 deg;
reproduction/v14_rerun/scripts/glofas_network.py), not by eye: every named river is anchored by one reference cell (listed in
RIVER_REFS, chosen from the river's course), and a cell belongs to that river when it lies on the reference cell's main stem
upstream or on its course downstream before a larger river joins (an upstream-area step > x2). The frozen Pineios file is an
Open-Meteo 0.1 deg lattice whose longitudes are offset by one 0.05 deg cell from the static maps and the EWDS grid
(lattice_shift_test: 0 inconsistent river/dry points with the +1-column mapping against 12 + 7 with the containing cell);
its coordinates are mapped with that offset. The model-grid part (injection cell, lowest-z_b active cell within 1 km, local
channel) uses the run's own dep/msk and a D8 network of the Copernicus DEM on the model grid (pyflwdir) for the local thalweg
("channel cell" = D8 upstream area >= half the largest within 1 km).

Usage: python -I d8_scope.py --repo <worktree> [--static-dir D:/ELKAK/implementation/v14/_static/glofas_v4] [--out-dir ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

V14 = Path("D:/ELKAK/implementation/v14")
STATIC_DEFAULT = V14 / "_static" / "glofas_v4"
SNAP_RADIUS_M = 1000.0
DEM_PAD_M = 30000.0
PATH_MAX_M = 60000.0
CHANNEL_FRACTION = 0.5

EVENTS = [("pineios", "pineios_enhanced_v141"), ("strymonas", "strymonas_enhanced_postD6"),
          ("valencia", "valencia_enhanced_164"), ("emilia", "emilia_enhanced_8aoi")]
EXTRA_POINTS = {"strymonas": [{"name": "kerkini_outlet@v1_prefix_src", "lon": 23.2, "lat": 41.08}]}
# Open-Meteo lattice files: the discharge of lattice point (lon, lat) is that of the static-map cell containing (lon + 0.05, lat)
LATTICE_LON_OFFSET = {"pineios": 0.05}
# one reference cell per named river (static-map cell centres), chosen on the river's course; membership is then computed
RIVER_REFS = {
    "Pineios": [(22.425, 39.725), (21.875, 39.525)], "Titarisios": (22.275, 39.725), "Enipeas": (22.375, 39.325), "Lithaios": (21.775, 39.575),
    "Strymonas": (23.375, 41.025), "Angitis": (23.925, 40.975),
    "Jucar": (-0.325, 39.175), "Magro": (-0.575, 39.275), "Turia": (-0.525, 39.525),
    "Lamone": (11.975, 44.325), "Senio": (11.775, 44.325), "Santerno": (11.725, 44.325), "Marzeno": (11.875, 44.225),
    "Montone": (11.975, 44.175), "Ronco": (12.075, 44.125), "Savio": (12.175, 44.075),
}
NAMED_RIVER = {"pineios_trikala": "Pineios", "pineios_kalambaka": "Pineios", "titarisios": "Titarisios", "enipeas": "Enipeas",
               "kerkini_outlet": "Strymonas", "kerkini_outlet@v1_prefix_src": "Strymonas", "angitis": "Angitis",
               "magro": "Magro", "jucar": "Jucar", "turia": "Turia",
               "lamone": "Lamone", "senio": "Senio", "montone": "Montone", "ronco": "Ronco", "savio": "Savio"}


# ----------------------------------------------------------------------------------------------------------------- terrain
def dem_on_model_grid(dem_dir: Path, epsg: int, bounds, res: float, pad_m: float):
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    x0, y0, x1, y1 = bounds[0] - pad_m, bounds[1] - pad_m, bounds[2] + pad_m, bounds[3] + pad_m
    w, h = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    T = from_origin(x0, y1, res, res)
    dst = np.full((h, w), np.nan, dtype=np.float32)
    tiles = sorted(p for p in dem_dir.glob("*.tif"))
    for t in tiles:
        with rasterio.open(t) as s:
            tmp = np.full((h, w), np.nan, dtype=np.float32)
            reproject(rasterio.band(s, 1), tmp, dst_transform=T, dst_crs=f"EPSG:{epsg}", dst_nodata=np.nan, src_nodata=s.nodata, resampling=Resampling.average)
            m = np.isfinite(tmp)
            dst[m] = tmp[m]
    return dst, T, [t.name for t in tiles]


def cell_centres(T, shape):
    rows, cols = np.indices(shape)
    return T.c + (cols + 0.5) * T.a, T.f + (rows + 0.5) * T.e


# ----------------------------------------------------------------------------------------------------------------- main
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--static-dir", type=Path, default=STATIC_DEFAULT)
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = a.out_dir or (repo / "reproduction" / "v14_rerun" / "code15")
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    sys.path.insert(0, str(repo / "reproduction" / "v14_rerun" / "scripts"))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    import pyflwdir
    import pyproj
    import rasterio
    from rasterio.transform import rowcol
    from _common import load_config
    import prep_q_at_outlets as pq
    from glofas_network import GlofasNetwork, lattice_shift_test, river_cells

    net = GlofasNetwork(a.static_dir)
    refs = {name: net.cell(*(ll[0] if isinstance(ll, list) else ll)) for name, ll in RIVER_REFS.items()}      # primary (most downstream) reference
    members = {}
    for name, ll in RIVER_REFS.items():
        members[name] = set()
        for one in (ll if isinstance(ll, list) else [ll]):
            members[name] |= set(river_cells(net, net.cell(*one)))

    def rivers_of(cell) -> list[str]:
        return [name for name, cells in members.items() if tuple(cell) in cells]

    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "snap_radius_m": SNAP_RADIUS_M, "confluence_ratio": 2.0,
           "channel_fraction_of_max_uparea_within_radius": CHANNEL_FRACTION, "static_maps": str(a.static_dir),
           "river_references": {k: {"reference_cells": (v if isinstance(v, list) else [v]), "uparea_km2": round(net.uparea(refs[k]), 1), "n_cells": len(members[k])} for k, v in RIVER_REFS.items()},
           "main_stem_share": 2.0 / 3.0,
           "lattice_lon_offset_deg": LATTICE_LON_OFFSET, "events": []}
    md = ["| event | point | YAML coordinate (sampling; injection) | GloFAS cell by the ±0.1° max-mean rule: file coord → network cell, river [uparea km²], peak m³/s (window / file) | injection model cell: (lon, lat), z_b m, msk | lowest-z_b active channel cell within 1 km of the YAML point: (lon, lat), z_b m, distance m | flags |",
          "|---|---|---|---|---|---|---|"]
    for event, run in EVENTS:
        cfgp = repo / "reproduction" / "v14_rerun" / "configs" / f"{run}.yaml"
        cfg = load_config(["--config", str(cfgp)])
        work = V14 / run
        gf = work / "data" / f"glofas_{cfg.event_slug}_clean.nc"
        da = pq.open_glofas(gf)
        la = np.asarray(da.latitude.values, dtype=float); lo = np.asarray(da.longitude.values, dtype=float)
        step = float(round(abs(lo[1] - lo[0]), 3))
        off = LATTICE_LON_OFFSET.get(event, 0.0)
        mmap = np.asarray(da.mean("time").values, dtype=float); mmap = np.where(np.isfinite(mmap), mmap, 0.0)
        lattice_lons = {round(float(v), 3) for v in lo}; lattice_lats = {round(float(v), 3) for v in la}

        def net_cell(file_lon, file_lat):
            return net.cell(float(file_lon) + off, float(file_lat))

        def file_coord(cell):
            """File coordinate carrying this network cell, or None when the file (lattice) does not contain it."""
            clon, clat = net.centre(cell)
            if off:
                cand = [x for x in lattice_lons if net.cell(x + off, clat) == tuple(cell)]
                candy = [y for y in lattice_lats if net.cell(clon, y) == tuple(cell)]
                return [cand[0], candy[0]] if cand and candy else None
            return [clon, clat] if (clon in lattice_lons and clat in lattice_lats) else None

        shift = lattice_shift_test(net, da) if off else None
        with rasterio.open(work / "model" / "gis" / "dep.tif") as s:
            dep = s.read(1).astype(float); T = s.transform; res = float(s.res[0]); bounds = tuple(s.bounds)
        with rasterio.open(work / "model" / "gis" / "msk.tif") as s:
            msk = s.read(1).astype(float)
        dem, Td, tiles = dem_on_model_grid(work / "data" / "copdem30", cfg.epsg, bounds, res, DEM_PAD_M)
        flw = pyflwdir.from_dem(data=dem, nodata=np.nan, transform=Td, latlon=False)
        uparea = flw.upstream_area(unit="km2")
        xs, ys = cell_centres(T, dep.shape); xd, yd = cell_centres(Td, dem.shape)
        to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True); to_ll = pyproj.Transformer.from_crs(cfg.epsg, 4326, always_xy=True)
        active = (msk == 1) & np.isfinite(dep)
        r_off = int(round((Td.f - T.f) / res)); c_off = int(round((T.c - Td.c) / res))
        up_model = uparea[r_off:r_off + dep.shape[0], c_off:c_off + dep.shape[1]]
        assert up_model.shape == dep.shape

        pts = list(cfg.upstream_q["src_points"]) + EXTRA_POINTS.get(event, [])
        try:
            df, rep = pq.sample_points(da, pts, cfg.tref, cfg.tstop)
            sampled = {p["name"]: p for p in rep["points"]}
        except pq.NoChannelError as e:
            sampled = {}; rep = {"error": str(e)}
        ev = {"event": event, "run_config": str(cfgp.relative_to(repo)), "glofas_file": str(gf), "glofas_lattice_step_deg": step, "lattice_lon_offset_deg": off,
              "lattice_shift_test": shift, "glofas_extent": {"lon": [float(lo.min()), float(lo.max())], "lat": [float(la.min()), float(la.max())]},
              "model": {"epsg": cfg.epsg, "res_m": res, "shape": list(dep.shape), "zmax": cfg.raw.get("grid", {}).get("zmax"), "active_cells": int(active.sum())},
              "dem": {"tiles": tiles, "pad_m": DEM_PAD_M}, "sampler_duplicates": rep.get("duplicate_cells", []), "points": []}
        rule_cells = {}
        for sp in pts:
            name = sp["name"]; lon, lat = float(sp["lon"]), float(sp["lat"])
            ilon, ilat = float(sp.get("src_lon", lon)), float(sp.get("src_lat", lat))
            half = float(sp.get("window_deg", pq.WINDOW_HALF_DEG))
            named = NAMED_RIVER.get(name, "?")
            P = {"name": name, "named_river": named, "yaml": {"lon": lon, "lat": lat, "src_lon": ilon, "src_lat": ilat, "window_deg": half}}
            # ---- the named point on the network
            p0 = net.cell(lon, lat)
            first_river = net.first_river_cell(p0)
            P["named_point_network"] = {"cell": list(net.centre(p0)), "uparea_km2": round(net.uparea(p0), 1), "rivers_at_point": rivers_of(p0),
                                        "first_river_cell_downstream": (list(net.centre(first_river)) if first_river else None),
                                        "first_river_uparea_km2": (round(net.uparea(first_river), 1) if first_river else None),
                                        "first_river_names": (rivers_of(first_river) if first_river else [])}
            own_last = net.last_cell_before_larger_river(refs[named]) if named in refs else None
            own_in_file = None
            if named in refs:
                chain = river_cells(net, refs[named])
                for c in reversed(chain):
                    fc = file_coord(c)
                    if fc is not None:
                        i_ = int(np.argmin(np.abs(la - fc[1]))); j_ = int(np.argmin(np.abs(lo - fc[0])))
                        own_in_file = {"network_cell": list(net.centre(c)), "uparea_km2": round(net.uparea(c), 1), "file_coord": fc,
                                       "mean_m3s": round(float(mmap[i_, j_]), 2), "peak_file_m3s": round(float(np.nan_to_num(da.isel(latitude=i_, longitude=j_).values).max()), 2)}
                        break
            P["named_river_own_last_cell"] = (list(net.centre(own_last)) + [round(net.uparea(own_last), 1)]) if own_last else None
            P["named_river_best_cell_in_file"] = own_in_file
            # ---- the rule cell
            s = sampled.get(name)
            if s:
                fc = tuple(s["cell_lonlat"]); nc = net_cell(*fc)
                P["glofas_rule_cell"] = {"file_coord": list(fc), "network_cell": list(net.centre(nc)), "uparea_km2": round(net.uparea(nc), 1), "rivers": rivers_of(nc),
                                         "window_cells": s["window_cells"], "mean_m3s": s["cell_mean_m3s"], "peak_file_m3s": s["cell_peak_m3s"],
                                         "peak_in_window_m3s": s["column_peak_m3s"], "mean_in_window_m3s": s["column_mean_m3s"],
                                         "relation_to_the_point_drainage": net.classify_rule_cell((lon, lat), (fc[0] + off, fc[1]))["relation"],
                                         "is_named_river": (named in rivers_of(nc))}
                rule_cells.setdefault(nc, []).append(name)
            else:
                P["glofas_rule_cell"] = {"error": rep.get("error")}
            clipped = {"west": lon - half < lo.min() - 1e-4, "east": lon + half > lo.max() + 1e-4, "south": lat - half < la.min() - 1e-4, "north": lat + half > la.max() + 1e-4}
            P["glofas_window"] = {"clipped": any(clipped.values()), "sides": [k for k, v in clipped.items() if v]}
            try:
                ser1, cell1, n1 = pq.select_window_cell(da, lon, lat, 0.05)
                nc1 = net_cell(*cell1)
                P["glofas_one_cell_window"] = {"file_coord": list(cell1), "network_cell": list(net.centre(nc1)), "uparea_km2": round(net.uparea(nc1), 1), "rivers": rivers_of(nc1),
                                               "n": n1, "mean_m3s": round(float(ser1.mean()), 2), "peak_file_m3s": round(float(ser1.max()), 2)}
            except pq.NoChannelError as e:
                P["glofas_one_cell_window"] = {"error": str(e)}
            # ---- the injection cell on the model grid
            xi, yi = to_utm.transform(ilon, ilat)
            r0, c0 = (int(v) for v in rowcol(T, xi, yi))
            inb = 0 <= r0 < dep.shape[0] and 0 <= c0 < dep.shape[1]
            dist = np.hypot(xs - xi, ys - yi); within = dist <= SNAP_RADIUS_M
            up_max_1km = float(np.nanmax(np.where(within, up_model, np.nan))) if within.any() else float("nan")
            rd, cd = (int(v) for v in rowcol(Td, xi, yi))
            inj = {"row_col": [r0, c0], "in_grid": bool(inb), "cell_lonlat": ([round(v, 4) for v in to_ll.transform(xs[r0, c0], ys[r0, c0])] if inb else None),
                   "zb_m": (round(float(dep[r0, c0]), 2) if inb and np.isfinite(dep[r0, c0]) else None),
                   "dem_m": (round(float(dem[rd, cd]), 1) if np.isfinite(dem[rd, cd]) else None),
                   "msk": (None if not inb or not np.isfinite(msk[r0, c0]) else int(msk[r0, c0])),
                   "uparea_km2": (round(float(up_model[r0, c0]), 2) if inb else None), "max_uparea_within_1km_km2": round(up_max_1km, 2)}
            inj["active"] = inj["msk"] == 1
            inj["on_channel"] = bool(inb and up_max_1km > 0 and up_model[r0, c0] >= CHANNEL_FRACTION * up_max_1km)
            pi = net.cell(ilon, ilat); fri = net.first_river_cell(pi)
            path_i = net.path_down(pi)
            inj["drains_to"] = {"first_river_cell": (list(net.centre(fri)) if fri else None), "uparea_km2": (round(net.uparea(fri), 1) if fri else None), "rivers": (rivers_of(fri) if fri else []),
                                "rivers_at_injection_cell": rivers_of(pi),
                                "reaches_named_river": (named in refs and any(c in members[named] for c in path_i)),
                                "first_referenced_river_on_path": next((rivers_of(c) for c in path_i if rivers_of(c)), [])}
            P["injection_cell"] = inj
            cand = active & within
            if cand.any():
                k = int(np.argmin(np.where(cand, dep, np.inf))); rr, cc = np.unravel_index(k, dep.shape)
                P["lowest_zb_active_within_1km"] = {"row_col": [int(rr), int(cc)], "cell_lonlat": [round(v, 4) for v in to_ll.transform(xs[rr, cc], ys[rr, cc])], "zb_m": round(float(dep[rr, cc]), 2),
                                                    "distance_m": round(float(dist[rr, cc])), "uparea_km2": round(float(up_model[rr, cc]), 2),
                                                    "on_channel": bool(up_model[rr, cc] >= CHANNEL_FRACTION * up_max_1km), "n_active_within_1km": int(cand.sum())}
                chan = cand & (up_model >= CHANNEL_FRACTION * up_max_1km)
                k2 = int(np.argmin(np.where(chan, dep, np.inf))); r2, c2 = np.unravel_index(k2, dep.shape)
                P["lowest_zb_active_channel_within_1km"] = {"row_col": [int(r2), int(c2)], "cell_lonlat": [round(v, 4) for v in to_ll.transform(xs[r2, c2], ys[r2, c2])], "zb_m": round(float(dep[r2, c2]), 2),
                                                            "distance_m": round(float(dist[r2, c2])), "uparea_km2": round(float(up_model[r2, c2]), 2), "n_channel_cells": int(chan.sum())}
            else:
                P["lowest_zb_active_within_1km"] = None; P["lowest_zb_active_channel_within_1km"] = None
            kn = int(np.argmin(np.where(active, dist, np.inf))); rn, cn = np.unravel_index(kn, dep.shape)
            P["nearest_active_cell"] = {"cell_lonlat": [round(v, 4) for v in to_ll.transform(xs[rn, cn], ys[rn, cn])], "zb_m": round(float(dep[rn, cn]), 2), "distance_m": round(float(dist[rn, cn]))}
            n5 = int(math.ceil(500.0 / res)); rs, re_ = max(0, rd - n5), min(dem.shape[0], rd + n5 + 1); cs, ce = max(0, cd - n5), min(dem.shape[1], cd + n5 + 1)
            win = uparea[rs:re_, cs:ce]; kk = int(np.argmax(win)); r_s, c_s = rs + kk // win.shape[1], cs + kk % win.shape[1]
            paths, _ = flw.path(idxs=[np.ravel_multi_index((r_s, c_s), dem.shape)], max_length=PATH_MAX_M, unit="m")
            entry = None
            pth = np.asarray(paths[0])
            dcum = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(xd.flat[pth]), np.diff(yd.flat[pth])))]) if pth.size > 1 else np.array([0.0])
            for k in range(pth.size):
                rr, cc = np.unravel_index(pth[k], dem.shape); rm, cm = rr - r_off, cc - c_off
                if 0 <= rm < dep.shape[0] and 0 <= cm < dep.shape[1] and active[rm, cm]:
                    entry = {"cell_lonlat": [round(v, 4) for v in to_ll.transform(xs[rm, cm], ys[rm, cm])], "zb_m": round(float(dep[rm, cm]), 2), "path_distance_m": round(float(dcum[k])), "uparea_km2": round(float(up_model[rm, cm]), 2)}
                    break
            P["first_active_cell_on_dem_path_from_injection_point"] = entry
            ev["points"].append(P)
        # ---- flags
        for P in ev["points"]:
            flags = []
            g = P["glofas_rule_cell"]; named = P["named_river"]
            if "network_cell" in g:
                nc = net.cell(*g["network_cell"])
                others = [n for n in rule_cells.get(nc, []) if n != P["name"]]
                if others:
                    flags.append(f"(ii) shares the GloFAS cell with {', '.join(others)}")
                if not g["is_named_river"]:
                    flags.append(f"(i) GloFAS cell is not on the {named}: it is on {', '.join(g['rivers']) or 'no referenced river'} [{g['uparea_km2']} km²]; {g['relation_to_the_point_drainage']}")
                for nc2, names2 in rule_cells.items():
                    if nc2 != nc and net.is_downstream(nc, nc2):
                        flags.append(f"(v) nested: drains into the GloFAS cell of {', '.join(names2)} {list(net.centre(nc2))} — counted again there")
            if P["glofas_window"]["clipped"]:
                flags.append(f"(iv) window clipped by the file edge ({', '.join(P['glofas_window']['sides'])})")
            inj = P["injection_cell"]
            if not inj["active"]:
                flags.append("(iii) injection cell inactive" + (" (outside the grid)" if not inj["in_grid"] else f" (msk {inj['msk']}, DEM {inj['dem_m']} m)"))
            elif not inj["on_channel"]:
                flags.append(f"(iii) injection cell off-channel (D8 upstream area {inj['uparea_km2']} vs {inj['max_uparea_within_1km_km2']} km² within 1 km)")
            dr = inj["drains_to"]
            if named in refs and not dr["reaches_named_river"]:
                flags.append(f"(vi) the injection point never drains through the {named}: its path reaches {', '.join(dr['first_referenced_river_on_path']) or 'no referenced river'} first (first river cell {dr['first_river_cell']}, {dr['uparea_km2']} km²)")
            if P["lowest_zb_active_within_1km"] is None:
                flags.append("no active cell within 1 km of the YAML point (v1.4.2 snap: hard error)")
            P["flags"] = flags
            lz = P["lowest_zb_active_channel_within_1km"]
            gtxt = (f"({g['file_coord'][0]}, {g['file_coord'][1]}) → ({g['network_cell'][0]}, {g['network_cell'][1]}), {', '.join(g['rivers']) or 'no referenced river'} [{g['uparea_km2']}]; {g['peak_in_window_m3s']} / {g['peak_file_m3s']}" if "network_cell" in g else f"ERROR {g.get('error')}")
            zb_txt = str(inj["zb_m"]) if inj["zb_m"] is not None else "— (DEM " + str(inj["dem_m"]) + ")"
            itxt = (f"({inj['cell_lonlat'][0]}, {inj['cell_lonlat'][1]}) z_b {zb_txt}, msk {inj['msk']}" if inj["in_grid"] else "outside the grid")
            if lz:
                ltxt = f"({lz['cell_lonlat'][0]}, {lz['cell_lonlat'][1]}) z_b {lz['zb_m']}, {lz['distance_m']} m [D8 {lz['uparea_km2']} km²]"
            else:
                e = P["first_active_cell_on_dem_path_from_injection_point"]
                ltxt = f"none — nearest active cell {P['nearest_active_cell']['distance_m']} m away" + (f"; the DEM channel path enters the active domain after {e['path_distance_m']} m at ({e['cell_lonlat'][0]}, {e['cell_lonlat'][1]})" if e else "")
            y = P["yaml"]
            ytxt = f"({y['lon']}, {y['lat']}); " + ("same" if (y["src_lon"], y["src_lat"]) == (y["lon"], y["lat"]) else f"({y['src_lon']}, {y['src_lat']})")
            md.append(f"| {event} | {P['name']} | {ytxt} | {gtxt} | {itxt} | {ltxt} | {'; '.join(flags) if flags else '—'} |")
        out["events"].append(ev)
        print(f"{event}: " + "; ".join(f"{P['name']}: {len(P['flags'])}" for P in ev["points"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "d8_scope.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    head = [f"# D8 source-point scope (CODE-15 A) — generated {out['utc']} by `reproduction/v14_rerun/scripts/d8_scope.py` (no model runs)", "",
            "Per named point of the four R3-on events (canonical v1.4 run configs): YAML coordinate → GloFAS cell chosen by the ±0.1° max-mean rule (the v1.4.1 sampler), as the file coordinate and as the "
            "GloFAS v4 network cell it stands for, with the river(s) that cell belongs to and its upstream area, and its peak (simulated window tref..tstop, step-filled / whole file) → model cell where the "
            "source is injected (centre, z_b from the model dep, msk: 1 active, 2 water-level boundary, None inactive) → the lowest-z_b active (msk = 1) channel cell within 1 km of the YAML injection point "
            "(channel = D8 upstream area on the Copernicus DEM ≥ half the largest within 1 km; the JSON also holds the plain lowest active cell). River membership is computed on the GloFAS v4 static maps "
            "(upstream area + drain direction): one reference cell per named river, a cell belongs to the river when it lies on the reference's main stem upstream or on its course downstream before a "
            "larger river joins (upstream-area step > ×2). The frozen Pineios file is an Open-Meteo lattice whose longitudes are offset by one 0.05° cell from the static maps / EWDS grid "
            "(`lattice_shift_test` in the JSON); its coordinates are mapped with that offset. Flags: (i) cell not on the named river, (ii) shared cell, (iii) injection inactive / off-channel, "
            "(iv) window clipped by the file edge, (v) nested (counted again in another point's cell), (vi) the injection point drains to another river.", ""]
    (out_dir / "d8_scope.md").write_text("\n".join(head + md) + "\n", encoding="utf-8")
    print("wrote", out_dir / "d8_scope.json", out_dir / "d8_scope.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
