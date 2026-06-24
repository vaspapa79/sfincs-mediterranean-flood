"""Aggregate per-event validation JSONs into the cross-event paper tables.

Reads paper/data/<event_slug>_metrics.json for each event slug listed in
EVENTS below, plus the baseline metric file <event_slug>_baseline_metrics.json
when present, and writes:

  paper/data/cross_event_metrics.json    machine-readable summary table
  paper/data/cross_event_table.md         paste-into-LaTeX-via-pandoc style
  paper/data/cross_event_table.tex        LaTeX-direct booktabs table

Usage:
    python paper/scripts/aggregate_metrics.py

This is a *reporter*, not a gate: it works with whatever subset of per-event
JSONs already exist on disk and reports gaps explicitly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PAPER_DATA = Path(__file__).resolve().parents[1] / "data"

# The canonical event ordering of the paper case-study section.
EVENTS = [
    {"slug": "mandra",    "label": "Mandra (EMSR257)",    "date": "2017-11-15"},
    {"slug": "strymonas", "label": "Strymonas (EMSR122)", "date": "2015-03-31"},
    {"slug": "pineios",   "label": "Pineios (EMSR692)",   "date": "2023-09-06"},
]


def _read_json(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARN: failed to parse {p}: {e}", file=sys.stderr)
        return None


def _f(v, n=3, na="—"):
    if v is None:
        return na
    if isinstance(v, float) and v != v:  # NaN
        return na
    try:
        return f"{float(v):.{n}f}"
    except Exception:
        return na


def main():
    rows = []
    for e in EVENTS:
        enh = _read_json(PAPER_DATA / f"{e['slug']}_metrics.json")
        bas = _read_json(PAPER_DATA / f"{e['slug']}_baseline_metrics.json")
        row = {
            "slug": e["slug"], "label": e["label"], "date": e["date"],
            "enhanced_available": enh is not None,
            "baseline_available": bas is not None,
        }
        if enh:
            primary = enh["ems"]["metrics_by_threshold"].get("h>0.10m", {})
            row["enhanced_csi"] = primary.get("csi")
            row["enhanced_hr"] = primary.get("hr")
            row["enhanced_far"] = primary.get("far")
            row["enhanced_f1"] = primary.get("f1")
            row["enhanced_peak_depth_m"] = enh["run"]["peak_max_depth_m"]
            row["enhanced_peak_area_km2"] = enh["run"]["peak_flooded_km2"]
            row["enhanced_rain_total_mm"] = enh["forcing"]["domain_mean_total_mm"]
            row["enhanced_rain_peak_mmph"] = enh["forcing"]["domain_mean_peak_intensity_mmph"]
            row["enhanced_rain_source"] = enh["forcing"]["rain_source"]
            row["evaluation_area_km2"] = enh["ems"]["evaluation_area_km2"]
            row["ems_wet_in_eval_km2"] = enh["ems"]["observed_wet_in_eval_area_km2"]
            row["delta_vs_baseline"] = enh.get("delta_vs_baseline", {})
        if bas:
            primary = bas["ems"]["metrics_by_threshold"].get("h>0.10m", {})
            row["baseline_csi"] = primary.get("csi")
            row["baseline_hr"] = primary.get("hr")
            row["baseline_far"] = primary.get("far")
            row["baseline_f1"] = primary.get("f1")
            row["baseline_rain_total_mm"] = bas["forcing"]["domain_mean_total_mm"]
            row["baseline_rain_peak_mmph"] = bas["forcing"]["domain_mean_peak_intensity_mmph"]
            row["baseline_peak_depth_m"] = bas["run"]["peak_max_depth_m"]
            row["baseline_peak_area_km2"] = bas["run"]["peak_flooded_km2"]
        rows.append(row)

    out_json = PAPER_DATA / "cross_event_metrics.json"
    out_json.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    print(f"wrote: {out_json}")

    # Markdown table — readable in the README and pasteable
    md = [
        "# Cross-event metrics summary",
        "",
        "## Enhanced runs (h > 0.10 m, on the SFINCS grid restricted to EMS AOIs)",
        "",
        "| Event | Rain | Total (mm) | Peak (mm/h) | CSI | HR | FAR | F1 | Peak depth (m) | Peak area (km²) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        if r["enhanced_available"]:
            md.append(
                f"| {r['label']} | {r['enhanced_rain_source']} | "
                f"{_f(r['enhanced_rain_total_mm'], 1)} | "
                f"{_f(r['enhanced_rain_peak_mmph'], 2)} | "
                f"{_f(r.get('enhanced_csi'))} | "
                f"{_f(r.get('enhanced_hr'))} | "
                f"{_f(r.get('enhanced_far'))} | "
                f"{_f(r.get('enhanced_f1'))} | "
                f"{_f(r.get('enhanced_peak_depth_m'), 2)} | "
                f"{_f(r.get('enhanced_peak_area_km2'), 1)} |"
            )
        else:
            md.append(f"| {r['label']} | _pending_ | — | — | — | — | — | — | — | — |")

    md += [
        "",
        "## Baseline rain-on-grid + ERA5 (same EMS rasterisation)",
        "",
        "| Event | Total (mm) | Peak (mm/h) | CSI | HR | FAR | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        if r["baseline_available"]:
            md.append(
                f"| {r['label']} | "
                f"{_f(r['baseline_rain_total_mm'], 1)} | "
                f"{_f(r['baseline_rain_peak_mmph'], 2)} | "
                f"{_f(r.get('baseline_csi'))} | "
                f"{_f(r.get('baseline_hr'))} | "
                f"{_f(r.get('baseline_far'))} | "
                f"{_f(r.get('baseline_f1'))} |"
            )
        else:
            md.append(f"| {r['label']} | — | — | — | — | — | — |")

    md += [
        "",
        "## Δ enhanced − baseline (same grid, h > 0.10 m)",
        "",
        "| Event | ΔCSI | ΔHR | ΔFAR | Δpeak depth (m) | Δpeak area (km²) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        d = r.get("delta_vs_baseline") or {}
        if d.get("available"):
            md.append(
                f"| {r['label']} | "
                f"{_f(d.get('delta_csi'))} | "
                f"{_f(d.get('delta_hr'))} | "
                f"{_f(d.get('delta_far'))} | "
                f"{_f(d.get('delta_peak_depth_m'), 2)} | "
                f"{_f(d.get('delta_peak_flooded_km2'), 1)} |"
            )
        else:
            md.append(f"| {r['label']} | — | — | — | — | — |")

    out_md = PAPER_DATA / "cross_event_table.md"
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote: {out_md}")

    # LaTeX-direct table for Section 5
    tex = [
        "% Cross-event metric table — auto-generated from per-event JSONs.",
        "% Regenerate with: python paper/scripts/aggregate_metrics.py",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \caption{Cross-event quantitative validation: enhanced forcing protocol vs.\ baseline rain-on-grid + ERA5. CSI/HR/FAR are evaluated pixel-wise on the SFINCS grid restricted to the union of Copernicus EMS AOIs, at the canonical $h_{\max} > 0.10$~m threshold. The $\Delta$ rows isolate the contribution of the enhanced forcing protocol from the underlying solver and DEM.}",
        r"  \label{tab:cross_event}",
        r"  \begin{tabular}{lrrrrrr}",
        r"    \toprule",
        r"    & \multicolumn{3}{c}{Enhanced} & \multicolumn{3}{c}{$\Delta$ vs.\ baseline} \\",
        r"    \cmidrule(lr){2-4} \cmidrule(lr){5-7}",
        r"    Event & CSI & HR & FAR & $\Delta$CSI & $\Delta$HR & $\Delta$FAR \\",
        r"    \midrule",
    ]
    for r in rows:
        d = r.get("delta_vs_baseline") or {}
        if r["enhanced_available"]:
            tex.append(
                f"    {r['label']} & "
                f"{_f(r.get('enhanced_csi'))} & "
                f"{_f(r.get('enhanced_hr'))} & "
                f"{_f(r.get('enhanced_far'))} & "
                f"{_f(d.get('delta_csi'))} & "
                f"{_f(d.get('delta_hr'))} & "
                f"{_f(d.get('delta_far'))} \\\\"
            )
        else:
            tex.append(f"    {r['label']} & — & — & — & — & — & — \\\\")
    tex += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ]
    out_tex = PAPER_DATA / "cross_event_table.tex"
    out_tex.write_text("\n".join(tex), encoding="utf-8")
    print(f"wrote: {out_tex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
