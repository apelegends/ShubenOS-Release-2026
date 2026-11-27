#!/usr/bin/env python3
"""Shuben Launcher OS — Settings App"""
import gi, os, json, subprocess, threading, hashlib
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GLib

A="#00A8E8"; D="#0D1117"; C="#161B22"; W="#FFFFFF"; G="#8B949E"; GR="#3FB950"; R="#F85149"
CSS=f"""
*{{font-family:'Segoe UI','Liberation Sans',sans-serif;}}
window{{background:{D};}}
#sidebar{{background:{D};border-right:1px solid #21262D;min-width:190px;}}
.sbtn{{background:transparent;border:none;color:{G};border-radius:8px;padding:10px 16px;font-size:13px;}}
.sbtn:hover{{background:rgba(255,255,255,0.06);color:{W};}}
.sbtn.active{{background:rgba(0,168,232,0.15);color:{A};border-left:3px solid {A};}}
.card{{background:{C};border-radius:10px;padding:20px;border:1px solid #21262D;}}
.title{{color:{W};font-size:20px;font-weight:700;}}
.head{{color:{W};font-size:14px;font-weight:600;}}
.sub{{color:{G};font-size:13px;}}
.btn-p{{background:{A};color:{W};border:none;border-radius:6px;padding:9px 18px;font-size:13px;font-weight:600;}}
.btn-s{{background:transparent;color:{G};border:1px solid #30363D;border-radius:6px;padding:7px 14px;font-size:13px;}}
.btn-s:hover{{border-color:{A};color:{W};}}
.btn-d{{background:{R};color:{W};border:none;border-radius:6px;padding:9px 18px;font-size:13px;font-weight:600;}}
.field{{background:#21262D;color:{W};border:1px solid #30363D;border-radius:6px;padding:8px 12px;font-size:13px;}}
.field:focus{{border-color:{A};}}
.ok{{color:{GR};font-size:12px;}} .err{{color:{R};font-size:12px;}}
.irow{{padding:6px 0;border-bottom:1px solid #21262D;}}
.warn-t{{color:{R};font-size:13px;font-weight:600;}}
"""
GPU_F="/var/lib/shuben/gpu-info.json"
ACCT_F="/var/lib/shuben/accounts.json"
PIN_F="/var/lib/shuben/pin.json"
PAGES=[("🖥️","Display","display"),("🎮","GPU","gpu"),("🔊","Sound","sound"),
       ("📶","Network","network"),("👤","Account","account"),("🔑","PIN","pin"),
       ("⚡","Power","power"),("ℹ️","About","about")]

def sha(s): return hashlib.sha256(s.encode()).hexdigest()

class Settings(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Settings")
        self.set_default_size(840,560); self.set_decorated(False)
        p=Gtk.CssProvider(); p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._build(); self.show_all()

    def _build(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL); self.add(vb)
        tb=Gtk.Box(); tb.set_size_request(-1,36)
        tb.override_background_color(Gtk.StateFlags.NORMAL,Gdk.RGBA(0.05,0.07,0.09,1))
        tl=Gtk.Label(); tl.set_markup(f'<span foreground="{A}" font="12" font_weight="bold">  ⚙  Shuben Settings</span>')
        tb.pack_start(tl,False,False,0); tb.pack_start(Gtk.Box(),True,True,0)
        for sym,fn in [("─",self.iconify),("□",lambda:self.unmaximize() if self.is_maximized() else self.maximize()),("✕",self.destroy)]:
            b=Gtk.Button(label=sym); b.get_style_context().add_class("btn-s"); b.set_size_request(40,36)
            b.connect("clicked",lambda _,f=fn:f()); tb.pack_end(b,False,False,0)
        tb.connect("button-press-event",lambda w,e:self.begin_move_drag(e.button,int(e.x_root),int(e.y_root),e.time))
        vb.pack_start(tb,False,False,0)
        hb=Gtk.Box(); vb.pack_start(hb,True,True,0)
        sb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); sb.set_name("sidebar")
        sb.set_margin_top(10); sb.set_margin_start(8); sb.set_margin_end(8)
        self.sbtns={}
        for em,nm,pg in PAGES:
            b=Gtk.Button(label=f"{em}  {nm}"); b.get_style_context().add_class("sbtn")
            b.connect("clicked",lambda _,p=pg:self._switch(p)); sb.pack_start(b,False,False,0); self.sbtns[pg]=b
        hb.pack_start(sb,False,False,0)
        self.stack=Gtk.Stack(); self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE); self.stack.set_transition_duration(120)
        hb.pack_start(self.stack,True,True,0)
        self._display(); self._gpu(); self._sound(); self._network(); self._account(); self._pin_pg(); self._power(); self._about()
        self._switch("display")

    def _switch(self,pg):
        self.stack.set_visible_child_name(pg)
        for n,b in self.sbtns.items():
            ctx=b.get_style_context()
            if n==pg: ctx.add_class("active")
            else: ctx.remove_class("active")

    def lbl(self,t,css="sub",xa=0):
        l=Gtk.Label(label=t); l.get_style_context().add_class(css); l.set_xalign(xa); l.set_line_wrap(True); return l
    def btn(self,t,css="btn-p",cb=None):
        b=Gtk.Button(label=t); b.get_style_context().add_class(css)
        if cb: b.connect("clicked",cb); return b
    def field(self,ph="",pw=False):
        e=Gtk.Entry(); e.set_placeholder_text(ph); e.get_style_context().add_class("field")
        if pw: e.set_visibility(False); e.set_invisible_char("●"); e.set_hexpand(True); return e
    def card(self,*ch,sp=12):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=sp); c.get_style_context().add_class("card")
        for x in ch: c.pack_start(x,False,False,0); return c
    def sw(self,ch):
        s=Gtk.ScrolledWindow(); s.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC); s.add(ch); return s
    def add_page(self,name,child):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16)
        vb.set_margin_top(22); vb.set_margin_start(22); vb.set_margin_end(22); vb.set_margin_bottom(22)
        vb.pack_start(child,False,False,0); self.stack.add_named(self.sw(vb),name)
    def run_cmd(self,cmd,st):
        st.set_text("Running…")
        def do():
            r=subprocess.run(cmd,shell=True,capture_output=True,text=True)
            GLib.idle_add(st.set_text,"✅ Done." if r.returncode==0 else f"❌ {r.stderr[:80]}")
        threading.Thread(target=do,daemon=True).start()

    def _display(self):
        st=self.lbl("","ok"); rb=Gtk.Box(spacing=8)
        for res in ["1920x1080","1600x900","1366x768","1280x720"]:
            rb.pack_start(self.btn(res,"btn-s",cb=lambda _,r=res:self.run_cmd(f"xrandr -s {r}",st)),False,False,0)
        fb=Gtk.Box(spacing=8)
        for hz in ["60","75","120","144","165"]:
            fb.pack_start(self.btn(f"{hz}Hz","btn-s",cb=lambda _,h=hz:self.run_cmd(f"xrandr --rate {h}",st)),False,False,0)
        self.add_page("display",self.card(self.lbl("Display","title"),self.lbl("Resolution","head"),rb,self.lbl("Refresh rate","head"),fb,st))

    def _gpu(self):
        try: gi=json.loads(open(GPU_F).read())
        except: gi={}
        detected=", ".join(filter(None,[("Intel" if gi.get("intel") else ""),("AMD" if gi.get("amd") else ""),("NVIDIA" if gi.get("nvidia") else "")])) or "Not detected"
        st=self.lbl("","ok")
        c=self.card(self.lbl("GPU & Graphics","title"),self.lbl("Detected GPUs","head"),self.lbl(detected,"sub"),
                    self.lbl(f"Raw: {gi.get('raw','N/A')}","sub"),self.lbl("Driver actions","head"),
                    self.btn("Re-run GPU auto-setup",cb=lambda _:self.run_cmd("pkexec shuben-gpu-setup",st)),st)
        if gi.get("nvidia"):
            nb=Gtk.Box(spacing=8)
            for pkg in ["nvidia-driver","nvidia-driver-525","nvidia-driver-535"]:
                nb.pack_start(self.btn(pkg,"btn-s",cb=lambda _,p=pkg:self.run_cmd(f"pkexec apt-get install -y {p}",st)),False,False,0)
            c.pack_start(self.lbl("NVIDIA proprietary drivers:","head"),False,False,0); c.pack_start(nb,False,False,0)
        self.add_page("gpu",c)

    def _sound(self):
        sc=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1); sc.set_value(80); sc.set_hexpand(True)
        sc.connect("value-changed",lambda s:subprocess.Popen(["pactl","set-sink-volume","@DEFAULT_SINK@",f"{int(s.get_value())}%"]))
        self.add_page("sound",self.card(self.lbl("Sound","title"),self.lbl("Volume","head"),sc,
                                         self.btn("Open full audio settings",cb=lambda _:subprocess.Popen(["pavucontrol"]))))

    def _network(self):
        st=self.lbl("","ok")
        self.add_page("network",self.card(self.lbl("Network & Wi-Fi","title"),
                       self.btn("Open Network Manager",cb=lambda _:subprocess.Popen(["nm-connection-editor"])),
                       self.btn("Check connection","btn-s",cb=lambda _:self.run_cmd("ip addr show > /tmp/net.txt && xterm -e 'cat /tmp/net.txt;read'",st)),st))

    def _account(self):
        try: acct=json.loads(open(ACCT_F).read()).get("primary",{})
        except: acct={}
        name=acct.get("display_name") or (acct.get("email","").split("@")[0]) or "User"
        email=acct.get("email","(no account)")
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12); c.get_style_context().add_class("card")
        c.pack_start(self.lbl("Account","title"),False,False,0)
        c.pack_start(self.lbl(f"Name: {name}","sub"),False,False,0); c.pack_start(self.lbl(f"Email: {email}","sub"),False,False,0)
        c.pack_start(self.lbl("Change display name","head"),False,False,0)
        self.acct_name=Gtk.Entry(); self.acct_name.set_text(name); self.acct_name.get_style_context().add_class("field")
        c.pack_start(self.acct_name,False,False,0)
        st=self.lbl("","ok")
        def save(_):
            try:
                data={}
                try: data=json.loads(open(ACCT_F).read())
                except: pass
                if "primary" not in data: data["primary"]={}
                data["primary"]["display_name"]=self.acct_name.get_text().strip()
                open(ACCT_F,"w").write(json.dumps(data)); st.set_text("✅ Saved.")
            except Exception as e: st.set_text(f"❌ {e}")
        c.pack_start(self.btn("Save name",cb=save),False,False,0); c.pack_start(st,False,False,0)
        self.add_page("account",c)

    def _pin_pg(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12); c.get_style_context().add_class("card")
        c.pack_start(self.lbl("PIN","title"),False,False,0); c.pack_start(self.lbl("Change your PIN","head"),False,False,0)
        self.p_old=Gtk.Entry(); self.p_old.set_placeholder_text("Current PIN"); self.p_old.set_visibility(False); self.p_old.set_max_length(4); self.p_old.get_style_context().add_class("field")
        self.p_new=Gtk.Entry(); self.p_new.set_placeholder_text("New PIN"); self.p_new.set_visibility(False); self.p_new.set_max_length(4); self.p_new.get_style_context().add_class("field")
        self.p_new2=Gtk.Entry(); self.p_new2.set_placeholder_text("Confirm new PIN"); self.p_new2.set_visibility(False); self.p_new2.set_max_length(4); self.p_new2.get_style_context().add_class("field")
        for w in [self.p_old,self.p_new,self.p_new2]: c.pack_start(w,False,False,0)
        st=self.lbl("","ok")
        def change(_):
            old=self.p_old.get_text(); new=self.p_new.get_text(); new2=self.p_new2.get_text()
            if not (old.isdigit() and new.isdigit() and new2.isdigit()): st.set_text("❌ Digits only."); return
            if new!=new2: st.set_text("❌ New PINs do not match."); return
            try:
                stored=json.loads(open(PIN_F).read()).get("pin_hash","")
                if sha(old)!=stored: st.set_text("❌ Current PIN incorrect."); return
                open(PIN_F,"w").write(json.dumps({"pin_hash":sha(new)})); st.set_text("✅ PIN changed.")
                for w in [self.p_old,self.p_new,self.p_new2]: w.set_text("")
            except Exception as e: st.set_text(f"❌ {e}")
        c.pack_start(self.btn("Change PIN",cb=change),False,False,0); c.pack_start(st,False,False,0)
        self.add_page("pin",c)

    def _power(self):
        rb=Gtk.Box(spacing=10)
        for lbl,cmd in [("🔒 Lock","shuben-lock"),("🔄 Restart","systemctl reboot"),("⏻ Shut down","systemctl poweroff"),("💤 Suspend","systemctl suspend")]:
            rb.pack_start(self.btn(lbl,"btn-s" if "Lock" not in lbl else "btn-p",cb=lambda _,c=cmd:subprocess.Popen(c.split())),False,False,0)
        self.add_page("power",self.card(self.lbl("Power","title"),self.lbl("Power options","head"),rb))

    def _about(self):
        try: kern=subprocess.check_output(["uname","-r"],text=True).strip()
        except: kern="unknown"
        try: cpu=subprocess.check_output("grep 'model name' /proc/cpuinfo|head -1|cut -d: -f2",shell=True,text=True).strip()
        except: cpu="unknown"
        try: mem=f"{int(subprocess.check_output('grep MemTotal /proc/meminfo|awk \"{print $2}\"',shell=True,text=True).strip())//1024} MB"
        except: mem="unknown"
        try: gi=json.loads(open(GPU_F).read()); gpus=", ".join(filter(None,[("Intel" if gi.get("intel") else ""),("AMD" if gi.get("amd") else ""),("NVIDIA" if gi.get("nvidia") else "")]))
        except: gpus="Unknown"
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10); c.get_style_context().add_class("card")
        c.pack_start(self.lbl("About Shuben Launcher OS","title"),False,False,0)
        for k,v in [("OS","Shuben Launcher OS 1.0"),("Base","Ubuntu 22.04"),("By","Shuben / Apelegends"),("Kernel",kern),("CPU",cpu),("RAM",mem),("GPU",gpus),("Browser","Microsoft Edge")]:
            row=Gtk.Box(spacing=14); row.get_style_context().add_class("irow")
            kl=self.lbl(k,"head"); kl.set_size_request(90,-1)
            row.pack_start(kl,False,False,0); row.pack_start(self.lbl(v,"sub"),True,True,0); c.pack_start(row,False,False,0)
        no_av=Gtk.Label(); no_av.set_markup(f'<span foreground="{R}" font_weight="bold">⚠  NO ANTIVIRUS — by design</span>'); no_av.set_xalign(0)
        c.pack_start(no_av,False,False,8); self.add_page("about",c)

def main():
    win=Settings(); win.connect("destroy",Gtk.main_quit); Gtk.main()
if __name__=="__main__": main()
