"""Which truth shapefiles does validate_event_v2._select_obs_shps pick only because the Windows glob is case-insensitive?
For each run of record: the validator's selection on this machine, and the same selection with the patterns matched
case-sensitively (fnmatchcase on the file name, as a POSIX glob would). Prints counts and the extra files."""
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo / "skill" / "scripts"))
sys.path.insert(0, str(repo / "validation"))
os.environ.setdefault("GDAL_DATA", os.path.join(sys.prefix, "Library", "share", "gdal"))
from _common import load_config  # noqa: E402
import validate_event_v2 as V  # noqa: E402

PATS = ["*DELINEATION*MONIT*crisis_information_poly.shp", "*GRADING*observed_event_a.shp", "*GRA_*observed_event_a.shp",
        "*DEL_MONIT*observedEventA*.shp", "*DEL_MONIT*observed_event*.shp", "*GRA_PRODUCT*observedEventA*.shp"]
RUNS = ["pineios_enhanced_v142", "mandra_enhanced", "strymonas_enhanced_postD6_v142", "valencia_enhanced_164_v142",
        "emilia_enhanced_8aoi_v142", "crete_canonical_r2on"]
out = {}
for run in RUNS:
    cfg = load_config(["--config", str(repo / "reproduction/v14_rerun/configs" / f"{run}.yaml")])
    inc = bool(cfg.ems.get("include_del_product", False))
    ems_dir = cfg.paths["data_dir"] / "ems_polygons"
    sel = V._select_obs_shps(ems_dir, include_del_product=inc)
    pats = PATS + (["*DEL_PRODUCT*observedEventA*.shp"] if inc else [])
    case_only = [p for p in sel if not any(fnmatch.fnmatchcase(p.name, pt) for pt in pats)]
    out[run] = {"n_selected": len(sel), "n_matched_only_case_insensitively": len(case_only),
                "case_insensitive_only": [p.name for p in case_only]}
    print(f"{run:32s} selected {len(sel):3d}; matched only case-insensitively {len(case_only)}: {[p.name for p in case_only]}")
Path(sys.argv[2]).write_text(json.dumps(out, indent=2), encoding="utf-8")
