# Per-event validation reports

One JSON per event, produced by `validation/validate_event_v2.py` — the pixel-wise
validation of each canonical enhanced SFINCS run against the Copernicus EMS
rapid-mapping flood extent on the evaluation mask (active model area ∩ union of the
EMS areas of interest). These are the headline numbers reported in the manuscript
(Tables 9, 13, 14); they are regenerable from the public inputs and the per-event YAML
configurations in `skill/examples/` — the `sfincs_map.nc` outputs are not shipped
(60–400 MB each; ~10 min/event to reproduce on a 16-thread CPU).

Each file gives, at the strict thresholds h_max > {0.05, 0.10, 0.25, 0.50} m, the full
contingency table (tp/fp/fn/tn) and CSI, HR, FAR, F1, F2, frequency bias B, GSS, HSS,
accuracy, plus the base-rate-robust SEDI and PSS. Canonical threshold is h_max > 0.10 m.

| file | event | strict CSI @0.10 m | observed wet (km²) |
|---|---|---|---|
| `pineios_emsr692_metrics.json`   | Storm Daniel / Pineios (EMSR692) | 0.456 | 1518.8 |
| `strymonas_emsr122_metrics.json` | Strymonas (EMSR122), audit-corrected v3 | 0.183 | 106.6 |
| `mandra_emsr257_metrics.json`    | Mandra (EMSR257) | 0.106 | 9.0 |
| `valencia_emsr773_metrics.json`  | Valencia DANA (EMSR773), held-out, R2 ×1.94 → 164 mm | 0.094 | 200.3 |
| `emilia_emsr664_metrics.json`    | Emilia-Romagna (EMSR664), held-out, full 8-AOI | 0.240 | 592.6 |

Truth union: per area of interest, the DELINEATION (crisis) product is used where
available, otherwise the GRADING product (see `_select_obs_shps` in
`validation/validate_event_v2.py`). For EMSR664 this unions the Forlì SAR delineation
with the seven downstream optical/aerial grading AOIs; for EMSR773 it uses the
delineation AOIs.
