"""CODE-17 C — anonymised review archive (local only: nothing is uploaded and the repository tree is not changed).

C1  <out-dir>/<name>/ = `git archive <tag>` (default v1.4.2 = 0084600; no .git, no commit metadata) + overlays copied from the
    working tree (current versions): skill/examples/*.yaml, reproduction/v14_rerun/configs/*.yaml, reproduction/emsr933/rule_ledger.md,
    every repository file listed as a source in reproduction/r6/TABLES_MANIFEST.md, the table and figure scripts
    (reproduction/r6/scripts, reproduction/v14_rerun/scripts), the tables and figures (reproduction/r6/tables, figures; not
    figures/archive, not _cache), both manifests, refs.bib / refs_datacite.bib, README.md, CHANGELOG.md, docs/AUDIT.md,
    reproduction/v14_rerun/code16 + code17 records, tests/, and README_REVIEW.md at the top level.
C2  Scrub (text files only; the cited-work metadata files are left untouched): author names, handles and initials -> [author];
    CERTH / ITI -> [institution]; our e-mails -> [e-mail withheld]; the authors' ORCID -> [ORCID withheld]; as-run machine paths
    (C:/Users/vaspapa/Desktop/ELKAK/..., D:/ELKAK/...) -> relative paths; github.com/vaspapa79 -> [repository withheld for review];
    our Zenodo DOIs / records -> [DOI withheld for review]; grant number -> [grant withheld]; ECHO -> [funder withheld].
    LICENSE holder -> "Anonymous authors (review copy)".
C3  Excluded: NOA/meteo.gr station files, credentials (.cdsapirc, .netrc, .env, machine.local.yaml), caches, CITATION.cff,
    CLAUDE.md, the anonymity tooling and its reports, this builder, the cited-work raw metadata, the archived earlier-release figures.
C5  <name>.zip (one top-level folder <name>/) + SHA-256; the build record <name>_build.json is written beside the zip.

Usage: python -I build_review_archive.py --repo <worktree> [--tag v1.4.2] [--name review_archive_v1.4.2]
       [--out-dir reproduction/r6/review_archive] [--readme reproduction/r6/README_REVIEW.md] [--no-zip]
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

FAMILY = ["Papaioannou", "Valsamis", "Anagnostopoulos", "Moumtzidou", "Gialampoukidis", "Vrochidis", "Kompatsiaris"]
GIVEN = ["Dimitris", "Dimitrios", "Vassilios", "Vasileios", "Christos", "Anastasia", "Ilias", "Stefanos", "Ioannis"]
OUR_ZENODO = ["20523154", "20523155", "20829572", "21487689", "21488879"]      # the concept record and its versions
OUR_ORCID = ["0000-0001-6598-7107"]
FAM, ZID = "|".join(FAMILY), "|".join(OUR_ZENODO)
PATH_TAIL = r"((?:[\w.\-]+[\\/])*[\w.\-]*)"                                       # the remainder of a path after a stripped prefix


def _rel(m):
    return m.group(1).replace("\\", "/")


RULES = [  # (name, regex, replacement) — applied in this order to every scrubbed text file
    ("repository URL", re.compile(r"(?:https?://)?(?:www\.)?github\.com[/:](?:vaspapa79|dmvalsamis)(?:/[\w.\-]+)*/?(?:[#?][\w=&%.\-]*)?", re.I),
     "[repository withheld for review]"),
    ("Zenodo DOI (ours)", re.compile(r"(?:https?://)?(?:dx\.)?(?:doi\.org/)?10\.5281/zenodo\.(?:" + ZID + r")\b", re.I), "[DOI withheld for review]"),
    ("Zenodo record (ours)", re.compile(r"(?:https?://)?zenodo\.org/(?:records?|doi|badge/DOI|api/records)/(?:" + ZID + r")\b[\w/.\-]*", re.I),
     "[DOI withheld for review]"),
    ("e-mail (ours)", re.compile(r"\b[\w.+-]*(?:valsamis|vaspapa|papaioannou)[\w.+-]*@[\w-]+(?:\.[\w-]+)+\b|\b[\w.+-]+@(?:iti|certh)\.gr\b", re.I),
     "[e-mail withheld]"),
    ("ORCID (ours)", re.compile(r"(?:https?://)?(?:orcid\.org/)?(?:" + "|".join(OUR_ORCID) + r")"), "[ORCID withheld]"),
    ("as-run root path (author machine)", re.compile(r"C:[\\/]Users[\\/]vaspapa[\\/]Desktop[\\/]ELKAK[\\/]" + PATH_TAIL), _rel),
    ("as-run root (author machine, bare)", re.compile(r"C:[\\/]Users[\\/]vaspapa[\\/]Desktop[\\/]ELKAK\b"), "<as-run root>"),
    ("as-run root path (this machine)", re.compile(r"D:[\\/]ELKAK[\\/]" + PATH_TAIL), _rel),
    ("as-run root (this machine, bare)", re.compile(r"D:[\\/]ELKAK\b"), "<as-run root>"),
    ("conda path", re.compile(r"C:[\\/]Users[\\/][\w.\-]+[\\/]AppData[\\/]Local[\\/]anaconda3"), "<conda>"),
    ("home path", re.compile(r"C:[\\/]Users[\\/](?:dvalsamis|vaspapa)[\\/]"), "~/"),
    ("full name", re.compile(r"\b(?:" + "|".join(GIVEN) + r")(?:\s+[A-Z]\.)*\s+(?:" + FAM + r")\b"), "[author]"),
    ("initial + family name", re.compile(r"\b(?:[A-Z]\.\s?)+(?:" + FAM + r")\b"), "[author]"),
    ("family name", re.compile(r"\b(?:" + FAM + r")\w*", re.I), "[author]"),
    ("account handle", re.compile(r"\b(?:d?m?valsamis\w*|vaspapa\w*)", re.I), "[author]"),
    ("initials", re.compile(r"\b(?:DvS|VP)\b"), "[author]"),
    ("affiliation (full)", re.compile(r"Information Technologies Institute(?:\s*\(ITI\))?,?\s*Centre for Research (?:and|&) Technology"
                                      r"(?: Hellas)?(?:\s*\(CERTH\))?(?:,\s*Thessaloniki,\s*Greece)?", re.I), "[institution]"),
    ("affiliation CERTH-ITI", re.compile(r"\bCERTH[-‐–/ ]?ITI\b"), "[institution]"),
    ("affiliation CERTH", re.compile(r"\bCERTH\b|Centre for Research (?:and|&) Technology(?: Hellas)?", re.I), "[institution]"),
    ("affiliation ITI", re.compile(r"\bITI\b|Information Technologies Institute"), "[institution]"),
    ("grant number", re.compile(r"\b101225575\b"), "[grant withheld]"),
    ("funder", re.compile(r"\bECHO\b"), "[funder withheld]"),
]
LICENSE_LINE = re.compile(r"Copyright \(c\) (\d{4}) .*")
CITED_WORK = re.compile(r"(^|/)(refs(_datacite)?\.bib|refs_crossref_raw\.json|REFERENCES_REPORT\.md)$")

OVERLAYS = ["skill/examples/*.yaml", "reproduction/v14_rerun/configs/*.yaml", "reproduction/emsr933/rule_ledger.md",
            "reproduction/r6/scripts/*.py", "reproduction/v14_rerun/scripts/*.py", "reproduction/r6/tables/*",
            "reproduction/r6/figures/*.tiff", "reproduction/r6/figures/*.png", "reproduction/r6/figures/meta/*.json",
            "reproduction/r6/figures/data/*", "reproduction/r6/TABLES_MANIFEST.md", "reproduction/r6/FIGURES_MANIFEST.md",
            "reproduction/r6/refs.bib", "reproduction/r6/refs_datacite.bib", "README.md", "CHANGELOG.md", "docs/AUDIT.md",
            "reproduction/v14_rerun/code16/**/*", "reproduction/v14_rerun/code17/**/*", "tests/*.py"]
EXCLUDES = ["CITATION.cff", "CLAUDE.md", ".cdsapirc", "*.netrc", ".env", "**/.env", "skill/machine.local.yaml",
            "reproduction/emsr933/noa_stations/*.csv", "reproduction/emsr933/noa_stations/.gitignore",
            "reproduction/v14_rerun/phase5/crete_rain_vs_noa.*", "reproduction/v14_rerun/phase5/logs/rain_vs_noa.log",
            "reproduction/r6/tables/S8_noa_stations.csv", "**/_cache/**", "**/__pycache__/**", "**/*.pyc",
            "reproduction/r6/scripts/anonymity_grep.py", "reproduction/r6/scripts/build_review_archive.py", "reproduction/r6/ANONYMITY_REPORT*.md",
            "reproduction/r6/ANONYMITY_REPORT*.json", "reproduction/r6/anonymity_hits.json", "reproduction/r6/refs_crossref_raw.json",
            "reproduction/r6/REFERENCES_REPORT.md", "reproduction/r6/figures/archive/**", "reproduction/r6/review_archive/**",
            "tests/test_code17_release.py"]


def scrub_text(text: str):
    """Apply RULES in order; returns (scrubbed text, {rule name: substitutions})."""
    counts = {}
    for name, rx, repl in RULES:
        text, k = rx.subn(repl, text)
        if k:
            counts[name] = counts.get(name, 0) + k
    return text, counts


def excluded(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch("/" + rel, "/" + pat) for pat in EXCLUDES)


def manifest_sources(repo: Path) -> list[str]:
    """Repository-relative files named in backticks in TABLES_MANIFEST.md (absolute run outputs and <--r5-dir> entries are skipped)."""
    txt = (repo / "reproduction/r6/TABLES_MANIFEST.md").read_text(encoding="utf-8")
    out = []
    for tok in re.findall(r"`([^`]+)`", txt):
        tok = tok.strip()
        if re.match(r"^[A-Za-z]:[\\/]|^<", tok):
            continue
        if (repo / tok).is_file():
            out.append(tok)
    return sorted(set(out))


def git_archive(repo: Path, tag: str, dest: Path) -> int:
    tar = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", tag], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
        members = tf.getmembers()
        tf.extractall(dest, filter="data")
    return sum(1 for m in members if m.isfile())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--tag", default="v1.4.2")
    ap.add_argument("--name", default="review_archive_v1.4.2")
    ap.add_argument("--out-dir", default="reproduction/r6/review_archive")
    ap.add_argument("--readme", default="reproduction/r6/README_REVIEW.md")
    ap.add_argument("--no-zip", action="store_true")
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = (repo / a.out_dir) if not Path(a.out_dir).is_absolute() else Path(a.out_dir)
    root = out_dir / a.name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tag": a.tag,
           "tag_commit": subprocess.run(["git", "-C", str(repo), "rev-parse", f"{a.tag}^{{commit}}"], capture_output=True, text=True, check=True).stdout.strip(),
           "head": subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()}
    rec["files_from_tag"] = git_archive(repo, a.tag, root)
    # overlays from the working tree
    over = set()
    for pat in OVERLAYS + manifest_sources(repo):
        for p in repo.glob(pat):
            if p.is_file():
                over.add(p.relative_to(repo).as_posix())
    for rel in sorted(over):
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / rel, dst)
    rec["overlay_files"] = len(over)
    # exclusions
    removed = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if excluded(rel):
                p.unlink()
                removed.append(rel)
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda q: -len(q.parts)):
        if not any(d.iterdir()):
            d.rmdir()
    rec["excluded_files"] = removed
    # the pattern tests of the excluded scanner
    t = root / "tests/test_r6_helpers.py"
    if t.exists():
        s = t.read_text(encoding="utf-8")
        s2 = s.replace("import anonymity_grep as AG  # noqa: E402\n", "")
        i, j = s2.find("def _pattern(cls):"), s2.find('if __name__ == "__main__":')
        if s2 != s and 0 < i < j:
            s2 = s2[:i] + s2[j:]
            s2 = s2.replace(" and of the anonymity dry run\n(reproduction/r6/scripts/anonymity_grep.py)", "")
            t.write_text(s2, encoding="utf-8", newline="\n")
            rec["patched_tests"] = ["tests/test_r6_helpers.py: scanner import and pattern tests removed"]
    # scrub
    totals, changed, text_files, binary_files, untouched = {}, [], 0, 0, []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        data = p.read_bytes()
        if b"\x00" in data[:8192]:
            binary_files += 1
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            binary_files += 1
            continue
        text_files += 1
        if CITED_WORK.search(rel):
            untouched.append(rel)
            continue
        new, counts = scrub_text(text)
        if rel == "LICENSE":
            new, k = LICENSE_LINE.subn(lambda m: f"Copyright (c) {m.group(1)} Anonymous authors (review copy)", new, count=1)
            counts["LICENSE holder"] = k
        for k_, v in counts.items():
            totals[k_] = totals.get(k_, 0) + v
        if new != text:
            p.write_bytes(new.encode("utf-8"))
            changed.append(rel)
    rec.update(text_files=text_files, binary_files=binary_files, files_changed=len(changed), substitutions=totals, cited_work_untouched=untouched)
    readme = repo / a.readme
    shutil.copy2(readme, root / "README_REVIEW.md")
    rec["readme"] = str(readme.relative_to(repo)).replace("\\", "/")
    rec["top_level"] = sorted(q.name + ("/" if q.is_dir() else "") for q in root.iterdir())
    rec["n_files"] = sum(1 for p in root.rglob("*") if p.is_file())
    if not a.no_zip:
        zpath = out_dir.parent / f"{a.name}.zip"
        if zpath.exists():
            zpath.unlink()
        with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(out_dir).as_posix())
        h = hashlib.sha256()
        with open(zpath, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        rec["zip"] = {"path": str(zpath.relative_to(repo)).replace("\\", "/"), "bytes": zpath.stat().st_size, "sha256": h.hexdigest()}
    (out_dir.parent / f"{a.name}_build.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: rec[k] for k in rec if k not in ("excluded_files", "cited_work_untouched")}, indent=1, ensure_ascii=False))
    print("excluded:", len(removed), "files; cited-work files left untouched:", untouched)
    return 0


if __name__ == "__main__":
    sys.exit(main())
