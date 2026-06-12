# 🎯 MCHR-BL CLI (Mi-Community Hero Request-BL)

<details>
  <summary>🌐 <b>Select Language / Pilih Bahasa</b></summary>
  
  * [Bahasa Indonesia](README.md)
  * [English (US)](README.en.md)
</details>

---

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)
![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=flat-square)

**MCHR-BL CLI** is an advanced, HFT-level (*High-Frequency Trading*) bot script specifically engineered to secure Xiaomi Global *Unlock Bootloader* (UBL) slots with nanosecond precision. 

Built with a highly optimized memory architecture, this script bypasses standard library latency overheads by injecting **Raw HTTP Socket** packets directly into Xiaomi's servers exactly at the daily quota reset millisecond.

---

## ⚡ Key Features

| Feature | Description |
| :--- | :--- |
| **Doppelganger** | Restructures HTTP Header Order and Fingerprint to mimic the original "Mi Community" app 100%. |
| **Chameleon** | Automatically generates a 39-Hex Device ID and syncs it across each Hero via Regex to bypass Xiaomi's WAF Firewall. |
| **Gungnir** | Executes Raw HTTP Sockets to dispatch payloads with zero library overhead for the lowest possible latency. |
| **Chronobreak** | Calculates global time offsets and OS clock drift, locking the execution time precisely using `perf_counter`. |
| **Bunshin** | Bypasses the Python GIL by running each "Hero" thread inside isolated system memory processes. |
| **Berserk** | Overrides system scheduling to force-bind execution threads to the CPU's *Performance Cores* (Anti-Throttling). |
| **Oracle** | High-precision NTP time synchronization coupled with OS *Hardware Clock* calibration for nanosecond accuracy. |
| **Volley** | Smartly spreads out request bursts across an optimal timeline based on real-time PING fluctuations to the server. |

---

## 📸 Preview

![Approve Result](assets/preview-00.png)

---

## 🛠️ Installation Guide (Android)

1. Download **Termux**. It is mandatory to use the [F-Droid version](https://f-droid.org/id/packages/com.termux/) or the [GitHub Releases version](https://github.com/termux/termux-app/releases), as the Google Play Store version is heavily outdated.

2. Run this command first to set up storage access:

```bash
termux-setup-storage

```
 3. Allow the storage permission prompt on your screen, then continue with the following commands:
```bash
pkg update && pkg upgrade -y
pkg install python git curl -y

```
 4. Copy and paste this installer script into Termux:
```bash
bash <(curl -s [https://raw.githubusercontent.com/ProjectRedis/mchrbl-cli/refs/heads/main/install.sh](https://raw.githubusercontent.com/ProjectRedis/mchrbl-cli/refs/heads/main/install.sh))

```
 5. Reload or restart Termux, then type this command to run the tool:
```bash
ubl-go

```
**Notes:**
 1. This tool is highly effective when launched **5 minutes before the daily slot reset window**.
 2. When prompted with **Debug Mode: y/n**, choose **n**. Debug mode is strictly intended for internal testing and bug fixing.
 
---

## 🔑 How to Capture "Cookie" on Android
 1. Install any network packet sniffer app of your choice: **(Proxyman, HTTP Toolkit, HTTP Sniffer, PCAPdroid)**
 2. Start the sniffer app; it will typically ask for VPN permissions to capture traffic locally.
 3. Open the official **Mi Community App**, navigate to the **Unlock Bootloader** page inside the **Me** tab (bottom-right corner).
 4. Go back to your sniffer app and stop the capturing session/VPN service.
 5. Filter or search for this specific endpoint: `"https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"`
 6. Look into the request **Headers** and locate the `"Cookie:"` field.
 7. Copy the entire value string right after `"Cookie:"` it should start with `"new_bbs_serviceToken="`.
 8. Paste it into Termux when prompted.
 9. Done!
 
**Note:** If the **Unlock Bootloader** menu does not appear in your **Mi Community App**, make sure to change your app's region setting to **Global**.

---
