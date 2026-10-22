"""CODE-20 B1 — order of the rule-freeze commit and the first Valencia metrics, every timestamp converted to UTC.

Reads (nothing retyped): docs/FREEZE_EVIDENCE.md (the published freeze record, local-time +03:00), the private manuscript
repository when present (git dates of bfd005a / 49da0d1 / 5447768, the generated_utc of runs/valencia_emsr773/metrics.json at
those commits, the mtimes of the first Valencia artefacts) and the CODE-19 anchor ledger (code19/lookups.json, D7) as the
repository's own record of the 13:13:03Z and 18:00:02Z metrics. Writes reproduction/v14_rerun/code20/b1_freeze_order.json.

Usage: python -I code20_b1_freeze_order.py --repo <worktree> [--nhess D:/ELKAK/ELKAK2/NHESS]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RULE_COMMIT, RESULTS_COMMIT, BIAS_COMMIT = "bfd005a", "49da0d1", "5447768"
VALENCIA_METRICS = "runs/valencia_emsr773/metrics.json"
SENTENCE = "The rule was committed on 15 July 2026, before either held-out configuration was written"


def to_utc(s: str) -> str:
    """'2026-07-15 14:33:54 +0300' | '... +03:00' | '2026-07-15T13:13:03Z' -> 'YYYY-MM-DDTHH:MM:SSZ'."""
    s = s.strip()
    if s.endswith("Z"):
        d = dt.datetime.fromisoformat(s[:-1]).replace(tzinfo=dt.timezone.utc)
    else:
        m = re.match(r"(\d{4}-\d\d-\d\d)[ T](\d\d:\d\d:\d\d)\s*([+-])(\d\d):?(\d\d)$", s)
        if m is None:
            raise ValueError(f"unrecognised timestamp {s!r}")
        sign = 1 if m.group(3) == "+" else -1
        tz = dt.timezone(sign * dt.timedelta(hours=int(m.group(4)), minutes=int(m.group(5))))
        d = dt.datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}").replace(tzinfo=tz)
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _p(u: str) -> dt.datetime:
    return dt.datetime.fromisoformat(u[:-1]).replace(tzinfo=dt.timezone.utc)


def order(commit_utc: str, metrics_utc: str) -> dict:
    lead = int(round((_p(metrics_utc) - _p(commit_utc)).total_seconds()))
    h, rem = divmod(abs(lead), 3600)
    m, s = divmod(rem, 60)
    return {"commit_utc": commit_utc, "metrics_utc": metrics_utc, "first": "commit" if lead > 0 else ("metrics" if lead < 0 else "same second"),
            "lead_s": abs(lead), "lead_hms": f"{h} h {m:02d} min {s:02d} s"}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, encoding="utf-8", errors="replace").stdout.strip()


def mtime_utc(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--nhess", type=Path, default=Path("D:/ELKAK/ELKAK2/NHESS"), help="private manuscript repository (optional)")
    a = ap.parse_args()
    repo = a.repo.resolve()
    out_dir = repo / "reproduction" / "v14_rerun" / "code20"
    out_dir.mkdir(parents=True, exist_ok=True)
    rec = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code20_b1_freeze_order.py",
           "manuscript_sentence_section_3_4": SENTENCE}
    # 1. the published freeze record
    fe = repo / "docs" / "FREEZE_EVIDENCE.md"
    txt = fe.read_text(encoding="utf-8")
    m = re.search(r"\| author date \| \*\*(.+?)\*\*", txt)
    author_local = m.group(1).strip() if m else None
    tbl = {}
    for ev in ("EMSR773 Valencia", "EMSR664 Emilia-Romagna"):
        mm = re.search(rf"\| {re.escape(ev)} \| (.+?) \| \*\*(.+?)\*\* \| (.+?) \|", txt)
        if mm:
            tbl[ev] = {"config_written_local": mm.group(1).strip(), "first_execution_local": mm.group(2).strip(), "first_score_local": mm.group(3).strip()}
    rec["freeze_evidence_md"] = {"file": "docs/FREEZE_EVIDENCE.md", "sha256": hashlib.sha256(fe.read_bytes()).hexdigest(), "author_date_as_written": author_local,
                                 "author_date_utc": to_utc(author_local) if author_local else None, "held_out_table_local_plus0300": tbl,
                                 "note": "the file states every time in local time +03:00"}
    # 2. the private repository (primary evidence) when present
    priv = {"path": str(a.nhess), "present": (a.nhess / ".git").exists()}
    if priv["present"]:
        for c in (RULE_COMMIT, RESULTS_COMMIT, BIAS_COMMIT):
            h, ad, cd, subj = git(a.nhess, "log", "-1", "--format=%H%n%ai%n%ci%n%s", c).split("\n")
            priv[c] = {"hash": h, "author_date": ad, "author_date_utc": to_utc(ad), "committer_date": cd, "committer_date_utc": to_utc(cd), "subject": subj}
        for c in (RESULTS_COMMIT, BIAS_COMMIT):
            try:
                j = json.loads(git(a.nhess, "show", f"{c}:{VALENCIA_METRICS}"))
                priv[c]["valencia_metrics_generated_utc"] = j.get("generated_utc")
                priv[c]["valencia_metrics_csi_h_gt_0p10"] = ((j.get("metrics") or {}).get("csi") if isinstance(j.get("metrics"), dict) else None)
            except subprocess.CalledProcessError:
                priv[c]["valencia_metrics_generated_utc"] = None
        files = git(a.nhess, "ls-tree", "-r", "--name-only", RESULTS_COMMIT).split("\n")
        priv[RESULTS_COMMIT]["metrics_files"] = {}
        for f in files:
            if f.endswith("metrics.json") and f.startswith("runs/"):
                try:
                    priv[RESULTS_COMMIT]["metrics_files"][f] = json.loads(git(a.nhess, "show", f"{RESULTS_COMMIT}:{f}")).get("generated_utc")
                except Exception:
                    priv[RESULTS_COMMIT]["metrics_files"][f] = None
        rd = a.nhess / "runs" / "valencia_emsr773"
        priv["valencia_run_dir_mtimes_utc"] = {n: mtime_utc(rd / n) for n in ("valencia_emsr773_enhanced.yaml", "run.log", "sfincs_build.yml", "run_bias.log", "metrics.json") if (rd / n).exists()}
        priv["pending_figures_in_rule_commit"] = [f for f in git(a.nhess, "show", "--format=", "--name-only", RULE_COMMIT).split("\n") if "pending" in f]
    rec["private_repository"] = priv
    # 3. the repository's own record of the two metrics times (CODE-19 D7 ledger)
    lk = repo / "reproduction" / "v14_rerun" / "code19" / "lookups.json"
    d7 = json.loads(lk.read_text(encoding="utf-8"))["D7_valencia_anchor_ledger"]["entries"]
    def when_utc(entry):
        mm = re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", entry["when"])
        return mm.group(1) if mm else None
    ledger = {"file": "reproduction/v14_rerun/code19/lookups.json", "sha256": hashlib.sha256(lk.read_bytes()).hexdigest(),
              "first_valencia_metrics_utc": when_utc(d7[0]), "first_valencia_state": d7[0]["state"], "metrics_350mm_utc": when_utc(d7[1])}
    rec["code19_ledger"] = ledger
    # 4. the orders
    commit_utc = (priv.get(RULE_COMMIT) or {}).get("author_date_utc") or rec["freeze_evidence_md"]["author_date_utc"]
    first = (priv.get(RESULTS_COMMIT) or {}).get("valencia_metrics_generated_utc") or ledger["first_valencia_metrics_utc"]
    m350 = (priv.get(BIAS_COMMIT) or {}).get("valencia_metrics_generated_utc") or ledger["metrics_350mm_utc"]
    rec["orders"] = {"rule_commit_vs_first_valencia_metrics": order(commit_utc, first), "rule_commit_vs_350mm_metrics": order(commit_utc, m350)}
    if priv.get("valencia_run_dir_mtimes_utc", {}).get("valencia_emsr773_enhanced.yaml"):
        rec["orders"]["rule_commit_vs_valencia_config_mtime"] = order(commit_utc, priv["valencia_run_dir_mtimes_utc"]["valencia_emsr773_enhanced.yaml"])
    if priv.get("valencia_run_dir_mtimes_utc", {}).get("run.log"):
        rec["orders"]["rule_commit_vs_valencia_run_log_mtime"] = order(commit_utc, priv["valencia_run_dir_mtimes_utc"]["run.log"])
    o = rec["orders"]["rule_commit_vs_first_valencia_metrics"]
    if o["first"] == "commit":
        rec["verdict"] = (f"The rule commit {RULE_COMMIT} ({commit_utc}) precedes the first Valencia metrics ({first}) by {o['lead_hms']} and the 350 mm "
                          f"metrics ({m350}) by {rec['orders']['rule_commit_vs_350mm_metrics']['lead_hms']}; the section 3.4 sentence stands, no replacement needed.")
        rec["proposed_replacement"] = None
    else:
        rec["verdict"] = f"The first Valencia metrics ({first}) precede the rule commit {RULE_COMMIT} ({commit_utc}) by {o['lead_hms']}; the section 3.4 sentence must change."
        rec["proposed_replacement"] = (f"The rule was committed on 15 July 2026 at {commit_utc[11:16]} UTC; the first held-out run had been scored "
                                       f"{o['lead_hms']} earlier ({first[11:16]} UTC), so the freeze post-dates that first score.")
    # discrepancy inside FREEZE_EVIDENCE.md (report only)
    fs = tbl.get("EMSR773 Valencia", {}).get("first_score_local")
    fx = tbl.get("EMSR773 Valencia", {}).get("first_execution_local")
    if fs and first:
        fs_utc = to_utc(fs + ":00 +03:00") if re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d$", fs) else fs
        first_local = _p(first).astimezone(dt.timezone(dt.timedelta(hours=3))).strftime("%Y-%m-%d %H:%M")
        rec["freeze_evidence_discrepancy"] = (f"docs/FREEZE_EVIDENCE.md gives the first Valencia score as {fs} local (+03:00; = {fs_utc}), which is the 350 mm run "
                                              f"({m350}); the raw-IMERG run was scored at {first} (= {first_local} local), after the first execution the file lists "
                                              f"({fx} local). Reported, not edited.")
    out = out_dir / "b1_freeze_order.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": rec["verdict"], "orders": rec["orders"], "discrepancy": rec.get("freeze_evidence_discrepancy")}, indent=1, ensure_ascii=False))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
