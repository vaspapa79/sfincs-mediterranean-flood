"""Phase 4d (GO Phases 3-5, 2026-10-19) — Figure 4 / Figure 6 equivalents: domain-mean rainfall series (raw IMERG, R2-corrected
IMERG, ERA5; the model forcing on top) from the rain_diagnostics series CSV of a run. PNG + the CSV is the data behind it.
Usage: python -I fig_rain_v14.py --series <..._series.csv> --json <rain json> --out <png> [--title ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", required=True, type=Path)
    ap.add_argument("--json", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})
    df = pd.read_csv(a.series, index_col=0, parse_dates=True)
    rj = json.loads(a.json.read_text(encoding="utf-8"))
    w = rj["windows"]
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    style = {"imerg_raw": ("raw IMERG", "#7f7f7f", "-"), "imerg": ("IMERG after R2 (as applied)", "#1f4e79", "-"), "era5": ("ERA5", "#c0392b", "-"),
             "model_forcing": ("model forcing (precip_2d.nc)", "#2e8b57", ":")}
    for col in ("imerg_raw", "imerg", "era5", "model_forcing"):
        if col in df:
            lab, c, ls = style[col]
            tot = rj["sources"].get(col, {}).get("by_window", {}).get("forcing", {}).get("domain_mean_total_mm")
            ax.plot(df.index, df[col], ls, color=c, lw=1.0, label=f"{lab}" + (f" — {tot:.0f} mm over the forcing window" if tot is not None else ""))
    for name, (t0, t1) in w.items():
        if name == "event":
            ax.axvspan(pd.Timestamp(t0), pd.Timestamp(t1), color="#fde8cf", zorder=0, label="R2 event window")
        if name == "simulated":
            ax.axvline(pd.Timestamp(t0), color="k", lw=0.6, ls="--"); ax.axvline(pd.Timestamp(t1), color="k", lw=0.6, ls="--")
    ax.set_ylabel("domain-mean rain rate (mm h⁻¹)"); ax.set_title(a.title or f"{rj['event']}: domain-mean precipitation, harness v1.4 forcing files")
    ax.legend(fontsize=6.5, frameon=False); fig.autofmt_xdate(); fig.tight_layout()
    a.out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(a.out); plt.close(fig)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
