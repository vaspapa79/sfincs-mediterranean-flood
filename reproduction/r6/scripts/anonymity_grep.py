"""CODE-16 D (2026-10-21) — anonymity dry run: REPORT ONLY, nothing is changed.

Scans (a) every file of the tracked tree at a tag (default v1.4.2; file contents read from git, not the working tree) and (b) the
records written after the tag (files changed or added since the tag in the working tree, tracked or not, under the given record
roots) for identifying strings, by class:
  author names (Latin and Greek forms, accent-insensitive), author handles / initials, affiliations (CERTH, ITI), e-mail addresses,
  ORCIDs, 'vaspapa', github.com URLs, Zenodo DOIs / records, grant numbers, 'ECHO'.
Text files are scanned line by line; PNG files through their text chunks (tEXt / iTXt / zTXt metadata); other binaries are listed
as not scanned. This script and its report contain the patterns by construction and are excluded from the scan.
Output: reproduction/r6/ANONYMITY_REPORT.md (+ anonymity_hits.json beside it).
Usage: python -I anonymity_grep.py --repo <worktree> [--tag v1.4.2] [--records reproduction/r6,reproduction/v14_rerun/code16,...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import struct
import subprocess
import sys
import unicodedata
import zlib
from pathlib import Path

AUTHORS = ["Papaioannou", "Valsamis", "Anagnostopoulos", "Moumtzidou", "Gialampoukidis", "Vrochidis", "Kompatsiaris"]
AUTHORS_EL = ["Παπαϊωάννου", "Βαλσάμης", "Αναγνωστόπουλος", "Μουμτζίδου", "Γιαλαμπουκίδης", "Βροχίδης", "Κομπατσιάρης"]


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


CLASSES = [  # (class, compiled regex, applies to accent-stripped lower-cased text?)
    ("author names", re.compile(r"\b(" + "|".join(a.lower() for a in AUTHORS) + r")\w*", re.I), False),
    ("author names (Greek)", re.compile("(" + "|".join(strip_accents(a).lower() for a in AUTHORS_EL) + ")"), True),
    ("author handles / initials", re.compile(r"\b(d?m?valsamis\w*|dmvalsamis|DvS)\b"), False),
    ("affiliation: CERTH", re.compile(r"\bCERTH\b|Centre for Research (and|&) Technology", re.I), False),
    ("affiliation: ITI", re.compile(r"\bITI\b|Information Technologies Institute"), False),
    ("e-mail addresses", re.compile(r"\b[A-Za-z0-9._%+-]*[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"), False),
    ("ORCIDs", re.compile(r"orcid\.org|\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b", re.I), False),
    ("vaspapa", re.compile(r"vaspapa\w*", re.I), False),
    ("github.com URLs", re.compile(r"github\.com[/\w.\-]*", re.I), False),
    ("Zenodo DOIs / records", re.compile(r"10\.5281/zenodo\.\d+|zenodo\.org[/\w.\-]*", re.I), False),
    ("grant numbers", re.compile(r"\b101225575\b|grant agreement", re.I), False),
    ("ECHO", re.compile(r"\bECHO\b"), False),
]
THIRD_PARTY = {"reproduction/r6/refs_crossref_raw.json": "third-party bibliographic metadata (Crossref/DataCite records of the cited works)"}
EXCLUDE = {"reproduction/r6/scripts/anonymity_grep.py", "reproduction/r6/ANONYMITY_REPORT.md", "reproduction/r6/anonymity_hits.json"}


def git(repo: Path, *args, binary: bool = False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8", errors="replace")


def png_text(data: bytes) -> list[str]:
    out = []
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return out
    i = 8
    while i + 8 <= len(data):
        n, typ = struct.unpack(">I4s", data[i:i + 8]); body = data[i + 8:i + 8 + n]; i += 12 + n
        try:
            if typ == b"tEXt":
                k, v = body.split(b"\x00", 1); out.append(f"{k.decode('latin-1')}: {v.decode('latin-1')}")
            elif typ == b"zTXt":
                k, rest = body.split(b"\x00", 1); out.append(f"{k.decode('latin-1')}: {zlib.decompress(rest[1:]).decode('latin-1')}")
            elif typ == b"iTXt":
                k, rest = body.split(b"\x00", 1); flag = rest[0]; rest = rest[2:]
                _lang, rest = rest.split(b"\x00", 1); _tk, txt = rest.split(b"\x00", 1)
                out.append(f"{k.decode('latin-1')}: {(zlib.decompress(txt) if flag else txt).decode('utf-8', errors='replace')}")
        except Exception:     # malformed chunk: skip
            pass
        if typ == b"IEND":
            break
    return out


TIFF_TAGS = {269: "DocumentName", 270: "ImageDescription", 305: "Software", 315: "Artist", 316: "HostComputer", 33432: "Copyright"}


def tiff_text(data: bytes) -> list[str]:
    """Text-valued TIFF tags that could carry a name (read with Pillow; empty when Pillow cannot open the file)."""
    import io
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            tags = getattr(im, "tag_v2", {}) or {}
            return [f"{TIFF_TAGS[k]}: {tags[k]}" for k in TIFF_TAGS if k in tags]
    except Exception:
        return []


def scan_text(path: str, text: str, where: str, hits: list):
    for ln_no, line in enumerate(text.splitlines(), 1):
        low = None
        for cls, rx, stripped in CLASSES:
            hay = line
            if stripped:
                low = low if low is not None else strip_accents(line).lower()
                hay = low
            for m in rx.finditer(hay):
                if stripped:      # positions refer to the accent-stripped text: show the line head
                    ctx_s = line[:160]
                else:
                    ctx_s = line[max(0, m.start() - 40): min(len(line), m.end() + 40)]
                ctx_s = ctx_s.replace("|", "/").strip()
                hits.append({"class": cls, "file": path, "line": ln_no, "match": m.group(0)[:80], "context": ctx_s[:160], "where": where})


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--tag", default="v1.4.2")
    ap.add_argument("--records", default="reproduction/r6,reproduction/v14_rerun/code16,reproduction/v14_rerun/scripts,reproduction/v14_rerun/NUMBER_MAP.md,docs/AUDIT.md,reproduction/emsr933")
    a = ap.parse_args()
    repo = a.repo.resolve()
    tag_commit = git(repo, "rev-parse", "--short", f"{a.tag}^{{commit}}").strip()
    files_tag = [f for f in git(repo, "ls-tree", "-r", "--name-only", a.tag).splitlines() if f and f not in EXCLUDE]
    changed = set(git(repo, "diff", "--name-only", a.tag).splitlines()) | set(git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
    roots = [r.strip().rstrip("/") for r in a.records.split(",") if r.strip()]
    files_rec = sorted(f for f in changed if f and f not in EXCLUDE and any(f == r or f.startswith(r + "/") for r in roots) and (repo / f).is_file())
    hits, not_scanned, scanned_tiff = [], [], []
    for f in files_tag:
        data = git(repo, "show", f"{a.tag}:{f}", binary=True)
        where = f"tag {a.tag}"
        if f.lower().endswith(".png"):
            for k, t in enumerate(png_text(data), 1):
                scan_text(f, t, where + " (PNG metadata)", hits)
            continue
        if f.lower().endswith((".tif", ".tiff")):
            for t in tiff_text(data):
                scan_text(f, t, where + " (TIFF tags)", hits)
            scanned_tiff.append(f); continue
        if b"\x00" in data[:8192]:
            not_scanned.append((f, where)); continue
        scan_text(f, data.decode("utf-8", errors="replace"), where, hits)
    for f in files_rec:
        data = (repo / f).read_bytes()
        where = "record after the tag" + (" (modified)" if f in files_tag else " (new)")
        if f.lower().endswith(".png"):
            for t in png_text(data):
                scan_text(f, t, where + " (PNG metadata)", hits)
            continue
        if f.lower().endswith((".tif", ".tiff")):
            for t in tiff_text(data):
                scan_text(f, t, where + " (TIFF tags)", hits)
            scanned_tiff.append(f); continue
        if b"\x00" in data[:8192]:
            not_scanned.append((f, where)); continue
        scan_text(f, data.decode("utf-8", errors="replace"), where, hits)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_dir = repo / "reproduction" / "r6"
    (out_dir / "anonymity_hits.json").write_text(json.dumps({"utc": now, "tag": a.tag, "tag_commit": tag_commit, "n_files_tag": len(files_tag), "n_files_records": len(files_rec),
                                                            "hits": hits, "not_scanned": not_scanned}, indent=1, ensure_ascii=False), encoding="utf-8")
    by_cls = {}
    for h in hits:
        by_cls.setdefault(h["class"], []).append(h)
    L = [f"# ANONYMITY_REPORT — dry run (report only; nothing changed)", "",
         f"Generated {now} by `reproduction/r6/scripts/anonymity_grep.py`. Scanned: the tracked tree at tag `{a.tag}` (`{tag_commit}`, {len(files_tag)} files, contents read from git) and "
         f"{len(files_rec)} record files changed or added after the tag under {', '.join(f'`{r}`' for r in roots)} (working tree). PNG files are scanned through their metadata text chunks and {len(scanned_tiff)} TIFF files through their text tags "
         f"(DocumentName, ImageDescription, Software, Artist, HostComputer, Copyright); {len(not_scanned)} other binary files are not scanned (listed at the end). This script, this report and `anonymity_hits.json` contain the patterns by construction and are excluded.", "",
         "## Summary by class", "", "| class | hits | files | in the tag tree | in records after the tag |", "|---|---|---|---|---|"]
    for cls, _rx, _s in CLASSES:
        hs = by_cls.get(cls, [])
        L.append(f"| {cls} | {len(hs)} | {len({h['file'] for h in hs})} | {sum(1 for h in hs if h['where'].startswith('tag'))} | {sum(1 for h in hs if not h['where'].startswith('tag'))} |")
    for cls, _rx, _s in CLASSES:
        hs = by_cls.get(cls, [])
        L += ["", f"## {cls} ({len(hs)} hits)", ""]
        if not hs:
            L.append("none"); continue
        by_file = {}
        for h in hs:
            by_file.setdefault((h["file"], h["where"]), []).append(h)
        L += ["| file | where | lines | matches (distinct) |", "|---|---|---|---|"]
        for (f, w), fh in sorted(by_file.items()):
            w = w + (f"; {THIRD_PARTY[f]}" if f in THIRD_PARTY else "")
            lines = sorted({h["line"] for h in fh})
            lines_s = ", ".join(str(x) for x in lines[:40]) + (f", … ({len(lines)} lines)" if len(lines) > 40 else "")
            L.append(f"| `{f}` | {w} | {lines_s} | {'; '.join(sorted({h['match'] for h in fh}))[:200]} |")
    L += ["", "## Not scanned (binary)", ""] + ([f"- `{f}` ({w})" for f, w in not_scanned] or ["none"])
    (out_dir / "ANONYMITY_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(hits)} hits in {len({h['file'] for h in hits})} files; by class: " + ", ".join(f"{c} {len(by_cls.get(c, []))}" for c, _r, _s in CLASSES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
