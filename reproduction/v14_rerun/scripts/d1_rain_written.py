"""CODE-16 B (2026-10-21) — D1 bookkeeping for Table S7: rain written to the model vs rain intended, for every IMERG-forced
enhanced run, release v1.3.0 model and harness-v1.4 run of record side by side. Post-processing only, no SFINCS run.

written  = model/precip_2d.nc (the field SFINCS read), rate x step summed over the simulated window [tstart, tstop) of the
           model's own sfincs.inp;
intended = the IMERG file the pipeline built it from (data/imerg_<slug>.nc: bias-corrected when R2 is on, raw otherwise),
           same window, rate x step;
both averaged over the precip_2d cells whose centre (with the v1.4 D5 half-cell shift recorded in the file attributes undone) maps
(EPSG of sfincs.inp -> lon/lat) to an IMERG cell centre within half an IMERG cell (0.05°); the IMERG side uses the matched (nearest) IMERG cell of each precip_2d cell, so both sides average over the
same footprint. ratio = written / intended (D1 made it ≈ 2 in release v1.3.0; harness v1.4 writes the rate once).
Valencia release v1.3.0 is the 164-mm re-run (rerun_v164), whose precip_2d is the 350-mm run's field x 164/350 and which has no
IMERG file of its own: its intended field is the 350-mm IMERG file x (164 / 350), the targets read from the F5 record.
(The F5 helper f5_d_volume.analyse_run is not reused here: it mis-aligns forcing files that start at the lead-in tref.)
Usage: python -I d1_rain_written.py --repo <worktree> [--out-json .../code16/d1_rain_written.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

IMPL = Path("D:/ELKAK/implementation")
V14 = IMPL / "v14"
NHESS = Path("D:/ELKAK/ELKAK2/NHESS")
# (event, release, run, model dir, IMERG file, intended-scale spec)
SPECS = [
    ("Pineios", "release v1.3.0", "pineios_sfincs_enhanced (published)", IMPL / "pineios_sfincs_enhanced" / "model_author_ref", IMPL / "pineios_sfincs_enhanced" / "data" / "imerg_pineios.nc", None),
    ("Pineios", "v1.4.2", "pineios_enhanced_v142", V14 / "pineios_enhanced_v142" / "model", V14 / "pineios_enhanced_v142" / "data" / "imerg_pineios.nc", None),
    ("Mandra", "release v1.3.0", "mandra_sfincs_enhanced (published)", IMPL / "mandra_sfincs_enhanced" / "model_author_ref", IMPL / "mandra_sfincs_enhanced" / "data" / "imerg_mandra.nc", None),
    ("Mandra", "v1.4.0", "mandra_enhanced", V14 / "mandra_enhanced" / "model", V14 / "mandra_enhanced" / "data" / "imerg_mandra.nc", None),
    ("Strymonas", "release v1.3.0", "emsr122_sfincs_v3 (published)", IMPL / "emsr122_sfincs_v3" / "model", IMPL / "emsr122_sfincs_v3" / "data" / "imerg_strymonas.nc", None),
    ("Strymonas", "v1.4.2", "strymonas_enhanced_postD6_v142", V14 / "strymonas_enhanced_postD6_v142" / "model", V14 / "strymonas_enhanced_postD6_v142" / "data" / "imerg_strymonas.nc", None),
    ("Valencia", "release v1.3.0", "rerun_v164 (published)", NHESS / "R1_verification" / "task_valencia_anchor" / "rerun_v164" / "model", NHESS / "runs" / "valencia_emsr773" / "data" / "imerg_valencia.nc", "f5:valencia_164_rerun"),
    ("Valencia", "v1.4.2", "valencia_enhanced_164_v142", V14 / "valencia_enhanced_164_v142" / "model", V14 / "valencia_enhanced_164_v142" / "data" / "imerg_valencia.nc", None),
    ("Emilia-R.", "release v1.3.0", "emilia_emsr664 (published)", NHESS / "runs" / "emilia_emsr664" / "model", NHESS / "runs" / "emilia_emsr664" / "data" / "imerg_emilia_romagna.nc", None),
    ("Emilia-R.", "v1.4.2", "emilia_enhanced_8aoi_v142", V14 / "emilia_enhanced_8aoi_v142" / "model", V14 / "emilia_enhanced_8aoi_v142" / "data" / "imerg_emilia_romagna.nc", None),
]


def _times(ds):
    import pandas as pd
    t = ds.indexes["time"]
    return t.to_datetimeindex(unsafe=True) if hasattr(t, "to_datetimeindex") else pd.DatetimeIndex(t)


def _inp(model: Path) -> dict:
    out = {}
    for line in (model / "sfincs.inp").read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1); out[k.strip()] = v.strip()
    return out


def window_totals(nc: Path, t0, t1):
    """(per-cell totals [mm] over t0 <= t < t1, step h, n steps, dataset); rates in mm/h, left-labelled, step = median spacing."""
    import xarray as xr
    ds = xr.open_dataset(nc)
    var = [v for v in ds.data_vars if ds[v].ndim == 3][0]
    t = _times(ds)
    step_h = float(np.median(np.diff(t.values).astype("timedelta64[s]").astype(float))) / 3600.0
    sel = (t >= t0) & (t < t1)
    tot = np.nansum(ds[var].values[sel], axis=0) * step_h
    return tot, step_h, int(sel.sum()), ds, var


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    import pandas as pd
    import pyproj
    f5rec = json.loads((repo / "reproduction" / "emsr933" / "f5" / "F5_d.json").read_text(encoding="utf-8"))
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/d1_rain_written.py",
           "method": "written = precip_2d.nc, intended = data/imerg_<slug>.nc; totals over the model's [tstart, tstop); mean over precip_2d cells matched to the nearest IMERG cell within 0.05 deg", "runs": []}
    for event, rel, run, model, imerg, scale in SPECS:
        inp = _inp(model)
        t0 = pd.Timestamp(dt.datetime.strptime(inp["tstart"], "%Y%m%d %H%M%S")); t1 = pd.Timestamp(dt.datetime.strptime(inp["tstop"], "%Y%m%d %H%M%S"))
        precip = model / inp.get("netamprfile", "precip_2d.nc")
        wm, sm, nm, dsm, _ = window_totals(precip, t0, t1)
        wi, si, ni, dsi, _ = window_totals(imerg, t0, t1)
        xs, ys = np.meshgrid(dsm["x"].values, dsm["y"].values)
        # harness v1.4 (D5) writes the meteo grid shifted by half a cell (corner alignment, recorded in the file attributes): undo the
        # shift so that every precip_2d cell maps onto the IMERG cell it was built from
        shift = (float(dsm.attrs.get("x_shift_m", 0.0)), float(dsm.attrs.get("y_shift_m", 0.0))) if str(dsm.attrs.get("sfincs_corner_alignment", "0")) == "1" else (0.0, 0.0)
        xs, ys = xs - shift[0], ys - shift[1]
        lon, lat = pyproj.Transformer.from_crs(f"EPSG:{int(float(inp['epsg']))}", "EPSG:4326", always_xy=True).transform(xs, ys)
        lonn = "lon" if "lon" in dsi.dims else "longitude"; latn = "lat" if "lat" in dsi.dims else "latitude"
        ilon, ilat = dsi[lonn].values, dsi[latn].values
        j = np.abs(lon[..., None] - ilon[None, None, :]).argmin(axis=-1); i = np.abs(lat[..., None] - ilat[None, None, :]).argmin(axis=-1)
        ok = (np.abs(ilon[j] - lon) <= 0.05 + 1e-9) & (np.abs(ilat[i] - lat) <= 0.05 + 1e-9)
        # imerg dims order (time, lat, lon) or (time, lon, lat)
        ivar = [v for v in dsi.data_vars if dsi[v].ndim == 3][0]
        dims = dsi[ivar].dims
        wi_ll = wi if dims[1] == latn else wi.T
        written = float(np.mean(wm[ok])); intended_file = float(np.mean(wi_ll[i[ok], j[ok]]))
        rec = {"event": event, "release": rel, "run": run, "model_dir": str(model), "precip_file": str(precip), "intended_file": str(imerg),
               "window": [str(t0), str(t1)], "steps_model": nm, "step_h_model": sm, "steps_imerg": ni, "step_h_imerg": si,
               "d5_shift_undone_m": list(shift), "n_cells_model": int(ok.size), "n_cells_matched": int(ok.sum()), "written_mm": written, "intended_file_mm": intended_file}
        if scale and scale.startswith("f5:"):
            fr = next(r for r in f5rec["runs"] if r["key"] == scale[3:])
            tg = fr["targets_mm"]; s_ = tg["run_target_164"] / tg["old_target_350"]
            rec["intended_scale"] = {"value": s_, "from": f"reproduction/emsr933/f5/F5_d.json runs[{scale[3:]}].targets_mm run_target_164 / old_target_350"}
            rec["intended_mm"] = intended_file * s_
        else:
            rec["intended_mm"] = intended_file
        rec["written_over_intended"] = written / rec["intended_mm"] if rec["intended_mm"] else None
        out["runs"].append(rec)
        print(f"{event:10s} {rel:15s} {run:38s} written {written:8.1f} mm / intended {rec['intended_mm']:8.1f} mm = {rec['written_over_intended']:.3f}  "
              f"({rec['n_cells_matched']}/{rec['n_cells_model']} cells, {nm} model steps of {sm:g} h, {ni} IMERG steps)", flush=True)
    op = a.out_json or (repo / "reproduction" / "v14_rerun" / "code16" / "d1_rain_written.json")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("wrote", op)
    return 0


if __name__ == "__main__":
    sys.exit(main())
