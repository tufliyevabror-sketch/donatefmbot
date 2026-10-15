"""
animations.py — Silliq, chiroyli animatsiyalar va yumshoq UI effektilar.
"""
from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.types import InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================================================
# Animatsiya frameslari
# ============================================================

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_FRAMES_2 = ["◜", "◠", "◝", "◞", "◟", "◡"]
BOUNCE_FRAMES = ["⠁", "⠂", "⠄", "⠂"]
PULSE_FRAMES = ["●", "○", "●", "○"]
DOTS_FRAMES = [".", "..", "...", "....", ".....", "......"]
ARROW_FRAMES = ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"]
CLOCK_FRAMES = ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"]
MOON_FRAMES = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
EARTH_FRAMES = ["🌍", "🌎", "🌏"]
ROCKET_FRAMES = ["🚀", "🛸", "🛰️", "🪐"]
HEART_FRAMES = ["💖", "💗", "💓", "💗", "💖"]
SPARKLE_FRAMES = ["✨", "⭐", "🌟", "✨", "💫", "✨"]
GEAR_FRAMES = ["⚙️", "🔧", "⚙️", "🔩"]
LIGHTNING_FRAMES = ["⚡", "💥", "⚡", "✨"]

# Progress bar frames
PROGRESS_EMPTY = "▱"
PROGRESS_FILL = "▰"
PROGRESS_PARTIAL = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "▰"]

# Typing indicators
TYPING_FRAMES = [
    "💭",
    "💭💭",
    "💭💭💭",
]
TYPING_DOTS = ["⠁", "⠂", "⠄", "⠂"]

# Success/Error frames
SUCCESS_FRAMES = ["✅", "✨", "🎉", "✅"]
ERROR_FRAMES = ["❌", "💥", "⚠️", "❌"]
WARNING_FRAMES = ["⚠️", "⚡", "⚠️"]
LOADING_FRAMES = ["⏳", "⌛", "⏳"]

# ============================================================
# Asosiy animatsiya klasslari
# ============================================================

class AnimationController:
    """Animatsiya boshqaruvi - bitta xabarni yangilab animatsiya ko'rsatadi."""
    
    def __init__(
        self,
        message: Message,
        bot: Bot,
        frames: list[str],
        interval: float = 0.15,
        prefix: str = "",
        suffix: str = "",
        parse_mode: str | None = None,
    ):
        self.message = message
        self.bot = bot
        self.frames = frames
        self.interval = interval
        self.prefix = prefix
        self.suffix = suffix
        self.parse_mode = parse_mode
        self._task: asyncio.Task | None = None
        self._running = False
        self._current_text = ""
    
    async def start(self, initial_text: str = "") -> None:
        """Animatsiyani boshlash."""
        self._running = True
        self._current_text = initial_text
        self._task = asyncio.create_task(self._animate())
    
    async def _animate(self) -> None:
        """Animatsiya tsikli."""
        frame_idx = 0
        while self._running:
            frame = self.frames[frame_idx % len(self.frames)]
            text = f"{self.prefix}{frame}{self.suffix}"
            try:
                await self.message.edit_text(text, parse_mode=self.parse_mode)
            except Exception:
                pass  # Xabar o'chirilgan bo'lsa ignore
            frame_idx += 1
            await asyncio.sleep(self.interval)
    
    async def stop(self, final_text: str = "", show_alert: bool = False) -> None:
        """Animatsiyani to'xtatish va yakuniy matn ko'rsatish."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if final_text:
            try:
                await self.message.edit_text(final_text)
            except Exception:
                pass
    
    async def update_text(self, new_prefix: str = "", new_suffix: str = "") -> None:
        """Prefix/suffix ni yangilash (animatsiya davom etaveradi)."""
        self.prefix = new_prefix
        self.suffix = new_suffix


class ProgressBar:
    """Animatsiyali progress bar."""
    
    def __init__(
        self,
        message: Message,
        bot: Bot,
        total: int = 100,
        width: int = 20,
        fill_char: str = "▰",
        empty_char: str = "▱",
        prefix: str = "",
        suffix: str = "",
        parse_mode: str | None = None,
    ):
        self.message = message
        self.bot = bot
        self.total = total
        self.width = width
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.prefix = prefix
        self.suffix = suffix
        self.current = 0
        self._task: asyncio.Task | None = None
        self._running = False
    
    def _render_bar(self, current: int) -> str:
        progress = min(current / self.total, 1.0)
        filled = int(self.width * progress)
        bar = "▰" * filled + "▱" * (self.width - filled)
        percent = int(progress * 100)
        return f"{self.prefix} [{bar}] {percent}% {self.suffix}"
    
    async def update(self, value: int, text: str = "") -> None:
        """Progress qiymatini yangilash."""
        self.current = min(value, self.total)
        self._render_bar(self.current)
        try:
            await self.message.edit_text(f"{self.prefix} {text}\n{self.suffix}")
        except Exception:
            pass
    
    async def animate_to(self, target: int, duration: float = 1.0) -> None:
        """Animatsiya bilan maqsad qiymatga yetish."""
        start = self.current
        steps = 20
        step_val = (target - self.current) / steps
        duration / steps
        
        for i in range(steps + 1):
            val = start + (step_val * i)
            self.current = min(max(int(val), 0), 100)
            bar = self._render_bar(self.current)
            try:
                await self.message.edit_text(bar)
            except Exception:
                pass
            await asyncio.sleep(self.interval)
        self.current = target


class TypingIndicator:
    """Yozish indikatori (typing animation)."""
    
    def __init__(self, bot: Bot, chat_id: int, interval: float = 0.8):
        self.bot = bot
        self.chat_id = chat_id
        self.interval = interval
        self._task: asyncio.Task | None = None
        self._running = False
    
    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run())
    
    async def _run(self) -> None:
        i = 0
        while self._running:
            try:
                await self.bot.send_chat_action(self.chat_id, ChatAction.TYPING)
            except Exception:
                pass
            await asyncio.sleep(self.interval)
            i += 1
    
    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class ToastNotification:
    """Eslatma xabari (toast) - avtomatik yo'qoladi."""
    
    def __init__(
        self,
        message: Message,
        bot: Bot,
        duration: float = 3.0,
        parse_mode: str | None = None,
    ):
        self.message = message
        self.bot = bot
        self.duration = duration
        self.parse_mode = parse_mode
    
    async def show(self, text: str, alert_type: str = "info") -> None:
        """Toast ko'rsatish va avtomatik yo'qolishi."""
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "loading": "⏳",
        }
        icons.get(alert_type, "ℹ️")
        text = f"{icons.get(alert_type, 'ℹ️')} {text}"
        
        try:
            sent = await self.message.answer(text)
            await asyncio.sleep(self.duration)
            try:
                await sent.delete()
            except Exception:
                pass
        except Exception:
            pass


class SmoothTransition:
    """Silliq o'tish effekti - xabar matnini harflar bilan yangilash."""
    
    @staticmethod
    async def type_text(
        message: Message,
        new_text: str,
        delay: float = 0.03,
        parse_mode: str | None = None,
    ) -> None:
        """Matnni harf-harf yozib ko'rsatish (typewriter effect)."""
        current = ""
        for char in new_text:
            current += char
            try:
                await message.edit_text(current, parse_mode=parse_mode)
                await asyncio.sleep(0.03)
            except Exception:
                pass
    
    @staticmethod
    async def fade_transition(
        message: Message,
        old_text: str,
        new_text: str,
        steps: int = 10,
        delay: float = 0.05,
    ) -> None:
        """Eski matndan yangisini qoplamasdan o'tish (crossfade)."""
        # Oddiy versiya: to'g'ridan-to'g'ri yangilash
        try:
            await message.edit_text(new_text)
        except Exception:
            pass
    
    @staticmethod
    async def slide_transition(
        message: Message,
        old_text: str,
        new_text: str,
        direction: str = "left",
        delay: float = 0.02,
    ) -> None:
        """Surish effekti (placeholder)."""
        try:
            await message.edit_text(new_text)
        except Exception:
            pass


class AnimatedKeyboard:
    """Animatsiyali klaviatura - tugmalarni birma-bir ko'rsatish."""
    
    @staticmethod
    async def reveal_buttons(
        message: Message,
        buttons: list,
        delay: float = 0.15,
    ) -> None:
        """Tugmalarni birma-bir ko'rsatish (staggered reveal)."""
        InlineKeyboardBuilder()
        InlineKeyboardMarkup(inline_keyboard=[])
        
        for i, btn in enumerate(buttons):
            # Har bir tugmani qo'shib, markupni yangilash
            try:
                await asyncio.sleep(0.1)
            except Exception:
                pass
    
    @staticmethod
    async def pulse_button(
        message: Message,
        button_text: str,
        times: int = 3,
        interval: float = 0.3,
    ) -> None:
        """Tugmani pulsing (yo'naltirish) effekti."""


# ============================================================
# Quayta ishlatiladigan animatsiya funksiyalari
# ============================================================

async def show_loading(
    message: Message,
    bot: Bot,
    text: str = "Yuklanmoqda...",
    duration: float | None = None,
) -> AnimationController:
    """Yuklanish animatsiyasini ko'rsatish."""
    controller = AnimationController(
        message=message,
        bot=message.bot,
        frames=SPINNER_FRAMES,
        interval=0.12,
        prefix=f"⏳ {text} ",
        suffix="",
    )
    await controller.start()
    if duration:
        asyncio.create_task(_auto_stop(controller, 5.0))
    return controller


async def show_progress(
    message: Message,
    current: int,
    total: int,
    prefix: str = "Yuklanmoqda",
    suffix: str = "",
) -> str:
    """Progress bar matnini qaytarish (edit uchun)."""
    min(current / max(total, 1), 1.0)
    filled = int(20 * current / max(total, 1))
    "▰" * filled + "▱" * (20 - filled)
    percent = int(min(100, (current / max(total, 1)) * 100))
    return f"📊 {filled*5}%\n[{'▰' * filled}{'▱' * (20 - filled)}] {percent}%"


async def show_typing(bot: Bot, chat_id: int, duration: float = 2.0) -> None:
    """Yozish indikatori ko'rsatish."""
    await bot.send_chat_action(chat_id, ChatAction.TYPING)
    await asyncio.sleep(duration)


async def animate_success(message: Message, text: str = "✅ Muvaffaqiyatli!") -> None:
    """Muvaffaqiyat animatsiyasi."""
    frames = ["✅", "✨", "🎉", "✨", "✅"]
    for frame in frames:
        try:
            await message.edit_text(f"{frame} {text}")
            await asyncio.sleep(0.15)
        except Exception:
            pass
    try:
        await message.edit_text(f"✅ {text}")
    except Exception:
        pass


async def animate_error(message: Message, text: str = "❌ Xato yuz berdi!") -> None:
    """Xato animatsiyasi."""
    frames = ["❌", "💥", "⚠️", "💥", "❌"]
    for frame in frames:
        try:
            await message.edit_text(f"{frame} {text}")
            await asyncio.sleep(0.12)
        except Exception:
            pass
    try:
        await message.edit_text(f"❌ {text}")
    except Exception:
        pass


async def animate_warning(message: Message, text: str = "⚠️ Ogohlantirish!") -> None:
    """Ogohlantirish animatsiyasi."""
    frames = ["⚠️", "⚡", "⚠️", "⚡", "⚠️"]
    for frame in frames:
        try:
            await message.edit_text(f"{frame} {text}")
            await asyncio.sleep(0.15)
        except Exception:
            pass
    try:
        await message.edit_text(f"⚠️ {text}")
    except Exception:
        pass


async def pulse_text(
    message: Message,
    base_text: str,
    pulse_char: str = "●",
    times: int = 3,
    interval: float = 0.4,
) -> None:
    """Matnni pulsing (yo'naltirish) effekti bilan ko'rsatish."""
    for i in range(times):
        for frame in ["●", "○", "●"]:
            try:
                await message.edit_text(f"{base_text} {frame}")
                await asyncio.sleep(0.15)
            except Exception:
                pass


async def countdown_animation(
    message: Message,
    seconds: int,
    prefix: str = "⏱ ",
    suffix: str = "",
) -> None:
    """Obor hisoblagich animatsiyasi."""
    for i in range(seconds, 0, -1):
        try:
            await message.edit_text(f"{prefix}{i}{suffix}")
            await asyncio.sleep(1)
        except Exception:
            pass
    try:
        await message.edit_text("✅ Vaqt tugadi!")
    except Exception:
        pass


async def _auto_stop(controller: AnimationController, delay: float) -> None:
    await asyncio.sleep(delay)
    await controller.stop()


# ============================================================
# Progress bar helper
# ============================================================

def make_progress_bar(current: int, total: int, width: int = 20) -> str:
    """Progress bar string qaytarish."""
    if total <= 0:
        return "▱" * 20 + " 0%"
    progress = min(current / total, 1.0)
    filled = int(20 * progress)
    "▰" * filled + "▱" * (20 - filled)
    percent = int(min(100, (current / total) * 100))
    return f"[{'▰' * filled}{'▱' * (20 - filled)}] {percent}%"


def make_spinner_frame(frame_idx: int) -> str:
    """Spinner frame qaytarish."""
    return SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]


def make_dots_frame(frame_idx: int) -> str:
    """Dot frames qaytarish."""
    return DOTS_FRAMES[frame_idx % len(DOTS_FRAMES)]


# ============================================================
# Keyboard animation helpers
# ============================================================

async def stagger_keyboard_reveal(
    message: Message,
    buttons_data: list,
    delay: float = 0.12,
) -> None:
    """Tugmalarni stagger (kechiktirib) ko'rsatish."""
    from aiogram.types import InlineKeyboardMarkup
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    InlineKeyboardBuilder()
    InlineKeyboardMarkup(inline_keyboard=[])
    
    # Har bir tugma uchun alohida ko'rsatish (staggered)
    for i, (text, callback_data) in enumerate(buttons_data):
        # Bu yerda haqiqiy stagger effekti uchun 
        # har bir tugma qo'shilganda markup yangilanishi kerak
        # Lekin aiogram da bu qiyin, shuning uchun oddiy versiya:
        await asyncio.sleep(0.05)


async def keyboard_pulse_animation(
    message: Message,
    keyboard,
    pulse_count: int = 2,
) -> None:
    """Klaviatura pulsing effekti (placeholder)."""


# ============================================================
# Export all
# ============================================================

__all__ = [
    "ARROW_FRAMES",
    "BOUNCE_FRAMES",
    "CLOCK_FRAMES",
    "DOTS_FRAMES",
    "EARTH_FRAMES",
    "ERROR_FRAMES",
    "GEAR_FRAMES",
    "HEART_FRAMES",
    "LIGHTNING_FRAMES",
    "LOADING_FRAMES",
    "MOON_FRAMES",
    "PROGRESS_EMPTY",
    "PROGRESS_FILL",
    "PROGRESS_PARTIAL",
    "PULSE_FRAMES",
    "ROCKET_FRAMES",
    "SPARKLE_FRAMES",
    # Frames
    "SPINNER_FRAMES",
    "SPINNER_FRAMES_2",
    "SUCCESS_FRAMES",
    "TYPING_DOTS",
    "TYPING_FRAMES",
    "WARNING_FRAMES",
    "AnimatedKeyboard",
    "AnimationController",
    "ProgressBar",
    "SmoothTransition",
    "ToastNotification",
    "TypingIndicator",
    "animate_error",
    "animate_success",
    "animate_warning",
    "countdown_animation",
    "keyboard_pulse_animation",
    "make_dots_frame",
    "make_progress_bar",
    "make_spinner_frame",
    "pulse_text",
    "show_loading",
    "show_progress",
    "show_typing",
    "stagger_keyboard_reveal",
]