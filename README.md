# 🎯 MCHR-BL CLI (Mi-Community Hero Request-BL)

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=flat-square)

**MCHR-BL CLI** adalah *sniper script* tingkat lanjut (Level HFT - *High-Frequency Trading*) yang dirancang khusus untuk merebut tiket *Unlock Bootloader* (UBL) Xiaomi Global dengan presisi nanodetik. 

Dibangun dengan arsitektur memori yang brutal, skrip ini mem- *bypass* latensi library standar dengan menembakkan **Raw HTTP Socket** langsung ke server Xiaomi tepat di milidetik *reset* harian.

---

## ⚡ Fitur Utama

| Fitur | Deskripsi |
| :--- | :--- |
| **Raw Socket Execution** | Mengirim *payload* HTTP murni tanpa *overhead* library untuk latensi serendah mungkin. |
| **Multiprocessing Architecture** | Terbebas dari Python GIL. Tiap "Hero" berjalan di proses memori yang terisolasi. |
| **Big-Core Affinity** | Memaksa OS Android/Linux untuk mengikat eksekusi ke *Performance Core* (Anti-Throttle). |
| **High-Precision Timer** | Sinkronisasi waktu NTP dipadukan dengan resolusi *Hardware Clock* nanodetik. |
| **Dynamic Latency Bracket** | Menyebar tembakan secara cerdas berdasarkan fluktuasi PING *real-time* ke server. |
| **Deep Account Checker** | Mendeteksi status akun (Eligible, Blocked, atau Under 30 Days) sebelum penembakan. |

---

## 🛠️ Persiapan (Prerequisites)

Sebelum menginstal, pastikan perangkatmu (Termux/Linux/Windows) sudah terinstal paket dasar berikut:

* **Git** (Untuk menarik repositori)
* **Python 3.8+** (Interpreter utama)
* **Curl** (Untuk menjalankan skrip instalasi cepat)

Jika kamu menggunakan **Termux** di Android, jalankan perintah ini terlebih dahulu untuk persiapan:
```bash
pkg update && pkg upgrade -y
pkg install python git curl -y
```
lalu copy ini di terminal mu
```bash
bash <(curl -s https://raw.githubusercontent.com/ProjectRedis/mchrbl-cli/refs/heads/main/install.sh)
```
