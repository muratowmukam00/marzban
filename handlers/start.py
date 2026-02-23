"""
Start handler - /start komutu ve dil seçimi
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import database as db
from handlers.i18n import t
from handlers.keyboards import main_menu_keyboard

router = Router()


def language_keyboard() -> InlineKeyboardMarkup:
    """Dil seçim klavyesi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data="lang:tr"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ]
    ])


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """/start komutunu işle: kullanıcıyı kaydet, dil seç."""
    tg_id = message.from_user.id

    # Kullanıcıyı veritabanına kaydet (yoksa)
    user = await db.get_or_create_user(tg_id)

    # Yasaklı mı?
    if user["is_banned"]:
        lang = user.get("lang", "en")
        await message.answer(t(lang, "banned"))
        return

    # Dil seçim ekranı göster
    await message.answer(
        t("en", "choose_language"),
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def cb_language(callback: CallbackQuery) -> None:
    """Dil seçimi callback."""
    tg_id = callback.from_user.id
    lang = callback.data.split(":")[1]

    if lang not in ("tr", "en", "ru"):
        await callback.answer()
        return

    # Dili kaydet
    await db.get_or_create_user(tg_id, lang)
    await db.set_user_lang(tg_id, lang)

    await callback.message.edit_text(
        t(lang, "language_set"),
    )
    # Ana menüyü göster
    await callback.message.answer(
        t(lang, "main_menu"),
        reply_markup=main_menu_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "change_lang")
async def cb_change_language(callback: CallbackQuery) -> None:
    """Dil değiştirme callback."""
    await callback.message.answer(
        t("en", "choose_language"),
        reply_markup=language_keyboard(),
    )
    await callback.answer()
