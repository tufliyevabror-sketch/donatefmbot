"""Router marshrutining integratsion testi — haqiqiy Bot + soxta session.

Maqsad: catch-all `F.text` handler buyruqlarni yutmasligini isbotlash.
Oldingi xato: `/start` -> qidiruvga ketardi (router tartibi noto'g'ri).

Session tarmoqqa ulanmaydi: har bir Telegram metodi `calls` ga yoziladi
va plauz javob qaytaradi. Shu sabab handlerlar haqiqiycha ishlaydi
(`Message.answer` bot'ga mount bo'ladi) — lekin internet kerak bo'lmaydi.
"""
import asyncio
import sys
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, "/home/abror69/donatefmbot")

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

import bot as botmod
import handlers.catalog
import handlers.payments
import handlers.start

FAKE_TOKEN = "123456:AAHfakefakefakefakefakefakefakefake"


class FakeSession(BaseSession):
    """Tarmoqqa ulanmaydi, metodlarni yozib qo'yadi."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):
        name = type(method).__api_method__
        self.calls.append(name)
        if name == "getMe":
            return User(id=111, is_bot=True, first_name="DonateFM", username="donatefm_bot")
        if name == "sendMessage":
            return Message(
                message_id=1,
                date=datetime.now(),
                chat=Chat(id=getattr(method, "chat_id", 0) or 0, type="private"),
                text=getattr(method, "text", "") or "",
            )
        if name == "answerCallbackQuery":
            return True
        return True

    async def stream_content(self, url, headers=None, timeout=30,
                             chunk_size=65536, raise_for_status=True):
        yield b""


_DP = None
_SESSION = None


def build():
    """run_bot() dagi router tartibini takrorlaydi (bir marta ulanadi)."""
    global _DP, _SESSION
    if _DP is None:
        _SESSION = FakeSession()
        _DP = Dispatcher(storage=MemoryStorage())
        _DP.include_router(handlers.start.router)
        _DP.include_router(handlers.catalog.router)
        _DP.include_router(handlers.payments.router)
        _DP.include_router(botmod.router)
    return _DP, Bot(token=FAKE_TOKEN, session=_SESSION)


def update(text, uid=5550001, mid=1):
    return Update(
        update_id=mid,
        message=Message(
            message_id=mid,
            date=datetime.now(),
            chat=Chat(id=uid, type="private"),
            from_user=User(id=uid, is_bot=False, first_name="Test"),
            text=text,
        ),
    )


async def run(text, **patches):
    dp, bot = build()
    _SESSION.calls.clear()
    ctx = [patch.object(target, name, new=new) for target, name, new in patches]
    for c in ctx:
        c.start()
    try:
        await dp.feed_update(bot, update(text))
    finally:
        for c in ctx:
            c.stop()


# ---------------------------------------------------------------- testlar

async def test_start_routes_to_cmd_start():
    """/start -> handlers.start.cmd_start; catch-all ISHLAMASLIGI kerak."""
    with patch.object(handlers.start.ls, "start_text", return_value="SALOM") as start_txt, \
         patch.object(botmod.ls, "menu_text", return_value="MENU") as menu_txt, \
         patch.object(handlers.start.db, "get_user", new=AsyncMockFactory(None)), \
         patch.object(handlers.start.db, "register_user", new=AsyncMockFactory(None)), \
         patch.object(handlers.start.config, "get_settings",
                      return_value={"webapp_url": "", "announcement": ""}):
        await run("/start")

    assert start_txt.called, "cmd_start ISHLAMADI — /start yutilib ketgan"
    assert not menu_txt.called, "catch-all ishladi — /start menyuga ketgan"
    print("  OK  /start -> cmd_start (catch-all ishga kirmadi)")


async def test_unknown_command_is_rejected():
    """`/audio` -> 'Noma'lum buyruq'; FSM holatiga aralashmasligi kerak."""
    from unittest.mock import AsyncMock

    with patch.object(botmod, "_ensure_not_banned", new=AsyncMock(return_value=True)), \
         patch.object(botmod.ls, "menu_text", return_value="MENU") as menu_txt:
        dp, bot = build()
        _SESSION.calls.clear()
        await dp.feed_update(bot, update("/audio"))
        sent = list(_SESSION.calls)

    assert "sendMessage" in sent, f"javob yuborilmadi (chaqirilgan: {sent})"
    assert not menu_txt.called, "noma'lum buyruq catch-all'ga tushdi"
    print("  OK  /audio -> javob yuborildi, catch-all ishga kirmadi")


async def test_known_command_reaches_main_router():
    """`/help` main router'da — state handler'ga yutilmasligi kerak."""
    from unittest.mock import AsyncMock

    with patch.object(botmod, "_help_text", return_value="YORDAM") as help_txt, \
         patch.object(botmod, "_ensure_not_banned", new=AsyncMock(return_value=True)):
        await run("/help")
    assert help_txt.called, "/help handler ishladi emas"
    print("  OK  /help -> _help_text")


async def test_plain_text_reaches_catchall():
    """Oddiy matn catch-all ga borishi kerak — aks holda bot javob bermaydi."""
    from unittest.mock import AsyncMock

    with patch.object(botmod, "_ensure_not_banned", new=AsyncMock(return_value=True)), \
         patch.object(botmod.ls, "menu_text", return_value="MENU") as menu_txt:
        await run("salom")
    assert menu_txt.called, "oddiy matn catch-all'ga tushmadi"
    print("  OK  'salom' -> catch-all (menu_text)")


def AsyncMockFactory(value):
    from unittest.mock import AsyncMock

    m = AsyncMock(return_value=value)
    return m


async def main():
    print("=== ROUTER MARSHRUTI (haqiqiy Bot + soxta session) ===")
    tests = [
        test_start_routes_to_cmd_start,
        test_unknown_command_is_rejected,
        test_known_command_reaches_main_router,
        test_plain_text_reaches_catchall,
    ]
    for t in tests:
        await t()
    print(f"BARCHA {len(tests)} TA TEST O'TDI")


if __name__ == "__main__":
    asyncio.run(main())