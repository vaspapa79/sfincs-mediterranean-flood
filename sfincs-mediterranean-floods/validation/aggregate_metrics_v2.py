"""Aggregate the v2 metric reports into a single cross-event headline table.

Reads:
  paper/data/{mandra,strymonas,pineios}_metrics_v2.json
  paper/data/{mandra,strymonas,pineios}_metrics.json     (for forcing stats)

Writes:
  paper/data/cross_event_metrics_v2.json
  paper/data/cross_event_table_v2.tex
  paper/data/cross_event_table_v2.md
"""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

EVENTS = [
    ("mandra",    "Mandra (EMSR257)",    "2017-11-15"),
    ("strymonas", "Strymonas (EMSR122)", "2015-03-31"),
    ("pineios",   "Pineios (EMSR692)",   "2023-09-06"),
]


def _read(slug):
    v2 = json.loads((DATA / f"{slug}_metrics_v2.json").read_text(encoding="utf-8"))
    v1 = json.loads((DATA / f"{slug}_metrics.json").read_text(encoding="utf-8"))
    return v1, v2


def main():
    rows = []
    for slug, label, date in EVENTS:
        v1, v2 = _read(slug)
        val = v2["validation"]
        strict = val["strict_threshold_sweep"]["h>0.10m"]
        best_thr = val["best_csi_threshold_m"]
        strict_best = val["strict_threshold_sweep"][f"h>{best_thr:.2f}m"]
        fuzzy_r1 = val["fuzzy_at_h_gt_0p10m"]["r=1"]
        fuzzy_r2 = val["fuzzy_at_h_gt_0p10m"]["r=2"]
        rows.append({
            "slug": slug,
            "label": label,
            "date": date,
            "tol_m_r1": val.get("tolerance_radius_m_at_r1"),
            "eval_area_km2": val["evaluation_area_km2"],
            "ems_wet_km2": val["observed_wet_km2_strict"],
            "rain_source": v1.get("rain_source", "imerg_half_hourly"),
            "rain_total_mm": v1["forcing"]["domain_mean_total_mm"],
            "rain_peak_mmph": v1["forcing"]["domain_mean_peak_intensity_mmph"],
            "peak_depth_m": v1["run"]["peak_max_depth_m"],
            "peak_area_km2": v1["run"]["peak_flooded_km2"],
            "strict_h10": strict,
            "strict_best": {**strict_best, "threshold_m": best_thr},
            "fuzzy_r1": fuzzy_r1,
            "fuzzy_r2": fuzzy_r2,
        })
    # JSON
    out_json = DATA / "cross_event_metrics_v2.json"
    out_json.write_text(json.dumps(rows, indent=2, default=str),
                        encoding="utf-8")
    print(f"wrote: {out_json}")

    # LaTeX — headline table for the cross-event section
    tex = []
    tex.append(r"\begin{table}[t]")
    tex.append(r"  \centering")
    tex.append(r"  \caption{Cross-event headline pixel-wise validation. "
               r"\textbf{Strict (h$>$0.10\,m):} unbuffered comparison on the "
               r"SFINCS grid restricted to the union of EMS AOIs. "
               r"\textbf{Fuzzy ($r=1$):} morphological 1-cell tolerance "
               r"applied to both the modelled and the observed wet extent, "
               r"absorbing the SAR positional uncertainty + base-grid "
               r"resolution gap (Wing et al.\ 2017; Bates 2022). "
               r"\textbf{Best CSI} reports the threshold and CSI value at "
               r"which the threshold sweep peaks. "
               r"$B = (\mathrm{TP}+\mathrm{FP})/(\mathrm{TP}+\mathrm{FN})$ "
               r"is the frequency bias (B$>$1 over-prediction); "
               r"GSS is the Gilbert Skill Score "
               r"(base-rate-corrected CSI).}")
    tex.append(r"  \label{tab:cross_event_v2}")
    tex.append(r"  \small")
    tex.append(r"  \begin{tabular}{l rrrrr | rrr | rr}")
    tex.append(r"    \toprule")
    tex.append(r"    & \multicolumn{5}{c}{Strict (h$>$0.10\,m)} & \multicolumn{3}{c}{Fuzzy $r=1$ (50--150\,m)} & \multicolumn{2}{c}{Best CSI} \\")
    tex.append(r"    \cmidrule(lr){2-6} \cmidrule(lr){7-9} \cmidrule(lr){10-11}")
    tex.append(r"    Event & CSI & HR & FAR & B & GSS & CSI & HR & FAR & h$>$ & CSI \\")
    tex.append(r"    \midrule")
    for r in rows:
        s10 = r["strict_h10"]; f1 = r["fuzzy_r1"]; sb = r["strict_best"]
        tex.append(
            f"    {r['label']} "
            f"& {s10['csi']:.3f} & {s10['hr']:.3f} & {s10['far']:.3f} "
            f"& {s10['bias']:.2f} & {s10['gss']:.3f} "
            f"& {f1['csi']:.3f} & {f1['hr']:.3f} & {f1['far']:.3f} "
            f"& {sb['threshold_m']:.2f} & {sb['csi']:.3f} \\\\"
        )
    tex.append(r"    \bottomrule")
    tex.append(r"  \end{tabular}")
    tex.append(r"\end{table}")
    out_tex = DATA / "cross_event_table_v2.tex"
    out_tex.write_text("\n".join(tex) + "\n", encoding="utf-8")
    print(f"wrote: {out_tex}")

    # Markdown
    md = []
    md.append("# Cross-event headline pixel-wise validation (v2)")
    md.append("")
    md.append("Strict = h>0.10 m on SFINCS grid ∩ EMS AOIs. ")
    md.append("Fuzzy r=1 = 1-cell morphological tolerance on both model and obs ")
    md.append("(50 m for Mandra, 150 m for Strymonas/Pineios). ")
    md.append("Best CSI = peak of the threshold sweep.")
    md.append("")
    md.append("| Event | Strict CSI | HR | FAR | Bias | GSS | Fuzzy(r=1) CSI | HR | FAR | Best h | Best CSI |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        s10 = r["strict_h10"]; f1 = r["fuzzy_r1"]; sb = r["strict_best"]
        md.append(
            f"| {r['label']} "
            f"| {s10['csi']:.3f} | {s10['hr']:.3f} | {s10['far']:.3f} "
            f"| {s10['bias']:.2f} | {s10['gss']:.3f} "
            f"| {f1['csi']:.3f} | {f1['hr']:.3f} | {f1['far']:.3f} "
            f"| {sb['threshold_m']:.2f} m | {sb['csi']:.3f} |"
        )
    out_md = DATA / "cross_event_table_v2.md"
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote: {out_md}")


if __name__ == "__main__":
    main()
