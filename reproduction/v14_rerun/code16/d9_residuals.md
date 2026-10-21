# D9 residual items, measured — generated 2026-10-21T09:15:21Z by `reproduction/v14_rerun/scripts/d9_residuals.py`

Ledger `code15/source_points_v142.json` (resolved 2026-10-20T12:42:30Z). Offset = distance from the snapped injection cell (or, for a point that is not injected, from its YAML injection coordinate) to the nearest model cell on the named river's channel: cells inside the 0.05° footprints of the river's GloFAS v4 cells within 15 km whose D8 upstream area is ≥ 0.5 × the footprint maximum (footprints whose D8 maximum exceeds 2.0 × the GloFAS upstream area — a larger river crossing — are skipped).

| id | point | kind | offset km | injection cell: z_b m, D8 km² | nearest channel cell: z_b m, D8 km², GloFAS footprint |
|---|---|---|---|---|---|
| D9-1 | pineios_trikala (Pineios) | injection | 3.76 | 95.79, 1.91 | 94.05, 152.48, [21.875, 39.525] |
| D9-2 | titarisios (Titarisios) | injection | 10.95 | 61.69, 4.88 | 82.51, 1632.26, [22.275, 39.725] |
| D9-3 | ronco (Ronco) | injection | 3.03 | 101.38, 6.32 | 44.98, 145.82, [12.075, 44.125] |
| D9-4 | montone (Montone) | injection | 0.6 | 62.98, 0.5 | 52.0, 175.46, [11.975, 44.175] |
| D9-5 | jucar (Jucar) | sampling at the mouth reach (Magro nested) | 0.0 | 2.95, 2183.77 | 2.95, 2183.77, [-0.325, 39.175] |
| D9-6 | pineios_kalambaka (Pineios) | sampled only (inject: false) | None | None, 0.02 | None, None, None |
| D9-7 | Pineios lattice | lattice offset of the frozen Open-Meteo file | 4.29 | — | +0.05° longitude at 39.66° N |
