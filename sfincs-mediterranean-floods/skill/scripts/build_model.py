"""Render sfincs_build.yml from the template and invoke `hydromt build sfincs`.

Optional blocks (rendered only when the relevant config section enables them):
  - infiltration  -> setup_cn_infiltration (needs cn_raster in data_catalog)
  - wind_pressure -> setup_wind_forcing_from_grid + setup_pressure_forcing_from_grid
  - coastal_bc    -> pavbnd: 1 in setup_config (IB at boundary cells)

Upstream Q is injected post-build (sfincs.src + sfincs.dis + sfincs.inp patch)
to sidestep a pandas-2.x incompatibility in hydromt-sfincs's
setup_discharge_forcing — same workaround used by strymonas_forecast_v2.
"""
from __future__ import annotations

import shutil
import string
import subprocess
import sys
from pathlib import Path

from _common import SKILL_DIR, load_config


def _infiltration_block(cfg) -> str:
    if not cfg.infiltration["enabled"]:
        return ""
    return (
        "\nsetup_cn_infiltration:\n"
        "  cn: cn_raster\n"
    )


def _wind_block(cfg) -> str:
    if not cfg.wind_pressure["enabled"]:
        return ""
    return (
        "\nsetup_wind_forcing_from_grid:\n"
        "  wind: era5_hourly\n"
    )


def _pressure_block(cfg) -> str:
    if not cfg.wind_pressure["enabled"]:
        return ""
    return (
        "\nsetup_pressure_forcing_from_grid:\n"
        "  press: era5_hourly\n"
    )


def _pavbnd_line(cfg) -> str:
    if not cfg.coastal_bc["enabled"]:
        return ""
    pav = int(cfg.coastal_bc["pavbnd"])
    return f"\n  pavbnd: {pav}"


def inject_q_forcing(cfg, model_dir: Path) -> None:
    """Write sfincs.src + sfincs.dis and patch sfincs.inp.

    Bypasses hydromt-sfincs's setup_discharge_forcing (pandas-2.x bug:
    RangeIndex.is_integer was removed). Same workaround as v2 forecast.
    """
    import pandas as pd
    import pyproj

    q = cfg.upstream_q
    if not q["enabled"] or not q["src_points"]:
        return
    csv_path = cfg.paths["data_dir"] / "q_outlet.csv"
    if not csv_path.exists():
        print(f"  WARN: {csv_path} missing — run prep_q_at_outlets.py before "
              f"build_model.py; skipping Q injection.")
        return

    to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
    utm = []
    for sp in q["src_points"]:
        # Use src_lon/src_lat if present (injection location differs from sampling location)
        inj_lon = float(sp.get("src_lon", sp["lon"]))
        inj_lat = float(sp.get("src_lat", sp["lat"]))
        utm.append((sp["name"], *to_utm.transform(inj_lon, inj_lat)))

    src_path = model_dir / "sfincs.src"
    with open(src_path, "w") as f:
        for name, x, y in utm:
            f.write(f"{x:.2f}  {y:.2f}\n")

    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    tref = cfg.tref
    dis_path = model_dir / "sfincs.dis"
    with open(dis_path, "w") as f:
        for ts, row in df.iterrows():
            t_sec = (ts.to_pydatetime() - tref).total_seconds()
            vals = "  ".join(f"{float(v):.2f}" for v in row.values)
            f.write(f"{t_sec:.0f}  {vals}\n")

    inp = model_dir / "sfincs.inp"
    txt = inp.read_text()
    if "srcfile" not in txt:
        txt = txt.rstrip() + "\nsrcfile = sfincs.src\ndisfile = sfincs.dis\n"
        inp.write_text(txt)
    print(f"  injected Q forcing: {len(utm)} src points, {len(df)} timesteps "
          f"({utm[0][0]} ...)", flush=True)


def main():
    cfg = load_config()
    work = cfg.paths["work_dir"]
    work.mkdir(parents=True, exist_ok=True)

    tmpl = (SKILL_DIR / "templates" / "sfincs_build.yml.tmpl").read_text()
    grid = cfg.grid
    rendered = string.Template(tmpl).substitute({
        "tref": cfg.tref.strftime("%Y%m%d %H%M%S"),
        "tstart": cfg.tstart.strftime("%Y%m%d %H%M%S"),
        "tstop": cfg.tstop.strftime("%Y%m%d %H%M%S"),
        "manning_land": grid["manning_land"],
        "manning_sea": grid["manning_sea"],
        "west": cfg.bbox["west"], "south": cfg.bbox["south"],
        "east": cfg.bbox["east"], "north": cfg.bbox["north"],
        "res": grid["res"], "epsg": cfg.epsg,
        "subgrid_pixels": grid["subgrid_pixels"],
        "manning_lookup": str(cfg.paths["manning_lookup"]).replace("\\", "/"),
        "zmin": grid["zmin"], "zmax": grid["zmax"],
        "fill_area": grid["fill_area_km2"],
        "drop_area": grid["drop_area_km2"],
        "pavbnd_line": _pavbnd_line(cfg),
        "infiltration_block": _infiltration_block(cfg),
        "wind_block": _wind_block(cfg),
        "pressure_block": _pressure_block(cfg),
        "rain_dataset": cfg.rain_source,
    })
    yml_path = work / "sfincs_build.yml"
    yml_path.write_text(rendered, encoding="utf-8")
    print(f"wrote: {yml_path}")

    model_dir = cfg.paths["model_dir"]
    if model_dir.exists():
        for child in model_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        print(f"cleared: {model_dir}")
    model_dir.mkdir(parents=True, exist_ok=True)

    hydromt = cfg.env.get("hydromt")
    if not hydromt:
        sys.exit("env.hydromt path not set in config")

    cmd = [
        str(hydromt), "build", "sfincs", str(model_dir),
        "-i", str(yml_path),
        "-d", str(work / "data_catalog.yml"),
        "--fo", "-vv",
    ]
    print(f"running: {' '.join(cmd)}", flush=True)
    res = subprocess.run(cmd, cwd=str(work))
    if res.returncode != 0:
        sys.exit(f"hydromt build failed with exit code {res.returncode}")
    print(f"HydroMT build succeeded -> {model_dir}")

    # Post-HydroMT: inject discharge forcing if configured
    inject_q_forcing(cfg, model_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
