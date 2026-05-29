from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.services import openrouter_seedance_client, provider_capability_service


SUPPORTED_IMAGE_SIZES = provider_capability_service.SUPPORTED_IMAGE_SIZES
MAX_STATIC_IMAGE_CAP = provider_capability_service.MAX_STATIC_IMAGE_CAP
MAX_PROMPT_CHARS = provider_capability_service.MAX_PROMPT_CHARS


def validate(
    *,
    generation_mode: str,
    should_generate_video: bool,
    should_generate_static_images: bool,
    product_reference_url: str,
    avatar_reference_url: str,
    use_avatar_image_reference: bool,
    seedance_model: str,
    image_model: str,
    max_static_images: int,
    image_size: str,
    require_product_reference_for_video: bool = True,
    content_prompt_package: dict[str, Any] | None = None,
    ads_creative_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks = []

    checks.append(
        _check(
            "generation_mode",
            generation_mode in {"both", "video", "static"},
            "passed",
            f"Generation mode is {generation_mode}.",
            "Use both, video, or static.",
        )
    )
    if product_reference_url:
        checks.append(
            _check(
                "product_reference_public_url",
                _is_public_http_url(product_reference_url),
                "passed",
                "Product reference URL is public HTTP(S).",
                "Use a public HTTPS product image URL, not localhost or a private file path.",
            )
        )
        checks.append(
            _check(
                "product_reference_direct_image_url",
                _looks_like_direct_image_url(product_reference_url),
                "passed",
                "Product reference URL looks like a direct image file.",
                "Product reference URL must be a direct image file such as .jpg, .png, .webp, or .avif. Product pages, docs, and HTML URLs cannot preserve exact product fidelity.",
            )
        )
    elif should_generate_video and not require_product_reference_for_video:
        checks.append(
            {
                "id": "product_reference_public_url",
                "status": "skipped",
                "reason": "This workflow does not require a product image reference for video.",
                "next_step": None,
            }
        )
    else:
        missing_status = "failed" if should_generate_video else "warning"
        missing_reason = (
            "Video generation requires a direct public HTTPS product image reference. "
            "Local uploads and product notes can help planning/static prompts, but video models cannot reliably preserve the exact product without a public image URL."
            if should_generate_video
            else "No public product reference URL was supplied. Local uploads can work for static image prompting, but video fidelity requires a direct public HTTPS product image URL."
        )
        checks.append(
            {
                "id": "product_reference_public_url",
                "status": missing_status,
                "reason": missing_reason,
                "next_step": "For video fidelity, provide a direct public HTTPS product image URL.",
            }
        )
    if use_avatar_image_reference:
        checks.append(
            _check(
                "avatar_reference_public_url",
                bool(avatar_reference_url) and _is_public_http_url(avatar_reference_url),
                "passed",
                "Avatar reference URL is public HTTP(S).",
                "Use a public HTTPS avatar reference URL or disable avatar image reference mode.",
            )
        )
        checks.append(
            _check(
                "avatar_reference_direct_image_url",
                bool(avatar_reference_url) and _looks_like_direct_image_url(avatar_reference_url),
                "passed",
                "Avatar reference URL looks like a direct image file.",
                "Avatar reference URL must be a direct image file such as .jpg, .png, .webp, or .avif, or disable avatar image reference mode.",
            )
        )
        checks.append(
            {
                "id": "avatar_reference_provider_restriction_risk",
                "status": "warning",
                "reason": "Some Seedance/OpenRouter video providers may reject realistic human avatar reference images because of privacy or sensitive-content restrictions.",
                "next_step": "If video generation fails with a real-person or sensitive-image restriction, turn off avatar image reference for that run and use prompt-only avatar consistency.",
            }
        )
    else:
        checks.append(
            {
                "id": "avatar_reference_public_url",
                "status": "skipped",
                "reason": "Avatar image reference mode is off.",
                "next_step": None,
            }
        )

    if should_generate_static_images:
        image_capability = provider_capability_service.image_model_capability(image_model)
        checks.append(
            _check(
                "image_model_supports_image_output",
                bool(image_capability.get("supports_image_output")),
                "passed",
                f"Selected image model looks image-capable: {image_model}.",
                "Selected image model does not support image generation. Use google/gemini-3-pro-image-preview.",
            )
        )
        checks[-1]["capability"] = image_capability
        checks.append(
            _check(
                "image_count_limit",
                0 <= int(max_static_images) <= MAX_STATIC_IMAGE_CAP,
                "passed",
                f"max_static_images={max_static_images} is inside the supported local cap.",
                f"Set max_static_images between 0 and {MAX_STATIC_IMAGE_CAP}.",
            )
        )
        checks.append(
            _check(
                "image_size_supported",
                str(image_size or "").upper() in SUPPORTED_IMAGE_SIZES,
                "passed",
                f"image_size={image_size} is supported.",
                "Use image size 1K, 2K, or 4K.",
            )
        )
    else:
        checks.extend(
            [
                _skipped("image_model_supports_image_output", "Static image generation is not requested."),
                _skipped("image_count_limit", "Static image generation is not requested."),
                _skipped("image_size_supported", "Static image generation is not requested."),
            ]
        )

    if should_generate_video:
        video_capability = provider_capability_service.video_model_capability(seedance_model)
        checks.append(
            _check(
                "video_model_supports_videos_endpoint",
                bool(video_capability.get("supports_videos_endpoint")),
                "passed",
                f"Selected video model looks /videos-capable: {seedance_model}.",
                "Selected video model does not look compatible with OpenRouter /videos. Use a bytedance/seedance or google/veo video model.",
            )
        )
        checks[-1]["capability"] = video_capability
        payload = (content_prompt_package or {}).get("seedance_payload") or {}
        aspect_ratio = str(payload.get("aspect_ratio") or "9:16")
        normalized_ratio = openrouter_seedance_client.ASPECT_RATIO_FALLBACKS.get(
            aspect_ratio, aspect_ratio
        )
        checks.append(
            _check(
                "video_aspect_ratio_supported",
                normalized_ratio in openrouter_seedance_client.SUPPORTED_ASPECT_RATIOS,
                "passed",
                f"Video aspect ratio {aspect_ratio} is supported or normalized to {normalized_ratio}.",
                "Use 9:16, 16:9, or 1:1 for this workflow.",
            )
        )
        seedance_prompt = str(payload.get("prompt") or "")
        checks.append(
            _check(
                "video_prompt_size",
                len(seedance_prompt) <= MAX_PROMPT_CHARS,
                "passed",
                f"Seedance prompt size is {len(seedance_prompt)} chars.",
                f"Final video prompt is too long. Keep it under {MAX_PROMPT_CHARS} characters.",
            )
        )
    else:
        checks.extend(
            [
                _skipped("video_model_supports_videos_endpoint", "Video generation is not requested."),
                _skipped("video_aspect_ratio_supported", "Video generation is not requested."),
                _skipped("video_prompt_size", "Video generation is not requested."),
            ]
        )

    if should_generate_static_images:
        static_prompt_generation = (ads_creative_set or {}).get("static_prompt_generation") or {}
        prompt_budget = static_prompt_generation.get("prompt_budget") or {}
        sent_chars = int(prompt_budget.get("user_chars_sent") or 0)
        checks.append(
            _check(
                "static_prompt_model_payload_size",
                not sent_chars or sent_chars <= MAX_PROMPT_CHARS,
                "passed",
                f"Static prompt model payload size is {sent_chars or 'unknown'} chars.",
                f"Static prompt payload is too long. Keep prompt model payload under {MAX_PROMPT_CHARS} characters.",
            )
        )
    else:
        checks.append(_skipped("static_prompt_model_payload_size", "Static image generation is not requested."))

    failed = [item for item in checks if item.get("status") == "failed"]
    return {
        "status": "blocked" if failed else "passed",
        "reason": failed[0]["reason"] if failed else None,
        "checks": checks,
    }
def _is_public_http_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname not in {"localhost", "127.0.0.1", "::1"}


def _looks_like_direct_image_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    haystack = f"{parsed.path.lower()}?{parsed.query.lower()}"
    image_markers = [
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
    return any(marker in haystack for marker in image_markers)


def _check(
    check_id: str,
    passed: bool,
    passed_status: str,
    passed_reason: str,
    failed_reason: str,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": passed_status if passed else "failed",
        "reason": passed_reason if passed else failed_reason,
        "next_step": None if passed else failed_reason,
    }


def _skipped(check_id: str, reason: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "skipped",
        "reason": reason,
        "next_step": None,
    }
