"""CODE-21 item 4 — record and verification of the history rewrite that removed the NOA/meteo.gr station data files.

The rewrite itself was run with git-filter-repo in a mirror clone (``--invert-paths`` over the eight data paths, ``--refs`` limited
to the commits after the published v1.3.0 = ccd423a, ``--preserve-commit-hashes`` so that every commit message stays verbatim)
and applied to this repository with ``git update-ref``; the previous refs are kept under refs/backup/code21/ and in a bundle.
This script reads filter-repo's commit-map / ref-map and re-verifies, in this repository, the five checks:
  (a) no removed path is reachable from any ref that GO-PUSH publishes (main, v1.4.0, v1.4.1, v1.4.2, emsr933-v1);
  (b) every rewritten commit differs from its original only by the removed paths, and its author / committer / dates / message
      are byte-identical;
  (c) the tags are annotated, their tagger / date / message unchanged, and each points at the rewrite of its original target;
  (d) the published history is untouched: every commit up to and including v1.3.0 (ccd423a) keeps its hash, origin/main is
      still an ancestor of main (fast-forward push), and the remote refs are unchanged;
  (e) the trees of main / fix/harness-v1.4 at HEAD are identical to the trees before the rewrite (the data files were already
      untracked there), and the backups exist (refs/backup/code21/*, the bundle, verified).
Writes reproduction/v14_rerun/code21/history_rewrite.json.

Usage: python -I code21_history_rewrite_record.py --repo <worktree> --maps <dir with commit-map_mirror3.txt, ref-map_mirror3.txt>
       --bundle <backup bundle> [--filter-repo-version <hash>]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REMOVED = ["reproduction/emsr933/noa_stations/published_totals.csv", "reproduction/emsr933/noa_stations/stations_daily.csv",
           "reproduction/emsr933/noa_stations/stations_meta.csv", "reproduction/r6/tables/S8_noa_stations.csv",
           "reproduction/v14_rerun/phase5/crete_rain_vs_noa.csv", "reproduction/v14_rerun/phase5/crete_rain_vs_noa.json",
           "reproduction/v14_rerun/phase5/crete_rain_vs_noa.png", "reproduction/v14_rerun/phase5/logs/rain_vs_noa.log"]
PUSH_REFS = ["main", "v1.4.0", "v1.4.1", "v1.4.2", "emsr933-v1"]
PUBLISHED_BASE = "ccd423a8c197601ad943965ee415f50b9ec53be8"       # v1.3.0 = origin/main
FMT = "%an|%ae|%ad|%cn|%ce|%cd|%B"


def git(repo: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--maps", required=True, type=Path)
    ap.add_argument("--bundle", required=True, type=Path)
    ap.add_argument("--filter-repo-version", default="")
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = repo / "reproduction" / "v14_rerun" / "code21"
    out_dir.mkdir(parents=True, exist_ok=True)
    cm = [ln.split() for ln in (a.maps / "commit-map_mirror3.txt").read_text(encoding="utf-8").splitlines()[1:]]
    rm = [ln.split() for ln in (a.maps / "ref-map_mirror3.txt").read_text(encoding="utf-8").splitlines()[1:]]
    changed = [(o, n) for o, n in cm if o != n]
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code21_history_rewrite_record.py",
           "tool": {"name": "git-filter-repo", "version": a.filter_repo_version, "git": git(repo, "--version").strip()},
           "command": "git filter-repo --force --preserve-commit-hashes --invert-paths " + " ".join(f"--path {p}" for p in REMOVED)
                      + " --refs ccd423a..refs/heads/main ccd423a..refs/heads/fix/harness-v1.4 ccd423a..refs/heads/emsr933-crete ccd423a..refs/tags/v1.4.0 "
                        "ccd423a..refs/tags/v1.4.1 ccd423a..refs/tags/v1.4.2 ccd423a..refs/tags/emsr933-v1   (in a mirror clone; refs applied with git update-ref)",
           "removed_paths": REMOVED, "kept_noa_related_paths": ["reproduction/emsr933/noa_stations/.gitignore", "reproduction/emsr933/noa_stations/sources.md",
                                                                "reproduction/v14_rerun/scripts/crete_rain_vs_noa.py", "tests/test_crete_rain_vs_noa.py"],
           "commits_mapped": len(cm), "commits_rewritten": len(changed), "commits_unchanged_in_range": len(cm) - len(changed),
           "ref_map": [{"ref": r, "old": o, "new": n} for o, n, r in rm], "commit_map": [{"old": o, "new": n} for o, n in cm]}
    checks = {}
    # (a) no removed path reachable from the pushed refs
    names = set(x for x in git(repo, "log", *PUSH_REFS, "--format=", "--name-only").split("\n") if x)
    checks["a_no_removed_path_in_pushed_history"] = {"pass": not (names & set(REMOVED)), "offending": sorted(names & set(REMOVED)),
                                                      "noa_related_paths_still_in_history": sorted(x for x in names if "noa" in x.lower())}
    # (b) tree diff only the removed paths; metadata identical
    bad_tree, bad_meta = [], []
    for o, n in changed:
        d = set(x for x in git(repo, "diff-tree", "-r", "--name-only", "--no-commit-id", o, n).split("\n") if x)
        if not d <= set(REMOVED):
            bad_tree.append({"old": o[:7], "new": n[:7], "extra": sorted(d - set(REMOVED))})
        if git(repo, "log", "-1", f"--format={FMT}", o) != git(repo, "log", "-1", f"--format={FMT}", n):
            bad_meta.append({"old": o[:7], "new": n[:7]})
    checks["b_rewritten_commits_differ_only_by_removed_paths_metadata_identical"] = {"pass": not bad_tree and not bad_meta, "tree_mismatches": bad_tree, "metadata_mismatches": bad_meta,
                                                                                      "commits_checked": len(changed)}
    # (c) tags annotated, tagger/message unchanged, pointing at the rewrite of the original target
    tag_rows, tag_ok = [], True
    cmap = dict(cm)
    for o, n, r in rm:
        if not r.startswith("refs/tags/"):
            continue
        t = r.split("/", 2)[2]
        typ = git(repo, "cat-file", "-t", n).strip()
        old_tgt = git(repo, "rev-parse", f"{o}^{{commit}}").strip()
        new_tgt = git(repo, "rev-parse", f"{n}^{{commit}}").strip()
        fmt_t = "%(taggername)|%(taggeremail)|%(taggerdate:iso)|%(contents)"
        same_tagger = git(repo, "for-each-ref", f"--format={fmt_t}", f"refs/backup/code21/tags/{t}") == git(repo, "for-each-ref", f"--format={fmt_t}", r)
        ok = typ == "tag" and cmap.get(old_tgt) == new_tgt and same_tagger and git(repo, "rev-parse", r).strip() == n
        tag_ok &= ok
        tag_rows.append({"tag": t, "annotated": typ == "tag", "old_tag": o[:7], "new_tag": n[:7], "old_commit": old_tgt[:7], "new_commit": new_tgt[:7],
                         "target_is_rewrite_of_original": cmap.get(old_tgt) == new_tgt, "tagger_date_message_unchanged": same_tagger, "ref_points_at_new": ok})
    checks["c_tags_annotated_unchanged_text_repointed"] = {"pass": bool(tag_ok), "tags": tag_rows}
    # (d) published history untouched
    pre = git(repo, "rev-list", PUBLISHED_BASE).split()
    identical_pre = all(cmap.get(c, c) == c for c in pre)
    remote = git(repo, "ls-remote", "--tags", "--heads", "origin", check=False).strip().splitlines()
    plan = repo / "reproduction" / "v14_rerun" / "code17" / "d4_push_plan.json"
    remote_before = json.loads(plan.read_text(encoding="utf-8"))["remote_refs"] if plan.exists() else {}
    remote_now = {ln.split("\t")[1]: ln.split("\t")[0] for ln in remote if "\t" in ln}
    ff = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", "origin/main", "main"]).returncode == 0
    checks["d_published_history_untouched"] = {"pass": identical_pre and ff and git(repo, "rev-parse", "v1.3.0^{commit}").strip() == PUBLISHED_BASE
                                                        and all(remote_now.get(k) == v for k, v in remote_before.items() if k != "HEAD"),
                                                "commits_up_to_v1_3_0": len(pre), "all_keep_hash": identical_pre, "origin_main_is_ancestor_of_main": ff,
                                                "v1_3_0_commit": git(repo, "rev-parse", "v1.3.0^{commit}").strip(),
                                                "remote_refs_unchanged_since_code17_plan": all(remote_now.get(k) == v for k, v in remote_before.items() if k != "HEAD"),
                                                "ahead_of_origin_main": int(git(repo, "rev-list", "--count", "origin/main..main").strip())}
    # (e) trees at HEAD unchanged; backups exist
    trees = {}
    for b in ("main", "fix/harness-v1.4"):
        trees[b] = {"before": git(repo, "rev-parse", f"refs/backup/code21/heads/{b}^{{tree}}").strip(), "after": git(repo, "rev-parse", f"refs/heads/{b}^{{tree}}").strip()}
    bundle_ok = subprocess.run(["git", "-C", str(repo), "bundle", "verify", str(a.bundle)], capture_output=True).returncode == 0
    backups = git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/backup/code21").strip().splitlines()
    checks["e_head_trees_unchanged_and_backups"] = {"pass": all(v["before"] == v["after"] for v in trees.values()) and bundle_ok and len(backups) == 7,
                                                     "trees": trees, "backup_refs": backups,
                                                     "bundle": {"path": str(a.bundle), "bytes": a.bundle.stat().st_size, "sha256": hashlib.sha256(a.bundle.read_bytes()).hexdigest(), "verify_ok": bundle_ok}}
    rec["checks"] = checks
    rec["all_pass"] = all(v["pass"] for v in checks.values())
    rec["note"] = ("The CODE-18 brief text was not available in this session (not in the transcript, memory or workspace documents); checks (a)-(e) above are the "
                   "reconstruction used here. The branch emsr933-crete (not pushed) was rewritten too; archive/local-main-2026-06 and release/portability-fix do not reach "
                   "the first commit that tracked the files and are untouched. The backup refs are local only (never pushed) and can be deleted after GO-PUSH.")
    out = out_dir / "history_rewrite.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k, v in checks.items():
        print(f"{k}: {'PASS' if v['pass'] else 'FAIL'}")
    print("all_pass", rec["all_pass"]); print("wrote", out)
    return 0 if rec["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
