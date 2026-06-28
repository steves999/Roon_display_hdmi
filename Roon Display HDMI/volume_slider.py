"""
volume_slider.py — Volume slider overlay for Roon Display HDMI

Shared state between roon_display.py and touch_handler.py.
The slider appears at the bottom of the screen when the volume
circle is tapped, and dismisses after a timeout or outside tap.
"""

import threading
import time

# --- Slider state ---
_visible       = False
_auto_hide_secs = 4
_last_interact  = 0
_lock           = threading.Lock()
_callback       = None   # called when volume should change: fn(pct)

# Slider geometry (set by roon_display to match actual screen)
slider_x      = 60     # left edge of slider track
slider_y      = 750    # y centre of slider
slider_w      = 1160   # width of slider track
slider_h      = 6      # thickness of track
knob_r        = 18     # radius of knob

# Volume circle geometry (must match draw_volume_circle in roon_display)
circle_cx     = 56
circle_cy     = 728
circle_r      = 38


def set_callback(fn):
    """Register callback: fn(pct) called when user drags slider."""
    global _callback
    _callback = fn


def is_visible():
    with _lock:
        return _visible


def show():
    global _visible, _last_interact
    with _lock:
        _visible      = True
        _last_interact = time.time()


def hide():
    global _visible
    with _lock:
        _visible = False


def touch(reset_timer=True):
    """Record interaction — resets auto-hide timer."""
    global _last_interact
    with _lock:
        if reset_timer:
            _last_interact = time.time()


def is_expired():
    """Returns True if auto-hide timeout has passed."""
    with _lock:
        if not _visible:
            return False
        return (time.time() - _last_interact) >= _auto_hide_secs


def hit_circle(x, y):
    """Returns True if (x, y) is within the volume circle."""
    return ((x - circle_cx)**2 + (y - circle_cy)**2) <= circle_r**2


def hit_slider(x, y):
    """Returns True if (x, y) is within the slider interaction area."""
    margin = 40  # generous hit area above/below track
    return (slider_x - knob_r <= x <= slider_x + slider_w + knob_r
            and slider_y - margin <= y <= slider_y + margin)


def pct_from_x(x):
    """Convert x position to volume percentage 0-100."""
    pct = (x - slider_x) / slider_w * 100
    return max(0, min(100, pct))


def x_from_pct(pct):
    """Convert volume percentage to x position."""
    return int(slider_x + (pct / 100) * slider_w)


def set_auto_hide(secs):
    global _auto_hide_secs
    _auto_hide_secs = secs


def draw(canvas, vol_pct, from_module=None):
    """
    Draw the volume slider overlay onto canvas.
    vol_pct: current volume 0-100
    Returns modified canvas.
    """
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    import os

    FONT_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyreheros-regular.otf"

    W, H = canvas.size
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Background pill
    pill_x1 = slider_x - 40
    pill_y1 = slider_y - 50
    pill_x2 = slider_x + slider_w + 40
    pill_y2 = slider_y + 50
    draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2],
                            radius=30,
                            fill=(0, 0, 0, 160))

    # Track background
    draw.rounded_rectangle(
        [slider_x, slider_y - slider_h//2,
         slider_x + slider_w, slider_y + slider_h//2],
        radius=slider_h//2,
        fill=(80, 80, 80, 220)
    )

    # Filled portion
    knob_x = x_from_pct(vol_pct)
    if knob_x > slider_x:
        draw.rounded_rectangle(
            [slider_x, slider_y - slider_h//2,
             knob_x, slider_y + slider_h//2],
            radius=slider_h//2,
            fill=(255, 255, 255, 220)
        )

    # Knob
    draw.ellipse(
        [knob_x - knob_r, slider_y - knob_r,
         knob_x + knob_r, slider_y + knob_r],
        fill=(255, 255, 255, 240),
        outline=(200, 200, 200, 255),
        width=2
    )

    # Volume percentage label
    try:
        font = ImageFont.truetype(FONT_REG, 28)
        label = f"{int(vol_pct)}%"
        draw.text((slider_x + slider_w + 56, slider_y),
                  label, font=font,
                  fill=(200, 200, 200, 200),
                  anchor="mm")
    except:
        pass

    result = Image.alpha_composite(canvas.convert('RGBA'), overlay)
    return result.convert('RGB')
