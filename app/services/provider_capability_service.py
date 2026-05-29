from __future__ import annotations

from typing import Any


MAX_STATIC_IMAGE_CAP = 10
MAX_PROMPT_CHARS = 18000
SUPPORTED_IMAGE_SIZES = {"1K", "2K", "4K"}
SUPPORTED_VIDEO_ASPECT_RATIOS = {"9:16", "16:9", "1:1"}
ASPECT_RATIO_FALLBACKS = {"4:5": "9:16", "5:4": "1:1"}

IMAGE_MODELS: dict[str, dict[str, Any]] = {
    "google/gemini-3-pro-image-preview": {
        "supports_image_output": True,
        "supports_reference_images": True,
        "recommended_for": ["static_ads", "scene_concepts"],
    },
    "google/gemini-2.5-flash-image-preview": {
        "supports_image_output": True,
        "supports_reference_images": True,
        "recommended_for": ["static_ads", "scene_concepts"],
    },
    "google/gemini-2.5-flash-image": {
        "supports_image_output": True,
        "supports_reference_images": True,
        "recommended_for": ["static_ads", "scene_concepts"],
    },
}

VIDEO_MODELS: dict[str, dict[str, Any]] = {
    "bytedance/seedance-2.0-fast": {
        "supports_videos_endpoint": True,
        "supports_prompt_only_avatar": True,
        "supports_exact_avatar_reference": "provider_sensitive",
        "recommended_for": ["ugc_video", "finance_personal_brand"],
    },
    "bytedance/seedance-1.0-pro": {
        "supports_videos_endpoint": True,
        "supports_prompt_only_avatar": True,
        "supports_exact_avatar_reference": "provider_sensitive",
        "recommended_for": ["ugc_video"],
    },
    "google/veo-3.1-fast": {
        "supports_videos_endpoint": True,
        "supports_prompt_only_avatar": True,
        "supports_exact_avatar_reference": "provider_sensitive",
        "supports_image_prompt_input": True,
        "supports_native_audio": True,
        "recommended_for": ["ugc_video", "premium_video", "image_to_video"],
        "provider_family": "google_veo",
        "price_hint": "from $0.10 per second",
    },
}


def registry() -> dict[str, Any]:
    return {
        "version": "provider_capability_registry_v1",
        "limits": {
            "max_static_images": MAX_STATIC_IMAGE_CAP,
            "max_prompt_chars": MAX_PROMPT_CHARS,
            "supported_image_sizes": sorted(SUPPORTED_IMAGE_SIZES),
            "supported_video_aspect_ratios": sorted(SUPPORTED_VIDEO_ASPECT_RATIOS),
            "aspect_ratio_fallbacks": ASPECT_RATIO_FALLBACKS,
        },
        "image_models": IMAGE_MODELS,
        "video_models": VIDEO_MODELS,
        "policies": {
            "avatar_reference_restriction": (
                "Realistic human avatar reference images may be rejected by some video providers. "
                "Use prompt-only avatar consistency when exact image reference triggers provider restrictions."
            ),
            "cta_policy": "Destination URLs and CTA buttons are supplied by the ad platform, not rendered inside creative assets.",
            "static_image_count_policy": "max_static_images is a hard cap and never pads with duplicate creatives.",
            "ecommerce_static_plan": "C2 product hero, C3 use context, C4 detail proof, C5 buying guide.",
        },
    }


def image_model_capability(model: str) -> dict[str, Any]:
    normalized = _normalize(model)
    exact = IMAGE_MODELS.get(normalized)
    if exact:
        return {"model": model, "known": True, **exact}
    if _looks_veo_model(normalized):
        return {
            "model": model,
            "known": True,
            "supports_image_output": False,
            "supports_reference_images": True,
            "recommended_for": ["ugc_video", "image_to_video"],
            "provider_note": "Veo is a video generation model. Use it as the video model, not the static image model.",
        }
    looks_image_capable = "image" in normalized or "imagen" in normalized
    return {
        "model": model,
        "known": False,
        "supports_image_output": looks_image_capable,
        "supports_reference_images": looks_image_capable,
        "recommended_for": [],
    }


def video_model_capability(model: str) -> dict[str, Any]:
    normalized = _normalize(model)
    exact = VIDEO_MODELS.get(normalized)
    if exact:
        return {"model": model, "known": True, **exact}
    looks_video_capable = "seedance" in normalized or _looks_veo_model(normalized)
    return {
        "model": model,
        "known": False,
        "supports_videos_endpoint": looks_video_capable,
        "supports_prompt_only_avatar": looks_video_capable,
        "supports_exact_avatar_reference": "unknown" if looks_video_capable else False,
        "recommended_for": [],
    }


def normalized_aspect_ratio(value: str) -> str:
    ratio = str(value or "9:16").strip()
    return ASPECT_RATIO_FALLBACKS.get(ratio, ratio)


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()


def _looks_veo_model(value: str) -> bool:
    normalized = _normalize(value)
    return normalized.startswith("google/veo") or "/veo-" in normalized or " veo-" in normalized
