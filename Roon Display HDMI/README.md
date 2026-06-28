# Roon Display HDMI

A Raspberry Pi HDMI display for Roon that shows album art, track info, and a clock — with Shazam vinyl detection, touch controls, and a heat pump controller overlay.

![Display showing album art with blurred sides, track info overlay, and station logo](https://placeholder)

---

## Features

- **Album art** — fetches from iTunes for radio streams, Roon library art for local tracks
- **Radio stream support** — detects any radio station, shows stream art, retries until track metadata arrives
- **Station overlay** — station artwork shown bottom right with feathered edges
- **Clock** — analogue clock with blurred art background when idle
- **Shazam vinyl detection** — listens via USB mic, identifies vinyl playing, shows album art
- **Volume indicator** — semi-transparent pie circle bottom left when track info is hidden
- **Touch controls** — tap zones, swipe, long press all configurable
- **Heat pump controller** — long press launches browser overlay to heat pump UI
- **Web config UI** — all settings adjustable via browser at port 8080

---

## Hardware

| Component | Details |
|-----------|---------|
| Pi | Raspberry Pi 4B, 5, or 400 (2GB+ recommended) |
| Display | Any HDMI display — tested at 1280×800 |
| Audio | USB microphone (for Shazam vinyl detection) |
| Touch | Optional — USB touch overlay |

**Roon bridge** — requires [roon-extension-http-api](https://github.com/st0g1e/roon-extension-http-api) running on another Pi or server on your network.

---

## Quick Install

### 1. Flash OS

Use **Raspberry Pi Imager** to flash **Raspberry Pi OS Lite (64-bit)** — Bookworm.

In the imager settings (gear icon) before flashing:
- Set hostname (e.g. `RoonDisplay`)
- Set username and password
- Configure WiFi
- Enable SSH

### 2. SSH in

```bash
ssh youruser@yourpi.local
```

### 3. Run the setup script

```bash
curl -fsSL https://raw.githubusercontent.com/steves999/Roon_display_hdmi/main/setup.sh | bash
```

You will be prompted for:
- **Roon bridge address** — IP and port of your roon-extension-http-api instance (e.g. `http://192.168.1.100:3001`)
- **Roon zone name** — the Roon zone to monitor (e.g. `Lounge`)
- **Heat pump URL** — URL of your heat pump controller web UI (e.g. `http://192.168.1.100:5000/`)

The script will install all dependencies, download files from GitHub, configure the framebuffer, set up systemd services, and reboot.

### 4. After reboot

The display starts automatically. Open the web UI to fine-tune settings:

```
http://<your-pi-ip>:8080
```

---

## Files

| File | Purpose |
|------|---------|
| `roon_display.py` | Main display script |
| `shazam_listener.py` | Background Shazam audio detection |
| `touch_handler.py` | Touch input handler |
| `web_config.py` | Flask web configuration UI |
| `setup.sh` | One-shot setup script |

---

## Touch Controls (defaults)

| Gesture | Action |
|---------|--------|
| Tap left third | Volume down |
| Tap right third | Volume up |
| Tap centre | Toggle track info |
| Double tap centre | Play / Pause |
| Swipe left | Next track |
| Swipe right | Previous track |
| Long press (anywhere) | Heat pump UI overlay |

All actions and zones are configurable via the web UI.

---

## Web UI

Open `http://<pi-ip>:8080` in any browser.

Sections:
- **Display** — framebuffer path, rotation
- **Roon Connection** — bridge address, zone, poll interval
- **Text & Timing** — text hold, scroll speed
- **Font Sizes** — artist, album, track sizes
- **Text Block** — opacity and blur
- **Progress Bar** — height and colour
- **Art Display** — blur radius for sides and clock background
- **Clock** — radius, position, flip
- **Touch Controls** — zone boundaries, actions, thresholds, long press, heat pump URL
- **Shazam** — silence threshold, timeout, sample settings

Changes are saved immediately. Restart Display button applies changes to the running display.

---

## Framebuffer Notes

This project writes directly to `/dev/fb0` using RGB565 (16-bit). The setup script switches from the default KMS driver to the `vc4-fkms-v3d` overlay which exposes a proper framebuffer.

If your display shows at a different resolution, check:
```bash
fbset
cat /sys/class/graphics/fb0/virtual_size
```

Update `W` and `H` at the top of `roon_display.py` to match, and adjust `clock_cx`, `clock_date_cx`, and `clock_radius` in the web UI accordingly.

---

## Roon Bridge

This project requires [roon-extension-http-api](https://github.com/st0g1e/roon-extension-http-api) running on your network. Install on a Pi or server:

```bash
git clone https://github.com/st0g1e/roon-extension-http-api
cd roon-extension-http-api
npm install
node server.js
```

Then enable the extension in Roon → Settings → Extensions.

---

## Adding Radio Stations

Unknown stations are detected automatically via `length is None` in the Roon API response. Station stream art is used as the overlay image automatically.

To add a known station with a custom logo, edit `KNOWN_STATIONS` in `roon_display.py`:

```python
KNOWN_STATIONS = {
    "Radio Paradise": {
        "logo_url": "https://example.com/logo.png",
    },
}
```

---

## Related Projects

- [Roon Display with Shazam (HyperPixel version)](https://github.com/steves999/Roon_display_with_shazam) — the original HyperPixel 4" version this project is based on

---

## Dependencies

```
pillow
shazamio
sounddevice
evdev
audioop-lts
flask
numpy
chromium
```

All installed automatically by `setup.sh`.
