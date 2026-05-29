"""Assemble the deliverable folder (README, docs, figures) and build the
two zip archives.

Reads run-time stats from sfincs_map.nc + sfincs_log.txt to fill in the
docs templates.
"""
from __future__ import annotations

import datetime as dt
import re
import string
import subprocess
import sys
import zipfile
from pathlib import Path

from _common import SKILL_DIR, load_config


def _human_mb(p: Path) -> str:
    if not p.exists():
        return "-"
    return f"{p.stat().st_size/1e6:.2f}"


def _run_stats(log_text: str) -> dict:
    out = {"wallclock_s": "?", "wallclock_breakdown": "", "avg_dt": "?",
           "exit_status": "0; no errors"}
    for line in log_text.splitlines():
        m = re.search(r"Total time\s*:\s*([\d.]+)", line)
        if m:
            out["wallclock_s"] = m.group(1)
        m = re.search(r"Time in (\w+)\s*:\s*([\d.]+)", line)
        if m:
            out["wallclock_breakdown"] += f"{m.group(1)} {m.group(2)} s · "
        m = re.search(r"Average time step \(s\)\s*:\s*([\d.]+)", line)
        if m:
            out["avg_dt"] = m.group(1)
    out["wallclock_breakdown"] = out["wallclock_breakdown"].rstrip(" · ")
    return out


def _extract_mp4_check_frame(mp4_path: Path, out_png: Path, peak_seek_s: float):
    """Use ffmpeg to grab a single peak frame from the MP4."""
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ff, "-y", "-ss", f"{peak_seek_s:.2f}", "-i", str(mp4_path),
                    "-frames:v", "1", "-update", "1", str(out_png)], check=True)


def main():
    cfg = load_config()
    import numpy as np
    import xarray as xr

    deliv = cfg.paths["deliverable_dir"]
    deliv.mkdir(parents=True, exist_ok=True)
    for sub in ["1_video", "2_interactive", "3_figures", "4_docs"]:
        (deliv / sub).mkdir(exist_ok=True)

    mp4 = deliv / "1_video" / f"{cfg.event_slug}_sfincs.mp4"
    html = deliv / "2_interactive" / f"{cfg.event_slug}_sfincs_animation.html"
    qc_png = deliv / "3_figures" / f"{cfg.event_slug}_qc_alignment.png"
    check_png = deliv / "3_figures" / f"{cfg.event_slug}_mp4_check.png"

    # Peak frame stats
    dm = xr.open_dataset(cfg.paths["model_dir"] / "sfincs_map.nc")
    zs = dm["zs"].values; zb = dm["zb"].values; msk = dm["msk"].values
    zs_f = np.where(np.isfinite(zs), zs, zb[None, :, :])
    h = np.maximum(zs_f - zb[None, :, :], 0); h[:, msk == 0] = 0
    flooded = ((h > 0.1) & (msk > 0)[None, :, :]).sum(axis=(1, 2))
    t_peak = int(np.argmax(flooded))
    nt = h.shape[0]
    peak_time = str(dm["time"].values[t_peak])[:16]
    cell_km2 = (float(dm["x"][0, 1] - dm["x"][0, 0]) *
                abs(float(dm["y"][1, 0] - dm["y"][0, 0]))) / 1e6

    # MP4 peak frame extract
    if mp4.exists():
        fps = int(cfg.animation.get("mp4", {}).get("fps", 12))
        seek_s = t_peak / fps
        try:
            _extract_mp4_check_frame(mp4, check_png, seek_s)
            print(f"  mp4 check frame: {check_png.name}")
        except Exception as e:
            print(f"  WARN: could not extract MP4 frame: {e}")

    # Run stats
    log_path = cfg.paths["model_dir"] / "sfincs_log.txt"
    stats = _run_stats(log_path.read_text() if log_path.exists() else "")

    ny, nx = h.shape[1], h.shape[2]
    utm_extent = (f"({dm['x'].values.min():.0f},{dm['y'].values.min():.0f}) - "
                  f"({dm['x'].values.max():.0f},{dm['y'].values.max():.0f})")

    ems_validation_section = ""
    if cfg.event_id:
        ems_dir = cfg.paths["data_dir"] / "ems_polygons"
        gpkg = ems_dir / f"{cfg.event_id}_observed_flood_all.gpkg"
        ems_validation_section = (
            f"Copernicus EMS activation {cfg.event_id} vector products were "
            f"downloaded from `{cfg.ems.get('base_url', '')}` and merged into "
            f"`{gpkg.relative_to(cfg.paths['work_dir']) if gpkg.exists() else '(not built)'}`. "
            f"Observed-flood polygons are from the DELINEATION_MONIT iterations; "
            f"the REFERENCE iterations contribute only AOI + hydrography polygons."
        )
    else:
        ems_validation_section = "No EMS overlay (event.id is null)."

    common = {
        "event_label": cfg.event_label,
        "event_name": cfg.event_name,
        "event_slug": cfg.event_slug,
        "event_date": cfg.event_date.isoformat(),
        "event_location": cfg.raw["event"].get("location", "—"),
        "event_reason": cfg.raw["event"].get("reason", "—"),
        "ems_label": cfg.event_id or "—",
        "ems_provenance": (f"16 vector products from `cems-mapping-website.s3...`"
                           if cfg.event_id else "no EMS overlay"),
        "ems_validation_section": ems_validation_section,
        "build_date": dt.date.today().isoformat(),
        "tref": cfg.tref.strftime("%Y-%m-%d %H:%M:%S"),
        "tstart": cfg.tstart.strftime("%Y-%m-%d %H:%M:%S"),
        "tstop": cfg.tstop.strftime("%Y-%m-%d %H:%M:%S"),
        "tstart_str": cfg.tstart.strftime("%Y-%m-%d"),
        "tstop_str": cfg.tstop.strftime("%Y-%m-%d"),
        "spinup_days": cfg.window["spinup_days"],
        "pre_event_days": cfg.window["pre_event_days"],
        "post_event_days": cfg.window["post_event_days"],
        "window_days": cfg.window["pre_event_days"] + cfg.window["post_event_days"],
        "n_frames": nt,
        "west": cfg.bbox["west"], "south": cfg.bbox["south"],
        "east": cfg.bbox["east"], "north": cfg.bbox["north"],
        "west_buf": cfg.bbox["west"] - float(cfg.bbox.get("era5_buffer_deg", 0.2)),
        "east_buf": cfg.bbox["east"] + float(cfg.bbox.get("era5_buffer_deg", 0.2)),
        "south_buf": cfg.bbox["south"] - float(cfg.bbox.get("era5_buffer_deg", 0.2)),
        "north_buf": cfg.bbox["north"] + float(cfg.bbox.get("era5_buffer_deg", 0.2)),
        "epsg": cfg.epsg,
        "res": cfg.grid["res"],
        "subgrid_pixels": cfg.grid["subgrid_pixels"],
        "effective_res": cfg.grid["res"] / cfg.grid["subgrid_pixels"],
        "ny": ny, "nx": nx,
        "total_cells": ny * nx,
        "active_cells": int((msk > 0).sum()),
        "utm_extent": utm_extent,
        "peak_frame": t_peak,
        "peak_time": peak_time,
        "peak_flooded_km2": f"{float(flooded[t_peak]) * cell_km2:.1f}",
        "peak_depth_m": f"{float(h[t_peak].max()):.2f}",
        "global_max_depth_m": f"{float(h.max()):.2f}",
        "cum_rain_mm": "~",
        "glofas_peak_q": "—",
        "dem_tile_count": len(cfg.dem_tiles()),
        "dem_tile_list": ", ".join(f"{n}{e}" for n, e in cfg.dem_tiles()),
        "worldcover_tile_count": len(cfg.worldcover_tiles()),
        "worldcover_vrt_note": ("wrapped in esa_worldcover_2021.vrt"
                                if len(cfg.worldcover_tiles()) > 1 else "single tile"),
        "wallclock_s": stats["wallclock_s"],
        "wallclock_breakdown": stats["wallclock_breakdown"],
        "avg_dt": stats["avg_dt"],
        "exit_status": stats["exit_status"],
        "mp4_size": _human_mb(mp4),
        "mp4_dims": "—",
        "mp4_seconds": f"{nt / int(cfg.animation.get('mp4', {}).get('fps', 12)):.1f}",
        "html_size": _human_mb(html),
        "work_dir": str(cfg.paths["work_dir"]).replace("\\", "/"),
        "event": cfg.event_slug,
        "py_path": cfg.env.get("python", "python"),
        "deliverable_basename": deliv.name,
        # File sizes for results.md
        "sfincs_inp_size": _human_mb(cfg.paths["model_dir"] / "sfincs.inp"),
        "sfincs_msk_size": _human_mb(cfg.paths["model_dir"] / "sfincs.msk"),
        "sfincs_ind_size": _human_mb(cfg.paths["model_dir"] / "sfincs.ind"),
        "sfincs_subgrid_size": _human_mb(cfg.paths["model_dir"] / "sfincs_subgrid.nc"),
        "precip2d_size": _human_mb(cfg.paths["model_dir"] / "precip_2d.nc"),
        "sfincs_map_size": _human_mb(cfg.paths["model_dir"] / "sfincs_map.nc"),
        "sfincs_log_size": _human_mb(log_path),
        "era5_size": _human_mb(cfg.paths["data_dir"] / f"era5_{cfg.event_slug}.nc"),
        "glofas_size": _human_mb(cfg.paths["data_dir"] / f"glofas_{cfg.event_slug}_clean.nc"),
        "dem_size": "—",
        "wc_size": "—",
        "ems_size": "—",
        "basemap_size": _human_mb(cfg.paths["data_dir"] / "basemap_satellite.png"),
        "tilecache_size": "—",
    }

    # MP4 dims
    if mp4.exists():
        try:
            import imageio_ffmpeg, subprocess as sp
            ff = imageio_ffmpeg.get_ffmpeg_exe()
            r = sp.run([ff, "-i", str(mp4), "-hide_banner"], capture_output=True, text=True)
            m = re.search(r", (\d+)x(\d+)[, ]", r.stderr)
            if m:
                common["mp4_dims"] = f"{m.group(1)}×{m.group(2)}"
        except Exception:
            pass

    def render(tmpl_name: str, out_path: Path):
        tmpl = (SKILL_DIR / "templates" / tmpl_name).read_text(encoding="utf-8")
        out_path.write_text(string.Template(tmpl).safe_substitute(common),
                            encoding="utf-8")
        print(f"  wrote: {out_path}")

    render("README.md.tmpl", deliv / "README.md")
    render("methodology.md.tmpl", deliv / "4_docs" / "methodology.md")
    render("results.md.tmpl", deliv / "4_docs" / "results.md")

    # Build zip archives.
    # If the work_dir basename ends in "_enhanced" (or similar variant tag),
    # carry that suffix through to the zip filenames so enhanced runs don't
    # overwrite their baseline counterparts in zip_dir.
    zip_dir = cfg.paths["zip_dir"]; zip_dir.mkdir(parents=True, exist_ok=True)
    label = f"{cfg.event_id}_{cfg.event_name}" if cfg.event_id else cfg.event_name
    work_name = cfg.paths["work_dir"].name
    suffix = ""
    for tag in ("_enhanced", "_v3", "_v4", "_v5"):
        if work_name.endswith(tag):
            suffix = tag
            break
    full_zip = zip_dir / f"{label}_SFINCS_deliverable{suffix}.zip"
    if full_zip.exists():
        full_zip.unlink()
    with zipfile.ZipFile(full_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(deliv.rglob("*")):
            if p.is_file():
                arc = Path(deliv.name) / p.relative_to(deliv)
                zf.write(p, arc.as_posix())
    print(f"wrote: {full_zip} ({full_zip.stat().st_size/1e6:.2f} MB)")

    vid_zip = zip_dir / f"{label}_SFINCS_video_only{suffix}.zip"
    if vid_zip.exists():
        vid_zip.unlink()
    with zipfile.ZipFile(vid_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        if mp4.exists():
            zf.write(mp4, mp4.name)
        zf.write(deliv / "README.md", "README.md")
    print(f"wrote: {vid_zip} ({vid_zip.stat().st_size/1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
