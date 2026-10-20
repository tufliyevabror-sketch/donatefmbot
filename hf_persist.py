import logging
import os
import sys
import tarfile
import tempfile
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("hf_persist")

DATA_DIR = os.environ.get("HF_PERSIST_DIR", os.getcwd())
REPO = os.environ.get("HF_DATASET_REPO", "").strip()
TOKEN = os.environ.get("HF_TOKEN", "").strip()
INTERVAL = int(os.environ.get("HF_SYNC_INTERVAL", "60"))
FILENAME = os.environ.get("HF_PERSIST_FILE", "state.tar.gz")
EXCLUDE = {
    x.strip()
    for x in os.environ.get(
        "HF_PERSIST_EXCLUDE",
        ".env,venv,__pycache__,logs,downloads,tor_data,mirror",
    ).split(",")
    if x.strip()
}


def enabled() -> bool:
    return bool(REPO and TOKEN)


def _filter(tarinfo: tarfile.TarInfo):
    if os.path.basename(tarinfo.name.rstrip("/")) in EXCLUDE:
        return None
    return tarinfo


def ensure_repo() -> None:
    if not enabled():
        return
    try:
        from huggingface_hub import HfApi

        HfApi(token=TOKEN).create_repo(
            repo_id=REPO, repo_type="dataset", private=True, exist_ok=True
        )
        log.info("repo tayyor: %s", REPO)
    except Exception as e:
        log.warning("repo yaratilmadi: %s", e)


def restore() -> None:
    if not enabled():
        log.info("persist o'chirilgan (HF_DATASET_REPO/HF_TOKEN yo'q)")
        return
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id=REPO, filename=FILENAME, repo_type="dataset", token=TOKEN
        )
    except Exception as e:
        log.info("snapshot topilmadi (%s) — toza holatdan boshlanadi", e)
        return
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with tarfile.open(path, "r:gz") as tar:
            try:
                tar.extractall(DATA_DIR, filter="data")
            except TypeError:
                tar.extractall(DATA_DIR)
        log.info("tiklandi: %s -> %s", REPO, DATA_DIR)
    except Exception as e:
        log.warning("tiklash xatosi: %s", e)


def snapshot() -> None:
    if not enabled():
        return
    from huggingface_hub import HfApi

    fd, tmp = tempfile.mkstemp(suffix=".tar.gz")
    os.close(fd)
    try:
        with tarfile.open(tmp, "w:gz") as tar:
            tar.add(DATA_DIR, arcname=".", filter=_filter)
        HfApi(token=TOKEN).upload_file(
            path_or_fileobj=tmp,
            path_in_repo=FILENAME,
            repo_id=REPO,
            repo_type="dataset",
        )
        log.info("saqlandi: %s", FILENAME)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def loop() -> None:
    if not enabled():
        return
    log.info("persist loop boshlandi (har %ss)", INTERVAL)
    while True:
        time.sleep(INTERVAL)
        try:
            snapshot()
        except Exception as e:
            log.warning("snapshot xatosi: %s", e)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "loop"
    if cmd == "restore":
        ensure_repo()
        restore()
    elif cmd == "save":
        snapshot()
    elif cmd == "loop":
        loop()
    else:
        log.error("noma'lum buyruq: %s", cmd)
        sys.exit(2)
