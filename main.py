import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


def _init_sentry():
    """Sentry: SENTRY_DSN .env da bo'lsa yoqiladi, bo'lmasa o'chirilgan."""
    try:
        dsn = os.environ.get("SENTRY_DSN", "").strip()
        if not dsn:
            return
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.05, send_default_pii=False)
        logger.info("Sentry yoqildi")
    except Exception as e:
        logger.warning("Sentry yoqilmadi: %s", e)


_init_sentry()

import uvicorn

import config
from server import app


def is_termux():
    """Termux (Android) muhitini aniqlash."""
    return "com.termux" in os.environ.get("PREFIX", "") or os.path.exists(
        "/data/data/com.termux"
    )


def check_allowed_environment():
    return True


def start_server():
    host = os.environ.get("WEBAPP_HOST", "127.0.0.1")
    port = int(os.environ.get("WEBAPP_PORT") or os.environ.get("PORT") or "8010")
    uvicorn.run(app, host=host, port=port, log_level="warning")


CLOUDFLARED_PROC = None
NGROK_PROC = None


def _which(name):
    return shutil.which(name)


# quick tunnel subdomainlari doim `so-zir-bu-joy.trycloudflare.com` shaklda
# bo'ladi. `api.trycloudflare.com` esa API hosti — regex uni ushlamasligi kerak.
CF_URL_PATTERN = r"https://[a-z0-9]+(?:-[a-z0-9]+)+\.trycloudflare\.com"


def extract_tunnel_url(log_path, timeout=30, patterns=None):
    """tunnel log faylidan https URL topadi. Block qilmaydi."""
    patterns = patterns or [CF_URL_PATTERN, r"https://[a-z0-9-]+\.ngrok\.app"]
    start = time.time()
    while time.time() - start < timeout:
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except FileNotFoundError:
            time.sleep(0.3)
            continue
        for pat in patterns:
            m = re.search(pat, content)
            if m:
                return m.group(0)
        time.sleep(0.5)
    return None


def ngrok_api_url():
    """ngrok localhost API'dan tunnel URL olish."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for t in data.get("tunnels", []):
                public_url = t.get("public_url", "")
                if public_url.startswith("https://"):
                    return public_url
    except Exception:
        return None
    return None


def start_ngrok():
    """ngrok tunnel ishga tushirish — Termux'da eng ishonchli."""
    global NGROK_PROC
    log_path = os.path.join(config.BASE_DIR, "logs", "ngrok.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
        os.remove(log_path)
    except OSError:
        pass
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            proc = subprocess.Popen(
                ["ngrok", "http", "8010", "--log", "stdout", "--log-format", "logfmt"],
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
            )
        NGROK_PROC = proc
        # ngrok API orqali URL olishga urinamiz, keyin logdan
        for _ in range(30):
            url = ngrok_api_url()
            if url:
                return url, [proc]
            time.sleep(0.5)
        url = extract_tunnel_url(log_path, timeout=10, patterns=[r"https://[a-z0-9-]+\.ngrok\.(app|io)"])
        if url:
            return url, [proc]
        logger.warning("ngrok URL olinmadi (localhost:4040 API'ni tekshiring)")
        return None, [proc]
    except Exception as e:
        logger.error("ngrok xatosi: %s", e)
        return None, []


def start_cloudflared(retries=4):
    global CLOUDFLARED_PROC
    log_path = os.path.join(config.BASE_DIR, "logs", "cloudflared.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
        os.remove(log_path)
    except OSError:
        pass
    procs = []
    for attempt in range(1, retries + 1):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                proc = subprocess.Popen(
                    ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8010", "--no-autoupdate"],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            procs.append(proc)
            CLOUDFLARED_PROC = proc
            url = extract_tunnel_url(log_path, timeout=30, patterns=[CF_URL_PATTERN])
            if url:
                return url, procs
            logger.warning("Tunnel URL ololmadi (urush %d/%d)", attempt, retries)
        except Exception as e:
            logger.error("cloudflared xatosi: %s", e)
            time.sleep(1)
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    return None, procs


def start_tunnel(retries=4):
    """Tunnel: desktopda cloudflared birinchi, Termux'da ngrok."""
    using_termux = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
    if not using_termux and _which("cloudflared"):
        try:
            url, procs = start_cloudflared(retries=retries)
            if url:
                logger.info("cloudflared tunnel: %s", url)
                return url, procs
        except Exception as e:
            logger.error("cloudflared ishga tushmadi: %s", e)
    if using_termux or _which("ngrok"):
        try:
            url, procs = start_ngrok()
            if url:
                logger.info("ngrok tunnel: %s", url)
                return url, procs
        except Exception as e:
            logger.error("ngrok ishga tushmadi: %s", e)
    if _which("cloudflared"):
        try:
            url, procs = start_cloudflared(retries=retries)
            if url:
                logger.info("cloudflared tunnel: %s", url)
                return url, procs
        except Exception as e:
            logger.error("cloudflared ishga tushmadi: %s", e)
    return None, []


LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "bot.lock")
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "bot.pid")
_lock_handle = None


def acquire_single_instance_lock():
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    global _lock_handle
    import fcntl
    _lock_handle = open(LOCK_FILE, "a+", encoding="utf-8")  # noqa: SIM115 — flock uchun ochiq turadi
    try:
        fcntl.flock(_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("⛔ Bot allaqachon ishga tushgan (lock topildi).")
        sys.exit(1)
    _lock_handle.seek(0)
    _lock_handle.truncate()
    _lock_handle.write(str(os.getpid()))
    _lock_handle.flush()


def write_pid_file():
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def main():
    if not check_allowed_environment():
        return

    acquire_single_instance_lock()
    write_pid_file()

    threading.Thread(target=start_server, daemon=True).start()
    time.sleep(1.5)

    external = os.environ.get("EXTERNAL_TUNNEL") == "1" or os.environ.get("RENDER") == "true"
    env_url = os.environ.get("WEBAPP_URL", "").strip() or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
    if env_url:
        url, procs = env_url, []
        logger.info("WEBAPP_URL muhitdan olindi: %s", env_url)
    elif external:
        url, procs = None, []
        logger.info("EXTERNAL_TUNNEL=1 — tashqi tunnel ishlatiladi")
    else:
        url, procs = start_tunnel(retries=4)
    if url:
        config.WEBAPP_URL = url
        config.update_settings({"webapp_url": url})
        import services as svc
        svc.set_webapp_url(url)
        logger.info("WEBAPP_URL = %s", url)
    else:
        saved = ""
        for _ in range(20 if external else 1):
            saved = config.get_settings().get("webapp_url", "")
            if saved:
                break
            time.sleep(1)
        if saved:
            config.WEBAPP_URL = saved
            import services as svc
            svc.set_webapp_url(saved)
            if external:
                logger.info("Tashqi tunnel URL: %s", saved)
            else:
                logger.warning("Yangi tunnel olinmadi, eski URL ishlatilmoqda: %s", saved)
        else:
            logger.error("BUGUNGI KUN: Tunnel URL olinmadi WEBAPP_URL bo'sh. Mini App tugmasi ko'rinmaydi.")

    from bot import run_bot

    max_restarts = 10
    restarts = 0
    try:
        while restarts < max_restarts:
            try:
                asyncio.run(run_bot())
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                restarts += 1
                logger.error("run_bot xatosi (%d/%d): %s", restarts, max_restarts, e)
                if restarts >= max_restarts:
                    break
                time.sleep(min(30, 2 ** restarts))
    finally:
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()