#!/usr/bin/env python3
"""
Shuben Launcher OS — Custom Taskbar & Desktop Shell
Windows 10-inspired but fully custom branded.
"""

import gi, os, json, subprocess, threading, time
gi.require_version("Gtk", "3.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

ACCENT  = "#00A8E8"
BG_BAR  = "rgba(13,17,23,0.96)"
BG_MENU = "#161B22"
TEXT_W  = "#FFFFFF"
TEXT_G  = "#8B949E"
HOV     = "rgba(0,168,232,0.15)"

ACCT_FILE = "/var/lib/shuben/accounts.json"

TASKBAR_CSS = f"""
* {{ font-family: 'Segoe UI', 'Liberation Sans', sans-serif; font-size: 13px; }}
#taskbar {{
  background: {BG_BAR};
  border-top: 1px solid rgba(255,255,255,0.08);
  min-height: 44px;
}}
#start-btn {{
  background: transparent;
  border: none;
  color: {ACCENT};
  font-size: 20px;
  padding: 0 14px;
  min-height: 44px;
}}
#start-btn:hover {{ background: {HOV}; }}
.taskbar-btn {{
  background: transparent;
  border: none;
  color: {TEXT_W};
  padding: 4px 12px;
  min-height: 44px;
  border-radius: 0;
}}
.taskbar-btn:hover {{ background: rgba(255,255,255,0.08); }}
.taskbar-btn.active {{ border-bottom: 2px solid {ACCENT}; }}
.sys-tray-btn {{
  background: transparent;
  border: none;
  color: {TEXT_G};
  padding: 0 8px;
  font-size: 12px;
  min-height: 44px;
}}
.sys-tray-btn:hover {{ color: {TEXT_W}; background: rgba(255,255,255,0.06); }}
.clock-lbl {{
  color: {TEXT_W};
  font-size: 12px;
  padding: 0 14px 0 4px;
}}
#start-menu {{
  background: {BG_MENU};
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px 10px 0 0;
  padding: 16px;
  min-width: 360px;
  min-height: 480px;
}}
.menu-title {{ color: {TEXT_G}; font-size: 11px; font-weight: 700; padding: 8px 0 4px; }}
.menu-item {{
  background: transparent;
  border: none;
  color: {TEXT_W};
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
}}
.menu-item:hover {{ background: rgba(255,255,255,0.07); }}
.menu-item label {{ xalign: 0; }}
.pinned-app {{
  background: rgba(255,255,255,0.05);
  border-radius: 10px;
  padding: 12px;
  min-width: 72px;
  min-height: 72px;
  border: none;
  color: {TEXT_W};
}}
.pinned-app:hover {{ background: rgba(0,168,232,0.15); }}
.user-pill {{
  background: rgba(255,255,255,0.05);
  border-radius: 20px;
  padding: 6px 14px;
  color: {TEXT_W};
  font-size: 12px;
}}
"""

PINNED_APPS = [
    ("🎮", "Minecraft",    "shuben-minecraft-launcher"),
    ("🌐", "Edge",         "microsoft-edge"),
    ("📁", "Files",        "pcmanfm"),
    ("⚙️", "Settings",    "shuben-settings"),
    ("🖥️", "Terminal",   "lxterminal"),
]

ALL_APPS = [
    ("🎮", "Minecraft Launcher", "shuben-minecraft-launcher"),
    ("🌐", "Microsoft Edge",     "microsoft-edge"),
    ("📁", "File Manager",       "pcmanfm"),
    ("⚙️", "Shuben Settings",   "shuben-settings"),
    ("🖥️", "Terminal",          "lxterminal"),
    ("🔊", "Audio Settings",     "pavucontrol"),
    ("📝", "Text Editor",        "mousepad"),
    ("🗜️", "Archive Manager",   "engrampa"),
    ("📊", "Task Manager",       "lxterminal -e htop"),
]

class Taskbar(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_name("taskbar-window")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)

        screen = Gdk.Screen.get_default()
        w = screen.get_width()
        h = screen.get_height()
        self.set_size_request(w, 44)
        self.move(0, h - 44)
        self.set_gravity(Gdk.Gravity.SOUTH_WEST)

        provider = Gtk.CssProvider()
        provider.load_from_data(TASKBAR_CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.start_menu_win = None
        self.build_ui()
        self.show_all()

        GLib.timeout_add(10000, self.update_clock)
        self.update_clock()

    def build_ui(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bar.set_name("taskbar")
        bar.set_hexpand(True)
        self.add(bar)

        # Start button
        start = Gtk.Button(label="⊞")
        start.set_name("start-btn")
        start.connect("clicked", self.toggle_start_menu)
        bar.pack_start(start, False, False, 0)

        # Pinned apps
        for emoji, name, cmd in PINNED_APPS:
            btn = Gtk.Button(label=f"{emoji}  {name}")
            btn.get_style_context().add_class("taskbar-btn")
            btn.connect("clicked", lambda _, c=cmd: self.launch(c))
            bar.pack_start(btn, False, False, 0)

        # Spacer
        bar.pack_start(Gtk.Box(), True, True, 0)

        # System tray area
        self.vol_btn = Gtk.Button(label="🔊")
        self.vol_btn.get_style_context().add_class("sys-tray-btn")
        self.vol_btn.connect("clicked", lambda _: self.launch("pavucontrol"))
        bar.pack_end(self.vol_btn, False, False, 0)

        self.net_btn = Gtk.Button(label="📶")
        self.net_btn.get_style_context().add_class("sys-tray-btn")
        self.net_btn.connect("clicked", self.on_network_click)
        bar.pack_end(self.net_btn, False, False, 0)

        # Clock
        self.clock_lbl = Gtk.Label(label="")
        self.clock_lbl.get_style_context().add_class("clock-lbl")
        bar.pack_end(self.clock_lbl, False, False, 0)

    def update_clock(self):
        from datetime import datetime
        now = datetime.now()
        self.clock_lbl.set_markup(
            f'<b>{now.strftime("%H:%M")}</b>\n'
            f'<span size="x-small">{now.strftime("%d/%m/%Y")}</span>'
        )
        return True

    def launch(self, cmd):
        subprocess.Popen(cmd.split())
        if self.start_menu_win:
            self.start_menu_win.hide()

    def on_network_click(self, _):
        subprocess.Popen(["nm-connection-editor"])

    def toggle_start_menu(self, _):
        if self.start_menu_win and self.start_menu_win.get_visible():
            self.start_menu_win.hide()
        else:
            self.show_start_menu()

    def show_start_menu(self):
        if self.start_menu_win is None:
            self.start_menu_win = self.build_start_menu()

        screen = Gdk.Screen.get_default()
        h = screen.get_height()
        menu_h = 500
        self.start_menu_win.move(0, h - 44 - menu_h)
        self.start_menu_win.show_all()
        self.start_menu_win.present()

    def build_start_menu(self):
        win = Gtk.Window()
        win.set_name("start-menu")
        win.set_decorated(False)
        win.set_skip_taskbar_hint(True)
        win.set_keep_above(True)
        win.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        win.set_size_request(380, 500)

        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual:
            win.set_visual(visual)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_name("start-menu")
        win.add(outer)

        # User pill
        acct = {}
        try:
            with open(ACCT_FILE) as f:
                acct = json.load(f).get("primary", {})
        except Exception:
            pass
        name = acct.get("display_name") or acct.get("email", "").split("@")[0] or "User"
        user_box = Gtk.Box(spacing=10)
        user_box.pack_start(Gtk.Label(label="🎮"), False, False, 0)
        user_lbl = Gtk.Label(label=name)
        user_lbl.get_style_context().add_class("user-pill")
        user_box.pack_start(user_lbl, False, False, 0)
        outer.pack_start(user_box, False, False, 0)

        sep = Gtk.Separator()
        outer.pack_start(sep, False, False, 8)

        # Pinned apps grid
        pin_lbl = Gtk.Label(label="PINNED")
        pin_lbl.get_style_context().add_class("menu-title")
        pin_lbl.set_xalign(0)
        outer.pack_start(pin_lbl, False, False, 0)

        pin_grid = Gtk.FlowBox()
        pin_grid.set_max_children_per_line(4)
        pin_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        for emoji, name, cmd in PINNED_APPS:
            btn = Gtk.Button()
            btn.get_style_context().add_class("pinned-app")
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            vbox.pack_start(Gtk.Label(label=emoji), False, False, 0)
            lbl = Gtk.Label(label=name)
            lbl.set_line_wrap(True)
            lbl.set_justify(Gtk.Justification.CENTER)
            vbox.pack_start(lbl, False, False, 0)
            btn.add(vbox)
            btn.connect("clicked", lambda _, c=cmd: self.launch(c))
            pin_grid.add(btn)
        outer.pack_start(pin_grid, False, False, 0)

        sep2 = Gtk.Separator()
        outer.pack_start(sep2, False, False, 8)

        # All apps list
        all_lbl = Gtk.Label(label="ALL APPS")
        all_lbl.get_style_context().add_class("menu-title")
        all_lbl.set_xalign(0)
        outer.pack_start(all_lbl, False, False, 0)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        apps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        for emoji, app_name, cmd in ALL_APPS:
            btn = Gtk.Button(label=f"{emoji}  {app_name}")
            btn.get_style_context().add_class("menu-item")
            btn.connect("clicked", lambda _, c=cmd: self.launch(c))
            apps_box.pack_start(btn, False, False, 0)
        sw.add(apps_box)
        outer.pack_start(sw, True, True, 0)

        sep3 = Gtk.Separator()
        outer.pack_start(sep3, False, False, 4)

        # Power row
        power_row = Gtk.Box(spacing=6)
        for icon, label_text, cmd in [
            ("🔒", "Lock",    "shuben-lock"),
            ("⚙️", "Settings","shuben-settings"),
            ("⏻",  "Power",   "shuben-power-menu"),
        ]:
            b = Gtk.Button(label=f"{icon}  {label_text}")
            b.get_style_context().add_class("menu-item")
            b.connect("clicked", lambda _, c=cmd: self.launch(c))
            power_row.pack_start(b, True, True, 0)
        outer.pack_start(power_row, False, False, 0)

        # Close on focus-out
        win.connect("focus-out-event", lambda w, e: w.hide())
        return win

def main():
    t = Taskbar()
    t.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
