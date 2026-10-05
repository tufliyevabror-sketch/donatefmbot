import asyncio

BOT = None
MAIN_LOOP = None
WEBAPP_URL = ""


def set_bot(bot, loop):
    global BOT, MAIN_LOOP
    BOT = bot
    MAIN_LOOP = loop


def get_bot():
    if BOT is None:
        raise RuntimeError("Bot hali o'rnatilmagan")
    return BOT


def set_webapp_url(url):
    global WEBAPP_URL
    WEBAPP_URL = url


def call_bot(coro_factory):
    """Bot metodini asosiy (polling) loopida bajarish."""
    if MAIN_LOOP is None:
        raise RuntimeError("Main loop yo'q")
    coro = coro_factory()
    fut = asyncio.run_coroutine_threadsafe(coro, MAIN_LOOP)
    return fut.result(timeout=15)


def safe_call_bot(coro_factory):
    try:
        return call_bot(coro_factory)
    except Exception:
        return None