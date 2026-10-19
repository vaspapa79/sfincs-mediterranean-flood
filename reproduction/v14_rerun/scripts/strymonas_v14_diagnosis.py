"""Checkpoint 4 — why the Strymonas v3 enhanced flood doubles under v1.4 (diagnostic record; no scoring, no tuning).

Collects, from the published v1.3 model and the v1.4 re-run (and the isolation experiments in the session scratchpad
if present): rain and discharge volumes, the water volume on land through time, the end-of-run pool in the Serres
plain, and the gorge/levee geometry at the pool front. Writes JSON + MD under reproduction/v14_rerun/.
Usage: python -I strymonas_v14_diagnosis.py --v13 <published model> --v14 <v1.4 model> [--exp <scratch dir>] --out <stem>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

CELL = 150.0 * 150.0


def load(m: Path):
    import xarray as xr
    ds = xr.open_dataset(m / "sfincs_map.nc")
    zb = ds["zb"].values; msk = ds["msk"].values; zs = ds["zs"].values
    h = np.where(np.isfinite(zs), np.maximum(zs - zb[None], 0.0), 0.0); h[:, msk == 0] = 0.0
    return ds, zb, msk, zs, h


def rain_total(m: Path, ds, msk, zb):
    import netCDF4
    nc = netCDF4.Dataset(m / "precip_2d.nc"); v = [k for k in nc.variables if nc[k].ndim == 3][0]
    t = nc["time"][:]; dt_h = float(t[1] - t[0]) / 60.0
    data = np.nan_to_num(nc[v][:].filled(0)); tot = data.sum(axis=0) * dt_h / 1000.0       # m
    px, py = nc["x"][:], nc["y"][:]
    shift = {a: (float(nc.getncattr(a)) if a in nc.ncattrs() else 0.0) for a in ("x_shift_m", "y_shift_m")}
    nc.close()
    x2, y2 = ds["x"].values, ds["y"].values
    ix = np.clip(np.round((x2 - (px[0] - shift["x_shift_m"])) / (px[1] - px[0])).astype(int), 0, len(px) - 1)
    iy = np.clip(np.round((y2 - (py[0] - shift["y_shift_m"])) / (py[1] - py[0])).astype(int), 0, len(py) - 1)
    land = (msk == 1) & (zb > 0)
    return {"domain_mean_mm": round(float(tot.mean() * 1000), 1), "on_land_Mm3": round(float((tot[iy, ix] * CELL)[land].sum() / 1e6), 1),
            "n_times": int(len(t)), "dt_h": dt_h, "file_shift_m": shift}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--v13", required=True, type=Path); ap.add_argument("--v14", required=True, type=Path)
    ap.add_argument("--exp", type=Path); ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "v13_model": str(a.v13), "v14_model": str(a.v14), "runs": {}}
    dis = np.loadtxt(a.v13 / "sfincs.dis"); t = dis[:, 0]; q = dis[:, 1:]
    sim = t >= 7 * 86400
    out["discharge_Mm3"] = {"total_14d": round(float(np.trapezoid(q.sum(1), t)) / 1e6, 1), "simulated_week": round(float(np.trapezoid(q.sum(1)[sim], t[sim])) / 1e6, 1),
                            "per_source_simulated_week": [round(float(np.trapezoid(q[sim, j], t[sim])) / 1e6, 1) for j in range(q.shape[1])],
                            "peak_m3s_per_source": [float(v) for v in q.max(0)], "identical_dis_src": (a.v13 / "sfincs.dis").read_bytes() == (a.v14 / "sfincs.dis").read_bytes()}
    for nm, m in (("v1.3", a.v13), ("v1.4", a.v14)):
        ds, zb, msk, zs, h = load(m)
        land = (msk == 1) & (zb > 0)
        V = (h[:, land] * CELL).sum(axis=1) / 1e6; Vt = (h * CELL).reshape(h.shape[0], -1).sum(axis=1) / 1e6
        x, y = ds["x"].values, ds["y"].values
        rc = np.unravel_index(np.argmin((x - 727.1e3) ** 2 + (y - 4535.0e3) ** 2), x.shape)   # centre of the v1.4 end-of-run pool
        r = {"active": int((msk > 0).sum()), "msk2": int((msk == 2).sum()), "rain": rain_total(m, ds, msk, zb),
             "V_land_zb_gt_0_daily_Mm3": [round(float(V[i]), 1) for i in range(0, len(V), 24)], "V_land_max_Mm3": round(float(V.max()), 1), "V_total_end_Mm3": round(float(Vt[-1]), 1),
             "wet_gt_0p10_km2_max_field": round(float((h.max(axis=0) > 0.10).sum() * CELL / 1e6), 1),
             "pool_centre_E727p1_N4535p0": {"zb_m": round(float(zb[rc]), 2), "depth_m_daily": [round(float(h[i][rc]), 2) for i in range(0, len(V), 24)]}}
        for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 20), (20, 40)):
            sel = (msk == 1) & (zb >= lo) & (zb < hi)
            r[f"end_wet_km2_zb_{lo}_{hi}"] = round(float(((h[-1] > 0.1) & sel).sum() * CELL / 1e6), 1)
        out["runs"][nm] = r
    if a.exp and a.exp.exists():
        out["experiments"] = {}
        for d in sorted(a.exp.glob("E*/report.json")):
            out["experiments"][d.parent.name] = json.loads(d.read_text(encoding="utf-8"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix(".json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
    L = [f"# Strymonas v3 enhanced — v1.3 vs v1.4 water balance ({out['utc']})", "",
         f"Discharge (identical sfincs.dis/src in both: {out['discharge_Mm3']['identical_dis_src']}): {out['discharge_Mm3']['total_14d']} Mm³ over the 14-day forcing window, "
         f"{out['discharge_Mm3']['simulated_week']} Mm³ inside the simulated week (Kerkini outlet / Angitis {out['discharge_Mm3']['per_source_simulated_week']}; peaks {out['discharge_Mm3']['peak_m3s_per_source']} m³/s).", "",
         "| quantity | v1.3 published | v1.4 |", "|---|---|---|"]
    A, B = out["runs"]["v1.3"], out["runs"]["v1.4"]
    for k, lab in (("active", "active cells"), ("msk2", "msk = 2 cells"), ("V_land_max_Mm3", "max water volume on land zb > 0 (Mm³)"), ("V_total_end_Mm3", "volume on the grid at the end (Mm³)"),
                   ("wet_gt_0p10_km2_max_field", "wet area h_max > 0.10 m (km²)")):
        L.append(f"| {lab} | {A[k]} | {B[k]} |")
    L.append(f"| rain: domain mean / on land (mm, Mm³) | {A['rain']['domain_mean_mm']} / {A['rain']['on_land_Mm3']} | {B['rain']['domain_mean_mm']} / {B['rain']['on_land_Mm3']} |")
    L.append(f"| water on land, daily (Mm³) | {A['V_land_zb_gt_0_daily_Mm3']} | {B['V_land_zb_gt_0_daily_Mm3']} |")
    L.append(f"| depth at the pool centre (E 727.1, N 4535.0 km; zb {A['pool_centre_E727p1_N4535p0']['zb_m']} m), daily (m) | {A['pool_centre_E727p1_N4535p0']['depth_m_daily']} | {B['pool_centre_E727p1_N4535p0']['depth_m_daily']} |")
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 20)):
        L.append(f"| end-of-run wet km² at zb {lo}–{hi} m | {A[f'end_wet_km2_zb_{lo}_{hi}']} | {B[f'end_wet_km2_zb_{lo}_{hi}']} |")
    if out.get("experiments"):
        L += ["", "## Isolation experiments (copies of the models with one change; no scoring)", "", "| experiment | change | V_land max / end (Mm³) | wet h > 0.10 m at the end (km²) | SFINCS s |", "|---|---|---|---|---|"]
        for nm, e in out["experiments"].items():
            ch = "; ".join([f"inp {p}" for p in e["patches"]] + [f"inp drop {u}" for u in e.get("unsets", [])]
                           + [f"file {Path(c).name} from {Path(c).parent.parent.name}" for c in e.get("copies", [])]
                           + ([f"precip_2d.nc from {Path(e['precip']).parent.parent.name}"] if e["precip"] else []))
            L.append(f"| {nm} (base: {Path(e['src']).parent.name}) | {ch} | {e['V_land_max']} / {e['V_land_end']} | {e['wet_gt_0p1_km2_end']} | {e['wall_s']} |")
    a.out.with_suffix(".md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
