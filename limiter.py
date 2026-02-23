"""
Limit kontrol motoru - asyncio.gather ile paralel IP/cihaz kontrolü
Her 30 saniyede bir tüm kullanıcılar eş zamanlı kontrol edilir
"""
import asyncio
import logging
from datetime import datetime, timezone

import database as db
from marzban_api import MarzbanAPI

logger = logging.getLogger(__name__)

# Bot nesnesi; bot.py tarafından set edilir
_bot = None


def set_bot(bot) -> None:
    """Bot nesnesini kaydet (bildirim göndermek için)."""
    global _bot
    _bot = bot


async def _check_single_limit(limit_row: dict) -> None:
    """
    Tek bir limitli kullanıcıyı kontrol et.
    IP sayısı > limit ise: deaktif et → 5 sn bekle → aktif et
    """
    panel_id = limit_row["panel_id"]
    marzban_user = limit_row["marzban_user"]
    device_limit = limit_row["device_limit"]
    panel_url = limit_row["url"]
    panel_username = limit_row["panel_username"]
    panel_password = limit_row["password"]
    tg_owner = limit_row["tg_id"]

    api = MarzbanAPI(panel_url, panel_username, panel_password)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        active_ips = await api.get_online_ip_count(marzban_user)
    except Exception as exc:
        logger.warning("Kullanıcı %s kontrol edilemedi: %s", marzban_user, exc)
        return

    # Kontrol zamanını güncelle
    await db.update_limit_check_time(limit_row["id"], now_str)

    if active_ips > device_limit:
        logger.info(
            "⚠️ %s limiti aştı: aktif=%d limit=%d", marzban_user, active_ips, device_limit
        )

        # İhlal kaydı ekle
        await db.add_violation(panel_id, marzban_user, active_ips, device_limit)
        await db.update_limit_violation_time(limit_row["id"], now_str)

        # Kullanıcıyı deaktif et
        try:
            await api.disable_user(marzban_user)
        except Exception as exc:
            logger.error("Kullanıcı %s deaktif edilemedi: %s", marzban_user, exc)
            return

        # 5 saniye bekle (fazla cihazların bağlantısı kesilsin)
        await asyncio.sleep(5)

        # Kullanıcıyı tekrar aktif et
        try:
            await api.enable_user(marzban_user)
        except Exception as exc:
            logger.error("Kullanıcı %s aktif edilemedi: %s", marzban_user, exc)
            return

        # Bot sahibine ve admin'e bildirim gönder
        if _bot is not None:
            from config import ADMIN_ID

            msg = (
                f"⚠️ <b>Limit Aşımı!</b>\n"
                f"👤 Kullanıcı: <code>{marzban_user}</code>\n"
                f"📊 Aktif cihaz: {active_ips} / Limit: {device_limit}\n"
                f"🔗 Panel: {panel_url}\n"
                f"🕐 Zaman: {now_str} UTC"
            )
            # Panel sahibine bildirim
            try:
                await _bot.send_message(tg_owner, msg, parse_mode="HTML")
            except Exception:
                pass
            # Admin'e bildirim (aynı kişi değilse)
            if ADMIN_ID and tg_owner != ADMIN_ID:
                try:
                    await _bot.send_message(ADMIN_ID, msg, parse_mode="HTML")
                except Exception:
                    pass


async def run_check_cycle() -> None:
    """
    Tüm limitli kullanıcıları asyncio.gather ile paralel kontrol et.
    100+ kullanıcı aynı anda işlenebilir.
    """
    all_limits = await db.get_all_limits()
    if not all_limits:
        return

    logger.info("Limit kontrol döngüsü başladı: %d kullanıcı", len(all_limits))

    # Tüm kullanıcıları aynı anda kontrol et
    await asyncio.gather(
        *[_check_single_limit(row) for row in all_limits],
        return_exceptions=True,
    )

    logger.info("Limit kontrol döngüsü tamamlandı.")
