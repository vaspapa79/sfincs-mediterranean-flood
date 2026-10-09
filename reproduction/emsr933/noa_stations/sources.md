# Sources — NOA/meteo.gr rainfall record for Crete, storm of 30 Sep – 5 Oct 2026 (EMSR933)

Research performed 2026-10-09 between 13:27 UTC and 14:02 UTC from a Windows machine (curl.exe for raw files, WebFetch for rendered pages,
WebSearch for discovery). Every number in the CSVs comes from a page/file listed here. Raw copies of the station TXT/HTML files, the
meteo.gr terms page, the NOA map images and the curl download log (with exact UTC time and HTTP status per request) are in `raw/`.

Time-stamp conventions: curl downloads carry exact UTC times (from `raw/_download_log.csv`); WebFetch calls were issued in batches and
carry the batch window ("approx.").

## 1. Station data (penteli.meteo.gr) — daily values in `stations_daily.csv`

Day convention: the daily RAIN column of the station's "MONTHLY CLIMATOLOGICAL SUMMARY" (NOAAMO.TXT = current month, NOAAPRMO.TXT =
previous month) is the logger's local calendar day. Station pages show "Latest Values / Τελευταίες Τιμές 09/10/2026 16:20–16:30" while
the fetch was made at 13:27–13:39 UTC, i.e. the station clocks run on Greek local time (EEST, UTC+3 in early October 2026). A local day
therefore spans 21:00 UTC (previous day) to 21:00 UTC. Coordinates in the TXT headers are rounded to whole arc-minutes (0.1°) by the
logger software; they are NOT precise station positions. Elevations are as printed in the TXT header.

Station pages (all HTTP 200 unless noted; exact times in `raw/_download_log.csv`):

| slug | page URL | station page (UTC) | NOAAMO.TXT (UTC) | NOAAPRMO.TXT (UTC) |
|---|---|---|---|---|
| anogeia | https://penteli.meteo.gr/stations/anogeia/ | 13:30:17Z (also 13:39:19Z) | 13:30:17Z / 13:39:19Z | 13:30:17Z / 13:39:19Z |
| asigonia | https://penteli.meteo.gr/stations/asigonia/ | 13:39:20Z | 13:39:20Z | 13:39:20Z |
| askyfou | https://penteli.meteo.gr/stations/askyfou/ | 13:39:20Z | 13:39:20Z | 13:39:20Z |
| fourfouras | https://penteli.meteo.gr/stations/fourfouras/ | 13:39:21Z | 13:39:21Z | 13:39:21Z |
| ierapetra | https://penteli.meteo.gr/stations/ierapetra/ | 13:39:22Z | 13:39:22Z | 13:39:22Z |
| kampoi | https://penteli.meteo.gr/stations/kampoi/ | 13:39:22Z | 13:39:22Z | 13:39:22Z |
| kandanos | https://penteli.meteo.gr/stations/kandanos/ | 13:39:21Z | 13:39:21Z | 13:39:21Z |
| potamoi | https://penteli.meteo.gr/stations/potamoi/ | 13:39:21Z | 13:39:22Z | 13:39:22Z |
| samaria (= Ξυλόσκαλο / Xyloskalo, Omalos) | https://penteli.meteo.gr/stations/samaria/ | 13:39:20Z | 13:39:20Z | 13:39:20Z |
| samariagorge (= Σαμαριά Φαράγγι) | https://penteli.meteo.gr/stations/samariagorge/ | 13:39:20Z | 13:39:20Z | 13:39:21Z |
| sebronas (Σέμπρωνας) | https://penteli.meteo.gr/stations/sebronas/ | 13:39:21Z | 13:39:21Z | 13:39:21Z |
| sitia | https://penteli.meteo.gr/stations/sitia/ | 13:39:22Z | 13:39:22Z | 13:39:22Z |
| tzermiado | https://penteli.meteo.gr/stations/tzermiado/ | 13:39:19Z | 13:39:19Z | 13:39:20Z |
| spili | https://penteli.meteo.gr/stations/spili/ | 13:39:23Z (200) | 13:39:23Z — curl exit 28 (timeout) | 13:39:44Z — timeout |

Each station page also links NOAAYR.TXT / NOAAPRYR.TXT (yearly summaries, not fetched) and https://meteosearch.meteo.gr/ (historical
archive, login required). No hourly or 10-minute series is exposed publicly on the station pages; sub-daily data would need the
meteosearch login (its front page states a limit of 30 measurement files per day / 720 per user).

Station-index attempts:
- https://meteo.gr/stations/ — 2026-10-09T13:28Z — HTTP 301 → https://penteli.meteo.gr/stations/
- https://penteli.meteo.gr/stations/ — 13:30:17Z — HTTP 200 but an 809-byte shell (`<div class="content"></div>`, script only resizes columns): **no public station list**.
- https://www.meteo.gr/observationsFull.cfm and /observations.cfm — 13:33:47Z — HTTP 200; forecast city lists only (cf.cfm?city_id=…), no station links.
- https://www.meteo.gr/crete/ — 13:33:48Z — HTTP 200; embeds an iframe `//stratus.meteo.noa.gr/meteo_data/crete` and lists six Crete stations with webcams: ΗΡΑΚΛΕΙΟ ΑΝΑΤΟΛΙΚΑ (heraclioneast), ΠΑΛΑΙΟΧΩΡΑ ΧΑΝΙΩΝ (paleochora), ΠΥΡΑΘΙ ΗΡΑΚΛΕΙΟΥ (pyrathi), ΡΕΘΥΜΝΟ (rethymno), ΣΤΑΥΡΑΚΙΑ ΗΡΑΚΛΕΙΟΥ (stavrakia), ΧΑΝΙΑ - ΕΝΕΤΙΚΟ ΛΙΜΑΝΙ (chania).
- https://stratus.meteo.noa.gr/meteo_data/crete — 13:36:38Z — curl exit 35 (CRYPT_E_REVOCATION_OFFLINE); retry with --ssl-no-revoke returned a Leaflet shell (data loaded by `api_meteo_data.js`, not parsed before the server stopped answering).
- https://meteosearch.meteo.gr/ — 13:35:28Z — HTTP 200, login page only.
- https://www.meteo.gr/meteonav/help/stations.html — ~13:33Z — help text for the MeteoNav live-station layer; no list.
- HEAD probes of guessed slugs at 13:37:01Z: HTTP 200 for tzermiado, askyfou, asigonia, samaria, samariagorge, sebronas, kandanos, fourfouras, potamoi, ierapetra, sitia, kampoi, spili, neapoli, sfakia, kissamos, plakias, souda, vrysses, alikianos, chania, heraclion, perama, melampes, anogeia; HTTP 404 for xyloskalo, omalos, agiosnikolaos, zaros, archanes, viannos, kastelli, heraklion/irakleio, schinokapsala, kakopetros and ~70 other variants. A second probe round and the data download for the remaining 200-slugs failed from ~13:39:44Z on: penteli.meteo.gr stopped accepting connections (curl exit 28, "Could not connect to server" after 21 s) — most likely rate limiting triggered by the rapid probes. Those stations are listed in `stations_meta.csv` with explicit "NOT retrieved" notes.

## 2. NOA / meteo.gr articles (official publications)

Index: https://www.meteo.gr/articles_all.cfm — ~13:30Z — lists entryIDs 4334–4343 for 30/09–07/10/2026.

- https://www.meteo.gr/article_view.cfm?entryID=4335 — ~13:31Z — "Μεγάλα ύψη βροχής στην Κρήτη το διήμερο Τετάρτης και Πέμπτης – Στα 361 mm το ύψος βροχής στα Ανώγεια Ρεθύμνου έως το μεσημέρι της Πέμπτης", Πέμπτη 1/10/2026 14:00 (I. Koletsis, G. Kyros, K. Lagouvardos). Map image: https://www.meteo.gr/UploadedFiles/articlePhotos/OCT26/2days_rain_crete_oct2026.jpg (downloaded 13:35:28Z; `raw/img_2days_rain_crete_oct2026.jpg`).
- https://www.meteo.gr/article_view.cfm?entryID=4336 — ~13:31Z and ~13:33Z — "Νέος γύρος έντονων βροχοπτώσεων στην Κρήτη - Επεισόδιο βροχόπτωσης κατηγορίας 4", Παρασκευή 2/10/2026 10:00. Quote: "Το επεισόδιο βροχόπτωσης για το Σάββατο 03/10, κατατάσσεται στην Κατηγορία 4 (Πολύ σημαντική)" (Rainfall Episode Index of the METEO unit). Forecast only, no totals.
- https://www.meteo.gr/article_view.cfm?entryID=4338 — ~13:31Z — "Μεγάλα ύψη βροχών στην Κρήτη το διήμερο Παρασκευής και Σαββάτου – Στα 420 mm το ύψος βροχής στο Ξυλόσκαλο Χανίων (Update)", Σάββατο 3/10/2026 19:00 (earlier version 10:45: 318 mm). Map: https://www.meteo.gr/UploadedFiles/articlePhotos/OCT26/udpate_creta_2daysrain_03102026_meteogr_noa.jpg (13:35:29Z).
- https://www.meteo.gr/article_view.cfm?entryID=4339 — ~13:31Z — "Μεγάλα ύψη βροχών στην Κρήτη για 5η συνεχόμενη ημέρα – Στα 91 mm το ύψος βροχής στο Ξυλόσκαλο Χανίων", Κυριακή 4/10/2026 16:00. Map: https://www.meteo.gr/UploadedFiles/articlePhotos/OCT26/creta_rain_041026.jpg (13:35:29Z).
- https://www.meteo.gr/article_view.cfm?entryID=4340 — ~13:31Z — "Από τον Ατλαντικό στο Αιγαίο: Πώς «μπλόκαρε» ο καιρός πάνω από την Ευρώπη", page dated Δευτέρα 5/10/2026 10:45 (index lists 04/10) (S. Ntafis, G. Kyros, K. Lagouvardos). Charts: https://www.meteo.gr/UploadedFiles/articlePhotos/OCT26/z500_explainer_20261001_hires_crete_meteogr_noa.jpg (synoptic) and https://www.meteo.gr/UploadedFiles/articlePhotos/OCT26/crete_rain_3009_0410_2026_meteogr_noa.jpg (5-day totals, 70 stations) — both downloaded 13:35:29Z.
- https://www.meteo.gr/article_view.cfm?entryID=4341 — ~13:31Z — "Η σύγκριση της πρόσφατης κακοκαιρίας στην Κρήτη με τις μεγάλες κακοκαιρίες του Φεβρουαρίου του 2019 (Χιόνη και Ωκεανίδα)", Τρίτη 6/10/2026 08:00 (K. Lagouvardos, G. Kyros, C. Petropoulos, S. Ntafis). 39 common stations; "η κακοκαιρία του 2026 είναι η σημαντικότερη που έχει σημειωθεί στην Κρήτη τουλάχιστον τα τελευταία 25 χρόνια" (except Chania prefecture, where the 2019 storms gave more). Charts crete_storms_maps.jpg / crete_storms_difference.jpg downloaded 13:35:29Z (not transcribed).
- https://www.meteo.gr/article_view.cfm?entryID=4342 — ~13:31Z — "Φερτές ύλες και τα πρώτα χιόνια στην Κρήτη από τον δορυφόρο Sentinel-2", Τρίτη 6/10/2026 21:00: "...ύψη βροχής, τα οποία ξεπέρασαν τα 800 mm σε περιοχές των Λευκών Ορέων και του Ψηλορείτη".

### 2a. Official meteorological characterisation (verbatim, article 4340)

"Η κακοκαιρία των τελευταίων ημερών στην Κρήτη ήταν το αποτέλεσμα μιας ασυνήθιστης για την εποχή ατμοσφαιρικής κυκλοφορίας, η οποία επηρέασε μεγάλο μέρος της Ευρώπης και της Μεσογείου."

"Η ατμοσφαιρική κυκλοφορία «μπλόκαρε», οι ψυχρές αέριες μάζες κατευθύνθηκαν από τη βορειοανατολική Ευρώπη προς τα Βαλκάνια και το Αιγαίο και οι βροχοπτώσεις μετατοπίστηκαν προς την ανατολική και νότια Ελλάδα."

"Στα τέλη Σεπτεμβρίου σημειώθηκε «εκρηκτική κυκλογένεση» στον Βόρειο Ατλαντικό, με πολύ γρήγορη ενίσχυση ενός βαρομετρικού χαμηλού. Η ταχεία αυτή εξέλιξη ενίσχυσε τη μεταφορά θερμότερου αέρα προς βορρά, στην ανατολική πλευρά του συστήματος (Σκανδιναβία) και συνέβαλε στην περαιτέρω ενίσχυση του αντικυκλώνα πάνω από την Βορειανατολική Ευρώπη."

"Το σημαντικότερο όμως ήταν η διάρκεια. Η διαταραχή αποκόπηκε σταδιακά από το κύριο ρεύμα της ατμοσφαιρικής κυκλοφορίας και σχημάτισε ένα αποκομμένο χαμηλό πάνω από τη Νοτιοανατολική Ευρώπη και την Ανατολική Μεσόγειο. Όταν συμβαίνει αυτό, ένα χαμηλό μπορεί να παραμείνει σχεδόν στάσιμο για αρκετές ημέρες, καθώς δεν μετακινείται εύκολα προς τα ανατολικά από τους ισχυρότερους ανέμους της ανώτερης ατμόσφαιρας."

"Στην περίπτωση αυτή, το αποκομμένο χαμηλό παρέμεινε για πολλές ημέρες στην ευρύτερη περιοχή της Νοτιοανατολικής Μεσογείου, ενώ οι υψηλές πιέσεις βορειότερα διατήρησαν μεγάλη διαφορά πίεσης και επίμονο βόρειο έως βορειοανατολικό ρεύμα πάνω από το Αιγαίο. Έτσι συνεχίστηκε η μεταφορά ψυχρών αερίων μαζών προς την Ελλάδα και ταυτόχρονα η τροφοδότηση της Κρήτης με υγρές αέριες μάζες."

"Καθώς η ψυχρή αέρια μάζα περνούσε πάνω από το θερμό ακόμη Αιγαίο, εμπλουτιζόταν με υγρασία και γινόταν ολοένα πιο ασταθής. Η παρουσία του αποκομμένου χαμηλού ευνοούσε παράλληλα την ανοδική κίνηση του αέρα, ενώ όταν η βόρεια ροή έφθανε στην Κρήτη, η ανύψωσή της πάνω από τους ορεινούς όγκους του νησιού ενίσχυε ακόμη περισσότερο τις βροχοπτώσεις."

"Τα συνολικά ύψη βροχής του πενθημέρου Τετάρτης 30/09-Κυριακής 04/10, παρουσιάζονται στο Χάρτη 2, όπως δημιουργήθηκε από τις μετρήσεις 70 μετεωρολογικών σταθμών της μονάδας ΜΕΤΕΟ του Εθνικού Αστεροσκοπείου Αθηνών στο νησί. Άνω από 840 χιλιοστά βροχής έπεσαν στη Σαμαριά (θέση Ξυλόσκαλο) και πάνω από 640 χιλιοστά στα Ανώγεια Ρεθύμνου. Στο οροπέδιο Λασιθίου (Τζερμιάδο) το συνολικό ύψος βροχής ήταν 448 χιλιοστά."

Event duration per the NOA articles: rain began Wednesday 30/09, first peak to midday Thursday 01/10 (art. 4335), lull Fri midday, second round from Friday afternoon 02/10 through Sunday 04/10 (art. 4336, 4338, 4339) — "5η συνεχόμενη ημέρα" on 04/10.

## 3. Press articles used (secondary; carry the "72-h" values the task asked to verify)

- https://www.tanea.gr/2026/10/03/greece/kriti-kakokairia-pou-thymizei-daniel-epesan-eos-700-xiliosta-vroxis-se-72-ores/ — ~13:34Z — Ta Nea 03/10/2026 20:35; the sentence "Στο Ξυλόσκαλο καταγράφηκαν σχεδόν 700 χιλιοστά βροχής, στα Ανώγεια περίπου 600 χιλιοστά, στο Φαράγγι 525 χιλιοστά, στο Τζερμιάδο 415 χιλιοστά, στο Ασκύφου 412 χιλιοστά και στην Ασή Γωνιά 355 χιλιοστά" is attributed to meteorologist Κλέαρχος Μαρουσάκης, not to NOA.
- https://www.onlarissa.gr/2026/10/03/ta-asyllipta-noumera-tis-kakokairias-stin-kriti-ti-kategrapse-i-politiki-prostasia-tis-perifereias-thessalias-eos-619-chiliosta-vrochis/ — ~13:34Z — 03/10/2026 23:43; Thessaly Region civil-protection compilation of meteo.gr/NOA data to midday 03/10 (73 stations): Xyloskalo 619.4, Anogeia 538.8, Farangi 468.8, Tzermiado 399, Potamoi 394.8, Askyfou 394.6, Asi Gonia 329, Sempronas 316.8.
- https://www.tanea.gr/2026/10/05/greece/kriti-i-pagida-tis-atmosfairas-pou-efere-akraies-vroxes-pano-apo-840-xiliosta-sti-samaria/ — ~13:30Z — 05/10/2026 12:20; reproduces article 4340 (840/640/448, cut-off low, N–NE flow, orographic lift).
- https://www.larissanet.gr/2026/10/01/meteo-eaa-megala-ypsi-vrochis-stin-kriti-pano-apo-360-chiliosta-sta-anogeia-rethymnou/ — ~13:30Z — 01/10/2026 22:10; "361,4 mm από την Τετάρτη 30/09 έως το μεσημέρι της Πέμπτης 01/10".
- https://www.tanea.gr/2026/10/03/greece/kakokairia-stin-kriti-318-tonoi-nerou-se-ena-stremma-pou-katagrafikan-ta-megalytera-ypsi-vroxis — ~13:30Z — 03/10/2026 13:58; 318 mm Xyloskalo (as of 10:20).
- https://www.cretalive.gr/kriti/akraia-ypsi-brohis-stin-kriti-pos-exelissetai-i-kakokairia and https://www.cretalive.gr/kriti/epnixe-tin-kriti-i-kakokairia-3614-hiliosta-brohis-sta-anogeia — ~13:34Z / ~13:36Z — 01/10/2026; same 8 values as the NOA map of 30/09–01/10 (361.4, 237, 197, 189, 178, 167, 137, 130).
- https://hania.news/2026/10/03/kriti-sta-420-chiliosta-i-vrochi-sto-xyloskalo-se-red-code-o-michanismos-politikis-prostasias — ~13:36Z — 03/10/2026; "420 χιλιοστά ... μέσα σε 42 ώρες ... έως τις 18:50" + same 8 values as the NOA 02–03/10 map.
- https://agonaskritis.gr/... (URL-encoded Greek slug, see published_totals.csv is not needed; same 02–03/10 values) — ~13:34Z.
- https://creta24.gr/ischyres-vrochoptoseis-stin-kriti-se-poia-periochi-xeperasan-ta-100-chiliosta/ — ~13:36Z — 01/10/2026 08:30; early running totals (Tzermiado 103, Kampoi Keramion 90, Asi Gonia 87, Stavrakia 79, Askyfou 75, Xyloskalo 70, Spili 66, Farangi 59).
- https://www.enikos.gr/society/kakokairia-stin-kriti-dokimazetai-to-nisi-gia-5i-synechomeni-imera-sta-91-chiliosta-to-ypsos-vrochis-sto-xyloskalo-chanion/2654610/ — ~13:36Z — 04/10/2026 19:35; 91 mm Xyloskalo to 15:10.
- https://meteo24news.gr/greece/kriti-440-mm-vroxis-xyloskalo-chania/ — ~13:34Z — 03/10/2026 10:55; claims 440 mm (inconsistent with NOA 318/420 — not used).
- https://www.euronews.com/2026/10/05/crete-plateau-deluged-with-440mm-of-rain-in-two-days — ~13:30Z — 05/10/2026; "about 440 mm in two days" (Lasithi plateau), "around 470 mm" four-day regional average — unverifiable against NOA.
- https://cretaone.gr/meteo-i-kakokairia-toy-2026-stin-kriti-xeperase-ta-istorika-epipeda-vrochoptosis-tis-eikosipentaetias/ — ~13:30Z — 07/10/2026; reproduces article 4341 (no numbers).
- https://www.in.gr/2026/10/06/greece/kriti-fertes-yles-kai-ta-prota-xionia-to-apotypoma-tis-prosfatis-kakokairias/ — ~13:33Z — 06/10/2026 23:26; reproduces 4342 (>800 mm) and 4340 (840/640/448).
- https://www.neakriti.gr/kairos/2203871_allazei-entelos-o-kairos-stin-kriti-ti-fernei-i-triti-meta-apo-pente-imeres-akraion — ~13:33Z — 06/10/2026 06:30; repeats 840/640/448.
- https://www.argophilia.com/news/crete-rainfall-anogeia/252118/ — ~13:30Z — HTTP 429 Too Many Requests (not retrieved).
- WebSearch queries used (~13:28Z, ~13:32Z, ~13:33Z): "Ξυλόσκαλο 840 Ανώγεια 640 Τζερμιάδο βροχή meteo"; "Crete floods October 2026 rainfall mm Xyloskalo Anogeia National Observatory of Athens meteo.gr"; "meteo.gr Κρήτη κακοκαιρία Οκτώβριος 2026 ύψη βροχής σταθμοί Εθνικό Αστεροσκοπείο Αθηνών"; "\"Ασκύφου\" \"Ασή Γωνιά\" Ξυλόσκαλο Τζερμιάδο χιλιοστά βροχής Κρήτη Οκτώβριος 2026 72 ώρες"; "Κρήτη κακοκαιρία \"Φαράγγι\" 525 \"Ασκύφου\" 412 \"Ασή Γωνιά\" 355 χιλιοστά meteo"; "meteo.gr όροι χρήσης δεδομένων σταθμών Εθνικό Αστεροσκοπείο Αθηνών άδεια χρήσης".

## 4. Verification of the press-reported values against NOA data

- 5-day totals (30/09–04/10): press ">840 / >640 / 448" are NOA's own wording (art. 4340). NOA's Chart 2 (image) gives 867 / 682 / 448, and the sums of the station daily files give Xyloskalo 867.2, Anogeia 681.8, Tzermiado 447.8 (also Samaria-gorge 632.0 vs map 636; Askyfou 510.6 vs 511; Sempronas 454.6 vs 455; Fourfouras 442.2 vs 446; Potamoi 442.0 vs 442; Kandanos 300.4; Asi Gonia 385.2; Kampoi 171.2; Sitia 103.0; Ierapetra 94.8).
- "72-h" values (Ta Nea, 03/10 20:35, attributed to K. Maroussakis): Xyloskalo ≈700, Anogeia ≈600, Farangi 525, Tzermiado 415, Askyfou 412, Asi Gonia 355. These are NOT found in any NOA publication. From the station daily files: 01–03/10 sums are Xyloskalo 671.2, Farangi 528.8, Anogeia 512.6, Tzermiado 373.8, Askyfou 345.0, Asi Gonia 284.6; 30/09–03/10 (4 days) sums are Xyloskalo 753.8, Anogeia 610.6, Farangi 577.2, Tzermiado 414.4, Askyfou 438.6, Asi Gonia 347.2. The press figures are therefore consistent with storm-to-date totals at roughly the article time (evening 03/10), not with a strict 72-h window. The NOA-derived compilation relayed by onlarissa.gr (to midday 03/10) gives 619.4 / 538.8 / 468.8 / 399 / 394.6 / 329 for the same six stations.

## 5. Licence / terms of use

Page: https://www.meteo.gr/terms.cfm ("meteo.gr: Αποποίηση ευθύνης- όροι χρήσης - δήλωση εχεμύθειας") — WebFetch ~13:33Z; raw HTML downloaded 13:33:48Z (`raw/meteo_gr_terms.html`). Verbatim Greek paragraphs are appended below (section 5a). In summary (WebFetch rendering): use of the information is at the visitor's own risk; NOA/IERSD does not guarantee correctness; reproduction of information from the site is prohibited without NOA's consent and without reference to the source "Εθνικό Αστεροσκοπείο Αθηνών/meteo.gr"; for station reports/measurements any table or presentation by third parties must carry the site logo and the attribution "Εθνικό Αστεροσκοπείο Αθηνών/meteo.gr". No open-data licence (e.g. CC) is stated. The NOA map images carry "© Εθνικό Αστεροσκοπείο Αθηνών - meteo.gr".

## 6. Gaps (explicit)

- No hourly/10-min series: not publicly exposed; needs meteosearch.meteo.gr login (quota 30 files/day).
- Daily series obtained for 13 stations only; the Crete network has ~70 (art. 4340) / 73 (onlarissa) stations. Stations known to exist but not retrieved (server stopped responding, curl exit 28 from 13:39:44Z): spili (page only), chania, heraclion, heraclioneast, paleochora, pyrathi, rethymno, stavrakia, neapoli, sfakia, kissamos, plakias, souda, vrysses, alikianos, perama, melampes. Slugs not found (404): Schinokapsala, Kakopetros, Agios Nikolaos, Zaros, Archanes, Viannos, Kastelli, Omalos (the Xyloskalo station is the Omalos-plateau station, slug `samaria`), Zakros, Moires, Gergeri, Kroussonas, Agia Varvara, Tympaki, Agia Galini, Elounda, Palekastro, Zoniana, Mochos, Malia.
- Precise coordinates not available: TXT headers are rounded to whole minutes; station pages carry no coordinates.
- Map "bubble" values for the other ~60 stations on NOA Chart 2 (5-day) are legible in `raw/img_crete_rain_3009_0410_2026.jpg` but were not transcribed (no station labels on the bubbles).

### 5a. Verbatim text extracted from raw/meteo_gr_terms.html (tags stripped; lines containing liability/reproduction/source/privacy terms; extracted 2026-10-09T14:03:54Z)

> meteo.gr: Αποποίηση ευθύνης- όροι χρήσης - δήλωση εχεμύθειας

> Αποποίηση ευθύνης- όροι χρήσης - δήλωση εχεμύθειας

> Απαγορεύεται η αναπαραγωγή πληροφοριών του παρόντος κόμβου χωρίς την συναίνεση του Εθνικού Αστεροσκοπείου Αθηνών (ΕΑΑ) και χωρίς την αναφορά στην πηγή (Εθνικό Αστεροσκοπείο Αθηνών/ meteo.gr). Πιο συγκεκριμένα, όσον αφορά στις προγνώσεις καιρού ανά περιοχή και στις αναφορές/μετρήσεις των σταθμών μας, οποιαδήποτε αναφορά, πίνακας ή άλλος τρόπος παρουσίασης από τρίτους πρέπει να φέρει το λογότυπο του κόμβου μας και τη σήμανση της πηγής: Εθνικό Αστεροσκοπείο Αθηνών/meteo.gr. Για οποιαδήποτε διευκρίνιση σχετικά μπορείτε να επικοινωνήσετε μαζί μας .

