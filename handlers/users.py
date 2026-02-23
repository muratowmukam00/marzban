"""
Kullanıcı listeleme ve limit koyma handler'ları
Panel seç → Kullanıcı seç → Limit belirle
Ayrıca subscription link ile limit koyma
"""
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from marzban_api import MarzbanAPI
from handlers.i18n import t
from handlers.keyboards import main_menu_keyboard, cancel_keyboard, back_keyboard

router = Router()

# Sabit limit seçenekleri
LIMIT_OPTIONS = [1, 2, 3, 5, 10]


class LimitForm(StatesGroup):
    """Limit koyma form adımları."""
    custom_limit = State()    # Özel limit sayısı
    link_input = State()      # Subscription link
    link_panel_select = State()  # Link'ten gelen kullanıcı için panel seçimi


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def panels_keyboard(panels: list[dict], lang: str) -> InlineKeyboardMarkup:
    """Panel listesi klavyesi."""
    buttons = []
    for p in panels:
        label = p.get("label") or p["url"]
        buttons.append([InlineKeyboardButton(
            text=f"🖥️ {label}", callback_data=f"panel_sel:{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def users_keyboard(users: list[dict], panel_id: int, lang: str) -> InlineKeyboardMarkup:
    """Marzban kullanıcı listesi klavyesi."""
    buttons = []
    for u in users[:30]:  # İlk 30 kullanıcı göster
        buttons.append([InlineKeyboardButton(
            text=f"👤 {u['username']}",
            callback_data=f"user_sel:{panel_id}:{u['username']}"
        )])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data="menu:users")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def limit_keyboard(panel_id: int, marzban_user: str, lang: str) -> InlineKeyboardMarkup:
    """Limit seçim klavyesi."""
    buttons = []
    row = []
    for opt in LIMIT_OPTIONS:
        row.append(InlineKeyboardButton(
            text=str(opt),
            callback_data=f"set_limit:{panel_id}:{marzban_user}:{opt}"
        ))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(
        text=t(lang, "limit_custom"),
        callback_data=f"custom_limit:{panel_id}:{marzban_user}"
    )])
    buttons.append([InlineKeyboardButton(
        text=t(lang, "btn_remove_limit"),
        callback_data=f"remove_limit:{panel_id}:{marzban_user}"
    )])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_back"), callback_data=f"panel_sel:{panel_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ---------------------------------------------------------------------------
# Kullanıcı listesi menüsü
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "menu:users")
async def cb_menu_users(callback: CallbackQuery) -> None:
    """Panel seçim ekranı."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)

    if await db.is_banned(tg_id):
        await callback.answer(t(lang, "banned"), show_alert=True)
        return

    panels = await db.get_panels(tg_id)
    if not panels:
        await callback.message.answer(t(lang, "panel_list_empty"), parse_mode="HTML")
        await callback.answer()
        return

    await callback.message.answer(
        t(lang, "panel_select"),
        reply_markup=panels_keyboard(panels, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("panel_sel:"))
async def cb_panel_selected(callback: CallbackQuery) -> None:
    """Panel seçildi, kullanıcıları listele."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    panel_id = int(callback.data.split(":")[1])

    panel = await db.get_panel(panel_id)
    if not panel or panel["tg_id"] != tg_id:
        await callback.answer(t(lang, "error_generic"), show_alert=True)
        return

    api = MarzbanAPI(panel["url"], panel["username"], panel["password"])
    try:
        data = await api.get_users()
        users = data.get("users", [])
    except Exception:
        await callback.message.answer(t(lang, "panel_error"))
        await callback.answer()
        return

    if not users:
        await callback.message.answer(t(lang, "users_empty"))
        await callback.answer()
        return

    await callback.message.answer(
        t(lang, "users_list_header", panel_url=panel["url"]),
        parse_mode="HTML",
        reply_markup=users_keyboard(users, panel_id, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("user_sel:"))
async def cb_user_selected(callback: CallbackQuery) -> None:
    """Kullanıcı seçildi, limit sorusu göster."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    _, panel_id_str, marzban_user = callback.data.split(":", 2)
    panel_id = int(panel_id_str)

    await callback.message.answer(
        t(lang, "limit_ask", username=marzban_user),
        parse_mode="HTML",
        reply_markup=limit_keyboard(panel_id, marzban_user, lang),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Limit ayarlama
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("set_limit:"))
async def cb_set_limit(callback: CallbackQuery) -> None:
    """Limit butonuna basıldı."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    parts = callback.data.split(":")
    panel_id, marzban_user, limit_val = int(parts[1]), parts[2], int(parts[3])

    await db.set_limit(panel_id, marzban_user, limit_val)
    await callback.message.answer(
        t(lang, "limit_set", username=marzban_user, limit=limit_val),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("custom_limit:"))
async def cb_custom_limit(callback: CallbackQuery, state: FSMContext) -> None:
    """Özel limit girişi."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    _, panel_id_str, marzban_user = callback.data.split(":", 2)

    await state.update_data(panel_id=int(panel_id_str), marzban_user=marzban_user)
    await state.set_state(LimitForm.custom_limit)
    await callback.message.answer(t(lang, "limit_custom_ask"), reply_markup=cancel_keyboard(lang))
    await callback.answer()


@router.message(LimitForm.custom_limit)
async def form_custom_limit(message: Message, state: FSMContext) -> None:
    """Özel limit değerini işle."""
    tg_id = message.from_user.id
    lang = await db.get_user_lang(tg_id)
    data = await state.get_data()
    await state.clear()

    try:
        limit_val = int(message.text.strip())
        if limit_val < 1:
            raise ValueError
    except ValueError:
        await message.answer(t(lang, "limit_invalid"))
        return

    panel_id = data["panel_id"]
    marzban_user = data["marzban_user"]
    await db.set_limit(panel_id, marzban_user, limit_val)
    await message.answer(
        t(lang, "limit_set", username=marzban_user, limit=limit_val),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )


@router.callback_query(F.data.startswith("remove_limit:"))
async def cb_remove_limit(callback: CallbackQuery) -> None:
    """Limiti kaldır."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    _, panel_id_str, marzban_user = callback.data.split(":", 2)
    panel_id = int(panel_id_str)

    await db.remove_limit(panel_id, marzban_user)
    await callback.message.answer(
        t(lang, "limit_removed", username=marzban_user),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Subscription link ile limit koyma
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "menu:link_limit")
async def cb_menu_link_limit(callback: CallbackQuery, state: FSMContext) -> None:
    """Link ile limit koyma başlat."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)

    if await db.is_banned(tg_id):
        await callback.answer(t(lang, "banned"), show_alert=True)
        return

    await state.set_state(LimitForm.link_input)
    await callback.message.answer(t(lang, "link_ask"), reply_markup=cancel_keyboard(lang))
    await callback.answer()


@router.message(LimitForm.link_input)
async def form_link_input(message: Message, state: FSMContext) -> None:
    """Subscription linkinden kullanıcı adını çıkar."""
    tg_id = message.from_user.id
    lang = await db.get_user_lang(tg_id)
    link = message.text.strip()

    # Subscription link formatı: https://panel.example.com:8080/sub/USERNAME/...
    # veya https://panel.example.com:8080/api/sub/USERNAME
    match = re.search(r"/sub/([^/?#\s]+)", link)
    if not match:
        await message.answer(t(lang, "link_invalid"))
        await state.clear()
        return

    marzban_user = match.group(1)
    panels = await db.get_panels(tg_id)
    if not panels:
        await message.answer(t(lang, "no_panels"))
        await state.clear()
        return

    # Panel seçim klavyesi göster
    await state.update_data(marzban_user=marzban_user)
    await state.set_state(LimitForm.link_panel_select)

    buttons = []
    for p in panels:
        label = p.get("label") or p["url"]
        buttons.append([InlineKeyboardButton(
            text=f"🖥️ {label}", callback_data=f"lp_sel:{p['id']}"
        )])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        t(lang, "link_user_found", username=marzban_user),
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("lp_sel:"), LimitForm.link_panel_select)
async def cb_link_panel_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Link ile limit koymak için panel seçildi."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)
    panel_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    marzban_user = data["marzban_user"]
    await state.clear()

    await callback.message.answer(
        t(lang, "limit_ask", username=marzban_user),
        parse_mode="HTML",
        reply_markup=limit_keyboard(panel_id, marzban_user, lang),
    )
    await callback.answer()
