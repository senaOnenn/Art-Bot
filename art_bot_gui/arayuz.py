"""
Robotik Ressam VIP — Kontrol Paneli  v2.1
==========================================
Kurulum (sadece bir kez çalıştır):
    pip install customtkinter websocket-client pillow

Kullanım:
    1. Bilgisayarını "Robotik_Ressam" WiFi'ına bağla (şifre: 12345678)
    2. python robot_arayuz.py
    3. IP kutusunda 192.168.4.1 yazar, Bağlan'a bas.
"""

import tkinter as tk
import customtkinter as ctk
import websocket
import threading
import json
import math
from collections import deque

# ── Tema ───────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

RENK = {
    "bg":      "#07090d",
    "bg2":     "#0d1117",
    "bg3":     "#111820",
    "border":  "#1a2332",
    "teal":    "#00c9a7",
    "amber":   "#f59e0b",
    "red":     "#ef4444",
    "blue":    "#3b82f6",
    "muted":   "#4a5568",
    "text":    "#e2e8f0",
    "text2":   "#718096",
    "canvas":  "#04060a",
    "grid":    "#0c1118",
}

CANVAS_SCALE = 1.0
MAX_KUYRUK   = 50


def ui(root, fn):
    root.after(0, fn)


class RobotArayuzu(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Robotik Ressam VIP — Kontrol Paneli")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(fg_color=RENK["bg"])

        self._ws: websocket.WebSocketApp | None = None
        self._ws_thread: threading.Thread | None = None
        self._connected = False

        self._rx = 0.0
        self._ry = 0.0
        self._raci = 0.0

        self._trail: list[tuple[float, float]] = [(0.0, 0.0)]
        self._trail_color = RENK["teal"]
        self._trail_w = 2

        self._local_q: deque[dict] = deque(maxlen=MAX_KUYRUK)
        self._keys: set[str] = set()

        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════════════════════════
    # UI İnşası
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        top = ctk.CTkFrame(self, height=44, fg_color=RENK["bg2"],
                           corner_radius=0, border_width=0)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="⬡  ART BOT", font=("Consolas", 15, "bold"),
                     text_color=RENK["teal"]).pack(side="left", padx=16)
        ctk.CTkLabel(top, text="v2.1  |  WebSocket Kontrol",
                     font=("Consolas", 10), text_color=RENK["muted"]).pack(side="left")

        self._heap_lbl = ctk.CTkLabel(top, text="HEAP: —",
                                      font=("Consolas", 10), text_color=RENK["muted"])
        self._heap_lbl.pack(side="right", padx=16)

        self._conn_dot = tk.Canvas(top, width=10, height=10,
                                   bg=RENK["bg2"], highlightthickness=0)
        self._conn_dot.pack(side="right", padx=(0, 4))
        self._conn_dot.create_oval(1, 1, 9, 9, fill=RENK["red"], outline="", tags="dot")

        self._conn_lbl = ctk.CTkLabel(top, text="Bağlı değil",
                                      font=("Consolas", 10), text_color=RENK["text2"])
        self._conn_lbl.pack(side="right", padx=(0, 6))

        content = ctk.CTkFrame(self, fg_color=RENK["bg"], corner_radius=0)
        content.pack(fill="both", expand=True)

        sol = ctk.CTkFrame(content, width=210, fg_color=RENK["bg2"],
                           corner_radius=0,
                           border_width=1, border_color=RENK["border"])
        sol.pack(side="left", fill="y")
        sol.pack_propagate(False)
        self._build_left(sol)

        orta = ctk.CTkFrame(content, fg_color=RENK["bg2"], corner_radius=0,
                            border_width=1, border_color=RENK["border"])
        orta.pack(side="left", fill="both", expand=True)
        self._build_center(orta)

        sag = ctk.CTkFrame(content, width=240, fg_color=RENK["bg2"],
                           corner_radius=0,
                           border_width=1, border_color=RENK["border"])
        sag.pack(side="right", fill="y")
        sag.pack_propagate(False)
        self._build_right(sag)

    def _build_left(self, parent):
        pad = dict(padx=10, pady=3)

        self._section(parent, "BAĞLANTI")
        conn_row = ctk.CTkFrame(parent, fg_color="transparent")
        conn_row.pack(fill="x", **pad)
        self._ip_entry = ctk.CTkEntry(conn_row, placeholder_text="192.168.4.1",
                                      font=("Consolas", 12), width=130)
        self._ip_entry.pack(side="left")
        self._ip_entry.insert(0, "192.168.4.1")
        self._baglan_btn = ctk.CTkButton(conn_row, text="Bağlan", width=60,
                                         font=("Consolas", 11),
                                         command=self._toggle_conn)
        self._baglan_btn.pack(side="left", padx=(4, 0))

        self._sep(parent)
        self._section(parent, "HAREKET")

        dpad = ctk.CTkFrame(parent, fg_color="transparent")
        dpad.pack(**pad)

        btn_cfg = dict(width=52, height=40, font=("Consolas", 14, "bold"),
                       fg_color=RENK["bg3"], border_width=1,
                       border_color=RENK["border"], text_color=RENK["text"],
                       hover_color=RENK["border"])

        ctk.CTkFrame(dpad, width=52, height=40, fg_color="transparent").grid(row=0, column=0, padx=2, pady=2)
        ctk.CTkButton(dpad, text="▲", **btn_cfg,
                      command=lambda: self._cmd("ileri", self._dist())).grid(row=0, column=1, padx=2, pady=2)
        ctk.CTkFrame(dpad, width=52, height=40, fg_color="transparent").grid(row=0, column=2, padx=2, pady=2)

        ctk.CTkButton(dpad, text="◄", **btn_cfg,
                      command=lambda: self._cmd("sol", self._ang())).grid(row=1, column=0, padx=2, pady=2)
        ctk.CTkButton(dpad, text="■", width=52, height=40,
                      font=("Consolas", 14, "bold"),
                      fg_color="#2a0a0a", border_width=1,
                      border_color="#5a1a1a", text_color=RENK["red"],
                      hover_color="#3a1010",
                      command=self._acil).grid(row=1, column=1, padx=2, pady=2)
        ctk.CTkButton(dpad, text="►", **btn_cfg,
                      command=lambda: self._cmd("sag", self._ang())).grid(row=1, column=2, padx=2, pady=2)

        ctk.CTkFrame(dpad, width=52, height=40, fg_color="transparent").grid(row=2, column=0, padx=2, pady=2)
        ctk.CTkButton(dpad, text="▼", **btn_cfg,
                      command=lambda: self._cmd("geri", self._dist())).grid(row=2, column=1, padx=2, pady=2)
        ctk.CTkFrame(dpad, width=52, height=40, fg_color="transparent").grid(row=2, column=2, padx=2, pady=2)

        for label, attr, default, unit in [
            ("Mesafe", "_in_mesafe", "200", "mm"),
            ("Açı",    "_in_aci",    "90",  "°"),
        ]:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label, font=("Consolas", 10),
                         text_color=RENK["text2"], width=48, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, font=("Consolas", 11), width=64)
            entry.insert(0, default)
            entry.pack(side="left")
            ctk.CTkLabel(row, text=unit, font=("Consolas", 10),
                         text_color=RENK["muted"]).pack(side="left", padx=3)
            setattr(self, attr, entry)

        hiz_row = ctk.CTkFrame(parent, fg_color="transparent")
        hiz_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(hiz_row, text="Hız", font=("Consolas", 10),
                     text_color=RENK["text2"], width=48, anchor="w").pack(side="left")
        self._hiz_val_lbl = ctk.CTkLabel(hiz_row, text="60%",
                                         font=("Consolas", 10),
                                         text_color=RENK["teal"], width=32)
        self._hiz_val_lbl.pack(side="right")
        self._hiz_slider = ctk.CTkSlider(hiz_row, from_=0.15, to=1.0,
                                         number_of_steps=17, command=self._on_hiz)
        self._hiz_slider.set(0.6)
        self._hiz_slider.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._sep(parent)

        ctk.CTkButton(parent, text="⚠  ACİL DURDUR",
                      font=("Consolas", 12, "bold"),
                      fg_color="#2a0808", border_width=1,
                      border_color="#6b1a1a", text_color=RENK["red"],
                      hover_color="#3d1010",
                      command=self._acil).pack(fill="x", padx=10, pady=6)

        self._sep(parent)

        self._section(parent, "HAZIR ŞEKİLLER")
        boyut_row = ctk.CTkFrame(parent, fg_color="transparent")
        boyut_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(boyut_row, text="Boyut", font=("Consolas", 10),
                     text_color=RENK["text2"], width=48, anchor="w").pack(side="left")
        self._in_boyut = ctk.CTkEntry(boyut_row, font=("Consolas", 11), width=64)
        self._in_boyut.insert(0, "200")
        self._in_boyut.pack(side="left")
        ctk.CTkLabel(boyut_row, text="mm", font=("Consolas", 10),
                     text_color=RENK["muted"]).pack(side="left", padx=3)

        sg = ctk.CTkFrame(parent, fg_color="transparent")
        sg.pack(fill="x", padx=10, pady=4)
        shapes = [("□ Kare", "kare"), ("△ Üçgen", "ucgen"),
                  ("★ Yıldız", "yildiz"), ("◎ Spiral", "spiral")]
        for i, (lbl, tip) in enumerate(shapes):
            ctk.CTkButton(sg, text=lbl, font=("Consolas", 10),
                          width=88, height=30,
                          fg_color=RENK["bg3"], border_width=1,
                          border_color=RENK["border"], text_color=RENK["text2"],
                          hover_color=RENK["border"],
                          command=lambda t=tip: self._sekil(t)).grid(
                row=i // 2, column=i % 2, padx=2, pady=2)

    def _build_center(self, parent):
        hdr = ctk.CTkFrame(parent, height=32, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="ROTA TAKİBİ",
                     font=("Consolas", 9), text_color=RENK["muted"]).pack(side="left")

        self._trail_color_btn = tk.Button(
            hdr, bg=RENK["teal"], width=2, height=1, relief="flat",
            cursor="hand2", command=self._pick_color)
        self._trail_color_btn.pack(side="right", padx=2)
        ctk.CTkLabel(hdr, text="Renk", font=("Consolas", 9),
                     text_color=RENK["text2"]).pack(side="right", padx=(0, 4))

        self._kalin_slider = ctk.CTkSlider(hdr, from_=1, to=5,
                                           number_of_steps=4, width=60,
                                           command=lambda v: setattr(self, "_trail_w", int(v)))
        self._kalin_slider.set(2)
        self._kalin_slider.pack(side="right", padx=4)
        ctk.CTkLabel(hdr, text="Kalınlık", font=("Consolas", 9),
                     text_color=RENK["text2"]).pack(side="right")

        for lbl, fn in [("🗑 Temizle", self._temizle), ("↓ PNG", self._indir)]:
            ctk.CTkButton(hdr, text=lbl, font=("Consolas", 9),
                          width=72, height=24,
                          fg_color=RENK["bg3"], border_width=1,
                          border_color=RENK["border"], text_color=RENK["text2"],
                          hover_color=RENK["border"],
                          command=fn).pack(side="right", padx=2)

        self.canvas = tk.Canvas(parent, bg=RENK["canvas"],
                                highlightthickness=1,
                                highlightbackground=RENK["border"])
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>",   self._on_zoom)
        self.canvas.bind("<Button-5>",   self._on_zoom)

        self._canvas_ready = False

    def _on_canvas_resize(self, _event=None):
        self._canvas_ready = True
        self._redraw_canvas()

    def _cx(self): return self.canvas.winfo_width()  / 2
    def _cy(self): return self.canvas.winfo_height() / 2

    def _w2c(self, xmm, ymm):
        return (self._cx() + xmm * CANVAS_SCALE,
                self._cy() - ymm * CANVAS_SCALE)

    def _redraw_canvas(self):
        if not self._canvas_ready:
            return
        self.canvas.delete("all")
        self._draw_grid()
        self._draw_trail()
        self._draw_robot()

    def _draw_grid(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        step = max(30, int(50 * CANVAS_SCALE))
        cx, cy = self._cx(), self._cy()
        for x in self._frange(cx % step, w, step):
            self.canvas.create_line(x, 0, x, h, fill=RENK["grid"], width=1)
        for y in self._frange(cy % step, h, step):
            self.canvas.create_line(0, y, w, y, fill=RENK["grid"], width=1)
        self.canvas.create_line(cx, 0, cx, h, fill="#1a2840", width=1)
        self.canvas.create_line(0, cy, w, cy, fill="#1a2840", width=1)
        self.canvas.create_oval(cx-4, cy-4, cx+4, cy+4,
                                fill=RENK["red"], outline="")

    def _draw_trail(self):
        if len(self._trail) < 2:
            return
        for i in range(1, len(self._trail)):
            x1, y1 = self._w2c(*self._trail[i-1])
            x2, y2 = self._w2c(*self._trail[i])
            self.canvas.create_line(x1, y1, x2, y2,
                                    fill=self._trail_color,
                                    width=self._trail_w,
                                    capstyle=tk.ROUND, tags="trail")

    def _draw_robot(self):
        cx, cy = self._w2c(self._rx, self._ry)
        rad = math.radians(self._raci)
        size = 10
        pts = []
        for angle in [0, 2.4, -2.4]:
            a = rad + angle
            length = size if angle == 0 else size * 0.6
            pts.extend([cx + length * math.sin(a),
                        cy - length * math.cos(a)])
        self.canvas.create_polygon(pts, fill=RENK["red"],
                                   outline=RENK["bg"], width=1, tags="robot")

    @staticmethod
    def _frange(start, stop, step):
        x = start
        while x < stop:
            yield x
            x += step

    def _on_zoom(self, event):
        global CANVAS_SCALE
        delta = 1.1 if (getattr(event, "delta", 0) > 0 or event.num == 4) else 0.9
        CANVAS_SCALE = max(0.2, min(5.0, CANVAS_SCALE * delta))
        self._redraw_canvas()

    def _pick_color(self):
        from tkinter import colorchooser
        color = colorchooser.askcolor(color=self._trail_color,
                                      title="Çizgi Rengi")[1]
        if color:
            self._trail_color = color
            self._trail_color_btn.configure(bg=color)

    def _build_right(self, parent):
        self._section(parent, "TELEMETRİ")
        tele_grid = ctk.CTkFrame(parent, fg_color="transparent")
        tele_grid.pack(fill="x", padx=8, pady=4)

        self._tele_labels = {}
        cards = [
            ("X (mm)",   "tX",  "0.0"),
            ("Y (mm)",   "tY",  "0.0"),
            ("Açı (°)",  "tA",  "0.0"),
            ("Durum",    "tD",  "Bekliyor"),
            ("Sol Puls", "tSL", "0"),
            ("Sağ Puls", "tSR", "0"),
        ]
        for i, (lbl, key, default) in enumerate(cards):
            card = ctk.CTkFrame(tele_grid, fg_color=RENK["bg3"],
                                border_width=1, border_color=RENK["border"],
                                corner_radius=5)
            card.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")
            tele_grid.columnconfigure(i % 2, weight=1)
            ctk.CTkLabel(card, text=lbl, font=("Consolas", 8),
                         text_color=RENK["muted"]).pack(anchor="w", padx=6, pady=(4, 0))
            val_lbl = ctk.CTkLabel(card, text=default,
                                   font=("Consolas", 13, "bold"),
                                   text_color=RENK["teal"])
            val_lbl.pack(anchor="w", padx=6, pady=(0, 4))
            self._tele_labels[key] = val_lbl

        self._sep(parent)
        self._section(parent, "PWM")
        pwm_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pwm_frame.pack(fill="x", padx=8, pady=4)
        self._pwm_bars = {}
        for key, lbl in [("sol", "SOL"), ("sag", "SAĞ")]:
            col = ctk.CTkFrame(pwm_frame, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(col, text=lbl, font=("Consolas", 8),
                         text_color=RENK["muted"]).pack()
            track = ctk.CTkFrame(col, height=48, fg_color=RENK["bg3"],
                                 border_width=1, border_color=RENK["border"],
                                 corner_radius=4)
            track.pack(fill="x")
            track.pack_propagate(False)
            fill = ctk.CTkFrame(track, height=0,
                                fg_color=RENK["blue"] if key == "sol" else RENK["teal"],
                                corner_radius=3)
            fill.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw", relheight=0.4)
            self._pwm_bars[key] = fill

        self._sep(parent)
        self._section(parent, "KOMUT KUYRUĞU  —  BAĞLI LİSTE")

        q_hdr = ctk.CTkFrame(parent, fg_color="transparent")
        q_hdr.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(q_hdr, text="head →",
                     font=("Consolas", 9), text_color=RENK["muted"]).pack(side="left")
        self._q_count_lbl = ctk.CTkLabel(q_hdr, text="0/50",
                                          font=("Consolas", 9),
                                          text_color=RENK["teal"])
        self._q_count_lbl.pack(side="right")

        self._ll_frame = ctk.CTkScrollableFrame(parent, fg_color=RENK["bg3"],
                                                 border_width=1,
                                                 border_color=RENK["border"],
                                                 corner_radius=5)
        self._ll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._render_ll()

    # ══════════════════════════════════════════════════════════════════════════
    # Yardımcı
    # ══════════════════════════════════════════════════════════════════════════

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Consolas", 9),
                     text_color=RENK["muted"], anchor="w").pack(fill="x", padx=10, pady=(10, 2))

    def _sep(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color=RENK["border"],
                     corner_radius=0).pack(fill="x", padx=8, pady=4)

    def _dist(self):
        try:    return float(self._in_mesafe.get())
        except: return 200.0

    def _ang(self):
        try:    return float(self._in_aci.get())
        except: return 90.0

    def _boyut(self):
        try:    return float(self._in_boyut.get())
        except: return 200.0

    def _on_hiz(self, val):
        self._hiz_val_lbl.configure(text=f"{int(val*100)}%")
        self._cmd("hiz", round(val, 2))

    # ══════════════════════════════════════════════════════════════════════════
    # WebSocket
    # ══════════════════════════════════════════════════════════════════════════

    def _toggle_conn(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        ip = self._ip_entry.get().strip()
        url = f"ws://{ip}/ws"
        self._baglan_btn.configure(text="Bağlanıyor…", state="disabled")

        def run():
            self._ws = websocket.WebSocketApp(
                url,
                on_open=self._on_ws_open,
                on_message=self._on_ws_msg,
                on_error=self._on_ws_error,
                on_close=self._on_ws_close,
            )
            self._ws.run_forever()

        self._ws_thread = threading.Thread(target=run, daemon=True)
        self._ws_thread.start()

    def _disconnect(self):
        if self._ws:
            self._ws.close()

    def _on_ws_open(self, ws):
        self._connected = True
        ui(self, lambda: self._set_conn_ui(True))
        self._ws_send({"cmd": "rota_al"})

    def _on_ws_msg(self, ws, raw):
        try:
            d = json.loads(raw)
        except Exception:
            return
        ui(self, lambda d=d: self._handle_msg(d))

    def _on_ws_error(self, ws, err):
        pass

    def _on_ws_close(self, ws, code, msg):
        self._connected = False
        ui(self, lambda: self._set_conn_ui(False))

    def _ws_send(self, obj: dict):
        if self._ws and self._connected:
            try:
                self._ws.send(json.dumps(obj))
            except Exception:
                pass

    def _set_conn_ui(self, ok: bool):
        color = RENK["teal"] if ok else RENK["red"]
        text  = "Bağlı" if ok else "Bağlı değil"
        btn   = "Kes" if ok else "Bağlan"
        self._conn_dot.itemconfig("dot", fill=color)
        self._conn_lbl.configure(text=text)
        self._baglan_btn.configure(text=btn, state="normal")

    # ══════════════════════════════════════════════════════════════════════════
    # Mesaj İşleme
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_msg(self, d: dict):
        if d.get("tip") == "durum":
            rx, ry, ra = d.get("x", 0), d.get("y", 0), d.get("aci", 0)
            self._tele_labels["tX"].configure(text=f"{rx:.1f}")
            self._tele_labels["tY"].configure(text=f"{ry:.1f}")
            self._tele_labels["tA"].configure(text=f"{ra:.1f}")
            running = d.get("yurutuyor", False)
            self._tele_labels["tD"].configure(
                text="▶ Çalışıyor" if running else "■ Bekliyor",
                text_color=RENK["amber"] if running else RENK["teal"])
            self._tele_labels["tSL"].configure(text=str(d.get("sol_puls", 0)))
            self._tele_labels["tSR"].configure(text=str(d.get("sag_puls", 0)))
            heap = d.get("heap", 0)
            self._heap_lbl.configure(text=f"HEAP: {heap/1024:.1f} KB")

            for key, field in [("sol", "pwm_sol"), ("sag", "pwm_sag")]:
                ratio = d.get(field, 0) / 1023
                self._pwm_bars[key].place_configure(relheight=max(0.02, ratio))

            if self._trail:
                lx, ly = self._trail[-1]
                if abs(rx - lx) > 0.5 or abs(ry - ly) > 0.5:
                    x1, y1 = self._w2c(lx, ly)
                    x2, y2 = self._w2c(rx, ry)
                    self.canvas.create_line(x1, y1, x2, y2,
                                            fill=self._trail_color,
                                            width=self._trail_w,
                                            capstyle=tk.ROUND, tags="trail")
            self._trail.append((rx, ry))
            self._rx, self._ry, self._raci = rx, ry, ra
            self.canvas.delete("robot")
            self._draw_robot()

            q = d.get("kuyruk", 0)
            self._q_count_lbl.configure(text=f"{q}/50")
            while len(self._local_q) > q:
                self._local_q.popleft()
            self._render_ll()

        elif d.get("tip") == "rota":
            noktalar = d.get("noktalar", [])
            self._trail = [(p["x"], p["y"]) for p in noktalar]
            if not self._trail:
                self._trail = [(0.0, 0.0)]
            self._rx, self._ry = self._trail[-1] if self._trail else (0.0, 0.0)
            self._redraw_canvas()

        elif d.get("hata") == "kuyruk_dolu":
            import tkinter.messagebox as mb
            mb.showwarning("Kuyruk Dolu", "ESP kuyruğu dolu!\nMevcut komutların bitmesini bekle.")

    # ══════════════════════════════════════════════════════════════════════════
    # Komut Gönderme
    # ══════════════════════════════════════════════════════════════════════════

    def _cmd(self, c: str, v: float = 0.0):
        self._ws_send({"cmd": c, "val": v})
        if c in ("ileri", "geri", "sol", "sag"):
            if len(self._local_q) < MAX_KUYRUK:
                self._local_q.append({"cmd": c, "val": v})
                self._render_ll()

    def _acil(self):
        self._ws_send({"cmd": "dur"})
        self._local_q.clear()
        self._render_ll()

    def _sekil(self, tip: str):
        self._ws_send({"cmd": tip, "val": self._boyut()})
        n_moves = {"kare": 8, "ucgen": 6, "yildiz": 10, "spiral": 20}.get(tip, 4)
        moves = ["ileri", "sag"] * (n_moves // 2)
        for m in moves:
            if len(self._local_q) < MAX_KUYRUK:
                self._local_q.append({"cmd": m, "val": self._boyut()})
        self._render_ll()

    def _temizle(self):
        self._trail = [(0.0, 0.0)]
        self._rx = self._ry = self._raci = 0.0
        self._ws_send({"cmd": "konum_sifirla"})
        self._local_q.clear()
        self._redraw_canvas()
        self._render_ll()

    def _indir(self):
        """Canvas'ı PNG olarak kaydeder. Pillow yoksa .eps olarak kaydeder."""
        import tkinter.filedialog as fd
        from datetime import datetime
        fname = fd.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"artbot_{datetime.now().strftime('%H%M%S')}.png",
            filetypes=[("PNG", "*.png"), ("EPS", "*.eps")])
        if not fname:
            return
        try:
            from PIL import ImageGrab
            x = self.canvas.winfo_rootx()
            y = self.canvas.winfo_rooty()
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            ImageGrab.grab((x, y, x+w, y+h)).save(fname)
        except ImportError:
            # Pillow yoksa EPS olarak kaydet
            eps_fname = fname.replace(".png", ".eps")
            self.canvas.postscript(file=eps_fname)
            import tkinter.messagebox as mb
            mb.showinfo("Kaydedildi", f"Pillow kurulu değil, EPS olarak kaydedildi:\n{eps_fname}\n\nPillow kurmak için: pip install pillow")

    # ══════════════════════════════════════════════════════════════════════════
    # Linked-List Görselleştiricisi
    # ══════════════════════════════════════════════════════════════════════════

    CMD_DISPLAY = {
        "ileri": "ILERI", "geri": "GERI", "sol": "SOL", "sag": "SAG",
        "dur": "DUR", "hiz": "HIZ",
        "kare": "KARE", "ucgen": "UCGEN", "yildiz": "YILDIZ", "spiral": "SPIRAL",
    }
    CMD_UNIT = {
        "ileri": "mm", "geri": "mm", "sol": "°", "sag": "°",
        "hiz": "%", "kare": "mm", "ucgen": "mm", "yildiz": "mm", "spiral": "mm",
    }

    def _render_ll(self):
        for w in self._ll_frame.winfo_children():
            w.destroy()

        q = list(self._local_q)

        if not q:
            ctk.CTkLabel(self._ll_frame,
                         text="[ Kuyruk boş ]  →  NULL",
                         font=("Consolas", 10),
                         text_color=RENK["muted"]).pack(pady=12)
            return

        visible = q[:14]

        for i, item in enumerate(visible):
            is_head = (i == 0)
            node_frame = ctk.CTkFrame(self._ll_frame, fg_color="transparent")
            node_frame.pack(fill="x", pady=0)

            bc = RENK["border"]
            bg = RENK["bg2"] if is_head else RENK["bg3"]
            box = ctk.CTkFrame(node_frame, fg_color=bg,
                               border_width=1, border_color=bc,
                               corner_radius=4, height=28)
            box.pack(fill="x", padx=4)
            box.pack_propagate(False)

            idx_lbl = "→" if is_head else f"{i+1:2d}"
            ctk.CTkLabel(box, text=idx_lbl, font=("Consolas", 9),
                         text_color=RENK["muted"], width=18).pack(side="left", padx=(4, 0))

            cmd_txt = self.CMD_DISPLAY.get(item["cmd"], item["cmd"].upper())
            ctk.CTkLabel(box, text=cmd_txt, font=("Consolas", 10, "bold"),
                         text_color=RENK["teal"], width=48).pack(side="left", padx=2)

            val = item.get("val", 0)
            unit = self.CMD_UNIT.get(item["cmd"], "")
            if val:
                v_str = f"{int(val*100)}{unit}" if item["cmd"] == "hiz" else f"{val:.0f}{unit}"
                ctk.CTkLabel(box, text=v_str, font=("Consolas", 9),
                             text_color=RENK["amber"]).pack(side="left", padx=2)

            ptr_txt = "*next →" if i < len(visible) - 1 else "NULL"
            ctk.CTkLabel(box, text=ptr_txt, font=("Consolas", 8),
                         text_color=RENK["muted"]).pack(side="right", padx=4)

            if i < len(visible) - 1:
                ctk.CTkLabel(node_frame, text="│", font=("Consolas", 8),
                             text_color=RENK["border"]).pack(anchor="w", padx=12)

        if len(q) > 14:
            ctk.CTkLabel(self._ll_frame,
                         text=f"  ↓  +{len(q)-14} daha…  →  NULL",
                         font=("Consolas", 9),
                         text_color=RENK["muted"]).pack(pady=2)
        else:
            ctk.CTkLabel(self._ll_frame, text="  └─  NULL",
                         font=("Consolas", 9),
                         text_color=RENK["muted"]).pack(pady=2)

    # ══════════════════════════════════════════════════════════════════════════
    # Klavye
    # ══════════════════════════════════════════════════════════════════════════

    def _bind_keys(self):
        self.bind("<KeyPress>",   self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)
        self.focus_set()

    def _on_key_press(self, event):
        key = event.keysym.lower()
        if key in self._keys:
            return
        self._keys.add(key)
        focused = self.focus_get()
        if isinstance(focused, (ctk.CTkEntry, tk.Entry)):
            return
        actions = {
            "w": lambda: self._cmd("ileri", self._dist()),
            "up": lambda: self._cmd("ileri", self._dist()),
            "s": lambda: self._cmd("geri",  self._dist()),
            "down": lambda: self._cmd("geri",  self._dist()),
            "a": lambda: self._cmd("sol",   self._ang()),
            "left": lambda: self._cmd("sol",   self._ang()),
            "d": lambda: self._cmd("sag",   self._ang()),
            "right": lambda: self._cmd("sag",   self._ang()),
            "space": self._acil,
            "r": self._temizle,
        }
        if key in actions:
            actions[key]()

    def _on_key_release(self, event):
        self._keys.discard(event.keysym.lower())

    def _on_close(self):
        self._disconnect()
        self.after(200, self.destroy)


# ── Giriş noktası ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = RobotArayuzu()
    app.mainloop()