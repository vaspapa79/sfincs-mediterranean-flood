"""Phase 4d (GO Phases 3-5, 2026-10-19) — Figure 10 and Figure 11 equivalents from the v1.4 JSON records, each PNG with the
data behind it as CSV.

  fig10_skill_v14.png / .csv   strict and fuzzy (r = 1) CSI per event (v1.4, new mask; v1.3 published as hollow markers)
                               against the benchmark bands quoted in the R5 Figure-10 caption (global multi-model 0.10-0.36,
                               Bernhofen et al. 2018; calibrated single-event 0.42-0.62, Hocini et al. 2021; Wing et al. 2017
                               median ~0.40) — the bands are literature constants, copied from the caption, not computed.
  fig11_sweeps_v14.png / .csv  (a) Pineios depth-threshold sweep CSI / HR / FAR; (b) Mandra fuzzy-tolerance sweep r = 0..3
                               CSI / HR / F2 — v1.4 solid, v1.3 published dashed.
Usage: python -I fig_skill_sweeps_v14.py --repo <worktree> [--out-dir reproduction/v14_rerun/phase4/figures]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BANDS = [("global multi-model (Bernhofen et al. 2018)", 0.10, 0.36, "#dddddd"), ("calibrated single-event (Hocini et al. 2021)", 0.42, 0.62, "#c8ddf0")]
WING_MEDIAN = 0.40
THR = [("h>0.05m", 0.05), ("h>0.10m", 0.10), ("h>0.25m", 0.25), ("h>0.50m", 0.50)]


def J(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--in-tag", default="", help="suffix of the cross_event JSON, e.g. _v141")
    ap.add_argument("--out-tag", default="", help="suffix of the figure/CSV names, e.g. _v141")
    ap.add_argument("--pineios-run", default="pineios_enhanced", help="run whose threshold sweep fills Fig 11a (e.g. pineios_enhanced_v141)")
    ap.add_argument("--harness-label", default="v1.4")
    a = ap.parse_args()
    T = a.out_tag; HL = a.harness_label
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 9, "savefig.dpi": 300})
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"
    out = a.out_dir or (R / "phase4" / "figures"); out.mkdir(parents=True, exist_ok=True)
    ce = J(R / "phase4" / f"cross_event_v14{a.in_tag}.json")
    if not ce:
        sys.exit("run cross_event_v14.py first")
    # ---- Fig 10
    rows = []
    for run, e in ce["events"].items():
        v, p = e.get("enhanced_v14"), e.get("enhanced_v13_published")
        if not v:
            continue
        rows.append({"event": e["label"], "run": run, "csi_strict_v14": v["strict"]["csi"], "csi_fuzzy_r1_v14": v["fuzzy_r1"]["csi"],
                     "csi_strict_v13_published": (p["strict"]["csi"] if p else None), "csi_fuzzy_r1_v13_published": (p["fuzzy_r1"]["csi"] if p else None),
                     "csi_star_v14": (v.get("csi_star") or {}).get("csi"), "csi_star_threshold": (v.get("csi_star") or {}).get("threshold")})
    with open(out / f"fig10_skill_v14{T}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    for lab, lo, hi, col in BANDS:
        ax.axhspan(lo, hi, color=col, zorder=0, label=lab)
    ax.axhline(WING_MEDIAN, color="grey", ls=":", lw=1, label="Wing et al. 2017 median ≈ 0.40")
    x = list(range(len(rows)))
    ax.plot(x, [r["csi_strict_v14"] for r in rows], "o", color="#1f4e79", label=f"strict CSI, {HL}")
    ax.plot(x, [r["csi_fuzzy_r1_v14"] for r in rows], "s", color="#2e8b57", label=f"fuzzy r = 1 CSI, {HL}")
    ax.plot(x, [r["csi_strict_v13_published"] for r in rows], "o", mfc="none", color="#1f4e79", label="strict CSI, v1.3 as published")
    ax.plot(x, [r["csi_fuzzy_r1_v13_published"] for r in rows], "s", mfc="none", color="#2e8b57", label="fuzzy r = 1, v1.3 as published")
    for i, r in enumerate(rows):
        if r["csi_star_v14"] is not None:
            ax.plot(i, r["csi_star_v14"], "^", color="#c0392b", ms=5, label=f"CSI* (best threshold), {HL}" if i == 0 else None)
    ax.set_xticks(x); ax.set_xticklabels([r["event"].split(" (")[0] for r in rows], rotation=15)
    ax.set_ylabel("CSI (hmax > 0.10 m)"); ax.set_ylim(0, 0.9); ax.set_title(f"Cross-event reproduction skill under harness {HL} (new evaluation mask)")
    ax.legend(fontsize=6.5, loc="upper left", ncol=2, frameon=False)
    fig.tight_layout(); fig.savefig(out / f"fig10_skill_v14{T}.png"); plt.close(fig)
    # ---- Fig 11
    pin14, pin13 = J(res / f"{a.pineios_run}_v14_newmask.json"), J(res / "pineios_enhanced_v13_publishedmask.json")
    man14, man13 = J(res / "mandra_enhanced_v14_newmask.json"), J(res / "mandra_enhanced_v13_publishedmask.json")
    crows = []
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.2))
    for tag, v, ls in ((HL, pin14, "-"), ("v1.3 published", pin13, "--")):
        if not v:
            continue
        sw = v["validation"]["strict_threshold_sweep"]
        xs = [t for k, t in THR if k in sw]
        for m, col in (("csi", "#1f4e79"), ("hr", "#2e8b57"), ("far", "#c0392b")):
            a1.plot(xs, [sw[k][m] for k, t in THR if k in sw], ls, marker="o", ms=3, color=col, label=f"{m.upper()} {tag}")
        for k, t in THR:
            if k in sw:
                crows.append({"panel": "a_pineios_threshold", "harness": tag, "x": t, "csi": sw[k]["csi"], "hr": sw[k]["hr"], "far": sw[k]["far"], "f2": sw[k]["f2"], "bias": sw[k]["bias"]})
    a1.set_xlabel("depth threshold hmax > x (m)"); a1.set_ylabel("score"); a1.set_title("(a) Pineios depth-threshold sweep"); a1.legend(fontsize=6, frameon=False, ncol=2)
    for tag, v, ls in ((HL if a.pineios_run == "pineios_enhanced" else "v1.4", man14, "-"), ("v1.3 published", man13, "--")):
        if not v:
            continue
        fzz = v["validation"]["fuzzy_at_h_gt_0p10m"]
        rs = [0, 1, 2, 3]
        for m, col in (("csi", "#1f4e79"), ("hr", "#2e8b57"), ("f2", "#8e44ad")):
            a2.plot(rs, [fzz[f"r={r}"][m] for r in rs], ls, marker="o", ms=3, color=col, label=f"{m.upper()} {tag}")
        for r in rs:
            crows.append({"panel": "b_mandra_fuzzy", "harness": tag, "x": r, "csi": fzz[f"r={r}"]["csi"], "hr": fzz[f"r={r}"]["hr"], "far": fzz[f"r={r}"]["far"], "f2": fzz[f"r={r}"]["f2"], "bias": fzz[f"r={r}"]["bias"]})
    a2.set_xlabel("neighbourhood radius r (cells of 50 m)"); a2.set_title("(b) Mandra fuzzy-tolerance sweep"); a2.legend(fontsize=6, frameon=False, ncol=2)
    fig.tight_layout(); fig.savefig(out / f"fig11_sweeps_v14{T}.png"); plt.close(fig)
    with open(out / f"fig11_sweeps_v14{T}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(crows[0].keys())); w.writeheader(); w.writerows(crows)
    print("wrote", out / f"fig10_skill_v14{T}.png", out / f"fig11_sweeps_v14{T}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
