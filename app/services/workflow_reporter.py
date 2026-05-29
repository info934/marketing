from __future__ import annotations

from typing import Any


def build(final_output: dict[str, Any]) -> dict[str, Any]:
    user_input = final_output.get("user_input") or {}
    product = final_output.get("product_analysis") or {}
    avatar = final_output.get("avatar") or {}
    ugc = final_output.get("ugc_strategy") or {}
    prompts = final_output.get("content_prompt_package") or {}
    ads = final_output.get("ads_creative_set") or {}
    static_images = final_output.get("static_image_generation") or {}
    video = final_output.get("video_generation") or {}
    provider_validation = final_output.get("provider_validation") or {}
    cost = final_output.get("session_cost_summary") or {}
    fidelity = final_output.get("product_fidelity_result") or {}
    compliance = final_output.get("compliance_result") or {}
    quality = final_output.get("quality_result") or {}
    self_critique = final_output.get("self_critique") or {}
    post_qa = final_output.get("post_generation_qa") or {}
    creative_memory = final_output.get("creative_memory") or {}
    marketing_skill_plan = final_output.get("marketing_skill_plan") or {}
    seedance_payload = final_output.get("seedance_payload") or prompts.get("seedance_payload") or {}

    blocking_reasons = _blocking_reasons(
        fidelity, compliance, static_images, video, quality, provider_validation
    )
    warnings = _warnings(product, fidelity, compliance, quality, prompts, static_images, video)
    warnings.extend(_post_qa_warnings(post_qa))

    return {
        "version": "workflow_report_v1",
        "purpose": "Human-readable audit of the full UGC ads workflow, ordered from inputs to final deliverables.",
        "executive_summary": {
            "final_export_status": final_output.get("final_export_status", "unknown"),
            "primary_outcome": _primary_outcome(final_output),
            "product_name": product.get("product_name") or user_input.get("product_name"),
            "product_category": product.get("likely_product_category"),
            "product_category_source": product.get("product_category_source"),
            "platform": ugc.get("platform") or user_input.get("platform"),
            "market": ugc.get("market") or user_input.get("market"),
            "language": ugc.get("language") or user_input.get("language"),
            "duration_seconds": ugc.get("duration_seconds") or user_input.get("video_length"),
            "aspect_ratio": ugc.get("aspect_ratio"),
            "session_folder": user_input.get("session_folder_name"),
            "session_type": user_input.get("session_type"),
            "generation_mode": user_input.get("generation_mode", "both"),
            "video_requested": bool(user_input.get("generate_video", True)),
            "static_images_requested": bool(user_input.get("generate_static_images", True)),
            "known_cost": cost.get("total_known_cost_display"),
            "cost_status": cost.get("status"),
            "self_critique_regeneration_recommended": self_critique.get("regeneration_recommended"),
        },
        "decision_state": {
            "can_use_export": final_output.get("final_export_status") in {"approved", "warning"},
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "next_actions": _next_actions(final_output, blocking_reasons, warnings),
        },
        "identity_and_product_lock": {
            "product_reference": {
                "path_or_url": product.get("product_image_path"),
                "strict_fidelity_present": "strict visual reference"
                in str(prompts.get("product_fidelity_instruction", "")).lower(),
                "known_product_facts": product.get("known_product_facts"),
                "user_provided_facts": product.get("user_provided_facts"),
            },
            "avatar_reference": {
                "creator_label": avatar.get("name"),
                "identity_type": avatar.get("identity_type"),
                "reference_url_present": bool(avatar.get("image_url")),
                "identity_contract": seedance_payload.get("avatar_identity_contract")
                or prompts.get("avatar_identity_contract"),
            },
            "category_prompt": {
                "selected_category": product.get("likely_product_category"),
                "directive_preview": _truncate(prompts.get("category_prompt_directive"), 420),
            },
        },
        "deliverables": _deliverables(ads, static_images, video, prompts, cost),
        "creative_memory": {
            "status": creative_memory.get("status"),
            "db_path": creative_memory.get("db_path"),
            "product_id": creative_memory.get("product_id"),
            "campaign_id": creative_memory.get("campaign_id"),
            "creative_count": creative_memory.get("creative_count"),
            "rag_guidance": creative_memory.get("rag_guidance"),
        },
        "marketing_skill_plan": {
            "version": marketing_skill_plan.get("version"),
            "source": marketing_skill_plan.get("source"),
            "foundation_context": marketing_skill_plan.get("foundation_context") or {},
            "selected_skills": marketing_skill_plan.get("selected_skills") or [],
            "generation_gate": marketing_skill_plan.get("generation_gate") or {},
            "creative_quality_contract": marketing_skill_plan.get("creative_quality_contract") or {},
        },
        "prompt_and_payload_map": _prompt_and_payload_map(prompts, static_images, seedance_payload),
        "workflow_stages": _workflow_stages(
            product=product,
            ugc=ugc,
            prompts=prompts,
            ads=ads,
            fidelity=fidelity,
            compliance=compliance,
            quality=quality,
            static_images=static_images,
            video=video,
            provider_validation=provider_validation,
            cost=cost,
            self_critique=self_critique,
            post_qa=post_qa,
        ),
        "raw_audit_sections": [
            {"title": "User input", "key": "user_input", "why_it_matters": "Original request values and UI overrides."},
            {"title": "Avatar", "key": "avatar", "why_it_matters": "Selected or custom own-person identity settings."},
            {"title": "Product analysis", "key": "product_analysis", "why_it_matters": "Safe product facts and risky claim separation."},
            {"title": "Marketing skill plan", "key": "marketing_skill_plan", "why_it_matters": "Corey Haines marketing skills selected for this mission and their generation gate."},
            {"title": "Creative brain", "key": "ugc_strategy.audience_research", "why_it_matters": "Audience archetype, psychology, hook strategy, scene direction, and memory influence."},
            {"title": "UGC strategy", "key": "ugc_strategy", "why_it_matters": "Hook, scene plan, voiceover, platform adaptation."},
            {"title": "Prompt package", "key": "content_prompt_package", "why_it_matters": "All prompts, structured scenes, and Seedance payload source."},
            {"title": "Ads creative set", "key": "ads_creative_set", "why_it_matters": "C1-C5 plan, copy, prompts, and platform assets."},
            {"title": "Static image generation", "key": "static_image_generation", "why_it_matters": "Image API plan, generated assets, skipped items, duplicate handling."},
            {"title": "Video generation", "key": "video_generation", "why_it_matters": "Seedance submission status, failure reason, job id, and payload trace."},
            {"title": "Post generation QA", "key": "post_generation_qa", "why_it_matters": "Checks generated/skipped assets, language contracts, fake CTA text, and scene chaining."},
            {"title": "Provider validation", "key": "provider_validation", "why_it_matters": "Preflight checks for model capability, public references, prompt size, image count, and aspect ratio."},
            {"title": "Prompt audit", "key": "prompt_audit", "why_it_matters": "Deterministic versus AI-refined versus final payload prompts."},
            {"title": "AI self critique", "key": "self_critique", "why_it_matters": "Scroll stopping, realism, policy risk, hook strength, product clarity, and regeneration recommendation."},
            {"title": "Creative plan preview", "key": "creative_plan_preview", "why_it_matters": "C1-C5 generation decision, selected/skipped status, and skip reasons."},
            {"title": "Creative memory", "key": "creative_memory", "why_it_matters": "Saved product, campaign, prompt, creative, rating, and performance learning records."},
            {"title": "Guards and quality", "key": "quality_result", "why_it_matters": "Approval, warnings, or block reasons."},
            {"title": "Cost summary", "key": "session_cost_summary", "why_it_matters": "Known OpenRouter costs and unknown components."},
        ],
    }


def _primary_outcome(final_output: dict[str, Any]) -> str:
    export_status = final_output.get("final_export_status", "unknown")
    static_status = (final_output.get("static_image_generation") or {}).get("image_generation_status", "unknown")
    video_status = (final_output.get("video_generation") or {}).get("video_generation_status", "unknown")
    if export_status == "blocked":
        return "Workflow was blocked by safety or fidelity checks before usable export."
    if video_status == "completed" and static_status in {"completed", "partial"}:
        return "Video and static ad assets were generated."
    if video_status == "completed":
        if static_status == "skipped":
            return "UGC video was generated; static image generation was not requested or was skipped."
        return "UGC video was generated; static image assets need review or regeneration."
    if static_status in {"completed", "partial"}:
        if video_status == "skipped":
            return "Static ad assets were generated; UGC video generation was not requested or was skipped."
        return "Static ad assets were generated; video needs review or regeneration."
    if video_status == "skipped" or static_status == "skipped":
        return "Creative plan and prompts were generated, but one or more API generations were skipped."
    return "Workflow completed with audit data; review generation statuses for next steps."


def _deliverables(
    ads: dict[str, Any],
    static_images: dict[str, Any],
    video: dict[str, Any],
    prompts: dict[str, Any],
    cost: dict[str, Any],
) -> dict[str, Any]:
    carousel = ads.get("carousel_ad") or {}
    image_assets = static_images.get("image_assets") or []
    generation_plan = static_images.get("generation_plan") or []
    return {
        "ugc_video": {
            "set_id": (ads.get("ugc_video_ad") or {}).get("set_id", "C1"),
            "status": video.get("video_generation_status", "unknown"),
            "job_id": video.get("job_id"),
            "video_path": video.get("video_path"),
            "prompt_ready": bool(prompts.get("seedance_video_prompt")),
            "skipped_by_generation_mode": bool(video.get("skipped_by_generation_mode")),
            "failure_reason": video.get("failure_reason") or video.get("error"),
        },
        "static_images": {
            "status": static_images.get("image_generation_status", "unknown"),
            "planned_count": len(generation_plan),
            "source_creative_count": static_images.get("source_creative_count"),
            "skipped_count": len(static_images.get("skipped_creatives") or []),
            "generated_count": static_images.get("generated_count", len(image_assets)),
            "asset_count": len(image_assets),
            "api_request_count": static_images.get("api_request_count", 0),
            "duplicate_skips": len(static_images.get("duplicate_skips") or []),
            "skipped_by_generation_mode": bool(static_images.get("skipped_by_generation_mode")),
            "selected_creatives": [
                {
                    "creative_id": item.get("creative_id"),
                    "set_id": item.get("set_id"),
                    "asset_type": item.get("asset_type"),
                    "angle": item.get("angle"),
                }
                for item in generation_plan
            ],
            "failure_reason": static_images.get("failure_reason") or static_images.get("error"),
        },
        "carousel": {
            "set_id": carousel.get("set_id", "C5"),
            "card_count": carousel.get("card_count", len(carousel.get("cards") or [])),
            "cards_ready": bool(carousel.get("cards")),
        },
        "ad_copy": {
            "description_variant_count": len((ads.get("ad_description_suggestions") or {}).get("variants") or []),
            "primary_text_variant_count": len(ads.get("primary_text_variants") or []),
            "google_headline_count": len(
                ((ads.get("google_ads_assets") or {}).get("responsive_search_ad") or {}).get("headlines") or []
            ),
        },
        "cost": {
            "status": cost.get("status"),
            "known_total": cost.get("total_known_cost_display"),
            "unknown_components": cost.get("unknown_cost_components") or [],
        },
    }


def _prompt_and_payload_map(
    prompts: dict[str, Any],
    static_images: dict[str, Any],
    seedance_payload: dict[str, Any],
) -> dict[str, Any]:
    prompt_generation = prompts.get("prompt_generation") or {}
    static_prompt_generation = static_images.get("static_prompt_generation") or {}
    return {
        "prompt_model": {
            "status": prompt_generation.get("status", "unknown"),
            "model": prompt_generation.get("model"),
            "fallback_used": prompt_generation.get("status") in {"skipped", "failed"},
            "error": prompt_generation.get("error"),
        },
        "static_creative_prompt_model": {
            "status": static_prompt_generation.get("status", "unknown"),
            "model": static_prompt_generation.get("model"),
            "fallback_used": static_prompt_generation.get("status") in {"skipped", "failed"},
            "error": static_prompt_generation.get("error"),
        },
        "seedance_video_payload": {
            "model": seedance_payload.get("model"),
            "duration": seedance_payload.get("duration"),
            "aspect_ratio": seedance_payload.get("aspect_ratio"),
            "resolution": seedance_payload.get("resolution"),
            "avatar_reference_mode": seedance_payload.get("avatar_reference_mode"),
            "input_reference_count": seedance_payload.get("input_reference_count")
            or len(seedance_payload.get("input_references") or []),
            "prompt_preview": _truncate(seedance_payload.get("prompt"), 900),
            "prompt_chars": len(str(seedance_payload.get("prompt") or "")),
            "structured_prompt_architecture": seedance_payload.get("structured_prompt_architecture"),
            "prompt_compression": seedance_payload.get("prompt_compression"),
        },
        "structured_prompt_v2": {
            "available": bool(prompts.get("structured_prompt_v2")),
            "scene_count": (prompts.get("structured_prompt_v2") or {}).get("scene_count"),
            "compression": prompts.get("prompt_compression"),
        },
        "static_image_prompts": {
            "model": static_images.get("model"),
            "selected_creative_count": static_images.get("selected_creative_count"),
            "source_creative_count": static_images.get("source_creative_count"),
            "prompt_contract": static_images.get("prompt_respect_contract"),
            "max_images_policy": static_images.get("max_images_policy"),
        },
        "editable_prompt_layers": {
            "negative_prompt_overridden": bool((prompts.get("seedance_payload") or {}).get("negative_prompt")),
            "category_prompt_present": bool(prompts.get("category_prompt_directive")),
            "avatar_identity_contract_present": bool(prompts.get("avatar_identity_contract")),
        },
    }


def _workflow_stages(
    product: dict[str, Any],
    ugc: dict[str, Any],
    prompts: dict[str, Any],
    ads: dict[str, Any],
    fidelity: dict[str, Any],
    compliance: dict[str, Any],
    quality: dict[str, Any],
    static_images: dict[str, Any],
    video: dict[str, Any],
    provider_validation: dict[str, Any],
    cost: dict[str, Any],
    self_critique: dict[str, Any],
    post_qa: dict[str, Any],
) -> list[dict[str, Any]]:
    angle_multiplier = ugc.get("ad_angle_multiplier") or ads.get("ad_angle_multiplier") or {}
    angle_selector = ugc.get("ad_angle_selector") or ads.get("ad_angle_selector") or {}
    return [
        _stage(
            "product_intake",
            "Product Intake Agent",
            _status_from_missing(product.get("missing_information")),
            "Reads product name, notes, selected category, and product reference.",
            f"Category={product.get('likely_product_category')}; safe facts={len(product.get('user_provided_facts') or [])}; unsupported claims={len(product.get('unsupported_claims') or [])}.",
            "product_analysis",
        ),
        _stage(
            "automatic_product_understanding",
            "Automatic Product Understanding",
            "pass" if (product.get("automatic_product_understanding") or {}).get("category") else "warning",
            "Detects category, material, market position, target audience, usage context, season, and style from the supplied product data.",
            _product_understanding_summary(product.get("automatic_product_understanding") or {}),
            "product_analysis.automatic_product_understanding",
        ),
        _stage(
            "audience_research",
            "Audience Research Agent",
            "pass" if (ugc.get("audience_research") or {}).get("primary_archetype") else "warning",
            "Selects category-specific buyer archetype and decision triggers from product facts and memory.",
            f"Primary={(ugc.get('audience_research') or {}).get('primary_archetype')}; triggers={len((ugc.get('audience_research') or {}).get('decision_triggers') or [])}.",
            "ugc_strategy.audience_research",
        ),
        _stage(
            "emotional_angle",
            "Emotional Angle Engine",
            "pass" if (ugc.get("emotional_angle") or {}).get("primary_angle") else "warning",
            "Selects the primary emotional performance angle and converts it into safe creative direction.",
            f"Angle={(ugc.get('emotional_angle') or {}).get('primary_safe_label')}; driver={_truncate((ugc.get('emotional_angle') or {}).get('driver'), 140)}.",
            "ugc_strategy.emotional_angle",
        ),
        _stage(
            "creative_psychology",
            "Creative Psychology Agent",
            "pass" if (ugc.get("creative_psychology") or {}).get("primary_driver") else "warning",
            "Builds behavior tree, emotional curve, hook psychology, and variation rules.",
            f"Driver={_truncate((ugc.get('creative_psychology') or {}).get('primary_driver'), 140)}.",
            "ugc_strategy.creative_psychology",
        ),
        _stage(
            "voice_personality",
            "Voice Personality Engine",
            "pass" if (ugc.get("voice_personality") or {}).get("creator_style") else "warning",
            "Defines tone, energy, confidence, accent, pacing, gesture style, and subtitle style for consistent creator delivery.",
            f"Style={(ugc.get('voice_personality') or {}).get('creator_style')}; tone={(ugc.get('voice_personality') or {}).get('tone')}; accent={_truncate((ugc.get('voice_personality') or {}).get('accent_profile'), 100)}.",
            "ugc_strategy.voice_personality",
        ),
        _stage(
            "ugc_hook",
            "UGC Hook Agent",
            "pass" if (ugc.get("hook_strategy") or {}).get("selected_hook") else "warning",
            "Chooses hook pattern using category psychology and performance memory.",
            f"Pattern={(ugc.get('hook_strategy') or {}).get('selected_pattern')}; hook={_truncate((ugc.get('hook_strategy') or {}).get('selected_hook'), 140)}.",
            "ugc_strategy.hook_strategy",
        ),
        _stage(
            "scene_director",
            "Scene Director Agent",
            "pass" if (ugc.get("scene_direction") or {}).get("directed_scenes") else "warning",
            "Directs shot types and scene visuals before prompt engineering.",
            f"Scenes={len((ugc.get('scene_direction') or {}).get('directed_scenes') or [])}; rules={len((ugc.get('scene_direction') or {}).get('camera_rules') or [])}.",
            "ugc_strategy.scene_direction",
        ),
        _stage(
            "scene_chaining",
            "Scene Chaining Agent",
            "pass" if (ugc.get("scene_chaining") or {}).get("scene_links") else "warning",
            "Adds last-frame continuity, wardrobe, environment, motion bridges, and reference strategy across scenes.",
            f"Mode={(ugc.get('scene_chaining') or {}).get('mode')}; links={len((ugc.get('scene_chaining') or {}).get('scene_links') or [])}.",
            "ugc_strategy.scene_chaining",
        ),
        _stage(
            "ugc_strategy",
            "UGC Strategy Agent",
            "pass" if ugc.get("hook") and ugc.get("scene_by_scene_script") else "warning",
            "Builds hook, voiceover, scenes, subtitles, language, and platform adaptation from the creative brain outputs.",
            f"Hook={_truncate(ugc.get('hook'), 120)}; scenes={len(ugc.get('scene_by_scene_script') or [])}; voice={_truncate(ugc.get('voice_profile'), 120)}.",
            "ugc_strategy",
        ),
        _stage(
            "content_prompt",
            "Content Prompt Engineer Agent",
            "pass" if prompts.get("seedance_video_prompt") else "warning",
            "Creates Seedance prompt, structured scene prompt, avatar identity contract, and fallback prompts.",
            f"Prompt model={(prompts.get('prompt_generation') or {}).get('status', 'unknown')}; category prompt={bool(prompts.get('category_prompt_directive'))}; identity contract={bool(prompts.get('avatar_identity_contract'))}.",
            "content_prompt_package",
        ),
        _stage(
            "structured_prompt_v2",
            "Structured Prompt Architecture V2",
            "pass" if prompts.get("structured_prompt_v2") else "warning",
            "Separates prompt intent into scene, camera, lighting, emotion, motion, product rules, and avatar rules before compiling.",
            f"Scenes={(prompts.get('structured_prompt_v2') or {}).get('scene_count')}; architecture={(prompts.get('structured_prompt_v2') or {}).get('version')}.",
            "content_prompt_package.structured_prompt_v2",
        ),
        _stage(
            "prompt_compression",
            "Prompt Compression Layer",
            "pass" if (prompts.get("prompt_compression") or {}).get("status") == "completed" else "warning",
            "Deduplicates repeated semantic clauses, uses reusable blocks, and enforces the provider prompt size limit.",
            f"Saved={(prompts.get('prompt_compression') or {}).get('chars_saved', 0)} chars; final={(prompts.get('prompt_compression') or {}).get('chars_provider_final')}; strategy={(prompts.get('prompt_compression') or {}).get('fit_strategy')}.",
            "content_prompt_package.prompt_compression",
        ),
        _stage(
            "ad_angle_multiplier",
            "Ad Angle Multiplier",
            "pass" if (angle_multiplier.get("angle_count") or 0) >= 10 else "warning",
            "Expands the core idea into distinct Pain/Desire/Proof/Identity/Contrarian/Urgency creative tests.",
            f"Angles={angle_multiplier.get('angle_count') or 0}; families={', '.join((angle_multiplier.get('families') or [])[:6])}.",
            "ugc_strategy.ad_angle_multiplier",
        ),
        _stage(
            "ad_angle_selector",
            "Ad Angle Selector",
            "pass" if (angle_selector.get("slot_selection") or {}) else "warning",
            "Scores angle options for C1-C5 using asset role, Creative Memory winners, avoid patterns, and seed priors.",
            _angle_selector_summary(angle_selector),
            "ugc_strategy.ad_angle_selector",
        ),
        _stage(
            "ads_set",
            "Ads Creative Set Agent",
            "pass" if ads.get("creative_plan") else "warning",
            "Creates C1-C5 media plan, static prompts, carousel cards, and ad copy suggestions, then optionally refines static prompts with the selected prompt model.",
            f"Plan sets={len(ads.get('creative_plan') or [])}; static ads={len(ads.get('static_image_ads') or [])}; carousel cards={(ads.get('carousel_ad') or {}).get('card_count', 0)}; static prompt model={(ads.get('static_prompt_generation') or {}).get('model', 'none')}.",
            "ads_creative_set",
        ),
        _stage(
            "product_fidelity_guard",
            "Product Fidelity Guard",
            _guard_status(fidelity.get("product_fidelity_status")),
            "Checks product reference, strict visual fidelity, and invented detail risks.",
            _guard_summary(fidelity, "changed_or_invented_details", "missing_fidelity_instructions"),
            "product_fidelity_result",
        ),
        _stage(
            "compliance_guard",
            "Compliance Guard",
            _guard_status(compliance.get("compliance_status")),
            "Checks unsupported claims, testimonials, trademarks, scarcity, discounts, and platform risks.",
            _compliance_summary(compliance),
            "compliance_result",
        ),
        _stage(
            "quality_scorer",
            "Quality Scorer",
            _quality_status(quality),
            "Scores fidelity, authenticity, conversion fit, compliance, clarity, and prompt engineering.",
            f"Overall={quality.get('overall_quality_score')}; export={quality.get('export_status')}; improvements={len(quality.get('recommended_improvements') or [])}.",
            "quality_result",
        ),
        _stage(
            "provider_validation",
            "Provider Capability Validation",
            _generation_status(provider_validation.get("status")),
            "Checks selected provider models, public references, prompt size, image count, and supported aspect ratio before API calls.",
            f"Status={provider_validation.get('status', 'unknown')}; reason={_truncate(provider_validation.get('reason'), 160)}; checks={len(provider_validation.get('checks') or [])}.",
            "provider_validation",
        ),
        _stage(
            "static_images",
            "Static Image Generation",
            _generation_status(static_images.get("image_generation_status")),
            "Selects planned static/carousel creatives, deduplicates prompts, calls image API if enabled, and records vision QA for generated assets.",
            f"Status={static_images.get('image_generation_status')}; generated={static_images.get('generated_count', len(static_images.get('image_assets') or []))}; selected={static_images.get('selected_creative_count')}; vision={static_images.get('vision_quality_status', 'unknown')}; retries={static_images.get('regeneration_attempts', 0)}; reason={_truncate(static_images.get('failure_reason') or static_images.get('error'), 160)}.",
            "static_image_generation",
        ),
        _stage(
            "seedance_video",
            "Seedance Video Generation",
            _generation_status(video.get("video_generation_status")),
            "Submits the final Seedance payload and records job/video status.",
            f"Status={video.get('video_generation_status')}; job={video.get('job_id')}; reason={_truncate(video.get('failure_reason') or video.get('error'), 160)}.",
            "video_generation",
        ),
        _stage(
            "post_generation_qa",
            "Post Generation QA",
            _generation_status(post_qa.get("status")),
            "Checks real asset availability, language contract, fake CTA controls, reference consistency, and scene chaining after generation.",
            f"Status={post_qa.get('status')}; failed={post_qa.get('failed_count')}; warnings={post_qa.get('warning_count')}; next={_truncate(post_qa.get('next_step'), 160)}.",
            "post_generation_qa",
        ),
        _stage(
            "self_critique",
            "AI Self Critique",
            "warning" if self_critique.get("regeneration_recommended") else "pass",
            "Reviews scroll stopping, realism, ad policy risk, hook strength, and product clarity after generation/prompt assembly.",
            f"Scroll={self_critique.get('scroll_stopping_score')}; realism={self_critique.get('realism_score')}; policy_risk={self_critique.get('ad_policy_risk_score')}; regenerate={self_critique.get('regeneration_recommended')}.",
            "self_critique",
        ),
        _stage(
            "creative_memory",
            "Creative Intelligence Memory",
            "pass" if prompts.get("creative_memory_guidance") is not None else "warning",
            "Stores product, campaign, prompt, creative, rating-ready, and performance-ready records for the learning loop.",
            f"RAG winners={len(((ugc.get('creative_memory_rag') or {}).get('winning_patterns') or []))}; avoid={len(((ugc.get('creative_memory_rag') or {}).get('avoid_patterns') or []))}.",
            "creative_memory",
        ),
        _stage(
            "session_cost",
            "Session Cost Summary",
            cost.get("status", "unknown"),
            "Aggregates OpenRouter usage costs returned by prompt, image, and video providers.",
            f"Known total={cost.get('total_known_cost_display')}; unknown components={', '.join(cost.get('unknown_cost_components') or []) or 'none'}.",
            "session_cost_summary",
        ),
    ]


def _stage(stage_id: str, title: str, status: str, input_summary: str, output_summary: str, inspect_key: str) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "title": title,
        "status": status,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "inspect_key": inspect_key,
    }


def _angle_selector_summary(selector: dict[str, Any]) -> str:
    slots = selector.get("slot_selection") or {}
    if not isinstance(slots, dict) or not slots:
        return "No selected angle slots yet."
    parts = []
    for slot in ["C1", "C2", "C3", "C4", "C5"]:
        selection = slots.get(slot) or {}
        if selection:
            parts.append(f"{slot}={selection.get('selected_family')}:{selection.get('score')}")
    return (
        f"{'; '.join(parts)}; memory={selector.get('memory_confidence')}; "
        f"used={selector.get('memory_used')}; competitor_bias={selector.get('competitor_bias_used')}."
    )


def _competitor_strategy_summary(strategy: dict[str, Any]) -> str:
    if not strategy or strategy.get("status") in {"disabled", None}:
        return "Competitor strategy mode was not used for this run."
    if strategy.get("status") != "ready":
        return f"Status={strategy.get('status')}; no usable competitor strategy was extracted."
    extraction = strategy.get("strategy_extraction") or {}
    summary = strategy.get("input_summary") or {}
    patterns = extraction.get("strategic_patterns") or []
    return (
        f"Competitor={summary.get('competitor_name') or 'unnamed'}; "
        f"primary_family={extraction.get('primary_angle_family')}; "
        f"patterns={', '.join(str(item) for item in patterns[:3]) or 'none'}; "
        f"screenshots={summary.get('screenshot_count') or 0}."
    )


def _status_from_missing(missing: Any) -> str:
    return "warning" if missing else "pass"


def _guard_status(status: Any) -> str:
    value = str(status or "unknown")
    if value == "fail":
        return "blocked"
    return value


def _quality_status(quality: dict[str, Any]) -> str:
    export_status = quality.get("export_status")
    if export_status == "blocked":
        return "blocked"
    if export_status == "warning":
        return "warning"
    return "pass" if export_status == "approved" else "unknown"


def _generation_status(status: Any) -> str:
    value = str(status or "unknown")
    if value in {"completed", "partial", "skipped", "blocked", "failed", "passed"}:
        return value
    return "unknown"


def _guard_summary(payload: dict[str, Any], *keys: str) -> str:
    parts = []
    for key in keys:
        values = payload.get(key) or []
        if values:
            parts.append(f"{key}: {', '.join(str(item) for item in values[:4])}")
    if payload.get("recommended_fixes"):
        parts.append(f"fixes: {', '.join(payload.get('recommended_fixes')[:2])}")
    return "; ".join(parts) or "No blocking issues found."


def _compliance_summary(compliance: dict[str, Any]) -> str:
    keys = [
        "unsupported_claims",
        "fake_review_risks",
        "trademark_risks",
        "platform_policy_risks",
        "uk_market_risks",
    ]
    parts = []
    for key in keys:
        values = compliance.get(key) or []
        if values:
            parts.append(f"{key}: {', '.join(str(item) for item in values[:4])}")
    return "; ".join(parts) or "No blocking compliance issues found."


def _product_understanding_summary(understanding: dict[str, Any]) -> str:
    if not understanding:
        return "Automatic product understanding was not available."
    contexts = understanding.get("usage_contexts") or []
    return (
        f"Source={understanding.get('source', 'unknown')}; category={understanding.get('category')}; "
        f"material={understanding.get('material')}; position={understanding.get('market_position')}; "
        f"style={_truncate(understanding.get('style'), 90)}; audience={_truncate(understanding.get('target_audience'), 120)}; "
        f"contexts={', '.join(str(item) for item in contexts[:3])}."
    )


def _blocking_reasons(
    fidelity: dict[str, Any],
    compliance: dict[str, Any],
    static_images: dict[str, Any],
    video: dict[str, Any],
    quality: dict[str, Any],
    provider_validation: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if fidelity.get("product_fidelity_status") == "fail":
        reasons.append(_guard_summary(fidelity, "changed_or_invented_details", "missing_fidelity_instructions"))
    if compliance.get("compliance_status") == "fail":
        reasons.append(_compliance_summary(compliance))
    if quality.get("export_status") == "blocked":
        reasons.extend(str(item) for item in quality.get("recommended_improvements") or [])
    if static_images.get("image_generation_status") in {"blocked", "failed"}:
        reasons.append(static_images.get("failure_reason") or static_images.get("error") or "Static image generation failed.")
    if video.get("video_generation_status") in {"blocked", "failed"}:
        reasons.append(video.get("failure_reason") or video.get("error") or "Video generation failed.")
    if provider_validation.get("status") == "blocked":
        reasons.append(provider_validation.get("reason") or "Provider validation blocked generation.")
    return [reason for reason in reasons if reason]


def _warnings(
    product: dict[str, Any],
    fidelity: dict[str, Any],
    compliance: dict[str, Any],
    quality: dict[str, Any],
    prompts: dict[str, Any],
    static_images: dict[str, Any],
    video: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if product.get("missing_information"):
        warnings.append(f"Missing product info: {', '.join(product.get('missing_information'))}.")
    if fidelity.get("product_fidelity_status") == "warning":
        warnings.append(_guard_summary(fidelity, "changed_or_invented_details", "missing_fidelity_instructions"))
    if compliance.get("compliance_status") == "warning":
        warnings.append(_compliance_summary(compliance))
    if quality.get("export_status") == "warning":
        warnings.extend(str(item) for item in quality.get("recommended_improvements") or [])
    prompt_generation = prompts.get("prompt_generation") or {}
    if prompt_generation.get("status") in {"skipped", "failed"}:
        warnings.append(prompt_generation.get("error") or "Prompt model enhancement did not run; deterministic fallback was used.")
    if static_images.get("image_generation_status") == "skipped" and not static_images.get("skipped_by_generation_mode"):
        warnings.append(static_images.get("failure_reason") or "Static image generation was skipped.")
    if video.get("video_generation_status") == "skipped" and not video.get("skipped_by_generation_mode"):
        warnings.append(video.get("failure_reason") or "Video generation was skipped.")
    return [warning for warning in warnings if warning]


def _post_qa_warnings(post_qa: dict[str, Any]) -> list[str]:
    if not post_qa or post_qa.get("status") == "passed":
        return []
    result = []
    for check in post_qa.get("checks") or []:
        if check.get("status") in {"failed", "warning"}:
            result.append(f"Post QA {check.get('id')}: {check.get('message')}")
    return result[:8]


def _next_actions(final_output: dict[str, Any], blocking_reasons: list[str], warnings: list[str]) -> list[str]:
    static_images = final_output.get("static_image_generation") or {}
    video = final_output.get("video_generation") or {}
    seedance_payload = final_output.get("seedance_payload") or {}
    actions: list[str] = []
    if blocking_reasons:
        actions.append("Fix the listed blocking reasons, then generate again.")
    if static_images.get("image_generation_status") == "skipped" and not static_images.get("skipped_by_generation_mode"):
        actions.append("Add an OpenRouter API key or enable static image generation to create image assets.")
    if video.get("video_generation_status") == "skipped" and not video.get("skipped_by_generation_mode"):
        actions.append("Add an OpenRouter API key to submit the Seedance video payload.")
    if video.get("video_generation_status") == "failed":
        actions.append("Check OpenRouter video logs and the submitted Seedance payload prompt.")
    if seedance_payload.get("avatar_reference_mode") == "prompt_only_not_image_input":
        actions.append("For stronger own-person consistency, use a public avatar reference URL and enable image reference mode.")
    if not actions and warnings:
        actions.append("Review warnings, prompts, and generated assets before launching ads.")
    if not actions:
        actions.append("Review the UGC video, static image assets, carousel cards, and ad copy before uploading to the ad platform.")
    return actions


def _truncate(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
