#!/usr/bin/env python3
"""
Shuben Launcher OS — Minecraft Launcher
Custom UI wrapper around minecraft-launcher / MultiMC / Prism Launcher logic.
"""

import gi, os, json, subprocess, threading, urllib.request, sys
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

ACCENT  = "#00A8E8"
BG_DARK = "#0D1117"
BG_CARD = "#161B22"
BG_SIDE = "#0D1117"
TEXT_W  = "#FFFFFF"
TEXT_G  = "#8B949E"
GREEN   = "#3FB950"
RED     = "#F85149"
ORANGE  = "#D29922"

CSS = f"""
* {{ font-family: 'Segoe UI', 'Liberation Sans', sans-serif; }}
window {{ background-color: {BG_DARK}; }}
#sidebar {{
  background: {BG_SIDE};
  border-right: 1px solid #21262D;
  min-width: 220px;
}}
#main-area {{ background: {BG_DARK}; }}
.sidebar-btn {{
  background: transparent;
  border: none;
  color: {TEXT_G};
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 13px;
}}
.sidebar-btn:hover {{ background: rgba(255,255,255,0.06); color: {TEXT_W}; }}
.sidebar-btn.active {{ background: rgba(0,168,232,0.15); color: {ACCENT}; border-left: 3px solid {ACCENT}; }}
.card {{
  background: {BG_CARD};
  border-radius: 10px;
  padding: 20px;
  border: 1px solid #21262D;
}}
.title {{ color: {TEXT_W}; font-size: 22px; font-weight: 700; }}
.subtitle {{ color: {TEXT_G}; font-size: 13px; }}
.section-title {{ color: {TEXT_W}; font-size: 15px; font-weight: 600; }}
.version-row {{
  background: rgba(255,255,255,0.03);
  border-radius: 6px;
  padding: 10px 14px;
  border: 1px solid #21262D;
}}
.version-row:hover {{ border-color: {ACCENT}; background: rgba(0,168,232,0.05); }}
.version-row.selected {{ border-color: {ACCENT}; background: rgba(0,168,232,0.1); }}
.btn-play {{
  background: {GREEN};
  color: {TEXT_W};
  border: none;
  border-radius: 8px;
  padding: 14px 40px;
  font-size: 16px;
  font-weight: 700;
}}
.btn-play:hover {{ background: #2EA043; }}
.btn-primary {{
  background: {ACCENT};
  color: {TEXT_W};
  border: none;
  border-radius: 6px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
}}
.btn-secondary {{
  background: transparent;
  color: {TEXT_G};
  border: 1px solid #30363D;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
}}
.btn-secondary:hover {{ border-color: {ACCENT}; color: {TEXT_W}; }}
.username-entry {{
  background: #21262D;
  color: {TEXT_W};
  border: 1px solid #30363D;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
}}
.username-entry:focus {{ border-color: {ACCENT}; }}
.status-ok   {{ color: {GREEN};  font-size: 12px; }}
.status-warn {{ color: {ORANGE}; font-size: 12px; }}
.status-err  {{ color: {RED};    font-size: 12px; }}
.logo-text {{
  color: {ACCENT};
  font-size: 28px;
  font-weight: 900;
  letter-spacing: 1px;
}}
.news-card {{
  background: {BG_CARD};
  border-radius: 8px;
  padding: 14px;
  border: 1px solid #21262D;
  margin: 4px 0;
}}
.ram-lbl {{ color: {TEXT_G}; font-size: 12px; }}
"""

VERSIONS = [
    ("1.21.4", "Release", "latest"),
    ("1.21.3", "Release", ""),
    ("1.20.6", "Release", ""),
    ("1.20.4", "Release", ""),
    ("1.19.4", "Release", ""),
    ("1.18.2", "Release", ""),
    ("1.17.1", "Release", ""),
    ("1.16.5", "Release", ""),
    ("1.12.2", "Release", "popular"),
    ("1.8.9",  "Release", "popular"),
    ("24w14a", "Snapshot", ""),
]

INSTALL_DIR = os.path.expanduser("~/.shuben-minecraft")
PROFILE_FILE = os.path.join(INSTALL_DIR, "profiles.json")

def load_profiles():
    try:
        with open(PROFILE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"username": "Player", "selected_version": "1.21.4", "ram": 2}

def save_profiles(data):
    os.makedirs(INSTALL_DIR, exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(data, f, indent=2)

class MinecraftLauncher(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Launcher — Minecraft")
        self.set_default_size(900, 600)
        self.set_decorated(False)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.profiles = load_profiles()
        self.selected_version = self.profiles.get("selected_version", "1.21.4")
        self.current_page = "home"

        self.build_ui()
        self.show_all()

    def build_ui(self):
        # Custom title bar
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        # Title bar
        tbar = Gtk.Box(spacing=0)
        tbar.set_size_request(-1, 36)
        tbar.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.05, 0.07, 0.09, 1))
        logo = Gtk.Label()
        logo.set_markup(f'<span foreground="{ACCENT}" font="13" font_weight="bold">  SHUBEN LAUNCHER  </span>'
                        f'<span foreground="#8B949E" font="11">— Minecraft</span>')
        tbar.pack_start(logo, False, False, 0)
        tbar.pack_start(Gtk.Box(), True, True, 0)
        for sym, cb in [("─", self.iconify), ("□", self.toggle_max), ("✕", self.destroy)]:
            b = Gtk.Button(label=sym)
            b.get_style_context().add_class("btn-secondary")
            b.set_size_request(42, 36)
            b.connect("clicked", lambda _, fn=cb: fn())
            tbar.pack_end(b, False, False, 0)
        # drag
        tbar.connect("button-press-event", self.on_drag)
        vbox.pack_start(tbar, False, False, 0)

        # Main layout
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(hbox, True, True, 0)

        # Sidebar
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.sidebar.set_name("sidebar")
        self.sidebar.set_margin_top(16)
        self.sidebar.set_margin_bottom(16)
        self.sidebar.set_margin_start(8)
        self.sidebar.set_margin_end(8)

        self.sidebar_buttons = {}
        pages = [
            ("🏠", "Home",     "home"),
            ("📦", "Versions", "versions"),
            ("👤", "Profile",  "profile"),
            ("⚙️", "Settings", "settings"),
            ("📰", "News",     "news"),
        ]
        for icon, label, name in pages:
            btn = Gtk.Button(label=f"{icon}  {label}")
            btn.get_style_context().add_class("sidebar-btn")
            btn.connect("clicked", lambda _, n=name: self.switch_page(n))
            self.sidebar.pack_start(btn, False, False, 0)
            self.sidebar_buttons[name] = btn

        hbox.pack_start(self.sidebar, False, False, 0)

        # Page stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        hbox.pack_start(self.stack, True, True, 0)

        self.build_home()
        self.build_versions()
        self.build_profile()
        self.build_settings()
        self.build_news()

        self.switch_page("home")

    def on_drag(self, widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)

    def toggle_max(self):
        if self.is_maximized():
            self.unmaximize()
        else:
            self.maximize()

    def switch_page(self, name):
        self.current_page = name
        self.stack.set_visible_child_name(name)
        for n, btn in self.sidebar_buttons.items():
            ctx = btn.get_style_context()
            if n == name:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

    def scroll_wrap(self, child):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(child)
        return sw

    def lbl(self, text, css="subtitle", xalign=0):
        l = Gtk.Label(label=text)
        l.get_style_context().add_class(css)
        l.set_xalign(xalign)
        l.set_line_wrap(True)
        return l

    def btn(self, text, css="btn-primary", cb=None):
        b = Gtk.Button(label=text)
        b.get_style_context().add_class(css)
        if cb:
            b.connect("clicked", cb)
        return b

    # ── HOME PAGE ─────────────────────────────────────────────────────────────
    def build_home(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_margin_top(32)
        page.set_margin_bottom(32)
        page.set_margin_start(32)
        page.set_margin_end(32)

        # Hero
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hero.get_style_context().add_class("card")

        logo = Gtk.Label()
        logo.set_markup(
            f'<span foreground="{ACCENT}" font="32" font_weight="900">⛏  MINECRAFT</span>'
        )
        logo.set_xalign(0)
        hero.pack_start(logo, False, False, 0)

        self.home_ver_lbl = self.lbl(f"Version: {self.selected_version}", "subtitle")
        hero.pack_start(self.home_ver_lbl, False, False, 0)

        # Username row
        urow = Gtk.Box(spacing=12)
        urow.pack_start(self.lbl("Username:", "subtitle"), False, False, 0)
        self.username_entry = Gtk.Entry()
        self.username_entry.set_text(self.profiles.get("username", "Player"))
        self.username_entry.get_style_context().add_class("username-entry")
        self.username_entry.set_size_request(180, -1)
        urow.pack_start(self.username_entry, False, False, 0)
        hero.pack_start(urow, False, False, 0)

        # Status
        self.play_status = self.lbl("", "status-ok")
        hero.pack_start(self.play_status, False, False, 0)

        # Play button
        play_btn = Gtk.Button(label="▶  PLAY")
        play_btn.get_style_context().add_class("btn-play")
        play_btn.set_halign(Gtk.Align.START)
        play_btn.connect("clicked", self.on_play)
        hero.pack_start(play_btn, False, False, 8)

        page.pack_start(hero, False, False, 0)

        # Quick actions
        qa_box = Gtk.Box(spacing=12)
        for label, cmd in [
            ("📂 Open .minecraft", f"xdg-open {os.path.expanduser('~/.minecraft')}"),
            ("🌐 Minecraft.net",   "microsoft-edge https://minecraft.net"),
        ]:
            b = self.btn(label, "btn-secondary", lambda _, c=cmd: subprocess.Popen(c.split()))
            qa_box.pack_start(b, False, False, 0)
        page.pack_start(qa_box, False, False, 0)

        self.stack.add_named(self.scroll_wrap(page), "home")

    def on_play(self, _):
        username = self.username_entry.get_text().strip() or "Player"
        self.profiles["username"] = username
        self.profiles["selected_version"] = self.selected_version
        save_profiles(self.profiles)

        self.play_status.set_text("Launching Minecraft…")
        self.play_status.get_style_context().remove_class("status-err")
        self.play_status.get_style_context().add_class("status-ok")

        def launch():
            mc_dir = os.path.expanduser("~/.minecraft")
            os.makedirs(mc_dir, exist_ok=True)
            # Try system minecraft launcher, then fall back to multimc/prismlauncher
            launchers = [
                ["minecraft-launcher"],
                ["prismlauncher"],
                ["multimc"],
                # Offline fallback using portable launcher
                ["java", "-jar", f"{INSTALL_DIR}/launcher.jar",
                 "--username", username, "--version", self.selected_version,
                 "--gameDir", mc_dir],
            ]
            launched = False
            for cmd in launchers:
                try:
                    result = subprocess.run(["which", cmd[0]], capture_output=True)
                    if result.returncode == 0:
                        subprocess.Popen(cmd)
                        launched = True
                        break
                except Exception:
                    continue
            if not launched:
                GLib.idle_add(
                    lambda: self.play_status.set_text(
                        "⚠ No Minecraft launcher found. Install via Settings."
                    )
                )
                GLib.idle_add(
                    lambda: self.play_status.get_style_context().add_class("status-warn")
                )
        threading.Thread(target=launch, daemon=True).start()

    # ── VERSIONS PAGE ─────────────────────────────────────────────────────────
    def build_versions(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        page.set_margin_start(24)
        page.set_margin_end(24)

        hdr = self.lbl("Select Version", "title")
        page.pack_start(hdr, False, False, 0)
        sub = self.lbl("Choose which version of Minecraft to launch.", "subtitle")
        page.pack_start(sub, False, False, 0)

        self.ver_rows = {}
        versions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for ver, vtype, tag in VERSIONS:
            row = Gtk.Box(spacing=12)
            row.get_style_context().add_class("version-row")
            if ver == self.selected_version:
                row.get_style_context().add_class("selected")

            icon = "📦" if vtype == "Release" else "🔬"
            lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_lbl = Gtk.Label(label=f"{icon}  Minecraft {ver}")
            name_lbl.get_style_context().add_class("section-title")
            name_lbl.set_xalign(0)
            type_lbl = Gtk.Label(label=vtype)
            type_lbl.get_style_context().add_class("subtitle")
            type_lbl.set_xalign(0)
            lbl_box.pack_start(name_lbl, False, False, 0)
            lbl_box.pack_start(type_lbl, False, False, 0)
            row.pack_start(lbl_box, True, True, 0)

            if tag:
                tag_lbl = Gtk.Label(label=f"⭐ {tag}")
                tag_lbl.get_style_context().add_class("status-ok" if tag == "latest" else "status-warn")
                row.pack_end(tag_lbl, False, False, 0)

            sel_btn = self.btn("Select", "btn-secondary")
            v = ver
            sel_btn.connect("clicked", lambda _, v=v: self.select_version(v))
            row.pack_end(sel_btn, False, False, 0)

            self.ver_rows[ver] = row
            versions_box.pack_start(row, False, False, 0)

        page.pack_start(self.scroll_wrap(versions_box), True, True, 0)
        self.stack.add_named(page, "versions")

    def select_version(self, ver):
        for v, row in self.ver_rows.items():
            ctx = row.get_style_context()
            if v == ver:
                ctx.add_class("selected")
            else:
                ctx.remove_class("selected")
        self.selected_version = ver
        self.home_ver_lbl.set_text(f"Version: {ver}")

    # ── PROFILE PAGE ──────────────────────────────────────────────────────────
    def build_profile(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(24)
        page.set_margin_start(24)
        page.set_margin_end(24)

        page.pack_start(self.lbl("Your Profile", "title"), False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.get_style_context().add_class("card")

        card.pack_start(self.lbl("Username", "section-title"), False, False, 0)
        self.profile_username = Gtk.Entry()
        self.profile_username.set_text(self.profiles.get("username", "Player"))
        self.profile_username.get_style_context().add_class("username-entry")
        card.pack_start(self.profile_username, False, False, 0)

        card.pack_start(self.lbl("Skin (URL or local file path)", "section-title"), False, False, 0)
        self.skin_entry = Gtk.Entry()
        self.skin_entry.set_placeholder_text("https://... or /path/to/skin.png")
        self.skin_entry.get_style_context().add_class("username-entry")
        card.pack_start(self.skin_entry, False, False, 0)

        save_btn = self.btn("Save profile", cb=self.on_save_profile)
        card.pack_start(save_btn, False, False, 0)

        self.profile_status = self.lbl("", "status-ok")
        card.pack_start(self.profile_status, False, False, 0)

        page.pack_start(card, False, False, 0)
        self.stack.add_named(self.scroll_wrap(page), "profile")

    def on_save_profile(self, _):
        name = self.profile_username.get_text().strip() or "Player"
        self.profiles["username"] = name
        self.username_entry.set_text(name)
        save_profiles(self.profiles)
        self.profile_status.set_text("✅ Profile saved.")

    # ── SETTINGS PAGE ─────────────────────────────────────────────────────────
    def build_settings(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(24)
        page.set_margin_start(24)
        page.set_margin_end(24)

        page.pack_start(self.lbl("Launcher Settings", "title"), False, False, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        card.get_style_context().add_class("card")

        # RAM
        card.pack_start(self.lbl("RAM allocation (GB)", "section-title"), False, False, 0)
        ram_box = Gtk.Box(spacing=12)
        self.ram_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 16, 1)
        self.ram_scale.set_value(self.profiles.get("ram", 2))
        self.ram_scale.set_hexpand(True)
        self.ram_scale.set_draw_value(True)
        ram_box.pack_start(self.ram_scale, True, True, 0)
        card.pack_start(ram_box, False, False, 0)

        # Java path
        card.pack_start(self.lbl("Java executable (leave blank for auto)", "section-title"), False, False, 0)
        self.java_entry = Gtk.Entry()
        self.java_entry.set_placeholder_text("/usr/bin/java")
        self.java_entry.get_style_context().add_class("username-entry")
        self.java_entry.set_text(self.profiles.get("java_path", ""))
        card.pack_start(self.java_entry, False, False, 0)

        # Install launcher
        card.pack_start(self.lbl("Install Minecraft Launcher", "section-title"), False, False, 0)
        inst_box = Gtk.Box(spacing=10)
        for lbl_text, cmd in [
            ("Prism Launcher",  "apt-get install -y prismlauncher"),
            ("MultiMC",         "apt-get install -y multimc"),
        ]:
            b = self.btn(lbl_text, "btn-secondary",
                         lambda _, c=cmd: self.run_install(c))
            inst_box.pack_start(b, False, False, 0)
        card.pack_start(inst_box, False, False, 0)

        self.settings_status = self.lbl("", "status-ok")
        card.pack_start(self.settings_status, False, False, 0)

        save_btn = self.btn("Save settings", cb=self.on_save_settings)
        card.pack_start(save_btn, False, False, 0)

        page.pack_start(card, False, False, 0)
        self.stack.add_named(self.scroll_wrap(page), "settings")

    def run_install(self, cmd):
        self.settings_status.set_text("Installing… (requires sudo)")
        def do():
            r = subprocess.run(["pkexec"] + cmd.split(), capture_output=True, text=True)
            msg = "✅ Done." if r.returncode == 0 else f"❌ Error: {r.stderr[:60]}"
            GLib.idle_add(self.settings_status.set_text, msg)
        threading.Thread(target=do, daemon=True).start()

    def on_save_settings(self, _):
        self.profiles["ram"] = int(self.ram_scale.get_value())
        self.profiles["java_path"] = self.java_entry.get_text().strip()
        save_profiles(self.profiles)
        self.settings_status.set_text("✅ Settings saved.")

    # ── NEWS PAGE ─────────────────────────────────────────────────────────────
    def build_news(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(24)
        page.set_margin_start(24)
        page.set_margin_end(24)

        page.pack_start(self.lbl("Minecraft News", "title"), False, False, 0)

        self.news_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        loading = self.lbl("Loading news…", "subtitle")
        self.news_box.pack_start(loading, False, False, 0)

        page.pack_start(self.scroll_wrap(self.news_box), True, True, 0)
        self.stack.add_named(page, "news")
        threading.Thread(target=self.fetch_news, daemon=True).start()

    def fetch_news(self):
        try:
            url = "https://launchercontent.mojang.com/news.json"
            with urllib.request.urlopen(url, timeout=6) as r:
                data = json.loads(r.read())
            entries = data.get("entries", [])[:8]
            GLib.idle_add(self.populate_news, entries)
        except Exception as e:
            GLib.idle_add(self.populate_news, [])

    def populate_news(self, entries):
        for child in self.news_box.get_children():
            self.news_box.remove(child)

        if not entries:
            self.news_box.pack_start(
                self.lbl("Could not load news. Check your internet connection.", "subtitle"),
                False, False, 0
            )
            self.news_box.show_all()
            return

        for entry in entries:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card.get_style_context().add_class("news-card")
            title = self.lbl(entry.get("title", "Minecraft Update"), "section-title")
            body  = self.lbl(entry.get("text", "")[:180] + "…", "subtitle")
            card.pack_start(title, False, False, 0)
            card.pack_start(body, False, False, 0)
            url = entry.get("readMoreLink", "")
            if url:
                b = self.btn("Read more", "btn-secondary",
                             lambda _, u=url: subprocess.Popen(["microsoft-edge", u]))
                card.pack_start(b, False, False, 0)
            self.news_box.pack_start(card, False, False, 0)

        self.news_box.show_all()

def main():
    win = MinecraftLauncher()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
