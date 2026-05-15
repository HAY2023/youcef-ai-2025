"""
╔══════════════════════════════════════════════════════════════╗
║   Nabtakir — RACE TIMER PRO  v6.2 (Stable Edition)         ║
║   بُني على طلب المستخدم: الحساس 1 يبدأ، والحساس 2 ينهي     ║
╚══════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading, time, csv, os, sys, winsound, json, urllib.request, webbrowser
from datetime import datetime
from PIL import Image, ImageTk

try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

APP_VERSION    = "6.2"

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# كود الأردوينو المدمج (المستقر والمنطقي)
ARDUINO_CODE_EMBEDDED = """
// RACE TIMER ARDUINO CODE v6.2 (STABLE)
#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5
#define DETECT_CM 30
#define DEBOUNCE 300

unsigned long start_ms = 0;
bool racing = false;
bool armed = false;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG1, OUTPUT); pinMode(ECHO1, INPUT);
  pinMode(TRIG2, OUTPUT); pinMode(ECHO2, INPUT);
  Serial.println("READY");
}

long readCM(int tr, int ec) {
  digitalWrite(tr, LOW); delayMicroseconds(2);
  digitalWrite(tr, HIGH); delayMicroseconds(10);
  digitalWrite(tr, LOW);
  long dur = pulseIn(ec, HIGH, 20000);
  return (dur <= 0) ? -1 : dur * 0.034 / 2;
}

void loop() {
  if(Serial.available()){
    String cmd = Serial.readStringUntil('\\n');
    cmd.trim();
    if(cmd == "ARM")   { armed = true; racing = false; Serial.println("ARMED_OK"); }
    if(cmd == "RESET") { armed = false; racing = false; Serial.println("RESET_OK"); }
  }

  if(armed && !racing){
    long d1 = readCM(TRIG1, ECHO1);
    if(d1 > 0 && d1 < DETECT_CM){
       start_ms = millis();
       racing = true;
       Serial.println("START");
       delay(DEBOUNCE);
    }
  }

  if(racing){
    long d2 = readCM(TRIG2, ECHO2);
    if(d2 > 0 && d2 < DETECT_CM){
       unsigned long total = millis() - start_ms;
       Serial.print("TIME:"); Serial.println(total);
       racing = false;
       armed = false;
       delay(DEBOUNCE);
    }
  }
}
"""

# ═══════════════════════════════════════════════
#  الألوان
# ═══════════════════════════════════════════════
THEMES = {
    "dark": {
        "bg":"#05070A","panel":"#0A0F16","card":"#111823","card2":"#18222F",
        "border":"#1E293B","accent":"#00D1FF","green":"#00FF85","green2":"#00B35D",
        "red":"#FF3A3A","amber":"#FFB020","purple":"#9066FF","muted":"#4A5568",
        "gold":"#FFD700","text":"#F1F5F9",
        "racer_colors":["#00D1FF","#00FF85","#9066FF","#FFB020","#FF3A3A","#06C8D8"]
    }
}
C = THEMES["dark"].copy()

def L(key, lang="ar", **kw):
    strs = {
        "ar": {
            "title": "نبتكر - Nabtakir", "conn_on": "متصل", "conn_off": "غير متصل",
            "setup_title": "إعداد المتسابقين", "port_title": "لوحة التحكم بالمتحكم",
            "start_race": "ابدأ السباق", "add": "إضافة +", "back": "رجوع",
            "manual_start": "بدء يدوي", "manual_stop": "إنهاء يدوي",
            "results": "النتائج النهائية", "winner": "🏆 الفائز: {name}",
            "export": "تصدير CSV", "arduino_btn": "كود المتحكم (Offline)",
            "sensor1": "حساس البداية", "sensor2": "حساس النهاية",
            "waiting": "بانتظار...", "detected": "تم الكشف!"
        }
    }
    t = strs.get("ar").get(key, key)
    return t.format(**kw) if kw else t

def fmt(ms:int)->str:
    return f"{ms//60000:02d}:{(ms%60000)//1000:02d}.{ms%1000:03d}"

# ═══════════════════════════════════════════════
class App:
    def __init__(self, root:tk.Tk):
        self.root = root
        self.lang = "ar"
        self.icon_path = resource_path("icon.ico")
        try:
            if os.path.exists(self.icon_path): self.root.iconbitmap(self.icon_path)
        except: pass

        self.root.title(L("title"))
        self.root.configure(bg=C["bg"])
        self.root.state("zoomed")
        
        self.ser = None
        self.connected = False
        self.racers = []
        self.curr = 0
        self.racing = False
        self.armed = False
        self.t0 = 0
        
        self._topbar()
        self.frame = tk.Frame(self.root, bg=C["bg"])
        self.frame.pack(fill="both", expand=True)
        self._page_port()

    def _topbar(self):
        self.top = tk.Frame(self.root, bg=C["panel"], height=60)
        self.top.pack(fill="x")
        tk.Label(self.top, text=f" ⏱ {L('title')}", font=("Segoe UI", 18, "bold"), bg=C["panel"], fg=C["accent"]).pack(side="left", padx=20)
        self.lbl_conn = tk.Label(self.top, text=L("conn_off"), fg=C["red"], bg=C["panel"], font=("Segoe UI", 10, "bold"))
        self.lbl_conn.pack(side="right", padx=20)

    def _clear(self):
        for w in self.frame.winfo_children(): w.destroy()

    def _page_port(self):
        self._clear()
        c = tk.Frame(self.frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        c.place(relx=0.5, rely=0.4, anchor="center", ipadx=50, ipady=40)
        tk.Label(c, text=L("port_title"), font=("Segoe UI", 22, "bold"), bg=C["card"], fg=C["text"]).pack(pady=(0, 20))
        self.cmb = ttk.Combobox(c, width=20, font=("Segoe UI", 12))
        self.cmb.pack(pady=10)
        self._refresh_ports()
        tk.Button(c, text=L("conn_on"), command=self._connect, bg=C["accent"], fg=C["bg"], font=("Segoe UI", 12, "bold"), padx=40, pady=10, relief="flat").pack(pady=20)
        tk.Button(c, text=L("arduino_btn"), command=self._save_arduino, bg=C["card2"], fg=C["green"], relief="flat").pack()

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()] if SERIAL_OK else ["COM1"]
        self.cmb["values"] = ports
        if ports: self.cmb.current(0)

    def _connect(self):
        port = self.cmb.get()
        try:
            if SERIAL_OK:
                self.ser = serial.Serial(port, 9600, timeout=0.1)
                self.connected = True
                self.lbl_conn.config(text=f"{L('conn_on')}: {port}", fg=C["green"])
                threading.Thread(target=self._serial_loop, daemon=True).start()
            self._page_setup()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _save_arduino(self):
        p = os.path.join(os.path.expanduser("~"), "Desktop", "RaceTimer_Stable.ino")
        with open(p, "w", encoding="utf-8") as f: f.write(ARDUINO_CODE_EMBEDDED)
        messagebox.showinfo("Done", f"Saved to Desktop: {p}")

    def _page_setup(self):
        self._clear()
        main = tk.Frame(self.frame, bg=C["bg"], padx=60, pady=40)
        main.pack(fill="both", expand=True)
        tk.Label(main, text=L("setup_title"), font=("Segoe UI", 26, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w")
        
        self.ent = tk.Entry(main, font=("Segoe UI", 16), bg=C["card2"], fg=C["text"])
        self.ent.pack(fill="x", pady=20)
        tk.Button(main, text=L("add"), command=self._add_racer, bg=C["green2"], fg="white", padx=20).pack()
        
        self.list_f = tk.Frame(main, bg=C["bg"])
        self.list_f.pack(fill="both", expand=True, pady=20)
        tk.Button(main, text=L("start_race"), command=self._start_race_ui, bg=C["accent"], font=("Segoe UI", 14, "bold")).pack(side="right")

    def _add_racer(self):
        n = self.ent.get().strip()
        if n: self.racers.append({"name": n, "ms": None}); self.ent.delete(0, "end"); self._render_racers()

    def _render_racers(self):
        for w in self.list_f.winfo_children(): w.destroy()
        for i, r in enumerate(self.racers):
            tk.Label(self.list_f, text=f"{i+1}. {r['name']}", bg=C["bg"], fg=C["text"], font=("Segoe UI", 12)).pack(anchor="w")

    def _start_race_ui(self):
        if not self.racers: return
        self._clear()
        self.curr = 0
        main = tk.Frame(self.frame, bg=C["bg"], padx=50)
        main.pack(fill="both", expand=True)
        self.lbl_rname = tk.Label(main, text="", font=("Segoe UI", 42, "bold"), bg=C["bg"])
        self.lbl_rname.pack()
        self.lbl_timer = tk.Label(main, text="00:00.000", font=("Consolas", 80, "bold"), bg=C["bg"], fg=C["text"])
        self.lbl_timer.pack(pady=30)
        
        self.s1_ui = tk.Label(main, text=L("sensor1"), fg=C["muted"], bg=C["bg"])
        self.s1_ui.pack()
        self.s2_ui = tk.Label(main, text=L("sensor2"), fg=C["muted"], bg=C["bg"])
        self.s2_ui.pack()
        
        self._activate_racer(0)

    def _activate_racer(self, i):
        if i >= len(self.racers): self._page_results(); return
        self.curr = i
        self.racing = False
        self.lbl_rname.config(text=self.racers[i]["name"])
        self.lbl_timer.config(text="00:00.000", fg=C["text"])
        self.s1_ui.config(fg=C["muted"]); self.s2_ui.config(fg=C["muted"])
        if self.connected: self._send("ARM")

    def _on_start(self):
        self.racing = True; self.t0 = time.perf_counter()
        self.s1_ui.config(fg=C["green"]); self._tick()

    def _tick(self):
        if not self.racing: return
        el = int((time.perf_counter() - self.t0) * 1000)
        self.lbl_timer.config(text=fmt(el))
        self.root.after(30, self._tick)

    def _on_stop(self, ms):
        self.racing = False; self.racers[self.curr]["ms"] = ms
        self.s2_ui.config(fg=C["accent"]); self.lbl_timer.config(text=fmt(ms))
        self.root.after(2000, lambda: self._activate_racer(self.curr + 1))

    def _serial_loop(self):
        while self.connected and self.ser:
            try:
                line = self.ser.readline().decode().strip()
                if line == "START": self.root.after(0, self._on_start)
                elif line.startswith("TIME:"):
                    ms = int(line.split(":")[1]); self.root.after(0, lambda m=ms: self._on_stop(m))
            except: break

    def _send(self, cmd):
        if self.ser: self.ser.write(f"{cmd}\n".encode())

    def _page_results(self):
        self._clear()
        tk.Label(self.frame, text=L("results"), font=("Segoe UI", 24), bg=C["bg"], fg=C["text"]).pack(pady=20)
        for r in sorted([r for r in self.racers if r["ms"]], key=lambda x: x["ms"]):
            tk.Label(self.frame, text=f"{r['name']}: {fmt(r['ms'])}", bg=C["bg"], fg=C["green"], font=("Consolas", 16)).pack()

if __name__ == "__main__":
    root = tk.Tk(); App(root); root.mainloop()
