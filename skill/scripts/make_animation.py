"""Self-contained HTML animation (canvas-aligned, base64-embedded frames)."""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

from _common import load_config


def main():
    cfg = load_config()
    import numpy as np
    from PIL import Image
    import pyproj
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject, Resampling

    from _anim_common import (open_sfincs, stats_per_frame, cum_rain_series,
                              glofas_peak_q, load_polys_paths)

    out_html = cfg.paths["deliverable_dir"] / "2_interactive" / f"{cfg.event_slug}_sfincs_animation.html"
    out_html.parent.mkdir(parents=True, exist_ok=True)

    s = open_sfincs(cfg.paths["model_dir"])
    nt = s["nt"]
    canvas_W = int(cfg.animation.get("canvas_width", 920))
    canvas_H = int(round(canvas_W * (s["ymax"] - s["ymin"]) / (s["xmax"] - s["xmin"])))
    print(f"frames={nt}  canvas={canvas_W}x{canvas_H}")

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
    reach = cfg.animation.get("glofas_reach", {})
    q_hourly, peak_cell, peak_q = glofas_peak_q(
        cfg.paths["data_dir"] / f"glofas_{cfg.event_slug}_clean.nc",
        reach, s["times"]) if reach else (np.zeros(nt), None, 0.0)

    # Basemap reproject
    buf = float(cfg.animation.get("basemap_buffer_m", 3000))
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
    bg_rgba = np.empty((canvas_H, canvas_W, 4), dtype=np.uint8)
    bg_rgba[..., :3] = blend.clip(0, 255).astype(np.uint8)
    bg_rgba[..., 3] = 255
    buf_b = io.BytesIO()
    Image.fromarray(bg_rgba, mode="RGBA").save(buf_b, format="PNG", optimize=True)
    bg_b64 = base64.b64encode(buf_b.getvalue()).decode("ascii")
    print(f"canvas basemap PNG: {len(buf_b.getvalue())/1024:.0f} kB")

    # Water frames
    def water_rgba(h_arr):
        h = np.clip(h_arr, 0, 3.0)
        out = np.zeros((*h.shape, 4), dtype=np.uint8)
        wet = h > 0.05
        if wet.any():
            f = h[wet] / 3.0
            out[wet, 0] = (40 + f * 30).astype(np.uint8)
            out[wet, 1] = (140 + f * 60).astype(np.uint8)
            out[wet, 2] = (220 + f * 35).astype(np.uint8)
            out[wet, 3] = (130 + f * 120).astype(np.uint8)
        return out

    frame_b64 = []
    for t in range(nt):
        rgba = water_rgba(h_canvas[t])
        buf_w = io.BytesIO()
        Image.fromarray(rgba, mode="RGBA").save(buf_w, format="PNG", optimize=True)
        frame_b64.append(base64.b64encode(buf_w.getvalue()).decode("ascii"))
    print(f"water frames: {nt}")

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

    def to_paths(xys):
        out = []
        for xs, ys in xys:
            out.append([[round(float(a), 1), round(float(b), 1)] for a, b in zip(xs, ys)])
        return out

    ems_paths = to_paths(polys["ems"])
    aoi_paths = to_paths(polys["aoi"])
    hydro_paths = to_paths(polys["hyd"])
    print(f"vectors: EMS {len(ems_paths)}  AOI {len(aoi_paths)}  hyd {len(hydro_paths)}")

    to_utm = pyproj.Transformer.from_crs(4326, cfg.epsg, always_xy=True)
    cities = []
    for c in cfg.animation.get("cities", []):
        ux, uy = to_utm.transform(c["lon"], c["lat"])
        if s["xmin"] <= ux <= s["xmax"] and s["ymin"] <= uy <= s["ymax"]:
            cities.append({"name": c["name"], "x": round(float(ux), 0), "y": round(float(uy), 0)})

    time_strs = [str(t)[:13].replace("T", " ") for t in s["times"]]

    data = {
        "W": canvas_W, "H": canvas_H,
        "xmin": s["xmin"], "xmax": s["xmax"], "ymin": s["ymin"], "ymax": s["ymax"],
        "times": time_strs,
        "cumRain": cum_rain.round(1).tolist(),
        "q": q_hourly.round(1).tolist(),
        "area": flooded_km2.round(2).tolist(),
        "depth": maxdepth_m.round(2).tolist(),
        "emsPaths": ems_paths, "aoiPaths": aoi_paths, "hydroPaths": hydro_paths,
        "cities": cities,
        "title": f"{cfg.event_label} — {cfg.tstart.strftime('%B %d')}–{cfg.tstop.strftime('%B %d, %Y')}",
        "epsg": cfg.epsg,
    }

    html = HTML_TEMPLATE \
        .replace("__DATA__", json.dumps(data)) \
        .replace("__FRAMES__", json.dumps(frame_b64)) \
        .replace("__BG__", bg_b64)
    out_html.write_text(html, encoding="utf-8")
    print(f"wrote: {out_html} ({out_html.stat().st_size/1e6:.2f} MB)")
    return 0


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SFINCS flood animation</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
:root{--bg:#0e1117;--surface:#1a1d26;--border:#2a2d38;--text:#e4e4e8;--text2:#9a9ba3;--text3:#6b6c75;--accent:#3b82f6;--good:#22c55e;--river:#22d3ee;}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;min-height:100vh;padding:24px 16px;}
h1{font-size:20px;font-weight:600;margin-bottom:4px;}
.subtitle{font-size:13px;color:var(--text2);margin-bottom:16px;}
.wrap{width:100%;max-width:960px;}
.badge{display:inline-block;background:rgba(34,197,94,0.15);color:var(--good);padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;margin-left:6px;text-transform:uppercase;}
canvas{width:100%;border-radius:10px;display:block;border:1px solid var(--border);background:#12151e;}
.controls{display:flex;gap:10px;margin-top:12px;align-items:center;flex-wrap:wrap;}
button{background:transparent;color:var(--text);border:1px solid var(--border);border-radius:6px;padding:6px 14px;font-size:13px;cursor:pointer;font-family:inherit;}
button:hover{background:var(--surface);}
button.toggled{background:var(--surface);border-color:var(--accent);color:var(--accent);}
button.river.toggled{border-color:var(--river);color:var(--river);}
label{font-size:12px;color:var(--text3);}
input[type=range]{height:4px;background:var(--border);border-radius:2px;outline:none;flex:1;max-width:140px;-webkit-appearance:none;}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:var(--accent);cursor:pointer;}
.clock{font-size:14px;font-weight:600;color:var(--accent);margin-left:auto;font-feature-settings:'tnum';}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px;}
.stat{background:var(--surface);border-radius:8px;padding:10px 12px;text-align:center;border:1px solid var(--border);}
.stat .lbl{font-size:11px;color:var(--text3);margin-bottom:4px;text-transform:uppercase;}
.stat .val{font-size:18px;font-weight:600;font-feature-settings:'tnum';}
.stat .val.rain{color:#60a5fa;} .stat .val.q{color:#f59e0b;} .stat .val.area{color:#ef4444;} .stat .val.depth{color:#a78bfa;}
.scrubber{margin-top:10px;}
.scrubber input{width:100%;max-width:none;}
.legend{margin-top:8px;font-size:11px;color:var(--text2);text-align:center;line-height:1.4;}
@media(max-width:600px){.stats{grid-template-columns:repeat(2,1fr);}.clock{margin-left:0;}}
</style></head>
<body>
<div class="wrap">
  <h1 id="ttl">SFINCS flood<span class="badge">aligned</span></h1>
  <p class="subtitle">Hourly modelled water depth · SFINCS rain-on-grid · Copernicus EMS overlays</p>
  <canvas id="fc"></canvas>
  <div class="controls">
    <button id="playBtn">&#9654; Play</button>
    <button id="resetBtn">&#8635; Reset</button>
    <button id="emsBtn" class="toggled">EMS observed</button>
    <button id="aoiBtn" class="toggled">EMS AOI</button>
    <button id="hydroBtn" class="river toggled">Hydrography</button>
    <button id="cityBtn" class="toggled">Cities</button>
    <div style="display:flex;align-items:center;gap:6px;"><label>Speed</label><input type="range" min="1" max="10" value="4" id="spd" step="1"/></div>
    <span class="clock" id="clock">--</span>
  </div>
  <div class="scrubber"><input type="range" id="scrub" min="0" max="0" value="0" step="1"/></div>
  <div class="stats">
    <div class="stat"><div class="lbl">Cum. rain</div><div class="val rain" id="statRain">0 mm</div></div>
    <div class="stat"><div class="lbl">Upstream Q (GloFAS)</div><div class="val q" id="statQ">0 m&sup3;/s</div></div>
    <div class="stat"><div class="lbl">Flooded area (h>0.1 m)</div><div class="val area" id="statArea">0 km&sup2;</div></div>
    <div class="stat"><div class="lbl">Max flood depth</div><div class="val depth" id="statDepth">0.0 m</div></div>
  </div>
  <p class="legend">
    Background: Esri World Imagery (z12, canvas-exact). Red: EMS observed flood. Yellow: EMS AOIs. Cyan: permanent hydrography. Blue: SFINCS modelled water depth (0-3 m).
  </p>
</div>
<script>
const DATA = __DATA__;
const FRAMES = __FRAMES__;
const BG = "__BG__";
document.getElementById('ttl').textContent = DATA.title;
(function(){
const C=document.getElementById('fc'),cx=C.getContext('2d');
const W=DATA.W,H=DATA.H;
C.width=W*2;C.height=H*2;C.style.aspectRatio=(W/H).toString();cx.scale(2,2);
const playBtn=document.getElementById('playBtn');const resetBtn=document.getElementById('resetBtn');
const emsBtn=document.getElementById('emsBtn');const aoiBtn=document.getElementById('aoiBtn');
const hydroBtn=document.getElementById('hydroBtn');const cityBtn=document.getElementById('cityBtn');
const spdS=document.getElementById('spd');const scrub=document.getElementById('scrub');
const clockEl=document.getElementById('clock');
const statRain=document.getElementById('statRain');const statQ=document.getElementById('statQ');
const statArea=document.getElementById('statArea');const statDepth=document.getElementById('statDepth');
const NT=DATA.times.length;scrub.max=NT-1;
const bgImg=new Image();bgImg.src='data:image/png;base64,'+BG;
const waterImgs=FRAMES.map(b=>{const im=new Image();im.src='data:image/png;base64,'+b;return im;});
function utmToPx(x,y){return[((x-DATA.xmin)/(DATA.xmax-DATA.xmin))*W,H-((y-DATA.ymin)/(DATA.ymax-DATA.ymin))*H];}
function drawPaths(paths,style){cx.strokeStyle=style.color;cx.lineWidth=style.lw;for(const path of paths){cx.beginPath();for(let i=0;i<path.length;i++){const[px,py]=utmToPx(path[i][0],path[i][1]);if(i===0)cx.moveTo(px,py);else cx.lineTo(px,py);}cx.closePath();cx.stroke();}}
let t=0,playing=false,showEMS=true,showAOI=true,showHydro=true,showCities=true;
function drawAxes(){cx.fillStyle='#cfd1d8';cx.font='600 11px sans-serif';cx.strokeStyle='rgba(0,0,0,0.85)';cx.lineWidth=3;function lab(txt,x,y,a){cx.textAlign=a;cx.strokeText(txt,x,y);cx.fillText(txt,x,y);}lab(`${Math.round(DATA.xmin)} E`,8,H-6,'left');lab(`${Math.round(DATA.xmax)} E`,W-8,H-6,'right');lab(`${Math.round(DATA.ymax)} N`,8,14,'left');lab(`${Math.round(DATA.ymin)} N`,8,H-18,'left');const dxUtm=DATA.xmax-DATA.xmin;const km_px=(10000/dxUtm)*W;const bx=W-km_px-20,by=H-30;cx.strokeStyle='white';cx.lineWidth=4;cx.beginPath();cx.moveTo(bx,by);cx.lineTo(bx+km_px,by);cx.stroke();cx.strokeStyle='black';cx.lineWidth=2;cx.beginPath();cx.moveTo(bx,by);cx.lineTo(bx+km_px,by);cx.stroke();cx.textAlign='center';cx.fillStyle='white';cx.font='600 11px sans-serif';cx.strokeStyle='rgba(0,0,0,0.85)';cx.lineWidth=3;cx.strokeText('10 km',bx+km_px/2,by-6);cx.fillText('10 km',bx+km_px/2,by-6);}
function drawCities(){if(!showCities)return;for(const c of DATA.cities){const[px,py]=utmToPx(c.x,c.y);if(px<0||px>W||py<0||py>H)continue;cx.fillStyle='white';cx.strokeStyle='black';cx.lineWidth=1.2;cx.beginPath();cx.arc(px,py,4,0,Math.PI*2);cx.fill();cx.stroke();cx.font='600 12px sans-serif';cx.textAlign='left';cx.fillStyle='white';cx.shadowColor='rgba(0,0,0,0.85)';cx.shadowBlur=4;cx.fillText(c.name,px+8,py+4);cx.shadowBlur=0;}}
function frame(){cx.clearRect(0,0,W,H);if(bgImg.complete)cx.drawImage(bgImg,0,0,W,H);if(showAOI)drawPaths(DATA.aoiPaths,{color:'rgba(250,204,21,0.7)',lw:1.4});if(showHydro)drawPaths(DATA.hydroPaths,{color:'rgba(34,211,238,0.7)',lw:0.9});if(showEMS)drawPaths(DATA.emsPaths,{color:'rgba(239,68,68,0.7)',lw:0.6});if(waterImgs[t]&&waterImgs[t].complete)cx.drawImage(waterImgs[t],0,0,W,H);drawCities();drawAxes();clockEl.textContent=DATA.times[t];statRain.textContent=Math.round(DATA.cumRain[t])+' mm';statQ.textContent=Math.round(DATA.q[t]).toLocaleString()+' m³/s';statArea.textContent=DATA.area[t].toFixed(1)+' km²';statDepth.textContent=DATA.depth[t].toFixed(2)+' m';scrub.value=t;if(playing){const speed=parseInt(spdS.value);t+=Math.max(1,Math.floor(speed/3));if(t>=NT-1){t=NT-1;playing=false;playBtn.textContent='▶ Replay';}}requestAnimationFrame(frame);}
playBtn.onclick=function(){if(t>=NT-1)t=0;playing=!playing;this.textContent=playing?'⏸ Pause':'▶ Play';};
resetBtn.onclick=function(){t=0;playing=false;playBtn.textContent='▶ Play';};
emsBtn.onclick=function(){showEMS=!showEMS;this.classList.toggle('toggled',showEMS);};
aoiBtn.onclick=function(){showAOI=!showAOI;this.classList.toggle('toggled',showAOI);};
hydroBtn.onclick=function(){showHydro=!showHydro;this.classList.toggle('toggled',showHydro);};
cityBtn.onclick=function(){showCities=!showCities;this.classList.toggle('toggled',showCities);};
scrub.oninput=function(){t=parseInt(this.value);};
frame();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
