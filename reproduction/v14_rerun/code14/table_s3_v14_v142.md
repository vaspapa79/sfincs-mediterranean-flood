# Table S3 equivalent — evaluation-mask sensitivity under harness v1.4_v142 (generated 2026-10-21T09:23:32Z by `scripts/table_s3_v14.py`)

Canonical run per event held fixed; the mask varies as in the published `_mask_sensitivity.py`; the v1.4 exclusion (WorldCover 80 ∪ open sea) is removed from every variant on both sides; variant 2 equals the canonical v1.4 record (checked in the JSON).

| Event | Mask | Area (km²) | CSI | HR | FAR | B | GSS | TP / FP / FN | published S3 (CSI / HR / B) |
|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) | Active mask (no AOI) | 4956 | 0.469 | 0.901 | 0.506 | 1.82 | 0.253 | 60367 / 61749 / 6640 | see supplement Table S3 |
|  | AOI-union (v1.4 reference) | 4507 | 0.496 | 0.901 | 0.475 | 1.72 | 0.263 | 60367 / 54722 / 6640 | see supplement Table S3 |
|  | AOI-union + 1 km | 4575 | 0.491 | 0.901 | 0.480 | 1.73 | 0.261 | 60367 / 55832 / 6640 | see supplement Table S3 |
|  | AOI-union − 1 km | 4414 | 0.500 | 0.901 | 0.471 | 1.70 | 0.264 | 60039 / 53452 / 6600 | see supplement Table S3 |
| Mandra (EMSR257) | Active mask (no AOI) | 280 | 0.070 | 0.760 | 0.928 | 10.60 | 0.041 | 2682 / 34723 / 846 | see supplement Table S3 |
|  | AOI-union (v1.4 reference) | 87 | 0.157 | 0.760 | 0.835 | 4.61 | 0.067 | 2682 / 13587 / 846 | see supplement Table S3 |
|  | AOI-union + 1 km | 122 | 0.123 | 0.760 | 0.872 | 5.92 | 0.058 | 2682 / 18197 / 846 | see supplement Table S3 |
|  | AOI-union − 1 km | 48 | 0.198 | 0.770 | 0.789 | 3.65 | 0.076 | 2107 / 7890 / 629 | see supplement Table S3 |
| Strymonas (EMSR122) | Active mask (no AOI) | 3985 | 0.318 | 0.921 | 0.673 | 2.82 | 0.300 | 4269 / 8787 / 364 | see supplement Table S3 |
|  | AOI-union (v1.4 reference) | 1196 | 0.334 | 0.921 | 0.656 | 2.68 | 0.272 | 4269 / 8153 / 364 | see supplement Table S3 |
|  | AOI-union + 1 km | 1279 | 0.332 | 0.921 | 0.659 | 2.70 | 0.274 | 4269 / 8244 / 364 | see supplement Table S3 |
|  | AOI-union − 1 km | 1109 | 0.336 | 0.922 | 0.654 | 2.66 | 0.270 | 4269 / 8068 / 361 | see supplement Table S3 |
| Valencia (EMSR773) | Active mask (no AOI) | 2915 | 0.139 | 0.939 | 0.860 | 6.70 | 0.077 | 18381 / 112765 / 1200 | — (not in S3) |
|  | AOI-union (v1.4 reference) | 2710 | 0.144 | 0.939 | 0.855 | 6.46 | 0.078 | 18381 / 108091 / 1200 | — (not in S3) |
|  | AOI-union + 1 km | 2723 | 0.144 | 0.939 | 0.855 | 6.48 | 0.078 | 18381 / 108429 / 1200 | — (not in S3) |
|  | AOI-union − 1 km | 2692 | 0.145 | 0.939 | 0.854 | 6.43 | 0.078 | 18381 / 107590 / 1200 | — (not in S3) |
| Emilia-R. (EMSR664) | Active mask (no AOI) | 5007 | 0.177 | 0.852 | 0.818 | 4.67 | 0.075 | 21507 / 96349 / 3733 | — (not in S3) |
|  | AOI-union (v1.4 reference) | 3148 | 0.253 | 0.852 | 0.735 | 3.22 | 0.098 | 21507 / 59690 / 3733 | — (not in S3) |
|  | AOI-union + 1 km | 3435 | 0.239 | 0.852 | 0.750 | 3.41 | 0.096 | 21507 / 64626 / 3733 | — (not in S3) |
|  | AOI-union − 1 km | 2823 | 0.260 | 0.861 | 0.729 | 3.17 | 0.096 | 20395 / 54835 / 3302 | — (not in S3) |
