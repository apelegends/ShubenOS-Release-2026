#!/usr/bin/env python3
"""Shuben Launcher OS — Custom Taskbar"""
import gi, os, json, subprocess
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GLib

A="#00A8E8"; D="#0D1117"; C="#161B22"; W="#FFFFFF"; G="#8B949E"
CSS=f"""
*{{font-family:'Segoe UI','Liberation Sans',sans-serif;font-size:13px;}}
#bar{{background:rgba(13,17,23,0.97);border-top:1px solid rgba(255,255,255,0.08);min-height:44px;}}
#start{{background:transparent;border:none;color:{A};font-size:20px;padding:0 14px;min-height:44px;}}
#start:hover{{background:rgba(0,168,232,0.15);}}
.tbtn{{background:transparent;border:none;color:{W};padding:4px 12px;min-height:44px;border-radius:0;}}
.tbtn:hover{{background:rgba(255,255,255,0.08);}}
.sysbtn{{background:transparent;border:none;color:{G};padding:0 8px;min-height:44px;font-size:12px;}}
.sysbtn:hover{{color:{W};background:rgba(255,255,255,0.06);}}
.clk{{color:{W};font-size:12px;padding:0 14px 0 4px;}}
#menu{{background:{C};border:1px solid rgba(255,255,255,0.1);border-radius:10px 10px 0 0;padding:16px;min-width:360px;}}
.mhead{{color:{G};font-size:11px;font-weight:700;padding:8px 0 4px;}}
.mitem{{background:transparent;border:none;color:{W};border-radius:6px;padding:10px 12px;font-size:13px;}}
.mitem:hover{{background:rgba(255,255,255,0.07);}}
.pinned{{background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;min-width:70px;border:none;color:{W};}}
.pinned:hover{{background:rgba(0,168,232,0.15);}}
.userpill{{background:rgba(255,255,255,0.05);border-radius:20px;padding:6px 14px;color:{W};font-size:12px;}}
"""
ACCT="/var/lib/shuben/accounts.json"
PINNED=[("🎮","Minecraft","shuben-minecraft-launcher"),("🌐","Edge","microsoft-edge-stable"),
        ("📁","Files","pcmanfm"),("⚙️","Settings","shuben-settings"),("🖥️","Terminal","lxterminal")]
ALL_APPS=[("🎮","Minecraft Launcher","shuben-minecraft-launcher"),("🌐","Microsoft Edge","microsoft-edge-stable"),
          ("📁","File Manager","pcmanfm"),("⚙️","Shuben Settings","shuben-settings"),
          ("🖥️","Terminal","lxterminal"),("🔊","Audio","pavucontrol"),("📝","Text Editor","mousepad"),
          ("🗜️","Archives","engrampa"),("💿","Install Shuben OS","shuben-installer")]

class Taskbar(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_decorated(False); self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True); self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        scr=Gdk.Screen.get_default(); w=scr.get_width(); h=scr.get_height()
        self.set_size_request(w,44); self.move(0,h-44)
        p=Gtk.CssProvider(); p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(scr,p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        vis=scr.get_rgba_visual()
        if vis: self.set_visual(vis)
        self.set_app_paintable(True)
        self.menu_win=None; self._build(); self.show_all()
        GLib.timeout_add(10000,self._clock); self._clock()

    def _launch(self,cmd):
        subprocess.Popen(cmd.split())
        if self.menu_win: self.menu_win.hide()

    def _build(self):
        bar=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bar.set_name("bar"); bar.set_hexpand(True); self.add(bar)
        st=Gtk.Button(label="⊞"); st.set_name("start"); st.connect("clicked",self._toggle_menu)
        bar.pack_start(st,False,False,0)
        for em,nm,cmd in PINNED:
            b=Gtk.Button(label=f"{em}  {nm}"); b.get_style_context().add_class("tbtn")
            b.connect("clicked",lambda _,c=cmd:self._launch(c)); bar.pack_start(b,False,False,0)
        bar.pack_start(Gtk.Box(),True,True,0)
        for lbl,cb in [("🔊",lambda _:self._launch("pavucontrol")),
                       ("📶",lambda _:self._launch("nm-connection-editor"))]:
            b=Gtk.Button(label=lbl); b.get_style_context().add_class("sysbtn"); b.connect("clicked",cb)
            bar.pack_end(b,False,False,0)
        self.clk=Gtk.Label(); self.clk.get_style_context().add_class("clk"); bar.pack_end(self.clk,False,False,0)

    def _clock(self):
        from datetime import datetime; n=datetime.now()
        self.clk.set_markup(f'<b>{n.strftime("%H:%M")}</b>\n<span size="x-small">{n.strftime("%d/%m/%Y")}</span>')
        return True

    def _toggle_menu(self,_):
        if self.menu_win and self.menu_win.get_visible(): self.menu_win.hide()
        else: self._show_menu()

    def _show_menu(self):
        if not self.menu_win: self.menu_win=self._build_menu()
        scr=Gdk.Screen.get_default(); h=scr.get_height()
        self.menu_win.move(0,h-44-500); self.menu_win.show_all(); self.menu_win.present()

    def _build_menu(self):
        win=Gtk.Window(); win.set_decorated(False); win.set_skip_taskbar_hint(True)
        win.set_keep_above(True); win.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        win.set_size_request(380,500)
        scr=Gdk.Screen.get_default(); vis=scr.get_rgba_visual()
        if vis: win.set_visual(vis)
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        outer.set_name("menu"); win.add(outer)
        # User
        try: acct=json.loads(open(ACCT).read()).get("primary",{})
        except: acct={}
        name=acct.get("display_name") or (acct.get("email","").split("@")[0]) or "User"
        ub=Gtk.Box(spacing=10)
        ub.pack_start(Gtk.Label(label="🎮"),False,False,0)
        ul=Gtk.Label(label=name); ul.get_style_context().add_class("userpill")
        ub.pack_start(ul,False,False,0); outer.pack_start(ub,False,False,0)
        outer.pack_start(Gtk.Separator(),False,False,8)
        # Pinned grid
        pl=Gtk.Label(label="PINNED"); pl.get_style_context().add_class("mhead"); pl.set_xalign(0)
        outer.pack_start(pl,False,False,0)
        grid=Gtk.FlowBox(); grid.set_max_children_per_line(4); grid.set_selection_mode(Gtk.SelectionMode.NONE)
        for em,nm,cmd in PINNED:
            b=Gtk.Button(); b.get_style_context().add_class("pinned")
            vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
            vb.pack_start(Gtk.Label(label=em),False,False,0)
            lbl=Gtk.Label(label=nm); lbl.set_line_wrap(True); lbl.set_justify(Gtk.Justification.CENTER)
            vb.pack_start(lbl,False,False,0); b.add(vb)
            b.connect("clicked",lambda _,c=cmd:self._launch(c)); grid.add(b)
        outer.pack_start(grid,False,False,0)
        outer.pack_start(Gtk.Separator(),False,False,8)
        # All apps
        al=Gtk.Label(label="ALL APPS"); al.get_style_context().add_class("mhead"); al.set_xalign(0)
        outer.pack_start(al,False,False,0)
        sw=Gtk.ScrolledWindow(); sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        ab=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        for em,nm,cmd in ALL_APPS:
            b=Gtk.Button(label=f"{em}  {nm}"); b.get_style_context().add_class("mitem")
            b.connect("clicked",lambda _,c=cmd:self._launch(c)); ab.pack_start(b,False,False,0)
        sw.add(ab); outer.pack_start(sw,True,True,0)
        outer.pack_start(Gtk.Separator(),False,False,4)
        # Power row
        pr=Gtk.Box(spacing=6)
        for em,nm,cmd in [("🔒","Lock","shuben-lock"),("⚙️","Settings","shuben-settings"),("⏻","Power","shuben-power-menu")]:
            b=Gtk.Button(label=f"{em}  {nm}"); b.get_style_context().add_class("mitem")
            b.connect("clicked",lambda _,c=cmd:self._launch(c)); pr.pack_start(b,True,True,0)
        outer.pack_start(pr,False,False,0)
        win.connect("focus-out-event",lambda w,e:w.hide())
        return win

def main():
    t=Taskbar(); t.connect("destroy",Gtk.main_quit); Gtk.main()
if __name__=="__main__": main()
