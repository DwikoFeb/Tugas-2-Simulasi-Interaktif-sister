#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tabs/request_response.py
=========================
Implementasi tab MODEL 1 -- REQUEST-RESPONSE (sinkron, point-to-point).

LOGIKA INTERAKSI:
  1. User menekan "Kirim Request" pada Client.
  2. Client membuat MessageEvent(kind="request") dan mengirimkannya ke
     Server. Secara visual: partikel hijau bergerak Client -> Server
     selama `latency_ms` (durasi dapat diatur via slider, mensimulasikan
     kondisi jaringan).
  3. Saat partikel tiba di Server: Server "memproses" (delay singkat
     acak, mensimulasikan waktu komputasi), lalu membuat
     MessageEvent(kind="response") dan mengirim balik ke Client.
  4. Client menerima response -> dicatat sebagai SATU siklus request-
     response selesai, latensi round-trip dihitung dan disimpan ke metrik.
  5. Jika slider "Probabilitas Gagal" terpenuhi (mensimulasikan server
     down/timeout), response TIDAK dikirim balik -- partikel "drop" di
     tengah jalan dan Client mencatatnya sebagai TIMEOUT.

SIFAT KUNCI YANG DIPERAGAKAN:
  - Sifat SYNCHRONOUS/BLOCKING secara logis: Client tidak bisa "lanjut"
    (tombol dinonaktifkan sementara) sampai response diterima/timeout --
    ini secara sengaja berbeda dari Pub-Sub & Queue yang fire-and-forget.
  - Coupling 1-ke-1: selalu tepat satu Server yang menjawab tepat satu
    Client untuk tiap request.
"""

import random
import tkinter as tk

from config import (
    BG_DARK, PANEL_BG, PANEL_BORDER, TEXT_PRIMARY, TEXT_DIM,
    ACCENT_REQRES, ACCENT_PUBSUB, ACCENT_OK, ACCENT_WARN,
    FONT_UI, FONT_UI_BOLD, FONT_TITLE,
    sim_clock_ms, make_panel, make_metric_row,
)
from visuals import NodeVisual, MessageParticle


class RequestResponseTab:
    """Tab simulasi model Request-Response (synchronous, point-to-point)."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=BG_DARK)
        self.particles = []
        self.msg_counter = 0
        self.awaiting_response = False
        self.latencies = []          # histori latensi round-trip (ms)
        self.total_sent = 0
        self.total_failed = 0

        self._build_layout()
        self._build_nodes()

    # -- konstruksi UI --
    def _build_layout(self):
        f = self.frame
        title = tk.Label(f, text="MODEL 1 — REQUEST-RESPONSE  (Sinkron, Point-to-Point)",
                          bg=BG_DARK, fg=ACCENT_REQRES, font=FONT_TITLE, anchor="w")
        title.pack(fill="x", padx=16, pady=(14, 2))

        desc = ("Client mengirim permintaan dan MENUNGGU balasan sebelum lanjut.\n"
                "Analogi dunia nyata: panggilan REST API seperti GET /produk/123.")
        tk.Label(f, text=desc, bg=BG_DARK, fg=TEXT_DIM, font=FONT_UI, justify="left",
                 anchor="w").pack(fill="x", padx=16, pady=(0, 10))

        body = tk.Frame(f, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Kanvas kiri (visual)
        canvas_wrap = tk.Frame(body, bg=PANEL_BORDER)
        canvas_wrap.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_wrap, bg=PANEL_BG, highlightthickness=0,
                                 width=560, height=380)
        self.canvas.pack(fill="both", expand=True, padx=1, pady=1)

        # Panel kanan (kontrol + log + metrik)
        side = tk.Frame(body, bg=BG_DARK, width=300)
        side.pack(side="left", fill="y", padx=(14, 0))
        side.pack_propagate(False)

        ctrl_panel = self._panel(side, "KONTROL")
        tk.Label(ctrl_panel, text="Ukuran payload (KB):", bg=PANEL_BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(8, 0))
        self.payload_var = tk.IntVar(value=4)
        tk.Scale(ctrl_panel, from_=1, to=50, orient="horizontal", variable=self.payload_var,
                  bg=PANEL_BG, fg=TEXT_PRIMARY, troughcolor=PANEL_BORDER,
                  highlightthickness=0, font=("Segoe UI", 8)).pack(fill="x", padx=10)

        tk.Label(ctrl_panel, text="Latensi jaringan (ms):", bg=PANEL_BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(6, 0))
        self.latency_var = tk.IntVar(value=600)
        tk.Scale(ctrl_panel, from_=100, to=2000, orient="horizontal", variable=self.latency_var,
                  bg=PANEL_BG, fg=TEXT_PRIMARY, troughcolor=PANEL_BORDER,
                  highlightthickness=0, font=("Segoe UI", 8)).pack(fill="x", padx=10)

        tk.Label(ctrl_panel, text="Probabilitas server gagal (%):", bg=PANEL_BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(6, 0))
        self.fail_var = tk.IntVar(value=15)
        tk.Scale(ctrl_panel, from_=0, to=80, orient="horizontal", variable=self.fail_var,
                  bg=PANEL_BG, fg=TEXT_PRIMARY, troughcolor=PANEL_BORDER,
                  highlightthickness=0, font=("Segoe UI", 8)).pack(fill="x", padx=10, pady=(0, 8))

        self.btn_send = tk.Button(ctrl_panel, text="▶  Kirim Request", command=self.send_request,
                                   bg=ACCENT_REQRES, fg="#06231C", activebackground="#7BF0D4",
                                   font=FONT_UI_BOLD, relief="flat", cursor="hand2", pady=6)
        self.btn_send.pack(fill="x", padx=10, pady=(2, 10))

        metric_panel = self._panel(side, "METRIK")
        self.lbl_sent = self._metric_row(metric_panel, "Total request terkirim", "0")
        self.lbl_failed = self._metric_row(metric_panel, "Gagal / timeout", "0")
        self.lbl_avg_latency = self._metric_row(metric_panel, "Rata-rata latensi round-trip", "- ms")
        self.lbl_status = self._metric_row(metric_panel, "Status Client", "IDLE")

        log_panel = self._panel(side, "LOG AKTIVITAS", expand=True)
        self.log_box = tk.Listbox(log_panel, bg=PANEL_BG, fg=TEXT_PRIMARY,
                                   font=("Courier New", 8), highlightthickness=0,
                                   relief="flat", selectbackground=PANEL_BORDER)
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

    def _panel(self, parent, title, expand=False):
        return make_panel(parent, title, expand)

    def _metric_row(self, parent, label, value):
        return make_metric_row(parent, label, value)

    def _build_nodes(self):
        self.canvas.update_idletasks()
        self.node_client = NodeVisual(self.canvas, 50, 160, 130, 70, "CLIENT",
                                       "request initiator", ACCENT_REQRES)
        self.node_server = NodeVisual(self.canvas, 380, 160, 130, 70, "SERVER",
                                       "request handler", ACCENT_REQRES)
        for n in (self.node_client, self.node_server):
            n.draw()
        self._draw_static_link()

    def _draw_static_link(self):
        c = self.canvas
        x0, y0 = self.node_client.center()
        x1, y1 = self.node_server.center()
        c.create_line(x0 + 65, y0, x1 - 65, y1, fill=PANEL_BORDER, width=1, dash=(3, 3))

    def log(self, text, ts=None):
        ts = ts if ts is not None else sim_clock_ms()
        self.log_box.insert(0, f"[{ts:>7} ms] {text}")
        if self.log_box.size() > 200:
            self.log_box.delete(200, tk.END)

    # -- logika interaksi inti --
    def send_request(self):
        if self.awaiting_response:
            return  # SIFAT SYNCHRONOUS: tidak bisa kirim request baru sebelum response diterima
        self.awaiting_response = True
        self.btn_send.config(state="disabled", text="⏳ Menunggu response...")
        self.lbl_status.config(text="WAITING", fg=ACCENT_PUBSUB)

        self.msg_counter += 1
        mid = self.msg_counter
        size_kb = self.payload_var.get()
        latency = self.latency_var.get()
        will_fail = random.randint(1, 100) <= self.fail_var.get()

        self.total_sent += 1
        sent_at = sim_clock_ms()
        self.log(f"REQUEST #{mid} dikirim Client -> Server ({size_kb} KB)", sent_at)

        x0, y0 = self.node_client.anchor_point(self.node_server.center())
        x1, y1 = self.node_server.anchor_point(self.node_client.center())

        def on_request_arrived():
            self.node_server.trigger_pulse()
            self.node_server.bump_count()
            if will_fail:
                self.total_failed += 1
                self.log(f"REQUEST #{mid} GAGAL diproses Server (timeout/error)", sim_clock_ms())
                self.lbl_status.config(text="TIMEOUT", fg=ACCENT_WARN)
                self._finish_cycle()
                return
            # Server "memproses" lalu mengirim balik response
            process_delay = random.randint(80, 260)
            self.app.root.after(process_delay, lambda: self._send_response(mid, sent_at, latency))

        particle = MessageParticle(self.canvas, x0, y0, x1, y1, duration_ms=latency,
                                    color=ACCENT_OK, label=f"REQ#{mid}", curve=-22,
                                    on_complete=on_request_arrived, will_drop=False)
        self.particles.append(particle)

    def _send_response(self, mid, sent_at, latency):
        x0, y0 = self.node_server.anchor_point(self.node_client.center())
        x1, y1 = self.node_client.anchor_point(self.node_server.center())

        def on_response_arrived():
            self.node_client.trigger_pulse()
            self.node_client.bump_count()
            rtt = sim_clock_ms() - sent_at
            self.latencies.append(rtt)
            self.log(f"RESPONSE #{mid} diterima Client (RTT = {rtt} ms)", sim_clock_ms())
            self.lbl_status.config(text="OK", fg=ACCENT_OK)
            self._finish_cycle()

        particle = MessageParticle(self.canvas, x0, y0, x1, y1, duration_ms=latency,
                                    color=ACCENT_PUBSUB, label=f"RES#{mid}", curve=22,
                                    on_complete=on_response_arrived, will_drop=False)
        self.particles.append(particle)

    def _finish_cycle(self):
        self.awaiting_response = False
        self.btn_send.config(state="normal", text="▶  Kirim Request")
        self.lbl_sent.config(text=str(self.total_sent))
        self.lbl_failed.config(text=str(self.total_failed))
        if self.latencies:
            avg = sum(self.latencies) / len(self.latencies)
            self.lbl_avg_latency.config(text=f"{avg:.0f} ms")
        self.app.refresh_comparison_tab()

    # -- dipanggil oleh game loop utama setiap tick --
    def step_animation(self):
        self.node_client.step_animation()
        self.node_server.step_animation()
        still_alive = []
        for p in self.particles:
            if p.step_and_draw():
                still_alive.append(p)
        self.particles = still_alive

    def get_metrics(self):
        avg = (sum(self.latencies) / len(self.latencies)) if self.latencies else 0
        return {
            "model": "Request-Response",
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "success_rate": (1 - self.total_failed / self.total_sent) * 100 if self.total_sent else 0,
            "avg_latency_ms": avg,
            "coupling": "Tinggi (1-ke-1, sinkron)",
            "throughput_note": "Dibatasi oleh round-trip time; 1 siklus selesai sebelum siklus berikutnya boleh mulai.",
        }


