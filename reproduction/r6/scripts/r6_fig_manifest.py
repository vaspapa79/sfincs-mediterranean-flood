"""R6 figure export (MESE close-out, part C) - verification of every written figure file + FIGURES_MANIFEST.md.

For each figures/meta/F<n>.json (written by r6_fig_common.export) re-open every file and check it against the export spec:
  * TIFF: RGB 8-bit, LZW, dpi tag = the declared dpi, pixel width = width_mm / 25.4 x dpi (+-1 px), height <= 234 mm,
    width 174 mm (two-column) or 84 mm (one-column);
  * preview PNG <= 2 MB;
and scan the texts drawn in the figure (recorded at export): no author name / affiliation (read from CITATION.cff), no URL,
DOI or repository name, no person-name citation, no 'published' wording; F9 (Crete) carries no score word at all (Crete is
scored on the tier-1 AOI03 block only, rule_ledger.md section 8 item 3; no all-AOI union score may appear).
Writes reproduction/r6/FIGURES_MANIFEST.md (one row per file). Fails (exit 1) on any violation.
Usage (sfincs-viz env): python -I r6_fig_manifest.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r6_fig_common as C  # noqa: E402

FIGS = ["F1", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11"]
SCORE_WORDS = re.compile(r"\b(CSI\*?|HR|FAR|GSS|SEDI|PSS|F2|bias|score|union)\b", re.I)


def forbidden_patterns():
    cff = (C.REPO / "CITATION.cff").read_text(encoding="utf-8")
    names = re.findall(r"family-names:\s*\"?([^\"\n]+)", cff)       # family names only: given names collide with place names
    affil = set(re.findall(r"affiliation:\s*\"([^\"]+)\"", cff))
    pats = [re.compile(re.escape(n.strip()), re.I) for n in names if len(n.strip()) > 3]
    for a in affil:
        pats += [re.compile(re.escape(part.strip()), re.I) for part in re.split(r"[,()]", a) if len(part.strip()) > 4 and part.strip() != "Greece"]
    pats += [re.compile(p, re.I) for p in (r"https?://", r"\bwww\.", r"\bdoi\b", r"10\.\d{4,}/", r"github", r"zenodo", r"orcid",
                                            r"\bCERTH\b", r"\bet al\b", r"published")]
    return pats, sorted(n.strip() for n in names)


def check_file(entry, column):
    from PIL import Image
    p = C.FIG_DIR / entry["file"]
    errs = []
    if not p.exists():
        return [f"{p.name} missing"], None
    with Image.open(p) as im:
        w, h = im.size
        info = dict(im.info)
        mode = im.mode
    nbytes = p.stat().st_size
    if [w, h] != list(entry["px"]):
        errs.append(f"{p.name}: size {w}x{h} != meta {entry['px']}")
    if p.suffix == ".tiff":
        dpi = info.get("dpi")
        if not dpi or abs(dpi[0] - entry["dpi"]) > 0.01 or abs(dpi[1] - entry["dpi"]) > 0.01:
            errs.append(f"{p.name}: dpi tag {dpi} != {entry['dpi']}")
        if info.get("compression") != "tiff_lzw":
            errs.append(f"{p.name}: compression {info.get('compression')} != tiff_lzw")
        if mode != "RGB":
            errs.append(f"{p.name}: mode {mode} != RGB")
        exp_w = entry["width_mm"] / 25.4 * entry["dpi"]
        exp_h = entry["height_mm"] / 25.4 * entry["dpi"]
        if abs(w - exp_w) > 1.0 or abs(h - exp_h) > 1.0:
            errs.append(f"{p.name}: {w}x{h} px != {exp_w:.1f}x{exp_h:.1f} px (width_mm/25.4 x dpi)")
        if entry["height_mm"] > C.MAX_HEIGHT_MM + 1e-6:
            errs.append(f"{p.name}: height {entry['height_mm']} mm > {C.MAX_HEIGHT_MM}")
        want = C.WIDTH_2COL_MM if column == "two-column" else C.WIDTH_1COL_MM
        if abs(entry["width_mm"] - want) > 0.01:
            errs.append(f"{p.name}: width {entry['width_mm']} mm != {want} mm ({column})")
        if entry["dpi"] != C.DPI_COMBINATION:
            errs.append(f"{p.name}: {entry['dpi']} dpi, but every figure here is line art / combination (600 dpi)")
    else:
        if nbytes > C.PREVIEW_MAX_BYTES:
            errs.append(f"{p.name}: {nbytes} bytes > 2 MB")
    return errs, {"w": w, "h": h, "bytes": nbytes}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pats, names = forbidden_patterns()
    rows, notes, problems = [], [], []
    for f in FIGS:
        mp = C.META_DIR / f"{f}.json"
        if not mp.exists():
            problems.append(f"{f}: no meta (figure not exported)")
            continue
        m = json.loads(mp.read_text(encoding="utf-8"))
        if m.get("layout_problems"):
            problems += [f"{f}: layout: {x}" for x in m["layout_problems"]]
        for t in m.get("texts_drawn", []):
            for pt in pats:
                if pt.search(t):
                    problems.append(f"{f}: forbidden text {t!r} (pattern {pt.pattern!r})")
            if f == "F9" and SCORE_WORDS.search(t):
                problems.append(f"F9: score word in {t!r} (Crete: tier-1 block only, nothing printed)")
        if not m.get("texts_drawn"):
            problems.append(f"{f}: no drawn-text record (re-export)")
        for e in m["files"]:
            errs, got = check_file(e, m["column"])
            problems += errs
            src = [f"`{m['script']}`"] + [f"`{C.portable(s)}`" for s in m["sources"]] if e["file"].endswith(".tiff") else [f"reduced from `{f}.tiff` (Lanczos)"]
            rows.append({"file": e["file"], "px": f"{got['w']} × {got['h']}" if got else "-", "dpi": e["dpi"], "width_mm": f"{e['width_mm']:g}",
                         "height_mm": f"{e['height_mm']:.1f}", "mb": f"{got['bytes'] / 1e6:.2f}" if got else "-", "src": "<br>".join(src),
                         "utc": e["generated_utc"], "check": "OK" if not errs else "FAIL"})
        notes.append((f, m["column"], m.get("notes", ""), len(m.get("texts_drawn", []))))
    out = C.R6 / "FIGURES_MANIFEST.md"
    L = ["# FIGURES_MANIFEST — R6 figure export (MESE close-out, part C)", "",
         f"Generated {C.utc_now()} by `{C.rel(Path(__file__))}` (verification of every file listed). Post-processing only: no SFINCS or "
         "pipeline step was run; inputs are the frozen v1.4.x records and model outputs named in the Source column; nothing outside "
         "`reproduction/r6/` was written.", "",
         "Export spec: TIFF, RGB 8-bit, LZW, **174 mm** wide (two-column; no figure fits one 84-mm column without losing the "
         "8-pt lettering or the map detail), height ≤ 234 mm, **600 dpi** for every figure (all are line art or combination "
         "figures — maps are raster + line/text; none is pure halftone, so 300 dpi is not used). Lettering sans-serif (Arial), 8 pt "
         "(panel letters 9 pt bold), checked on the rendered 600-dpi canvas (no text < 8 pt, within 0.3 mm of the edge, or "
         "overlapping another text). Pixel size verified as width_mm / 25.4 × dpi (± 1 px). Previews: reduced PNG ≤ 2 MB.", "",
         "F2 is not exported here (drawn by the author).", "",
         "| File | Pixel size (px) | dpi | Width (mm) | Height (mm) | Size (MB) | Source (script + inputs) | Generated (UTC) | Check |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| `{r['file']}` | {r['px']} | {r['dpi']} | {r['width_mm']} | {r['height_mm']} | {r['mb']} | {r['src']} | {r['utc']} | {r['check']} |")
    L += ["", "## Figure notes", ""]
    for f, col, n, k in notes:
        L.append(f"- **{f}** ({col}, 174 mm): {n}. Drawn texts scanned: {k}.")
    arch = sorted((C.FIG_DIR / "archive" / "meta").glob("*.json"))
    if arch:
        L += ["", "## Archived figures (`figures/archive/`, not used in the manuscript)", "",
              "| File | Pixel size (px) | Generated (UTC) | Why archived |", "|---|---|---|---|"]
        for mp in arch:
            m = json.loads(mp.read_text(encoding="utf-8"))
            for e in m["files"]:
                L.append(f"| `archive/{e['file']}` | {e['px'][0]} × {e['px'][1]} | {e['generated_utc']} | earlier export with the release v1.3.0 "
                         "series beside the run of record; superseded by the run-of-record-only figure (CODE-17 A3) |")
    L += ["", "## Content checks (run by this script)", "",
          f"- No author name or affiliation (the {len(names)} family names listed in `CITATION.cff`), URL, DOI, repository name, person-name "
          "citation or 'published' wording in any drawn text. Main-text figures show the run of record only (CODE-17 A1/A2): F10/F11 "
          "carry no earlier-release series and no version label; the previous F10/F11 with the release v1.3.0 series are kept under "
          "`figures/archive/` and are not used in the manuscript. Map legends read 'excluded from the evaluation universe (permanent "
          "water, open sea)' (A4).",
          "- F9 (Crete) draws no score word or number: Crete is scored on the tier-1 AOI03 block only (`rule_ledger.md` §8 item 3); "
          "the generator asserts the AOI03 contingency against `phase5/crete_canonical_r2on_tiers.json` and never computes the "
          "all-AOI union. F10 takes Crete from the tier-1 block (asserted against the tiers JSON).",
          "- F3/F5–F8: the strict contingency of the drawn fields on the v1.4 universe equals the run's `results/<run>_v14_newmask.json` "
          "(tp/fp/fn/tn asserted). F4: every total, peak and watershed-box value printed is read from `phase4/rain/<run>_v14.json` and "
          "asserted against the series CSV, the run configuration (watershed box, anchor, window) and the IMERG NetCDF files "
          "(watershed-box event totals recomputed, bias-correction attribute parsed).",
          "", "## Regenerate", "", "```",
          "SFV=<conda>/envs/sfincs-viz          # sfincs-viz env (xarray, rasterio, pyogrio)",
          "GDAL_DATA=$SFV/Library/share/gdal PROJ_LIB=$SFV/Library/share/proj $SFV/python.exe -I reproduction/r6/scripts/r6_figures.py --fig all",
          "<conda>/python.exe -I reproduction/r6/scripts/r6_fig1_overview.py   # cartopy env (base), cached Natural Earth only",
          "$SFV/python.exe -I reproduction/r6/scripts/r6_fig_manifest.py",
          "```", "",
          "`r6_figures.py --fig F1data` writes `figures/data/F1_inputs.json` (domain boxes + AOI centroids) for the cartopy step. "
          "F1's TIFF is written with tifffile/imagecodecs (LZW): the cartopy env's Pillow 10.0.1 / libtiff 4.5.0 crashes natively on "
          "LZW writes; the result is verified here like every other TIFF.", ""]
    if problems:
        L += ["## Problems", ""] + [f"- {p}" for p in problems] + [""]
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {C.rel(out)}: {len(rows)} files, {len(problems)} problem(s)")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
