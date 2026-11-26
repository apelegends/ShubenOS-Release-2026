#!/usr/bin/env python3
"""
Shuben Launcher OS — Custom Installer
Options: Erase Disk (clean install) or Dual-Boot (alongside Windows/Linux)
Full error reporting with fix instructions on every failure.
Must be run as root.
"""

import gi, os, sys, json, subprocess, threading, time, shutil, re
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

# ── Colours ──────────────────────────────────────────────────────────────────
ACCENT  = "#00A8E8"
BG_DARK = "#0D1117"
BG_CARD = "#161B22"
TEXT_W  = "#FFFFFF"
TEXT_G  = "#8B949E"
GREEN   = "#3FB950"
RED     = "#F85149"
ORANGE  = "#D29922"

CSS = f"""
* {{ font-family: 'Segoe UI', 'Liberation Sans', sans-serif; }}
window {{ background-color: {BG_DARK}; }}
.card {{
  background: {BG_CARD};
  border-radius: 10px;
  padding: 24px;
  border: 1px solid #21262D;
}}
.title   {{ color: {TEXT_W}; font-size: 24px; font-weight: 700; }}
.heading {{ color: {TEXT_W}; font-size: 16px; font-weight: 600; }}
.subtitle {{ color: {TEXT_G}; font-size: 13px; }}
.logo {{
  color: {ACCENT};
  font-size: 30px;
  font-weight: 900;
  letter-spacing: 2px;
}}
.btn-primary {{
  background: {ACCENT}; color: {TEXT_W}; border: none;
  border-radius: 7px; padding: 12px 28px;
  font-size: 14px; font-weight: 700;
}}
.btn-primary:hover {{ background: #0090CC; }}
.btn-secondary {{
  background: transparent; color: {TEXT_G};
  border: 1px solid #30363D; border-radius: 7px;
  padding: 10px 22px; font-size: 14px;
}}
.btn-secondary:hover {{ border-color: {ACCENT}; color: {TEXT_W}; }}
.btn-danger {{
  background: {RED}; color: {TEXT_W}; border: none;
  border-radius: 7px; padding: 12px 28px;
  font-size: 14px; font-weight: 700;
}}
.btn-danger:hover {{ background: #c0392b; }}
.btn-back {{
  background: transparent; color: {TEXT_G};
  border: none; font-size: 13px; padding: 6px 0;
}}
.option-card {{
  background: {BG_CARD};
  border-radius: 12px;
  padding: 20px;
  border: 2px solid #21262D;
}}
.option-card:hover {{ border-color: {ACCENT}; }}
.option-card.selected {{ border-color: {ACCENT}; background: rgba(0,168,232,0.07); }}
.disk-row {{
  background: rgba(255,255,255,0.03);
  border-radius: 7px;
  padding: 12px 16px;
  border: 1px solid #21262D;
}}
.disk-row:hover {{ border-color: {ACCENT}; }}
.disk-row.selected {{ border-color: {ACCENT}; background: rgba(0,168,232,0.08); }}
.warn-box {{
  background: rgba(248,81,73,0.09);
  border: 1px solid {RED};
  border-radius: 8px;
  padding: 14px;
}}
.warn-text {{ color: {RED}; font-size: 13px; font-weight: 600; }}
.info-box {{
  background: rgba(0,168,232,0.07);
  border: 1px solid {ACCENT};
  border-radius: 8px;
  padding: 14px;
}}
.info-text {{ color: {ACCENT}; font-size: 13px; }}
.progress-bar progress {{ background: {ACCENT}; border-radius: 4px; }}
.progress-bar trough {{ background: #21262D; border-radius: 4px; }}
.log-view {{
  background: #0A0E13;
  color: #A0B0C0;
  font-family: 'Liberation Mono', monospace;
  font-size: 12px;
  border-radius: 6px;
  padding: 10px;
}}
.error-box {{
  background: rgba(248,81,73,0.12);
  border: 1px solid {RED};
  border-radius: 8px;
  padding: 16px;
}}
.error-title {{ color: {RED}; font-size: 15px; font-weight: 700; }}
.error-body  {{ color: {TEXT_W}; font-size: 13px; }}
.fix-box {{
  background: rgba(61,185,80,0.09);
  border: 1px solid {GREEN};
  border-radius: 8px;
  padding: 14px;
}}
.fix-title {{ color: {GREEN}; font-size: 13px; font-weight: 700; }}
.fix-body  {{ color: {TEXT_G}; font-size: 12px; }}
.step-dot {{
  min-width: 10px; min-height: 10px;
  border-radius: 5px;
  background: #30363D;
}}
.step-dot.done   {{ background: {GREEN}; }}
.step-dot.active {{ background: {ACCENT}; }}
.step-dot.error  {{ background: {RED}; }}
.success-text {{ color: {GREEN}; font-size: 20px; font-weight: 700; }}
"""

# ── Error database: known errors → fix instructions ───────────────────────
ERROR_FIXES = {
    "No space left":
        "The disk or partition is full.\n"
        "• Go back and choose a larger disk\n"
        "• Or use 'Erase Disk' mode to wipe the whole drive",
    "No medium found":
        "The selected disk disappeared.\n"
        "• Check that the drive is still plugged in\n"
        "• Try a different USB port\n"
        "• Reboot and try again",
    "Permission denied":
        "The installer lacks permission.\n"
        "• Make sure you launched the installer as root\n"
        "• Open a terminal and run: sudo shuben-installer",
    "read-only file system":
        "The disk is write-protected.\n"
        "• Check the physical write-protect switch on the drive\n"
        "• Try a different disk",
    "Device or resource busy":
        "The disk is in use by another process.\n"
        "• Unmount any mounted partitions on that disk first\n"
        "• Run: sudo umount /dev/sdXN  (replace X and N)\n"
        "• Then restart the installer",
    "Input/output error":
        "Disk read/write error — the drive may be failing.\n"
        "• Try a different disk or USB drive\n"
        "• Run: sudo badblocks -v /dev/sdX to check for bad sectors",
    "not enough free space":
        "Not enough free space for dual-boot.\n"
        "• You need at least 20 GB of unallocated space\n"
        "• Shrink your Windows partition first:\n"
        "  Windows → Disk Management → right-click C: → Shrink Volume",
    "failed to find a free partition":
        "The disk has no free (unallocated) space.\n"
        "• Shrink an existing partition to make room\n"
        "• Or use 'Erase Disk' mode instead",
    "grub-install":
        "GRUB bootloader installation failed.\n"
        "• Make sure UEFI Secure Boot is DISABLED in BIOS\n"
        "  (BIOS → Security → Secure Boot → Disabled)\n"
        "• Try a different EFI partition\n"
        "• If dual-booting with Windows, check Windows Fast Startup is OFF",
    "efi":
        "EFI/UEFI error.\n"
        "• Disable Secure Boot in BIOS/UEFI settings\n"
        "• Make sure you booted the USB in UEFI mode (not Legacy/CSM)\n"
        "• Look for 'Boot Mode: UEFI' in BIOS",
    "mkfs":
        "Partition formatting failed.\n"
        "• The disk may be write-protected or failing\n"
        "• Try a different drive\n"
        "• Run: sudo fsck /dev/sdXN to check the partition",
    "parted":
        "Partitioning error.\n"
        "• The disk partition table may be corrupted\n"
        "• Back up your data first!\n"
        "• Try: sudo parted /dev/sdX mklabel gpt  (WARNING: erases disk)\n"
        "• Or use a different disk",
    "mount":
        "Could not mount the partition.\n"
        "• The filesystem may be damaged\n"
        "• Run: sudo fsck /dev/sdXN\n"
        "• Make sure no other process is using it",
    "rsync":
        "File copy failed.\n"
        "• Check that the source (live ISO) is fully loaded\n"
        "• Make sure the destination has enough space\n"
        "• Try re-running the installer",
    "squashfs":
        "Could not read the live filesystem.\n"
        "• The ISO may be corrupted\n"
        "• Re-download and re-flash the ISO to USB\n"
        "• Try a different USB drive",
    "debootstrap":
        "Base system installation failed.\n"
        "• Check your internet connection\n"
        "• Try a different mirror or retry\n"
        "• Make sure the target partition has enough space (20+ GB)",
    "timeout":
        "An operation timed out.\n"
        "• Check your internet connection\n"
        "• The disk may be very slow — try a faster drive\n"
        "• Retry the installation",
}

def get_fix(error_text):
    """Return a human-readable fix for a known error, or a generic tip."""
    err_lower = error_text.lower()
    for keyword, fix in ERROR_FIXES.items():
        if keyword.lower() in err_lower:
            return fix
    return (
        "An unexpected error occurred.\n"
        "• Take a photo of this screen and report it at:\n"
        "  github.com/apelegends/shuben-launcher-os/issues\n"
        "• Include the full error message above\n"
        "• Try restarting the installer"
    )

# ── Disk helpers ──────────────────────────────────────────────────────────────
def list_disks():
    """Return list of dicts: {device, model, size, size_bytes, partitions}"""
    disks = []
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,MODEL,SIZE,TYPE,MOUNTPOINT,FSTYPE,HOTPLUG"],
            text=True
        )
        data = json.loads(out)
        for dev in data.get("blockdevices", []):
            if dev.get("type") != "disk":
                continue
            # Skip the live boot device
            if dev.get("mountpoint") in ["/", "/run/live/medium"]:
                continue
            # Get size in bytes
            try:
                size_bytes = int(subprocess.check_output(
                    ["blockdev", "--getsize64", f"/dev/{dev['name']}"],
                    text=True).strip())
            except Exception:
                size_bytes = 0
            partitions = []
            for child in dev.get("children", []):
                partitions.append({
                    "name": child["name"],
                    "size": child.get("size", "?"),
                    "fstype": child.get("fstype", ""),
                    "mountpoint": child.get("mountpoint", ""),
                })
            disks.append({
                "device": f"/dev/{dev['name']}",
                "model": dev.get("model") or dev["name"],
                "size": dev.get("size", "?"),
                "size_bytes": size_bytes,
                "partitions": partitions,
            })
    except Exception as e:
        pass
    return disks

def has_windows(disk):
    """Check if any partition on disk looks like Windows."""
    try:
        out = subprocess.check_output(
            ["parted", disk["device"], "-s", "print"],
            text=True, stderr=subprocess.DEVNULL)
        return "ntfs" in out.lower() or "microsoft" in out.lower()
    except Exception:
        return False

def free_space_gb(disk):
    """Rough estimate of free (unpartitioned) space on the disk in GB."""
    try:
        total = disk["size_bytes"]
        used = 0
        for p in disk["partitions"]:
            try:
                pb = int(subprocess.check_output(
                    ["blockdev", "--getsize64", f"/dev/{p['name']}"],
                    text=True).strip())
                used += pb
            except Exception:
                pass
        free = total - used
        return free / (1024 ** 3)
    except Exception:
        return 0

# ── Main installer window ─────────────────────────────────────────────────────
class Installer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Launcher OS — Installer")
        self.set_default_size(820, 580)
        self.maximize()
        self.set_decorated(False)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.install_mode   = None   # "erase" or "dualboot"
        self.selected_disk  = None
        self.log_lines      = []
        self.install_steps  = []

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self.stack.set_transition_duration(260)
        self.add(self.stack)

        self.build_welcome()
        self.build_choose_mode()
        self.build_choose_disk()
        self.build_confirm()
        self.build_installing()
        self.build_done()
        self.build_error()

        self.stack.set_visible_child_name("welcome")
        self.show_all()

    # ── Layout helpers ────────────────────────────────────────────────────────
    def goto(self, page): self.stack.set_visible_child_name(page)

    def centered(self, child, margin=0):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        if margin: box.set_margin_top(margin)
        box.pack_start(child, False, False, 0)
        return box

    def lbl(self, text, css="subtitle", xalign=0, wrap=True):
        l = Gtk.Label(label=text)
        l.get_style_context().add_class(css)
        l.set_xalign(xalign)
        l.set_line_wrap(wrap)
        return l

    def btn(self, text, css="btn-primary", cb=None):
        b = Gtk.Button(label=text)
        b.get_style_context().add_class(css)
        if cb: b.connect("clicked", cb)
        return b

    def card(self, *children, spacing=14):
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        c.get_style_context().add_class("card")
        for ch in children: c.pack_start(ch, False, False, 0)
        return c

    def scroll(self, child, min_h=120):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(min_h)
        sw.add(child)
        return sw

    def page_box(self, name, child, width=680):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        child.set_size_request(width, -1)
        outer.pack_start(child, False, False, 0)
        self.stack.add_named(outer, name)

    # ── WELCOME ───────────────────────────────────────────────────────────────
    def build_welcome(self):
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        c.get_style_context().add_class("card")
        c.set_size_request(600, -1)

        logo = self.lbl("SHUBEN LAUNCHER OS", "logo", xalign=0.5)
        c.pack_start(logo, False, False, 0)

        sub = self.lbl("Installer  ·  v1.0", "subtitle", xalign=0.5)
        c.pack_start(sub, False, False, 0)

        sep = Gtk.Separator(); c.pack_start(sep, False, False, 4)

        c.pack_start(self.lbl(
            "This will install Shuben Launcher OS to your computer.\n"
            "You can choose to erase the disk or dual-boot alongside Windows.",
            "subtitle", xalign=0.5), False, False, 0)

        warn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        warn.get_style_context().add_class("warn-box")
        warn.pack_start(self.lbl("⚠  Back up your data before continuing!", "warn-text"), False, False, 0)
        warn.pack_start(self.lbl(
            "The installer can erase your entire disk. Make sure your files are safe.",
            "subtitle"), False, False, 0)
        c.pack_start(warn, False, False, 0)

        # Root check
        if os.geteuid() != 0:
            root_warn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            root_warn.get_style_context().add_class("error-box")
            root_warn.pack_start(self.lbl("❌  Not running as root!", "error-title"), False, False, 0)
            root_warn.pack_start(self.lbl(
                "The installer must be run as root.\n"
                "Open a terminal and run:  sudo shuben-installer",
                "error-body"), False, False, 0)
            c.pack_start(root_warn, False, False, 0)
            start_btn = self.btn("Cannot continue — not root", "btn-danger")
            start_btn.set_sensitive(False)
        else:
            start_btn = self.btn("Start installation →", cb=lambda _: self.goto("mode"))

        btn_row = Gtk.Box(); btn_row.set_halign(Gtk.Align.CENTER)
        btn_row.pack_start(start_btn, False, False, 0)
        c.pack_start(btn_row, False, False, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(c, False, False, 0)
        self.stack.add_named(outer, "welcome")

    # ── CHOOSE MODE ───────────────────────────────────────────────────────────
    def build_choose_mode(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        vbox.set_size_request(680, -1)

        vbox.pack_start(self.lbl("How do you want to install?", "title"), False, False, 0)
        vbox.pack_start(self.lbl(
            "Choose an installation mode.", "subtitle"), False, False, 0)

        # Option cards
        opts_box = Gtk.Box(spacing=16)

        # Erase Disk
        erase_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        erase_card.get_style_context().add_class("option-card")
        erase_card.pack_start(self.lbl("🗑️", "title", xalign=0.5), False, False, 0)
        erase_card.pack_start(self.lbl("Erase Disk", "heading", xalign=0.5), False, False, 0)
        erase_card.pack_start(self.lbl(
            "Wipe the entire selected disk and install Shuben Launcher OS.\n"
            "Best for dedicated gaming machines or new drives.\n\n"
            "⚠ ALL DATA ON THE DISK WILL BE DELETED.",
            "subtitle", xalign=0.5), False, False, 0)
        erase_btn = self.btn("Choose Erase Disk", "btn-danger",
                             cb=lambda _: self.on_mode("erase"))
        erase_card.pack_start(erase_btn, False, False, 8)
        opts_box.pack_start(erase_card, True, True, 0)

        # Dual Boot
        dual_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        dual_card.get_style_context().add_class("option-card")
        dual_card.pack_start(self.lbl("⚡", "title", xalign=0.5), False, False, 0)
        dual_card.pack_start(self.lbl("Dual Boot", "heading", xalign=0.5), False, False, 0)
        dual_card.pack_start(self.lbl(
            "Install alongside Windows or another OS.\n"
            "Choose which OS to boot from GRUB at startup.\n\n"
            "Requires 20+ GB of free unallocated space on the disk.",
            "subtitle", xalign=0.5), False, False, 0)
        dual_btn = self.btn("Choose Dual Boot", "btn-primary",
                            cb=lambda _: self.on_mode("dualboot"))
        dual_card.pack_start(dual_btn, False, False, 8)
        opts_box.pack_start(dual_card, True, True, 0)

        vbox.pack_start(opts_box, False, False, 0)

        back_btn = self.btn("← Back", "btn-back", cb=lambda _: self.goto("welcome"))
        vbox.pack_start(back_btn, False, False, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(vbox, False, False, 0)
        self.stack.add_named(outer, "mode")

    def on_mode(self, mode):
        self.install_mode = mode
        self.refresh_disk_list()
        self.goto("disk")

    # ── CHOOSE DISK ───────────────────────────────────────────────────────────
    def build_choose_disk(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_size_request(700, -1)

        self.disk_title = self.lbl("Select a disk", "title")
        vbox.pack_start(self.disk_title, False, False, 0)
        self.disk_subtitle = self.lbl("", "subtitle")
        vbox.pack_start(self.disk_subtitle, False, False, 0)

        self.disk_listbox = Gtk.ListBox()
        self.disk_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.disk_listbox.connect("row-selected", self.on_disk_selected)
        vbox.pack_start(self.scroll(self.disk_listbox, 220), False, False, 0)

        self.disk_warn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.disk_warn.get_style_context().add_class("warn-box")
        self.disk_warn_lbl = self.lbl("", "warn-text")
        self.disk_warn.pack_start(self.disk_warn_lbl, False, False, 0)
        self.disk_warn.set_visible(False)
        vbox.pack_start(self.disk_warn, False, False, 0)

        btn_row = Gtk.Box(spacing=12)
        btn_row.pack_start(self.btn("← Back", "btn-back",
                                    cb=lambda _: self.goto("mode")), False, False, 0)
        btn_row.pack_start(Gtk.Box(), True, True, 0)
        btn_row.pack_start(self.btn("Refresh", "btn-secondary",
                                    cb=lambda _: self.refresh_disk_list()), False, False, 0)
        self.disk_next_btn = self.btn("Next →", cb=self.on_disk_next)
        self.disk_next_btn.set_sensitive(False)
        btn_row.pack_start(self.disk_next_btn, False, False, 0)
        vbox.pack_start(btn_row, False, False, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(vbox, False, False, 0)
        self.stack.add_named(outer, "disk")

    def refresh_disk_list(self):
        for row in self.disk_listbox.get_children():
            self.disk_listbox.remove(row)
        self.selected_disk = None
        self.disk_next_btn.set_sensitive(False)

        if self.install_mode == "erase":
            self.disk_title.set_text("Select disk to erase")
            self.disk_subtitle.set_text(
                "⚠  The entire disk will be wiped. All data will be lost.")
        else:
            self.disk_title.set_text("Select disk for dual-boot")
            self.disk_subtitle.set_text(
                "The installer will use free (unallocated) space on this disk.")

        disks = list_disks()
        if not disks:
            row = Gtk.ListBoxRow()
            lbl = self.lbl(
                "No disks found!\n"
                "• Make sure a drive is connected\n"
                "• The live USB itself is excluded\n"
                "• Try clicking Refresh",
                "warn-text")
            lbl.set_margin_top(12); lbl.set_margin_bottom(12)
            lbl.set_margin_start(12); lbl.set_margin_end(12)
            row.add(lbl)
            self.disk_listbox.add(row)
            self.disk_listbox.show_all()
            return

        for disk in disks:
            row = Gtk.ListBoxRow()
            row.set_data("disk", disk)
            box = Gtk.Box(spacing=16)
            box.get_style_context().add_class("disk-row")
            box.set_margin_top(6); box.set_margin_bottom(6)
            box.set_margin_start(8); box.set_margin_end(8)

            # Icon
            icon_lbl = self.lbl("💾" if disk["size_bytes"] > 50*1024**3 else "🖴", "heading")
            icon_lbl.set_size_request(32, -1)
            box.pack_start(icon_lbl, False, False, 0)

            # Info
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            name_lbl = self.lbl(
                f"{disk['model']}  ({disk['device']})", "heading")
            size_lbl = self.lbl(f"Size: {disk['size']}", "subtitle")
            info_box.pack_start(name_lbl, False, False, 0)
            info_box.pack_start(size_lbl, False, False, 0)

            # Partitions summary
            if disk["partitions"]:
                parts_text = "  ".join(
                    f"{p['name']} ({p['size']} {p['fstype'] or '?'})"
                    for p in disk["partitions"][:4])
                info_box.pack_start(self.lbl(parts_text, "subtitle"), False, False, 0)

            # Windows detected badge
            if has_windows(disk):
                win_lbl = self.lbl("🪟 Windows detected", "info-text")
                info_box.pack_start(win_lbl, False, False, 0)

            # Dual-boot free space warning
            if self.install_mode == "dualboot":
                free = free_space_gb(disk)
                if free < 20:
                    free_lbl = self.lbl(
                        f"⚠  Only ~{free:.1f} GB free — need 20+ GB", "warn-text")
                    info_box.pack_start(free_lbl, False, False, 0)
                else:
                    free_lbl = self.lbl(f"✅  ~{free:.1f} GB free", "status-ok")
                    info_box.pack_start(free_lbl, False, False, 0)

            box.pack_start(info_box, True, True, 0)
            row.add(box)
            self.disk_listbox.add(row)

        self.disk_listbox.show_all()

    def on_disk_selected(self, listbox, row):
        if row is None:
            self.selected_disk = None
            self.disk_next_btn.set_sensitive(False)
            return
        disk = row.get_data("disk")
        if disk is None:
            return
        self.selected_disk = disk

        # Validate for dual-boot
        if self.install_mode == "dualboot":
            free = free_space_gb(disk)
            if free < 20:
                self.disk_warn_lbl.set_text(
                    f"⚠  Only ~{free:.1f} GB free on this disk.\n"
                    "Dual-boot needs at least 20 GB of unallocated space.\n"
                    "Shrink your Windows C: partition first using Windows Disk Management.")
                self.disk_warn.set_visible(True)
                self.disk_next_btn.set_sensitive(False)
                return

        self.disk_warn.set_visible(False)
        self.disk_next_btn.set_sensitive(True)

    def on_disk_next(self, _):
        if not self.selected_disk:
            return
        self.refresh_confirm()
        self.goto("confirm")

    # ── CONFIRM ───────────────────────────────────────────────────────────────
    def build_confirm(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        vbox.set_size_request(660, -1)

        vbox.pack_start(self.lbl("Confirm installation", "title"), False, False, 0)

        self.confirm_summary = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.confirm_summary.get_style_context().add_class("card")
        vbox.pack_start(self.confirm_summary, False, False, 0)

        self.confirm_warn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.confirm_warn.get_style_context().add_class("warn-box")
        self.confirm_warn_lbl = self.lbl("", "warn-text")
        self.confirm_warn.pack_start(self.confirm_warn_lbl, False, False, 0)
        vbox.pack_start(self.confirm_warn, False, False, 0)

        self.confirm_check = Gtk.CheckButton(
            label="I understand what will happen and want to proceed.")
        self.confirm_check.connect("toggled",
            lambda btn: self.confirm_btn.set_sensitive(btn.get_active()))
        vbox.pack_start(self.confirm_check, False, False, 0)

        btn_row = Gtk.Box(spacing=12)
        btn_row.pack_start(self.btn("← Back", "btn-back",
                                    cb=lambda _: self.goto("disk")), False, False, 0)
        btn_row.pack_start(Gtk.Box(), True, True, 0)
        self.confirm_btn = self.btn("Install now ▶", "btn-danger",
                                    cb=self.on_confirm)
        self.confirm_btn.set_sensitive(False)
        btn_row.pack_start(self.confirm_btn, False, False, 0)
        vbox.pack_start(btn_row, False, False, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(vbox, False, False, 0)
        self.stack.add_named(outer, "confirm")

    def refresh_confirm(self):
        for ch in self.confirm_summary.get_children():
            self.confirm_summary.remove(ch)
        self.confirm_check.set_active(False)

        disk = self.selected_disk
        mode = self.install_mode

        rows = [
            ("Mode",   "🗑️ Erase Disk — FULL WIPE" if mode == "erase" else "⚡ Dual Boot"),
            ("Disk",   f"{disk['model']}  ({disk['device']})"),
            ("Size",   disk["size"]),
            ("OS",     "Shuben Launcher OS 1.0"),
        ]
        if mode == "erase":
            rows.append(("⚠ Warning", "ALL data on this disk will be permanently deleted!"))
        else:
            rows.append(("Free space", f"~{free_space_gb(disk):.1f} GB will be used"))

        for key, val in rows:
            row = Gtk.Box(spacing=16)
            kl = self.lbl(key, "heading"); kl.set_size_request(100, -1)
            vl = self.lbl(val, "subtitle" if key != "⚠ Warning" else "warn-text")
            row.pack_start(kl, False, False, 0)
            row.pack_start(vl, True, True, 0)
            self.confirm_summary.pack_start(row, False, False, 0)

        if mode == "erase":
            self.confirm_warn_lbl.set_text(
                "⚠  This will ERASE everything on the disk. This cannot be undone.")
        else:
            self.confirm_warn_lbl.set_text(
                "⚠  Dual-boot will use free space. Existing partitions will NOT be deleted.")
        self.confirm_summary.show_all()

    def on_confirm(self, _):
        self.goto("installing")
        threading.Thread(target=self.run_install, daemon=True).start()

    # ── INSTALLING ────────────────────────────────────────────────────────────
    def build_installing(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_size_request(700, -1)

        vbox.pack_start(self.lbl("Installing Shuben Launcher OS…", "title"), False, False, 0)
        vbox.pack_start(self.lbl(
            "Do not turn off your computer.", "subtitle"), False, False, 0)

        # Step indicators
        self.steps_box = Gtk.Box(spacing=10)
        self.steps_box.set_halign(Gtk.Align.START)
        self.step_labels = []
        step_names = [
            "Partition", "Format", "Copy files",
            "Install bootloader", "Configure", "Finish"
        ]
        for i, name in enumerate(step_names):
            step_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            step_col.set_halign(Gtk.Align.CENTER)
            dot = Gtk.Box()
            dot.get_style_context().add_class("step-dot")
            dot.set_size_request(12, 12)
            lbl = self.lbl(name, "subtitle", xalign=0.5)
            step_col.pack_start(dot, False, False, 0)
            step_col.pack_start(lbl, False, False, 0)
            self.steps_box.pack_start(step_col, False, False, 0)
            self.step_labels.append(dot)
            if i < len(step_names) - 1:
                sep = Gtk.Label(label="──")
                sep.get_style_context().add_class("subtitle")
                self.steps_box.pack_start(sep, False, False, 0)
        vbox.pack_start(self.steps_box, False, False, 0)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.get_style_context().add_class("progress-bar")
        self.progress.set_show_text(True)
        self.progress.set_text("Preparing…")
        vbox.pack_start(self.progress, False, False, 0)

        # Current action
        self.install_action_lbl = self.lbl("", "subtitle")
        vbox.pack_start(self.install_action_lbl, False, False, 0)

        # Log
        self.log_buffer = Gtk.TextBuffer()
        log_view = Gtk.TextView(buffer=self.log_buffer)
        log_view.set_editable(False)
        log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        log_view.get_style_context().add_class("log-view")
        vbox.pack_start(self.scroll(log_view, 180), True, True, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(vbox, False, False, 0)
        self.stack.add_named(outer, "installing")

    def log(self, text):
        GLib.idle_add(self._append_log, text)

    def _append_log(self, text):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text + "\n")

    def set_step(self, idx, state="active"):
        """state: active | done | error"""
        def _do():
            for i, dot in enumerate(self.step_labels):
                ctx = dot.get_style_context()
                ctx.remove_class("active")
                ctx.remove_class("done")
                ctx.remove_class("error")
                if i < idx:
                    ctx.add_class("done")
                elif i == idx:
                    ctx.add_class(state)
        GLib.idle_add(_do)

    def set_progress(self, fraction, text=""):
        def _do():
            self.progress.set_fraction(min(fraction, 1.0))
            if text: self.progress.set_text(text)
            self.install_action_lbl.set_text(text)
        GLib.idle_add(_do)

    def run_cmd(self, cmd, step_idx, desc="", check=True):
        """Run a shell command. On error, raise with full output."""
        self.log(f"$ {cmd}")
        self.set_progress(None, desc)
        try:
            result = subprocess.run(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, timeout=600
            )
            self.log(result.stdout or "")
            if check and result.returncode != 0:
                raise RuntimeError(
                    f"Command failed (exit {result.returncode}):\n{cmd}\n\n"
                    f"Output:\n{result.stdout or '(no output)'}"
                )
            return result.stdout or ""
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Timed out after 600s:\n{cmd}")

    # ── The actual install logic ───────────────────────────────────────────────
    def run_install(self):
        disk = self.selected_disk["device"]
        mode = self.install_mode

        TARGET   = "/mnt/shuben-install"
        EFI_PART = ""
        ROOT_PART = ""

        try:
            os.makedirs(TARGET, exist_ok=True)

            # ── STEP 0: Partition ─────────────────────────────────────────────
            self.set_step(0, "active")
            self.set_progress(0.05, "Partitioning disk…")

            if mode == "erase":
                self.log("==> Erasing disk and creating new partition table…")
                self.run_cmd(f"wipefs -a {disk}", 0, "Wiping disk signatures…")
                self.run_cmd(f"parted -s {disk} mklabel gpt", 0, "Creating GPT table…")
                # EFI partition (512 MB)
                self.run_cmd(
                    f"parted -s {disk} mkpart EFI fat32 1MiB 513MiB",
                    0, "Creating EFI partition…")
                self.run_cmd(
                    f"parted -s {disk} set 1 esp on", 0)
                # Root partition (rest)
                self.run_cmd(
                    f"parted -s {disk} mkpart root ext4 513MiB 100%",
                    0, "Creating root partition…")
                # Find actual partition names (e.g. sda1, nvme0n1p1)
                lsblk_out = self.run_cmd(
                    f"lsblk -ln -o NAME {disk}", 0, check=False)
                parts = [l.strip() for l in lsblk_out.strip().split("\n")
                         if l.strip() and l.strip() != disk.split("/")[-1]]
                if len(parts) < 2:
                    raise RuntimeError(
                        "Could not find newly created partitions.\n"
                        "The partitioning step may have failed.\n"
                        "Try running: sudo parted " + disk + " print")
                EFI_PART  = f"/dev/{parts[0]}"
                ROOT_PART = f"/dev/{parts[1]}"

            else:  # dual-boot
                self.log("==> Setting up dual-boot partitions in free space…")
                # Find free space start/end
                parted_out = self.run_cmd(
                    f"parted -s {disk} unit MiB print free", 0,
                    "Scanning free space…", check=False)
                free_regions = []
                for line in parted_out.split("\n"):
                    if "Free Space" in line:
                        parts_line = line.split()
                        try:
                            start = parts_line[0].replace("MiB","")
                            end   = parts_line[1].replace("MiB","")
                            size  = float(parts_line[2].replace("MiB",""))
                            if size >= 20*1024:
                                free_regions.append((start, end, size))
                        except Exception:
                            pass
                if not free_regions:
                    raise RuntimeError(
                        "No free space region of 20+ GB found on the disk.\n"
                        "To fix this:\n"
                        "• Boot into Windows\n"
                        "• Open Disk Management (Win+X → Disk Management)\n"
                        "• Right-click your C: drive → Shrink Volume\n"
                        "• Shrink by at least 20480 MB (20 GB)\n"
                        "• Then reboot the installer")

                start, end, size = free_regions[0]
                self.log(f"Free region: {start} MiB – {end} MiB ({size/1024:.1f} GB)")

                # Create EFI only if none exists
                efi_check = self.run_cmd(
                    f"parted -s {disk} print | grep -i 'esp\\|efi'",
                    0, check=False)
                if not efi_check.strip():
                    # Create EFI in first 512 MiB of free space
                    efi_end = str(int(start) + 512)
                    self.run_cmd(
                        f"parted -s {disk} mkpart EFI fat32 {start}MiB {efi_end}MiB",
                        0, "Creating EFI partition…")
                    self.run_cmd(f"parted -s {disk} set 1 esp on", 0)
                    start = efi_end
                    # Find EFI partition
                    lsblk_out = self.run_cmd(
                        f"lsblk -ln -o NAME,PARTTYPE {disk}", 0, check=False)
                    for line in lsblk_out.split("\n"):
                        if "c12a7328" in line.lower() or "EFI" in line:
                            EFI_PART = f"/dev/{line.split()[0]}"
                            break
                else:
                    # Use existing EFI
                    for line in efi_check.strip().split("\n"):
                        num = re.search(r'^\s*(\d+)', line)
                        if num:
                            suffix = num.group(1)
                            base = re.sub(r'\d+$', '', disk)
                            EFI_PART = f"{base}{suffix}"
                            break

                # Root partition in remaining free space
                self.run_cmd(
                    f"parted -s {disk} mkpart shuben ext4 {start}MiB {end}",
                    0, "Creating Shuben root partition…")

                # Find the new root partition
                lsblk_out2 = self.run_cmd(
                    f"lsblk -ln -o NAME {disk}", 0, check=False)
                all_parts = [l.strip() for l in lsblk_out2.strip().split("\n")
                             if l.strip() and l.strip() != disk.split("/")[-1]]
                ROOT_PART = f"/dev/{all_parts[-1]}"

            self.log(f"EFI partition:  {EFI_PART}")
            self.log(f"Root partition: {ROOT_PART}")
            self.set_step(0, "done")

            # ── STEP 1: Format ────────────────────────────────────────────────
            self.set_step(1, "active")
            self.set_progress(0.15, "Formatting partitions…")

            if EFI_PART:
                self.run_cmd(f"mkfs.fat -F32 {EFI_PART}", 1, "Formatting EFI partition…")
            self.run_cmd(f"mkfs.ext4 -F -L 'ShubenOS' {ROOT_PART}", 1,
                        "Formatting root partition…")
            self.set_step(1, "done")

            # ── STEP 2: Copy files ────────────────────────────────────────────
            self.set_step(2, "active")
            self.set_progress(0.25, "Mounting partitions…")
            self.run_cmd(f"mount {ROOT_PART} {TARGET}", 2, "Mounting root…")
            if EFI_PART:
                os.makedirs(f"{TARGET}/boot/efi", exist_ok=True)
                self.run_cmd(f"mount {EFI_PART} {TARGET}/boot/efi", 2,
                            "Mounting EFI…")

            self.set_progress(0.30, "Copying system files (this takes a while)…")
            self.log("==> Copying live filesystem to disk…")

            # Try squashfs first, then rsync from live root
            squash = "/run/live/medium/live/filesystem.squashfs"
            if os.path.exists(squash):
                self.run_cmd(
                    f"unsquashfs -f -d {TARGET} {squash}",
                    2, "Extracting system files…")
            else:
                # Fallback: rsync from live root
                excludes = " ".join([
                    f"--exclude={x}" for x in [
                        "/proc/*", "/sys/*", "/dev/*", "/run/*",
                        "/mnt/*", "/media/*", "/tmp/*", "/lost+found",
                    ]])
                self.run_cmd(
                    f"rsync -aAX {excludes} / {TARGET}/",
                    2, "Copying files via rsync…")

            self.set_progress(0.60, "Files copied.")
            self.set_step(2, "done")

            # ── STEP 3: Install bootloader ────────────────────────────────────
            self.set_step(3, "active")
            self.set_progress(0.65, "Installing GRUB bootloader…")

            # Bind mounts for chroot
            for bind in ["dev", "proc", "sys", "run"]:
                os.makedirs(f"{TARGET}/{bind}", exist_ok=True)
                self.run_cmd(f"mount --bind /{bind} {TARGET}/{bind}", 3)
            if EFI_PART:
                os.makedirs(f"{TARGET}/boot/efi", exist_ok=True)

            self.run_cmd(
                f"chroot {TARGET} grub-install --target=x86_64-efi "
                f"--efi-directory=/boot/efi --bootloader-id='Shuben Launcher OS' "
                f"--recheck {disk}",
                3, "Installing GRUB EFI…")

            self.run_cmd(
                f"chroot {TARGET} update-grub",
                3, "Generating GRUB config…")

            self.set_step(3, "done")

            # ── STEP 4: Configure ─────────────────────────────────────────────
            self.set_step(4, "active")
            self.set_progress(0.80, "Configuring system…")

            # fstab
            root_uuid = self.run_cmd(
                f"blkid -s UUID -o value {ROOT_PART}", 4).strip()
            efi_uuid  = self.run_cmd(
                f"blkid -s UUID -o value {EFI_PART}", 4).strip() if EFI_PART else ""

            fstab = f"# Shuben Launcher OS fstab\n"
            fstab += f"UUID={root_uuid}  /          ext4  errors=remount-ro  0  1\n"
            if efi_uuid:
                fstab += f"UUID={efi_uuid}   /boot/efi  vfat  umask=0077         0  1\n"
            fstab += "tmpfs  /tmp  tmpfs  defaults,nosuid,nodev  0  0\n"

            with open(f"{TARGET}/etc/fstab", "w") as f:
                f.write(fstab)
            self.log("fstab written.")

            # Hostname
            with open(f"{TARGET}/etc/hostname", "w") as f:
                f.write("shuben-launcher\n")

            # Locale
            self.run_cmd(
                f"chroot {TARGET} locale-gen en_US.UTF-8",
                4, "Setting locale…", check=False)

            # Reset OOBE state so it runs on first login
            oobe_state = f"{TARGET}/var/lib/shuben/oobe-state.json"
            if os.path.exists(oobe_state):
                os.remove(oobe_state)
            mc_flag = f"{TARGET}/var/lib/shuben/.mc-launched"
            if os.path.exists(mc_flag):
                os.remove(mc_flag)

            self.set_step(4, "done")

            # ── STEP 5: Finish / unmount ──────────────────────────────────────
            self.set_step(5, "active")
            self.set_progress(0.92, "Cleaning up…")

            for bind in ["run", "sys", "proc", "dev"]:
                self.run_cmd(f"umount -l {TARGET}/{bind}", 5, check=False)
            if EFI_PART:
                self.run_cmd(f"umount {TARGET}/boot/efi", 5, check=False)
            self.run_cmd(f"umount {TARGET}", 5, "Unmounting…", check=False)

            self.set_step(5, "done")
            self.set_progress(1.0, "Installation complete!")
            self.log("\n✅ Shuben Launcher OS installed successfully!")
            GLib.timeout_add(1200, lambda: self.goto("done") or False)

        except Exception as e:
            error_text = str(e)
            fix_text = get_fix(error_text)
            GLib.idle_add(self.show_error, error_text, fix_text)

    # ── ERROR PAGE ────────────────────────────────────────────────────────────
    def build_error(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_size_request(680, -1)

        vbox.pack_start(self.lbl("❌  Installation failed", "title"), False, False, 0)
        vbox.pack_start(self.lbl(
            "An error occurred. Read below to find out how to fix it.",
            "subtitle"), False, False, 0)

        self.error_box_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.error_box_widget.get_style_context().add_class("error-box")
        self.error_title_lbl = self.lbl("Error details", "error-title")
        self.error_body_lbl  = self.lbl("", "error-body")
        self.error_body_lbl.set_selectable(True)
        self.error_box_widget.pack_start(self.error_title_lbl, False, False, 0)
        self.error_box_widget.pack_start(self.error_body_lbl,  False, False, 0)
        vbox.pack_start(self.scroll(self.error_box_widget, 120), False, False, 0)

        self.fix_box_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.fix_box_widget.get_style_context().add_class("fix-box")
        fix_header = self.lbl("🔧  How to fix this", "fix-title")
        self.fix_body_lbl = self.lbl("", "fix-body")
        self.fix_body_lbl.set_selectable(True)
        self.fix_box_widget.pack_start(fix_header, False, False, 0)
        self.fix_box_widget.pack_start(self.fix_body_lbl, False, False, 0)
        vbox.pack_start(self.fix_box_widget, False, False, 0)

        report_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        report_box.get_style_context().add_class("info-box")
        report_box.pack_start(self.lbl(
            "📋  If the fix above didn't help, report this issue:", "info-text"),
            False, False, 0)
        report_box.pack_start(self.lbl(
            "github.com/apelegends/shuben-launcher-os/issues\n"
            "Include a photo of this screen.", "subtitle"), False, False, 0)
        vbox.pack_start(report_box, False, False, 0)

        btn_row = Gtk.Box(spacing=12)
        btn_row.pack_start(
            self.btn("← Try again", cb=lambda _: self.goto("mode")),
            False, False, 0)
        btn_row.pack_start(
            self.btn("Open terminal", "btn-secondary",
                     cb=lambda _: subprocess.Popen(["lxterminal"])),
            False, False, 0)
        vbox.pack_start(btn_row, False, False, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(vbox, False, False, 0)
        self.stack.add_named(outer, "error")

    def show_error(self, error_text, fix_text):
        # Mark failed step
        for i, dot in enumerate(self.step_labels):
            ctx = dot.get_style_context()
            if "active" in ctx.list_classes():
                ctx.remove_class("active")
                ctx.add_class("error")
                break
        self.error_body_lbl.set_text(error_text)
        self.fix_body_lbl.set_text(fix_text)
        self.goto("error")

    # ── DONE ─────────────────────────────────────────────────────────────────
    def build_done(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        vbox.set_size_request(560, -1)
        vbox.set_halign(Gtk.Align.CENTER)

        ok_lbl = self.lbl("✅  Installation complete!", "success-text", xalign=0.5)
        vbox.pack_start(ok_lbl, False, False, 0)

        sub = self.lbl(
            "Shuben Launcher OS has been installed successfully.\n"
            "Remove the USB drive, then reboot your computer.",
            "subtitle", xalign=0.5)
        vbox.pack_start(sub, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info.get_style_context().add_class("info-box")
        info.pack_start(self.lbl("What happens next:", "info-text"), False, False, 0)
        info.pack_start(self.lbl(
            "1. Remove the USB drive\n"
            "2. Reboot — GRUB will appear if dual-booting\n"
            "3. Select 'Shuben Launcher OS'\n"
            "4. The setup wizard (OOBE) will run\n"
            "5. Set your PIN and you're ready!",
            "subtitle"), False, False, 0)
        vbox.pack_start(info, False, False, 0)

        self.countdown_lbl = self.lbl("", "subtitle", xalign=0.5)
        vbox.pack_start(self.countdown_lbl, False, False, 0)

        btn_row = Gtk.Box(spacing=12)
        btn_row.set_halign(Gtk.Align.CENTER)
        btn_row.pack_start(
            self.btn("🔄  Reboot now",
                     cb=lambda _: subprocess.Popen(["systemctl", "reboot"])),
            False, False, 0)
        btn_row.pack_start(
            self.btn("Continue using live session", "btn-secondary",
                     cb=lambda _: self.destroy()),
            False, False, 0)
        vbox.pack_start(btn_row, False, False, 0)

        outer = Gtk.Box()
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(vbox, False, False, 0)
        self.stack.add_named(outer, "done")
        self.stack.connect("notify::visible-child", self.on_stack_changed)

    def on_stack_changed(self, stack, _):
        if stack.get_visible_child_name() == "done":
            self._countdown = 60
            GLib.timeout_add(1000, self.done_tick)

    def done_tick(self):
        self._countdown -= 1
        self.countdown_lbl.set_text(
            f"Auto-rebooting in {self._countdown}s…")
        if self._countdown <= 0:
            subprocess.Popen(["systemctl", "reboot"])
            return False
        return True

def main():
    if os.geteuid() != 0:
        # Try to re-exec as root
        try:
            os.execvp("pkexec", ["pkexec", sys.executable] + sys.argv)
        except Exception:
            pass

    win = Installer()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
