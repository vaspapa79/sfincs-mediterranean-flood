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
| 1 Rule ledger + YAMLs (no model runs); also F2/F4 fixes + regression, F5_VERIFY.md, daily latency probe, NOA station retrieval | 2026-10-09T13:08:34Z | 2026-10-09T14:15Z | 1 h 07 min | 1.1 | _to fill_ | | start = Checkpoint-0 go; end = Checkpoint-1 posted; four F5 agents + one web-research agent ran in parallel (their wall-clock is inside this hour) |

## Data-latency probe (daily, until ERA5T covers 7 Oct) — `scripts/daily_probe.py`, CSV in `latency_probe.csv`
| probe UTC | ERA5 last requestable day | IMERG Final granules 27 Sep–7 Oct | GloFAS v4 intermediate last day | EMS products F/I/N | AOI03 GRA |
|---|---|---|---|---|---|
| 2026-10-09T13:20:35Z | 2026-10-03 | 0 | 2026-10-06 | 6/1/11 | I (id 2965, maps 0, dl=no) |
| 2026-10-12T09:01:29Z | 2026-10-06 | 0 | 2026-10-08 | 7/0/11 | F (id 2965, maps 1, dl=yes) |

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

## Stage 1 — event log
- 2026-10-09T13:08:34Z — Checkpoint-0 go received (decisions 1–8); Stage 1 started.
- 2026-10-09T13:1xZ — found that `docs/AUDIT.md` was never tracked in the public repo; canonical copy brought onto the branch (`d1752c6`).
- 2026-10-09T13:20:35Z — first daily latency probe (table above).
- 2026-10-09T13:27Z — F2/F4 implemented under TDD (14 tests GREEN); regression vs published Valencia/Emilia records IDENTICAL (`regression_f2f4.json`); F5 analyses (a–f) dispatched to four parallel read-only agents at 13:12Z; NOA station research dispatched 13:27Z; GLO-30 + WorldCover tile download started 13:27Z (done 13:29Z).
- 2026-10-09T13:32:48Z — `stage1_terrain.py` (pyflwdir on GLO-30 @ 90 m, 23 s); 13:38:33Z `stage1_depressions.py` (polje components).
- 2026-10-09T13:31–13:37Z — the four F5 agents returned (a–c 13:31, e 13:33, f 13:35, d 13:37); `F5_VERIFY.md` compiled 13:45Z; agent numbers spot-checked against their JSONs.
- 2026-10-09T13:49Z — catalog-label test GREEN (17 tests); schema validation of `emsr933_crete.yaml` + `emsr933_crete_enhanced.yaml` OK (`stage1_yaml_validation.json`); `rule_ledger.md` written, §7 (R2-on anchor) pending the NOA/meteo.gr retrieval; commit `46aba38` 13:50Z.
- 2026-10-09T14:04Z — NOA/meteo.gr retrieval returned (13 stations, 117 daily values, 57 published figures, sources + licence); Tzermiado 30 Sep–4 Oct = 447.8 mm (NOA 448).
- 2026-10-09T14:08Z — polje catchments recomputed basin-based (Lasithi 128.6 km², was 223 by inlet-sum double counting); `emsr933_crete_enhanced_R2on.yaml` written and schema-checked (3 configs, preflight OK); ledger §7 completed.
