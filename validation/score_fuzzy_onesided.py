"""V3 fix — re-score the three canonical runs with TRUE one-sided fuzzy.

Re-validates the stored sfincs_map.nc of each canonical run (NO SFINCS re-run)
through validate_event_v2.py (which now emits, per r, the symmetric block plus
two genuine one-sided directions), then writes:

  docs/fuzzy_onesided.json   — strict + symmetric + model-oriented + obs-oriented
  docs/fuzzy_onesided.md      — comparison table

Strict (r=0) is the regression anchor: r=0 of every direction must equal the
published strict@0.10m metrics. Run with the sfincs-viz python:

  <env>/python.exe validation/score_fuzzy_onesided.py
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ELKAK = REPO.parent
DOCS = REPO / "docs"
EX = REPO / "skill" / "examples"
VALIDATOR = REPO / "validation" / "validate_event_v2.py"
# GDAL_DATA for the subprocess (machine-local sfincs-viz env).
GDAL = os.environ.get("SFINCS_GDAL_DATA") or os.environ.get("GDAL_DATA") or \
    r"C:/Users/dvalsamis/AppData/Local/anaconda3/envs/sfincs-viz/Library/share/gdal"

# (label, slug, example yaml, canonical stored work_dir, model subdir, AUDIT strict anchor csi/hr)
# Strymonas: model/ now holds the fresh numpy-2.4.6 re-run (0.182/0.322); the
# PUBLISHED canonical output is the author reference (model_author_ref/, 0.183/
# 0.328) per docs/AUDIT.md — so we score that, staged via a junction.
CANON = [
    ("Pineios EMSR692 (v1 enhanced)", "pineios", "emsr692_pineios_enhanced",
     ELKAK / "implementation" / "pineios_sfincs_enhanced", "model", (0.456, 0.947)),
    ("Strymonas EMSR122 (v3)", "strymonas", "emsr122_strymonas_enhanced",
     ELKAK / "implementation" / "emsr122_sfincs_v3", "model_author_ref", (0.183, 0.328)),
    ("Mandra EMSR257 (v1 enhanced)", "mandra", "emsr257_mandra_enhanced",
     ELKAK / "implementation" / "mandra_sfincs_enhanced", "model", (0.106, 0.873)),
]
RADII = (0, 1, 2, 3)


def _win(p: Path) -> str:
    return str(p).replace("/", "\\")


def _stage_workdir(work_dir: Path, model_name: str, cleanup: list) -> Path:
    """Return a work_dir whose 'model' resolves to model_name. If model_name is
    'model' use work_dir directly; else junction-stage model+data into a temp dir
    so the validator (which hardcodes work_dir/model) reads the chosen output."""
    if model_name == "model":
        return work_dir
    stage = Path(tempfile.mkdtemp(prefix=f"fz_stage_{work_dir.name}_"))
    for link_name, target in (("model", work_dir / model_name), ("data", work_dir / "data")):
        link = stage / link_name
        subprocess.run(["cmd", "/c", "mklink", "/J", _win(link), _win(target)],
                       capture_output=True, check=True)
        cleanup.append(link)
    cleanup.append(stage)
    return stage


def revalidate(example_yaml: Path, work_dir: Path, model_name: str) -> dict:
    import yaml
    cleanup: list = []
    try:
        staged = _stage_workdir(work_dir, model_name, cleanup)
        raw = yaml.safe_load(example_yaml.read_text(encoding="utf-8"))
        raw.setdefault("paths", {})
        raw["paths"]["work_dir"] = str(staged)
        raw["paths"]["deliverable_dir"] = str(staged.parent / (staged.name + "_deliv"))
        raw["paths"]["zip_dir"] = str(staged.parent)
        tmp_cfg = Path(tempfile.gettempdir()) / f"fz_cfg_{work_dir.name}.yaml"
        tmp_cfg.write_text(yaml.safe_dump(raw), encoding="utf-8")
        tmp_json = Path(tempfile.gettempdir()) / f"fz_val_{work_dir.name}.json"
        env = dict(os.environ, GDAL_DATA=GDAL)
        r = subprocess.run([sys.executable, str(VALIDATOR),
                            "--config", str(tmp_cfg), "--out-json", str(tmp_json)],
                           env=env)
        if r.returncode != 0:
            raise SystemExit(f"validator failed for {work_dir}")
        return json.loads(tmp_json.read_text(encoding="utf-8"))["validation"]
    finally:
        # Remove junctions first (rmdir on a junction drops only the reparse
        # point, never the target), then the staging dir.
        for p in cleanup:
            subprocess.run(["cmd", "/c", "rmdir", _win(p)], capture_output=True)


def pick(block: dict, r: int) -> dict:
    c = block[f"r={r}"]
    return {k: c[k] for k in ("csi", "hr", "far", "bias", "gss", "tp", "fp", "fn")}


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    results = {}
    anchor_report = []
    for label, slug, yaml_stub, work_dir, model_name, (acsi, ahr) in CANON:
        nc = work_dir / model_name / "sfincs_map.nc"
        if not nc.exists():
            raise SystemExit(f"missing stored output: {nc}")
        print(f"\n### {label}  ({work_dir.name}/{model_name}) ###", flush=True)
        v = revalidate(EX / f"{yaml_stub}.yaml", work_dir, model_name)
        strict = v["strict_threshold_sweep"]["h>0.10m"]
        sym = v["fuzzy_at_h_gt_0p10m"]
        mo = v["fuzzy_model_oriented_dilate_obs_at_h_gt_0p10m"]
        oo = v["fuzzy_obs_oriented_dilate_model_at_h_gt_0p10m"]
        # Strict anchor guard: r=0 of each one-sided direction == strict@0.10m.
        for name, blk in (("symmetric", sym), ("model_oriented", mo), ("obs_oriented", oo)):
            r0 = blk["r=0"]
            assert abs(r0["csi"] - strict["csi"]) < 1e-9 and abs(r0["hr"] - strict["hr"]) < 1e-9, \
                f"{slug} {name} r=0 != strict ({r0['csi']} vs {strict['csi']})"
        d_csi = abs(round(strict["csi"], 3) - acsi)
        d_hr = abs(round(strict["hr"], 3) - ahr)
        ok = d_csi <= 0.001 and d_hr <= 0.001
        anchor_report.append((label, round(strict["csi"], 3), round(strict["hr"], 3), acsi, ahr, ok))
        print(f"  strict@0.10m CSI={strict['csi']:.3f} HR={strict['hr']:.3f} "
              f"(anchor {acsi}/{ahr}) {'OK' if ok else 'DRIFT!'}", flush=True)
        results[slug] = {
            "label": label, "work_dir": str(work_dir),
            "strict_h0p10m": {k: strict[k] for k in ("csi", "hr", "far", "bias", "gss")},
            "symmetric": {f"r={r}": pick(sym, r) for r in RADII},
            "model_oriented_dilate_obs": {f"r={r}": pick(mo, r) for r in RADII},
            "obs_oriented_dilate_model": {f"r={r}": pick(oo, r) for r in RADII},
        }

    out_json = DOCS / "fuzzy_onesided.json"
    out_json.write_text(json.dumps({
        "note": ("One-sided fuzzy re-scoring of the canonical runs (V3 fix). "
                 "model_oriented dilates OBS only (tolerant FAR/precision); "
                 "obs_oriented dilates MODEL only (tolerant HR/recall); symmetric "
                 "dilates both (kept for comparison). r=0 == strict@0.10m anchor."),
        "results": results,
    }, indent=2), encoding="utf-8")
    print(f"\nwrote: {out_json}")

    # Markdown
    md = ["# One-sided fuzzy validation of the canonical runs (V3 fix)", "",
          "Strict (r=0) is unchanged from the published headline numbers. The previous "
          "\"asymmetric (Wing 2017)\" block dilated **both** fields, so it was byte-identical "
          "to the symmetric block; this table replaces it with two genuine one-sided "
          "directions.", "",
          "- **Symmetric** — dilate BOTH model & obs (over-counts agreement; kept for comparison).",
          "- **Model-oriented (dilate OBS only)** — a modelled wet cell is a hit if an observed "
          "cell is within *r*; FAR/precision-meaningful.",
          "- **Obs-oriented (dilate MODEL only)** — an observed wet cell is detected if a modelled "
          "cell is within *r*; HR/recall-meaningful.", ""]
    for label, slug, *_ in CANON:
        rr = results[slug]
        md += [f"## {label}", "",
               "| r | sym CSI | sym HR | sym FAR | mdl-orient CSI | mdl-orient HR | mdl-orient FAR "
               "| obs-orient CSI | obs-orient HR | obs-orient FAR |",
               "|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|"]
        for r in RADII:
            s = rr["symmetric"][f"r={r}"]
            m = rr["model_oriented_dilate_obs"][f"r={r}"]
            o = rr["obs_oriented_dilate_model"][f"r={r}"]
            tag = " (=strict)" if r == 0 else ""
            md.append(f"| {r}{tag} | {s['csi']:.3f} | {s['hr']:.3f} | {s['far']:.3f} "
                      f"| {m['csi']:.3f} | {m['hr']:.3f} | {m['far']:.3f} "
                      f"| {o['csi']:.3f} | {o['hr']:.3f} | {o['far']:.3f} |")
        md.append("")
    out_md = DOCS / "fuzzy_onesided.md"
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote: {out_md}")

    print("\n=== strict anchor check ===")
    allok = True
    for label, csi, hr, acsi, ahr, ok in anchor_report:
        allok = allok and ok
        print(f"  {'OK ' if ok else 'BAD'}  {label}: {csi}/{hr} vs {acsi}/{ahr}")
    print("STRICT ANCHOR PRESERVED" if allok else "STRICT ANCHOR DRIFT — INVESTIGATE")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
