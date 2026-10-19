"""Controlled Strymonas experiments (diagnostic, NO scoring): copies of a model dir with one change each.
Usage: python run_exp.py <name> <src_model_dir> [key=value inp patches ...] [--precip <file>]
Reports: V_land(zb>0) series (Mm3), wet>0.1 km2 at the end, max zs in the Serres pool window, SFINCS wall-clock.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np, xarray as xr

SFINCS = "D:/ELKAK/implementation/SFINCS_bin/SFINCS_v2.3.0_mt_Faber_release_exe/sfincs.exe"
ROOT = Path(__file__).resolve().parent
SKIP = {"sfincs_map.nc", "sfincs.log", "sfincs_log.txt", "hydromt.log", "sfincs_his.nc"}


def set_inp(txt, key, val):
    out, done = [], False
    for ln in txt.splitlines():
        if ln.split("=")[0].strip() == key:
            out.append(f"{key:<20} = {val}"); done = True
        else:
            out.append(ln)
    if not done:
        out.append(f"{key:<20} = {val}")
    return "\n".join(out) + "\n"


def main():
    name, src = sys.argv[1], Path(sys.argv[2])
    patches = [a for a in sys.argv[3:] if "=" in a and not a.startswith("--")]
    precip = sys.argv[sys.argv.index("--precip") + 1] if "--precip" in sys.argv else None
    copies = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--copy"]
    unsets = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--unset"]
    dst = ROOT / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.is_file() and f.name not in SKIP:
            shutil.copy2(f, dst / f.name)
    txt = (dst / "sfincs.inp").read_text()
    for p in patches:
        k, v = p.split("=", 1); txt = set_inp(txt, k.strip(), v.strip())
    for k in unsets:
        txt = chr(10).join(ln for ln in txt.splitlines() if ln.split("=")[0].strip() != k) + chr(10)
    (dst / "sfincs.inp").write_text(txt)
    for f in copies:
        shutil.copy2(f, dst / Path(f).name)
    if precip:
        shutil.copy2(precip, dst / "precip_2d.nc")
    t0 = time.time()
    run = subprocess.run([SFINCS], cwd=str(dst), capture_output=True, text=True)
    wall = time.time() - t0
    (dst / "sfincs_log.txt").write_text(run.stdout + run.stderr)
    ds = xr.open_dataset(dst / "sfincs_map.nc")
    zb = ds["zb"].values; msk = ds["msk"].values; zs = ds["zs"].values; x = ds["x"].values; y = ds["y"].values
    h = np.where(np.isfinite(zs), np.maximum(zs - zb[None], 0), 0); h[:, msk == 0] = 0
    land = (msk == 1) & (zb > 0)
    V = (h[:, land] * 22500).sum(axis=1) / 1e6
    pool = (msk == 1) & (x > 720e3) & (x < 740e3) & (y > 4525e3) & (y < 4540e3)
    zsmax = np.nanmax(np.where(pool[None], zs, np.nan), axis=(1, 2))
    rep = {"name": name, "src": str(src), "patches": patches, "precip": precip, "copies": copies, "unsets": unsets, "wall_s": round(wall, 1),
           "V_land_daily_Mm3": [round(float(V[i]), 1) for i in range(0, len(V), 24)], "V_land_max": round(float(V.max()), 1), "V_land_end": round(float(V[-1]), 1),
           "wet_gt_0p1_km2_end": round(float((h[-1] > 0.1).sum() * 0.0225), 1), "wet_gt_0p1_km2_max": round(float((h.max(axis=0) > 0.1).sum() * 0.0225), 1),
           "pool_zs_max_daily": [None if not np.isfinite(zsmax[i]) else round(float(zsmax[i]), 2) for i in range(0, len(V), 24)],
           "log_tail": run.stdout.splitlines()[-3:]}
    (dst / "report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
