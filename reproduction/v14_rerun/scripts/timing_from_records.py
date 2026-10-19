"""Timing lines for reproduction/emsr933/timing.md from the run records (GO Phases 3-5): one line per finished run with
start/end UTC, hydromt build, SFINCS and validation wall-clocks (published SFINCS wall-clock in brackets). Nothing retyped.
Usage: python -I timing_from_records.py --repo <worktree> --phase 3|5 [--append]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--phase", type=int, required=True)
    ap.add_argument("--append", action="store_true")
    a = ap.parse_args()
    res = a.repo / "reproduction" / "v14_rerun" / "results"
    lines = []
    recs = sorted((json.loads(p.read_text(encoding="utf-8")) for p in res.glob("*_record.json")), key=lambda r: r.get("start_utc") or "")
    for r in recs:
        if r.get("phase") != a.phase or not r.get("end_utc"):
            continue
        st = {s["step"]: s for s in r.get("steps", [])}
        b = st.get(10, {}).get("wall_s"); v = (r.get("validation_v14") or {}).get("wall_s")
        lines.append(f"- {r['start_utc']} → {r['end_utc']} — `{r['run']}`" + (f" (MANIFEST row {r['manifest_row']})" if r.get("manifest_row") else "") +
                     f": hydromt build {b} s, SFINCS {r.get('sfincs_total_time_s')} s" + (f" (published {r['published_wallclock_s']} s)" if r.get("published_wallclock_s") else "") +
                     f", v1.4 validation {v} s" + ("; resumed (validation only)" if r.get("resumed") else "") + (f"; {r['label']}" if r.get("label") else "") + ".")
    out = "\n".join(lines)
    print(out)
    if a.append and lines:
        with open(a.repo / "reproduction" / "emsr933" / "timing.md", "a", encoding="utf-8") as fh:
            fh.write(f"\n### Phase {a.phase} runs (from the records, `timing_from_records.py`)\n" + out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
