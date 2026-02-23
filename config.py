"""
Ayarlar modülü - .env dosyasından yapılandırma okuma
"""
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Telegram bot token'ı
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Admin Telegram kullanıcı ID'si
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# Periyodik kontrol aralığı (saniye)
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "30"))

# Fernet şifreleme anahtarı (panel parolaları için)
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# Veritabanı dosya yolu
DB_PATH: str = os.getenv("DB_PATH", "limiter.db")
