#!/usr/bin/env python3
"""Shuben Launcher OS — Minecraft Launcher"""
import gi, os, json, subprocess, threading, urllib.request
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GLib

A="#00A8E8"; D="#0D1117"; C="#161B22"; W="#FFFFFF"; G="#8B949E"; GR="#3FB950"; R="#F85149"
CSS=f"""
*{{font-family:'Segoe UI','Liberation Sans',sans-serif;}}
window{{background:{D};}}
#sidebar{{background:{D};border-right:1px solid #21262D;min-width:200px;}}
.sbtn{{background:transparent;border:none;color:{G};border-radius:8px;padding:10px 16px;font-size:13px;}}
.sbtn:hover{{background:rgba(255,255,255,0.06);color:{W};}}
.sbtn.active{{background:rgba(0,168,232,0.15);color:{A};border-left:3px solid {A};}}
.card{{background:{C};border-radius:10px;padding:20px;border:1px solid #21262D;}}
.title{{color:{W};font-size:20px;font-weight:700;}}
.head{{color:{W};font-size:14px;font-weight:600;}}
.sub{{color:{G};font-size:13px;}}
.play{{background:{GR};color:{W};border:none;border-radius:8px;padding:14px 40px;font-size:16px;font-weight:700;}}
.play:hover{{background:#2EA043;}}
.btn-p{{background:{A};color:{W};border:none;border-radius:6px;padding:9px 18px;font-size:13px;font-weight:600;}}
.btn-s{{background:transparent;color:{G};border:1px solid #30363D;border-radius:6px;padding:7px 14px;font-size:13px;}}
.btn-s:hover{{border-color:{A};color:{W};}}
.field{{background:#21262D;color:{W};border:1px solid #30363D;border-radius:6px;padding:8px 12px;font-size:13px;}}
.field:focus{{border-color:{A};}}
.vrow{{background:rgba(255,255,255,0.03);border-radius:6px;padding:10px 14px;border:1px solid #21262D;margin:2px 0;}}
.vrow:hover{{border-color:{A};}}
.ok{{color:{GR};font-size:12px;}} .warn{{color:#D29922;font-size:12px;}} .err{{color:{R};font-size:12px;}}
.logo{{color:{A};font-size:26px;font-weight:900;}}
.news{{background:{C};border-radius:8px;padding:14px;border:1px solid #21262D;margin:4px 0;}}
"""
VERSIONS=[("1.21.4","Release","latest"),("1.21.3","Release",""),("1.20.6","Release",""),
           ("1.20.4","Release",""),("1.19.4","Release",""),("1.18.2","Release",""),
           ("1.16.5","Release",""),("1.12.2","Release","popular"),("1.8.9","Release","popular"),
           ("24w14a","Snapshot","")]
INST_DIR=os.path.expanduser("~/.shuben-minecraft")
PROF=os.path.join(INST_DIR,"profiles.json")

def load_prof():
    try: return json.loads(open(PROF).read())
    except: return {"username":"Player","version":"1.21.4","ram":2}
def save_prof(d): os.makedirs(INST_DIR,exist_ok=True); open(PROF,"w").write(json.dumps(d,indent=2))

PAGES=[("🏠","Home","home"),("📦","Versions","versions"),("👤","Profile","profile"),("⚙️","Settings","settings"),("📰","News","news")]

class MCLauncher(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Launcher — Minecraft")
        self.set_default_size(900,580); self.set_decorated(False)
        p=Gtk.CssProvider(); p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.prof=load_prof(); self.sel_ver=self.prof.get("version","1.21.4"); self.ver_rows={}
        self._build(); self.show_all()

    def _build(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL); self.add(vb)
        # Titlebar
        tb=Gtk.Box(); tb.set_size_request(-1,36)
        tb.override_background_color(Gtk.StateFlags.NORMAL,Gdk.RGBA(0.05,0.07,0.09,1))
        tl=Gtk.Label(); tl.set_markup(f'<span foreground="{A}" font="12" font_weight="bold">  SHUBEN LAUNCHER  </span><span foreground="{G}" font="11">— Minecraft</span>')
        tb.pack_start(tl,False,False,0); tb.pack_start(Gtk.Box(),True,True,0)
        for sym,fn in [("─",self.iconify),("□",lambda:self.unmaximize() if self.is_maximized() else self.maximize()),("✕",self.destroy)]:
            b=Gtk.Button(label=sym); b.get_style_context().add_class("btn-s"); b.set_size_request(40,36)
            b.connect("clicked",lambda _,f=fn:f()); tb.pack_end(b,False,False,0)
        tb.connect("button-press-event",lambda w,e:self.begin_move_drag(e.button,int(e.x_root),int(e.y_root),e.time))
        vb.pack_start(tb,False,False,0)
        hb=Gtk.Box(); vb.pack_start(hb,True,True,0)
        # Sidebar
        sb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        sb.set_name("sidebar"); sb.set_margin_top(14); sb.set_margin_start(8); sb.set_margin_end(8)
        self.sbtns={}
        for em,nm,pg in PAGES:
            b=Gtk.Button(label=f"{em}  {nm}"); b.get_style_context().add_class("sbtn")
            b.connect("clicked",lambda _,p=pg:self._switch(p)); sb.pack_start(b,False,False,0); self.sbtns[pg]=b
        hb.pack_start(sb,False,False,0)
        self.stack=Gtk.Stack(); self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE); self.stack.set_transition_duration(140)
        hb.pack_start(self.stack,True,True,0)
        self._home(); self._versions(); self._profile(); self._settings(); self._news()
        self._switch("home")

    def _switch(self,pg):
        self.stack.set_visible_child_name(pg)
        for n,b in self.sbtns.items():
            ctx=b.get_style_context()
            if n==pg: ctx.add_class("active")
            else: ctx.remove_class("active")

    def lbl(self,t,css="sub",xa=0,wrap=True):
        l=Gtk.Label(label=t); l.get_style_context().add_class(css); l.set_xalign(xa); l.set_line_wrap(wrap); return l
    def btn(self,t,css="btn-p",cb=None):
        b=Gtk.Button(label=t); b.get_style_context().add_class(css)
        if cb: b.connect("clicked",cb); return b
    def field(self,ph="",pw=False):
        e=Gtk.Entry(); e.set_placeholder_text(ph); e.get_style_context().add_class("field")
        if pw: e.set_visibility(False); e.set_invisible_char("●"); e.set_hexpand(True); return e
    def sw(self,ch,mh=100):
        s=Gtk.ScrolledWindow(); s.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        s.set_min_content_height(mh); s.add(ch); return s
    def page(self,name,child):
        p=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16)
        p.set_margin_top(24); p.set_margin_start(24); p.set_margin_end(24); p.set_margin_bottom(24)
        p.pack_start(child,False,False,0); self.stack.add_named(self.sw(p,400),name)

    def _home(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16)
        hero=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10); hero.get_style_context().add_class("card")
        hero.pack_start(self.lbl("⛏  MINECRAFT","logo"),False,False,0)
        self.ver_lbl=self.lbl(f"Version: {self.sel_ver}","sub"); hero.pack_start(self.ver_lbl,False,False,0)
        ur=Gtk.Box(spacing=10); ur.pack_start(self.lbl("Username:","sub"),False,False,0)
        self.uname=self.field("Player"); self.uname.set_text(self.prof.get("username","Player"))
        self.uname.set_size_request(180,-1); ur.pack_start(self.uname,False,False,0)
        hero.pack_start(ur,False,False,0)
        self.play_st=self.lbl("","sub"); hero.pack_start(self.play_st,False,False,0)
        pb=self.btn("▶  PLAY","play",cb=self._play); pb.set_halign(Gtk.Align.START)
        hero.pack_start(pb,False,False,8); vb.pack_start(hero,False,False,0)
        qa=Gtk.Box(spacing=12)
        qa.pack_start(self.btn("📂 Open .minecraft","btn-s",cb=lambda _:subprocess.Popen(["xdg-open",os.path.expanduser("~/.minecraft")])),False,False,0)
        qa.pack_start(self.btn("🌐 Minecraft.net","btn-s",cb=lambda _:subprocess.Popen(["microsoft-edge-stable","https://minecraft.net"])),False,False,0)
        vb.pack_start(qa,False,False,0); self.page("home",vb)

    def _play(self,_):
        u=self.uname.get_text().strip() or "Player"
        self.prof["username"]=u; self.prof["version"]=self.sel_ver; save_prof(self.prof)
        self.play_st.set_text("Launching…")
        def do():
            mc=os.path.expanduser("~/.minecraft"); os.makedirs(mc,exist_ok=True)
            for cmd in [["minecraft-launcher"],["prismlauncher"],["multimc"]]:
                if subprocess.run(["which",cmd[0]],capture_output=True).returncode==0:
                    subprocess.Popen(cmd); GLib.idle_add(self.play_st.set_text,"✅ Launched!"); return
            GLib.idle_add(self.play_st.set_text,"⚠ No launcher found. Install via Settings.")
        threading.Thread(target=do,daemon=True).start()

    def _versions(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        vb.pack_start(self.lbl("Select Version","title"),False,False,0)
        vb.pack_start(self.lbl("Choose which Minecraft version to launch.","sub"),False,False,0)
        lb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        for ver,vtype,tag in VERSIONS:
            row=Gtk.Box(spacing=12); row.get_style_context().add_class("vrow")
            ib=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
            ib.pack_start(self.lbl(f"{'📦' if vtype=='Release' else '🔬'}  Minecraft {ver}","head"),False,False,0)
            ib.pack_start(self.lbl(vtype,"sub"),False,False,0)
            row.pack_start(ib,True,True,0)
            if tag: row.pack_end(self.lbl(f"⭐ {tag}","ok" if tag=="latest" else "warn"),False,False,0)
            sb=self.btn("Select","btn-s",cb=lambda _,v=ver:self._sel_ver(v))
            row.pack_end(sb,False,False,0); self.ver_rows[ver]=row; lb.pack_start(row,False,False,0)
        vb.pack_start(self.sw(lb,380),True,True,0); self.page("versions",vb)

    def _sel_ver(self,v):
        for vv,row in self.ver_rows.items():
            if vv==v: row.override_background_color(Gtk.StateFlags.NORMAL,Gdk.RGBA(0,0.17,0.3,1))
            else: row.override_background_color(Gtk.StateFlags.NORMAL,Gdk.RGBA(1,1,1,0.03))
        self.sel_ver=v; self.ver_lbl.set_text(f"Version: {v}")

    def _profile(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        vb.pack_start(self.lbl("Your Profile","title"),False,False,0)
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10); c.get_style_context().add_class("card")
        c.pack_start(self.lbl("Username","head"),False,False,0)
        self.prof_uname=self.field("Player"); self.prof_uname.set_text(self.prof.get("username","Player"))
        c.pack_start(self.prof_uname,False,False,0)
        c.pack_start(self.lbl("Skin URL or file path","head"),False,False,0)
        self.skin_f=self.field("https://... or /path/to/skin.png"); c.pack_start(self.skin_f,False,False,0)
        self.prof_st=self.lbl("","ok")
        def save(_):
            self.prof["username"]=self.prof_uname.get_text().strip() or "Player"
            self.uname.set_text(self.prof["username"]); save_prof(self.prof); self.prof_st.set_text("✅ Saved.")
        c.pack_start(self.btn("Save profile",cb=save),False,False,0); c.pack_start(self.prof_st,False,False,0)
        vb.pack_start(c,False,False,0); self.page("profile",vb)

    def _settings(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        vb.pack_start(self.lbl("Launcher Settings","title"),False,False,0)
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12); c.get_style_context().add_class("card")
        c.pack_start(self.lbl("RAM allocation (GB)","head"),False,False,0)
        self.ram=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,1,16,1)
        self.ram.set_value(self.prof.get("ram",2)); self.ram.set_hexpand(True); self.ram.set_draw_value(True)
        c.pack_start(self.ram,False,False,0)
        c.pack_start(self.lbl("Install a Minecraft launcher","head"),False,False,0)
        ib=Gtk.Box(spacing=10)
        self.inst_st=self.lbl("","ok")
        for nm,pkg in [("Prism Launcher","prismlauncher"),("MultiMC","multimc")]:
            ib.pack_start(self.btn(nm,"btn-s",cb=lambda _,p=pkg:self._install_launcher(p)),False,False,0)
        c.pack_start(ib,False,False,0); c.pack_start(self.inst_st,False,False,0)
        self.sett_st=self.lbl("","ok")
        def save(_):
            self.prof["ram"]=int(self.ram.get_value()); save_prof(self.prof); self.sett_st.set_text("✅ Saved.")
        c.pack_start(self.btn("Save settings",cb=save),False,False,0); c.pack_start(self.sett_st,False,False,0)
        vb.pack_start(c,False,False,0); self.page("settings",vb)

    def _install_launcher(self,pkg):
        self.inst_st.set_text("Installing…")
        def do():
            r=subprocess.run(["pkexec","apt-get","install","-y",pkg],capture_output=True,text=True)
            GLib.idle_add(self.inst_st.set_text,"✅ Done." if r.returncode==0 else f"❌ {r.stderr[:60]}")
        threading.Thread(target=do,daemon=True).start()

    def _news(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        vb.pack_start(self.lbl("Minecraft News","title"),False,False,0)
        self.news_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.news_box.pack_start(self.lbl("Loading news…","sub"),False,False,0)
        vb.pack_start(self.sw(self.news_box,420),True,True,0); self.page("news",vb)
        threading.Thread(target=self._fetch_news,daemon=True).start()

    def _fetch_news(self):
        try:
            with urllib.request.urlopen("https://launchercontent.mojang.com/news.json",timeout=6) as r:
                entries=json.loads(r.read()).get("entries",[])[:8]
            GLib.idle_add(self._show_news,entries)
        except: GLib.idle_add(self._show_news,[])

    def _show_news(self,entries):
        for ch in self.news_box.get_children(): self.news_box.remove(ch)
        if not entries:
            self.news_box.pack_start(self.lbl("Could not load news. Check your internet connection.","sub"),False,False,0)
        else:
            for e in entries:
                c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); c.get_style_context().add_class("news")
                c.pack_start(self.lbl(e.get("title","Update"),"head"),False,False,0)
                c.pack_start(self.lbl((e.get("text","")[:200]+"…"),"sub"),False,False,0)
                url=e.get("readMoreLink","")
                if url: c.pack_start(self.btn("Read more","btn-s",cb=lambda _,u=url:subprocess.Popen(["microsoft-edge-stable",u])),False,False,0)
                self.news_box.pack_start(c,False,False,0)
        self.news_box.show_all()

def main():
    win=MCLauncher(); win.connect("destroy",Gtk.main_quit); Gtk.main()
if __name__=="__main__": main()
