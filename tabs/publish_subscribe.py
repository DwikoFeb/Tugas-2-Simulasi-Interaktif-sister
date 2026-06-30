#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tabs/publish_subscribe.py
==========================
Implementasi tab MODEL 2 -- PUBLISH-SUBSCRIBE (asinkron, many-to-many via
Broker).

LOGIKA INTERAKSI:
  1. User menekan "Publish Event" pada Publisher.
  2. Publisher mengirim MessageEvent(kind="event") ke BROKER (bukan
     langsung ke subscriber -- ini kunci dari decoupling Pub-Sub).
  3. Broker, begitu menerima event, langsung mem-fan-out (menyalin dan
     meneruskan) event tersebut secara PARALEL ke SEMUA Subscriber yang
     sedang berstatus "subscribed" pada topic ini (dicentang via checkbox).
  4. Setiap Subscriber menerima event secara independen -- TIDAK ADA
     balasan/response yang dikirim balik ke Publisher. Publisher "lepas
     tangan" begitu event diserahkan ke Broker (fire-and-forget).
  5. Subscriber yang TIDAK mencentang status subscribe tidak menerima
     apa pun -- mensimulasikan sifat selektif topic-based messaging.

SIFAT KUNCI YANG DIPERAGAKAN:
  - DECOUPLING: Publisher tidak tahu/tidak peduli siapa & berapa banyak
    subscriber yang ada. Menambah/mengurangi subscriber tidak mengubah
    kode/perilaku Publisher sama sekali.
  - ASYNCHRONOUS & ONE-TO-MANY: satu event bisa diterima 0, 1, atau N
    penerima sekaligus, secara paralel, tanpa Publisher menunggu.
  - Tidak ada konsep "response" -- berbeda fundamental dari Req-Resp.
"""

import random
import tkinter as tk
from tkinter import ttk

from config import (
    BG_DARK, PANEL_BG, PANEL_BORDER, TEXT_PRIMARY, TEXT_DIM,
    ACCENT_PUBSUB, ACCENT_OK, ACCENT_WARN,
    FONT_UI, FONT_UI_BOLD, FONT_TITLE,
    sim_clock_ms, make_panel, make_metric_row,
)
from visuals import NodeVisual, MessageParticle


class PublishSubscribeTab:
    """Tab simulasi model Publish-Subscribe (asynchronous, many-to-many)."""

    SUBSCRIBER_NAMES = ["Subscriber A\n(Email Svc)", "Subscriber B\n(Analytics)",
                         "Subscriber C\n(Inventory)"]

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=BG_DARK)
        self.particles = []
        self.msg_counter = 0
        self.total_published = 0
        self.total_deliveries = 0  # jumlah (event x subscriber) yang berhasil terkirim
        self.fanout_history = []   # jumlah penerima per event, untuk metrik rata-rata fan-out

        self._build_layout()
        self._build_nodes()

    def _build_layout(self):
        f = self.frame
        title = tk.Label(f, text="MODEL 2 — PUBLISH-SUBSCRIBE  (Asinkron, Many-to-Many via Broker)",
                          bg=BG_DARK, fg=ACCENT_PUBSUB, font=FONT_TITLE, anchor="w")
        title.pack(fill="x", padx=16, pady=(14, 2))

        desc = ("Publisher mengirim event ke Broker tanpa tahu siapa penerimanya.\n"
                "Analogi dunia nyata: event 'OrderCreated' yang didengar banyak microservice (Kafka/RabbitMQ).")
        tk.Label(f, text=desc, bg=BG_DARK, fg=TEXT_DIM, font=FONT_UI, justify="left",
                 anchor="w").pack(fill="x", padx=16, pady=(0, 10))

        body = tk.Frame(f, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        canvas_wrap = tk.Frame(body, bg=PANEL_BORDER)
        canvas_wrap.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_wrap, bg=PANEL_BG, highlightthickness=0,
                                 width=560, height=380)
        self.canvas.pack(fill="both", expand=True, padx=1, pady=1)

        side = tk.Frame(body, bg=BG_DARK, width=300)
        side.pack(side="left", fill="y", padx=(14, 0))
        side.pack_propagate(False)

        ctrl_panel = make_panel(side, "KONTROL")
        tk.Label(ctrl_panel, text="Topic event:", bg=PANEL_BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(8, 0))
        self.topic_var = tk.StringVar(value="order.created")
        topic_combo = ttk.Combobox(ctrl_panel, textvariable=self.topic_var, state="readonly",
                                    values=["order.created", "payment.failed", "user.signup"])
        topic_combo.pack(fill="x", padx=10, pady=(0, 6))

        tk.Label(ctrl_panel, text="Subscriber aktif:", bg=PANEL_BG, fg=TEXT_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(4, 2))
        self.sub_vars = []
        for nm in self.SUBSCRIBER_NAMES:
            var = tk.BooleanVar(value=True)
            self.sub_vars.append(var)
            chk = tk.Checkbutton(ctrl_panel, text=nm.replace("\n", " "), variable=var,
                                  bg=PANEL_BG, fg=TEXT_PRIMARY, selectcolor=PANEL_BG,
                                  activebackground=PANEL_BG, font=("Segoe UI", 8),
                                  highlightthickness=0)
            chk.pack(anchor="w", padx=10)

        self.btn_publish = tk.Button(ctrl_panel, text="▶  Publish Event", command=self.publish_event,
                                      bg=ACCENT_PUBSUB, fg="#2B1604", activebackground="#F7C28C",
                                      font=FONT_UI_BOLD, relief="flat", cursor="hand2", pady=6)
        self.btn_publish.pack(fill="x", padx=10, pady=(10, 10))

        metric_panel = make_panel(side, "METRIK")
        self.lbl_published = self._metric_row(metric_panel, "Total event dipublish", "0")
        self.lbl_deliveries = self._metric_row(metric_panel, "Total pengiriman (fan-out)", "0")
        self.lbl_avg_fanout = self._metric_row(metric_panel, "Rata-rata penerima/event", "0")
        self.lbl_status = self._metric_row(metric_panel, "Status Publisher", "IDLE")

        log_panel = make_panel(side, "LOG AKTIVITAS", expand=True)
        self.log_box = tk.Listbox(log_panel, bg=PANEL_BG, fg=TEXT_PRIMARY,
                                   font=("Courier New", 8), highlightthickness=0,
                                   relief="flat", selectbackground=PANEL_BORDER)
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

    def _metric_row(self, parent, label, value):
        return make_metric_row(parent, label, value)

    def log(self, text, ts=None):
        ts = ts if ts is not None else sim_clock_ms()
        self.log_box.insert(0, f"[{ts:>7} ms] {text}")
        if self.log_box.size() > 200:
            self.log_box.delete(200, tk.END)

    def _build_nodes(self):
        self.node_publisher = NodeVisual(self.canvas, 30, 165, 110, 60, "PUBLISHER",
                                          "event source", ACCENT_PUBSUB)
        self.node_broker = NodeVisual(self.canvas, 225, 165, 110, 60, "BROKER",
                                       "topic fan-out", ACCENT_PUBSUB)
        self.subscriber_nodes = []
        ys = [40, 165, 290]
        for i, nm in enumerate(self.SUBSCRIBER_NAMES):
            short = nm.split("\n")[0]
            sub_label = nm.split("\n")[1] if "\n" in nm else ""
            node = NodeVisual(self.canvas, 420, ys[i], 130, 60, short, sub_label, ACCENT_PUBSUB)
            self.subscriber_nodes.append(node)
        for n in [self.node_publisher, self.node_broker] + self.subscriber_nodes:
            n.draw()
        self._draw_static_links()

    def _draw_static_links(self):
        c = self.canvas
        x0, y0 = self.node_publisher.center()
        x1, y1 = self.node_broker.center()
        c.create_line(x0 + 55, y0, x1 - 55, y1, fill=PANEL_BORDER, width=1, dash=(3, 3))
        for node in self.subscriber_nodes:
            sx, sy = node.center()
            c.create_line(x1 + 55, y1, sx - 65, sy, fill=PANEL_BORDER, width=1, dash=(3, 3))

    def publish_event(self):
        self.msg_counter += 1
        mid = self.msg_counter
        topic = self.topic_var.get()
        self.total_published += 1
        sent_at = sim_clock_ms()
        self.log(f"EVENT #{mid} '{topic}' dipublish Publisher -> Broker", sent_at)
        self.lbl_status.config(text="PUBLISHING", fg=ACCENT_PUBSUB)

        x0, y0 = self.node_publisher.anchor_point(self.node_broker.center())
        x1, y1 = self.node_broker.anchor_point(self.node_publisher.center())

        def on_broker_received():
            self.node_broker.trigger_pulse()
            self.node_broker.bump_count()
            self.log(f"BROKER menerima EVENT #{mid}, melakukan fan-out...", sim_clock_ms())
            self._fanout_to_subscribers(mid, topic)

        particle = MessageParticle(self.canvas, x0, y0, x1, y1, duration_ms=450,
                                    color=ACCENT_OK, label=f"EVT#{mid}",
                                    on_complete=on_broker_received)
        self.particles.append(particle)

    def _fanout_to_subscribers(self, mid, topic):
        active_indices = [i for i, v in enumerate(self.sub_vars) if v.get()]
        self.fanout_history.append(len(active_indices))

        if not active_indices:
            self.log(f"EVENT #{mid}: tidak ada subscriber aktif -> event hilang tanpa efek", sim_clock_ms())
            self.lbl_status.config(text="NO SUBSCRIBERS", fg=ACCENT_WARN)
            self._update_metrics()
            return

        self.lbl_status.config(text="FANNED OUT", fg=ACCENT_OK)
        for idx in active_indices:
            node = self.subscriber_nodes[idx]
            x0, y0 = self.node_broker.anchor_point(node.center())
            x1, y1 = node.anchor_point(self.node_broker.center())
            # Jitter kecil pada durasi supaya ketiga subscriber tidak menerima
            # event di waktu yang identik persis (lebih realistis & enak dilihat)
            duration = random.randint(380, 620)

            def make_callback(target_node=node, m=mid):
                def cb():
                    target_node.trigger_pulse()
                    target_node.bump_count()
                    self.total_deliveries += 1
                    self.log(f"  -> {target_node.name} menerima EVENT #{m}", sim_clock_ms())
                    self._update_metrics()
                return cb

            particle = MessageParticle(self.canvas, x0, y0, x1, y1, duration_ms=duration,
                                        color=ACCENT_PUBSUB, label=f"#{mid}",
                                        on_complete=make_callback())
            self.particles.append(particle)
        self._update_metrics()

    def _update_metrics(self):
        self.lbl_published.config(text=str(self.total_published))
        self.lbl_deliveries.config(text=str(self.total_deliveries))
        if self.fanout_history:
            avg_fo = sum(self.fanout_history) / len(self.fanout_history)
            self.lbl_avg_fanout.config(text=f"{avg_fo:.1f}")
        self.app.refresh_comparison_tab()

    def step_animation(self):
        for n in [self.node_publisher, self.node_broker] + self.subscriber_nodes:
            n.step_animation()
        still_alive = []
        for p in self.particles:
            if p.step_and_draw():
                still_alive.append(p)
        self.particles = still_alive

    def get_metrics(self):
        avg_fo = (sum(self.fanout_history) / len(self.fanout_history)) if self.fanout_history else 0
        return {
            "model": "Publish-Subscribe",
            "total_sent": self.total_published,
            "total_deliveries": self.total_deliveries,
            "avg_fanout": avg_fo,
            "coupling": "Rendah (Publisher tidak tahu Subscriber)",
            "throughput_note": "Publisher tidak menunggu; throughput efektif berlipat sesuai jumlah subscriber.",
        }


