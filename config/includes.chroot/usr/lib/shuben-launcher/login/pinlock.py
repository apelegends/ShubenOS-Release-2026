#!/usr/bin/env python3
"""
Shuben Launcher OS — PIN Lock Screen
Shown after OOBE and on every wake/login.
"""

import gi, os, json, hashlib, subprocess, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

PIN_FILE  = "/var/lib/shuben/pin.json"
ACCT_FILE = "/var/lib/shuben/accounts.json"

ACCENT   = "#00A8E8"
BG_DARK  = "#0D1117"
BG_CARD  = "#161B22"
TEXT_W   = "#FFFFFF"
TEXT_G   = "#8B949E"
RED      = "#F85149"

CSS = f"""
* {{ font-family: 'Segoe UI', 'Liberation Sans', sans-serif; }}
window {{
  background-image: url('/usr/share/shuben-launcher/wallpapers/lockscreen.jpg');
  background-size: cover;
  background-position: center;
}}
.lock-card {{
  background: rgba(13,17,23,0.90);
  border-radius: 16px;
  padding: 40px 48px;
  border: 1px solid rgba(255,255,255,0.08);
}}
.user-name {{ color: {TEXT_W}; font-size: 22px; font-weight: 700; }}
.user-email {{ color: {TEXT_G}; font-size: 13px; }}
.time-lbl {{ color: {TEXT_W}; font-size: 64px; font-weight: 300; }}
.date-lbl {{ color: {TEXT_G}; font-size: 16px; }}
.pin-digit {{
  background: rgba(255,255,255,0.08);
  color: {TEXT_W};
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 8px;
  font-size: 28px;
  font-weight: 700;
  min-width: 60px;
  min-height: 70px;
}}
.pin-digit:focus {{ border-color: {ACCENT}; }}
.error-lbl {{ color: {RED}; font-size: 13px; }}
.hint-lbl {{ color: {TEXT_G}; font-size: 12px; }}
.btn-unlock {{
  background: {ACCENT};
  color: {TEXT_W};
  border: none;
  border-radius: 6px;
  padding: 12px 32px;
  font-size: 15px;
  font-weight: 600;
}}
"""

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def load_pin_hash():
    try:
        with open(PIN_FILE) as f:
            return json.load(f).get("pin_hash", "")
    except Exception:
        return ""

def load_account():
    try:
        with open(ACCT_FILE) as f:
            return json.load(f).get("primary", {})
    except Exception:
        return {}

class PinLock(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.fullscreen()
        self.set_decorated(False)
        self.set_keep_above(True)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.pin_hash = load_pin_hash()
        self.acct = load_account()
        self.attempts = 0

        overlay = Gtk.Overlay()
        self.add(overlay)

        # Clock overlay (top left)
        clock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        clock_box.set_margin_top(48)
        clock_box.set_margin_start(64)
        clock_box.set_valign(Gtk.Align.START)
        clock_box.set_halign(Gtk.Align.START)
        self.time_lbl = Gtk.Label()
        self.time_lbl.get_style_context().add_class("time-lbl")
        self.date_lbl = Gtk.Label()
        self.date_lbl.get_style_context().add_class("date-lbl")
        clock_box.pack_start(self.time_lbl, False, False, 0)
        clock_box.pack_start(self.date_lbl, False, False, 0)
        overlay.add_overlay(clock_box)

        # PIN card (center)
        from datetime import datetime
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        card.get_style_context().add_class("lock-card")
        card.set_halign(Gtk.Align.CENTER)
        card.set_valign(Gtk.Align.CENTER)

        # User avatar / name
        name = self.acct.get("display_name") or self.acct.get("email", "").split("@")[0] or "User"
        email = self.acct.get("email", "")
        avatar_lbl = Gtk.Label(label="🎮")
        avatar_lbl.set_markup('<span font="48">🎮</span>')
        name_lbl = Gtk.Label(label=name)
        name_lbl.get_style_context().add_class("user-name")
        card.pack_start(avatar_lbl, False, False, 0)
        card.pack_start(name_lbl, False, False, 0)
        if email:
            em_lbl = Gtk.Label(label=email)
            em_lbl.get_style_context().add_class("user-email")
            card.pack_start(em_lbl, False, False, 0)

        hint = Gtk.Label(label="Enter your PIN to continue")
        hint.get_style_context().add_class("hint-lbl")
        card.pack_start(hint, False, False, 0)

        # PIN digits
        pin_row = Gtk.Box(spacing=12)
        pin_row.set_halign(Gtk.Align.CENTER)
        self.pin_entries = []
        for i in range(4):
            e = Gtk.Entry()
            e.set_max_length(1)
            e.set_input_purpose(Gtk.InputPurpose.DIGITS)
            e.set_visibility(False)
            e.set_invisible_char("●")
            e.get_style_context().add_class("pin-digit")
            e.set_width_chars(2)
            idx = i
            def changed(w, ni=idx+1):
                txt = w.get_text()
                if txt and not txt.isdigit():
                    w.set_text("")
                    return
                if txt and ni < 4:
                    self.pin_entries[ni].grab_focus()
                elif txt and ni == 4:
                    self.on_submit(None)
            e.connect("changed", changed)
            self.pin_entries.append(e)
            pin_row.pack_start(e, False, False, 0)
        card.pack_start(pin_row, False, False, 0)

        self.error_lbl = Gtk.Label(label="")
        self.error_lbl.get_style_context().add_class("error-lbl")
        card.pack_start(self.error_lbl, False, False, 0)

        btn = Gtk.Button(label="Unlock →")
        btn.get_style_context().add_class("btn-unlock")
        btn.connect("clicked", self.on_submit)
        card.pack_start(btn, False, False, 0)

        overlay.add(card)
        self.show_all()

        # Clock update
        self.update_clock()
        GLib.timeout_add(10000, self.update_clock)

        # Focus first PIN box
        GLib.idle_add(self.pin_entries[0].grab_focus)

    def update_clock(self):
        from datetime import datetime
        now = datetime.now()
        self.time_lbl.set_text(now.strftime("%H:%M"))
        self.date_lbl.set_text(now.strftime("%A, %B %d"))
        return True

    def on_submit(self, _):
        pin = "".join(e.get_text() for e in self.pin_entries)
        if len(pin) != 4:
            self.error_lbl.set_text("Please enter all 4 digits.")
            return
        if hash_pin(pin) == self.pin_hash:
            self.destroy()
            Gtk.main_quit()
        else:
            self.attempts += 1
            for e in self.pin_entries:
                e.set_text("")
            self.pin_entries[0].grab_focus()
            if self.attempts >= 5:
                self.error_lbl.set_text(
                    f"❌ Incorrect PIN ({self.attempts} attempts). Try again."
                )
            else:
                self.error_lbl.set_text(f"❌ Incorrect PIN. Try again.")

def main():
    win = PinLock()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
