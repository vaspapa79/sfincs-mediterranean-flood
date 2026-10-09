"""CODE-10 Stage 1d — schema check of the EMSR933 YAMLs WITHOUT running the pipeline.

For each config: load it through the pipeline's own loader (machine-local override applied), print
every derived quantity the pipeline would use (window, bbox, tiles, grid, rule flags), render the
data catalog and the HydroMT build file with the same substitutions as prep_inputs.py /
build_model.py into <out-dir>/validate/<stem>/, and run the pipeline's preflight_check.
No download, no hydromt, no SFINCS.

Usage: python -I stage1_validate_yaml.py --repo <worktree> --out-dir <...> skill/examples/emsr933_crete.yaml ...
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import string
import sys
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("configs", nargs="+", type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    from _common import SKILL_DIR, load_config, preflight_check
    import build_model
    import prep_inputs

    report = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "configs": {}}
    rc_all = 0
    for cp in a.configs:
        cfg = load_config(["--config", str(cp)])
        g = cfg.grid
        d = {"label": cfg.event_label, "slug": cfg.event_slug, "date": str(cfg.event_date),
             "window": cfg.window, "tref": cfg.tref.isoformat(), "tstart": cfg.tstart.isoformat(),
             "tstop": cfg.tstop.isoformat(), "bbox": cfg.bbox, "cds_area_NWSE": cfg.bbox_with_buffer,
             "epsg": cfg.epsg, "grid": g, "dem_tiles": ["".join(t) for t in cfg.dem_tiles()],
             "worldcover_tiles": ["".join(t) for t in cfg.worldcover_tiles()],
             "rain_source": cfg.rain_source, "imerg_product": cfg.imerg_product,
             "rain_bias_correct": cfg.rain_bias_correct, "coastal_bc": cfg.coastal_bc,
             "wind_pressure": cfg.wind_pressure, "infiltration_enabled": cfg.infiltration["enabled"],
             "infiltration_amc": cfg.infiltration["amc"], "upstream_q": cfg.upstream_q,
             "ems_switches": {k: cfg.ems.get(k) for k in ("activation", "include_del_product", "exclude_not_analysed",
                                                           "truth_cutoff_snapshot_utc")},
             "paths_resolved": {k: str(v) for k, v in cfg.paths.items()}}
        vd = a.out_dir / "validate" / cp.stem
        vd.mkdir(parents=True, exist_ok=True)
        (vd / "data_catalog.yml").write_text(prep_inputs.render_catalog(cfg), encoding="utf-8")
        tmpl = (SKILL_DIR / "templates" / "sfincs_build.yml.tmpl").read_text()
        rendered = string.Template(tmpl).substitute({
            "tref": cfg.tref.strftime("%Y%m%d %H%M%S"), "tstart": cfg.tstart.strftime("%Y%m%d %H%M%S"),
            "tstop": cfg.tstop.strftime("%Y%m%d %H%M%S"), "manning_land": g["manning_land"],
            "manning_sea": g["manning_sea"], "west": cfg.bbox["west"], "south": cfg.bbox["south"],
            "east": cfg.bbox["east"], "north": cfg.bbox["north"], "res": g["res"], "epsg": cfg.epsg,
            "subgrid_pixels": g["subgrid_pixels"],
            "manning_lookup": str(cfg.paths["manning_lookup"]).replace("\\", "/"),
            "zmin": g["zmin"], "zmax": g["zmax"], "fill_area": g["fill_area_km2"], "drop_area": g["drop_area_km2"],
            "pavbnd_line": build_model._pavbnd_line(cfg), "infiltration_block": build_model._infiltration_block(cfg),
            "wind_block": build_model._wind_block(cfg), "pressure_block": build_model._pressure_block(cfg),
            "rain_dataset": cfg.rain_source})
        (vd / "sfincs_build.yml").write_text(rendered, encoding="utf-8")
        d["rendered"] = [str(vd / "data_catalog.yml"), str(vd / "sfincs_build.yml")]
        print(f"\n===== {cp.name}")
        for k, v in d.items():
            print(f"  {k}: {v}")
        print("  --- sfincs_build.yml (rendered):")
        print("\n".join("    " + ln for ln in rendered.splitlines()))
        rc = preflight_check(cfg)
        d["preflight_rc"] = rc
        rc_all |= rc
        report["configs"][cp.name] = d
    (a.out_dir / "stage1_yaml_validation.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n-> {a.out_dir / 'stage1_yaml_validation.json'}  (preflight rc all = {rc_all})")
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
