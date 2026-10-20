"""Phase 4 (GO Phases 3-5, 2026-10-19) — post-processing of the v1.4 outputs, all six events, new mask. No SFINCS run.

Per finished run (record + v14 JSON present): truth-buffer sweep (±20 m), time-matched diagnostic, rainfall diagnostics
(+ series CSV), map figure (+ CSV). Then: cross-event JSON/MD (Tables 9/10/13/14 equivalents), Fig 10/11 equivalents,
Fig 4/6 equivalents (rain series), and the Phase-4 manifest. Every product goes under reproduction/v14_rerun/phase4/.
Usage: python -I phase4.py --repo <worktree> [--runs a,b,...] [--skip-existing]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CANONICAL = ["pineios_enhanced", "pineios_baseline_gridmatched", "mandra_enhanced", "mandra_baseline", "strymonas_enhanced_postD6", "strymonas_baseline",
             "valencia_enhanced_164", "emilia_enhanced_8aoi", "crete_baseline", "crete_canonical_r2on"]
SENSITIVITY = ["strymonas_leadin7d", "pineios_timevarying_q", "pineios_qinf5", "pineios_raw_imerg", "valencia_raw_imerg", "crete_sens_r2off",
               "crete_sens_anchor_224", "crete_sens_anchor_336", "crete_sens_anchor_582", "crete_sens_karst_q1914"]
# CODE-14 (2026-10-20): harness v1.4.1 re-runs of the D7-affected Pineios runs (+ the labelled D8 diagnostic) and MANIFEST row 16
V141 = ["pineios_enhanced_v141", "pineios_r2_220_v141", "pineios_r2_295_v141", "pineios_r2_510_v141", "pineios_cn_on_v141", "pineios_raw_imerg_v141",
        "pineios_qinf5_v141", "pineios_enhanced_v141_d8titarisios", "mandra_v3_maskrestrict"]
# CODE-15 (2026-10-20): harness v1.4.2 re-runs (D8 source-point resolution) of every run whose injected series or cells changed
V142 = [f"{b}_v142" for b in ("pineios_enhanced", "pineios_r2_220", "pineios_r2_295", "pineios_r2_510", "pineios_cn_on", "pineios_raw_imerg", "pineios_qinf5", "pineios_timevarying_q",
                               "emilia_enhanced_8aoi", "valencia_enhanced_164", "valencia_raw_imerg", "strymonas_enhanced_postD6", "strymonas_abl_cnoff_q", "strymonas_leadin7d", "strymonas_v1_prefix_src")]
CRETE_CLUSTERS = ["Lefka_Ori=23.75,35.15,24.25,35.55", "Psiloritis=24.60,35.05,25.05,35.40", "Dikti_Lasithi=25.30,34.95,25.80,35.30"]
TITLES = {"pineios_enhanced": "Pineios (EMSR692) enhanced", "pineios_baseline_gridmatched": "Pineios grid-matched baseline", "mandra_enhanced": "Mandra (EMSR257) enhanced",
          "mandra_baseline": "Mandra baseline", "strymonas_enhanced_postD6": "Strymonas (EMSR122) enhanced v3 (D6)", "strymonas_baseline": "Strymonas baseline",
          "valencia_enhanced_164": "Valencia (EMSR773) R2 164 mm", "emilia_enhanced_8aoi": "Emilia-Romagna (EMSR664) 8-AOI", "crete_baseline": "Crete (EMSR933) baseline",
          "crete_canonical_r2on": "Crete (EMSR933) canonical R2 on", "pineios_enhanced_v141": "Pineios (EMSR692) enhanced, harness v1.4.1 (D7 fix)",
          "pineios_enhanced_v141_d8titarisios": "Pineios (EMSR692) v1.4.1, D8 diagnostic (Titarisios cell)", "mandra_v3_maskrestrict": "Mandra (EMSR257) v3 mask restriction on the v1.4 build",
          "pineios_enhanced_v142": "Pineios (EMSR692) enhanced, harness v1.4.2 (D8 sources)", "strymonas_enhanced_postD6_v142": "Strymonas (EMSR122) enhanced v3 (D6), harness v1.4.2",
          "valencia_enhanced_164_v142": "Valencia (EMSR773) R2 164 mm, harness v1.4.2", "emilia_enhanced_8aoi_v142": "Emilia-Romagna (EMSR664) 8-AOI, harness v1.4.2"}
WINDOWS = {"strymonas_leadin7d": "canonical=2015-03-28T00:00,2015-04-04T00:00"}


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--runs", default="")
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import _load_machine_override
    ov = _load_machine_override(); py = ov["env"]["python"]
    env = dict(os.environ); env["GDAL_DATA"] = ov["env"].get("gdal_data", env.get("GDAL_DATA", "")); env["PYTHONIOENCODING"] = "utf-8"
    R = repo / "reproduction" / "v14_rerun"; res, cfgs, masks, S = R / "results", R / "configs", R / "masks", R / "scripts"
    P4 = R / "phase4"
    for d in ("truth_buffer", "time_matched", "rain", "figures", "logs"):
        (P4 / d).mkdir(parents=True, exist_ok=True)
    sel = [x for x in a.runs.split(",") if x] or (CANONICAL + SENSITIVITY + V141 + V142)
    manifest = {"utc_start": utc(), "runs": {}}

    def run(cmd, logname):
        t0 = time.time()
        with open(P4 / "logs" / f"{logname}.log", "w", encoding="utf-8") as fh:
            r = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)
        return {"exit": r.returncode, "wall_s": round(time.time() - t0, 1)}

    for name in sel:
        rec = res / f"{name}_record.json"; v14 = res / f"{name}_v14_newmask.json"; cfg = cfgs / f"{name}.yaml"
        if not (rec.exists() and v14.exists() and cfg.exists()):
            manifest["runs"][name] = {"status": "not finished"}; print(f"[{utc()}] {name}: not finished, skipped", flush=True); continue
        event = json.loads(rec.read_text(encoding="utf-8"))["event"]
        excl = masks / f"{event}_exclusion.tif"
        m = {"event": event}
        tb = P4 / "truth_buffer" / f"{name}_v14.json"
        if not (a.skip_existing and tb.exists()):
            m["truth_buffer"] = run([py, "-I", str(S / "truth_buffer_scores.py"), "--repo", str(repo), "--config", str(cfg), "--exclusion-tif", str(excl), "--out-json", str(tb)], f"{name}_truth_buffer")
        tm = P4 / "time_matched" / f"{name}_v14.json"
        if not (a.skip_existing and tm.exists()):
            cmd = [py, "-I", str(S / "time_matched_scores.py"), "--repo", str(repo), "--config", str(cfg), "--exclusion-tif", str(excl), "--out-json", str(tm)]
            if name in WINDOWS:
                cmd += ["--window", WINDOWS[name].split("=", 1)[1]]
            m["time_matched"] = run(cmd, f"{name}_time_matched")
        rj = P4 / "rain" / f"{name}_v14.json"
        if not (a.skip_existing and rj.exists()):
            m["rain"] = run([py, "-I", str(S / "rain_diagnostics.py"), "--repo", str(repo), "--config", str(cfg), "--out-json", str(rj)], f"{name}_rain")
        png = P4 / "figures" / f"map_{name}_v14.png"
        if not (a.skip_existing and png.exists()):
            # Crete: the all-AOI union is not a headline (rule_ledger §8) -> no union numbers in the figure titles; the tier-1 score is in the tiers JSON
            metrics = [] if event == "crete" else ["--metrics", str(v14)]
            cmd = [py, "-I", str(S / "fig_map_v14.py"), "--repo", str(repo), "--config", str(cfg), "--exclusion-tif", str(excl), *metrics, "--out", str(png),
                   "--title", TITLES.get(name, name) + " — harness v1.4"]
            if event == "crete":
                for c in CRETE_CLUSTERS:
                    cmd += ["--clusters", c]
            m["map"] = run(cmd, f"{name}_map")
            if event == "crete":
                m["map_island"] = run([py, "-I", str(S / "fig_map_v14.py"), "--repo", str(repo), "--config", str(cfg), "--exclusion-tif", str(excl),
                                       "--out", str(P4 / "figures" / f"map_{name}_island_v14.png"), "--title", TITLES.get(name, name) + " — island, harness v1.4"], f"{name}_map_island")
        series = P4 / "rain" / f"{name}_v14_series.csv"
        if series.exists() and name in ("pineios_enhanced", "mandra_enhanced", "strymonas_enhanced_postD6", "valencia_enhanced_164", "emilia_enhanced_8aoi", "crete_canonical_r2on", "pineios_enhanced_v141"):
            m["rain_fig"] = run([py, "-I", str(S / "fig_rain_v14.py"), "--series", str(series), "--json", str(rj), "--out", str(P4 / "figures" / f"rain_{name}_v14.png"),
                                 "--title", TITLES.get(name, name) + ": domain-mean precipitation (v1.4 forcing files)"], f"{name}_rain_fig")
        manifest["runs"][name] = m
        print(f"[{utc()}] {name}: {m}", flush=True)
    manifest["cross_event"] = run([py, "-I", str(S / "cross_event_v14.py"), "--repo", str(repo)], "cross_event")
    manifest["fig_skill_sweeps"] = run([py, "-I", str(S / "fig_skill_sweeps_v14.py"), "--repo", str(repo)], "fig_skill_sweeps")
    manifest["utc_end"] = utc()
    (P4 / "phase4_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "runs"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
