import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading, time, csv, os, winsound
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False

# ═══════════════════════════════════════════════
#  الإعدادات البصرية (Visual Settings)
# ═══════════════════════════════════════════════
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg": "#0B0E14",
    "card": "#151921",
    "accent": "#00D1FF",
    "green": "#2ECC71",
    "red": "#E74C3C",
    "gold": "#F1C40F",
    "text": "#E0E6ED",
    "muted": "#7F8C8D"
}

RACER_COLORS = ["#3498DB", "#2ECC71", "#9B59B6", "#F1C40F", "#E74C3C", "#1ABC9C", "#E67E22"]

def fmt(ms: int) -> str:
    """تحويل المللي ثانية إلى تنسيق MM:SS.mmm"""
    return f"{ms//60000:02d}:{(ms%60000)//1000:02d}.{ms%1000:03d}"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RACE TIMER PRO — v4.0")
        self.geometry("1100x750")
        self.configure(fg_color=COLORS["bg"])

        # Serial State
        self.ser = None
        self.connected = False

        # Race Logic State
        self.racers = []
        self.curr = 0
        self.racing = False
        self.armed = False
        self.t0 = 0.0
        self.tick_id = None

        self._setup_ui()

    def _setup_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=COLORS["card"])
        self.sidebar.pack(side="left", fill="y")

        logo_label = ctk.CTkLabel(self.sidebar, text="⏱ RACE TIMER", font=ctk.CTkFont(size=24, weight="bold"), text_color=COLORS["accent"])
        logo_label.pack(pady=30, padx=20)

        # Navigation Buttons
        self.btn_port_page = ctk.CTkButton(self.sidebar, text="الربط (Serial)", command=self._page_port, fg_color="transparent", border_width=1, border_color=COLORS["accent"], hover_color="#1A2A3A")
        self.btn_port_page.pack(pady=10, padx=20, fill="x")

        self.btn_setup_page = ctk.CTkButton(self.sidebar, text="إعداد المتسابقين", command=self._page_setup, state="disabled")
        self.btn_setup_page.pack(pady=10, padx=20, fill="x")

        self.btn_race_page = ctk.CTkButton(self.sidebar, text="شاشة السباق", command=self._page_race, state="disabled")
        self.btn_race_page.pack(pady=10, padx=20, fill="x")

        self.btn_results_page = ctk.CTkButton(self.sidebar, text="النتائج النهائية", command=self._page_results, state="disabled")
        self.btn_results_page.pack(pady=10, padx=20, fill="x")

        # Bottom Status
        self.lbl_status = ctk.CTkLabel(self.sidebar, text="● غير متصل", text_color=COLORS["red"], font=ctk.CTkFont(size=12))
        self.lbl_status.pack(side="bottom", pady=20)

        # Main Workspace Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self._page_port()

    def _clear_main(self):
        """إفراغ مساحة العمل الرئيسية قبل تحميل صفحة جديدة"""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    # ════════════════════════════════════════════
    #  Page 1: الاتصال (Port Selection)
    # ════════════════════════════════════════════
    def _page_port(self):
        self._clear_main()
        
        frame = ctk.CTkFrame(self.main_container, fg_color=COLORS["card"], corner_radius=15)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="اتصال Arduino", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(30, 10), padx=50)
        ctk.CTkLabel(frame, text="اختر المنفذ المناسب للبدء", text_color=COLORS["muted"]).pack(pady=(0, 30))

        # Port Selection
        self.cmb_port = ctk.CTkOptionMenu(frame, values=["جاري البحث..."], fg_color=COLORS["bg"], button_color=COLORS["accent"])
        self.cmb_port.pack(pady=10, padx=50, fill="x")
        self._refresh_ports()

        # Baud Rate Selection
        self.cmb_baud = ctk.CTkOptionMenu(frame, values=["9600", "115200"], fg_color=COLORS["bg"], button_color=COLORS["accent"])
        self.cmb_baud.set("9600")
        self.cmb_baud.pack(pady=10, padx=50, fill="x")

        # Action Buttons
        ctk.CTkButton(frame, text="اتصال الآن", command=self._connect, fg_color=COLORS["accent"], text_color="#000", hover_color="#00A3CC", font=ctk.CTkFont(weight="bold")).pack(pady=20, padx=50, fill="x")
        
        ctk.CTkButton(frame, text="وضع المحاكاة", command=self._demo_mode, fg_color="transparent", border_width=1).pack(pady=(0, 30), padx=50, fill="x")

    def _refresh_ports(self):
        if SERIAL_OK:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            if ports:
                self.cmb_port.configure(values=ports)
                self.cmb_port.set(ports[0])
            else:
                self.cmb_port.configure(values=["لا توجد منافذ"])
                self.cmb_port.set("لا توجد منافذ")

    def _connect(self):
        port = self.cmb_port.get()
        baud = int(self.cmb_baud.get())
        if port == "لا توجد منافذ" or port == "جاري البحث...": return
        
        try:
            if SERIAL_OK:
                self.ser = serial.Serial(port, baud, timeout=0.5)
                time.sleep(2) # انتظار استقرار الأردوينو
                self.connected = True
                self.lbl_status.configure(text=f"● متصل: {port}", text_color=COLORS["green"])
                threading.Thread(target=self._serial_loop, daemon=True).start()
                self.btn_setup_page.configure(state="normal")
                self._page_setup()
        except Exception as e:
            messagebox.showerror("خطأ في الاتصال", f"لا يمكن فتح المنفذ:\n{e}")

    def _demo_mode(self):
        self.connected = False
        self.lbl_status.configure(text="● وضع المحاكاة", text_color=COLORS["gold"])
        self.btn_setup_page.configure(state="normal")
        self._page_setup()

    # ════════════════════════════════════════════
    #  Page 2: إعداد المتسابقين (Setup)
    # ════════════════════════════════════════════
    def _page_setup(self):
        self._clear_main()
        self.racers = []

        header = ctk.CTkLabel(self.main_container, text="إعداد المتسابقين", font=ctk.CTkFont(size=28, weight="bold"))
        header.pack(pady=(0, 20), anchor="w")

        input_frame = ctk.CTkFrame(self.main_container, fg_color=COLORS["card"])
        input_frame.pack(fill="x", pady=10)

        self.ent_name = ctk.CTkEntry(input_frame, placeholder_text="اكتب اسم المتسابق أو رقم الجولة...", height=45, font=ctk.CTkFont(size=14))
        self.ent_name.pack(side="left", fill="x", expand=True, padx=15, pady=15)
        self.ent_name.bind("<Return>", lambda e: self._add_racer())

        ctk.CTkButton(input_frame, text="إضافة +", command=self._add_racer, width=120, height=45, fg_color=COLORS["green"], font=ctk.CTkFont(weight="bold")).pack(side="right", padx=15)

        # Container for racer list
        self.list_scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.list_scroll.pack(fill="both", expand=True, pady=10)

        # Bottom Start Button
        self.btn_start_race = ctk.CTkButton(self.main_container, text="بدء السباق ▶", command=self._page_race, state="disabled", height=50, fg_color=COLORS["accent"], text_color="#000", font=ctk.CTkFont(size=18, weight="bold"))
        self.btn_start_race.pack(pady=20, fill="x")

    def _add_racer(self):
        name = self.ent_name.get().strip()
        if not name: return
        self.racers.append({"name": name, "ms": None, "state": "waiting"})
        self.ent_name.delete(0, 'end')
        self._render_racers()
        if len(self.racers) > 0:
            self.btn_start_race.configure(state="normal")
            self.btn_race_page.configure(state="normal")

    def _render_racers(self):
        for widget in self.list_scroll.winfo_children():
            widget.destroy()
        
        for i, r in enumerate(self.racers):
            color = RACER_COLORS[i % len(RACER_COLORS)]
            row = ctk.CTkFrame(self.list_scroll, fg_color=COLORS["card"], height=60)
            row.pack(fill="x", pady=5)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=f"{i+1}", fg_color=color, text_color="#fff", width=40, height=60, font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(row, text=r["name"], font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20)
            
            ctk.CTkButton(row, text="حذف", width=80, fg_color="transparent", text_color=COLORS["red"], hover_color="#330000", command=lambda idx=i: self._remove_racer(idx)).pack(side="right", padx=20)

    def _remove_racer(self, idx):
        self.racers.pop(idx)
        self._render_racers()
        if not self.racers:
            self.btn_start_race.configure(state="disabled")

    # ════════════════════════════════════════════
    #  Page 3: شاشة السباق (Live Race)
    # ════════════════════════════════════════════
    def _page_race(self):
        self._clear_main()
        self.curr = 0
        self.racing = False
        self.armed = False
        for r in self.racers:
            r["ms"] = None
            r["state"] = "waiting"

        # Header with Current Racer Name
        top_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_frame.pack(fill="x", pady=10)

        self.lbl_curr_name = ctk.CTkLabel(top_frame, text="جاري التجهيز...", font=ctk.CTkFont(size=36, weight="bold"))
        self.lbl_curr_name.pack(side="left")

        self.lbl_count = ctk.CTkLabel(top_frame, text="0 / 0", text_color=COLORS["muted"], font=ctk.CTkFont(size=18))
        self.lbl_count.pack(side="right")

        # Large Timer Centerpiece
        timer_card = ctk.CTkFrame(self.main_container, fg_color=COLORS["card"], corner_radius=25, border_width=1, border_color="#1E232E")
        timer_card.pack(fill="both", expand=True, pady=20)

        self.lbl_timer = ctk.CTkLabel(timer_card, text="00:00.000", font=ctk.CTkFont(family="Consolas", size=120, weight="bold"), text_color=COLORS["text"])
        self.lbl_timer.place(relx=0.5, rely=0.45, anchor="center")

        # Visual Progress Bar
        self.progress_bar = ctk.CTkProgressBar(timer_card, width=650, height=12, progress_color=COLORS["accent"])
        self.progress_bar.set(0)
        self.progress_bar.place(relx=0.5, rely=0.7, anchor="center")

        # Sensor Status Indicators
        sensor_frame = ctk.CTkFrame(timer_card, fg_color="transparent")
        sensor_frame.place(relx=0.5, rely=0.88, anchor="center")

        self.s1_dot = ctk.CTkLabel(sensor_frame, text="●", text_color=COLORS["muted"], font=ctk.CTkFont(size=40))
        self.s1_dot.grid(row=0, column=0, padx=5)
        ctk.CTkLabel(sensor_frame, text="البداية (S1)", text_color=COLORS["muted"]).grid(row=0, column=1, padx=(0, 40))

        self.s2_dot = ctk.CTkLabel(sensor_frame, text="●", text_color=COLORS["muted"], font=ctk.CTkFont(size=40))
        self.s2_dot.grid(row=0, column=2, padx=5)
        ctk.CTkLabel(sensor_frame, text="النهاية (S2)", text_color=COLORS["muted"]).grid(row=0, column=3)

        # Control Row
        ctrl_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=10)

        ctk.CTkButton(ctrl_frame, text="▷ محاكاة سريعة", command=self._demo_curr_race, width=160, height=45).pack(side="left", padx=5)
        ctk.CTkButton(ctrl_frame, text="⟳ إعادة المحاولة", command=self._restart_curr, width=160, height=45, fg_color="transparent", border_width=1).pack(side="left", padx=5)

        self._activate_racer(0)

    def _activate_racer(self, idx):
        if idx >= len(self.racers):
            self.btn_results_page.configure(state="normal")
            self._page_results()
            return

        self.curr = idx
        self.racing = False
        self.armed = True
        self.racers[idx]["state"] = "ready"
        
        color = RACER_COLORS[idx % len(RACER_COLORS)]
        self.lbl_curr_name.configure(text=self.racers[idx]["name"], text_color=color)
        self.lbl_count.configure(text=f"متسابق {idx+1} من {len(self.racers)}")
        self.lbl_timer.configure(text="00:00.000", text_color=COLORS["text"])
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color=color)
        
        self.s1_dot.configure(text_color=COLORS["muted"])
        self.s2_dot.configure(text_color=COLORS["muted"])

        if self.connected:
            self._send_serial("ARM")

    def _on_start(self):
        if self.racing: return
        self.racing = True
        self.t0 = time.time()
        self.s1_dot.configure(text_color=COLORS["green"])
        self.lbl_timer.configure(text_color=COLORS["green"])
        self._tick()

    def _tick(self):
        if not self.racing: return
        el = int((time.time() - self.t0) * 1000)
        self.lbl_timer.configure(text=fmt(el))
        # Update progress bar (visual only, max 30s)
        self.progress_bar.set(min(el / 30000, 1.0))
        self.tick_id = self.after(30, self._tick)

    def _on_stop(self, ms):
        if not self.racing: return
        self.racing = False
        self.racers[self.curr]["ms"] = ms
        self.racers[self.curr]["state"] = "done"
        
        self.s2_dot.configure(text_color=COLORS["green"])
        self.lbl_timer.configure(text=fmt(ms), text_color=RACER_COLORS[self.curr % len(RACER_COLORS)])
        self.progress_bar.set(1.0)
        
        threading.Thread(target=lambda: winsound.Beep(1200, 400), daemon=True).start()
        
        # الانتقال للمتسابق التالي بعد 3 ثواني
        self.after(3000, lambda: self._activate_racer(self.curr + 1))

    def _restart_curr(self):
        self._activate_racer(self.curr)

    def _demo_curr_race(self):
        self._on_start()
        import random
        delay_ms = random.randint(2500, 9000)
        self.after(delay_ms, lambda: self._on_stop(delay_ms))

    # ════════════════════════════════════════════
    #  Page 4: النتائج النهائية (Results)
    # ════════════════════════════════════════════
    def _page_results(self):
        self._clear_main()
        
        header = ctk.CTkLabel(self.main_container, text="🏆 النتائج النهائية", font=ctk.CTkFont(size=32, weight="bold"), text_color=COLORS["gold"])
        header.pack(pady=(0, 20), anchor="w")

        scroll = ctk.CTkScrollableFrame(self.main_container, fg_color=COLORS["card"], corner_radius=15)
        scroll.pack(fill="both", expand=True)

        done = [r for r in self.racers if r["ms"] is not None]
        ranked = sorted(done, key=lambda x: x["ms"])

        for i, r in enumerate(ranked):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            medals = ["🥇", "🥈", "🥉"]
            prefix = medals[i] if i < 3 else f" {i+1} "
            
            ctk.CTkLabel(row, text=prefix, font=ctk.CTkFont(size=24), width=70).pack(side="left", pady=15)
            ctk.CTkLabel(row, text=r["name"], font=ctk.CTkFont(size=18, weight="bold"), width=250, anchor="w").pack(side="left", padx=20)
            ctk.CTkLabel(row, text=fmt(r["ms"]), font=ctk.CTkFont(family="Consolas", size=24, weight="bold"), text_color=COLORS["accent"]).pack(side="right", padx=40)
            
            if i == 0:
                ctk.CTkLabel(row, text="رقم قياسي!", text_color=COLORS["gold"], font=ctk.CTkFont(size=13, slant="italic")).pack(side="right")

            # Separator line
            if i < len(ranked) - 1:
                line = ctk.CTkFrame(scroll, height=1, fg_color="#1E232E")
                line.pack(fill="x", padx=20)

        # Export and Reset
        btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(btn_frame, text="حفظ النتائج Excel/CSV", command=self._export_csv, height=45, fg_color=COLORS["green"], text_color="#000", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="سباق جديد", command=self._page_setup, height=45, fg_color="transparent", border_width=1).pack(side="left", padx=5)

    def _export_csv(self):
        done = [r for r in self.racers if r["ms"] is not None]
        if not done: return
        ranked = sorted(done, key=lambda x: x["ms"])
        filename = f"RaceResults_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
        path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["المركز", "الاسم", "الزمن (ms)", "الزمن المنسق"])
                for i, r in enumerate(ranked, 1):
                    writer.writerow([i, r["name"], r["ms"], fmt(r["ms"])])
            messagebox.showinfo("تم الحفظ", f"تم حفظ الملف بنجاح على سطح المكتب:\n{filename}")
        except Exception as e:
            messagebox.showerror("خطأ", f"تعذر حفظ الملف:\n{e}")

    # ════════════════════════════════════════════
    #  Serial Loop & Communication
    # ════════════════════════════════════════════
    def _serial_loop(self):
        """حلقة مراقبة البيانات الواردة من الأردوينو"""
        while self.connected and self.ser:
            try:
                line = self.ser.readline().decode().strip()
                if not line: continue
                if line == "START":
                    self.after(0, self._on_start)
                elif line.startswith("TIME:"):
                    try:
                        ms = int(line.split(":")[1])
                        self.after(0, lambda m=ms: self._on_stop(m))
                    except: pass
                elif line == "READY":
                    self.after(0, lambda: self.lbl_status.configure(text="● الأردوينو جاهز", text_color=COLORS["green"]))
            except:
                break

    def _send_serial(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{cmd}\n".encode())
            except: pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
