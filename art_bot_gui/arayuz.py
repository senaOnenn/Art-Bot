import tkinter as tk
import threading
import math
import json
import websocket

ROBOT_IP = "192.168.4.1"
WS_URL   = f"ws://{ROBOT_IP}/ws"

BG      = "#0a0a0f"
SURFACE = "#12121a"
BORDER  = "#1e1e2e"
ACCENT  = "#00e5ff"
ACCENT2 = "#ff4081"
TEXT    = "#e8e8e8"
MUTED   = "#606080"
OK      = "#00c853"
WARN    = "#ff9800"
GERI_C  = "#7c4dff"

ws_app    = None
kuyruk    = []
calisiyor = False
yollar    = [{"x": 0, "y": 0}]
pos_x, pos_y, pos_yon = 0.0, 0.0, 0.0

OLCEK = 14   # 8'den 14'e çıkarıldı — çizim daha büyük
MX    = 0
MY    = 0

def ws_gonder(obj):
    global ws_app
    if ws_app:
        try: ws_app.send(json.dumps(obj))
        except: pass

def ws_mesaj(ws, message):
    global calisiyor, pos_x, pos_y, pos_yon, yollar
    try:
        d = json.loads(message)
        t = d.get("type", "")
        if t == "pos":
            pos_x   = d.get("x", 0)
            pos_y   = d.get("y", 0)
            pos_yon = d.get("yon", 0)
            if not yollar or abs(yollar[-1]["x"]-pos_x)>0.05 or abs(yollar[-1]["y"]-pos_y)>0.05:
                yollar.append({"x": pos_x, "y": pos_y})
            root.after(0, konum_guncelle_ui)
        elif t == "status":
            mod = d.get("mod", "")
            calisiyor = (mod == "Calisiyor")
            root.after(0, lambda m=mod: status_guncelle_ui(m))
        elif t == "queue":
            items = d.get("items", [])
            root.after(0, lambda it=items: kuyruk_guncelle_ui(it))
    except Exception as e:
        print("WS hata:", e)

def ws_ac(ws):
    root.after(0, lambda: bag_label.config(text="● BAĞLI", fg=OK))

def ws_kapat(ws, code, msg):
    root.after(0, lambda: bag_label.config(text="● KESİLDİ", fg=ACCENT2))
    threading.Timer(3, ws_baslat).start()

def ws_hata(ws, err):
    root.after(0, lambda: bag_label.config(text="● HATA", fg=WARN))

def ws_baslat():
    global ws_app
    try:
        ws_app = websocket.WebSocketApp(
            WS_URL, on_open=ws_ac, on_message=ws_mesaj,
            on_close=ws_kapat, on_error=ws_hata)
        threading.Thread(target=ws_app.run_forever, daemon=True).start()
    except Exception as e:
        print("Bağlantı hatası:", e)

def konum_guncelle_ui():
    lbl_x.config(text=f"X: {pos_x:.1f} cm")
    lbl_y.config(text=f"Y: {pos_y:.1f} cm")
    lbl_yon.config(text=f"Yön: {pos_yon:.0f}°")
    cizimi_yenile()

def status_guncelle_ui(mod):
    renk = WARN if mod=="Calisiyor" else OK if mod=="Tamamlandi" else ACCENT
    lbl_mod.config(text=mod.upper(), fg=renk)
    disabled = tk.DISABLED if mod=="Calisiyor" else tk.NORMAL
    for b in [btn_ileri, btn_geri,
              btn_sag90, btn_sol90,
              btn_sag60, btn_sol60,
              btn_sag45, btn_sol45,
              btn_sag120, btn_sol120,
              btn_sag180, btn_run, btn_temizle]:
        b.config(state=disabled)

def kuyruk_guncelle_ui(items):
    global kuyruk
    kuyruk = list(items)
    kuyruk_listbox.delete(0, tk.END)
    icons = {
        "ILERI":  "▲ İLERİ",
        "GERI":   "▼ GERİ",
        "SAG90":  "↻ SAĞ 90°",
        "SOL90":  "↺ SOL 90°",
        "SAG60":  "↻ SAĞ 60°",
        "SOL60":  "↺ SOL 60°",
        "SAG45":  "↘ SAĞ 45°",
        "SOL45":  "↙ SOL 45°",
        "SAG120": "↻ SAĞ 120°",
        "SOL120": "↺ SOL 120°",
        "SAG180": "↻ 180°",
    }
    for i, k in enumerate(items):
        kuyruk_listbox.insert(tk.END, f"  {i+1:02d}  {icons.get(k,k)}")
    lbl_kuyruk_sayi.config(text=f"{len(items)} komut")

def ekle(cmd):
    if calisiyor: return
    ws_gonder({"type": "add", "cmd": cmd})

def calistir():
    if calisiyor or not kuyruk: return
    ws_gonder({"type": "run"})

def acil_stop():
    ws_gonder({"type": "stop"})

def temizle():
    if calisiyor: return
    ws_gonder({"type": "clear"})
    global yollar, pos_x, pos_y, pos_yon
    pos_x = 0.0
    pos_y = 0.0
    pos_yon = 0.0
    yollar.clear()
    yollar.append({"x": 0, "y": 0})
    ws_gonder({"type": "reset"})
    konum_guncelle_ui()

def sifirla():
    global yollar, pos_x, pos_y, pos_yon
    pos_x = 0.0
    pos_y = 0.0
    pos_yon = 0.0
    yollar.clear()
    yollar.append({"x": 0, "y": 0})
    ws_gonder({"type": "reset"})
    konum_guncelle_ui()

def cizimi_yenile():
    global MX, MY
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if w < 10 or h < 10: return
    MX = w // 2
    MY = h // 2

    canvas.delete("all")
    canvas.create_rectangle(0, 0, w, h, fill="#080810", outline="")

    # Izgara — OLCEK'e göre dinamik aralık
    grid_px = OLCEK * 5   # her 5 cm'de bir çizgi
    for x in range(MX % grid_px, w, grid_px):
        canvas.create_line(x, 0, x, h, fill="#0d0d1e", width=1)
    for y in range(MY % grid_px, h, grid_px):
        canvas.create_line(0, y, w, y, fill="#0d0d1e", width=1)

    canvas.create_line(MX, 0, MX, h, fill="#1a1a35", width=1, dash=(4,4))
    canvas.create_line(0, MY, w, MY, fill="#1a1a35", width=1, dash=(4,4))
    canvas.create_text(MX+10, 14,    text="+Y", fill=MUTED, font=("Consolas", 9))
    canvas.create_text(w-20,  MY-12, text="+X", fill=MUTED, font=("Consolas", 9))

    # Yol
    if len(yollar) >= 2:
        for i in range(1, len(yollar)):
            x1 = MX + yollar[i-1]["x"] * OLCEK
            y1 = MY - yollar[i-1]["y"] * OLCEK
            x2 = MX + yollar[i]["x"]   * OLCEK
            y2 = MY - yollar[i]["y"]   * OLCEK
            canvas.create_line(x1,y1,x2,y2, fill="#004455", width=5, capstyle=tk.ROUND)
            canvas.create_line(x1,y1,x2,y2, fill=ACCENT,   width=2, capstyle=tk.ROUND)

    for pt in yollar[:-1]:
        px = MX + pt["x"] * OLCEK
        py = MY - pt["y"] * OLCEK
        canvas.create_oval(px-3,py-3,px+3,py+3, fill=ACCENT, outline="")

    # Başlangıç noktası
    canvas.create_oval(MX-8,MY-8,MX+8,MY+8, fill="", outline=OK, width=2)
    canvas.create_oval(MX-3,MY-3,MX+3,MY+3, fill=OK, outline="")

    # Robot
    rx = MX + pos_x * OLCEK
    ry = MY - pos_y * OLCEK
    canvas.create_oval(rx-16,ry-16,rx+16,ry+16, fill="", outline="#ff408133", width=1)
    canvas.create_oval(rx-11,ry-11,rx+11,ry+11, fill="#1a0010", outline=ACCENT2, width=2)
    canvas.create_oval(rx-5, ry-5, rx+5, ry+5,  fill=ACCENT2, outline="")

    rad = math.radians(pos_yon)
    ox = rx + 20 * math.sin(rad)
    oy = ry - 20 * math.cos(rad)
    canvas.create_line(rx,ry,ox,oy, fill=ACCENT2, width=2,
                       arrow=tk.LAST, arrowshape=(9,11,4))

    canvas.create_text(rx+15,ry-15,
                       text=f"({pos_x:.0f},{pos_y:.0f})",
                       fill=TEXT, font=("Consolas", 9), anchor="w")

def klavye_bind(event):
    k = event.keysym
    if   k=="Up":     ekle("ILERI")
    elif k=="Down":   ekle("GERI")
    elif k=="Right":  ekle("SAG90")
    elif k=="Left":   ekle("SOL90")
    elif k=="Return": calistir()
    elif k=="Escape": acil_stop()

# ============================================
# PENCERE
# ============================================
root = tk.Tk()
root.title("ArtBot Kontrol Paneli v8.1")
root.configure(bg=BG)
root.attributes("-fullscreen", True)
root.bind("<F11>",     lambda e: root.attributes("-fullscreen", True))
root.bind("<KeyPress>", klavye_bind)

# HEADER
header = tk.Frame(root, bg=SURFACE, height=48)
header.pack(fill=tk.X)
header.pack_propagate(False)
tk.Label(header, text="ART", bg=SURFACE, fg=ACCENT,
         font=("Consolas",16,"bold")).pack(side=tk.LEFT, padx=(20,0))
tk.Label(header, text="BOT", bg=SURFACE, fg=TEXT,
         font=("Consolas",16,"bold")).pack(side=tk.LEFT)
tk.Label(header, text="v8.1  |  5cm adım  |  Eş Zamanlı Odometri",
         bg=SURFACE, fg=MUTED, font=("Consolas",9)).pack(side=tk.LEFT, padx=20)
bag_label = tk.Label(header, text="● BAĞLANIYOR...",
                      bg=SURFACE, fg=MUTED, font=("Consolas",9,"bold"))
bag_label.pack(side=tk.RIGHT, padx=20)
tk.Button(header, text="F11: Tam Ekran  |  ESC: Çık",
          bg=BORDER, fg=MUTED, font=("Consolas",8), bd=0, padx=8,
          command=lambda: root.attributes("-fullscreen",
                            not root.attributes("-fullscreen"))
          ).pack(side=tk.RIGHT, padx=4)

# LAYOUT
layout = tk.Frame(root, bg=BG)
layout.pack(fill=tk.BOTH, expand=True)

# SOL panel — genişliği 200'e düşürüldü, canvas'a daha fazla yer
sol = tk.Frame(layout, bg=SURFACE, width=200)
sol.pack(side=tk.LEFT, fill=tk.Y)
sol.pack_propagate(False)

def sep(p): tk.Frame(p, bg=BORDER, height=1).pack(fill=tk.X, padx=10, pady=3)
def sec_baslik(p, t):
    tk.Label(p, text=t, bg=SURFACE, fg=MUTED,
             font=("Consolas",8)).pack(anchor="w", padx=14, pady=(8,2))

def komut_btn(p, text, color, fg_c, cmd):
    b = tk.Button(p, text=text, bg=color, fg=fg_c,
                  font=("Consolas",10,"bold"), bd=0, pady=8,
                  cursor="hand2", activebackground=color, activeforeground=fg_c,
                  command=cmd)
    b.pack(fill=tk.X, padx=10, pady=1)
    return b

sec_baslik(sol, "BAĞLANTI")
tk.Button(sol, text="↺  Yeniden Bağlan",
          bg=BORDER, fg=TEXT, font=("Consolas",9),
          bd=0, pady=6, cursor="hand2",
          command=ws_baslat).pack(fill=tk.X, padx=10, pady=2)
sep(sol)

sec_baslik(sol, "KONUM")
konum_frame = tk.Frame(sol, bg=SURFACE)
konum_frame.pack(fill=tk.X, padx=12)
lbl_x   = tk.Label(konum_frame, text="X: 0.0 cm", bg=SURFACE, fg=ACCENT,
                    font=("Consolas",11,"bold"), anchor="w")
lbl_x.pack(fill=tk.X)
lbl_y   = tk.Label(konum_frame, text="Y: 0.0 cm", bg=SURFACE, fg=ACCENT,
                    font=("Consolas",11,"bold"), anchor="w")
lbl_y.pack(fill=tk.X)
lbl_yon = tk.Label(konum_frame, text="Yön: 0°",   bg=SURFACE, fg=ACCENT2,
                    font=("Consolas",11,"bold"), anchor="w")
lbl_yon.pack(fill=tk.X)
lbl_mod = tk.Label(sol, text="BEKLİYOR", bg=SURFACE, fg=OK,
                    font=("Consolas",10,"bold"))
lbl_mod.pack(pady=3)
sep(sol)

sec_baslik(sol, "HAREKET  (ok tuşları)")
btn_ileri  = komut_btn(sol, "▲  İLERİ",    ACCENT,    "#000", lambda: ekle("ILERI"))
btn_geri   = komut_btn(sol, "▼  GERİ",     GERI_C,    "#fff", lambda: ekle("GERI"))
btn_sag90  = komut_btn(sol, "↻  SAĞ 90°",  BORDER,    TEXT,   lambda: ekle("SAG90"))
btn_sol90  = komut_btn(sol, "↺  SOL 90°",  BORDER,    TEXT,   lambda: ekle("SOL90"))
btn_sag60  = komut_btn(sol, "↻  SAĞ 60°",  "#162020", TEXT,   lambda: ekle("SAG60"))
btn_sol60  = komut_btn(sol, "↺  SOL 60°",  "#162020", TEXT,   lambda: ekle("SOL60"))
btn_sag45  = komut_btn(sol, "↘  SAĞ 45°",  "#162016", TEXT,   lambda: ekle("SAG45"))
btn_sol45  = komut_btn(sol, "↙  SOL 45°",  "#162016", TEXT,   lambda: ekle("SOL45"))
btn_sag120 = komut_btn(sol, "↻  SAĞ 120°", "#201616", TEXT,   lambda: ekle("SAG120"))
btn_sol120 = komut_btn(sol, "↺  SOL 120°", "#201616", TEXT,   lambda: ekle("SOL120"))
btn_sag180 = komut_btn(sol, "↻  180°",     "#201620", TEXT,   lambda: ekle("SAG180"))
sep(sol)

sec_baslik(sol, "KONTROL  (Enter)")
btn_run     = komut_btn(sol, "▶  ÇALIŞTIR",        OK,      "#000", calistir)
btn_stop    = komut_btn(sol, "■  ACİL STOP",       ACCENT2, "#fff", acil_stop)
btn_temizle = komut_btn(sol, "✕  KUYRUĞU TEMİZLE", BORDER,  TEXT,   temizle)
btn_sifirla = komut_btn(sol, "◎  ÇİZİMİ SIFIRLA",  BORDER,  TEXT,   sifirla)

# SAĞ panel (kuyruk) — 210px
sag = tk.Frame(layout, bg=SURFACE, width=210)
sag.pack(side=tk.RIGHT, fill=tk.Y)
sag.pack_propagate(False)

kh = tk.Frame(sag, bg=BORDER, height=36)
kh.pack(fill=tk.X); kh.pack_propagate(False)
tk.Label(kh, text="KOMUT KUYRUĞU", bg=BORDER, fg=ACCENT,
         font=("Consolas",10,"bold")).pack(side=tk.LEFT, padx=12)
lbl_kuyruk_sayi = tk.Label(kh, text="0 komut", bg=BORDER, fg=MUTED,
                             font=("Consolas",8))
lbl_kuyruk_sayi.pack(side=tk.RIGHT, padx=8)

kf = tk.Frame(sag, bg=SURFACE)
kf.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
sb = tk.Scrollbar(kf, bg=BORDER, troughcolor=SURFACE, highlightthickness=0)
sb.pack(side=tk.RIGHT, fill=tk.Y)
kuyruk_listbox = tk.Listbox(kf, bg=BG, fg=TEXT, font=("Consolas",11),
                              selectbackground=BORDER, selectforeground=ACCENT,
                              bd=0, highlightthickness=0, activestyle="none",
                              yscrollcommand=sb.set)
kuyruk_listbox.pack(fill=tk.BOTH, expand=True)
sb.config(command=kuyruk_listbox.yview)
tk.Label(sag, text="Sırasıyla çalıştırılır.",
         bg=SURFACE, fg=MUTED, font=("Consolas",8)).pack(pady=6)

# ORTA CANVAS — artık daha geniş
canvas_frame = tk.Frame(layout, bg=BG)
canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
canvas = tk.Canvas(canvas_frame, bg="#080810", bd=0,
                    highlightthickness=1, highlightbackground=BORDER)
canvas.pack(fill=tk.BOTH, expand=True)
canvas.bind("<Configure>", lambda e: cizimi_yenile())

cizimi_yenile()
ws_baslat()
root.mainloop()