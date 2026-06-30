# Simulasi Interaktif Model Komunikasi dalam Sistem Terdistribusi ###

Simulasi GUI desktop (Python 3 + Tkinter) yang membandingkan dua model
komunikasi: **Request-Response** (sinkron, 1-ke-1) dan
**Publish-Subscribe** (asinkron, 1-ke-banyak).


## Struktur Proyek

```
distributed_sim/
├── main.py                         # entry point — jalankan ini
├── app.py                          # kelas App: merangkai 3 tab + game loop animasi
├── config.py                       # konstanta, palet warna, util generik
├── models.py                       # struktur data MessageEvent
├── visuals.py                      # NodeVisual & MessageParticle (mesin animasi kanvas)
└── tabs/
    ├── __init__.py
    ├── request_response.py        # Model 1: Request-Response
    ├── publish_subscribe.py       # Model 2: Publish-Subscribe
    └── comparison.py              # Tab 3: dashboard perbandingan & metrik
```


## Cara Menjalankan

```bash
# Pastikan Python 3.8+ sudah terpasang.
# Tkinter sudah bawaan di Windows & macOS.
# Di Linux (Ubuntu/Debian), jika belum ada:
sudo apt install python3-tk

# Masuk ke folder proyek, lalu jalankan main.py (BUKAN file lain):
cd distributed_sim
python3 main.py
```

> **Penting:** jalankan selalu dari dalam folder `distributed_sim/` (atau
> buka folder ini sebagai workspace root di VS Code) supaya Python bisa
> menemukan `config.py`, `models.py`, dkk lewat import relatif sederhana
> (`from config import ...`). Kalau dijalankan dari folder induk, akan
> muncul `ModuleNotFoundError`.

### Membuka di VS Code

1. `File → Open Folder...` → pilih folder `distributed_sim/`.
2. Buka `main.py`, lalu jalankan lewat tombol ▷ Run atau `F5`.
3. Struktur file di Explorer kiri akan terlihat seperti pohon di atas —
   silakan jelajahi tiap modul untuk membaca docstring penjelasannya.

Tidak ada dependency eksternal apa pun — hanya modul standar Python
(`tkinter`, `dataclasses`, `random`, `time`, `math`).

## Cara Pakai Singkat

1. Tab **1 — Request-Response**: atur slider lalu klik **Kirim Request**.
   Perhatikan tombolnya terkunci sampai balasan datang — itu sengaja,
   meniru sifat blocking call.
2. Tab **2 — Publish-Subscribe**: centang/lepas Subscriber, lalu klik
   **Publish Event**. Anda bisa langsung publish lagi tanpa menunggu apa pun.
3. Tab **3 — Perbandingan**: lihat metrik & insight otomatis dari kedua
   model berdasarkan interaksi yang sudah dilakukan.

