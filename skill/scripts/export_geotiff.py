"""Export SFINCS results as GeoTIFFs (peak depth, flood extent, peak velocity).

Reads model/sfincs_map.nc and writes, in the model CRS:
  hmax_<res>m.tif          peak water depth on the SFINCS grid (m)
  flood_extent_<res>m.tif  1 = flooded (h > --flood-threshold), 0 = dry, 255 = outside model
  vmax_<res>m.tif          peak flow velocity (m/s), only if the run had storevelmax = 1
  hmax_<dem>m.tif          peak depth downscaled onto the high-resolution DEM
  flood_extent_<dem>m.tif  flood extent from the downscaled depth

Sea cells (bed level <= 0 m) are always wet, so they are masked out by default
(--keep-sea to keep them). zsmax is stored per dtmaxout interval (e.g. per day), so the peak is the max
over all intervals, not the last one.

Usage:
  python scripts/export_geotiff.py --config examples/<event>.yaml
  python scripts/export_geotiff.py --model-dir <model> --dem <dem.tif|vrt> --out-dir <dir>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", help="event YAML (derives model dir, DEM and output dir)")
    ap.add_argument("--model-dir", help="SFINCS model folder containing sfincs_map.nc")
    ap.add_argument("--dem", help="high-resolution DEM for downscaling (any CRS)")
    ap.add_argument("--out-dir", help="output folder for the GeoTIFFs")
    ap.add_argument("--dem-res", type=float, default=30.0, help="downscaling resolution in m (default 30)")
    ap.add_argument("--hmin", type=float, default=0.05, help="min depth kept in depth maps, m (default 0.05)")
    ap.add_argument("--keep-sea", action="store_true",
                    help="keep cells with bed level <= 0 m (sea); by default they are masked out")
    ap.add_argument("--flood-threshold", type=float, default=0.10,
                    help="depth defining 'flooded' in extent maps, m (default 0.10, as in the EMS validation)")
    args = ap.parse_args()
    if args.config:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _common import load_config
        cfg = load_config(["--config", args.config])
        args.model_dir = args.model_dir or cfg.paths["model_dir"]
        args.dem = args.dem or cfg.paths["data_dir"] / "copdem30" / "copdem30.vrt"
        args.out_dir = args.out_dir or cfg.paths["deliverable_dir"] / "5_geotiff"
    if not (args.model_dir and args.out_dir):
        ap.error("give --config, or --model-dir and --out-dir")
    return args


def grid_da(values, x1d, y1d, epsg, name, nodata):
    """2-D array on the SFINCS grid -> north-up, georeferenced DataArray."""
    import xarray as xr
    import rioxarray  # noqa: F401  (registers .rio)
    da = xr.DataArray(values, dims=("y", "x"), coords={"y": y1d, "x": x1d}, name=name)
    da = da.sortby("y", ascending=False)
    da = da.rio.write_crs(f"EPSG:{epsg}").rio.write_nodata(nodata, encoded=False)
    return da


def write_tif(da, path: Path):
    da.rio.to_raster(path, compress="deflate", tiled=True)
    print(f"wrote: {path.name:28s} {path.stat().st_size / 1e6:6.2f} MB")


def main():
    args = parse_args()
    import xarray as xr
    import rioxarray  # noqa: F401
    from rasterio.enums import Resampling

    model_dir, out_dir = Path(args.model_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ds = xr.open_dataset(model_dir / "sfincs_map.nc")
    epsg = int(ds["crs"].attrs.get("epsg_code", "EPSG:0").split(":")[-1]) if "crs" in ds else 0
    if not epsg:
        epsg = int(ds["inp"].attrs["epsg"])
    x1d = ds["x"].values[0, :]
    y1d = ds["y"].values[:, 0]
    res = int(round(abs(float(x1d[1] - x1d[0]))))
    zb = ds["zb"].values
    active = ds["msk"].values > 0
    if not args.keep_sea:
        active &= zb > 0

    # Peak water level over ALL dtmaxout intervals (zsmax restarts each interval).
    zsmax = ds["zsmax"].max("timemax") if "timemax" in ds["zsmax"].dims else ds["zsmax"]
    zsmax_v = zsmax.values
    hmax = np.where(np.isfinite(zsmax_v), zsmax_v - zb, 0.0)
    hmax = np.where(active & (hmax >= args.hmin), hmax, np.nan).astype("float32")
    write_tif(grid_da(hmax, x1d, y1d, epsg, "hmax", np.nan), out_dir / f"hmax_{res}m.tif")

    ext = np.where(active, (np.nan_to_num(hmax) > args.flood_threshold).astype("uint8"), 255).astype("uint8")
    write_tif(grid_da(ext, x1d, y1d, epsg, "flood_extent", 255), out_dir / f"flood_extent_{res}m.tif")
    cell_km2 = res * res / 1e6
    print(f"  flooded area (h > {args.flood_threshold} m, {res} m grid): {(ext == 1).sum() * cell_km2:,.1f} km2"
          f" | max depth {np.nanmax(hmax):.2f} m")

    if "vmax" in ds:
        vmax_v = ds["vmax"].max("timemax").values if "timemax" in ds["vmax"].dims else ds["vmax"].values
        vmax = np.where(active & (np.nan_to_num(hmax) > 0), vmax_v, np.nan).astype("float32")
        write_tif(grid_da(vmax, x1d, y1d, epsg, "vmax", np.nan), out_dir / f"vmax_{res}m.tif")
        print(f"  max velocity in flooded cells: {np.nanmax(vmax):.2f} m/s")
    else:
        print("  no vmax in sfincs_map.nc (run SFINCS with storevelmax = 1 to get velocities)")

    if not args.dem:
        return 0
    # Downscale: project the DEM to the model CRS at --dem-res over the model extent,
    # then let HydroMT-SFINCS spread the peak water level over it (depth = zsmax - DEM).
    from hydromt_sfincs.utils import downscale_floodmap
    dres = args.dem_res
    xmin, xmax = x1d.min() - res / 2, x1d.max() + res / 2
    ymin, ymax = y1d.min() - res / 2, y1d.max() + res / 2
    dem = rioxarray.open_rasterio(args.dem, masked=True).squeeze("band", drop=True)
    dem = dem.rio.reproject(f"EPSG:{epsg}", resolution=dres,
                            resampling=Resampling.bilinear).rio.clip_box(xmin, ymin, xmax, ymax)
    if not args.keep_sea:
        dem = dem.where(dem > 0)
    dem = dem.rio.write_nodata(np.nan, encoded=False)
    dem.name = "elevtn"

    zs_da = grid_da(np.where(active, zsmax_v, np.nan).astype("float32"), x1d, y1d, epsg, "zsmax", np.nan)
    dem_tag = int(round(dres))
    hmax_hr = downscale_floodmap(zsmax=zs_da, dep=dem, hmin=args.hmin, reproj_method="bilinear")
    hmax_hr = hmax_hr.astype("float32").rio.write_crs(f"EPSG:{epsg}").rio.write_nodata(np.nan, encoded=False)
    write_tif(hmax_hr, out_dir / f"hmax_{dem_tag}m.tif")

    in_model = (np.isfinite(zs_da.rio.reproject_match(hmax_hr, resampling=Resampling.nearest).values)
                & np.isfinite(dem.rio.reproject_match(hmax_hr).values))
    h_hr = np.nan_to_num(hmax_hr.values)
    ext_hr = np.where(in_model, (h_hr > args.flood_threshold).astype("uint8"), 255).astype("uint8")
    ext_hr_da = hmax_hr.copy(data=ext_hr).rio.write_nodata(255, encoded=False)
    ext_hr_da.name = "flood_extent"
    write_tif(ext_hr_da, out_dir / f"flood_extent_{dem_tag}m.tif")
    print(f"  flooded area (h > {args.flood_threshold} m, {dem_tag} m DEM): "
          f"{(ext_hr == 1).sum() * dres * dres / 1e6:,.1f} km2 | max depth {np.nanmax(hmax_hr.values):.2f} m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
