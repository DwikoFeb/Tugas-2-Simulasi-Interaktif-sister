import time
import tkinter as tk

BG_DARK = "#0B0E14"           # latar utama, biru-hitam pekat
PANEL_BG = "#121826"          # latar panel/kartu
PANEL_BORDER = "#1E2738"      # garis tepi panel
TEXT_PRIMARY = "#C8D3E8"      # teks utama, abu-biru terang
TEXT_DIM = "#5C6B85"          # teks sekunder/caption
ACCENT_REQRES = "#5EE6C5"     # cyan-mint -> Request-Response
ACCENT_PUBSUB = "#F2A65A"     # oranye hangat -> Publish-Subscribe
ACCENT_OK = "#6FCF97"         # hijau -> sukses/ack
ACCENT_WARN = "#E0626B"       # merah -> drop/timeout/error
NODE_FILL = "#1A2233"         # isi kotak node
NODE_BORDER = "#2E3B57"       # tepi kotak node

FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_LABEL_NODE = ("Courier New", 9, "bold")

ANIM_TICK_MS = 16  
SIM_START_TIME = time.time()


def sim_clock_ms() -> int:
    """Mengembalikan waktu simulasi berjalan dalam milidetik sejak start."""
    return int((time.time() - SIM_START_TIME) * 1000)


def lerp(a: float, b: float, t: float) -> float:
    """Interpolasi linear antara a dan b pada parameter t in [0,1]."""
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    """Easing kubik supaya gerakan partikel pesan terasa natural, bukan linear kaku."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def make_panel(parent, title, expand=False):
    outer = tk.Frame(parent, bg=PANEL_BORDER)
    outer.pack(fill="both" if expand else "x", expand=expand, pady=(0, 10))
    inner = tk.Frame(outer, bg=PANEL_BG)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Label(inner, text=title, bg=PANEL_BG, fg=TEXT_DIM, font=("Segoe UI", 8, "bold")
              ).pack(anchor="w", padx=10, pady=(8, 2))
    return inner


def make_metric_row(parent, label, value):
    row = tk.Frame(parent, bg=PANEL_BG)
    row.pack(fill="x", padx=10, pady=2)
    tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT_DIM, font=("Segoe UI", 8)
              ).pack(side="left")
    val = tk.Label(row, text=value, bg=PANEL_BG, fg=TEXT_PRIMARY, font=("Courier New", 9, "bold"))
    val.pack(side="right")
    return val
