#!/bin/bash
# ============================================================
# Roon Display HDMI — Setup Script
# Run as the display user (not root)
# ============================================================

set -e

REPO="https://raw.githubusercontent.com/steves999/Roon_display_hdmi/main"
CONFIG_FILE="$HOME/config.json"
SERVICE_USER=$(whoami)

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     Roon Display HDMI — Setup Script     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# --- Prompts ---
read -p "Roon bridge IP and port [http://192.168.8.118:3001]: " BRIDGE
BRIDGE=${BRIDGE:-"http://192.168.8.118:3001"}

read -p "Roon zone name [Lounge]: " ZONE
ZONE=${ZONE:-"Lounge"}

read -p "Heat pump URL [http://192.168.8.118:5000/]: " HEATPUMP
HEATPUMP=${HEATPUMP:-"http://192.168.8.118:5000/"}

echo ""
echo "──────────────────────────────────────────"
echo "  Bridge:    $BRIDGE"
echo "  Zone:      $ZONE"
echo "  Heat pump: $HEATPUMP"
echo "──────────────────────────────────────────"
echo ""
read -p "Proceed? [Y/n]: " CONFIRM
CONFIRM=${CONFIRM:-"Y"}
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "► Updating package lists..."
sudo apt update -q

echo "► Installing apt dependencies..."
sudo apt install -y \
    python3-pip python3-flask python3-numpy \
    sox libsox-fmt-all ffmpeg \
    libopenblas0 libportaudio2 libasound2-dev \
    fonts-roboto tex-gyre fontconfig \
    chromium xorg x11-xserver-utils xserver-xorg-video-fbdev \
    cage

echo "► Installing pip packages..."
pip3 install pillow shazamio sounddevice evdev audioop-lts --break-system-packages

echo "► Downloading display files from GitHub..."
cd "$HOME"
curl -fsSL "$REPO/roon_display.py"    -o roon_display.py
curl -fsSL "$REPO/web_config.py"      -o web_config.py
curl -fsSL "$REPO/shazam_listener.py" -o shazam_listener.py
curl -fsSL "$REPO/touch_handler.py"   -o touch_handler.py

echo "► Configuring ALSA for USB mic..."
cat > "$HOME/.asoundrc" << 'EOF'
pcm.!default {
    type hw
    card 0
    device 0
}
ctl.!default {
    type hw
    card 0
}
EOF

echo "► Configuring framebuffer (fkms)..."
# Check if already configured
if ! grep -q "vc4-fkms-v3d" /boot/firmware/config.txt; then
    # Comment out kms if present
    sudo sed -i 's/^dtoverlay=vc4-kms-v3d/#dtoverlay=vc4-kms-v3d/' /boot/firmware/config.txt
    sudo sed -i 's/^disable_fw_kms_setup=1/#disable_fw_kms_setup=1/' /boot/firmware/config.txt
    # Add fkms
    echo "dtoverlay=vc4-fkms-v3d" | sudo tee -a /boot/firmware/config.txt > /dev/null
    echo "framebuffer_depth=32" | sudo tee -a /boot/firmware/config.txt > /dev/null
    echo "framebuffer_ignore_alpha=1" | sudo tee -a /boot/firmware/config.txt > /dev/null
fi

echo "► Allowing X server access..."
sudo tee /etc/X11/Xwrapper.config > /dev/null << 'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF

echo "► Adding $SERVICE_USER to video group..."
sudo usermod -a -G video "$SERVICE_USER"

echo "► Configuring sudoers..."
echo "$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/shutdown, /bin/systemctl" | sudo tee /etc/sudoers.d/roon-display > /dev/null
sudo chmod 440 /etc/sudoers.d/roon-display

echo "► Creating default config.json..."
cat > "$CONFIG_FILE" << EOF
{
  "bridge": "$BRIDGE",
  "target_zone": "$ZONE",
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
  "clock_flip": false,
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
  "heat_pump_url": "$HEATPUMP"
}
EOF

echo "► Creating systemd services..."
sudo tee /etc/systemd/system/roon-display.service > /dev/null << EOF
[Unit]
Description=Roon Display
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/$SERVICE_USER/roon_display.py
Restart=always
User=$SERVICE_USER
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/roon-web.service > /dev/null << EOF
[Unit]
Description=Roon Display Web Config
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/$SERVICE_USER/web_config.py
Restart=always
User=$SERVICE_USER

[Install]
WantedBy=multi-user.target
EOF

echo "► Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable roon-display roon-web
sudo systemctl start roon-web

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║              Setup complete!             ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "  Web UI:  http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "  A reboot is required to activate the framebuffer changes."
echo "  The display service will start automatically after reboot."
echo ""
read -p "Reboot now? [Y/n]: " REBOOT
REBOOT=${REBOOT:-"Y"}
if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
