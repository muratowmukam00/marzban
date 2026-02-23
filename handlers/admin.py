"""
Admin handler'ları - sadece ADMIN_ID'ye sahip kullanıcılar için
İstatistikler, kullanıcı listesi, yasaklama
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from config import ADMIN_ID
from handlers.i18n import t
from handlers.keyboards import main_menu_keyboard, cancel_keyboard

router = Router()


def is_admin(tg_id: int) -> bool:
    """Kullanıcının admin olup olmadığını kontrol et."""
    return bool(ADMIN_ID) and tg_id == ADMIN_ID


class AdminForm(StatesGroup):
    """Admin işlem form adımları."""
    ban_user = State()
    unban_user = State()


# ---------------------------------------------------------------------------
# Admin komutu ve menüsü
# ---------------------------------------------------------------------------

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """/admin komutu - sadece admin'e görünür."""
    tg_id = message.from_user.id
    if not is_admin(tg_id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 İstatistikler", callback_data="admin:stats")],
        [InlineKeyboardButton(text="👥 Tüm Kullanıcılar", callback_data="admin:users")],
        [InlineKeyboardButton(text="🚫 Kullanıcı Yasakla", callback_data="admin:ban")],
        [InlineKeyboardButton(text="✅ Yasak Kaldır", callback_data="admin:unban")],
        [InlineKeyboardButton(text="🖥️ Tüm Paneller", callback_data="admin:panels")],
    ])
    await message.answer("🛡️ <b>Admin Paneli</b>", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery) -> None:
    """İstatistikleri göster."""
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    stats = await db.get_stats()
    text = t("tr", "admin_stats",
             total_users=stats["total_users"],
             total_panels=stats["total_panels"],
             total_limits=stats["total_limits"],
             total_violations=stats["total_violations"])
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def cb_admin_users(callback: CallbackQuery) -> None:
    """Tüm kullanıcıları listele."""
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    users = await db.get_all_users()
    lines = [t("tr", "admin_users_header")]
    for u in users:
        banned_str = "✅" if u["is_banned"] else "—"
        lines.append(t("tr", "admin_user_row",
                       tg_id=u["tg_id"], lang=u["lang"], banned=banned_str))

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:panels")
async def cb_admin_panels(callback: CallbackQuery) -> None:
    """Tüm panelleri listele."""
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    panels = await db.get_all_panels()
    if not panels:
        await callback.message.answer("📭 Panel bulunamadı.")
        await callback.answer()
        return

    lines = ["🖥️ <b>Tüm Paneller:</b>"]
    for p in panels:
        lines.append(f"\n🆔 Panel #{p['id']}\n👤 TG: {p['tg_id']}\n🔗 {p['url']}\n👤 {p['username']}")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


# ---------------------------------------------------------------------------
# Kullanıcı yasaklama
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "admin:ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext) -> None:
    """Yasaklamak için ID sor."""
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminForm.ban_user)
    await callback.message.answer(t("tr", "admin_ban_ask"),
                                  reply_markup=cancel_keyboard("tr"))
    await callback.answer()


@router.message(AdminForm.ban_user)
async def form_ban_user(message: Message, state: FSMContext) -> None:
    """Yasaklama işlemi."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Geçersiz ID.")
        return
    await db.ban_user(target_id)
    await message.answer(t("tr", "admin_banned", tg_id=target_id))


@router.callback_query(F.data == "admin:unban")
async def cb_admin_unban(callback: CallbackQuery, state: FSMContext) -> None:
    """Yasak kaldırmak için ID sor."""
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.set_state(AdminForm.unban_user)
    await callback.message.answer("Yasağını kaldırmak istediğiniz kullanıcının ID'sini girin:",
                                  reply_markup=cancel_keyboard("tr"))
    await callback.answer()


@router.message(AdminForm.unban_user)
async def form_unban_user(message: Message, state: FSMContext) -> None:
    """Yasak kaldırma işlemi."""
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.clear()
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Geçersiz ID.")
        return
    await db.unban_user(target_id)
    await message.answer(t("tr", "admin_unbanned", tg_id=target_id))
