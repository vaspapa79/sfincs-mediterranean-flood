"""CODE-19 A3 — the machine behind the canonical runs: CPU model, physical cores, logical processors, RAM and OS (Windows CIM, read on
the machine that holds the run directories), the SFINCS build and thread count printed in each run's sfincs.log, the executable and
interpreter paths in each pipeline log, and the run records' start/end times — to state whether all six canonical runs used the same
machine. Read-only.

Usage: python -I code19_a3_hardware.py --repo <worktree>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path

RUNS = [("pineios", "pineios_enhanced_v142"), ("mandra", "mandra_enhanced"), ("strymonas", "strymonas_enhanced_postD6_v142"),
        ("valencia", "valencia_enhanced_164_v142"), ("emilia", "emilia_enhanced_8aoi_v142"), ("crete", "crete_canonical_r2on")]
PS = ("$p = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed; "
      "$c = Get-CimInstance Win32_ComputerSystem | Select-Object Name, TotalPhysicalMemory, Manufacturer, Model; "
      "$o = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture; "
      "$m = (Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum; "
      "[pscustomobject]@{processor=$p; computer=$c; os=$o; installed_memory_bytes=$m} | ConvertTo-Json -Depth 4")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "skill" / "scripts"))
    from _common import load_config
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "generator": "reproduction/v14_rerun/scripts/code19_a3_hardware.py",
           "read_on_host": socket.gethostname(), "python_platform": platform.platform()}
    try:
        cim = json.loads(subprocess.run(["powershell", "-NoProfile", "-Command", PS], capture_output=True, text=True, check=True).stdout)
    except Exception as e:  # noqa: BLE001
        cim = {"error": repr(e)}
    out["machine_cim"] = cim
    runs = []
    for event, run in RUNS:
        cfg = load_config(["--config", str(repo / "reproduction" / "v14_rerun" / "configs" / f"{run}.yaml")])
        model = cfg.paths["model_dir"]; work = cfg.paths["work_dir"]
        log = (model / "sfincs.log").read_text(encoding="utf-8", errors="replace") if (model / "sfincs.log").exists() else ""
        plog = (work / "pipeline_v14.log").read_text(encoding="utf-8", errors="replace") if (work / "pipeline_v14.log").exists() else ""
        rec = json.loads((repo / "reproduction" / "v14_rerun" / "results" / f"{run}_record.json").read_text(encoding="utf-8"))
        thr = re.search(r"Using (\d+) of (\d+) available threads", log)
        exe_lines = sorted({ln.strip()[:200] for ln in plog.splitlines() if re.search(r"sfincs\.exe|running:", ln, re.I)})[:4]
        runs.append({"event": event, "run": run, "model_dir": str(model), "sfincs_build_revision": (re.search(r"Build-Revision:\s*(.+)", log) or [None, None])[1],
                     "sfincs_build_date": (re.search(r"Build-Date:\s*\$Date:\s*([\d-]+)", log) or [None, None])[1],
                     "threads_used": int(thr.group(1)) if thr else None, "threads_available": int(thr.group(2)) if thr else None,
                     "config_sfincs_exe": cfg.env.get("sfincs_exe"), "pipeline_log_lines": exe_lines, "start_utc": rec.get("start_utc"), "end_utc": rec.get("end_utc"),
                     "sfincs_total_time_s": rec.get("sfincs_total_time_s"),
                     "local_user_paths_in_pipeline_log": sorted(set(re.findall(r"[A-Za-z]:[/\\]Users[/\\]([A-Za-z0-9_.-]+)", plog)))})
    out["runs"] = runs
    out["same_machine_evidence"] = {"thread_lines_identical": len({(r["threads_used"], r["threads_available"]) for r in runs}) == 1,
                                    "build_identical": len({(r["sfincs_build_revision"], r["sfincs_build_date"]) for r in runs}) == 1,
                                    "user_paths": sorted({u for r in runs for u in r["local_user_paths_in_pipeline_log"]}),
                                    "run_dirs_on_this_host": all(Path(r["model_dir"]).exists() for r in runs)}
    p = repo / "reproduction" / "v14_rerun" / "code19" / "a3_hardware.json"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "runs"}, indent=1, ensure_ascii=False))
    for r in runs:
        print(r["run"], "|", r["sfincs_build_revision"], r["sfincs_build_date"], "| threads", r["threads_used"], "/", r["threads_available"], "|", r["start_utc"], "->", r["end_utc"], "|", r["pipeline_log_lines"][:1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
