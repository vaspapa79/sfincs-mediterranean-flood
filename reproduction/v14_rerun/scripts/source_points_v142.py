"""CODE-15 C (2026-10-20) — the harness v1.4.2 source-point ledger: for every R3-on event the resolved `upstream_q.src_points`
(sampling coordinate, per-point window, injection coordinate, inject flag), the GloFAS v4 network cell each one resolves to,
the reason for every change against the frozen v1.3/v1.4.1 points, and the UTC time of the resolution. phase1.py reads the
JSON to build the v1.4.2 run configs, so the ledger is the single source of the v1.4.2 configuration.

Decisions (D8 scope, code15/d8_scope.{json,md}):
  * authorised by CODE-15 B(1): a point whose +-0.1 deg window resolves to another river gets its own GloFAS cell — the named
    river's own last cell before a larger river joins (the pattern of the author's Titarisios prescription 22.24/39.71) with a
    window that isolates it: Titarisios (user-prescribed), Magro, Senio; Montone needs only a one-cell window.
  * B(2): the Pineios lattice is re-downloaded with the extended request area; Kalambaka's window is no longer clipped.
  * B(3)/(4): every injected point is snapped at build time (source_snap); duplicate GloFAS cells are a hard error.
  * forced by the data (reported, not in the brief): Kalambaka's cell (the Pineios at Kalambaka, 928 km2) lies upstream of the
    Trikala cell (2073 km2) on the same river — injecting both counts it twice — and its injection point has no channel of
    the Pineios within 1 km; it is sampled and recorded, not injected (inject: false). The Senio and Savio injection points
    drain to the Lamone and the Ronco (flag vi); their injection is moved to the named river's channel: the lowest-z_b active
    channel cell inside the footprint of the named river's GloFAS cell nearest to the old point (computed here on the run's
    DEM, same machinery as the pipeline snap).
Everything else keeps its frozen coordinates (the pipeline snap applies within 1 km).

Usage: python -I source_points_v142.py --repo <worktree> [--static-dir ...] [--out-dir reproduction/v14_rerun/code15]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

V14 = Path("D:/ELKAK/implementation/v14")
STATIC_DEFAULT = V14 / "_static" / "glofas_v4"
PINEIOS_EXT = V14 / "_seed" / "pineios" / "data" / "glofas_pineios.nc"
LATTICE_LON_OFFSET = {"pineios": 0.05}
EVENT_RUN = {"pineios": "pineios_enhanced_v141", "strymonas": "strymonas_enhanced_postD6", "valencia": "valencia_enhanced_164", "emilia": "emilia_enhanced_8aoi"}
EVENT_SLUG = {"pineios": "pineios", "strymonas": "strymonas", "valencia": "valencia", "emilia": "emilia_romagna"}

# the resolved points: frozen v1.3 points with the v1.4.2 changes; "move_injection_to_river_cell" is computed on the DEM below
RESOLVED = {
    "pineios": [
        {"name": "pineios_trikala", "lon": 21.77, "lat": 39.56, "src_lon": 21.86, "src_lat": 39.56,
         "change": "none (sampling + injection as frozen; the build-time snap applies)", "named_river": "Pineios"},
        {"name": "pineios_kalambaka", "lon": 21.63, "lat": 39.70, "src_lon": 21.86, "src_lat": 39.70, "inject": False,
         "change": "inject: false — the extended lattice gives the Pineios at Kalambaka (928 km2), nested upstream of the Trikala cell (2073 km2, same river): injecting both would count the Kalambaka flow twice; "
                   "its injection point lies on an inactive mountainside (DEM 413 m) with no Pineios channel within 1 km. Sampled and recorded (window no longer clipped, B(2)), not injected.", "named_river": "Pineios"},
        {"name": "titarisios", "lon": 22.24, "lat": 39.71, "window_deg": 0.05, "src_lon": 22.42, "src_lat": 39.71,
         "change": "sampling point moved to the Titarisios' last lattice cell (22.24, 39.71) with a one-cell window (CODE-15 B(1), author's prescription); injection point unchanged", "named_river": "Titarisios"},
        {"name": "enipeas", "lon": 22.39, "lat": 39.30, "src_lon": 22.39, "src_lat": 39.33, "change": "none", "named_river": "Enipeas"},
    ],
    "strymonas": [
        {"name": "kerkini_outlet", "lon": 23.3991, "lat": 41.0289, "change": "none", "named_river": "Strymonas"},
        {"name": "angitis", "lon": 23.92, "lat": 41.0, "change": "none", "named_river": "Angitis"},
    ],
    "valencia": [
        {"name": "magro", "lon": -0.475, "lat": 39.225, "window_deg": 0.02, "src_lon": -0.68, "src_lat": 39.2,
         "change": "sampling point moved to the Magro's own last cell before the Jucar (-0.475, 39.225; 1648 km2) with a one-cell window — the frozen window resolved to the Jucar below the Tous dam (17128 km2); "
                   "injection point unchanged (it drains to the Magro; the build-time snap puts it on the nearest active channel cell)", "named_river": "Magro"},
        {"name": "jucar", "lon": -0.34, "lat": 39.16, "change": "none", "named_river": "Jucar"},
        {"name": "turia", "lon": -0.55, "lat": 39.52, "change": "none", "named_river": "Turia"},
    ],
    "emilia": [
        {"name": "lamone", "lon": 11.9, "lat": 44.24, "change": "none", "named_river": "Lamone"},
        {"name": "senio", "lon": 11.875, "lat": 44.375, "window_deg": 0.02, "move_injection_to_river_cell": (11.825, 44.325), "old": {"lon": 11.83, "lat": 44.27},
         "change": "sampling point moved to the Senio's own last cell (11.875, 44.375; 266 km2) with a one-cell window — the frozen point (11.83, 44.27) lies in the Lamone valley and resolved to the Lamone at Faenza (600 km2), the cell the Montone point also took; "
                   "injection moved to the Senio channel (lowest-z_b active channel cell inside the footprint of the Senio cell nearest to the old point, 11.825/44.325), because the old point drains to the Lamone (flag vi)", "named_river": "Senio"},
        {"name": "montone", "lon": 11.98, "lat": 44.18, "window_deg": 0.05,
         "change": "one-cell window: resolves to the Montone at Forli (12.025, 44.225; 467 km2) instead of the Lamone at Faenza; injection unchanged", "named_river": "Montone"},
        {"name": "ronco", "lon": 12.03, "lat": 44.13, "change": "none", "named_river": "Ronco"},
        {"name": "savio", "lon": 12.1, "lat": 44.06, "move_injection_to_river_cell": (12.175, 44.075), "old": {"lon": 12.1, "lat": 44.06},
         "change": "sampling unchanged (the Savio south of Cesena, 558 km2); injection moved to the Savio channel (lowest-z_b active channel cell inside the footprint of the Savio cell nearest to the old point, 12.175/44.075), because the old point drains to the Ronco (flag vi)", "named_river": "Savio"},
    ],
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--static-dir", type=Path, default=STATIC_DEFAULT)
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = a.out_dir or (repo / "reproduction" / "v14_rerun" / "code15")
    sys.path.insert(0, str(repo / "skill" / "scripts")); sys.path.insert(0, str(repo / "reproduction" / "v14_rerun" / "scripts"))
    os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
    import pyproj
    import rasterio
    from _common import load_config
    import prep_q_at_outlets as pq
    import source_snap as ss
    from glofas_network import GlofasNetwork

    net = GlofasNetwork(a.static_dir)
    utc = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {"utc": utc, "harness_tag": "v1.4.2", "generator": "reproduction/v14_rerun/scripts/source_points_v142.py", "scope": "reproduction/v14_rerun/code15/d8_scope.json", "events": {}}
    md = [f"# Harness v1.4.2 source-point ledger (CODE-15 C) — resolved {utc} by `reproduction/v14_rerun/scripts/source_points_v142.py`", "",
          "Per R3-on event the `upstream_q.src_points` written into every v1.4.2 run config (phase1.py reads the JSON next to this file): sampling coordinate (+ per-point window), injection coordinate, "
          "inject flag, the GloFAS v4 network cell the sampler resolves to (static maps; the Pineios lattice is mapped with its +0.05° longitude offset), its upstream area and the file peak, and the reason for every change. "
          "Injection cells themselves are decided at build time by the v1.4.2 snap (lowest-z_b active channel cell within 1 km) and recorded per run in `model/sfincs_src_snap.json` → `results/<run>_record.json`.", "",
          "| event | point | sampling (lon, lat, window) | injection (lon, lat) | inject | GloFAS cell: file coord → network cell, river, uparea km², peak m³/s (file) | change vs frozen |", "|---|---|---|---|---|---|---|"]
    for event, pts in RESOLVED.items():
        run = EVENT_RUN[event]; cfgp = repo / "reproduction" / "v14_rerun" / "configs" / f"{run}.yaml"
        cfg = load_config(["--config", str(cfgp)])
        gf = PINEIOS_EXT if event == "pineios" else V14 / run / "data" / f"glofas_{EVENT_SLUG[event]}_clean.nc"
        da = pq.open_glofas(gf)
        off = LATTICE_LON_OFFSET.get(event, 0.0)
        # injection moves computed on the run's DEM
        g = V14 / run / "model" / "gis"
        with rasterio.open(g / "dep.tif") as s:
            dep = s.read(1).astype(float); T = s.transform
        with rasterio.open(g / "msk.tif") as s:
            msk = s.read(1).astype(float)
        uparea = None
        to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True); to_ll = pyproj.Transformer.from_crs(cfg.epsg, 4326, always_xy=True)
        xs, ys = ss.cell_centres(T, dep.shape)
        lon_c, lat_c = to_ll.transform(xs, ys)
        resolved = []
        for p in pts:
            q = {k: v for k, v in p.items() if k in ("name", "lon", "lat", "window_deg", "src_lon", "src_lat", "inject")}
            note = {"name": p["name"], "named_river": p["named_river"], "change": p["change"]}
            if p.get("move_injection_to_river_cell"):
                if uparea is None:
                    uparea = ss.dem_uparea_on_grid(V14 / run / "data" / "copdem30", cfg.epsg, T, dep.shape)
                clon, clat = p["move_injection_to_river_cell"]
                foot = (lon_c >= clon - 0.025) & (lon_c <= clon + 0.025) & (lat_c >= clat - 0.025) & (lat_c <= clat + 0.025)
                cand = foot & (msk == 1) & np.isfinite(dep)
                up = np.where(np.isfinite(uparea), uparea, 0.0)
                up_max = float(up[cand].max())
                chan = cand & (up >= 0.5 * up_max)
                k = int(np.argmin(np.where(chan, dep, np.inf))); r, c = np.unravel_index(k, dep.shape)
                q["src_lon"] = round(float(lon_c[r, c]), 5); q["src_lat"] = round(float(lat_c[r, c]), 5)
                note["injection_move"] = {"river_cell": [clon, clat], "footprint_active_cells": int(cand.sum()), "chosen_row_col": [int(r), int(c)], "zb_m": round(float(dep[r, c]), 2),
                                          "uparea_km2": round(float(up[r, c]), 2), "max_uparea_in_footprint_km2": round(up_max, 2),
                                          "old_injection": [p["old"]["lon"], p["old"]["lat"]]}
            # the GloFAS cell this point resolves to (production sampler) on the file the runs will use
            ser, cell, n = pq.select_window_cell(da, float(q["lon"]), float(q["lat"]), float(q.get("window_deg", pq.WINDOW_HALF_DEG)))
            nc = net.cell(cell[0] + off, cell[1])
            note["glofas"] = {"file_coord": list(cell), "network_cell": list(net.centre(nc)), "uparea_km2": round(net.uparea(nc), 1), "window_cells": n,
                              "peak_file_m3s": round(float(ser.max()), 2), "mean_file_m3s": round(float(ser.mean()), 2)}
            note["final_point"] = q
            resolved.append((q, note))
        names = {}
        for q, note in resolved:
            names.setdefault(tuple(note["glofas"]["network_cell"]), []).append(q["name"])
        dups = {k: v for k, v in names.items() if len(v) > 1}
        nested = []
        cells = {tuple(n["glofas"]["network_cell"]): q["name"] for q, n in resolved if q.get("inject", True)}
        for c1, n1 in cells.items():
            for c2, n2 in cells.items():
                if c1 != c2 and net.is_downstream(net.cell(*c1), net.cell(*c2)):
                    nested.append(f"{n1} ⊂ {n2}")
        out["events"][event] = {"run_config_base": run, "glofas_file": str(gf), "lattice_lon_offset_deg": off, "src_points": [q for q, _ in resolved], "notes": [n for _, n in resolved],
                                "duplicate_network_cells": [{"cell": list(k), "points": v} for k, v in dups.items()], "nested_injected_cells": nested}
        for q, note in resolved:
            gl = note["glofas"]
            md.append(f"| {event} | {q['name']} | ({q['lon']}, {q['lat']}, ±{q.get('window_deg', 0.1)}°) | ({q.get('src_lon', q['lon'])}, {q.get('src_lat', q['lat'])}) | {q.get('inject', True)} | "
                      f"({gl['file_coord'][0]}, {gl['file_coord'][1]}) → ({gl['network_cell'][0]}, {gl['network_cell'][1]}), {note['named_river']}, {gl['uparea_km2']}, {gl['peak_file_m3s']} | {note['change']} |")
        print(f"{event}: duplicates {dups or 'none'}; nested injected cells: {nested or 'none'}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "source_points_v142.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    md += ["", "Nested injected cells (one source's cell upstream of another's on the same river, flagged for the author; the Magro ⊂ Júcar-at-the-mouth nesting is inherited from the frozen Júcar point and left as is): " +
           "; ".join(f"{e}: {', '.join(v['nested_injected_cells']) or 'none'}" for e, v in out["events"].items()), ""]
    (out_dir / "source_points_v142.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote", out_dir / "source_points_v142.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
