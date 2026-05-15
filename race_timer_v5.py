"""
╔══════════════════════════════════════════════════════════════╗
║   Nabtakir — RACE TIMER PRO  v6.0 (Controller Edition)      ║
║   بُني على أحدث معايير واجهات المستخدم وتجربة السباق       ║
║   المميزات: لوحة تحكم متكاملة، كود مدمج، استقرار عالي     ║
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

APP_VERSION    = "6.0"
# كود الأردوينو المدمج (للحفظ اليدوي)
ARDUINO_CODE_EMBEDDED = """
// RACE TIMER ARDUINO CODE v6.0
#define TRIG1 2
#define ECHO1 3
#define TRIG2 4
#define ECHO2 5
#define DETECT_CM 25
#define DEBOUNCE 400

long lastTime = 0;
bool armed = false;
unsigned long start_ms = 0;

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
  return (dur == 0) ? -1 : dur * 0.034 / 2;
}

void loop() {
  if(Serial.available()){
    String cmd = Serial.readStringUntil('\\n');
    cmd.trim();
    if(cmd == "ARM") { armed = true; Serial.println("ARMED_OK"); }
    if(cmd == "RESET") { armed = false; Serial.println("RESET_OK"); }
  }

  if(armed){
    long d1 = readCM(TRIG1, ECHO1);
    if(d1 > 0 && d1 < DETECT_CM && millis()-lastTime > DEBOUNCE){
       start_ms = millis();
       lastTime = millis();
       Serial.println("START");
       armed = false; // Stop checking start sensor
       while(true){ // Wait for end sensor
          long d2 = readCM(TRIG2, ECHO2);
          if(d2 > 0 && d2 < DETECT_CM && millis()-lastTime > DEBOUNCE){
             unsigned long total = millis() - start_ms;
             Serial.print("TIME:"); Serial.println(total);
             lastTime = millis();
             break;
          }
          if(Serial.available()) break; // Exit if new command
       }
    }
  }
}
"""

# ═══════════════════════════════════════════════
#  الألوان (Legendary Dark & Light)
# ═══════════════════════════════════════════════
THEMES = {
    "dark": {
        "bg":"#05070A","panel":"#0A0F16","card":"#111823","card2":"#18222F",
        "border":"#1E293B","accent":"#00D1FF","green":"#00FF85","green2":"#00B35D",
        "red":"#FF3A3A","amber":"#FFB020","purple":"#9066FF","muted":"#4A5568",
        "gold":"#FFD700","text":"#F1F5F9",
        "racer_colors":["#00D1FF","#00FF85","#9066FF","#FFB020","#FF3A3A","#06C8D8"]
    },
    "light": {
        "bg":"#F8FAFC","panel":"#F1F5F9","card":"#FFFFFF","card2":"#F1F5F9",
        "border":"#E2E8F0","accent":"#0284C7","green":"#16A34A","green2":"#15803D",
        "red":"#DC2626","amber":"#D97706","purple":"#7C3AED","muted":"#64748B",
        "gold":"#D97706","text":"#0F172A",
        "racer_colors":["#0284C7","#16A34A","#7C3AED","#D97706","#DC2626","#0891B2"]
    }
}

STRINGS = {
    "ar": {
        "title": "نبتكر - Nabtakir", "conn_on": "متصل", "conn_off": "غير متصل",
        "setup_title": "إعداد المتسابقين", "port_title": "لوحة التحكم بالمتحكم",
        "start_race": "ابدأ السباق", "add": "إضافة +", "back": "رجوع",
        "manual_start": "بدء يدوي", "manual_stop": "إنهاء يدوي",
        "results": "النتائج النهائية", "winner": "🏆 الفائز: {name}",
        "export": "تصدير CSV", "arduino_btn": "كود المتحكم (Offline)",
        "sensor1": "حساس البداية", "sensor2": "حساس النهاية",
        "waiting": "بانتظار...", "detected": "تم الكشف!", "running": "يعدو الآن"
    },
    "en": {
        "title": "Nabtakir - Timer", "conn_on": "Connected", "conn_off": "Disconnected",
        "setup_title": "Racer Setup", "port_title": "Controller Hub",
        "start_race": "Start Race", "add": "Add +", "back": "Back",
        "manual_start": "Manual Start", "manual_stop": "Manual Stop",
        "results": "Final Results", "winner": "🏆 Winner: {name}",
        "export": "Export CSV", "arduino_btn": "Arduino Code (Offline)",
        "sensor1": "Start Sensor", "sensor2": "Finish Sensor",
        "waiting": "Waiting...", "detected": "Detected!", "running": "Running"
    }
}

C = THEMES["dark"].copy()

def L(key, lang="ar", **kw):
    t = STRINGS.get(lang, STRINGS["ar"]).get(key, key)
    return t.format(**kw) if kw else t

def fmt(ms:int)->str:
    return f"{ms//60000:02d}:{(ms%60000)//1000:02d}.{ms%1000:03d}"

# ═══════════════════════════════════════════════
class App:
    def __init__(self, root:tk.Tk):
        self.root = root
        self._load_settings()
        self.lang = self.settings.get("lang", "ar")
        self.is_dark = self.settings.get("theme", "dark") == "dark"
        self._update_colors()
        
        self.root.title(L("title", self.lang))
        self.root.configure(bg=C["bg"])
        self.root.state("zoomed")
        
        # الحالة
        self.ser = None
        self.connected = False
        self.racers = []
        self.curr = 0
        self.racing = False
        self.armed = False
        self.t0 = 0
        self.tick_id = None
        
        self._topbar()
        self._statusbar()
        self.frame = tk.Frame(self.root, bg=C["bg"])
        self.frame.pack(fill="both", expand=True)
        
        self._page_port()
        self._auto_reconnect_loop()

    def _load_settings(self):
        p = os.path.join(os.getenv("LOCALAPPDATA", "."), "NabtakirV6")
        os.makedirs(p, exist_ok=True)
        self.set_file = os.path.join(p, "settings.json")
        self.settings = {"theme":"dark", "lang":"ar", "port":"", "baud":"9600"}
        if os.path.exists(self.set_file):
            try:
                with open(self.set_file, "r") as f: self.settings.update(json.load(f))
            except: pass

    def _save_settings(self):
        with open(self.set_file, "w") as f: json.dump(self.settings, f)

    def _update_colors(self):
        global C
        C = THEMES["dark" if self.is_dark else "light"].copy()

    def _topbar(self):
        self.top = tk.Frame(self.root, bg=C["panel"], height=60)
        self.top.pack(fill="x")
        tk.Label(self.top, text=f" ⏱ {L('title', self.lang)}", font=("Segoe UI", 18, "bold"), bg=C["panel"], fg=C["accent"]).pack(side="left", padx=20)
        
        self.btn_lang = tk.Button(self.top, text="EN/AR", command=self._toggle_lang, bg=C["card"], fg=C["text"], relief="flat", padx=10)
        self.btn_lang.pack(side="right", padx=10, pady=15)
        
        self.lbl_conn = tk.Label(self.top, text=L("conn_off", self.lang), fg=C["red"], bg=C["panel"], font=("Segoe UI", 10, "bold"))
        self.lbl_conn.pack(side="right", padx=20)

    def _statusbar(self):
        self.bot = tk.Frame(self.root, bg=C["panel"], height=30)
        self.bot.pack(fill="x", side="bottom")
        self.sb_var = tk.StringVar(value="Ready")
        tk.Label(self.bot, textvariable=self.sb_var, bg=C["panel"], fg=C["muted"], font=("Segoe UI", 9)).pack(side="left", padx=15)

    def _clear(self):
        for w in self.frame.winfo_children(): w.destroy()

    # ─── شاشة الاتصال ───────────────────────────
    def _page_port(self):
        self._clear()
        self.curr_page = "port"
        
        c = tk.Frame(self.frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        c.place(relx=0.5, rely=0.4, anchor="center", ipadx=50, ipady=40)
        
        tk.Label(c, text=L("port_title", self.lang), font=("Segoe UI", 22, "bold"), bg=C["card"], fg=C["text"]).pack(pady=(0, 20))
        
        row = tk.Frame(c, bg=C["card"])
        row.pack()
        self.cmb = ttk.Combobox(row, width=15, font=("Segoe UI", 12))
        self.cmb.pack(side="left", padx=10)
        tk.Button(row, text="↻", command=self._refresh_ports, bg=C["card2"], fg=C["text"], relief="flat").pack(side="left")
        
        tk.Button(c, text=L("conn_on", self.lang), command=self._connect, bg=C["accent"], fg=C["bg"], font=("Segoe UI", 12, "bold"), padx=40, pady=10, relief="flat").pack(pady=30)
        
        tk.Button(c, text=L("arduino_btn", self.lang), command=self._save_arduino_offline, bg=C["card2"], fg=C["green"], font=("Segoe UI", 9), relief="flat").pack()
        
        tk.Button(c, text=L("demo", self.lang if self.lang=="en" else "ar"), command=self._demo_mode, bg=C["bg"], fg=C["muted"], relief="flat").pack(pady=(15, 0))
        
        self._refresh_ports()

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()] if SERIAL_OK else ["COM1", "COM2"]
        self.cmb["values"] = ports
        if ports: self.cmb.current(0)

    def _connect(self):
        port = self.cmb.get()
        if not port: return
        try:
            if SERIAL_OK:
                self.ser = serial.Serial(port, 9600, timeout=0.1)
                self.connected = True
                self.lbl_conn.config(text=f"{L('conn_on', self.lang)}: {port}", fg=C["green"])
                threading.Thread(target=self._serial_loop, daemon=True).start()
            self._page_setup()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _demo_mode(self):
        self.connected = False
        self.lbl_conn.config(text="Demo Mode", fg=C["amber"])
        self._page_setup()

    def _save_arduino_offline(self):
        p = os.path.join(os.path.expanduser("~"), "Desktop", "Nabtakir_Controller.ino")
        with open(p, "w", encoding="utf-8") as f: f.write(ARDUINO_CODE_EMBEDDED)
        messagebox.showinfo("Success", f"Saved to Desktop:\n{p}")

    # ─── شاشة الإعداد ───────────────────────────
    def _page_setup(self):
        self._clear()
        self.curr_page = "setup"
        
        main = tk.Frame(self.frame, bg=C["bg"], padx=60, pady=40)
        main.pack(fill="both", expand=True)
        
        tk.Label(main, text=L("setup_title", self.lang), font=("Segoe UI", 26, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w", pady=(0, 20))
        
        add_f = tk.Frame(main, bg=C["card"], padx=20, pady=20, highlightbackground=C["border"], highlightthickness=1)
        add_f.pack(fill="x")
        
        self.ent = tk.Entry(add_f, font=("Segoe UI", 16), bg=C["card2"], fg=C["text"], relief="flat", insertbackground=C["text"])
        self.ent.pack(side="left", fill="x", expand=True, padx=(0, 20), ipady=8)
        self.ent.bind("<Return>", lambda e: self._add_racer())
        
        tk.Button(add_f, text=L("add", self.lang), command=self._add_racer, bg=C["green2"], fg="white", font=("Segoe UI", 12, "bold"), padx=25, relief="flat").pack(side="right")
        
        self.list_f = tk.Frame(main, bg=C["bg"])
        self.list_f.pack(fill="both", expand=True, pady=20)
        self._render_racers()
        
        btn_f = tk.Frame(main, bg=C["bg"])
        btn_f.pack(fill="x")
        tk.Button(btn_f, text=L("back", self.lang), command=self._page_port, bg=C["card"], fg=C["muted"], relief="flat", padx=20).pack(side="left")
        tk.Button(btn_f, text=L("start_race", self.lang), command=self._start_race_ui, bg=C["accent"], fg=C["bg"], font=("Segoe UI", 14, "bold"), padx=40, pady=10, relief="flat").pack(side="right")

    def _add_racer(self):
        name = self.ent.get().strip()
        if name:
            self.racers.append({"name": name, "ms": None})
            self.ent.delete(0, "end")
            self._render_racers()

    def _render_racers(self):
        for w in self.list_f.winfo_children(): w.destroy()
        for i, r in enumerate(self.racers):
            row = tk.Frame(self.list_f, bg=C["card"], pady=10, padx=15)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{i+1}", bg=C["accent"], fg=C["bg"], width=3, font=("Consolas", 12, "bold")).pack(side="left")
            tk.Label(row, text=r["name"], bg=C["card"], fg=C["text"], font=("Segoe UI", 13)).pack(side="left", padx=15)
            tk.Button(row, text="✕", command=lambda x=i: self._del_racer(x), bg=C["card"], fg=C["red"], relief="flat").pack(side="right")

    def _del_racer(self, i):
        self.racers.pop(i)
        self._render_racers()

    # ─── شاشة السباق ────────────────────────────
    def _start_race_ui(self):
        if not self.racers: return
        self._clear()
        self.curr_page = "race"
        self.curr = 0
        
        main = tk.Frame(self.frame, bg=C["bg"], padx=50, pady=30)
        main.pack(fill="both", expand=True)
        
        self.lbl_rname = tk.Label(main, text="", font=("Segoe UI", 42, "bold"), bg=C["bg"])
        self.lbl_rname.pack(anchor="w")
        
        timer_c = tk.Frame(main, bg=C["card"], highlightbackground=C["border"], highlightthickness=2)
        timer_c.pack(fill="x", pady=20)
        self.lbl_timer = tk.Label(timer_c, text="00:00.000", font=("Consolas", 90, "bold"), bg=C["card"], fg=C["text"])
        self.lbl_timer.pack(pady=40)
        
        self.prog = tk.Canvas(timer_c, height=10, bg=C["card"], highlightthickness=0)
        self.prog.pack(fill="x")
        self.bar = self.prog.create_rectangle(0,0,0,10, fill=C["accent"], outline="")
        
        # مؤشرات الحساسات
        sens_f = tk.Frame(main, bg=C["bg"])
        sens_f.pack(fill="x", pady=20)
        
        self.s1_ui = self._mk_sensor_ui(sens_f, L("sensor1", self.lang))
        self.s2_ui = self._mk_sensor_ui(sens_f, L("sensor2", self.lang))
        
        ctrl_f = tk.Frame(main, bg=C["bg"])
        ctrl_f.pack(fill="x")
        tk.Button(ctrl_f, text=L("manual_start", self.lang), command=self._on_start, bg=C["green2"], fg="white", relief="flat", padx=20).pack(side="left")
        tk.Button(ctrl_f, text=L("manual_stop", self.lang), command=lambda: self._on_stop(2500), bg=C["red"], fg="white", relief="flat", padx=20, ml=10).pack(side="left", padx=10)
        
        self._activate_racer(0)

    def _mk_sensor_ui(self, parent, label):
        f = tk.Frame(parent, bg=C["card"], padx=15, pady=10, highlightbackground=C["border"], highlightthickness=1)
        f.pack(side="left", expand=True, fill="x", padx=5)
        dot = tk.Label(f, text="●", fg=C["muted"], bg=C["card"], font=("Segoe UI", 18))
        dot.pack(side="left")
        tk.Label(f, text=label, bg=C["card"], fg=C["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        st = tk.Label(f, text=L("waiting", self.lang), bg=C["card"], fg=C["muted"])
        st.pack(side="right")
        return {"dot":dot, "st":st}

    def _activate_racer(self, i):
        if i >= len(self.racers): self._page_results(); return
        self.curr = i
        self.racing = False
        self.armed = True
        col = C["racer_colors"][i % len(C["racer_colors"])]
        self.lbl_rname.config(text=self.racers[i]["name"], fg=col)
        self.lbl_timer.config(text="00:00.000", fg=C["text"])
        self._set_sens(1, False); self._set_sens(2, False)
        if self.connected: self._send("ARM")

    def _set_sens(self, n, active):
        ui = self.s1_ui if n==1 else self.s2_ui
        ui["dot"].config(fg=C["green"] if active else C["muted"])
        ui["st"].config(text=L("detected" if active else "waiting", self.lang), fg=C["green"] if active else C["muted"])

    def _on_start(self):
        if self.racing: return
        self.racing = True
        self.t0 = time.perf_counter()
        self.lbl_timer.config(fg=C["green"])
        self._set_sens(1, True)
        self._tick()

    def _tick(self):
        if not self.racing: return
        el = int((time.perf_counter() - self.t0) * 1000)
        self.lbl_timer.config(text=fmt(el))
        w = self.prog.winfo_width()
        self.prog.coords(self.bar, 0, 0, int(w * min(el/30000, 1)), 10)
        self.root.after(30, self._tick)

    def _on_stop(self, ms):
        if not self.racing: return
        self.racing = False
        self.racers[self.curr]["ms"] = ms
        self._set_sens(2, True)
        self.lbl_timer.config(text=fmt(ms), fg=C["accent"])
        self.root.after(2000, lambda: self._activate_racer(self.curr + 1))

    # ─── شاشة النتائج ───────────────────────────
    def _page_results(self):
        self._clear()
        main = tk.Frame(self.frame, bg=C["bg"], padx=60, pady=40)
        main.pack(fill="both", expand=True)
        
        done = sorted([r for r in self.racers if r["ms"]], key=lambda x: x["ms"])
        if done:
            tk.Label(main, text=L("winner", self.lang, name=done[0]['name']), font=("Segoe UI", 32, "bold"), bg=C["bg"], fg=C["gold"]).pack(pady=20)
        
        tk.Label(main, text=L("results", self.lang), font=("Segoe UI", 20, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w")
        
        for i, r in enumerate(done):
            row = tk.Frame(main, bg=C["card"], pady=10, padx=20)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"#{i+1}", font=("Segoe UI", 16, "bold"), bg=C["card"], fg=C["accent"]).pack(side="left")
            tk.Label(row, text=r["name"], font=("Segoe UI", 16), bg=C["card"], fg=C["text"]).pack(side="left", padx=20)
            tk.Label(row, text=fmt(r["ms"]), font=("Consolas", 18, "bold"), bg=C["card"], fg=C["green"]).pack(side="right")
        
        tk.Button(main, text="New Race", command=self._page_setup, bg=C["accent"], fg=C["bg"], font=("Segoe UI", 12, "bold"), padx=30, pady=10, relief="flat").pack(pady=40)

    # ─── المساعدات ──────────────────────────────
    def _serial_loop(self):
        while self.connected and self.ser:
            try:
                line = self.ser.readline().decode().strip()
                if line == "START": self.root.after(0, self._on_start)
                elif line.startswith("TIME:"):
                    ms = int(line.split(":")[1])
                    self.root.after(0, lambda m=ms: self._on_stop(m))
            except: break

    def _send(self, cmd):
        if self.ser: self.ser.write(f"{cmd}\n".encode())

    def _toggle_lang(self):
        self.lang = "en" if self.lang=="ar" else "ar"
        self.settings["lang"] = self.lang
        self._save_settings()
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _auto_reconnect_loop(self):
        # Placeholder for auto-reconnect logic
        self.root.after(5000, self._auto_reconnect_loop)

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
