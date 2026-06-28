#!/usr/bin/env python3
"""Roon Display Web Configuration Server — HDMI version"""

from flask import Flask, request, jsonify, render_template_string, send_file
import json, os, subprocess

app = Flask(__name__)
CONFIG_FILE = os.path.expanduser("~/config.json")

FONTS = {
    "TeX Gyre Heros": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf",
    },
    "TeX Gyre Heros Condensed": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheroscn-regular.otf",
    },
    "TeX Gyre Pagella": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrepagella-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrepagella-regular.otf",
    },
    "TeX Gyre Bonum": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrebonum-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrebonum-regular.otf",
    },
    "TeX Gyre Termes": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-regular.otf",
    },
    "TeX Gyre Adventor": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreadventor-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreadventor-regular.otf",
    },
    "TeX Gyre Cursor": {
        "bold":    "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrecursor-bold.otf",
        "regular": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrecursor-regular.otf",
    },
    "Roboto": {
        "bold":    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf",
    },
    "Roboto Light": {
        "bold":    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Medium.ttf",
        "regular": "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Light.ttf",
    },
    "Roboto Condensed": {
        "bold":    "/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/roboto/unhinted/RobotoCondensed-Regular.ttf",
    },
    "Liberation Sans": {
        "bold":    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    },
    "Liberation Serif": {
        "bold":    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    },
    "Liberation Mono": {
        "bold":    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    },
    "DejaVu Sans": {
        "bold":    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    },
    "DejaVu Serif": {
        "bold":    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    },
    "DejaVu Mono": {
        "bold":    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    },
}

TOUCH_ACTIONS = ["volume_up","volume_down","next","previous","play_pause","toggle_text","heat_pump","none"]

DEFAULT_CONFIG = {
    "bridge": "http://192.168.8.118:3001",
    "target_zone": "Lounge",
    "poll_interval": 10,
    "text_hold": 20,
    "scroll_speed": 1.5,
    "scroll_hold": 2.0,
    "scroll_fps": 20,
    "size_artist": 52,
    "size_album": 42,
    "size_track": 42,
    "line_spacing": 10,
    "line_spacing_artist": 16,
    "artist_bold": True,
    "text_bg_opacity": 180,
    "text_bg_blur": 16,
    "progress_bar_height": 5,
    "progress_bar_colour": "#ffffff",
    "blur_radius": 40,
    "clock_blur_radius": 60,
    "clock_radius": 300,
    "clock_cx": 900,
    "clock_date_cx": 260,
    "clock_flip": False,
    "clock_day_size": 70,
    "clock_date_size": 66,
    "clock_text_y_offset": 0,
    "font_track": "TeX Gyre Heros",
    "font_clock": "TeX Gyre Heros",
    "silence_threshold": 50,
    "silence_timeout": 30,
    "sample_interval": 30,
    "sample_duration": 5,
    "retry_delay": 15,
    "display_fb": "/dev/fb0",
    "display_rotation": 0,
    "touch_swipe_min_dx": 250,
    "touch_swipe_max_dy": 200,
    "touch_swipe_max_ms": 600,
    "touch_tap_max_move": 30,
    "touch_double_tap_ms": 400,
    "touch_long_press_ms": 1000,
    "touch_vol_step": 5,
    "touch_left_zone": 0.33,
    "touch_right_zone": 0.67,
    "touch_action_left": "volume_down",
    "touch_action_right": "volume_up",
    "touch_action_centre": "toggle_text",
    "touch_action_double": "play_pause",
    "touch_action_long": "heat_pump",
    "touch_action_swipe_left": "next",
    "touch_action_swipe_right": "previous",
    "heat_pump_url": "http://192.168.8.118:5000/",
    "text_fade_steps": 20,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

# Build @font-face CSS and font name→CSS-family map
def build_font_css():
    css = ""
    for name, paths in FONTS.items():
        family = name.replace(" ", "_")
        bold_file   = os.path.basename(paths["bold"])
        reg_file    = os.path.basename(paths["regular"])
        css += f'@font-face {{ font-family: "{family}"; src: url("/fonts/{bold_file}"); font-weight: bold; }}\n'
        css += f'@font-face {{ font-family: "{family}"; src: url("/fonts/{reg_file}"); font-weight: normal; }}\n'
    return css

def font_option_html(name, selected_name):
    family = name.replace(" ", "_")
    sel = "selected" if name == selected_name else ""
    return f'<option value="{name}" style="font-family: \'{family}\'; font-size: 15px;" {sel}>{name}</option>'

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Roon Display HDMI</title>
<style>
{{ font_css }}

:root {
  --bg:#0a0a0a; --surface:#111; --border:#222; --accent:#e8e8e8;
  --accent2:#888; --danger:#cc3333; --text:#e0e0e0; --text-dim:#666; --radius:4px;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--text); font-family:'TeX_Gyre_Heros',sans-serif;
  font-weight:300; min-height:100vh; padding:40px 20px 80px; }
.container { max-width:680px; margin:0 auto; }
header { margin-bottom:48px; border-bottom:1px solid var(--border); padding-bottom:24px; }
header h1 { font-size:11px; letter-spacing:.25em; text-transform:uppercase;
  color:var(--text-dim); margin-bottom:8px; }
header p { font-size:28px; font-weight:300; color:var(--accent); }
.badge { display:inline-block; font-size:10px; letter-spacing:.15em; text-transform:uppercase;
  color:#4488cc; border:1px solid #4488cc; padding:2px 8px; border-radius:2px; margin-top:8px; }
.section { margin-bottom:40px; overflow:visible; }
.section-title { font-size:10px; letter-spacing:.25em; text-transform:uppercase;
  color:var(--text-dim); margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid var(--border); }
.field { display:flex; align-items:center; justify-content:space-between;
  padding:13px 0; border-bottom:1px solid #161616; gap:16px; overflow:visible; position:relative; }
.field:last-child { border-bottom:none; }
.field-label { font-size:14px; font-weight:400; }
.field-hint { font-size:11px; color:var(--text-dim); margin-top:2px; font-family:monospace; }
.field-control { display:flex; align-items:center; gap:10px; flex-shrink:0; }
.field-value { font-family:monospace; font-size:12px; color:var(--accent2);
  min-width:44px; text-align:right; }
input[type=range] { -webkit-appearance:none; width:140px; height:2px;
  background:var(--border); outline:none; border-radius:1px; }
input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:14px; height:14px;
  border-radius:50%; background:var(--accent); cursor:pointer; }
input[type=number], input[type=text], select {
  background:var(--surface); border:1px solid var(--border); color:var(--text);
  padding:6px 10px; font-family:monospace; font-size:12px;
  border-radius:var(--radius); width:90px; text-align:center; }
select { width:auto; min-width:200px; text-align:left; cursor:pointer; position:relative; z-index:10; }
select.font-select { font-size:15px; padding:8px 10px; }

/* Custom font picker */
.font-picker { position:relative; min-width:240px; user-select:none; }
.font-picker-selected {
  background:var(--surface); border:1px solid var(--border); color:var(--text);
  padding:9px 36px 9px 12px; border-radius:var(--radius); cursor:pointer;
  font-size:15px; display:flex; align-items:center; justify-content:space-between;
  transition:border-color .15s;
}
.font-picker-selected:hover { border-color:var(--accent2); }
.font-picker-selected::after { content:"▾"; color:var(--accent2); font-size:12px; flex-shrink:0; }
.font-picker-dropdown {
  display:none; position:fixed; background:#1a1a1a;
  border:1px solid var(--border); border-radius:var(--radius);
  max-height:320px; overflow-y:auto; z-index:9999;
  box-shadow:0 8px 32px rgba(0,0,0,.6); min-width:240px;
}
.font-picker-dropdown.open { display:block; }
.font-picker-option {
  padding:10px 14px; cursor:pointer; font-size:15px;
  color:var(--text); border-bottom:1px solid #222; transition:background .1s;
}
.font-picker-option:last-child { border-bottom:none; }
.font-picker-option:hover { background:#2a2a2a; }
.font-picker-option.selected { background:#1e2a1e; color:#66cc66; }
input[type=color] { -webkit-appearance:none; width:36px; height:28px;
  border:1px solid var(--border); border-radius:var(--radius); background:none; cursor:pointer; padding:2px; }
input[type=number]:focus, input[type=text]:focus, select:focus {
  outline:none; border-color:var(--accent2); }
.toggle { position:relative; width:40px; height:22px; flex-shrink:0; }
.toggle input { opacity:0; width:0; height:0; }
.toggle-slider { position:absolute; inset:0; background:var(--border);
  border-radius:11px; cursor:pointer; transition:background .2s; }
.toggle-slider:before { content:''; position:absolute; width:16px; height:16px;
  left:3px; top:3px; background:var(--accent2); border-radius:50%;
  transition:transform .2s, background .2s; }
.toggle input:checked + .toggle-slider { background:#2a5a2a; }
.toggle input:checked + .toggle-slider:before { transform:translateX(18px); background:#66cc66; }
.touch-diagram { display:flex; height:80px; border:1px solid var(--border);
  border-radius:var(--radius); overflow:hidden; margin:16px 0;
  font-size:10px; letter-spacing:.1em; text-transform:uppercase; }
.touch-zone { display:flex; align-items:center; justify-content:center;
  flex-direction:column; gap:4px; color:var(--text-dim); cursor:default; }
.touch-zone.left { background:#111820; border-right:1px solid var(--border); }
.touch-zone.centre { background:#111; border-right:1px solid var(--border); flex:1; }
.touch-zone.right { background:#182018; }
.touch-zone .zone-label { color:var(--text); font-size:11px; }
.actions { display:flex; gap:12px; margin-top:48px; flex-wrap:wrap; align-items:center; }
button { font-family:monospace; font-size:11px; letter-spacing:.15em; text-transform:uppercase;
  padding:11px 22px; border:1px solid var(--border); border-radius:var(--radius);
  cursor:pointer; transition:all .15s; background:transparent; color:var(--text); }
button:hover { border-color:var(--accent2); color:var(--accent); }
.btn-save { border-color:var(--accent2); color:var(--accent); }
.btn-save:hover { background:var(--accent); color:var(--bg); }
.btn-shutdown { border-color:#441111; color:#cc6666; margin-left:auto; }
.btn-shutdown:hover { background:var(--danger); border-color:var(--danger); color:white; }
.toast { position:fixed; bottom:24px; right:24px; background:var(--surface);
  border:1px solid var(--border); color:var(--text); padding:12px 20px;
  font-family:monospace; font-size:11px; border-radius:var(--radius);
  opacity:0; transform:translateY(8px); transition:all .2s; pointer-events:none; z-index:200; }
.toast.show { opacity:1; transform:translateY(0); }
.toast.error { border-color:var(--danger); color:#cc6666; }
.shutdown-confirm { display:none; position:fixed; inset:0; background:rgba(0,0,0,.85);
  align-items:center; justify-content:center; z-index:100; }
.shutdown-confirm.show { display:flex; }
.shutdown-dialog { background:var(--surface); border:1px solid #331111;
  padding:32px; border-radius:var(--radius); text-align:center; max-width:320px; }
.shutdown-dialog h2 { font-size:16px; font-weight:400; color:#cc6666; margin-bottom:12px; }
.shutdown-dialog p { font-size:13px; color:var(--text-dim); margin-bottom:24px; line-height:1.6; }
.dialog-actions { display:flex; gap:12px; justify-content:center; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Configuration</h1>
    <p>Roon Display</p>
    <div class="badge">HDMI · 1280×800</div>
  </header>

  <div class="section">
    <div class="section-title">Display</div>
    <div class="field">
      <div><div class="field-label">Framebuffer</div><div class="field-hint">/dev/fb0 or /dev/fb1</div></div>
      <input type="text" id="display_fb" value="{{ config.display_fb }}" style="width:130px">
    </div>
    <div class="field">
      <div><div class="field-label">Rotation</div></div>
      <select id="display_rotation">
        <option value="0" {% if config.display_rotation==0 %}selected{% endif %}>0°</option>
        <option value="90" {% if config.display_rotation==90 %}selected{% endif %}>90°</option>
        <option value="180" {% if config.display_rotation==180 %}selected{% endif %}>180°</option>
        <option value="270" {% if config.display_rotation==270 %}selected{% endif %}>270°</option>
      </select>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Roon Connection</div>
    <div class="field">
      <div><div class="field-label">Bridge Address</div></div>
      <input type="text" id="bridge" value="{{ config.bridge }}" style="width:200px">
    </div>
    <div class="field">
      <div><div class="field-label">Target Zone</div></div>
      <input type="text" id="target_zone" value="{{ config.target_zone }}">
    </div>
    <div class="field">
      <div><div class="field-label">Poll Interval</div><div class="field-hint">seconds</div></div>
      <div class="field-control">
        <input type="range" min="2" max="30" value="{{ config.poll_interval }}" oninput="update('poll_interval',this.value,'s')">
        <span class="field-value" id="poll_interval_val">{{ config.poll_interval }}s</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Track Text Font</div>
    <div class="field">
      <div><div class="field-label">Font</div><div class="field-hint">Artist / album / track lines</div></div>
      <div class="font-picker" id="picker_font_track">
        <div class="font-picker-selected" id="font_track_display" onclick="togglePicker('font_track')">Loading...</div>
        <div class="font-picker-dropdown" id="font_track_dropdown"></div>
      </div>
      <input type="hidden" id="font_track" value="{{ config.font_track }}">
    </div>
    <div class="field">
      <div><div class="field-label">Artist Size</div></div>
      <div class="field-control">
        <input type="range" min="24" max="80" value="{{ config.size_artist }}" oninput="update('size_artist',this.value,'pt')">
        <span class="field-value" id="size_artist_val">{{ config.size_artist }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Album Size</div></div>
      <div class="field-control">
        <input type="range" min="18" max="70" value="{{ config.size_album }}" oninput="update('size_album',this.value,'pt')">
        <span class="field-value" id="size_album_val">{{ config.size_album }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Track Size</div></div>
      <div class="field-control">
        <input type="range" min="18" max="70" value="{{ config.size_track }}" oninput="update('size_track',this.value,'pt')">
        <span class="field-value" id="size_track_val">{{ config.size_track }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Artist → Album Gap</div><div class="field-hint">Space below artist line</div></div>
      <div class="field-control">
        <input type="range" min="0" max="60" value="{{ config.line_spacing_artist }}" oninput="update('line_spacing_artist',this.value,'px')">
        <span class="field-value" id="line_spacing_artist_val">{{ config.line_spacing_artist }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Album → Track Gap</div><div class="field-hint">Space between album and track</div></div>
      <div class="field-control">
        <input type="range" min="0" max="30" value="{{ config.line_spacing }}" oninput="update('line_spacing',this.value,'px')">
        <span class="field-value" id="line_spacing_val">{{ config.line_spacing }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Artist Bold</div><div class="field-hint">Bold weight for artist line</div></div>
      <label class="toggle">
        <input type="checkbox" id="artist_bold" {% if config.artist_bold %}checked{% endif %}>
        <span class="toggle-slider"></span>
      </label>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Clock Font</div>
    <div class="field">
      <div><div class="field-label">Font</div><div class="field-hint">Day name and date</div></div>
      <div class="font-picker" id="picker_font_clock">
        <div class="font-picker-selected" id="font_clock_display" onclick="togglePicker('font_clock')">Loading...</div>
        <div class="font-picker-dropdown" id="font_clock_dropdown"></div>
      </div>
      <input type="hidden" id="font_clock" value="{{ config.font_clock }}">
    </div>
    <div class="field">
      <div><div class="field-label">Day Name Size</div></div>
      <div class="field-control">
        <input type="range" min="30" max="120" value="{{ config.clock_day_size }}" oninput="update('clock_day_size',this.value,'pt')">
        <span class="field-value" id="clock_day_size_val">{{ config.clock_day_size }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Date Size</div></div>
      <div class="field-control">
        <input type="range" min="24" max="100" value="{{ config.clock_date_size }}" oninput="update('clock_date_size',this.value,'pt')">
        <span class="field-value" id="clock_date_size_val">{{ config.clock_date_size }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Vertical Position</div><div class="field-hint">Offset in pixels (negative = up)</div></div>
      <div class="field-control">
        <input type="range" min="-200" max="200" value="{{ config.clock_text_y_offset }}" oninput="update('clock_text_y_offset',this.value,'px')">
        <span class="field-value" id="clock_text_y_offset_val">{{ config.clock_text_y_offset }}px</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Text Block Appearance</div>
    <div class="field">
      <div><div class="field-label">Background Opacity</div></div>
      <div class="field-control">
        <input type="range" min="0" max="255" value="{{ config.text_bg_opacity }}" oninput="update('text_bg_opacity',this.value,'')">
        <span class="field-value" id="text_bg_opacity_val">{{ config.text_bg_opacity }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Background Blur</div></div>
      <div class="field-control">
        <input type="range" min="0" max="40" value="{{ config.text_bg_blur }}" oninput="update('text_bg_blur',this.value,'')">
        <span class="field-value" id="text_bg_blur_val">{{ config.text_bg_blur }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Fade Steps</div><div class="field-hint">Frames for text fade out</div></div>
      <div class="field-control">
        <input type="range" min="5" max="40" value="{{ config.text_fade_steps }}" oninput="update('text_fade_steps',this.value,'')">
        <span class="field-value" id="text_fade_steps_val">{{ config.text_fade_steps }}</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Text & Timing</div>
    <div class="field">
      <div><div class="field-label">Text Hold</div><div class="field-hint">Seconds before fade</div></div>
      <div class="field-control">
        <input type="range" min="5" max="60" value="{{ config.text_hold }}" oninput="update('text_hold',this.value,'s')">
        <span class="field-value" id="text_hold_val">{{ config.text_hold }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Scroll Speed</div></div>
      <div class="field-control">
        <input type="range" min="0.5" max="5" step="0.1" value="{{ config.scroll_speed }}" oninput="update('scroll_speed',this.value,'s',1)">
        <span class="field-value" id="scroll_speed_val">{{ config.scroll_speed }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Scroll Hold</div></div>
      <div class="field-control">
        <input type="range" min="0.5" max="5" step="0.5" value="{{ config.scroll_hold }}" oninput="update('scroll_hold',this.value,'s',1)">
        <span class="field-value" id="scroll_hold_val">{{ config.scroll_hold }}s</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Progress Bar</div>
    <div class="field">
      <div><div class="field-label">Height</div></div>
      <div class="field-control">
        <input type="range" min="1" max="12" value="{{ config.progress_bar_height }}" oninput="update('progress_bar_height',this.value,'px')">
        <span class="field-value" id="progress_bar_height_val">{{ config.progress_bar_height }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Colour</div></div>
      <input type="color" id="progress_bar_colour" value="{{ config.progress_bar_colour }}">
    </div>
  </div>

  <div class="section">
    <div class="section-title">Art Display</div>
    <div class="field">
      <div><div class="field-label">Side Blur</div></div>
      <div class="field-control">
        <input type="range" min="5" max="80" value="{{ config.blur_radius }}" oninput="update('blur_radius',this.value,'')">
        <span class="field-value" id="blur_radius_val">{{ config.blur_radius }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Clock Background Blur</div></div>
      <div class="field-control">
        <input type="range" min="5" max="100" value="{{ config.clock_blur_radius }}" oninput="update('clock_blur_radius',this.value,'')">
        <span class="field-value" id="clock_blur_radius_val">{{ config.clock_blur_radius }}</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Clock</div>
    <div class="field">
      <div><div class="field-label">Clock Size</div><div class="field-hint">Radius in pixels</div></div>
      <div class="field-control">
        <input type="range" min="150" max="380" value="{{ config.clock_radius }}" oninput="update('clock_radius',this.value,'px')">
        <span class="field-value" id="clock_radius_val">{{ config.clock_radius }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Flip Layout</div></div>
      <label class="toggle">
        <input type="checkbox" id="clock_flip" {% if config.clock_flip %}checked{% endif %}>
        <span class="toggle-slider"></span>
      </label>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Touch Controls</div>
    <div class="touch-diagram">
      <div class="touch-zone left" id="diag-left" style="width:33%">
        <span class="zone-label" id="diag-left-label">Vol −</span><span>tap</span>
      </div>
      <div class="touch-zone centre" id="diag-centre">
        <span class="zone-label" id="diag-centre-label">Info</span><span>tap · dbl=pause</span>
      </div>
      <div class="touch-zone right" id="diag-right" style="width:33%">
        <span class="zone-label" id="diag-right-label">Vol +</span><span>tap</span>
      </div>
    </div>
    <div style="font-family:monospace;font-size:10px;color:var(--text-dim);margin-bottom:16px;letter-spacing:.1em;">
      SWIPE LEFT = next · SWIPE RIGHT = previous · LONG PRESS = heat pump
    </div>
    <div class="field">
      <div><div class="field-label">Left Zone Width</div></div>
      <div class="field-control">
        <input type="range" min="0.1" max="0.45" step="0.01" value="{{ config.touch_left_zone }}" oninput="update('touch_left_zone',this.value,'',2);updateDiagram()">
        <span class="field-value" id="touch_left_zone_val">{{ "%.2f"|format(config.touch_left_zone) }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Right Zone Start</div></div>
      <div class="field-control">
        <input type="range" min="0.55" max="0.9" step="0.01" value="{{ config.touch_right_zone }}" oninput="update('touch_right_zone',this.value,'',2);updateDiagram()">
        <span class="field-value" id="touch_right_zone_val">{{ "%.2f"|format(config.touch_right_zone) }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Left Tap Action</div></div>
      <select id="touch_action_left" onchange="updateDiagram()">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_left==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Right Tap Action</div></div>
      <select id="touch_action_right" onchange="updateDiagram()">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_right==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Centre Tap Action</div></div>
      <select id="touch_action_centre" onchange="updateDiagram()">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_centre==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Centre Double Tap</div></div>
      <select id="touch_action_double">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_double==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Swipe Left Action</div></div>
      <select id="touch_action_swipe_left">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_swipe_left==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Swipe Right Action</div></div>
      <select id="touch_action_swipe_right">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_swipe_right==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Long Press Action</div></div>
      <select id="touch_action_long">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_long==a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Long Press Duration</div></div>
      <div class="field-control">
        <input type="range" min="300" max="3000" step="100" value="{{ config.touch_long_press_ms }}" oninput="update('touch_long_press_ms',this.value,'ms')">
        <span class="field-value" id="touch_long_press_ms_val">{{ config.touch_long_press_ms }}ms</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Volume Step</div></div>
      <div class="field-control">
        <input type="range" min="1" max="20" value="{{ config.touch_vol_step }}" oninput="update('touch_vol_step',this.value,'')">
        <span class="field-value" id="touch_vol_step_val">{{ config.touch_vol_step }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Min Swipe Distance</div></div>
      <div class="field-control">
        <input type="range" min="50" max="500" value="{{ config.touch_swipe_min_dx }}" oninput="update('touch_swipe_min_dx',this.value,'px')">
        <span class="field-value" id="touch_swipe_min_dx_val">{{ config.touch_swipe_min_dx }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Max Swipe Drift</div></div>
      <div class="field-control">
        <input type="range" min="30" max="400" value="{{ config.touch_swipe_max_dy }}" oninput="update('touch_swipe_max_dy',this.value,'px')">
        <span class="field-value" id="touch_swipe_max_dy_val">{{ config.touch_swipe_max_dy }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Max Swipe Time</div></div>
      <div class="field-control">
        <input type="range" min="100" max="1500" value="{{ config.touch_swipe_max_ms }}" oninput="update('touch_swipe_max_ms',this.value,'ms')">
        <span class="field-value" id="touch_swipe_max_ms_val">{{ config.touch_swipe_max_ms }}ms</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Max Tap Movement</div></div>
      <div class="field-control">
        <input type="range" min="5" max="150" value="{{ config.touch_tap_max_move }}" oninput="update('touch_tap_max_move',this.value,'px')">
        <span class="field-value" id="touch_tap_max_move_val">{{ config.touch_tap_max_move }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Double Tap Window</div></div>
      <div class="field-control">
        <input type="range" min="100" max="800" value="{{ config.touch_double_tap_ms }}" oninput="update('touch_double_tap_ms',this.value,'ms')">
        <span class="field-value" id="touch_double_tap_ms_val">{{ config.touch_double_tap_ms }}ms</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Heat Pump URL</div></div>
      <input type="text" id="heat_pump_url" value="{{ config.heat_pump_url }}" style="width:220px">
    </div>
  </div>

  <div class="section">
    <div class="section-title">Shazam / Audio Detection</div>
    <div class="field">
      <div><div class="field-label">Silence Threshold</div></div>
      <div class="field-control">
        <input type="range" min="10" max="300" value="{{ config.silence_threshold }}" oninput="update('silence_threshold',this.value,'')">
        <span class="field-value" id="silence_threshold_val">{{ config.silence_threshold }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Silence Timeout</div></div>
      <div class="field-control">
        <input type="range" min="10" max="120" value="{{ config.silence_timeout }}" oninput="update('silence_timeout',this.value,'s')">
        <span class="field-value" id="silence_timeout_val">{{ config.silence_timeout }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Sample Interval</div></div>
      <div class="field-control">
        <input type="range" min="10" max="120" value="{{ config.sample_interval }}" oninput="update('sample_interval',this.value,'s')">
        <span class="field-value" id="sample_interval_val">{{ config.sample_interval }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Sample Duration</div></div>
      <div class="field-control">
        <input type="range" min="3" max="15" value="{{ config.sample_duration }}" oninput="update('sample_duration',this.value,'s')">
        <span class="field-value" id="sample_duration_val">{{ config.sample_duration }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Retry Delay</div></div>
      <div class="field-control">
        <input type="range" min="5" max="60" value="{{ config.retry_delay }}" oninput="update('retry_delay',this.value,'s')">
        <span class="field-value" id="retry_delay_val">{{ config.retry_delay }}s</span>
      </div>
    </div>
  </div>

  <div class="actions">
    <button class="btn-save" onclick="saveConfig()">Save Changes</button>
    <button onclick="restartDisplay()">Restart Display</button>
    <button class="btn-shutdown" onclick="showShutdown()">Shutdown</button>
  </div>
</div>

<div class="toast" id="toast"></div>
<div class="shutdown-confirm" id="shutdownConfirm">
  <div class="shutdown-dialog">
    <h2>Shutdown?</h2>
    <p>The display will power off.</p>
    <div class="dialog-actions">
      <button onclick="hideShutdown()">Cancel</button>
      <button class="btn-shutdown" onclick="confirmShutdown()">Shut Down</button>
    </div>
  </div>
</div>

<script>
function update(key, value, suffix, decimals) {
  const el = document.getElementById(key + '_val');
  if (el) {
    const v = decimals !== undefined ? parseFloat(value).toFixed(decimals) : parseInt(value);
    el.textContent = v + (suffix || '');
  }
}

// Font names injected from server
const FONT_NAMES = {{ font_names_json }};

function fontFamily(name) { return "'" + name.replace(/ /g, '_') + "'"; }

function buildPicker(fieldId, currentValue) {
  const dropdown = document.getElementById(fieldId + '_dropdown');
  const display   = document.getElementById(fieldId + '_display');
  dropdown.innerHTML = '';
  FONT_NAMES.forEach(name => {
    const opt = document.createElement('div');
    opt.className = 'font-picker-option' + (name === currentValue ? ' selected' : '');
    opt.style.fontFamily = fontFamily(name);
    opt.textContent = name;
    opt.onclick = (e) => {
      e.stopPropagation();
      selectFont(fieldId, name);
    };
    dropdown.appendChild(opt);
  });
  display.textContent = currentValue;
  display.style.fontFamily = fontFamily(currentValue);
}

function selectFont(fieldId, name) {
  document.getElementById(fieldId).value = name;
  document.getElementById(fieldId + '_display').textContent = name;
  document.getElementById(fieldId + '_display').style.fontFamily = fontFamily(name);
  document.querySelectorAll('#' + fieldId + '_dropdown .font-picker-option').forEach(o => {
    o.classList.toggle('selected', o.textContent === name);
  });
  closePickers();
}

function togglePicker(fieldId) {
  const dropdown = document.getElementById(fieldId + '_dropdown');
  const isOpen = dropdown.classList.contains('open');
  closePickers();
  if (!isOpen) {
    dropdown.classList.add('open');
    // Position dropdown below the selected display
    const display = document.getElementById(fieldId + '_display');
    const rect = display.getBoundingClientRect();
    dropdown.style.top  = (rect.bottom + 4) + 'px';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.width = Math.max(rect.width, 280) + 'px';
    // Scroll selected into view
    const sel = dropdown.querySelector('.selected');
    if (sel) sel.scrollIntoView({block:'nearest'});
  }
}

function closePickers() {
  document.querySelectorAll('.font-picker-dropdown').forEach(d => d.classList.remove('open'));
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.font-picker')) closePickers();
});

function updateDiagram() {
  const lf = parseFloat(document.querySelector('[oninput*="touch_left_zone"]').value);
  const rf = parseFloat(document.querySelector('[oninput*="touch_right_zone"]').value);
  document.getElementById('diag-left').style.width  = (lf*100).toFixed(0)+'%';
  document.getElementById('diag-right').style.width = ((1-rf)*100).toFixed(0)+'%';
  document.getElementById('diag-left-label').textContent  = document.getElementById('touch_action_left').value;
  document.getElementById('diag-right-label').textContent = document.getElementById('touch_action_right').value;
  document.getElementById('diag-centre-label').textContent = document.getElementById('touch_action_centre').value;
}

function getConfig() {
  return {
    bridge:               document.getElementById('bridge').value.trim(),
    target_zone:          document.getElementById('target_zone').value.trim(),
    poll_interval:        parseInt(document.querySelector('[oninput*="poll_interval"]').value),
    text_hold:            parseInt(document.querySelector('[oninput*="text_hold"]').value),
    text_fade_steps:      parseInt(document.querySelector('[oninput*="text_fade_steps"]').value),
    scroll_speed:         parseFloat(document.querySelector('[oninput*="scroll_speed"]').value),
    scroll_hold:          parseFloat(document.querySelector('[oninput*="scroll_hold"]').value),
    font_track:           document.getElementById('font_track').value,
    font_clock:           document.getElementById('font_clock').value,
    size_artist:          parseInt(document.querySelector('[oninput*="size_artist"]').value),
    size_album:           parseInt(document.querySelector('[oninput*="size_album"]').value),
    size_track:           parseInt(document.querySelector('[oninput*="size_track"]').value),
    line_spacing:         parseInt(document.querySelector('[oninput*="line_spacing"]:not([oninput*="artist"])').value),
    line_spacing_artist:  parseInt(document.querySelector('[oninput*="line_spacing_artist"]').value),
    artist_bold:          document.getElementById('artist_bold').checked,
    clock_day_size:       parseInt(document.querySelector('[oninput*="clock_day_size"]').value),
    clock_date_size:      parseInt(document.querySelector('[oninput*="clock_date_size"]').value),
    clock_text_y_offset:  parseInt(document.querySelector('[oninput*="clock_text_y_offset"]').value),
    text_bg_opacity:      parseInt(document.querySelector('[oninput*="text_bg_opacity"]').value),
    text_bg_blur:         parseInt(document.querySelector('[oninput*="text_bg_blur"]').value),
    progress_bar_height:  parseInt(document.querySelector('[oninput*="progress_bar_height"]').value),
    progress_bar_colour:  document.getElementById('progress_bar_colour').value,
    blur_radius:          parseInt(document.querySelector('[oninput*="blur_radius"]').value),
    clock_blur_radius:    parseInt(document.querySelector('[oninput*="clock_blur_radius"]').value),
    clock_radius:         parseInt(document.querySelector('[oninput*="clock_radius"]').value),
    clock_flip:           document.getElementById('clock_flip').checked,
    silence_threshold:    parseInt(document.querySelector('[oninput*="silence_threshold"]').value),
    silence_timeout:      parseInt(document.querySelector('[oninput*="silence_timeout"]').value),
    sample_interval:      parseInt(document.querySelector('[oninput*="sample_interval"]').value),
    sample_duration:      parseInt(document.querySelector('[oninput*="sample_duration"]').value),
    retry_delay:          parseInt(document.querySelector('[oninput*="retry_delay"]').value),
    display_fb:           document.getElementById('display_fb').value.trim(),
    display_rotation:     parseInt(document.getElementById('display_rotation').value),
    touch_swipe_min_dx:   parseInt(document.querySelector('[oninput*="touch_swipe_min_dx"]').value),
    touch_swipe_max_dy:   parseInt(document.querySelector('[oninput*="touch_swipe_max_dy"]').value),
    touch_swipe_max_ms:   parseInt(document.querySelector('[oninput*="touch_swipe_max_ms"]').value),
    touch_tap_max_move:   parseInt(document.querySelector('[oninput*="touch_tap_max_move"]').value),
    touch_double_tap_ms:  parseInt(document.querySelector('[oninput*="touch_double_tap_ms"]').value),
    touch_long_press_ms:  parseInt(document.querySelector('[oninput*="touch_long_press_ms"]').value),
    touch_vol_step:       parseInt(document.querySelector('[oninput*="touch_vol_step"]').value),
    touch_left_zone:      parseFloat(document.querySelector('[oninput*="touch_left_zone"]').value),
    touch_right_zone:     parseFloat(document.querySelector('[oninput*="touch_right_zone"]').value),
    touch_action_left:    document.getElementById('touch_action_left').value,
    touch_action_right:   document.getElementById('touch_action_right').value,
    touch_action_centre:  document.getElementById('touch_action_centre').value,
    touch_action_double:  document.getElementById('touch_action_double').value,
    touch_action_long:    document.getElementById('touch_action_long').value,
    touch_action_swipe_left:  document.getElementById('touch_action_swipe_left').value,
    touch_action_swipe_right: document.getElementById('touch_action_swipe_right').value,
    heat_pump_url:        document.getElementById('heat_pump_url').value.trim(),
  };
}

function showToast(msg, error=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (error ? ' error' : '');
  setTimeout(() => t.className = 'toast', 2500);
}

async function saveConfig() {
  const r = await fetch('/save', {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(getConfig())});
  if (r.ok) showToast('Saved'); else showToast('Error saving', true);
}

async function restartDisplay() {
  await fetch('/save', {method:'POST',
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(getConfig())});
  const r = await fetch('/restart', {method:'POST'});
  if (r.ok) showToast('Display restarting...'); else showToast('Error', true);
}

function showShutdown() { document.getElementById('shutdownConfirm').classList.add('show'); }
function hideShutdown() { document.getElementById('shutdownConfirm').classList.remove('show'); }

async function confirmShutdown() {
  hideShutdown();
  await fetch('/shutdown', {method:'POST'});
  showToast('Shutting down...');
}

// Init
updateDiagram();
buildPicker('font_track', document.getElementById('font_track').value);
buildPicker('font_clock', document.getElementById('font_clock').value);
</script>
</body>
</html>'''

@app.route('/')
def index():
    import json as _json
    config = load_config()
    font_css = build_font_css()
    font_names = list(FONTS.keys())
    html = HTML.replace("{{ font_css }}", font_css)
    html = html.replace("{{ font_names_json }}", _json.dumps(font_names))
    return render_template_string(html,
        config=type('cfg', (), config)(),
        actions=TOUCH_ACTIONS,
    )

@app.route('/fonts/<filename>')
def serve_font(filename):
    font_dirs = [
        '/usr/share/texmf/fonts/opentype/public/tex-gyre/',
        '/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/',
        '/usr/share/fonts/truetype/roboto/unhinted/',
        '/usr/share/fonts/truetype/liberation/',
        '/usr/share/fonts/truetype/dejavu/',
    ]
    for d in font_dirs:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return send_file(path)
    return "Not found", 404

@app.route('/save', methods=['POST'])
def save():
    try:
        new_cfg = request.get_json()
        cfg = load_config()
        cfg.update(new_cfg)
        save_config(cfg)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/restart', methods=['POST'])
def restart():
    try:
        subprocess.Popen(['sudo', 'systemctl', 'restart', 'roon-display'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
    app.run(host='0.0.0.0', port=8080, debug=False)
