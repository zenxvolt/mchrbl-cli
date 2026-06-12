#!/bin/sh
# ==========================================
# HeroRBL 1-Click Auto Install (Termux)
# Termux setup storage & wake lock included
# ==========================================

echo "[Info.] Memulai instalasi HeroRBL..."

# 0. Setup storage (jika pertama kali install Termux)
echo "[Info.] Meminta izin storage..."
termux-setup-storage

# 0b. Aktifkan wake-lock supaya Termux tidak sleep saat running
echo "[Info.] Mengaktifkan wake lock..."
termux-wake-lock

# 1. Update Termux
echo "[Info.] Update package Termux..."
pkg update -y && pkg upgrade -y

# 2. Install Python & tools
echo "[Info.] Install Python, wget, curl..."
pkg install python git wget curl -y

# 3. Install dependencies Python
echo "[Info.] Install Python dependencies..."
pip install requests colorama ntplib

# 4. Unduh script herorbl.py
SCRIPT_PATH="$HOME/herorbl.py"
echo "[Info.] Mengunduh herorbl.py..."
wget -O "$SCRIPT_PATH" "https://raw.githubusercontent.com/ProjectRedis/mchrbl-cli/refs/heads/main/herorbl.py"

# 5. Tambahkan alias ubl-go
echo "[Info.] Membuat alias ubl-go..."
grep -qxF "alias ubl-go='python3 $SCRIPT_PATH'" ~/.bashrc || echo "alias ubl-go='python3 $SCRIPT_PATH'" >> ~/.bashrc
grep -qxF "alias ubl-go='python3 $SCRIPT_PATH'" ~/.zshrc 2>/dev/null || echo "alias ubl-go='python3 $SCRIPT_PATH'" >> ~/.zshrc 2>/dev/null

# 6. Sumber ulang shell
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
elif [ -f ~/.zshrc ]; then
    source ~/.zshrc
fi

echo "[Success.] Instalasi selesai! Restart termux dan jalankan 'ubl-go' untuk memulai script."
