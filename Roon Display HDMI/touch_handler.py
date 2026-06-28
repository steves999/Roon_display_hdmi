"""
touch_handler.py — Touch input handler for Roon Display HDMI
Reads touch events from evdev and triggers Roon API commands.
All thresholds and actions configurable via config.json.

Gestures:
  Long press (anywhere)  : configurable action (default: heat_pump)
  Left zone tap          : configurable (default: volume_down)
  Right zone tap         : configurable (default: volume_up)
  Centre tap             : configurable (default: toggle_text)
  Centre double tap      : configurable (default: play_pause)
  Swipe left             : configurable (default: next)
  Swipe right            : configurable (default: previous)
"""

import threading
import time
import requests
import json
import os
import subprocess

CONFIG_FILE = os.path.expanduser("~/config.json")

_defaults = {
    "touch_swipe_min_dx":        250,
    "touch_swipe_max_dy":        200,
    "touch_swipe_max_ms":        600,
    "touch_tap_max_move":         30,
    "touch_double_tap_ms":       400,
    "touch_long_press_ms":      1000,
    "touch_vol_step":              5,
    "touch_left_zone":          0.33,
    "touch_right_zone":         0.67,
    "touch_action_left":    "volume_down",
    "touch_action_right":   "volume_up",
    "touch_action_centre":  "toggle_text",
    "touch_action_double":  "play_pause",
    "touch_action_long":    "heat_pump",
    "touch_action_swipe_left":  "next",
    "touch_action_swipe_right": "previous",
    "heat_pump_url":        "http://192.168.8.118:5000/",
}

W = 1280

_show_text      = True
_text_lock      = threading.Lock()
_callback       = None
_running        = False
_thread         = None
_bridge         = "http://192.168.8.118:3001"
_zone_id        = None
_output_id      = None
_browser_proc   = None
_browser_lock   = threading.Lock()
_last_vol_pct   = 50.0


def _load_touch_cfg():
    cfg = dict(_defaults)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            for k in _defaults:
                if k in data:
                    cfg[k] = data[k]
        except:
            pass
    return cfg


def configure(bridge, zone_id, output_id, vol_pct=None):
    global _bridge, _zone_id, _output_id, _last_vol_pct
    _bridge    = bridge
    _zone_id   = zone_id
    _output_id = output_id
    if vol_pct is not None:
        _last_vol_pct = vol_pct


def set_callback(fn):
    global _callback
    _callback = fn


def get_show_text():
    with _text_lock:
        return _show_text


def set_show_text(val):
    with _text_lock:
        global _show_text
        _show_text = val


def is_browser_open():
    with _browser_lock:
        return _browser_proc is not None and _browser_proc.poll() is None


def _launch_browser(url):
    global _browser_proc
    with _browser_lock:
        if _browser_proc is not None and _browser_proc.poll() is None:
            return
        print(f"[Touch] Launching browser: {url}")
        try:
            _browser_proc = subprocess.Popen(
                ["startx", "/usr/bin/chromium",
                 "--kiosk", "--noerrdialogs", "--disable-infobars",
                 "--disable-session-crashed-bubble",
                 url, "--", ":1"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if _callback:
                _callback("browser_open", url)
        except Exception as e:
            print(f"[Touch] Browser launch error: {e}")


def _close_browser():
    global _browser_proc
    with _browser_lock:
        print("[Touch] Closing browser")
        try:
            subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
            subprocess.run(["pkill", "Xorg"], capture_output=True)
            try:
                os.remove("/tmp/.X1-lock")
            except:
                pass
        except Exception as e:
            print(f"[Touch] Browser close error: {e}")
        _browser_proc = None
        if _callback:
            _callback("browser_closed", None)


def _find_touch_device():
    try:
        import evdev
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            caps = dev.capabilities()
            if evdev.ecodes.EV_ABS in caps:
                abs_codes = [c for c, _ in caps[evdev.ecodes.EV_ABS]]
                if evdev.ecodes.ABS_MT_POSITION_X in abs_codes:
                    print(f"[Touch] Found device: {dev.name} at {dev.path}")
                    dev.grab()
                    return dev
        print("[Touch] No touch device found")
        return None
    except Exception as e:
        print(f"[Touch] Device search error: {e}")
        return None


def _roon_get(endpoint, params=None):
    try:
        r = requests.get(f"{_bridge}/roonAPI/{endpoint}", params=params, timeout=5)
        return r.json()
    except Exception as e:
        print(f"[Touch] Roon API error: {e}")
        return None


def _do_action(action, cfg):
    global _last_vol_pct
    if action == "volume_up":
        if _output_id:
            _roon_get("change_volume_relative", {"volume": cfg["touch_vol_step"], "outputId": _output_id})
            _last_vol_pct = min(100, _last_vol_pct + cfg["touch_vol_step"])
            print(f"[Touch] Volume +{cfg['touch_vol_step']}")
    elif action == "volume_down":
        if _output_id:
            _roon_get("change_volume_relative", {"volume": -cfg["touch_vol_step"], "outputId": _output_id})
            _last_vol_pct = max(0, _last_vol_pct - cfg["touch_vol_step"])
            print(f"[Touch] Volume -{cfg['touch_vol_step']}")
    elif action == "next":
        if _zone_id:
            _roon_get("next", {"zoneId": _zone_id})
            print("[Touch] Next track")
    elif action == "previous":
        if _zone_id:
            _roon_get("previous", {"zoneId": _zone_id})
            print("[Touch] Previous track")
    elif action == "play_pause":
        if _zone_id:
            zone = _roon_get("listZones")
            if zone:
                z = next((z for z in zone["zones"] if z["zone_id"] == _zone_id), None)
                if z:
                    if z["state"] == "playing":
                        _roon_get("pause", {"zoneId": _zone_id})
                        print("[Touch] Paused")
                    else:
                        _roon_get("play", {"zoneId": _zone_id})
                        print("[Touch] Playing")
    elif action == "toggle_text":
        current = get_show_text()
        set_show_text(not current)
        print(f"[Touch] Text {'shown' if not current else 'hidden'}")
        if _callback:
            _callback("toggle_text", not current)
        return
    elif action == "heat_pump":
        if is_browser_open():
            _close_browser()
        else:
            _launch_browser(cfg["heat_pump_url"])
        return
    elif action == "none":
        return

    if _callback:
        _callback(action, None)


def _process_touch(x, y, dx, dy, duration_ms, cfg):
    left_boundary  = int(W * cfg["touch_left_zone"])
    right_boundary = int(W * cfg["touch_right_zone"])

    # Swipe
    if (abs(dx) >= cfg["touch_swipe_min_dx"]
            and abs(dy) <= cfg["touch_swipe_max_dy"]
            and duration_ms <= cfg["touch_swipe_max_ms"]):
        if dx < 0:
            _do_action(cfg["touch_action_swipe_left"], cfg)
        else:
            _do_action(cfg["touch_action_swipe_right"], cfg)
        return "swipe"

    # Tap
    if abs(dx) <= cfg["touch_tap_max_move"] and abs(dy) <= cfg["touch_tap_max_move"]:
        if x < left_boundary:
            _do_action(cfg["touch_action_left"], cfg)
            return "left_tap"
        elif x > right_boundary:
            _do_action(cfg["touch_action_right"], cfg)
            return "right_tap"
        else:
            return "centre_tap"

    return None


def _touch_loop():
    import evdev
    from evdev import ecodes

    last_tap_time = 0
    last_tap_zone = None

    while _running:
        dev = _find_touch_device()
        if not dev:
            time.sleep(5)
            continue

        touch_x    = 0
        touch_y    = 0
        start_x    = None
        start_y    = None
        start_time = None
        touching   = False
        long_fired = False
        long_timer = None

        def cancel_long_timer():
            nonlocal long_timer
            if long_timer and long_timer.is_alive():
                long_timer.cancel()
            long_timer = None

        def fire_long_press():
            nonlocal long_fired
            cfg = _load_touch_cfg()
            long_fired = True
            print(f"[Touch] Long press")
            _do_action(cfg["touch_action_long"], cfg)

        try:
            for event in dev.read_loop():
                if not _running:
                    break

                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_MT_POSITION_X:
                        touch_x = event.value
                    elif event.code == ecodes.ABS_MT_POSITION_Y:
                        touch_y = event.value
                    elif event.code == ecodes.ABS_MT_TRACKING_ID:
                        if event.value != -1:
                            touching   = True
                            long_fired = False
                            start_x    = touch_x
                            start_y    = touch_y
                            start_time = time.time()
                            cfg_now = _load_touch_cfg()
                            long_timer = threading.Timer(
                                cfg_now["touch_long_press_ms"] / 1000.0,
                                fire_long_press
                            )
                            long_timer.start()
                        else:
                            cancel_long_timer()
                            if touching and start_x is not None and not long_fired:
                                cfg      = _load_touch_cfg()
                                now      = time.time()
                                dur_ms   = int((now - start_time) * 1000)
                                dx       = touch_x - start_x
                                dy       = touch_y - start_y
                                mid_x    = (touch_x + start_x) // 2
                                mid_y    = (touch_y + start_y) // 2
                                gesture  = _process_touch(mid_x, mid_y, dx, dy, dur_ms, cfg)

                                if gesture == "centre_tap":
                                    elapsed = (now - last_tap_time) * 1000
                                    if elapsed < cfg["touch_double_tap_ms"] and last_tap_zone == "centre":
                                        _do_action(cfg["touch_action_double"], cfg)
                                        last_tap_time = 0
                                        last_tap_zone = None
                                    else:
                                        last_tap_time = now
                                        last_tap_zone = "centre"
                                        _do_action(cfg["touch_action_centre"], cfg)

                            touching   = False
                            long_fired = False
                            start_x    = None

        except OSError:
            cancel_long_timer()
            print("[Touch] Device disconnected, retrying...")
            time.sleep(2)
        except Exception as e:
            cancel_long_timer()
            print(f"[Touch] Error: {e}")
            time.sleep(2)


def start(bridge=None, zone_id=None, output_id=None):
    global _running, _thread
    if bridge:
        configure(bridge, zone_id, output_id)
    if _running:
        return
    _running = True
    _thread  = threading.Thread(target=_touch_loop, daemon=True)
    _thread.start()
    print("[Touch] Handler started")


def stop():
    global _running
    _running = False
    print("[Touch] Handler stopped")
