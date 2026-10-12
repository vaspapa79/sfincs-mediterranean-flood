# A2 — pavbnd reference pressure 101325 Pa vs event-window domain-mean ERA5 MSLP, 2026-10-12T10:00:41Z

IB offset = (pavbnd - p) / (rhow g), rhow = 1024 kg/m³ (SFINCS default), g = 9.81. Window = [tstart, tstop] of the enhanced YAML (Crete: baseline YAML, same window); all ERA5 cells of the downloaded box (bbox + buffer). SFINCS `gapres` default = 101200 Pa.

| event | window | mean MSLP (hPa) | 101325 − mean (hPa) | constant IB offset at the mean (m) | domain-mean minimum (hPa, time) | IB at the minimum (m) | IB range in window (m) |
|---|---|---|---|---|---|---|---|
| Pineios EMSR692 | 2023-09-03 → 2023-09-11 | 1015.38 | -2.13 | -0.021 | 1007.94 (2023-09-05 03:00) | +0.053 | 0.113 |
| Mandra EMSR257 | 2017-11-13 → 2017-11-18 | 1012.99 | +0.26 | +0.003 | 1004.12 (2017-11-13 13:00) | +0.091 | 0.138 |
| Strymonas EMSR122 | 2015-03-28 → 2015-04-04 | 1009.02 | +4.23 | +0.042 | 1001.72 (2015-03-28 03:00) | +0.115 | 0.159 |
| Valencia EMSR773 | 2024-10-27 → 2024-11-01 | 1018.03 | -4.78 | -0.048 | 1013.25 (2024-10-29 17:00) | +0.000 | 0.089 |
| Emilia-Romagna EMSR664 | 2023-05-14 → 2023-05-22 | 1011.62 | +1.63 | +0.016 | 1000.70 (2023-05-16 08:00) | +0.125 | 0.178 |
| Crete EMSR933 | 2026-09-28 → 2026-10-06 | 1018.46 | -5.21 | -0.052 | 1014.53 (2026-10-01 03:00) | -0.013 | 0.071 |
