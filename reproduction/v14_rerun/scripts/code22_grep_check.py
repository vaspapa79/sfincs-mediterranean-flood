"""CODE-22 step 2 — where pre-rewrite hashes are still quoted, after the published texts were mapped.

(1) The six pre-rewrite fix commits (the distinct values of the "pre-rewrite fix commit" column of table S10): every tracked or
    new, not ignored file of the working tree that still quotes one, by category. Only "other" must be empty; the brief allows the
    commit map and the audit trail, the S10 CSV keeps the column by design, the rewrite record is the source of the map, and the
    dated records (run records' git_head, checkpoints, run manifest, rule ledger, timing log, code14 plan) are left as written —
    like the earlier audit entries — and resolve through the map.
(2) The published texts and the code files that were mapped: the number of pre-rewrite hashes (any of the 34) at HEAD and now.
No hash is written into the record (it would count as a hit itself); fix commits are named by their defect labels.

Usage: python -I code22_grep_check.py --repo <worktree> [--out reproduction/v14_rerun/code22/grep_check.json]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "r6" / "scripts"))
import commit_map as CM  # noqa: E402

RULES = [  # (glob, category), first match wins
    ("docs/COMMIT_MAP_*.md", "commit map"),
    ("docs/AUDIT.md", "audit trail (entries before the rewrite)"),
    ("reproduction/r6/tables/S10.csv", "S10.csv pre-rewrite column (by design)"),
    ("reproduction/v14_rerun/code21/history_rewrite.json", "rewrite record (source of the map)"),
    ("reproduction/v14_rerun/results/*_record.json", "dated record"),
    ("reproduction/v14_rerun/CHECKPOINT*.md", "dated record"),
    ("reproduction/v14_rerun/MANIFEST.md", "dated record"),
    ("reproduction/v14_rerun/code1[0-9]/*", "dated record"),
    ("reproduction/emsr933/rule_ledger.md", "dated record"),
    ("reproduction/emsr933/timing.md", "dated record"),
]
PUBLISHED = ["CHANGELOG.md", "README.md", "reproduction/r6/README_REVIEW.md", "reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md",
             "reproduction/r6/tables/S10.md", "reproduction/r6/tables/S10.csv", "CITATION.cff", ".zenodo.json",
             "reproduction/r6/scripts/release_docs.py", "tests/test_code17_helpers.py"]


def category(path: str) -> str:
    for pat, cat in RULES:
        if fnmatch.fnmatch(path, pat):
            return cat
    return "other"


def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode not in (0, 1):          # git grep returns 1 when nothing matches
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def fix_commits(repo: Path) -> list[tuple[str, str]]:
    """(defect labels, pre-rewrite fix commit) from S10.csv, one entry per distinct commit."""
    with open(repo / "reproduction/r6/tables/S10.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    by = {}
    for r in rows:
        h = r["pre-rewrite fix commit"]
        if h not in ("", "—"):
            by.setdefault(h, []).append(r["defect"])
    return [("/".join(v), h) for h, v in by.items()]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path("reproduction/v14_rerun/code22/grep_check.json"))
    a = ap.parse_args()
    repo = a.repo.resolve()
    fc = fix_commits(repo)
    # substring match, as a plain grep: a 7-character hash also counts where a record quotes the full 40-character hash
    args = ["grep", "-c", "-F", "--untracked"] + [x for _, h in fc for x in ("-e", h)]
    per_file = {}
    for ln in git(repo, *args).splitlines():
        f, n = ln.rsplit(":", 1)
        per_file[f] = int(n)
    by_cat: dict[str, dict] = {}
    for f, n in sorted(per_file.items()):
        c = category(f)
        by_cat.setdefault(c, {"files": 0, "hits": 0, "paths": []})
        by_cat[c]["files"] += 1; by_cat[c]["hits"] += n; by_cat[c]["paths"].append(f"{f} ({n})")
    labels_per_file = {}
    for lab, h in fc:
        for ln in git(repo, "grep", "-l", "-F", "--untracked", "-e", h).splitlines():
            labels_per_file.setdefault(ln, []).append(lab)
    cmap = CM.load_map(repo)
    pub = []
    for f in PUBLISHED:
        head = git(repo, "show", f"HEAD:{f}", check=False)
        now = (repo / f).read_text(encoding="utf-8") if (repo / f).exists() else ""
        pub.append({"file": f, "pre_rewrite_hashes_at_HEAD": len(CM.map_text(head, cmap)[1]) if head else None,
                    "pre_rewrite_hashes_now": len(CM.map_text(now, cmap)[1]) if now else None})
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code22_grep_check.py",
           "head": git(repo, "rev-parse", "--short", "HEAD").strip(),
           "searched": "the six pre-rewrite fix commits of table S10 (" + ", ".join(lab for lab, _ in fc) + "), 7-character substring (full quotes count), in every tracked and every new, "
                       "not ignored file of the working tree",
           "n_fix_commits": len(fc), "files_with_hits": len(per_file), "hits": sum(per_file.values()),
           "by_category": by_cat, "other_hits": by_cat.get("other", {}).get("hits", 0),
           "defects_per_file": {f: sorted(v) for f, v in sorted(labels_per_file.items())},
           "published_texts": pub}
    out = repo / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for c, v in by_cat.items():
        print(f"{c}: {v['files']} files, {v['hits']} hits")
    for p in pub:
        print(f"  {p['file']}: {p['pre_rewrite_hashes_at_HEAD']} at HEAD -> {p['pre_rewrite_hashes_now']} now")
    print("other hits:", rec["other_hits"]); print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
