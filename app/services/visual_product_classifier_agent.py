from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from app import config
from app.services import json_schema_contracts
from app.services.image_reference_utils import local_image_to_data_url, normalize_public_image_url


SUPPORTED_CATEGORIES = {"handbag", "shoes", "apparel", "beauty", "home", "electronics", "unknown"}
SUPPORTED_TEMPLATES = {
    "apparel_try_on_full_body",
    "worn_footwear_check",
    "carry_capacity_check",
    "creator_connected_lifestyle",
    "product_unboxing",
    "talking_head_product_check",
    "app_promo",
}


def classify(
    *,
    product_analysis: dict[str, Any],
    product_image_path: str | Path | None,
    settings: dict[str, Any],
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    """Use the product image to guide category, template, scenario, and QA decisions."""

    image_url = _image_url(product_image_path)
    selected_model = model or config.OPENROUTER_VISION_MODEL
    if not image_url:
        return _skipped("No readable product image was available for visual classification.", selected_model)
    if not api_key:
        return _skipped("No OpenRouter API key was available for visual classification.", selected_model)

    payload = {
        "model": selected_model,
        "temperature": 0.1,
        "response_format": json_schema_contracts.VISUAL_PRODUCT_CLASSIFIER_RESPONSE_FORMAT,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a visual ecommerce product classifier for dropshipping UGC creatives. "
                    "Inspect the product image and return only valid JSON. Do not invent claims, brand proof, reviews, prices, or benefits. "
                    "Recommend the video template and scenario rules that best prove the product visually. "
                    "For apparel, use neutral garment wording such as cut, drape, silhouette, movement, and visible finish from the reference; "
                    "do not mention comfort, fabric type, fabric texture, or material unless it is explicitly verified."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "task": "Classify the product from the image and recommend UGC video template rules.",
                                "product_name": product_analysis.get("product_name"),
                                "text_detected_category": product_analysis.get("likely_product_category"),
                                "requested_product_category": product_analysis.get("requested_product_category"),
                                "known_product_facts": product_analysis.get("known_product_facts"),
                                "user_notes": product_analysis.get("internal_brief_notes"),
                                "market": settings.get("market"),
                                "language": settings.get("language"),
                                "template_rules": {
                                    "apparel": "Use apparel_try_on_full_body: full or near-full body worn view first, normal phone try-on, then cut, drape, silhouette, movement, and visible finish. Avoid comfort or material/fabric claims unless verified.",
                                    "shoes": "Use worn_footwear_check: shoes worn on adult feet, side profile, sole/upper detail, outfit context.",
                                    "handbag": "Use carry_capacity_check: bag carried or on shoulder, scale against body, verified capacity only when supplied.",
                                    "packaging": "Use product_unboxing only when packaging/box is visually present or user supplied.",
                                    "generic": "Use creator_connected_lifestyle for ordinary physical products that need real handling or use context.",
                                },
                            },
                            ensure_ascii=False,
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        "usage": {"include": True},
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "Visual Product Classifier",
            },
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        result = response.json()
        parsed = _parse_json_object(_message_content(result))
        if not parsed:
            return _error("Vision model returned invalid JSON.", selected_model, result.get("usage"))
        normalized = _normalize(parsed, product_analysis)
        return {
            "agent": "Visual Product Classifier Agent",
            "status": "completed",
            "model": selected_model,
            "source": "product_image_vision_model",
            "image_source": "data_url" if image_url.startswith("data:image/") else "public_url",
            "usage": result.get("usage"),
            **normalized,
        }
    except Exception as exc:
        return _error(str(exc), selected_model, None)


def apply_to_product_analysis(
    product_analysis: dict[str, Any],
    visual: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(product_analysis)
    enriched["visual_product_understanding"] = visual
    sources = dict(enriched.get("prompt_data_sources") or {})
    derived = list(sources.get("derived_from_user_input") or [])
    if "visual_product_understanding" not in derived:
        derived.append("visual_product_understanding")
    sources["derived_from_user_input"] = derived
    enriched["prompt_data_sources"] = sources

    if visual.get("status") != "completed":
        return enriched
    requested = str(enriched.get("requested_product_category") or "auto").lower()
    detected = str(visual.get("category") or "unknown").lower()
    confidence = float(visual.get("category_confidence") or 0)
    if requested == "auto" and detected in SUPPORTED_CATEGORIES and detected != "unknown" and confidence >= 0.72:
        if detected != enriched.get("likely_product_category"):
            enriched["likely_product_category"] = detected
            enriched["product_category_source"] = "visual_product_classifier"
    enriched["visual_subcategory"] = visual.get("subcategory") or ""
    enriched["visual_prompt_grounding_details"] = visual.get("visual_evidence") or []
    enriched["visual_scenario_rules"] = visual.get("scenario_rules") or []
    enriched["visual_shot_requirements"] = visual.get("shot_requirements") or []
    enriched["visual_qa_expectations"] = visual.get("qa_expectations") or []
    return enriched


def _image_url(product_image_path: str | Path | None) -> str:
    value = str(product_image_path or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return normalize_public_image_url(value)
    if value.startswith("data:image/"):
        return value
    return local_image_to_data_url(value) or ""


def _normalize(parsed: dict[str, Any], product_analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    category = str(parsed.get("category") or "unknown").lower()
    if category not in SUPPORTED_CATEGORIES:
        category = "unknown"
    template = str(parsed.get("recommended_template_id") or "").strip()
    if template not in SUPPORTED_TEMPLATES:
        template = _template_for_category(category)
    confidence = parsed.get("category_confidence")
    try:
        confidence_value = max(0.0, min(1.0, float(confidence)))
    except Exception:
        confidence_value = 0.0
    known_material = _known_material(product_analysis or {})
    return {
        "detected_object": _clean(parsed.get("detected_object"), 120),
        "category": category,
        "subcategory": _clean(parsed.get("subcategory"), 120),
        "category_confidence": confidence_value,
        "visual_evidence": _neutralize_unverified_material_text(
            _clean_list(parsed.get("visual_evidence"), 8, 140), category, known_material
        ),
        "reference_style": str(parsed.get("reference_style") or "unclear"),
        "recommended_template_id": template,
        "scenario_rules": _neutralize_unverified_material_text(
            _clean_list(parsed.get("scenario_rules"), 8, 180), category, known_material
        ),
        "shot_requirements": _neutralize_unverified_material_text(
            _clean_list(parsed.get("shot_requirements"), 8, 180), category, known_material
        ),
        "avoid_in_generation": _neutralize_unverified_material_text(
            _clean_list(parsed.get("avoid_in_generation"), 8, 180), category, known_material
        ),
        "qa_expectations": _neutralize_unverified_material_text(
            _clean_list(parsed.get("qa_expectations"), 8, 180), category, known_material
        ),
    }


_MATERIAL_WORDS = [
    "two-layer cowhide leather",
    "cowhide leather",
    "vegan leather",
    "leather",
    "suede",
    "silk",
    "fabric",
    "canvas",
    "plastic",
    "glass",
    "metal",
    "ceramic",
    "wood",
    "rubber",
    "cotton",
    "linen",
    "wool",
    "polyester",
    "nylon",
]


def _known_material(product_analysis: dict[str, Any]) -> str:
    facts = product_analysis.get("known_product_facts") or {}
    material = str(facts.get("material") or "").strip().lower() if isinstance(facts, dict) else ""
    if material in {"", "unknown", "not applicable"}:
        return ""
    return material


def _neutralize_unverified_material_text(values: list[str], category: str, known_material: str) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = str(value or "")
        if category == "apparel":
            text = text.replace("comfort and movement of the fabric", "movement, drape, and visible finish")
            text = text.replace("movement of the fabric", "garment movement")
            text = text.replace("flow of the fabric", "garment drape and movement")
            text = text.replace("how the fabric flows", "how the garment drapes and moves")
            text = text.replace("fabric flows", "garment drape and movement")
            text = text.replace("fabric-only", "garment-detail-only")
        if not known_material:
            text = _strip_unverified_material_examples(text)
        for word in _MATERIAL_WORDS:
            if not _material_word_allowed(word, known_material):
                text = _replace_unverified_material_word(text, word)
        cleaned.append(_clean(text, 180))
    return [item for item in cleaned if item]


def _material_word_allowed(word: str, known_material: str) -> bool:
    return bool(known_material and word in known_material)


def _strip_unverified_material_examples(text: str) -> str:
    return re.sub(
        r"\((?:e\.g\.|eg|for example)[^)]*(?:leather|suede|silk|fabric|canvas|plastic|glass|metal|ceramic|wood|rubber|cotton|linen|wool|polyester|nylon|waterproof)[^)]*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _replace_unverified_material_word(text: str, word: str) -> str:
    if word == "fabric":
        text = re.sub(r"\bcheckered\s+fabric\s+texture\b", "checkered pattern and visible surface texture", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfabric\s+texture\b", "visible surface texture", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfabric\s+weave\b", "visible surface texture", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfabric[- ]only\b", "detail-only", text, flags=re.IGNORECASE)
        return re.sub(r"\bfabric\b", "visible material finish", text, flags=re.IGNORECASE)
    if word in {"leather", "suede", "silk", "canvas", "plastic", "glass", "metal", "ceramic", "wood", "rubber"}:
        text = re.sub(rf"\b{re.escape(word)}\s+(texture|finish|look|material)\b", "visible surface detail", text, flags=re.IGNORECASE)
        return re.sub(rf"\b{re.escape(word)}\b", "material", text, flags=re.IGNORECASE)
    return re.sub(rf"\b{re.escape(word)}\b", "material", text, flags=re.IGNORECASE)


def _template_for_category(category: str) -> str:
    return {
        "apparel": "apparel_try_on_full_body",
        "shoes": "worn_footwear_check",
        "handbag": "carry_capacity_check",
        "beauty": "creator_connected_lifestyle",
        "home": "creator_connected_lifestyle",
        "electronics": "creator_connected_lifestyle",
    }.get(category, "talking_head_product_check")


def _message_content(result: dict[str, Any]) -> str:
    choices = result.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
    return ""


def _parse_json_object(content: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _clean(value: Any, max_len: int) -> str:
    return " ".join(str(value or "").split())[:max_len]


def _clean_list(value: Any, max_items: int, max_len: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean(item, max_len) for item in value if _clean(item, max_len)][:max_items]


def _skipped(reason: str, model: str) -> dict[str, Any]:
    return {
        "agent": "Visual Product Classifier Agent",
        "status": "skipped",
        "reason": reason,
        "model": model,
    }


def _error(reason: str, model: str, usage: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "agent": "Visual Product Classifier Agent",
        "status": "vision_error",
        "reason": reason,
        "model": model,
        "usage": usage,
    }
