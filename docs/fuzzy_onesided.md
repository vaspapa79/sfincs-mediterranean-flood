# One-sided fuzzy validation of the canonical runs (V3 fix)

Strict (r=0) is unchanged from the published headline numbers. The previous "asymmetric (Wing 2017)" block dilated **both** fields, so it was byte-identical to the symmetric block; this table replaces it with two genuine one-sided directions.

- **Symmetric** — dilate BOTH model & obs (over-counts agreement; kept for comparison).
- **Model-oriented (dilate OBS only)** — a modelled wet cell is a hit if an observed cell is within *r*; FAR/precision-meaningful.
- **Obs-oriented (dilate MODEL only)** — an observed wet cell is detected if a modelled cell is within *r*; HR/recall-meaningful.

## Pineios EMSR692 (v1 enhanced)

| r | sym CSI | sym HR | sym FAR | mdl-orient CSI | mdl-orient HR | mdl-orient FAR | obs-orient CSI | obs-orient HR | obs-orient FAR |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 (=strict) | 0.456 | 0.947 | 0.532 | 0.456 | 0.947 | 0.532 | 0.456 | 0.947 | 0.532 |
| 1 | 0.426 | 0.992 | 0.572 | 0.511 | 0.911 | 0.463 | 0.359 | 0.995 | 0.640 |
| 2 | 0.441 | 0.998 | 0.558 | 0.540 | 0.886 | 0.420 | 0.334 | 1.000 | 0.666 |
| 3 | 0.470 | 0.999 | 0.530 | 0.560 | 0.867 | 0.387 | 0.329 | 1.000 | 0.671 |

## Strymonas EMSR122 (v3)

| r | sym CSI | sym HR | sym FAR | mdl-orient CSI | mdl-orient HR | mdl-orient FAR | obs-orient CSI | obs-orient HR | obs-orient FAR |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 (=strict) | 0.183 | 0.328 | 0.706 | 0.183 | 0.328 | 0.706 | 0.183 | 0.328 | 0.706 |
| 1 | 0.250 | 0.398 | 0.599 | 0.186 | 0.270 | 0.625 | 0.220 | 0.458 | 0.702 |
| 2 | 0.287 | 0.424 | 0.528 | 0.181 | 0.237 | 0.566 | 0.233 | 0.535 | 0.708 |
| 3 | 0.312 | 0.436 | 0.476 | 0.176 | 0.216 | 0.511 | 0.235 | 0.590 | 0.719 |

## Mandra EMSR257 (v1 enhanced)

| r | sym CSI | sym HR | sym FAR | mdl-orient CSI | mdl-orient HR | mdl-orient FAR | obs-orient CSI | obs-orient HR | obs-orient FAR |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 (=strict) | 0.106 | 0.873 | 0.892 | 0.106 | 0.873 | 0.892 | 0.106 | 0.873 | 0.892 |
| 1 | 0.159 | 0.962 | 0.840 | 0.164 | 0.791 | 0.829 | 0.092 | 0.978 | 0.907 |
| 2 | 0.205 | 0.986 | 0.794 | 0.207 | 0.748 | 0.778 | 0.086 | 0.994 | 0.914 |
| 3 | 0.247 | 0.995 | 0.753 | 0.241 | 0.723 | 0.734 | 0.083 | 1.000 | 0.917 |

