from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from app import config
from app.services.image_reference_utils import local_image_to_data_url


FAIL_THRESHOLD = 75


def score_generated_asset(
    product_reference_url: str,
    generated_image_path: str | Path,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    key = api_key if api_key is not None else config.OPENROUTER_API_KEY
    selected_model = model or config.OPENROUTER_VISION_MODEL
    if not key:
        return _skipped("OpenRouter API key is missing.")
    generated_data_url = local_image_to_data_url(generated_image_path)
    if not generated_data_url:
        return _skipped("Generated image file could not be read for vision scoring.")
    reference_url = _reference_image_url(product_reference_url)
    if not reference_url:
        return _skipped("Product reference image is unavailable for vision comparison.")

    payload = {
        "model": selected_model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _vision_prompt()},
                    {"type": "image_url", "image_url": {"url": reference_url}},
                    {"type": "image_url", "image_url": {"url": generated_data_url}},
                ],
            }
        ],
        "usage": {"include": True},
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
            },
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        result = response.json()
        parsed = _parse_json(_message_content(result))
        if not parsed:
            return _vision_error("Vision model returned invalid JSON.", selected_model, result.get("usage"))
        normalized = _normalize_score(parsed)
        normalized["model"] = selected_model
        normalized["usage"] = result.get("usage")
        return normalized
    except Exception as exc:
        return _vision_error(str(exc), selected_model, None)


def _vision_prompt() -> str:
    return (
        "You are an ecommerce creative QA vision model. Compare image 1 (product reference) "
        "with image 2 (generated ad creative). Return only one valid JSON object. Score product fidelity "
        "and human realism from 0 to 100. Product fidelity must compare shape, colour, material finish, "
        "proportions, branding/visible markings, and whether the product was modified, restyled, recoloured, "
        "or rebranded. Human realism must inspect face artifacts, hands/fingers, anatomy, lighting, reflections, "
        "skin texture, scale, and photographic plausibility. Also flag dropshipping trust issues in notes and the "
        "regeneration addendum: over-polished catalogue/studio look, fake luxury positioning, glossy AI retouch, "
        "fake reviews/ratings/discounts/scarcity, platform UI, unreadable or broken text, and product scenes that "
        "feel less like a real buyer checking the item than a synthetic brand shoot. If any core score is below 75, set status=failed, "
        "regeneration_required=true, and write a concise regeneration_prompt_addendum that can be appended to "
        "the next image generation prompt. If no person is visible, score human realism only for visible hands/body "
        "or set non_applicable=true. Required JSON schema: "
        "{\"status\":\"passed|failed\",\"product_fidelity\":{\"shape_match\":0,\"color_match\":0,"
        "\"branding_match\":0,\"material_finish_match\":0,\"notes\":[]},\"human_realism\":{\"overall\":0,"
        "\"face_artifacts\":0,\"hands_fingers\":0,\"anatomy\":0,\"lighting_realism\":0,"
        "\"reflection_realism\":0,\"skin_texture\":0,\"non_applicable\":false,\"notes\":[]},"
        "\"regeneration_required\":false,\"regeneration_prompt_addendum\":\"\"}"
    )


def _reference_image_url(value: str | Path) -> str:
    text = str(value or "").strip()
    if text.startswith(("http://", "https://", "data:image/")):
        return text
    return local_image_to_data_url(text) or ""


def _normalize_score(parsed: dict[str, Any]) -> dict[str, Any]:
    fidelity = parsed.get("product_fidelity") if isinstance(parsed.get("product_fidelity"), dict) else {}
    realism = parsed.get("human_realism") if isinstance(parsed.get("human_realism"), dict) else {}
    normalized_fidelity = {
        "shape_match": _score(fidelity.get("shape_match")),
        "color_match": _score(fidelity.get("color_match")),
        "branding_match": _score(fidelity.get("branding_match")),
        "material_finish_match": _score(fidelity.get("material_finish_match")),
        "notes": _notes(fidelity.get("notes")),
    }
    normalized_realism = {
        "overall": _score(realism.get("overall")),
        "face_artifacts": _score(realism.get("face_artifacts")),
        "hands_fingers": _score(realism.get("hands_fingers")),
        "anatomy": _score(realism.get("anatomy")),
        "lighting_realism": _score(realism.get("lighting_realism")),
        "reflection_realism": _score(realism.get("reflection_realism")),
        "skin_texture": _score(realism.get("skin_texture")),
        "non_applicable": bool(realism.get("non_applicable")),
        "notes": _notes(realism.get("notes")),
    }
    core_scores = [
        normalized_fidelity["shape_match"],
        normalized_fidelity["color_match"],
        normalized_fidelity["branding_match"],
        normalized_fidelity["material_finish_match"],
    ]
    if not normalized_realism["non_applicable"]:
        core_scores.extend(
            [
                normalized_realism["overall"],
                normalized_realism["anatomy"],
                normalized_realism["lighting_realism"],
            ]
        )
    failed_by_score = any(score < FAIL_THRESHOLD for score in core_scores)
    addendum = str(parsed.get("regeneration_prompt_addendum") or "").strip()
    requested_retry = bool(parsed.get("regeneration_required")) or parsed.get("status") == "failed"
    has_actionable_note = bool(
        addendum
        or normalized_fidelity["notes"]
        or normalized_realism["notes"]
    )
    ignored_model_retry = bool(requested_retry and not failed_by_score and not has_actionable_note)
    status = "failed" if failed_by_score or (requested_retry and has_actionable_note) else "passed"
    if status == "failed" and not addendum:
        addendum = (
            "Regenerate with stricter product fidelity, exact shape and colour match, realistic adult anatomy, "
            "natural hands, physically plausible lighting, no AI gloss or distorted product geometry, and a more "
            "believable buyer-proof dropshipping product-check look"
        )
    return {
        "status": status,
        "product_fidelity": normalized_fidelity,
        "human_realism": normalized_realism,
        "regeneration_required": status == "failed",
        "regeneration_prompt_addendum": addendum[:700],
        "model_retry_ignored": ignored_model_retry,
    }


def _score(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return 0


def _notes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip()[:180] for item in value if str(item).strip()][:6]
    if value:
        return [str(value).strip()[:180]]
    return []


def _message_content(result: dict[str, Any]) -> str:
    for choice in result.get("choices") or []:
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return ""


def _parse_json(content: str) -> dict[str, Any] | None:
    content = str(content or "").strip()
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


def _skipped(reason: str) -> dict[str, Any]:
    return {
        "status": "skipped",
        "reason": reason,
        "regeneration_required": False,
        "product_fidelity": None,
        "human_realism": None,
    }


def _vision_error(reason: str, model: str, usage: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "status": "vision_error",
        "reason": reason,
        "model": model,
        "usage": usage,
        "regeneration_required": False,
        "product_fidelity": None,
        "human_realism": None,
    }
