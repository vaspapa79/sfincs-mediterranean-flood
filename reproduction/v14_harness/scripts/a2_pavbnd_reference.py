"""CODE-12 A2 — reference pressure for the inverse-barometer boundary: 101325 Pa (proposed) versus the
event-window domain-mean ERA5 MSLP of every event, and the resulting constant offset of the boundary
water level (pavbnd - p_mean) / (rhow g) with rhow = 1024 kg/m3 (SFINCS default), g = 9.81.

Usage: python -I a2_pavbnd_reference.py --repo <worktree> --out-json <...> --out-md <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

RHOW, G, PREF = 1024.0, 9.81, 101325.0
EVENTS = [
    ("Pineios EMSR692", "emsr692_pineios_enhanced.yaml", "D:/ELKAK/implementation/pineios_sfincs_enhanced/data"),
    ("Mandra EMSR257", "emsr257_mandra_enhanced.yaml", "D:/ELKAK/implementation/mandra_sfincs_enhanced/data"),
    ("Strymonas EMSR122", "emsr122_strymonas_enhanced.yaml", "D:/ELKAK/implementation/emsr122_sfincs_v3/data"),
    ("Valencia EMSR773", "emsr773_valencia_enhanced.yaml", "D:/ELKAK/ELKAK2/NHESS/runs/valencia_emsr773/data"),
    ("Emilia-Romagna EMSR664", "emsr664_emilia_romagna_enhanced.yaml", "D:/ELKAK/ELKAK2/NHESS/runs/emilia_emsr664/data"),
    ("Crete EMSR933", "emsr933_crete.yaml", "D:/ELKAK/implementation/emsr933_crete/data"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--out-md", required=True, type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.repo / "skill" / "scripts"))
    import pandas as pd
    import xarray as xr
    from _common import load_config

    rep = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rhow": RHOW, "g": G, "pref_pa": PREF,
           "sfincs_gapres_default_pa": 101200.0, "events": []}
    for label, yml, ddir in EVENTS:
        cfg = load_config(["--config", str(a.repo / "skill" / "examples" / yml)])
        f = Path(ddir) / f"era5_{cfg.event_slug}.nc"
        ds = xr.open_dataset(f)
        p = ds["press_msl"]
        t = pd.to_datetime(p["time"].values)
        sel = (t >= pd.Timestamp(cfg.tstart)) & (t <= pd.Timestamp(cfg.tstop))
        pw = p.isel(time=np.where(sel)[0])
        dom_mean = float(pw.mean().values); dom_min_t = pw.mean(dim=[d for d in pw.dims if d != "time"])
        imin = int(dom_min_t.argmin().values)
        row = {"label": label, "file": str(f), "window": [cfg.tstart.isoformat(), cfg.tstop.isoformat()], "n_hours": int(sel.sum()),
               "n_cells": int(np.prod([pw.sizes[d] for d in pw.dims if d != "time"])),
               "mslp_mean_pa": round(dom_mean, 1), "mslp_domainmean_min_pa": round(float(dom_min_t.values[imin]), 1),
               "mslp_domainmean_min_time": str(t[sel][imin])[:16], "mslp_domainmean_max_pa": round(float(dom_min_t.max().values), 1),
               "offset_pref_minus_mean_pa": round(PREF - dom_mean, 1), "ib_offset_at_mean_m": round((PREF - dom_mean) / (RHOW * G), 3),
               "ib_at_domainmean_min_m": round((PREF - float(dom_min_t.values[imin])) / (RHOW * G), 3),
               "ib_range_within_window_m": round((float(dom_min_t.max().values) - float(dom_min_t.values[imin])) / (RHOW * G), 3)}
        rep["events"].append(row); print(label, json.dumps(row))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    L = [f"# A2 — pavbnd reference pressure 101325 Pa vs event-window domain-mean ERA5 MSLP, {rep['utc']}", "",
         f"IB offset = (pavbnd - p) / (rhow g), rhow = {RHOW:.0f} kg/m³ (SFINCS default), g = {G}. Window = [tstart, tstop] of the enhanced YAML "
         "(Crete: baseline YAML, same window); all ERA5 cells of the downloaded box (bbox + buffer). SFINCS `gapres` default = 101200 Pa.", "",
         "| event | window | mean MSLP (hPa) | 101325 − mean (hPa) | constant IB offset at the mean (m) | domain-mean minimum (hPa, time) | IB at the minimum (m) | IB range in window (m) |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rep["events"]:
        L.append(f"| {r['label']} | {r['window'][0][:10]} → {r['window'][1][:10]} | {r['mslp_mean_pa']/100:.2f} | {r['offset_pref_minus_mean_pa']/100:+.2f} | "
                 f"{r['ib_offset_at_mean_m']:+.3f} | {r['mslp_domainmean_min_pa']/100:.2f} ({r['mslp_domainmean_min_time']}) | {r['ib_at_domainmean_min_m']:+.3f} | {r['ib_range_within_window_m']:.3f} |")
    a.out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L)); print(f"-> {a.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
