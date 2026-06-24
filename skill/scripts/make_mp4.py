"""Render the libx264 MP4 with the side stats panel via matplotlib."""
from __future__ import annotations

import sys
from pathlib import Path

from _common import load_config


def main():
    cfg = load_config()
    import numpy as np
    import pyproj
    from PIL import Image
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.animation as manim
    import matplotlib.patheffects as pe
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject, Resampling
    import imageio_ffmpeg
    matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()

    from _anim_common import (open_sfincs, stats_per_frame, cum_rain_series,
                              glofas_peak_q, load_polys_paths)

    out_mp4 = cfg.paths["deliverable_dir"] / "1_video" / f"{cfg.event_slug}_sfincs.mp4"
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    s = open_sfincs(cfg.paths["model_dir"])
    nt = s["nt"]
    anim_cfg = cfg.animation
    canvas_W = int(anim_cfg.get("canvas_width", 920))
    canvas_H = int(round(canvas_W * (s["ymax"] - s["ymin"]) / (s["xmax"] - s["xmin"])))

    src_t = from_bounds(s["xmin"], s["ymin"], s["xmax"], s["ymax"], s["nx"], s["ny"])
    tgt_t = from_bounds(s["xmin"], s["ymin"], s["xmax"], s["ymax"], canvas_W, canvas_H)
    h_all_nu = s["h"][:, ::-1, :]
    msk_active_nu = (s["msk"] > 0).astype(np.float32)[::-1, :]
    h_canvas = np.empty((nt, canvas_H, canvas_W), dtype=np.float32)
    for t in range(nt):
        d = np.zeros((canvas_H, canvas_W), dtype=np.float32)
        reproject(source=h_all_nu[t].astype(np.float32), destination=d,
                  src_transform=src_t, src_crs=f"EPSG:{cfg.epsg}",
                  dst_transform=tgt_t, dst_crs=f"EPSG:{cfg.epsg}",
                  resampling=Resampling.bilinear)
        h_canvas[t] = d
    msk_canvas = np.zeros((canvas_H, canvas_W), dtype=np.float32)
    reproject(source=msk_active_nu, destination=msk_canvas,
              src_transform=src_t, src_crs=f"EPSG:{cfg.epsg}",
              dst_transform=tgt_t, dst_crs=f"EPSG:{cfg.epsg}",
              resampling=Resampling.nearest)
    msk_canvas = (msk_canvas >= 0.5).astype(np.uint8)

    flooded_km2, maxdepth_m = stats_per_frame(s)
    cum_rain = cum_rain_series(cfg.paths["model_dir"], nt)
    reach = anim_cfg.get("glofas_reach", {})
    q_hourly, _, _ = glofas_peak_q(
        cfg.paths["data_dir"] / f"glofas_{cfg.event_slug}_clean.nc",
        reach, s["times"]) if reach else (np.zeros(nt), None, 0.0)

    # Basemap
    buf = float(anim_cfg.get("basemap_buffer_m", 3000))
    bm_xmin = s["xmin"] - buf; bm_xmax = s["xmax"] + buf
    bm_ymin = s["ymin"] - buf; bm_ymax = s["ymax"] + buf
    bm_arr = np.array(Image.open(cfg.paths["data_dir"] / "basemap_satellite.png").convert("RGB"))
    bm_H, bm_W = bm_arr.shape[:2]
    src_t_bm = from_bounds(bm_xmin, bm_ymin, bm_xmax, bm_ymax, bm_W, bm_H)
    bg = np.zeros((3, canvas_H, canvas_W), dtype=np.uint8)
    for b in range(3):
        reproject(source=bm_arr[:, :, b], destination=bg[b],
                  src_transform=src_t_bm, src_crs=f"EPSG:{cfg.epsg}",
                  dst_transform=tgt_t, dst_crs=f"EPSG:{cfg.epsg}",
                  resampling=Resampling.bilinear)
    bg = np.transpose(bg, (1, 2, 0))
    bg_d = (bg.astype(np.float32) * 0.85).clip(0, 255).astype(np.uint8)
    inactive = (msk_canvas == 0)
    shade = np.array([15, 18, 25], dtype=np.float32)
    blend = bg_d.astype(np.float32).copy()
    blend[inactive] = bg_d[inactive].astype(np.float32) * 0.55 + shade * 0.45
    bg_disp = blend.clip(0, 255).astype(np.uint8)

    # Polygons
    polys = load_polys_paths(
        cfg.paths["data_dir"] / "ems_polygons", cfg.epsg,
        [("ems", ["*DELINEATION*MONIT*crisis_information_poly.shp",
                   "*GRADING*observed_event_a.shp",
                   "*GRA_*observed_event_a.shp"], 80.0),
         ("aoi", ["*area_of_interest.shp",
                   "*area_of_interest_a.shp"], 60.0),
         ("hyd", ["*DELINEATION*hydrography_poly.shp",
                   "*GRADING*hydrography_l.shp",
                   "*GRA_*hydrography_l.shp"], 40.0)],
    )

    to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
    cities = anim_cfg.get("cities", [])

    fps = int(anim_cfg.get("mp4", {}).get("fps", 12))
    dpi = int(anim_cfg.get("mp4", {}).get("dpi", 110))
    bitrate = int(anim_cfg.get("mp4", {}).get("bitrate_kbps", 4000))

    side_w_in = 4.0
    fig_w_in = (canvas_W / dpi) + side_w_in
    fig_h_in = canvas_H / dpi + 0.5
    fig = plt.figure(figsize=(fig_w_in, fig_h_in), facecolor="#0e1117")
    gs = fig.add_gridspec(1, 2, width_ratios=[canvas_W / dpi, side_w_in],
                          wspace=0.04, left=0.01, right=0.985, top=0.92, bottom=0.06)
    ax = fig.add_subplot(gs[0, 0]); side = fig.add_subplot(gs[0, 1])
    ax.set_facecolor("#0e1117"); side.set_facecolor("#0e1117"); side.set_axis_off()
    ax.imshow(bg_disp, extent=[s["xmin"], s["xmax"], s["ymin"], s["ymax"]],
              origin="upper", interpolation="bilinear")
    for xs, ys in polys["hyd"]:
        ax.plot(xs, ys, color=(0.13, 0.83, 0.93, 0.65), linewidth=0.8, zorder=2)
    for xs, ys in polys["aoi"]:
        ax.plot(xs, ys, color=(0.98, 0.80, 0.13, 0.75), linewidth=1.3, zorder=3)
    for xs, ys in polys["ems"]:
        ax.plot(xs, ys, color=(0.94, 0.27, 0.27, 0.75), linewidth=0.5, zorder=4)
    for c in cities:
        ux, uy = to_utm.transform(c["lon"], c["lat"])
        if s["xmin"] <= ux <= s["xmax"] and s["ymin"] <= uy <= s["ymax"]:
            ax.scatter([ux], [uy], s=36, c="white", edgecolor="black", linewidth=1.0, zorder=6)
            ax.annotate(c["name"], (ux, uy), xytext=(7, 5),
                        textcoords="offset points", fontsize=10, fontweight="bold",
                        color="white",
                        path_effects=[pe.withStroke(linewidth=2.4, foreground="black")],
                        zorder=6)

    import numpy as np
    h0 = np.where(h_canvas[0] > 0.05, h_canvas[0], np.nan)
    im_water = ax.imshow(h0, extent=[s["xmin"], s["xmax"], s["ymin"], s["ymax"]],
                         origin="upper", cmap="Blues", vmin=0, vmax=3.0, alpha=0.78,
                         interpolation="nearest", zorder=5, animated=True)
    ax.set_xlim(s["xmin"], s["xmax"]); ax.set_ylim(s["ymin"], s["ymax"]); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor("#2a2d38")

    # Scale bar
    sb = 10000
    bx0 = s["xmin"] + 0.04 * (s["xmax"] - s["xmin"]); by0 = s["ymin"] + 0.05 * (s["ymax"] - s["ymin"])
    ax.plot([bx0, bx0 + sb], [by0, by0], color="white", linewidth=5,
            solid_capstyle="butt", zorder=8)
    ax.plot([bx0, bx0 + sb], [by0, by0], color="black", linewidth=2.5,
            solid_capstyle="butt", zorder=8)
    ax.text(bx0 + sb / 2, by0 + (s["ymax"] - s["ymin"]) * 0.012, "10 km",
            ha="center", color="white", fontweight="bold", fontsize=10,
            path_effects=[pe.withStroke(linewidth=2.5, foreground="black")], zorder=8)

    fig.text(0.01, 0.965, f"{cfg.event_label} — {cfg.event_name} flood "
             f"({cfg.tstart.strftime('%B %d')}–{cfg.tstop.strftime('%B %d, %Y')})",
             color="white", fontsize=13, fontweight="bold", ha="left", va="top")
    fig.text(0.01, 0.945,
             f"SFINCS v2.3.0 · {cfg.grid['res']} m grid / {cfg.grid['res']/cfg.grid['subgrid_pixels']:.1f} m subgrid · "
             f"ERA5 rain-on-grid · bbox {cfg.bbox['west']}-{cfg.bbox['east']}°E, {cfg.bbox['south']}-{cfg.bbox['north']}°N",
             color="#22c55e", fontsize=10, fontweight="bold", ha="left", va="top",
             bbox=dict(facecolor=(0.13, 0.78, 0.37, 0.18), edgecolor="none",
                       boxstyle="round,pad=0.25"))

    txt_t = side.text(0.5, 0.97, "", color="#60a5fa", fontsize=15, fontweight="bold",
                      ha="center", va="top", transform=side.transAxes, family="monospace")
    txt_rain = side.text(0.04, 0.86, "", color="#60a5fa", fontsize=12,
                         ha="left", va="top", transform=side.transAxes, family="monospace")
    txt_q = side.text(0.04, 0.81, "", color="#f59e0b", fontsize=12,
                      ha="left", va="top", transform=side.transAxes, family="monospace")
    txt_area = side.text(0.04, 0.76, "", color="#ef4444", fontsize=12,
                         ha="left", va="top", transform=side.transAxes, family="monospace")
    txt_depth = side.text(0.04, 0.71, "", color="#a78bfa", fontsize=12,
                          ha="left", va="top", transform=side.transAxes, family="monospace")

    side_left = 1 - side_w_in / fig_w_in
    cb_left = side_left + 0.04 * side_w_in / fig_w_in
    cax = fig.add_axes([cb_left, 0.27, 0.045, 0.35])
    cb = fig.colorbar(im_water, cax=cax)
    cb.set_label("water depth [m]", color="white", fontsize=11)
    cb.ax.yaxis.set_tick_params(color="white", labelcolor="white", labelsize=10)
    for sp in cb.ax.spines.values():
        sp.set_edgecolor("#2a2d38")

    side.text(0.5, 0.20, "Legend", color="white", fontsize=11, ha="center", va="top",
              transform=side.transAxes, fontweight="bold")
    for i, (color, lbl) in enumerate([
        ("#ef4444", "EMS observed flood"),
        ("#facc15", "EMS AOI extent"),
        ("#22d3ee", "permanent hydrography"),
        ("#60a5fa", "Modelled water depth"),
    ]):
        side.plot([0.08, 0.18], [0.17 - i * 0.030, 0.17 - i * 0.030], color=color,
                  linewidth=3.0, transform=side.transAxes, solid_capstyle="round")
        side.text(0.22, 0.17 - i * 0.030, lbl, color="white", fontsize=10,
                  ha="left", va="center", transform=side.transAxes)

    fig.text(0.99, 0.005,
             "Basemap © Esri, Maxar, Earthstar Geographics & GIS community  ·  "
             "Validation: Copernicus EMS  ·  Model: SFINCS (Deltares)",
             color="#9a9ba3", fontsize=7.5, ha="right", va="bottom")

    def init():
        return [im_water, txt_t, txt_rain, txt_q, txt_area, txt_depth]

    def update(t):
        h_m = np.where(h_canvas[t] > 0.05, h_canvas[t], np.nan)
        im_water.set_data(h_m)
        ts = str(s["times"][t])[:16].replace("T", "  ")
        txt_t.set_text(ts + " UTC")
        txt_rain.set_text(f"cum rain    {cum_rain[t]:>7.1f} mm")
        txt_q.set_text(   f"upstream Q  {q_hourly[t]:>7.0f} m³/s")
        txt_area.set_text(f"flooded     {flooded_km2[t]:>7.1f} km²")
        txt_depth.set_text(f"max depth   {maxdepth_m[t]:>7.2f} m")
        return [im_water, txt_t, txt_rain, txt_q, txt_area, txt_depth]

    ani = manim.FuncAnimation(fig, update, frames=nt, init_func=init,
                              interval=1000 // fps, blit=True)
    writer = manim.FFMpegWriter(fps=fps, codec="libx264", bitrate=bitrate,
                                extra_args=["-pix_fmt", "yuv420p",
                                            "-movflags", "+faststart",
                                            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"])
    ani.save(out_mp4, writer=writer, dpi=dpi)
    plt.close(fig)
    print(f"wrote: {out_mp4} ({out_mp4.stat().st_size/1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
