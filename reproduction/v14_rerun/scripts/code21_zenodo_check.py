"""CODE-21 item 5 — the creators of the existing Zenodo record against CITATION.cff (the source of the regenerated Zenodo
description), and the facts a GO-PUSH release needs: what the tag tree carries as citation metadata, the webhook history of the
earlier releases, and the exact push command of the push-plan record.

Reads the Zenodo / DataCite API responses saved under --api-dir (record_<id>.json, datacite_<id>.json, datacite_concept.json),
CITATION.cff at HEAD and at the release tag, and reproduction/v14_rerun/code21/push_plan.json. Writes
reproduction/v14_rerun/code21/zenodo_release_check.json. No request is sent by this script.

Usage: python -I code21_zenodo_check.py --repo <worktree> --api-dir <dir> [--tag v1.4.2]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

CONCEPT = "10.5281/zenodo.20523154"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def cff_creators(text: str) -> list:
    out = []
    for block in re.split(r"\n\s*-\s+family-names:", text.split("authors:", 1)[1].split("\nlicense:", 1)[0]):
        if "given-names" not in block:
            continue
        g = lambda k: (re.search(k + r":\s*\"?([^\"\n]+)\"?", block) or [None, None])[1]
        fam = block.strip().split("\n")[0].strip().strip('"') if not block.lstrip().startswith("family-names") else g("family-names")
        out.append({"name": f"{fam}, {g('given-names')}", "affiliation": g("affiliation"), "orcid": (g("orcid") or "").replace("https://orcid.org/", "") or None})
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--api-dir", required=True, type=Path)
    ap.add_argument("--tag", default="v1.4.2")
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = repo / "reproduction" / "v14_rerun" / "code21"
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code21_zenodo_check.py", "api_files": {}}
    zen = None
    for p in sorted(a.api_dir.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rec["api_files"][p.name] = {"note": "not JSON (an HTTP error page from a first attempt); ignored"}
            continue
        rec["api_files"][p.name] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "fetched_utc": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if "metadata" in d and d.get("conceptdoi") == CONCEPT and (zen is None or d["metadata"].get("version", "") > zen["metadata"].get("version", "")):
            zen = d
    if zen is None:
        raise SystemExit("no Zenodo record JSON under --api-dir")
    zm = zen["metadata"]
    zen_creators = [{"name": c["name"], "affiliation": c.get("affiliation"), "orcid": c.get("orcid")} for c in zm["creators"]]
    cff_head = (repo / "CITATION.cff").read_text(encoding="utf-8")
    cff_tag = git(repo, "show", f"{a.tag}:CITATION.cff")
    head_creators = cff_creators(cff_head)
    tag_creators = cff_creators(cff_tag)
    ver = lambda t: (re.search(r'^version:\s*"([^"]+)"', t, re.M) or [None, None])[1]
    rec["existing_record"] = {"doi": zen.get("doi"), "concept_doi": zen.get("conceptdoi"), "version": zm.get("version"), "publication_date": zm.get("publication_date"),
                              "title": zm.get("title"), "license": (zm.get("license") or {}).get("id") if isinstance(zm.get("license"), dict) else zm.get("license"),
                              "related": [(x.get("relation"), x.get("identifier")) for x in zm.get("related_identifiers", [])], "creators": zen_creators,
                              "versions_of_concept": sorted({x.get("relatedIdentifier") for p in a.api_dir.glob("datacite_concept.json")
                                                             for x in json.loads(p.read_text(encoding="utf-8"))["data"]["attributes"].get("relatedIdentifiers", []) if x.get("relationType") == "HasVersion"})}
    same = [c["name"] for c in zen_creators] == [c["name"] for c in head_creators] and all(
        (c["affiliation"] == h["affiliation"]) and ((c.get("orcid") or None) == (h.get("orcid") or None)) for c, h in zip(zen_creators, head_creators))
    rec["creators_check"] = {"citation_cff_head_matches_zenodo_record": same, "n_zenodo": len(zen_creators), "n_cff_head": len(head_creators), "cff_head": head_creators,
                             "cff_at_tag_same_names": [c["name"] for c in tag_creators] == [c["name"] for c in zen_creators]}
    rec["tag_tree_metadata"] = {"tag": a.tag, "tag_commit": git(repo, "rev-parse", f"{a.tag}^{{commit}}").strip(), "citation_cff_version_at_tag": ver(cff_tag),
                                "citation_cff_version_at_head": ver(cff_head), "zenodo_json_at_tag": bool(git(repo, "cat-file", "-e", f"{a.tag}:.zenodo.json") == "" and
                                                                                                          subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{a.tag}:.zenodo.json"]).returncode == 0),
                                "zenodo_json_at_head": (repo / ".zenodo.json").exists(),
                                "consequence": "Zenodo's GitHub integration builds the new version's metadata from the release's tree (.zenodo.json, else CITATION.cff); the tag tree "
                                               "carries CITATION.cff version 1.3.0, so the auto-created record would state version 1.3.0 until its metadata is edited "
                                               "(version, description from reproduction/r6/ZENODO_DESCRIPTION_v1.4.2.md); the creators are the same either way."}
    plan = out_dir / "push_plan.json"
    if plan.exists():
        p = json.loads(plan.read_text(encoding="utf-8"))
        rec["push"] = {"command": p["push_command"], "main": p["main"][:7], "ahead": p["ahead"], "fast_forward": p["fast_forward"], "refs": p["refs"],
                       "tracked_noa_files": p["tracked_noa_files"], "tracked_credential_files": p["tracked_credential_files"],
                       "history_noa_files": p.get("history_noa_files"), "history_credential_files": p.get("history_credential_files")}
    rec["go_push_sequence"] = [
        "git -C <main checkout> push --atomic origin main v1.4.0 v1.4.1 v1.4.2 emsr933-v1",
        f"gh release create {a.tag} --repo vaspapa79/sfincs-mediterranean-flood --title \"{a.tag}\" --notes-file <the CHANGELOG {a.tag} section>   (one release: the Zenodo webhook mints one version DOI per GitHub release)",
        "poll https://zenodo.org/api/records?q=conceptrecid:20523154&all_versions=true until the new version appears; report its DOI URL and the release URL",
        "then edit the new Zenodo version's metadata (version 1.4.2, description = ZENODO_DESCRIPTION_v1.4.2.md) — creators unchanged",
        "delete the local backup refs refs/backup/code21/* and refs/rewritten/* once the push is verified (git for-each-ref refs/backup/code21 | cut -f2 | xargs -n1 git update-ref -d)"]
    out = out_dir / "zenodo_release_check.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("creators match:", same, "| record", rec["existing_record"]["doi"], rec["existing_record"]["version"], "| tag CITATION version", rec["tag_tree_metadata"]["citation_cff_version_at_tag"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
