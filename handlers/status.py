"""
Durum görüntüleme handler'ı
Tüm limitli kullanıcıları ve ihlal geçmişini gösterir
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

import database as db
from marzban_api import MarzbanAPI
from handlers.i18n import t
from handlers.keyboards import main_menu_keyboard

router = Router()


@router.callback_query(F.data == "menu:status")
async def cb_status(callback: CallbackQuery) -> None:
    """Limit durumunu göster."""
    tg_id = callback.from_user.id
    lang = await db.get_user_lang(tg_id)

    if await db.is_banned(tg_id):
        await callback.answer(t(lang, "banned"), show_alert=True)
        return

    limits = await db.get_limits_by_owner(tg_id)
    if not limits:
        await callback.message.answer(
            t(lang, "status_header") + "\n\n" + t(lang, "status_empty"),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(lang),
        )
        await callback.answer()
        return

    lines = [t(lang, "status_header")]
    panels_cache: dict[int, dict] = {}

    for row in limits:
        panel_id = row["panel_id"]
        marzban_user = row["marzban_user"]
        device_limit = row["device_limit"]
        last_checked = row.get("last_checked") or "—"
        last_violation = row.get("last_violation") or "—"

        # Aktif IP sayısını API'den çek
        active = "?"
        try:
            panel = panels_cache.get(panel_id)
            if panel is None:
                panel = await db.get_panel(panel_id)
                panels_cache[panel_id] = panel
            if panel:
                api = MarzbanAPI(panel["url"], panel["username"], panel["password"])
                active = await api.get_online_ip_count(marzban_user)
        except Exception:
            active = "?"

        lines.append(
            "\n" + t(lang, "status_row",
                     username=marzban_user,
                     limit=device_limit,
                     active=active,
                     last_checked=last_checked,
                     last_violation=last_violation)
        )

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(lang),
    )
    await callback.answer()
