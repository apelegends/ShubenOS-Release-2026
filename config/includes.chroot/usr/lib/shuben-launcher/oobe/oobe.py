#!/usr/bin/env python3
"""
Shuben Launcher OS — Out-of-Box Experience (OOBE)
Runs on first boot, fullscreen, before the desktop appears.
Stages: Welcome → Features/Warnings → WiFi → Account (or Skip) → PIN → Done
"""

import gi, os, sys, json, subprocess, threading, hashlib, time
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

STATE_FILE = "/var/lib/shuben/oobe-state.json"
USERS_FILE = "/var/lib/shuben/accounts.json"

ACCENT   = "#00A8E8"   # Shuben blue
BG_DARK  = "#0D1117"
BG_CARD  = "#161B22"
TEXT_W   = "#FFFFFF"
TEXT_G   = "#8B949E"
RED      = "#F85149"
GREEN    = "#3FB950"

CSS = f"""
* {{ font-family: 'Segoe UI', 'Liberation Sans', sans-serif; }}
window {{ background-color: {BG_DARK}; }}
.card {{
  background-color: {BG_CARD};
  border-radius: 12px;
  padding: 32px;
  border: 1px solid #30363D;
}}
.title {{
  color: {TEXT_W};
  font-size: 28px;
  font-weight: 700;
}}
.subtitle {{
  color: {TEXT_G};
  font-size: 15px;
}}
.btn-primary {{
  background: {ACCENT};
  color: {TEXT_W};
  border: none;
  border-radius: 6px;
  padding: 12px 28px;
  font-size: 15px;
  font-weight: 600;
}}
.btn-primary:hover {{ background: #0090CC; }}
.btn-secondary {{
  background: transparent;
  color: {TEXT_G};
  border: 1px solid #30363D;
  border-radius: 6px;
  padding: 10px 24px;
  font-size: 14px;
}}
.btn-secondary:hover {{ border-color: {ACCENT}; color: {TEXT_W}; }}
.btn-danger {{
  background: {RED};
  color: {TEXT_W};
  border: none;
  border-radius: 6px;
  padding: 12px 28px;
  font-size: 15px;
  font-weight: 600;
}}
.warning-box {{
  background: rgba(248,81,73,0.1);
  border: 1px solid {RED};
  border-radius: 8px;
  padding: 16px;
}}
.warning-text {{ color: {RED}; font-size: 14px; font-weight: 600; }}
.input-field {{
  background: #21262D;
  color: {TEXT_W};
  border: 1px solid #30363D;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 14px;
}}
.input-field:focus {{ border-color: {ACCENT}; }}
.pin-digit {{
  background: #21262D;
  color: {TEXT_W};
  border: 1px solid #30363D;
  border-radius: 8px;
  font-size: 24px;
  font-weight: 700;
  min-width: 56px;
  min-height: 64px;
}}
.pin-digit:focus {{ border-color: {ACCENT}; }}
.step-indicator {{ color: {TEXT_G}; font-size: 13px; }}
.step-active {{ color: {ACCENT}; font-weight: 700; }}
.feature-row {{
  padding: 10px 0;
  border-bottom: 1px solid #21262D;
}}
.shuben-logo {{
  color: {ACCENT};
  font-size: 42px;
  font-weight: 900;
  letter-spacing: 2px;
}}
"""

def apply_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

def save_state(data):
    os.makedirs("/var/lib/shuben", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def save_account(email, pw_hash, display_name):
    accounts = {}
    try:
        with open(USERS_FILE) as f:
            accounts = json.load(f)
    except Exception:
        pass
    accounts["primary"] = {
        "email": email,
        "pw_hash": pw_hash,
        "display_name": display_name or email.split("@")[0]
    }
    os.makedirs("/var/lib/shuben", exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(accounts, f)

def save_pin(pin):
    os.makedirs("/var/lib/shuben", exist_ok=True)
    with open("/var/lib/shuben/pin.json", "w") as f:
        json.dump({"pin_hash": hash_password(pin)}, f)
    # Also set system user password to something random (PIN used instead)
    subprocess.run(["passwd", "-l", "shuben"], capture_output=True)

# ─────────────────────────────────────────────────────────────────────────────
# OOBE Window
# ─────────────────────────────────────────────────────────────────────────────

class OOBEWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Launcher OS — Setup")
        self.set_default_size(900, 640)
        self.maximize()
        self.fullscreen()
        self.set_decorated(False)
        self.set_resizable(False)

        apply_css()

        self.state = load_state()
        self.account_data = {}

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self.stack.set_transition_duration(300)
        self.add(self.stack)

        self.build_welcome()
        self.build_features()
        self.build_wifi()
        self.build_account()
        self.build_pin()
        self.build_done()

        self.stack.set_visible_child_name("welcome")
        self.show_all()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def card(self, width=560):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.get_style_context().add_class("card")
        box.set_size_request(width, -1)
        return box

    def centered(self, child):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(child, False, False, 0)
        return outer

    def label(self, text, css_class="subtitle", wrap=True):
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class(css_class)
        lbl.set_line_wrap(wrap)
        lbl.set_xalign(0)
        return lbl

    def btn(self, text, css_class="btn-primary", callback=None):
        b = Gtk.Button(label=text)
        b.get_style_context().add_class(css_class)
        if callback:
            b.connect("clicked", callback)
        return b

    def entry(self, placeholder="", password=False):
        e = Gtk.Entry()
        e.set_placeholder_text(placeholder)
        e.get_style_context().add_class("input-field")
        if password:
            e.set_visibility(False)
            e.set_invisible_char("●")
        e.set_hexpand(True)
        return e

    def goto(self, name):
        self.stack.set_visible_child_name(name)

    def step_bar(self, steps, current):
        box = Gtk.Box(spacing=12)
        box.set_halign(Gtk.Align.CENTER)
        for i, s in enumerate(steps):
            lbl = Gtk.Label(label=s)
            lbl.get_style_context().add_class("step_active" if i == current else "step-indicator")
            box.pack_start(lbl, False, False, 0)
            if i < len(steps) - 1:
                sep = Gtk.Label(label="›")
                sep.get_style_context().add_class("step-indicator")
                box.pack_start(sep, False, False, 0)
        return box

    # ── Pages ─────────────────────────────────────────────────────────────────

    def build_welcome(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)

        c = self.card(600)
        c.set_spacing(20)

        logo = self.label("SHUBEN LAUNCHER", "shuben-logo", wrap=False)
        logo.set_xalign(0.5)
        c.pack_start(logo, False, False, 0)

        sub = self.label("Minecraft OS  ·  Built on Debian  ·  By Apelegends", "subtitle")
        sub.set_xalign(0.5)
        c.pack_start(sub, False, False, 0)

        sep = Gtk.Separator()
        c.pack_start(sep, False, False, 8)

        welcome_text = self.label(
            "Welcome! Let's get your system ready.\n"
            "This will only take a few minutes.",
            "subtitle"
        )
        welcome_text.set_xalign(0.5)
        c.pack_start(welcome_text, False, False, 0)

        btn_box = Gtk.Box(spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.pack_start(self.btn("Let's go →", callback=lambda _: self.goto("features")), False, False, 0)
        c.pack_start(btn_box, False, False, 24)

        page.pack_start(self.centered(c), True, True, 0)
        self.stack.add_named(page, "welcome")

    def build_features(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)

        c = self.card(620)
        c.set_spacing(16)

        bar = self.step_bar(["Features", "Wi-Fi", "Account", "PIN", "Done"], 0)
        c.pack_start(bar, False, False, 0)

        title = self.label("What's included", "title")
        title.set_xalign(0)
        c.pack_start(title, False, False, 8)

        features = [
            ("✅", "Custom Shuben Launcher desktop"),
            ("✅", "Minecraft Launcher pre-installed"),
            ("✅", "Auto GPU drivers (Intel / AMD / NVIDIA)"),
            ("✅", "Microsoft Edge browser"),
            ("✅", "Dual-boot ready (GRUB with Windows detection)"),
            ("✅", "PIN login — no Microsoft account required"),
            ("✅", "Lightweight — optimised for gaming"),
        ]

        for icon, text in features:
            row = Gtk.Box(spacing=12)
            row.get_style_context().add_class("feature-row")
            row.pack_start(self.label(icon, wrap=False), False, False, 0)
            row.pack_start(self.label(text), True, True, 0)
            c.pack_start(row, False, False, 0)

        # WARNING BOX
        warn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        warn_box.get_style_context().add_class("warning-box")
        w1 = self.label("⚠  NO ANTIVIRUS INCLUDED", "warning-text")
        w2 = self.label(
            "Shuben Launcher OS does NOT include antivirus software. "
            "It is your responsibility to stay safe online.",
            "subtitle"
        )
        warn_box.pack_start(w1, False, False, 0)
        warn_box.pack_start(w2, False, False, 0)

        self.accept_check = Gtk.CheckButton(label="I understand there is NO antivirus and I accept this.")
        self.accept_check.get_style_context().add_class("warning-text")

        c.pack_start(warn_box, False, False, 8)
        c.pack_start(self.accept_check, False, False, 4)

        self.features_next_btn = self.btn("Next →", callback=self.on_features_next)
        btn_box = Gtk.Box(spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.pack_end(self.features_next_btn, False, False, 0)
        c.pack_start(btn_box, False, False, 8)

        page.pack_start(self.centered(c), True, True, 0)
        self.stack.add_named(page, "features")

    def on_features_next(self, _):
        if not self.accept_check.get_active():
            dlg = Gtk.MessageDialog(
                transient_for=self, flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Please accept the no-antivirus notice to continue."
            )
            dlg.run(); dlg.destroy()
            return
        self.goto("wifi")

    def build_wifi(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)

        c = self.card(620)
        c.set_spacing(16)

        bar = self.step_bar(["Features", "Wi-Fi", "Account", "PIN", "Done"], 1)
        c.pack_start(bar, False, False, 0)

        title = self.label("Connect to Wi-Fi", "title")
        c.pack_start(title, False, False, 8)

        sub = self.label("Select a network or skip to connect later.", "subtitle")
        c.pack_start(sub, False, False, 0)

        # Network list (populated dynamically)
        self.wifi_listbox = Gtk.ListBox()
        self.wifi_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(160)
        sw.add(self.wifi_listbox)
        c.pack_start(sw, True, True, 0)

        self.wifi_ssid_entry = self.entry("SSID (network name)")
        self.wifi_pass_entry = self.entry("Password", password=True)
        c.pack_start(self.wifi_ssid_entry, False, False, 0)
        c.pack_start(self.wifi_pass_entry, False, False, 0)

        btn_row = Gtk.Box(spacing=12)
        btn_row.set_halign(Gtk.Align.END)
        btn_row.pack_start(
            self.btn("Scan networks", "btn-secondary", callback=self.on_wifi_scan),
            False, False, 0)
        btn_row.pack_start(
            self.btn("Skip", "btn-secondary", callback=lambda _: self.goto("account")),
            False, False, 0)
        btn_row.pack_start(
            self.btn("Connect →", callback=self.on_wifi_connect),
            False, False, 0)
        c.pack_start(btn_row, False, False, 8)

        self.wifi_status = self.label("", "step-indicator")
        c.pack_start(self.wifi_status, False, False, 0)

        page.pack_start(self.centered(c), True, True, 0)
        self.stack.add_named(page, "wifi")
        GLib.idle_add(self.on_wifi_scan, None)

    def on_wifi_scan(self, _):
        self.wifi_status.set_text("Scanning…")
        def scan():
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi"],
                    capture_output=True, text=True, timeout=10
                )
                networks = []
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[0].strip():
                        networks.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else "?"))
                GLib.idle_add(self.populate_wifi_list, networks)
            except Exception as e:
                GLib.idle_add(self.wifi_status.set_text, f"Scan error: {e}")
        threading.Thread(target=scan, daemon=True).start()

    def populate_wifi_list(self, networks):
        for child in self.wifi_listbox.get_children():
            self.wifi_listbox.remove(child)
        for ssid, signal in networks[:12]:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=12)
            box.set_margin_top(8); box.set_margin_bottom(8)
            box.set_margin_start(12); box.set_margin_end(12)
            lbl = Gtk.Label(label=ssid)
            lbl.set_xalign(0)
            sig_lbl = Gtk.Label(label=f"📶 {signal}")
            sig_lbl.get_style_context().add_class("step-indicator")
            box.pack_start(lbl, True, True, 0)
            box.pack_end(sig_lbl, False, False, 0)
            row.add(box)
            row.set_data("ssid", ssid)
            self.wifi_listbox.add(row)
        self.wifi_listbox.show_all()
        self.wifi_status.set_text(f"{len(networks)} networks found.")

        # Auto-fill SSID on row select
        def on_row_activated(lb, row):
            ssid = row.get_data("ssid")
            if ssid:
                self.wifi_ssid_entry.set_text(ssid)
                self.wifi_pass_entry.grab_focus()
        self.wifi_listbox.connect("row-activated", on_row_activated)

    def on_wifi_connect(self, _):
        ssid = self.wifi_ssid_entry.get_text().strip()
        pw   = self.wifi_pass_entry.get_text()
        if not ssid:
            self.wifi_status.set_text("Please enter or select a network name.")
            return
        self.wifi_status.set_text(f"Connecting to '{ssid}'…")
        def connect():
            try:
                cmd = ["nmcli", "dev", "wifi", "connect", ssid]
                if pw:
                    cmd += ["password", pw]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                if r.returncode == 0:
                    GLib.idle_add(self.wifi_status.set_text, f"✅ Connected to {ssid}")
                    GLib.timeout_add(1200, lambda: self.goto("account") or False)
                else:
                    GLib.idle_add(self.wifi_status.set_text, f"❌ Failed: {r.stderr.strip()[:80]}")
            except Exception as e:
                GLib.idle_add(self.wifi_status.set_text, f"Error: {e}")
        threading.Thread(target=connect, daemon=True).start()

    def build_account(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)

        c = self.card(540)
        c.set_spacing(16)

        bar = self.step_bar(["Features", "Wi-Fi", "Account", "PIN", "Done"], 2)
        c.pack_start(bar, False, False, 0)

        title = self.label("Sign in or create account", "title")
        c.pack_start(title, False, False, 8)

        sub = self.label("Works with any email address. No Microsoft account needed.", "subtitle")
        c.pack_start(sub, False, False, 0)

        # Tabs: Sign In / Sign Up
        tab_box = Gtk.Box(spacing=0)
        self.tab_signin_btn = self.btn("Sign In", "btn-secondary", callback=lambda _: self.show_account_tab("signin"))
        self.tab_signup_btn = self.btn("Sign Up", "btn-secondary", callback=lambda _: self.show_account_tab("signup"))
        tab_box.pack_start(self.tab_signin_btn, True, True, 0)
        tab_box.pack_start(self.tab_signup_btn, True, True, 0)
        c.pack_start(tab_box, False, False, 0)

        self.account_stack = Gtk.Stack()

        # Sign-in fields
        si_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.si_email = self.entry("Email address")
        self.si_pass  = self.entry("Password", password=True)
        si_box.pack_start(self.si_email, False, False, 0)
        si_box.pack_start(self.si_pass,  False, False, 0)
        self.account_stack.add_named(si_box, "signin")

        # Sign-up fields
        su_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.su_name  = self.entry("Display name (optional)")
        self.su_email = self.entry("Email address")
        self.su_pass  = self.entry("Password", password=True)
        self.su_pass2 = self.entry("Confirm password", password=True)
        su_box.pack_start(self.su_name,  False, False, 0)
        su_box.pack_start(self.su_email, False, False, 0)
        su_box.pack_start(self.su_pass,  False, False, 0)
        su_box.pack_start(self.su_pass2, False, False, 0)
        self.account_stack.add_named(su_box, "signup")

        c.pack_start(self.account_stack, False, False, 0)

        self.account_error = self.label("", "warning-text")
        c.pack_start(self.account_error, False, False, 0)

        btn_row = Gtk.Box(spacing=12)
        btn_row.set_halign(Gtk.Align.END)
        btn_row.pack_start(
            self.btn("Skip for now", "btn-secondary", callback=self.on_account_skip),
            False, False, 0)
        btn_row.pack_start(
            self.btn("Continue →", callback=self.on_account_continue),
            False, False, 0)
        c.pack_start(btn_row, False, False, 8)

        page.pack_start(self.centered(c), True, True, 0)
        self.stack.add_named(page, "account")
        self.account_stack.set_visible_child_name("signup")

    def show_account_tab(self, tab):
        self.account_stack.set_visible_child_name(tab)
        self.account_error.set_text("")

    def on_account_skip(self, _):
        self.account_data = {"skipped": True}
        save_account("", "", "User")
        self.goto("pin")

    def on_account_continue(self, _):
        tab = self.account_stack.get_visible_child_name()
        if tab == "signup":
            name  = self.su_name.get_text().strip()
            email = self.su_email.get_text().strip()
            pw    = self.su_pass.get_text()
            pw2   = self.su_pass2.get_text()
            if not email:
                self.account_error.set_text("Email address is required.")
                return
            if "@" not in email:
                self.account_error.set_text("Please enter a valid email address.")
                return
            if len(pw) < 4:
                self.account_error.set_text("Password must be at least 4 characters.")
                return
            if pw != pw2:
                self.account_error.set_text("Passwords do not match.")
                return
            save_account(email, hash_password(pw), name)
            self.account_data = {"email": email, "name": name}
        else:
            email = self.si_email.get_text().strip()
            pw    = self.si_pass.get_text()
            if not email:
                self.account_error.set_text("Email address is required.")
                return
            # Load saved accounts and verify
            try:
                with open(USERS_FILE) as f:
                    accounts = json.load(f)
                acct = accounts.get("primary", {})
                if acct.get("email") == email and acct.get("pw_hash") == hash_password(pw):
                    self.account_data = {"email": email}
                else:
                    self.account_error.set_text("Incorrect email or password.")
                    return
            except Exception:
                self.account_error.set_text("No account found. Please sign up first.")
                return
        self.goto("pin")

    def build_pin(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)

        c = self.card(480)
        c.set_spacing(16)

        bar = self.step_bar(["Features", "Wi-Fi", "Account", "PIN", "Done"], 3)
        c.pack_start(bar, False, False, 0)

        title = self.label("Set your PIN", "title")
        c.pack_start(title, False, False, 8)

        sub = self.label("Your PIN is used to unlock the desktop. Required.", "subtitle")
        c.pack_start(sub, False, False, 0)

        # 4 PIN digit boxes
        pin_box = Gtk.Box(spacing=12)
        pin_box.set_halign(Gtk.Align.CENTER)
        self.pin_entries = []
        for i in range(4):
            e = Gtk.Entry()
            e.set_max_length(1)
            e.set_max_width_chars(1)
            e.set_input_purpose(Gtk.InputPurpose.DIGITS)
            e.set_visibility(False)
            e.set_invisible_char("●")
            e.get_style_context().add_class("pin-digit")
            e.set_width_chars(2)
            # auto-advance
            idx = i
            def on_key(widget, event, next_idx=idx+1):
                if event.keyval in (Gdk.KEY_Return, Gdk.KEY_Tab):
                    if next_idx < len(self.pin_entries):
                        self.pin_entries[next_idx].grab_focus()
                return False
            e.connect("key-release-event", on_key)
            self.pin_entries.append(e)
            pin_box.pack_start(e, False, False, 0)
        c.pack_start(pin_box, False, False, 8)

        sub2 = self.label("Confirm PIN", "subtitle")
        c.pack_start(sub2, False, False, 0)

        pin_box2 = Gtk.Box(spacing=12)
        pin_box2.set_halign(Gtk.Align.CENTER)
        self.pin_confirm_entries = []
        for i in range(4):
            e = Gtk.Entry()
            e.set_max_length(1)
            e.set_max_width_chars(1)
            e.set_input_purpose(Gtk.InputPurpose.DIGITS)
            e.set_visibility(False)
            e.set_invisible_char("●")
            e.get_style_context().add_class("pin-digit")
            e.set_width_chars(2)
            idx = i
            def on_key2(widget, event, next_idx=idx+1):
                if event.keyval in (Gdk.KEY_Return, Gdk.KEY_Tab):
                    if next_idx < len(self.pin_confirm_entries):
                        self.pin_confirm_entries[next_idx].grab_focus()
                return False
            e.connect("key-release-event", on_key2)
            self.pin_confirm_entries.append(e)
            pin_box2.pack_start(e, False, False, 0)
        c.pack_start(pin_box2, False, False, 0)

        self.pin_error = self.label("", "warning-text")
        c.pack_start(self.pin_error, False, False, 0)

        btn_row = Gtk.Box()
        btn_row.set_halign(Gtk.Align.END)
        btn_row.pack_start(self.btn("Set PIN & finish →", callback=self.on_pin_set), False, False, 0)
        c.pack_start(btn_row, False, False, 8)

        page.pack_start(self.centered(c), True, True, 0)
        self.stack.add_named(page, "pin")

    def on_pin_set(self, _):
        pin  = "".join(e.get_text() for e in self.pin_entries)
        pin2 = "".join(e.get_text() for e in self.pin_confirm_entries)
        if len(pin) != 4 or not pin.isdigit():
            self.pin_error.set_text("Please enter a 4-digit PIN.")
            return
        if pin != pin2:
            self.pin_error.set_text("PINs do not match.")
            return
        save_pin(pin)
        # Mark OOBE complete
        state = load_state()
        state["oobe_complete"] = True
        state.update(self.account_data)
        save_state(state)
        self.goto("done")

    def build_done(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)

        c = self.card(540)
        c.set_spacing(20)

        done_lbl = self.label("🎮  You're all set!", "title")
        done_lbl.set_xalign(0.5)
        c.pack_start(done_lbl, False, False, 0)

        sub = self.label(
            "Shuben Launcher OS is ready.\n"
            "Your Minecraft launcher will open automatically.",
            "subtitle"
        )
        sub.set_xalign(0.5)
        c.pack_start(sub, False, False, 0)

        self.countdown_lbl = self.label("Starting desktop in 5…", "step-indicator")
        self.countdown_lbl.set_xalign(0.5)
        c.pack_start(self.countdown_lbl, False, False, 0)

        btn_row = Gtk.Box()
        btn_row.set_halign(Gtk.Align.CENTER)
        btn_row.pack_start(self.btn("Start now →", callback=self.launch_desktop), False, False, 0)
        c.pack_start(btn_row, False, False, 8)

        page.pack_start(self.centered(c), True, True, 0)
        self.stack.add_named(page, "done")
        self.stack.connect("notify::visible-child", self.on_page_changed)

    def on_page_changed(self, stack, _):
        if stack.get_visible_child_name() == "done":
            self.start_countdown()

    def start_countdown(self):
        self._countdown = 5
        def tick():
            self._countdown -= 1
            if self._countdown <= 0:
                self.launch_desktop(None)
                return False
            self.countdown_lbl.set_text(f"Starting desktop in {self._countdown}…")
            return True
        GLib.timeout_add(1000, tick)

    def launch_desktop(self, _):
        self.destroy()
        # Unfullscreen and launch openbox session
        subprocess.Popen(["openbox-session"])
        Gtk.main_quit()

def main():
    # Check if OOBE already done
    state = load_state()
    if state.get("oobe_complete"):
        sys.exit(0)

    win = OOBEWindow()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
