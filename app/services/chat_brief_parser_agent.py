from __future__ import annotations

import json
import re
from typing import Any

import requests

from app import config
from app.services import json_schema_contracts


VERSION = "chat_brief_parser_v1"

SYSTEM_PROMPT = """
You are the AI Brief Parser for an ecommerce creative generation app.

Turn messy chat messages, URLs, pasted ad notes, and attachment metadata into a structured campaign draft.
Classify inputs into product, competitor strategy, avatar guidance, and creative direction.
Do not write final ads. Do not invent product facts. Preserve the user's language preference when it is explicit.
Parse explicit labels such as Product, Product name, Name, Nazev, Nazev produktu, Product URL, URL produktu,
Image URL, Obrazek, Popis, Description, Brief, Notes, Material, and Benefits.
Use product_reference_url only for a direct public product image URL (jpg/png/webp/avif/gif or equivalent image format URL).
Keep non-image ecommerce product page URLs inside product_info as Product URL context instead of dropping them.
Never use a label word such as "Product", "Produkt", "Name", or "URL" as the product_name.

Return only JSON with:
{
  "campaign_draft": {
    "product_name": "",
    "product_info": "",
    "product_reference_url": "",
    "competitor_strategy_enabled": false,
    "competitor_name": "",
    "competitor_url": "",
    "competitor_chat_brief": "",
    "avatar_reference_url": "",
    "custom_avatar_persona": "",
    "avatar_identity_note": "",
    "ugc_video_extra_prompt": "",
    "platform": "",
    "market": "",
    "language": "",
    "generation_mode": ""
  },
  "attachment_roles": [{"item_id": "", "role": "product|competitor|avatar|direction", "reason": ""}],
  "field_sources": {"product_name": "", "...": "short source note for every campaign_draft field"},
  "warnings": []
}
""".strip()

FIELD_LIMITS = {
    "product_name": 120,
    "product_info": 4000,
    "product_reference_url": 500,
    "competitor_name": 120,
    "competitor_url": 500,
    "competitor_chat_brief": 5000,
    "avatar_reference_url": 500,
    "custom_avatar_persona": 1200,
    "avatar_identity_note": 1200,
    "ugc_video_extra_prompt": 3500,
    "platform": 40,
    "market": 20,
    "language": 20,
    "generation_mode": 20,
}

PRODUCT_NAME_LABELS = {
    "product",
    "produkt",
    "product name",
    "name",
    "nazev",
    "název",
    "nazev produktu",
    "název produktu",
    "jmeno",
    "jméno",
}
PRODUCT_URL_LABELS = {
    "url",
    "link",
    "product url",
    "product link",
    "product page",
    "url produktu",
    "produkt url",
    "link produktu",
    "odkaz",
    "odkaz produktu",
    "odkaz na produkt",
    "produktovy odkaz",
    "produktový odkaz",
}
PRODUCT_IMAGE_LABELS = {
    "image",
    "image url",
    "product image",
    "product image url",
    "reference image",
    "obrazek",
    "obrázek",
    "url obrazku",
    "url obrázku",
    "produktovy obrazek",
    "produktový obrázek",
    "foto",
    "fotka",
}
PRODUCT_DESCRIPTION_LABELS = {
    "description",
    "desc",
    "brief",
    "notes",
    "product info",
    "info",
    "popis",
    "poznamky",
    "poznámky",
    "produktovy brief",
    "produktový brief",
    "material",
    "materiál",
    "benefit",
    "benefits",
    "vyhody",
    "výhody",
    "features",
    "vlastnosti",
}
PRODUCT_LABEL_ALIASES = {
    **{label: "product_name" for label in PRODUCT_NAME_LABELS},
    **{label: "product_url" for label in PRODUCT_URL_LABELS},
    **{label: "product_image_url" for label in PRODUCT_IMAGE_LABELS},
    **{label: "product_info" for label in PRODUCT_DESCRIPTION_LABELS},
}
PRODUCT_LABEL_PATTERN = "|".join(re.escape(label) for label in sorted(PRODUCT_LABEL_ALIASES, key=len, reverse=True))


def parse(
    payload: dict[str, Any],
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    items = _normalize_items(payload.get("chatBriefItems") or payload.get("chat_brief_items") or [])
    current_form = payload.get("current_form") or payload.get("form") or {}
    deterministic = _deterministic_parse(items, current_form)
    prompt_model = model or payload.get("prompt_model") or config.OPENROUTER_PROMPT_MODEL
    if not api_key or not items:
        return {
            **deterministic,
            "status": "deterministic",
            "parser_mode": "deterministic_fallback",
            "model": prompt_model,
            "ai_error": "" if items else "No chat items supplied.",
        }

    try:
        ai_result = _call_openrouter(
            items=items,
            current_form=current_form,
            deterministic=deterministic,
            api_key=api_key,
            model=prompt_model,
            base_url=base_url,
        )
        merged = _merge_with_deterministic(ai_result, deterministic)
        return {
            **merged,
            "status": "ai_refined",
            "parser_mode": "openrouter_chat_brief_parser",
            "model": prompt_model,
            "ai_error": "",
        }
    except Exception as exc:
        return {
            **deterministic,
            "status": "deterministic",
            "parser_mode": "deterministic_fallback_after_ai_error",
            "model": prompt_model,
            "ai_error": str(exc)[:500],
        }


def _deterministic_parse(items: list[dict[str, Any]], current_form: dict[str, Any]) -> dict[str, Any]:
    buckets = {"product": [], "competitor": [], "avatar": [], "direction": []}
    attachment_roles = []
    for item in items:
        role = _role_for_item(item)
        text = str(item.get("text") or "").strip()
        if text:
            buckets[role].append(text)
        if item.get("urls"):
            buckets[role].extend(str(url) for url in item.get("urls") or [] if url)
        if int(item.get("file_count") or 0) > 0:
            attachment_roles.append(
                {
                    "item_id": item.get("id") or "",
                    "role": role,
                    "reason": f"Attachment classified from chat context as {role}.",
                }
            )

    all_text = "\n".join(str(item.get("text") or "") for item in items)
    product_text = _join_blocks(buckets["product"])
    competitor_text = _join_blocks(buckets["competitor"])
    avatar_text = _join_blocks(buckets["avatar"])
    direction_text = _join_blocks(buckets["direction"])
    product_fields = _product_fields(product_text or all_text, current_form)
    competitor_urls = _urls(competitor_text)
    avatar_urls = _urls(avatar_text)
    avatar_image_urls = [url for url in avatar_urls if _looks_like_direct_image_url(url)]
    draft = {
        "product_name": product_fields["product_name"],
        "product_info": product_fields["product_info"],
        "product_reference_url": product_fields["product_reference_url"],
        "competitor_strategy_enabled": bool(competitor_text or any(role.get("role") == "competitor" for role in attachment_roles)),
        "competitor_name": _competitor_name(competitor_text),
        "competitor_url": competitor_urls[0] if competitor_urls else "",
        "competitor_chat_brief": _strip_urls(competitor_text),
        "avatar_reference_url": avatar_image_urls[0] if avatar_image_urls else "",
        "custom_avatar_persona": _strip_urls(avatar_text),
        "avatar_identity_note": _strip_urls(avatar_text),
        "ugc_video_extra_prompt": _strip_urls(direction_text),
        "platform": _detect_platform(all_text),
        "market": _detect_market(all_text),
        "language": _detect_language(all_text),
        "generation_mode": _detect_generation_mode(all_text),
    }
    draft = _sanitize_draft(draft)
    return {
        "version": VERSION,
        "campaign_draft": draft,
        "attachment_roles": attachment_roles,
        "field_sources": {
            key: "chat_brief_parser_deterministic"
            for key, value in draft.items()
            if value not in ("", False, None)
        },
        "warnings": _warnings(draft, items),
        "phase2_contract": "chatBriefItems -> structured campaign draft -> existing form",
    }


def _call_openrouter(
    *,
    items: list[dict[str, Any]],
    current_form: dict[str, Any],
    deterministic: dict[str, Any],
    api_key: str,
    model: str,
    base_url: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Creative OS Chat Brief Parser",
    }
    user = {
        "chatBriefItems": items,
        "current_form": _safe_form(current_form),
        "deterministic_draft": deterministic.get("campaign_draft") or {},
        "rules": [
            "Prefer explicit user instructions over heuristics.",
            "Do not overwrite a non-empty current form field unless chat clearly improves it.",
            "If uncertain, leave a field empty and add a warning.",
            "Use attachment_roles to classify local image files by item_id; do not require file bytes.",
        ],
    }
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": json_schema_contracts.CHAT_BRIEF_PARSER_RESPONSE_FORMAT,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        json=payload,
        timeout=35,
    )
    response.raise_for_status()
    data = response.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    parsed = _json_object(content)
    if not isinstance(parsed, dict):
        raise ValueError("Prompt model did not return a JSON object.")
    return parsed


def _merge_with_deterministic(ai_result: dict[str, Any], deterministic: dict[str, Any]) -> dict[str, Any]:
    ai_draft = _sanitize_draft(ai_result.get("campaign_draft") or {})
    fallback_draft = deterministic.get("campaign_draft") or {}
    draft = {}
    for key in FIELD_LIMITS:
        draft[key] = ai_draft.get(key) if ai_draft.get(key) not in ("", None) else fallback_draft.get(key, "")
    draft["competitor_strategy_enabled"] = bool(
        ai_draft.get("competitor_strategy_enabled")
        or fallback_draft.get("competitor_strategy_enabled")
        or draft.get("competitor_chat_brief")
    )
    draft = _normalize_product_draft_after_ai(draft, fallback_draft)
    attachment_roles = ai_result.get("attachment_roles") or deterministic.get("attachment_roles") or []
    warnings = _unique((ai_result.get("warnings") or []) + (deterministic.get("warnings") or []))
    return {
        "version": VERSION,
        "campaign_draft": _sanitize_draft(draft),
        "attachment_roles": _sanitize_attachment_roles(attachment_roles),
        "field_sources": ai_result.get("field_sources") or deterministic.get("field_sources") or {},
        "warnings": warnings,
        "phase2_contract": "chatBriefItems -> structured campaign draft -> existing form",
    }


def _normalize_product_draft_after_ai(draft: dict[str, Any], fallback_draft: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(draft)
    product_reference = str(normalized.get("product_reference_url") or "").strip()
    fallback_reference = str(fallback_draft.get("product_reference_url") or "").strip()
    if product_reference and not _looks_like_direct_image_url(product_reference):
        normalized["product_info"] = _append_product_url_to_info(normalized.get("product_info"), product_reference)
        product_reference = fallback_reference if _looks_like_direct_image_url(fallback_reference) else ""
    normalized["product_reference_url"] = product_reference
    normalized["product_info"] = _normalize_product_info_urls(normalized.get("product_info"), product_reference)
    return normalized


def _append_product_url_to_info(product_info: Any, url: str) -> str:
    if not url:
        return str(product_info or "")
    return _join_blocks([product_info, f"Product URL: {url}"])


def _normalize_items(items: list[Any]) -> list[dict[str, Any]]:
    normalized = []
    for index, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        text = _clip_multiline(item.get("text"), 5000)
        urls = _unique([*_urls(text), *(item.get("urls") or [])])[:8]
        files = item.get("files") or []
        file_names = item.get("file_names") or []
        normalized.append(
            {
                "id": _clip(item.get("id") or f"item_{index + 1}", 80),
                "text": text,
                "urls": urls,
                "file_count": int(item.get("file_count") or len(files) or len(file_names) or 0),
                "file_names": [_clip(name, 160) for name in file_names[:8]],
                "applied_as": [str(value) for value in (item.get("applied_as") or []) if value],
            }
        )
    return normalized[:30]


def _role_for_item(item: dict[str, Any]) -> str:
    applied = {str(value).lower() for value in item.get("applied_as") or []}
    for role in ["product", "competitor", "avatar", "direction"]:
        if role in applied:
            return role
    text = " ".join([str(item.get("text") or ""), " ".join(item.get("file_names") or [])]).lower()
    if any(word in text for word in ["competitor", "konkur", "rival", "ad library", "reklam", "facebook ad", "meta ad"]):
        return "competitor"
    if any(word in text for word in ["avatar", "creator", "persona", "hlas", "voice", "identity"]):
        return "avatar"
    if any(word in text for word in ["režie", "rezie", "direction", "style", "shot", "scene", "ugc video", "kamera"]):
        return "direction"
    return "product"


def _sanitize_draft(draft: dict[str, Any]) -> dict[str, Any]:
    sanitized = {}
    for key, limit in FIELD_LIMITS.items():
        if key == "competitor_strategy_enabled":
            continue
        value = str(draft.get(key) or "").strip()
        sanitized[key] = _clip(value, limit)
    sanitized["platform"] = _normalize_platform(sanitized.get("platform"))
    sanitized["market"] = _normalize_market(sanitized.get("market"))
    sanitized["language"] = _normalize_language(sanitized.get("language"))
    sanitized["generation_mode"] = _normalize_generation_mode(sanitized.get("generation_mode"))
    sanitized["competitor_strategy_enabled"] = bool(draft.get("competitor_strategy_enabled"))
    return sanitized


def _sanitize_attachment_roles(values: list[Any]) -> list[dict[str, str]]:
    roles = []
    for value in values:
        if not isinstance(value, dict):
            continue
        role = str(value.get("role") or "").lower()
        if role not in {"product", "competitor", "avatar", "direction"}:
            continue
        roles.append(
            {
                "item_id": _clip(value.get("item_id"), 80),
                "role": role,
                "reason": _clip(value.get("reason"), 180),
            }
        )
    return roles[:30]


def _safe_form(form: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "product_name",
        "product_info",
        "product_reference_url",
        "competitor_strategy_enabled",
        "competitor_name",
        "competitor_url",
        "competitor_chat_brief",
        "avatar_reference_url",
        "custom_avatar_persona",
        "avatar_identity_note",
        "ugc_video_extra_prompt",
        "platform",
        "market",
        "language",
        "generation_mode",
    ]
    return {key: _clip(form.get(key), FIELD_LIMITS.get(key, 200)) for key in allowed if form.get(key)}


def _product_fields(text: str, current_form: dict[str, Any]) -> dict[str, str]:
    sections = _product_labeled_sections(text)
    all_urls = _urls(text)
    labeled_image_urls = _flatten(sections.get("product_image_url") or [])
    image_urls = _unique(
        [
            *(url for value in labeled_image_urls for url in _urls(value)),
            *(url for url in all_urls if _looks_like_direct_image_url(url)),
        ]
    )
    product_reference_url = next((url for url in image_urls if _looks_like_direct_image_url(url)), "")
    product_name = _explicit_product_name(sections, current_form) or _product_name(text, current_form)
    product_info = _product_info(text, product_name=product_name, product_reference_url=product_reference_url, sections=sections)
    return {
        "product_name": product_name,
        "product_info": product_info,
        "product_reference_url": product_reference_url,
    }


def _product_labeled_sections(text: str) -> dict[str, list[str]]:
    prepared = _prepare_product_labeled_text(text)
    sections: dict[str, list[str]] = {}
    current_key = ""
    for raw_line in prepared.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(
            rf"^\s*(?P<label>{PRODUCT_LABEL_PATTERN})\s*(?:[:=\-–—])\s*(?P<value>.*)$",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            label = _normalize_product_label(match.group("label"))
            current_key = PRODUCT_LABEL_ALIASES.get(label, "")
            value = match.group("value").strip()
            if current_key and value:
                sections.setdefault(current_key, []).append(value)
            continue
        if current_key == "product_info":
            sections.setdefault(current_key, []).append(line)
    return sections


def _prepare_product_labeled_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(
        rf"(?<!^)(?<!\n)\s+(?P<label>{PRODUCT_LABEL_PATTERN})\s*(?=[:=\-–—])",
        lambda match: f"\n{match.group('label')}",
        str(text),
        flags=re.IGNORECASE,
    )


def _explicit_product_name(sections: dict[str, list[str]], current_form: dict[str, Any]) -> str:
    if current_form.get("product_name"):
        return _clip(current_form.get("product_name"), FIELD_LIMITS["product_name"])
    for value in sections.get("product_name") or []:
        candidate = _clean_product_name_candidate(value)
        if candidate:
            return candidate
    return ""


def _product_name(text: str, current_form: dict[str, Any]) -> str:
    if current_form.get("product_name"):
        return _clip(current_form.get("product_name"), FIELD_LIMITS["product_name"])
    text_without_urls = _strip_urls(text)
    for line in re.split(r"[\n.;|]+", text_without_urls):
        cleaned = _strip_product_label_prefix(line).strip(" -*#\t")
        cleaned = _clean_product_name_candidate(cleaned)
        if not cleaned or _urls(cleaned):
            continue
        if len(cleaned) <= 90 and not _is_generic_label_value(cleaned):
            return cleaned
    return ""


def _product_info(
    text: str,
    *,
    product_name: str,
    product_reference_url: str,
    sections: dict[str, list[str]],
) -> str:
    parts = [_strip_direct_image_urls(value) for value in sections.get("product_info") or []]
    if not parts:
        prepared = _prepare_product_labeled_text(text)
        for raw_line in prepared.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            key, value = _split_product_label(line)
            if key in {"product_url", "product_image_url"}:
                continue
            if key == "product_name":
                candidate = _clean_product_name_candidate(value)
                if candidate and candidate.lower() == product_name.lower():
                    continue
                line = value
            elif key == "product_info":
                line = value
            cleaned = _strip_direct_image_urls(line).strip(" -*#\t")
            if not cleaned or cleaned.lower() == product_name.lower():
                continue
            if _is_generic_label_value(cleaned):
                continue
            parts.append(cleaned)
    non_image_product_urls = _non_image_product_urls(text, sections, product_reference_url)
    for url in non_image_product_urls:
        parts.append(f"Product URL: {url}")
    return _normalize_product_info_urls(_join_blocks(_unique(parts)), product_reference_url)


def _normalize_product_info_urls(product_info: Any, product_reference_url: str = "") -> str:
    text = str(product_info or "")
    urls = _urls(text)
    product_urls = _unique(
        [
            url
            for url in urls
            if url != product_reference_url and not _looks_like_direct_image_url(url)
        ]
    )
    for url in urls:
        text = text.replace(url, "")
    lines = []
    for line in text.replace("\r", "\n").split("\n"):
        cleaned = re.sub(r"\bProduct URL\s*:\s*$", "", line.strip(), flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        if cleaned:
            lines.append(cleaned)
    lines.extend(f"Product URL: {url}" for url in product_urls[:4])
    return _clip_multiline(_join_blocks(_unique(lines)), FIELD_LIMITS["product_info"])


def _split_product_label(line: str) -> tuple[str, str]:
    match = re.match(
        rf"^\s*(?P<label>{PRODUCT_LABEL_PATTERN})\s*(?:[:=\-–—])\s*(?P<value>.*)$",
        str(line or "").strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return "", str(line or "").strip()
    label = _normalize_product_label(match.group("label"))
    return PRODUCT_LABEL_ALIASES.get(label, ""), match.group("value").strip()


def _non_image_product_urls(text: str, sections: dict[str, list[str]], product_reference_url: str) -> list[str]:
    labeled_urls = [url for value in _flatten(sections.get("product_url") or []) for url in _urls(value)]
    all_urls = _unique([*labeled_urls, *_urls(text)])
    return [
        url
        for url in all_urls
        if url != product_reference_url and not _looks_like_direct_image_url(url)
    ][:4]


def _clean_product_name_candidate(value: Any) -> str:
    text = _strip_urls(value)
    text = _strip_product_label_prefix(text)
    text = re.sub(r"\b(?:product|produkt|name|nazev|název|jmeno|jméno)\b\s*[:=\-–—]*", "", text, flags=re.IGNORECASE)
    text = " ".join(text.strip(" -*#\t\"'").split())
    if not text or _is_generic_label_value(text):
        return ""
    return _clip(text, FIELD_LIMITS["product_name"])


def _strip_product_label_prefix(value: Any) -> str:
    return re.sub(
        rf"^\s*(?:{PRODUCT_LABEL_PATTERN})\s*(?:[:=\-–—])\s*",
        "",
        str(value or ""),
        flags=re.IGNORECASE,
    )


def _strip_direct_image_urls(value: Any) -> str:
    text = str(value or "")
    for url in _urls(text):
        if _looks_like_direct_image_url(url):
            text = text.replace(url, "")
    return " ".join(text.split()).strip()


def _normalize_product_label(label: Any) -> str:
    return " ".join(str(label or "").strip().lower().split())


def _is_generic_label_value(value: Any) -> bool:
    text = re.sub(r"[^a-z0-9á-ž]+", "", str(value or "").strip().lower())
    return text in {"product", "produkt", "name", "nazev", "název", "jmeno", "jméno", "url", "link", "popis", "description", "brief"}


def _flatten(values: list[Any]) -> list[str]:
    return [str(value or "").strip() for value in values if str(value or "").strip()]


def _competitor_name(text: str) -> str:
    for pattern in [r"competitor[:\s]+([^\n,.]{2,80})", r"konkur(?:ent|ence)?[:\s]+([^\n,.]{2,80})"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _detect_platform(text: str) -> str:
    lowered = text.lower()
    if "tiktok" in lowered:
        return "tiktok"
    if "instagram" in lowered or "reels" in lowered:
        return "instagram"
    if "youtube" in lowered:
        return "youtube"
    if "google" in lowered:
        return "google_ads"
    if "meta" in lowered or "facebook" in lowered:
        return "meta"
    return ""


def _detect_market(text: str) -> str:
    upper = text.upper()
    for market in ["UK", "US", "CZ", "DE", "FR", "EU"]:
        if re.search(rf"\b{market}\b", upper):
            return market
    if "ČES" in upper or "CES" in upper:
        return "CZ"
    return ""


def _detect_language(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["čeština", "cesky", "česky", "czech"]):
        return "cs"
    if any(word in lowered for word in ["german", "něm", "deutsch"]):
        return "de"
    if any(word in lowered for word in ["french", "francouz"]):
        return "fr"
    if any(word in lowered for word in ["polish", "polsky"]):
        return "pl"
    if any(word in lowered for word in ["english", "anglicky", "angličtina"]):
        return "en"
    return ""


def _detect_generation_mode(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["jen video", "only video", "video only"]):
        return "video"
    if any(word in lowered for word in ["jen stat", "static only", "only static", "bez videa"]):
        return "static"
    if any(word in lowered for word in ["video +", "video a stat", "both", "ugc + stat"]):
        return "both"
    return ""


def _normalize_platform(value: str | None) -> str:
    value = str(value or "").strip().lower()
    if value in {"meta", "google_ads", "tiktok", "instagram", "youtube"}:
        return value
    return ""


def _normalize_market(value: str | None) -> str:
    value = str(value or "").strip().upper()
    return value if value in {"UK", "US", "CZ", "DE", "FR", "EU"} else ""


def _normalize_language(value: str | None) -> str:
    value = str(value or "").strip().lower()
    return value if value in {"en", "cs", "de", "fr", "pl"} else ""


def _normalize_generation_mode(value: str | None) -> str:
    value = str(value or "").strip().lower()
    return value if value in {"both", "video", "static"} else ""


def _warnings(draft: dict[str, Any], items: list[dict[str, Any]]) -> list[str]:
    warnings = []
    if not items:
        warnings.append("No chat items supplied.")
    if not draft.get("product_info") and not draft.get("product_reference_url"):
        warnings.append("Product brief is still sparse; add product notes, a product URL, or an image.")
    if "Product URL:" in str(draft.get("product_info") or "") and not draft.get("product_reference_url"):
        warnings.append("Product page URL was captured in product_info; video generation still needs a direct product image URL.")
    if draft.get("competitor_strategy_enabled") and not draft.get("competitor_chat_brief") and not draft.get("competitor_url"):
        warnings.append("Competitor mode is enabled but competitor notes are sparse.")
    return warnings


def _json_object(content: str) -> dict[str, Any]:
    text = str(content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _urls(text: Any) -> list[str]:
    return _unique([_clean_url(value) for value in re.findall(r"https?://[^\s<>'\"]+", str(text or ""))])


def _clean_url(value: Any) -> str:
    url = str(value or "").strip().strip("\"'<>")
    while re.search(r"[.,;:!?'\"]$", url):
        url = url[:-1]
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    return url


def _looks_like_direct_image_url(value: str) -> bool:
    text = str(value or "").strip().lower()
    return any(
        marker in text
        for marker in [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".avif",
            ".gif",
            "format=jpg",
            "format=jpeg",
            "format=png",
            "format=webp",
            "format=avif",
            "image/",
        ]
    )


def _strip_urls(text: Any) -> str:
    result = str(text or "")
    for url in _urls(result):
        result = result.replace(url, "")
    return result.strip()


def _join_blocks(values: list[Any]) -> str:
    return "\n\n".join(_clip_multiline(value, 2000) for value in values if str(value or "").strip()).strip()


def _clip(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").replace("\r", "\n").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _clip_multiline(value: Any, limit: int) -> str:
    lines = [" ".join(line.split()) for line in str(value or "").replace("\r", "\n").split("\n")]
    text = "\n".join(line for line in lines if line).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _unique(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
