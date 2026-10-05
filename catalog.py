"""`data/packages.json` katalogni o'qish/yozish (atomik + oraliq qulf)."""
import json
import logging
import os

from config import PACKAGES_PATH

logger = logging.getLogger("catalog")

LOCK_PATH = PACKAGES_PATH + ".lock"
TMP_PATH = PACKAGES_PATH + ".tmp"


def load():
    with open(PACKAGES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_games():
    return load().get("games", [])


def find_game(game_id):
    for g in load_games():
        if g.get("id") == game_id:
            return g
    return None


def _lock_fd():
    import fcntl

    fd = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT, 0o644)
    return fd, fcntl


def save_games(games):
    """Katalogni atomik yozadi (flock + os.replace)."""
    fd, fcntl = _lock_fd()
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        data = load()
        data["games"] = games
        with open(TMP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(TMP_PATH, PACKAGES_PATH)
        logger.info("Katalog saqlandi: %d ta o'yin", len(games))
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)


def save(data):
    fd, fcntl = _lock_fd()
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with open(TMP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(TMP_PATH, PACKAGES_PATH)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)


# ---------------- O'yin (game) ----------------

def add_game(game_id, name, emoji="", desc=""):
    games = load_games()
    if find_game(game_id):
        return None, "Bunday ID allaqachon mavjud"
    gid = game_id.strip().lower()
    if not gid:
        return None, "ID bo'sh bo'lishi mumkin emas"
    games.append({
        "id": gid,
        "name": name.strip(),
        "emoji": emoji.strip(),
        "desc": desc.strip(),
        "grid_mode": True,
        "categories": {"all": "Hammasi"},
        "packages": [],
    })
    save_games(games)
    return find_game(gid), None


def update_game(game_id, fields):
    games = load_games()
    for g in games:
        if g.get("id") == game_id:
            g.update(fields)
            save_games(games)
            return g
    return None


def delete_game(game_id):
    games = load_games()
    new = [g for g in games if g.get("id") != game_id]
    if len(new) == len(games):
        return False
    save_games(new)
    return True


# ---------------- Paket ----------------

def add_package(game_id, pkg):
    games = load_games()
    for g in games:
        if g.get("id") == game_id:
            g.setdefault("packages", []).append(pkg)
            save_games(games)
            return pkg
    return None


def update_package(game_id, pkg_id, fields):
    games = load_games()
    for g in games:
        if g.get("id") != game_id:
            continue
        for p in g.get("packages", []):
            if p.get("id") == pkg_id:
                p.update(fields)
                save_games(games)
                return p
    return None


def delete_package(game_id, pkg_id):
    games = load_games()
    for g in games:
        if g.get("id") != game_id:
            continue
        before = len(g.get("packages", []))
        g["packages"] = [p for p in g.get("packages", []) if p.get("id") != pkg_id]
        if len(g["packages"]) == before:
            return False
        save_games(games)
        return True
    return False


def unique_package_id(game_id, base="pkg"):
    existing = {p.get("id") for p in (find_game(game_id) or {}).get("packages", [])}
    n = 1
    while f"{game_id}-{base}{n}" in existing:
        n += 1
    return f"{game_id}-{base}{n}"
