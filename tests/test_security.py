"""Konfig xavfsizlik testlari: secret kodda qolmasligi kerak."""


def test_no_hardcoded_token():
    with open("config.py", encoding="utf-8") as f:
        src = f.read()
    assert "AAFp7RU2Et3ZykGmeiq_UEQOf7pZp-Ut6Xo" not in src
    assert "AAEoLC5p5eibymlvqOKMXw_wgA9ZEiuEkkY" not in src


def test_env_example_has_placeholder():
    with open(".env.example", encoding="utf-8") as f:
        src = f.read()
    assert "BOT_TOKEN=" in src
    assert "example" in src.lower() or "replace_me" in src


def test_gitignore_covers_secrets():
    with open(".gitignore", encoding="utf-8") as f:
        src = f.read()
    for needle in (".env", "*.db", "logs/"):
        assert needle in src
