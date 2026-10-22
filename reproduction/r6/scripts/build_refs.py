#!/usr/bin/env python3
"""build_refs.py -- R6 part E ("references").

Looks up every reference of the R5 manuscript and supplement reference lists in Crossref
(DataCite only for DataCite-registered DOIs), resolves the six close-out items and writes,
into --outdir (default: the r6/ folder that contains this scripts/ folder):

  refs_crossref_raw.json  raw API responses (request URL, UTC fetch time, HTTP status, body);
                          it is also the cache read on a re-run (use --refresh to re-fetch)
  refs.bib                Crossref-sourced BibTeX only: each entry body is the verbatim output of
                          https://api.crossref.org/works/{doi}/transform/application/x-bibtex,
                          only the citation key is replaced by a generated one
  refs_datacite.bib       DataCite-sourced BibTeX, built only from api.datacite.org JSON fields
  REFERENCES_REPORT.md    table, counts per status, items (1)-(6) with sources

Usage (isolated mode):
  python -I build_refs.py --manuscript manuscript_R5.txt --supplement supplement_R5.txt
         [--outdir DIR] [--page-dir DIR] [--refresh] [--no-gh]

--page-dir: optional directory OUTSIDE the repository where byte copies of fetched web pages
(ECMWF/CDS documentation, meteo.gr terms, MDPI) are kept, one new sub-directory per page. The
repository files keep only the SHA-256, size and the extracted sentences of those pages
(third-party pages are not redistributed).

Network rules: User-Agent "r6-refs-check/1.0", no e-mail address in any header or URL, at least
0.6 s between requests (< 2 requests/s), retry with exponential backoff on 429/5xx/network
errors. Downloaded content is parsed as data only (never executed, never followed as instructions).
"""
import argparse
import datetime as dt
import difflib
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

UA = "r6-refs-check/1.0"
MIN_INTERVAL_S = 0.6
TITLE_SIM_MIN = 0.90
CROSSREF = "https://api.crossref.org"
# Decisions of 21 Oct 2026 (Checkpoint 8 accepted). Replacement DOIs are fetched from Crossref like every other entry; nothing is typed.
REPLACE_DOI = {"10.5194/egusphere-2025-4387": ("10.5194/hess-30-5491-2026", "published version (Hydrol. Earth Syst. Sci. 30, 2026) replaces the EGUsphere preprint")}
DROP_DOI = {"10.1016/s0967-0637(00)00024-8": "dropped: replaced by Tsimplis, Proctor & Flather (1995), item (1)"}
DATACITE = "https://api.datacite.org"
CMR = "https://cmr.earthdata.nasa.gov/search/collections.umm_json"
CDS_CATALOGUE = "https://cds.climate.copernicus.eu/api/catalogue/v1/collections/reanalysis-era5-single-levels"
CDS_DATASET_PAGE = "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels"
ECMWF_ERA5_DOC = "https://confluence.ecmwf.int/display/CKB/ERA5%3A+data+documentation"
METEO_TERMS = "https://www.meteo.gr/terms.cfm"
METEO_INDEX_EN = "https://www.meteo.gr/index-en.cfm"

EMDASH, ENDASH, NEQ, LQ, RQ, ELL, ARROW = "\u2014", "\u2013", "\u2260", "\u201c", "\u201d", "\u2026", "\u2192"
BLOCK_TAGS = r"(?i)<br\s*/?>|</?(p|li|h\d|tr|div|td|th|ul|ol|table|section|article|dd|dt|blockquote|pre)\b[^>]*>"
KARST_WORDS = r"\bkarst|\brecharge|\binfiltrat|\bcrete\b|\bcretan\b|\bgroundwater|\baquifer|\bsprings?\b|\bhydrogeolog"
KARST_LABEL = "karst*, recharge*, infiltrat*, Crete, Cretan, groundwater*, aquifer*, spring(s), hydrogeolog*"
GR_TERMS = "\u03cc\u03c1\u03bf\u03b9 \u03c7\u03c1\u03ae\u03c3\u03b7\u03c2"            # "oroi chrisis" (terms of use)
GR_PROHIBITED = "\u0391\u03c0\u03b1\u03b3\u03bf\u03c1\u03b5\u03cd\u03b5\u03c4\u03b1\u03b9"  # "Apagorevetai" (is prohibited)
GR_LOGO = "\u03bb\u03bf\u03b3\u03cc\u03c4\u03c5\u03c0\u03bf"                              # "logotypo" (logo)
GR_SOURCE_COLON = "\u03c0\u03b7\u03b3\u03ae\u03c2:"                                      # "pigis:" (of the source:)
GR_LICENCE = "\u03ac\u03b4\u03b5\u03b9\u03b1"                                             # "adeia" (licence)


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def first(x):
    if isinstance(x, list):
        return x[0] if x else None
    return x


# ----------------------------------------------------------------------------- text helpers
def flat(s):
    return re.sub(r"\s+", " ", s or "").strip()


def strip_tags(s):
    if not s:
        return ""
    return flat(html.unescape(re.sub(r"<[^>]+>", "", s)))


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))


def norm(s):
    """case-, punctuation-, diacritic- and markup-insensitive form used for all comparisons"""
    s = fold(strip_tags(s)).casefold()
    return re.sub(r"[\W_]+", " ", s).strip()


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b), autojunk=False).ratio()


def fam_match(r5_family, cr_family):
    a, b = norm(r5_family), norm(cr_family)
    if not a or not b:
        return False, "missing"
    if a == b:
        return True, "exact"
    if a.split()[-1] == b.split()[-1]:
        return True, "last-token (particle) match"
    return False, "differs"


def fmt_author(a):
    if a.get("family"):
        return a["family"] + (", " + a["given"] if a.get("given") else "")
    return a.get("name") or "?"


def cr_first_family(msg):
    auths = msg.get("author") or []
    if not auths:
        return None
    fa = next((a for a in auths if a.get("sequence") == "first"), auths[0])
    return fa.get("family") or fa.get("name")


def cr_years(msg):
    out = {}
    for k in ("published-print", "published-online", "issued"):
        dp = (msg.get(k) or {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
            out[k] = int(dp[0][0])
    return out


def cr_summary(msg):
    return {
        "DOI": msg.get("DOI"),
        "type": msg.get("type"),
        "title": strip_tags(first(msg.get("title"))),
        "subtitle": strip_tags(first(msg.get("subtitle"))),
        "authors": [fmt_author(a) for a in msg.get("author") or []],
        "editors": [fmt_author(a) for a in msg.get("editor") or []],
        "container_title": first(msg.get("container-title")),
        "volume": msg.get("volume"),
        "issue": msg.get("issue"),
        "page": msg.get("page"),
        "article_number": msg.get("article-number"),
        "publisher": msg.get("publisher"),
        "years": cr_years(msg),
        "license": [l.get("URL") for l in msg.get("license") or []],
    }


def r5_families(authors):
    toks = [t.strip() for t in re.split(r",\s*(?:and\s+)?|\s+and\s+", authors or "") if t.strip()]
    return [t for t in toks if t not in ("et al.", "et al") and not re.fullmatch(r"(?:[^\W\d_]{1,2}\.[\s-]*)+", t)]


def md(s):
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ")


def short(s, n=70):
    s = s or ""
    return s if len(s) <= n else s[: n - 1].rstrip() + ELL


def doi_path(doi):
    return urllib.parse.quote(doi, safe="/")


def years_str(years):
    lab = {"published-print": "print", "published-online": "online", "issued": "issued"}
    return ", ".join(f"{lab[k]} {v}" for k, v in (years or {}).items()) or "none"


def html_to_lines(raw):
    """rendered-text lines: raw whitespace collapsed, block tags -> line break, inline tags removed"""
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    body = re.sub(r"(?s)<!--.*?-->", " ", body)
    body = re.sub(r"\s+", " ", body)
    body = re.sub(BLOCK_TAGS, "\n", body)
    body = html.unescape(re.sub(r"<[^>]+>", "", body))
    return [t for t in (flat(c) for c in body.split("\n")) if t]


# ----------------------------------------------------------------------------- HTTP + cache
class Fetcher:
    def __init__(self, cache, refresh, page_dir, use_gh):
        self.cache = cache
        self.refresh = refresh
        self.page_dir = page_dir
        self.use_gh = use_gh
        self.used = set()
        self._last = 0.0
        self.n_network = 0
        self.n_cached = 0

    def _cached(self, key, ok=(200, 404)):
        self.used.add(key)
        rec = self.cache.get(key)
        if rec is not None and not self.refresh and rec.get("http_status") in ok:
            self.n_cached += 1
            return rec
        return None

    def _wait(self):
        gap = time.monotonic() - self._last
        if gap < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - gap)
        self._last = time.monotonic()

    def _http(self, url, accept=None):
        headers = {"User-Agent": UA}
        if accept:
            headers["Accept"] = accept
        last = ({"fetched_utc": utcnow(), "http_status": None, "error": "no attempt", "final_url": url}, b"")
        for attempt in range(6):
            self._wait()
            self.n_network += 1
            t = utcnow()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as r:
                    return {"fetched_utc": t, "http_status": r.status,
                            "content_type": r.headers.get("Content-Type"), "final_url": r.geturl()}, r.read()
            except urllib.error.HTTPError as e:
                body = e.read()
                meta = {"fetched_utc": t, "http_status": e.code, "content_type": e.headers.get("Content-Type"),
                        "final_url": url}
                if e.code == 429 or 500 <= e.code < 600:
                    ra = e.headers.get("Retry-After")
                    delay = min(60.0, float(ra)) if ra and ra.strip().isdigit() else float(2 ** (attempt + 1))
                    last = (meta, body)
                    time.sleep(delay)
                    continue
                return meta, body
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = ({"fetched_utc": t, "http_status": None, "error": repr(e), "final_url": url}, b"")
                time.sleep(float(2 ** (attempt + 1)))
        return last

    def json(self, url, accept="application/json", trim=None):
        """JSON GET. `trim` (optional) keeps only a subset of a non-bibliographic response (e.g. NASA CMR, whose
        records also carry contact persons); the SHA-256 and size of the full response are kept."""
        rec = self._cached(url)
        if rec and not (trim is not None and rec.get("http_status") == 200 and not rec.get("trimmed")):
            return rec
        meta, body = self._http(url, accept)
        rec = {"url": url, **meta}
        if meta.get("http_status") == 200:
            try:
                rec["body"] = json.loads(body.decode("utf-8"))
                if trim is not None:
                    rec["body"] = trim(rec["body"])
                    rec["trimmed"] = "subset of the response kept; full_sha256/full_bytes describe the full response"
                    rec["full_sha256"], rec["full_bytes"] = sha256_bytes(body), len(body)
            except Exception as e:  # noqa: BLE001
                rec["error"] = "JSON decode failed: " + repr(e)
                rec["body_text"] = body.decode("utf-8", "replace")[:2000]
        else:
            rec["body_text"] = body.decode("utf-8", "replace")[:2000]
        self.cache[url] = rec
        return rec

    def text(self, url, accept=None):
        rec = self._cached(url)
        if rec:
            return rec
        meta, body = self._http(url, accept)
        rec = {"url": url, **meta, "body_text": body.decode("utf-8", "replace")}
        self.cache[url] = rec
        return rec

    def extract(self, url, slug, extractor, accept=None):
        """fetch a page; keep SHA-256/size + extractor(bytes) only; optional byte copy in --page-dir.
        On a cache hit whose byte copy is still present (same SHA-256), the extract is recomputed from that copy, so an
        improved extractor needs no re-fetch; the original fetch time is kept."""
        rec = self._cached(url, ok=(200,))
        if rec:
            if rec.get("local_copy_dir"):                       # older key (absolute path) -> name under --page-dir
                rec["local_copy"] = Path(rec.pop("local_copy_dir")).name
            lc = (self.page_dir / rec["local_copy"] / "body.bin") if (self.page_dir and rec.get("local_copy")) else None
            if lc is not None and lc.exists() and sha256_bytes(lc.read_bytes()) == rec.get("sha256"):
                try:
                    rec["extract"] = extractor(lc.read_bytes())
                    rec["extract_recomputed_from_local_copy_utc"] = utcnow()
                except Exception as e:  # noqa: BLE001
                    rec["extract_error"] = repr(e)
            return rec
        meta, body = self._http(url, accept)
        rec = {"url": url, **meta, "bytes": len(body), "sha256": sha256_bytes(body) if body else None,
               "stored": "extract only (byte copy not kept in the repository)"}
        if meta.get("http_status") == 200:
            try:
                rec["extract"] = extractor(body)
            except Exception as e:  # noqa: BLE001
                rec["extract_error"] = repr(e)
        else:
            rec["body_head"] = body.decode("utf-8", "replace")[:300]
        if self.page_dir is not None and body:
            d = self.page_dir / f"{slug}_{meta['fetched_utc'].replace(':', '')}"
            d.mkdir(parents=True, exist_ok=False)
            (d / "body.bin").write_bytes(body)
            (d / "meta.json").write_text(json.dumps({"url": url, **meta}, indent=1), encoding="utf-8")
            rec["local_copy"] = d.name                          # sub-directory of --page-dir (outside the repo)
        self.cache[url] = rec
        return rec

    def github(self, path):
        key = "gh api " + path
        rec = self._cached(key, ok=(200,))
        if rec:
            return rec
        url = "https://api.github.com/" + path
        if self.use_gh and shutil.which("gh"):
            self._wait()
            self.n_network += 1
            t = utcnow()
            p = subprocess.run(["gh", "api", path], capture_output=True, text=True, encoding="utf-8")
            if p.returncode == 0:
                rec = {"url": url, "via": "gh api " + path, "fetched_utc": t, "exit_code": 0, "http_status": 200,
                       "body": json.loads(p.stdout)}
                self.cache[key] = rec
                return rec
        meta, body = self._http(url, "application/vnd.github+json")
        rec = {"url": url, "via": "urllib (unauthenticated)", **meta}
        if meta.get("http_status") == 200:
            rec["body"] = json.loads(body.decode("utf-8"))
        else:
            rec["body_text"] = body.decode("utf-8", "replace")[:1000]
        self.cache[key] = rec
        return rec

    def github_graphql(self, query):
        key = "gh api graphql " + sha256_bytes(query.encode())[:16]
        rec = self._cached(key, ok=(200,))
        if rec:
            return rec
        if not (self.use_gh and shutil.which("gh")):
            return {"via": "gh api graphql", "query": query, "error": "gh CLI not available (GraphQL needs auth)"}
        self._wait()
        self.n_network += 1
        t = utcnow()
        p = subprocess.run(["gh", "api", "graphql", "-f", "query=" + query], capture_output=True, text=True,
                           encoding="utf-8")
        rec = {"url": "https://api.github.com/graphql", "via": "gh api graphql", "query": query, "fetched_utc": t,
               "exit_code": p.returncode, "http_status": 200 if p.returncode == 0 else None}
        if p.returncode == 0:
            rec["body"] = json.loads(p.stdout)
        else:
            rec["stderr"] = p.stderr[:500]
        self.cache[key] = rec
        return rec


# ----------------------------------------------------------------------------- R5 lists
def read_ref_list(path):
    raw = Path(path).read_bytes()
    lines = [l.rstrip("\r") for l in raw.decode("utf-8").split("\n")]
    if raw.endswith(b"\n"):
        lines = lines[:-1]
    heads = [i for i, l in enumerate(lines) if l.strip() == "References"]
    if not heads:
        raise SystemExit(f"no line 'References' in {path}")
    h = heads[-1]
    refs = [{"line": j + 1, "text": lines[j].strip()} for j in range(h + 1, len(lines)) if lines[j].strip()]
    info = {"path": "<r5-dir>/" + Path(path).name, "sha256": sha256_bytes(raw), "lines_in_file": len(lines),
            "newline_count_wc_l": raw.count(b"\n"), "trailing_newline": raw.endswith(b"\n"),
            "references_heading_line": h + 1, "first_ref_line": refs[0]["line"], "last_ref_line": refs[-1]["line"],
            "n_refs": len(refs)}
    return info, refs, lines


def parse_ref(text):
    authors, rest = text.split(": ", 1) if ": " in text else ("", text)
    m = re.search(r"https?://(?:dx\.)?doi\.org/(.+?)(?=,\s|\s|$)", text)
    doi = m.group(1).rstrip(".") if m else None
    y = re.search(r"(\d{4})[a-z]?\.?\s*$", text)
    pre = re.split(r",\s*https?://", rest)[0]
    return {"authors": authors, "first_author": authors.split(", ")[0].strip() if authors else "",
            "year": int(y.group(1)) if y else None, "doi": doi, "pre_url": pre, "parts": pre.split(", ")}


def best_title(parts, targets):
    best = (0.0, parts[0] if parts else "", "")
    for k in range(1, len(parts) + 1):
        cand = ", ".join(parts[:k])
        for t in targets:
            if t:
                s = sim(cand, t)
                if s > best[0]:
                    best = (s, cand, t)
    return best


def vol_pages(parts, title_k):
    """(volume, pages) from the R5 tail 'Journal, Vol, Pages'; (None, None) when not in that form"""
    tail = parts[title_k:]
    if len(tail) >= 3 and re.fullmatch(r"\d+(?:[\u2013-]\d+)?", tail[-2]) and \
            re.fullmatch(r"[\w.]+(?:[\u2013-][\w.]+)?", tail[-1]):
        return tail[-2], tail[-1], tail
    return None, None, tail


def assess(msg, pr):
    cr_title = strip_tags(first(msg.get("title")))
    cr_sub = strip_tags(first(msg.get("subtitle")))
    targets = [cr_title] + ([cr_title + ": " + cr_sub] if cr_sub else [])
    s, r5_title, matched = best_title(pr["parts"], targets)
    title_k = len(r5_title.split(", ")) if r5_title else 1
    fam = cr_first_family(msg)
    fam_ok, fam_how = fam_match(pr["first_author"], fam)
    years = cr_years(msg)
    yfields = [k for k, v in years.items() if v == pr["year"]]
    notes = []
    vol, pages, tail = vol_pages(pr["parts"], title_k)
    if vol is not None:
        cv = msg.get("volume")
        if cv is not None and norm(cv) != norm(vol):
            notes.append(f"volume: R5 {vol} vs Crossref {cv}")
        cp, an = msg.get("page") or "", msg.get("article-number") or ""
        npg = norm(pages).split()
        if not cp and not an:
            notes.append(f"pages: R5 {pages}; Crossref returns no page or article-number")
        elif norm(pages) not in {norm(cp), norm(an)} and not (cp and npg and npg[0] == (norm(cp).split() or [""])[0]):
            notes.append(f"pages: R5 {pages} vs Crossref page {cp or '(none)'} / article-number {an or '(none)'}")
    elif pr["doi"]:
        notes.append(f"volume/pages not compared (R5 tail: {LQ}{', '.join(tail)}{RQ})")
    if re.search(r"<[a-zA-Z/][^>]*>", first(msg.get("title")) or ""):
        notes.append("the Crossref title contains markup tags (e.g. <scp>), as returned by Crossref")
    return {"title_sim": round(s, 3), "r5_title": r5_title, "crossref_title": matched or cr_title,
            "title_ok": s >= TITLE_SIM_MIN, "r5_first_author": pr["first_author"], "crossref_first_author": fam,
            "author_ok": fam_ok, "author_how": fam_how, "r5_year": pr["year"], "crossref_years": years,
            "year_fields_matched": yfields, "year_ok": bool(yfields), "notes": notes}


def detail_str(a):
    lab = {"published-print": "print", "published-online": "online", "issued": "issued"}
    bits = []
    if a["title_ok"]:
        bits.append(f"title {a['title_sim']:.3f}")
    else:
        bits.append(f"TITLE differs ({a['title_sim']:.3f}): R5 {LQ}{short(a['r5_title'], 90)}{RQ} vs Crossref "
                    f"{LQ}{short(a['crossref_title'], 90)}{RQ}")
    if a["author_ok"]:
        extra = "" if a["author_how"] == "exact" else f" ({a['author_how']}: Crossref {a['crossref_first_author']})"
        bits.append(f"1st author {a['r5_first_author']}{extra}")
    elif a["crossref_first_author"] is None:
        bits.append(f"1ST AUTHOR differs: R5 {a['r5_first_author']} vs Crossref (record has no author field)")
    else:
        bits.append(f"1ST AUTHOR differs: R5 {a['r5_first_author']} vs Crossref {a['crossref_first_author']}")
    if a["year_ok"]:
        other = {k: v for k, v in a["crossref_years"].items() if v != a["r5_year"]}
        bits.append(f"year {a['r5_year']} = " + "/".join(lab[k] for k in a["year_fields_matched"]) +
                    (f" ({years_str(other)})" if other else ""))
    else:
        bits.append(f"YEAR differs: R5 {a['r5_year']} vs Crossref {years_str(a['crossref_years'])}")
    return "; ".join(bits)


def make_key(family, year, title, used):
    fam = re.sub(r"[^a-z0-9]", "", fold(family or "anon").lower()) or "anon"
    words = [re.sub(r"[^a-z0-9]", "", fold(w).lower()) for w in strip_tags(title or "").split()]
    words = [w for w in words if w and w not in ("a", "an", "the", "on", "of")]
    key = f"{fam}{year or ''}{words[0] if words else ''}"
    k, i = key, 0
    while k in used:
        i += 1
        k = key + "abcdefghij"[i - 1]
    used.add(k)
    return k


def rekey(bib, key):
    bib = (bib or "").strip()
    m = re.match(r"@(\w+)\s*\{\s*([^,\s]*)\s*,", bib)
    if not m:
        return None
    return "@" + m.group(1) + "{" + key + "," + bib[m.end():]


def dc_publisher(attrs):
    p = attrs.get("publisher")
    return p if isinstance(p, str) else (p or {}).get("name")


def datacite_bib(attrs, key):
    names = []
    for c in attrs.get("creators") or []:
        if c.get("familyName") and c.get("givenName"):
            names.append(f"{c['familyName']}, {c['givenName']}")
        elif c.get("familyName"):
            names.append(c["familyName"])
        else:
            names.append("{" + (c.get("name") or "") + "}")
    fields = [("author", " and ".join(names)), ("title", first(attrs.get("titles") or [{}]).get("title")),
              ("publisher", dc_publisher(attrs)), ("year", attrs.get("publicationYear")),
              ("version", attrs.get("version")), ("doi", attrs.get("doi"))]
    etype = (attrs.get("types") or {}).get("bibtex") or "misc"
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v not in (None, ""))
    return f"@{etype}{{{key},\n{body}\n}}"


def dc_summary(attrs):
    return {"doi": attrs.get("doi"), "title": first(attrs.get("titles") or [{}]).get("title"),
            "creators": [c.get("name") for c in attrs.get("creators") or []],
            "creator_families": [c.get("familyName") or c.get("name") for c in attrs.get("creators") or []],
            "publisher": dc_publisher(attrs), "publicationYear": attrs.get("publicationYear"),
            "version": attrs.get("version"), "resourceTypeGeneral": (attrs.get("types") or {}).get("resourceTypeGeneral"),
            "url": attrs.get("url"), "state": attrs.get("state"), "registered": attrs.get("registered"),
            "dates": attrs.get("dates"),
            "has_version_count": sum(1 for r in attrs.get("relatedIdentifiers") or [] if r.get("relationType") == "HasVersion")}


# ----------------------------------------------------------------------------- extractors
def trim_cmr(j):
    keep = ("ShortName", "Version", "EntryTitle", "DOI", "CollectionCitations")
    return {"hits": j.get("hits"),
            "items": [{"meta": {k: it.get("meta", {}).get(k) for k in ("concept-id", "provider-id", "revision-date")},
                       "umm": {k: it.get("umm", {}).get(k) for k in keep}} for it in j.get("items") or []]}


def ex_confluence(b):
    raw = b.decode("utf-8", "replace")
    lines = html_to_lines(raw)
    m = re.search(r'datetime="Last modified on (\d{4}-\d{2}-\d{2})"', raw)
    t = re.search(r"(?is)<title>(.*?)</title>", raw)
    keep = [l for l in lines if re.search(r"ERA5T|expver", l)]
    cite = []
    for i, l in enumerate(lines):
        if l.startswith("How to acknowledge and cite ERA5"):
            for l2 in lines[i:i + 12]:
                if l2 == "References":
                    break
                cite.append(l2)
            break
    return {"title": html.unescape(t.group(1)).strip() if t else None, "last_modified": m.group(1) if m else None,
            "era5t_lines": keep, "citation_section": cite}


def ex_cds_layout(b):
    lay = json.loads(b.decode("utf-8"))
    out = {"era5t_sentences_elsewhere": [], "qa_updates": None, "citation_block": None, "doi_block": None}

    def walk(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)

    for o in walk(lay):
        if o.get("id") == "qa_data_records_updates":
            out["qa_updates"] = o.get("content")
        elif o.get("id") == "qa_documentation_content":
            out["qa_documentation_content"] = o.get("content")
        elif o.get("id") == "citation":
            out["citation_block"] = o.get("content")
        elif o.get("id") == "doi" and isinstance(o.get("content"), str):
            out["doi_block"] = o.get("content")
        elif isinstance(o.get("content"), str) and "ERA5T" in o["content"]:
            out["era5t_sentences_elsewhere"] += [flat(s) for s in re.findall(r"[^.\n]*ERA5T[^.\n]*\.", o["content"])]
    return out


def ex_meteo_terms(b):
    raw = b.decode("utf-8", "replace")
    t = re.search(r"(?is)<title>(.*?)</title>", raw)
    heading, items, paras = None, [], []
    h = re.search(r"(?is)<h2[^>]*>([^<]*" + GR_TERMS + r"[^<]*)</h2>", raw)
    if h:
        heading = flat(html.unescape(h.group(1)))
        rest = raw[h.end():]
        w0 = rest.find('class="well"')
        seg = rest[w0:] if w0 >= 0 else rest
        ul = re.search(r"(?is)<ul[^>]*>(.*?)</ul>", seg)
        if ul:
            for k, li in enumerate(re.findall(r"(?is)<li[^>]*>(.*?)</li>", ul.group(1)), start=1):
                parts = html_to_lines(li)          # block tags (div/br/p) split, inline tags removed
                items.append(" ".join(parts))
                paras += [{"li": k, "text": p_} for p_ in parts]
    links = []
    for a in re.finditer(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw):
        if re.search(r"noa\.gr|terms|licen|creativecommons", a.group(1), re.I):
            links.append({"href": a.group(1), "label": flat(html.unescape(re.sub(r"<[^>]+>", " ", a.group(2))))})
    full = " ".join(items)
    attribution = None
    for p_ in paras:
        m = re.search(GR_SOURCE_COLON + r"\s*(.+?)\.?$", p_["text"])
        if m and GR_LOGO in p_["text"]:
            attribution = m.group(1).strip()
    return {"title": html.unescape(t.group(1)).strip() if t else None, "heading": heading, "items": items,
            "paragraphs": paras, "links_terms_noa_licence": links,
            "has_prohibition_sentence": any(p_["text"].startswith(GR_PROHIBITED) for p_ in paras),
            "has_logo_attribution_sentence": any(GR_LOGO in p_["text"] for p_ in paras), "attribution_string": attribution,
            "mentions_open_licence": bool(re.search(r"creative\s*commons|CC[ -]BY|open data|" + GR_LICENCE, full, re.I))}


def ex_meteo_index_en(b):
    raw = b.decode("utf-8", "replace")
    out = []
    for a in re.finditer(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw):
        lab = flat(html.unescape(re.sub(r"<[^>]+>", " ", a.group(2))))
        if re.search(r"terms|disclaim|policy|licen|noa\.gr", a.group(1) + " " + lab, re.I):
            out.append({"href": a.group(1), "label": lab})
    return {"terms_like_links": out}


def ex_51_3(b):
    raw = b.decode("utf-8", "replace")
    if raw.startswith("%PDF"):
        return {"format": "pdf", "note": "PDF not parsed by this script"}
    txt = " ".join(html_to_lines(raw))
    hits = []
    for m in re.finditer(r"51\.3\s*%", txt):
        s0 = txt.rfind(". ", 0, m.start())
        s0 = s0 + 2 if s0 >= 0 else 0
        e0 = txt.find(". ", m.end())
        e0 = e0 + 1 if e0 >= 0 else len(txt)
        hits.append(txt[s0:e0].strip())
    return {"format": "html", "sentences_with_51_3": hits,
            "context_infiltration_or_recharge": [bool(re.search(r"infiltration|recharge", h, re.I)) for h in hits]}


# ----------------------------------------------------------------------------- repo records
def repo_records(root):
    rec = {}
    y = root / "reproduction/v14_rerun/configs/crete_sens_karst_q1914.yaml"
    yt = y.read_text(encoding="utf-8")
    nb = re.search(r"(?ms)^notes:\n(.*?)^[^\s-]", yt)
    rec["karst_yaml"] = {"path": y.relative_to(root).as_posix(), "notes_raw": nb.group(1).rstrip() if nb else None,
                         "mentions": {k: (k in yt) for k in ("qinf", "0.513", "1.914", "51.3", "Steiakakis", "karst")},
                         "infiltration_enabled_false": bool(re.search(r"(?m)^infiltration:\n\s+enabled: false", yt))}
    p1 = root / "reproduction/v14_rerun/scripts/phase1.py"
    if p1.exists():
        lines = p1.read_text(encoding="utf-8").split("\n")
        rec["phase1_py"] = {"path": p1.relative_to(root).as_posix(),
                            "lines": [(i + 1, l.strip()) for i, l in enumerate(lines) if "crete_sens_karst_q1914" in l or "1.914" in l]}
    led = (root / "reproduction/emsr933/rule_ledger.md").read_text(encoding="utf-8")
    m = re.search(r"(?s)   - (\(c\) \*\*Karst bracket\*\*.*?)(?=\n   - \(|\n\d+\. |\n## |\Z)", led)
    rec["ledger_8_5c"] = m.group(1).strip() if m else None
    m = re.search(r"(?s)\n- (\*\*Licence\.\*\*.*?)(?=\n- \*\*|\n## |\Z)", led)
    rec["ledger_7_licence"] = m.group(1).strip() if m else None
    m = re.search(r"(?s)\n- (\*\*Source\.\*\*.*?)(?=\n- \*\*)", led)
    rec["ledger_7_source"] = m.group(1).strip() if m else None
    ks = (root / "reproduction/emsr933/karst_recharge_sources.md").read_text(encoding="utf-8")
    m = re.search(r"(?s)## 1\. Primary.*?\n(.*?)(?=\n## 2\.)", ks)
    sec1 = m.group(1).strip() if m else ""
    rec["karst_sources_sec1"] = sec1
    f1 = flat(sec1)
    c18 = re.search(r"\*\*Steiakakis, E\. \((\d{4})\)\.\*\* (.+?)\. \*(\w+)\* (\d+)\((\d+)\), (\d+)\. (https://doi\.org/\S+)", f1)
    c11 = re.search(r"(Steiakakis, [^(]+?) \((\d{4})\), in \*(.+?)\* vol\. (\d+), (\w+), (\d+)[\u2013-](\d+), (https://doi\.org/\S+)", f1)
    rec["claim_2018"] = dict(zip(["year", "title", "journal", "volume", "issue", "article", "doi_url"], c18.groups())) if c18 else None
    rec["claim_2011"] = dict(zip(["authors", "year", "book", "volume", "publisher", "first_page", "last_page", "doi_url"],
                                 c11.groups())) if c11 else None
    q = re.search(r'Verbatim: "(.*?51\.3%\*\*\.?)"', f1)
    rec["karst_sources_quote"] = q.group(1).replace("**", "") if q else None
    prov = (root / "reproduction/v14_rerun/code14/E_d5_provenance.md").read_text(encoding="utf-8")
    m = re.search(r"github\.com/([\w.-]+)/([\w.-]+)/issues/386", prov)
    rec["sfincs_repo"] = {"owner": m.group(1), "repo": m.group(2)} if m else None
    src = (root / "reproduction/emsr933/noa_stations/sources.md").read_text(encoding="utf-8")
    m = re.search(r"(?s)## 5\. Licence / terms of use\n(.*?)(?=\n## )", src)
    rec["noa_sources_sec5"] = m.group(1).strip() if m else None
    gi = root / "reproduction/emsr933/noa_stations/.gitignore"
    rec["noa_gitignore"] = gi.read_text(encoding="utf-8").strip() if gi.exists() else None
    return rec


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manuscript", required=True)
    ap.add_argument("--supplement", required=True)
    ap.add_argument("--outdir", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--page-dir", default=None)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-gh", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir).resolve()
    root = next(p for p in Path(__file__).resolve().parents if (p / "reproduction").is_dir() and (p / ".git").exists())
    raw_path = outdir / "refs_crossref_raw.json"
    cache = {}
    if raw_path.exists():
        old = json.loads(raw_path.read_text(encoding="utf-8"))
        cache = dict(old.get("requests", {}))
        for e in old.get("entries", []):
            for rec in e.get("lookups", []):
                if isinstance(rec, dict) and rec.get("cache_key"):
                    cache[rec["cache_key"]] = rec
    page_dir = Path(args.page_dir).resolve() if args.page_dir else None
    if page_dir is not None:
        try:
            page_dir.relative_to(root)
            raise SystemExit("--page-dir must be outside the repository")
        except ValueError:
            pass
        page_dir.mkdir(parents=True, exist_ok=True)
    F = Fetcher(cache, args.refresh, page_dir, not args.no_gh)
    started = utcnow()

    # ---------------- R5 lists
    m_info, m_refs, m_lines = read_ref_list(args.manuscript)
    s_info, s_refs, _ = read_ref_list(args.supplement)
    entries, by_key = [], {}
    for where, refs in (("manuscript", m_refs), ("supplement", s_refs)):
        for r in refs:
            pr = parse_ref(r["text"])
            key = (pr["doi"] or "").lower() or norm(r["text"])
            if key in by_key:
                e = by_key[key]
                e["where"][where] = r["line"]
                e["text_identical"] = e["text_identical"] and (e["text"] == r["text"])
                continue
            e = {"n": len(entries) + 1, "text": r["text"], "where": {where: r["line"]}, "parsed": pr,
                 "text_identical": True, "lookups": []}
            entries.append(e)
            by_key[key] = e

    used_keys, bib_entries, dc_entries = set(), [], []

    def crossref_bib(msg, year_for_key, comment_lines, role):
        doi = msg["DOI"]
        t = F.text(f"{CROSSREF}/works/{doi_path(doi)}/transform/application/x-bibtex")
        key = make_key(cr_first_family(msg), year_for_key, first(msg.get("title")), used_keys)
        out = {"role": role, "doi": doi, "key": key, "transform_url": t["url"], "fetched_utc": t.get("fetched_utc"),
               "http_status": t.get("http_status"), "bib": None, "bib_year": None, "comments": list(comment_lines)}
        body = rekey(t.get("body_text"), key) if t.get("http_status") == 200 else None
        if body:
            ym = re.search(r"\byear\s*=\s*\{?(\d{4})", body)
            out["bib"], out["bib_year"] = body, (int(ym.group(1)) if ym else None)
            if not re.search(r"\btitle\s*=", body):
                out["comments"].append(f"% NOTE: Crossref's BibTeX output has no title field; the Crossref JSON title is "
                                       f"{LQ}{strip_tags(first(msg.get('title')))}{RQ}")
            if not re.search(r"\bauthor\s*=", body):
                out["comments"].append("% NOTE: Crossref's BibTeX output has no author field (the Crossref JSON record "
                                       "has no author either)" if not msg.get("author") else
                                       "% NOTE: Crossref's BibTeX output has no author field")
            if re.search(r"<[a-zA-Z/][^>]*>", re.sub(r"\b(?:url|DOI)=\{[^}]*\}", "", body)):
                out["comments"].append("% NOTE: the title contains markup tags and line breaks exactly as returned by "
                                       "Crossref (kept verbatim)")
        bib_entries.append(out)
        return out

    for e in entries:
        pr = e["parsed"]
        key_doi = (pr["doi"] or "").lower()
        if key_doi in REPLACE_DOI:
            new_doi, why = REPLACE_DOI[key_doi]
            e["replaced_doi"], e["replacement_reason"] = pr["doi"], why
            pr = dict(pr, doi=new_doi)
            e["parsed_effective"] = pr
        if key_doi in DROP_DOI:
            e["drop_bib"], e["drop_reason"] = True, DROP_DOI[key_doi]
        if pr["doi"]:
            rec = F.json(f"{CROSSREF}/works/{doi_path(pr['doi'])}")
            e["lookups"].append(rec["url"])
            if rec.get("http_status") == 200:
                msg = rec["body"]["message"]
                a = assess(msg, pr)
                e.update(crossref=cr_summary(msg), assessment=a, doi_crossref=msg.get("DOI"))
                e["status"] = "verified" if (a["title_ok"] and a["author_ok"] and a["year_ok"]) else "mismatch"
                e["detail"] = detail_str(a)
                if e.get("replaced_doi"):
                    e["status"] = "replaced" if (a["title_ok"] and a["author_ok"]) else "mismatch"
                    e["detail"] = f"R5 cites {e['replaced_doi']}; {e['replacement_reason']}; Crossref record of the replacement: " + detail_str(a)
                if e.get("drop_bib"):
                    e["status"], e["detail"] = "dropped", e["drop_reason"] + "; Crossref record of the R5 entry: " + detail_str(a)
                yk = pr["year"] if a["year_ok"] else a["crossref_years"].get("issued")
                if e.get("drop_bib"):
                    e["bib_key"] = None
                    continue
                cm = ["% MISMATCH: " + detail_str(a)] if e["status"] == "mismatch" else []
                if e.get("replaced_doi"):
                    cm = [f"% REPLACED (decision 21 Oct 2026): R5 cites {e['replaced_doi']} ({e['replacement_reason']})"] + cm
                b = crossref_bib(msg, yk, cm, f"R5 #{e['n']}")
                e["lookups"].append(b["transform_url"])
                e["bib_key"] = b["key"]
                if b.get("bib_year") and b["bib_year"] != pr["year"]:
                    b["comments"].append(f"% NOTE: the Crossref BibTeX year is {b['bib_year']}; the R5 year is "
                                         f"{pr['year']} (Crossref {years_str(a['crossref_years'])})")
            elif rec.get("http_status") == 404:
                ag = F.json(f"{CROSSREF}/works/{doi_path(pr['doi'])}/agency")
                e["lookups"].append(ag["url"])
                agency = (((ag.get("body") or {}).get("message") or {}).get("agency") or {}).get("id")
                e["agency"], e["doi_crossref"] = agency, None
                if agency == "datacite":
                    e["status"] = "not in Crossref (DataCite DOI)"
                    dc = F.json(f"{DATACITE}/dois/{pr['doi']}")
                    e["lookups"].append(dc["url"])
                    if dc.get("http_status") == 200:
                        at = dc["body"]["data"]["attributes"]
                        e["datacite"] = dc_summary(at)
                        s_, t_, _ = best_title(pr["parts"], [e["datacite"]["title"]])
                        fam = first(e["datacite"]["creator_families"])
                        fok = fam_match(pr["first_author"], fam)[0]
                        yok = str(at.get("publicationYear")) == str(pr["year"])
                        e["detail"] = (f"Crossref 404; registration agency (Crossref /agency) = DataCite. DataCite record: "
                                       f"{LQ}{short(e['datacite']['title'], 80)}{RQ} (title sim {s_:.2f} with R5 "
                                       f"{LQ}{short(t_, 60)}{RQ}); 1st creator {fam} ({'=' if fok else NEQ} R5 "
                                       f"{pr['first_author']}); year {at.get('publicationYear')} ({'=' if yok else NEQ} R5 "
                                       f"{pr['year']}); publisher {e['datacite']['publisher']}; resourceTypeGeneral "
                                       f"{e['datacite']['resourceTypeGeneral']}; registered {e['datacite']['registered']}; "
                                       f"landing URL {e['datacite']['url']}")
                        dsm = e["datacite"]
                        if dsm["has_version_count"]:
                            e["detail"] += (f"; concept-type record with {dsm['has_version_count']} HasVersion links, "
                                            f"metadata of version {dsm['version']} (dates: "
                                            + ", ".join(f"{d_.get('dateType')} {d_.get('date')}" for d_ in dsm["dates"] or [])
                                            + ")")
                        key = make_key(fam, at.get("publicationYear"), e["datacite"]["title"], used_keys)
                        dc_entries.append({"role": f"R5 #{e['n']}", "doi": at.get("doi"), "key": key, "url": dc["url"],
                                           "fetched_utc": dc.get("fetched_utc"), "bib": datacite_bib(at, key),
                                           "resourceTypeGeneral": e["datacite"]["resourceTypeGeneral"]})
                        e["bib_key_datacite"] = key
                    else:
                        e["detail"] = f"Crossref 404; /agency = DataCite; DataCite API HTTP {dc.get('http_status')}"
                else:
                    e["status"] = "not found"
                    e["detail"] = f"Crossref /works HTTP 404; /agency: {agency or ag.get('http_status')}"
            else:
                e["status"], e["doi_crossref"] = "not found", None
                e["detail"] = f"Crossref request failed: HTTP {rec.get('http_status')} {rec.get('error', '')}"
        else:
            q = urllib.parse.urlencode({"query.bibliographic": e["text"], "rows": 3})
            rec = F.json(f"{CROSSREF}/works?{q}")
            e["lookups"].append(rec["url"])
            its = ((rec.get("body") or {}).get("message") or {}).get("items") or []
            e["doi_crossref"] = None
            if its:
                top = its[0]
                a = assess(top, pr)
                e["search_top_hit"], e["assessment"] = cr_summary(top), a
                e["search_other_hits"] = [{"DOI": h.get("DOI"), "title": strip_tags(first(h.get("title"))),
                                           "first_author": cr_first_family(h), "years": cr_years(h)} for h in its[1:]]
                n_ok = sum([a["title_ok"], a["author_ok"], a["year_ok"]])
                e["status"] = "verified" if n_ok == 3 else ("mismatch" if n_ok == 2 else "not found")
                e["doi_crossref"] = top.get("DOI") if n_ok >= 2 else None
                e["detail"] = (f"no DOI in R5; Crossref query.bibliographic top hit {top.get('DOI')} "
                               f"{LQ}{short(strip_tags(first(top.get('title'))), 80)}{RQ} "
                               f"({first(top.get('container-title')) or top.get('type')}; {years_str(cr_years(top))}): "
                               + detail_str(a) + ("" if n_ok >= 2 else f" {EMDASH} not a plausible match"))
                if n_ok >= 2:
                    yk = pr["year"] if a["year_ok"] else a["crossref_years"].get("issued")
                    b = crossref_bib(top, yk, [] if n_ok == 3 else ["% MISMATCH: " + detail_str(a)], f"R5 #{e['n']}")
                    e["lookups"].append(b["transform_url"])
                    e["bib_key"] = b["key"]
            else:
                e["status"] = "not found"
                e["detail"] = "no DOI in R5; Crossref search returned no items"
        for nt in (e.get("assessment") or {}).get("notes", []):
            e["detail"] += f"; note: {nt}"

    items = {}
    repo = repo_records(root)
    items["repo_records"] = repo

    # ---------------- item 1: tide citation
    tb = next((e for e in entries if (e["parsed"]["doi"] or "").lower() == "10.1016/s0967-0637(00)00024-8"), None)
    cites = []
    for i, l in enumerate(m_lines[: m_info["references_heading_line"] - 1]):
        j = l.find("Tsimplis and Bryden")
        if j >= 0:
            cites.append({"line": i + 1, "excerpt": (ELL if j > 110 else "") + l[max(0, j - 110): j + 35] + ELL})
    q = urllib.parse.urlencode({"query.bibliographic": "Tsimplis Proctor Flather 1995 two-dimensional tidal model Mediterranean Sea",
                                "rows": 5})
    srch = F.json(f"{CROSSREF}/works?{q}")
    hits = ((srch.get("body") or {}).get("message") or {}).get("items") or []
    it1 = {"tsimplis_bryden_2000": (tb or {}).get("crossref"), "tsimplis_bryden_2000_status": (tb or {}).get("status"),
           "tsimplis_bryden_2000_url": ((tb or {}).get("lookups") or [None])[0], "citing_lines": cites,
           "search_url": srch["url"], "search_fetched_utc": srch.get("fetched_utc"),
           "search_hits": [{"DOI": h.get("DOI"), "title": strip_tags(first(h.get("title"))),
                            "first_author": cr_first_family(h), "years": cr_years(h)} for h in hits]}
    if hits:
        full = F.json(f"{CROSSREF}/works/{doi_path(hits[0]['DOI'])}")
        msg = full["body"]["message"] if full.get("http_status") == 200 else hits[0]
        fams = [norm(a.get("family") or "") for a in msg.get("author") or []]
        crit = {"first_author_Tsimplis": norm(cr_first_family(msg) or "") == "tsimplis",
                "coauthors_Proctor_Flather": ("proctor" in fams and "flather" in fams),
                "year_1995": 1995 in cr_years(msg).values(),
                "title_sim_vs_task_descriptor": round(sim(first(msg.get("title")) or "",
                                                          "a two-dimensional tidal model of the Mediterranean Sea"), 3)}
        crit["verified"] = (crit["first_author_Tsimplis"] and crit["coauthors_Proctor_Flather"] and crit["year_1995"]
                            and crit["title_sim_vs_task_descriptor"] >= TITLE_SIM_MIN)
        it1.update(tpf_1995=cr_summary(msg), tpf_1995_record_url=full["url"], tpf_1995_fetched_utc=full.get("fetched_utc"),
                   tpf_1995_criteria=crit)
        if crit["verified"]:
            b = crossref_bib(msg, 1995, ["% replaces the tide citation Tsimplis & Bryden (2000) (item 1; decision 21 Oct 2026)"], "item (1)")
            it1["tpf_1995_bib_key"] = b["key"]
    items["1"] = it1

    # ---------------- item 2: karst recharge coefficient
    it2 = {}
    for tag, doi in (("steiakakis_2018", "10.3390/geosciences8010019"), ("steiakakis_2011", "10.1007/978-3-642-19902-8_57")):
        r = F.json(f"{CROSSREF}/works/{doi_path(doi)}")
        it2[tag] = {"url": r["url"], "fetched_utc": r.get("fetched_utc"), "http_status": r.get("http_status")}
        if r.get("http_status") != 200:
            continue
        msg = r["body"]["message"]
        it2[tag]["record"] = cr_summary(msg)
        it2[tag]["resource_primary"] = ((msg.get("resource") or {}).get("primary") or {}).get("URL")
        it2[tag]["links"] = [l.get("URL") for l in msg.get("link") or []]
        if tag == "steiakakis_2018" and repo.get("claim_2018"):
            c = repo["claim_2018"]
            it2[tag]["vs_ledger"] = {
                "title_sim": round(sim(c["title"], first(msg.get("title")) or ""), 3),
                "first_author": cr_first_family(msg), "years": cr_years(msg),
                "journal": (first(msg.get("container-title")), c["journal"]),
                "volume": (msg.get("volume"), c["volume"]), "issue": (msg.get("issue"), c["issue"]),
                "page_or_article": (msg.get("page") or msg.get("article-number"), c["article"])}
        if tag == "steiakakis_2011" and repo.get("claim_2011"):
            c = repo["claim_2011"]
            it2[tag]["vs_ledger"] = {
                "author_families": ([a.get("family") for a in msg.get("author") or []],
                                    [x.strip() for x in re.split(r",|&", c["authors"]) if x.strip()]),
                "book": (first(msg.get("container-title")), c["book"]), "years": cr_years(msg),
                "year_claimed": c["year"], "volume": (msg.get("volume"), c["volume"]),
                "pages": (msg.get("page"), f"{c['first_page']}-{c['last_page']}"),
                "publisher": (msg.get("publisher"), c["publisher"])}
    q = urllib.parse.urlencode({"query.author": "Steiakakis", "rows": 100,
                                "select": "DOI,title,author,container-title,type,issued,published-print,published-online,volume,page"})
    r = F.json(f"{CROSSREF}/works?{q}")
    its = ((r.get("body") or {}).get("message") or {}).get("items") or []
    cands = []
    for h in its:
        if "steiakakis" in [norm(a.get("family") or "") for a in h.get("author") or []]:
            cands.append({"DOI": h.get("DOI"), "title": strip_tags(first(h.get("title"))),
                          "authors": [fmt_author(a) for a in h.get("author") or []],
                          "venue": first(h.get("container-title")), "type": h.get("type"), "years": cr_years(h)})
    it2["author_search"] = {"url": r["url"], "fetched_utc": r.get("fetched_utc"),
                            "total_results": ((r.get("body") or {}).get("message") or {}).get("total-results"),
                            "returned": len(its), "with_author_family_Steiakakis": cands}
    mdpi = []
    s18 = it2.get("steiakakis_2018", {})
    for u in [s18.get("resource_primary")] + (s18.get("links") or []):
        if u:
            rr = F.extract(u, "mdpi_" + re.sub(r"\W+", "_", u.split("//", 1)[-1])[-40:], ex_51_3)
            mdpi.append({k: rr.get(k) for k in ("url", "fetched_utc", "http_status", "content_type", "bytes", "sha256",
                                                 "extract", "body_head", "error")})
    it2["mdpi_fulltext_check"] = mdpi
    items["2"] = it2

    # ---------------- item 3: IMERG V07 Late / Final data-set DOIs
    it3 = {}
    for tag, sn in (("late", "GPM_3IMERGHHL"), ("final", "GPM_3IMERGHH")):
        r = F.json(CMR + "?" + urllib.parse.urlencode({"short_name": sn, "version": "07"}), trim=trim_cmr)
        its = (r.get("body") or {}).get("items") or []
        umm = its[0]["umm"] if its else {}
        doi = (umm.get("DOI") or {}).get("DOI")
        d = {"short_name": sn, "cmr_url": r["url"], "cmr_fetched_utc": r.get("fetched_utc"),
             "cmr_hits": (r.get("body") or {}).get("hits"), "cmr_entry_title": umm.get("EntryTitle"), "cmr_doi": doi,
             "cmr_concept_id": its[0]["meta"].get("concept-id") if its else None,
             "cmr_collection_citation": first(umm.get("CollectionCitations"))}
        if doi:
            dc = F.json(f"{DATACITE}/dois/{doi}")
            d["datacite_url"], d["datacite_fetched_utc"] = dc["url"], dc.get("fetched_utc")
            if dc.get("http_status") == 200:
                at = dc["body"]["data"]["attributes"]
                d["datacite"] = dc_summary(at)
                existing = next((x for x in dc_entries if (x["doi"] or "").lower() == (at.get("doi") or "").lower()), None)
                if existing:
                    existing["role"] += f"; item (3) IMERG V07 {tag} run"
                    d["bib_key"] = existing["key"]
                else:
                    key = make_key(first(d["datacite"]["creator_families"]), at.get("publicationYear"),
                                   d["datacite"]["title"], used_keys)
                    dc_entries.append({"role": f"item (3) IMERG V07 {tag} run", "doi": at.get("doi"), "key": key,
                                       "url": dc["url"], "fetched_utc": dc.get("fetched_utc"), "bib": datacite_bib(at, key),
                                       "resourceTypeGeneral": d["datacite"]["resourceTypeGeneral"]})
                    d["bib_key"] = key
        it3[tag] = d
    items["3"] = it3

    # ---------------- item 4: ERA5T
    it4 = {}
    r = F.json(CDS_CATALOGUE)
    body = r.get("body") or {}
    desc = body.get("description") or ""
    it4["cds_catalogue"] = {"url": r["url"], "fetched_utc": r.get("fetched_utc"), "http_status": r.get("http_status"),
                            "title": body.get("title"), "sci:doi": body.get("sci:doi"),
                            "license_links": [l for l in body.get("links", []) if l.get("rel") == "license"],
                            "era5t_lines": [l.strip() for l in desc.split("\n") if "ERA5T" in l]}
    lay = next((l["href"] for l in body.get("links", []) if l.get("rel") == "layout"), None)
    if lay:
        lr = F.extract(lay, "cds_layout", ex_cds_layout)
        it4["cds_layout"] = {k: lr.get(k) for k in ("url", "fetched_utc", "http_status", "bytes", "sha256", "extract")}
    cr = F.extract(ECMWF_ERA5_DOC, "ecmwf_era5_doc", ex_confluence)
    it4["ecmwf_doc"] = {k: cr.get(k) for k in ("url", "fetched_utc", "http_status", "bytes", "sha256", "extract", "error")}
    exc = (it4["ecmwf_doc"].get("extract") or {})
    lx = ((it4.get("cds_layout") or {}).get("extract") or {})
    it4["separate_era5t_citation_found"] = bool(
        any(re.search(r"\bcite|citation|DOI", l, re.I) for l in exc.get("era5t_lines") or []) or
        any("ERA5T" in l for l in exc.get("citation_section") or []) or "ERA5T" in (lx.get("citation_block") or ""))
    dsdoi = body.get("sci:doi")
    if dsdoi:
        dc = F.json(f"{DATACITE}/dois/{dsdoi}")
        it4["datacite_url"], it4["datacite_fetched_utc"] = dc["url"], dc.get("fetched_utc")
        if dc.get("http_status") == 200:
            at = dc["body"]["data"]["attributes"]
            it4["datacite"] = dc_summary(at)
            key = make_key(first(it4["datacite"]["creator_families"]), at.get("publicationYear"), it4["datacite"]["title"],
                           used_keys)
            dc_entries.append({"role": "item (4) candidate data-set citation (CDS catalogue entry)", "doi": at.get("doi"),
                               "key": key, "url": dc["url"], "fetched_utc": dc.get("fetched_utc"),
                               "bib": datacite_bib(at, key), "resourceTypeGeneral": it4["datacite"]["resourceTypeGeneral"]})
            it4["bib_key"] = key
    hers = next((e for e in entries if (e["parsed"]["doi"] or "").lower() == "10.1002/qj.3803"), None)
    it4["hersbach_2020_status"] = (hers or {}).get("status")
    it4["r5_lists_cds_doi"] = any("10.24381" in e["text"] for e in entries)
    items["4"] = it4

    # ---------------- item 5: SFINCS GitHub issues
    it5 = {}
    sr = repo.get("sfincs_repo") or {"owner": "Deltares", "repo": "SFINCS"}
    o, rp = sr["owner"], sr["repo"]
    it5["repo"] = f"{o}/{rp}"
    for n in (253, 386, 254):
        g = F.github(f"repos/{o}/{rp}/issues/{n}")
        b = g.get("body") or {}
        it5[str(n)] = {"api": g.get("url"), "via": g.get("via"), "fetched_utc": g.get("fetched_utc"),
                       "number": b.get("number"), "title": b.get("title"), "created_at": b.get("created_at"),
                       "user": (b.get("user") or {}).get("login"), "state": b.get("state"),
                       "state_reason": b.get("state_reason"), "closed_at": b.get("closed_at"),
                       "closed_by": (b.get("closed_by") or {}).get("login"), "comments": b.get("comments"),
                       "html_url": b.get("html_url"), "is_pull_request": bool(b.get("pull_request"))}
    g = F.github(f"repos/{o}/{rp}/pulls/254")
    b = g.get("body") or {}
    it5["pull_254"] = {"api": g.get("url"), "via": g.get("via"), "fetched_utc": g.get("fetched_utc"),
                       "title": b.get("title"), "state": b.get("state"), "merged": b.get("merged"),
                       "merged_at": b.get("merged_at"), "merged_by": (b.get("merged_by") or {}).get("login"),
                       "user": (b.get("user") or {}).get("login"), "head_ref": (b.get("head") or {}).get("ref"),
                       "base_ref": (b.get("base") or {}).get("ref"), "html_url": b.get("html_url"),
                       "created_at": b.get("created_at"),
                       "body_first_line": ((b.get("body") or "").replace("\r", "").split("\n") or [""])[0]}
    for n in (253, 386):
        qg = ('query { repository(owner:"%s", name:"%s") { issue(number:%d) { number '
              'closedByPullRequestsReferences(first:10, includeClosedPrs:true) { nodes { number title state merged '
              'mergedAt url headRefName } } } } }') % (o, rp, n)
        gq = F.github_graphql(qg)
        iss = ((((gq.get("body") or {}).get("data") or {}).get("repository") or {}).get("issue") or {})
        it5[f"linked_prs_{n}"] = {"via": gq.get("via"), "fetched_utc": gq.get("fetched_utc"),
                                  "nodes": (iss.get("closedByPullRequestsReferences") or {}).get("nodes"),
                                  "error": gq.get("error") or gq.get("stderr")}
    tl = F.github(f"repos/{o}/{rp}/issues/253/timeline?per_page=100")
    it5["timeline_253"] = {"fetched_utc": tl.get("fetched_utc"), "via": tl.get("via"),
                           "events": [{"event": ev.get("event"), "created_at": ev.get("created_at"),
                                       "actor": (ev.get("actor") or {}).get("login"),
                                       "source_issue": ((ev.get("source") or {}).get("issue") or {}).get("number")}
                                      for ev in (tl.get("body") or [])]}
    items["5"] = it5

    # ---------------- item 6: NOA / meteo.gr
    it6 = {}
    t = F.extract(METEO_TERMS, "meteo_terms", ex_meteo_terms)
    it6["terms"] = {k: t.get(k) for k in ("url", "fetched_utc", "http_status", "content_type", "bytes", "sha256",
                                          "extract", "error", "body_head")}
    t = F.extract(METEO_INDEX_EN, "meteo_index_en", ex_meteo_index_en)
    it6["index_en"] = {k: t.get(k) for k in ("url", "fetched_utc", "http_status", "bytes", "sha256", "extract", "error")}
    lag = next((e for e in entries if (e["parsed"]["doi"] or "").lower() == "10.1002/gdj3.44"), None)
    it6["lagouvardos_2017_status"] = (lag or {}).get("status")
    it6["lagouvardos_2017"] = (lag or {}).get("crossref")
    items["6"] = it6

    # ---------------- outputs
    generated = utcnow()
    entry_keys = set()
    entries_out = []
    for e in entries:
        eo = dict(e)
        eo["lookups"] = []
        for u in e["lookups"]:
            entry_keys.add(u)
            if u in F.cache:
                eo["lookups"].append({"cache_key": u, **F.cache[u]})
        entries_out.append(eo)
    requests_out = {k: v for k, v in F.cache.items() if k in F.used and k not in entry_keys}
    raw_out = {"generated_utc": generated, "run_started_utc": started, "script": "reproduction/r6/scripts/build_refs.py",
               "user_agent": UA, "min_interval_s": MIN_INTERVAL_S, "network_requests_this_run": F.n_network,
               "cache_hits_this_run": F.n_cached,
               "note": "entries[].lookups hold the raw Crossref/DataCite responses of each R5 reference (request URL, "
                       "fetched_utc, HTTP status, body); 'requests' holds the item-level responses (Crossref searches, "
                       "DataCite, NASA CMR, CDS catalogue, GitHub) and, for web pages, SHA-256 + extracted text only.",
               "inputs": {"manuscript": m_info, "supplement": s_info},
               "entries": entries_out, "items": items, "bib_crossref": bib_entries, "bib_datacite": dc_entries,
               "requests": requests_out}
    raw_path.write_text(json.dumps(raw_out, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["% refs.bib -- Crossref-sourced BibTeX for the R5 reference lists (manuscript + supplement)",
         f"% Generated {generated} by reproduction/r6/scripts/build_refs.py; provenance in refs_crossref_raw.json.",
         "% Each entry body is the verbatim output of https://api.crossref.org/works/{doi}/transform/application/x-bibtex;",
         "% only the citation key was replaced (first-author family + year + first title word, from Crossref fields).",
         "% DataCite-registered DOIs are NOT here (see refs_datacite.bib). Do not edit by hand; re-run the script.", ""]
    for b in bib_entries:
        e = next((x for x in entries if x.get("bib_key") == b["key"]), None)
        if e:
            L.append(f"% {b['role']} ({'/'.join(e['where'])}; status {e['status']}): " + short(e["text"], 110))
            L.append(f"% source: {b['transform_url']} fetched {b['fetched_utc']} (HTTP {b['http_status']})")
            L += b["comments"]
        else:
            L += b["comments"]
            L.append(f"% {b['role']} -- not an R5 reference; source: {b['transform_url']} fetched {b['fetched_utc']} "
                     f"(HTTP {b['http_status']})")
        L.append(b["bib"] if b["bib"] else f"% (no BibTeX returned by the transform endpoint for {b['doi']})")
        L.append("")
    (outdir / "refs.bib").write_text("\n".join(L), encoding="utf-8")

    L = ["% refs_datacite.bib -- DataCite-sourced entries (NOT Crossref).",
         "% Built only from fields returned by https://api.datacite.org/dois/{doi} (creators, titles, publisher,",
         "% publicationYear, version, doi; entry type = DataCite types.bibtex). Kept separate from refs.bib.",
         f"% Generated {generated} by reproduction/r6/scripts/build_refs.py; raw records in refs_crossref_raw.json.", ""]
    for d in dc_entries:
        L.append(f"% {d['role']} -- DataCite record {d['url']} fetched {d['fetched_utc']}; "
                 f"resourceTypeGeneral={d['resourceTypeGeneral']}")
        L.append(d["bib"])
        L.append("")
    (outdir / "refs_datacite.bib").write_text("\n".join(L), encoding="utf-8")

    write_report(outdir, generated, started, m_info, s_info, entries, items, bib_entries, dc_entries, F)
    print(f"done: {len(entries)} unique references; network requests {F.n_network}, cache hits {F.n_cached}")
    for st in ("verified", "replaced", "dropped", "mismatch", "not found", "not in Crossref (DataCite DOI)"):
        print(f"  {st}: {sum(1 for e in entries if e['status'] == st)}")


# ----------------------------------------------------------------------------- report
def ans2011(it):
    d = it.get("steiakakis_2011") or {}
    rc, vl = d.get("record") or {}, d.get("vs_ledger") or {}
    if not rc:
        return f"The 2011 DOI was not resolved by Crossref (HTTP {d.get('http_status')})."
    lab = {"author_families": "authors (family names)", "book": "book title", "pages": "pages"}
    same = [lab[k] for k in ("author_families", "book", "pages") if vl.get(k) and vl[k][0] == vl[k][1]]
    if vl.get("year_claimed") and int(vl["year_claimed"]) in (vl.get("years") or {}).values():
        same.append("year")
    diff = []
    if vl.get("volume") and str(vl["volume"][0] or "") != str(vl["volume"][1] or ""):
        diff.append(f"volume (Crossref {vl['volume'][0] or '(none)'} / ledger {vl['volume'][1]})")
    if vl.get("publisher") and vl["publisher"][0] != vl["publisher"][1]:
        diff.append(f"publisher wording (Crossref {LQ}{vl['publisher'][0]}{RQ} / ledger {LQ}{vl['publisher'][1]}{RQ})")
    return (f"The 2011 DOI resolves in Crossref to the book chapter {LQ}{md(rc.get('title'))}{RQ} "
            f"({md('; '.join(rc.get('authors') or []))}; {LQ}{md(rc.get('container_title'))}{RQ}, {rc.get('publisher')}, "
            f"pp. {rc.get('page')}, {years_str(rc.get('years'))}); it agrees with the ledger in "
            f"{', '.join(same) or 'none of the compared fields'}"
            + (f" and differs in {', '.join(diff)}" if diff else "") +
            ". Whether the chapter's text contains the 51.3 % figure was not checked here (the repo records the chapter as "
            "paywalled and the number as not verified there).")


def write_report(outdir, generated, started, m_info, s_info, entries, items, bib_entries, dc_entries, F):
    R = []
    w = R.append
    w(f"# R6 part E {EMDASH} reference check of the R5 reference lists")
    w("")
    w(f"Generated **{generated}** (run started {started}) by `reproduction/r6/scripts/build_refs.py`. Raw responses with "
      f"request URL and UTC fetch time: `refs_crossref_raw.json`. Network requests in this run: {F.n_network}; responses "
      f"reused from the cache: {F.n_cached} (a reused response keeps its original fetch time).")
    w("")
    w("## Method")
    w("")
    for tag, inf in (("manuscript", m_info), ("supplement", s_info)):
        w(f"- **Input {tag}:** `{inf['path']}` (SHA-256 `{inf['sha256'][:16]}{ELL}`): heading `References` on line "
          f"{inf['references_heading_line']}, **{inf['n_refs']} entries on lines {inf['first_ref_line']}{ENDASH}"
          f"{inf['last_ref_line']}** (the file has {inf['lines_in_file']} lines; trailing newline: "
          f"{'yes' if inf['trailing_newline'] else 'no'}, so `wc -l` reports {inf['newline_count_wc_l']}).")
    nb = sum(1 for e in entries if len(e["where"]) == 2)
    w(f"- Deduplicated by DOI (by normalised text when there is no DOI): **{len(entries)} unique references**; {nb} appear "
      f"in both lists; every supplement entry is textually identical to its manuscript entry: "
      f"{'yes' if all(e['text_identical'] for e in entries) else 'NO'}.")
    w(f"- **Bibliographic source = Crossref REST API only.** DOI given {ARROW} `GET https://api.crossref.org/works/{{doi}}`; "
      f"HTTP 404 {ARROW} `GET {ELL}/works/{{doi}}/agency` (registration agency). DataCite-registered DOIs are reported as "
      "*not in Crossref (DataCite DOI)*; their DataCite record (`https://api.datacite.org/dois/{doi}`) feeds only "
      f"`refs_datacite.bib` and the detail column. No DOI {ARROW} `GET https://api.crossref.org/works?query.bibliographic="
      "<full reference text>&rows=3`, top hit judged by the same rule.")
    w(f"- **Matching rule.** *verified* = title similarity {chr(8805)} {TITLE_SIM_MIN:.2f} (difflib ratio on text that is "
      "NFKD-folded, stripped of diacritics and markup, case-folded, with every run of punctuation/whitespace replaced by one "
      "space; the R5 title is the comma-delimited prefix of the text after the author colon that best matches the Crossref "
      "title or title + subtitle), first-author family name equal after the same normalisation (a match on the last name "
      "token only, i.e. a particle difference, would be accepted and flagged), and R5 year equal to the Crossref "
      "published-print, published-online or issued year (the matching field(s) are listed). *mismatch* = a record exists but "
      "at least one criterion fails (both values shown). *not found* = DOI unknown to Crossref (404 and agency not DataCite) "
      "or no plausible search hit (plausible = at least two of the three criteria hold). Volume/page differences are listed "
      "as notes and do not change the status.")
    w(f"- **HTTP etiquette.** User-Agent `{UA}`, no e-mail address in any header or URL, {chr(8805)} {MIN_INTERVAL_S} s "
      "between requests (< 2 requests/s), exponential backoff on 429/5xx/network errors. GitHub via `gh api` (REST + "
      "GraphQL). Web pages (CDS/ECMWF documentation, meteo.gr, MDPI) were parsed as data only; the repository keeps their "
      "SHA-256, size and the extracted sentences, not the pages.")
    w("- **refs.bib** entry bodies are Crossref's own `.../transform/application/x-bibtex` output, verbatim except the citation "
      "key (first-author family + year + first title word, generated from Crossref fields). Mismatches carry a `% MISMATCH:` "
      "line; entries whose Crossref BibTeX year differs from the R5 year carry a `% NOTE:` line.")
    w("")
    w("## Reference table")
    w("")
    w("| # | R5 reference (first author, year, short title) | in | DOI (R5) | DOI (Crossref) | status | detail |")
    w("|---|---|---|---|---|---|---|")
    for e in entries:
        pr = e["parsed"]
        a = e.get("assessment") or {}
        ttl = a.get("r5_title") or (pr["parts"][0] if pr["parts"] else "")
        if e.get("datacite"):
            ttl = best_title(pr["parts"], [e["datacite"]["title"]])[1] or ttl
        loc = ", ".join(("M" if k == "manuscript" else "S") + str(v) for k, v in e["where"].items())
        where = "both" if len(e["where"]) == 2 else next(iter(e["where"]))
        w(f"| {e['n']} | {md(pr['first_author'])} {pr['year']}, {md(short(ttl, 60))} | {where} ({loc}) | "
          f"{md(pr['doi'] or EMDASH)} | {md(e.get('doi_crossref') or EMDASH)} | **{e['status']}** | {md(e['detail'])} |")
    w("")
    w("## Counts")
    w("")
    for st in ("verified", "replaced", "dropped", "mismatch", "not found", "not in Crossref (DataCite DOI)"):
        lst = [str(e["n"]) for e in entries if e["status"] == st]
        w(f"- **{st}:** {len(lst)}" + (f" (# {', '.join(lst)})" if lst and st != "verified" else ""))
    w(f"- total: {len(entries)}; refs.bib entries: {sum(1 for b in bib_entries if b['bib'])} (Crossref-held R5 references "
      f"+ proposed additions); refs_datacite.bib entries: {len(dc_entries)}.")
    notes = [(e["n"], nt) for e in entries for nt in (e.get("assessment") or {}).get("notes", [])]
    if notes:
        w("- Notes (do not affect the status): " + "; ".join(f"#{n}: {md(nt)}" for n, nt in notes) + ".")
    w("")
    w("### Entries needing attention (from the table)")
    w("")
    for e in entries:
        pr = e["parsed"]
        tag = f"#{e['n']} {md(pr['first_author'])} {pr['year']}"
        if e["status"] in ("mismatch", "not found"):
            w(f"- {tag} ({e['status']}): {md(e['detail'])}")
        elif e.get("datacite"):
            dsm = e["datacite"]
            s_ = best_title(pr["parts"], [dsm["title"]])[0]
            diffs = []
            if s_ < TITLE_SIM_MIN:
                diffs.append(f"title {LQ}{md(dsm['title'])}{RQ} (sim {s_:.2f})")
            if not fam_match(pr["first_author"], first(dsm["creator_families"]))[0]:
                diffs.append(f"first creator {md(first(dsm['creator_families']))}")
            if str(dsm["publicationYear"]) != str(pr["year"]):
                diffs.append(f"publicationYear {dsm['publicationYear']}")
            if diffs:
                w(f"- {tag} (DataCite DOI {pr['doi']}): the DataCite record differs from R5 in " + "; ".join(diffs) + ".")
    for n, nt in notes:
        if "markup" in nt or "no page" in nt or ("R5 tail" in nt and re.search(r"\d:\d", nt)):
            w(f"- #{n}: {md(nt)}" + (" (R5 uses the form volume:pages here, unlike the other entries)."
                                     if re.search(r"\d:\d", nt) else "."))
    w("")

    I, rr = items, items["repo_records"]
    w("## Items")
    w("")
    # (1) ------------------------------------------------------------------
    it = I["1"]
    w(f"### (1) Tide citation ({LQ}Aegean M2 < 5 cm{RQ})")
    w("")
    w("R5 manuscript lines citing *Tsimplis and Bryden, 2000*: " +
      "; ".join(f"line {c['line']}: {LQ}{md(c['excerpt'])}{RQ}" for c in it["citing_lines"]) + ".")
    w("")
    tb, tp = it.get("tsimplis_bryden_2000") or {}, it.get("tpf_1995") or {}
    w("| Crossref field | R5 citation: Tsimplis & Bryden (2000) | Crossref search hit: Tsimplis, Proctor & Flather (1995) |")
    w("|---|---|---|")
    for lab, k in (("title", "title"), ("authors", "authors"), ("journal", "container_title"), ("volume", "volume"),
                   ("issue", "issue"), ("pages", "page"), ("year (Crossref date fields)", "years"), ("DOI", "DOI"),
                   ("type", "type")):
        def fv(d, k=k):
            return "; ".join(d.get(k) or []) if k == "authors" else (years_str(d.get(k)) if k == "years" else d.get(k))
        w(f"| {lab} | {md(fv(tb))} | {md(fv(tp))} |")
    w("")
    w(f"Sources: `{it.get('tsimplis_bryden_2000_url')}` (table status: {it.get('tsimplis_bryden_2000_status')}); search "
      f"`{it['search_url']}` fetched {it.get('search_fetched_utc')}; top hit re-read from `{it.get('tpf_1995_record_url')}` "
      f"fetched {it.get('tpf_1995_fetched_utc')}. Other hits of that search: " +
      ("; ".join(f"{h['DOI']} ({h['first_author']}, {years_str(h['years'])}, {LQ}{md(short(h['title'], 60))}{RQ})"
                 for h in it["search_hits"][1:]) or "none") + ".")
    w("")
    crit = it.get("tpf_1995_criteria") or {}
    w(f"Check of the 1995 hit: first author Tsimplis {crit.get('first_author_Tsimplis')}; co-authors Proctor and Flather "
      f"{crit.get('coauthors_Proctor_Flather')}; year 1995 {crit.get('year_1995')}; title similarity to the task descriptor "
      f"{LQ}a two-dimensional tidal model of the Mediterranean Sea{RQ} = {crit.get('title_sim_vs_task_descriptor')} {ARROW} "
      f"**{'verified' if crit.get('verified') else 'not verified'}**." +
      (f" Added to refs.bib as `{it['tpf_1995_bib_key']}` under `% proposed replacement for the tide citation (item 1)`."
       if it.get("tpf_1995_bib_key") else " Not added to refs.bib."))
    w("")
    w(f"**Answer (1):** by the Crossref titles, the Mediterranean tidal model is the 1995 record ({LQ}{md(tp.get('title'))}"
      f"{RQ}, {md(tp.get('container_title'))}, https://doi.org/{tp.get('DOI')}); the cited 2000 record is {LQ}"
      f"{md(tb.get('title'))}{RQ} ({md(tb.get('container_title'))}). The M2 < 5 cm figure itself was not checked here.")
    w("")
    # (2) ------------------------------------------------------------------
    it = I["2"]
    w(f"### (2) Source of the 0.513 (51.3 %) recharge coefficient {EMDASH} run `crete_sens_karst_q1914`")
    w("")
    ky = rr["karst_yaml"]
    w(f"- **Config `{ky['path']}`:** its `notes:` block does not mention the coefficient (strings present in the file: " +
      ", ".join(f"`{k}` {'yes' if v else 'no'}" for k, v in ky["mentions"].items()) +
      f"; `infiltration.enabled: false`: {'yes' if ky['infiltration_enabled_false'] else 'no'}). Notes, verbatim:")
    w("")
    w("```")
    w(ky["notes_raw"] or "(none)")
    w("```")
    if rr.get("phase1_py"):
        w(f"- The constant rate is a post-build patch defined in `{rr['phase1_py']['path']}`: " +
          "; ".join(f"line {n}: `{short(l, 240)}`" for n, l in rr["phase1_py"]["lines"]) + ".")
    w(f"- **Ledger {chr(167)}8 item 5(c)** (`reproduction/emsr933/rule_ledger.md`), verbatim: {LQ}"
      f"{md(flat(rr.get('ledger_8_5c') or '(not found)'))}{RQ}")
    w(f"- **`reproduction/emsr933/karst_recharge_sources.md` {chr(167)}1** records the sentence as read from the article "
      f"PDF (p. 4{ENDASH}5) on 2026-10-19: {LQ}{md(flat(rr.get('karst_sources_quote') or '(not parsed)'))}{RQ}; of the "
      f"2011 chapter it says {LQ}paywalled; number not verified there directly{RQ}.")
    w("")
    for tag, lab in (("steiakakis_2018", "DOI 10.3390/geosciences8010019 (ledger: Steiakakis 2018)"),
                     ("steiakakis_2011", "DOI 10.1007/978-3-642-19902-8_57 (ledger: Steiakakis et al. 2011)")):
        d = it.get(tag) or {}
        rc = d.get("record") or {}
        eds = f"editors {md('; '.join(rc.get('editors')))}; " if rc.get("editors") else ""
        w(f"**Crossref {EMDASH} {lab}** (`{d.get('url')}`, fetched {d.get('fetched_utc')}, HTTP {d.get('http_status')}): "
          f"title {LQ}{md(rc.get('title'))}{RQ}; authors {md('; '.join(rc.get('authors') or []))}; {eds}venue "
          f"{LQ}{md(rc.get('container_title'))}{RQ}; volume {rc.get('volume') or '(none)'}, issue {rc.get('issue') or '(none)'}, "
          f"page {rc.get('page') or '(none)'}; publisher {md(rc.get('publisher'))}; type {rc.get('type')}; "
          f"{years_str(rc.get('years'))}; "
          f"licence {md(', '.join(rc.get('license') or []) or 'none returned')}.")
        vl = d.get("vs_ledger")
        if vl:
            def rv(x):
                if x is None or x == "":
                    return "(none)"
                if isinstance(x, list):
                    return ", ".join(str(y) for y in x)
                if isinstance(x, dict):
                    return years_str(x)
                return str(x)
            w("")
            w("  Against the repo record (Crossref / repo): " + "; ".join(
                (f"{k}: {md(rv(v[0]))} / {md(rv(v[1]))}" if isinstance(v, tuple) else f"{k}: {md(rv(v))}")
                for k, v in vl.items()) + ".")
        w("")
    a_s = it["author_search"]
    w(f"**Crossref author search** `{a_s['url']}` (fetched {a_s['fetched_utc']}; total-results {a_s['total_results']}, "
      f"{a_s['returned']} returned; {len(a_s['with_author_family_Steiakakis'])} carry an author with family name Steiakakis):")
    w("")
    w(f"| DOI | year | title | venue | authors | title words ({KARST_LABEL}) |")
    w("|---|---|---|---|---|---|")
    for c in sorted(a_s["with_author_family_Steiakakis"], key=lambda c: (c["years"].get("issued") or 0, c["DOI"])):
        kw = sorted(set(m_.group(0).lower() for m_ in re.finditer(KARST_WORDS, c["title"] or "", re.I)))
        w(f"| {c['DOI']} | {c['years'].get('issued')} | {md(short(c['title'], 90))} | {md(short(c['venue'] or c['type'], 45))} "
          f"| {md(short('; '.join(c['authors']), 80))} | {', '.join(kw) or EMDASH} |")
    w("")
    w(f"**Full-text check for {LQ}51.3{RQ}** (open-access article, CC BY per Crossref; URLs taken from the Crossref record):")
    for mc in it["mdpi_fulltext_check"]:
        ex = mc.get("extract") or {}
        if mc.get("http_status") == 200 and ex.get("sentences_with_51_3"):
            w(f"- `{mc['url']}` fetched {mc['fetched_utc']}, HTTP 200: " +
              " | ".join(f"{LQ}{md(s)}{RQ}" for s in ex["sentences_with_51_3"]))
        else:
            extra = f"; {ex['note']}" if ex.get("note") else ""
            if mc.get("http_status") == 200 and ex.get("format") == "html":
                extra += "; no sentence with 51.3 %"
            w(f"- `{mc['url']}` fetched {mc['fetched_utc']}: HTTP {mc.get('http_status')} ({mc.get('content_type')}, "
              f"{mc.get('bytes')} bytes){extra}.")
    w("")
    vl18 = (it.get("steiakakis_2018") or {}).get("vs_ledger") or {}
    ok18 = bool(vl18) and vl18["title_sim"] >= TITLE_SIM_MIN and norm(vl18.get("first_author") or "") == "steiakakis" \
        and 2018 in (vl18.get("years") or {}).values() and all(str(vl18[k][0]) == str(vl18[k][1])
                                                              for k in ("journal", "volume", "issue", "page_or_article"))
    got = any((mc.get("extract") or {}).get("sentences_with_51_3") for mc in it["mdpi_fulltext_check"])
    rc18 = (it.get("steiakakis_2018") or {}).get("record") or {}
    if ok18:
        w(f"**Answer (2): full reference + DOI verified by Crossref** {EMDASH} {md('; '.join(rc18.get('authors') or []))} "
          f"({(rc18.get('years') or {}).get('issued')}): {md(rc18.get('title'))}. *{md(rc18.get('container_title'))}* "
          f"{rc18.get('volume')}({rc18.get('issue')}), {rc18.get('page')}. https://doi.org/{rc18.get('DOI')} {EMDASH} identical "
          "to the ledger's citation in title, author, year, journal, volume, issue and article number. " +
          ("The 51.3 % sentence was found in the fetched full text (quoted above)." if got else
           "The value 51.3 % itself was not re-read in the article text in this run (publisher responses above); it rests on "
           "the verbatim quote recorded in `karst_recharge_sources.md`.") + " " + ans2011(it))
    else:
        w("**Answer (2):** the Crossref record for the ledger's DOI does not match the ledger's citation in every field "
          "(comparison above).")
    w("")
    # (3) ------------------------------------------------------------------
    it = I["3"]
    w("### (3) IMERG V07 half-hourly data-set citations (DataCite)")
    w("")
    L3, F3 = it.get("late") or {}, it.get("final") or {}
    dl, dfn = L3.get("datacite") or {}, F3.get("datacite") or {}
    w("DOIs found with the NASA CMR collection search (GES DISC metadata, `short_name` + `version=07`); metadata from DataCite:")
    w("")
    w("| field | Late Run (`GPM_3IMERGHHL` V07) | Final Run (`GPM_3IMERGHH` V07; R5 Huffman et al.) |")
    w("|---|---|---|")
    w(f"| CMR query (hits, fetched) | `{md(L3.get('cmr_url'))}` ({L3.get('cmr_hits')}, {L3.get('cmr_fetched_utc')}) | "
      f"`{md(F3.get('cmr_url'))}` ({F3.get('cmr_hits')}, {F3.get('cmr_fetched_utc')}) |")
    w(f"| CMR entry title / concept id | {md(L3.get('cmr_entry_title'))} / {L3.get('cmr_concept_id')} | "
      f"{md(F3.get('cmr_entry_title'))} / {F3.get('cmr_concept_id')} |")
    w(f"| CMR DOI | {L3.get('cmr_doi')} | {F3.get('cmr_doi')} |")
    for lab, k in (("DataCite DOI", "doi"), ("title", "title"), ("creators", "creators"), ("publisher", "publisher"),
                   ("publicationYear", "publicationYear"), ("version", "version"),
                   ("resourceTypeGeneral", "resourceTypeGeneral"), ("registered URL", "url")):
        def fv(d, k=k):
            v = "; ".join(d.get(k) or []) if k == "creators" else d.get(k)
            return "(none returned)" if v in (None, "") else v
        w(f"| {lab} | {md(fv(dl))} | {md(fv(dfn))} |")
    w(f"| DataCite record (fetched) | `{L3.get('datacite_url')}` ({L3.get('datacite_fetched_utc')}) | "
      f"`{F3.get('datacite_url')}` ({F3.get('datacite_fetched_utc')}) |")
    w(f"| refs_datacite.bib key | `{L3.get('bib_key')}` | `{F3.get('bib_key')}` |")
    cc, cf = L3.get("cmr_collection_citation") or {}, F3.get("cmr_collection_citation") or {}
    w(f"| CMR CollectionCitation (release date) | {md(cc.get('Creator'))}; {md(cc.get('Title'))}; {md(cc.get('Publisher'))} "
      f"({cc.get('ReleaseDate')}) | {md(cf.get('Creator'))}; {md(cf.get('Title'))}; {md(cf.get('Publisher'))} "
      f"({cf.get('ReleaseDate')}) |")
    w("")
    hf = next((e for e in entries if (e["parsed"]["doi"] or "").lower() == (dfn.get("doi") or "#").lower()), None)
    if hf:
        fams = r5_families(hf["parsed"]["authors"])
        w(f"R5 Huffman et al. (row #{hf['n']}) vs the DataCite Final-Run record: authors R5 {len(fams)} "
          f"({md(', '.join(fams))}) vs DataCite {len(dfn.get('creator_families') or [])} "
          f"({md(', '.join(dfn.get('creator_families') or []))}); title R5 {LQ}{md(best_title(hf['parsed']['parts'], [dfn.get('title')])[1])}"
          f"{RQ} vs DataCite {LQ}{md(dfn.get('title'))}{RQ}; publisher R5 text contains {LQ}NASA Goddard Earth Sciences Data and "
          f"Information Services Center (GES DISC){RQ} vs DataCite {LQ}{md(dfn.get('publisher'))}{RQ}; year R5 "
          f"{hf['parsed']['year']} vs DataCite {dfn.get('publicationYear')}.")
    w("")
    w(f"**Answer (3):** Late Run V07 (`GPM_3IMERGHHL`) DOI **{L3.get('cmr_doi') or dl.get('doi')}**; Final Run V07 "
      f"(`GPM_3IMERGHH`) DOI **{F3.get('cmr_doi') or dfn.get('doi')}** (the DOI R5 cites). Both are DataCite DOIs (DataCite "
      "returns them lower-cased) and both are in refs_datacite.bib.")
    w("")
    # (4) ------------------------------------------------------------------
    it = I["4"]
    w("### (4) ERA5T and the ERA5 citation")
    w("")
    cat = it["cds_catalogue"]
    lic = ", ".join(f"{l.get('href', '')} ({l.get('title', '')})" for l in cat["license_links"])
    w(f"- **CDS catalogue entry** (`{cat['url']}`, the JSON behind {CDS_DATASET_PAGE}; fetched {cat['fetched_utc']}, HTTP "
      f"{cat['http_status']}): title {LQ}{md(cat['title'])}{RQ}, `sci:doi` **{cat['sci:doi']}**, licence link {md(lic)}. "
      "Overview text, verbatim:")
    for s in cat["era5t_lines"]:
        w(f"  > {s}")
    lay = it.get("cds_layout") or {}
    lx = lay.get("extract") or {}
    if lx:
        mq = re.search(r"Forward extensions[^|]*", lx.get("qa_updates") or "")
        w(f"- **CDS dataset-page layout** (`{lay.get('url')}`, fetched {lay.get('fetched_utc')}, SHA-256 "
          f"`{(lay.get('sha256') or '')[:16]}{ELL}`): quality-assurance criterion 2.3.1 ({LQ}Updates{RQ}), comment verbatim:")
        w(f"  > {mq.group(0).strip() if mq else '(not found on this fetch)'}")
        mk = re.search(r"Key references:[^|]*", lx.get("qa_documentation_content") or "")
        w(f"  criterion 4.1.3 ({LQ}Documentation / Content{RQ}), comment excerpt verbatim:")
        w(f"  > {mk.group(0).strip() if mk else '(not found on this fetch)'}")
        w(f"  and the {LQ}Citation and attribution{RQ} block, verbatim (Markdown as served):")
        for ln in (lx.get("citation_block") or "").split("\n"):
            if ln.strip():
                w(f"  > {ln.strip()}")
    ed = it.get("ecmwf_doc") or {}
    ex = ed.get("extract") or {}
    w(f"- **ECMWF Confluence {LQ}{md(ex.get('title'))}{RQ}** (`{ed.get('url')}`, fetched {ed.get('fetched_utc')}, HTTP "
      f"{ed.get('http_status')}; page last modified {ex.get('last_modified')}), verbatim:")
    for p in (r"^Initial release data", r"^For the CDS, ERA5T data for a month is overwritten", r"expver=0005",
              r"^The full ERA5 and ERA5T datasets", r"^ERA5 \(and recent ERA5T\)"):
        hit = next((l for l in ex.get("era5t_lines") or [] if re.search(p, l)), None)
        if hit and len(hit) > 320:
            hit = re.split(r"(?<=\.)\s", hit)[0]
        w(f"  > {hit if hit else '(pattern ' + p + ' not found on this fetch)'}")
    if ex.get("citation_section"):
        w(f"  Section {LQ}How to acknowledge and cite ERA5{RQ}, verbatim lines: " +
          " / ".join(f"{LQ}{md(l)}{RQ}" for l in ex["citation_section"][1:9]))
    dc = it.get("datacite") or {}
    w(f"- **Candidate data-set citation {EMDASH} DataCite record of {cat['sci:doi']}** (`{it.get('datacite_url')}`, fetched "
      f"{it.get('datacite_fetched_utc')}): title {LQ}{md(dc.get('title'))}{RQ}; creators {md('; '.join(dc.get('creators') or []))}; "
      f"publisher {LQ}{md(dc.get('publisher'))}{RQ}; publicationYear {dc.get('publicationYear')}; resourceTypeGeneral "
      f"{dc.get('resourceTypeGeneral')}; registered URL {dc.get('url')}. In refs_datacite.bib as `{it.get('bib_key')}`. "
      "Note: the CDS page's own suggested citation texts (quoted above) give other creators and another year than this "
      "DataCite record.")
    w(f"- **Answer (4):** both documentation sources describe ERA5T as the initial (early) release of ERA5, updated daily "
      f"(about 5 days behind real time) and served through the same CDS entry {LQ}{md(cat['title'])}{RQ}; it is replaced by "
      "the final ERA5 after 2 to 3 months (CDS overview and QA text) / about two months after the month in question (ECMWF "
      "documentation); ERA5T is identified in GRIB by `expver=0005`. A separate ERA5T citation or DOI: "
      f"{'found' if it.get('separate_era5t_citation_found') else 'none on these pages'}. The CDS citation instructions are "
      f"per catalogue entry (DOI {cat['sci:doi']}), i.e. they cover whatever release of that entry was downloaded, ERA5T "
      f"included; Hersbach et al. (2020) (R5 status *{it.get('hersbach_2020_status')}*) is the key reference named in the "
      f"CDS QA text. R5 lists the CDS catalogue-entry DOI: {'yes' if it.get('r5_lists_cds_doi') else 'no'}.")
    w("")
    # (5) ------------------------------------------------------------------
    it = I["5"]
    w(f"### (5) SFINCS GitHub issues ({it['repo']}; owner/repo read from `reproduction/v14_rerun/code14/E_d5_provenance.md`)")
    w("")
    w("| # | kind | title | opened (UTC) | author | state | closed (UTC) | URL |")
    w("|---|---|---|---|---|---|---|---|")
    for n in ("253", "386", "254"):
        d = it[n]
        st = d["state"] + (f" ({d['state_reason']})" if d.get("state_reason") else "")
        w(f"| {n} | {'pull request' if d['is_pull_request'] else 'issue'} | {md(d['title'])} | {d['created_at']} | "
          f"{d['user']} | {st} | {d['closed_at'] or EMDASH} | {d['html_url']} |")
    p = it["pull_254"]
    w("")
    w(f"Sources: `gh api repos/{it['repo']}/issues/{{253,386,254}}` and `{ELL}/pulls/254` (fetched {it['253']['fetched_utc']} "
      f"to {p['fetched_utc']}). PR #254: state {p['state']}, merged **{p['merged']}** at {p['merged_at']} by "
      f"{p['merged_by']}; head branch `{p['head_ref']}` {ARROW} `{p['base_ref']}`; the {LQ}{ELL}{RQ} at the end of the "
      f"title is part of the title as returned by the API, and the PR body begins {LQ}{md(p.get('body_first_line'))}{RQ}.")
    l253, l386 = it["linked_prs_253"], it["linked_prs_386"]
    nodes = l253.get("nodes") or []
    w(f"Linked PRs (GraphQL `closedByPullRequestsReferences`, fetched {l253.get('fetched_utc')}): #253 {ARROW} " +
      (", ".join(f"#{x['number']} ({x['state']}, merged {x['merged']}, {x['mergedAt']})" for x in nodes) or "none") +
      f"; #386 {ARROW} " + (", ".join(f"#{x['number']}" for x in (l386.get("nodes") or [])) or "none") + ".")
    w("Timeline of #253: " + "; ".join(f"{x['event']} {x['created_at']} by {x['actor']}" +
                                        (f" (from #{x['source_issue']})" if x.get("source_issue") else "")
                                        for x in it["timeline_253"]["events"]) + ".")
    w("")
    linked = any(x["number"] == 254 for x in nodes)
    w(f"**Answer (5):** #253 {LQ}{md(it['253']['title'])}{RQ}, opened {it['253']['created_at']} by {it['253']['user']}, "
      f"state {it['253']['state']} ({it['253']['state_reason']}, closed {it['253']['closed_at']} by {it['253']['closed_by']}); "
      f"#386 {LQ}{md(it['386']['title'])}{RQ}, opened "
      f"{it['386']['created_at']} by {it['386']['user']}, {it['386']['state']}, {it['386']['comments']} comments. #254 "
      + ("**is** the PR linked to #253 (it closes #253)" if linked else "is **not** linked to #253") +
      f": {LQ}{md(p['title'])}{RQ} by {p['user']}, {p['state']}, merged = {p['merged']} ({p['merged_at']}).")
    w("")
    # (6) ------------------------------------------------------------------
    it = I["6"]
    w("### (6) NOA automatic weather-station network (meteo.gr) " + EMDASH + " attribution and terms")
    w("")
    w(f"- **Repo record:** ledger {chr(167)}7: {LQ}{md(flat(rr.get('ledger_7_licence') or '(not found)'))}{RQ}")
    if rr.get("noa_gitignore"):
        gi = " ".join(l.lstrip("# ").strip() for l in rr["noa_gitignore"].split("\n") if l.startswith("#"))
        w(f"- `reproduction/emsr933/noa_stations/.gitignore`: {LQ}{md(gi)}{RQ}")
    t = it["terms"]
    tx = t.get("extract") or {}
    w(f"- **Provider terms page re-fetched:** `{t['url']}` at **{t['fetched_utc']}**, HTTP {t['http_status']}, page title "
      f"{LQ}{md(tx.get('title'))}{RQ} (SHA-256 `{(t.get('sha256') or '')[:16]}{ELL}`). The section {LQ}{md(tx.get('heading'))}"
      f"{RQ} is a list of {len(tx.get('items') or [])} items; verbatim (Greek, as published; one quoted line per rendered "
      "block, item number in brackets):")
    for p_ in tx.get("paragraphs") or []:
        w(f"  > [{p_['li']}] {p_['text']}")
    lk = sorted(set(x["href"] for x in tx.get("links_terms_noa_licence") or []
                    if re.search(r"noa\.gr|licen|creativecommons", x["href"], re.I)))
    w(f"  Open-licence wording (Creative Commons / CC BY / open data / {GR_LICENCE}) in these paragraphs: "
      f"{'present' if tx.get('mentions_open_licence') else 'none'}. Links on the page to noa.gr or licence pages: "
      f"{md(', '.join(lk)) or 'none'}.")
    ie = it["index_en"]
    iex = ie.get("extract") or {}
    tl_ = iex.get("terms_like_links") or []
    w(f"- **English version:** `{ie['url']}` fetched {ie['fetched_utc']} (HTTP {ie['http_status']}); its terms-type links: " +
      (", ".join(f"{LQ}{md(x['label'])}{RQ} {ARROW} `{x['href']}`" for x in tl_) or "none") +
      (". No separate English terms page was found: the English site's TERMS link points to the same `terms.cfm` page."
       if tl_ and all(x["href"].rstrip("/").endswith("terms.cfm") for x in tl_) else "."))
    lg = it.get("lagouvardos_2017") or {}
    w(f"- **Citable reference (Crossref; table status *{it.get('lagouvardos_2017_status')}*):** "
      f"{md('; '.join(lg.get('authors') or []))} ({years_str(lg.get('years'))}): {LQ}{md(lg.get('title'))}{RQ}, "
      f"{md(lg.get('container_title'))} {lg.get('volume')}({lg.get('issue')}), {lg.get('page')}, https://doi.org/{lg.get('DOI')}.")
    if tx.get("has_prohibition_sentence") and tx.get("has_logo_attribution_sentence"):
        w(f"- **Answer (6):** attribution asked by the provider = the source mark {LQ}{md(tx.get('attribution_string'))}{RQ} "
          "together with the site logo on any third-party report, table or other presentation of the station "
          "measurements; licence = none stated beyond these terms: reproduction of the site's information is prohibited "
          "without the consent of the National Observatory of Athens and without citing the source (quoted above). "
          "Citable network reference: Lagouvardos et al. (2017).")
    else:
        w("- **Answer (6):** the expected prohibition/attribution sentences were not found on this fetch; see the text above.")
    w("")
    w("## Files written")
    w("")
    for f in ("scripts/build_refs.py", "refs_crossref_raw.json", "refs.bib", "refs_datacite.bib", "REFERENCES_REPORT.md"):
        w(f"- `reproduction/r6/{f}`")
    (outdir / "REFERENCES_REPORT.md").write_text("\n".join(R) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
