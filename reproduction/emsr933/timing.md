# EMSR933 Crete — timing log (CODE-10)

Purpose: the manuscript reports the elapsed time from the EMS activation
(**2026-10-04 11:02 UTC**, to be confirmed from the API snapshot) to a validated hindcast. Every stage
logs wall-clock start/end in UTC and person-hours. "Claude" = the Claude Code session
(agent wall-clock, including waiting on downloads); "DvS" = Dimitris Valsamis (to be filled in by DvS);
"VP" = Papaioannou decision time, if any.

Wall-clock sources: Claude session transcript timestamps (session `9345177c`) and `date -u` at stage
boundaries. Times are UTC.

| Stage | Start (UTC) | End (UTC) | Wall-clock | Claude (h) | DvS (h) | VP (h) | Notes |
|---|---|---|---|---|---|---|---|
| 0 Preflight + EMS snapshot + availability | 2026-10-09T12:35:48Z | 2026-10-09T12:56Z | 0 h 20 min | 0.35 | _to fill_ | — | session start = task paste; end = STAGE0_REPORT.md written |
| 1 Rule ledger + YAMLs (no model runs); also F2/F4 fixes + regression, F5_VERIFY.md, daily latency probe | 2026-10-09T13:08:34Z | | | | _to fill_ | | start = Checkpoint-0 go received |

## Data-latency probe (daily, until ERA5T covers 7 Oct) — `scripts/daily_probe.py`, CSV in `latency_probe.csv`
| probe UTC | ERA5 last requestable day | IMERG Final granules 27 Sep–7 Oct | GloFAS v4 intermediate last day | EMS products F/I/N | AOI03 GRA |
|---|---|---|---|---|---|
| 2026-10-09T13:20:35Z | 2026-10-03 | 0 | 2026-10-06 | 6/1/11 | I (id 2965, maps 0, dl=no) |

Reference point for the manuscript: `activationTime` **2026-10-04T11:02:00** UTC (API snapshot
`ems_api_snapshot_20261009T124720Z.json`). Task issued 2026-10-09T12:35:48Z, i.e. 5 d 1 h 34 min after
activation — idle time before CODE-10 existed, to be reported as such, not as pipeline time.

## Stage 0 — event log
- 2026-10-09T12:35:48Z — CODE-10 task received; workspace orientation (CLAUDE.md, DIRECTORY_MAP, memory, held-out templates).
- 2026-10-09T12:43Z — branch `emsr933-crete` created as a linked worktree at
  `sfincs-mediterranean-floods/.worktrees/emsr933-crete`, base `origin/main` = v1.3.0 (`ccd423a`), `--no-track`.
- 2026-10-09T12:44Z — preflight (`run_pipeline.py --check` + `scripts/preflight_stage0.py`) PASS.
- 2026-10-09T12:47:20Z — EMS API snapshot (provisional cut-off); 6 released packages downloaded by 12:48Z.
- 2026-10-09T12:51:44Z — availability checks (IMERG/CDS/EWDS/DEM/WorldCover); 12:52:19–12:53Z ERA5T expver probe (2 CDS requests, 35 s each).
- 2026-10-09T12:56Z — STAGE0_REPORT.md written; commit follows. Waiting for Checkpoint-0 go.
- 2026-10-09T12:59:16Z — commit `6a5e64b` (Stage 0 records); AUDIT.md §8 entry + this line committed next.
