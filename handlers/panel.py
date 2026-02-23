"""
Panel bağlama handler'ları
Kullanıcı URL → username → password girer; API test edilir
"""
import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database as db
from config import ADMIN_ID
from marzban_api import MarzbanAPI
from handlers.i18n import t
from handlers.keyboards import main_menu_keyboard, cancel_keyboard

router = Router()
logger = logging.getLogger(__name__)


class PanelForm(StatesGroup):
    """Panel ekleme form adımları."""
    url = State()
    username = State()
    password = State()


@router.callback_query(F.data == "menu:add_panel")
async def cb_add_panel(callback: CallbackQuery, state: FSMContext) -> None:
    """Panel ekleme başlat."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)

    # Yasaklı kontrol
    if await db.is_banned(tg_id):
        await callback.answer(t(lang, "banned"), show_alert=True)
        return

    await state.set_state(PanelForm.url)
    await callback.message.answer(t(lang, "panel_enter_url"), parse_mode="HTML",
                                  reply_markup=cancel_keyboard(lang))
    await callback.answer()


@router.message(PanelForm.url)
async def form_url(message: Message, state: FSMContext) -> None:
    """URL adımı."""
    tg_id = message.from_user.id
    lang = await db.get_user_lang(tg_id)

    url = message.text.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        await message.answer(t(lang, "panel_error"))
        return

    await state.update_data(url=url)
    await state.set_state(PanelForm.username)
    await message.answer(t(lang, "panel_enter_username"), reply_markup=cancel_keyboard(lang))


@router.message(PanelForm.username)
async def form_username(message: Message, state: FSMContext) -> None:
    """Kullanıcı adı adımı."""
    tg_id = message.from_user.id
    lang = await db.get_user_lang(tg_id)

    await state.update_data(username=message.text.strip())
    await state.set_state(PanelForm.password)
    await message.answer(t(lang, "panel_enter_password"), reply_markup=cancel_keyboard(lang))


@router.message(PanelForm.password)
async def form_password(message: Message, state: FSMContext) -> None:
    """Şifre adımı - API bağlantısı dene."""
    tg_id = message.from_user.id
    lang = await db.get_user_lang(tg_id)
    data = await state.get_data()
    await state.clear()

    url = data["url"]
    username = data["username"]
    password = message.text.strip()

    # Bağlanılıyor bildirimi
    connecting_msg = await message.answer(t(lang, "panel_connecting"))

    api = MarzbanAPI(url, username, password)
    success = await api.test_connection()

    if not success:
        logger.warning("Panel connection failed: url=%s user=%s", url, username)
        await connecting_msg.edit_text(t(lang, "panel_error"))
        return

    # Veritabanına kaydet
    panel_id = await db.add_panel(tg_id, url, username, password)

    await connecting_msg.edit_text(
        t(lang, "panel_connected", url=url, username=username),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )

    # Admin'e bildirim gönder
    if ADMIN_ID and tg_id != ADMIN_ID:
        try:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            # Admin'in tercih ettiği dilde bildirim gönder
            admin_lang = await db.get_user_lang(ADMIN_ID)
            notify_text = t(admin_lang, "admin_panel_notify",
                            tg_id=tg_id, url=url, username=username, time=now)
            from bot import bot as _bot
            await _bot.send_message(ADMIN_ID, notify_text, parse_mode="HTML")
        except Exception:
            pass
