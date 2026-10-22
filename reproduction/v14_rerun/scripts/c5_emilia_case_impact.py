"""Score impact of the case-insensitive truth selection on EMSR664 (run of record emilia_enhanced_8aoi_v142): strict
contingency at h > 0.10 m on the v1.4 evaluation mask with the validator's 13 truth files (Windows) and with the 10 files a
case-sensitive glob selects (the three previousObservedEventA layers dropped). Same functions as validate_event_v2."""
import fnmatch
import json
import os
import sys
from pathlib import Path

import numpy as np

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo / "skill" / "scripts"))
sys.path.insert(0, str(repo / "validation"))
os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
from _common import load_config  # noqa: E402
import validate_event_v2 as V  # noqa: E402
from eval_exclusion import read_mask_for_grid  # noqa: E402

run = "emilia_enhanced_8aoi_v142"
cfg = load_config(["--config", str(repo / "reproduction/v14_rerun/configs" / f"{run}.yaml")])
s = V.open_sfincs_light(cfg.paths["model_dir"])
excl = read_mask_for_grid(repo / "reproduction/v14_rerun/masks/emilia_exclusion.tif", s)
ems_dir = cfg.paths["data_dir"] / "ems_polygons"
sel = V._select_obs_shps(ems_dir, include_del_product=False)
PATS = ["*DELINEATION*MONIT*crisis_information_poly.shp", "*GRADING*observed_event_a.shp", "*GRA_*observed_event_a.shp",
        "*DEL_MONIT*observedEventA*.shp", "*DEL_MONIT*observed_event*.shp", "*GRA_PRODUCT*observedEventA*.shp"]
cs = [p for p in sel if any(fnmatch.fnmatchcase(p.name, pt) for pt in PATS)]
aoi = V._list_shps(ems_dir, ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])
# AOI universe: on a case-sensitive system the AOI patterns match the same files (checked below)
aoi_cs = [p for p in aoi if any(fnmatch.fnmatchcase(p.name, pt) for pt in ["*area_of_interest.shp", "*area_of_interest_a.shp", "*areaOfInterestA*.shp"])]
uni = (s["msk"] > 0) & V._rasterise_polys_to_grid(aoi, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"]) & ~excl
zsmax = s["ds"]["zsmax"].max(dim="timemax").values
hmax = np.where(np.isnan(zsmax), 0.0, np.maximum(zsmax - s["zb"], 0))
mw = hmax > 0.10
res = {"run": run, "n_truth_files_windows": len(sel), "n_truth_files_case_sensitive": len(cs),
       "aoi_files_same_case_sensitive": len(aoi_cs) == len(aoi)}
for name, files in (("windows_13", sel), ("case_sensitive_10", cs)):
    truth = V._rasterise_polys_to_grid(files, s["x"], s["y"], cfg.epsg, s["dx"], s["dy"])
    c = V._contingency_full(mw, truth, uni)
    res[name] = {"observed_km2": float((truth & uni).sum() * s["cell_area_km2"]),
                 **{k: c[k] for k in ("tp", "fp", "fn", "tn", "csi", "hr", "far", "bias") if k in c}}
rec = json.loads((repo / "reproduction/v14_rerun/results" / f"{run}_v14_newmask.json").read_text(encoding="utf-8"))
res["record_csi_h_gt_0p10"] = rec.get("strict", {}).get("h>0.10m", {}).get("csi") if isinstance(rec.get("strict"), dict) else None
print(json.dumps(res, indent=1))
Path(sys.argv[2]).write_text(json.dumps(res, indent=2), encoding="utf-8")
