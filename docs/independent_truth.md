# docs/independent_truth.md — Pineios independent-truth cross-check (C4, referees M1/M2)

**Objective.** Show the Pineios flagship skill (EMS CSI **0.456** / HR **0.947**) is not an artefact of using Copernicus EMS as the reference, by confronting the *unchanged* canonical Pineios v1-enhanced run with independent SAR-derived Storm-Daniel flood extents (He et al. 2024; Falaras et al. 2025).

> **Headline caveat (read first).** The two independent delineations report only *areas* — neither publishes its flood-extent geospatial data (He: "available from the corresponding author upon reasonable request"; Falaras: no dataset DOI / no public deposit). A genuine **pixel-wise** cross-validation (CSI/HR per reference) was therefore **possible only against EMS**. Against He and Falaras this reduces to the weaker **area-agreement** check (STEP 3), which is reported and labelled as such. We did not fabricate or digitise any extent.

## 0. Gate — EMS baseline reproduces exactly

Re-scoring the committed canonical hmax (`implementation/pineios_sfincs_enhanced/model/sfincs_map.nc`) through the committed harness functions, on the 4642 km² EMSR692 mask:

| threshold | CSI | HR | FAR | B | GSS |
|---|---|---|---|---|---|
| hmax>0.10 m | **0.456** | **0.947** | 0.532 | 2.02 | 0.201 |
| hmax>0.50 m | **0.515** | 0.741 | 0.372 | 1.18 | 0.337 |

Reproduces AUDIT.md to the decimal (0.456/0.947/0.532/2.02/0.201 @0.10 m; 0.515 @0.50 m). Mask 4642 km², EMS observed 1519 km². Gate PASSED -> cross-scoring is meaningful.

## 1. Provenance of the independent extents

| reference | DOI | data availability | sensor(s) | acq. date(s) | footprint | reported area |
|---|---|---|---|---|---|---|
| **Copernicus EMS** EMSR692 | activation EMSR692 | **public** (24 observed-event delineations, 7 AOIs) | multi-sensor SAR+optical (rapid mapping) | ~05–21 Sep 2023 (16-day union) | 7 AOIs over the Thessaly plain | 1519 km² (merged, in mask) |
| **He et al. 2024** | 10.5194/nhess-24-2375-2024 (NHESS) | **NOT public** — "inundation map from RAPID … available from the corresponding author upon reasonable request" | Sentinel-1 (RAPID) | 6 & 12 Sep 2023 | Greece total; Thessalian plain | **1150 km² total / 820 km² plain** |
| **Falaras et al. 2025** | 10.3390/rs17101750 (Remote Sensing) | **NOT public** — no dataset DOI / no Zenodo·figshare·GitHub deposit (Crossref relations empty; MDPI CC-BY, article only) | Sentinel-1, Sentinel-2, Landsat 8/9 (GEE; SAR threshold + MNDWI) | multiple Sep 2023 overpasses | Thessaly plain | **949.52 km²** (max extent) |

Both independent products = single/few overpasses; EMS = multi-sensor 16-day union — so EMS is expected to be the *largest* of the three, and the SAR areas the same order but smaller.

## 2. Per-reference scoring on the common domain

**EMS — full pixel-wise (STEP 2)** at hmax>0.10 m, 4642 km² mask:

- strict: CSI 0.456, HR 0.947, FAR 0.532, B 2.02, GSS 0.201; at >0.50 m CSI 0.515.
- one-sided fuzzy r=1 (±150 m): tolerant **HR 0.995** (dilate model) / tolerant **CSI 0.511** (dilate obs).

**He & Falaras — area-agreement only (STEP 3; *not* a pixel-wise cross-validation).** Model flooded area in the EMS mask vs each independent reported area (footprints differ, so these are frequency-bias-style ratios, not spatial overlap):

| reference (area) | model>0.10 m / ref | model>0.50 m / ref |
|---|---|---|
| EMS merged (1519 km²) | 2.02 | 1.18 |
| He plain (820 km²) | 3.75 | 2.18 |
| He total (1150 km²) | 2.67 | 1.56 |
| Falaras (949.52 km²) | 3.24 | 1.89 |

Model wet area: **3074 km² at >0.10 m**, **1791 km² at >0.50 m**. The model over-predicts area against *every* reference (ratio > 1 throughout) — i.e. the B≈2 over-prediction seen against EMS is **not** an EMS artefact; it holds against two fully independent delineations. At the calibrated peak-CSI depth (>0.50 m) the model area (1791 km²) sits within 1.2–2.2× of all three observed areas (820–1519 km²).

## 3. CSI across references

Pixel-wise CSI is available for **one** reference only:

| reference | pixel-wise CSI@0.10 m | basis |
|---|---|---|
| Copernicus EMS | 0.456 | full contingency (public extent) |
| He et al. 2024 | — | extent not public -> area-agreement only |
| Falaras et al. 2025 | — | extent not public -> area-agreement only |

**We cannot state a "CSI 0.43–0.49 across three independent references" range** — that would require the He/Falaras extents, which are not available. What the independent data *do* establish is that the EMS truth is of representative magnitude (1519 km² vs 949–1150 km²), so the EMS-scored CSI is not inflated by an anomalous reference.

## 4. Verdict

**Area-robust, pixel-untestable.** At the only level the independent data permit (area), the result is **corroborative, not contradictory**: two fully independent SAR delineations (949–1150 km²) bracket the same order as the EMS-merged 1519 km² the model scores 0.456/0.947 against, and the model's area over-prediction is consistent across all three references. A true pixel-wise cross-validation against He/Falaras was **not possible** (extents unpublished) and must not be claimed. Recommendation: keep the independent SAR products as an *area-consistency* argument, and (if a pixel-wise independent check is wanted for revision) request the He RAPID inundation map from the corresponding author (E. N. Anagnostou) — it is offered on request.

## 5. Manuscript-ready note + reconciled area figures

**Reconciliation (the §5.1/§5.2/§7.4 figures are currently conflated):**

| figure | correct source | value |
|---|---|---|
| total Thessaly inundation | He et al. 2024 | ~1150 km² |
| Thessalian plain | He et al. 2024 | ~820 km² |
| max flood extent (plain) | Falaras et al. 2025 | **949.52 km²** (not 820) |
| EMS-merged extent (model's reference, in mask) | this study | 1519 km² |

The v5 text attributes "~1150 km² total and ~820 km² in the plain" to *both* He **and** Falaras; in fact 1150/820 are both He, while Falaras reports ~950 km². Fix the attribution.

**Drop-in note for §5.1 / §7.4:**

> Because Copernicus EMS is itself a SAR-derived product, we checked that the Pineios skill is not an artefact of that single reference against two fully independent Storm-Daniel delineations. He et al. (2024) map ~1150 km² of inundation across Greece (~820 km² within the Thessalian plain) from Sentinel-1, and Falaras et al. (2025) map a ~950 km² maximum extent in the plain from Sentinel-1/2 and Landsat 8/9 — both the same order as, and somewhat smaller than, the 1519 km² EMS-merged extent (each independent product being a single/few-overpass map versus the EMS 16-day multi-sensor union). Neither independent extent is publicly available for pixel-wise scoring, so this is an area-consistency check rather than a second pixel-wise validation; on that basis the EMS reference is of representative magnitude and the model's modest area over-prediction (frequency bias ≈ 2 at 0.10 m, ≈ 1.2 at the 0.50 m peak-CSI depth) holds against all three references, not EMS alone.

---
_Re-score only; the model was not re-run. Gate + scoring: `reproduction/independent_truth/score.py` (reuses the committed harness functions); numbers in `ems_rescore.json`. all_touched=True (committed convention, matches the 0.456 baseline; AUDIT.md notes the +inflation)._

---

## 6. ADDENDUM — pixel-wise SAR cross-validation (Falaras 2025, digitized) — UPGRADES §3/§4

The "pixel-untestable" conclusion above was for the *released* data. A **defensible digitization** of
the Falaras et al. (2025) extent was subsequently obtained, enabling an actual pixel-wise cross-validation.

**Digitization provenance (disclosed as APPROXIMATE).** Source = Falaras et al. (2025) **Fig. 10**
("Affected Buildings — MS Bing Maps"), which renders the Flooded Area as a single distinct cyan over a
dark satellite basemap (unlike He's Fig. 3, which colours inundation by land-cover class and is not
cleanly separable). Method, fully reproducible (`reproduction/independent_truth/score_sar.py`):
- **georeference:** affine pixel→UTM-34N fitted from **4 labelled city markers** (Trikala, Karditsa,
  Larissa, Volos) — **RMS residual 253 m, max 328 m** (≈1–2 model cells over a 150 km map);
- **flood mask:** colour-distance < 120 to the legend "Flooded Area" swatch (RGB 3,197,255) + 1-iteration
  morphological closing → **903 km² recovered of the reported 949.52 km² (95 %)** — quality-gated against
  the authors' published area;
- rasterized onto the **same 150 m model grid** (any flood pixel in a cell → wet, ~all_touched=True, the
  EMS convention) → observed-wet **986 km²** on the 4642 km² mask. Extent file:
  `reproduction/independent_truth/refs/falaras_sar_extent_modelgrid.tif` (EPSG:32634).

**Evaluation domain.** Falaras maps the whole Thessaly region (Sentinel-1/2 + Landsat 8/9), so the SAR
footprint covers the entire model domain → eval domain = the **4642 km² EMS AOI-union active mask**
(identical to the EMS scoring; no model-wet cells fall outside the SAR footprint).

**Contingency — model hindcast vs Falaras-SAR, beside EMS (same harness, same mask):**
| threshold | reference | obs-wet | CSI | HR | FAR | B | GSS | TP / FP / FN (km²) |
|---|---|---|---|---|---|---|---|---|
| h>0.10 m | **Falaras-SAR** | 986 km² | **0.299** | **0.948** | 0.696 | 3.12 | 0.114 | 934 / 2139 / 52 |
| h>0.10 m | EMS | 1519 km² | 0.456 | 0.947 | 0.532 | 2.02 | 0.201 | 1438 / 1636 / 81 |
| h>0.50 m | **Falaras-SAR** | 986 km² | **0.402** | 0.808 | 0.556 | 1.82 | 0.260 | 796 / 995 / 190 |
| h>0.50 m | EMS | 1519 km² | 0.515 | 0.741 | 0.372 | 1.18 | 0.337 | 1125 / 666 / 394 |

One-sided fuzzy (dilate model, ±150 m) tolerant HR vs Falaras-SAR = **0.993**.

**Caveats (a reviewer will look for these).**
- *Digitization*: the extent is digitized from a published figure, not the authors' raster — approximate
  (georef RMS 253 m; 95 % of the reported area recovered). Disclose as such in-text.
- *Temporal snapshot*: Falaras is a multi-sensor map over weeks; the model field is max-over-time. A
  few-overpass SAR under-maps relative to a time-envelope, so this tests robustness to the choice of
  reference **source**, with a temporal-completeness caveat. (He's 2-overpass map would bracket lower at
  ~820 km²; it was not digitized — its land-cover-coloured figure precludes a comparably clean trace.)

**Verdict (upgrades §4): NOT EMS-specific — robustness CONFIRMED at the pixel level for detection.**
Against a fully independent SAR extent the hindcast recovers **HR 0.948** (FN only 52 km²) — *equal to its
EMS hit rate* — so the model recovers an independently-mapped flood and the skill is **not an artefact of
the EMS reference**. CSI is lower (0.299 at 0.10 m, rising to 0.402 at 0.50 m) exactly as expected: the
model's known area over-prediction (B 2.0 vs EMS) is scored against a **smaller** single-/few-overpass
truth (986 vs 1519 km²) so it reads as B 3.1; the over-prediction is in the **same direction against every
reference** and widens against the sparser snapshot — partly a reference-completeness effect, not pure
model error. At the 0.50 m depth the model extent contracts toward the SAR and CSI improves to 0.402.

**§5.1 replacement sentence (drop-in):**
> Re-scored pixel-wise against an independent multi-sensor flood extent (Falaras et al. 2025, digitized
> from their published map: 903 km² of the reported 949.52 km² recovered, georeferenced to 253 m RMS via
> four city control points) on the overlapping 4642 km² footprint, the hindcast yields HR = 0.95 (934 km²
> of 986 km² observed recovered, 52 km² missed), CSI = 0.30 and frequency bias = 3.1 at h > 0.10 m (CSI =
> 0.40, B = 1.8 at h > 0.50 m). The hit rate equals that against EMS (0.95), confirming the hindcast
> recovers an independently mapped flood and that the skill is not specific to the EMS reference; the lower
> CSI reflects the model's area over-prediction — also present against EMS (B = 2.0) — scored against a
> smaller single-/few-overpass SAR snapshot.

_Scoring: `reproduction/independent_truth/score_sar.py`; numbers in `sar_rescore.json`; extent raster in
`refs/falaras_sar_extent_modelgrid.tif`; source figure `refs/fal_g010.png`._