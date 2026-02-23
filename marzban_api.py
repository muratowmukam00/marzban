"""
Marzban API istemcisi - async httpx ile v0.8.4 API çağrıları
"""
import logging
import httpx
from typing import Any

logger = logging.getLogger(__name__)


class MarzbanAPI:
    """Marzban panel API'si için asenkron istemci."""

    def __init__(self, base_url: str, username: str, password: str):
        # Sondaki slash'ı kaldır
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: str | None = None

    async def _get_token(self) -> str:
        """Admin token'ı al veya mevcut olanı döndür."""
        if self._token:
            return self._token
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/admin/token",
                data={"username": self.username, "password": self.password},
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
        return self._token

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    async def _request(
        self, method: str, path: str, *, refresh: bool = False, **kwargs
    ) -> Any:
        """Token'lı API isteği gönder; 401'de token'ı yenile."""
        if refresh:
            self._token = None
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(token),
                **kwargs,
            )
            if resp.status_code == 401 and not refresh:
                # Token süresi dolmuş olabilir; yenile ve tekrar dene
                return await self._request(method, path, refresh=True, **kwargs)
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> bool:
        """Bağlantıyı test et; başarılıysa True döndür."""
        try:
            await self._get_token()
            return True
        except Exception:
            return False

    async def get_users(self, page: int = 1, size: int = 100) -> dict:
        """Tüm Marzban kullanıcılarını listele."""
        return await self._request(
            "GET", "/api/users", params={"page": page, "size": size}
        )

    async def get_user(self, username: str) -> dict:
        """Kullanıcı detayını getir (online IP'ler dahil)."""
        return await self._request("GET", f"/api/user/{username}")

    async def disable_user(self, username: str) -> dict:
        """Kullanıcıyı deaktif et."""
        return await self._request(
            "PUT",
            f"/api/user/{username}",
            json={"status": "disabled"},
        )

    async def enable_user(self, username: str) -> dict:
        """Kullanıcıyı aktif et."""
        return await self._request(
            "PUT",
            f"/api/user/{username}",
            json={"status": "active"},
        )

    async def get_online_ip_count(self, username: str) -> int:
        """Kullanıcının şu an aktif IP/cihaz sayısını döndür."""
        user = await self.get_user(username)
        # Marzban v0.8.4'te online_at alanı aktif IP listesi içerir
        online_ips = user.get("online_at")
        if isinstance(online_ips, list):
            return len(online_ips)
        # Alternatif alan adı
        online_val = user.get("online")
        if online_val is not None:
            try:
                return int(online_val)
            except (TypeError, ValueError):
                logger.warning(
                    "Kullanıcı %s için 'online' alanı dönüştürülemedi: %r",
                    username, online_val,
                )
        logger.debug(
            "Kullanıcı %s için aktif IP alanı bulunamadı; 0 döndürülüyor. "
            "Mevcut anahtarlar: %s",
            username, list(user.keys()),
        )
        return 0
