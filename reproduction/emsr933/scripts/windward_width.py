"""GO-C decision 6 — organising scale of the EMSR933 rain: windward slope width of Lefka Ori, Psiloritis and Dikti
measured from GLO-30 (the Crete copdem30 VRT), to be recorded in rule_ledger.md §8 BEFORE any Crete run.

Flow of the event (NOA article 4340, ledger §7): persistent north-to-north-east flow over the Aegean, so the windward
slopes face N to NE. For each massif: the summit is the GLO-30 maximum within 6 km of the published summit; a transect
is drawn from the summit towards the upwind side (azimuths 0 deg = N, 22.5 deg = NNE, 45 deg = NE) at 90-m steps until
the coastline (first cell with z <= 0 / nodata); the profile is smoothed with a 450-m running mean. Two widths:
  L_coast_crest : horizontal distance coastline -> summit along the transect;
  L_10_90       : horizontal distance between the first crossings (from the coast) of 10 % and 90 % of the summit
                  height — the windward slope proper (the organising scale compared with the IMERG footprint).
Usage: python -I windward_width.py --vrt <copdem30.vrt> --out-json <...> --out-md <...>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

SUMMITS = {  # name: (lat, lon, published height m) — WGS84, from the 1:50k mapping; refined on the DEM
    "Lefka Ori (Pachnes)": (35.303, 24.017, 2453),
    "Psiloritis (Timios Stavros)": (35.223, 24.770, 2456),
    "Dikti (Spathi)": (35.117, 25.483, 2148),
}
AZIMUTHS = {"N (0 deg)": 0.0, "NNE (22.5 deg)": 22.5, "NE (45 deg)": 45.0}
STEP_M = 90.0
IMERG_FOOTPRINT_KM = (0.1 * 111.32 * np.cos(np.radians(35.2)), 0.1 * 111.32)   # E-W, N-S at 35.2 N


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--vrt", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    ap.add_argument("--out-md", required=True, type=Path)
    a = ap.parse_args()
    import rasterio
    from pyproj import Transformer
    to_utm = Transformer.from_crs(4326, 32635, always_xy=True)      # UTM 35N for metric transects over central/east Crete
    to_ll = Transformer.from_crs(32635, 4326, always_xy=True)
    out = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "dem": str(a.vrt), "step_m": STEP_M,
           "smoothing_m": 5 * STEP_M, "imerg_footprint_km_EW_NS": [round(float(IMERG_FOOTPRINT_KM[0]), 2), round(float(IMERG_FOOTPRINT_KM[1]), 2)],
           "flow": "N to NE (NOA art. 4340; windward = N/NE-facing slopes)", "massifs": {}}
    with rasterio.open(a.vrt) as src:
        nod = src.nodata

        def sample(xs, ys):
            lon, lat = to_ll.transform(xs, ys)
            v = np.array([q[0] for q in src.sample(zip(lon, lat))], dtype=float)
            if nod is not None:
                v[v == nod] = np.nan
            return v

        for name, (lat, lon, hpub) in SUMMITS.items():
            x0, y0 = to_utm.transform(lon, lat)
            # refine the summit: DEM max within 6 km (300-m search grid, then 90-m)
            best = (-1, x0, y0)
            for r in (300.0, 90.0):
                gx, gy = np.meshgrid(np.arange(-6000, 6001, r) if r == 300.0 else np.arange(-450, 451, r),
                                     np.arange(-6000, 6001, r) if r == 300.0 else np.arange(-450, 451, r))
                xs = best[1] + gx.ravel(); ys = best[2] + gy.ravel()
                z = sample(xs, ys); i = int(np.nanargmax(z))
                best = (float(z[i]), float(xs[i]), float(ys[i]))
            zs, xs0, ys0 = best
            lon_s, lat_s = to_ll.transform(xs0, ys0)
            m = {"published_summit": {"lat": lat, "lon": lon, "h_m": hpub}, "dem_summit": {"lat": round(lat_s, 4), "lon": round(lon_s, 4), "h_m": round(zs, 1)}, "transects": {}}
            for label, az in AZIMUTHS.items():
                dx, dy = np.sin(np.radians(az)), np.cos(np.radians(az))        # unit vector towards the upwind side
                n = int(60000 / STEP_M)
                d = STEP_M * np.arange(n + 1)
                z = sample(xs0 + dx * d, ys0 + dy * d)
                coast = np.where(~np.isfinite(z) | (z <= 0))[0]
                if coast.size == 0:
                    m["transects"][label] = {"note": "no coastline within 60 km"}; continue
                ic = int(coast[0])
                prof = z[:ic + 1].copy(); prof[~np.isfinite(prof)] = 0.0
                k = 5; ker = np.ones(k) / k
                sm = np.convolve(np.pad(prof, (k // 2, k // 2), mode="edge"), ker, mode="valid")
                # from the coast (index ic) towards the summit (index 0): first crossings of 10 % and 90 % of the summit height
                rev = sm[::-1]                                                    # rev[0] = coast, rev[-1] = summit
                i10 = int(np.argmax(rev >= 0.10 * zs)); i90 = int(np.argmax(rev >= 0.90 * zs))
                i25 = int(np.argmax(rev >= 0.25 * zs)); i75 = int(np.argmax(rev >= 0.75 * zs))
                l_cc = ic * STEP_M; l_10_90 = (i90 - i10) * STEP_M; l_25_75 = (i75 - i25) * STEP_M
                # mean slope of the 10-90 band; the 25-75 band is the core of the slope (half the height range)
                slope = (0.8 * zs) / l_10_90 if l_10_90 > 0 else None
                # steep band: longest contiguous stretch (approaching the crest) with a smoothed slope >= 0.10 (5.7 deg)
                grad = np.abs(np.diff(rev)) / STEP_M
                steep = grad >= 0.10
                best_len = cur = 0
                for flag in steep:
                    cur = cur + 1 if flag else 0
                    best_len = max(best_len, cur)
                m["transects"][label] = {"azimuth_deg": az, "L_coast_crest_km": round(l_cc / 1000, 2), "L_10_90_km": round(l_10_90 / 1000, 2),
                                         "L_25_75_km": round(l_25_75 / 1000, 2), "L_steep_ge_0p10_km": round(best_len * STEP_M / 1000, 2),
                                         "mean_slope_10_90": (round(slope, 3) if slope else None),
                                         "coast_point": dict(zip(("lon", "lat"), [round(v, 4) for v in to_ll.transform(xs0 + dx * l_cc, ys0 + dy * l_cc)])),
                                         "profile_km_m": [[round(float(dd) / 1000, 2), round(float(zz), 0)] for dd, zz in zip(d[:ic + 1:10], sm[::10])]}
            out["massifs"][name] = m
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    L = [f"# EMSR933 — windward slope widths from GLO-30 ({out['utc']}; `windward_width.py`)", "",
         f"Flow N–NE (ledger §7). IMERG footprint at 35.2°N: {out['imerg_footprint_km_EW_NS'][0]} km E–W × {out['imerg_footprint_km_EW_NS'][1]} km N–S. "
         "L_coast_crest = coastline → summit along the upwind transect; L_10_90 = horizontal width between the 10 % and 90 % summit-height crossings (the slope proper).", "",
         "L_25_75 = width of the core of the slope (25–75 % of the summit height); L_steep = longest contiguous stretch with smoothed slope ≥ 0.10.", "",
         "| massif | DEM summit (lat, lon, m) | transect | L_coast_crest km | L_10_90 km | L_25_75 km | L_steep≥0.10 km | mean slope 10–90 |", "|---|---|---|---|---|---|---|---|"]
    for name, m in out["massifs"].items():
        s = m["dem_summit"]
        for label, t in m["transects"].items():
            if "note" in t:
                L.append(f"| {name} | {s['lat']}, {s['lon']}, {s['h_m']} | {label} | {t['note']} | | | | |")
            else:
                L.append(f"| {name} | {s['lat']}, {s['lon']}, {s['h_m']} | {label} | {t['L_coast_crest_km']} | {t['L_10_90_km']} | {t['L_25_75_km']} | {t['L_steep_ge_0p10_km']} | {t['mean_slope_10_90']} |")
    a.out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
