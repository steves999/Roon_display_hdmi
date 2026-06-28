import requests
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from io import BytesIO
import time
import math
from datetime import datetime
import json
import os
import shazam_listener
import touch_handler

CONFIG_FILE = os.path.expanduser("~/config.json")

W = 1280
H = 800

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

KNOWN_STATIONS = {}
STATION_OVERLAY_SIZE = 220

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    return DEFAULT_CONFIG.copy()

cfg = load_config()
config_mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0

def maybe_reload_config():
    global cfg, config_mtime
    if os.path.exists(CONFIG_FILE):
        mtime = os.path.getmtime(CONFIG_FILE)
        if mtime != config_mtime:
            cfg = load_config()
            config_mtime = mtime
            print("Config reloaded")

FB = "/dev/fb0"
FONT_BOLD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-bold.otf"
FONT_REG  = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf"
PAD        = 16
MARGIN     = 20
MAX_TEXT_W = 768

_station_logo_cache   = {}
_stream_overlay_cache = {}
_touch_show_text      = False


def on_touch_event(event, data=None):
    global _touch_show_text
    if event == "toggle_text" and data == True:
        _touch_show_text = True


def detect_station(line1):
    for name in KNOWN_STATIONS:
        if name.lower() in line1.lower():
            return name
    return None

def is_radio_stream(image_key='', line1='', seek_position=None, length=None):
    if length is None:
        return True
    if image_key and len(image_key) > 50:
        return True
    if line1 and detect_station(line1):
        return True
    return False

def get_station_logo(station_name):
    if station_name in _station_logo_cache:
        return _station_logo_cache[station_name]
    info = KNOWN_STATIONS.get(station_name, {})
    url  = info.get("logo_url")
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        img = Image.open(BytesIO(r.content)).convert('RGBA')
        img = img.resize((STATION_OVERLAY_SIZE, STATION_OVERLAY_SIZE), Image.LANCZOS)
        _station_logo_cache[station_name] = img
        print(f"[Logo] Fetched logo for {station_name}")
        return img
    except Exception as e:
        print(f"[Logo] Error: {e}")
        _station_logo_cache[station_name] = None
        return None

def get_stream_overlay(station_name, image_key):
    if station_name:
        logo = get_station_logo(station_name)
        if logo:
            return logo
    if image_key:
        if image_key in _stream_overlay_cache:
            return _stream_overlay_cache[image_key]
        try:
            art = get_art(image_key)
            if art:
                art = art.convert('RGBA').resize(
                    (STATION_OVERLAY_SIZE, STATION_OVERLAY_SIZE), Image.LANCZOS
                )
                _stream_overlay_cache[image_key] = art
                print(f"[Logo] Cached stream art overlay")
                return art
        except Exception as e:
            print(f"[Logo] Stream overlay error: {e}")
        _stream_overlay_cache[image_key] = None
    return None

def overlay_station_logo(canvas, logo, alpha=200):
    if logo is None:
        return canvas
    x = W - STATION_OVERLAY_SIZE - 16
    y = H - STATION_OVERLAY_SIZE - 16
    rgba = canvas.convert('RGBA')
    logo_copy = logo.copy().convert('RGBA')
    r, g, b, a = logo_copy.split()
    a = a.point(lambda p: int(p * alpha / 255))
    size = logo_copy.size
    feather = 24
    mask = Image.new('L', size, 0)
    inner = Image.new('L', (size[0] - feather*2, size[1] - feather*2), 255)
    mask.paste(inner, (feather, feather))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))
    a = Image.composite(a, Image.new('L', size, 0), mask)
    logo_copy = Image.merge('RGBA', (r, g, b, a))
    rgba.paste(logo_copy, (x, y), logo_copy)
    return rgba.convert('RGB')

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def write_fb(img):
    fb = cfg.get("display_fb", "/dev/fb0")
    rotation = cfg.get("display_rotation", 0)
    if rotation != 0:
        img = img.rotate(rotation, expand=True)
    img = img.convert('RGB')
    r = np.array(img)[:, :, 0].astype(np.uint16)
    g = np.array(img)[:, :, 1].astype(np.uint16)
    b = np.array(img)[:, :, 2].astype(np.uint16)
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    with open(fb, 'wb') as f:
        f.write(rgb565.astype(np.uint16).tobytes())


# --- Volume indicator ---

def get_volume_pct(zone):
    try:
        vol = zone["outputs"][0]["volume"]
        v   = vol["value"]
        mn  = vol["min"]
        mx  = vol["max"]
        return max(0, min(100, (v - mn) / (mx - mn) * 100))
    except:
        return None

def draw_volume_circle(canvas, pct, cx=56, cy=728, radius=38):
    if pct is None:
        return canvas
    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                 fill=(60, 60, 60, 80), outline=(140, 140, 140, 100), width=3)
    if pct > 1:
        sweep = int(360 * pct / 100)
        draw.pieslice([cx-radius, cy-radius, cx+radius, cy+radius],
                      start=-90, end=-90+sweep,
                      fill=(255, 255, 255, 100))
    return Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')


# --- Clock ---

def draw_clock_on_canvas(canvas, show_mic=False):
    now  = datetime.now()
    draw = ImageDraw.Draw(canvas)
    r    = cfg["clock_radius"]
    flip = cfg.get("clock_flip", False)
    if flip:
        cx      = W - cfg["clock_cx"]
        date_cx = W - cfg["clock_date_cx"]
    else:
        cx      = cfg["clock_cx"]
        date_cx = cfg["clock_date_cx"]
    cy = H // 2

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        if i % 3 == 0:
            inner, outer, w = r - 32, r - 6, 4
        else:
            inner, outer, w = r - 20, r - 6, 3
        x1 = cx + inner * math.cos(angle)
        y1 = cy + inner * math.sin(angle)
        x2 = cx + outer * math.cos(angle)
        y2 = cy + outer * math.sin(angle)
        draw.line([x1, y1, x2, y2], fill=(255, 255, 255), width=w)

    hour_angle = math.radians((now.hour % 12) * 30 + now.minute * 0.5 - 90)
    hx = cx + (r * 0.55) * math.cos(hour_angle)
    hy = cy + (r * 0.55) * math.sin(hour_angle)
    draw.line([cx, cy, hx, hy], fill=(255, 255, 255), width=10)

    min_angle = math.radians(now.minute * 6 - 90)
    mx = cx + (r * 0.8) * math.cos(min_angle)
    my = cy + (r * 0.8) * math.sin(min_angle)
    draw.line([cx, cy, mx, my], fill=(255, 255, 255), width=6)
    draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(255, 255, 255))

    day_str  = now.strftime("%A")
    date_str = now.strftime("%-d %B %y")
    font_day  = ImageFont.truetype(FONT_BOLD, 70)
    font_date = ImageFont.truetype(FONT_REG,  66)

    def text_w(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    dw, dh   = text_w(day_str,  font_day)
    dtw, dth = text_w(date_str, font_date)
    gap     = 24
    total_h = dh + gap + dth
    text_y  = (H - total_h) // 2
    draw.text((date_cx - dw  // 2, text_y),            day_str,  font=font_day,  fill=(255, 255, 255))
    draw.text((date_cx - dtw // 2, text_y + dh + gap), date_str, font=font_date, fill=(180, 180, 180))

    if show_mic:
        rgba = canvas.convert('RGBA')
        shazam_listener.draw_mic_icon(rgba, x=1210, y=758, color=(220, 220, 220, 200), size=44)
        canvas = rgba.convert('RGB')

    return canvas


def make_plain_clock_screen(show_mic=False):
    canvas = Image.new('RGB', (W, H), (0, 0, 0))
    return draw_clock_on_canvas(canvas, show_mic=show_mic)


def make_art_clock_screen(art, show_mic=False):
    canvas = art.resize((W, H), Image.LANCZOS)
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=cfg["clock_blur_radius"]))
    overlay = Image.new('RGB', (W, H), (0, 0, 0))
    canvas = Image.blend(canvas, overlay, alpha=0.3)
    return draw_clock_on_canvas(canvas, show_mic=show_mic)


# --- Art screen ---

def make_base_screen(art, station_overlay=None):
    canvas = Image.new('RGB', (W, H), (0, 0, 0))
    bg = art.resize((W, H), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=cfg["blur_radius"]))
    canvas.paste(bg, (0, 0))
    fg = art.resize((H, H), Image.LANCZOS)
    canvas.paste(fg, ((W - H) // 2, 0))
    if station_overlay:
        canvas = overlay_station_logo(canvas, station_overlay)
    return canvas

def draw_progress(canvas, seek_pos, length):
    if seek_pos is not None and length and length > 0:
        draw = ImageDraw.Draw(canvas)
        progress = seek_pos / length
        bh    = cfg["progress_bar_height"]
        bar_y = H - bh
        col   = hex_to_rgb(cfg["progress_bar_colour"])
        draw.rectangle([0, bar_y, W, H], fill=(40, 40, 40))
        draw.rectangle([0, bar_y, int(W * progress), H], fill=col)
    return canvas

def measure_text(text, font):
    dummy = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def make_text_overlay(artist, album, track, scroll_line=None, scroll_offset=0, source='roon'):
    font_artist = ImageFont.truetype(FONT_BOLD, cfg["size_artist"])
    font_album  = ImageFont.truetype(FONT_REG,  cfg["size_album"])
    font_track  = ImageFont.truetype(FONT_REG,  cfg["size_track"])

    aw, ah = measure_text(artist, font_artist)
    lw, lh = measure_text(album,  font_album)
    tw, th = measure_text(track,  font_track)

    ls = cfg["line_spacing"]
    display_w = max(aw, lw, tw)
    block_w   = display_w + PAD * 2
    block_h   = ah + lh + th + ls * 2 + PAD * 2

    x = MARGIN
    y = H - block_h - MARGIN - cfg["progress_bar_height"] - 6

    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [x - 12, y - 12, x + block_w + 12, y + block_h + 12],
        fill=(0, 0, 0, cfg["text_bg_opacity"])
    )
    if cfg["text_bg_blur"] > 0:
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=cfg["text_bg_blur"]))
    overlay_draw = ImageDraw.Draw(overlay)

    def draw_line(text, font, ty, color, line_key):
        w, h = measure_text(text, font)
        tx = x + PAD
        if line_key == scroll_line and scroll_offset > 0:
            tmp = Image.new('RGBA', (w + 10, h + 4), (0, 0, 0, 0))
            tmp_draw = ImageDraw.Draw(tmp)
            tmp_draw.text((0, 0), text, font=font, fill=color)
            crop_w  = min(block_w - PAD * 2, w)
            cropped = tmp.crop((scroll_offset, 0, scroll_offset + crop_w, h + 4))
            overlay.paste(cropped, (tx, ty), cropped)
        else:
            overlay_draw.text((tx, ty), text, font=font, fill=color)

    ty = y + PAD
    draw_line(artist, font_artist, ty, (255, 255, 255, 255), 'artist')
    ty += ah + ls
    draw_line(album,  font_album,  ty, (220, 220, 220, 255), 'album')
    ty += lh + ls
    draw_line(track,  font_track,  ty, (220, 220, 220, 255), 'track')

    if source == 'shazam':
        font_icon = ImageFont.truetype(FONT_REG, 32)
        overlay_draw.text((W - 40, H - 40), '♩', font=font_icon, fill=(180, 180, 180, 200))

    return overlay

def composite(base, overlay, seek_pos=None, length=None):
    canvas = base.copy().convert('RGBA')
    canvas = Image.alpha_composite(canvas, overlay)
    canvas = canvas.convert('RGB')
    if seek_pos is not None:
        canvas = draw_progress(canvas, seek_pos, length)
    return canvas

def fade_out_overlay(base, overlay, seek_pos, length):
    """Fade text overlay out over ~1 second."""
    steps = cfg.get("text_fade_steps", 20)
    frame_time = 1.0 / steps
    for step in range(steps):
        zone_check = get_zone()
        if not zone_check or zone_check["state"] != "playing":
            break
        fade_alpha = 1.0 - (step / steps)
        # Scale overlay alpha channel
        r, g, b, a = overlay.convert('RGBA').split()
        a = a.point(lambda p: int(p * fade_alpha))
        faded = Image.merge('RGBA', (r, g, b, a))
        canvas = base.copy().convert('RGBA')
        canvas = Image.alpha_composite(canvas, faded)
        canvas = canvas.convert('RGB')
        if seek_pos is not None:
            canvas = draw_progress(canvas, seek_pos, length)
        write_fb(canvas)
        time.sleep(frame_time)


def display_roon(base, artist, album, track, seek_pos, length, radio=False, track_id=None):
    global _touch_show_text
    font_artist = ImageFont.truetype(FONT_BOLD, cfg["size_artist"])
    font_album  = ImageFont.truetype(FONT_REG,  cfg["size_album"])
    font_track  = ImageFont.truetype(FONT_REG,  cfg["size_track"])

    aw, _ = measure_text(artist, font_artist)
    lw, _ = measure_text(album,  font_album)
    tw, _ = measure_text(track,  font_track)

    widths       = {'artist': aw, 'album': lw, 'track': tw}
    longest_line = max(widths, key=widths.get)
    longest_w    = widths[longest_line]
    overflow     = longest_w - MAX_TEXT_W

    overlay = make_text_overlay(artist, album, track, source='roon')
    write_fb(composite(base, overlay, seek_pos, length))

    if overflow > 0:
        time.sleep(cfg["scroll_hold"])
        total_frames = int(cfg["scroll_fps"] * cfg["scroll_speed"])
        frame_time   = 1.0 / cfg["scroll_fps"]
        aborted = False
        for frame in range(total_frames + 1):
            zone_check = get_zone()
            if not zone_check or zone_check["state"] != "playing":
                aborted = True
                break
            offset  = int(overflow * frame / total_frames)
            overlay = make_text_overlay(artist, album, track,
                                        scroll_line=longest_line,
                                        scroll_offset=offset,
                                        source='roon')
            write_fb(composite(base, overlay, seek_pos, length))
            time.sleep(frame_time)

        if not aborted:
            time.sleep(cfg["scroll_hold"])
            overlay = make_text_overlay(artist, album, track, source='roon')
            write_fb(composite(base, overlay, seek_pos, length))

    # Text hold
    for _ in range(cfg["text_hold"]):
        zone_check = get_zone()
        if not zone_check or zone_check["state"] != "playing":
            break
        seek_pos = zone_check["now_playing"].get("seek_position")
        length   = zone_check["now_playing"].get("length")
        write_fb(composite(base, overlay, seek_pos, length))
        time.sleep(1)

    # Fade out text overlay
    zone_check = get_zone()
    if zone_check and zone_check["state"] == "playing":
        seek_pos = zone_check["now_playing"].get("seek_position")
        length   = zone_check["now_playing"].get("length")
        fade_out_overlay(base, overlay, seek_pos, length)

    # Idle loop — clean art with volume circle, touch to re-show text
    while True:
        zone_check = get_zone()
        if not zone_check or zone_check["state"] != "playing":
            break
        np_check = zone_check["now_playing"]
        if radio:
            current = np_check["two_line"]["line2"]
            compare = track_id or track
        else:
            current = np_check["two_line"]["line1"]
            compare = track
        if current != compare:
            break

        # Touch requested text re-display
        if _touch_show_text:
            _touch_show_text = False
            overlay = make_text_overlay(artist, album, track, source='roon')
            for _ in range(cfg["text_hold"]):
                zone_check2 = get_zone()
                if not zone_check2 or zone_check2["state"] != "playing":
                    break
                seek_pos = zone_check2["now_playing"].get("seek_position")
                length   = zone_check2["now_playing"].get("length")
                write_fb(composite(base, overlay, seek_pos, length))
                time.sleep(1)
            # Fade out again
            zone_check2 = get_zone()
            if zone_check2 and zone_check2["state"] == "playing":
                seek_pos = zone_check2["now_playing"].get("seek_position")
                length   = zone_check2["now_playing"].get("length")
                fade_out_overlay(base, overlay, seek_pos, length)
            continue

        seek_pos = np_check.get("seek_position")
        length   = np_check.get("length")
        vol_pct  = get_volume_pct(zone_check)
        screen   = base.copy()
        screen   = draw_progress(screen, seek_pos, length)
        screen   = draw_volume_circle(screen, vol_pct)
        write_fb(screen)
        time.sleep(5)


def display_shazam(base, artist, album, track):
    font_artist = ImageFont.truetype(FONT_BOLD, cfg["size_artist"])
    font_album  = ImageFont.truetype(FONT_REG,  cfg["size_album"])
    font_track  = ImageFont.truetype(FONT_REG,  cfg["size_track"])

    aw, _ = measure_text(artist, font_artist)
    lw, _ = measure_text(album,  font_album)
    tw, _ = measure_text(track,  font_track)

    widths       = {'artist': aw, 'album': lw, 'track': tw}
    longest_line = max(widths, key=widths.get)
    longest_w    = widths[longest_line]
    overflow     = longest_w - MAX_TEXT_W

    overlay = make_text_overlay(artist, album, track, source='shazam')
    write_fb(composite(base, overlay))

    if overflow > 0:
        time.sleep(cfg["scroll_hold"])
        total_frames = int(cfg["scroll_fps"] * cfg["scroll_speed"])
        frame_time   = 1.0 / cfg["scroll_fps"]
        for frame in range(total_frames + 1):
            offset  = int(overflow * frame / total_frames)
            overlay = make_text_overlay(artist, album, track,
                                        scroll_line=longest_line,
                                        scroll_offset=offset,
                                        source='shazam')
            write_fb(composite(base, overlay))
            time.sleep(frame_time)

        time.sleep(cfg["scroll_hold"])
        overlay = make_text_overlay(artist, album, track, source='shazam')
        write_fb(composite(base, overlay))

    for _ in range(cfg["text_hold"]):
        time.sleep(1)

    # Fade out shazam overlay too
    fade_out_overlay(base, overlay, None, None)

    clean = base.copy()
    rgba  = clean.convert('RGBA')
    draw  = ImageDraw.Draw(rgba)
    font_icon = ImageFont.truetype(FONT_REG, 32)
    draw.text((W - 40, H - 40), '♩', font=font_icon, fill=(180, 180, 180, 200))
    write_fb(rgba.convert('RGB'))


# --- Roon API ---

def get_zone():
    try:
        r = requests.get(f"{cfg['bridge']}/roonAPI/listZones", timeout=5)
        zones = r.json()["zones"]
        return next((z for z in zones if z["display_name"] == cfg["target_zone"]), None)
    except Exception as e:
        print(f"Error getting zone: {e}")
        return None

def get_art(image_key):
    try:
        r = requests.get(f"{cfg['bridge']}/roonAPI/getOriginalImage?image_key={image_key}", timeout=10)
        return Image.open(BytesIO(r.content))
    except Exception as e:
        print(f"Error getting art: {e}")
        return None

def clean_track_for_itunes(track):
    for sep in ['|', '(', '[']:
        track = track.split(sep)[0]
    return track.strip()

def get_itunes_art(artist, track):
    try:
        track = clean_track_for_itunes(track)
        query = requests.utils.quote(f"{artist} {track}")
        r = requests.get(
            f"https://itunes.apple.com/search?term={query}&entity=song&limit=1",
            timeout=10
        )
        data = r.json()
        if data['resultCount'] > 0:
            url = data['results'][0].get('artworkUrl100', '')
            if url:
                url = url.replace('100x100', '600x600')
                img_r = requests.get(url, timeout=10)
                img = Image.open(BytesIO(img_r.content))
                print(f"[iTunes] Art found for {artist} - {track}")
                return img
        print(f"[iTunes] No art found for {artist} - {track}")
    except Exception as e:
        print(f"[iTunes] Error: {e}")
    return None

def get_station_fallback_art(station_name, image_key):
    if image_key:
        art = get_art(image_key)
        if art:
            print(f"[Roon] Using stream art as fallback")
            return art
    if station_name:
        info = KNOWN_STATIONS.get(station_name, {})
        url  = info.get("logo_url")
        if url:
            try:
                r = requests.get(url, timeout=10)
                logo = Image.open(BytesIO(r.content)).convert('RGBA')
                canvas = Image.new('RGB', (800, 800), (20, 20, 20))
                logo_large = logo.resize((400, 400), Image.LANCZOS)
                canvas.paste(logo_large, (200, 200), logo_large)
                return canvas
            except Exception as e:
                print(f"[Logo] Fallback art error: {e}")
    return None

def parse_radio_track(line2):
    if ' - ' in line2:
        parts = line2.split(' - ', 1)
        return parts[0].strip(), parts[1].strip()
    return '', line2.strip()


# --- Main loop ---

last_image_key    = None
last_track        = None
last_art          = None
clock_idle_since  = None
clock_last_min    = -1
shazam_active     = False
last_shazam_track = None
last_mic_state    = False

print("Starting Roon display (HDMI 1280x800)...")

touch_handler.set_callback(on_touch_event)
touch_handler.start(bridge=cfg["bridge"])

while True:
    maybe_reload_config()
    zone = get_zone()

    if zone and zone["state"] == "playing" and "now_playing" in zone:
        zone_id   = zone.get("zone_id")
        output_id = zone["outputs"][0].get("output_id") if zone.get("outputs") else None
        vol_pct   = get_volume_pct(zone)
        touch_handler.configure(cfg["bridge"], zone_id, output_id, vol_pct)

        if shazam_active:
            shazam_listener.stop()
            shazam_active     = False
            last_shazam_track = None
            last_mic_state    = False

        np_info   = zone["now_playing"]
        image_key = np_info.get("image_key")
        line1     = np_info["two_line"]["line1"]
        line2     = np_info["two_line"]["line2"]
        album     = np_info.get("three_line", {}).get("line3", "")
        seek_pos  = np_info.get("seek_position")
        length    = np_info.get("length")

        clock_idle_since = None
        clock_last_min   = -1

        station_name = detect_station(line1)
        radio = is_radio_stream(image_key, line1, seek_pos, length)

        if radio and ' - ' in line2:
            radio_artist, radio_track = parse_radio_track(line2)
            display_artist = radio_artist
            display_track  = radio_track
            display_album  = line1
            use_itunes     = True
            track_id       = line2
        else:
            display_artist = line2
            display_track  = line1
            display_album  = album
            use_itunes     = False
            track_id       = line1
            if not radio:
                station_name = None

        if not display_artist and not line2.strip():
            print(f"[Roon] No metadata yet — retrying...")
            if image_key != last_image_key:
                fallback = get_station_fallback_art(station_name, image_key) if station_name else get_art(image_key)
                if fallback:
                    st_overlay = get_stream_overlay(station_name, image_key)
                    last_art   = fallback
                    base       = make_base_screen(fallback, station_overlay=st_overlay)
                    write_fb(base)
                last_image_key = image_key
            last_track = None
            time.sleep(2)
            continue

        if (image_key or track_id) and (image_key != last_image_key or track_id != last_track):
            print(f"[Roon] Now playing: {display_artist} / {display_album} / {display_track}")
            new_art = None

            if use_itunes:
                print(f"[iTunes] Fetching art for {display_artist} - {display_track}")
                new_art = get_itunes_art(display_artist, display_track)

            if not new_art and use_itunes:
                print(f"[Roon] iTunes failed — using station fallback art")
                new_art = get_station_fallback_art(station_name, image_key)
                last_image_key = image_key
                last_track     = None
            elif not new_art and image_key:
                new_art = get_art(image_key)
                last_image_key = image_key
                last_track     = track_id
            else:
                last_image_key = image_key
                last_track     = track_id

            if new_art:
                st_overlay = get_stream_overlay(station_name, image_key) if radio else None
                last_art   = new_art
                base       = make_base_screen(new_art, station_overlay=st_overlay)
                display_roon(base, display_artist, display_album, display_track,
                             seek_pos, length, radio=radio, track_id=line2)

    else:
        if last_image_key is not None:
            print("Roon stopped")
            last_image_key   = None
            last_track       = None
            clock_idle_since = time.time()
            clock_last_min   = -1

        if not shazam_active:
            shazam_listener.start()
            shazam_active = True

        mic_sampling  = shazam_listener.is_sampling()
        shazam_track  = shazam_listener.get_current_track()
        silence_secs  = shazam_listener.seconds_since_sound()

        if silence_secs > cfg["silence_timeout"] + cfg["sample_interval"] and last_shazam_track is not None:
            print(f"[Shazam] Silence {silence_secs:.0f}s — returning to clock")
            last_shazam_track = None
            clock_last_min    = -1

        if (shazam_track is not None
                and silence_secs <= cfg["silence_timeout"] + cfg["sample_interval"]
                and (last_shazam_track is None
                     or shazam_track['title'] != last_shazam_track['title']
                     or shazam_track['artist'] != last_shazam_track['artist'])):
            print(f"[Shazam] New track: {shazam_track['artist']} - {shazam_track['title']}")
            art = shazam_listener.fetch_art(shazam_track['art_url'])
            if art:
                last_art          = art
                last_shazam_track = shazam_track
                clock_idle_since  = None
                clock_last_min    = -1
                last_mic_state    = False
                base = make_base_screen(art)
                display_shazam(base,
                               shazam_track['artist'],
                               shazam_track['album'],
                               shazam_track['title'])

        elif last_shazam_track is None:
            now = datetime.now()
            if now.minute != clock_last_min or mic_sampling != last_mic_state:
                if last_art is not None:
                    write_fb(make_art_clock_screen(last_art, show_mic=mic_sampling))
                else:
                    write_fb(make_plain_clock_screen(show_mic=mic_sampling))
                clock_last_min = now.minute
                last_mic_state = mic_sampling

        time.sleep(2)
