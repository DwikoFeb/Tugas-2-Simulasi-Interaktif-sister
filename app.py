import tkinter as tk
from tkinter import ttk

from config import BG_DARK, PANEL_BG, PANEL_BORDER, TEXT_PRIMARY, TEXT_DIM, ANIM_TICK_MS
from tabs.request_response import RequestResponseTab
from tabs.publish_subscribe import PublishSubscribeTab
from tabs.comparison import ComparisonTab


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simulasi Model Komunikasi Sistem Terdistribusi")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("1000x720")
        self.root.minsize(900, 650)

        self._build_header()
        self._build_notebook()

        self.root.after(ANIM_TICK_MS, self._global_tick)

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG_DARK)
        header.pack(fill="x")
        tk.Label(header, text="◆ DISTRIBUTED SYSTEMS COMM LAB",
                 bg=BG_DARK, fg=TEXT_PRIMARY, font=("Segoe UI", 13, "bold")
                 ).pack(side="left", padx=18, pady=(14, 6))
        tk.Label(header, text="Request-Response · Publish-Subscribe",
                 bg=BG_DARK, fg=TEXT_DIM, font=("Segoe UI", 9)
                 ).pack(side="left", padx=(0, 18), pady=(16, 6))
        sep = tk.Frame(self.root, bg=PANEL_BORDER, height=1)
        sep.pack(fill="x")

    def _build_notebook(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL_BG, foreground=TEXT_DIM,
                         padding=[16, 8], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab",
                   background=[("selected", PANEL_BORDER)],
                   foreground=[("selected", TEXT_PRIMARY)])

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_reqres = RequestResponseTab(self.notebook, self)
        self.tab_pubsub = PublishSubscribeTab(self.notebook, self)
        self.tab_compare = ComparisonTab(self.notebook, self)

        self.notebook.add(self.tab_reqres.frame, text="1 ⟷ Request-Response")
        self.notebook.add(self.tab_pubsub.frame, text="2 ⇶ Publish-Subscribe")
        self.notebook.add(self.tab_compare.frame, text="3 ▣ Perbandingan")

        self._tabs_in_order = [self.tab_reqres, self.tab_pubsub, self.tab_compare]

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event=None):
        # Saat pengguna membuka tab Perbandingan, segarkan datanya seketika.
        current = self.notebook.index(self.notebook.select())
        if self._tabs_in_order[current] is self.tab_compare:
            self.tab_compare.refresh()

    def refresh_comparison_tab(self):
        """
        Dipanggil oleh tab 1-2 setiap kali ada event komunikasi yang selesai,
        supaya tab Perbandingan selalu punya data terbaru begitu dibuka.
        """
        self.tab_compare.refresh()

    def _global_tick(self):
        """Game loop utama: animasikan hanya tab yang sedang aktif/terlihat."""
        try:
            current = self.notebook.index(self.notebook.select())
            active_tab = self._tabs_in_order[current]
            active_tab.step_animation()
        except (tk.TclError, IndexError):
            pass
        self.root.after(ANIM_TICK_MS, self._global_tick)
