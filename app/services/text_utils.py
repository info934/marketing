from __future__ import annotations

import re
from typing import Iterable


RISKY_CLAIM_PATTERNS = {
    "medical": [
        r"\bcure[sd]?\b",
        r"\btreats?\b",
        r"\bheals?\b",
        r"\borthop(a|ae)dic\b",
        r"\bmedical\b",
        r"\bpain[- ]?free\b",
        r"\bdoctor[- ]?recommended\b",
    ],
    "scarcity": [
        r"\bonly \d+ left\b",
        r"\bselling out\b",
        r"\blast chance\b",
        r"\blimited stock\b",
    ],
    "discount": [
        r"\b\d+% off\b",
        r"\bwas \$?\d+\b",
        r"\bflash sale\b",
        r"\bfree today\b",
    ],
    "testimonial": [
        r"\bi (love|used|tried|tested|wear|wore)\b",
        r"\bmy results\b",
        r"\bbefore and after\b",
        r"\bcustomer[s]? say\b",
        r"\b5[- ]?star\b",
    ],
    "trademark": [
        r"\bdesigner dupe\b",
        r"\breplica\b",
        r"\bknockoff\b",
        r"\blike (nike|adidas|gucci|prada|chanel|louis vuitton|lv|hermes|dior)\b",
    ],
}

CATEGORY_KEYWORDS = {
    "shoes": ["shoe", "shoes", "sneaker", "boot", "loafer", "heel", "sandals"],
    "handbag": ["bag", "handbag", "purse", "tote", "crossbody", "wallet"],
    "beauty": ["serum", "cream", "makeup", "lipstick", "skincare", "mascara"],
    "home": ["lamp", "chair", "sofa", "kitchen", "organizer", "blanket", "glass", "cup", "mug", "sklenice", "tasse", "becher"],
    "electronics": ["charger", "phone", "camera", "speaker", "earbuds", "watch"],
    "apparel": ["shirt", "dress", "jacket", "hoodie", "leggings", "coat"],
}


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def sanitize_avatar_descriptor(value: str | None) -> str:
    """Keep avatar styling from looking like product/material claims."""
    text = normalize_text(value)
    if not text:
        return ""
    replacements = [
        (r"\bluxury\b", "polished"),
        (r"\bdesigner\b", "styled"),
        (r"\bleather\b", "textured"),
        (r"\bsuede\b", "soft-textured"),
        (r"\bsilk\b", "smooth-fabric"),
        (
            r"\blike (nike|adidas|gucci|prada|chanel|louis vuitton|lv|hermes|dior)\b",
            "brand-free polished",
        ),
    ]
    cleaned = text
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return normalize_text(cleaned)


def split_notes(notes: str | None) -> list[str]:
    text = normalize_text(notes)
    if not text:
        return []
    parts = re.split(r"[.;\n]+", text)
    return [part.strip(" -") for part in parts if part.strip(" -")]


def find_pattern_matches(text: str, patterns: Iterable[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found.append(match.group(0))
    return found


def detect_category(product_name: str, notes: str) -> str:
    haystack = f"{product_name} {notes}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category
    return "unknown"


def safe_slug(value: str, fallback: str = "product") -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug[:60] or fallback


def unique_preserve_order(items: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
