"""Checkpoint 4 — share of the false alarms of each published v1.3 enhanced run that fall on open-sea, WorldCover-80
or inland zb < 0 cells (GO-C Phase 1 reporting item). Published mask, published output, h > 0.10 m; no new score.

Usage: python -I fa_share_v13.py --repo <worktree> --config <example yaml> --work <published work dir>
       --open-sea-tif <v1.4 open_sea_mask.tif> --worldcover <vrt> --out-json <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--open-sea-tif", required=True, type=Path)
    ap.add_argument("--worldcover", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    a = ap.parse_args()
    os.environ["SFINCS_WORK_DIR"] = str(a.work)
    sys.path.insert(0, str(a.repo / "skill" / "scripts")); sys.path.insert(0, str(a.repo / "validation"))
    import rasterio
    from _common import load_config
    from _anim_common import open_sfincs
    import validate_event_v2 as V
    import eval_exclusion as EX
    cfg = load_config(["--config", str(a.config)])
    s = open_sfincs(cfg.paths["model_dir"])
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    obs = V._select_obs_shps(ems_dir, include_del_product=bool(cfg.ems.get("include_del_product", False)))
    aoi = V._list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
    ems_wet = V._rasterise_polys_to_grid(obs, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
    msk_bool = s["msk"] > 0
    ev = msk_bool & V._rasterise_polys_to_grid(aoi, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]) if aoi else msk_bool
    zsmax = s["ds"]["zsmax"].max(dim="timemax").values
    hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
    model_wet = hmax > 0.10
    fa = model_wet & ~ems_wet & ev
    tp = model_wet & ems_wet & ev
    open_sea = EX.read_mask_for_grid(a.open_sea_tif, s)
    with rasterio.open(a.open_sea_tif) as src:
        tr, shape = src.transform, (src.height, src.width)
    wc80_n = EX.worldcover80_at_centres(a.worldcover, tr, shape, cfg.epsg)
    wc80 = wc80_n[::-1, :] if (s["y"][1, 0] > s["y"][0, 0]) else wc80_n
    inland_neg = ~open_sea & (s["zb"] < 0) & msk_bool
    cats = {"open_sea": open_sea, "wc80": wc80, "wc80_land": wc80 & ~open_sea, "inland_zb_lt_0": inland_neg,
            "union_open_sea_wc80": open_sea | wc80, "union_all_three": open_sea | wc80 | inland_neg}
    A = s["cell_area_km2"]
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "config": str(a.config), "work": str(a.work),
           "threshold_m": 0.10, "mask": "published (msk>0 & AOI union)", "eval_cells": int(ev.sum()), "eval_km2": round(float(ev.sum() * A), 2),
           "fa_cells": int(fa.sum()), "fa_km2": round(float(fa.sum() * A), 2), "tp_cells": int(tp.sum()), "tp_km2": round(float(tp.sum() * A), 2),
           "observed_cells_in_eval": int((ems_wet & ev).sum()), "categories": {}}
    for k, c in cats.items():
        n = int((fa & c).sum())
        out["categories"][k] = {"fa_cells": n, "fa_km2": round(float(n * A), 3), "share_of_fa": round(n / max(int(fa.sum()), 1), 4),
                                "cells_in_eval": int((c & ev).sum()), "observed_cells_in_eval": int((c & ev & ems_wet).sum()),
                                "tp_cells": int((tp & c).sum())}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
