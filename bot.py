"""
Ana bot dosyası - Aiogram 3.x dispatcher kurulumu ve APScheduler
"""
import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, CHECK_INTERVAL
import database as db
import limiter
from handlers import start, panel, users, status, admin
from handlers.i18n import t
from handlers.keyboards import main_menu_keyboard

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Bot ve dispatcher nesneleri
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())


# ---------------------------------------------------------------------------
# Ana menü callback'i
# ---------------------------------------------------------------------------

@dp.callback_query(lambda c: c.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery) -> None:
    """Ana menüye dön."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    await callback.message.answer(
        t(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


# Ayarlar menüsü
@dp.callback_query(lambda c: c.data == "menu:settings")
async def cb_settings(callback: CallbackQuery) -> None:
    """Ayarlar menüsünü göster."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "settings_my_panels"), callback_data="settings:panels")],
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:main")],
    ])
    await callback.message.answer(t(lang, "settings_header"), reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "settings:panels")
async def cb_settings_panels(callback: CallbackQuery) -> None:
    """Kullanıcının panellerini listele (silme seçeneğiyle)."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)

    panels = await db.get_panels(tg_id)
    if not panels:
        await callback.message.answer(t(lang, "panel_list_empty"), parse_mode="HTML")
        await callback.answer()
        return

    buttons = []
    for p in panels:
        label = p.get("label") or p["url"]
        buttons.append([
            InlineKeyboardButton(text=f"🖥️ {label}", callback_data=f"noop"),
            InlineKeyboardButton(
                text="🗑️", callback_data=f"del_panel:{p['id']}"
            ),
        ])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:settings")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(t(lang, "panel_list_header"), parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("del_panel:"))
async def cb_delete_panel(callback: CallbackQuery) -> None:
    """Paneli sil."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    panel_id = int(callback.data.split(":")[1])

    deleted = await db.delete_panel(panel_id, tg_id)
    if deleted:
        await callback.message.answer(t(lang, "panel_deleted"),
                                      reply_markup=main_menu_keyboard(lang))
    else:
        await callback.message.answer(t(lang, "error_generic"))
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """FSM işlemini iptal et."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    await state.clear()
    await callback.message.answer(
        t(lang, "operation_cancelled"),
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """Hiçbir şey yapma (dekoratif buton)."""
    await callback.answer()


# ---------------------------------------------------------------------------
# Tüm handler router'larını kaydet
# ---------------------------------------------------------------------------

dp.include_router(start.router)
dp.include_router(panel.router)
dp.include_router(users.router)
dp.include_router(status.router)
dp.include_router(admin.router)


# ---------------------------------------------------------------------------
# Başlatma ve zamanlayıcı
# ---------------------------------------------------------------------------

async def on_startup() -> None:
    """Bot başlarken çalışır."""
    await db.init_db()
    limiter.set_bot(bot)
    logger.info("Veritabanı başlatıldı.")


async def main() -> None:
    """Ana giriş noktası."""
    await on_startup()

    # APScheduler ile periyodik limit kontrolü
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        limiter.run_check_cycle,
        trigger="interval",
        seconds=CHECK_INTERVAL,
        id="limit_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Zamanlayıcı başlatıldı: her %d saniyede bir kontrol.", CHECK_INTERVAL)

    try:
        logger.info("Bot başlatılıyor...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
