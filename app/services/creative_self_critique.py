from __future__ import annotations

import json
from typing import Any

import requests

from app import config


def critique(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    ads_creative_set: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    deterministic = _deterministic_critique(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        ads_creative_set=ads_creative_set,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
    )
    key = api_key if api_key is not None else config.OPENROUTER_API_KEY
    if not key:
        return {
            **deterministic,
            "source": "deterministic",
            "ai_critique": {"status": "skipped", "reason": "OPENROUTER_API_KEY is missing."},
        }
    ai = _ai_critique(
        deterministic=deterministic,
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        static_image_generation=static_image_generation,
        api_key=key,
        model=model or config.OPENROUTER_PROMPT_MODEL,
        base_url=base_url,
    )
    return _merge(deterministic, ai)


def _deterministic_critique(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    ads_creative_set: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
) -> dict[str, Any]:
    hook = str(ugc_strategy.get("hook") or "")
    scenes = ugc_strategy.get("scene_by_scene_script") or []
    assets = static_image_generation.get("image_assets") or []
    vision_checks = static_image_generation.get("vision_quality_checks") or []
    prompt = str((content_prompt_package.get("seedance_payload") or {}).get("prompt") or "")
    scroll = 72 + (8 if "?" in hook else 0) + (8 if (ugc_strategy.get("emotional_angle") or {}).get("primary_angle") else 0)
    hook_strength = 70 + (10 if len(hook.split()) <= 18 else 0) + (8 if hook else 0)
    product_clarity = 70 + min(20, len(product_analysis.get("ad_safe_detail_phrases") or []) * 4)
    if "strict visual reference" in prompt:
        product_clarity += 5
    realism = 82
    failed_vision = [item for item in vision_checks if (item.get("result") or {}).get("status") == "failed"]
    if failed_vision:
        realism -= 15
    if assets and static_image_generation.get("vision_quality_status") in {"completed", "completed_with_regeneration"}:
        realism += 5
    ad_policy_risk = 15
    if product_analysis.get("unsupported_claims"):
        ad_policy_risk += 35
    if not scenes:
        hook_strength -= 15
        scroll -= 10
    scores = {
        "scroll_stopping_score": _clamp(scroll),
        "realism_score": _clamp(realism),
        "ad_policy_risk_score": _clamp(ad_policy_risk),
        "hook_strength_score": _clamp(hook_strength),
        "product_clarity_score": _clamp(product_clarity),
    }
    regen = (
        scores["scroll_stopping_score"] < 70
        or scores["realism_score"] < 75
        or scores["hook_strength_score"] < 75
        or scores["product_clarity_score"] < 75
        or scores["ad_policy_risk_score"] > 45
    )
    return {
        "agent": "AI Self Critique",
        "version": "creative_self_critique_v1",
        "source": "deterministic",
        **scores,
        "regeneration_recommended": regen,
        "regeneration_reasons": _reasons(scores, failed_vision),
        "recommended_changes": _recommended_changes(scores, ugc_strategy, static_image_generation),
        "reviewed_assets": {
            "static_asset_count": len(assets),
            "video_status": video_generation.get("video_generation_status"),
            "vision_quality_status": static_image_generation.get("vision_quality_status"),
            "prompt_architecture": (content_prompt_package.get("structured_prompt_v2") or {}).get("version"),
        },
    }


def _ai_critique(
    *,
    deterministic: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    static_image_generation: dict[str, Any],
    api_key: str,
    model: str,
    base_url: str,
) -> dict[str, Any] | None:
    user = {
        "task": "Critique this paid UGC ad creative set. Return only JSON with scores 0-100 and concise recommendations.",
        "required_schema": {
            "scroll_stopping_score": 0,
            "realism_score": 0,
            "ad_policy_risk_score": 0,
            "hook_strength_score": 0,
            "product_clarity_score": 0,
            "regeneration_recommended": False,
            "regeneration_reasons": [],
            "recommended_changes": [],
        },
        "deterministic_baseline": deterministic,
        "product": {
            "name": product_analysis.get("product_name"),
            "category": product_analysis.get("likely_product_category"),
            "facts": product_analysis.get("user_provided_facts"),
            "unsupported_claims": product_analysis.get("unsupported_claims"),
        },
        "ugc": {
            "hook": ugc_strategy.get("hook"),
            "voice_profile": ugc_strategy.get("voice_profile"),
            "emotional_angle": ugc_strategy.get("emotional_angle"),
            "scenes": ugc_strategy.get("scene_by_scene_script"),
        },
        "static_generation": {
            "status": static_image_generation.get("image_generation_status"),
            "vision_quality_status": static_image_generation.get("vision_quality_status"),
            "vision_quality_checks": static_image_generation.get("vision_quality_checks"),
            "failures": static_image_generation.get("failures"),
        },
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
            },
            json={
                "model": model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict paid social creative critic. Score scroll stopping, realism, "
                            "ad policy risk, hook strength, and product clarity. Do not invent facts."
                        ),
                    },
                    {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                ],
                "usage": {"include": True},
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        parsed = _parse_json(_message_content(result))
        if not parsed:
            return {"ai_critique": {"status": "failed", "reason": "invalid JSON", "model": model}}
        parsed["ai_critique"] = {"status": "completed", "model": model, "usage": result.get("usage")}
        return parsed
    except Exception as exc:
        return {"ai_critique": {"status": "failed", "reason": str(exc), "model": model}}


def _merge(deterministic: dict[str, Any], ai: dict[str, Any] | None) -> dict[str, Any]:
    if not ai or ai.get("ai_critique", {}).get("status") != "completed":
        return {**deterministic, "ai_critique": (ai or {}).get("ai_critique") or {"status": "failed"}}
    merged = dict(deterministic)
    for key in [
        "scroll_stopping_score",
        "realism_score",
        "ad_policy_risk_score",
        "hook_strength_score",
        "product_clarity_score",
    ]:
        if key in ai:
            merged[key] = _clamp(ai.get(key))
    merged["regeneration_recommended"] = bool(ai.get("regeneration_recommended"))
    merged["regeneration_reasons"] = [str(item)[:180] for item in ai.get("regeneration_reasons") or []][:6]
    merged["recommended_changes"] = [str(item)[:220] for item in ai.get("recommended_changes") or []][:8]
    merged["source"] = "ai_refined"
    merged["ai_critique"] = ai.get("ai_critique")
    return merged


def _reasons(scores: dict[str, int], failed_vision: list[dict[str, Any]]) -> list[str]:
    reasons = []
    if scores["scroll_stopping_score"] < 70:
        reasons.append("Scroll stopping score is weak.")
    if scores["realism_score"] < 75:
        reasons.append("Realism score is weak.")
    if failed_vision:
        reasons.append("Vision QA found generated asset issues.")
    if scores["ad_policy_risk_score"] > 45:
        reasons.append("Ad policy risk is elevated.")
    if scores["hook_strength_score"] < 75:
        reasons.append("Hook needs a stronger first-three-second reason.")
    if scores["product_clarity_score"] < 75:
        reasons.append("Product clarity is too low.")
    return reasons


def _recommended_changes(
    scores: dict[str, int],
    ugc_strategy: dict[str, Any],
    static_image_generation: dict[str, Any],
) -> list[str]:
    changes = []
    if scores["scroll_stopping_score"] < 80:
        changes.append("Make the first scene more specific: show the product/category detail immediately.")
    if scores["hook_strength_score"] < 85:
        changes.append("Rewrite hook around the selected emotional angle and one visible product detail.")
    if scores["realism_score"] < 85 or static_image_generation.get("vision_quality_rejections"):
        changes.append("Regenerate weak static assets with stricter realism and product-fidelity addendum.")
    if not (ugc_strategy.get("emotional_angle") or {}).get("primary_angle"):
        changes.append("Select an emotional angle before generating the next creative set.")
    return changes


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
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(content[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _clamp(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return 0
