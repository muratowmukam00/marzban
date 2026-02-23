"""
Veritabanı modülü - aiosqlite ile asenkron SQLite işlemleri
Panel bilgileri Fernet ile şifrelenmiş olarak saklanır
"""
import json
import aiosqlite
from cryptography.fernet import Fernet
from config import DB_PATH, ENCRYPTION_KEY

# Fernet şifreleme nesnesi
_fernet: Fernet | None = None


def get_fernet() -> Fernet:
    """Fernet örneğini döndür (lazy init)."""
    global _fernet
    if _fernet is None:
        if not ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY is not set! Please check your .env file.")
        _fernet = Fernet(ENCRYPTION_KEY.encode())
    return _fernet


def encrypt(text: str) -> str:
    """Metni Fernet ile şifrele."""
    return get_fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    """Fernet ile şifrelenmiş metni çöz."""
    return get_fernet().decrypt(token.encode()).decode()


async def init_db() -> None:
    """Veritabanı tablolarını oluştur."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Kullanıcılar tablosu (Telegram kullanıcıları)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tg_users (
                tg_id       INTEGER PRIMARY KEY,
                lang        TEXT    NOT NULL DEFAULT 'en',
                is_banned   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Paneller tablosu
        await db.execute("""
            CREATE TABLE IF NOT EXISTS panels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER NOT NULL,
                url         TEXT    NOT NULL,
                username    TEXT    NOT NULL,
                password    TEXT    NOT NULL,   -- Fernet ile şifrelenmiş
                label       TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (tg_id) REFERENCES tg_users(tg_id)
            )
        """)

        # Limitli kullanıcılar tablosu
        await db.execute("""
            CREATE TABLE IF NOT EXISTS limits (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                panel_id        INTEGER NOT NULL,
                marzban_user    TEXT    NOT NULL,
                device_limit    INTEGER NOT NULL DEFAULT 1,
                last_checked    TEXT,
                last_violation  TEXT,
                UNIQUE(panel_id, marzban_user),
                FOREIGN KEY (panel_id) REFERENCES panels(id)
            )
        """)

        # Limit aşım geçmişi tablosu
        await db.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                panel_id        INTEGER NOT NULL,
                marzban_user    TEXT    NOT NULL,
                active_ips      INTEGER NOT NULL,
                device_limit    INTEGER NOT NULL,
                violated_at     TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        await db.commit()


# ---------------------------------------------------------------------------
# Telegram kullanıcı işlemleri
# ---------------------------------------------------------------------------

async def get_or_create_user(tg_id: int, lang: str = "en") -> dict:
    """Kullanıcıyı getir veya oluştur."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tg_users WHERE tg_id = ?", (tg_id,)) as cur:
            row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO tg_users (tg_id, lang) VALUES (?, ?)",
                (tg_id, lang),
            )
            await db.commit()
            async with db.execute("SELECT * FROM tg_users WHERE tg_id = ?", (tg_id,)) as cur:
                row = await cur.fetchone()
        return dict(row)


async def set_user_lang(tg_id: int, lang: str) -> None:
    """Kullanıcının dilini güncelle."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tg_users SET lang = ? WHERE tg_id = ?", (lang, tg_id))
        await db.commit()


async def get_user_lang(tg_id: int) -> str:
    """Kullanıcının dilini getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT lang FROM tg_users WHERE tg_id = ?", (tg_id,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else "en"


async def ban_user(tg_id: int) -> None:
    """Kullanıcıyı yasakla."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tg_users SET is_banned = 1 WHERE tg_id = ?", (tg_id,))
        await db.commit()


async def unban_user(tg_id: int) -> None:
    """Kullanıcı yasağını kaldır."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tg_users SET is_banned = 0 WHERE tg_id = ?", (tg_id,))
        await db.commit()


async def is_banned(tg_id: int) -> bool:
    """Kullanıcının yasaklı olup olmadığını kontrol et."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_banned FROM tg_users WHERE tg_id = ?", (tg_id,)) as cur:
            row = await cur.fetchone()
    return bool(row[0]) if row else False


async def get_all_users() -> list[dict]:
    """Tüm Telegram kullanıcılarını getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tg_users ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Panel işlemleri
# ---------------------------------------------------------------------------

async def add_panel(tg_id: int, url: str, username: str, password: str, label: str = "") -> int:
    """Yeni panel ekle (şifrelenmiş)."""
    enc_password = encrypt(password)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO panels (tg_id, url, username, password, label) VALUES (?, ?, ?, ?, ?)",
            (tg_id, url, username, enc_password, label),
        )
        await db.commit()
        return cur.lastrowid


async def get_panels(tg_id: int) -> list[dict]:
    """Kullanıcının panellerini getir (şifresi çözülmüş)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM panels WHERE tg_id = ?", (tg_id,)) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["password"] = decrypt(d["password"])
        result.append(d)
    return result


async def get_panel(panel_id: int) -> dict | None:
    """Belirli bir paneli getir (şifresi çözülmüş)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM panels WHERE id = ?", (panel_id,)) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["password"] = decrypt(d["password"])
    return d


async def get_all_panels() -> list[dict]:
    """Tüm panelleri getir (admin için, şifresi çözülmüş)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM panels ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["password"] = decrypt(d["password"])
        result.append(d)
    return result


async def delete_panel(panel_id: int, tg_id: int) -> bool:
    """Kullanıcının panelini sil."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM panels WHERE id = ? AND tg_id = ?", (panel_id, tg_id)
        )
        await db.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Limit işlemleri
# ---------------------------------------------------------------------------

async def set_limit(panel_id: int, marzban_user: str, device_limit: int) -> None:
    """Kullanıcı limiti ekle veya güncelle."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO limits (panel_id, marzban_user, device_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(panel_id, marzban_user) DO UPDATE SET device_limit = excluded.device_limit
            """,
            (panel_id, marzban_user, device_limit),
        )
        await db.commit()


async def remove_limit(panel_id: int, marzban_user: str) -> None:
    """Kullanıcı limitini kaldır."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM limits WHERE panel_id = ? AND marzban_user = ?",
            (panel_id, marzban_user),
        )
        await db.commit()


async def get_limits_for_panel(panel_id: int) -> list[dict]:
    """Belirli bir panelin tüm limitli kullanıcılarını getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM limits WHERE panel_id = ?", (panel_id,)
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_all_limits() -> list[dict]:
    """Tüm limitli kullanıcıları panelleriyle birlikte getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT l.*, p.url, p.username AS panel_username, p.password, p.tg_id
            FROM limits l
            JOIN panels p ON l.panel_id = p.id
        """) as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["password"] = decrypt(d["password"])
        result.append(d)
    return result


async def get_limits_by_owner(tg_id: int) -> list[dict]:
    """Belirli bir Telegram kullanıcısının tüm limitlerini getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT l.*, p.url, p.username AS panel_username, p.label
            FROM limits l
            JOIN panels p ON l.panel_id = p.id
            WHERE p.tg_id = ?
        """, (tg_id,)) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_limit_check_time(limit_id: int, last_checked: str) -> None:
    """Limit kontrol zamanını güncelle."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE limits SET last_checked = ? WHERE id = ?",
            (last_checked, limit_id),
        )
        await db.commit()


async def update_limit_violation_time(limit_id: int, last_violation: str) -> None:
    """Son ihlal zamanını güncelle."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE limits SET last_violation = ? WHERE id = ?",
            (last_violation, limit_id),
        )
        await db.commit()


async def add_violation(
    panel_id: int, marzban_user: str, active_ips: int, device_limit: int
) -> None:
    """İhlal kaydı ekle."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO violations (panel_id, marzban_user, active_ips, device_limit)
            VALUES (?, ?, ?, ?)
            """,
            (panel_id, marzban_user, active_ips, device_limit),
        )
        await db.commit()


async def get_violations(panel_id: int | None = None, limit: int = 20) -> list[dict]:
    """İhlal geçmişini getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if panel_id is not None:
            async with db.execute(
                "SELECT * FROM violations WHERE panel_id = ? ORDER BY violated_at DESC LIMIT ?",
                (panel_id, limit),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM violations ORDER BY violated_at DESC LIMIT ?",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_stats() -> dict:
    """Genel istatistikleri getir."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM tg_users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM panels") as cur:
            total_panels = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM limits") as cur:
            total_limits = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM violations") as cur:
            total_violations = (await cur.fetchone())[0]
    return {
        "total_users": total_users,
        "total_panels": total_panels,
        "total_limits": total_limits,
        "total_violations": total_violations,
    }
