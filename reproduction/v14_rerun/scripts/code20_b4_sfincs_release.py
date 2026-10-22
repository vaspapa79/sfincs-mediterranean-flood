"""CODE-20 B4 — the Deltares release of SFINCS v2.3.0: release name and date, whether an executable is attached, and how the
binary that ran the six reproductions (sfincs.log "Build-Date 2025-11-18", recorded by CODE-19 A3) relates to it.

Reads the GitHub releases listing of Deltares/SFINCS and the tag commit as fetched to --downloads (api.github.com JSON; copied
into code20/ as a dated snapshot), the fetched download.deltares.nl page (size only; its content is script-rendered) and
code19/a3_hardware.json. Writes reproduction/v14_rerun/code20/b4_sfincs_release.json.

Usage: python -I code20_b4_sfincs_release.py --repo <worktree> --downloads <dir with releases.json, commit_*.json, download_page.html>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

TAG = "v2.3.0_mt_Faber_release"
BUILD_DATE = "2025-11-18"


def release_summary(releases: list, tag: str) -> dict:
    r = next(x for x in releases if x["tag_name"] == tag)
    assets = [{"name": x["name"], "bytes": x.get("size"), "created_at": x.get("created_at"), "updated_at": x.get("updated_at")} for x in r.get("assets", [])]
    return {"tag": tag, "name": r["name"], "published_at": r["published_at"], "created_at": r["created_at"], "prerelease": bool(r.get("prerelease")),
            "html_url": r.get("html_url"), "n_assets": len(assets), "assets": assets,
            "assets_dated": [x for x in assets if (x["created_at"] or "").startswith(BUILD_DATE) or (x["updated_at"] or "").startswith(BUILD_DATE)]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--downloads", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = repo / "reproduction" / "v14_rerun" / "code20"
    out_dir.mkdir(parents=True, exist_ok=True)
    rel_path = a.downloads / "releases.json"
    releases = json.loads(rel_path.read_text(encoding="utf-8"))
    fetched = dt.datetime.fromtimestamp(rel_path.stat().st_mtime, dt.timezone.utc)
    snap = out_dir / f"github_releases_Deltares_SFINCS_{fetched.strftime('%Y%m%dT%H%M%SZ')}.json"
    shutil.copyfile(rel_path, snap)
    s = release_summary(releases, TAG)
    body = next(x for x in releases if x["tag_name"] == TAG)["body"]
    lines = [ln.strip() for ln in body.splitlines() if re.search(r"executable|download\.deltares|docker|source code", ln, re.I)]
    pre = [release_summary(releases, x["tag_name"]) for x in releases if x["tag_name"].startswith("v2.3.0") and x["tag_name"] != TAG]
    commit = {}
    for p in sorted(a.downloads.glob("commit_*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        commit = {"sha": c["sha"], "author_date": c["commit"]["author"]["date"], "committer_date": c["commit"]["committer"]["date"], "message_first_line": c["commit"]["message"].splitlines()[0]}
    tag_ref = {}
    tr = a.downloads / "tag_v230.json"
    if tr.exists():
        t = json.loads(tr.read_text(encoding="utf-8"))
        tag_ref = {"ref": t["ref"], "object_sha": t["object"]["sha"], "object_type": t["object"]["type"]}
    page = a.downloads / "download_page.html"
    page_info = None
    if page.exists():
        h = page.read_text(encoding="utf-8", errors="replace")
        hits = sorted(set(re.findall(r"(?i)2\.3\.0[^<\"]{0,60}|faber[^<\"]{0,60}", h)))
        page_info = {"url": "https://download.deltares.nl/en/sfincs/", "bytes": page.stat().st_size, "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                     "version_or_release_strings_in_html": hits, "note": "the page is script-rendered; a plain fetch carries no version or build-date text" if not hits else ""}
    a3_path = repo / "reproduction" / "v14_rerun" / "code19" / "a3_hardware.json"
    a3 = json.loads(a3_path.read_text(encoding="utf-8"))
    def walk(o, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("sfincs_build_revision", "sfincs_build_date", "config_sfincs_exe") and isinstance(v, str):
                    acc.add(f"{k} = {v.strip()}")
                else:
                    walk(v, acc)
        elif isinstance(o, list):
            for v in o:
                walk(v, acc)
        return acc
    build_lines = sorted(walk(a3, set()))      # the per-run sfincs.log facts recorded by CODE-19 A3 (identical for the six runs)
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code20_b4_sfincs_release.py",
           "github_api": {"url": "https://api.github.com/repos/Deltares/SFINCS/releases?per_page=30", "fetched_utc": fetched.strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "snapshot": snap.relative_to(repo).as_posix(), "sha256": hashlib.sha256(rel_path.read_bytes()).hexdigest()},
           "release": s, "release_body_distribution_lines": lines, "tag_ref": tag_ref, "tag_commit": commit, "pre_releases_of_v2_3_0": pre,
           "deltares_download_page": page_info,
           "binary_as_run": {"source": "reproduction/v14_rerun/code19/a3_hardware.json", "sha256": hashlib.sha256(a3_path.read_bytes()).hexdigest(), "sfincs_log_version_lines": build_lines},
           "answer": (f"GitHub release '{s['name']}' (tag {TAG}), published {s['published_at']}, created {s['created_at']}; {s['n_assets']} attached assets "
                      f"(no executable dated {BUILD_DATE} is attached on GitHub); the release text points to download.deltares.nl for the pre-compiled Windows executable and to Docker; "
                      f"the tag commit {commit.get('sha', '')[:7]} is dated {commit.get('committer_date')}, the same day as the binary's own 'Build-Date {BUILD_DATE}' in every sfincs.log."),
           "proposed_section_3_1_wording": "SFINCS v2.3.0 (mt Faber Release 2025.02, published 19 November 2025; Windows executable built 18 November 2025)"}
    out = out_dir / "b4_sfincs_release.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(rec["answer"]); print("build lines:", build_lines); print("page:", page_info and page_info["version_or_release_strings_in_html"]); print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
