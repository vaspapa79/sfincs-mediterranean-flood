"""Download all Copernicus EMS vector ZIPs for an activation and merge
DELINEATION_MONIT crisis polygons into a single gpkg in UTM.

Driven by the YAML config (`event.id`, `ems.base_url`, `ems.aois`,
`ems.iterations`, `crs.epsg`). If `event.id` is null/empty, exits 0
without doing anything.

Two download backends:

  A. **Legacy S3 bucket** (pre-2024 activations such as EMSR122 / Strymonas
     and EMSR257 / Mandra) — base_url ``cems-mapping-website.s3.…``.
     Walks the Cartesian product of ``aois × iterations`` from the YAML
     and tries ``{base_url}/{event_id}/{event_id}_{aoi}_{iteration}_vector.zip``,
     skipping 403/404 silently.

  B. **rapidmapping API** (newer activations such as EMSR692 / Storm
     Daniel / Pineios) — base_url ``rapidmapping.emergency.copernicus.eu``.
     Queries the dashboard-api endpoint for the activation, then for each
     feasible product with statusCode='F' downloads
     ``{base_url}/{event_id}/AOI{nn}/{type}/{event_id}_AOI{nn}_{type}_v{n}.zip``.
     AOI list in the YAML is **ignored** for this backend; everything
     visible to the public API is fetched. ``iterations`` may also be
     omitted (only DEL_MONIT** is downloaded by default).
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

from _common import load_config, ensure_dir


def _download_legacy(base: str, event_id: str, aois: list, iterations: list,
                     dest: Path, headers: dict) -> None:
    """Old S3-bucket backend used by EMSR122 / EMSR257."""
    for aoi in aois:
        for it in iterations:
            name = f"{event_id}_{aoi}_{it}_vector"
            sub = dest / name.replace("_vector", "")
            if sub.exists() and any(sub.glob("*.shp")):
                print(f"  skip (cached): {sub.name}")
                continue
            url = f"{base}/{event_id}/{name}.zip"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
            except urllib.error.HTTPError as e:
                # AWS S3 returns 403 (not 404) for missing keys when
                # ListBucket is denied — treat both as "iteration not
                # published for this AOI" and continue.
                if e.code in (403, 404):
                    print(f"  {e.code}, skipping: {name}")
                    continue
                raise
            sub.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(sub)
            print(f"  downloaded: {name} ({len(data)/1024:.0f} kB)")


def _download_rapidmapping(base: str, event_id: str, dest: Path,
                           headers: dict, status_codes: set[str]) -> None:
    """Newer dashboard-api backend used by EMSR692.

    Queries the public-activations endpoint, walks AOIs × products,
    downloads each ZIP that exists. ``status_codes`` selects which
    products to fetch — by default we take only 'F' (finalised /
    delivered) since 'N' (not produced) and others have no ZIP.
    """
    api = f"{base.rstrip('/')}/dashboard-api/public-activations/?code={event_id}"
    print(f"  querying API: {api}")
    req = urllib.request.Request(api, headers=headers)
    j = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    if not j.get("results"):
        print(f"  WARN: no activation matched code={event_id}")
        return
    act = j["results"][0]
    for aoi in act.get("aois", []):
        n = aoi["number"]
        aoi_tag = f"AOI{n:02d}"
        for p in aoi.get("products", []):
            v = p.get("version") or {}
            if v.get("statusCode") not in status_codes:
                continue
            # Build product-type folder name.
            #   monitoring=False, type=DEL -> "DEL"
            #   monitoring=True,  type=DEL, monitoringNumber=3 -> "DEL_MONIT03"
            ptype = p["type"]
            if p.get("monitoring") and p.get("monitoringNumber"):
                ptype = f"{ptype}_MONIT{int(p['monitoringNumber']):02d}"
            vnum = int(v.get("number") or 1)
            # Prefer the API's authoritative downloadPath: GRADING products live under
            # a "GRA_PRODUCT" folder, not the "{ptype}" path the stem convention assumes,
            # so the constructed URL 404s for them. downloadPath is the real ZIP location
            # for every product family (delineation and grading alike).
            dl = p.get("downloadPath")
            if dl:
                url = dl
                stem = dl.rstrip("/").rsplit("/", 1)[-1]
                if stem.endswith(".zip"):
                    stem = stem[:-4]
            else:
                stem = f"{event_id}_{aoi_tag}_{ptype}_v{vnum}"
                url = f"{base.rstrip('/')}/{event_id}/{aoi_tag}/{ptype}/{stem}.zip"
            sub = dest / stem
            if sub.exists() and any(sub.glob("*.shp")):
                print(f"  skip (cached): {sub.name}")
                continue
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=300) as r:
                    data = r.read()
            except urllib.error.HTTPError as e:
                # 404 / 403 / 405 all mean "not available" — skip.
                if e.code in (403, 404, 405):
                    print(f"  {e.code}, skipping: {stem}")
                    continue
                raise
            sub.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(sub)
            print(f"  downloaded: {stem} ({len(data)/1024:.0f} kB)")


def main():
    cfg = load_config()
    if not cfg.event_id:
        print("event.id is null — skipping EMS download.")
        return 0

    import pyogrio
    import pyproj
    from shapely import from_wkb
    from shapely.ops import transform as shp_transform
    import geopandas as gpd

    ems = cfg.ems
    base = ems.get(
        "base_url",
        "https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations",
    )
    aois = ems.get("aois", [])
    iterations = ems.get("iterations", [])
    dest = ensure_dir(cfg.paths["data_dir"] / "ems_polygons")
    event_id = cfg.event_id
    headers = {
        "User-Agent": f"Mozilla/5.0 ({event_id} fetcher)",
        "Accept": "application/json, application/zip, */*",
    }

    if "rapidmapping.emergency.copernicus.eu" in base:
        # New dashboard-api backend (EMSR692 et al).
        _download_rapidmapping(base, event_id, dest, headers,
                               status_codes={"F"})
    else:
        # Legacy S3 backend (EMSR122 / EMSR257 …).
        if not aois or not iterations:
            sys.exit("ems.aois and ems.iterations must be set when event.id "
                     "is given for the legacy S3 backend. "
                     "See references/ems_catalog.md.")
        _download_legacy(base, event_id, aois, iterations, dest, headers)

    # Merge observed-flood polygons into a single gpkg in UTM.
    # Three product families ship the polygons under different filenames:
    #   - DELINEATION/MONIT (legacy S3):  *crisis_information_poly.shp
    #   - GRADING (EMSR257 etc., legacy): *observed_event_a.shp
    #   - DEL_MONIT** (rapidmapping API): *observedEventA_v*.shp
    target_crs = pyproj.CRS.from_epsg(cfg.epsg)
    all_geoms, all_sources = [], []
    pats = [
        "*DELINEATION*MONIT*crisis_information_poly.shp",
        "*GRADING*observed_event_a.shp",
        "*GRA_*observed_event_a.shp",
        "*DEL_MONIT*observedEventA*.shp",
        "*DEL_MONIT*observed_event*.shp",
        "*GRA_PRODUCT*observedEventA*.shp",
    ]
    shp_paths = []
    for pat in pats:
        shp_paths.extend(dest.rglob(pat))
    # dedupe while preserving order
    seen = set()
    shp_paths = [p for p in shp_paths if not (p in seen or seen.add(p))]
    shp_paths.sort()
    if not shp_paths:
        print(f"WARN: no shapefiles matched any of {pats}; nothing to merge.")
        return 0

    for shp in shp_paths:
        info = pyogrio.read_info(shp)
        src_crs = pyproj.CRS.from_user_input(info["crs"])
        meta, fids, gw, fields = pyogrio.raw.read(str(shp), return_fids=True)
        geoms = [from_wkb(g) for g in gw]
        if src_crs != target_crs:
            tr = pyproj.Transformer.from_crs(src_crs, target_crs, always_xy=True).transform
            geoms = [shp_transform(tr, g) for g in geoms]
        for g in geoms:
            all_geoms.append(g)
            all_sources.append(shp.parent.name)

    print(f"merged {len(all_geoms)} observed-flood polygons from {len(shp_paths)} shapefiles")
    if not all_geoms:
        return 0

    out = dest / f"{event_id}_observed_flood_all.gpkg"
    gdf = gpd.GeoDataFrame({"source": all_sources, "geometry": all_geoms},
                           crs=f"EPSG:{cfg.epsg}")
    gdf.to_file(out, driver="GPKG")
    print(f"wrote: {out}  ({out.stat().st_size/1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
