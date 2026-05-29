from __future__ import annotations

import re
from typing import Any

from app.services.text_utils import normalize_text


def normalize_language_code(language: Any) -> str:
    value = str(language or "en").strip().lower().replace("_", "-")
    if value.startswith(("cs", "cz")) or value in {"czech", "cesky"}:
        return "cs"
    if value.startswith("de") or value in {"german", "deutsch"}:
        return "de"
    if value.startswith("en") or value in {"english"}:
        return "en"
    return value.split("-", 1)[0] or "en"


def is_czech(language: Any) -> bool:
    return normalize_language_code(language) == "cs"


def is_german(language: Any) -> bool:
    return normalize_language_code(language) == "de"


def target_language_name(language: Any) -> str:
    return {
        "cs": "Czech",
        "de": "German",
        "en": "English",
        "fr": "French",
        "es": "Spanish",
        "it": "Italian",
        "nl": "Dutch",
        "pl": "Polish",
    }.get(normalize_language_code(language), str(language or "English"))


_PHRASE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "visible product shape": {
        "cs": "viditelny tvar produktu",
        "de": "sichtbare Produktform",
    },
    "product details shown clearly": {
        "cs": "jasne viditelne detaily produktu",
        "de": "klare Produktdetails",
    },
    "everyday context without extra claims": {
        "cs": "bezny kontext bez slibu navic",
        "de": "Alltagskontext ohne Zusatzversprechen",
    },
    "visible size and placement": {
        "cs": "viditelna velikost a umisteni",
        "de": "sichtbare Groesse und Platzierung",
    },
    "room context without performance claims": {
        "cs": "kontext mistnosti bez vykonnostnich slibu",
        "de": "Raumkontext ohne Leistungsversprechen",
    },
    "material details only if visible": {
        "cs": "materialove detaily jen kdyz jsou videt",
        "de": "Materialdetails nur wenn sichtbar",
    },
    "visible product details": {
        "cs": "viditelne detaily produktu",
        "de": "sichtbare Produktdetails",
    },
    "visible detail": {
        "cs": "viditelny detail",
        "de": "sichtbares Detail",
    },
    "visible finish": {
        "cs": "viditelne provedeni",
        "de": "sichtbare Verarbeitung",
    },
    "shape and finish": {
        "cs": "tvar a provedeni",
        "de": "Form und Verarbeitung",
    },
    "overall product detail": {
        "cs": "celkovy detail produktu",
        "de": "gesamter Produktdetail",
    },
    "clear practical": {
        "cs": "jasne prakticke",
        "de": "klar und praktisch",
    },
    "everyday product context": {
        "cs": "bezny kontext produktu",
        "de": "Alltagskontext des Produkts",
    },
    "home routine": {
        "cs": "domaci rutina",
        "de": "Alltag zu Hause",
    },
    "custom name inscription": {
        "cs": "vlastni napis se jmenem",
        "de": "personalisierter Namensaufdruck",
    },
    "personalized name inscription": {
        "cs": "personalizovany napis se jmenem",
        "de": "personalisierter Namensaufdruck",
    },
    "plastic material": {
        "cs": "plastovy material",
        "de": "Kunststoffmaterial",
    },
    "clear product body": {
        "cs": "cire telo produktu",
        "de": "klarer Produktkoerper",
    },
    "shatter resistant plastic": {
        "cs": "odolny plast",
        "de": "bruchfester Kunststoff",
    },
    "460 ml capacity": {
        "cs": "objem 460 ml",
        "de": "460 ml Fassungsvermoegen",
    },
    "minimalist design": {
        "cs": "minimalisticky design",
        "de": "minimalistisches Design",
    },
    "clean minimalist shape": {
        "cs": "cisty minimalisticky tvar",
        "de": "klare minimalistische Form",
    },
    "structured shape": {
        "cs": "pevnejsi tvar",
        "de": "strukturierte Form",
    },
    "work errands and travel context": {
        "cs": "kontext prace, pochuzek a cestovani",
        "de": "Kontext fuer Arbeit, Erledigungen und Reisen",
    },
    "leather texture": {
        "cs": "textura kuze",
        "de": "Lederstruktur",
    },
    "material texture": {
        "cs": "struktura materialu",
        "de": "Materialstruktur",
    },
    "stitching": {
        "cs": "siti",
        "de": "Naehte",
    },
    "handles": {
        "cs": "ucha",
        "de": "Griffe",
    },
    "interior lining": {
        "cs": "vnitrni podsitka",
        "de": "Innenfutter",
    },
}


_CATEGORY_TRANSLATIONS: dict[str, dict[str, str]] = {
    "handbag": {"cs": "kabelka", "de": "Tasche", "en": "bag"},
    "shoes": {"cs": "boty", "de": "Schuhe", "en": "shoes"},
    "apparel": {"cs": "obleceni", "de": "Kleidung", "en": "garment"},
    "beauty": {"cs": "beauty produkt", "de": "Beauty-Produkt", "en": "beauty product"},
    "home": {"cs": "produkt do domacnosti", "de": "Produkt fuer zu Hause", "en": "home item"},
    "electronics": {"cs": "elektronika", "de": "Elektronikprodukt", "en": "electronics item"},
    "product": {"cs": "produkt", "de": "Produkt", "en": "product"},
    "unknown": {"cs": "produkt", "de": "Produkt", "en": "product"},
}


def localize_category(category: Any, language: Any) -> str:
    code = normalize_language_code(language)
    key = str(category or "product").strip().lower()
    return (_CATEGORY_TRANSLATIONS.get(key) or _CATEGORY_TRANSLATIONS["product"]).get(code) or key


def localize_phrase(value: Any, language: Any) -> str:
    text = normalize_text(str(value or ""))
    if not text:
        return ""
    code = normalize_language_code(language)
    if code == "en":
        return text
    key = _phrase_key(text)
    direct = _PHRASE_TRANSLATIONS.get(key, {}).get(code)
    if direct:
        return direct
    ml_match = re.search(r"\b(\d{2,4})\s*ml\b", text, flags=re.IGNORECASE)
    if ml_match:
        amount = ml_match.group(1)
        if code == "de":
            return f"{amount} ml Fassungsvermoegen"
        if code == "cs":
            return f"objem {amount} ml"
    if code == "de" and _looks_english(text):
        return _word_replace(text, _GERMAN_WORD_REPLACEMENTS)
    if code == "cs" and _looks_english(text):
        return _word_replace(text, _CZECH_WORD_REPLACEMENTS)
    return text


def localize_phrases(values: list[Any] | tuple[Any, ...] | None, language: Any) -> list[str]:
    result: list[str] = []
    seen = set()
    for value in values or []:
        localized = localize_phrase(value, language)
        key = localized.lower()
        if localized and key not in seen:
            seen.add(key)
            result.append(localized)
    return result


def language_copy_policy(language: Any) -> str:
    name = target_language_name(language)
    return (
        f"All customer-facing copy, spoken lines, captions, subtitles, ad text, overlay text, "
        f"and product-note-derived details must be written in {name}. "
        "Product notes are internal source material: translate and rewrite them naturally, never paste raw notes verbatim."
    )


def voice_descriptor_conflicts_language(value: Any, language: Any) -> bool:
    text = normalize_text(str(value or "")).lower()
    if not text:
        return False
    code = normalize_language_code(language)
    language_markers = {
        "cs": [
            "english",
            "british",
            "american",
            "german",
            "deutsch",
            "polish",
            "slovak",
            "slovakian",
        ],
        "de": ["english", "british", "american", "czech", "cesky", "polish", "slovak", "slovakian"],
        "en": ["czech", "cesky", "german", "deutsch", "polish", "slovak", "slovakian"],
    }
    return any(marker in text for marker in language_markers.get(code, []))


def language_safe_voice_descriptor(value: Any, language: Any) -> str:
    descriptor = normalize_text(str(value or "")).strip()
    if not descriptor:
        return ""
    if not voice_descriptor_conflicts_language(descriptor, language):
        return descriptor
    lowered = descriptor.lower()
    preserved = []
    for marker, replacement in [
        ("warm", "warm"),
        ("calm", "calm"),
        ("relaxed", "relaxed"),
        ("conversational", "conversational"),
        ("direct", "direct"),
        ("clear", "clear"),
        ("natural", "natural"),
        ("medium", "medium energy"),
        ("low", "low energy"),
    ]:
        if marker in lowered and replacement not in preserved:
            preserved.append(replacement)
    return ", ".join(preserved)


def _phrase_key(text: str) -> str:
    cleaned = text.lower()
    cleaned = cleaned.replace("-", " ")
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _looks_english(text: str) -> bool:
    lowered = f" {text.lower()} "
    return any(
        token in lowered
        for token in [
            " visible ",
            " product ",
            " detail ",
            " details ",
            " shape ",
            " finish ",
            " context ",
            " material ",
            " everyday ",
            " clear ",
            " close ",
        ]
    )


def _word_replace(text: str, replacements: dict[str, str]) -> str:
    result = text
    for source, target in replacements.items():
        result = re.sub(rf"\b{re.escape(source)}\b", target, result, flags=re.IGNORECASE)
    return normalize_text(result)


_GERMAN_WORD_REPLACEMENTS = {
    "visible": "sichtbare",
    "product": "Produkt",
    "details": "Details",
    "detail": "Detail",
    "shape": "Form",
    "finish": "Verarbeitung",
    "context": "Kontext",
    "material": "Material",
    "everyday": "Alltag",
    "clear": "klar",
    "close": "nah",
    "up": "",
    "shown": "gezeigt",
    "clearly": "klar",
}


_CZECH_WORD_REPLACEMENTS = {
    "visible": "viditelny",
    "product": "produkt",
    "details": "detaily",
    "detail": "detail",
    "shape": "tvar",
    "finish": "provedeni",
    "context": "kontext",
    "material": "material",
    "everyday": "bezny",
    "clear": "jasny",
    "close": "zblizka",
    "shown": "ukazany",
    "clearly": "jasne",
}
