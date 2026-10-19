# EMSR933 - Stage 5a: final truth set frozen from the post-closure EMS API snapshot (2026-10-19T13:34:37Z)

Generated 2026-10-19T13:57:20Z by `scripts/stage5_truth_freeze.py` from `ems_snapshot_20261019T133437Z_products.csv` (vs the provisional cut-off `ems_snapshot_20261009T124720Z_products.csv`) and the snapshot manifest (raw API JSON sha256 `710f620e6d4567d4...`). Activation closed: **True**. Released packages: **7** of 18 API rows; AOIs without any released product: 02, 05, 08. Tiers: rule_ledger.md section 8 item 3.

| AOI | product | id | tier | enters scored truth | post-event image (acquisition UTC) | obs km2 (union) | notAnalysed km2 | AOI km2 | zip sha256 | since 9 Oct cut-off |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 Kastelli | DEL_MONIT01 | 2962 | 2 | yes | Legion 06/10/2026 T10:47:00Z (1.2 m) | 0.242 | 45.298 | 252.53 | `bbe7fe84c5f2` | unchanged |
| 03 Tzermiado | DEL | 2955 | 1 | yes | Sentinel-1 04/10/2026 T16:22:00Z (20.0 m) | 3.2192 | 0.0 | 174.41 | `14789be38b4d` | unchanged |
| 03 Tzermiado | DEL_MONIT02 | 2959 | 1 | yes | GeoEye-1 08/10/2026 T09:02:00Z (2.0 m) | 3.7807 | 0.0 | 174.41 | `07ae2fb6f7f1` | unchanged |
| 03 Tzermiado | GRA | 2965 | 1 | no - grading dropped: a delineation exists for this AOI | Legion 09/10/2026 T09:32:00Z (0.4 m) | 4.0685 | 0.0 | 46.74 | `67908c72d1d7` | status I -> F |
| 04 Agios Ioannis | DEL_MONIT01 | 2957 | 2 | yes | WorldView-3 06/10/2026 T10:46:00Z (1.6 m) | 0.0325 | 0.0 | 59.26 | `24339cffc56c` | unchanged |
| 06 Agios Nikolaos | DEL_MONIT01 | 2960 | 2 | yes | Legion 08/10/2026 T08:55:00Z (2.0 m) | 0.0593 | 0.0 | 116.18 | `a989df1406ee` | unchanged |
| 07 Omalos | DEL_MONIT01 | 2964 | 2 | yes | Legion 06/10/2026 T10:45:00Z (1.6 m) | 0.0506 | 30.047 | 266.31 | `4e1f53866489` | unchanged |

Tier 1 (scored) = AOI03 Tzermiado: the validator unions every released delineation package of the AOI (`_select_obs_shps`, `include_del_product: true`): DEL (Sentinel-1 04/10/2026 T16:22:00Z (20.0 m)) + DEL_MONIT02 (GeoEye-1 08/10/2026 T09:02:00Z (2.0 m)); the grading package released after the cut-off is dropped by the delineation-first rule (kept on disk; its acquisition is listed for the time-matched diagnostic).
Tier 2 (km2 only) = AOIs 01, 04, 06, 07 (one optical DEL_MONIT01 each). Tier 3 (excluded) = AOIs 02, 05, 08 (every product 'N - remote sensing limitations'). No all-AOI union score.
Files: `stage5_truth_freeze.json`, `ems_snapshot_20261019T133437Z_products.csv`, `ems_snapshot_20261019T133437Z_products.md`, `ems_snapshot_20261019T133437Z_manifest.json`; packages extracted under `D:\ELKAK\implementation\emsr933_crete\ems_snapshots\20261019T133437Z\extracted`.
