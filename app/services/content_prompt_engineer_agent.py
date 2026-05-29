from __future__ import annotations

import os
import re
from typing import Any

from app import config
from app.services import finance_video_agent, prompt_defaults, scenario_contract
from app.services.avatar_authorization import AUTHORIZED_AVATAR_CONSENT_STATEMENT
from app.services.localization_utils import (
    language_copy_policy,
    language_safe_voice_descriptor,
    target_language_name,
)
from app.services.text_utils import sanitize_avatar_descriptor


NEGATIVE_PROMPT = prompt_defaults.NEGATIVE_PROMPT


def _is_czech(language: str) -> bool:
    value = str(language or "").lower()
    return value.startswith("cs") or value in {"cz", "czech"}


def _voice_profile(language: str, market: str) -> str:
    language_value = str(language or "").lower()
    market_value = str(market or "").upper()
    if language_value.startswith("en") and market_value in {"UK", "GB", "GBR"}:
        return (
            "natural British English creator voice with a subtle everyday British accent, "
            "British phrasing and spelling, relaxed conversational delivery, not American"
        )
    if language_value.startswith("en") and market_value in {"US", "USA"}:
        return "natural American English creator voice, relaxed conversational delivery"
    if _is_czech(language):
        return "natural Czech-only creator voice, cs-CZ pronunciation, Czech phrasing and sentence rhythm, relaxed conversational delivery"
    if language_value.startswith("de"):
        return "natural German creator voice, relaxed conversational delivery, German phrasing"
    return f"natural creator voice for market {market}, relaxed conversational delivery"


def _company_prompt_context(product_analysis: dict[str, Any], settings: dict[str, Any]) -> str:
    company = settings.get("company_profile") or product_analysis.get("company_profile") or {}
    if not company:
        return ""
    parts = []
    name = str(company.get("company_name") or company.get("name") or "").strip()
    ad_vertical = str(company.get("ad_vertical") or "").strip()
    business_model = str(company.get("business_model") or "").strip()
    audience = str(company.get("audience") or "").strip()
    positioning = str(company.get("positioning") or "").strip()
    brand_voice = str(company.get("brand_voice") or "").strip()
    creative_channels = company.get("creative_channels") or []
    proof_points = company.get("proof_points") or []
    forbidden_claims = company.get("forbidden_claims") or []
    quality_rules = company.get("creative_quality_rules") or []
    if name:
        parts.append(f"brand/client is {name}")
    if ad_vertical or business_model:
        parts.append(f"ad vertical {ad_vertical or 'general ads'}, business model {business_model or 'unspecified'}")
    if creative_channels:
        parts.append("channels: " + ", ".join(str(item) for item in creative_channels[:5]))
    if audience:
        parts.append(f"target audience: {audience}")
    if positioning:
        parts.append(f"positioning: {positioning}")
    if brand_voice:
        parts.append(f"voice: {brand_voice}")
    if proof_points:
        parts.append("proof moments to prefer: " + ", ".join(str(item) for item in proof_points[:5]))
    if quality_rules:
        parts.append("creative quality rules: " + ", ".join(str(item) for item in quality_rules[:5]))
    if forbidden_claims:
        parts.append("never imply: " + ", ".join(str(item) for item in forbidden_claims[:6]))
    return ". ".join(parts)[:900]


def generate_prompt_package(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    avatar: dict[str, Any],
    product_image_path: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    if finance_video_agent.is_finance_mode(settings):
        return _generate_finance_personal_brand_prompt_package(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            avatar=avatar,
            settings=settings,
        )
    model = settings.get("seedance_model") or os.getenv(
        "OPENROUTER_SEEDANCE_MODEL", config.OPENROUTER_SEEDANCE_MODEL
    )
    use_avatar_image_reference = bool(settings.get("use_avatar_image_reference", False))
    negative_prompt = settings.get("negative_prompt") or prompt_defaults.NEGATIVE_PROMPT
    base_video_prompt_template = (
        settings.get("base_video_prompt_template")
        or prompt_defaults.BASE_VIDEO_PROMPT_TEMPLATE
    )
    language = ugc_strategy["language"]
    market = ugc_strategy["market"]
    fidelity = _fidelity_instruction(product_analysis, product_image_path)
    avatar_instruction = _avatar_instruction(avatar, use_avatar_image_reference, language)
    scene_avatar_instruction = _scene_avatar_instruction(avatar, use_avatar_image_reference, language)
    avatar_identity_contract = _avatar_identity_contract(avatar, use_avatar_image_reference, language)
    duration = ugc_strategy["duration_seconds"]
    aspect_ratio = ugc_strategy["aspect_ratio"]
    platform = ugc_strategy["platform"]
    voice_profile = _language_safe_voice_profile(
        ugc_strategy.get("voice_profile") or _voice_profile(language, market),
        language,
        market,
    )
    platform_copy = _platform_copy(language, product_analysis["product_name"])
    user_scenario_lock = ugc_strategy.get("user_scenario_lock") or {}
    user_scenario_contract = scenario_contract.build(
        user_scenario_lock,
        avatar=avatar,
        product_analysis=product_analysis,
    )
    category_prompt_directive = _category_prompt_directive(product_analysis, settings, user_scenario_contract)
    scene_chaining = ugc_strategy.get("scene_chaining") or settings.get("scene_chaining") or {}
    scene_chaining_addendum = _clean_inline(scene_chaining.get("seedance_prompt_addendum") or "")
    voice_personality = ugc_strategy.get("voice_personality") or settings.get("voice_personality") or {}
    company_prompt = _company_prompt_context(product_analysis, settings)
    creative_memory_guidance = (
        ugc_strategy.get("creative_memory_rag")
        or settings.get("creative_memory_guidance")
        or (settings.get("performance_insights") or {}).get("creative_memory_rag")
        or {}
    )
    learning_guidance = _creative_memory_prompt_guidance(creative_memory_guidance)
    video_extra_prompt = _video_extra_prompt_directive(
        settings.get("ugc_video_extra_prompt") or "",
        product_analysis,
    )
    mirror_selfie_lock = _is_mirror_selfie_scenario_lock(user_scenario_lock)
    if mirror_selfie_lock:
        category_prompt_directive = _mirror_selfie_category_prompt_directive(
            product_analysis,
            category_prompt_directive,
        )
    environment_control = _environment_control(settings)
    if mirror_selfie_lock:
        environment_control = {
            **environment_control,
            "environment_selection": "user_scenario_mirror_selfie",
            "directive": _mirror_selfie_environment_control_directive(),
        }
    environment_control_directive = (
        _mirror_selfie_environment_control_directive()
        if mirror_selfie_lock
        else _environment_control_directive(environment_control)
    )
    subtitle_contract = _subtitle_contract(ugc_strategy, language, platform)
    hook_sticker = _hook_sticker_text(ugc_strategy)

    video_prompt = base_video_prompt_template.format(
        duration=duration,
        platform=platform,
        language=language,
        market=market,
        fidelity=fidelity,
        avatar_instruction=avatar_instruction,
        voiceover=ugc_strategy["voiceover"],
        voice_profile=voice_profile,
        scene_summary=_scene_summary(ugc_strategy["scene_by_scene_script"]),
        aspect_ratio=aspect_ratio,
        category_prompt=category_prompt_directive,
        environment_control=environment_control_directive,
        video_extra_prompt=video_extra_prompt,
        negative_prompt=negative_prompt,
    )
    if mirror_selfie_lock:
        video_prompt = _apply_mirror_selfie_prompt_lock(video_prompt)
    if subtitle_contract and subtitle_contract not in video_prompt:
        video_prompt = f"{video_prompt} No generated text contract: {subtitle_contract}"
    if category_prompt_directive and category_prompt_directive not in video_prompt:
        video_prompt = f"{video_prompt} Category-specific product prompt: {category_prompt_directive}"
    if scene_chaining_addendum and scene_chaining_addendum not in video_prompt:
        video_prompt = f"{video_prompt} {scene_chaining_addendum}"
    if learning_guidance and learning_guidance not in video_prompt:
        video_prompt = f"{video_prompt} Creative memory guidance: {learning_guidance}"
    if company_prompt and company_prompt not in video_prompt:
        video_prompt = f"{video_prompt} Brand ads context: {company_prompt}"
    if environment_control_directive and environment_control_directive not in video_prompt:
        video_prompt = f"{video_prompt} Environment control: {environment_control_directive}"
    ugc_prompt_skill = _ugc_prompt_skill_directive(ugc_strategy)
    if ugc_prompt_skill and ugc_prompt_skill not in video_prompt:
        video_prompt = f"{video_prompt} Creator prompt skill guidance: {ugc_prompt_skill}"
    if video_extra_prompt and video_extra_prompt not in video_prompt:
        video_prompt = f"{video_prompt} Extra UGC video direction: {video_extra_prompt}"
    scenario_lock_prompt = _user_scenario_lock_directive(user_scenario_lock)
    if scenario_lock_prompt and scenario_lock_prompt not in video_prompt:
        video_prompt = f"{video_prompt} User scenario lock: {scenario_lock_prompt}"
    scenario_contract_prompt = scenario_contract.video_prompt_lock(user_scenario_contract)
    if scenario_contract_prompt and scenario_contract_prompt not in video_prompt:
        video_prompt = f"{video_prompt} Approved scenario contract: {scenario_contract_prompt}"
    language_hard_lock = _language_hard_lock_prompt(language)
    if language_hard_lock and language_hard_lock not in video_prompt:
        video_prompt = f"{video_prompt} {language_hard_lock}"
    prompt_package = {
        "agent": "Content Prompt Engineer Agent",
        "product_fidelity_instruction": fidelity,
        "avatar_consistency_instruction": avatar_instruction,
        "avatar_scene_instruction": scene_avatar_instruction,
        "avatar_identity_contract": avatar_identity_contract,
        "voice_profile": voice_profile,
        "customer_language_name": target_language_name(language),
        "language_copy_policy": language_copy_policy(language),
        "voice_personality": voice_personality,
        "brand_ads_context": settings.get("company_profile") or product_analysis.get("company_profile") or {},
        "company_prompt_context": company_prompt,
        "creative_memory_guidance": creative_memory_guidance,
        "scene_chaining": scene_chaining,
        "ugc_prompt_skill": ugc_strategy.get("ugc_prompt_skill"),
        "user_scenario_lock": user_scenario_lock,
        "user_scenario_contract": user_scenario_contract,
        "category_prompt_directive": category_prompt_directive,
        "environment_control": environment_control,
        "environment_control_directive": environment_control_directive,
        "ecommerce_hook_text_mode": {
            "enabled": False,
            "mode": "spoken_hook_only",
            "spoken_hook": hook_sticker,
            "text": "",
            "duration": "not rendered in generated video",
            "style": "post-production captions only; provider must not draw text",
            "forbidden": "no hook sticker, no subtitles, no lower thirds, no captions, no random text",
        },
        "subtitle_contract": subtitle_contract,
        "speech_language_contract": _speech_language_contract(language, market),
        "ugc_video_extra_prompt": video_extra_prompt,
        "negative_prompt": negative_prompt,
        "seedance_video_prompt": video_prompt,
        "structured_scene_prompt": _structured_scene_fallback(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            avatar_instruction=avatar_instruction,
            scene_avatar_instruction=scene_avatar_instruction,
            fidelity=fidelity,
            aspect_ratio=aspect_ratio,
            duration=duration,
            platform=platform,
            market=market,
            language=language,
            use_avatar_image_reference=use_avatar_image_reference,
            scene_chaining=scene_chaining,
            environment_control=environment_control,
        ),
        "product_closeup_prompt": (
            f"Generate product close-up shots using {product_image_path} as the strict visual reference. "
            f"Show only visible details from the reference. {fidelity} Negative prompt: {negative_prompt}"
        ),
        "thumbnail_cover_image_prompt": (
            f"Create a clean paid-social cover image with the product from {product_image_path} as the strict reference, "
            f"avatar consistent with {avatar.get('name', 'selected avatar')}, readable text: '{ugc_strategy['on_screen_text'][0]}'. "
            f"Do not alter the product. Negative prompt: {negative_prompt}"
        ),
        "voiceover_tts_prompt": (
            f"Read in a natural creator voice, {language}, market {market}. Voice profile: {voice_profile}. "
            "Avoid hype and testimonial claims. "
            f"Script: {ugc_strategy['voiceover']}"
        ),
        "subtitle_prompt": (
            f"Do not ask Seedance to render subtitles or captions inside the generated ecommerce video. "
            f"The hook should be spoken aloud by the avatar, not rendered as text. "
            f"For post-production only, create concise {language} captions from the approved scene voiceover: {ugc_strategy.get('subtitles', [])}. "
            f"Keep each caption under 8 words, same language, no invented claims, no product notes, no click/tap/button/URL wording, safe for {platform} UI."
        ),
        "on_screen_text_prompt": (
            f"Seedance must render no generated on-screen text for ecommerce UGC video. "
            f"Treat planned on_screen_text as post-production metadata only: {ugc_strategy['on_screen_text']}. "
            f"No hook sticker, subtitles, lower thirds, CTA text, random words, or later-scene generated text; captions can be added after generation for {platform}."
        ),
        "meta_ads_copy": platform_copy["meta_ads_copy"],
        "google_youtube_ads_copy": platform_copy["google_youtube_ads_copy"],
        "ab_testing_variation_prompts": [
            f"Variation A: lead with product close-up in first second. {fidelity} Negative prompt: {negative_prompt}",
            f"Variation B: lead with avatar holding or wearing the product; the hook is spoken aloud, with no generated on-screen text. {fidelity} Negative prompt: {negative_prompt}",
            f"Variation C: lead with everyday context shot while keeping product unchanged. {fidelity} Negative prompt: {negative_prompt}",
        ],
    }
    prompt_package["seedance_payload"] = {
        "model": model,
        "prompt": video_prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": settings.get("resolution", "720p"),
        "generate_audio": True,
        "audio_language_instruction": _audio_language_instruction(language, market),
        "product_image_path": product_image_path,
        "avatar_image_path": avatar.get("image_path"),
        "avatar_image_url": avatar.get("image_url"),
        "avatar_reference_mode": (
            "exact_image_input_reference"
            if use_avatar_image_reference
            else "prompt_only_not_image_input"
        ),
        "avatar_identity_contract": avatar_identity_contract,
        "negative_prompt": negative_prompt,
        "category_prompt_directive": category_prompt_directive,
        "environment_control": environment_control,
        "environment_control_directive": environment_control_directive,
        "ugc_video_extra_prompt": video_extra_prompt,
        "user_scenario_lock": user_scenario_lock,
        "scene_chaining": scene_chaining,
        "voice_personality": voice_personality,
    }
    speech_language = _target_speech_language(language)
    if speech_language:
        prompt_package["seedance_payload"]["speech_language"] = speech_language
    input_references = [ref for ref in settings.get("input_references", []) if ref]
    if input_references:
        prompt_package["seedance_payload"]["input_references"] = input_references
    frame_images = [ref for ref in settings.get("frame_images", []) if ref]
    if frame_images:
        prompt_package["seedance_payload"]["frame_images"] = frame_images
        prompt_package["seedance_payload"]["approved_scene_reference_usage"] = (
            "public approved scene concept also sent as frame_images/reference guidance when provider supports it"
        )
    return prompt_package


def _generate_finance_personal_brand_prompt_package(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    avatar: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    model = settings.get("seedance_model") or os.getenv(
        "OPENROUTER_SEEDANCE_MODEL", config.OPENROUTER_SEEDANCE_MODEL
    )
    use_avatar_image_reference = bool(settings.get("use_avatar_image_reference", False))
    negative_prompt = settings.get("negative_prompt") or prompt_defaults.NEGATIVE_PROMPT
    avatar_instruction = _avatar_instruction(avatar, use_avatar_image_reference, "cs")
    scene_avatar_instruction = _scene_avatar_instruction(avatar, use_avatar_image_reference, "cs")
    avatar_identity_contract = _avatar_identity_contract(avatar, use_avatar_image_reference, "cs")
    duration = int(ugc_strategy["duration_seconds"])
    aspect_ratio = ugc_strategy["aspect_ratio"]
    platform = ugc_strategy["platform"]
    market = ugc_strategy["market"]
    language = "cs"
    voice_profile = ugc_strategy.get("voice_profile") or _voice_profile(language, market)
    disclaimer = (ugc_strategy.get("finance_compliance") or {}).get(
        "disclaimer", finance_video_agent.DEFAULT_FINANCE_DISCLAIMER
    )
    scene_concept = settings.get("finance_scene_concept") or ugc_strategy.get("finance_scene_concept") or {}
    fidelity = (
        "No physical ecommerce product in this mode. Preserve factual finance content, avatar identity, "
        "personal brand tone, strict Czech language, readable captions, and compliance disclaimer. "
        "All spoken words, subtitles, and infographic labels must be high-quality Czech with Czech diacritics; "
        "no Polish, Slovak, English filler, mixed-language text, or machine-translated Slavic wording. "
        "Do not invent returns, client results, certifications, performance numbers, fees, tax/legal facts, "
        "or promised outcomes. Do not present individualized financial advice."
    )
    scene_summary = _scene_summary(ugc_strategy["scene_by_scene_script"])
    video_prompt = _finance_video_prompt(
        ugc_strategy=ugc_strategy,
        avatar_instruction=avatar_instruction,
        scene_summary=scene_summary,
        scene_concept=scene_concept,
        disclaimer=disclaimer,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
        platform=platform,
        market=market,
        duration=duration,
    )
    structured_scene_prompt = _structured_finance_scene_prompt(
        ugc_strategy=ugc_strategy,
        scene_avatar_instruction=scene_avatar_instruction,
        fidelity=fidelity,
        use_avatar_image_reference=use_avatar_image_reference,
        scene_concept=scene_concept,
    )
    platform_copy = {
        "meta_ads_copy": {
            "primary_text": "Krátké finanční vysvětlení bez slibů výnosů. Vzdělávací obsah, ne individuální doporučení.",
            "headline": "Finančně jednoduše",
            "description": "Osobní brand video.",
        },
        "google_youtube_ads_copy": {
            "headline": "Finanční téma jednoduše",
            "description": "Vzdělávací video bez garancí a bez individuálního doporučení.",
            "cta": "handled_by_ad_platform",
        },
    }
    prompt_package = {
        "agent": "Finance Personal Brand Prompt Engineer",
        "creative_mode": "finance_personal_brand",
        "product_fidelity_instruction": fidelity,
        "avatar_consistency_instruction": avatar_instruction,
        "avatar_scene_instruction": scene_avatar_instruction,
        "avatar_identity_contract": avatar_identity_contract,
        "voice_profile": voice_profile,
        "speech_language_contract": {
            "spoken_language": "cs-CZ",
            "audio_voice": "Czech only",
            "lip_sync": "sync lips to Czech voiceover only",
            "forbidden_audio": "no English, Polish, Slovak, mixed Slavic, machine-translated accent, or non-Czech filler words",
        },
        "voice_personality": ugc_strategy.get("voice_personality") or {},
        "creative_memory_guidance": settings.get("creative_memory_guidance") or {},
        "finance_scene_concept": scene_concept,
        "scene_chaining": settings.get("scene_chaining") or {},
        "category_prompt_directive": "Finance personal brand mode: Czech-only educational finance ad from a modern podcast studio, interactive premium infographics, and strict compliance guardrails.",
        "environment_control": _environment_control(settings),
        "environment_control_directive": "Use a modern podcast studio by default: desk microphone or boom arm, acoustic panels, warm key light, subtle LED accents, expert interview setup. Do not create fake financial institution branding.",
        "ugc_video_extra_prompt": _video_extra_prompt_directive(settings.get("ugc_video_extra_prompt") or ""),
        "negative_prompt": negative_prompt,
        "seedance_video_prompt": video_prompt,
        "structured_scene_prompt": structured_scene_prompt,
        "product_closeup_prompt": "Not applicable in finance personal brand mode.",
        "thumbnail_cover_image_prompt": "Not applicable in finance personal brand mode.",
        "voiceover_tts_prompt": f"Read in clean standard Czech with Czech diacritics, calm finance educator voice, no Polish or Slovak phrasing. Script: {ugc_strategy['voiceover']}",
        "subtitle_prompt": "Create concise Czech subtitles with Czech diacritics only. Keep finance disclaimer readable.",
        "on_screen_text_prompt": f"Place modern Czech finance infographic overlays inside safe areas: {ugc_strategy['on_screen_text']}. Make overlays react subtly to creator gaze, pointing, and air-tap gestures. Use no Polish, Slovak, or mixed-language text.",
        "meta_ads_copy": platform_copy["meta_ads_copy"],
        "google_youtube_ads_copy": platform_copy["google_youtube_ads_copy"],
        "ab_testing_variation_prompts": [],
    }
    prompt_package["seedance_payload"] = {
        "model": model,
        "prompt": video_prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": settings.get("resolution", "720p"),
        "product_image_path": "finance_personal_brand_no_product_reference",
        "avatar_image_path": avatar.get("image_path"),
        "avatar_image_url": avatar.get("image_url"),
        "avatar_reference_mode": (
            "exact_image_input_reference"
            if use_avatar_image_reference
            else "prompt_only_not_image_input"
        ),
        "avatar_identity_contract": avatar_identity_contract,
        "negative_prompt": negative_prompt,
        "creative_mode": "finance_personal_brand",
        "finance_disclaimer": disclaimer,
        "generate_audio": True,
        "speech_language": "cs-CZ",
        "audio_language_instruction": "Avatar must speak Czech only. Generate audio and lip-sync in natural Czech, no English, Polish, Slovak, or mixed-language speech.",
    }
    input_references = [ref for ref in settings.get("input_references", []) if ref]
    if input_references:
        prompt_package["seedance_payload"]["input_references"] = input_references
    frame_images = [ref for ref in settings.get("frame_images", []) if ref]
    if frame_images:
        prompt_package["seedance_payload"]["frame_images"] = frame_images
        prompt_package["seedance_payload"]["approved_scene_reference_usage"] = (
            "public approved scene concept also sent as frame_images/reference guidance when provider supports it"
        )
    series_plan = ugc_strategy.get("finance_video_series") or {}
    episodes = series_plan.get("episodes") or []
    if series_plan.get("confirmed") and len(episodes) > 1:
        series_payloads = []
        for episode in episodes:
            episode_strategy = _episode_strategy(
                base_strategy=ugc_strategy,
                episode=episode,
                disclaimer=disclaimer,
            )
            episode_prompt = _finance_video_prompt(
                ugc_strategy=episode_strategy,
                avatar_instruction=avatar_instruction,
                scene_summary=_scene_summary(episode_strategy["scene_by_scene_script"]),
                scene_concept=scene_concept,
                disclaimer=disclaimer,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                platform=platform,
                market=market,
                duration=int(episode.get("duration_seconds") or finance_video_agent.DEFAULT_SERIES_SECONDS),
            )
            payload = {
                **prompt_package["seedance_payload"],
                "prompt": episode_prompt,
                "duration": int(episode.get("duration_seconds") or finance_video_agent.DEFAULT_SERIES_SECONDS),
                "series_episode": episode.get("position"),
                "series_total": episode.get("total"),
                "series_title": episode.get("title"),
            }
            series_payloads.append(payload)
        prompt_package["seedance_series_payloads"] = series_payloads
        prompt_package["finance_video_series"] = series_plan
    return prompt_package


def _finance_video_prompt(
    *,
    ugc_strategy: dict[str, Any],
    avatar_instruction: str,
    scene_summary: str,
    scene_concept: dict[str, Any] | None = None,
    disclaimer: str,
    negative_prompt: str,
    aspect_ratio: str,
    platform: str,
    market: str,
    duration: int,
) -> str:
    scene_lock = _finance_scene_concept_prompt(scene_concept or {})
    return (
        f"Seedance image-to-video personal brand finance ad video for Meta Ads and Instagram, not UGC, Aspect ratio {aspect_ratio}, "
        f"{aspect_ratio} vertical orientation, {duration}s duration, platform {platform}, market {market}, language Czech. "
        f"{avatar_instruction}. Avatar reference image is the strict visual reference for creator identity when supplied. "
        "Creator speaks directly to camera as a trustworthy Czech finance educator in a modern podcast studio. "
        "SPOKEN AUDIO REQUIREMENT: the on-camera avatar must speak only Czech. Generate voice/audio in natural Czech, with Czech pronunciation and Czech sentence rhythm. "
        "Lip-sync must match the Czech voiceover exactly; do not translate, dub, paraphrase, or switch to English, Polish, Slovak, or mixed-language speech. "
        f"Voiceover must be clean standard Czech with Czech diacritics and follow this approved script exactly: \"{ugc_strategy['voiceover']}\". "
        "CZECH LANGUAGE HARD LOCK: every spoken word, subtitle, lower third, chart label, card label, and visible text must be Czech with Czech diacritics. "
        "Never use Polish, Slovak, English filler, mixed-language subtitles, malformed Slavic words, or pseudo-Czech. If readable text is uncertain, use abstract card shapes without legible wrong-language text. "
        f"{scene_lock} "
        f"Visual direction: {scene_summary}. Default environment: modern podcast studio, desk microphone or boom arm visible, "
        "acoustic panels, warm key light, subtle LED accent, expert interview setup, premium but realistic. "
        "Add modern premium interactive infographics that follow the approved scene blueprint: animated lower thirds, kinetic Czech typography, glassmorphism finance cards, simple line charts, "
        "timeline cards, checklist bullets, subtle financial icons, transparent overlays, smooth motion, readable Czech labels. "
        "The creator should interact with the infographics naturally: look toward a card, point beside the body, lightly tap or swipe in the air, then the relevant card highlights, slides, ticks, or advances in sync with the gesture and voiceover. "
        "Keep all interaction subtle and physically plausible, like a presenter explaining a screen in a podcast studio; central safe area, no clutter, no fake platform UI, no bank logos unless provided. "
        f"Compliance: {disclaimer}. Avoid outcome promises, risk-free wording, invented numbers, individualized advice, "
        "no pressure to buy now. Personal brand ad style, polished but human, realistic face and lip sync, "
        "locked medium close-up or slow push-in, hands visible when gesturing, subtle camera movement, podcast-studio background continuity. "
        f"Negative prompt: {negative_prompt}"
    )


def _finance_scene_concept_prompt(scene_concept: dict[str, Any]) -> str:
    if not scene_concept:
        return ""
    compiled = str(scene_concept.get("video_prompt_addendum_compiled") or "").strip()
    if compiled:
        return compiled[:2600]
    parts = [
        "APPROVED FINANCE SCENE BLUEPRINT: reuse the approved podcast-studio scene concept for layout, lighting, infographic placement, and gesture timing.",
        f"Visual brief: {scene_concept.get('visual_brief')}",
        f"Infographic system: {scene_concept.get('infographic_system')}",
        f"Infographic elements: {scene_concept.get('infographic_elements')}",
        f"Gesture sync: {scene_concept.get('interaction_plan')}",
    ]
    return _clean_inline(" ".join(str(part) for part in parts if part))[:2600]


def _episode_strategy(
    *,
    base_strategy: dict[str, Any],
    episode: dict[str, Any],
    disclaimer: str,
) -> dict[str, Any]:
    script = str(episode.get("script") or "").strip()
    chunks = finance_video_agent._script_chunks(script, 3)  # noqa: SLF001 - local prompt compiler helper
    overlays = [
        finance_video_agent._clip_words(str(episode.get("title") or "Finance video"), 5),  # noqa: SLF001
        "Jednoduše a přehledně",
        finance_video_agent._clip_words(disclaimer, 6),  # noqa: SLF001
    ]
    scenes = []
    for index, chunk in enumerate(chunks[:3]):
        voiceover = chunk
        if index == 2 and disclaimer.lower() not in voiceover.lower():
            voiceover = f"{voiceover} {disclaimer}"
        scenes.append(
            {
                "time": ["0-5s", "5-10s", "10-15s"][index],
                "visual": [
                    "creator opens the episode from a modern podcast studio with direct camera delivery, glances toward an animated Czech headline card, and points to its first keyword",
                    "creator explains one finance idea from the podcast desk while modern infographic cards build beside the face and highlight when the creator air-taps toward them",
                    "creator closes the episode in the same podcast studio with a calm summary, small hand cue, and visible Czech disclaimer lower third sliding in after the cue",
                ][index],
                "voiceover": voiceover,
                "on_screen_text": overlays[index],
                "subtitle": voiceover,
                "shot_type": ["personal brand hook", "infographic explainer", "compliant close"][index],
                "psychology_step": ["hook", "education", "cta"][index],
            }
        )
    return {
        **base_strategy,
        "duration_seconds": int(episode.get("duration_seconds") or finance_video_agent.DEFAULT_SERIES_SECONDS),
        "hook": chunks[0] if chunks else script,
        "scene_by_scene_script": scenes,
        "voiceover": " ".join(scene["voiceover"] for scene in scenes),
        "on_screen_text": overlays,
        "subtitles": [scene["subtitle"] for scene in scenes],
    }


def _creative_memory_prompt_guidance(guidance: dict[str, Any]) -> str:
    if not guidance:
        return ""
    text = _clean_inline(guidance.get("prompt_guidance") or "")
    if text:
        return text
    winners = guidance.get("winning_patterns") or []
    avoid = guidance.get("avoid_patterns") or []
    parts = []
    if winners:
        parts.append("prefer " + ", ".join(str(item) for item in winners[:5]))
    if avoid:
        parts.append("avoid " + ", ".join(str(item) for item in avoid[:5]))
    return _clean_inline("; ".join(parts))


def _video_extra_prompt_directive(
    value: str,
    product_analysis: dict[str, Any] | None = None,
) -> str:
    text = _clean_inline(value)[:900]
    if not text:
        return ""
    text = _sanitize_apparel_generic_fabric_words(text, product_analysis)
    specific_environment = bool(
        re.search(
            r"\b(mirror selfie|simple bedroom|bedroom|simple room|neutral wall|zrcad|ložnic|loznic|pokoj|neutralni stena|neutrální stěna)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    environment_rule = (
        "When this note specifies a mirror, bedroom, room, or neutral wall, that specific setting overrides the normal automatic location selection"
        if specific_environment
        else "Do not use it to copy the avatar reference background or to create a random room; the environment is category-auto unless the user explicitly requests a specific setting"
    )
    return (
        "Do not alter product colour, shape, logo, material, packaging, "
        "or avatar identity unless that exact change is explicitly supported by the provided product facts. "
        f"{text}. Apply this only as video scene direction, motion, timing, lighting, camera behaviour, "
        f"or creator reaction guidance. {environment_rule}"
    )


def _sanitize_apparel_generic_fabric_words(
    text: str,
    product_analysis: dict[str, Any] | None,
) -> str:
    product_analysis = product_analysis or {}
    category = str(product_analysis.get("likely_product_category") or "").strip().lower()
    known_facts = product_analysis.get("known_product_facts") or {}
    material = str(known_facts.get("material") or "").strip().lower() if isinstance(known_facts, dict) else ""
    if category != "apparel" or (material and material != "unknown"):
        return text
    # For apparel, a user often says "fabric" as plain garment handling. Keep
    # specific material words such as silk/cotton/polyester intact for the guard.
    return re.sub(r"\bfabric\b", "garment", text, flags=re.IGNORECASE)


def _user_scenario_lock_directive(value: dict[str, Any]) -> str:
    if not isinstance(value, dict) or not value.get("enabled"):
        return ""
    parts = [
        value.get("priority"),
        f"template={value.get('template_id')}" if value.get("template_id") else "",
        f"spoken_hook={value.get('hook_text')}" if value.get("hook_text") else "",
        f"user_direction={value.get('raw_user_direction')}" if value.get("raw_user_direction") else "",
        value.get("compiled_direction"),
        (
            "mirror_selfie_hard_lock: use one simple bedroom mirror reflection setup; smartphone must be visibly held in the creator's hand; "
            "keep the phone low or to the side while speaking so the mouth remains visible; "
            "use normal smartphone 9:16 framing with natural body proportions and no stretched mirror reflection; "
            "the camera source is only the iPhone mirror-selfie recording for the entire duration; "
            "do not use non-bedroom/public/work/outdoor locations, tripod, external-camera, ordinary talking-head setup, third-person camera, side filming, over-the-shoulder shot, room camera, observer camera, cinematic b-roll, cutaway, product-only insert, perspective switch, phone covering the mouth, fisheye, ultra-wide distortion, or body warping; "
            "do not start with a frozen still frame; first frame should already have tiny phone sway, blink, mouth movement, or a small hand gesture"
            if value.get("template_id") == "mirror_selfie_try_on_review"
            else ""
        ),
        "forbidden: " + "; ".join(str(item) for item in (value.get("forbidden") or [])[:4])
        if value.get("forbidden")
        else "",
    ]
    return _clean_inline(" ".join(str(part) for part in parts if part))[:1100]


def _is_mirror_selfie_scenario_lock(value: dict[str, Any]) -> bool:
    return (
        isinstance(value, dict)
        and bool(value.get("enabled"))
        and value.get("template_id") == "mirror_selfie_try_on_review"
    )


def _mirror_selfie_environment_lock_text() -> str:
    return (
        "one simple bedroom mirror-selfie setup only: plain neutral wall, minimal background, visible mirror reflection, "
        "creator films herself through the mirror with smartphone visibly held in one hand inside the reflection, low or to the side while speaking so the mouth remains visible, "
        "normal smartphone 9:16 framing, natural human proportions, no mirror stretch or fisheye distortion, natural indoor daylight or soft room light, slight handheld phone shake, ordinary home atmosphere, "
        "continuous mirror perspective only, no scene changes, no perspective changes, no external camera, no tripod, no side filming, no over-the-shoulder shot, no room camera, no cinematic b-roll, no cutaways"
    )


def _mirror_selfie_environment_control_directive() -> str:
    return _clean_inline(
        "background_consistency=strict, environment_override=false, environment_selection=user_scenario_mirror_selfie; "
        f"{_mirror_selfie_environment_lock_text()}; this user-approved mirror setup overrides the normal automatic location examples; "
        "no non-bedroom/public/work/outdoor location, no secondary room setup, no studio, no tripod, no external camera, no third-person operator, no ordinary front-facing talking-head setup, no side camera, no back shot, no avatar walking away from the mirror, no phone covering the mouth during speech, no fisheye or stretched body proportions"
    )


def _mirror_selfie_category_prompt_directive(
    product_analysis: dict[str, Any],
    previous_directive: str,
) -> str:
    category = str(product_analysis.get("likely_product_category") or "").strip().lower()
    product_name = str(product_analysis.get("product_name") or "the product").strip()
    classifier = _visual_classifier_prompt_directive(product_analysis)
    apparel_detail = (
        f"Show {product_name} worn on the creator from the first beat: full-body or near full-body head-to-toe reflected outfit view, normal adult body proportions, garment length, waist, neckline, hem, drape, cut, and body-to-garment scale visible. "
        "The free hand naturally points to waist, neckline, cut, drape, and overall silhouette while the other hand keeps the phone visible but not over the speaking mouth."
        if category == "apparel"
        else f"Show {product_name} naturally in the same mirror-reflection buyer-check setup, held, worn, or used only when that matches the product category."
    )
    return _clean_inline(
        "Mirror-selfie try-on preset: user-approved mirror scene overrides normal location examples from the category preset. "
        f"{_mirror_selfie_environment_lock_text()}. "
        f"{apparel_detail} "
        "The avatar must visibly speak on-camera in the mirror reflection with natural lip, jaw, cheek, and expression movement; do not make it feel like audio laid over a silent try-on. "
        "Opening anti-freeze rule: first frame must already feel live, with tiny phone sway, blink, mouth/jaw beginning the spoken hook, or a small free-hand movement; no still poster frame or frozen face at the start. "
        "Camera lock: keep mirror-selfie perspective for the entire duration; never switch to third-person, external, side, over-the-shoulder, back-view, room-camera, tripod, observer, b-roll, cutaway, product-only insert, or fashion-commercial angles. "
        "The avatar must not walk away from the mirror or turn fully back; only a partial side-turn is allowed while still facing the mirror. "
        "Keep proportions like a normal smartphone mirror selfie: no wide-angle stretch, no warped mirror, no elongated limbs, no squeezed body, no cropped/letterboxed aspect ratio. "
        "Keep the real product reference unchanged; do not invent fit, sizing, comfort, body outcome, material, or quality claims. "
        "No non-bedroom/public/work/outdoor location, luxury setup, studio setup, tripod, external-camera framing, product-only insert, face/chest-only crop, frozen face, closed-mouth speech, or phone covering the mouth. "
        f"{classifier}"
    ) or previous_directive


def _apply_mirror_selfie_prompt_lock(prompt: str) -> str:
    text = str(prompt or "")
    mirror_environment = (
        "User-approved mirror selfie environment lock: "
        f"{_mirror_selfie_environment_lock_text()}. "
        "This overrides all normal automatic location examples; do not select any public, work, outdoor, studio, tripod, external-camera, third-person setup, side filming, b-roll, cutaway, perspective switch, or phone-over-mouth composition. Start with live motion, not a frozen still frame."
    )
    avatar_environment = (
        "Avatar identity-only lock: the avatar reference image controls creator identity, face consistency, expression dynamics, and approved wardrobe policy only. "
        "Do not copy the avatar reference background, furniture, wall decor, lighting setup, camera crop, props, or lifestyle context. "
        f"For this user-approved mirror selfie scenario, the generated environment is locked to {_mirror_selfie_environment_lock_text()}. During spoken lines, the face and mouth must stay visible and actively speaking; first frame and each new segment should show live phone sway, blink, mouth movement, or hand movement, not a frozen hold."
    )
    text = text.replace(prompt_defaults.CATEGORY_AUTO_ENVIRONMENT_LOCK, mirror_environment)
    text = text.replace(prompt_defaults.AVATAR_IDENTITY_ONLY_ENVIRONMENT_LOCK, avatar_environment)
    text = text.replace(
        "Use the avatar reference image only when use_reference_image is true and only for identity. Use the product reference image for strict product fidelity only; choose environment from product category/context.",
        "Use the avatar reference image only when use_reference_image is true and only for identity. Use the product reference image for strict product fidelity only; keep the user-approved mirror selfie bedroom environment locked.",
    )
    if "MIRROR SELFIE HARD LOCK" not in text:
        text = f"MIRROR SELFIE HARD LOCK: {mirror_environment} {text}"
    return _clean_inline(text)


def _subtitle_contract(ugc_strategy: dict[str, Any], language: str, platform: str) -> str:
    subtitles = [
        _clean_inline(str(item))
        for item in (ugc_strategy.get("subtitles") or [])
        if _clean_inline(str(item))
    ]
    joined = " | ".join(subtitles[:4]) if subtitles else ""
    spoken_hook = _hook_sticker_text(ugc_strategy)
    return _clean_inline(
        f"Render no generated text inside the ecommerce creator video for {platform}: no hook sticker, subtitles, lower thirds, CTA text, floating text, platform UI, prompt labels, random words, title cards, or later-scene captions. "
        f"The opening hook should be spoken aloud by the avatar, not drawn as text{f': {spoken_hook}' if spoken_hook else ''}. "
        f"Spoken audio in {language} carries the message; captions should be added later in post-production where typography and safe area can be controlled. "
        f"Approved spoken fragments for later post-production captioning: {joined}. "
        "The only other visible words allowed in the generated video are verified product markings already present on the reference or an exact requested personalization word printed on the product."
    )


def _hook_sticker_text(ugc_strategy: dict[str, Any]) -> str:
    candidates: list[Any] = []
    for key in ["on_screen_text", "subtitles"]:
        value = ugc_strategy.get(key)
        if isinstance(value, list) and value:
            candidates.append(value[0])
    candidates.append(ugc_strategy.get("hook"))
    for value in candidates:
        text = _clean_inline(str(value or ""))
        if text and not _looks_like_internal_text(text):
            return " ".join(text.split()[:8])
    return ""


def _looks_like_internal_text(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    markers = [
        "angle:",
        "hook intent",
        "visual direction",
        "voiceover=",
        "on_screen_text",
        "structured prompt",
        "product_rules",
        "i'd show",
        "i would show",
        "i'd check",
        "i would check",
    ]
    return any(marker in normalized for marker in markers)


def _ugc_prompt_skill_directive(ugc_strategy: dict[str, Any]) -> str:
    guidance = ugc_strategy.get("ugc_prompt_skill")
    if not isinstance(guidance, dict) or not guidance:
        return ""
    prompt_rules = guidance.get("prompt_rules") or {}
    beats = guidance.get("beat_structure") or []
    visual = guidance.get("visual_classifier") or {}
    avoid_words = prompt_rules.get("avoid_words") or []
    parts = [
        f"use {guidance.get('template_name') or guidance.get('template_id')} from local claude-arcads creative rules; Arcads API is not used",
        (
            "visual classifier guidance: "
            + "; ".join(str(item) for item in (visual.get("shot_requirements") or [])[:4])
            if visual.get("status") == "completed" and visual.get("shot_requirements")
            else ""
        ),
        prompt_rules.get("no_generated_text") or "",
        prompt_rules.get("realism") or "",
        f"beat order: {' / '.join(str(beat) for beat in beats[:4])}" if beats else "",
        f"avoid polished words: {', '.join(str(word) for word in avoid_words)}" if avoid_words else "",
        guidance.get("closing_emotion") or "",
    ]
    return _clean_inline(" ".join(part.strip() for part in parts if part))


def _environment_control(settings: dict[str, Any]) -> dict[str, Any]:
    defaults = prompt_defaults.ENVIRONMENT_CONTROL_DEFAULTS
    consistency = str(settings.get("background_consistency") or defaults["background_consistency"]).strip().lower()
    if consistency not in {"strict", "balanced", "free"}:
        consistency = "strict"
    override = _as_bool(settings.get("environment_override"), defaults["environment_override"])
    preserve_requested = _as_bool(settings.get("preserve_original_scene_layout"), False)
    allow_reference_scene = _as_bool(settings.get("allow_reference_scene_environment"), False)
    preserve_layout = bool(preserve_requested and allow_reference_scene)
    return {
        "background_consistency": consistency,
        "environment_override": override,
        "preserve_original_scene_layout": preserve_layout,
        "environment_selection": defaults.get("environment_selection", "category_auto"),
        "directive": defaults["directive"],
    }


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _environment_control_directive(environment_control: dict[str, Any]) -> str:
    consistency = environment_control.get("background_consistency") or "strict"
    override = bool(environment_control.get("environment_override"))
    preserve_layout = bool(environment_control.get("preserve_original_scene_layout"))
    directive = _clean_inline(environment_control.get("directive") or "")
    if consistency == "free" or override:
        freedom = "environment_override=true, allow user-requested environment changes while preserving product and avatar identity; avatar reference still controls identity only"
    elif consistency == "balanced":
        freedom = "background_consistency=balanced, choose a category-relevant real environment and keep its general room type and colour palette stable; do not copy avatar reference background"
    else:
        freedom = "background_consistency=strict, environment_override=false, environment_selection=category_auto; choose one simple category-appropriate real environment from product type, market, and campaign context; do not preserve product-reference or avatar-reference background"
    return _clean_inline(
        f"{freedom}; preserve_original_scene_layout={str(preserve_layout).lower()}; {directive}; "
        "Creator-video authenticity comes from camera motion, speaking cadence, natural delivery, and product handling, not background copying or random room redesign"
    )


def _category_prompt_directive(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    user_scenario_contract: dict[str, Any] | None = None,
) -> str:
    category = str(product_analysis.get("likely_product_category") or "").strip().lower()
    overrides = settings.get("category_prompt_overrides") or {}
    override = _clean_inline(overrides.get(category) or "")
    if override:
        return override
    preset = prompt_defaults.CATEGORY_PROMPT_PRESETS.get(category) or {}
    parts = [
        preset.get("system_prompt", ""),
        preset.get("video_directive", ""),
        _visual_classifier_prompt_directive(product_analysis, user_scenario_contract),
    ]
    directive = _clean_inline(" ".join(part for part in parts if part))
    directive = scenario_contract.rewrite_for_contract(directive, user_scenario_contract or {"enabled": False})
    directive = scenario_contract.remove_conflicting_directives(directive, user_scenario_contract or {"enabled": False})
    return _clean_inline(directive)


def _visual_classifier_prompt_directive(
    product_analysis: dict[str, Any],
    user_scenario_contract: dict[str, Any] | None = None,
) -> str:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return ""
    user_scenario_contract = user_scenario_contract or {"enabled": False}
    chunks = []
    detected = str(visual.get("detected_object") or "").strip()
    subcategory = str(visual.get("subcategory") or "").strip()
    if detected or subcategory:
        chunks.append(f"Visual classifier: image appears to show {detected or subcategory}; use this only for scene choice and visual proof, not as a customer-facing claim.")
    template = str(visual.get("recommended_template_id") or "").strip()
    if template:
        chunks.append(f"Recommended UGC template from image: {template}.")
    for label, key in [
        ("Scenario rules", "scenario_rules"),
        ("Required shots", "shot_requirements"),
        ("Avoid", "avoid_in_generation"),
    ]:
        values = scenario_contract.filter_conflicting_items(
            [str(item).strip() for item in (visual.get(key) or [])[:4] if str(item).strip()],
            user_scenario_contract,
        )
        if values:
            chunks.append(f"{label}: {'; '.join(values)}.")
    directive = scenario_contract.rewrite_for_contract(" ".join(chunks), user_scenario_contract)
    directive = scenario_contract.remove_conflicting_directives(directive, user_scenario_contract)
    if user_scenario_contract.get("enabled") and directive:
        directive = _clean_inline(
            f"{directive} User scenario contract overrides visual classifier suggestions when they conflict."
        )
    return _clean_inline(directive)


def _structured_scene_fallback(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    avatar_instruction: str,
    scene_avatar_instruction: str,
    fidelity: str,
    aspect_ratio: str,
    duration: int,
    platform: str,
    market: str,
    language: str,
    use_avatar_image_reference: bool,
    scene_chaining: dict[str, Any] | None = None,
    environment_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scene_durations = _scene_durations(duration)
    scenes = []
    scene_defs = ugc_strategy["scene_by_scene_script"]
    scene_links = (scene_chaining or {}).get("scene_links") or []
    scenario_lock = ugc_strategy.get("user_scenario_lock") or {}
    mirror_selfie_lock = (
        isinstance(scenario_lock, dict)
        and scenario_lock.get("enabled")
        and scenario_lock.get("template_id") == "mirror_selfie_try_on_review"
    )
    environment_phrase = (
        "same simple bedroom mirror-selfie environment, smartphone visibly held by the creator in the mirror reflection, no external camera, no tripod, no ordinary talking-head setup"
        if mirror_selfie_lock
        else "category-selected environment based on product type and context, not copied from avatar reference"
    )
    for index, scene_duration in enumerate(scene_durations):
        source = "original_avatar" if index == 0 else "previous_scene_last_frame"
        avatar_on_camera = True
        use_reference = bool(use_avatar_image_reference and avatar_on_camera)
        if index == len(scene_durations) - 1 and len(scene_defs) > 1:
            selected = scene_defs[-1]
        else:
            selected = scene_defs[min(index, len(scene_defs) - 1)]
        continuity = scene_links[min(index, len(scene_links) - 1)] if scene_links else {}
        continuity_note = _clean_inline(
            " ".join(
                str(part)
                for part in [
                    continuity.get("last_frame_capture"),
                    continuity.get("next_scene_start"),
                    continuity.get("motion_bridge"),
                ]
                if part
            )
        )
        scenes.append(
            {
                "scene_id": f"s{index + 1}",
                "purpose": "hook" if index == 0 else "cta" if index == len(scene_durations) - 1 else "demonstration",
                "duration": scene_duration,
                "avatar_on_camera": avatar_on_camera,
                "use_reference_image": use_reference,
                "reference_image_source": source if use_reference else "none",
                "avatar_instruction": scene_avatar_instruction,
                "scene_summary": _clean_inline(
                    f"{selected['visual']}, creator/avatar remains visibly present in frame with face, upper body, shoulder, or natural hands connected to the product, no product-only insert shot, {environment_phrase}, medium close shot with slight handheld camera sway, consistent natural light, natural conversational pacing"
                ),
                "fidelity": _clean_inline(f"{fidelity}, product not modified, not restyled, not recolored, not rebranded"),
                "voiceover": _clean_inline(selected["voiceover"]),
                "on_screen_text": {
                    "text": selected["on_screen_text"][:48],
                    "position": "upper_third_center" if index == 0 else "bottom_center",
                },
                "framing_notes": _clean_inline(
                    "Keep avatar face or upper body/hands and product inside central safe area; only scene 1 may use an exact first-hook text sticker in the upper third for 1-2 seconds, all other ecommerce text is post-production only. "
                    "Every scene must include the same visible creator/avatar for trust; do not cut to a product-only insert. "
                    "Use the avatar reference only for identity; choose a simple category-appropriate environment and keep it consistent. "
                    + (f"Continuity: {continuity_note}" if continuity_note else "")
                ),
                "continuity_notes": continuity,
                "environment_notes": _environment_control_directive(
                    environment_control or _environment_control({})
                ),
            }
        )
    return {
        "variants": [
            {
                "variant_id": "v1",
                "total_duration_seconds": sum(scene_durations),
                "language": language,
                "market": market,
                "platform": platform,
                "aspect_ratio": aspect_ratio,
                "seedance_mode": "image_to_video",
                "reference_image_strategy": "original_avatar_for_first_scene_then_last_frame_chain",
                "environment_control": environment_control or _environment_control({}),
                "scenes": scenes,
                "stitching": {
                    "transition_style": "hard cut",
                    "cut_timing_notes": _clean_inline(
                        "Cut on natural sentence endings. "
                        + str((scene_chaining or {}).get("seedance_prompt_addendum") or "")
                    ),
                },
                "safety_rewrites": [],
                "hypothesis": f"Authentic creator framing with verified product details lowers perceived ad-ness and improves consideration for {product_analysis['product_name']}.",
            }
        ]
    }


def _structured_finance_scene_prompt(
    *,
    ugc_strategy: dict[str, Any],
    scene_avatar_instruction: str,
    fidelity: str,
    use_avatar_image_reference: bool,
    scene_concept: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scene_defs = ugc_strategy.get("scene_by_scene_script") or []
    concept = scene_concept or {}
    concept_elements = concept.get("infographic_elements") if isinstance(concept, dict) else []
    scenes = []
    for index, scene in enumerate(scene_defs):
        infographic = _clean_inline(scene.get("infographic") or "")
        if concept_elements:
            labels = ", ".join(
                str(item.get("label"))
                for item in concept_elements
                if isinstance(item, dict) and item.get("label")
            )
            infographic = _clean_inline(f"{infographic}; approved Czech infographic labels: {labels}")
        scenes.append(
            {
                "scene_id": f"s{index + 1}",
                "purpose": scene.get("psychology_step") or ("hook" if index == 0 else "education"),
                "duration": _duration_from_time(scene.get("time")),
                "avatar_on_camera": True,
                "use_reference_image": bool(use_avatar_image_reference),
                "reference_image_source": "original_avatar" if index == 0 else "previous_scene_last_frame",
                "avatar_instruction": scene_avatar_instruction,
                "scene_summary": _clean_inline(
                    f"{scene.get('visual')}, approved scene concept layout preserved, {infographic}, modern premium interactive finance infographic overlays responding to gaze, pointing, and small air-tap gestures, clean Czech captions, modern podcast studio, desk microphone or boom arm visible, acoustic panels, warm key light, subtle LED accent, medium close shot with hands visible when gesturing, static camera or slow push-in, professional but natural"
                ),
                "fidelity": _clean_inline(fidelity),
                "voiceover": _clean_inline(scene.get("voiceover")),
                "on_screen_text": {
                    "text": _clean_inline(scene.get("on_screen_text"))[:48],
                    "position": "center",
                },
                "framing_notes": _clean_inline(
                    "Keep avatar face, hands, subtitles, disclaimer, and infographic text inside central safe area. "
                    "Use readable Czech typography with Czech diacritics, no Polish or Slovak text, simple charts, no fake financial performance numbers, and subtle gesture-synced highlights. "
                    "Reuse approved scene concept infographic positions and do not replace them with a generic dashboard."
                ),
                "infographic_notes": infographic,
            }
        )
    return {
        "variants": [
            {
                "variant_id": "v1",
                "total_duration_seconds": ugc_strategy.get("duration_seconds"),
                "language": "cs",
                "market": ugc_strategy.get("market"),
                "platform": ugc_strategy.get("platform"),
                "aspect_ratio": ugc_strategy.get("aspect_ratio"),
                "seedance_mode": "image_to_video",
                "reference_image_strategy": "original_avatar_for_first_scene_then_last_frame_chain",
                "approved_scene_concept": concept,
                "scenes": scenes,
                "stitching": {
                    "transition_style": "hard cut with subtle infographic motion continuity and gesture continuity",
                    "cut_timing_notes": "Cut on natural sentence endings; keep charts, Czech captions, and gesture-triggered highlights readable.",
                },
                "safety_rewrites": [],
                "hypothesis": "Podcast-studio personal brand finance ad builds trust by simplifying a complex topic with compliant Czech language and modern visual structure.",
            }
        ]
    }


def _duration_from_time(value: Any) -> int:
    text = str(value or "")
    match = re.search(r"(\d+)\s*-\s*(\d+)", text)
    if not match:
        return 5
    return max(1, int(match.group(2)) - int(match.group(1)))


def _platform_copy(language: str, product_name: str) -> dict[str, dict[str, str]]:
    if _is_czech(language):
        return {
            "meta_ads_copy": {
                "primary_text": (
                    f"Misto jedne vzdalene fotky se podivej na {product_name} zblizka. "
                    "Realny detail, zadne vymyslene sliby. Vhodne pro klidne posouzeni produktu."
                ),
                "headline": "Podivej se zblizka",
                "description": "Realny detail, bez hype.",
            },
            "google_youtube_ads_copy": {
                "headline": f"See {product_name} up close",
                "description": "A short product detail overview focused on what is actually visible.",
                "cta": "handled_by_ad_platform",
            },
        }
    return {
        "meta_ads_copy": {
            "primary_text": (
                f"Instead of one distant photo, see {product_name} up close. "
                "Real detail, no invented promises. Made for a calmer product check."
            ),
            "headline": "See it up close",
            "description": "Real detail, no hype.",
        },
        "google_youtube_ads_copy": {
            "headline": f"See {product_name} up close",
            "description": "A short product detail overview focused on what is actually visible.",
            "cta": "handled_by_ad_platform",
        },
    }


def _target_speech_language(language: str) -> str:
    language_value = str(language or "").lower()
    if _is_czech(language):
        return "cs-CZ"
    if language_value.startswith("de"):
        return "de-DE"
    if language_value.startswith("en"):
        return "en-GB" if language_value in {"en-gb", "en-uk"} else "en-US"
    return ""


def _speech_language_contract(language: str, market: str) -> dict[str, str]:
    spoken_language = _target_speech_language(language)
    language_name = target_language_name(language)
    return {
        "spoken_language": spoken_language,
        "audio_voice": f"{language_name} only",
        "lip_sync": f"sync lips to approved {language_name} voiceover only",
        "forbidden_audio": "no mixed-language filler, dubbing mismatch, untranslated prompt notes, or language switching",
        "market": str(market or ""),
    }


def _language_safe_voice_profile(voice_profile: Any, language: str, market: str) -> str:
    base = _voice_profile(language, market)
    safe_descriptor = language_safe_voice_descriptor(voice_profile, language)
    if _is_czech(language):
        if safe_descriptor and safe_descriptor.lower() not in base.lower():
            return f"{base}; non-language avatar delivery tone: {safe_descriptor}"
        return base
    return safe_descriptor or base


def _audio_language_instruction(language: str, market: str) -> str:
    if _is_czech(language):
        return (
            "CZECH SPOKEN AUDIO HARD LOCK: generate audible spoken audio in Czech only, cs-CZ. "
            "Avatar lips must sync exactly to the approved Czech voiceover as visible on-camera speech, not off-camera narration. "
            "Keep the speaking face and mouth visible with natural lip, jaw, cheek, blink, and expression movement. "
            "Do not translate, paraphrase, dub, switch to English, Polish, Slovak, German, or mixed-language filler, hide the mouth, freeze the face, or create text-only delivery."
        )
    return (
        f"Generate audible spoken audio in {language} for market {market}; audio must read as live on-camera creator speech from the visible avatar, not off-camera narration. "
        "Avatar lips, jaw, cheeks, and expression must visibly sync to the approved voiceover. "
        "Do not create a silent avatar, silent mouthing, frozen face, hidden mouth, dubbed mismatch, or text-only delivery."
    )


def _language_hard_lock_prompt(language: str) -> str:
    if _is_czech(language):
        return (
            "CZECH LANGUAGE HARD LOCK: all spoken customer-facing content must be Czech only, with cs-CZ pronunciation and Czech sentence rhythm. "
            "The avatar must speak only the approved Czech spoken lines. Do not speak English, Polish, Slovak, German, bilingual filler, pseudo-Czech, or any language-switching. "
            "If the avatar voice/persona text mentions English, British, American, German, Polish, or Slovak, ignore that language cue and keep only the non-language delivery tone."
        )
    value = str(language or "").lower()
    if value.startswith("de"):
        return (
            "GERMAN LANGUAGE HARD LOCK: all spoken customer-facing content must be German only, with de-DE pronunciation and natural German sentence rhythm. "
            "Do not speak English, Czech, Polish, Slovak, bilingual filler, or machine-translated mixed-language lines."
        )
    if value.startswith("en"):
        return (
            "ENGLISH LANGUAGE HARD LOCK: all spoken customer-facing content must be English only, with natural English sentence rhythm. "
            "Do not speak Czech, German, Polish, Slovak, bilingual filler, or untranslated product notes."
        )
    return ""


def _scene_durations(duration: int) -> list[int]:
    if duration >= 30:
        return [10, 10, duration - 20]
    if duration >= 20:
        return [10, duration - 10]
    if duration >= 15:
        return [5, 5, duration - 10]
    return [duration]


def _clean_inline(value: str) -> str:
    return " ".join(str(value).split()).strip(" .")


def improve_prompt_package(
    prompt_package: dict[str, Any],
    quality_result: dict[str, Any],
) -> dict[str, Any]:
    improved = dict(prompt_package)
    improvements = (
        " Additional strict improvement pass: prioritize exact product fidelity, verified claims only, "
        "clear platform safe areas, readable captions, and specific shot timing. "
    )
    improved["seedance_video_prompt"] = improved["seedance_video_prompt"] + improvements
    improved["seedance_payload"] = dict(improved["seedance_payload"])
    improved["seedance_payload"]["prompt"] = improved["seedance_payload"]["prompt"] + improvements
    improved["improvement_pass"] = {
        "applied": True,
        "reason": quality_result.get("recommended_improvements", []),
    }
    return improved


def _fidelity_instruction(product_analysis: dict[str, Any], product_image_path: str) -> str:
    known_facts = product_analysis.get("known_product_facts") or {}
    user_facts = product_analysis.get("user_provided_facts") or []
    fact_clauses = []
    if known_facts.get("product_line_or_label") and known_facts.get("product_line_or_label") != "unknown":
        fact_clauses.append(f"product label from user input is {known_facts['product_line_or_label']}")
    if known_facts.get("material") and known_facts.get("material") != "unknown":
        fact_clauses.append(f"material from user brief is {known_facts['material']}")
    if known_facts.get("color") and known_facts.get("color") != "unknown":
        fact_clauses.append(f"color from user brief is {known_facts['color']}")
    if user_facts:
        fact_clauses.append(f"user-provided product facts: {', '.join(user_facts[:5])}")
    grounding = f" {'; '.join(fact_clauses)}." if fact_clauses else ""
    return (
        f"Use the product image reference at {product_image_path} as the strict visual reference. "
        f"{prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK} "
        f"{prompt_defaults.PRODUCT_REFERENCE_ROLE_LOCK} "
        f"{prompt_defaults.MATERIAL_FIDELITY_HARD_LOCK} "
        f"{_material_fidelity_lock(product_analysis)} "
        f"Preserve the exact visible product shape, color, material, finish, texture, proportions, physical size, scale, packaging, and any visible markings. "
        f"Known brand is {known_facts.get('brand', 'unknown')}; do not invent brand or material. "
        f"{_category_fidelity_lock(product_analysis)} "
        "Product not modified, not restyled, not recolored, not rebranded, not resized, not rematerialized, not substituted."
        f"{grounding}"
    )


def _material_fidelity_lock(product_analysis: dict[str, Any]) -> str:
    known_facts = product_analysis.get("known_product_facts") or {}
    material = _clean_inline(str(known_facts.get("material") or ""))
    color = _clean_inline(str(known_facts.get("color") or ""))
    if material and material.lower() != "unknown":
        color_clause = f" and color remains {color}" if color and color.lower() != "unknown" else ""
        return (
            f"Material lock: verified product material is {material}{color_clause}; every scene must preserve this exact material appearance, finish, texture scale, and opacity. "
            "Do not make it look like a different material family, do not add unsupported grain/weave/shine/transparency, and do not use category-default material styling."
        )
    return (
        "Material lock: material is not confidently verified, so the video must copy only the visible material finish from the product reference; "
        "do not name or depict leather, suede, fabric, canvas, plastic, glass, metal, ceramic, wood, rubber, glossy, matte, transparent, opaque, pebbled, woven, quilted, padded, smooth, or grained material unless visible in the reference."
    )


def _category_fidelity_lock(product_analysis: dict[str, Any]) -> str:
    category = str(product_analysis.get("likely_product_category") or "").lower()
    if category == "handbag":
        return (
            "Handbag size lock: preserve the same bag size, silhouette, width/height/depth ratio, "
            "handle length, strap drop, carry position, and body-to-bag scale across every scene and asset; "
            "do not change it into a tote, clutch, mini bag, crossbody, oversized shopper, or different bag type."
        )
    return ""


def _avatar_instruction(
    avatar: dict[str, Any],
    use_avatar_image_reference: bool = False,
    language: str = "en",
) -> str:
    image_reference = avatar.get("image_url") or avatar.get("image_path")
    creator_name = avatar.get("name", "selected avatar")
    persona = sanitize_avatar_descriptor(avatar.get("persona") or avatar.get("style", "natural creator"))
    voice = language_safe_voice_descriptor(
        sanitize_avatar_descriptor(avatar.get("voice", "warm, clear, conversational")),
        language,
    ) or "warm, clear, conversational"
    identity_note = avatar.get("identity_note")
    wardrobe_clause = _wardrobe_clause(avatar.get("wardrobe_policy"))
    if image_reference and use_avatar_image_reference:
        note_part = f" Creator note for delivery only: {identity_note}." if identity_note else ""
        return (
            "Use the supplied avatar reference image as the identity source of truth for the user's own or authorized UGC creator. "
            "Preserve the reference identity exactly: subject from reference image, identity preserved, no facial morphing, no appearance drift. "
            "Do not describe or override static appearance such as age, gender, ethnicity, hair, eyes, skin, face, build, or body type in scene prompts. "
            f"{wardrobe_clause}. Creator label={creator_name}; persona={persona}; voice={voice}. "
            "Ignore the avatar reference background, room, furniture, props, and lighting. Scene prompts should describe only motion, expression dynamics, speaking state, camera, and a category-selected product environment."
            f"{note_part}"
        )
    identity_mode = "Prompt-only identity mode"
    if image_reference:
        identity_mode = f"Prompt-only identity mode with avatar visual reference for style context only={image_reference}"
    note_part = f" Identity note: {identity_note}." if identity_note else ""
    return (
        f"{identity_mode}. Use the same user's own AI avatar or authorized creator persona across every UGC scene: "
        f"creator label={creator_name}, persona={persona}, voice={voice}. "
        f"{wardrobe_clause}. Keep the creator consistent across scenes; avoid swapping to a different person, changing wardrobe logic, or changing voice/cadence."
        f"{note_part}"
    )


def _scene_avatar_instruction(
    avatar: dict[str, Any],
    use_avatar_image_reference: bool,
    language: str = "en",
) -> str:
    voice = language_safe_voice_descriptor(
        sanitize_avatar_descriptor(avatar.get("voice", "warm, clear, conversational")),
        language,
    ) or "warm, clear, conversational"
    if use_avatar_image_reference and (avatar.get("image_url") or avatar.get("image_path")):
        return _clean_inline(
            "subject from reference image, identity preserved, no facial morphing, no appearance drift, "
            "looking directly into camera and speaking naturally, subtle expression changes with occasional blink, "
            f"mouth, jaw, and lips visibly moving in sync with the approved spoken script in {voice}, no frozen face or hidden mouth, {_wardrobe_scene_clause(avatar.get('wardrobe_policy'))}"
        )
    return _clean_inline(
        "same creator persona throughout the video, looking directly into camera and speaking naturally, "
        f"subtle expression changes with occasional blink, mouth, jaw, and lips visibly moving in sync with the approved spoken script in {voice}, no frozen face or hidden mouth, "
        f"{_wardrobe_scene_clause(avatar.get('wardrobe_policy'))}"
    )


def _avatar_identity_contract(
    avatar: dict[str, Any],
    use_avatar_image_reference: bool,
    language: str = "en",
) -> dict[str, Any]:
    image_reference = avatar.get("image_url") or avatar.get("image_path")
    exact_reference = bool(use_avatar_image_reference and image_reference)
    authorized = bool(avatar.get("own_person_confirmed", False))
    return {
        "identity_mode": "exact_image_reference" if exact_reference else "prompt_only",
        "identity_source": "avatar_reference_image" if exact_reference else "avatar_profile_text",
        "reference_image_available": bool(image_reference),
        "own_person_or_authorized_avatar_confirmed": authorized,
        "authorization_statement": (
            str(avatar.get("authorization_statement") or AUTHORIZED_AVATAR_CONSENT_STATEMENT)
            if authorized
            else ""
        ),
        "creator_label": avatar.get("name", "selected avatar"),
        "persona": sanitize_avatar_descriptor(avatar.get("persona") or avatar.get("style", "natural creator")),
        "voice": language_safe_voice_descriptor(
            sanitize_avatar_descriptor(avatar.get("voice", "warm, clear, conversational")),
            language,
        )
        or "warm, clear, conversational",
        "wardrobe_policy": avatar.get("wardrobe_policy", "reference_unchanged"),
        "scene_rule": (
            "When exact image reference is enabled, reference image controls creator identity only; scene prompts describe motion plus a category-selected environment, never the avatar reference background."
            if exact_reference
            else "Prompt-only mode is less consistent; use a public avatar reference image and enable image reference for stronger identity lock."
        ),
        "recommended_capture": [
            "use one clear front-facing reference image with natural light",
            "keep the same wardrobe when consistency matters",
            "avoid sunglasses, heavy filters, extreme angles, or cropped face in the reference",
            "use public HTTPS image URL for video APIs; localhost and data URLs are stripped before submission",
        ],
    }


def _wardrobe_clause(policy: Any) -> str:
    value = str(policy or "reference_unchanged")
    if value == "consistent_simple":
        return "Wardrobe should remain simple and consistent across scenes"
    if value == "allow_controlled_change":
        return "Wardrobe may change only when explicitly needed by the product category, while identity remains locked"
    return "Wardrobe as in the reference image, unchanged"


def _wardrobe_scene_clause(policy: Any) -> str:
    value = str(policy or "reference_unchanged")
    if value == "consistent_simple":
        return "simple consistent wardrobe across scenes"
    if value == "allow_controlled_change":
        return "controlled wardrobe continuity, no distracting outfit changes"
    return "wardrobe as in reference image, unchanged"


def _scene_summary(scenes: list[dict[str, Any]]) -> str:
    return " | ".join(
        f"{scene['time']}: {scene['visual']} VO: {scene['voiceover']}" for scene in scenes
    )
