"""CODE-20 A1 — the F10 v3 benchmark constants with the quotes behind each number: Bernhofen et al. (2018) average CSI range
0.45–0.70 (band) and Sadana et al. (2026) same-solver means 0.42 (upstream area ≥ 1000 km²) / 0.29 (< 50 km²) under GloFAS
forcing and 0.67 with observed discharge (lines). Quotes are regex-extracted from the PDF text (never retyped); the Bernhofen
quotes are those of the CODE-19 record (code19/lookups.json, D4_bernhofen2018) plus the MODIS sentence from the same text dump.
Also records what F10 v2 drew (fig_skill_sweeps_v14.BANDS, the section 4.7 claim, the Fig. 10 caption of the R6b manuscript).
Writes reproduction/v14_rerun/code20/f10_benchmarks.json, which r6_figures.fig10 asserts against its constants.

Usage (an interpreter with PyMuPDF): python -I code20_lookups.py --repo <worktree> --sadana-pdf <hess-30-5491-2026.pdf>
       [--bernhofen-txt <code19 text dump>] [--manuscript-txt <R6b text>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from code19_lookups import norm, pages, quote  # noqa: E402

SADANA_DOI = "10.5194/hess-30-5491-2026"
SADANA_URL = "https://hess.copernicus.org/articles/30/5491/2026/hess-30-5491-2026.pdf"
SADANA_FIRST_PAGE = 5491
BIB_KEY = "sadana2026validation"

CONSTANTS = {"band": {"label": "global models vs MODIS extents, Bernhofen et al. (2018)", "lo": 0.45, "hi": 0.70, "colour": "#dddddd"},
             "lines": [{"label": "SFINCS, GloFAS forcing, ≥ 1000 km² / < 50 km² (Sadana et al. 2026)", "values": [0.42, 0.29], "ls": ":"},
                       {"label": "SFINCS, observed discharge (Sadana et al. 2026)", "values": [0.67], "ls": "--"}],
             "ylim": [0.0, 0.8]}

SADANA_QUOTES = {
    "abstract_glofas_means": r"global mean CSI of 0\.42 for basins with large upstream area \(\s*>\s*1000 km2\) and a CSI of 0\.29 for basins with small upstream area \(<\s*50 km2\)",
    "results_glofas_means": r"the average CSI rose from 0\.29 in the basins with a small upstream area \(<\s*50 km2\) to 0\.42 in the basins with a large upstream area \(≥\s*1000 km2\)",
    "table3_large": r"≥\s*1000 km2 \(n = 8834\) 0\.62 0\.41 0\.42 1\.22",
    "table3_small": r"<\s*50 km2 \(n = 5304\) 0\.42 0\.46 0\.29 0\.61",
    "glofas_forcing": r"The primary global dataset was GloFAS \(Grimaldi et al\., 2022\)[^.]*\.",
    "observed_discharge_results": r"achieving an average CSI of 0\.67 compared to the average global mean of 0\.39 \(Table 2\)",
    "observed_discharge_discussion": r"when SFINCS was forced with observed USGS discharges, the average CSI was 0\.67 \(HR = 0\.86; FAR = 0\.21\)",
    "abstract_observed": r"the CSI improved from 0\.39 to 0\.67",
    "global_mean": r"with a mean CSI of 0\.39 using GloFAS modelled discharges as input forcing",
    "events": r"simulating 499 riverine floods globally",
}
BERNHOFEN_EXTRA = {"modis": r"[^.]*\(MODIS\) imagery to capture flood events[^.]*\.", "modis_fig3": r"Overlap of individual global flood model extent for return period flows of 25 and 100 years and MODIS observed flood[^.]*"}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump_pdf(pdf: Path, txt: Path) -> int:
    import fitz
    doc = fitz.open(pdf)
    with open(txt, "w", encoding="utf-8") as fh:
        for i, p in enumerate(doc):
            fh.write(f"\n===== PDF page {i + 1} =====\n" + p.get_text())
    return len(doc)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--sadana-pdf", required=True, type=Path)
    ap.add_argument("--bernhofen-txt", type=Path, default=None)
    ap.add_argument("--manuscript-txt", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    v14 = repo / "reproduction" / "v14_rerun"
    out_dir = v14 / "code20"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Sadana et al. 2026
    txt = a.sadana_pdf.with_suffix(".txt")
    n_pages = dump_pdf(a.sadana_pdf, txt)
    pg = pages(txt)
    sq = {k: quote(pg, None, pat, SADANA_FIRST_PAGE - 1) for k, pat in SADANA_QUOTES.items()}
    missing = [k for k, v in sq.items() if not v["found"]]
    bib = (repo / "reproduction" / "r6" / "refs.bib").read_text(encoding="utf-8")
    bib_entry = next((ln for ln in bib.splitlines() if ln.startswith(f"@article{{{BIB_KEY},")), None)
    sadana = {"doi": SADANA_DOI, "bib_key": BIB_KEY, "bib_entry_present": bib_entry is not None, "bib_pages": (re.search(r"pages=\{([^}]*)\}", bib_entry).group(1) if bib_entry else None),
              "document": {"url": SADANA_URL, "file": a.sadana_pdf.name, "sha256": sha256(a.sadana_pdf), "bytes": a.sadana_pdf.stat().st_size, "pdf_pages": n_pages,
                           "retrieved_utc": dt.datetime.fromtimestamp(a.sadana_pdf.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "text_dump_sha256": sha256(txt)},
              "printed_page_rule": f"printed page = {SADANA_FIRST_PAGE - 1} + PDF page", "quotes": sq,
              "reading": "0.42 / 0.29 are average CSI by basin upstream-area class (Table 3; GloFAS discharge forcing; 499 events); 0.67 is the average CSI of "
                         "ten US events forced with observed USGS discharge (Table 2 / Sect. 3.7); the global mean with GloFAS forcing is 0.39 (not drawn)."}
    # Bernhofen et al. 2018: the CODE-19 record + the MODIS sentence
    lk = v14 / "code19" / "lookups.json"
    b19 = json.loads(lk.read_text(encoding="utf-8"))["D4_bernhofen2018"]
    bern = {"from_code19_record": {"file": "reproduction/v14_rerun/code19/lookups.json", "sha256": sha256(lk)}, "crossref": b19["crossref"], "document": b19["document"],
            "printed_page_rule": b19["printed_page_rule"], "quotes": dict(b19["quotes"])}
    if a.bernhofen_txt and a.bernhofen_txt.exists():
        bp = pages(a.bernhofen_txt)
        for k, pat in BERNHOFEN_EXTRA.items():
            bern["quotes"][k] = quote(bp, None, pat, -1)
        bern["text_dump_sha256"] = sha256(a.bernhofen_txt)
    # what F10 v2 drew
    sys.path.insert(0, str(v14 / "scripts"))
    import fig_skill_sweeps_v14 as FS
    prev = {"fig_skill_sweeps_v14.BANDS": [list(b) for b in FS.BANDS], "fig_skill_sweeps_v14.WING_MEDIAN": FS.WING_MEDIAN,
            "manuscript_claim_section_4_7_as_recorded_by_code19": b19.get("manuscript_claim"),
            "note": "fig_skill_sweeps_v14.py (phase-4 figure of the v1.4.2 freeze) is left unchanged; F10 v3 no longer reads it"}
    if a.manuscript_txt and a.manuscript_txt.exists():
        cap = next((ln for ln in a.manuscript_txt.read_text(encoding="utf-8").splitlines() if ln.startswith("Fig. 10 ")), None)
        prev["fig10_caption_R6b_tracked"] = cap
        prev["manuscript_txt_sha256"] = sha256(a.manuscript_txt)
    rec = {"utc": now, "generator": "reproduction/v14_rerun/scripts/code20_lookups.py", "constants": CONSTANTS,
           "sources": {"bernhofen2018": bern, "sadana2026": sadana}, "previous_f10_v2": prev, "quotes_missing": missing}
    out = out_dir / "f10_benchmarks.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k, v in sq.items():
        print(f"{k}: p. {v['printed_page']} | {v['quote']}")
    for k in BERNHOFEN_EXTRA:
        v = bern["quotes"].get(k, {})
        print(f"bernhofen {k}: p. {v.get('printed_page')} | {v.get('quote')}")
    print("missing:", missing); print("wrote", out)
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
