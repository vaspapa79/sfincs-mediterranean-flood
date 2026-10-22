# CODE-17 C — records for the manuscript (look-ups, 21 Oct 2026)

> **Note (22 Oct 2026):** written for the first CODE-17 checkpoint. The look-ups were re-done and extended on 22 Oct 2026; the record of reference is `lookups.json` (B1–B4) with `c6_alltouched_inflation.json` (B5, now with the centre-point re-scoring) and the CODE-17 block of `docs/AUDIT.md`. Where this file and `lookups.json` differ, `lookups.json` applies.

All look-ups were made on 2026-10-21 (UTC). Raw responses are in the CODE-17 attachments (`c1/`, `c2c3/`, `c4/`, `c5/`).
No e-mail address or personal identifier was sent to any service. These records are not committed: the A commit
`f3a11f4` was the single commit of CODE-17.

## C1. When the frozen rule became public

- **Origin commit.** The rule was frozen in `bfd005a` of the private manuscript-build repository, on 2026-07-15 at
  14:33:54 +03:00. That repository has no public remote, so this commit was never pushed to origin
  ([docs/FREEZE_EVIDENCE.md](../../../docs/FREEZE_EVIDENCE.md)).
- **Public copy.** `docs/frozen_rule_R.md` and `docs/FREEZE_EVIDENCE.md` were added in `786fc50`, authored
  2026-07-20 at 12:12:30Z. The file is unchanged since then (`git diff 786fc50 HEAD -- docs/frozen_rule_R.md` is empty).
- **First push of `786fc50` to origin:** **2026-07-22T08:31:35Z**, in the push `ecc9d5d → a72897c` to
  `github.com/vaspapa79/sfincs-mediterranean-flood` by `dmvalsamis`. Source: the GitHub repository-activity API
  (`c1/github_activity.json`). The local reflog of `origin/main` agrees ("update by push", 2026-07-22 11:31:35 +0300).
- **Zenodo** (Zenodo records API and DataCite, `c1/zenodo_versions.json` and `c1/datacite_*.json`):
  - Concept DOI **10.5281/zenodo.20523154**: registered 2026-06-03T08:12:29Z with v.0.0.1 (record 20523155). It
    predates the rule and resolves to the latest version.
  - **10.5281/zenodo.21488879** = v1.3.0: created and published **2026-07-22T09:43:56Z**; `publication_date` 2026-07-22.
  - The first archive that contains the rule is v1.2.0, **10.5281/zenodo.21487689**, created 2026-07-22T09:04:56Z
    (tag v1.2.0 → `738fa3d`, a descendant of `786fc50`). v1.1.0 (20829572, 2026-06-24) predates the rule.
- **Earliest third-party-attested date of the rule:** 2026-07-22T08:31:35Z (the GitHub push). That is after the two
  held-out runs of 15 Jul and before the EMSR933 event (30 Sep) and its activation (2026-10-04T11:02Z).

## C2. Copernicus DEM GLO-30 citation (`c2c3/RESULT.md`)

- **10.5069/G9028PQB** (DataCite) is OpenTopography's DOI for its own distribution. DataCite gives the title
  "Copernicus GLO-90 Digital Surface Model" (OpenTopography, 2021). The landing page covers COP30 and COP90 under the
  same DOI, and OpenTopography has no separate GLO-30 DOI. We did not use that distribution.
- **ESA's DOI for the Copernicus DEM: 10.5270/ESA-c5d3d65.** It is registered with Crossref, not DataCite:
  "Copernicus DEM", European Space Agency and Airbus, 2022, dataset. ESA asks users to cite it; this rests on a
  Wayback copy of 2026-10-18 of the CDSE COP-DEM page, which was down today.
- **The copy we downloaded** (AWS bucket `copernicus-dem-30m`) has the DataCite DOI **10.60489/roda.mxyog0**:
  "Copernicus Digital Elevation Model (DEM)", Sinergise, Registry of Open Data on AWS, 2020, version 1.0. The registry
  page itself shows no DOI.
- **Required notice for modified data**, licence COP-DEM-GLO-30-F Art. 6(b): "produced using Copernicus WorldDEM-30 ©
  DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and
  ESA; all rights reserved".
- **Proposed:** cite 10.5270/ESA-c5d3d65, optionally with 10.60489/roda.mxyog0 for the AWS distribution, and add the
  Art. 6(b) notice. Drop 10.5069/G9028PQB.

## C3. Arcement & Schneider 1989 (`c2c3/RESULT.md`)

- **USGS Publications Warehouse** (`pubs-services/publication/wsp2339`):
  - authors "Arcement, George J." (rank 1) and "Schneider, Verne R." (rank 2), with no suffix and no ORCID;
  - title "Guide for selecting Manning's roughness coefficients for natural channels and flood plains";
  - 1989, Water Supply Paper 2339, DOI 10.3133/wsp2339, "v, 38 p.".
- **USGS suggested citation:** "Arcement, G.J., and Schneider, V.R., 1989, …". The printed title page reads "GEORGE J.
  ARCEMENT, JR., and VERNE R. SCHNEIDER".
- **Crossref** (10.3133/wsp2339) has no author field, which explains the CODE-16 mismatch.

## C4. Event facts and their sources (`c4/RESULT.md`; quotes re-checked in the saved files)

### (a) Mandra

- **Gauges.** No source documents gauge totals of 158–300 mm or > 30 mm/h at NOA Vilia. NOA's own 2017 report (IERSD
  annual report, p. 26) says "Στην περιοχή του συμβάντος δεν υπήρχαν εγκατεστημένα βροχόμετρα" [no rain gauges were
  installed in the event area]. It also says the radar core "πλησίασε τα 300 χιλ. σε χρονικό διάστημα 6 ωρών"
  [approached 300 mm within 6 hours].
- **The documented totals are radar**, from Varlas et al. 2019, *Remote Sens.* 11, 45, p. 17 of the PDF
  (10.3390/rs11010045). Over 14 Nov 12:00 – 15 Nov 12:00 UTC, XPOL observed "up to 300 mm accumulated precipitation in
  the core". The basin-average 24-h total was 194 mm over Soures and 153 mm over Agia Aikaterini. Basin-average rates
  reached 57 and 41 mm/h (02–06 UTC).
- **Vilia in the literature:**

  | Source | Vilia value |
  |---|---|
  | Stamou 2018, p. 5 of the PDF (citing NOA) | 35 mm |
  | NTUA slides | 33.6 mm |
  | FloodList | 67.2 mm in 24 h |

- **Radar agreement.** Varlas compared XPOL with distant gauges over 14 Nov – 26 Dec (CR > 0.9, BR 0.91), and NOA
  states that the radar agrees with GPM IMERG. No source compares a gauge with the radar at the storm peak.
- **Diakakis et al. 2019.** Only the abstract was readable (publisher 403). It gives "300 mm in 13 h in the core zone"
  and a peak unit discharge "between 9 and 10 m3/s/km2"; the draft has "> 3 (locally > 5)".
- **Lagouvardos et al. 2017** (online 2017-04-05) documents none of these facts.
- **Corrections for the draft:**
  - "158" matches no source; the documented figure is 153.
  - The catchment means of 153–194 mm and the 300 mm core value are radar values, not gauge values.
  - Remove "> 30 mm h⁻¹ from the NOA-Vilia gauge", or replace it with the radar basin-average rates.
  - Cite Varlas et al. 2019 and the NOA report in place of Lagouvardos et al. 2017.

### (b) Valencia

- **Turís, AEMET station 8337X.** AEMET's study of 23 Dec 2024 (`estudio_28_oct_4_nov_2024.pdf`, p. 30, Tabla 4.5)
  gives the maxima 184.6 mm (1 h), 620.6 mm (6 h) and 720.4 mm (12 h), and a 24-h total of **771.8 mm**. Page 31 adds
  that 710.8 mm fell in the pluviometric day (08–08 h), against 771.8 mm in the civil day.
- **Chiva, 491 mm in 8 h.** The only source is AEMET's post on X of 2024-10-30: "En Chiva, de hecho, se recogieron 491
  l/m² en solo ocho horas" [in Chiva, in fact, 491 l/m² fell in only eight hours].
  - AEMET's study gives **615.0 mm in 24 h** at Chiva-La Pailla (8334B), p. 30.
  - Sect. 2's "daily totals above 490 mm at Chiva" is wrong. Sect. 4's "about 491 mm in 8 h" matches the AEMET post.
- **Peer-reviewed source:** Calvo-Sancho et al. 2026, *Nat. Commun.* 17, 1492: "771.8 mm in 16 h" at Turís and 184.6 mm
  in 1 h. Rombeek et al. 2025 reports neither number.

## C5. EMS product citations (`c5/RESULT.md`, `c5/c5_ems_products.csv`: 56 packages read by the validator plus 5 content-only rows)

**Versions.** Every version used is the latest released version (API `version.number`, status F). For the legacy
activations, the activation page lists only the version used.

**Suggested citations:**

- EMSR122 (© European Union, 2015): Flood in Greece. Delineation Overview products (first delineation and
  Monit01–Monit03), AOI01–AOI04, v1–v2. Delivered 2015-04-02 to 2015-04-03.
  https://mapping.emergency.copernicus.eu/activations/EMSR122/
- EMSR257 (© European Union, 2017): Flood in Attika, Greece. Grading maps for AOI01 Mandra, AOI02 Nea Peramos and AOI03
  Lakka Kalogirou, versions v2, v2 and v1. Delivered 2017-11-22.
  https://mapping.emergency.copernicus.eu/activations/EMSR257/
- EMSR664 (© European Union, 2023): Flood in Italy. DEL monitoring products MONIT01–03 for AOI01 Forlì, and GRA products
  for AOI02–AOI08, v1–v2. Delivered 2023-05-19 to 2023-05-23.
  https://mapping.emergency.copernicus.eu/activations/EMSR664/
- EMSR692 (© European Union, 2024): Flood in Greece. DEL monitoring products MONIT01–05 for AOI01–AOI07, v2–v4.
  `version.deliveryTime` is 2024-04-24 for every version used (a single re-release batch; activation 2023-09-05).
  https://mapping.emergency.copernicus.eu/activations/EMSR692/
- EMSR773 (© European Union, 2024): Flood in Valencia Region, Spain. DEL monitoring products for AOI01 (MONIT01–04) and
  AOI06 (MONIT01), v1. Delivered 2024-11-03 to 2024-11-08.
  https://mapping.emergency.copernicus.eu/activations/EMSR773/
- EMSR933 (© European Union, 2026): Flood in Crete, Greece.
  - Scored: AOI03, first DEL and MONIT02, v1.
  - Area comparison only: AOI01, AOI04, AOI06 and AOI07, MONIT01, v1.
  - Delivered 2026-10-04 to 2026-10-08. https://mapping.emergency.copernicus.eu/activations/EMSR933/

**Legacy record.** EMSR122 and EMSR257 are not in the dashboard API (it returns 403, the same reply as for an unknown
code). The record used is the activation page; S3's Last-Modified date there is an upload date.

**Findings while checking (reported, nothing changed):**

- **EMSR664 truth depends on the platform.** The Windows glob is case-insensitive, so
  `*DEL_MONIT*observedEventA*.shp` also matches the three AOI01 `previousObservedEventA` layers (MONIT01–03). The
  MONIT01 layer equals the first delineation. On a case-sensitive file system the truth has 10 files, not 13.
  - The observed area falls from 567.9 to 461.0 km².
  - Strict CSI at h > 0.10 m falls from **0.253 (the record) to 0.210**; HR goes from 0.852 to 0.861 and B from 3.22
    to 3.96 (`code17/c5_emilia_case_impact.json`).
  - The other five events are unaffected (`code17/c5_truth_glob_case.json`).
- **EMSR773 truth depends on what was downloaded.** It is AOI01 MONIT01–04 plus AOI06 MONIT01, because older download
  URLs returned 404. The API now lists 38 released products, 33 of them unused; the agent counts 23 overlapping the
  domain, including grading AOIs. A fresh run of `download_ems.py` would change the truth.
- **EMSR933.** `exclude_not_analysed` and `truth_cutoff_snapshot_utc` are set in the YAMLs, but no scoring code reads
  them.
  - The tier-1 score is unaffected: AOI03 has 0 km² not analysed.
  - The tier-2 universes of AOI01 and AOI07 include 45.3 and 30.0 km² of not-analysed area (STAGE5_TRUTH_FREEZE.md).

## C6. Any-touched against centre burning of the observed polygons (`code17/c6_alltouched_inflation.json`)

**Method.** Observed-wet cells are counted inside the evaluation universe, with polygons burned any-touched (the
validator's rule) and by cell centre (`all_touched=False`). The polygons, AOIs, grid and exclusion mask are those of
each run of record. The any-touched raster is asserted to equal `validate_event_v2._rasterise_polys_to_grid`.

**Check against the earlier figures.** On the release universe (published models, AOI ∩ active) this gives Pineios
+17.7 %, Strymonas +52.2 % and Mandra +81.8 %. The earlier text gave +18 / +52 / +82 %.

| event (run of record) | v1.4 universe km² | observed, any-touched km² | observed, centre km² | inflation | release universe |
|---|---|---|---|---|---|
| Pineios (`pineios_enhanced_v142`) | 4506.7 | 1507.7 | 1287.7 | **+17.1 %** | +17.7 % |
| Strymonas (`strymonas_enhanced_postD6_v142`) | 1196.2 | 104.2 | 69.2 | **+50.7 %** | +52.2 % |
| Mandra (`mandra_enhanced`) | 86.9 | 8.82 | 4.83 | **+82.8 %** | +81.8 % |
| Valencia (`valencia_enhanced_164_v142`) | 2709.5 | 195.8 | 165.2 | **+18.6 %** | +20.3 % |
| Emilia-Romagna (`emilia_enhanced_8aoi_v142`) | 3148.0 | 567.9 | 318.8 | **+78.2 %** | +80.9 % |
| Crete, tier-1 block AOI03 Tzermiado (`crete_canonical_r2on`) | 176.9 | 11.26 | 4.33 | **+160.0 %** | — |

**Crete tier-2 AOIs** (area comparison only). The traces are a few cells wide, so any-touched burning multiplies them:

| AOI | any-touched km² | centre km² | inflation |
|---|---|---|---|
| AOI01 | 1.78 | 0.22 | +709 % |
| AOI04 | 0.41 | 0.02 | +1950 % |
| AOI06 | 0.23 | 0.06 | +283 % |
| AOI07 | 0.65 | 0.02 | +3150 % |

**Vector areas, for reference.** Mandra 4.96 km², Valencia 173.5 km², Tzermiado 4.44 km². Above 2,000 polygons the
vector union is not computed (Pineios, Strymonas, Emilia).

**Emilia** includes the three `previousObservedEventA` layers, as on the run machine (see C5).
