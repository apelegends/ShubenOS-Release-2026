#!/usr/bin/env python3
"""Shuben Launcher OS — OOBE (Out Of Box Experience)
Stages: Welcome → Features/No-AV warning → WiFi → Account (or Skip) → PIN → Done
"""
import gi, os, json, hashlib, subprocess, threading
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GLib

A="#00A8E8"; D="#0D1117"; C="#161B22"; W="#FFFFFF"; G="#8B949E"; R="#F85149"; GR="#3FB950"
CSS=f"""
*{{font-family:'Segoe UI','Liberation Sans',sans-serif;}}
window{{background:{D};}}
.card{{background:{C};border-radius:12px;padding:32px;border:1px solid #30363D;}}
.title{{color:{W};font-size:26px;font-weight:700;}}
.head{{color:{W};font-size:15px;font-weight:600;}}
.sub{{color:{G};font-size:14px;}}
.logo{{color:{A};font-size:38px;font-weight:900;letter-spacing:2px;}}
.btn-p{{background:{A};color:{W};border:none;border-radius:6px;padding:12px 28px;font-size:14px;font-weight:600;}}
.btn-p:hover{{background:#0090CC;}}
.btn-s{{background:transparent;color:{G};border:1px solid #30363D;border-radius:6px;padding:10px 22px;font-size:13px;}}
.btn-s:hover{{border-color:{A};color:{W};}}
.warn{{background:rgba(248,81,73,0.1);border:1px solid {R};border-radius:8px;padding:14px;}}
.warn-t{{color:{R};font-size:13px;font-weight:700;}}
.field{{background:#21262D;color:{W};border:1px solid #30363D;border-radius:6px;padding:9px 13px;font-size:13px;}}
.field:focus{{border-color:{A};}}
.pin-box{{background:#21262D;color:{W};border:1px solid #30363D;border-radius:8px;font-size:26px;font-weight:700;min-width:58px;min-height:66px;}}
.pin-box:focus{{border-color:{A};}}
.step{{color:{G};font-size:12px;}}
.step-on{{color:{A};font-weight:700;}}
.ok-t{{color:{GR};font-size:13px;}}
.feat-row{{padding:8px 0;border-bottom:1px solid #21262D;}}
"""
STATE="/var/lib/shuben/oobe-state.json"
USERS="/var/lib/shuben/accounts.json"
PIN_F="/var/lib/shuben/pin.json"

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def save_state(d):
    os.makedirs("/var/lib/shuben",exist_ok=True)
    open(STATE,"w").write(json.dumps(d))
def load_state():
    try: return json.loads(open(STATE).read())
    except: return {}
def save_account(email,pw_hash,name):
    os.makedirs("/var/lib/shuben",exist_ok=True)
    open(USERS,"w").write(json.dumps({"primary":{"email":email,"pw_hash":pw_hash,"display_name":name or email.split("@")[0]}}))
def save_pin(pin):
    os.makedirs("/var/lib/shuben",exist_ok=True)
    open(PIN_F,"w").write(json.dumps({"pin_hash":sha(pin)}))

class OOBE(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Launcher OS — Setup")
        self.maximize(); self.set_decorated(False)
        p=Gtk.CssProvider(); p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.acct={}
        self.stack=Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self.stack.set_transition_duration(280)
        self.add(self.stack)
        self._welcome(); self._features(); self._wifi(); self._account(); self._pin(); self._done()
        self.stack.set_visible_child_name("welcome")
        self.show_all()

    def go(self,p): self.stack.set_visible_child_name(p)
    def lbl(self,t,css="sub",xa=0,wrap=True):
        l=Gtk.Label(label=t); l.get_style_context().add_class(css)
        l.set_xalign(xa); l.set_line_wrap(wrap); return l
    def btn(self,t,css="btn-p",cb=None):
        b=Gtk.Button(label=t); b.get_style_context().add_class(css)
        if cb: b.connect("clicked",cb); return b
    def entry(self,ph="",pw=False):
        e=Gtk.Entry(); e.set_placeholder_text(ph); e.get_style_context().add_class("field")
        if pw: e.set_visibility(False); e.set_invisible_char("●")
        e.set_hexpand(True); return e
    def steps(self,names,cur):
        b=Gtk.Box(spacing=10); b.set_halign(Gtk.Align.CENTER)
        for i,n in enumerate(names):
            l=Gtk.Label(label=n); l.get_style_context().add_class("step-on" if i==cur else "step")
            b.pack_start(l,False,False,0)
            if i<len(names)-1: b.pack_start(self.lbl("›","step"),False,False,0)
        return b
    def center(self,child):
        o=Gtk.Box(); o.set_halign(Gtk.Align.CENTER); o.set_valign(Gtk.Align.CENTER)
        o.pack_start(child,False,False,0); return o

    def _welcome(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=22)
        c.get_style_context().add_class("card"); c.set_size_request(560,-1)
        c.pack_start(self.lbl("SHUBEN LAUNCHER","logo",0.5),False,False,0)
        c.pack_start(self.lbl("Minecraft OS  ·  by Apelegends","sub",0.5),False,False,0)
        c.pack_start(Gtk.Separator(),False,False,6)
        c.pack_start(self.lbl("Welcome! Let's get your system ready.\nThis takes just a few minutes.","sub",0.5),False,False,0)
        br=Gtk.Box(); br.set_halign(Gtk.Align.CENTER)
        br.pack_start(self.btn("Let's go →",cb=lambda _:self.go("features")),False,False,0)
        c.pack_start(br,False,False,16)
        self.stack.add_named(self.center(c),"welcome")

    def _features(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        c.get_style_context().add_class("card"); c.set_size_request(600,-1)
        c.pack_start(self.steps(["Features","Wi-Fi","Account","PIN","Done"],0),False,False,0)
        c.pack_start(self.lbl("What's included","title"),False,False,8)
        for icon,text in [
            ("✅","Custom Shuben Launcher desktop"),
            ("✅","Minecraft Launcher pre-installed"),
            ("✅","Auto GPU drivers — Intel, AMD, NVIDIA"),
            ("✅","Microsoft Edge browser"),
            ("✅","Dual-boot ready"),
            ("✅","PIN login — no Microsoft account required"),
            ("✅","Lightweight — optimised for gaming"),
        ]:
            row=Gtk.Box(spacing=10); row.get_style_context().add_class("feat-row")
            row.pack_start(self.lbl(icon),False,False,0); row.pack_start(self.lbl(text),True,True,0)
            c.pack_start(row,False,False,0)
        # NO ANTIVIRUS warning
        wb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); wb.get_style_context().add_class("warn")
        wb.pack_start(self.lbl("⚠  NO ANTIVIRUS INCLUDED","warn-t"),False,False,0)
        wb.pack_start(self.lbl("Shuben Launcher OS ships without antivirus software by design.\nIt is your responsibility to stay safe online.","sub"),False,False,0)
        c.pack_start(wb,False,False,4)
        self.av_check=Gtk.CheckButton(label="I understand — NO antivirus, and I accept this.")
        self.av_check.get_style_context().add_class("warn-t")
        c.pack_start(self.av_check,False,False,0)
        br=Gtk.Box(); br.set_halign(Gtk.Align.END)
        br.pack_start(self.btn("Next →",cb=self._feat_next),False,False,0)
        c.pack_start(br,False,False,8)
        self.stack.add_named(self.center(c),"features")

    def _feat_next(self,_):
        if not self.av_check.get_active():
            d=Gtk.MessageDialog(transient_for=self,flags=0,
                message_type=Gtk.MessageType.WARNING,buttons=Gtk.ButtonsType.OK,
                text="Please accept the no-antivirus notice to continue.")
            d.run(); d.destroy(); return
        self.go("wifi")

    def _wifi(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        c.get_style_context().add_class("card"); c.set_size_request(620,-1)
        c.pack_start(self.steps(["Features","Wi-Fi","Account","PIN","Done"],1),False,False,0)
        c.pack_start(self.lbl("Connect to Wi-Fi","title"),False,False,8)
        c.pack_start(self.lbl("Select a network below or skip to connect later.","sub"),False,False,0)
        self.wifi_lb=Gtk.ListBox(); self.wifi_lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        sw=Gtk.ScrolledWindow(); sw.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(150); sw.add(self.wifi_lb); c.pack_start(sw,True,True,0)
        self.wifi_ssid=self.entry("Network name (SSID)")
        self.wifi_pass=self.entry("Password",pw=True)
        c.pack_start(self.wifi_ssid,False,False,0); c.pack_start(self.wifi_pass,False,False,0)
        self.wifi_status=self.lbl("","step"); c.pack_start(self.wifi_status,False,False,0)
        br=Gtk.Box(spacing=10); br.set_halign(Gtk.Align.END)
        br.pack_start(self.btn("Scan","btn-s",cb=self._wifi_scan),False,False,0)
        br.pack_start(self.btn("Skip","btn-s",cb=lambda _:self.go("account")),False,False,0)
        br.pack_start(self.btn("Connect →",cb=self._wifi_connect),False,False,0)
        c.pack_start(br,False,False,8)
        self.stack.add_named(self.center(c),"wifi")
        self.wifi_lb.connect("row-activated",lambda lb,row:self.wifi_ssid.set_text(row.get_data("ssid") or ""))
        GLib.idle_add(self._wifi_scan,None)

    def _wifi_scan(self,_):
        self.wifi_status.set_text("Scanning…")
        def do():
            try:
                r=subprocess.run(["nmcli","-t","-f","SSID,SIGNAL","dev","wifi"],
                                  capture_output=True,text=True,timeout=10)
                nets=[]
                for line in r.stdout.strip().split("\n"):
                    p=line.split(":")
                    if p and p[0].strip(): nets.append((p[0].strip(),p[1].strip() if len(p)>1 else "?"))
                GLib.idle_add(self._wifi_populate,nets)
            except Exception as e: GLib.idle_add(self.wifi_status.set_text,f"Scan error: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _wifi_populate(self,nets):
        for ch in self.wifi_lb.get_children(): self.wifi_lb.remove(ch)
        for ssid,sig in nets[:12]:
            row=Gtk.ListBoxRow(); row.set_data("ssid",ssid)
            box=Gtk.Box(spacing=10); box.set_margin_top(6); box.set_margin_bottom(6)
            box.set_margin_start(10); box.set_margin_end(10)
            box.pack_start(self.lbl(ssid,"head"),True,True,0)
            box.pack_end(self.lbl(f"📶 {sig}","step"),False,False,0)
            row.add(box); self.wifi_lb.add(row)
        self.wifi_lb.show_all()
        self.wifi_status.set_text(f"{len(nets)} networks found.")

    def _wifi_connect(self,_):
        ssid=self.wifi_ssid.get_text().strip(); pw=self.wifi_pass.get_text()
        if not ssid: self.wifi_status.set_text("Enter a network name."); return
        self.wifi_status.set_text(f"Connecting to '{ssid}'…")
        def do():
            try:
                cmd=["nmcli","dev","wifi","connect",ssid]
                if pw: cmd+=["password",pw]
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
                if r.returncode==0:
                    GLib.idle_add(self.wifi_status.set_text,f"✅ Connected to {ssid}")
                    GLib.timeout_add(1000,lambda:self.go("account") or False)
                else:
                    GLib.idle_add(self.wifi_status.set_text,f"❌ Failed: {r.stderr[:80]}")
            except Exception as e: GLib.idle_add(self.wifi_status.set_text,f"Error: {e}")
        threading.Thread(target=do,daemon=True).start()

    def _account(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        c.get_style_context().add_class("card"); c.set_size_request(540,-1)
        c.pack_start(self.steps(["Features","Wi-Fi","Account","PIN","Done"],2),False,False,0)
        c.pack_start(self.lbl("Sign in or create account","title"),False,False,8)
        c.pack_start(self.lbl("Works with any email address. No Microsoft account needed.","sub"),False,False,0)
        # Tabs
        tabs=Gtk.Box(spacing=0)
        self.tab_si=self.btn("Sign In","btn-s",cb=lambda _:self.acct_stack.set_visible_child_name("si"))
        self.tab_su=self.btn("Sign Up","btn-s",cb=lambda _:self.acct_stack.set_visible_child_name("su"))
        tabs.pack_start(self.tab_si,True,True,0); tabs.pack_start(self.tab_su,True,True,0)
        c.pack_start(tabs,False,False,0)
        self.acct_stack=Gtk.Stack()
        # Sign-in
        si=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.si_email=self.entry("Email address")
        self.si_pass=self.entry("Password",pw=True)
        si.pack_start(self.si_email,False,False,0); si.pack_start(self.si_pass,False,False,0)
        self.acct_stack.add_named(si,"si")
        # Sign-up
        su=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.su_name=self.entry("Display name (optional)")
        self.su_email=self.entry("Email address")
        self.su_pass=self.entry("Password",pw=True)
        self.su_pass2=self.entry("Confirm password",pw=True)
        for w in [self.su_name,self.su_email,self.su_pass,self.su_pass2]: su.pack_start(w,False,False,0)
        self.acct_stack.add_named(su,"su")
        self.acct_stack.set_visible_child_name("su")
        c.pack_start(self.acct_stack,False,False,0)
        self.acct_err=self.lbl("","warn-t"); c.pack_start(self.acct_err,False,False,0)
        br=Gtk.Box(spacing=10); br.set_halign(Gtk.Align.END)
        br.pack_start(self.btn("Skip for now","btn-s",cb=self._acct_skip),False,False,0)
        br.pack_start(self.btn("Continue →",cb=self._acct_next),False,False,0)
        c.pack_start(br,False,False,8)
        self.stack.add_named(self.center(c),"account")

    def _acct_skip(self,_):
        save_account("","","User"); self.acct={"skipped":True}; self.go("pin")

    def _acct_next(self,_):
        tab=self.acct_stack.get_visible_child_name()
        if tab=="su":
            name=self.su_name.get_text().strip(); email=self.su_email.get_text().strip()
            pw=self.su_pass.get_text(); pw2=self.su_pass2.get_text()
            if not email or "@" not in email: self.acct_err.set_text("Valid email required."); return
            if len(pw)<4: self.acct_err.set_text("Password must be 4+ characters."); return
            if pw!=pw2: self.acct_err.set_text("Passwords do not match."); return
            save_account(email,sha(pw),name); self.acct={"email":email}
        else:
            email=self.si_email.get_text().strip(); pw=self.si_pass.get_text()
            if not email: self.acct_err.set_text("Email required."); return
            try:
                accts=json.loads(open(USERS).read())
                a=accts.get("primary",{})
                if a.get("email")!=email or a.get("pw_hash")!=sha(pw):
                    self.acct_err.set_text("Incorrect email or password."); return
            except: self.acct_err.set_text("No account found. Sign up first."); return
            self.acct={"email":email}
        self.acct_err.set_text(""); self.go("pin")

    def _pin(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14)
        c.get_style_context().add_class("card"); c.set_size_request(480,-1)
        c.pack_start(self.steps(["Features","Wi-Fi","Account","PIN","Done"],3),False,False,0)
        c.pack_start(self.lbl("Set your PIN","title"),False,False,8)
        c.pack_start(self.lbl("4-digit PIN used to unlock the desktop. Required.","sub"),False,False,0)
        self.pin_entries=[]; self.pin2_entries=[]
        for label,store in [("PIN",self.pin_entries),("Confirm PIN",self.pin2_entries)]:
            c.pack_start(self.lbl(label,"head"),False,False,4)
            row=Gtk.Box(spacing=10); row.set_halign(Gtk.Align.CENTER)
            for i in range(4):
                e=Gtk.Entry(); e.set_max_length(1); e.set_input_purpose(Gtk.InputPurpose.DIGITS)
                e.set_visibility(False); e.set_invisible_char("●")
                e.get_style_context().add_class("pin-box"); e.set_width_chars(2)
                ni=i+1; lst=store
                def on_ch(w,nl=ni,ls=lst):
                    t=w.get_text()
                    if t and not t.isdigit(): w.set_text(""); return
                    if t and nl<len(ls): ls[nl].grab_focus()
                e.connect("changed",on_ch); store.append(e); row.pack_start(e,False,False,0)
            c.pack_start(row,False,False,0)
        self.pin_err=self.lbl("","warn-t"); c.pack_start(self.pin_err,False,False,0)
        br=Gtk.Box(); br.set_halign(Gtk.Align.END)
        br.pack_start(self.btn("Set PIN & finish →",cb=self._pin_set),False,False,0)
        c.pack_start(br,False,False,8)
        self.stack.add_named(self.center(c),"pin")
        GLib.idle_add(lambda:self.pin_entries[0].grab_focus() if self.pin_entries else None)

    def _pin_set(self,_):
        pin="".join(e.get_text() for e in self.pin_entries)
        pin2="".join(e.get_text() for e in self.pin2_entries)
        if len(pin)!=4 or not pin.isdigit(): self.pin_err.set_text("Enter a 4-digit PIN."); return
        if pin!=pin2: self.pin_err.set_text("PINs do not match."); return
        save_pin(pin)
        st=load_state(); st["oobe_complete"]=True; st.update(self.acct); save_state(st)
        self.go("done")

    def _done(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20)
        c.get_style_context().add_class("card"); c.set_size_request(520,-1)
        c.pack_start(self.lbl("🎮  You're all set!","title",0.5),False,False,0)
        c.pack_start(self.lbl("Shuben Launcher OS is ready.\nMinecraft Launcher will open automatically.","sub",0.5),False,False,0)
        self.done_cd=self.lbl("Starting desktop in 5…","step",0.5); c.pack_start(self.done_cd,False,False,0)
        br=Gtk.Box(); br.set_halign(Gtk.Align.CENTER)
        br.pack_start(self.btn("Start now →",cb=self._launch),False,False,0); c.pack_start(br,False,False,8)
        self.stack.add_named(self.center(c),"done")
        self.stack.connect("notify::visible-child",self._on_stack)

    def _on_stack(self,s,_):
        if s.get_visible_child_name()=="done": self._cd=5; GLib.timeout_add(1000,self._tick)
    def _tick(self):
        self._cd-=1; self.done_cd.set_text(f"Starting desktop in {self._cd}…")
        if self._cd<=0: self._launch(None); return False
        return True
    def _launch(self,_):
        self.destroy(); subprocess.Popen(["openbox-session"]); Gtk.main_quit()

def main():
    if load_state().get("oobe_complete"): return
    win=OOBE(); win.connect("destroy",Gtk.main_quit); Gtk.main()

if __name__=="__main__": main()
