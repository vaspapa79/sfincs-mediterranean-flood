# Table S3 equivalent — evaluation-mask sensitivity under harness v1.4 (generated 2026-10-20T08:54:22Z by `scripts/table_s3_v14.py`)

Canonical run per event held fixed; the mask varies as in the published `_mask_sensitivity.py`; the v1.4 exclusion (WorldCover 80 ∪ open sea) is removed from every variant on both sides; variant 2 equals the canonical v1.4 record (checked in the JSON).

| Event | Mask | Area (km²) | CSI | HR | FAR | B | GSS | TP / FP / FN | published S3 (CSI / HR / B) |
|---|---|---|---|---|---|---|---|---|---|
| Pineios (EMSR692) | Active mask (no AOI) | 4956 | 0.468 | 0.898 | 0.506 | 1.82 | 0.252 | 60201 / 61693 / 6806 | see supplement Table S3 |
|  | AOI-union (v1.4 reference) | 4507 | 0.495 | 0.898 | 0.476 | 1.71 | 0.262 | 60201 / 54666 / 6806 | see supplement Table S3 |
|  | AOI-union + 1 km | 4575 | 0.490 | 0.898 | 0.481 | 1.73 | 0.260 | 60201 / 55776 / 6806 | see supplement Table S3 |
|  | AOI-union − 1 km | 4414 | 0.499 | 0.898 | 0.471 | 1.70 | 0.262 | 59873 / 53396 / 6766 | see supplement Table S3 |
| Mandra (EMSR257) | Active mask (no AOI) | 280 | 0.070 | 0.760 | 0.928 | 10.60 | 0.041 | 2682 / 34723 / 846 | see supplement Table S3 |
|  | AOI-union (v1.4 reference) | 87 | 0.157 | 0.760 | 0.835 | 4.61 | 0.067 | 2682 / 13587 / 846 | see supplement Table S3 |
|  | AOI-union + 1 km | 122 | 0.123 | 0.760 | 0.872 | 5.92 | 0.058 | 2682 / 18197 / 846 | see supplement Table S3 |
|  | AOI-union − 1 km | 48 | 0.198 | 0.770 | 0.789 | 3.65 | 0.076 | 2107 / 7890 / 629 | see supplement Table S3 |
| Strymonas (EMSR122) | Active mask (no AOI) | 3985 | 0.318 | 0.921 | 0.673 | 2.82 | 0.300 | 4269 / 8798 / 364 | see supplement Table S3 |
|  | AOI-union (v1.4 reference) | 1196 | 0.334 | 0.921 | 0.657 | 2.68 | 0.272 | 4269 / 8162 / 364 | see supplement Table S3 |
|  | AOI-union + 1 km | 1279 | 0.331 | 0.921 | 0.659 | 2.70 | 0.274 | 4269 / 8253 / 364 | see supplement Table S3 |
|  | AOI-union − 1 km | 1109 | 0.336 | 0.922 | 0.654 | 2.67 | 0.269 | 4269 / 8077 / 361 | see supplement Table S3 |
| Valencia (EMSR773) | Active mask (no AOI) | 2915 | 0.139 | 0.939 | 0.860 | 6.70 | 0.077 | 18381 / 112808 / 1200 | — (not in S3) |
|  | AOI-union (v1.4 reference) | 2710 | 0.144 | 0.939 | 0.855 | 6.46 | 0.078 | 18381 / 108134 / 1200 | — (not in S3) |
|  | AOI-union + 1 km | 2723 | 0.144 | 0.939 | 0.855 | 6.48 | 0.078 | 18381 / 108472 / 1200 | — (not in S3) |
|  | AOI-union − 1 km | 2692 | 0.144 | 0.939 | 0.854 | 6.44 | 0.078 | 18381 / 107633 / 1200 | — (not in S3) |
| Emilia-R. (EMSR664) | Active mask (no AOI) | 5007 | 0.176 | 0.850 | 0.819 | 4.68 | 0.074 | 21455 / 96758 / 3785 | — (not in S3) |
|  | AOI-union (v1.4 reference) | 3148 | 0.251 | 0.850 | 0.737 | 3.23 | 0.096 | 21455 / 60073 / 3785 | — (not in S3) |
|  | AOI-union + 1 km | 3435 | 0.238 | 0.850 | 0.752 | 3.43 | 0.094 | 21455 / 65035 / 3785 | — (not in S3) |
|  | AOI-union − 1 km | 2823 | 0.258 | 0.859 | 0.731 | 3.19 | 0.094 | 20350 / 55215 / 3347 | — (not in S3) |
