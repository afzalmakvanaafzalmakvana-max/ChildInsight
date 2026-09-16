"""Lightweight internationalization (i18n) package for ChildInsight."""

from .en import TRANSLATIONS as EN_TRANSLATIONS
from .hi import TRANSLATIONS as HI_TRANSLATIONS

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi'
}

COMING_SOON_LANGUAGES = {
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh': 'Mandarin'
}


def normalize_language(val: str | None) -> str:
    """
    Normalizes language name (e.g. 'Hindi', 'English', 'Spanish') or code ('hi', 'en', 'es')
    to a supported 2-letter language code ('hi' or 'en').
    Unsupported or Coming Soon languages cleanly fall back to 'en'.
    """
    if not val:
        return 'en'
    cleaned = str(val).strip().lower()
    if cleaned in ('hi', 'hindi', 'hin'):
        return 'hi'
    return 'en'


def get_translations(lang: str) -> dict:
    """Return translation dictionary for a given language code."""
    if lang == 'hi':
        return HI_TRANSLATIONS
    return EN_TRANSLATIONS


def translate(key: str, lang: str = 'en', default: str | None = None, **kwargs) -> str:
    """Translate a key into target language with fallback to English."""
    normalized_lang = normalize_language(lang)
    trans = get_translations(normalized_lang)
    text = trans.get(key, EN_TRANSLATIONS.get(key, default or key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
