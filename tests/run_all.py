"""Barcha testlarni bitta buyruq bilan ishga tushurish:

    ./venv/bin/python tests/run_all.py

Tarmoqqa ulanmaydi. Testlar haqiqiy DB'ga YOZMAYDI.
"""
import asyncio
import importlib.util
import inspect
import sys
import traceback
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_names(mod):
    return sorted(n for n in dir(mod) if n.startswith("test_"))


def run_tests(mod):
    """Sync va async testlarni TO'G'RI ishga tushiradi.

    Muhim: async testlarni await qilmasdan chaqirish koroutine yaratib
    tashlab ketadi — test «o'tgan»dek ko'rinadi, lekin umuman ishlamaydi.
    """
    ran = 0
    for n in test_names(mod):
        fn = getattr(mod, n)
        if inspect.iscoroutinefunction(fn):
            asyncio.run(fn())
        else:
            fn()
        ran += 1
    return ran


def main():
    files = ["test_api.py", "test_routing.py", "test_security.py"]
    results = []
    for fname in files:
        p = Path(__file__).parent / fname
        if not p.exists():
            continue
        mod = load(p)
        try:
            n = run_tests(mod)
            results.append(("OK", fname, n, None))
        except AssertionError as e:
            results.append(("FAIL", fname, len(test_names(mod)), e))
        except Exception as e:
            results.append(("ERR", fname, len(test_names(mod)), e))

    print()
    print("=== NATIJA ===")
    total = bad = 0
    for status, fname, n, err in results:
        total += n
        if status == "OK":
            print(f"[OK]   {fname}: {n}/{n}")
        else:
            bad += 1
            print(f"[{status}] {fname}: muammo -> {type(err).__name__}: {err}")

    if bad:
        print(f"\nXATO: {bad}/{len(results)} ta faylda muammo")
        return 1
    print(f"\nHAMMA TESTLAR HAQIQATAN O'TDI — {total} ta test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())