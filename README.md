# 🛡️ Marzban Device Limiter Bot

---

## 🇹🇷 Türkçe Kurulum Rehberi

Marzban v0.8.4 paneli ile entegre çalışan, kullanıcıların subscription linklerini paylaşmasını engellemek için device/IP limit koyan bir Telegram botu.

### Özellikler
- 🌍 Çok dil desteği (TR, RU, EN)
- 👥 Çok kullanıcı: Herkes kendi panelini bağlayabilir
- ⚡ Async: 100+ kullanıcı aynı anda
- 🔒 Her abonelik için cihaz/IP limiti
- 📊 Gerçek zamanlı izleme

### Gereksinimler
- Python 3.10+
- VPS veya sunucu

### Kurulum Adımları

```bash
# 1. Repoyu klonla
git clone https://github.com/muratowmukam00/marzban.git
cd marzban

# 2. Sanal ortam oluştur
python3 -m venv venv
source venv/bin/activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. .env dosyasını oluştur
cp .env.example .env
nano .env
```

### .env Dosyası Ayarları
```
BOT_TOKEN=your_telegram_bot_token     # @BotFather'dan alınan token
ADMIN_ID=123456789                     # Kendi Telegram kullanıcı ID'niz
CHECK_INTERVAL=30                      # Kontrol aralığı (saniye)
ENCRYPTION_KEY=your_fernet_key         # Fernet şifreleme anahtarı
DB_PATH=limiter.db                     # Veritabanı dosya yolu
```

Fernet anahtarı oluşturmak için:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Botu Başlatma
```bash
python bot.py
```

### systemd Service (Arka Planda Çalıştırma)
```ini
[Unit]
Description=Marzban Device Limiter Bot
After=network.target

[Service]
User=root
WorkingDirectory=/opt/marzban-bot
ExecStart=/opt/marzban-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp marzban-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable marzban-bot
sudo systemctl start marzban-bot
```

### Bot Komutları
- `/start` - Botu başlat, dil seç
- `/admin` - Admin paneli (sadece ADMIN_ID)

### Kullanım
1. `/start` ile botu başlat ve dil seç
2. **🔗 Panel Bağla** ile Marzban panelinizi ekleyin
3. **📋 Kullanıcılarım** ile kullanıcı seçip limit koyun
4. **📊 Durum** ile limitleri izleyin

---

## 🇷🇺 Руководство по установке (Русский)

Telegram-бот для управления лимитами устройств/IP в панели Marzban v0.8.4.

### Особенности
- 🌍 Многоязычность (TR, RU, EN)
- 👥 Мультипользовательский: каждый может подключить свою панель
- ⚡ Асинхронный: 100+ пользователей одновременно
- 🔒 Лимит устройств/IP на каждую подписку
- 📊 Мониторинг в реальном времени

### Требования
- Python 3.10+
- VPS или сервер

### Шаги установки

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/muratowmukam00/marzban.git
cd marzban

# 2. Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Создайте .env файл
cp .env.example .env
nano .env
```

### Настройка .env файла
```
BOT_TOKEN=your_telegram_bot_token     # Токен от @BotFather
ADMIN_ID=123456789                     # Ваш Telegram ID
CHECK_INTERVAL=30                      # Интервал проверки (секунды)
ENCRYPTION_KEY=your_fernet_key         # Ключ шифрования Fernet
DB_PATH=limiter.db                     # Путь к базе данных
```

Генерация ключа Fernet:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Запуск бота
```bash
python bot.py
```

### Команды бота
- `/start` - Запустить бота, выбрать язык
- `/admin` - Панель администратора (только ADMIN_ID)

---

## 🇬🇧 English Setup Guide

A Telegram bot integrated with Marzban v0.8.4 panel to prevent users from sharing subscription links by enforcing device/IP limits.

### Features
- 🌍 Multi-language support (TR, RU, EN)
- 👥 Multi-user: Everyone can connect their own panel
- ⚡ Async: 100+ users simultaneously with `asyncio.gather`
- 🔒 Device/IP limit per subscription
- 📊 Real-time monitoring dashboard

### Requirements
- Python 3.10+
- VPS or server

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/muratowmukam00/marzban.git
cd marzban

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file
cp .env.example .env
nano .env
```

### .env Configuration
```
BOT_TOKEN=your_telegram_bot_token     # Token from @BotFather
ADMIN_ID=123456789                     # Your Telegram user ID
CHECK_INTERVAL=30                      # Check interval in seconds
ENCRYPTION_KEY=your_fernet_key         # Fernet encryption key
DB_PATH=limiter.db                     # Database file path
```

Generate a Fernet key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Running the Bot
```bash
python bot.py
```

### systemd Service (Run in Background)
```ini
[Unit]
Description=Marzban Device Limiter Bot
After=network.target

[Service]
User=root
WorkingDirectory=/opt/marzban-bot
ExecStart=/opt/marzban-bot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp marzban-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable marzban-bot
sudo systemctl start marzban-bot
```

### Bot Commands
- `/start` - Start the bot and choose language
- `/admin` - Admin panel (ADMIN_ID only)

### Usage
1. Send `/start` and choose your language
2. Use **🔗 Connect Panel** to add your Marzban panel
3. Use **📋 My Users** to select a user and set a device limit
4. Use **📊 Status** to monitor all limits in real time

### Project Structure
```
├── bot.py                  # Main bot file (Aiogram 3.x)
├── config.py               # Settings (.env reader)
├── database.py             # SQLite database (aiosqlite)
├── marzban_api.py          # Marzban API client (async httpx)
├── limiter.py              # IP/Device limit engine (asyncio.gather)
├── handlers/
│   ├── __init__.py
│   ├── i18n.py             # Translation helper
│   ├── keyboards.py        # Shared keyboard builders
│   ├── start.py            # /start + language selection
│   ├── panel.py            # Panel connection flow
│   ├── users.py            # User listing + limit setting
│   ├── status.py           # Status display
│   └── admin.py            # Admin commands
├── locales/
│   ├── tr.json             # Turkish translations
│   ├── ru.json             # Russian translations
│   └── en.json             # English translations
├── .env.example            # Example .env file
├── requirements.txt        # Dependencies
└── README.md               # This file
```
