# Shuben Launcher OS 1.0

**Minecraft OS — Built on Debian 12 — by Apelegends / shuben**

A lightweight, gaming-focused operating system designed around the Minecraft experience.
Dual-boot ready, no antivirus, fully custom interface.

---

## Features

| Feature | Detail |
|---|---|
| 🎮 Minecraft Launcher | Custom UI, version picker, offline play |
| 🖥️ Custom Desktop | Openbox + Shuben taskbar (Windows 10 style) |
| 🔑 PIN Login | 4-digit PIN, no Microsoft account needed |
| 👤 Account | Any email/password — or skip entirely |
| 📶 Wi-Fi Setup | OOBE network picker + NetworkManager |
| 🎨 GPU Auto-detect | Intel, AMD, NVIDIA (nouveau) auto-configured |
| ⚙️ Settings App | Display, GPU, Sound, Network, PIN, Power |
| 🌐 Browser | Microsoft Edge (browser only) |
| ⚡ Lightweight | No antivirus, no GNOME, no KDE bloat |
| 🔄 Dual-boot | GRUB with Windows auto-detection (os-prober) |
| 💿 Installer | Calamares for permanent install + dual-boot |

---

## Build the ISO

### Via GitHub Actions (recommended — works on Windows)

1. Push this repo to GitHub (create a new repo, upload everything)
2. Go to **Actions** → **Build Shuben Launcher OS ISO** → **Run workflow**
3. Wait ~30–60 minutes
4. Download `shuben-launcher-os-1.0-amd64.iso` from the Artifacts

### Locally (Linux only)

```bash
# Install dependencies
sudo apt-get install -y live-build debootstrap squashfs-tools xorriso

# Clone/copy this project
cd shuben-launcher-os

# Configure
bash live-build-scripts/setup-lb.sh

# Build (takes ~20–45 min)
sudo lb build

# Your ISO is: shuben-launcher-os-1.0-amd64.iso
```

---

## Flash to USB

### Windows
- Use [Rufus](https://rufus.ie) — select the ISO, pick GPT + UEFI, write
- Or use [Balena Etcher](https://etcher.balena.io)

### Linux
```bash
sudo dd if=shuben-launcher-os-1.0-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

---

## First Boot — OOBE Steps

1. **Features & Warnings** — Read the feature list, accept the **NO ANTIVIRUS** notice
2. **Wi-Fi** — Pick your network or skip
3. **Account** — Sign up or sign in with any email, or click **Skip for now**
4. **PIN** — Set a 4-digit PIN (required)
5. **Done** — Minecraft Launcher opens automatically!

---

## Dual-Boot with Windows

The installer (Calamares) detects Windows automatically via os-prober.
On permanent install, GRUB will show:
- Shuben Launcher OS
- Windows 10 / 11 (detected automatically)

Recommended partition setup: leave existing Windows partitions, install alongside on free space.

---

## ⚠ No Antivirus — by design

Shuben Launcher OS intentionally ships **without antivirus software**.
This is disclosed during OOBE. Stay safe online — only run trusted software.

---

## Project Structure

```
shuben-launcher-os/
├── .github/workflows/build-iso.yml     ← GitHub Actions build
├── live-build-scripts/setup-lb.sh      ← live-build config
├── config/
│   ├── package-lists/shuben.list.chroot
│   └── hooks/live/
│       ├── 0010-install-edge.hook.chroot
│       ├── 0020-gpu-autodetect.hook.chroot
│       ├── 0030-install-shuben-apps.hook.chroot
│       ├── 0040-grub-dualboot.hook.chroot
│       └── 0050-cleanup.hook.chroot
│   └── includes.chroot/usr/lib/shuben-launcher/
│       ├── oobe/oobe.py                ← First-boot setup wizard
│       ├── login/pinlock.py            ← PIN lock screen
│       ├── desktop/taskbar.py          ← Custom taskbar
│       ├── minecraft/launcher.py       ← Minecraft launcher UI
│       └── settings/settings.py        ← Control panel
└── README.md
```

---

## Credits

Made by **shuben / Apelegends**
Based on Debian 12 Bookworm
