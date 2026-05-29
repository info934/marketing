from __future__ import annotations

import json
from typing import Any

import requests

from app import config
from app.services import json_schema_contracts
from app.services.localization_utils import localize_phrases
from app.services.text_utils import normalize_text, unique_preserve_order


SUPPORTED_CATEGORIES = {"handbag", "shoes", "apparel", "beauty", "home", "electronics", "unknown"}


def enrich(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    """Add category/style/audience intelligence without trusting unsupported claims."""
    deterministic = _deterministic_understanding(product_analysis, settings)
    ai_understanding = _ai_refine_understanding(
        product_analysis=product_analysis,
        settings=settings,
        deterministic=deterministic,
        api_key=api_key if api_key is not None else config.OPENROUTER_API_KEY,
        model=model or config.OPENROUTER_PROMPT_MODEL,
        base_url=base_url,
    )
    final = _merge_understanding(deterministic, ai_understanding)
    enriched = {**product_analysis}
    enriched["automatic_product_understanding"] = final
    enriched["likely_product_category"] = _final_category(product_analysis, final)
    if enriched["likely_product_category"] != product_analysis.get("likely_product_category"):
        enriched["product_category_source"] = "automatic_product_understanding"
    enriched["suggested_target_audience"] = final.get("target_audience") or product_analysis.get(
        "suggested_target_audience"
    )
    enriched["safe_use_cases"] = unique_preserve_order(
        (product_analysis.get("safe_use_cases") or []) + (final.get("usage_contexts") or [])
    )[:6]
    enriched["ad_safe_detail_phrases"] = unique_preserve_order(
        (product_analysis.get("ad_safe_detail_phrases") or [])
        + (final.get("prompt_grounding_details") or [])
    )[:10]
    language = settings.get("language") or product_analysis.get("customer_language") or "en"
    enriched["user_provided_facts_localized"] = localize_phrases(
        product_analysis.get("user_provided_facts") or [],
        language,
    )
    enriched["safe_benefits_localized"] = localize_phrases(
        product_analysis.get("safe_benefits") or [],
        language,
    )
    enriched["ad_safe_detail_phrases_localized"] = localize_phrases(
        enriched.get("ad_safe_detail_phrases") or [],
        language,
    )
    enriched["customer_language"] = language
    sources = enriched.get("prompt_data_sources") or {}
    derived = sources.get("derived_from_user_input") or []
    sources["derived_from_user_input"] = unique_preserve_order(
        derived + ["automatic_product_understanding"]
    )
    enriched["prompt_data_sources"] = sources
    return enriched


def _deterministic_understanding(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    facts = product_analysis.get("known_product_facts") or {}
    notes = " ".join(
        [
            str(product_analysis.get("product_name") or ""),
            str(product_analysis.get("internal_brief_notes") or ""),
            " ".join(product_analysis.get("user_provided_facts") or []),
        ]
    )
    lowered = notes.lower()
    category = str(product_analysis.get("likely_product_category") or "unknown")
    material = facts.get("material") or _detect_material(lowered)
    style_tags = _style_tags(category, lowered)
    usage_contexts = _usage_contexts(category, lowered)
    season = _season(lowered, category)
    target_audience = _target_audience(category, lowered, settings)
    market_position = _market_position(lowered, material)
    prompt_grounding = _prompt_grounding(product_analysis, style_tags, usage_contexts)

    return {
        "agent": "Automatic Product Understanding",
        "status": "fallback",
        "source": "deterministic",
        "category": category if category in SUPPORTED_CATEGORIES else "unknown",
        "category_confidence": 0.78 if category != "unknown" else 0.42,
        "material": material,
        "style": ", ".join(style_tags[:3]) if style_tags else "clear everyday product styling",
        "style_tags": style_tags,
        "market_position": market_position,
        "positioning_level": market_position,
        "target_audience": target_audience,
        "usage_contexts": usage_contexts,
        "season": season,
        "fashion_style": _fashion_style(category, style_tags, usage_contexts),
        "prompt_grounding_details": prompt_grounding,
        "category_specific_prompt_rules": _category_rules(category),
        "creative_implications": _creative_implications(category, style_tags, usage_contexts),
        "claim_policy": "Use these fields as internal prompt guidance only; do not turn market_position or style into unsupported ad claims.",
        "ai_refinement": {"status": "skipped", "reason": "No prompt model call was made."},
    }


def _ai_refine_understanding(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    deterministic: dict[str, Any],
    api_key: str,
    model: str,
    base_url: str,
) -> dict[str, Any] | None:
    if not api_key:
        return None
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": json_schema_contracts.PRODUCT_UNDERSTANDING_RESPONSE_FORMAT,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an ecommerce product understanding agent. Return only valid JSON. "
                    "Detect category, material, style, market_position, target_audience, usage_contexts, "
                    "season, fashion_style, and prompt_grounding_details from the user's product facts. "
                    "Do not invent facts, reviews, claims, prices, discounts, medical benefits, or brand proof. "
                    "Use market_position as internal creative guidance, not as customer-facing copy."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "product_analysis": {
                            "product_name": product_analysis.get("product_name"),
                            "known_product_facts": product_analysis.get("known_product_facts"),
                            "user_provided_facts": product_analysis.get("user_provided_facts"),
                            "safe_benefits": product_analysis.get("safe_benefits"),
                            "internal_brief_notes": product_analysis.get("internal_brief_notes"),
                            "requested_product_category": product_analysis.get("requested_product_category"),
                        },
                        "settings": {
                            "market": settings.get("market"),
                            "language": settings.get("language"),
                            "platform": settings.get("platform"),
                        },
                        "deterministic_understanding": deterministic,
                        "required_schema": {
                            "category": "handbag|shoes|apparel|beauty|home|electronics|unknown",
                            "category_confidence": "0..1 number",
                            "material": "string or unknown",
                            "style": "short internal descriptor",
                            "style_tags": ["string"],
                            "market_position": "value|mid-market|mid-premium|premium-coded|unknown",
                            "target_audience": "short internal descriptor",
                            "usage_contexts": ["string"],
                            "season": "all-season|spring|summer|autumn|winter|unknown",
                            "fashion_style": "short internal descriptor",
                            "prompt_grounding_details": ["verified visual/detail cues only"],
                            "creative_implications": ["prompt guidance only"],
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "usage": {"include": True},
    }
    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        content = _message_content(result)
        parsed = _parse_json_object(content)
        if not parsed:
            return {"ai_refinement": {"status": "failed", "reason": "Prompt model returned invalid JSON."}}
        parsed["ai_refinement"] = {
            "status": "completed",
            "model": model,
            "usage": result.get("usage"),
        }
        return parsed
    except Exception as exc:
        return {"ai_refinement": {"status": "failed", "reason": str(exc), "model": model}}


def _merge_understanding(deterministic: dict[str, Any], ai_understanding: dict[str, Any] | None) -> dict[str, Any]:
    if not ai_understanding:
        return deterministic
    if not ai_understanding.get("category") and not ai_understanding.get("style"):
        return {**deterministic, "ai_refinement": ai_understanding.get("ai_refinement")}
    merged = {**deterministic}
    for key in [
        "category",
        "category_confidence",
        "material",
        "style",
        "market_position",
        "positioning_level",
        "target_audience",
        "season",
        "fashion_style",
    ]:
        value = ai_understanding.get(key)
        if value not in (None, "", [], {}):
            merged[key] = _sanitize_scalar(value)
    for key in ["style_tags", "usage_contexts", "prompt_grounding_details", "creative_implications"]:
        value = ai_understanding.get(key)
        if isinstance(value, list) and value:
            merged[key] = unique_preserve_order([_sanitize_scalar(item) for item in value if item])[:8]
    merged["source"] = "ai_refined" if ai_understanding.get("ai_refinement", {}).get("status") == "completed" else "fallback"
    merged["status"] = merged["source"]
    merged["ai_refinement"] = ai_understanding.get("ai_refinement") or deterministic.get("ai_refinement")
    return merged


def _final_category(product_analysis: dict[str, Any], understanding: dict[str, Any]) -> str:
    requested = str(product_analysis.get("requested_product_category") or "auto")
    current = str(product_analysis.get("likely_product_category") or "unknown")
    if requested and requested != "auto":
        return current
    detected = str(understanding.get("category") or current)
    confidence = float(understanding.get("category_confidence") or 0)
    if detected in SUPPORTED_CATEGORIES and confidence >= 0.6:
        return detected
    return current


def _detect_material(lowered: str) -> str:
    for material in ["two-layer cowhide leather", "cowhide leather", "vegan leather", "leather", "cotton", "linen", "wool", "metal", "wood", "ceramic"]:
        if material in lowered:
            return material
    return "unknown"


def _style_tags(category: str, lowered: str) -> list[str]:
    tags = []
    rules = {
        "minimalist": ["minimalist", "minimal", "clean"],
        "structured": ["structured", "holds shape", "stays structured"],
        "office-ready": ["work", "office", "commute"],
        "travel-friendly": ["travel", "weekend", "airport"],
        "everyday practical": ["errands", "daily", "real life", "everyday"],
        "polished casual": ["effortless", "polished", "smart casual"],
        "sporty": ["sport", "gym", "run", "training"],
        "soft lifestyle": ["soft", "cosy", "cozy"],
    }
    for tag, needles in rules.items():
        if any(needle in lowered for needle in needles):
            tags.append(tag)
    if not tags:
        defaults = {
            "handbag": ["everyday practical", "polished casual"],
            "shoes": ["everyday practical", "outfit-led"],
            "apparel": ["outfit-led", "polished casual"],
        }
        tags = defaults.get(category, ["clear practical"])
    return tags[:5]


def _usage_contexts(category: str, lowered: str) -> list[str]:
    contexts = []
    for label, needles in {
        "work commute": ["work", "office", "commute"],
        "errands": ["errands", "school run"],
        "travel": ["travel", "airport", "weekend"],
        "daily outfit styling": ["outfit", "style", "fashion"],
        "home routine": ["home", "living room", "kitchen"],
    }.items():
        if any(needle in lowered for needle in needles):
            contexts.append(label)
    if contexts:
        return contexts[:5]
    defaults = {
        "handbag": ["daily carry setup", "outfit styling"],
        "shoes": ["worn outfit view", "walking context"],
        "apparel": ["outfit styling", "garment movement"],
    }
    return defaults.get(category, ["everyday product context"])


def _season(lowered: str, category: str) -> str:
    seasons = {
        "summer": ["summer", "sandals", "beach", "holiday"],
        "winter": ["winter", "coat", "boots", "cold"],
        "spring": ["spring"],
        "autumn": ["autumn", "fall"],
    }
    for season, needles in seasons.items():
        if any(needle in lowered for needle in needles):
            return season
    if category in {"handbag", "beauty", "home", "electronics"}:
        return "all-season"
    return "unknown"


def _target_audience(category: str, lowered: str, settings: dict[str, Any]) -> str:
    market = normalize_text(settings.get("market")) or "market"
    if category == "handbag":
        if any(word in lowered for word in ["work", "office", "commute"]):
            return f"{market} women 25-45 comparing polished daily work bags"
        return f"{market} fashion shoppers 25-45 comparing practical daily bags"
    if category == "shoes":
        return f"{market} adults comparing footwear for outfit fit and everyday use"
    if category == "apparel":
        return f"{market} fashion shoppers comparing styling and fit"
    return f"{market} shoppers who want a clear product-led preview"


def _market_position(lowered: str, material: str) -> str:
    if any(word in lowered for word in ["cheap", "budget", "discount"]):
        return "value"
    if material in {"two-layer cowhide leather", "cowhide leather", "leather"} or any(
        word in lowered for word in ["structured", "minimalist", "crafted"]
    ):
        return "mid-premium"
    if any(word in lowered for word in ["premium", "polished", "refined"]):
        return "premium-coded"
    return "mid-market"


def _fashion_style(category: str, style_tags: list[str], usage_contexts: list[str]) -> str:
    if category not in {"handbag", "shoes", "apparel"}:
        return "not fashion-led"
    if "minimalist" in style_tags and "office-ready" in style_tags:
        return "minimal office style"
    if "travel-friendly" in style_tags:
        return "polished travel casual"
    if usage_contexts and "outfit" in usage_contexts[0]:
        return "outfit-led everyday style"
    return ", ".join(style_tags[:2]) or "everyday style"


def _prompt_grounding(product_analysis: dict[str, Any], style_tags: list[str], usage_contexts: list[str]) -> list[str]:
    facts = product_analysis.get("user_provided_facts") or []
    return unique_preserve_order(facts + style_tags[:2] + usage_contexts[:2])[:8]


def _category_rules(category: str) -> list[str]:
    rules = {
        "handbag": [
            "Show the bag carried on shoulder, held in hand, placed with an outfit, or opened for a storage view",
            "Avoid table-only product renders unless the creative is a detail zoom",
        ],
        "shoes": [
            "Show shoes worn on feet or in a walking/outfit context",
            "Avoid floating shoes, table still lifes, or unsupported comfort claims",
        ],
        "apparel": [
            "Show garment worn on an adult person or moving naturally on body",
            "Avoid mannequin-only imagery unless explicitly requested",
        ],
    }
    return rules.get(category, ["Use a real-life context that fits the detected product category"])


def _creative_implications(category: str, style_tags: list[str], usage_contexts: list[str]) -> list[str]:
    implications = [
        f"Lead with {usage_contexts[0]}" if usage_contexts else "Lead with product context",
        f"Visual tone should feel {style_tags[0]}" if style_tags else "Visual tone should feel clear and practical",
    ]
    if category == "handbag":
        implications.append("Prefer outfit/body context over tabletop still life for lifestyle creatives")
    if category == "shoes":
        implications.append("Prefer worn-on-foot context for static lifestyle and UGC b-roll")
    return implications


def _message_content(result: dict[str, Any]) -> str:
    for choice in result.get("choices") or []:
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return ""


def _parse_json_object(content: str) -> dict[str, Any] | None:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(content[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _sanitize_scalar(value: Any) -> Any:
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return normalize_text(str(value))[:240]
