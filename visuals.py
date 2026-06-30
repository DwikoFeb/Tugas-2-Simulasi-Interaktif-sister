#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visuals.py
==========
Mesin animasi kanvas generik, dipakai bersama oleh kedua tab model
komunikasi supaya gaya visual & UX konsisten. Terdiri dari dua kelas:

  - NodeVisual      : kotak node (Client/Server/Broker, dst)
  - MessageParticle  : titik bercahaya yang bergerak dari node A ke node B,
                        merepresentasikan satu MessageEvent "in transit"
"""

import math
import tkinter as tk
from typing import Optional, Callable

from config import (
    BG_DARK, NODE_FILL, NODE_BORDER, TEXT_PRIMARY, TEXT_DIM,
    ACCENT_REQRES, ACCENT_WARN, FONT_LABEL_NODE, sim_clock_ms, ease_in_out,
)


class NodeVisual:
    """
    Representasi visual sebuah komponen sistem (node) di atas kanvas Tkinter.
    Digambar sebagai kotak rounded dengan label nama, sublabel status, dan
    counter jumlah pesan yang sudah diproses node tersebut.
    """

    def __init__(self, canvas: tk.Canvas, x: float, y: float, w: float, h: float,
                 name: str, subtitle: str = "", accent: str = ACCENT_REQRES,
                 shape: str = "box"):
        self.canvas = canvas
        self.x, self.y, self.w, self.h = x, y, w, h
        self.name = name
        self.subtitle = subtitle
        self.accent = accent
        self.shape = shape  # "box" untuk server/client, "drum" untuk queue
        self.processed_count = 0
        self.pulse = 0.0          # 0..1, dipakai untuk efek "berkedip" saat menerima pesan
        self.active = False
        self._ids = []
        self.draw()

    def trigger_pulse(self):
        """Memicu efek kedip pada node, dipanggil saat node menerima pesan."""
        self.pulse = 1.0
        self.active = True

    def bump_count(self):
        self.processed_count += 1

    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def anchor_point(self, towards_xy):
        """
        Titik di tepi kotak node yang menghadap ke arah (towards_xy),
        supaya garis/partikel pesan tampak keluar/masuk dari sisi kotak,
        bukan menembus tengah kotak.
        """
        cx, cy = self.center()
        tx, ty = towards_xy
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return (cx, cy)
        # Cari skala terkecil agar titik (cx + dx*scale, cy + dy*scale)
        # tepat berhenti di tepi kotak (pendekatan sederhana berbasis
        # setengah lebar/tinggi kotak, cukup akurat untuk kebutuhan visual).
        scale_x = (self.w / 2) / (abs(dx) + 1e-6)
        scale_y = (self.h / 2) / (abs(dy) + 1e-6)
        scale = min(scale_x, scale_y)
        ex = cx + dx * scale
        ey = cy + dy * scale
        # Klem ke dalam batas kotak untuk jaga-jaga pada kasus tepi ekstrem.
        ex = max(self.x, min(self.x + self.w, ex))
        ey = max(self.y, min(self.y + self.h, ey))
        return (ex, ey)

    def clear(self):
        for i in self._ids:
            self.canvas.delete(i)
        self._ids = []

    def draw(self):
        self.clear()
        c = self.canvas
        glow_strength = self.pulse
        # Efek glow halus di belakang kotak ketika baru dipicu pulse
        if glow_strength > 0.02:
            pad = 6 * glow_strength
            glow = c.create_rectangle(
                self.x - pad, self.y - pad, self.x + self.w + pad, self.y + self.h + pad,
                outline=self.accent, width=2, fill="")
            self._ids.append(glow)

        border_color = self.accent if self.active else NODE_BORDER
        body = c.create_rectangle(
            self.x, self.y, self.x + self.w, self.y + self.h,
            fill=NODE_FILL, outline=border_color, width=2)
        self._ids.append(body)

        # Strip kecil di kiri atas sebagai aksen warna kategori node
        strip = c.create_rectangle(
            self.x, self.y, self.x + 5, self.y + self.h,
            fill=self.accent, outline="")
        self._ids.append(strip)

        name_id = c.create_text(
            self.x + self.w / 2 + 3, self.y + self.h / 2 - (8 if self.subtitle else 0),
            text=self.name, fill=TEXT_PRIMARY, font=FONT_LABEL_NODE)
        self._ids.append(name_id)

        if self.subtitle:
            sub_id = c.create_text(
                self.x + self.w / 2 + 3, self.y + self.h / 2 + 9,
                text=self.subtitle, fill=TEXT_DIM, font=("Courier New", 8))
            self._ids.append(sub_id)

        # Badge counter pojok kanan atas
        badge_x = self.x + self.w - 2
        badge_y = self.y - 2
        badge = c.create_oval(badge_x - 11, badge_y - 9, badge_x + 11, badge_y + 9,
                               fill=BG_DARK, outline=self.accent, width=1.5)
        self._ids.append(badge)
        badge_text = c.create_text(badge_x, badge_y, text=str(self.processed_count),
                                    fill=self.accent, font=("Courier New", 8, "bold"))
        self._ids.append(badge_text)

    def step_animation(self):
        """Dipanggil tiap tick: meluruhkan efek pulse secara bertahap."""
        if self.pulse > 0:
            self.pulse = max(0.0, self.pulse - 0.06)
            if self.pulse == 0:
                self.active = False
            self.draw()


class MessageParticle:
    """
    Satu partikel visual yang bergerak dari node sumber ke node tujuan di
    atas kanvas, merepresentasikan sebuah MessageEvent yang sedang "in
    transit" melalui jaringan. Mendukung jalur melengkung (curve) opsional
    supaya pesan request dan response yang lewat jalur sama tidak saling
    tumpang tindih secara visual.
    """

    def __init__(self, canvas: tk.Canvas, x0, y0, x1, y1, duration_ms: int,
                 color: str, label: str = "", curve: float = 0.0,
                 on_complete: Optional[Callable[[], None]] = None,
                 will_drop: bool = False, radius: float = 6.0):
        self.canvas = canvas
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.duration_ms = max(duration_ms, 50)
        self.color = color
        self.label = label
        self.curve = curve  # offset tegak lurus garis lurus, untuk lengkungan
        self.start_time = sim_clock_ms()
        self.on_complete = on_complete
        self.will_drop = will_drop
        self.radius = radius
        self.finished = False
        self._ids = []
        self.trail_positions = []  # untuk efek jejak (trail) di belakang partikel

    def _bezier_point(self, t):
        """Posisi di sepanjang kurva kuadratik sederhana pada parameter t."""
        mx, my = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2
        # Titik kontrol digeser tegak lurus terhadap garis lurus sejauh self.curve
        dx, dy = self.x1 - self.x0, self.y1 - self.y0
        length = math.hypot(dx, dy) + 1e-6
        nx, ny = -dy / length, dx / length  # vektor normal satuan
        cx, cy = mx + nx * self.curve, my + ny * self.curve
        x = (1 - t) ** 2 * self.x0 + 2 * (1 - t) * t * cx + t ** 2 * self.x1
        y = (1 - t) ** 2 * self.y0 + 2 * (1 - t) * t * cy + t ** 2 * self.y1
        return x, y

    def progress(self):
        elapsed = sim_clock_ms() - self.start_time
        return min(1.0, elapsed / self.duration_ms)

    def clear(self):
        for i in self._ids:
            self.canvas.delete(i)
        self._ids = []

    def step_and_draw(self) -> bool:
        """
        Menggambar ulang posisi partikel untuk frame saat ini.
        Mengembalikan True jika partikel masih bergerak (belum selesai),
        False jika sudah mencapai tujuan (lalu dibersihkan dari kanvas).
        """
        self.clear()
        t_raw = self.progress()

        # Jika pesan akan "drop", animasinya berhenti di tengah jalan (60%)
        # dan memudar, mensimulasikan paket yang hilang di jaringan.
        if self.will_drop and t_raw >= 0.6:
            fade_t = (t_raw - 0.6) / 0.4
            if fade_t >= 1.0:
                self.finished = True
                if self.on_complete:
                    self.on_complete()
                return False
            x, y = self._bezier_point(0.6)
            alpha_color = ACCENT_WARN
            r = self.radius * (1.0 - fade_t * 0.6)
            c = self.canvas
            self._ids.append(c.create_oval(x - r, y - r, x + r, y + r,
                                            fill="", outline=alpha_color, width=2))
            self._ids.append(c.create_text(x, y - 14, text="✕ drop", fill=ACCENT_WARN,
                                            font=("Courier New", 8, "bold")))
            return True

        t = ease_in_out(t_raw)
        x, y = self._bezier_point(t)

        c = self.canvas
        # Jejak/trail halus di belakang partikel untuk kesan "kecepatan"
        for i, frac in enumerate((0.18, 0.10)):
            t_trail = max(0.0, t_raw - frac)
            tx, ty = self._bezier_point(ease_in_out(t_trail))
            trail_r = self.radius * (0.55 - i * 0.15)
            self._ids.append(c.create_oval(tx - trail_r, ty - trail_r,
                                            tx + trail_r, ty + trail_r,
                                            fill="", outline=self.color, width=1))

        glow = c.create_oval(x - self.radius - 3, y - self.radius - 3,
                              x + self.radius + 3, y + self.radius + 3,
                              fill="", outline=self.color, width=1)
        self._ids.append(glow)
        dot = c.create_oval(x - self.radius, y - self.radius,
                             x + self.radius, y + self.radius,
                             fill=self.color, outline="")
        self._ids.append(dot)

        if self.label:
            txt = c.create_text(x, y - 14, text=self.label, fill=self.color,
                                 font=("Courier New", 8, "bold"))
            self._ids.append(txt)

        if t_raw >= 1.0:
            self.finished = True
            self.clear()
            if self.on_complete:
                self.on_complete()
            return False
        return True

