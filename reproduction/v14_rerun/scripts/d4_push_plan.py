"""CODE-17 D4 — what GO-PUSH would push, and the tracked-content checks (nothing is pushed; read-only on git).

Reports: main vs origin/main (ahead count, fast-forward test), the refs the push command would create or move, every tag
with its target, and two checks over the tree that would become public: (1) no NOA/meteo.gr station file and no credential
file is tracked at HEAD, and (2) whether any commit reachable from the pushed refs ever contained such files (history is pushed
with the branch). Credential patterns: .cdsapirc / .netrc / .env files, CDS key lines ("key: <uuid>"), netrc machine lines.

Usage: python -I d4_push_plan.py --repo <worktree> [--out-json reproduction/v14_rerun/code17/d4_push_plan.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

NOA_PATTERNS = [r"noa_stations/.*\.csv$", r"noa_stations/raw/", r"crete_rain_vs_noa\.", r"rain_vs_noa\.log$", r"S8_noa_stations\.csv$", r"stations_daily", r"published_totals", r"stations_meta"]
CRED_FILES = [r"(^|/)\.cdsapirc$", r"(^|/)\.?netrc$", r"(^|/)\.env$", r"(^|/)machine\.local\.yaml$", r"(^|/)\.cdsapirc\..*", r"credentials", r"\.pem$", r"\.key$"]
CRED_CONTENT = [(r"^\s*key\s*:\s*[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\s*$", "CDS API key line"),
                (r"^\s*machine\s+urs\.earthdata\.nasa\.gov\b.*(login|password)", "Earthdata netrc line"),
                (r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9+/_\-]{16,}", "key/secret assignment")]
PUSH_REFS = ["main", "v1.4.0", "v1.4.1", "v1.4.2", "emsr933-v1"]


def git(repo: Path, *args: str, check=True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.strip()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args()
    repo = a.repo.resolve()
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    main_sha, origin = git(repo, "rev-parse", "main"), git(repo, "rev-parse", "origin/main")
    out["main"], out["origin_main"] = main_sha, origin
    out["fast_forward"] = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", origin, main_sha]).returncode == 0
    out["ahead"], out["behind"] = [int(x) for x in git(repo, "rev-list", "--left-right", "--count", f"{main_sha}...{origin}").split()]
    remote = {}
    for ln in git(repo, "ls-remote", "origin").splitlines():
        sha, ref = ln.split("\t")
        remote[ref] = sha
    out["remote_refs"] = remote
    refs = []
    for r in PUSH_REFS:
        is_tag = r != "main"
        local = git(repo, "rev-parse", r)
        target = git(repo, "rev-parse", f"{r}^{{commit}}")
        rref = f"refs/tags/{r}" if is_tag else "refs/heads/main"
        refs.append({"ref": r, "kind": "annotated tag" if is_tag and local != target else ("tag" if is_tag else "branch"), "object": local[:7],
                     "commit": target[:7], "on_remote": remote.get(rref, None), "action": ("update" if rref in remote else "create")})
    out["push_command"] = "git push --atomic origin " + " ".join(PUSH_REFS)
    out["refs"] = refs
    # tracked at HEAD
    tracked = git(repo, "ls-files").splitlines()
    noa_rx, cred_rx = [re.compile(p) for p in NOA_PATTERNS], [re.compile(p) for p in CRED_FILES]
    out["tracked_noa_files"] = [f for f in tracked if any(r.search(f) for r in noa_rx)]
    out["tracked_credential_files"] = [f for f in tracked if any(r.search(f) for r in cred_rx)]
    hits = []
    for f in tracked:
        p = repo / f
        if not p.is_file() or p.stat().st_size > 5_000_000:
            continue
        data = p.read_bytes()
        if b"\x00" in data[:8192]:
            continue
        text = data.decode("utf-8", errors="replace")
        for rx, lab in CRED_CONTENT:
            for m in re.finditer(rx, text, re.M):
                hits.append({"file": f, "what": lab, "excerpt": m.group(0)[:60]})
    out["tracked_credential_content_hits"] = hits
    # history: files ever added under the pushed refs
    ever = git(repo, "log", "--all-match", "--name-only", "--format=", main_sha).splitlines()
    ever = sorted({f for f in ever if f})
    out["history_noa_files"] = [f for f in ever if any(r.search(f) for r in noa_rx)]
    out["history_credential_files"] = [f for f in ever if any(r.search(f) for r in cred_rx)]
    out["history_first_commit_with_noa"] = None
    if out["history_noa_files"]:
        first = git(repo, "log", "--reverse", "--format=%h %cI %s", main_sha, "--", *out["history_noa_files"]).splitlines()
        out["history_first_commit_with_noa"] = first[0] if first else None
        out["history_tags_containing_noa_files"] = [t for t in git(repo, "tag").splitlines()
                                                    if git(repo, "ls-tree", "-r", "--name-only", t, check=False) and any(any(r.search(f) for r in noa_rx) for f in git(repo, "ls-tree", "-r", "--name-only", t, check=False).splitlines())]
    if a.out_json:
        a.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "remote_refs"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
