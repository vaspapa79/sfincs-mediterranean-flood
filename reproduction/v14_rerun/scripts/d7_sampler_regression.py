"""CODE-14 B (2026-10-20) — real-data regression of the v1.4.1 GloFAS sampler against the v1.4.0 records (no runs).

For every R3-on v1.4 run the fixed `prep_q_at_outlets.sample_points` is applied to the run's own config and GloFAS file
and compared with the `q_outlet.csv` / `sfincs.dis` the v1.4.0 pipeline wrote: the correctly-sampled events (Strymonas,
Valencia, Emilia) must come out byte-identical (same cells, same hourly values), the Pineios runs show the series that
replace the 11.589 m3/s constant. Written to reproduction/v14_rerun/code14/d7_sampler_regression.{json,md}.

Usage: python -I d7_sampler_regression.py --repo <worktree>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

V14 = Path("D:/ELKAK/implementation/v14")
RUNS = ["strymonas_enhanced", "strymonas_enhanced_postD6", "strymonas_abl_cnoff_q", "strymonas_v1_prefix_src", "strymonas_leadin7d",
        "valencia_enhanced_164", "valencia_raw_imerg", "emilia_enhanced_8aoi",
        "pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5", "pineios_timevarying_q"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    import pandas as pd
    from _common import load_config
    import prep_q_at_outlets as pq
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sampler": "skill/scripts/prep_q_at_outlets.py (v1.4.1)", "runs": []}
    md = ["| run | GloFAS axis | v1.4.0 q_outlet.csv vs v1.4.1 sampler | sfincs.dis vs v1.4.1 sampler | cells (v1.4.1) | column peaks v1.4.1 (m³/s) |", "|---|---|---|---|---|---|"]
    for run in RUNS:
        cfg_path = repo / "reproduction" / "v14_rerun" / "configs" / f"{run}.yaml"
        cfg = load_config(["--config", str(cfg_path)])
        data, model = V14 / run / "data", V14 / run / "model"
        gf = data / f"glofas_{cfg.event_slug}_clean.nc"
        da = pq.open_glofas(gf)
        df, rep = pq.sample_points(da, cfg.upstream_q["src_points"], cfg.tref, cfg.tstop)
        old = pd.read_csv(data / "q_outlet.csv", index_col=0, parse_dates=True)
        csv_same = bool(old.shape == df.shape and np.array_equal(old.values, df.values) and list(old.columns) == list(df.columns))
        csv_maxdiff = float(np.nanmax(np.abs(old.values - df.values))) if old.shape == df.shape else None
        disp = model / ("sfincs.dis.pipeline" if (model / "sfincs.dis.pipeline").exists() else "sfincs.dis")
        dis = np.loadtxt(disp); dis = dis[None, :] if dis.ndim == 1 else dis
        new_dis = np.round(df.values, 2)
        dis_same = bool(dis[:, 1:].shape == new_dis.shape and np.allclose(dis[:, 1:], new_dis, atol=0.006))
        dis_maxdiff = float(np.max(np.abs(dis[:, 1:] - new_dis))) if dis[:, 1:].shape == new_dis.shape else None
        rec = {"run": run, "event": cfg.event_slug, "config": str(cfg_path.relative_to(repo)), "glofas_file": str(gf), "latitude_order": rep["latitude_order"],
               "q_outlet_csv_identical": csv_same, "q_outlet_csv_max_abs_diff": csv_maxdiff, "dis_file": str(disp), "sfincs_dis_identical": dis_same,
               "sfincs_dis_max_abs_diff": dis_maxdiff, "v141_points": rep["points"], "duplicate_cells": rep["duplicate_cells"],
               "v140_column_peaks": [round(float(v), 2) for v in old.max().values], "v141_column_peaks": [p["column_peak_m3s"] for p in rep["points"]],
               "v141_combined_hourly_peak_m3s": round(float(df.sum(axis=1).max()), 2)}
        out["runs"].append(rec)
        md.append(f"| {run} | {rep['latitude_order']} | {'identical' if csv_same else f'DIFFERENT (max |Δ| {csv_maxdiff:.2f})'} | "
                  f"{'identical' if dis_same else f'DIFFERENT (max |Δ| {dis_maxdiff:.2f}; v1.4.0 file {disp.name})'} | "
                  + "; ".join(f"{p['name']} ({p['cell_lonlat'][0]}, {p['cell_lonlat'][1]})" for p in rep["points"]) + " | "
                  + " / ".join(f"{p['column_peak_m3s']:.2f}" for p in rep["points"]) + f" (combined {rec['v141_combined_hourly_peak_m3s']:.1f}) |")
        print(f"{run}: csv identical {csv_same}, dis identical {dis_same}, peaks {rec['v141_column_peaks']}, duplicates {rep['duplicate_cells']}")
    out_dir = repo / "reproduction" / "v14_rerun" / "code14"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "d7_sampler_regression.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (out_dir / "d7_sampler_regression.md").write_text(f"# v1.4.1 sampler vs v1.4.0 records — generated {out['utc']} by `scripts/d7_sampler_regression.py`\n\n" + "\n".join(md) + "\n", encoding="utf-8")
    print("wrote", out_dir / "d7_sampler_regression.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
