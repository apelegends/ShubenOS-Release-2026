#!/usr/bin/env python3
"""
Shuben Launcher OS — Settings App
Custom Windows-10-inspired control panel.
"""

import gi, os, json, subprocess, threading
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

ACCENT  = "#00A8E8"
BG_DARK = "#0D1117"
BG_CARD = "#161B22"
TEXT_W  = "#FFFFFF"
TEXT_G  = "#8B949E"
GREEN   = "#3FB950"
RED     = "#F85149"

CSS = f"""
* {{ font-family: 'Segoe UI', 'Liberation Sans', sans-serif; }}
window {{ background-color: {BG_DARK}; }}
#sidebar {{ background: #0D1117; border-right: 1px solid #21262D; min-width: 200px; }}
.sidebar-btn {{
  background: transparent; border: none; color: {TEXT_G};
  border-radius: 8px; padding: 10px 16px; font-size: 13px;
}}
.sidebar-btn:hover {{ background: rgba(255,255,255,0.06); color: {TEXT_W}; }}
.sidebar-btn.active {{ background: rgba(0,168,232,0.15); color: {ACCENT}; border-left: 3px solid {ACCENT}; }}
.card {{ background: {BG_CARD}; border-radius: 10px; padding: 20px; border: 1px solid #21262D; }}
.title {{ color: {TEXT_W}; font-size: 20px; font-weight: 700; }}
.subtitle {{ color: {TEXT_G}; font-size: 13px; }}
.section-title {{ color: {TEXT_W}; font-size: 14px; font-weight: 600; }}
.btn-primary {{
  background: {ACCENT}; color: {TEXT_W}; border: none;
  border-radius: 6px; padding: 9px 20px; font-size: 13px; font-weight: 600;
}}
.btn-secondary {{
  background: transparent; color: {TEXT_G}; border: 1px solid #30363D;
  border-radius: 6px; padding: 7px 14px; font-size: 13px;
}}
.btn-secondary:hover {{ border-color: {ACCENT}; color: {TEXT_W}; }}
.btn-danger {{
  background: {RED}; color: {TEXT_W}; border: none;
  border-radius: 6px; padding: 9px 20px; font-size: 13px; font-weight: 600;
}}
.field {{
  background: #21262D; color: {TEXT_W}; border: 1px solid #30363D;
  border-radius: 6px; padding: 8px 12px; font-size: 13px;
}}
.field:focus {{ border-color: {ACCENT}; }}
.status-ok  {{ color: {GREEN}; font-size: 12px; }}
.status-err {{ color: {RED};   font-size: 12px; }}
.info-row {{ padding: 6px 0; border-bottom: 1px solid #21262D; }}
"""

GPU_INFO_FILE = "/var/lib/shuben/gpu-info.json"
ACCT_FILE     = "/var/lib/shuben/accounts.json"
PIN_FILE      = "/var/lib/shuben/pin.json"

PAGES = [
    ("🖥️",  "Display",   "display"),
    ("🎮",  "GPU",       "gpu"),
    ("🔊",  "Sound",     "sound"),
    ("📶",  "Network",   "network"),
    ("👤",  "Account",   "account"),
    ("🔑",  "PIN",       "pin"),
    ("⚡",  "Power",     "power"),
    ("ℹ️",  "About",     "about"),
]

class SettingsApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Settings")
        self.set_default_size(840, 560)
        self.set_decorated(False)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.build_ui()
        self.show_all()

    def build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        # Title bar
        tbar = Gtk.Box(spacing=0)
        tbar.set_size_request(-1, 36)
        tbar.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.05, 0.07, 0.09, 1))
        logo = Gtk.Label()
        logo.set_markup(f'<span foreground="{ACCENT}" font="12" font_weight="bold">  ⚙  Shuben Settings</span>')
        tbar.pack_start(logo, False, False, 0)
        tbar.pack_start(Gtk.Box(), True, True, 0)
        for sym, fn in [("─", self.iconify), ("□", lambda: self.maximize() if not self.is_maximized() else self.unmaximize()), ("✕", self.destroy)]:
            b = Gtk.Button(label=sym)
            b.get_style_context().add_class("btn-secondary")
            b.set_size_request(40, 36)
            b.connect("clicked", lambda _, f=fn: f())
            tbar.pack_end(b, False, False, 0)
        tbar.connect("button-press-event", lambda w, e: self.begin_move_drag(e.button, int(e.x_root), int(e.y_root), e.time))
        vbox.pack_start(tbar, False, False, 0)

        hbox = Gtk.Box()
        vbox.pack_start(hbox, True, True, 0)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sidebar.set_name("sidebar")
        sidebar.set_margin_top(12)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)
        self.sidebar_btns = {}
        for icon, label, name in PAGES:
            btn = Gtk.Button(label=f"{icon}  {label}")
            btn.get_style_context().add_class("sidebar-btn")
            btn.connect("clicked", lambda _, n=name: self.switch(n))
            sidebar.pack_start(btn, False, False, 0)
            self.sidebar_btns[name] = btn
        hbox.pack_start(sidebar, False, False, 0)

        # Stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        hbox.pack_start(self.stack, True, True, 0)

        self.build_display()
        self.build_gpu()
        self.build_sound()
        self.build_network()
        self.build_account()
        self.build_pin()
        self.build_power()
        self.build_about()

        self.switch("display")

    def switch(self, name):
        self.stack.set_visible_child_name(name)
        for n, b in self.sidebar_btns.items():
            ctx = b.get_style_context()
            if n == name: ctx.add_class("active")
            else: ctx.remove_class("active")

    def page_wrap(self, name, child):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_bottom(24)
        box.pack_start(child, False, False, 0)
        sw.add(box)
        self.stack.add_named(sw, name)

    def card(self, *children, spacing=12):
        c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        c.get_style_context().add_class("card")
        for ch in children: c.pack_start(ch, False, False, 0)
        return c

    def lbl(self, text, css="subtitle", xalign=0):
        l = Gtk.Label(label=text)
        l.get_style_context().add_class(css)
        l.set_xalign(xalign)
        return l

    def btn(self, text, css="btn-primary", cb=None):
        b = Gtk.Button(label=text)
        b.get_style_context().add_class(css)
        if cb: b.connect("clicked", cb)
        return b

    def run_cmd(self, cmd, status_lbl):
        status_lbl.set_text("Running…")
        def do():
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            msg = "✅ Done." if r.returncode == 0 else f"❌ {r.stderr[:80]}"
            GLib.idle_add(status_lbl.set_text, msg)
        threading.Thread(target=do, daemon=True).start()

    # ── DISPLAY ───────────────────────────────────────────────────────────────
    def build_display(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("Display", "title"), False, False, 0)

        status = self.lbl("", "status-ok")
        c = self.card(
            self.lbl("Resolution", "section-title"),
            self.lbl("Change display resolution:", "subtitle"),
        )
        res_box = Gtk.Box(spacing=10)
        for res in ["1920x1080", "1600x900", "1366x768", "1280x720"]:
            b = self.btn(res, "btn-secondary",
                         lambda _, r=res: self.run_cmd(f"xrandr -s {r}", status))
            res_box.pack_start(b, False, False, 0)
        c.pack_start(res_box, False, False, 0)

        c.pack_start(self.lbl("Refresh rate", "section-title"), False, False, 0)
        rr_box = Gtk.Box(spacing=10)
        for hz in ["60Hz", "75Hz", "120Hz", "144Hz", "165Hz"]:
            b = self.btn(hz, "btn-secondary",
                         lambda _, h=hz.replace("Hz",""): self.run_cmd(
                             f"xrandr --rate {h}", status))
            rr_box.pack_start(b, False, False, 0)
        c.pack_start(rr_box, False, False, 0)

        c.pack_start(status, False, False, 0)
        vbox.pack_start(c, False, False, 0)
        self.page_wrap("display", vbox)

    # ── GPU ───────────────────────────────────────────────────────────────────
    def build_gpu(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("GPU & Graphics", "title"), False, False, 0)

        # Load detected GPU info
        gpu_info = {}
        try:
            with open(GPU_INFO_FILE) as f:
                gpu_info = json.load(f)
        except Exception:
            pass

        raw = gpu_info.get("raw", "Not detected yet")
        detected = []
        if gpu_info.get("intel"): detected.append("Intel")
        if gpu_info.get("amd"):   detected.append("AMD")
        if gpu_info.get("nvidia"): detected.append("NVIDIA (nouveau)")

        info_card = self.card(
            self.lbl("Detected GPU(s)", "section-title"),
            self.lbl(", ".join(detected) if detected else "Run GPU setup first", "subtitle"),
            self.lbl(f"Raw: {raw}", "subtitle"),
        )
        vbox.pack_start(info_card, False, False, 0)

        status = self.lbl("", "status-ok")
        drv_card = self.card(
            self.lbl("Driver actions", "section-title"),
            self.btn("Re-run GPU auto-setup",
                     cb=lambda _: self.run_cmd("pkexec shuben-gpu-setup", status)),
        )

        # NVIDIA proprietary
        if gpu_info.get("nvidia"):
            drv_card.pack_start(self.lbl("NVIDIA — install proprietary driver:", "subtitle"), False, False, 0)
            nb = Gtk.Box(spacing=10)
            for pkg in ["nvidia-driver", "nvidia-driver-525", "nvidia-driver-535"]:
                b = self.btn(pkg, "btn-secondary",
                             lambda _, p=pkg: self.run_cmd(f"pkexec apt-get install -y {p}", status))
                nb.pack_start(b, False, False, 0)
            drv_card.pack_start(nb, False, False, 0)

        drv_card.pack_start(status, False, False, 0)
        vbox.pack_start(drv_card, False, False, 0)

        # Vulkan info
        vulk_status = self.lbl("", "status-ok")
        vulk_card = self.card(
            self.lbl("Vulkan", "section-title"),
            self.btn("Check Vulkan support",
                     cb=lambda _: self.run_cmd("vulkaninfo | head -20 > /tmp/vk.txt && xterm -e 'cat /tmp/vk.txt; read'", vulk_status)),
            vulk_status,
        )
        vbox.pack_start(vulk_card, False, False, 0)
        self.page_wrap("gpu", vbox)

    # ── SOUND ─────────────────────────────────────────────────────────────────
    def build_sound(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("Sound", "title"), False, False, 0)
        c = self.card(
            self.lbl("Volume", "section-title"),
        )
        self.vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol_scale.set_value(80)
        self.vol_scale.set_hexpand(True)
        self.vol_scale.connect("value-changed", self.on_vol_change)
        c.pack_start(self.vol_scale, False, False, 0)
        c.pack_start(self.btn("Open full audio settings",
                              cb=lambda _: subprocess.Popen(["pavucontrol"])), False, False, 0)
        vbox.pack_start(c, False, False, 0)
        self.page_wrap("sound", vbox)

    def on_vol_change(self, scale):
        v = int(scale.get_value())
        subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{v}%"])

    # ── NETWORK ───────────────────────────────────────────────────────────────
    def build_network(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("Network & Wi-Fi", "title"), False, False, 0)
        status = self.lbl("", "status-ok")
        c = self.card(
            self.lbl("Wi-Fi", "section-title"),
            self.btn("Open Network Manager",
                     cb=lambda _: subprocess.Popen(["nm-connection-editor"])),
            self.lbl("Ethernet", "section-title"),
            self.btn("Check connection", "btn-secondary",
                     cb=lambda _: self.run_cmd("ip addr show | head -30 > /tmp/net.txt && xterm -e 'cat /tmp/net.txt; read'", status)),
            status,
        )
        vbox.pack_start(c, False, False, 0)
        self.page_wrap("network", vbox)

    # ── ACCOUNT ───────────────────────────────────────────────────────────────
    def build_account(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("Account", "title"), False, False, 0)

        acct = {}
        try:
            with open(ACCT_FILE) as f:
                acct = json.load(f).get("primary", {})
        except Exception:
            pass

        name  = acct.get("display_name") or acct.get("email", "").split("@")[0] or "User"
        email = acct.get("email", "(no account)")

        c = self.card(
            self.lbl("Current account", "section-title"),
            self.lbl(f"Name:  {name}", "subtitle"),
            self.lbl(f"Email: {email}", "subtitle"),
        )

        c.pack_start(self.lbl("Change display name", "section-title"), False, False, 0)
        self.acct_name_entry = Gtk.Entry()
        self.acct_name_entry.set_text(name)
        self.acct_name_entry.get_style_context().add_class("field")
        c.pack_start(self.acct_name_entry, False, False, 0)

        acct_status = self.lbl("", "status-ok")
        def save_name(_):
            new_name = self.acct_name_entry.get_text().strip()
            try:
                data = {}
                try:
                    with open(ACCT_FILE) as f: data = json.load(f)
                except: pass
                if "primary" not in data: data["primary"] = {}
                data["primary"]["display_name"] = new_name
                with open(ACCT_FILE, "w") as f: json.dump(data, f)
                acct_status.set_text("✅ Saved.")
            except Exception as e:
                acct_status.set_text(f"❌ {e}")

        c.pack_start(self.btn("Save name", cb=save_name), False, False, 0)
        c.pack_start(acct_status, False, False, 0)
        vbox.pack_start(c, False, False, 0)
        self.page_wrap("account", vbox)

    # ── PIN ───────────────────────────────────────────────────────────────────
    def build_pin(self):
        import hashlib
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("PIN", "title"), False, False, 0)

        c = self.card(self.lbl("Change your PIN", "section-title"))

        for attr, ph in [("pin_old", "Current PIN"), ("pin_new", "New PIN"), ("pin_new2", "Confirm new PIN")]:
            e = Gtk.Entry()
            e.set_placeholder_text(ph)
            e.set_visibility(False)
            e.set_max_length(4)
            e.get_style_context().add_class("field")
            setattr(self, attr, e)
            c.pack_start(e, False, False, 0)

        pin_status = self.lbl("", "status-ok")

        def change_pin(_):
            old  = self.pin_old.get_text()
            new  = self.pin_new.get_text()
            new2 = self.pin_new2.get_text()
            if not (old.isdigit() and new.isdigit() and new2.isdigit()):
                pin_status.set_text("❌ PINs must be digits only.")
                return
            if new != new2:
                pin_status.set_text("❌ New PINs do not match.")
                return
            try:
                stored = json.load(open(PIN_FILE)).get("pin_hash", "")
                if hashlib.sha256(old.encode()).hexdigest() != stored:
                    pin_status.set_text("❌ Current PIN is incorrect.")
                    return
                with open(PIN_FILE, "w") as f:
                    json.dump({"pin_hash": hashlib.sha256(new.encode()).hexdigest()}, f)
                pin_status.set_text("✅ PIN changed.")
                for e in [self.pin_old, self.pin_new, self.pin_new2]: e.set_text("")
            except Exception as ex:
                pin_status.set_text(f"❌ {ex}")

        c.pack_start(self.btn("Change PIN", cb=change_pin), False, False, 0)
        c.pack_start(pin_status, False, False, 0)
        vbox.pack_start(c, False, False, 0)
        self.page_wrap("pin", vbox)

    # ── POWER ─────────────────────────────────────────────────────────────────
    def build_power(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("Power", "title"), False, False, 0)
        c = self.card(self.lbl("Power options", "section-title"))
        row = Gtk.Box(spacing=12)
        for label, cmd in [
            ("🔒 Lock",      "shuben-lock"),
            ("🔄 Restart",   "systemctl reboot"),
            ("⏻  Shut down", "systemctl poweroff"),
            ("💤 Suspend",   "systemctl suspend"),
        ]:
            b = self.btn(label, "btn-secondary" if "Lock" not in label else "btn-primary",
                         lambda _, c=cmd: subprocess.Popen(c.split()))
            row.pack_start(b, False, False, 0)
        c.pack_start(row, False, False, 0)
        vbox.pack_start(c, False, False, 0)
        self.page_wrap("power", vbox)

    # ── ABOUT ─────────────────────────────────────────────────────────────────
    def build_about(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.pack_start(self.lbl("About Shuben Launcher OS", "title"), False, False, 0)

        try:
            kern = subprocess.check_output(["uname", "-r"], text=True).strip()
        except: kern = "unknown"
        try:
            cpu = subprocess.check_output(
                "grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2",
                shell=True, text=True).strip()
        except: cpu = "unknown"
        try:
            mem = subprocess.check_output(
                "grep MemTotal /proc/meminfo | awk '{print $2}'",
                shell=True, text=True).strip()
            mem = f"{int(mem)//1024} MB"
        except: mem = "unknown"

        gpu_info = {}
        try:
            with open(GPU_INFO_FILE) as f: gpu_info = json.load(f)
        except: pass
        gpus = []
        if gpu_info.get("intel"):  gpus.append("Intel")
        if gpu_info.get("amd"):    gpus.append("AMD")
        if gpu_info.get("nvidia"): gpus.append("NVIDIA")
        gpu_str = ", ".join(gpus) if gpus else "Not detected"

        c = self.card(
            self.lbl("System information", "section-title"),
        )
        for key, val in [
            ("OS",      "Shuben Launcher OS 1.0"),
            ("Base",    "Debian 12 Bookworm"),
            ("By",      "Shuben / Apelegends"),
            ("Kernel",  kern),
            ("CPU",     cpu or "unknown"),
            ("RAM",     mem),
            ("GPU",     gpu_str),
            ("Browser", "Microsoft Edge"),
        ]:
            row = Gtk.Box(spacing=16)
            row.get_style_context().add_class("info-row")
            kl = self.lbl(key, "section-title")
            kl.set_size_request(120, -1)
            vl = self.lbl(val, "subtitle")
            row.pack_start(kl, False, False, 0)
            row.pack_start(vl, True, True, 0)
            c.pack_start(row, False, False, 0)

        no_av = Gtk.Label()
        no_av.set_markup(f'<span foreground="{RED}" font_weight="bold">⚠  NO ANTIVIRUS — by design</span>')
        no_av.set_xalign(0)
        c.pack_start(no_av, False, False, 8)

        vbox.pack_start(c, False, False, 0)
        self.page_wrap("about", vbox)

def main():
    win = SettingsApp()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
