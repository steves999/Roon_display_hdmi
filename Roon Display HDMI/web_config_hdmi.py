#!/usr/bin/env python3
"""
Roon Display Web Configuration Server — HDMI version
"""

from flask import Flask, request, jsonify, render_template_string
import json
import os
import subprocess

app = Flask(__name__)
CONFIG_FILE = os.path.expanduser("~/config.json")

DEFAULT_CONFIG = {
    # Roon
    "bridge": "http://192.168.8.118:3001",
    "target_zone": "Lounge",
    "poll_interval": 10,
    # Text & timing
    "text_hold": 20,
    "scroll_speed": 1.5,
    "scroll_hold": 2.0,
    "scroll_fps": 20,
    # Font sizes
    "size_artist": 52,
    "size_album": 42,
    "size_track": 42,
    "line_spacing": 10,
    # Text block appearance
    "text_bg_opacity": 180,
    "text_bg_blur": 16,
    # Progress bar
    "progress_bar_height": 5,
    "progress_bar_colour": "#ffffff",
    # Art display
    "blur_radius": 40,
    "clock_blur_radius": 60,
    # Clock
    "clock_radius": 300,
    "clock_cx": 900,
    "clock_date_cx": 260,
    "clock_flip": False,
    # Shazam
    "silence_threshold": 50,
    "silence_timeout": 30,
    "sample_interval": 30,
    "sample_duration": 5,
    "retry_delay": 15,
    # Display
    "display_fb": "/dev/fb0",
    "display_rotation": 0,
    # Touch thresholds
    "touch_swipe_min_dx": 250,
    "touch_swipe_max_dy": 200,
    "touch_swipe_max_ms": 600,
    "touch_tap_max_move": 30,
    "touch_double_tap_ms": 400,
    "touch_vol_step": 5,
    # Touch zone boundaries (x as fraction of screen width 0.0-1.0)
    "touch_left_zone": 0.33,
    "touch_right_zone": 0.67,
    # Touch actions
    "touch_action_left": "volume_down",
    "touch_action_right": "volume_up",
    "touch_action_centre": "toggle_text",
    "touch_action_double": "play_pause",
    "touch_action_swipe_left": "next",
    "touch_action_swipe_right": "previous",
    "touch_action_long": "heat_pump",
    "touch_long_press_ms": 1000,
    "heat_pump_url": "http://192.168.8.118:5000/",
}

TOUCH_ACTIONS = [
    "volume_up",
    "volume_down",
    "next",
    "previous",
    "play_pause",
    "toggle_text",
    "heat_pump",
    "none",
]

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

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Roon Display HDMI</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

  :root {
    --bg: #0a0a0a;
    --surface: #111111;
    --border: #222222;
    --accent: #e8e8e8;
    --accent2: #888888;
    --danger: #cc3333;
    --text: #e0e0e0;
    --text-dim: #666666;
    --radius: 4px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
    min-height: 100vh;
    padding: 40px 20px 80px;
  }

  .container { max-width: 680px; margin: 0 auto; }

  header {
    margin-bottom: 48px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 24px;
  }

  header h1 {
    font-family: 'DM Mono', monospace;
    font-weight: 300;
    font-size: 11px;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 8px;
  }

  header p { font-size: 28px; font-weight: 300; color: var(--accent); letter-spacing: -0.02em; }

  header .badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #4488cc;
    border: 1px solid #4488cc;
    padding: 2px 8px;
    border-radius: 2px;
    margin-top: 8px;
  }

  .section { margin-bottom: 40px; }

  .section-title {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }

  .field {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 13px 0;
    border-bottom: 1px solid #161616;
    gap: 16px;
  }

  .field:last-child { border-bottom: none; }
  .field-label { font-size: 14px; color: var(--text); font-weight: 400; }
  .field-hint { font-size: 11px; color: var(--text-dim); margin-top: 2px; font-family: 'DM Mono', monospace; }
  .field-control { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

  .field-value {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: var(--accent2);
    min-width: 44px;
    text-align: right;
  }

  input[type="range"] {
    -webkit-appearance: none;
    width: 140px;
    height: 2px;
    background: var(--border);
    outline: none;
    border-radius: 1px;
    flex-shrink: 0;
  }

  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px; height: 14px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    transition: transform 0.1s;
  }

  input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.2); }

  input[type="number"], input[type="text"], select {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    border-radius: var(--radius);
    width: 90px;
    text-align: center;
  }

  select { width: 140px; text-align: left; cursor: pointer; }

  input[type="color"] {
    -webkit-appearance: none;
    width: 36px; height: 28px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: none;
    cursor: pointer;
    padding: 2px;
  }

  input[type="number"]:focus, input[type="text"]:focus, select:focus {
    outline: none;
    border-color: var(--accent2);
  }

  .toggle { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .toggle-slider {
    position: absolute; inset: 0;
    background: var(--border);
    border-radius: 11px;
    cursor: pointer;
    transition: background 0.2s;
  }
  .toggle-slider:before {
    content: '';
    position: absolute;
    width: 16px; height: 16px;
    left: 3px; top: 3px;
    background: var(--accent2);
    border-radius: 50%;
    transition: transform 0.2s, background 0.2s;
  }
  .toggle input:checked + .toggle-slider { background: #2a5a2a; }
  .toggle input:checked + .toggle-slider:before { transform: translateX(18px); background: #66cc66; }

  /* Touch zone diagram */
  .touch-diagram {
    display: flex;
    height: 80px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin: 16px 0;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .touch-zone {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 4px;
    color: var(--text-dim);
    transition: background 0.2s;
    cursor: default;
  }

  .touch-zone.left  { background: #111820; border-right: 1px solid var(--border); }
  .touch-zone.centre { background: #111111; border-right: 1px solid var(--border); flex: 1; }
  .touch-zone.right { background: #182018; }
  .touch-zone .zone-label { color: var(--text); font-size: 11px; }

  .actions { display: flex; gap: 12px; margin-top: 48px; flex-wrap: wrap; align-items: center; }

  button {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    padding: 11px 22px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    transition: all 0.15s;
    background: transparent;
    color: var(--text);
  }

  button:hover { border-color: var(--accent2); color: var(--accent); }
  .btn-save { border-color: var(--accent2); color: var(--accent); }
  .btn-save:hover { background: var(--accent); color: var(--bg); }
  .btn-shutdown { border-color: #441111; color: #cc6666; margin-left: auto; }
  .btn-shutdown:hover { background: var(--danger); border-color: var(--danger); color: white; }

  .toast {
    position: fixed;
    bottom: 24px; right: 24px;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 12px 20px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    border-radius: var(--radius);
    opacity: 0;
    transform: translateY(8px);
    transition: all 0.2s;
    pointer-events: none;
    z-index: 200;
  }
  .toast.show { opacity: 1; transform: translateY(0); }
  .toast.error { border-color: var(--danger); color: #cc6666; }

  .shutdown-confirm {
    display: none;
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.85);
    align-items: center; justify-content: center;
    z-index: 100;
  }
  .shutdown-confirm.show { display: flex; }
  .shutdown-dialog {
    background: var(--surface);
    border: 1px solid #331111;
    padding: 32px;
    border-radius: var(--radius);
    text-align: center;
    max-width: 320px;
  }
  .shutdown-dialog h2 { font-size: 16px; font-weight: 400; color: #cc6666; margin-bottom: 12px; font-family: 'DM Mono', monospace; letter-spacing: 0.1em; }
  .shutdown-dialog p { font-size: 13px; color: var(--text-dim); margin-bottom: 24px; line-height: 1.6; }
  .dialog-actions { display: flex; gap: 12px; justify-content: center; }
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
      <div><div class="field-label">Framebuffer</div><div class="field-hint">Usually /dev/fb0 or /dev/fb1</div></div>
      <input type="text" id="display_fb" value="{{ config.display_fb }}" style="width:130px">
    </div>
    <div class="field">
      <div><div class="field-label">Rotation</div><div class="field-hint">Screen rotation in degrees</div></div>
      <select id="display_rotation">
        <option value="0" {% if config.display_rotation == 0 %}selected{% endif %}>0° (normal)</option>
        <option value="90" {% if config.display_rotation == 90 %}selected{% endif %}>90°</option>
        <option value="180" {% if config.display_rotation == 180 %}selected{% endif %}>180°</option>
        <option value="270" {% if config.display_rotation == 270 %}selected{% endif %}>270°</option>
      </select>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Roon Connection</div>
    <div class="field">
      <div><div class="field-label">Bridge Address</div><div class="field-hint">REST bridge IP and port</div></div>
      <input type="text" id="bridge" value="{{ config.bridge }}" style="width:180px">
    </div>
    <div class="field">
      <div><div class="field-label">Target Zone</div><div class="field-hint">Roon zone name to monitor</div></div>
      <input type="text" id="target_zone" value="{{ config.target_zone }}">
    </div>
    <div class="field">
      <div><div class="field-label">Poll Interval</div><div class="field-hint">Seconds between Roon checks</div></div>
      <div class="field-control">
        <input type="range" min="2" max="30" value="{{ config.poll_interval }}"
               oninput="update('poll_interval', this.value, 's')">
        <span class="field-value" id="poll_interval_val">{{ config.poll_interval }}s</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Text & Timing</div>
    <div class="field">
      <div><div class="field-label">Text Hold</div><div class="field-hint">Seconds before text disappears</div></div>
      <div class="field-control">
        <input type="range" min="5" max="60" value="{{ config.text_hold }}"
               oninput="update('text_hold', this.value, 's')">
        <span class="field-value" id="text_hold_val">{{ config.text_hold }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Scroll Speed</div><div class="field-hint">Seconds for full scroll</div></div>
      <div class="field-control">
        <input type="range" min="0.5" max="5" step="0.1" value="{{ config.scroll_speed }}"
               oninput="update('scroll_speed', this.value, 's', 1)">
        <span class="field-value" id="scroll_speed_val">{{ config.scroll_speed }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Scroll Hold</div><div class="field-hint">Pause before and after scroll</div></div>
      <div class="field-control">
        <input type="range" min="0.5" max="5" step="0.5" value="{{ config.scroll_hold }}"
               oninput="update('scroll_hold', this.value, 's', 1)">
        <span class="field-value" id="scroll_hold_val">{{ config.scroll_hold }}s</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Font Sizes</div>
    <div class="field">
      <div><div class="field-label">Artist</div><div class="field-hint">Top line — bold</div></div>
      <div class="field-control">
        <input type="range" min="24" max="80" value="{{ config.size_artist }}"
               oninput="update('size_artist', this.value, 'pt')">
        <span class="field-value" id="size_artist_val">{{ config.size_artist }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Album</div><div class="field-hint">Second line</div></div>
      <div class="field-control">
        <input type="range" min="18" max="70" value="{{ config.size_album }}"
               oninput="update('size_album', this.value, 'pt')">
        <span class="field-value" id="size_album_val">{{ config.size_album }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Track</div><div class="field-hint">Third line</div></div>
      <div class="field-control">
        <input type="range" min="18" max="70" value="{{ config.size_track }}"
               oninput="update('size_track', this.value, 'pt')">
        <span class="field-value" id="size_track_val">{{ config.size_track }}pt</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Line Spacing</div><div class="field-hint">Pixels between text lines</div></div>
      <div class="field-control">
        <input type="range" min="0" max="30" value="{{ config.line_spacing }}"
               oninput="update('line_spacing', this.value, 'px')">
        <span class="field-value" id="line_spacing_val">{{ config.line_spacing }}px</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Text Block Appearance</div>
    <div class="field">
      <div><div class="field-label">Background Opacity</div><div class="field-hint">Darkness of pill behind text</div></div>
      <div class="field-control">
        <input type="range" min="0" max="255" value="{{ config.text_bg_opacity }}"
               oninput="update('text_bg_opacity', this.value, '')">
        <span class="field-value" id="text_bg_opacity_val">{{ config.text_bg_opacity }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Background Blur</div><div class="field-hint">Softness of pill edges</div></div>
      <div class="field-control">
        <input type="range" min="0" max="40" value="{{ config.text_bg_blur }}"
               oninput="update('text_bg_blur', this.value, '')">
        <span class="field-value" id="text_bg_blur_val">{{ config.text_bg_blur }}</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Progress Bar</div>
    <div class="field">
      <div><div class="field-label">Height</div><div class="field-hint">Pixels</div></div>
      <div class="field-control">
        <input type="range" min="1" max="12" value="{{ config.progress_bar_height }}"
               oninput="update('progress_bar_height', this.value, 'px')">
        <span class="field-value" id="progress_bar_height_val">{{ config.progress_bar_height }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Colour</div><div class="field-hint">Progress bar fill colour</div></div>
      <div class="field-control">
        <input type="color" id="progress_bar_colour" value="{{ config.progress_bar_colour }}">
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Art Display</div>
    <div class="field">
      <div><div class="field-label">Side Blur</div><div class="field-hint">Blur radius for blurred side fill</div></div>
      <div class="field-control">
        <input type="range" min="5" max="80" value="{{ config.blur_radius }}"
               oninput="update('blur_radius', this.value, '')">
        <span class="field-value" id="blur_radius_val">{{ config.blur_radius }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Clock Background Blur</div><div class="field-hint">Blur radius for art clock background</div></div>
      <div class="field-control">
        <input type="range" min="5" max="100" value="{{ config.clock_blur_radius }}"
               oninput="update('clock_blur_radius', this.value, '')">
        <span class="field-value" id="clock_blur_radius_val">{{ config.clock_blur_radius }}</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Clock</div>
    <div class="field">
      <div><div class="field-label">Clock Size</div><div class="field-hint">Radius in pixels</div></div>
      <div class="field-control">
        <input type="range" min="150" max="380" value="{{ config.clock_radius }}"
               oninput="update('clock_radius', this.value, 'px')">
        <span class="field-value" id="clock_radius_val">{{ config.clock_radius }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Flip Layout</div><div class="field-hint">Swap clock and date sides</div></div>
      <label class="toggle">
        <input type="checkbox" id="clock_flip" {% if config.clock_flip %}checked{% endif %}>
        <span class="toggle-slider"></span>
      </label>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Touch Controls</div>

    <div class="touch-diagram" id="touchDiagram">
      <div class="touch-zone left" id="diag-left" style="width:33%">
        <span class="zone-label" id="diag-left-label">Vol −</span>
        <span>tap</span>
      </div>
      <div class="touch-zone centre" id="diag-centre">
        <span class="zone-label" id="diag-centre-label">Info</span>
        <span>tap · dbl=pause</span>
      </div>
      <div class="touch-zone right" id="diag-right" style="width:33%">
        <span class="zone-label" id="diag-right-label">Vol +</span>
        <span>tap</span>
      </div>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:10px;color:var(--text-dim);margin-bottom:16px;letter-spacing:0.1em;">
      SWIPE LEFT = next · SWIPE RIGHT = previous
    </div>

    <div class="field">
      <div><div class="field-label">Left Zone Width</div><div class="field-hint">Fraction of screen width</div></div>
      <div class="field-control">
        <input type="range" min="0.1" max="0.45" step="0.01" value="{{ config.touch_left_zone }}"
               oninput="update('touch_left_zone', this.value, '', 2); updateDiagram()">
        <span class="field-value" id="touch_left_zone_val">{{ "%.2f"|format(config.touch_left_zone) }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Right Zone Start</div><div class="field-hint">Fraction of screen width</div></div>
      <div class="field-control">
        <input type="range" min="0.55" max="0.9" step="0.01" value="{{ config.touch_right_zone }}"
               oninput="update('touch_right_zone', this.value, '', 2); updateDiagram()">
        <span class="field-value" id="touch_right_zone_val">{{ "%.2f"|format(config.touch_right_zone) }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Left Tap Action</div><div class="field-hint">What left zone tap does</div></div>
      <select id="touch_action_left" onchange="updateDiagram()">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_left == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Right Tap Action</div><div class="field-hint">What right zone tap does</div></div>
      <select id="touch_action_right" onchange="updateDiagram()">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_right == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Centre Tap Action</div><div class="field-hint">Single tap in centre</div></div>
      <select id="touch_action_centre" onchange="updateDiagram()">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_centre == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Centre Double Tap</div><div class="field-hint">Double tap in centre</div></div>
      <select id="touch_action_double">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_double == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Swipe Left Action</div><div class="field-hint">Left swipe gesture</div></div>
      <select id="touch_action_swipe_left">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_swipe_left == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Swipe Right Action</div><div class="field-hint">Right swipe gesture</div></div>
      <select id="touch_action_swipe_right">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_swipe_right == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Volume Step</div><div class="field-hint">Volume change per tap</div></div>
      <div class="field-control">
        <input type="range" min="1" max="20" value="{{ config.touch_vol_step }}"
               oninput="update('touch_vol_step', this.value, '')">
        <span class="field-value" id="touch_vol_step_val">{{ config.touch_vol_step }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Min Swipe Distance</div><div class="field-hint">Pixels to trigger a swipe</div></div>
      <div class="field-control">
        <input type="range" min="50" max="500" value="{{ config.touch_swipe_min_dx }}"
               oninput="update('touch_swipe_min_dx', this.value, 'px')">
        <span class="field-value" id="touch_swipe_min_dx_val">{{ config.touch_swipe_min_dx }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Max Swipe Drift</div><div class="field-hint">Max vertical drift for swipe</div></div>
      <div class="field-control">
        <input type="range" min="30" max="400" value="{{ config.touch_swipe_max_dy }}"
               oninput="update('touch_swipe_max_dy', this.value, 'px')">
        <span class="field-value" id="touch_swipe_max_dy_val">{{ config.touch_swipe_max_dy }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Max Swipe Time</div><div class="field-hint">Milliseconds to complete swipe</div></div>
      <div class="field-control">
        <input type="range" min="100" max="1500" value="{{ config.touch_swipe_max_ms }}"
               oninput="update('touch_swipe_max_ms', this.value, 'ms')">
        <span class="field-value" id="touch_swipe_max_ms_val">{{ config.touch_swipe_max_ms }}ms</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Max Tap Movement</div><div class="field-hint">Pixels — above this = not a tap</div></div>
      <div class="field-control">
        <input type="range" min="5" max="150" value="{{ config.touch_tap_max_move }}"
               oninput="update('touch_tap_max_move', this.value, 'px')">
        <span class="field-value" id="touch_tap_max_move_val">{{ config.touch_tap_max_move }}px</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Double Tap Window</div><div class="field-hint">Max ms between taps</div></div>
      <div class="field-control">
        <input type="range" min="100" max="800" value="{{ config.touch_double_tap_ms }}"
               oninput="update('touch_double_tap_ms', this.value, 'ms')">
        <span class="field-value" id="touch_double_tap_ms_val">{{ config.touch_double_tap_ms }}ms</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Long Press Action</div><div class="field-hint">Hold anywhere on screen</div></div>
      <select id="touch_action_long">
        {% for a in actions %}<option value="{{ a }}" {% if config.touch_action_long == a %}selected{% endif %}>{{ a }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <div><div class="field-label">Long Press Duration</div><div class="field-hint">Milliseconds to trigger</div></div>
      <div class="field-control">
        <input type="range" min="300" max="3000" step="100" value="{{ config.touch_long_press_ms }}"
               oninput="update('touch_long_press_ms', this.value, 'ms')">
        <span class="field-value" id="touch_long_press_ms_val">{{ config.touch_long_press_ms }}ms</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Heat Pump URL</div><div class="field-hint">URL for heat pump control</div></div>
      <input type="text" id="heat_pump_url" value="{{ config.heat_pump_url }}" style="width:220px">
    </div>
  </div>

  <div class="section">
    <div class="section-title">Shazam / Audio Detection</div>
    <div class="field">
      <div><div class="field-label">Silence Threshold</div><div class="field-hint">RMS below this = silence</div></div>
      <div class="field-control">
        <input type="range" min="10" max="300" value="{{ config.silence_threshold }}"
               oninput="update('silence_threshold', this.value, '')">
        <span class="field-value" id="silence_threshold_val">{{ config.silence_threshold }}</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Silence Timeout</div><div class="field-hint">Seconds before returning to clock</div></div>
      <div class="field-control">
        <input type="range" min="10" max="120" value="{{ config.silence_timeout }}"
               oninput="update('silence_timeout', this.value, 's')">
        <span class="field-value" id="silence_timeout_val">{{ config.silence_timeout }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Sample Interval</div><div class="field-hint">Seconds between Shazam samples</div></div>
      <div class="field-control">
        <input type="range" min="10" max="120" value="{{ config.sample_interval }}"
               oninput="update('sample_interval', this.value, 's')">
        <span class="field-value" id="sample_interval_val">{{ config.sample_interval }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Sample Duration</div><div class="field-hint">Seconds of audio to record</div></div>
      <div class="field-control">
        <input type="range" min="3" max="15" value="{{ config.sample_duration }}"
               oninput="update('sample_duration', this.value, 's')">
        <span class="field-value" id="sample_duration_val">{{ config.sample_duration }}s</span>
      </div>
    </div>
    <div class="field">
      <div><div class="field-label">Retry Delay</div><div class="field-hint">Seconds between retries on no match</div></div>
      <div class="field-control">
        <input type="range" min="5" max="60" value="{{ config.retry_delay }}"
               oninput="update('retry_delay', this.value, 's')">
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
    <p>The display will power off. You'll need to physically restart it.</p>
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

function updateDiagram() {
  const leftFrac  = parseFloat(document.querySelector('[oninput*="touch_left_zone"]').value);
  const rightFrac = parseFloat(document.querySelector('[oninput*="touch_right_zone"]').value);
  const leftPct   = (leftFrac * 100).toFixed(0) + '%';
  const rightPct  = ((1 - rightFrac) * 100).toFixed(0) + '%';
  document.getElementById('diag-left').style.width  = leftPct;
  document.getElementById('diag-right').style.width = rightPct;
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
    scroll_speed:         parseFloat(document.querySelector('[oninput*="scroll_speed"]').value),
    scroll_hold:          parseFloat(document.querySelector('[oninput*="scroll_hold"]').value),
    size_artist:          parseInt(document.querySelector('[oninput*="size_artist"]').value),
    size_album:           parseInt(document.querySelector('[oninput*="size_album"]').value),
    size_track:           parseInt(document.querySelector('[oninput*="size_track"]').value),
    line_spacing:         parseInt(document.querySelector('[oninput*="line_spacing"]').value),
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
    touch_vol_step:       parseInt(document.querySelector('[oninput*="touch_vol_step"]').value),
    touch_left_zone:      parseFloat(document.querySelector('[oninput*="touch_left_zone"]').value),
    touch_right_zone:     parseFloat(document.querySelector('[oninput*="touch_right_zone"]').value),
    touch_action_left:    document.getElementById('touch_action_left').value,
    touch_action_right:   document.getElementById('touch_action_right').value,
    touch_action_centre:  document.getElementById('touch_action_centre').value,
    touch_action_double:  document.getElementById('touch_action_double').value,
    touch_action_swipe_left:  document.getElementById('touch_action_swipe_left').value,
    touch_action_swipe_right: document.getElementById('touch_action_swipe_right').value,
    touch_action_long:        document.getElementById('touch_action_long').value,
    touch_long_press_ms:      parseInt(document.querySelector('[oninput*="touch_long_press_ms"]').value),
    heat_pump_url:            document.getElementById('heat_pump_url').value.trim(),
  };
}

function showToast(msg, error=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (error ? ' error' : '');
  setTimeout(() => t.className = 'toast', 2500);
}

async function saveConfig() {
  const r = await fetch('/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(getConfig())
  });
  if (r.ok) showToast('Saved');
  else showToast('Error saving', true);
}

async function restartDisplay() {
  await fetch('/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(getConfig())
  });
  const r = await fetch('/restart', {method: 'POST'});
  if (r.ok) showToast('Display restarting...');
  else showToast('Error', true);
}

function showShutdown() { document.getElementById('shutdownConfirm').classList.add('show'); }
function hideShutdown() { document.getElementById('shutdownConfirm').classList.remove('show'); }

async function confirmShutdown() {
  hideShutdown();
  await fetch('/shutdown', {method: 'POST'});
  showToast('Shutting down...');
}

// Init diagram
updateDiagram();
</script>
</body>
</html>'''

@app.route('/')
def index():
    config = load_config()
    return render_template_string(HTML, config=type('cfg', (), config)(), actions=TOUCH_ACTIONS)

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
