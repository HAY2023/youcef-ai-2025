"""
╔══════════════════════════════════════════════════════════════╗
║          RACE TIMER PRO — v4.1 (Legendary Edition)           ║
║  تطبيق Python كامل مع Serial ثنائي الاتجاه                 ║
║  تم التعديل لإضافة مظهر أسطوري واستخدام الأيقونة المخصصة     ║
╚══════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading, time, csv, os, sys, winsound, json
from datetime import datetime
from PIL import Image, ImageTk

try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

# ═══════════════════════════════════════════════
#  الألوان والخطوط (Legendary Theme)
# ═══════════════════════════════════════════════
C = {
    "bg":      "#05070A",
    "panel":   "#0A0F16",
    "card":    "#111823",
    "card2":   "#18222F",
    "border":  "#1E293B",
    "accent":  "#00D1FF",
    "green":   "#00FF85",
    "green2":  "#00B35D",
    "red":     "#FF3A3A",
    "amber":   "#FFB020",
    "purple":  "#9066FF",
    "muted":   "#4A5568",
    "dim":     "#0F172A",
    "gold":    "#FFD700",
    "text":    "#F1F5F9",
    "white":   "#FFFFFF",
}

RACER_COLORS = ["#00D1FF","#00FF85","#9066FF","#FFB020","#FF3A3A","#06C8D8","#FF7A30"]

def resource_path(relative_path):
    """ الحصول على المسار الصحيح للملف سواء في وضع التطوير أو بعد البناء (PyInstaller) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def fmt(ms: int) -> str:
    return f"{ms//60000:02d}:{(ms%60000)//1000:02d}.{ms%1000:03d}"

def btn(parent, text, cmd, bg, fg, px=12, py=7, font_size=10):
    return tk.Button(parent, text=text, command=cmd,
                     font=("Segoe UI", font_size, "bold"),
                     bg=bg, fg=fg, activebackground=bg,
                     activeforeground=fg, relief="flat",
                     cursor="hand2", padx=px, pady=py,
                     bd=0, highlightthickness=0)

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Nabtakir - نبتكر")
        self.root.configure(bg=C["bg"])

        # محاولة تحميل الأيقونة
        self.icon_path = resource_path("icon.ico")
        try:
            if os.path.exists(self.icon_path):
                self.root.iconbitmap(self.icon_path)
        except:
            pass

        w, h = 1000, 720
        ws, hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x, y = int((ws/2) - (w/2)), int((hs/2) - (h/2) - 40)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(850, 650)
        
        # العرض في شكل مكتب (تكبير الشاشة ملء الشاشة)
        self.root.state('zoomed')

        self.ser        = None
        self.connected  = False
        self._load_data()
        self.curr       = 0
        self.racing     = False
        self.armed      = False
        self.t0         = 0.0
        self.tick_id    = None

        # تحميل الشعار من الأيقونة أو ملف خارجي
        self.logo_img = None
        try:
            if os.path.exists(self.icon_path):
                raw = Image.open(self.icon_path)
                self.logo_img = ImageTk.PhotoImage(raw.resize((120, 120), Image.LANCZOS))
        except:
            pass

        self._style()
        self._topbar()
        self._statusbar()
        self.frame = tk.Frame(self.root, bg=C["bg"])
        self.frame.pack(fill="both", expand=True)

        self._page_port()

    def _load_data(self):
        self.data_file = resource_path("nabtakir_data.json")
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.racers = json.load(f)
            else:
                self.racers = []
        except:
            self.racers = []

    def _save_data(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.racers, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving data: {e}")

    def _topbar(self):
        bar = tk.Frame(self.root, bg=C["panel"], height=60)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="  ⏱  NABTAKIR - نبتكر",
                 font=("Segoe UI", 16, "bold"),
                 bg=C["panel"], fg=C["accent"]).pack(side="left", pady=14)

        self.lbl_conn = tk.Label(bar, text="● غير متصل",
                                  font=("Segoe UI", 10),
                                  bg=C["panel"], fg=C["red"])
        self.lbl_conn.pack(side="right", padx=20)

        self.lbl_port_info = tk.Label(bar, text="",
                                       font=("Consolas", 10),
                                       bg=C["panel"], fg=C["muted"])
        self.lbl_port_info.pack(side="right", padx=10)

    def _statusbar(self):
        self.sb_var = tk.StringVar(value="  جاهز للبدء")
        bar = tk.Frame(self.root, bg=C["panel"], height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self.sb_lbl = tk.Label(bar, textvariable=self.sb_var,
                                font=("Segoe UI", 9),
                                bg=C["panel"], fg=C["muted"], anchor="w")
        self.sb_lbl.pack(fill="x", padx=12, pady=5)

    def _status(self, msg, color=None):
        self.sb_var.set(f"  {msg}")
        self.sb_lbl.config(fg=color or C["muted"])

    def _clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def _style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TCombobox",
                    fieldbackground=C["card2"], background=C["card2"],
                    foreground=C["text"], selectbackground=C["accent"],
                    bordercolor=C["border"], arrowcolor=C["muted"])
        s.configure("Race.Treeview",
                    background=C["card"], foreground=C["text"],
                    fieldbackground=C["card"], bordercolor=C["border"],
                    rowheight=38, font=("Consolas", 12))
        s.configure("Race.Treeview.Heading",
                    background=C["panel"], foreground=C["muted"],
                    font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Race.Treeview",
              background=[("selected", C["accent"])],
              foreground=[("selected", C["bg"])])

    def _page_port(self):
        self._clear()
        outer = tk.Frame(self.frame, bg=C["bg"])
        outer.place(relx=.5, rely=.5, anchor="center")
        card = tk.Frame(outer, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        card.pack(ipadx=60, ipady=50)

        if self.logo_img:
            tk.Label(card, image=self.logo_img, bg=C["card"]).pack(pady=(0, 15))
        else:
            tk.Label(card, text="⏱", font=("Segoe UI", 72), bg=C["card"], fg=C["accent"]).pack()

        tk.Label(card, text="تطبيق نبتكر (Nabtakir)", font=("Segoe UI", 28, "bold"), bg=C["card"], fg=C["text"]).pack()
        tk.Label(card, text="إدارة السباقات الذكية — اختر المنفذ للبدء", font=("Segoe UI", 12), bg=C["card"], fg=C["muted"]).pack(pady=(4, 35))

        row = tk.Frame(card, bg=C["card"])
        row.pack()
        tk.Label(row, text="COM Port:", font=("Segoe UI", 12), bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 10))
        self.cmb = ttk.Combobox(row, width=12, state="readonly", font=("Segoe UI", 12))
        self.cmb.pack(side="left")
        btn(row, "↻", self._refresh, C["dim"], C["muted"], px=10, py=7).pack(side="left", padx=(8, 0))

        row2 = tk.Frame(card, bg=C["card"])
        row2.pack(pady=(12, 0))
        tk.Label(row2, text="Baud Rate:", font=("Segoe UI", 12), bg=C["card"], fg=C["muted"]).pack(side="left", padx=(0, 10))
        self.cmb_baud = ttk.Combobox(row2, width=10, state="readonly", values=["9600","115200"], font=("Segoe UI", 12))
        self.cmb_baud.set("9600")
        self.cmb_baud.pack(side="left")

        btn(card, "  اتصال بـ Arduino  ", self._connect, C["accent"], C["bg"], px=32, py=12, font_size=13).pack(pady=(30, 0))
        sep = tk.Frame(card, bg=C["border"], height=1)
        sep.pack(fill="x", pady=(25, 20))
        btn(card, "▷  محاكاة (بدون Arduino)", self._demo_mode, C["dim"], C["muted"], px=20).pack()
        self._refresh()

    def _refresh(self):
        if SERIAL_OK:
            ports = [p.device for p in serial.tools.list_ports.comports()]
        else:
            ports = ["COM3", "COM4", "COM5"]
        self.cmb["values"] = ports
        if ports: self.cmb.current(0)

    def _connect(self):
        port = self.cmb.get()
        baud = int(self.cmb_baud.get())
        if not port: return
        try:
            self.ser = serial.Serial(port, baud, timeout=0.5)
            time.sleep(2)
            self.connected = True
            self.lbl_conn.config(text=f"● {port} @ {baud}", fg=C["green"])
            self._status(f"تم الاتصال بـ {port}", C["green"])
            threading.Thread(target=self._serial_loop, daemon=True).start()
            self._page_setup()
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def _demo_mode(self):
        self.connected = False
        self.lbl_conn.config(text="● محاكاة", fg=C["amber"])
        self._page_setup()

    def _page_setup(self):
        self._clear()
        main = tk.Frame(self.frame, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=50, pady=35)
        tk.Label(main, text="إعداد المتسابقين", font=("Segoe UI", 24, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(main, text="أضف المتسابقين لبدء السباق", font=("Segoe UI", 12), bg=C["bg"], fg=C["muted"]).pack(anchor="w", pady=(2, 25))

        add = tk.Frame(main, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        add.pack(fill="x")
        row = tk.Frame(add, bg=C["card"], padx=20, pady=20)
        row.pack(fill="x")
        self.ent = tk.Entry(row, font=("Segoe UI", 15), bg=C["card2"], fg=C["text"], insertbackground=C["text"], relief="flat")
        self.ent.pack(side="left", fill="x", expand=True, ipady=10)
        self.ent.bind("<Return>", lambda e: self._add_racer())
        btn(row, " + إضافة ", self._add_racer, C["green2"], C["white"], px=22, py=10).pack(side="left", padx=(15, 0))

        self.list_fr = tk.Frame(main, bg=C["card"], highlightbackground=C["border"], highlightthickness=1)
        self.list_fr.pack(fill="both", expand=True, pady=20)
        self._render_list()

        bot = tk.Frame(main, bg=C["bg"])
        bot.pack(fill="x")
        btn(bot, "← رجوع", self._page_port, C["dim"], C["muted"], px=15).pack(side="left")
        self.btn_go = btn(bot, "  ابدأ السباق  ▶", self._page_race, C["dim"], C["muted"], px=32, py=12, font_size=13)
        self.btn_go.pack(side="right")

    def _add_racer(self):
        name = self.ent.get().strip()
        if not name: return
        self.racers.append({"name": name, "ms": None, "state": "waiting"})
        self.ent.delete(0, tk.END)
        self._save_data()
        self._render_list()
        if self.racers: self.btn_go.config(bg=C["accent"], fg=C["bg"])

    def _render_list(self):
        for w in self.list_fr.winfo_children(): w.destroy()
        if not self.racers:
            tk.Label(self.list_fr, text="لا يوجد متسابقين", bg=C["card"], fg=C["muted"], font=("Segoe UI", 12)).pack(pady=40)
            return
        for i, r in enumerate(self.racers):
            col = RACER_COLORS[i % len(RACER_COLORS)]
            row = tk.Frame(self.list_fr, bg=C["card2"], pady=5)
            row.pack(fill="x", padx=10, pady=2)
            tk.Label(row, text=f" {i+1} ", bg=col, fg=C["bg"], font=("Consolas", 12, "bold"), width=3).pack(side="left")
            tk.Label(row, text=r["name"], bg=C["card2"], fg=C["text"], font=("Segoe UI", 13, "bold")).pack(side="left", padx=15)
            tk.Button(row, text="✕", bg=C["card2"], fg=C["red"], relief="flat", command=lambda x=i: self._del_racer(x)).pack(side="right", padx=15)

    def _del_racer(self, i):
        self.racers.pop(i)
        self._save_data()
        self._render_list()
        if not self.racers: self.btn_go.config(bg=C["dim"], fg=C["muted"])

    def _page_race(self):
        self._clear()
        self.curr = 0; self.racing = False; self.armed = False
        for r in self.racers: r["ms"] = None; r["state"] = "waiting"
        self._save_data()
        
        main = tk.Frame(self.frame, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=40, pady=30)
        
        self.lbl_name = tk.Label(main, text="", font=("Segoe UI", 36, "bold"), bg=C["bg"])
        self.lbl_name.pack(anchor="w")
        
        tc = tk.Frame(main, bg=C["card"], highlightbackground=C["border"], highlightthickness=2)
        tc.pack(fill="x", pady=20)
        self.lbl_t = tk.Label(tc, text="00:00.000", font=("Consolas", 80, "bold"), bg=C["card"], fg=C["text"])
        self.lbl_t.pack(pady=30)
        
        self.c_bar = tk.Canvas(tc, height=8, bg=C["card"], highlightthickness=0)
        self.c_bar.pack(fill="x")
        self._bar = self.c_bar.create_rectangle(0, 0, 0, 8, fill=C["accent"], outline="")
        
        br = tk.Frame(main, bg=C["bg"])
        br.pack(fill="x", pady=20)
        btn(br, "▷ محاكاة", self._demo_curr, C["dim"], C["accent"], px=20).pack(side="left")
        btn(br, "⟳ إعادة", self._restart_race, C["dim"], C["amber"], px=20).pack(side="left", padx=10)
        btn(br, "← إنهاء", self._page_setup, C["dim"], C["red"], px=20).pack(side="right")
        
        self._activate(0)

    def _activate(self, idx):
        if idx >= len(self.racers): self._page_results(); return
        self.curr = idx; self.racing = False; self.armed = True
        self.racers[idx]["state"] = "ready"
        col = RACER_COLORS[idx % len(RACER_COLORS)]
        self.lbl_name.config(text=self.racers[idx]["name"], fg=col)
        self.lbl_t.config(text="00:00.000", fg=C["text"])
        self.c_bar.itemconfig(self._bar, fill=col)
        self._send("ARM")

    def _on_start(self):
        if self.racing: return
        self.racing = True; self.t0 = time.time()
        self.lbl_t.config(fg=C["green"])
        self._tick()

    def _tick(self):
        if not self.racing: return
        el = int((time.time() - self.t0) * 1000)
        self.lbl_t.config(text=fmt(el))
        w = self.c_bar.winfo_width()
        self.c_bar.coords(self._bar, 0, 0, int(w * min(el/30000, 1)), 8)
        self.tick_id = self.root.after(30, self._tick)

    def _on_stop(self, ms):
        if not self.racing: return
        self.racing = False
        self.racers[self.curr]["ms"] = ms
        self.racers[self.curr]["state"] = "done"
        self._save_data()
        winsound.Beep(1000, 200)
        self.root.after(2000, lambda: self._activate(self.curr + 1))

    def _restart_race(self): self._activate(self.curr)
    def _demo_curr(self):
        self._on_start()
        d = 3000 + int(time.time()*1000)%5000
        self.root.after(d, lambda: self._on_stop(d))

    def _page_results(self):
        self._clear()
        done = sorted([r for r in self.racers if r["ms"]], key=lambda x: x["ms"])
        main = tk.Frame(self.frame, bg=C["bg"], padx=50, pady=40)
        main.pack(fill="both", expand=True)
        tk.Label(main, text="🏆 النتائج", font=("Segoe UI", 32, "bold"), bg=C["bg"], fg=C["gold"]).pack(anchor="w")
        
        for i, r in enumerate(done):
            row = tk.Frame(main, bg=C["card"], pady=10)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=f"#{i+1}", font=("Segoe UI", 18, "bold"), bg=C["card"], width=5).pack(side="left")
            tk.Label(row, text=r["name"], font=("Segoe UI", 18), bg=C["card"], width=20, anchor="w").pack(side="left")
            tk.Label(row, text=fmt(r["ms"]), font=("Consolas", 20, "bold"), bg=C["card"], fg=C["accent"]).pack(side="right", padx=20)

        btn(main, "إعادة سباق جديد", self._page_setup, C["accent"], C["bg"], px=30, py=10).pack(pady=30)

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

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
