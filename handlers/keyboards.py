"""
Ortak klavye oluşturma yardımcıları
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.i18n import t


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Ana menü inline klavyesi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_users"),     callback_data="menu:users")],
        [InlineKeyboardButton(text=t(lang, "btn_add_panel"), callback_data="menu:add_panel")],
        [InlineKeyboardButton(text=t(lang, "btn_link_limit"),callback_data="menu:link_limit")],
        [InlineKeyboardButton(text=t(lang, "btn_status"),    callback_data="menu:status")],
        [InlineKeyboardButton(text=t(lang, "btn_settings"),  callback_data="menu:settings")],
        [InlineKeyboardButton(text=t(lang, "btn_language"),  callback_data="change_lang")],
    ])


def back_keyboard(lang: str, callback: str = "menu:main") -> InlineKeyboardMarkup:
    """Tek geri butonu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=callback)]
    ])


def cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    """İptal butonu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_cancel"), callback_data="cancel")]
    ])
