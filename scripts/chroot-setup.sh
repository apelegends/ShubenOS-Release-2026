#!/bin/bash
# Shuben Launcher OS — chroot setup script
# Runs inside the Ubuntu squashfs chroot during build
set -e

echo "==> Shuben chroot setup starting..."

# ── OS identity ──────────────────────────────────────────────────────────────
cat > /etc/os-release << 'EOF'
PRETTY_NAME="Shuben Launcher OS 1.0"
NAME="Shuben Launcher OS"
VERSION="1.0"
VERSION_ID="1.0"
ID=shuben-launcher
ID_LIKE=ubuntu
HOME_URL="https://github.com/apelegends/shuben-launcher-os"
SUPPORT_URL="https://github.com/apelegends/shuben-launcher-os/issues"
BUG_REPORT_URL="https://github.com/apelegends/shuben-launcher-os/issues"
EOF

echo "shuben-launcher" > /etc/hostname

cat > /etc/hosts << 'EOF'
127.0.0.1   localhost
127.0.1.1   shuben-launcher
::1         localhost ip6-localhost ip6-loopback
EOF

cat > /etc/motd << 'EOF'

  ███████╗██╗  ██╗██╗   ██╗██████╗ ███████╗███╗   ██╗
  ██╔════╝██║  ██║██║   ██║██╔══██╗██╔════╝████╗  ██║
  ███████╗███████║██║   ██║██████╔╝█████╗  ██╔██╗ ██║
  ╚════██║██╔══██║██║   ██║██╔══██╗██╔══╝  ██║╚██╗██║
  ███████║██║  ██║╚██████╔╝██████╔╝███████╗██║ ╚████║
  ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝
  Launcher OS 1.0 — by Apelegends / shuben
  Minecraft OS | Lightweight | Dual-boot ready
  ⚠  NO ANTIVIRUS — by design

EOF

# ── Create shuben user ────────────────────────────────────────────────────────
useradd -m -s /bin/bash -G sudo,audio,video,plugdev,netdev shuben 2>/dev/null || true
echo "shuben:shuben" | chpasswd
passwd -l shuben  # Lock password — PIN used instead

# ── /usr/bin wrappers ─────────────────────────────────────────────────────────
for script in installer oobe taskbar pinlock minecraft-launcher settings; do
  case $script in
    installer)        py="installer/installer.py" ;;
    oobe)             py="oobe/oobe.py" ;;
    taskbar)          py="desktop/taskbar.py" ;;
    pinlock)          py="login/pinlock.py" ;;
    minecraft-launcher) py="minecraft/launcher.py" ;;
    settings)         py="settings/settings.py" ;;
  esac
  cat > /usr/bin/shuben-$script << WEOF
#!/bin/bash
exec python3 /usr/lib/shuben-launcher/$py "\$@"
WEOF
  chmod +x /usr/bin/shuben-$script
done

cat > /usr/bin/shuben-lock << 'EOF'
#!/bin/bash
exec python3 /usr/lib/shuben-launcher/login/pinlock.py "$@"
EOF
chmod +x /usr/bin/shuben-lock

cat > /usr/bin/shuben-power-menu << 'EOF'
#!/bin/bash
CHOICE=$(zenity --list --title="Power" --column="Action" \
  "Shut down" "Restart" "Suspend" "Lock" 2>/dev/null)
case "$CHOICE" in
  "Shut down") systemctl poweroff ;;
  "Restart")   systemctl reboot ;;
  "Suspend")   systemctl suspend ;;
  "Lock")      shuben-lock ;;
esac
EOF
chmod +x /usr/bin/shuben-power-menu

# ── GPU auto-detect service ───────────────────────────────────────────────────
cat > /usr/bin/shuben-gpu-setup << 'GPUEOF'
#!/bin/bash
LOG="/var/log/shuben-gpu-setup.log"
exec >> "$LOG" 2>&1
echo "[$(date)] GPU setup starting..."
mkdir -p /var/lib/shuben
GPU=$(lspci | grep -Ei "vga|3d|display")
echo "GPU: $GPU"
NVIDIA=0; AMD=0; INTEL=0
echo "$GPU" | grep -qi "nvidia"  && NVIDIA=1
echo "$GPU" | grep -qi "amd\|radeon" && AMD=1
echo "$GPU" | grep -qi "intel"   && INTEL=1

mkdir -p /etc/X11/xorg.conf.d

if [ $INTEL -eq 1 ]; then
  cat > /etc/X11/xorg.conf.d/20-intel.conf << 'EOF'
Section "Device"
  Identifier "Intel"
  Driver     "intel"
  Option     "TearFree" "true"
  Option     "DRI" "3"
EndSection
EOF
fi

if [ $AMD -eq 1 ]; then
  cat > /etc/X11/xorg.conf.d/20-amd.conf << 'EOF'
Section "Device"
  Identifier "AMD"
  Driver     "amdgpu"
  Option     "TearFree" "true"
  Option     "DRI" "3"
EndSection
EOF
  echo "options amdgpu si_support=1 cik_support=1" > /etc/modprobe.d/amdgpu.conf
fi

if [ $NVIDIA -eq 1 ]; then
  cat > /etc/X11/xorg.conf.d/20-nvidia.conf << 'EOF'
Section "Device"
  Identifier "NVIDIA"
  Driver     "nouveau"
EndSection
EOF
fi

cat > /var/lib/shuben/gpu-info.json << GPUJSON
{"nvidia":$NVIDIA,"amd":$AMD,"intel":$INTEL,"raw":"$(echo $GPU | head -c 200)"}
GPUJSON

echo "[$(date)] GPU setup done."
GPUEOF
chmod +x /usr/bin/shuben-gpu-setup

cat > /etc/systemd/system/shuben-gpu-setup.service << 'EOF'
[Unit]
Description=Shuben GPU Auto-Detection
After=local-fs.target
Before=display-manager.service
ConditionPathExists=!/var/lib/shuben/gpu-setup-done

[Service]
Type=oneshot
ExecStart=/usr/bin/shuben-gpu-setup
ExecStartPost=/bin/touch /var/lib/shuben/gpu-setup-done
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl enable shuben-gpu-setup.service 2>/dev/null || true

# ── Installer systemd service (runs at live boot) ─────────────────────────────
cat > /etc/systemd/system/shuben-installer-autostart.service << 'EOF'
[Unit]
Description=Shuben Installer Auto-Start
After=graphical.target
Wants=graphical.target

[Service]
Type=simple
User=shuben
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/shuben/.Xauthority
ExecStartPre=/bin/sleep 4
ExecStart=/usr/bin/shuben-installer
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# ── LightDM — auto-login to shuben, PIN takes over ───────────────────────────
mkdir -p /etc/lightdm
cat > /etc/lightdm/lightdm.conf << 'EOF'
[Seat:*]
autologin-user=shuben
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
greeter-session=lightdm-gtk-greeter
EOF

cat > /etc/lightdm/lightdm-gtk-greeter.conf << 'EOF'
[greeter]
background=#0D1117
theme-name=Adwaita-dark
icon-theme-name=hicolor
font-name=Segoe UI 11
EOF

# ── Openbox session ───────────────────────────────────────────────────────────
mkdir -p /etc/skel/.config/openbox

cat > /etc/skel/.config/openbox/autostart << 'EOF'
#!/bin/bash
# Shuben Launcher OS — Openbox autostart

# Compositor
picom --daemon &

# Wallpaper
feh --bg-scale /usr/share/shuben-launcher/wallpapers/desktop.jpg &

# Taskbar
shuben-taskbar &

# OOBE on first boot
if [ ! -f /var/lib/shuben/oobe-state.json ] || \
   ! python3 -c "import json; d=json.load(open('/var/lib/shuben/oobe-state.json')); exit(0 if d.get('oobe_complete') else 1)" 2>/dev/null; then
  sleep 1
  shuben-oobe &
fi

# PIN lock after OOBE
if [ -f /var/lib/shuben/pin.json ]; then
  sleep 0.5
  shuben-lock &
fi

# On live session: auto-launch installer after a short wait
if grep -q "boot=live" /proc/cmdline 2>/dev/null; then
  sleep 5
  shuben-installer &
fi

# On installed system: launch Minecraft on first run
if [ ! -f /var/lib/shuben/.mc-launched ] && ! grep -q "boot=live" /proc/cmdline 2>/dev/null; then
  sleep 3
  touch /var/lib/shuben/.mc-launched
  shuben-minecraft-launcher &
fi
EOF

cat > /etc/skel/.config/openbox/rc.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <theme>
    <name>Clearlooks</name>
    <keepBorder>no</keepBorder>
    <animateIconify>no</animateIconify>
  </theme>
  <desktops><number>1</number></desktops>
  <keyboard>
    <keybind key="C-A-t"><action name="Execute"><command>lxterminal</command></action></keybind>
    <keybind key="C-A-l"><action name="Execute"><command>shuben-lock</command></action></keybind>
    <keybind key="A-F4"><action name="Close"/></keybind>
    <keybind key="A-Tab"><action name="NextWindow"/></keybind>
    <keybind key="Super-d"><action name="ShowDesktop"/></keybind>
  </keyboard>
  <mouse>
    <context name="Desktop">
      <mousebind button="Right" action="Press">
        <action name="ShowMenu"><menu>root-menu</menu></action>
      </mousebind>
    </context>
  </mouse>
  <applications/>
</openbox_config>
EOF

# ── GTK dark theme ────────────────────────────────────────────────────────────
mkdir -p /etc/skel/.config/gtk-3.0 /etc/skel/.config/gtk-2.0
cat > /etc/skel/.config/gtk-3.0/settings.ini << 'EOF'
[Settings]
gtk-theme-name=Adwaita-dark
gtk-font-name=Segoe UI 10
gtk-application-prefer-dark-theme=1
EOF

cat > /etc/skel/.config/gtk-2.0/gtkrc << 'EOF'
gtk-theme-name="Adwaita-dark"
gtk-font-name="Segoe UI 10"
EOF

# ── .desktop files ────────────────────────────────────────────────────────────
mkdir -p /usr/share/applications

cat > /usr/share/applications/shuben-installer.desktop << 'EOF'
[Desktop Entry]
Name=Install Shuben Launcher OS
Comment=Install to your computer
Exec=shuben-installer
Icon=drive-harddisk
Terminal=false
Type=Application
Categories=System;
EOF

cat > /usr/share/applications/shuben-minecraft.desktop << 'EOF'
[Desktop Entry]
Name=Minecraft Launcher
Exec=shuben-minecraft-launcher
Icon=shuben-minecraft
Terminal=false
Type=Application
Categories=Game;
EOF

cat > /usr/share/applications/shuben-settings.desktop << 'EOF'
[Desktop Entry]
Name=Shuben Settings
Exec=shuben-settings
Icon=preferences-system
Terminal=false
Type=Application
Categories=Settings;
EOF

cat > /usr/share/applications/shuben-browser.desktop << 'EOF'
[Desktop Entry]
Name=Web Browser
Exec=microsoft-edge-stable %U
Icon=microsoft-edge
Terminal=false
Type=Application
Categories=Network;WebBrowser;
MimeType=x-scheme-handler/http;x-scheme-handler/https;
EOF

# Desktop shortcuts
mkdir -p /etc/skel/Desktop
cp /usr/share/applications/shuben-installer.desktop /etc/skel/Desktop/
cp /usr/share/applications/shuben-minecraft.desktop  /etc/skel/Desktop/
chmod +x /etc/skel/Desktop/*.desktop

# ── Generate wallpaper ────────────────────────────────────────────────────────
mkdir -p /usr/share/shuben-launcher/wallpapers
python3 << 'WALLEOF'
try:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1920, 1080))
    draw = ImageDraw.Draw(img)
    for y in range(1080):
        t = y / 1080
        r = int(5 + 15*t); g = int(8 + 20*t); b = int(20 + 50*t)
        draw.line([(0,y),(1920,y)], fill=(r,g,b))
    for x in range(0, 1920, 80):
        draw.line([(x,0),(x,1080)], fill=(20,20,30))
    for y in range(0, 1080, 80):
        draw.line([(0,y),(1920,y)], fill=(20,20,30))
    img.save("/usr/share/shuben-launcher/wallpapers/desktop.jpg", quality=95)
    lock = img.copy()
    ImageDraw.Draw(lock).rectangle([(0,0),(1920,1080)], fill=(0,0,0,100))
    lock.save("/usr/share/shuben-launcher/wallpapers/lockscreen.jpg", quality=90)
    print("Wallpapers generated.")
except Exception as e:
    print(f"Wallpaper skipped: {e}")
WALLEOF

# ── XDG dirs ──────────────────────────────────────────────────────────────────
mkdir -p /etc/skel/{Desktop,Downloads,Documents,Pictures,Videos}
cat > /etc/skel/.config/user-dirs.dirs << 'EOF'
XDG_DESKTOP_DIR="$HOME/Desktop"
XDG_DOWNLOAD_DIR="$HOME/Downloads"
XDG_DOCUMENTS_DIR="$HOME/Documents"
XDG_PICTURES_DIR="$HOME/Pictures"
XDG_VIDEOS_DIR="$HOME/Videos"
EOF

# ── Sudoers for shuben user ───────────────────────────────────────────────────
echo "shuben ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/shuben
chmod 440 /etc/sudoers.d/shuben

echo "==> Shuben chroot setup complete."
