#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tabs/comparison.py
====================
Tab ke-3 -- PERBANDINGAN & METRIK AGREGAT.

Tab ini TIDAK mensimulasikan komunikasi baru -- ia hanya membaca metrik
yang sudah dikumpulkan oleh kedua tab lain (lewat method get_metrics())
dan menyajikannya berdampingan, baik dalam bentuk tabel naratif maupun
bar chart yang digambar langsung di atas Canvas (tanpa library chart
eksternal, sesuai prinsip "tanpa dependency tambahan").

Mekanisme refresh: setiap kali sebuah event (request atau publish)
selesai diproses di tab manapun, tab tersebut memanggil
`app.refresh_comparison_tab()` yang akan memanggil `self.refresh()` di
sini -- sehingga tab Perbandingan selalu menampilkan data terbaru
tanpa perlu di-refresh manual oleh pengguna.

Catatan desain: tab ini sengaja TIDAK mengimpor RequestResponseTab dkk
secara langsung. Ia hanya menerima objek `app` dan mengakses
`app.tab_reqres`, `app.tab_pubsub` -- sehingga tidak ada dependency
siklik antar modul tab.
"""

import tkinter as tk

from config import (
    BG_DARK, PANEL_BG, PANEL_BORDER, TEXT_PRIMARY, TEXT_DIM,
    ACCENT_REQRES, ACCENT_PUBSUB, ACCENT_OK,
    FONT_UI, FONT_TITLE, make_panel,
)


class ComparisonTab:
    """Tab ke-3: dashboard perbandingan kuantitatif & naratif antar model."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=BG_DARK)
        self._build_layout()

    def _build_layout(self):
        f = self.frame
        title = tk.Label(f, text="PERBANDINGAN ANTAR MODEL KOMUNIKASI",
                          bg=BG_DARK, fg=TEXT_PRIMARY, font=FONT_TITLE, anchor="w")
        title.pack(fill="x", padx=16, pady=(14, 2))
        desc = ("Metrik berikut dihitung langsung dari interaksi Anda di tab 1-2.\n"
                "Coba kirim beberapa pesan di tiap tab lalu kembali ke sini untuk melihat pola yang muncul.")
        tk.Label(f, text=desc, bg=BG_DARK, fg=TEXT_DIM, font=FONT_UI, justify="left",
                 anchor="w").pack(fill="x", padx=16, pady=(0, 10))

        body = tk.Frame(f, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # --- Kanvas bar-chart throughput/volume ---
        chart_wrap = tk.Frame(body, bg=PANEL_BORDER)
        chart_wrap.pack(side="left", fill="both", expand=True)
        tk.Label(chart_wrap, text="VOLUME PESAN TERKIRIM/TERKIRIM-ULANG (FAN-OUT) PER MODEL",
                 bg=PANEL_BG, fg=TEXT_DIM, font=("Segoe UI", 8, "bold")).pack(
                     fill="x", padx=1, pady=(1, 0))
        self.chart_canvas = tk.Canvas(chart_wrap, bg=PANEL_BG, highlightthickness=0,
                                       width=560, height=380)
        self.chart_canvas.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        # --- Tabel naratif perbandingan ---
        side = tk.Frame(body, bg=BG_DARK, width=320)
        side.pack(side="left", fill="y", padx=(14, 0))
        side.pack_propagate(False)

        self.table_panel = make_panel(side, "TABEL PERBANDINGAN", expand=True)
        self.table_text = tk.Text(self.table_panel, bg=PANEL_BG, fg=TEXT_PRIMARY,
                                   font=("Courier New", 8), highlightthickness=0,
                                   relief="flat", wrap="word", height=24)
        self.table_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.table_text.config(state="disabled")

        insight_panel = make_panel(side, "INSIGHT OTOMATIS")
        self.insight_label = tk.Label(insight_panel, text="Belum ada data. Kirim pesan di tab lain dulu.",
                                       bg=PANEL_BG, fg=TEXT_DIM, font=("Segoe UI", 8),
                                       justify="left", wraplength=280, anchor="w")
        self.insight_label.pack(fill="x", padx=10, pady=(0, 10), anchor="w")

        self.refresh()

    def _draw_bar_chart(self):
        c = self.chart_canvas
        c.delete("all")
        c.update_idletasks()
        w = c.winfo_width() or 560
        h = c.winfo_height() or 380

        rr = self.app.tab_reqres.get_metrics()
        ps = self.app.tab_pubsub.get_metrics()

        # Dua "kelompok batang": volume terkirim vs volume diterima/diproses
        groups = [
            ("Req-Resp", rr["total_sent"], rr["total_sent"] - rr["total_failed"], ACCENT_REQRES),
            ("Pub-Sub", ps["total_sent"], ps.get("total_deliveries", 0), ACCENT_PUBSUB),
        ]
        max_val = max([1] + [g[1] for g in groups] + [g[2] for g in groups])

        margin_left, margin_bottom, margin_top = 60, 50, 30
        plot_h = h - margin_bottom - margin_top
        plot_w = w - margin_left - 30
        group_w = plot_w / len(groups)

        # Sumbu
        c.create_line(margin_left, margin_top, margin_left, h - margin_bottom,
                       fill=PANEL_BORDER, width=1)
        c.create_line(margin_left, h - margin_bottom, w - 20, h - margin_bottom,
                       fill=PANEL_BORDER, width=1)
        for frac in (0.25, 0.5, 0.75, 1.0):
            yy = h - margin_bottom - plot_h * frac
            c.create_line(margin_left, yy, w - 20, yy, fill=PANEL_BORDER, width=1, dash=(2, 4))
            c.create_text(margin_left - 8, yy, text=str(int(max_val * frac)), fill=TEXT_DIM,
                           font=("Courier New", 7), anchor="e")

        bar_w = group_w * 0.28
        for i, (name, sent, recv, color) in enumerate(groups):
            gx = margin_left + group_w * i + group_w / 2
            # Batang 1: dikirim/dipublish/dienqueue
            h1 = (sent / max_val) * plot_h if max_val else 0
            x1a, x1b = gx - bar_w - 4, gx - 4
            c.create_rectangle(x1a, h - margin_bottom - h1, x1b, h - margin_bottom,
                                fill=color, outline="")
            c.create_text((x1a + x1b) / 2, h - margin_bottom - h1 - 10, text=str(sent),
                           fill=color, font=("Courier New", 8, "bold"))

            # Batang 2: diterima/diproses/sukses (warna lebih redup sebagai pembeda)
            h2 = (recv / max_val) * plot_h if max_val else 0
            x2a, x2b = gx + 4, gx + 4 + bar_w
            c.create_rectangle(x2a, h - margin_bottom - h2, x2b, h - margin_bottom,
                                fill=ACCENT_OK, outline="")
            c.create_text((x2a + x2b) / 2, h - margin_bottom - h2 - 10, text=str(recv),
                           fill=ACCENT_OK, font=("Courier New", 8, "bold"))

            c.create_text(gx, h - margin_bottom + 18, text=name, fill=TEXT_PRIMARY,
                           font=("Segoe UI", 9, "bold"))

        legend_y = margin_top - 14
        c.create_rectangle(margin_left, legend_y, margin_left + 10, legend_y + 10,
                            fill=TEXT_DIM, outline="")
        c.create_text(margin_left + 16, legend_y + 5, text="kiri = dikirim/dipublish/dienqueue",
                       fill=TEXT_DIM, font=("Courier New", 7), anchor="w")
        c.create_rectangle(margin_left + 230, legend_y, margin_left + 240, legend_y + 10,
                            fill=ACCENT_OK, outline="")
        c.create_text(margin_left + 246, legend_y + 5, text="kanan = sukses diterima/diproses",
                       fill=TEXT_DIM, font=("Courier New", 7), anchor="w")

    def _build_table_text(self):
        rr = self.app.tab_reqres.get_metrics()
        ps = self.app.tab_pubsub.get_metrics()

        lines = []
        lines.append("=" * 38)
        lines.append("1. REQUEST-RESPONSE")
        lines.append("=" * 38)
        lines.append(f" Request terkirim     : {rr['total_sent']}")
        lines.append(f" Gagal/timeout        : {rr['total_failed']}")
        lines.append(f" Success rate         : {rr['success_rate']:.0f}%")
        lines.append(f" Avg latency RTT      : {rr['avg_latency_ms']:.0f} ms")
        lines.append(f" Coupling             : {rr['coupling']}")
        lines.append(f" Catatan throughput   : {rr['throughput_note']}")
        lines.append("")
        lines.append("=" * 38)
        lines.append("2. PUBLISH-SUBSCRIBE")
        lines.append("=" * 38)
        lines.append(f" Event dipublish      : {ps['total_sent']}")
        lines.append(f" Total pengiriman     : {ps['total_deliveries']}")
        lines.append(f" Avg penerima/event   : {ps['avg_fanout']:.1f}")
        lines.append(f" Coupling             : {ps['coupling']}")
        lines.append(f" Catatan throughput   : {ps['throughput_note']}")
        return "\n".join(lines)

    def _build_insight(self):
        rr = self.app.tab_reqres.get_metrics()
        ps = self.app.tab_pubsub.get_metrics()

        total_activity = rr["total_sent"] + ps["total_sent"]
        if total_activity == 0:
            return "Belum ada data. Kirim pesan di tab Request-Response atau Publish-Subscribe dulu, lalu kembali ke tab ini."

        notes = []
        if rr["total_sent"] > 0:
            notes.append(
                f"• Req-Resp: setiap siklus harus tuntas (RTT rata-rata "
                f"{rr['avg_latency_ms']:.0f} ms) sebelum siklus berikutnya dimulai — "
                f"ini sebabnya model ini paling lambat untuk volume tinggi, "
                f"tapi paling MUDAH dipahami alur sebab-akibatnya."
            )
        if ps["total_sent"] > 0:
            notes.append(
                f"• Pub-Sub: {ps['total_sent']} event menghasilkan "
                f"{ps['total_deliveries']} total pengiriman (rata-rata "
                f"{ps['avg_fanout']:.1f} penerima/event) — satu publish bisa "
                f"'dikalikan' tanpa menambah beban kerja Publisher itu sendiri, "
                f"dan Publisher tidak pernah menunggu balasan apa pun."
            )
        if rr["total_sent"] > 0 and ps["total_sent"] > 0:
            notes.append(
                f"• Bandingkan langsung: untuk mengirim jumlah pesan yang sama, "
                f"Req-Resp butuh waktu sekitar {rr['avg_latency_ms']:.0f} ms PER SIKLUS "
                f"(karena harus menunggu balasan), sedangkan Pub-Sub bisa langsung "
                f"publish berturut-turut tanpa menunggu sama sekali — inilah mengapa "
                f"Pub-Sub jauh lebih unggul soal throughput, dengan harga yang dibayar: "
                f"tidak ada garansi pesan benar-benar diproses oleh penerimanya."
            )
        notes.append(
            "• Trade-off inti: Req-Resp = konsisten, mudah dilacak, dan selalu tahu "
            "hasil setiap permintaan (sukses/gagal) — tapi lambat & tightly-coupled "
            "karena Client terikat langsung pada ketersediaan Server. Pub-Sub = "
            "sangat scalable & decoupled (Publisher tidak peduli siapa/berapa banyak "
            "Subscriber) — tapi tidak ada garansi balasan maupun konfirmasi bahwa "
            "event benar-benar selesai diproses."
        )
        return "\n\n".join(notes)

    def refresh(self):
        self._draw_bar_chart()
        self.table_text.config(state="normal")
        self.table_text.delete("1.0", tk.END)
        self.table_text.insert("1.0", self._build_table_text())
        self.table_text.config(state="disabled")
        self.insight_label.config(text=self._build_insight())

    def step_animation(self):
        pass  # tab ini statis/tabular, tidak ada animasi partikel berjalan
