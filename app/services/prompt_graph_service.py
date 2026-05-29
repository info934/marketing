from __future__ import annotations

from typing import Any


def build_prompt_graph(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    structured = content_prompt_package.get("structured_prompt_v2") or {}
    memory = (
        content_prompt_package.get("creative_memory_guidance")
        or ugc_strategy.get("creative_memory_rag")
        or settings.get("creative_memory_guidance")
        or {}
    )
    scene_chaining = ugc_strategy.get("scene_chaining") or content_prompt_package.get("scene_chaining") or {}
    angle_multiplier = ugc_strategy.get("ad_angle_multiplier") or settings.get("ad_angle_multiplier") or {}
    angle_selector = ugc_strategy.get("ad_angle_selector") or settings.get("ad_angle_selector") or {}
    competitor_strategy = ugc_strategy.get("competitor_strategy") or settings.get("competitor_strategy") or {}
    environment_control = content_prompt_package.get("environment_control") or {}
    return {
        "version": "prompt_graph_v1",
        "source_of_truth": "structured blocks compiled into provider prompts",
        "workspace": "finance" if settings.get("app_mode") == "finance_personal_brand" else "ecommerce",
        "product_rules": {
            "product_name": product_analysis.get("product_name"),
            "category": product_analysis.get("likely_product_category"),
            "safe_facts": product_analysis.get("user_provided_facts") or [],
            "visible_detail_phrases": product_analysis.get("ad_safe_detail_phrases") or [],
            "fidelity": content_prompt_package.get("product_fidelity_instruction"),
            "rule": "Product reference controls exact shape, scale, color, markings, material appearance, and branding.",
        },
        "category_rules": {
            "selected_category": product_analysis.get("likely_product_category"),
            "directive": content_prompt_package.get("category_prompt_directive"),
            "image_directive": content_prompt_package.get("category_image_directive"),
            "overrides": settings.get("category_prompt_overrides") or {},
        },
        "avatar_rules": {
            "identity_contract": content_prompt_package.get("avatar_identity_contract"),
            "consistency_instruction": content_prompt_package.get("avatar_consistency_instruction"),
            "use_avatar_image_reference": bool(settings.get("use_avatar_image_reference")),
            "scene_chaining": _scene_chaining_summary(scene_chaining),
            "rule": "Avatar identity is preserved through reference or prompt-only continuity; avatar reference background, furniture, props, and lighting are not scene inputs.",
        },
        "environment_rules": {
            "control": environment_control,
            "directive": content_prompt_package.get("environment_control_directive"),
            "background_consistency": environment_control.get("background_consistency"),
            "environment_override": bool(environment_control.get("environment_override")),
            "preserve_original_scene_layout": bool(environment_control.get("preserve_original_scene_layout")),
            "environment_selection": environment_control.get("environment_selection") or "category_auto",
            "rule": "Choose a simple product/category/context environment and keep it consistent; product reference controls product fidelity only, avatar reference controls identity only.",
        },
        "camera_rules": structured.get("camera") or structured.get("camera_global"),
        "motion_rules": structured.get("motion") or structured.get("motion_global"),
        "scene_chaining_rules": _scene_chaining_summary(scene_chaining),
        "language_rules": {
            "language": ugc_strategy.get("language") or settings.get("language"),
            "market": ugc_strategy.get("market") or settings.get("market"),
            "voice_personality": ugc_strategy.get("voice_personality"),
            "subtitle_contract": content_prompt_package.get("subtitle_contract"),
        },
        "safety_rules": {
            "negative_prompt": content_prompt_package.get("negative_prompt"),
            "cta_policy": "No destination URLs, fake UI buttons, click/tap instructions, or platform CTA controls inside creative assets.",
            "compliance_inputs": {
                "unsupported_claims": product_analysis.get("unsupported_claims") or [],
                "permitted_claims": product_analysis.get("permitted_claims") or [],
            },
        },
        "memory_guidance": {
            "status": memory.get("status"),
            "winning_patterns": memory.get("winning_patterns") or [],
            "avoid_patterns": memory.get("avoid_patterns") or [],
            "prompt_guidance": memory.get("prompt_guidance"),
            "rule": "Use memory as a bias only; never copy unsafe claims or override product/avatar fidelity.",
        },
        "competitor_strategy": {
            "version": competitor_strategy.get("version"),
            "status": competitor_strategy.get("status"),
            "system_prompt": settings.get("competitor_strategy_system_prompt") or competitor_strategy.get("system_prompt"),
            "adaptation_brief": competitor_strategy.get("adaptation_brief"),
            "selector_bias": competitor_strategy.get("selector_bias") or {},
            "originality_guard": competitor_strategy.get("originality_guard") or {},
            "rule": "Use competitor input as temporary strategic context only, never as copy or direct visual reference.",
        },
        "ad_angle_multiplier": {
            "version": angle_multiplier.get("version"),
            "skill_source": angle_multiplier.get("skill_source"),
            "angle_count": angle_multiplier.get("angle_count"),
            "families": angle_multiplier.get("families") or [],
            "sample_hooks": [
                item.get("hook")
                for item in (angle_multiplier.get("angles") or [])[:6]
                if isinstance(item, dict) and item.get("hook")
            ],
            "rule": "Expand one core idea into materially distinct Pain/Desire/Proof/Identity/Contrarian/Urgency tests.",
        },
        "ad_angle_selector": {
            "version": angle_selector.get("version"),
            "strategy": angle_selector.get("selection_strategy"),
            "memory_used": angle_selector.get("memory_used"),
            "memory_confidence": angle_selector.get("memory_confidence"),
            "slot_selection": {
                slot: {
                    "family": selection.get("selected_family"),
                    "hook": selection.get("selected_hook"),
                    "score": selection.get("score"),
                    "reason": selection.get("selection_reason"),
                }
                for slot, selection in (angle_selector.get("slot_selection") or {}).items()
                if isinstance(selection, dict)
            },
            "rule": "Choose each C1-C5 angle using role priors first, then memory winners and avoid patterns when evidence exists.",
        },
        "compiled_outputs": {
            "deterministic_or_refined_seedance_prompt_chars": len(str(content_prompt_package.get("seedance_video_prompt") or "")),
            "final_payload_prompt_chars": len(str((content_prompt_package.get("seedance_payload") or {}).get("prompt") or "")),
            "prompt_compression": content_prompt_package.get("prompt_compression"),
        },
    }


def _scene_chaining_summary(scene_chaining: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scene_chaining, dict):
        return {}
    plan = scene_chaining.get("true_scene_chaining_plan") or {}
    execution = scene_chaining.get("provider_execution") or {}
    return {
        "version": scene_chaining.get("version"),
        "mode": scene_chaining.get("mode"),
        "strategy": plan.get("strategy") or scene_chaining.get("reference_strategy"),
        "current_execution_mode": execution.get("current_mode"),
        "actual_last_frame_reuse": execution.get("actual_last_frame_reuse"),
        "scene_link_count": plan.get("scene_link_count") or len(scene_chaining.get("scene_links") or []),
        "identity_lock": plan.get("identity_lock") or scene_chaining.get("identity_continuity"),
        "environment_lock": plan.get("environment_lock") or scene_chaining.get("environment_continuity"),
        "product_or_graphic_lock": plan.get("product_or_graphic_lock"),
    }
