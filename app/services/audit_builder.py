from __future__ import annotations

import difflib
from typing import Any

from app.services import openrouter_image_client


def build_prompt_audit(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    deterministic_content_prompt_package: dict[str, Any],
    final_content_prompt_package: dict[str, Any],
    deterministic_ads_creative_set: dict[str, Any],
    final_ads_creative_set: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
    prompt_model: str,
) -> dict[str, Any]:
    prompt_generation = final_content_prompt_package.get("prompt_generation") or {}
    static_prompt_generation = final_ads_creative_set.get("static_prompt_generation") or {}
    deterministic_video_prompt = str(
        deterministic_content_prompt_package.get("seedance_video_prompt") or ""
    )
    ai_refined_video_prompt = str(final_content_prompt_package.get("seedance_video_prompt") or "")
    final_payload_prompt = str(
        (video_generation.get("submitted_payload") or {}).get("prompt")
        or (final_content_prompt_package.get("seedance_payload") or {}).get("prompt")
        or ai_refined_video_prompt
    )

    deterministic_static = _static_prompt_map(deterministic_ads_creative_set)
    ai_refined_static = _static_prompt_map(final_ads_creative_set)
    final_image_prompts = _final_image_prompt_map(static_image_generation)
    scene_chaining = (
        final_content_prompt_package.get("scene_chaining")
        or ((final_content_prompt_package.get("structured_prompt_v2") or {}).get("avatar_rules") or {}).get(
            "scene_chaining"
        )
        or {}
    )

    return {
        "version": "prompt_audit_v1",
        "structured_prompt_v2": {
            "architecture": (final_content_prompt_package.get("structured_prompt_v2") or {}).get(
                "version"
            ),
            "scene_count": (final_content_prompt_package.get("structured_prompt_v2") or {}).get(
                "scene_count"
            ),
            "compiled_prompt_chars": len(
                str(final_content_prompt_package.get("seedance_video_prompt_uncompressed_v2") or "")
            ),
            "final_prompt_chars": len(
                str(
                    (final_content_prompt_package.get("seedance_payload") or {}).get("prompt")
                    or final_content_prompt_package.get("seedance_video_prompt")
                    or ""
                )
            ),
            "prompt_size_guard": {
                "target_limit": (final_content_prompt_package.get("prompt_compression") or {}).get(
                    "target_limit"
                ),
                "hard_limit": (final_content_prompt_package.get("prompt_compression") or {}).get(
                    "hard_limit"
                ),
                "fit_strategy": (final_content_prompt_package.get("prompt_compression") or {}).get(
                    "fit_strategy"
                ),
                "fits_hard_limit": (final_content_prompt_package.get("prompt_compression") or {}).get(
                    "fits_hard_limit"
                ),
            },
            "available": bool(final_content_prompt_package.get("structured_prompt_v2")),
        },
        "instruction_alignment": _instruction_alignment(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            final_content_prompt_package=final_content_prompt_package,
            final_payload_prompt=final_payload_prompt,
        ),
        "prompt_graph": final_content_prompt_package.get("prompt_graph") or {},
        "scene_chaining": _scene_chaining_audit(scene_chaining),
        "prompt_compression": final_content_prompt_package.get("prompt_compression"),
        "ugc_prompt": {
            "requested_model": prompt_generation.get("requested_model") or prompt_model,
            "used_model": prompt_generation.get("model"),
            "status": prompt_generation.get("status", "unknown"),
            "source_label": _source_label(prompt_generation.get("status")),
            "fallback_used": prompt_generation.get("status") in {"skipped", "failed"},
            "error": prompt_generation.get("error"),
            "deterministic_prompt": deterministic_video_prompt,
            "ai_refined_prompt": ai_refined_video_prompt,
            "final_payload_prompt": final_payload_prompt,
            "diff": {
                "deterministic_to_ai_refined": _diff_payload(
                    deterministic_video_prompt, ai_refined_video_prompt
                ),
                "ai_refined_to_final_payload": _diff_payload(
                    ai_refined_video_prompt, final_payload_prompt
                ),
            },
        },
        "static_prompt": {
            "requested_model": static_prompt_generation.get("requested_model") or prompt_model,
            "used_model": static_prompt_generation.get("model"),
            "status": static_prompt_generation.get("status", "unknown"),
            "source_label": _source_label(static_prompt_generation.get("status")),
            "fallback_used": static_prompt_generation.get("status")
            in {"skipped", "failed", "completed_with_fallback"},
            "fallback_reason": static_prompt_generation.get("fallback_reason"),
            "error": static_prompt_generation.get("error"),
            "prompt_budget": static_prompt_generation.get("prompt_budget"),
            "deterministic_prompts": deterministic_static,
            "ai_refined_prompts": ai_refined_static,
            "final_image_prompts": final_image_prompts,
            "diff": {
                "deterministic_to_ai_refined": _map_diff(deterministic_static, ai_refined_static),
                "ai_refined_to_final_payload": _map_diff(ai_refined_static, final_image_prompts),
            },
        },
    }


def _instruction_alignment(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    final_content_prompt_package: dict[str, Any],
    final_payload_prompt: str,
) -> dict[str, Any]:
    prompt_lower = str(final_payload_prompt or "").lower()
    category = str(product_analysis.get("likely_product_category") or "").lower()
    visual = product_analysis.get("visual_product_understanding") or {}
    selected_template = str((ugc_strategy.get("category_video_recipe") or {}).get("ugc_template") or "")
    expected_template = str(visual.get("recommended_template_id") or "")
    checks = [
        {
            "id": "no_generated_text_contract",
            "status": "passed" if "no generated text" in prompt_lower and "spoken audio" in prompt_lower else "warning",
            "message": "Ecommerce video prompt bans generated in-video text and keeps the hook in spoken audio."
            if "no generated text" in prompt_lower and "spoken audio" in prompt_lower
            else "Ecommerce video prompt should ban generated in-video text and keep hook/captions in spoken audio or post-production.",
        },
        {
            "id": "visual_classifier_template_alignment",
            "status": (
                "skipped"
                if visual.get("status") != "completed" or not expected_template
                else "passed"
                if expected_template == selected_template
                else "warning"
            ),
            "message": (
                f"Selected UGC template matches visual classifier: {selected_template}."
                if visual.get("status") == "completed" and expected_template == selected_template
                else f"Visual classifier expected {expected_template}, selected {selected_template}."
                if visual.get("status") == "completed" and expected_template
                else "Visual classifier was not available for this run."
            ),
        },
        {
            "id": "category_proof_contract",
            "status": _category_contract_status(category, prompt_lower),
            "message": _category_contract_message(category, prompt_lower),
        },
        {
            "id": "structured_prompt_v2",
            "status": "passed" if final_content_prompt_package.get("structured_prompt_v2") else "warning",
            "message": "Structured Prompt V2 is active."
            if final_content_prompt_package.get("structured_prompt_v2")
            else "Structured Prompt V2 is missing.",
        },
    ]
    warnings = [check for check in checks if check["status"] == "warning"]
    return {
        "version": "ugc_instruction_alignment_v1",
        "status": "warning" if warnings else "passed",
        "category": category,
        "selected_template": selected_template,
        "visual_classifier_status": visual.get("status"),
        "visual_recommended_template": expected_template,
        "checks": checks,
    }


def _category_contract_status(category: str, prompt_lower: str) -> str:
    if category == "apparel":
        return "passed" if "full-body" in prompt_lower and ("try-on" in prompt_lower or "head-to-toe" in prompt_lower) else "warning"
    if category == "shoes":
        return "passed" if "worn" in prompt_lower and ("feet" in prompt_lower or "foot" in prompt_lower) else "warning"
    if category == "handbag":
        return "passed" if ("shoulder" in prompt_lower or "hand" in prompt_lower) and "scale" in prompt_lower else "warning"
    return "passed"


def _category_contract_message(category: str, prompt_lower: str) -> str:
    status = _category_contract_status(category, prompt_lower)
    if status == "passed":
        return f"Category proof contract looks present for {category or 'generic product'}."
    if category == "apparel":
        return "Apparel prompt should require full-body/near-full-body try-on before detail close-ups."
    if category == "shoes":
        return "Shoes prompt should require worn-on-foot proof, side profile, and outfit context."
    if category == "handbag":
        return "Handbag prompt should require carry/shoulder scale proof and stable bag proportions."
    return "Category proof contract should be more specific."


def build_creative_plan_preview(
    *,
    ads_creative_set: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
    provider_validation: dict[str, Any],
    generation_mode: str,
    prompt_api_key_available: bool,
    max_static_images: int,
    product_reference_url: str = "",
) -> dict[str, Any]:
    image_plan = (
        {
            "selected": static_image_generation.get("generation_plan") or [],
            "skipped": static_image_generation.get("skipped_creatives") or [],
            "source_creative_count": static_image_generation.get("source_creative_count"),
            "selected_creative_count": static_image_generation.get("selected_creative_count"),
            "max_images_requested": static_image_generation.get("max_images_requested"),
            "max_images_policy": static_image_generation.get("max_images_policy"),
        }
        if static_image_generation
        else openrouter_image_client.preview_ad_image_plan(
            ads_creative_set,
            product_reference_url=product_reference_url,
            max_images=max_static_images,
        )
    )
    selected_sets = {str(item.get("set_id") or "") for item in image_plan.get("selected") or []}
    skipped_by_set = _skipped_by_set(image_plan.get("skipped") or [])
    provider_failed = [
        item for item in provider_validation.get("checks") or [] if item.get("status") == "failed"
    ]

    rows = []
    for item in ads_creative_set.get("creative_plan") or []:
        set_id = str(item.get("set_id") or "")
        if set_id == "C1":
            if generation_mode == "static":
                status, reason = "SKIPPED", "generation mode=static"
            elif any("video" in str(check.get("id")) for check in provider_failed):
                status, reason = "BLOCKED", _first_failed_reason(provider_failed, "video")
            elif not prompt_api_key_available:
                status, reason = "SKIPPED", "no API key"
            else:
                status = "YES" if not video_generation.get("skipped_by_generation_mode") else "SKIPPED"
                reason = video_generation.get("failure_reason") or "selected for video generation"
        else:
            if generation_mode == "video":
                status, reason = "SKIPPED", "generation mode=video"
            elif any("image" in str(check.get("id")) for check in provider_failed):
                status, reason = "BLOCKED", _first_failed_reason(provider_failed, "image")
            elif not prompt_api_key_available:
                status, reason = "SKIPPED", "no API key"
            elif set_id in selected_sets:
                status, reason = "YES", "selected for image generation"
            else:
                status, reason = "SKIPPED", skipped_by_set.get(set_id) or "max_static_images"
        rows.append(
            {
                "set_id": set_id,
                "creative_type": item.get("creative_type"),
                "angle": item.get("angle"),
                "aspect_ratio": item.get("aspect_ratio"),
                "funnel_stage": item.get("funnel_stage"),
                "budget_share_percent": item.get("budget_share_percent"),
                "generation_target": item.get("generation_target"),
                "status": status,
                "reason": reason,
            }
        )

    return {
        "version": "creative_plan_preview_v1",
        "generation_mode": generation_mode,
        "max_static_images": max_static_images,
        "prompt_api_key_available": prompt_api_key_available,
        "image_plan_policy": image_plan.get("max_images_policy"),
        "source_creative_count": image_plan.get("source_creative_count"),
        "selected_image_count": image_plan.get("selected_creative_count"),
        "items": rows,
    }


def _source_label(status: Any) -> str:
    if status == "completed":
        return "AI Refined"
    if status == "completed_with_fallback":
        return "Fallback after AI parse failure"
    return "Fallback"


def _scene_chaining_audit(scene_chaining: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scene_chaining, dict) or not scene_chaining:
        return {"available": False}
    plan = scene_chaining.get("true_scene_chaining_plan") or {}
    execution = scene_chaining.get("provider_execution") or {}
    scene_links = plan.get("scene_links") or scene_chaining.get("scene_links") or []
    return {
        "available": True,
        "version": scene_chaining.get("version"),
        "mode": scene_chaining.get("mode"),
        "strategy": plan.get("strategy") or scene_chaining.get("reference_strategy"),
        "current_execution_mode": execution.get("current_mode"),
        "actual_last_frame_reuse": execution.get("actual_last_frame_reuse"),
        "avatar_reference_supplied": execution.get("avatar_reference_supplied"),
        "input_reference_count": execution.get("input_reference_count"),
        "frame_image_count": execution.get("frame_image_count"),
        "scene_link_count": plan.get("scene_link_count") or len(scene_links),
        "identity_lock": plan.get("identity_lock") or scene_chaining.get("identity_continuity"),
        "environment_lock": plan.get("environment_lock") or scene_chaining.get("environment_continuity"),
        "product_or_graphic_lock": plan.get("product_or_graphic_lock"),
        "quality_requirements": (plan.get("quality_requirements") or [])[:4],
        "limitations": (plan.get("limitations") or [])[:3],
        "scene_links_preview": scene_links[:4],
    }


def _static_prompt_map(ads_creative_set: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in ads_creative_set.get("static_image_ads") or []:
        creative_id = item.get("creative_id") or item.get("set_id")
        if creative_id:
            result[str(creative_id)] = str(item.get("visual_prompt") or "")
    carousel = ads_creative_set.get("carousel_ad") or {}
    for card in carousel.get("cards") or []:
        card_id = f"{carousel.get('set_id') or 'C5'}_card_{card.get('card_number')}"
        result[card_id] = str(card.get("visual_prompt") or "")
    return result


def _final_image_prompt_map(static_image_generation: dict[str, Any]) -> dict[str, str]:
    assets = static_image_generation.get("image_assets") or []
    if assets:
        return {
            str(asset.get("creative_id") or f"asset_{index}"): str(asset.get("prompt") or "")
            for index, asset in enumerate(assets, start=1)
        }
    return {
        str(item.get("creative_id") or f"creative_{index}"): str(item.get("prompt_preview") or "")
        for index, item in enumerate(static_image_generation.get("generation_plan") or [], start=1)
    }


def _diff_payload(before: str, after: str) -> dict[str, Any]:
    return {
        "changed": before != after,
        "before_chars": len(before),
        "after_chars": len(after),
        "unified_diff_preview": _unified_diff_preview(before, after),
    }


def _map_diff(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    keys = sorted(set(before) | set(after))
    changed = []
    for key in keys:
        before_value = before.get(key, "")
        after_value = after.get(key, "")
        if before_value != after_value:
            changed.append(
                {
                    "key": key,
                    "before_chars": len(before_value),
                    "after_chars": len(after_value),
                    "unified_diff_preview": _unified_diff_preview(before_value, after_value),
                }
            )
    return {
        "changed_count": len(changed),
        "total_compared": len(keys),
        "items": changed,
    }


def _unified_diff_preview(before: str, after: str, max_lines: int = 80) -> str:
    if before == after:
        return ""
    diff = difflib.unified_diff(
        before.splitlines() or [before],
        after.splitlines() or [after],
        fromfile="deterministic",
        tofile="refined_or_final",
        lineterm="",
    )
    return "\n".join(list(diff)[:max_lines])


def _skipped_by_set(skipped_items: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in skipped_items:
        set_id = str(item.get("set_id") or "")
        if set_id and set_id not in result:
            result[set_id] = str(item.get("reason") or "max_static_images")
    return result


def _first_failed_reason(failed_checks: list[dict[str, Any]], marker: str) -> str:
    for check in failed_checks:
        if marker in str(check.get("id")):
            return str(check.get("reason") or "provider validation failed")
    return "provider validation failed"
