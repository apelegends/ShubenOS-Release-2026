#!/bin/bash
# Shuben Launcher OS — live-build configuration script
set -e

echo "==> Configuring live-build for Shuben Launcher OS..."

lb config \
  --mode debian \
  --distribution bookworm \
  --archive-areas "main contrib non-free non-free-firmware" \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --bootloader grub-efi \
  --debian-installer none \
  --memtest none \
  --iso-application "Shuben Launcher OS" \
  --iso-publisher "Shuben / Apelegends" \
  --iso-volume "SHUBEN-LAUNCHER-OS" \
  --firmware-binary true \
  --firmware-chroot true \
  --apt-recommends false \
  --security true \
  --updates true \
  --backports false \
  --compression xz \
  --zsync false \
  --checksums sha256

echo "==> live-build configured."
