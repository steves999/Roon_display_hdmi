"""
touch_handler.py — Touch input handler for Roon Display HDMI
Reads touch events from evdev and triggers Roon API commands.

Touch zones (landscape 1280x800):
  Left third  (x < 427)   : volume down
  Right third (x > 853)   : volume up
  Centre tap              : show/hide track info
  Centre double tap       : play/pause
  Swipe left  (dx < -100) : next track
  Swipe right (dx > 100)  : previous track
"""

import threading
import time
import requests
import glob

# --- State shared with main display loop ---
_show_text    = True   # controls whether text overlay is shown
_text_lock    = threading.Lock()
_callback     = None   # called when state changes: fn(event, data)

# Touch detection thresholds
SWIPE_MIN_DX    = 150   # minimum x movement for a swipe (pixels)
SWIPE_MAX_DY    = 200   # maximum y movement for a swipe (must be mostly horizontal)
SWIPE_MAX_MS    = 600   # maximum milliseconds for a swipe gesture
DOUBLE_TAP_MS   = 400   # max ms between taps for double-tap
TAP_MAX_MOVE    = 60    # max movement for a tap (not a swipe)
VOL_STEP        = 5     # volume change per tap

_running        = False
_thread         = None
_bridge         = "http://192.168.8.118:3001"
_zone_id        = None
_output_id      = None


def configure(bridge, zone_id, output_id):
    """Set Roon bridge URL and zone/output IDs."""
    global _bridge, _zone_id, _output_id
    _bridge    = bridge
    _zone_id   = zone_id
    _output_id = output_id


def set_callback(fn):
    """Register callback for touch events: fn(event_name, data)"""
    global _callback
    _callback = fn


def get_show_text():
    with _text_lock:
        return _show_text


def set_show_text(val):
    with _text_lock:
        global _show_text
        _show_text = val


def _find_touch_device():
    """Find the first touch input device via evdev."""
    try:
        import evdev
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for dev in devices:
            caps = dev.capabilities()
            # Touch devices have EV_ABS with ABS_MT_POSITION_X
            if evdev.ecodes.EV_ABS in caps:
                abs_codes = [c for c, _ in caps[evdev.ecodes.EV_ABS]]
                if evdev.ecodes.ABS_MT_POSITION_X in abs_codes:
                    print(f"[Touch] Found device: {dev.name} at {dev.path}")
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


def _roon_play_pause():
    if not _zone_id:
        return
    zone = _roon_get("listZones")
    if not zone:
        return
    z = next((z for z in zone["zones"] if z["zone_id"] == _zone_id), None)
    if not z:
        return
    if z["state"] == "playing":
        _roon_get("pause", {"zoneId": _zone_id})
        print("[Touch] Paused")
    else:
        _roon_get("play", {"zoneId": _zone_id})
        print("[Touch] Playing")


def _roon_next():
    if _zone_id:
        _roon_get("next", {"zoneId": _zone_id})
        print("[Touch] Next track")


def _roon_previous():
    if _zone_id:
        _roon_get("previous", {"zoneId": _zone_id})
        print("[Touch] Previous track")


def _roon_volume(delta):
    if _output_id:
        _roon_get("change_volume_relative", {
            "volume": delta,
            "outputId": _output_id
        })
        print(f"[Touch] Volume {'+' if delta > 0 else ''}{delta}")


def _notify(event, data=None):
    if _callback:
        try:
            _callback(event, data)
        except Exception as e:
            print(f"[Touch] Callback error: {e}")


def _process_touch(x, y, dx, dy, duration_ms):
    """Classify a completed touch gesture and act on it."""
    W = 1280
    # Swipe detection — mostly horizontal movement
    if abs(dx) >= SWIPE_MIN_DX and abs(dy) <= SWIPE_MAX_DY and duration_ms <= SWIPE_MAX_MS:
        if dx < 0:
            _roon_next()
            _notify("next")
        else:
            _roon_previous()
            _notify("previous")
        return "swipe"

    # Tap — minimal movement
    if abs(dx) <= TAP_MAX_MOVE and abs(dy) <= TAP_MAX_MOVE:
        if x < W // 3:
            _roon_volume(-VOL_STEP)
            _notify("volume_down")
            return "volume_down"
        elif x > (W * 2) // 3:
            _roon_volume(VOL_STEP)
            _notify("volume_up")
            return "volume_up"
        else:
            return "centre_tap"

    return None


def _touch_loop():
    """Main touch reading loop."""
    import evdev
    from evdev import ecodes

    last_tap_time  = 0
    last_tap_zone  = None

    while _running:
        dev = _find_touch_device()
        if not dev:
            time.sleep(5)
            continue

        touch_x     = 0
        touch_y     = 0
        start_x     = None
        start_y     = None
        start_time  = None
        touching    = False

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
                            # Touch start
                            touching   = True
                            start_x    = touch_x
                            start_y    = touch_y
                            start_time = time.time()
                        else:
                            # Touch end
                            if touching and start_x is not None:
                                now_ms    = time.time()
                                dur_ms    = int((now_ms - start_time) * 1000)
                                dx        = touch_x - start_x
                                dy        = touch_y - start_y
                                mid_x     = (touch_x + start_x) // 2
                                mid_y     = (touch_y + start_y) // 2
                                gesture   = _process_touch(mid_x, mid_y, dx, dy, dur_ms)

                                if gesture == "centre_tap":
                                    # Check for double tap
                                    elapsed = (now_ms - last_tap_time) * 1000
                                    if elapsed < DOUBLE_TAP_MS and last_tap_zone == "centre":
                                        _roon_play_pause()
                                        _notify("play_pause")
                                        last_tap_time = 0
                                        last_tap_zone = None
                                    else:
                                        # Single tap — toggle text
                                        last_tap_time = now_ms
                                        last_tap_zone = "centre"
                                        current = get_show_text()
                                        set_show_text(not current)
                                        _notify("toggle_text", not current)
                                        print(f"[Touch] Text {'shown' if not current else 'hidden'}")

                            touching   = False
                            start_x    = None

        except OSError:
            print("[Touch] Device disconnected, retrying...")
            time.sleep(2)
        except Exception as e:
            print(f"[Touch] Error: {e}")
            time.sleep(2)


def start(bridge=None, zone_id=None, output_id=None):
    """Start the touch handler thread."""
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
    """Stop the touch handler thread."""
    global _running
    _running = False
    print("[Touch] Handler stopped")
