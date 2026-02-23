"""
Ortak yardımcı fonksiyonlar - dil yükleme ve çeviri
"""
import json
import os
from functools import lru_cache

LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")

SUPPORTED_LANGS = ("tr", "en", "ru")


@lru_cache(maxsize=8)
def load_locale(lang: str) -> dict:
    """Belirtilen dil için JSON çeviri dosyasını yükle."""
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def t(lang: str, key: str, **kwargs) -> str:
    """Çeviriyi döndür; kwargs ile format uygula."""
    locale = load_locale(lang)
    text = locale.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text
