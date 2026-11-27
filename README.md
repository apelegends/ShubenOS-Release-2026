# Shuben Launcher OS 1.0
**Minecraft OS — Ubuntu 22.04 base — by Apelegends / shuben**

## How to build the ISO (GitHub Actions)

1. Create a new GitHub repository
2. Upload ALL files from this ZIP into the repo root (keeping folder structure)
3. Go to **Actions** tab → you will see **"Build Shuben Launcher OS ISO"**
4. Click **Run workflow** → wait ~45–90 minutes
5. Download `shuben-launcher-os-1.0-amd64.iso` from the **Artifacts** section

## Flash to USB
- **Windows:** Use [Rufus](https://rufus.ie) — select ISO, GPT + UEFI mode, write
- **Linux:** `sudo dd if=shuben-launcher-os-1.0-amd64.iso of=/dev/sdX bs=4M status=progress`

## First boot
Boot from USB → Shuben boot menu appears → choose **"Try Shuben Launcher OS"**  
The installer opens automatically on the desktop.

## Installer options
- **Erase Disk** — wipes the entire drive, clean install
- **Dual Boot** — installs alongside Windows in free space (needs 20+ GB free)

Every error shows exactly how to fix it.

## Features
- Custom Shuben desktop (Openbox + taskbar)
- Minecraft Launcher with version picker
- Auto GPU drivers (Intel / AMD / NVIDIA nouveau)
- Microsoft Edge browser
- PIN login — no Microsoft account needed
- OOBE setup wizard on first boot
- Dual-boot GRUB with Windows auto-detection
- **NO antivirus — by design (disclosed during setup)**

## Repo structure
```
.github/workflows/build-iso.yml   ← GitHub Actions build
scripts/chroot-setup.sh           ← System configuration
configs/grub.cfg                  ← Boot menu
shuben-ui/
  installer/installer.py          ← Custom installer UI
  oobe/oobe.py                    ← First-boot wizard
  login/pinlock.py                ← PIN lock screen
  desktop/taskbar.py              ← Taskbar + Start menu
  minecraft/launcher.py           ← Minecraft launcher UI
  settings/settings.py            ← Control panel
```
