"""Phase 4a (GO Phases 3-5, 2026-10-19) — the cross-event JSON for the manuscript tables, harness v1.4 beside v1.3.

Reads the per-run validation JSONs of reproduction/v14_rerun/results (v1.4 new mask; v1.3 published mask; v1.3 new mask),
the Phase-4 diagnostics (truth buffer, time-matched, rainfall) when present, and writes
  reproduction/v14_rerun/phase4/cross_event_v14.json   every number the tables need, with its source file
  reproduction/v14_rerun/phase4/cross_event_v14.md     Table 9 / 10 / 13 / 14 equivalents (+ sweeps, fuzzy, buffer)
Table equivalents (R5 numbering): 9 strict + fuzzy r = 1 per event; 10 baseline vs enhanced Δ (Strymonas, Mandra, Pineios
grid-matched); 13 held-out (Valencia, Emilia, Crete Tzermiado tier 1); 14 CSI / SEDI / PSS / B / CSI* / B* (CSI* = max over the
hmax sweep 0.05/0.10/0.25/0.50 m, B* = bias there).
Usage: python -I cross_event_v14.py --repo <worktree>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

EVENTS = [  # (label, enhanced run, baseline run or None, held-out?)
    ("Pineios (EMSR692)", "pineios_enhanced", "pineios_baseline_gridmatched", False),
    ("Mandra (EMSR257)", "mandra_enhanced", "mandra_baseline", False),
    ("Strymonas (EMSR122)", "strymonas_enhanced_postD6", "strymonas_baseline", False),
    ("Valencia (EMSR773)", "valencia_enhanced_164", None, True),
    ("Emilia-R. (EMSR664)", "emilia_enhanced_8aoi", None, True),
    ("Crete Tzermiado (EMSR933, tier 1)", "crete_canonical_r2on", "crete_baseline", True),
]
THR = ("h>0.05m", "h>0.10m", "h>0.25m", "h>0.50m")


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def sweep(v):
    return v["validation"]["strict_threshold_sweep"]


def strict(v):
    return sweep(v)["h>0.10m"]


def fz(v, r=1):
    return v["validation"]["fuzzy_at_h_gt_0p10m"][f"r={r}"]


def csi_star(v):
    best = max(sweep(v).items(), key=lambda kv: (kv[1]["csi"] if kv[1]["csi"] == kv[1]["csi"] else -1))
    return best[0], best[1]["csi"], best[1]["bias"]


def tier1(v, token="AOI03"):
    """Crete: the scored row is the per-AOI block of Tzermiado (tier 1), not the all-AOI union."""
    for a in v["validation"]["per_aoi_canonical_and_r1"]:
        if token in a["aoi_file"]:
            return a
    return None


def block(v, aoi_token=None, tiers=None):
    if v is None:
        return None
    if aoi_token:
        a = tier1(v, aoi_token)
        if not a:
            return None
        s, f1 = a["strict"], a["fuzzy_r1"]
        out = {"strict": s, "fuzzy_r1": f1, "eval_km2": a["active_km2"], "obs_km2": a["ems_wet_km2_strict"], "per_aoi": True, "sweep": None, "csi_star": None}
        t = (tiers or {}).get("aois", {}).get(aoi_token[-2:]) if tiers else None
        if t and t.get("strict_threshold_sweep"):            # crete_tier_scores.py: the tier-1 sweep, CSI*, fuzzy r = 0..3 on the AOI universe
            sw = t["strict_threshold_sweep"]
            out["sweep"] = {k: {m: sw[k][m] for m in ("tp", "fp", "fn", "tn", "csi", "hr", "far", "bias", "gss")} for k in THR if k in sw}
            out["csi_star"] = t["csi_star"]
            out["fuzzy"] = {r: t["fuzzy_at_h_gt_0p10m"][f"r={r}"]["csi"] for r in (0, 1, 2, 3)}
            out["fuzzy_model_oriented_r1"] = t["fuzzy_model_oriented_r1"]["csi"]; out["fuzzy_obs_oriented_r1"] = t["fuzzy_obs_oriented_r1"]["csi"]
            out["tiers_source"] = "phase5 tiers json"
        return out
    s = strict(v)
    th, cs, bs = csi_star(v)
    return {"strict": s, "fuzzy_r1": fz(v), "eval_km2": v["validation"]["evaluation_area_km2"], "obs_km2": v["validation"]["observed_wet_km2_strict"],
            "sweep": {k: {m: sweep(v)[k][m] for m in ("tp", "fp", "fn", "tn", "csi", "hr", "far", "bias", "gss")} for k in THR if k in sweep(v)},
            "csi_star": {"threshold": th, "csi": cs, "bias": bs}, "fuzzy": {r: fz(v, r)["csi"] for r in (0, 1, 2, 3)},
            "fuzzy_model_oriented_r1": v["validation"]["fuzzy_model_oriented_dilate_obs_at_h_gt_0p10m"]["r=1"]["csi"],
            "fuzzy_obs_oriented_r1": v["validation"]["fuzzy_obs_oriented_dilate_model_at_h_gt_0p10m"]["r=1"]["csi"],
            "exclusion": v["validation"].get("evaluation_mask_exclusion")}


def skill(s):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "validation"))
    import skill_scores as ss
    return ss.skill_scores(s["tp"], s["fp"], s["fn"], s["tn"])


def f(x, nd=3):
    return "—" if x is None or x != x else f"{x:.{nd}f}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--enhanced-override", action="append", default=[], help="base_run=alternate_run, e.g. pineios_enhanced=pineios_enhanced_v141 (v1.3 columns stay with the base run)")
    ap.add_argument("--out-tag", default="", help="suffix of the output files, e.g. _v141 -> cross_event_v14_v141.{json,md}")
    ap.add_argument("--harness-label", default="v1.4", help="column label of the re-run harness, e.g. v1.4.1")
    a = ap.parse_args()
    OV = dict(x.split("=", 1) for x in a.enhanced_override)
    R = a.repo / "reproduction" / "v14_rerun"; res = R / "results"; P4 = R / "phase4"; P5 = R / "phase5"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {"utc": now, "generator": "reproduction/v14_rerun/scripts/cross_event_v14.py", "harness_label": a.harness_label, "enhanced_overrides": OV, "events": {}}
    for label, enh0, base, held in EVENTS:
        enh = OV.get(enh0, enh0)                                   # CODE-14: v1.4.1 re-run in place of the v1.4.0 run (same v1.3 columns)
        if enh != enh0:
            label = f"{label} [{a.harness_label}: {enh}]"
        tok = "AOI03" if enh.startswith("crete") else None
        e = {"label": label, "enhanced_run": enh, "enhanced_base_run": enh0, "baseline_run": base, "held_out": held, "scored_block": ("per-AOI Tzermiado (tier 1)" if tok else "AOI union"), "sources": {}}
        for tag, run in (("enhanced", enh), ("baseline", base)):
            if not run:
                continue
            for ver, suffix in (("v14", "_v14_newmask.json"), ("v13_published", "_v13_publishedmask.json"), ("v13_newmask", "_v13_newmask.json")):
                src = run
                if ver != "v14" and run == enh and enh != enh0:
                    src = enh0                                        # the v1.3 re-scoring of the same published output lives under the base run
                if ver != "v14" and src == "strymonas_enhanced_postD6":
                    src = "strymonas_enhanced"                    # v1.3 columns of the canonical Strymonas live under the Phase-1 name
                p = res / f"{src}{suffix}"
                b = block(J(p), tok, J(P5 / f"{run}_tiers.json") if tok else None)
                if b:
                    b["skill"] = skill(b["strict"]); e[f"{tag}_{ver}"] = b; e["sources"][f"{tag}_{ver}"] = str(p.relative_to(a.repo))
            rec = J(res / f"{run}_record.json")
            if rec:
                e[f"{tag}_record"] = {"sfincs_total_time_s": rec.get("sfincs_total_time_s"), "published_wallclock_s": rec.get("published_wallclock_s"), "end_utc": rec.get("end_utc"),
                                      "published_record_check": (rec.get("published_record_check") or {}).get("identical_tp_fp_fn_tn")}
            for diag, folder in (("truth_buffer", "truth_buffer"), ("time_matched", "time_matched"), ("rain", "rain")):
                p = P4 / folder / f"{run}_v14.json"
                if p.exists():
                    e.setdefault(f"{tag}_diagnostics", {})[diag] = str(p.relative_to(a.repo))
                    d = J(p)
                    if diag == "truth_buffer":
                        e.setdefault(f"{tag}_truth_buffer", {}).update({k: v["csi"] for k, v in d["sweep"].items()})
                    if diag == "time_matched":
                        u = d["union"]
                        e.setdefault(f"{tag}_time_matched", {}).update({"full": u["full_window"]["csi"], "to_earliest": u.get("hmax_to_earliest", {}).get("csi"), "to_latest": u.get("hmax_to_latest", {}).get("csi"),
                                                                          "earliest_acq": u.get("earliest_acq_utc"), "latest_acq": u.get("latest_acq_utc"), "n_products": d["n_products"]})
        if e.get("enhanced_v14") and e.get("baseline_v14"):
            s1, s0 = e["enhanced_v14"]["strict"], e["baseline_v14"]["strict"]
            e["delta_v14"] = {k: s1[k] - s0[k] for k in ("csi", "hr", "far", "bias", "gss")}
        if e.get("enhanced_v13_published") and e.get("baseline_v13_published"):
            s1, s0 = e["enhanced_v13_published"]["strict"], e["baseline_v13_published"]["strict"]
            e["delta_v13_published"] = {k: s1[k] - s0[k] for k in ("csi", "hr", "far", "bias", "gss")}
        out["events"][enh] = e
    P4.mkdir(parents=True, exist_ok=True)
    (P4 / f"cross_event_v14{a.out_tag}.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    # ---- markdown
    L = [f"# Cross-event tables under harness {a.harness_label} (new evaluation mask), v1.3 as published beside — generated {now}" + (f"; enhanced-run overrides {OV}" if OV else ""), "",
         f"Every number below is read from the JSON named in `cross_event_v14{a.out_tag}.json` → `events.<run>.sources`. Scores at h > 0.10 m unless stated; "
         "new mask = AOI ∩ active minus (WorldCover 80 ∪ v1.4 open sea), both sides. Crete = the Tzermiado per-AOI block (tier 1); no union score.", "",
         "## Table 9 equivalent — strict and fuzzy (r = 1) skill, enhanced runs", "",
         "| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.3 | HR v1.4 | FAR v1.3 | FAR v1.4 | B v1.3 | B v1.4 | GSS v1.4 | fuzzy r=1 CSI v1.3 | fuzzy r=1 CSI v1.4 | eval km² v1.4 | obs km² v1.4 |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for enh, e in out["events"].items():
        v, p = e.get("enhanced_v14"), e.get("enhanced_v13_published")
        if not v:
            L.append(f"| {e['label']} | pending | | | | | | | | | | | | |"); continue
        s = v["strict"]; q = p["strict"] if p else {}
        L.append(f"| {e['label']} | {f(q.get('csi'))} | **{f(s['csi'])}** | {f(q.get('hr'))} | {f(s['hr'])} | {f(q.get('far'))} | {f(s['far'])} | {f(q.get('bias'), 2)} | {f(s['bias'], 2)} | {f(s['gss'])} | "
                 f"{f(p['fuzzy_r1']['csi']) if p else '—'} | {f(v['fuzzy_r1']['csi'])} | {v['eval_km2']:.1f} | {v['obs_km2']:.1f} |")
    L += ["", "## Table 10 equivalent — enhanced minus baseline (same harness, same mask)", "",
          "| Event | baseline CSI v1.4 | enhanced CSI v1.4 | ΔCSI v1.4 | ΔHR v1.4 | ΔFAR v1.4 | ΔB v1.4 | ΔCSI v1.3 publ. | ΔHR v1.3 | ΔFAR v1.3 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for enh, e in out["events"].items():
        if not e.get("baseline_run"):
            continue
        d, d3 = e.get("delta_v14"), e.get("delta_v13_published")
        if not d:
            L.append(f"| {e['label']} | pending | | | | | | | | |"); continue
        L.append(f"| {e['label']} | {f(e['baseline_v14']['strict']['csi'])} | {f(e['enhanced_v14']['strict']['csi'])} | {d['csi']:+.3f} | {d['hr']:+.3f} | {d['far']:+.3f} | {d['bias']:+.2f} | "
                 + (f"{d3['csi']:+.3f} | {d3['hr']:+.3f} | {d3['far']:+.3f} |" if d3 else "— | — | — |"))
    L += ["", "## Table 13 equivalent — held-out events", "", "| Event | CSI v1.3 publ. | CSI v1.4 | HR v1.4 | FAR v1.4 | B v1.4 | GSS v1.4 | obs km² | eval km² | note |", "|---|---|---|---|---|---|---|---|---|---|"]
    for enh, e in out["events"].items():
        if not e["held_out"]:
            continue
        v, p = e.get("enhanced_v14"), e.get("enhanced_v13_published")
        if not v:
            L.append(f"| {e['label']} | pending | | | | | | | | |"); continue
        s = v["strict"]
        L.append(f"| {e['label']} | {f(p['strict']['csi']) if p else '—'} | **{f(s['csi'])}** | {f(s['hr'])} | {f(s['far'])} | {f(s['bias'], 2)} | {f(s['gss'])} | {v['obs_km2']:.1f} | {v['eval_km2']:.1f} | {e['scored_block']} |")
    L += ["", "## Table 14 equivalent — base-rate-robust skill (v1.4; v1.3 published in brackets)", "", "| Event | CSI | SEDI | PSS | B | CSI* (threshold) | B* |", "|---|---|---|---|---|---|---|"]
    for enh, e in out["events"].items():
        v, p = e.get("enhanced_v14"), e.get("enhanced_v13_published")
        if not v:
            L.append(f"| {e['label']} | pending | | | | | |"); continue
        s, k = v["strict"], v["skill"]
        pk = p["skill"] if p else {}
        cs = v.get("csi_star") or {}
        pcs = (p or {}).get("csi_star") or {}
        L.append(f"| {e['label']} | {f(s['csi'])} ({f(p['strict']['csi']) if p else '—'}) | {f(k['sedi'])} ({f(pk.get('sedi'))}) | {f(k['pss'])} ({f(pk.get('pss'))}) | {f(s['bias'], 2)} ({f((p or {}).get('strict', {}).get('bias'), 2)}) | "
                 f"{f(cs.get('csi'))} ({cs.get('threshold', '—')}) [{f(pcs.get('csi'))}] | {f(cs.get('bias'), 2)} [{f(pcs.get('bias'), 2)}] |")
    L += ["", "## Threshold sweep (v1.4, enhanced): CSI at 0.05 / 0.10 / 0.25 / 0.50 m; fuzzy r = 0..3; one-sided r = 1", "",
          "| Event | 0.05 | 0.10 | 0.25 | 0.50 | r=0 | r=1 | r=2 | r=3 | model-oriented r=1 | obs-oriented r=1 | truth buffer −20 / 0 / +20 m | time-matched (to latest acq) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for enh, e in out["events"].items():
        v = e.get("enhanced_v14")
        if not v or not v.get("sweep") or not v.get("fuzzy"):
            L.append(f"| {e['label']} | pending | | | | | | | | | | | |"); continue
        sw, fzz = v["sweep"], v["fuzzy"]
        tb = e.get("enhanced_truth_buffer") or {}
        tmd = e.get("enhanced_time_matched") or {}
        pre = "union: " if v.get("per_aoi") else ""          # the buffer / time-matched diagnostics run on the AOI union; Crete's headline block is per-AOI
        L.append(f"| {e['label']} | " + " | ".join(f(sw[k]['csi']) for k in THR) + " | " + " | ".join(f(fzz[r]) for r in (0, 1, 2, 3)) +
                 f" | {f(v['fuzzy_model_oriented_r1'])} | {f(v['fuzzy_obs_oriented_r1'])} | {pre}{f(tb.get('-20'))} / {f(tb.get('0'))} / {f(tb.get('20'))} | {pre}{f(tmd.get('to_latest'))} |")
    (P4 / f"cross_event_v14{a.out_tag}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
