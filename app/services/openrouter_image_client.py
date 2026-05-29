from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from app import config
from app.services.image_reference_utils import local_image_to_data_url
from app.services.text_utils import safe_slug
from app.services import prompt_defaults, vision_quality_client


DEFAULT_MAX_IMAGES = 8
IMAGE_PROMPT_MAX_CHARS = 9000
STATIC_DROPSHIPPING_REALISM_GUARD = (
    "Dropshipping static realism guard: make the image feel like a believable buyer-proof product check, "
    "not a polished catalogue render or luxury brand shoot. Use ordinary natural light, real camera perspective, "
    "simple everyday surroundings, honest product scale, visible detail proof, and slight real-photo imperfection. "
    "Avoid studio/showroom staging, glossy retouch, cinematic grading, fake premium lifestyle, fake reviews, ratings, "
    "discount badges, scarcity banners, platform UI, and overproduced DTC perfection."
)


def generate_single_image(
    *,
    prompt: str,
    creative_id: str,
    product_name: str,
    output_dir: str | Path = config.OUTPUT_DIR,
    api_key: str | None = None,
    model: str = config.OPENROUTER_IMAGE_MODEL,
    base_url: str = config.OPENROUTER_BASE_URL,
    aspect_ratio: str = "9:16",
    image_size: str = "1K",
    product_reference_url: str = "",
    reference_image_urls: list[str] | None = None,
) -> dict[str, Any]:
    key = api_key if api_key is not None else config.OPENROUTER_API_KEY
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    if not key:
        return {
            "image_generation_status": "skipped",
            "error": "OPENROUTER_API_KEY is missing; scene concept image generation was skipped.",
            "failure_reason": "OpenRouter API key is missing, so the scene concept image was not generated.",
            "next_step": "Add OPENROUTER_API_KEY to .env or paste the key in the UI, then prepare the scene again.",
            "model": model,
            "image_assets": [],
            "prompt": prompt,
            "reference_image_urls": reference_image_urls or [],
            "output_dir": str(output_dir),
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Finance Scene Concept Image",
    }
    payload = _request_payload(
        model=model,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        product_reference_url=product_reference_url,
        reference_image_urls=reference_image_urls,
    )
    trace_id = f"single_image_{int(time.time() * 1000)}"
    _write_trace(
        output_dir,
        {
            "trace_id": trace_id,
            "event": "single_image_request",
            "creative_id": creative_id,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "prompt": prompt,
            "reference_image_count": len([item for item in [product_reference_url, *(reference_image_urls or [])] if str(item or "").strip()]),
        },
    )
    try:
        response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=240)
        response.raise_for_status()
        result = response.json()
        image_urls = _extract_image_urls(result)[:1]
        if not image_urls:
            raise ValueError("OpenRouter response did not include generated images.")
        source_image_url = image_urls[0]
        suffix = _suffix_for_image_url(source_image_url)
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}_{safe_slug(creative_id)}{suffix}"
        image_path = target_dir / filename
        image_path.write_bytes(_image_bytes(source_image_url, headers, base_url))
        asset = {
            "creative_id": creative_id,
            "asset_type": "finance_scene_concept",
            "image_path": str(image_path),
            "image_url": _output_url(image_path),
            "source_image_url": source_image_url,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "prompt": prompt,
            "generation_id": result.get("id"),
            "usage": result.get("usage"),
        }
        return {
            "image_generation_status": "completed",
            "error": None,
            "failure_reason": None,
            "next_step": "Review and approve the scene concept before generating the video.",
            "model": model,
            "image_assets": [asset],
            "attempted_count": 1,
            "prompt": prompt,
            "reference_image_urls": reference_image_urls or [],
            "output_dir": str(output_dir),
            "usage": result.get("usage"),
            "generation_id": result.get("id"),
        }
    except Exception as exc:
        error = _format_request_error(exc)
        _write_trace(
            output_dir,
            {
                "trace_id": trace_id,
                "event": "single_image_failed",
                "creative_id": creative_id,
                "error": error,
            },
        )
        return {
            "image_generation_status": "failed",
            "error": error,
            "failure_reason": _human_failure_reason(error),
            "next_step": _next_step_for_error(error),
            "model": model,
            "image_assets": [],
            "attempted_count": 1,
            "prompt": prompt,
            "reference_image_urls": reference_image_urls or [],
            "output_dir": str(output_dir),
        }


def preview_ad_image_plan(
    ads_creative_set: dict[str, Any],
    product_reference_url: str = "",
    reference_image_urls: list[str] | None = None,
    max_images: int = DEFAULT_MAX_IMAGES,
    include_meme_images: bool = False,
) -> dict[str, Any]:
    extra_reference_image_urls = _unique_reference_urls(reference_image_urls or [], primary=product_reference_url)
    collected_creatives = _collect_image_creatives(
        ads_creative_set,
        product_reference_url,
        include_meme_style=include_meme_images,
    )
    creatives = _select_creatives_for_generation(
        collected_creatives,
        max_images=max_images,
    )
    for creative in creatives:
        creative["reference_image_urls"] = extra_reference_image_urls
    selected_ids = {creative["creative_id"] for creative in creatives}
    return {
        "selected": [
            {
                **_creative_metadata(creative),
                "prompt_preview": _render_image_prompt(creative)[:900],
                "selected_for_api": True,
            }
            for creative in creatives
        ],
        "skipped": [
            {
                **_creative_metadata(creative),
                "selected_for_api": False,
                "reason": "Not selected because the max_static_images cap was reached; the cap does not request replacement creatives.",
            }
            for creative in collected_creatives
            if creative["creative_id"] not in selected_ids
        ],
        "source_creative_count": len(collected_creatives),
        "selected_creative_count": len(creatives),
        "max_images_requested": max_images,
        "max_images_policy": "cap_only_no_padding",
    }


def generate_ad_images(
    ads_creative_set: dict[str, Any],
    product_name: str,
    output_dir: str | Path = config.OUTPUT_DIR,
    api_key: str | None = None,
    model: str = config.OPENROUTER_IMAGE_MODEL,
    base_url: str = config.OPENROUTER_BASE_URL,
    product_reference_url: str = "",
    reference_image_urls: list[str] | None = None,
    enabled: bool = True,
    max_images: int = DEFAULT_MAX_IMAGES,
    image_size: str = "1K",
    include_meme_images: bool = False,
    enable_vision_quality_check: bool = False,
    vision_model: str | None = None,
    vision_retry_on_fail: bool = True,
) -> dict[str, Any]:
    key = api_key if api_key is not None else config.OPENROUTER_API_KEY
    extra_reference_image_urls = _unique_reference_urls(reference_image_urls or [], primary=product_reference_url)
    collected_creatives = _collect_image_creatives(
        ads_creative_set,
        product_reference_url,
        include_meme_style=include_meme_images,
    )
    creatives = _select_creatives_for_generation(
        collected_creatives,
        max_images=max_images,
    )
    for creative in creatives:
        creative["reference_image_urls"] = extra_reference_image_urls
    max_images_policy_note = (
        "max_static_images is a cap only: the image client selects up to that many planned creatives "
        "and never pads the count with duplicate or extra creative types. It is also a hard cap for image API "
        "requests, so vision QA retries are skipped once the cap is reached. When the cap is low, selection favors "
        "a diverse mix over two similar lifestyle renders."
    )
    selected_ids = {creative["creative_id"] for creative in creatives}
    skipped_creatives = [
        {
            **_creative_metadata(creative),
            "reason": "Not selected because the max_static_images cap was reached; the cap does not request replacement creatives.",
        }
        for creative in collected_creatives
        if creative["creative_id"] not in selected_ids
    ]
    if not include_meme_images:
        skipped_creatives.extend(_skipped_meme_creatives(ads_creative_set))
    generation_plan = [
        {
            **_creative_metadata(creative),
            "prompt_preview": _render_image_prompt(creative)[:900],
            "selected_for_api": True,
        }
        for creative in creatives
    ]
    prompt_respect_contract = (
        "Each image request is rendered from the selected creative's set_id, distinct marketing angle family/hook, funnel stage, "
        "layout, visual_prompt, post-production overlay metadata, and product reference. C2-C4 static images and C5 carousel "
        "cards are generated by default; meme-style ideas remain in ads_creative_set unless include_meme_images is enabled."
    )
    if not enabled:
        return {
            "image_generation_status": "skipped",
            "error": "Static image generation is disabled.",
            "failure_reason": "Static image generation was turned off for this request.",
            "next_step": "Enable static image generation in the UI when you want image files.",
            "model": model,
            "output_dir": str(output_dir),
            "image_assets": [],
            "attempted_count": 0,
            "selected_creative_count": len(creatives),
            "source_creative_count": len(collected_creatives),
            "generation_plan": generation_plan,
            "skipped_creatives": skipped_creatives,
            "prompt_respect_contract": prompt_respect_contract,
            "max_images_requested": max_images,
            "max_images_policy": "cap_only_no_padding",
            "max_images_policy_note": max_images_policy_note,
            "reference_image_urls": extra_reference_image_urls,
            "reference_image_count": len([item for item in [product_reference_url, *extra_reference_image_urls] if str(item or "").strip()]),
        }
    if not key:
        return {
            "image_generation_status": "skipped",
            "error": "OPENROUTER_API_KEY is missing; static image generation was skipped.",
            "failure_reason": "OpenRouter API key is missing, so static ad images were not generated.",
            "next_step": "Add OPENROUTER_API_KEY to .env or paste the key in the UI before generating.",
            "model": model,
            "output_dir": str(output_dir),
            "image_assets": [],
            "attempted_count": 0,
            "selected_creative_count": len(creatives),
            "source_creative_count": len(collected_creatives),
            "generation_plan": generation_plan,
            "skipped_creatives": skipped_creatives,
            "prompt_respect_contract": prompt_respect_contract,
            "max_images_requested": max_images,
            "max_images_policy": "cap_only_no_padding",
            "max_images_policy_note": max_images_policy_note,
            "reference_image_urls": extra_reference_image_urls,
            "reference_image_count": len([item for item in [product_reference_url, *extra_reference_image_urls] if str(item or "").strip()]),
        }
    if not creatives:
        return {
            "image_generation_status": "skipped",
            "error": "No static ad creatives were available for image generation.",
            "failure_reason": "The ads creative set did not contain static, carousel, or meme prompts to render.",
            "next_step": "Check the Ads Creative Set section and regenerate with product details.",
            "model": model,
            "output_dir": str(output_dir),
            "image_assets": [],
            "attempted_count": 0,
            "selected_creative_count": len(creatives),
            "source_creative_count": len(collected_creatives),
            "generation_plan": generation_plan,
            "skipped_creatives": skipped_creatives,
            "prompt_respect_contract": prompt_respect_contract,
            "max_images_requested": max_images,
            "max_images_policy": "cap_only_no_padding",
            "max_images_policy_note": max_images_policy_note,
            "reference_image_urls": extra_reference_image_urls,
            "reference_image_count": len([item for item in [product_reference_url, *extra_reference_image_urls] if str(item or "").strip()]),
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
    }
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    trace_id = f"image_{int(time.time() * 1000)}"
    assets: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    usage_records: list[dict[str, Any]] = []
    duplicate_skips: list[dict[str, Any]] = []
    vision_quality_checks: list[dict[str, Any]] = []
    vision_quality_rejections: list[dict[str, Any]] = []
    assets_by_fingerprint: dict[str, list[dict[str, Any]]] = {}
    failures_by_fingerprint: dict[str, dict[str, Any]] = {}
    api_request_count = 0
    regeneration_attempts = 0

    for creative in creatives:
        prompt = _render_image_prompt(creative)
        effective_product_reference = creative.get("product_reference_url") or product_reference_url
        fingerprint = _request_fingerprint(
            model=model,
            prompt=prompt,
            aspect_ratio=creative["aspect_ratio"],
            image_size=image_size,
            product_reference_url=effective_product_reference,
            reference_image_urls=extra_reference_image_urls,
        )
        if fingerprint in assets_by_fingerprint:
            source_asset = assets_by_fingerprint[fingerprint][0]
            duplicate_skips.append(
                {
                    "creative_id": creative["creative_id"],
                    "asset_type": creative["asset_type"],
                    "reason": "Duplicate image prompt; skipped extra API call and did not add a duplicate gallery asset.",
                    "duplicate_prompt_skip_reason": "Duplicate image prompt; skipped extra API call and did not add a duplicate gallery asset.",
                    "duplicate_of_creative_id": source_asset.get("creative_id"),
                    "would_reuse_image_path": source_asset.get("image_path"),
                    "request_fingerprint": fingerprint,
                    "prompt": prompt,
                }
            )
            _write_trace(
                output_dir,
                {
                    "trace_id": trace_id,
                    "event": "image_duplicate_reused",
                    "creative_id": creative["creative_id"],
                    "duplicate_of_creative_id": source_asset.get("creative_id"),
                    "request_fingerprint": fingerprint,
                },
            )
            continue
        if fingerprint in failures_by_fingerprint:
            original_failure = failures_by_fingerprint[fingerprint]
            duplicate_skips.append(
                {
                    "creative_id": creative["creative_id"],
                    "asset_type": creative["asset_type"],
                    "reason": "Duplicate image prompt skipped because the original matching API request already failed.",
                    "duplicate_prompt_skip_reason": "Duplicate image prompt skipped because the original matching API request already failed.",
                    "duplicate_of_creative_id": original_failure.get("creative_id"),
                    "failure_reason": original_failure.get("failure_reason"),
                    "request_fingerprint": fingerprint,
                }
            )
            _write_trace(
                output_dir,
                {
                    "trace_id": trace_id,
                    "event": "image_duplicate_skipped_after_failure",
                    "creative_id": creative["creative_id"],
                    "duplicate_of_creative_id": original_failure.get("creative_id"),
                    "request_fingerprint": fingerprint,
                },
            )
            continue
        payload = _request_payload(
            model=model,
            prompt=prompt,
            aspect_ratio=creative["aspect_ratio"],
            image_size=image_size,
            product_reference_url=effective_product_reference,
            reference_image_urls=extra_reference_image_urls,
        )
        _write_trace(
            output_dir,
            {
                "trace_id": trace_id,
                "event": "image_request",
                "creative_id": creative["creative_id"],
                "asset_type": creative["asset_type"],
                "model": model,
                "aspect_ratio": creative["aspect_ratio"],
                "image_size": image_size,
                "has_product_reference_url": bool(creative.get("product_reference_url") or product_reference_url),
                "reference_image_count": len([item for item in [effective_product_reference, *extra_reference_image_urls] if str(item or "").strip()]),
                "payload_keys": sorted(payload.keys()),
                "request_fingerprint": fingerprint,
                "prompt": prompt,
                "creative_metadata": _creative_metadata(creative),
            },
        )
        try:
            api_request_count += 1
            response = requests.post(endpoint, headers=headers, json=payload, timeout=240)
            response.raise_for_status()
            result = response.json()
            image_urls = _extract_image_urls(result)[:1]
            if not image_urls:
                raise ValueError("OpenRouter response did not include generated images.")
            usage_records.append(
                {
                    "creative_id": creative["creative_id"],
                    "asset_type": creative["asset_type"],
                    "model": model,
                    "image_count": len(image_urls),
                    "generation_id": result.get("id"),
                    "usage": result.get("usage"),
                }
            )
            new_assets: list[dict[str, Any]] = []
            for image_index, image_url in enumerate(image_urls, start=1):
                suffix = _suffix_for_image_url(image_url)
                filename = (
                    f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}_"
                    f"{safe_slug(creative['creative_id'])}_{image_index}{suffix}"
                )
                image_path = target_dir / filename
                image_path.write_bytes(_image_bytes(image_url, headers, base_url))
                asset = {
                    **_creative_metadata(creative),
                    "creative_id": creative["creative_id"],
                    "asset_type": creative["asset_type"],
                    "image_path": str(image_path),
                    "image_url": _output_url(image_path),
                    "model": model,
                    "aspect_ratio": creative["aspect_ratio"],
                    "image_size": image_size,
                    "overlay_text": creative.get("overlay_text"),
                    "prompt": payload["messages"][0]["content"][0]["text"],
                    "generation_reused": False,
                    "request_fingerprint": fingerprint,
                    "reference_image_urls": extra_reference_image_urls,
                }
                assets.append(asset)
                new_assets.append(asset)
            quality_result = _score_first_asset_if_enabled(
                new_assets=new_assets,
                product_reference_url=effective_product_reference,
                api_key=key,
                vision_model=vision_model,
                base_url=base_url,
                enabled=enable_vision_quality_check,
            )
            if quality_result:
                vision_quality_checks.append(
                    {
                        "creative_id": creative["creative_id"],
                        "attempt": "initial",
                        "result": quality_result,
                    }
                )
                for asset in new_assets:
                    asset["vision_quality"] = quality_result
                can_retry_within_cap = api_request_count < max(0, int(max_images or 0))
                if quality_result.get("regeneration_required") and vision_retry_on_fail and can_retry_within_cap:
                    regeneration_attempts += 1
                    for asset in new_assets:
                        asset["quality_rejected"] = True
                    vision_quality_rejections.extend(
                        {
                            **_creative_metadata(creative),
                            "image_path": asset.get("image_path"),
                            "image_url": asset.get("image_url"),
                            "vision_quality": quality_result,
                            "reason": "Vision quality check requested regeneration before accepting this asset.",
                        }
                        for asset in new_assets
                    )
                    assets = [asset for asset in assets if asset not in new_assets]
                    retry_prompt = _retry_prompt(payload["messages"][0]["content"][0]["text"], quality_result)
                    retry_payload = _request_payload(
                        model=model,
                        prompt=retry_prompt,
                        aspect_ratio=creative["aspect_ratio"],
                        image_size=image_size,
                        product_reference_url=effective_product_reference,
                        reference_image_urls=extra_reference_image_urls,
                    )
                    _write_trace(
                        output_dir,
                        {
                            "trace_id": trace_id,
                            "event": "image_retry_after_vision_quality_fail",
                            "creative_id": creative["creative_id"],
                            "request_fingerprint": fingerprint,
                            "vision_quality": quality_result,
                        },
                    )
                    api_request_count += 1
                    retry_response = requests.post(endpoint, headers=headers, json=retry_payload, timeout=240)
                    retry_response.raise_for_status()
                    retry_result = retry_response.json()
                    retry_image_urls = _extract_image_urls(retry_result)[:1]
                    if not retry_image_urls:
                        raise ValueError("OpenRouter retry response did not include generated images.")
                    usage_records.append(
                        {
                            "creative_id": creative["creative_id"],
                            "asset_type": creative["asset_type"],
                            "model": model,
                            "image_count": len(retry_image_urls),
                            "generation_id": retry_result.get("id"),
                            "usage": retry_result.get("usage"),
                            "retry_after_vision_quality_fail": True,
                        }
                    )
                    retry_assets: list[dict[str, Any]] = []
                    for image_index, image_url in enumerate(retry_image_urls, start=1):
                        suffix = _suffix_for_image_url(image_url)
                        filename = (
                            f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}_"
                            f"{safe_slug(creative['creative_id'])}_retry_{image_index}{suffix}"
                        )
                        image_path = target_dir / filename
                        image_path.write_bytes(_image_bytes(image_url, headers, base_url))
                        retry_asset = {
                            **_creative_metadata(creative),
                            "creative_id": creative["creative_id"],
                            "asset_type": creative["asset_type"],
                            "image_path": str(image_path),
                            "image_url": _output_url(image_path),
                            "model": model,
                            "aspect_ratio": creative["aspect_ratio"],
                            "image_size": image_size,
                            "overlay_text": creative.get("overlay_text"),
                            "prompt": retry_payload["messages"][0]["content"][0]["text"],
                            "generation_reused": False,
                            "request_fingerprint": fingerprint,
                            "reference_image_urls": extra_reference_image_urls,
                            "regenerated_after_vision_quality_fail": True,
                        }
                        assets.append(retry_asset)
                        retry_assets.append(retry_asset)
                    retry_quality = _score_first_asset_if_enabled(
                        new_assets=retry_assets,
                        product_reference_url=effective_product_reference,
                        api_key=key,
                        vision_model=vision_model,
                        base_url=base_url,
                        enabled=enable_vision_quality_check,
                    )
                    if retry_quality:
                        vision_quality_checks.append(
                            {
                                "creative_id": creative["creative_id"],
                                "attempt": "retry_1",
                                "result": retry_quality,
                            }
                        )
                        for asset in retry_assets:
                            asset["vision_quality"] = retry_quality
                    new_assets = retry_assets
                elif quality_result.get("regeneration_required") and vision_retry_on_fail and not can_retry_within_cap:
                    _write_trace(
                        output_dir,
                        {
                            "trace_id": trace_id,
                            "event": "image_retry_skipped_by_max_images_cap",
                            "creative_id": creative["creative_id"],
                            "request_fingerprint": fingerprint,
                            "api_request_count": api_request_count,
                            "max_images_requested": max_images,
                            "vision_quality": quality_result,
                        },
                    )
            assets_by_fingerprint[fingerprint] = new_assets
            _write_trace(
                output_dir,
                {
                    "trace_id": trace_id,
                    "event": "image_response",
                    "creative_id": creative["creative_id"],
                    "status_code": response.status_code,
                    "image_count": len(image_urls),
                    "request_fingerprint": fingerprint,
                },
            )
        except Exception as exc:
            error = _format_request_error(exc)
            failures.append(
                {
                    "creative_id": creative["creative_id"],
                    "asset_type": creative["asset_type"],
                    "error": error,
                    "failure_reason": _human_failure_reason(error),
                    "next_step": _next_step_for_error(error),
                    "request_fingerprint": fingerprint,
                    "prompt": prompt,
                }
            )
            failures_by_fingerprint[fingerprint] = failures[-1]
            _write_trace(
                output_dir,
                {
                    "trace_id": trace_id,
                    "event": "image_exception",
                    "creative_id": creative["creative_id"],
                    "error": error,
                    "request_fingerprint": fingerprint,
                },
            )

    status = "completed" if assets and not failures else "partial" if assets else "failed"
    first_failure = failures[0] if failures else {}
    reused_count = len([asset for asset in assets if asset.get("generation_reused")])
    return {
        "image_generation_status": status,
        "error": first_failure.get("error"),
        "failure_reason": None if status == "completed" else first_failure.get("failure_reason"),
        "next_step": None if status == "completed" else first_failure.get("next_step"),
        "model": model,
        "output_dir": str(output_dir),
        "image_assets": assets,
        "failures": failures,
        "duplicate_skips": duplicate_skips,
        "skipped_creatives": skipped_creatives,
        "generation_plan": generation_plan,
        "prompt_respect_contract": prompt_respect_contract,
        "max_images_requested": max_images,
        "max_images_policy": "cap_only_no_padding",
        "max_images_policy_note": max_images_policy_note,
        "reference_image_urls": extra_reference_image_urls,
        "reference_image_count": len([item for item in [product_reference_url, *extra_reference_image_urls] if str(item or "").strip()]),
        "source_creative_count": len(collected_creatives),
        "usage_records": usage_records,
        "attempted_count": len(creatives),
        "selected_creative_count": len(creatives),
        "api_request_count": api_request_count,
        "generated_count": len(assets) - reused_count,
        "asset_count": len(assets),
        "reused_count": reused_count,
        "vision_quality_status": _vision_quality_status(
            enable_vision_quality_check,
            vision_quality_checks,
            vision_quality_rejections,
        ),
        "vision_model": vision_model or config.OPENROUTER_VISION_MODEL,
        "vision_quality_checks": vision_quality_checks,
        "vision_quality_rejections": vision_quality_rejections,
        "regeneration_attempts": regeneration_attempts,
    }


def _collect_image_creatives(
    ads_creative_set: dict[str, Any],
    product_reference_url: str,
    include_meme_style: bool = False,
) -> list[dict[str, Any]]:
    creatives: list[dict[str, Any]] = []
    material_fidelity_lock = str(ads_creative_set.get("static_product_material_fidelity_lock") or "").strip()
    visual_classifier_directive = str(ads_creative_set.get("static_visual_classifier_directive") or "").strip()
    for item in ads_creative_set.get("static_image_ads") or []:
        if not isinstance(item, dict):
            continue
        creatives.append(
            {
                "creative_id": item.get("creative_id") or f"static_{len(creatives) + 1}",
                "asset_type": "static_image",
                "set_id": item.get("set_id"),
                "creative_type": item.get("creative_type"),
                "angle": _effective_creative_angle(item),
                "slot_angle": item.get("angle"),
                "angle_family": item.get("angle_family"),
                "angle_multiplier_angle": item.get("angle_multiplier_angle"),
                "angle_multiplier_hook": item.get("angle_multiplier_hook"),
                "angle_selection_reason": item.get("angle_selection_reason"),
                "creative_test_hypothesis": item.get("creative_test_hypothesis"),
                "variation_rule": item.get("variation_rule"),
                "angle_diversity_contract": item.get("angle_diversity_contract"),
                "static_creative_quality_contract": item.get("static_creative_quality_contract"),
                "static_marketing_job": item.get("static_marketing_job"),
                "scroll_stop_mechanism": item.get("scroll_stop_mechanism"),
                "buyer_psychology_trigger": item.get("buyer_psychology_trigger"),
                "feed_read": item.get("feed_read"),
                "static_differentiation_rule": item.get("static_differentiation_rule"),
                "quality_contract_status": item.get("quality_contract_status"),
                "display_hook": _display_hook(item),
                "funnel_stage": item.get("funnel_stage"),
                "budget_share_percent": item.get("budget_share_percent"),
                "format": item.get("format", "Static image"),
                "layout": item.get("layout"),
                "concept": item.get("concept"),
                "why_this_angle": item.get("why_this_angle"),
                "visual_prompt": item.get("visual_prompt"),
                "overlay_text": item.get("overlay_text"),
                "headline": item.get("headline"),
                "cta": None,
                "primary_text": item.get("primary_text"),
                "aspect_ratio": item.get("aspect_ratio") or "1:1",
                "product_reference_url": product_reference_url,
                "product_material_fidelity_lock": material_fidelity_lock,
                "static_visual_classifier_directive": item.get("static_visual_classifier_directive") or visual_classifier_directive,
            }
        )
    carousel = ads_creative_set.get("carousel_ad") or {}
    if isinstance(carousel, dict):
        for card in carousel.get("cards") or []:
            if not isinstance(card, dict):
                continue
            number = card.get("card_number") or len(creatives) + 1
            creatives.append(
                {
                    "creative_id": f"{carousel.get('set_id') or 'carousel'}_card_{number}",
                    "asset_type": "carousel_card",
                    "set_id": carousel.get("set_id"),
                    "creative_type": carousel.get("creative_type"),
                    "angle": _effective_creative_angle(card, fallback=carousel),
                    "slot_angle": carousel.get("angle"),
                    "angle_family": card.get("angle_family") or carousel.get("angle_family"),
                    "angle_multiplier_angle": card.get("angle_multiplier_angle") or carousel.get("angle_multiplier_angle"),
                    "angle_multiplier_hook": card.get("angle_multiplier_hook") or carousel.get("angle_multiplier_hook"),
                    "angle_selection_reason": carousel.get("angle_selection_reason"),
                    "creative_test_hypothesis": card.get("creative_test_hypothesis") or carousel.get("creative_test_hypothesis"),
                    "variation_rule": card.get("variation_rule"),
                    "angle_diversity_contract": card.get("angle_diversity_contract"),
                    "static_creative_quality_contract": card.get("static_creative_quality_contract") or carousel.get("static_creative_quality_contract"),
                    "static_marketing_job": card.get("static_marketing_job") or carousel.get("static_marketing_job"),
                    "scroll_stop_mechanism": card.get("scroll_stop_mechanism") or carousel.get("scroll_stop_mechanism"),
                    "buyer_psychology_trigger": card.get("buyer_psychology_trigger") or carousel.get("buyer_psychology_trigger"),
                    "feed_read": card.get("feed_read") or carousel.get("feed_read"),
                    "static_differentiation_rule": card.get("static_differentiation_rule") or carousel.get("static_differentiation_rule"),
                    "quality_contract_status": card.get("quality_contract_status") or carousel.get("quality_contract_status"),
                    "display_hook": _display_hook(card, fallback=carousel),
                    "funnel_stage": carousel.get("funnel_stage"),
                    "budget_share_percent": carousel.get("budget_share_percent"),
                    "format": "Carousel card",
                    "card_number": number,
                    "layout": card.get("role"),
                    "visual_prompt": card.get("visual_prompt"),
                    "overlay_text": card.get("overlay_text"),
                    "headline": card.get("overlay_text"),
                    "cta": None,
                    "primary_text": carousel.get("primary_text"),
                    "aspect_ratio": carousel.get("aspect_ratio") or "1:1",
                    "product_reference_url": product_reference_url,
                    "product_material_fidelity_lock": material_fidelity_lock,
                    "static_visual_classifier_directive": card.get("static_visual_classifier_directive") or visual_classifier_directive,
                }
            )
    if include_meme_style:
        for item in ads_creative_set.get("meme_style_creatives") or []:
            if not isinstance(item, dict):
                continue
            creatives.append(
                {
                    "creative_id": item.get("creative_id") or f"meme_{len(creatives) + 1}",
                    "asset_type": "meme_style_static",
                    "set_id": item.get("set_id"),
                    "creative_type": item.get("creative_type"),
                    "angle": item.get("angle"),
                    "funnel_stage": item.get("funnel_stage"),
                    "budget_share_percent": item.get("budget_share_percent"),
                    "format": item.get("format", "Meme-style static"),
                    "layout": item.get("layout"),
                    "visual_prompt": item.get("visual_prompt"),
                    "overlay_text": item.get("copy"),
                    "headline": item.get("copy"),
                    "cta": None,
                    "primary_text": item.get("copy"),
                    "aspect_ratio": "1:1",
                    "product_reference_url": product_reference_url,
                    "product_material_fidelity_lock": material_fidelity_lock,
                    "static_visual_classifier_directive": item.get("static_visual_classifier_directive") or visual_classifier_directive,
                }
            )
    return creatives


def _skipped_meme_creatives(ads_creative_set: dict[str, Any]) -> list[dict[str, Any]]:
    skipped = []
    for item in ads_creative_set.get("meme_style_creatives") or []:
        if not isinstance(item, dict):
            continue
        skipped.append(
            {
                "creative_id": item.get("creative_id") or "meme_style_static",
                "asset_type": "meme_style_static",
                "format": item.get("format", "Meme-style static"),
                "layout": item.get("layout"),
                "reason": "Meme-style creative is kept as a copy/concept suggestion and is not auto-rendered in the C1-C5 media plan.",
            }
        )
    return skipped


def _effective_creative_angle(source: dict[str, Any], fallback: dict[str, Any] | None = None) -> str:
    data = source if isinstance(source, dict) else {}
    fallback_data = fallback if isinstance(fallback, dict) else {}
    family = str(data.get("angle_family") or fallback_data.get("angle_family") or "").strip()
    multiplier_angle = str(data.get("angle_multiplier_angle") or fallback_data.get("angle_multiplier_angle") or "").strip()
    hook = str(data.get("angle_multiplier_hook") or fallback_data.get("angle_multiplier_hook") or "").strip()
    legacy = str(data.get("angle") or fallback_data.get("angle") or "").strip()
    if multiplier_angle and family and not multiplier_angle.lower().startswith(family.lower()):
        return f"{family} - {_short_angle_text(multiplier_angle)}"
    if multiplier_angle:
        return _short_angle_text(multiplier_angle)
    if family and hook:
        return f"{family} - {_short_angle_text(hook)}"
    if family:
        return family
    return legacy


def _display_hook(source: dict[str, Any], fallback: dict[str, Any] | None = None) -> str:
    data = source if isinstance(source, dict) else {}
    fallback_data = fallback if isinstance(fallback, dict) else {}
    for value in [
        data.get("overlay_text"),
        data.get("headline"),
        fallback_data.get("overlay_text"),
        fallback_data.get("headline"),
        data.get("angle_multiplier_hook"),
        fallback_data.get("angle_multiplier_hook"),
    ]:
        hook = _short_angle_text(value, 56)
        if hook and not _looks_like_internal_hook(hook):
            return hook
    return ""


def _looks_like_internal_hook(value: str) -> bool:
    text = str(value or "").strip().lower()
    internal_terms = [
        "product_hero",
        "use_context",
        "detail_proof",
        "buying_guide",
        "creative angle",
        "angle family",
        "desire angle",
        "identity angle",
        "proof angle",
        "pain angle",
        "urgency angle",
        "contrarian angle",
    ]
    return text in {"c2", "c3", "c4", "c5"} or any(term in text for term in internal_terms)


def _short_angle_text(value: Any, limit: int = 72) -> str:
    text = " ".join(str(value or "").replace("\n", " ").replace("\r", " ").split())
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[: max(0, limit - 3)].rstrip()}..."


def _static_quality_contract_prompt_line(creative: dict[str, Any]) -> str:
    contract = creative.get("static_creative_quality_contract")
    contract_data = contract if isinstance(contract, dict) else {}
    values = {
        "marketing job": creative.get("static_marketing_job") or contract_data.get("marketing_job"),
        "scroll stop": creative.get("scroll_stop_mechanism") or contract_data.get("scroll_stop_mechanism"),
        "psychology trigger": creative.get("buyer_psychology_trigger") or contract_data.get("buyer_psychology_trigger"),
        "feed read": creative.get("feed_read") or contract_data.get("feed_read"),
        "differentiation": creative.get("static_differentiation_rule") or contract_data.get("differentiation_rule"),
    }
    parts = [
        f"{label}={_short_angle_text(value, 180)}"
        for label, value in values.items()
        if str(value or "").strip()
    ]
    if not parts:
        return ""
    return (
        "Static creative quality contract, internal direction only: "
        + "; ".join(parts)
        + ". Use it to choose scene, crop, proof focus, and composition. Never render these words, set IDs, labels, or psychology terms as visible image text."
    )


def _static_quality_contract_summary(creative: dict[str, Any]) -> str:
    line = _static_quality_contract_prompt_line(creative)
    if not line:
        return ""
    return _short_angle_text(
        line.replace("Static creative quality contract, internal direction only: ", ""),
        360,
    )


def _creative_metadata(creative: dict[str, Any]) -> dict[str, Any]:
    return {
        "creative_id": creative.get("creative_id"),
        "asset_type": creative.get("asset_type"),
        "set_id": creative.get("set_id"),
        "creative_type": creative.get("creative_type"),
        "angle": creative.get("angle"),
        "slot_angle": creative.get("slot_angle"),
        "angle_family": creative.get("angle_family"),
        "angle_multiplier_angle": creative.get("angle_multiplier_angle"),
        "angle_multiplier_hook": creative.get("angle_multiplier_hook"),
        "angle_selection_reason": creative.get("angle_selection_reason"),
        "creative_test_hypothesis": creative.get("creative_test_hypothesis"),
        "variation_rule": creative.get("variation_rule"),
        "angle_diversity_contract": creative.get("angle_diversity_contract"),
        "static_creative_quality_contract": creative.get("static_creative_quality_contract"),
        "static_marketing_job": creative.get("static_marketing_job"),
        "scroll_stop_mechanism": creative.get("scroll_stop_mechanism"),
        "buyer_psychology_trigger": creative.get("buyer_psychology_trigger"),
        "feed_read": creative.get("feed_read"),
        "static_differentiation_rule": creative.get("static_differentiation_rule"),
        "quality_contract_status": creative.get("quality_contract_status"),
        "display_hook": creative.get("display_hook"),
        "funnel_stage": creative.get("funnel_stage"),
        "budget_share_percent": creative.get("budget_share_percent"),
        "format": creative.get("format"),
        "layout": creative.get("layout"),
        "concept": creative.get("concept"),
        "why_this_angle": creative.get("why_this_angle"),
        "card_number": creative.get("card_number"),
        "aspect_ratio": creative.get("aspect_ratio"),
        "overlay_text": creative.get("overlay_text"),
        "visual_prompt": creative.get("visual_prompt"),
        "static_visual_classifier_directive": creative.get("static_visual_classifier_directive"),
        "visual_diversity_score": _visual_diversity_score(creative),
    }


def _select_creatives_for_generation(
    creatives: list[dict[str, Any]],
    max_images: int,
) -> list[dict[str, Any]]:
    limit = max(0, max_images)
    if not creatives or limit == 0:
        return []
    if all(not creative.get("set_id") for creative in creatives):
        return creatives[:limit]
    selected = sorted(
        enumerate(creatives),
        key=lambda item: (_selection_priority(item[1]), item[0]),
    )[:limit]
    return [
        creative
        for _, creative in sorted(
            selected,
            key=lambda item: (_display_order(item[1]), item[0]),
        )
    ]


def _selection_priority(creative: dict[str, Any]) -> int:
    set_id = str(creative.get("set_id") or "")
    angle = str(creative.get("angle") or "").upper()
    asset_type = str(creative.get("asset_type") or "")
    if set_id == "C2" or angle in {"PAIN", "PRODUCT_HERO"}:
        return 10
    if set_id == "C6" or "objection" in str(creative.get("creative_type") or "").lower():
        return 15
    if set_id == "C4" or "detail" in str(creative.get("creative_type") or "").lower():
        return 20
    if set_id == "C3" or angle in {"IDENTITY", "USE_CONTEXT"}:
        return 30
    if set_id == "C7" or "anti-hype" in str(creative.get("creative_type") or "").lower():
        return 35
    if set_id == "C5" or asset_type == "carousel_card":
        return 40 + int(creative.get("card_number") or 0)
    return 100


def _display_order(creative: dict[str, Any]) -> int:
    set_order = {"C2": 20, "C6": 25, "C3": 30, "C4": 40, "C7": 45, "C5": 50}
    set_id = str(creative.get("set_id") or "")
    return set_order.get(set_id, 100) + int(creative.get("card_number") or 0)


def _visual_diversity_score(creative: dict[str, Any]) -> int:
    text = " ".join(
        str(creative.get(key) or "")
        for key in ["set_id", "angle", "layout", "concept", "visual_prompt", "funnel_stage"]
    ).lower()
    markers = [
        "adult person",
        "worn",
        "carried",
        "held",
        "macro",
        "detail",
        "entryway",
        "doorway",
        "outfit",
        "office",
        "commute",
        "identity",
        "pain",
        "demonstration",
        "objection",
        "anti-hype",
        "contrarian",
        "scale",
        "different",
        "distinct",
    ]
    score = 45 + min(45, 5 * sum(1 for marker in markers if marker in text))
    if "same background" in text or "reuse" in text:
        score -= 15
    return max(0, min(100, score))


def _render_image_prompt(creative: dict[str, Any]) -> str:
    has_primary_text = bool(str(creative.get("primary_text") or "").strip())
    product_reference = creative.get("product_reference_url") or ""
    budget = creative.get("budget_share_percent")
    quality_contract_line = _static_quality_contract_prompt_line(creative)
    lines = [
        "Create one finished paid social static ad image.",
        "Generate exactly one image for this one creative; do not create a collage, contact sheet, multi-panel set, or multiple variants in one image.",
        "Internal creative labels, set IDs, angle names, layout roles, and workflow terms are metadata only and must never appear as visible text in the image.",
        f"Asset type: {creative.get('asset_type')}.",
        f"Format: {creative.get('format')}.",
        f"Layout: {creative.get('layout')}.",
        f"Visual direction: {creative.get('visual_prompt')}.",
        f"Aspect ratio: {creative.get('aspect_ratio')}.",
        f"Variation contract: {_static_variation_contract(creative)}",
        f"Category fidelity rule: {_category_fidelity_rule(creative)}",
        "Static creative v2 requirement: C2 must read as a product-first commerce hero, C3 as real use context, C4 as visible proof detail, C6 as objection check, C7 as anti-hype check, and C5 as a buying-guide card. Keep each role instantly readable in one feed glance.",
        "Human/product context requirement: follow the creative role. Include an adult person wearing, carrying, holding, trying on, or standing directly with the product whenever physically plausible for this product category. For bags, show the bag on shoulder, in hand, or against an outfit; for shoes or apparel, show the product worn. Cropped face, turned-away face, hands-only, torso-only, or off-frame head is acceptable. Use adults only; no children, public figures, celebrity likeness, or stock-photo glamour posing. Keep the product as the hero and preserve exact product fidelity.",
        "Hand realism requirement: if hands are visible, use relaxed adult hands with natural five-finger anatomy, stable grip, plausible wrist angle, and one object per action. Avoid extra fingers, missing fingers, fused fingers, warped knuckles, elongated fingers, melting hands, or impossible hand poses; crop hands at the frame edge if uncertain.",
        "Aim for a trustworthy low-polish ecommerce proof image: natural lighting, real materials, mid-saturation color, readable product framing, no generated typography, no clutter, no platform UI mockups, no fake app chrome, no watermarks, no generic stock-photo feel, scroll-stopping but not overproduced.",
        STATIC_DROPSHIPPING_REALISM_GUARD,
        "Realism requirement: make the image look like a real photograph from a real camera, with physically plausible perspective, scale, shadows, highlights, lens behaviour, surface texture, and environmental context. Avoid AI-rendered gloss, invented plastic-looking surfaces on non-plastic products, over-smoothed surfaces, surreal composition, impossible reflections, duplicated objects, distorted product geometry, synthetic studio render feel, and generic stock-photo staging.",
        "Creative-set diversity rule: do not reuse the same background setup, room, prop arrangement, camera distance, or lighting mood from other C2/C3/C4/C5/C6/C7 assets unless the visual direction explicitly asks for reference-scene preservation. C2 should feel like a product-first hero frame, C3 like real use context, C4 like a tight proof detail, C6 like a practical buyer doubt, C7 like a low-polish anti-ad check, and C5 like a clear buyer-guide sequence.",
        "Static no-text rule: render no generated words, typography, captions, hook text, overlay text, labels, stickers, badges, callouts, title cards, buttons, product annotations, or random letters inside the image. Any overlay_text/headline/copy fields are post-production metadata only and must not be drawn by the image model.",
        "Do not render labels such as C2, C3, C4, C5, C6, C7, PRODUCT_HERO, USE_CONTEXT, DETAIL_PROOF, BUYING_GUIDE, PAIN_POINT, CONTRARIAN_CHECK, hero view, outfit context, proof detail, final check, creative angle, static image, carousel, or buying guide.",
        "Do not render buttons, CTA pills, clickable controls, tap/click instructions, cursors, destination URLs, platform UI, or app-like interface elements; the advertising platform supplies those controls outside the image.",
        "Do not invent reviews, ratings, star counts, discounts, scarcity claims, certifications, medical effects, brand badges that are not in the product reference, or platform logos.",
        prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK,
        prompt_defaults.STATIC_IMAGE_MATERIAL_FIDELITY_LOCK,
        _product_material_fidelity_line(creative),
        "Preserve the product from the reference exactly: product not modified, not restyled, not recolored, not rebranded, not resized, not rematerialized, not substituted; exact shape, color, material, finish, texture, proportions, physical size, scale, and visible markings.",
    ]
    if creative.get("set_id"):
        lines.insert(1, f"Internal set ID, metadata only, never render as text: {creative.get('set_id')}.")
    if creative.get("angle"):
        lines.insert(2, f"Internal angle, metadata only, never render as text: {creative.get('angle')}.")
    if creative.get("funnel_stage"):
        lines.insert(3, f"Internal funnel stage, metadata only, never render as text: {creative.get('funnel_stage')}.")
    if budget is not None:
        lines.insert(4, f"Internal budget share context, metadata only, never render as text: {budget}%.")
    if creative.get("concept"):
        lines.insert(5, f"Creative concept: {creative.get('concept')}.")
    if creative.get("why_this_angle"):
        lines.insert(6, f"Reason this angle exists: {creative.get('why_this_angle')}.")
    if creative.get("angle_family") or creative.get("angle_multiplier_hook"):
        lines.insert(
            7,
            (
                "Distinct marketing angle, metadata only, never render as visible text: "
                f"family={creative.get('angle_family') or 'unspecified'}; "
                f"angle={creative.get('angle_multiplier_angle') or creative.get('angle') or 'unspecified'}; "
                f"hook intent={creative.get('angle_multiplier_hook') or 'unspecified'}."
            ),
        )
    if creative.get("creative_test_hypothesis"):
        lines.insert(8, f"Creative test hypothesis, metadata only: {creative.get('creative_test_hypothesis')}.")
    if creative.get("variation_rule"):
        lines.insert(9, f"Variation rule for this image: {creative.get('variation_rule')}.")
    if creative.get("static_visual_classifier_directive"):
        lines.insert(
            10,
            (
                "Visual classifier static directive: "
                f"{creative.get('static_visual_classifier_directive')} "
                "Use this for shot choice, product proof, and QA expectations only; never render classifier words as visible image text."
            ),
        )
    if creative.get("angle_diversity_contract"):
        lines.insert(
            11,
            (
                f"Angle diversity contract: {creative.get('angle_diversity_contract')} "
                "Do not turn this into the same buyer motivation or same visual proof as the other static assets."
            ),
        )
    if quality_contract_line:
        lines.insert(12, quality_contract_line)
    if product_reference:
        lines.append("Use the supplied product reference image as the source of truth for product appearance.")
    if creative.get("reference_image_urls"):
        lines.append(
            "Additional static-only product reference images are color/variant references for the same product. "
            "Use them to understand available colours and finishes, but do not combine multiple colourways into one impossible product."
        )
    if has_primary_text:
        lines.append("Primary_text/copy exists for the later ad post only; do not render any of that copy as visible text in the generated image.")
    return _compress_image_prompt(lines)


def _product_material_fidelity_line(creative: dict[str, Any]) -> str:
    specific_lock = " ".join(str(creative.get("product_material_fidelity_lock") or "").split())
    if specific_lock:
        return f"Product-specific material/opacity lock: {specific_lock}"
    return (
        "Product-specific material/opacity lock: copy the product material, finish, shine, texture, thickness, "
        "and opacity/transparency from the supplied product reference exactly; do not make the item transparent, "
        "opaque, glass-like, plastic-looking, metallic, ceramic, leather, fabric, matte, or glossy unless the reference clearly supports it."
    )


def _compress_image_prompt(lines: list[str], max_chars: int = IMAGE_PROMPT_MAX_CHARS) -> str:
    text = "\n".join(lines)
    if len(text) <= max_chars:
        return text
    note = (
        "Prompt compression applied: product fidelity, human realism, category rules, no-generated-text contract, "
        "and safety rules are preserved; lower-priority descriptive copy was shortened."
    )

    compressed: list[str] = []
    for line in lines:
        if line.startswith("Visual direction: "):
            compressed.append(_clip_line(line, 1800))
        elif line.startswith("Layout: "):
            compressed.append(_clip_line(line, 600))
        elif line.startswith("Creative concept: ") or line.startswith("Reason this angle exists: "):
            compressed.append(_clip_line(line, 500))
        elif line.startswith("Static creative quality contract"):
            compressed.append(_clip_line(line, 900))
        elif line.startswith("Use this copy only as context"):
            compressed.append(_clip_line(line, 500))
        else:
            compressed.append(line)

    text = "\n".join([note, *compressed])
    if len(text) <= max_chars:
        return text

    high_priority = []
    medium_priority = []
    low_priority = []
    for line in compressed:
        target = (
            high_priority
            if _is_high_priority_image_prompt_line(line)
            else medium_priority
            if line.startswith(
                (
                    "Visual direction:",
                    "Layout:",
                    "Creative concept:",
                    "Reason this angle exists:",
                    "Distinct marketing angle",
                    "Creative test hypothesis",
                    "Variation rule for this image",
                    "Visual classifier static directive",
                    "Angle diversity contract",
                    "Static creative quality contract",
                )
            )
            else low_priority
        )
        target.append(line)

    result: list[str] = [note]
    for line in [*high_priority, *medium_priority, *low_priority]:
        candidate = "\n".join([*result, line])
        if len(candidate) <= max_chars:
            result.append(line)
    return "\n".join(result)[:max_chars]


def _clip_line(line: str, limit: int) -> str:
    text = " ".join(str(line or "").split())
    return text if len(text) <= limit else f"{text[: max(0, limit - 3)].rstrip()}..."


def _is_high_priority_image_prompt_line(line: str) -> bool:
    prefixes = (
        "Create one finished",
        "Generate exactly one",
        "Creative set:",
        "Creative angle:",
        "Funnel stage:",
        "Asset type:",
        "Format:",
        "Aspect ratio:",
        "Variation contract:",
        "Category fidelity rule:",
        "Distinct marketing angle",
        "Creative test hypothesis",
        "Variation rule for this image",
        "Visual classifier static directive",
        "Angle diversity contract",
        "Static creative quality contract",
        "Static creative v2 requirement:",
        "Human/product context requirement:",
        "Human context requirement:",
        "Aim for the level",
        "Aim for a trustworthy",
        "Dropshipping static realism guard:",
        "Realism requirement:",
        "Creative-set diversity rule:",
        "Static no-text rule:",
        "Do not render buttons",
        "Do not invent",
        "Product identity hard lock:",
        "Static image material fidelity lock:",
        "Product-specific material/opacity lock:",
        "Preserve the product",
        "Use the supplied product reference image",
    )
    return line.startswith(prefixes)


def _with_static_quality_contract(base: str, creative: dict[str, Any]) -> str:
    summary = _static_quality_contract_summary(creative)
    if not summary:
        return base
    return f"{base}. Quality brief: {summary}"


def _static_variation_contract(creative: dict[str, Any]) -> str:
    set_id = str(creative.get("set_id") or "").upper()
    angle = str(creative.get("angle") or "").upper()
    asset_type = str(creative.get("asset_type") or "")
    if set_id == "C2" or angle in {"PAIN", "PRODUCT_HERO"}:
        return _with_static_quality_contract(
            (
                "C2 PRODUCT_HERO must show immediate product recognition, clean composition, believable scale, and one visible reason to care; "
                "avoid crowded lifestyle scenes and avoid using the same setting as C3"
            ),
            creative,
        )
    if set_id == "C3" or angle in {"IDENTITY", "USE_CONTEXT"}:
        return _with_static_quality_contract(
            (
                "C3 USE_CONTEXT must show the product integrated into a real routine, outfit, or use context; "
                "use a different location, crop, lighting mood, and body framing than C2"
            ),
            creative,
        )
    if set_id == "C4" or "detail" in str(creative.get("creative_type") or "").lower():
        return _with_static_quality_contract(
            (
                "C4 DETAIL_PROOF must be a tight product detail or macro crop, product filling most of the frame; "
                "avoid full-room lifestyle backgrounds and avoid repeating C2/C3 composition"
            ),
            creative,
        )
    if set_id == "C6" or "objection" in str(creative.get("creative_type") or "").lower():
        return _with_static_quality_contract(
            (
                "C6 PAIN_POINT must make one practical buyer doubt visible through product scale, handling, access, or setup; "
                "answer the doubt visually without text labels, invented claims, fake before/after, or repeating the C2 hero composition"
            ),
            creative,
        )
    if set_id == "C7" or "anti-hype" in str(creative.get("creative_type") or "").lower():
        return _with_static_quality_contract(
            (
                "C7 CONTRARIAN_CHECK must feel like a low-polish honest product inspection, not a glossy catalogue ad; "
                "use a distinct real-world setting, imperfect crop, and a skipped-detail focus without making the product look cheap or altered"
            ),
            creative,
        )
    if set_id == "C5" or asset_type == "carousel_card":
        return _with_static_quality_contract(
            (
                "C5 buying-guide carousel card must be one step in a sequence; make this card visually distinct by crop, feature focus, "
                "camera distance, and overlay hierarchy"
            ),
            creative,
        )
    return _with_static_quality_contract(
        "single static creative with distinct product-specific context, not a generic reusable background",
        creative,
    )


def _category_fidelity_rule(creative: dict[str, Any]) -> str:
    text = " ".join(
        str(creative.get(key) or "")
        for key in ["creative_type", "layout", "visual_prompt", "primary_text"]
    ).lower()
    if any(term in text for term in ["handbag", " bag", "shoulder bag", "tote"]):
        return (
            "Handbag scale consistency is mandatory: keep the same bag size relative to adult torso, shoulder, arm, and hands in every generated asset; "
            "preserve silhouette, width/height/depth ratio, handle length, strap drop, carry position, and apparent capacity cues from the reference; "
            "do not transform the bag into a mini bag, clutch, crossbody, tote, oversized shopper, backpack, or a different bag type."
        )
    return "preserve exact product scale and proportions from the reference; do not change category, size class, or use context"


def _request_fingerprint(
    model: str,
    prompt: str,
    aspect_ratio: str,
    image_size: str,
    product_reference_url: str,
    reference_image_urls: list[str] | None = None,
) -> str:
    source = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "product_reference_url": str(product_reference_url or ""),
        "reference_image_urls": _unique_reference_urls(reference_image_urls or [], primary=product_reference_url),
    }
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _request_payload(
    model: str,
    prompt: str,
    aspect_ratio: str,
    image_size: str,
    product_reference_url: str,
    reference_image_urls: list[str] | None = None,
) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for reference_url in [product_reference_url, *(reference_image_urls or [])]:
        image_part = _image_content_part(reference_url)
        if image_part:
            content.append(image_part)
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
        "stream": False,
        "usage": {"include": True},
        "image_config": {
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
        },
    }


def _unique_reference_urls(reference_image_urls: list[str], primary: str = "") -> list[str]:
    seen = {str(primary or "").strip()}
    unique: list[str] = []
    for item in reference_image_urls:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique[:8]


def _image_content_part(reference_url: str | None) -> dict[str, Any] | None:
    value = str(reference_url or "").strip()
    if not value:
        return None
    if _is_public_http_url(value):
        return {"type": "image_url", "image_url": {"url": value}}
    if value.startswith("data:image/"):
        return {"type": "image_url", "image_url": {"url": value}}
    data_url = local_image_to_data_url(value)
    if data_url:
        return {"type": "image_url", "image_url": {"url": data_url}}
    return None


def _extract_image_urls(result: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for choice in result.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") or {}
        if isinstance(message, dict):
            urls.extend(_urls_from_images(message.get("images")))
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        urls.extend(_urls_from_images([part]))
            urls.extend(_urls_from_images(message.get("data")))
        delta = choice.get("delta") or {}
        if isinstance(delta, dict):
            urls.extend(_urls_from_images(delta.get("images")))
    urls.extend(_urls_from_images(result.get("images")))
    return [url for index, url in enumerate(urls) if url and url not in urls[:index]]


def _urls_from_images(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value] if value.startswith(("data:image/", "http://", "https://")) else []
    if isinstance(value, dict):
        image_url = value.get("image_url") or value.get("imageUrl") or {}
        if isinstance(image_url, dict) and image_url.get("url"):
            return [str(image_url["url"])]
        if value.get("url"):
            return [str(value["url"])]
        if value.get("b64_json"):
            return [f"data:image/png;base64,{value['b64_json']}"]
        if value.get("data"):
            return _urls_from_images(value["data"])
        return []
    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            urls.extend(_urls_from_images(item))
        return urls
    return []


def _image_bytes(image_url: str, headers: dict[str, str], base_url: str) -> bytes:
    if image_url.startswith("data:image/"):
        _, encoded = image_url.split(",", 1)
        return base64.b64decode(encoded)
    request_headers = headers if _should_send_auth(image_url, base_url) else None
    response = requests.get(image_url, headers=request_headers, timeout=180)
    response.raise_for_status()
    return response.content


def _suffix_for_image_url(image_url: str) -> str:
    if image_url.startswith("data:image/"):
        mime_type = image_url.split(";", 1)[0].replace("data:", "")
        return mimetypes.guess_extension(mime_type) or ".png"
    suffix = Path(urlparse(image_url).path).suffix
    return suffix if suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"


def _should_send_auth(url: str, base_url: str) -> bool:
    target_host = urlparse(url).netloc.lower()
    base_host = urlparse(base_url).netloc.lower()
    return target_host == base_host or target_host.endswith(".openrouter.ai")


def _output_url(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(config.OUTPUT_DIR.resolve())
        return f"/output/{relative.as_posix()}"
    except Exception:
        return f"/output/{path.name}"


def _is_public_http_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname not in {"localhost", "127.0.0.1", "::1"}


def _write_trace(output_dir: str | Path, event: dict[str, Any]) -> None:
    try:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        trace_path = target_dir / "openrouter_image_trace.jsonl"
        event = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **event}
        with trace_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _score_first_asset_if_enabled(
    new_assets: list[dict[str, Any]],
    product_reference_url: str,
    api_key: str,
    vision_model: str | None,
    base_url: str,
    enabled: bool,
) -> dict[str, Any] | None:
    if not enabled or not new_assets:
        return None
    return vision_quality_client.score_generated_asset(
        product_reference_url=product_reference_url,
        generated_image_path=new_assets[0].get("image_path") or "",
        api_key=api_key,
        model=vision_model or config.OPENROUTER_VISION_MODEL,
        base_url=base_url,
    )


def _retry_prompt(original_prompt: str, quality_result: dict[str, Any]) -> str:
    addendum = quality_result.get("regeneration_prompt_addendum") or (
        "Improve product fidelity and human realism while preserving the same creative concept"
    )
    return (
        f"{original_prompt}\n\n"
        "Vision QA correction pass: regenerate the same creative concept, but fix the issues found by QA. "
        f"{addendum}. Keep the exact product reference shape, colour, proportions, finish, and visible markings. "
        "Use realistic adult anatomy, natural hands, plausible lighting and reflections, and real-camera photographic texture."
    )[:12000]


def _vision_quality_status(
    enabled: bool,
    checks: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
) -> str:
    if not enabled:
        return "disabled"
    if not checks:
        return "skipped"
    if any((item.get("result") or {}).get("status") == "vision_error" for item in checks):
        return "partial"
    if rejections:
        return "completed_with_regeneration"
    return "completed"


def _format_request_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        body = ""
        try:
            body = response.text[:1200]
        except Exception:
            body = ""
        return f"{type(exc).__name__}: HTTP {response.status_code}. {body}".strip()
    return f"{type(exc).__name__}: {exc}"


def _human_failure_reason(error_text: str) -> str:
    lowered = error_text.lower()
    if _is_billing_overdue_error(lowered):
        return (
            "The selected image provider/model returned AccountOverdueError, even though other OpenRouter "
            "models may still have usable credit on the same key."
        )
    if "api key" in lowered or "401" in lowered or "unauthorized" in lowered:
        return "OpenRouter API key is missing or invalid."
    if "rate limit" in lowered or "429" in lowered:
        return "OpenRouter rate limit or credit limit stopped static image generation."
    if "modalit" in lowered or "image" in lowered and "support" in lowered:
        return "The selected OpenRouter model may not support image output with the requested parameters."
    if "content" in lowered or "safety" in lowered or "policy" in lowered:
        return "The image model rejected the prompt or reference because of content policy or safety filtering."
    return error_text


def _next_step_for_error(error_text: str) -> str:
    lowered = error_text.lower()
    if _is_billing_overdue_error(lowered):
        return (
            "If OpenRouter credits are available, switch image model/provider or contact OpenRouter support "
            "with the provider request id. Also verify the UI is using the intended API key."
        )
    if "api key" in lowered or "401" in lowered or "unauthorized" in lowered:
        return "Set OPENROUTER_API_KEY or paste a valid key in the UI."
    if "rate limit" in lowered or "429" in lowered:
        return "Check OpenRouter credits/rate limits, then retry fewer images or lower image size."
    if "modalit" in lowered or "image" in lowered and "support" in lowered:
        return "Use google/gemini-3-pro-image-preview and keep modalities set to image plus text."
    if "content" in lowered or "safety" in lowered or "policy" in lowered:
        return "Simplify overlay text and use a direct product-only reference image."
    return "Open the Static image generation section and OpenRouter logs for the raw provider response."


def _is_billing_overdue_error(lowered_error_text: str) -> bool:
    return (
        "accountoverdueerror" in lowered_error_text
        or "overdue balance" in lowered_error_text
        or ("account" in lowered_error_text and "overdue" in lowered_error_text)
    )
