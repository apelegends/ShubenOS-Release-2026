#!/usr/bin/env python3
"""Shuben Launcher OS — PIN Lock Screen"""
import gi, os, json, hashlib, subprocess
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, Gdk, GLib

A="#00A8E8"; D="#0D1117"; W="#FFFFFF"; G="#8B949E"; R="#F85149"; GR="#3FB950"
CSS=f"""
*{{font-family:'Segoe UI','Liberation Sans',sans-serif;}}
window{{background:{D};}}
.name{{color:{W};font-size:20px;font-weight:700;}}
.email{{color:{G};font-size:12px;}}
.time{{color:{W};font-size:60px;font-weight:300;}}
.date{{color:{G};font-size:15px;}}
.hint{{color:{G};font-size:13px;}}
.pin-box{{background:rgba(255,255,255,0.08);color:{W};border:1px solid rgba(255,255,255,0.15);
  border-radius:8px;font-size:26px;font-weight:700;min-width:58px;min-height:66px;}}
.pin-box:focus{{border-color:{A};}}
.err{{color:{R};font-size:13px;}}
.unlock{{background:{A};color:{W};border:none;border-radius:6px;padding:12px 32px;font-size:14px;font-weight:600;}}
.card{{background:rgba(13,17,23,0.92);border-radius:16px;padding:40px 48px;border:1px solid rgba(255,255,255,0.08);}}
"""
PIN_F="/var/lib/shuben/pin.json"
ACCT_F="/var/lib/shuben/accounts.json"

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def load_pin():
    try: return json.loads(open(PIN_F).read()).get("pin_hash","")
    except: return ""
def load_acct():
    try: return json.loads(open(ACCT_F).read()).get("primary",{})
    except: return {}

class PinLock(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.fullscreen(); self.set_decorated(False); self.set_keep_above(True)
        p=Gtk.CssProvider(); p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.pin_hash=load_pin(); self.acct=load_acct(); self.attempts=0
        overlay=Gtk.Overlay(); self.add(overlay)
        # Clock
        clk=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        clk.set_margin_top(48); clk.set_margin_start(64)
        clk.set_valign(Gtk.Align.START); clk.set_halign(Gtk.Align.START)
        self.time_lbl=Gtk.Label(); self.time_lbl.get_style_context().add_class("time")
        self.date_lbl=Gtk.Label(); self.date_lbl.get_style_context().add_class("date")
        clk.pack_start(self.time_lbl,False,False,0); clk.pack_start(self.date_lbl,False,False,0)
        overlay.add_overlay(clk)
        # Card
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18)
        card.get_style_context().add_class("card")
        card.set_halign(Gtk.Align.CENTER); card.set_valign(Gtk.Align.CENTER)
        name=self.acct.get("display_name") or (self.acct.get("email","").split("@")[0]) or "User"
        email=self.acct.get("email","")
        av=Gtk.Label(); av.set_markup('<span font="44">🎮</span>')
        nl=Gtk.Label(label=name); nl.get_style_context().add_class("name")
        card.pack_start(av,False,False,0); card.pack_start(nl,False,False,0)
        if email:
            el=Gtk.Label(label=email); el.get_style_context().add_class("email"); card.pack_start(el,False,False,0)
        hint=Gtk.Label(label="Enter your PIN to continue"); hint.get_style_context().add_class("hint")
        card.pack_start(hint,False,False,0)
        # PIN digits
        row=Gtk.Box(spacing=12); row.set_halign(Gtk.Align.CENTER); self.pins=[]
        for i in range(4):
            e=Gtk.Entry(); e.set_max_length(1); e.set_input_purpose(Gtk.InputPurpose.DIGITS)
            e.set_visibility(False); e.set_invisible_char("●")
            e.get_style_context().add_class("pin-box"); e.set_width_chars(2)
            ni=i+1
            def ch(w,nl=ni):
                t=w.get_text()
                if t and not t.isdigit(): w.set_text(""); return
                if t and nl<4: self.pins[nl].grab_focus()
                elif t and nl==4: self._submit()
            e.connect("changed",ch); self.pins.append(e); row.pack_start(e,False,False,0)
        card.pack_start(row,False,False,0)
        self.err=Gtk.Label(label=""); self.err.get_style_context().add_class("err"); card.pack_start(self.err,False,False,0)
        ub=Gtk.Button(label="Unlock →"); ub.get_style_context().add_class("unlock"); ub.connect("clicked",lambda _:self._submit())
        card.pack_start(ub,False,False,0)
        overlay.add(card); self.show_all()
        self._update_clock(); GLib.timeout_add(10000,self._update_clock)
        GLib.idle_add(self.pins[0].grab_focus)

    def _update_clock(self):
        from datetime import datetime
        n=datetime.now()
        self.time_lbl.set_text(n.strftime("%H:%M"))
        self.date_lbl.set_text(n.strftime("%A, %B %d"))
        return True

    def _submit(self):
        pin="".join(e.get_text() for e in self.pins)
        if len(pin)!=4: self.err.set_text("Enter all 4 digits."); return
        if sha(pin)==self.pin_hash:
            self.destroy(); Gtk.main_quit()
        else:
            self.attempts+=1
            for e in self.pins: e.set_text("")
            self.pins[0].grab_focus()
            self.err.set_text(f"❌ Incorrect PIN ({self.attempts} attempt{'s' if self.attempts>1 else ''}).")

def main():
    win=PinLock(); win.connect("destroy",Gtk.main_quit); Gtk.main()
if __name__=="__main__": main()
