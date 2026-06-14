#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import atexit
import gc
import gzip
import json
import os
import shutil
import socket
import ssl
import struct
import sys
import getpass
import time
import threading
import random
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# ─────────────────────── ANSI COLORS (native, no colorama) ─────────────────────── #
class Fore:
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

class Style:
    RESET_ALL = "\033[0m"

# ─────────────────────── KONFIGURASI ─────────────────────── #
STATE_URL       = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
UNLOCK_URL      = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
SERVER_HOST     = "sgp-api.buy.mi.com"
USER_AGENT      = "okhttp/4.12.0"
TIMEOUT         = 5
BEIJING_TZ      = timezone(timedelta(hours=8))
LABEL_WIDTH     = 14
TAG_WIDTH       = 12
MSG_WIDTH       = 16
PING_SAMPLES    = 5
BRACKET_FACTOR  = 0.8
CURRENT_VERSION = "v3.4.0-Rev.2026.06.15"

# ─────────────────────── JITTER CONFIG ─────────────────────── #
JITTER_MIN_MS = 1.0
JITTER_MAX_MS = 8.0

# ─────────────────────── PRE-COMPILED (module-level constants) ─────────────────────── #
_DEVICE_ID_RE = re.compile(r'deviceId=[^;]+')
_URL_PATH     = "/" + "/".join(UNLOCK_URL.split("/")[3:])
_NTP_EPOCH    = 2208988800

_PING_REQ = (
    f"HEAD / HTTP/1.1\r\n"
    f"Host: {SERVER_HOST}\r\n"
    f"User-Agent: {USER_AGENT}\r\n"
    f"Connection: close\r\n"
    f"\r\n"
).encode("utf-8")

_PING_CTX = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_PING_CTX.check_hostname = False
_PING_CTX.verify_mode = ssl.CERT_NONE

_TCP_QUICKACK = getattr(socket, 'TCP_QUICKACK', 12)

# ─────────────────────── RUNTIME FLAGS ─────────────────────── #
print_lock   = threading.Lock()
_wake_locked = False

# ─────────────────────── LANGUAGE MANAGER (i18n) ─────────────────────── #
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LANG_FILE  = os.path.join(SCRIPT_DIR, ".lang_config")
LOCALE_DIR = os.path.join(SCRIPT_DIR, "locales")

GITHUB_LOCALE_URL = "https://raw.githubusercontent.com/ProjectRedis/mchrbl-cli/main/locales/"

MENU_BAHASA = {
    "1": {"code": "id", "name": "Bahasa Indonesia"},
    "2": {"code": "en", "name": "English"},
}

# Hardcoded fallback — guarantees script is always usable even without
# network access, corrupted locale files, or failed downloads.
_FALLBACK_TEXTS: dict[str, str] = {
    "cpu_ok": "terdeteksi sebagai big core",
    "cpu_no": "Big core tidak terdeteksi (path /sys tidak tersedia)",
    "up_err": "Gagal cek update: {}",
    "up_no": "Tidak bisa membaca versi di GitHub.",
    "up_ok": "Script sudah terbaru ({})",
    "up_up": "Update tersedia : {}",
    "up_now": "Versi saat ini  : {}",
    "up_ask": "Update sekarang? (y/n): ",
    "up_late": "Melanjutkan menggunakan versi saat ini.",
    "up_done": "Berhasil update ke {}",
    "up_go": "Silakan jalankan ulang script.",
    "up_fail": "Gagal update otomatis: {}",
    "change_no": "Changelog tidak ditemukan.",
    "err_send": "Send Error",
    "err_parse": "Parse Error",
    "err_ssl": "SSL/Connect Error",
    "lang_select": "Select Language:",
    "lang_choice": "Pilihan / Choice (1/2): ",
    "lang_force": "Force updating language pack...",
    "lang_dl": "Downloading language pack ({})...",
    "lang_ok": "Language pack installed!",
    "lang_fail": "Failed to download language: {}",
    "lang_load_fail": "Failed to load language file: {}",
    "wake_lock": "Wake-lock aktif (Anti-Doze)",
}

TEXTS: dict[str, str] = {}


def init_language() -> None:
    global TEXTS

    force_change = "--lang" in sys.argv
    force_update = "--update-lang" in sys.argv
    lang_code = "id"

    if not force_change and os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, "r", encoding="utf-8") as f:
                lang_code = f.read().strip()
        except OSError:
            pass
    else:
        print(colored(f"\n[Input!] {_t('lang_select')}", Fore.BLUE))
        for k, v in MENU_BAHASA.items():
            print(f"  [{k}] {v['name']}")

        pilih = input(colored(_t("lang_choice"), Fore.YELLOW)).strip()
        if pilih in MENU_BAHASA:
            lang_code = MENU_BAHASA[pilih]["code"]

        try:
            with open(LANG_FILE, "w", encoding="utf-8") as f:
                f.write(lang_code)
        except OSError:
            pass

    if not os.path.exists(LOCALE_DIR):
        os.makedirs(LOCALE_DIR)

    json_path = os.path.join(LOCALE_DIR, f"{lang_code}.json")

    if force_update and os.path.exists(json_path):
        os.remove(json_path)
        log("[DL.]", _t("lang_force"), Fore.CYAN)

    if not os.path.exists(json_path):
        print()
        log("[DL.]", _t("lang_dl", lang_code.upper()), Fore.CYAN)
        try:
            req = urllib.request.Request(
                f"{GITHUB_LOCALE_URL}{lang_code}.json",
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                lang_data = resp.read().decode("utf-8")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(lang_data)
            log("[Success.]", _t("lang_ok"), Fore.GREEN)
        except (urllib.error.URLError, OSError, ValueError) as e:
            log("[Error.]", _t("lang_fail", e), Fore.RED)
            return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            TEXTS = json.load(f)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        log("[Error.]", _t("lang_load_fail", e), Fore.RED)


def _t(key: str, *args) -> str:
    """Get translated text. Lookup order: TEXTS → _FALLBACK_TEXTS → key."""
    teks = TEXTS.get(key) or _FALLBACK_TEXTS.get(key, key)
    if args:
        try:
            return teks.format(*args)
        except (IndexError, KeyError, ValueError):
            return teks
    return teks


# ─────────────────────── THREAD-SAFE GC ─────────────────────── #
_gc_ref_lock = threading.Lock()
_gc_ref_cnt  = 0


def _gc_disable() -> None:
    global _gc_ref_cnt
    with _gc_ref_lock:
        if _gc_ref_cnt == 0:
            gc.disable()
        _gc_ref_cnt += 1


def _gc_enable() -> None:
    global _gc_ref_cnt
    with _gc_ref_lock:
        _gc_ref_cnt = max(0, _gc_ref_cnt - 1)
        if _gc_ref_cnt == 0:
            gc.enable()


# ─────────────────────── HELPERS ─────────────────────── #
def colored(msg: str, color: str) -> str:
    return f"{color}{msg}{Style.RESET_ALL}"


def log(label: str, msg: str, color: str = Fore.WHITE) -> None:
    with print_lock:
        print(f"{colored(f'{label:<{LABEL_WIDTH}}', color)} {msg}")


def get_result_meaning(code: int) -> tuple[str, str, str]:
    table = {
        1: (Fore.GREEN, "[Approved.]", _t("ticket_got")),
        2: (Fore.WHITE, "[Info.]",     _t("ticket_has")),
        3: (Fore.RED,   "[Failed.]",   _t("ticket_0")),
        6: (Fore.RED,   "[Failed.]",   _t("ticket_busy")),
    }
    return table.get(code, (Fore.RED, "[Failed.]", f"Result code: {code}"))


# ─────────────────────── TERMUX WAKE-LOCK ─────────────────────── #
def _acquire_wake_lock() -> None:
    global _wake_locked
    if shutil.which("termux-wake-lock") is None:
        return
    try:
        ret = os.system("termux-wake-lock >/dev/null 2>&1")
        if ret == 0:
            _wake_locked = True
            atexit.register(_release_wake_lock)
            log("[Success.]", _t("wake_lock"), Fore.GREEN)
    except OSError:
        pass


def _release_wake_lock() -> None:
    global _wake_locked
    if _wake_locked:
        os.system("termux-wake-unlock >/dev/null 2>&1")
        _wake_locked = False


# ─────────────────────── TCP OPTIMIZATION ─────────────────────── #
def _apply_tcp_opts(sock: socket.socket) -> None:
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except (OSError, AttributeError):
        pass
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, 6)
    except (OSError, PermissionError, AttributeError):
        pass
    try:
        sock.setsockopt(socket.IPPROTO_TCP, _TCP_QUICKACK, 1)
    except (OSError, AttributeError):
        pass


# ─────────────────────── DNS PRE-RESOLVE ─────────────────────── #
def resolve_server(host: str = SERVER_HOST) -> str:
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            info = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
            ip = info[0][4][0]
            log("[Info.]", f"{host} → {ip}", Fore.WHITE)
            return ip
        except (socket.gaierror, socket.herror, OSError) as e:
            last_err = e
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    log("[Warn!]", _t("dns_pre", last_err), Fore.YELLOW)
    return host


# ─────────────────────── TIMING ─────────────────────── #
def _ntp_query(server: str, timeout: float = 5) -> float:
    packet = b'\x1b' + b'\0' * 47
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        t1 = time.time()
        sock.sendto(packet, (server, 123))
        data, _ = sock.recvfrom(1024)
        t4 = time.time()
    finally:
        sock.close()

    if len(data) < 48:
        raise ValueError("Short NTP response")

    def _parse_ts(offset: int) -> float:
        sec  = struct.unpack('!I', data[offset:offset + 4])[0] - _NTP_EPOCH
        frac = struct.unpack('!I', data[offset + 4:offset + 8])[0] / (2 ** 32)
        return sec + frac

    t2 = _parse_ts(32)
    t3 = _parse_ts(40)
    return ((t2 - t1) + (t3 - t4)) / 2.0 * 1000.0


def get_ntp_offset() -> float:
    for server in ("pool.ntp.org", "id.pool.ntp.org", "time.google.com"):
        try:
            offset = _ntp_query(server)
            log("[Connected.]", _t("ntp_conn", server), Fore.GREEN)
            return offset
        except (socket.timeout, OSError, struct.error, ValueError):
            continue
    log("[Error.]", _t("ntp_err"), Fore.RED)
    return 0.0


def get_accurate_now_ms(base_time_ms: int, perf_base_ns: int, offset_ms: float) -> float:
    return base_time_ms + (time.perf_counter_ns() - perf_base_ns) / 1_000_000.0 + offset_ms


def get_next_beijing_midnight_ms() -> float:
    now_beijing   = datetime.now(BEIJING_TZ)
    next_midnight = now_beijing.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    return next_midnight.timestamp() * 1000.0


# ─────────────────────── LATENCY ─────────────────────── #
def measure_latency(server_ip: str, n: int = 3) -> float:
    samples: list[float] = []
    for _ in range(n):
        sock = None
        try:
            t0 = time.perf_counter()
            sock = socket.create_connection((server_ip, 443), timeout=TIMEOUT)
            _apply_tcp_opts(sock)
            with _PING_CTX.wrap_socket(sock, server_hostname=SERVER_HOST) as ssock:
                ssock.sendall(_PING_REQ)
                ssock.recv(4096)
            samples.append((time.perf_counter() - t0) * 1000.0)
        except (OSError, ssl.SSLError):
            pass
        finally:
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
    return sum(samples) / len(samples) if samples else 300.0


def weighted_median(data: list[float], weights: list[float] | None = None) -> float:
    if not data:
        return 0.0
    if weights is None:
        weights = [1.0] * len(data)
    combined   = sorted(zip(data, weights), key=lambda x: x[0])
    half       = sum(weights) / 2.0
    cumulative = 0.0
    for val, w in combined:
        cumulative += w
        if cumulative >= half:
            return val
    return combined[-1][0]


# ─────────────────────── CPU / BIG CORE DETECTION ─────────────────────── #
def get_big_cores(threshold: int = 2_000_000) -> list[int]:
    cpu_dir = "/sys/devices/system/cpu/"
    cores: list[int] = []
    for i in range(os.cpu_count() or 1):
        try:
            with open(f"{cpu_dir}cpu{i}/cpufreq/cpuinfo_max_freq") as f:
                if int(f.read().strip()) >= threshold:
                    cores.append(i)
        except OSError:
            continue
    if cores:
        for c in cores:
            log("[Info.]", f"CPU{c} " + _t("cpu_ok"), Fore.WHITE)
    else:
        log("[Info.]", _t("cpu_no"), Fore.WHITE)
    return cores


# ─────────────────────── TOKEN CHECK ─────────────────────── #
def test_cookie(cookie: str, label: str) -> bool:
    try:
        req = urllib.request.Request(
            STATE_URL,
            headers={"Cookie": cookie, "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("[Error.]", f"{label} " + _t("acc_down", e), Fore.RED)
        return False

    try:
        res_json = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        log("[Error.]", f"{label} " + _t("acc_down", "Invalid JSON"), Fore.RED)
        return False

    code = res_json.get("code", -1)

    if code == 100004:
        log("[Error.]", f"{label} " + _t("cookie_err"), Fore.RED)
        return False

    data      = res_json.get("data") or {}
    is_pass   = data.get("is_pass", -1)
    btn_state = data.get("button_state", -1)
    deadline  = data.get("deadline_format", "")

    if is_pass == 1:
        log("[Approved.]", f"Status {label}: " + _t("acc_got", deadline), Fore.GREEN)
        return True

    col, tag, msg = {
        (4, 1): (Fore.GREEN,  "[Valid.]",   f"Status {label}: " + _t("acc_ok")),
        (4, 2): (Fore.RED,    "[Blocked.]", f"Status {label}: " + _t("acc_block", deadline)),
        (4, 3): (Fore.YELLOW, "[Warn!]",    f"Status {label}: " + _t("acc_warn")),
    }.get(
        (is_pass, btn_state),
        (Fore.WHITE, "[Account.]", f"{label} " + _t("acc_pass", is_pass)),
    )
    log(tag, msg, col)

    if (is_pass, btn_state) == (4, 1):
        return True

    return False


# ─────────────────────── UPDATE CHECKER ─────────────────────── #
def check_update() -> None:
    BASE          = "https://raw.githubusercontent.com/ProjectRedis/mchrbl-cli/refs/heads/main/"
    url_script    = BASE + "herorbl.py"
    url_changelog = BASE + "changelog.txt"

    try:
        req = urllib.request.Request(url_script, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=5) as resp:
            remote_text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        log("[Error.]", _t("up_err", f"HTTP {e.code}"), Fore.RED)
        return
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("[Error.]", _t("up_err", e), Fore.RED)
        return

    remote_version: str | None = None
    for line in remote_text.splitlines():
        if line.startswith("CURRENT_VERSION"):
            remote_version = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

    if not remote_version:
        log("[Info.]", _t("up_no"), Fore.WHITE)
        return

    if remote_version == CURRENT_VERSION:
        log("[Info.]", _t("up_ok", CURRENT_VERSION), Fore.WHITE)
        return

    print()
    log("[Info.]", _t("up_up", remote_version), Fore.WHITE)
    log("[Info.]", _t("up_now", CURRENT_VERSION), Fore.WHITE)
    print()
    log("[Changelog.]", "", Fore.YELLOW)

    try:
        req2 = urllib.request.Request(url_changelog, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            changelog_text = resp2.read().decode("utf-8")

        target_version = remote_version.split("-")[0]
        capture = False
        captured_lines: list[str] = []

        for line in changelog_text.splitlines():
            line_stripped = line.strip()
            if capture and line_stripped.startswith("----"):
                break
            if line_stripped.startswith(target_version):
                capture = True
            if capture:
                captured_lines.append(line_stripped)

        if captured_lines:
            for line in captured_lines:
                if line:
                    print(" " * LABEL_WIDTH + line)
                else:
                    print()
        else:
            for line in changelog_text.strip().splitlines()[:10]:
                if line.strip():
                    print(" " * LABEL_WIDTH + line)

    except (urllib.error.URLError, OSError, ValueError):
        log("[Info.]", _t("change_no"), Fore.WHITE)

    print()
    jawab = input(
        colored(f'{"[Input!]":<{LABEL_WIDTH}}', Fore.BLUE) + _t("up_ask")
    ).strip().lower()

    if jawab != "y":
        log("[Info.]", _t("up_late"), Fore.WHITE)
        return

    try:
        script_path = os.path.abspath(sys.argv[0])
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(remote_text)
        if os.path.exists(LOCALE_DIR):
            shutil.rmtree(LOCALE_DIR, ignore_errors=True)
        log("[Success.]", _t("up_done", remote_version), Fore.GREEN)
        log("[Info.]", _t("up_go"), Fore.WHITE)
        raise SystemExit(0)
    except SystemExit:
        raise
    except (OSError, ValueError) as e:
        log("[Error.]", _t("up_fail", e), Fore.RED)


# ─────────────────────── HTTP HELPERS ─────────────────────── #
def _recv_full(ssock: ssl.SSLSocket, buf: int = 4096, max_body: int = 2 * 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    headers_raw: bytes | None = None
    body_start = 0
    is_chunked = False
    content_length: int | None = None

    while True:
        try:
            chunk = ssock.recv(buf)
        except (ssl.SSLError, OSError):
            break
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)

        if headers_raw is None:
            if b"\r\n\r\n" not in data:
                continue
            sep = data.index(b"\r\n\r\n")
            headers_raw = data[:sep]
            body_start  = sep + 4
            lower_h     = headers_raw.lower()
            is_chunked  = b"transfer-encoding: chunked" in lower_h
            if not is_chunked:
                for line in headers_raw.split(b"\r\n"):
                    if line.lower().startswith(b"content-length:"):
                        try:
                            content_length = int(line.split(b":", 1)[1].strip())
                        except (ValueError, IndexError):
                            content_length = None
                        break

        body = data[body_start:]
        if len(body) > max_body:
            break
        if is_chunked:
            if body.endswith(b"0\r\n\r\n"):
                break
        else:
            if content_length is None or len(body) >= content_length:
                break

    return b"".join(chunks)


def _decode_chunked(body: bytes) -> bytes:
    parts: list[bytes] = []
    while body:
        idx = body.find(b"\r\n")
        if idx == -1:
            break
        try:
            size = int(body[:idx], 16)
        except ValueError:
            break
        if size == 0:
            break
        parts.append(body[idx + 2: idx + 2 + size])
        body = body[idx + 2 + size + 2:]
    return b"".join(parts)


def _parse_response(raw: bytes) -> dict:
    if b"\r\n\r\n" not in raw:
        return {}
    headers_raw, body = raw.split(b"\r\n\r\n", 1)
    headers_lower = headers_raw.lower()
    if b"transfer-encoding: chunked" in headers_lower:
        body = _decode_chunked(body)
    if b"content-encoding: gzip" in headers_lower:
        try:
            body = gzip.decompress(body)
        except (gzip.BadGzipFile, OSError, EOFError):
            pass
    try:
        return json.loads(body.decode("utf-8", errors="ignore"))
    except (json.JSONDecodeError, ValueError):
        return {}


# ─────────────────────── SEND WAVE (THREAD) ─────────────────────── #
def send_wave(
    wave_id:      int,
    target_ms:    float,
    cookie:       str,
    server_ip:    str,
    base_time_ms: int,
    perf_base_ns: int,
    offset_ms:    float,
    label:        str,
    output:       dict,
    core_id:      int | None = None,
) -> None:

    if core_id is not None:
        try:
            os.sched_setaffinity(0, {core_id})
            log("[Success.]", _t("pin_ok", wave_id, core_id), Fore.GREEN)
        except (OSError, ValueError) as e:
            log("[Warn!]", _t("pin_no", wave_id, e), Fore.YELLOW)

    hex_chars = "0123456789ABCDEF"
    fake_device_id = ''.join(random.choices(hex_chars, k=39))

    payload = '{"is_retry":false}' if wave_id == 1 else '{"is_retry":true}'
    payload_bytes = payload.encode("utf-8")

    dynamic_cookie = cookie
    if "deviceId=" in dynamic_cookie:
        dynamic_cookie = _DEVICE_ID_RE.sub(f'deviceId={fake_device_id}', dynamic_cookie)
    else:
        dynamic_cookie = dynamic_cookie if dynamic_cookie.endswith(';') else dynamic_cookie + ';'
        dynamic_cookie += f'deviceId={fake_device_id};'

    raw_req = (
        f"POST {_URL_PATH} HTTP/1.1\r\n"
        f"Cookie: {dynamic_cookie}\r\n"
        f"Accept: application/json\r\n"
        f"Content-Type: application/json; charset=utf-8\r\n"
        f"Content-Length: {len(payload_bytes)}\r\n"
        f"Host: {SERVER_HOST}\r\n"
        f"Connection: close\r\n"
        f"Accept-Encoding: gzip\r\n"
        f"User-Agent: {USER_AGENT}\r\n"
        f"\r\n"
    ).encode("utf-8") + payload_bytes

    # ─────────────────────────────────────────────────────────

    sock = None
    drift = 0.0
    jitter_ms = 0.0
    try:
        sock = socket.create_connection((server_ip, 443), timeout=5)
        _apply_tcp_opts(sock)
        ctx  = ssl.create_default_context()
        with ctx.wrap_socket(sock, server_hostname=SERVER_HOST) as ssock:

            try:
                ssock.setsockopt(socket.IPPROTO_TCP, _TCP_QUICKACK, 1)
            except (OSError, AttributeError):
                pass

            jitter_ms       = random.uniform(JITTER_MIN_MS, JITTER_MAX_MS)
            final_target_ms = target_ms + jitter_ms

            while True:
                remain = final_target_ms - get_accurate_now_ms(base_time_ms, perf_base_ns, offset_ms)
                if remain > 20:
                    time.sleep((remain - 20) / 1000.0)
                elif remain > 2:
                    time.sleep(0)
                else:
                    break

            _gc_disable()
            try:
                while get_accurate_now_ms(base_time_ms, perf_base_ns, offset_ms) < final_target_ms:
                    pass
                ssock.sendall(raw_req)
                drift = get_accurate_now_ms(base_time_ms, perf_base_ns, offset_ms) - final_target_ms
            except (OSError, ssl.SSLError, TimeoutError) as e:
                output[wave_id - 1] = (
                    Fore.RED,
                    "[Failed.]",
                    f"{_t('err_send'):<{MSG_WIDTH}} [Hero-{wave_id:02d}]   | Jitt: {jitter_ms:+.2f}ms | {e}",
                )
                return
            finally:
                _gc_enable()

            try:
                raw_resp  = _recv_full(ssock)
                resp_json = _parse_response(raw_resp)
                result = (resp_json.get("data") or {}).get("apply_result", -1)
                col, tag, msg = get_result_meaning(result)
                output[wave_id - 1] = (
                    col,
                    tag,
                    f"{msg:<{MSG_WIDTH}} [Hero-{wave_id:02d}]   | Jitt: {jitter_ms:+.2f}ms | Drift: {drift:+.2f}ms",
                )
            except (OSError, ssl.SSLError, json.JSONDecodeError, ValueError) as e:
                output[wave_id - 1] = (
                    Fore.RED,
                    "[Failed.]",
                    f"{_t('err_parse'):<{MSG_WIDTH}} [Hero-{wave_id:02d}]   | Jitt: {jitter_ms:+.2f}ms | Drift: {drift:+.2f}ms | {e}",
                )

    except (OSError, ssl.SSLError, TimeoutError) as e:
        output[wave_id - 1] = (
            Fore.RED,
            "[Failed.]",
            f"{_t('err_ssl'):<{MSG_WIDTH}} [Hero-{wave_id:02d}]   | Jitt: {jitter_ms:+.2f}ms | {e}",
        )
    finally:
        if sock:
            try:
                sock.close()
            except OSError:
                pass


# ─────────────────────── COUNTDOWN ─────────────────────── #
def _format_remain(ms: float) -> str:
    s = int(ms / 1000)
    h, rem = divmod(abs(s), 3600)
    m, s_  = divmod(rem, 60)
    return f"{h % 24:02d}:{m:02d}:{s_:02d}" if s >= 60 else f"{s_:02d}s"


def _countdown(
    label:        str,
    until_ms:     float,
    base_time_ms: int,
    perf_base_ns: int,
    offset_ms:    float,
) -> None:
    prefix = colored(f"{'[Wait!]':<{LABEL_WIDTH}}", Fore.CYAN)
    while True:
        remain = until_ms - get_accurate_now_ms(base_time_ms, perf_base_ns, offset_ms)
        if remain <= 0:
            break
        dots = "." * (int(time.time() * 2) % 4)
        print(f"{prefix} {label} {_format_remain(remain):<8} {dots:<3}", end="\r", flush=True)
        time.sleep(0.05)
    print()


# ─────────────────────── MAIN ─────────────────────── #
def main() -> None:
    print(colored("=" * 56,                               Fore.CYAN))
    print(colored("                 MI-COMMUNITY HERO REQ-BL",  Fore.WHITE))
    print(colored(f"                  {CURRENT_VERSION}",    Fore.YELLOW))
    print(colored("                   GitHub @ProjectRedis",    Fore.BLUE))
    print(colored("=" * 56,                               Fore.CYAN))
    print()

    init_language()

    _acquire_wake_lock()

    check_update()
    print()
    big_cores = get_big_cores()
    print()

    # ── 1. Input & validasi cookie ──
    valid_a = False
    valid_b = False
    cookie_a = ""
    cookie_b = ""

    while not (valid_a or valid_b):

        if not valid_a:
            cookie_a = getpass.getpass(
                colored(f'{"[Input!]":<{LABEL_WIDTH}}', Fore.BLUE) + " " + _t("cookie_a") + _t("cookie_skip")
            ).strip()

            if cookie_a:
                log("[Success.]", _t("cookie_acc", "A") + colored("**********", Fore.WHITE), Fore.GREEN)
                log("[Check!]", _t("cookie_check", "A"), Fore.MAGENTA)
                if test_cookie(cookie_a, "Token-A"):
                    valid_a = True
                else:
                    log("[Error.]", _t("cookie_ax"), Fore.RED)
            else:
                log("[Info.]", _t("cookie_as"), Fore.WHITE)

        print()

        if not valid_b:
            cookie_b = getpass.getpass(
                colored(f'{"[Input!]":<{LABEL_WIDTH}}', Fore.BLUE) + " " + _t("cookie_b") + _t("cookie_skip")
            ).strip()

            if cookie_b:
                log("[Success.]", _t("cookie_acc", "B") + colored("**********", Fore.WHITE), Fore.GREEN)
                log("[Check!]", _t("cookie_check", "B"), Fore.MAGENTA)
                if test_cookie(cookie_b, "Token-B"):
                    valid_b = True
                else:
                    log("[Error.]", _t("cookie_bx"), Fore.RED)
            else:
                log("[Info.]", _t("cookie_bs"), Fore.WHITE)

        if not valid_a and not valid_b:
            print()
            log("[Warn!]", _t("cookie_warn"), Fore.YELLOW)
            print()

    print()
    log("[Success.]", _t("cookie_ready"), Fore.GREEN)

    # ── 2. DNS Pre-resolve ──
    print()
    log("[Check!]", _t("dns_pre_start", SERVER_HOST), Fore.MAGENTA)
    server_ip = resolve_server()

    # ── 3. NTP sync ──
    print()
    log("[Check!]", _t("ntp_sync"), Fore.MAGENTA)
    ntp_offset  = get_ntp_offset()
    perf_base   = time.perf_counter_ns()
    time_base   = int(time.time() * 1000)
    log("[Info.]", _t("ntp_offset", ntp_offset), Fore.WHITE)

    # ── 4. Konfigurasi jadwal ──
    print()
    debug = (
        input(colored(f'{"[Input!]":<{LABEL_WIDTH}}', Fore.BLUE) + " " + _t("input_debug"))
        .strip().lower() == "y"
    )
    target_ms = (
        get_accurate_now_ms(time_base, perf_base, ntp_offset) + 20_000
        if debug else
        get_next_beijing_midnight_ms()
    )

    raw_count     = input(
        colored(f'{"[Input!]":<{LABEL_WIDTH}}', Fore.BLUE) + " " + _t("input_hero")
    ).strip()
    trigger_count = int(raw_count) if raw_count.isdigit() and int(raw_count) > 0 else 4

    raw_margin    = input(
        colored(f'{"[Input!]":<{LABEL_WIDTH}}', Fore.BLUE) + " " + _t("input_margin")
    ).strip()
    try:
        safety_margin = int(raw_margin)
    except ValueError:
        safety_margin = 30

    # ── 5. Tunggu fase ping ──
    _countdown(_t("wait_start"), target_ms - 15_000, time_base, perf_base, ntp_offset)

    # ── 6. Ping sampling ──
    log("[Info.]", _t("ping_go", PING_SAMPLES, server_ip), Fore.WHITE)
    ping_samples: list[float] = []
    ping_weights: list[float] = []
    for i in range(PING_SAMPLES):
        sample = measure_latency(server_ip)
        ping_samples.append(sample)
        ping_weights.append(float(i + 1))
        log("[Ping!]", _t("ping_sample", sample), Fore.MAGENTA)
        time.sleep(1)

    eff_latency  = weighted_median(ping_samples, ping_weights)
    base_send    = target_ms - eff_latency
    bracket_half = int(eff_latency * BRACKET_FACTOR) + 50
    log("[Active.]", _t("dyn_bracket", bracket_half, eff_latency), Fore.GREEN)

    # ── 7. Hitung offset tiap Hero ──
    if trigger_count > 1:
        span    = 2.0 * (bracket_half - safety_margin)
        offsets = [
            int(-bracket_half + safety_margin + span * i / (trigger_count - 1))
            for i in range(trigger_count)
        ]
    else:
        offsets = [0]

    # ── 8. Siapkan thread Hero ──
    output: dict[int, tuple] = {}
    threads: list[threading.Thread] = []

    valid_cookies: list[tuple[str, str]] = []
    if valid_a:
        valid_cookies.append(("Tok-A", cookie_a))
    if valid_b:
        valid_cookies.append(("Tok-B", cookie_b))

    for idx, wave_off in enumerate(offsets):
        wave_id = idx + 1

        tok_label, cookie_use = valid_cookies[idx % len(valid_cookies)]

        wave_target = base_send + wave_off

        dt_cst = datetime.fromtimestamp(wave_target / 1000.0, BEIJING_TZ)
        ts     = f"{dt_cst.strftime('%H:%M:%S')}.{int(wave_target % 1000):03d}"
        log("[Info.]", _t("hero_standby", wave_id, tok_label, ts, wave_off))

        core_id = big_cores[idx % len(big_cores)] if big_cores else None
        t = threading.Thread(
            target=send_wave,
            args=(
                wave_id, wave_target, cookie_use, server_ip,
                time_base, perf_base, ntp_offset,
                tok_label, output, core_id,
            ),
            daemon=True,
        )
        threads.append(t)

    # ── 9. Countdown menuju aba-aba ──
    _countdown(_t("wait_war"), base_send - 1000, time_base, perf_base, ntp_offset)

    # ── 10. Tembak! ──
    log("[Active.]", _t("spin_lock_active"), Fore.GREEN)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    time.sleep(0.3)

    # ── 11. Laporan ──
    print()
    log("[Info.]", _t("war_log"), Fore.WHITE)
    time.sleep(1)

    for i in range(trigger_count):
        item = output.get(i)
        if isinstance(item, tuple) and len(item) == 3:
            col, tag, detail = item
            log(tag, detail, col)
        else:
            log("[Failed.]", _t("hero_down", i + 1), Fore.RED)

    print()
    log("[Completed.]", _t("war_done"), Fore.GREEN)


if __name__ == "__main__":
    main()
