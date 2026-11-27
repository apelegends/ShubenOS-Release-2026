#!/usr/bin/env python3
"""
Shuben Launcher OS — Custom Installer
Ubuntu-based ISO, full Shuben UI, no Ubiquity/Calamares.
Modes: Erase Disk or Dual-Boot. Every error shows how to fix it.
"""
import gi, os, sys, json, subprocess, threading, re
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GLib

A="#00A8E8"; D="#0D1117"; C="#161B22"; W="#FFFFFF"; G="#8B949E"
GR="#3FB950"; R="#F85149"

CSS=f"""
*{{font-family:'Segoe UI','Liberation Sans',sans-serif;}}
window{{background:{D};}}
.card{{background:{C};border-radius:10px;padding:24px;border:1px solid #21262D;}}
.title{{color:{W};font-size:22px;font-weight:700;}}
.head{{color:{W};font-size:15px;font-weight:600;}}
.sub{{color:{G};font-size:13px;}}
.logo{{color:{A};font-size:28px;font-weight:900;letter-spacing:2px;}}
.btn-p{{background:{A};color:{W};border:none;border-radius:7px;padding:12px 28px;font-size:14px;font-weight:700;}}
.btn-p:hover{{background:#0090CC;}}
.btn-s{{background:transparent;color:{G};border:1px solid #30363D;border-radius:7px;padding:10px 20px;font-size:13px;}}
.btn-s:hover{{border-color:{A};color:{W};}}
.btn-d{{background:{R};color:{W};border:none;border-radius:7px;padding:12px 28px;font-size:14px;font-weight:700;}}
.btn-d:hover{{background:#c0392b;}}
.btn-back{{background:transparent;color:{G};border:none;font-size:13px;padding:4px 0;}}
.opt{{background:{C};border-radius:12px;padding:20px;border:2px solid #21262D;}}
.opt:hover{{border-color:{A};}}
.disk-row{{background:rgba(255,255,255,0.03);border-radius:7px;padding:12px 16px;border:1px solid #21262D;margin:3px 0;}}
.disk-row:hover{{border-color:{A};}}
.warn{{background:rgba(248,81,73,0.09);border:1px solid {R};border-radius:8px;padding:14px;}}
.warn-t{{color:{R};font-size:13px;font-weight:600;}}
.info{{background:rgba(0,168,232,0.07);border:1px solid {A};border-radius:8px;padding:14px;}}
.info-t{{color:{A};font-size:13px;}}
.fix{{background:rgba(61,185,80,0.09);border:1px solid {GR};border-radius:8px;padding:14px;}}
.fix-t{{color:{GR};font-size:13px;font-weight:700;}}
.fix-b{{color:{G};font-size:12px;}}
.err-box{{background:rgba(248,81,73,0.12);border:1px solid {R};border-radius:8px;padding:16px;}}
.err-t{{color:{R};font-size:15px;font-weight:700;}}
.err-b{{color:{W};font-size:13px;}}
.log{{background:#0A0E13;color:#A0B0C0;font-family:'Liberation Mono',monospace;font-size:11px;border-radius:6px;padding:8px;}}
.prog progress{{background:{A};border-radius:4px;}}
.prog trough{{background:#21262D;border-radius:4px;}}
.ok{{color:{GR};font-size:19px;font-weight:700;}}
.dot{{min-width:10px;min-height:10px;border-radius:5px;background:#30363D;}}
.dot.done{{background:{GR};}}
.dot.active{{background:{A};}}
.dot.error{{background:{R};}}
"""

FIXES={
    "no space left":          "Pick a larger disk or use Erase Disk mode.",
    "no medium found":        "Drive disconnected — replug it and click Retry.",
    "permission denied":      "Run as root:\n  sudo shuben-installer",
    "read-only":              "Drive is write-protected. Try a different drive.",
    "device or resource busy":"Unmount first:\n  sudo umount /dev/sdXN",
    "input/output error":     "Drive hardware error:\n  sudo badblocks -v /dev/sdX",
    "not enough free":        "Need 20+ GB free. Shrink Windows C: via Disk Management.",
    "no free partition":      "No unallocated space. Shrink a partition or use Erase mode.",
    "grub-install":           "Disable Secure Boot:\n  BIOS → Security → Secure Boot → Disabled",
    "efi":                    "Boot USB in UEFI mode and disable Secure Boot in BIOS.",
    "mkfs":                   "Format failed — try a different drive.",
    "parted":                 "Partition error. Back up data!\n  sudo parted /dev/sdX mklabel gpt",
    "mount":                  "Mount failed:\n  sudo fsck /dev/sdXN",
    "rsync":                  "Copy failed — check disk space and retry.",
    "squashfs":               "ISO corrupted — re-download and re-flash to USB.",
    "timeout":                "Timed out — slow drive or no internet. Retry.",
    "debootstrap":            "Check internet and disk space (20+ GB needed).",
}

def get_fix(err):
    el=err.lower()
    for k,v in FIXES.items():
        if k in el: return v
    return "Unexpected error.\nReport at: github.com/apelegends/shuben-launcher-os/issues\nInclude a photo of this screen."

def list_disks():
    disks=[]
    try:
        out=subprocess.check_output(["lsblk","-J","-o","NAME,MODEL,SIZE,TYPE,MOUNTPOINT"],text=True)
        data=json.loads(out)
        for d in data.get("blockdevices",[]):
            if d.get("type")!="disk": continue
            try: sb=int(subprocess.check_output(["blockdev","--getsize64",f"/dev/{d['name']}"],text=True).strip())
            except: sb=0
            parts=[{"name":c["name"],"size":c.get("size","?"),"fstype":c.get("fstype","")} for c in d.get("children",[])]
            disks.append({"device":f"/dev/{d['name']}","model":d.get("model") or d["name"],
                          "size":d.get("size","?"),"size_bytes":sb,"partitions":parts})
    except: pass
    return disks

def has_windows(disk):
    try:
        out=subprocess.check_output(["parted",disk["device"],"-s","print"],text=True,stderr=subprocess.DEVNULL)
        return "ntfs" in out.lower() or "microsoft" in out.lower()
    except: return False

def free_gb(disk):
    try:
        total=disk["size_bytes"]; used=0
        for p in disk["partitions"]:
            try: used+=int(subprocess.check_output(["blockdev","--getsize64",f"/dev/{p['name']}"],text=True).strip())
            except: pass
        return (total-used)/(1024**3)
    except: return 0

class Installer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Shuben Launcher OS — Installer")
        self.set_default_size(860,600); self.maximize(); self.set_decorated(False)
        p=Gtk.CssProvider(); p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.mode=None; self.disk=None; self.step_dots=[]
        self.stack=Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self.stack.set_transition_duration(240)
        self.add(self.stack)
        self._welcome(); self._mode_page(); self._disk_page()
        self._confirm_page(); self._installing_page()
        self._done_page(); self._error_page()
        self.stack.set_visible_child_name("welcome")
        self.show_all()

    def go(self,p): self.stack.set_visible_child_name(p)
    def lbl(self,t,css="sub",xa=0,wrap=True):
        l=Gtk.Label(label=t); l.get_style_context().add_class(css)
        l.set_xalign(xa); l.set_line_wrap(wrap); return l
    def btn(self,t,css="btn-p",cb=None):
        b=Gtk.Button(label=t); b.get_style_context().add_class(css)
        if cb: b.connect("clicked",cb)
        return b
    def sw(self,ch,mh=120):
        s=Gtk.ScrolledWindow(); s.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        s.set_min_content_height(mh); s.add(ch); return s
    def add_page(self,name,child,w=720):
        o=Gtk.Box(); o.set_halign(Gtk.Align.CENTER); o.set_valign(Gtk.Align.CENTER)
        child.set_size_request(w,-1); o.pack_start(child,False,False,0)
        self.stack.add_named(o,name)

    # ── Welcome ───────────────────────────────────────────────────────────────
    def _welcome(self):
        c=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20)
        c.get_style_context().add_class("card"); c.set_size_request(580,-1)
        c.pack_start(self.lbl("SHUBEN LAUNCHER OS","logo",0.5),False,False,0)
        c.pack_start(self.lbl("Installer  ·  v1.0","sub",0.5),False,False,0)
        c.pack_start(Gtk.Separator(),False,False,4)
        c.pack_start(self.lbl("Welcome! Install Shuben Launcher OS to your computer.\nChoose a clean install or dual-boot with Windows.","sub",0.5),False,False,0)
        w=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); w.get_style_context().add_class("warn")
        w.pack_start(self.lbl("⚠  Back up your files before continuing!","warn-t"),False,False,0)
        w.pack_start(self.lbl("The installer can wipe your disk.","sub"),False,False,0)
        c.pack_start(w,False,False,0)
        if os.geteuid()!=0:
            eb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); eb.get_style_context().add_class("err-box")
            eb.pack_start(self.lbl("❌  Not running as root!","err-t"),False,False,0)
            eb.pack_start(self.lbl("Open terminal and run:  sudo shuben-installer","err-b"),False,False,0)
            c.pack_start(eb,False,False,0)
            sb=self.btn("Cannot continue — not root","btn-d"); sb.set_sensitive(False)
        else:
            sb=self.btn("Start →",cb=lambda _:self.go("mode"))
        br=Gtk.Box(); br.set_halign(Gtk.Align.CENTER); br.pack_start(sb,False,False,0)
        c.pack_start(br,False,False,0)
        o=Gtk.Box(); o.set_halign(Gtk.Align.CENTER); o.set_valign(Gtk.Align.CENTER)
        o.pack_start(c,False,False,0); self.stack.add_named(o,"welcome")

    # ── Mode ──────────────────────────────────────────────────────────────────
    def _mode_page(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20); vb.set_size_request(740,-1)
        vb.pack_start(self.lbl("How do you want to install?","title"),False,False,0)
        row=Gtk.Box(spacing=16)
        for icon,title,desc,mode,css in [
            ("🗑️","Erase Disk","Wipe the entire disk and install Shuben Launcher OS.\nBest for dedicated gaming PCs or blank drives.\n\n⚠  ALL DATA WILL BE DELETED.","erase","btn-d"),
            ("⚡","Dual Boot","Install alongside Windows.\nBoot either OS from the Shuben menu.\n\nRequires 20+ GB of free space.","dualboot","btn-p"),
        ]:
            card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10); card.get_style_context().add_class("opt")
            card.pack_start(self.lbl(icon,"title",0.5),False,False,0)
            card.pack_start(self.lbl(title,"head",0.5),False,False,0)
            card.pack_start(self.lbl(desc,"sub",0.5),False,False,0)
            b=self.btn(f"Choose {title}",css,cb=lambda _,m=mode:self._on_mode(m))
            card.pack_start(b,False,False,8); row.pack_start(card,True,True,0)
        vb.pack_start(row,False,False,0)
        vb.pack_start(self.btn("← Back","btn-back",cb=lambda _:self.go("welcome")),False,False,0)
        self.add_page("mode",vb,740)

    def _on_mode(self,m): self.mode=m; self._refresh_disks(); self.go("disk")

    # ── Disk ──────────────────────────────────────────────────────────────────
    def _disk_page(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14); vb.set_size_request(760,-1)
        self.disk_title=self.lbl("Select a disk","title"); self.disk_sub=self.lbl("","sub")
        vb.pack_start(self.disk_title,False,False,0); vb.pack_start(self.disk_sub,False,False,0)
        self.disk_lb=Gtk.ListBox(); self.disk_lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.disk_lb.connect("row-selected",self._on_disk_sel)
        vb.pack_start(self.sw(self.disk_lb,220),False,False,0)
        self.disk_wbox=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); self.disk_wbox.get_style_context().add_class("warn")
        self.disk_wlbl=self.lbl("","warn-t"); self.disk_wbox.pack_start(self.disk_wlbl,False,False,0)
        self.disk_wbox.set_visible(False); vb.pack_start(self.disk_wbox,False,False,0)
        br=Gtk.Box(spacing=12)
        br.pack_start(self.btn("← Back","btn-back",cb=lambda _:self.go("mode")),False,False,0)
        br.pack_start(Gtk.Box(),True,True,0)
        br.pack_start(self.btn("Refresh","btn-s",cb=lambda _:self._refresh_disks()),False,False,0)
        self.disk_next=self.btn("Next →",cb=self._on_disk_next); self.disk_next.set_sensitive(False)
        br.pack_start(self.disk_next,False,False,0); vb.pack_start(br,False,False,0)
        self.add_page("disk",vb,760)

    def _refresh_disks(self):
        for r in self.disk_lb.get_children(): self.disk_lb.remove(r)
        self.disk=None; self.disk_next.set_sensitive(False); self.disk_wbox.set_visible(False)
        self.disk_title.set_text("Select disk to erase" if self.mode=="erase" else "Select disk for dual-boot")
        self.disk_sub.set_text("⚠  Entire disk will be wiped." if self.mode=="erase" else "Free space on this disk will be used.")
        disks=list_disks()
        if not disks:
            r=Gtk.ListBoxRow(); r.add(self.lbl("No disks found. Connect a drive and click Refresh.","warn-t"))
            self.disk_lb.add(r); self.disk_lb.show_all(); return
        for d in disks:
            row=Gtk.ListBoxRow(); row.set_data("disk",d)
            box=Gtk.Box(spacing=14); box.get_style_context().add_class("disk-row")
            box.set_margin_top(5); box.set_margin_bottom(5); box.set_margin_start(8); box.set_margin_end(8)
            box.pack_start(self.lbl("💾","head"),False,False,0)
            ib=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3)
            ib.pack_start(self.lbl(f"{d['model']}  ({d['device']})","head"),False,False,0)
            ib.pack_start(self.lbl(f"Size: {d['size']}","sub"),False,False,0)
            if d["partitions"]:
                ib.pack_start(self.lbl("  ".join(f"{p['name']} ({p['size']})" for p in d["partitions"][:4]),"sub"),False,False,0)
            if has_windows(d): ib.pack_start(self.lbl("🪟 Windows detected","info-t"),False,False,0)
            if self.mode=="dualboot":
                fr=free_gb(d)
                col="warn-t" if fr<20 else "fix-t"
                ib.pack_start(self.lbl(f"⚠ Only ~{fr:.1f} GB free — need 20+" if fr<20 else f"✅ ~{fr:.1f} GB free",col),False,False,0)
            box.pack_start(ib,True,True,0); row.add(box); self.disk_lb.add(row)
        self.disk_lb.show_all()

    def _on_disk_sel(self,lb,row):
        if not row: self.disk=None; self.disk_next.set_sensitive(False); return
        d=row.get_data("disk")
        if not d: return
        self.disk=d
        if self.mode=="dualboot" and free_gb(d)<20:
            self.disk_wlbl.set_text(f"⚠ Only ~{free_gb(d):.1f} GB free.\nShrink Windows C: via Disk Management first:\nRight-click C: → Shrink Volume → 20480+ MB")
            self.disk_wbox.set_visible(True); self.disk_next.set_sensitive(False); return
        self.disk_wbox.set_visible(False); self.disk_next.set_sensitive(True)

    def _on_disk_next(self,_):
        if not self.disk: return
        self._refresh_confirm(); self.go("confirm")

    # ── Confirm ───────────────────────────────────────────────────────────────
    def _confirm_page(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16); vb.set_size_request(680,-1)
        vb.pack_start(self.lbl("Confirm installation","title"),False,False,0)
        self.conf_sum=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8); self.conf_sum.get_style_context().add_class("card")
        vb.pack_start(self.conf_sum,False,False,0)
        self.conf_wbox=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); self.conf_wbox.get_style_context().add_class("warn")
        self.conf_wlbl=self.lbl("","warn-t"); self.conf_wbox.pack_start(self.conf_wlbl,False,False,0)
        vb.pack_start(self.conf_wbox,False,False,0)
        self.conf_check=Gtk.CheckButton(label="I understand and want to proceed.")
        self.conf_check.connect("toggled",lambda b:self.conf_btn.set_sensitive(b.get_active()))
        vb.pack_start(self.conf_check,False,False,0)
        br=Gtk.Box(spacing=12)
        br.pack_start(self.btn("← Back","btn-back",cb=lambda _:self.go("disk")),False,False,0)
        br.pack_start(Gtk.Box(),True,True,0)
        self.conf_btn=self.btn("Install now ▶","btn-d",cb=self._on_confirm); self.conf_btn.set_sensitive(False)
        br.pack_start(self.conf_btn,False,False,0); vb.pack_start(br,False,False,0)
        self.add_page("confirm",vb,680)

    def _refresh_confirm(self):
        for ch in self.conf_sum.get_children(): self.conf_sum.remove(ch)
        self.conf_check.set_active(False); self.conf_btn.set_sensitive(False)
        d=self.disk; m=self.mode
        for k,v in [("Mode","🗑️ Erase Disk — FULL WIPE" if m=="erase" else "⚡ Dual Boot"),
                     ("Disk",f"{d['model']}  ({d['device']})"),("Size",d["size"]),("OS","Shuben Launcher OS 1.0"),
                     ("⚠","ALL data deleted!" if m=="erase" else f"~{free_gb(d):.1f} GB free space used")]:
            r=Gtk.Box(spacing=14); kl=self.lbl(k,"head"); kl.set_size_request(80,-1)
            r.pack_start(kl,False,False,0); r.pack_start(self.lbl(v,"warn-t" if k=="⚠" else "sub"),True,True,0)
            self.conf_sum.pack_start(r,False,False,0)
        self.conf_wlbl.set_text("⚠ This will ERASE everything. This cannot be undone." if m=="erase"
                                 else "⚠ Existing partitions will NOT be deleted.")
        self.conf_sum.show_all()

    def _on_confirm(self,_): self.go("installing"); threading.Thread(target=self._install,daemon=True).start()

    # ── Installing ────────────────────────────────────────────────────────────
    def _installing_page(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14); vb.set_size_request(760,-1)
        vb.pack_start(self.lbl("Installing Shuben Launcher OS…","title"),False,False,0)
        vb.pack_start(self.lbl("Do not turn off your computer.","sub"),False,False,0)
        sb=Gtk.Box(spacing=8); sb.set_halign(Gtk.Align.START); self.step_dots=[]
        STEPS=["Partition","Format","Copy","Bootloader","Configure","Finish"]
        for i,s in enumerate(STEPS):
            col=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3); col.set_halign(Gtk.Align.CENTER)
            dot=Gtk.Box(); dot.get_style_context().add_class("dot"); dot.set_size_request(12,12)
            col.pack_start(dot,False,False,0); col.pack_start(self.lbl(s,"sub",0.5),False,False,0)
            sb.pack_start(col,False,False,0); self.step_dots.append(dot)
            if i<len(STEPS)-1: sb.pack_start(self.lbl("──","sub"),False,False,0)
        vb.pack_start(sb,False,False,0)
        self.prog=Gtk.ProgressBar(); self.prog.get_style_context().add_class("prog"); self.prog.set_show_text(True)
        vb.pack_start(self.prog,False,False,0)
        self.act_lbl=self.lbl("","sub"); vb.pack_start(self.act_lbl,False,False,0)
        self.log_buf=Gtk.TextBuffer(); tv=Gtk.TextView(buffer=self.log_buf)
        tv.set_editable(False); tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); tv.get_style_context().add_class("log")
        vb.pack_start(self.sw(tv,200),True,True,0)
        self.add_page("installing",vb,760)

    def _log(self,t): GLib.idle_add(lambda:self.log_buf.insert(self.log_buf.get_end_iter(),t+"\n"))
    def _prog(self,f,t=""):
        def _():
            if f is not None: self.prog.set_fraction(min(f,1.0))
            if t: self.prog.set_text(t); self.act_lbl.set_text(t)
        GLib.idle_add(_)
    def _step(self,idx,state="active"):
        def _():
            for i,d in enumerate(self.step_dots):
                ctx=d.get_style_context()
                for c in ["active","done","error"]: ctx.remove_class(c)
                if i<idx: ctx.add_class("done")
                elif i==idx: ctx.add_class(state)
        GLib.idle_add(_)
    def _cmd(self,cmd,desc="",check=True):
        self._log(f"$ {cmd}")
        if desc: self._prog(None,desc)
        try:
            r=subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
            if r.stdout: self._log(r.stdout.strip())
            if check and r.returncode!=0:
                raise RuntimeError(f"Failed (exit {r.returncode}):\n{cmd}\n\n{r.stdout or '(no output)'}")
            return r.stdout or ""
        except subprocess.TimeoutExpired: raise RuntimeError(f"Timed out:\n{cmd}")

    def _install(self):
        TARGET="/mnt/shuben-install"; disk=self.disk["device"]; mode=self.mode
        EFI=""; ROOT=""
        try:
            os.makedirs(TARGET,exist_ok=True)
            # 0 — Partition
            self._step(0,"active"); self._prog(0.04,"Partitioning…")
            if mode=="erase":
                self._cmd(f"wipefs -a {disk}","Wiping signatures…")
                self._cmd(f"parted -s {disk} mklabel gpt","Creating GPT…")
                self._cmd(f"parted -s {disk} mkpart EFI fat32 1MiB 513MiB","EFI partition…")
                self._cmd(f"parted -s {disk} set 1 esp on")
                self._cmd(f"parted -s {disk} mkpart root ext4 513MiB 100%","Root partition…")
                parts=[p.strip() for p in self._cmd(f"lsblk -ln -o NAME {disk}",check=False).strip().split("\n")
                       if p.strip() and p.strip()!=disk.split("/")[-1]]
                if len(parts)<2: raise RuntimeError("Could not find new partitions.\nCheck: sudo parted "+disk+" print")
                EFI=f"/dev/{parts[0]}"; ROOT=f"/dev/{parts[1]}"
            else:
                out=self._cmd(f"parted -s {disk} unit MiB print free","Scanning free space…",check=False)
                regions=[]
                for line in out.split("\n"):
                    if "Free Space" in line:
                        pts=line.split()
                        try:
                            start=pts[0].replace("MiB",""); end=pts[1].replace("MiB","")
                            sz=float(pts[2].replace("MiB",""))
                            if sz>=20*1024: regions.append((start,end,sz))
                        except: pass
                if not regions:
                    raise RuntimeError("No free region of 20+ GB found.\nFix:\n• Boot Windows\n• Disk Management → right-click C: → Shrink Volume → 20480+ MB\n• Reboot installer")
                start,end,_=regions[0]
                efi_check=self._cmd(f"parted -s {disk} print|grep -i 'esp\\|efi'",check=False)
                if not efi_check.strip():
                    es=str(int(start)+512)
                    self._cmd(f"parted -s {disk} mkpart EFI fat32 {start}MiB {es}MiB","Creating EFI…")
                    self._cmd(f"parted -s {disk} set 1 esp on"); start=es
                for line in self._cmd(f"lsblk -ln -o NAME,PARTLABEL {disk}",check=False).split("\n"):
                    if "EFI" in line.upper():
                        EFI=f"/dev/{line.split()[0]}"; break
                self._cmd(f"parted -s {disk} mkpart shuben ext4 {start}MiB {end}","Root partition…")
                parts=[p.strip() for p in self._cmd(f"lsblk -ln -o NAME {disk}",check=False).strip().split("\n")
                       if p.strip() and p.strip()!=disk.split("/")[-1]]
                ROOT=f"/dev/{parts[-1]}"
            self._log(f"EFI={EFI}  ROOT={ROOT}"); self._step(0,"done")
            # 1 — Format
            self._step(1,"active"); self._prog(0.14,"Formatting…")
            if EFI: self._cmd(f"mkfs.fat -F32 {EFI}","Formatting EFI…")
            self._cmd(f"mkfs.ext4 -F -L 'ShubenOS' {ROOT}","Formatting root…"); self._step(1,"done")
            # 2 — Copy
            self._step(2,"active"); self._prog(0.22,"Mounting…")
            self._cmd(f"mount {ROOT} {TARGET}","Mounting root…")
            if EFI:
                os.makedirs(f"{TARGET}/boot/efi",exist_ok=True)
                self._cmd(f"mount {EFI} {TARGET}/boot/efi","Mounting EFI…")
            self._prog(0.28,"Copying system (this takes a while)…")
            sq="/run/live/medium/casper/filesystem.squashfs"
            sq2="/run/live/medium/live/filesystem.squashfs"
            if os.path.exists(sq): self._cmd(f"unsquashfs -f -d {TARGET} {sq}","Extracting…")
            elif os.path.exists(sq2): self._cmd(f"unsquashfs -f -d {TARGET} {sq2}","Extracting…")
            else:
                exc=" ".join(f"--exclude={x}" for x in ["/proc/*","/sys/*","/dev/*","/run/*","/mnt/*","/media/*","/tmp/*","/lost+found"])
                self._cmd(f"rsync -aAX {exc} / {TARGET}/","Copying files via rsync…")
            self._prog(0.62,"Files copied."); self._step(2,"done")
            # 3 — Bootloader
            self._step(3,"active"); self._prog(0.65,"Installing bootloader…")
            for b in ["dev","proc","sys","run"]:
                os.makedirs(f"{TARGET}/{b}",exist_ok=True)
                self._cmd(f"mount --bind /{b} {TARGET}/{b}")
            self._cmd(f"chroot {TARGET} grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id='Shuben Launcher OS' --recheck {disk}","Installing GRUB…")
            ruuid=self._cmd(f"blkid -s UUID -o value {ROOT}").strip()
            grub=f"""set default=0
set timeout=8
set gfxmode=1920x1080,auto
loadfont /boot/grub/fonts/unicode.pf2
terminal_output gfxterm
set color_normal=white/black
set color_highlight=black/cyan

menuentry "▶  Shuben Launcher OS" {{
  linux  /vmlinuz root=UUID={ruuid} ro quiet splash
  initrd /initrd.img
}}
menuentry "🔧  Shuben (Safe Graphics)" {{
  linux  /vmlinuz root=UUID={ruuid} ro nomodeset quiet splash
  initrd /initrd.img
}}
menuentry "🛠  Boot from first hard drive" {{ set root=(hd0); chainloader +1 }}
menuentry "⚙  UEFI Firmware Settings" {{ fwsetup }}
"""
            with open(f"{TARGET}/boot/grub/grub.cfg","w") as f: f.write(grub)
            self._cmd(f"chroot {TARGET} update-grub","Updating GRUB…",check=False)
            self._step(3,"done")
            # 4 — Configure
            self._step(4,"active"); self._prog(0.80,"Configuring…")
            euuid=self._cmd(f"blkid -s UUID -o value {EFI}").strip() if EFI else ""
            fstab=f"UUID={ruuid}  /          ext4  errors=remount-ro  0  1\n"
            if euuid: fstab+=f"UUID={euuid}   /boot/efi  vfat  umask=0077  0  1\n"
            fstab+="tmpfs  /tmp  tmpfs  defaults  0  0\n"
            with open(f"{TARGET}/etc/fstab","w") as f: f.write(fstab)
            with open(f"{TARGET}/etc/hostname","w") as f: f.write("shuben-launcher\n")
            for path in [f"{TARGET}/var/lib/shuben/oobe-state.json",f"{TARGET}/var/lib/shuben/.mc-launched"]:
                try: os.remove(path)
                except: pass
            self._step(4,"done")
            # 5 — Finish
            self._step(5,"active"); self._prog(0.92,"Cleaning up…")
            for b in ["run","sys","proc","dev"]: self._cmd(f"umount -l {TARGET}/{b}",check=False)
            if EFI: self._cmd(f"umount {TARGET}/boot/efi",check=False)
            self._cmd(f"umount {TARGET}",check=False)
            self._step(5,"done"); self._prog(1.0,"Installation complete! ✅")
            self._log("\n✅ Shuben Launcher OS installed successfully!")
            GLib.timeout_add(1200,lambda:self.go("done") or False)
        except Exception as e:
            err=str(e); GLib.idle_add(self._show_error,err,get_fix(err))

    # ── Error ─────────────────────────────────────────────────────────────────
    def _error_page(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14); vb.set_size_request(720,-1)
        vb.pack_start(self.lbl("❌  Installation failed","title"),False,False,0)
        vb.pack_start(self.lbl("Read the fix below before retrying.","sub"),False,False,0)
        eb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); eb.get_style_context().add_class("err-box")
        self.err_t=self.lbl("Error","err-t"); self.err_b=self.lbl("","err-b"); self.err_b.set_selectable(True)
        eb.pack_start(self.err_t,False,False,0); eb.pack_start(self.err_b,False,False,0)
        vb.pack_start(self.sw(eb,110),False,False,0)
        fb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); fb.get_style_context().add_class("fix")
        fb.pack_start(self.lbl("🔧  How to fix this","fix-t"),False,False,0)
        self.fix_b=self.lbl("","fix-b"); self.fix_b.set_selectable(True)
        fb.pack_start(self.fix_b,False,False,0); vb.pack_start(fb,False,False,0)
        ib=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4); ib.get_style_context().add_class("info")
        ib.pack_start(self.lbl("Still stuck? Report at:","info-t"),False,False,0)
        ib.pack_start(self.lbl("github.com/apelegends/shuben-launcher-os/issues","sub"),False,False,0)
        vb.pack_start(ib,False,False,0)
        br=Gtk.Box(spacing=12)
        br.pack_start(self.btn("← Try again",cb=lambda _:self.go("mode")),False,False,0)
        br.pack_start(self.btn("Open terminal","btn-s",cb=lambda _:subprocess.Popen(["lxterminal"])),False,False,0)
        vb.pack_start(br,False,False,0); self.add_page("error",vb,720)

    def _show_error(self,err,fix):
        for d in self.step_dots:
            ctx=d.get_style_context()
            if "active" in ctx.list_classes():
                ctx.remove_class("active"); ctx.add_class("error"); break
        self.err_b.set_text(err); self.fix_b.set_text(fix); self.go("error")

    # ── Done ──────────────────────────────────────────────────────────────────
    def _done_page(self):
        vb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20); vb.set_size_request(560,-1)
        vb.pack_start(self.lbl("✅  Installation complete!","ok",0.5),False,False,0)
        vb.pack_start(self.lbl("Remove the USB drive, then reboot.","sub",0.5),False,False,0)
        ib=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); ib.get_style_context().add_class("info")
        ib.pack_start(self.lbl("What happens next:","info-t"),False,False,0)
        ib.pack_start(self.lbl("1. Remove the USB\n2. Reboot — Shuben boot menu appears\n3. Select Shuben Launcher OS\n4. Setup wizard runs\n5. Set your PIN — done!","sub"),False,False,0)
        vb.pack_start(ib,False,False,0)
        self.cd_lbl=self.lbl("","sub",0.5); vb.pack_start(self.cd_lbl,False,False,0)
        br=Gtk.Box(spacing=12); br.set_halign(Gtk.Align.CENTER)
        br.pack_start(self.btn("🔄  Reboot now",cb=lambda _:subprocess.Popen(["systemctl","reboot"])),False,False,0)
        br.pack_start(self.btn("Stay in live session","btn-s",cb=lambda _:self.destroy()),False,False,0)
        vb.pack_start(br,False,False,0); self.add_page("done",vb,560)
        self.stack.connect("notify::visible-child",self._on_stack)
    def _on_stack(self,s,_):
        if s.get_visible_child_name()=="done": self._cd=60; GLib.timeout_add(1000,self._tick)
    def _tick(self):
        self._cd-=1; self.cd_lbl.set_text(f"Auto-rebooting in {self._cd}s…")
        if self._cd<=0: subprocess.Popen(["systemctl","reboot"]); return False
        return True

def main():
    if os.geteuid()!=0:
        try: os.execvp("pkexec",["pkexec",sys.executable]+sys.argv)
        except: pass
    win=Installer(); win.connect("destroy",Gtk.main_quit); Gtk.main()

if __name__=="__main__": main()
