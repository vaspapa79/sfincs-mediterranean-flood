"""CODE-19 D — the source look-ups as a record (code19/lookups.json): every quoted value is extracted by regular expression from
the text of the retrieved document (PDF text dumped with PyMuPDF, HTML stripped), with the page it sits on, the file's SHA-256,
its URL and the retrieval time; Crossref records are copied from the saved API responses; nothing is typed from memory. The
Valencia anchor ledger (D7) is assembled from the NHESS run repository (git), the re-anchoring task folder (file times, score
files) and the repository history of the Valencia example config.

Usage: python -I code19_lookups.py --repo <worktree> --sources <scratchpad dir with pdf/, html/, crossref/, downloads/>
       --tool-results <dir of the fetch agent's saved PDFs>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html as html_mod
import json
import re
import subprocess
import sys
from pathlib import Path


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mtime_utc(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm(t: str) -> str:
    t = t.replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\ufb00", "ff")
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(\w)[­‐‑‒–-] (\w)", r"\1\2", t)   # line-end hyphenation: ASCII, soft (U+00AD, ARPAE PDFs) and Unicode hyphens


def pages(txt: Path) -> dict:
    out, cur = {}, None
    for ln in txt.read_text(encoding="utf-8").splitlines():
        m = re.match(r"===== PDF page (\d+) =====", ln)
        if m:
            cur = int(m.group(1)); out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return {k: norm(" ".join(v)) for k, v in out.items()}


def quote(pg: dict, page, pattern: str, printed) -> dict:
    """page None: search every page and report the page found (printed = offset to add to the PDF page)."""
    if page is None:
        for k in sorted(pg):
            m = re.search(pattern, pg[k], re.I)
            if m:
                return {"pdf_page": k, "printed_page": (k + printed) if isinstance(printed, int) else printed, "quote": m.group(0).strip(), "found": True}
        return {"pdf_page": None, "printed_page": None, "quote": None, "found": False}
    m = re.search(pattern, pg.get(page, ""), re.I)
    return {"pdf_page": page, "printed_page": printed, "quote": m.group(0).strip() if m else None, "found": bool(m)}


def html_text(p: Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return norm(html_mod.unescape(t))


def hquote(t: str, pattern: str) -> dict:
    m = re.search(pattern, t, re.I)
    return {"quote": m.group(0).strip() if m else None, "found": bool(m)}


def crossref(d: Path, doi: str) -> dict:
    p = d / (doi.replace("/", "_") + ".json")
    m = json.loads(p.read_text(encoding="utf-8"))["message"]
    return {"doi": doi, "title": (m.get("title") or [""])[0], "container": (m.get("container-title") or [""])[0], "volume": m.get("volume"), "issue": m.get("issue"),
            "page": m.get("page"), "article_number": m.get("article-number"), "issued": m.get("issued", {}).get("date-parts"), "type": m.get("type"),
            "authors": [f"{a.get('family', '')}, {a.get('given', '')}" for a in m.get("author", [])], "publisher": m.get("publisher"), "crossref_file_sha256": sha256(p),
            "retrieved_utc": mtime_utc(p), "abstract_present": bool(m.get("abstract"))}


def git(repo: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--sources", required=True, type=Path)
    ap.add_argument("--tool-results", required=True, type=Path)
    a = ap.parse_args()
    repo, S, TR = a.repo.resolve(), a.sources.resolve(), a.tool_results.resolve()
    PDF, HTML, CR, DL = S / "pdf", S / "html", S / "crossref", S / "downloads"

    def doc(path: Path, url: str, txt: Path | None = None, note: str = ""):
        return {"file": str(path), "sha256": sha256(path), "bytes": path.stat().st_size, "url": url, "retrieved_utc": mtime_utc(path), "note": note}

    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code19_lookups.py",
           "method": "quotes extracted by regex from the retrieved text (PyMuPDF text layer of the PDF / stripped HTML); printed page numbers from the PDF running heads; "
                     "Crossref from saved api.crossref.org responses (no identifying parameters sent); documents that refused automated access are recorded as not retrievable"}

    # ---------------- D3 Rombeek et al. 2025
    rom_pdf = TR / "webfetch-1792671139582-qgaymu.pdf"; pg = pages(PDF / "rombeek2025.txt")
    out["D3_rombeek2025"] = {
        "crossref": crossref(CR, "10.5194/hess-29-6715-2025"), "document": doc(rom_pdf, "https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf"),
        "printed_page_rule": "printed = PDF page + 6714 (running head)",
        "quotes": {
            "table1_caption": quote(pg, 4, r"Table 1\. Area and mean discharge per unit area of the gauged catchments indicated in Fig\. 1b\.", 6718),
            "table1_row_ID4": quote(pg, 4, r"ID4 \(Poyo\) 182 NA NA NA 0 147 433", 6718),
            "table1_rows_ID1_ID3": quote(pg, 4, r"ID1 \(Júcar\) 21 ?331 .{0,60}ID2 \(Magro\) 706 .{0,60}ID3 \(Turia\) 6123", 6718),
            "poyo_is_gauge_ID4": quote(pg, 13, r"No historic discharge timeseries longer than three months were available for the streamflow gauge in this catchment \(ID4\)\.", 6727),
            "poyo_description": quote(pg, 3, r"In the Rambla de Poyo catchment, characterized by an ephemeral stream with impermeable lithology and an average slope of 17 ?%, nearly 40 flash flood events were recorded in less than 20 years \(Camarasa-Belmonte, 2016\)\.", 6717),
            "fig6_caption": quote(pg, 9, r"Figure 6\. \(a\) Catchment-average rainfall over time .{0,900}? with the same colour in \(b–d\)\.", 6723),
            "fig6a_legend_areas_visual": {"found": True, "quote": "1) - 960 km²; 2) - 571 km²; 3) - 1661 km²; 4) - 316 km²", "pdf_page": 9, "printed_page": 6723,
                                          "note": "legend of Fig. 6a read from the rendered figure (raster, not in the PDF text layer)"},
            "areas_316_1661_text": quote(pg, None, r"catchment averages of more than 150 ?mm ?d−1 across areas between 316 and 1661 km2", 6714),
            "catchment4_164mm": quote(pg, 9, r"On the other hand, for catchment \(4\) a significantly higher catchment-averaged rainfall is estimated, which is more than 40 mm, namely 164 mm\.", 6723),
            "catchment1_79mm": quote(pg, 9, r"The largest reduction occurs in catchment \(1\), with a decrease of approximately 60 mm, resulting in a catchment-? ?average rainfall of 79 mm\.", 6723),
            "catchment3_magro": quote(pg, None, r"In this catchment area \(1661 km2, catchment 3 in Fig\. 6\) 8 PWSs are located and only one AEMET station", 6714),
            "smallest_largest": quote(pg, 8, r"response times between 1 and 2 h can be expected for the smallest \(176\.7 km2\) and largest catchment \(2104 km2\) in Fig\. 1\.", 6722),
            "turis_400mm": quote(pg, 8, r"This station reported more than 400 mm within 24 h, with most rain \(around 280 mm\) between 18:00–00:00, while PWSs within 10 km did not record this\.", 6722),
        },
        "reading": "Two numbering schemes: Table 1 / Fig. 1b gauge catchments ID1–ID4, where ID4 is the Poyo gauge with 182 km²; Fig. 6 rainfall catchments (1)–(4) with areas 960 / 571 / 1661 / 316 km² "
                   "(legend of Fig. 6a), where (3) is named the Magro and (4) carries the 164 mm. The text never names catchment (4); it is not the 182 km² gauged Poyo catchment (316 km²).",
        "figure_reading_visual": "read from the rendered pages (not from the text): Fig. 1b places gauge ID4 (Poyo) at about 0.60° W, 39.47° N beside Chiva, the Poyo draining east to the Albufera; "
                                 "Fig. 6d places the yellow catchment (4) with the '164 mm' label south of the Magro mouth around Algemesí (about 0.55–0.35° W, 39.15–39.30° N), while the red catchment (2) "
                                 "(571 km²; '162 mm' combined in panel d, '173 mm' AEMET-only in panel b) encloses Chiva and gauge ID4. On that reading the 164 mm belongs to the coastal catchment "
                                 "south of the Albufera, and the Poyo lies in catchment (2) with 162 mm (combined) — numerically 2 mm from the anchor used.",
    }

    # ---------------- D4 benchmarks
    ber_pdf = TR / "webfetch-1792671298269-dnx2li.pdf"; pg = pages(PDF / "bernhofen2018.txt")
    out["D4_bernhofen2018"] = {
        "crossref": crossref(CR, "10.1088/1748-9326/aae014"), "document": doc(ber_pdf, "https://iopscience.iop.org/article/10.1088/1748-9326/aae014/pdf"),
        "printed_page_rule": "ERL article number 104007; PDF page n = article page n-1 (page 1 of the PDF is the IOP cover sheet)",
        "quotes": {
            "abstract": quote(pg, 2, r"The critical success index of individual models across the three regions ranges from 0\.45 to 0\.7 and the percentage of flood captured ranges from 52% to 97%\.", "article p. 1 (abstract)"),
            "results": quote(pg, 6, r"The average CSI of the GFMs range from 0\.45 \(GLOFRIS\) to 0\.70 \(JRC\) for a 25 year flow\.", "article p. 5"),
            "literature_context": quote(pg, 6, r"CSI scores from other flood validation literature, in different validation regions, range from 0\.3 to 0\.9", "article p. 5"),
            "conclusions": quote(pg, 10, r"with average CSI scores ranging from 0\.45 to 0\.7\.", "article p. 9"),
            "median": {"found": False, "note": "no median CSI is stated anywhere in the text"},
        },
        "manuscript_claim": "section 4.7: 'Bernhofen et al. (2018) report CSI 0.10–0.36 (median about 0.22) across six global models'; F10 band constant 0.10–0.36 (fig_skill_sweeps_v14.py BANDS)",
    }
    tri_pdf = TR / "webfetch-1792671297786-p7xc5g.pdf"; pg = pages(PDF / "trigg2016.txt")
    out["D4_trigg2016"] = {
        "crossref": crossref(CR, "10.1088/1748-9326/11/9/094014"), "document": doc(tri_pdf, "https://iopscience.iop.org/article/10.1088/1748-9326/11/9/094014/pdf"),
        "printed_page_rule": "ERL article number 094014; PDF page n = article page n-1",
        "quotes": {
            "abstract": quote(pg, 2, r"While there is around 30%–40% agreement in flood extent, our results show that even at continental scales, there are significant differences in hazard magnitude and spatial pattern between models", "article p. 1 (abstract)"),
            "mai_kappa": quote(pg, 6, r"we find a MAI of only 0\.29, and a mean Cohen’s kappa coefficient of 0\.43, across all models and all return periods\.", "article p. 5"),
            "csi": {"found": False, "note": "the article reports model-to-model agreement (model agreement index, Cohen's kappa), not a CSI against observations"},
        },
        "manuscript_claim": "section 4.7: 'Trigg et al. (2016) 0.10–0.35'",
    }
    hoc_pdf = TR / "webfetch-1792671304199-loys0z.pdf"; pg = pages(PDF / "hocini2021.txt")
    out["D4_hocini2021"] = {
        "crossref": crossref(CR, "10.5194/hess-25-2979-2021"), "document": doc(hoc_pdf, "https://hess.copernicus.org/articles/25/2979/2021/hess-25-2979-2021.pdf"),
        "printed_page_rule": "printed = PDF page + 2978",
        "quotes": {
            "abstract": quote(pg, 1, r"With these methods, a good retrieval of the inundated areas is illustrated by critical success index \(CSI\) median values close to 80 ?%, and the errors on water levels remain mostly below 80 cm for the 2D Floodos approach\.", 2979),
            "section4_1": quote(pg, 8, r"Overall, similar and satisfactory results are observed for the caRtino 1D and Floodos 2D approaches, with a slight advantage for Floodos, for which the 15 ?% quantiles of CSI values exceed 50 ?% and the median CSI values are close to 80 ?%\.", 2986),
            "la_redorte": quote(pg, 9, r"In this section, the CSI scores are, respectively, 69 ?% for the Floodos model, 63 ?% for the caRtino 1D model, and 35 ?% for the HAND/MS method\.", 2987),
            "conclusion": quote(pg, 14, r"with median CSI values close to 80 ?% for the approach based on the Floodos model\.", 2992),
        },
        "manuscript_claim": "section 4.7: 'Hocini et al. (2021) 0.42–0.62 for calibrated single-event runs'; F10 band constant 0.42–0.62",
    }
    wing_t = html_text(HTML / "bristol_wing.html") if (HTML / "bristol_wing.html").exists() else ""
    out["D4_wing2017"] = {
        "crossref": crossref(CR, "10.1002/2017WR020917"),
        "access": "full text not retrievable by automated access: Wiley (doi.org / onlinelibrary pdfdirect) HTTP 403 for the fetch agent and for curl; the Bristol repository PDF "
                  "(research-information.bris.ac.uk/files/133466974/…) HTTP 403; only the Bristol landing-page abstract was readable",
        "abstract_quotes": {"fema": hquote(wing_t, r"Where the FEMA SFHAs are based on high quality local models, the continental-scale model attains a Hit Rate of 86%\."),
                            "usgs": hquote(wing_t, r"Against the higher quality USGS data the average Hit Rate reaches 92% for the 1 in 100-year flood, and 90% for all flood return periods\.")},
        "abstract_source": doc(HTML / "bristol_wing.html", "https://research-information.bris.ac.uk/en/publications/8d9fc333-5961-421b-8c1a-ed3673d77154") if wing_t else None,
        "csi": {"found": False, "note": "CSI values versus FEMA and USGS not readable (body text inaccessible); F10's former 'benchmark median' constant WING_MEDIAN = 0.40 is unverified and the line is removed (B1)"},
    }

    # ---------------- D5 Schumann 2016
    bt = html_text(HTML / "bristol_schumann.html")
    out["D5_schumann2016"] = {"crossref": crossref(CR, "10.1002/2016GL070260"),
                              "publisher_page": "not retrievable: agupubs.onlinelibrary.wiley.com (doi, full, abs, pdfdirect) HTTP 403 for the fetch agent and for curl",
                              "bristol_record": {"source": doc(HTML / "bristol_schumann.html", "https://research-information.bris.ac.uk/en/publications/rethinking-flood-hazard-at-the-global-scale"),
                                                 "pages_field": hquote(bt, r"Pages \(from-to\) \d{5}-\d{5}"), "apa_citation": hquote(bt, r"Schumann, G\. J\. P\., Stampoulis, D\.,.{0,260}?10249-10256")},
                              "refs_bib_action": "not added: the brief admits the range only when the publisher page shows it, and the publisher page could not be read"}

    # ---------------- D6 Ross 2018
    out["D6_ross2018"] = {"crossref": crossref(CR, "10.1038/sdata.2018.91"), "refs_bib_action": "not added (pending the author's decision for section 5.4)"}

    # ---------------- D1 Diakakis 2019 / Varlas 2019
    out["D1_mandra_sources"] = {
        "diakakis2019": {"crossref": crossref(CR, "10.1016/j.ijdrr.2018.10.015"), "access": "paywalled (Elsevier); ScienceDirect preview HTTP 403 for the fetch agent; OpenAlex is_oa false; "
                         "see CODE-17 lookups.json B3 for the publicly visible abstract values (300 mm in 13 h, 153 / 194 mm basin means, 9–10 m3/s/km2, 24 people)",
                         "catchment_areas": "not retrievable", "pateras_wildfire": "not retrievable"},
        "varlas2019": {"crossref": crossref(CR, "10.3390/rs11010045"), "access": "open access (CC BY) but mdpi.com returned HTTP 403 to the fetch agent (/htm) and to curl (/pdf); Semantic Scholar "
                       "and OpenAlex list only the mdpi.com PDF as the open-access location; OpenAIRE lists no mirror", "catchment_areas": "not retrievable", "pateras_wildfire": "not retrievable"},
        "manuscript_text": "section 2: 'at the confluence of the Soures (about 12 km²) and Agia Aikaterini (about 7 km²) streams' — source of the areas not verified in this pass",
    }

    # ---------------- D2 Emilia-Romagna 2023
    arr_pdf = DL / "arrighi2024.pdf"; pg = pages(PDF / "arrighi2024.txt")
    sp = pages(PDF / "arpae_idrometeoclima_2023.txt"); ar = pages(PDF / "arpae_20230516-18.txt")
    reg_t = html_text(HTML / "regione_20231215.html"); fer_t = html_text(HTML / "ferrari2025.html"); cima_t = html_text(HTML / "cima_20230519.html")
    out["D2_emilia_romagna_2023"] = {
        "arrighi_domeneghetti_2024": {"crossref": crossref(CR, "10.5194/nhess-24-673-2024"), "document": doc(arr_pdf, "https://nhess.copernicus.org/articles/24/673/2024/nhess-24-673-2024.pdf"),
                                      "printed_page_rule": "printed = PDF page + 672",
                                      "quotes": {"rivers": quote(pg, 2, r"23 rivers overflowed, affecting 100 municipalities, and more than 400 landslides severely damaged infrastructure", 674),
                                                 "levees": quote(pg, 2, r"because they hit basins and rivers already affected by intense rainfall and floods \(i\.e\. levee overtopping and failures\) occurring after the 1–4 May event", 674),
                                                 "deaths": quote(pg, 2, r"In total, the events caused more than 36 ?000 people to be displaced and 15 deaths \(Agenzia per la sicurezza territoriale e la protezione civile, 2023\)\.", 674)}},
        "ferrari_et_al_2025": {"citation": "Ferrari, A. et al.: Brief communication: Hydrological and hydraulic investigation of the extreme September 2024 flood on the Lamone River in Emilia-Romagna, Italy, "
                                            "Nat. Hazards Earth Syst. Sci., 25, 2473–2479, https://doi.org/10.5194/nhess-25-2473-2025, 2025",
                               "document": doc(HTML / "ferrari2025.html", "https://nhess.copernicus.org/articles/25/2473/2025/"),
                               "quotes": {"may2023_return_period": hquote(fer_t, r"even the return period of May 2023 events, which was evaluated by carrying out the statistical analysis described in Sect\. 2 considering the 1928–2022 observation dataset, was estimated to exceed the 500-year return period for the precipitation accumulated over 24 ?h \(for the remaining durations the return periods were in the range 2–250 years\)\."),
                                          "gauges": hquote(fer_t, r"the rain gauges of San Cassiano sul Lamone in the Lamone catchment \(95 years of records\) and Tredozio in the Marzeno catchment \(43 years of records\)"),
                                          "rivers": hquote(fer_t, r"already suffered extensive and devastating floods in May 2023 due to the overflowing of 23 rivers \(Arrighi and Domeneghetti, 2024\)")}},
        "regione_er_press_release_2023_12_15": {"title": "Post alluvione. Ecco il Rapporto della Commissione tecnico-scientifica: “In Emilia-Romagna un evento senza precedenti nella storia osservata”",
                                                "organisation": "Regione Emilia-Romagna (press release on the report of the technical-scientific commission coordinated by Armando Brath; report dated Bologna, 12 December 2023)",
                                                "document": doc(HTML / "regione_20231215.html", "https://notizie.regione.emilia-romagna.it/comunicati/2023/dicembre/post-alluvione-ecco-il-rapporto-della-commissione-tecnico-scientifica-201cin-emilia-romagna-un-evento-senza-precedenti-nella-storia-osservata201d-la-vicepresidente-priolo-201cabbiamo-affrontato-qualcosa-di-difficilmente-immaginabile-uno-spartiacque-tra"),
                                                "date": hquote(reg_t, r"15 dicembre 2023"),
                                                "quotes": {"return_period": hquote(reg_t, r"“Un evento senza precedenti nella storia osservata” scrivono gli esperti, con tempi di ritorno[^.]*“in alcuni casi molto superiori ai 500 anni dove le esondazioni sono state più significative ?”\."),
                                                           "basins": hquote(reg_t, r"Parliamo soprattutto dei bacini di Senio, Lamone e Montone[^.]*\."),
                                                           "rivers": hquote(reg_t, r"dai 23 fiumi esondati contemporaneamente, per un volume di esondazione stimato in circa 350 milioni di metri cubi")},
                                                "report_pdf": "the commission report itself (20231212_rapporto_commissione_rer.pdf) returned HTTP 404 at the two URLs found; the press release is the citable record read"},
        "arpae_idrometeoclima_2023_special": {"title": "Rapporto IdroMeteoClima Emilia-Romagna DATI 2023 — Speciale 'Alluvione in Romagna: l'evento, la gestione dell'emergenza, gli impatti'",
                                              "organisation": "Arpae Emilia-Romagna (published with the news item of 20 June 2024)", "document": doc(DL / "arpae_idrometeoclima_2023.pdf", "https://www.arpae.it/it/notizie/speciale-alluvione-idrometeoclima-2023.pdf"),
                                              "printed_page_rule": "PDF page 2 = report pp. 14–15, page 3 = pp. 16–17",
                                              "quotes": {"numbers_box": quote(sp, 3, r"I NUMERI DELL'ALLUVIONE[^A-Z]*?17 decessi[^A-Z]*?23 fiumi in esondazione[^A-Z]*?540 km2 di territorio allagato[^A-Z]*?65\.598 frane[^A-Z]*?fino a 1\.000 anni tempi di ritorno dei due eventi pluviometrici \(1-3 \+ 16-17 maggio\)", "16–17"),
                                                         "commission_estimate": quote(sp, 3, r"La commissione incaricata dalla Regione Emilia-?\s?Romagna per valutare l.eccezionalit. di quanto avvenu-?\s?to ha stimato tempi di ritorno per i singoli eventi tra 100 e 500 anni, a seconda della localit. considerata, mentre per la probabilit. che due eventi di tale inten-?\s?sit. si verificassero cos. ravvicinati nel tempo i tempi di ritorno stimati sono superiori a 1\.000 anni\.", "16–17")}},
        "arpae_event_report_16_18_may_2023": {"title": "Rapporto dell'evento meteorologico dal 16 al 18 maggio 2023 (Arpae Emilia-Romagna, Struttura Idro-Meteo-Clima)",
                                              "document": doc(DL / "arpae_idro_meteo_20230516-18.pdf", "https://www.arpae.it/it/temi-ambientali/meteo/report-meteo/rapporti-post-evento/rapporto_idro_meteo_20230516-18.pdf"),
                                              "quotes": {"return_periods_24h": quote(ar, 19, r"si stimano per le piogge di durata 24 ore tempi di ritorno superiori ai 200 anni per i pluviometri appartenenti ai bacini di Santerno, Senio, Lamone, Montone e Ronco\.", 19),
                                                         "return_periods_2d": quote(ar, 19, r"Per le piogge di durata 2 giorni consecutivi, si stimano tempi di ritorno superiori ai 200 anni per i pluviometri appartenenti ai bacini di Santerno, Senio, Lamone, superiori ai 100 anni sui pluviometri di Sillaro e Montone\.", 19),
                                                         "peaks": quote(ar, 2, r"Su Samoggia, Idice, Quaderna, Sillaro, Santerno, Senio, Lamone, Montone, Ronco, Bevano, Savio e Rubicone, sono stati registrati livelli al colmo ancora più alti delle piene di 14 giorni prima", 2)}},
        "cima_2023_05_19": {"document": doc(HTML / "cima_20230519.html", "https://www.cimafoundation.org/en/news/the-italian-floods-of-may-2023-a-scientific-analysis"),
                            "quote": hquote(cima_t, r"record rainfall occurred, causing flooding and overflowing of 21 rivers in several municipalities between Romagna and the Bologna area")},
        "cremonini_et_al_2024": {"crossref": crossref(CR, "10.3390/land13111800"), "access": "candidate peer-reviewed source for the >500-year statement (search-engine snippet names Senio, Lamone and Montone); "
                                 "full text not retrievable by automated access (mdpi.com, iris.cnr.it, preprints.org all HTTP 403); the Crossref abstract carries no return-period sentence — unverified"},
        "summary": {"(a) >500-year return periods, Senio/Lamone/Montone": "Regione press release of 15 Dec 2023 on the commission report (quotes above); Ferrari et al. 2025 (>500-year for the 24-h rainfall at the Lamone/Marzeno gauges); "
                                                                        "ARPAE event report: >200-year for the 24-h rainfall in Santerno, Senio, Lamone, Montone, Ronco; ARPAE special: commission estimate 100–500 years per event",
                    "(b) >20 rivers": "ARPAE special '23 fiumi in esondazione'; Regione '23 fiumi esondati contemporaneamente'; Arrighi & Domeneghetti 2024 '23 rivers overflowed' with 'levee overtopping and failures'; CIMA '21 rivers'",
                    "(c) fatalities": "ARPAE special '17 decessi'; Arrighi & Domeneghetti 2024 '15 deaths' (civil-protection source, Feb 2024); no peer-reviewed source read gives 17"},
    }

    # ---------------- D7 Valencia anchor ledger
    nhess = Path("D:/ELKAK/ELKAK2/NHESS"); task = nhess / "R1_verification" / "task_valencia_anchor"
    prov = (task / "PROVENANCE.md").read_text(encoding="utf-8", errors="replace")
    def prov_val(col_regex):
        m = re.search(col_regex, prov)
        return m.group(1) if m else None
    csi_row = re.search(r"\| CSI \| ([\d.]+) \| \*\*([\d.]+)\*\* \| ([\d.]+) \| ([\d.]+) \|", prov)
    scoring = {}
    for n in ("score_canon350.json", "score_v175.json", "score_v164.json"):
        p = task / "_scoring" / n
        if p.exists():
            j = json.loads(p.read_text(encoding="utf-8"))
            scoring[n] = {"generated_utc": j.get("generated_utc"), "mtime_utc": mtime_utc(p), "sha256": sha256(p)}
    ex_hist = git(repo, "log", "--format=%h %cI %s", "--", "skill/examples/emsr773_valencia_enhanced.yaml").splitlines()
    first_example = git(repo, "show", "1a62b2d:skill/examples/emsr773_valencia_enhanced.yaml")
    m350 = re.search(r"[^\n]*--target-mm 350[^\n]*", first_example)
    cur = (repo / "skill" / "examples" / "emsr773_valencia_enhanced.yaml").read_text(encoding="utf-8")
    m164 = re.search(r"[^\n]*target_mm: 164[^\n]*", cur)
    readme50 = git(nhess, "show", "HEAD:runs/README.md")
    mread = re.search(r"[^\n]*350 mm[^\n]*", readme50)
    out["D7_valencia_anchor_ledger"] = {
        "sources": {"nhess_repo": str(nhess), "task_folder": str(task), "repo_example": "skill/examples/emsr773_valencia_enhanced.yaml", "reproduction_record": "reproduction/v14_rerun/configs/valencia_enhanced_164*.yaml, results/"},
        "entries": [
            {"anchor_mm": None, "state": "raw IMERG (no anchor)", "when": "2026-07-15T13:13:03Z (metrics generated_utc; NHESS commit 49da0d1, 2026-07-15T17:00:54+03:00)",
             "evidence": "ELKAK2/NHESS runs/valencia_emsr773/metrics.json at 49da0d1; YAML comment 'leave raw until that target is set'", "score_computed": "yes — CSI 0.105 at h > 0.10 m (CODE-5 ledger)"},
            {"anchor_mm": 350.0, "state": "hand-typed areal target (bias_correct_imerg.py --target-mm 350), factor x4.14", "when": "2026-07-15T18:00:02Z (metrics generated_utc; NHESS commit 5447768, 2026-07-15T21:09:15+03:00)",
             "evidence": (mread.group(0).strip() if mread else "runs/README.md") + "; repository example at 1a62b2d (2026-07-16T10:21:23+03:00): " + (m350.group(0).strip() if m350 else "—"),
             "score_computed": "yes — CSI 0.082 (h > 0.10 m), 0.126 (h > 0.50 m); published in the NHESS draft; re-scored 2026-07-21T09:02:04Z (score_canon350.json)",
             "score_known_before_next_change": True},
            {"anchor_mm": 175.0, "state": "midpoint of the 150–200 mm band (superseded)", "when": f"2026-07-21 ~08:56–09:29Z (rerun_v175/precip_2d.nc mtime {mtime_utc(task / 'rerun_v175' / 'model' / 'precip_2d.nc')}; score_v175.json generated {scoring.get('score_v175.json', {}).get('generated_utc')})",
             "evidence": "PROVENANCE.md: 'Supersedes an earlier 175 mm midpoint guess (rerun_v175/, x2.07)'", "score_computed": "yes — CSI 0.093 (h > 0.10 m), 0.165 (h > 0.50 m)",
             "score_known_before_next_change": True},
            {"anchor_mm": 164.0, "state": "Rombeek et al. 2025 catchment (4) 24-h mean, taken as the Rambla de Poyo value; factor x1.94", "when": f"2026-07-21 (rerun_v164/precip_2d.nc mtime {mtime_utc(task / 'rerun_v164' / 'model' / 'precip_2d.nc')}; score_v164.json generated {scoring.get('score_v164.json', {}).get('generated_utc')}; TARGET_SELECTION.md mtime {mtime_utc(task / 'TARGET_SELECTION.md')}); adopted in the repository example at commit 5eff694 (2026-07-22T12:29:05+03:00)",
             "evidence": "TARGET_SELECTION.md / PROVENANCE.md; " + (m164.group(0).strip() if m164 else "—"), "score_computed": "yes — CSI 0.094 (h > 0.10 m), 0.170 (h > 0.50 m); v1.3 release run valencia_enhanced_164; v1.4 re-runs keep 164",
             "score_known_before_next_change": "no later change"},
        ],
        "provenance_table_csi_h_gt_0p10": {"raw": csi_row.group(1), "164": csi_row.group(2), "175": csi_row.group(3), "350": csi_row.group(4)} if csi_row else None,
        "scoring_files": scoring, "repo_example_history": ex_hist,
        "reading": "every anchor change followed a computed score of the previous value (350 scored 15 Jul; 175 scored 09:29Z and replaced by 164 at ~10:00Z the same morning; 164 scored 10:41Z and adopted). "
                   "The documented motive for each change is sourcing (unsourced 350 -> literature band midpoint -> catchment-specific published value), recorded in TARGET_SELECTION.md and PROVENANCE.md; "
                   "the D3 reading above questions whether the 164 mm catchment (4) is the gauged Poyo catchment.",
    }
    p = repo / "reproduction" / "v14_rerun" / "code19" / "lookups.json"
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    # report what was not found
    missing = []
    def walk(o, path=""):
        if isinstance(o, dict):
            if "found" in o and not o["found"] and "quote" in o:
                missing.append(path)
            for k, v in o.items():
                walk(v, f"{path}/{k}")
    walk(out)
    print("wrote", p, "| quotes not found:", missing or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
