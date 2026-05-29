from __future__ import annotations

import json
import re
from typing import Any

import requests

from app import config
from app.services import json_schema_contracts, prompt_defaults
from app.services.localization_utils import normalize_language_code, target_language_name


STATIC_CREATIVE_PROMPT_MAX_USER_CHARS = 18000
STATIC_CREATIVE_PROMPT_FIELD_LIMITS = {
    "visual_prompt": 700,
    "primary_text": 520,
    "overlay_text": 48,
    "headline": 64,
    "hook": 140,
    "copy": 260,
}
STATIC_CREATIVE_PROMPT_SHARD_COUNT = 2


class PromptModelFailure(RuntimeError):
    def __init__(self, attempts: list[dict[str, Any]]):
        self.attempts = attempts
        message = attempts[-1]["error"] if attempts else "Prompt model call failed."
        super().__init__(message)


class PromptModelInvalidJSON(ValueError):
    def __init__(
        self,
        message: str,
        *,
        raw: dict[str, Any],
        used_model: str,
        attempts: list[dict[str, Any]],
        prompt_budget: dict[str, Any],
        raw_content: str,
    ):
        self.raw = raw
        self.used_model = used_model
        self.attempts = attempts
        self.prompt_budget = prompt_budget
        self.raw_content = raw_content
        super().__init__(message)


def enhance_prompt_package(
    content_prompt_package: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    avatar: dict[str, Any],
    api_key: str | None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
    system_prompt: str | None = None,
    task_prompt: str | None = None,
) -> dict[str, Any]:
    prompt_model = model or config.OPENROUTER_PROMPT_MODEL
    requested_language = (
        ugc_strategy.get("language")
        or content_prompt_package.get("language")
        or product_analysis.get("language")
        or "en"
    )
    humanizer_instruction = _ugc_scenario_humanizer_instruction(requested_language)
    if not api_key:
        return {
            **content_prompt_package,
            "prompt_generation": {
                "status": "skipped",
                "model": prompt_model,
                "scenario_generation_workflow": "skeleton_then_conversational_rewrite",
                "humanizer_instruction": humanizer_instruction,
                "error": "OPENROUTER_API_KEY is missing; deterministic prompt package was used.",
            },
        }

    system = _with_ugc_scenario_humanizer_guard(
        system_prompt or prompt_defaults.CONTENT_PROMPT_SYSTEM
    )
    user = {
        "task": task_prompt or prompt_defaults.CONTENT_PROMPT_TASK,
        "required_schema": "Return the variants JSON object described in the system prompt.",
        "target_language": target_language_name(requested_language),
        "scenario_generation_workflow": {
            "phase_1_internal_skeleton": (
                "First build the clean UGC scenario skeleton internally: hook, product proof, "
                "detail proof, lifestyle/context beat, and closing recap. Do not return this draft."
            ),
            "phase_2_required_rewrite": humanizer_instruction,
            "output_rule": (
                "Return only the final rewritten strict JSON. voiceover and scene_summary must be natural in the selected target language. "
                "For ecommerce, on_screen_text.text is post-production overlay metadata only; the generated video should speak hooks aloud and render no generated text."
            ),
        },
        "user_scenario_lock": content_prompt_package.get("user_scenario_lock") or ugc_strategy.get("user_scenario_lock"),
        "brief_usage_rule": (
            "Treat product_info/internal_brief_notes as internal guidance only. "
            "Translate product-note-derived details into the requested output language and rewrite them naturally. "
            "Do not copy user notes verbatim into voiceover, on_screen_text, scene_summary, meme copy, carousel text, or primary text."
        ),
        "language_copy_policy": content_prompt_package.get("language_copy_policy"),
        "category_prompt_directive": content_prompt_package.get("category_prompt_directive"),
        "environment_control": content_prompt_package.get("environment_control"),
        "environment_control_rule": content_prompt_package.get("environment_control_directive"),
        "ugc_video_extra_prompt": content_prompt_package.get("ugc_video_extra_prompt"),
        "avatar_identity_contract": content_prompt_package.get("avatar_identity_contract"),
        "avatar_runtime": {
            "persona_allows_first_person_testimonial": bool(
                ugc_strategy.get("avatar_direction", {}).get("personal_use_claims_allowed")
            ),
            "allow_outfit_change": (
                content_prompt_package.get("avatar_identity_contract", {}).get("wardrobe_policy")
                == "allow_controlled_change"
            ),
            "image_to_video_reference_enabled": bool(
                content_prompt_package.get("seedance_payload", {}).get("avatar_reference_mode")
                == "exact_image_input_reference"
            ),
            "own_person_or_authorized_avatar_confirmed": bool(
                content_prompt_package.get("avatar_identity_contract", {}).get(
                    "own_person_or_authorized_avatar_confirmed"
                )
            ),
        },
        "product_analysis": product_analysis,
        "ugc_strategy": ugc_strategy,
        "avatar": avatar,
        "current_prompt_package": _sanitize_for_prompt_model(content_prompt_package),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
    }
    payload = {
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "usage": {"include": True},
    }
    _apply_response_format_for_model(
        payload,
        model=prompt_model,
        response_format=json_schema_contracts.SCENARIO_WRITER_RESPONSE_FORMAT,
        fallback_contract_hint=(
            "Return exactly one JSON object with a variants array. Do not wrap it in markdown. "
            "Every variant must contain scenes, stitching, safety_rewrites, and hypothesis."
        ),
    )
    try:
        raw, used_model, attempts = _post_chat_completion_with_fallback(
            base_url=base_url,
            headers=headers,
            payload=payload,
            requested_model=prompt_model,
        )
        content = raw["choices"][0]["message"]["content"]
        enhanced = _parse_json_object(content)
        validation_error = _structured_variants_validation_error(enhanced) if "variants" in enhanced else ""
        if validation_error:
            return {
                **content_prompt_package,
                "prompt_generation": {
                    "status": "completed_with_fallback",
                    "model": used_model,
                    "requested_model": prompt_model,
                    "scenario_generation_workflow": "skeleton_then_conversational_rewrite",
                    "humanizer_instruction": humanizer_instruction,
                    "fallback_used": used_model != prompt_model,
                    "error": f"Prompt model returned invalid structured scene JSON: {validation_error}",
                    "attempts": attempts,
                    "generation_id": raw.get("id"),
                    "usage": raw.get("usage"),
                    "raw_content_preview": str(content or "")[:1200],
                },
            }
    except PromptModelFailure as exc:
        return {
            **content_prompt_package,
            "prompt_generation": {
                "status": "failed",
                "model": prompt_model,
                "scenario_generation_workflow": "skeleton_then_conversational_rewrite",
                "humanizer_instruction": humanizer_instruction,
                "error": str(exc),
                "attempts": exc.attempts,
            },
        }
    except Exception as exc:
        return {
            **content_prompt_package,
            "prompt_generation": {
                "status": "failed",
                "model": prompt_model,
                "scenario_generation_workflow": "skeleton_then_conversational_rewrite",
                "humanizer_instruction": humanizer_instruction,
                "error": str(exc),
            },
        }
    result = dict(content_prompt_package)
    if _is_structured_variants(enhanced):
        result["structured_scene_prompt"] = enhanced
        result["seedance_video_prompt"] = _normalize_seedance_prompt(
            _compile_structured_prompt(enhanced, content_prompt_package)
        )
    else:
        for key, value in enhanced.items():
            if key in result:
                result[key] = value
        result["seedance_video_prompt"] = _normalize_seedance_prompt(
            result.get("seedance_video_prompt", content_prompt_package["seedance_video_prompt"])
        )
    result["seedance_video_prompt"] = _append_video_extra_direction(
        result["seedance_video_prompt"], content_prompt_package
    )
    result["seedance_video_prompt"] = _append_environment_control(
        result["seedance_video_prompt"], content_prompt_package
    )
    result["seedance_payload"] = dict(content_prompt_package["seedance_payload"])
    result["seedance_payload"]["prompt"] = result.get(
        "seedance_video_prompt", content_prompt_package["seedance_video_prompt"]
    )
    result["prompt_generation"] = {
        "status": "completed",
        "model": used_model,
        "requested_model": prompt_model,
        "scenario_generation_workflow": "skeleton_then_conversational_rewrite",
        "humanizer_instruction": humanizer_instruction,
        "fallback_used": used_model != prompt_model,
        "attempts": attempts,
        "generation_id": raw.get("id"),
        "usage": raw.get("usage"),
    }
    return result


def _with_ugc_scenario_humanizer_guard(system: str) -> str:
    guard = (
        "\n\n# UGC SCENARIO HUMANIZER WORKFLOW\n"
        "For ecommerce UGC scenario writing, work in two internal passes before returning JSON. "
        "Pass 1: build the structural scenario skeleton with a clear hook, product proof, detail proof, "
        "lifestyle/use context, and closing recap. Pass 2: rewrite every customer-facing spoken line, "
        "scene_summary phrase, spoken hook, and planned post-production overlay metadata into relaxed spoken language in the requested "
        "target language, like a normal person explaining it to a friend in a pub/bar conversation. "
        "Use short sentences, natural pauses, everyday words, and local phrasing. Remove complex, polished, "
        "corporate, marketing-sounding language, and production directions. The avatar must never say what the prompt, skill, model, or shot plan is doing. "
        "Do not use phrases such as angle:, visual direction, hook intent, I'd show, I'd check, this scene shows, voiceover=, or on_screen_text. "
        "For ecommerce videos, do not render on_screen_text.text inside the generated video; all overlay text is added in post-production. "
        "If user_scenario_lock.enabled is true, preserve its camera setup, shot style, environment type, pacing, spoken hook, and creator behaviour unless they conflict with product fidelity, avatar identity, safety, target language, or verified facts. "
        "Do not replace a user-locked mirror selfie or try-on review with a generic lifestyle scene. "
        "Do not return the skeleton draft; return only strict JSON "
        "containing the rewritten final scenario."
    )
    if "UGC SCENARIO HUMANIZER WORKFLOW" in system:
        return system
    return f"{system.rstrip()}{guard}"


def _ugc_scenario_humanizer_instruction(language: Any) -> str:
    code = normalize_language_code(language)
    language_name = target_language_name(language)
    if code == "cs":
        return (
            "Jakmile mas kostru, prepis tento scenar do uvolnene, mluvene cestiny, "
            "jako bys to rikal kamaradovi u piva. Nepouzivej zadna slozita nebo marketingova slova. "
            "Avatar rika reklamni sdeleni k produktu, ne rezijni poznamky typu co by se melo ukazat. "
            "Zachovej ovsem produktova fakta, claims safety a striktni JSON schema."
        )
    if code == "de":
        return (
            "Sobald die Struktur steht, schreibe das Szenario in lockeres, gesprochenes Deutsch um, "
            "als wuerdest du es einem Freund in der Kneipe erzaehlen. Keine komplizierten oder marketinghaften Woerter. "
            "Der Avatar spricht die Werbebotschaft zum Produkt, keine Regieanweisungen darueber, was gezeigt werden soll. "
            "Produktfakten, Claim-Sicherheit und das strikte JSON-Schema bleiben unveraendert."
        )
    if code == "en":
        return (
            "Once the skeleton is ready, rewrite the scenario into relaxed spoken English, "
            "like telling a friend at a pub. Do not use complex or marketing-sounding words. "
            "The avatar speaks the product ad message, not production notes about what should be shown. "
            "Keep product facts, claim safety, and the strict JSON schema intact."
        )
    return (
        f"Once the skeleton is ready, rewrite the scenario into relaxed spoken {language_name}, "
        "like explaining it casually to a friend at a local pub or bar. Do not use complex, corporate, "
        "or marketing-sounding words. The avatar speaks the product ad message, not production notes about what should be shown. "
        "Keep product facts, claim safety, and the strict JSON schema intact."
    )


def enhance_ads_creative_set(
    ads_creative_set: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    api_key: str | None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    prompt_model = model or config.OPENROUTER_PROMPT_MODEL
    if not api_key:
        return {
            **ads_creative_set,
            "static_prompt_generation": {
                "status": "skipped",
                "model": prompt_model,
                "error": "OPENROUTER_API_KEY is missing; deterministic static creative prompts were used.",
            },
        }

    system = (
        "You are the Ads Creative Strategy and Prompt Engineer inside a paid social creative workflow. "
        "Use the product brief, product analysis, UGC strategy, platform, market, language, and category prompt to rewrite the actual creative strategy, not just polish wording. "
        "Return ONLY valid JSON that matches the provided response_format schema. Use empty arrays/objects for sections that do not need changes. Preserve the C1-C5 media architecture, all set_id values, creative_id values, card_number values, counts, aspect_ratio values, funnel_stage values, and budget_share_percent values. "
        "You may rewrite creative_angles, hook_bank, static image layouts/prompts/post-production overlay metadata/headline/primary_text, carousel primary_text/cards visual prompts/post-production overlay metadata, meme concepts, primary_text_variants, ad_description_suggestions, and Google Ads text assets. "
        "Treat the existing creative text as a weak placeholder only. Discard generic fallback wording and create fresh product-specific concepts. "
        "Make every variation product-specific and materially different: distinct angle, setting, visual composition, prop logic, shot distance, post-production overlay idea, and reason-to-care. "
        "Enforce C2/C3/C4 visual separation: C2 PRODUCT_HERO is a product-first commerce hero frame, C3 USE_CONTEXT is a believable real-use/outfit/routine moment, C4 DETAIL_PROOF is a tight macro or visible-proof frame. Do not reuse the same background, room, surface, prop arrangement, camera distance, or lighting mood across C2/C3/C4 unless the product reference explicitly requires strict scene preservation. "
        "Static customer-facing hook copy must not be repetitive. Avoid defaulting to the same phrases like 'real detail', 'no hype', 'quick detail', or 'before deciding' across every static. Each overlay_text metadata value and primary text should reflect the role and a concrete visible product cue. "
        "Static and carousel overlay_text is post-production metadata for a later design layer, not text the AI image model should draw. Keep it short in the requested output language, ideally 2-5 words, but never include instructions in visual_prompt to render text, typography, labels, stickers, badges, callouts, or captions inside the generated image. Derive overlay_text from angle_multiplier_hook, product details, and buyer motivation; do not output the angle family or strategy label itself. A good metadata hook is 'Fits the routine' or 'Look at the finish', not 'Desire angle', 'Identity hook', or 'Detail proof'. "
        "Never use internal role labels or workflow names as visible overlay text: no Hero view, Main view, Product hero, Use context, Outfit context, Detail proof, Proof detail, Buying guide, Final check, C2/C3/C4/C5, creative angle names, angle family names, or set IDs. Those are internal metadata only. "
        "Use the selected C2/C3/C4/C5 slots as containers, not as creative shackles: C2 can be any product-first thumb stop, C3 any use-context proof, C4 any detail/texture/scale proof, and C5 any buying-guide sequence. "
        "Keep the response compact. Return only fields you improve, never repeat the full input object. "
        "Length limits: visual_prompt max 700 chars, primary_text max 520 chars, overlay_text max 48 chars, headline max 64 chars, hook max 140 chars, meme copy max 260 chars. "
        "For static image creatives, prefer human-context images by default: the product should be carried, worn, held, tried on, or placed directly on/against an adult person whenever the category allows it. "
        "For bags: show the bag on shoulder, in hand, against an outfit, or being carried; preserve the same handbag size relative to body/hands/shoulder across all static assets and carousel cards, including handle length, strap drop, silhouette, width/height/depth ratio, and carry position. Never turn a shoulder bag into a tote, clutch, mini bag, crossbody, oversized shopper, backpack, or different bag type. For shoes/apparel: show the product worn. Faces may be cropped, turned away, or out of frame. Use adults only, no children, no public figures, no celebrity likeness, no stock-photo glamour pose. "
        "Static image concepts must be as realistic as possible: real-camera photography, physically plausible lighting, believable scale, natural shadows, real materials, imperfect everyday composition, no AI-gloss, no synthetic render look, no invented plastic texture on non-plastic products, no surreal props, no impossible reflections, and no over-smoothed product surfaces. "
        f"{prompt_defaults.STATIC_IMAGE_MATERIAL_FIDELITY_LOCK} "
        "When writing static visual_prompt fields, material-proof language must stay conditional on verified product facts. If the product material, finish, opacity, or transparency is not verified, write 'exact visible material finish from the reference' instead of naming a new material. For drinkware, cups, glasses, bottles, jars, or packaging, never make the item transparent, glass-like, opaque, frosted, glossy, or matte unless the reference or supplied facts already show that property. "
        "Do not invent reviews, ratings, discounts, urgency, medical claims, status-signaling claims, competitor comparisons, materials, brand facts, capacity claims, social proof, or performance claims. "
        "Product notes are internal guidance; convert them into verified visual/product-detail language and never copy messy notes verbatim. "
        "Do not include destination URLs, button labels, fake CTA buttons, click/tap instructions, app UI, platform UI, or wording like ad button, CTA button, learn more, shop now, view details, open detail. "
        "The ad platform supplies CTA controls separately; creative text should focus on hooks, product detail, contrast, use context, and product-specific visual reasons."
    )
    user = {
        "task": (
            "Rewrite the creative set inside the existing structure. Return all top-level keys required by the response schema; use empty arrays/objects for sections you do not improve. Sections: "
            "creative_angles, hook_bank, static_image_ads, carousel_ad, meme_style_creatives, primary_text_variants, "
            "ad_description_suggestions, google_ads_assets. "
            "For static_image_ads include the same creative_id/set_id entries and only update layout, visual_prompt, overlay_text, primary_text, headline. overlay_text/headline are post-production customer-visible hooks, not angle labels, and visual_prompt must not ask the image model to render them as text. "
            "For carousel_ad keep five cards and only update primary_text plus cards[].visual_prompt and cards[].overlay_text; card visual_prompt must stay photo-first and no-generated-text. "
            "Omit any section that does not need improvement. Do not echo unchanged data. Keep the JSON small enough for downstream parsing. "
            "For Google Ads keep character limits in mind. Do not output CTA/button fields."
        ),
        "output_size_contract": STATIC_CREATIVE_PROMPT_FIELD_LIMITS,
        "product_analysis": _static_product_prompt_payload(product_analysis),
        "ugc_strategy_context": _static_ugc_prompt_payload(ugc_strategy),
        "ads_creative_set": _static_ads_prompt_payload(ads_creative_set),
    }
    prompt_budget = _prompt_budget_report(user)
    if _should_shard_static_prompt(prompt_budget, ads_creative_set):
        return _enhance_ads_creative_set_sharded(
            ads_creative_set=ads_creative_set,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            api_key=api_key,
            model=prompt_model,
            base_url=base_url,
            system=system,
            full_prompt_budget=prompt_budget["metadata"],
        )

    try:
        call = _run_ads_creative_set_prompt_call(
            user=user,
            system=system,
            api_key=api_key,
            model=prompt_model,
            base_url=base_url,
        )
        enhanced = call["enhanced"]
    except PromptModelFailure as exc:
        return {
            **ads_creative_set,
            "static_prompt_generation": {
                "status": "failed",
                "model": prompt_model,
                "error": str(exc),
                "attempts": exc.attempts,
            },
        }
    except PromptModelInvalidJSON as exc:
        return {
            **ads_creative_set,
            "static_prompt_generation": {
                "status": "completed_with_fallback",
                "model": exc.used_model,
                "requested_model": prompt_model,
                "fallback_used": exc.used_model != prompt_model,
                "fallback_reason": "Prompt model returned invalid JSON, so deterministic C1-C5 static creative prompts were used for image generation.",
                "error": str(exc),
                "attempts": exc.attempts,
                "generation_id": exc.raw.get("id"),
                "usage": exc.raw.get("usage"),
                "raw_content_preview": str(exc.raw_content or "")[:1200],
                "prompt_budget": exc.prompt_budget,
            },
        }
    except Exception as exc:
        return {
            **ads_creative_set,
            "static_prompt_generation": {
                "status": "failed",
                "model": prompt_model,
                "error": str(exc),
            },
        }

    result = _merge_static_ads_prompt_enhancement(
        ads_creative_set,
        enhanced,
        product_analysis=product_analysis,
    )
    result["static_prompt_generation"] = {
        "status": "completed",
        "model": call["used_model"],
        "requested_model": prompt_model,
        "fallback_used": call["used_model"] != prompt_model,
        "attempts": call["attempts"],
        "generation_id": call["raw"].get("id"),
        "usage": call["raw"].get("usage"),
        "prompt_budget": call["prompt_budget"],
    }
    return result


def _run_ads_creative_set_prompt_call(
    *,
    user: dict[str, Any],
    system: str,
    api_key: str,
    model: str,
    base_url: str,
    prompt_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    budget = prompt_budget or _prompt_budget_report(user)
    user_content = budget["content"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
    }
    payload = {
        "temperature": 0.25,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "usage": {"include": True},
    }
    _apply_response_format_for_model(
        payload,
        model=model,
        response_format=json_schema_contracts.ADS_CREATIVE_SET_RESPONSE_FORMAT,
        fallback_contract_hint=(
            "Return exactly one compact JSON object. Top-level keys: creative_angles, hook_bank, "
            "static_image_ads, carousel_ad, meme_style_creatives, primary_text_variants, "
            "ad_description_suggestions, google_ads_assets. Use empty arrays or objects for sections "
            "you do not improve. Do not wrap JSON in markdown."
        ),
    )
    raw, used_model, attempts = _post_chat_completion_with_fallback(
        base_url=base_url,
        headers=headers,
        payload=payload,
        requested_model=model,
    )
    raw_content = raw["choices"][0]["message"]["content"]
    try:
        enhanced = _parse_json_object(raw_content)
    except Exception as exc:
        raise PromptModelInvalidJSON(
            str(exc),
            raw=raw,
            used_model=used_model,
            attempts=attempts,
            prompt_budget=budget["metadata"],
            raw_content=raw_content,
        ) from exc
    return {
        "enhanced": enhanced,
        "raw": raw,
        "used_model": used_model,
        "attempts": attempts,
        "prompt_budget": budget["metadata"],
        "raw_content_preview": str(raw_content or "")[:1200],
    }


def _enhance_ads_creative_set_sharded(
    *,
    ads_creative_set: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    api_key: str,
    model: str,
    base_url: str,
    system: str,
    full_prompt_budget: dict[str, Any],
) -> dict[str, Any]:
    result = json.loads(json.dumps(ads_creative_set, ensure_ascii=False))
    shard_results = []
    successful_calls = []
    for shard in _static_prompt_shards(ads_creative_set):
        shard_user = _static_prompt_shard_user_payload(
            shard=shard,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            ads_creative_set=ads_creative_set,
        )
        try:
            call = _run_ads_creative_set_prompt_call(
                user=shard_user,
                system=system,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )
            enhanced = _filter_static_prompt_enhancement_for_shard(call["enhanced"], shard)
            result = _merge_static_ads_prompt_enhancement(
                result,
                enhanced,
                product_analysis=product_analysis,
            )
            successful_calls.append(call)
            shard_results.append(
                {
                    "name": shard["name"],
                    "status": "completed",
                    "model": call["used_model"],
                    "requested_model": model,
                    "fallback_used": call["used_model"] != model,
                    "generation_id": call["raw"].get("id"),
                    "usage": call["raw"].get("usage"),
                    "prompt_budget": call["prompt_budget"],
                    "attempts": call["attempts"],
                    "static_creative_ids": shard.get("static_creative_ids") or [],
                    "include_carousel": shard.get("include_carousel"),
                    "include_copy": shard.get("include_copy"),
                }
            )
        except PromptModelFailure as exc:
            shard_results.append(
                {
                    "name": shard["name"],
                    "status": "failed",
                    "error": str(exc),
                    "attempts": exc.attempts,
                    "static_creative_ids": shard.get("static_creative_ids") or [],
                    "include_carousel": shard.get("include_carousel"),
                    "include_copy": shard.get("include_copy"),
                }
            )
        except PromptModelInvalidJSON as exc:
            shard_results.append(
                {
                    "name": shard["name"],
                    "status": "failed",
                    "error": str(exc),
                    "attempts": exc.attempts,
                    "model": exc.used_model,
                    "requested_model": model,
                    "generation_id": exc.raw.get("id"),
                    "usage": exc.raw.get("usage"),
                    "prompt_budget": exc.prompt_budget,
                    "raw_content_preview": str(exc.raw_content or "")[:1200],
                    "static_creative_ids": shard.get("static_creative_ids") or [],
                    "include_carousel": shard.get("include_carousel"),
                    "include_copy": shard.get("include_copy"),
                }
            )
        except Exception as exc:
            shard_results.append(
                {
                    "name": shard["name"],
                    "status": "failed",
                    "error": str(exc),
                    "attempts": [],
                    "static_creative_ids": shard.get("static_creative_ids") or [],
                    "include_carousel": shard.get("include_carousel"),
                    "include_copy": shard.get("include_copy"),
                }
            )

    if not successful_calls:
        return {
            **ads_creative_set,
            "static_prompt_generation": {
                "status": "failed",
                "model": model,
                "requested_model": model,
                "error": "All sharded static prompt model calls failed.",
                "sharded": True,
                "shards": shard_results,
                "prompt_budget": _aggregate_shard_prompt_budget(
                    full_prompt_budget=full_prompt_budget,
                    shard_results=shard_results,
                ),
            },
        }

    failed_count = sum(1 for item in shard_results if item.get("status") != "completed")
    used_models = [call["used_model"] for call in successful_calls]
    result["static_prompt_generation"] = {
        "status": "completed" if failed_count == 0 else "completed_with_fallback",
        "model": used_models[-1],
        "requested_model": model,
        "fallback_used": any(used_model != model for used_model in used_models) or failed_count > 0,
        "fallback_reason": (
            f"{failed_count} static prompt shard(s) failed; deterministic creative text was kept for those shards."
            if failed_count
            else None
        ),
        "sharded": True,
        "shard_strategy": "split_static_images_then_carousel_copy",
        "shard_count": len(shard_results),
        "shards": shard_results,
        "attempts": [
            {"shard": item.get("name"), "attempts": item.get("attempts") or []}
            for item in shard_results
        ],
        "generation_id": ",".join(
            str(item.get("generation_id"))
            for item in shard_results
            if item.get("generation_id")
        ),
        "usage": _aggregate_prompt_usage([call["raw"].get("usage") for call in successful_calls]),
        "prompt_budget": _aggregate_shard_prompt_budget(
            full_prompt_budget=full_prompt_budget,
            shard_results=shard_results,
        ),
    }
    return result


def _should_shard_static_prompt(prompt_budget: dict[str, Any], ads_creative_set: dict[str, Any]) -> bool:
    metadata = prompt_budget.get("metadata") or {}
    before_chars = int(metadata.get("user_chars_before_budget") or 0)
    has_multiple_targets = len(ads_creative_set.get("static_image_ads") or []) > 1 or bool(
        ((ads_creative_set.get("carousel_ad") or {}).get("cards") or [])
    )
    return has_multiple_targets and before_chars > STATIC_CREATIVE_PROMPT_MAX_USER_CHARS


def _static_prompt_shards(ads_creative_set: dict[str, Any]) -> list[dict[str, Any]]:
    static_items = [item for item in (ads_creative_set.get("static_image_ads") or []) if isinstance(item, dict)]
    split_at = max(1, (len(static_items) + 1) // STATIC_CREATIVE_PROMPT_SHARD_COUNT)
    first_static = static_items[:split_at]
    second_static = static_items[split_at:]
    shards = []
    if first_static:
        shards.append(
            {
                "name": "static_images_1",
                "static_items": first_static,
                "static_creative_ids": [item.get("creative_id") for item in first_static if item.get("creative_id")],
                "include_carousel": False,
                "include_copy": False,
            }
        )
    if second_static or ((ads_creative_set.get("carousel_ad") or {}).get("cards") or []):
        shards.append(
            {
                "name": "static_images_2_carousel_copy",
                "static_items": second_static,
                "static_creative_ids": [item.get("creative_id") for item in second_static if item.get("creative_id")],
                "include_carousel": True,
                "include_copy": True,
            }
        )
    return shards or [
        {
            "name": "static_prompt_single_fallback",
            "static_items": static_items,
            "static_creative_ids": [item.get("creative_id") for item in static_items if item.get("creative_id")],
            "include_carousel": True,
            "include_copy": True,
        }
    ]


def _static_prompt_shard_user_payload(
    *,
    shard: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    ads_creative_set: dict[str, Any],
) -> dict[str, Any]:
    scope = "static image prompts"
    if shard.get("include_carousel") and shard.get("include_copy"):
        scope = "remaining static image prompts, carousel, and copy assets"
    return {
        "task": (
            f"Static prompt shard {shard['name']}: rewrite only the provided {scope}. "
            "Do not invent missing sections. Preserve IDs and return valid JSON matching the schema; use empty arrays or safe empty objects for unrelated sections."
        ),
        "output_size_contract": STATIC_CREATIVE_PROMPT_FIELD_LIMITS,
        "prompt_shard": {
            "name": shard["name"],
            "static_creative_ids": shard.get("static_creative_ids") or [],
            "include_carousel": bool(shard.get("include_carousel")),
            "include_copy": bool(shard.get("include_copy")),
            "merge_rule": "Only returned fields for this shard will be merged into the final ads_creative_set.",
        },
        "product_analysis": _static_product_prompt_payload(product_analysis),
        "ugc_strategy_context": _static_ugc_prompt_payload(ugc_strategy),
        "ads_creative_set": _static_ads_prompt_payload_for_shard(
            ads_creative_set=ads_creative_set,
            static_items=shard.get("static_items") or [],
            include_carousel=bool(shard.get("include_carousel")),
            include_copy=bool(shard.get("include_copy")),
        ),
    }


def _static_ads_prompt_payload_for_shard(
    *,
    ads_creative_set: dict[str, Any],
    static_items: list[dict[str, Any]],
    include_carousel: bool,
    include_copy: bool,
) -> dict[str, Any]:
    payload = _static_ads_prompt_payload(ads_creative_set)
    payload["static_image_ads"] = _compact_static_image_ads(static_items)
    if not include_carousel:
        payload["carousel_ad"] = {}
    if not include_copy:
        payload["creative_angles"] = []
        payload["hook_bank"] = []
        payload["meme_style_creatives"] = []
        payload["primary_text_variants"] = []
        payload["ad_description_suggestions"] = {}
        payload["google_ads_assets"] = {}
    return payload


def _filter_static_prompt_enhancement_for_shard(
    enhanced: dict[str, Any],
    shard: dict[str, Any],
) -> dict[str, Any]:
    allowed_ids = set(shard.get("static_creative_ids") or [])
    filtered: dict[str, Any] = {
        "static_image_ads": [
            item
            for item in enhanced.get("static_image_ads") or []
            if isinstance(item, dict) and item.get("creative_id") in allowed_ids
        ]
    }
    if shard.get("include_carousel") and isinstance(enhanced.get("carousel_ad"), dict):
        filtered["carousel_ad"] = enhanced["carousel_ad"]
    if shard.get("include_copy"):
        for key in [
            "creative_angles",
            "hook_bank",
            "meme_style_creatives",
            "primary_text_variants",
            "ad_description_suggestions",
            "google_ads_assets",
        ]:
            if key in enhanced:
                filtered[key] = enhanced[key]
    return filtered


def _aggregate_prompt_usage(usages: list[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"shard_count": len([usage for usage in usages if isinstance(usage, dict)])}
    total_cost = 0.0
    has_cost = False
    for usage in usages:
        if not isinstance(usage, dict):
            continue
        for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            if isinstance(usage.get(key), (int, float)):
                result[key] = result.get(key, 0) + usage[key]
        if isinstance(usage.get("cost"), (int, float)):
            total_cost += float(usage["cost"])
            has_cost = True
    if has_cost:
        result["cost"] = round(total_cost, 10)
    return result


def _aggregate_shard_prompt_budget(
    *,
    full_prompt_budget: dict[str, Any],
    shard_results: list[dict[str, Any]],
) -> dict[str, Any]:
    shard_budgets = [
        item.get("prompt_budget")
        for item in shard_results
        if isinstance(item.get("prompt_budget"), dict)
    ]
    sent_values = [int(item.get("user_chars_sent") or 0) for item in shard_budgets]
    before_values = [int(item.get("user_chars_before_budget") or 0) for item in shard_budgets]
    return {
        "max_user_chars": STATIC_CREATIVE_PROMPT_MAX_USER_CHARS,
        "user_chars_before_budget": int(full_prompt_budget.get("user_chars_before_budget") or 0),
        "user_chars_sent": max(sent_values or [0]),
        "total_user_chars_sent": sum(sent_values),
        "max_shard_user_chars_before_budget": max(before_values or [0]),
        "truncated_for_budget": any(bool(item.get("truncated_for_budget")) for item in shard_budgets),
        "hard_fit_applied": any(bool(item.get("hard_fit_applied")) for item in shard_budgets),
        "sharded": True,
        "shard_count": len(shard_results),
        "shards": [
            {
                "name": item.get("name"),
                "status": item.get("status"),
                "user_chars_before_budget": (item.get("prompt_budget") or {}).get("user_chars_before_budget"),
                "user_chars_sent": (item.get("prompt_budget") or {}).get("user_chars_sent"),
                "truncated_for_budget": (item.get("prompt_budget") or {}).get("truncated_for_budget"),
                "hard_fit_applied": (item.get("prompt_budget") or {}).get("hard_fit_applied"),
            }
            for item in shard_results
        ],
    }


def _post_chat_completion_with_fallback(
    base_url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    requested_model: str,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for candidate in _prompt_model_candidates(requested_model):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json={**payload, "model": candidate},
                timeout=90,
            )
            response.raise_for_status()
            raw = response.json()
            if "error" in raw:
                raise ValueError(f"OpenRouter error: {raw['error']}")
            if "choices" not in raw or not raw["choices"]:
                raise ValueError(f"OpenRouter response missing choices: {str(raw)[:1000]}")
            attempts.append({"model": candidate, "status": "completed"})
            return raw, candidate, attempts
        except Exception as exc:
            attempts.append(
                {
                    "model": candidate,
                    "status": "failed",
                    "error": _format_prompt_model_error(exc),
                }
            )
    raise PromptModelFailure(attempts)


def _prompt_model_candidates(requested_model: str) -> list[str]:
    candidates = [requested_model or config.OPENROUTER_PROMPT_MODEL]
    candidates.extend(config.OPENROUTER_PROMPT_FALLBACK_MODELS)
    seen: set[str] = set()
    unique = []
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _apply_response_format_for_model(
    payload: dict[str, Any],
    *,
    model: str,
    response_format: dict[str, Any],
    fallback_contract_hint: str,
) -> None:
    if _supports_provider_json_schema(model):
        payload["response_format"] = response_format
        return
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return
    first = messages[0]
    if not isinstance(first, dict):
        return
    first["content"] = (
        f"{first.get('content') or ''}\n\n"
        "# JSON OUTPUT CONTRACT\n"
        f"{fallback_contract_hint}\n"
        "The provider JSON schema transport is disabled for this model, so obey this JSON contract in plain text."
    )


def _supports_provider_json_schema(model: str) -> bool:
    normalized = str(model or "").strip().lower()
    if normalized.startswith("google/") or "gemini" in normalized:
        return False
    return True


def _format_prompt_model_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.text[:600]
        except Exception:
            body = ""
        return f"{type(exc).__name__}: HTTP {response.status_code}. {body}".strip()
    return f"{type(exc).__name__}: {exc}"


def _is_structured_variants(value: dict[str, Any]) -> bool:
    variants = value.get("variants")
    return isinstance(variants, list) and bool(variants) and isinstance(variants[0], dict)


def _structured_variants_validation_error(value: dict[str, Any]) -> str:
    variants = value.get("variants")
    if not isinstance(variants, list) or not variants:
        return "variants must be a non-empty list"
    variant = variants[0]
    if not isinstance(variant, dict):
        return "variants[0] must be an object"
    scenes = variant.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return "variants[0].scenes must be a non-empty list"
    total_duration = _coerce_int(variant.get("total_duration_seconds"))
    if total_duration <= 0:
        return "total_duration_seconds must be a positive number"
    scene_duration_sum = 0
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            return f"scene {index + 1} must be an object"
        for key in [
            "scene_id",
            "purpose",
            "duration",
            "avatar_on_camera",
            "use_reference_image",
            "reference_image_source",
            "avatar_instruction",
            "scene_summary",
            "fidelity",
            "voiceover",
            "on_screen_text",
            "framing_notes",
        ]:
            if key not in scene:
                return f"scene {index + 1} missing {key}"
        duration = _coerce_int(scene.get("duration"))
        if duration <= 0:
            return f"scene {index + 1} duration must be positive"
        scene_duration_sum += duration
        for key in ["scene_id", "purpose", "avatar_instruction", "scene_summary", "fidelity", "voiceover", "framing_notes"]:
            if not str(scene.get(key) or "").strip():
                return f"scene {index + 1} has empty {key}"
        on_screen_text = scene.get("on_screen_text")
        if not isinstance(on_screen_text, dict) or not str(on_screen_text.get("text") or "").strip():
            return f"scene {index + 1} on_screen_text.text is required"
        if bool(scene.get("use_reference_image")) and not str(scene.get("avatar_instruction") or "").startswith(
            "subject from reference image, identity preserved, no facial morphing, no appearance drift"
        ):
            return f"scene {index + 1} reference-image avatar_instruction missing identity lock token"
        forbidden = _forbidden_ad_creative_phrase(
            " ".join(
                str(part or "")
                for part in [
                    scene.get("voiceover"),
                    scene.get("scene_summary"),
                    on_screen_text.get("text"),
                ]
            )
        )
        if forbidden:
            return f"scene {index + 1} contains forbidden CTA/platform phrase: {forbidden}"
        delivery_forbidden = _forbidden_scenario_delivery_phrase(
            " ".join(
                str(part or "")
                for part in [
                    scene.get("voiceover"),
                    on_screen_text.get("text"),
                ]
            )
        )
        if delivery_forbidden:
            return f"scene {index + 1} contains internal production wording in customer-facing copy: {delivery_forbidden}"
    if scene_duration_sum != total_duration:
        return f"scene durations sum to {scene_duration_sum}, expected {total_duration}"
    if str(scenes[0].get("purpose") or "").lower() != "hook" or not bool(scenes[0].get("avatar_on_camera")):
        return "first scene must be a hook with avatar_on_camera=true"
    if not bool(scenes[-1].get("avatar_on_camera")):
        return "last scene must have avatar_on_camera=true"
    if not str(variant.get("hypothesis") or "").strip():
        return "hypothesis is required"
    return ""


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _static_product_prompt_payload(product_analysis: dict[str, Any]) -> dict[str, Any]:
    facts = product_analysis.get("known_product_facts") or {}
    visual = product_analysis.get("visual_product_understanding") or {}
    return {
        "product_name": _clip_text(product_analysis.get("product_name"), 120),
        "likely_product_category": product_analysis.get("likely_product_category"),
        "requested_product_category": product_analysis.get("requested_product_category"),
        "known_product_facts": {
            "name": _clip_text(facts.get("name"), 120),
            "category": facts.get("category"),
            "brand": _clip_text(facts.get("brand"), 80),
            "product_line_or_label": _clip_text(facts.get("product_line_or_label"), 100),
            "material": _clip_text(facts.get("material"), 100),
            "color": _clip_text(facts.get("color"), 80),
        },
        "static_material_fidelity_rule": prompt_defaults.STATIC_IMAGE_MATERIAL_FIDELITY_LOCK,
        "visual_product_understanding": _static_visual_understanding_payload(visual),
        "user_provided_facts": _clip_list(product_analysis.get("user_provided_facts"), 8, 140),
        "safe_benefits": _clip_list(product_analysis.get("safe_benefits"), 8, 180),
        "ad_safe_detail_phrases": _clip_list(
            product_analysis.get("ad_safe_detail_phrases"), 8, 120
        ),
        "unsupported_claims": _clip_list(product_analysis.get("unsupported_claims"), 6, 160),
        "safe_use_cases": _clip_list(product_analysis.get("safe_use_cases"), 5, 140),
        "safest_creative_angle": _clip_text(
            product_analysis.get("safest_creative_angle"), 220
        ),
        "internal_brief_notes_summary": _clip_text(
            product_analysis.get("internal_brief_notes"), 700
        ),
    }


def _static_visual_understanding_payload(visual: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(visual, dict) or visual.get("status") != "completed":
        return {}
    return {
        "status": visual.get("status"),
        "detected_object": _clip_text(visual.get("detected_object"), 100),
        "subcategory": _clip_text(visual.get("subcategory"), 80),
        "category_confidence": visual.get("category_confidence"),
        "recommended_template_id": _clip_text(visual.get("recommended_template_id"), 80),
        "scenario_rules": _clip_list(visual.get("scenario_rules"), 4, 120),
        "shot_requirements": _clip_list(visual.get("shot_requirements"), 4, 120),
        "avoid_in_generation": _clip_list(visual.get("avoid_in_generation"), 4, 120),
        "qa_expectations": _clip_list(visual.get("qa_expectations"), 4, 120),
        "rule": "Use visual classifier output for static shot selection and QA expectations only; do not turn it into customer-facing claim text.",
    }


def _static_ugc_prompt_payload(ugc_strategy: dict[str, Any]) -> dict[str, Any]:
    return {
        "hook": _clip_text(ugc_strategy.get("hook"), 180),
        "voice_profile": _clip_text(ugc_strategy.get("voice_profile"), 260),
        "market": ugc_strategy.get("market"),
        "language": ugc_strategy.get("language"),
        "platform": ugc_strategy.get("platform"),
        "selected_angle": _clip_text(ugc_strategy.get("selected_angle"), 200),
        "ad_detail_phrases": _clip_list(ugc_strategy.get("ad_detail_phrases"), 8, 120),
        "on_screen_text": _clip_list(ugc_strategy.get("on_screen_text"), 5, 80),
        "audience_research": {
            "primary_archetype": _clip_text(
                (ugc_strategy.get("audience_research") or {}).get("primary_archetype"), 80
            ),
            "secondary_archetypes": _clip_list(
                (ugc_strategy.get("audience_research") or {}).get("secondary_archetypes"),
                3,
                60,
            ),
            "decision_triggers": _clip_list(
                (ugc_strategy.get("audience_research") or {}).get("decision_triggers"),
                5,
                120,
            ),
        },
        "creative_psychology": {
            "primary_driver": _clip_text(
                (ugc_strategy.get("creative_psychology") or {}).get("primary_driver"),
                180,
            ),
            "behavior_sequence": _clip_list(
                ((ugc_strategy.get("creative_psychology") or {}).get("behavior_tree") or {}).get(
                    "sequence"
                ),
                5,
                100,
            ),
        },
        "emotional_angle": {
            "primary_angle": _clip_text(
                (ugc_strategy.get("emotional_angle") or {}).get("primary_angle"), 60
            ),
            "safe_label": _clip_text(
                (ugc_strategy.get("emotional_angle") or {}).get("primary_safe_label"), 80
            ),
            "driver": _clip_text((ugc_strategy.get("emotional_angle") or {}).get("driver"), 180),
            "creative_set_bias": (ugc_strategy.get("emotional_angle") or {}).get("creative_set_bias"),
        },
        "voice_personality": {
            key: _clip_text((ugc_strategy.get("voice_personality") or {}).get(key), 120)
            for key in ["tone", "energy", "confidence", "creator_style", "pacing", "gesture_style", "accent_profile"]
        },
        "scene_chaining": {
            "mode": _clip_text((ugc_strategy.get("scene_chaining") or {}).get("mode"), 80),
            "reference_strategy": _clip_text(
                (ugc_strategy.get("scene_chaining") or {}).get("reference_strategy"), 220
            ),
            "seedance_prompt_addendum": _clip_text(
                (ugc_strategy.get("scene_chaining") or {}).get("seedance_prompt_addendum"), 500
            ),
        },
        "ad_angle_multiplier": {
            "version": (ugc_strategy.get("ad_angle_multiplier") or {}).get("version"),
            "angle_count": (ugc_strategy.get("ad_angle_multiplier") or {}).get("angle_count"),
            "families": _clip_list((ugc_strategy.get("ad_angle_multiplier") or {}).get("families"), 6, 40),
            "angles": _clip_dict_list(
                (ugc_strategy.get("ad_angle_multiplier") or {}).get("angles"),
                8,
                {
                    "angle_family": 40,
                    "angle": 80,
                    "hook": 140,
                    "creative_test_hypothesis": 180,
                    "visual_direction": 180,
                },
            ),
        },
        "ad_angle_selector": {
            "version": (ugc_strategy.get("ad_angle_selector") or {}).get("version"),
            "strategy": (ugc_strategy.get("ad_angle_selector") or {}).get("selection_strategy"),
            "memory_used": (ugc_strategy.get("ad_angle_selector") or {}).get("memory_used"),
            "memory_confidence": (ugc_strategy.get("ad_angle_selector") or {}).get("memory_confidence"),
            "slot_selection": {
                slot: {
                    "family": selection.get("selected_family"),
                    "hook": _clip_text(selection.get("selected_hook"), 140),
                    "score": selection.get("score"),
                    "reason": _clip_text(selection.get("selection_reason"), 220),
                }
                for slot, selection in ((ugc_strategy.get("ad_angle_selector") or {}).get("slot_selection") or {}).items()
                if isinstance(selection, dict)
            },
        },
        "competitor_strategy": {
            "status": (ugc_strategy.get("competitor_strategy") or {}).get("status"),
            "adaptation_brief": _clip_text(
                (ugc_strategy.get("competitor_strategy") or {}).get("adaptation_brief"), 600
            ),
            "strategic_patterns": _clip_list(
                ((ugc_strategy.get("competitor_strategy") or {}).get("strategy_extraction") or {}).get("strategic_patterns"),
                6,
                120,
            ),
            "originality_rules": _clip_list(
                ((ugc_strategy.get("competitor_strategy") or {}).get("originality_guard") or {}).get("rules"),
                4,
                180,
            ),
        },
        "performance_memory": {
            "matching_record_count": (ugc_strategy.get("performance_insights") or {}).get(
                "matching_record_count"
            ),
            "winner_count": (ugc_strategy.get("performance_insights") or {}).get("winner_count"),
            "winning_hooks": _clip_list(
                (ugc_strategy.get("performance_insights") or {}).get("winning_hooks"),
                3,
                120,
            ),
            "winning_shot_types": _clip_list(
                (ugc_strategy.get("performance_insights") or {}).get("winning_shot_types"),
                3,
                100,
            ),
            "creative_memory_rag": {
                "knowledge_item_count": (
                    ((ugc_strategy.get("performance_insights") or {}).get("creative_memory_rag") or {}).get(
                        "knowledge_item_count"
                    )
                ),
                "winning_patterns": _clip_list(
                    ((ugc_strategy.get("performance_insights") or {}).get("creative_memory_rag") or {}).get(
                        "winning_patterns"
                    ),
                    6,
                    120,
                ),
                "avoid_patterns": _clip_list(
                    ((ugc_strategy.get("performance_insights") or {}).get("creative_memory_rag") or {}).get(
                        "avoid_patterns"
                    ),
                    6,
                    120,
                ),
                "prompt_guidance": _clip_text(
                    ((ugc_strategy.get("performance_insights") or {}).get("creative_memory_rag") or {}).get(
                        "prompt_guidance"
                    ),
                    700,
                ),
            },
        },
    }


def _static_ads_prompt_payload(ads_creative_set: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": ads_creative_set.get("platform"),
        "market": ads_creative_set.get("market"),
        "language": ads_creative_set.get("language"),
        "selected_product_category": ads_creative_set.get("selected_product_category"),
        "static_product_material_fidelity_lock": _clip_text(
            ads_creative_set.get("static_product_material_fidelity_lock"), 900
        ),
        "static_visual_classifier_directive": _clip_text(
            ads_creative_set.get("static_visual_classifier_directive"), 900
        ),
        "category_image_directive": _clip_text(
            ads_creative_set.get("category_image_directive"), 1000
        ),
        "creative_plan": _compact_creative_plan(ads_creative_set.get("creative_plan")),
        "static_image_ads": _compact_static_image_ads(ads_creative_set.get("static_image_ads")),
        "carousel_ad": _compact_carousel_ad(ads_creative_set.get("carousel_ad")),
        "cta_link_policy": ads_creative_set.get("cta_link_policy"),
        "compliance_notes": _clip_text(ads_creative_set.get("compliance_notes"), 700),
        "creative_angles": _clip_dict_list(
            ads_creative_set.get("creative_angles"),
            8,
            {"angle": 60, "motivation": 160, "hook": 140, "variation_rule": 180},
        ),
        "hook_bank": _clip_dict_list(
            ads_creative_set.get("hook_bank"), 10, {"pattern": 60, "hook": 140}
        ),
        "meme_style_creatives": _clip_dict_list(
            ads_creative_set.get("meme_style_creatives"),
            3,
            {
                "creative_id": 80,
                "layout": 160,
                "visual_prompt": 320,
                "copy": 220,
                "fatigue_note": 160,
            },
        ),
        "primary_text_variants": _clip_dict_list(
            ads_creative_set.get("primary_text_variants"),
            3,
            {"framework": 40, "primary_text": 420},
        ),
        "ad_description_suggestions": _compact_ad_description_suggestions(
            ads_creative_set.get("ad_description_suggestions")
        ),
        "google_ads_assets": _compact_google_ads_assets(
            ads_creative_set.get("google_ads_assets")
        ),
    }


def _compact_creative_plan(plan: Any) -> list[dict[str, Any]]:
    if not isinstance(plan, list):
        return []
    compact = []
    for item in plan[:6]:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "set_id": item.get("set_id"),
                "creative_type": item.get("creative_type"),
                "angle": item.get("angle"),
                "funnel_stage": item.get("funnel_stage"),
                "budget_share_percent": item.get("budget_share_percent"),
                "generation_target": _clip_text(item.get("generation_target"), 120),
                "notes": _clip_text(item.get("notes"), 180),
            }
        )
    return compact


def _compact_static_image_ads(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compact = []
    for item in items[:4]:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "creative_id": item.get("creative_id"),
                "set_id": item.get("set_id"),
                "creative_type": item.get("creative_type"),
                "angle": _clip_text(item.get("angle"), 80),
                "angle_family": _clip_text(item.get("angle_family"), 40),
                "angle_multiplier_angle": _clip_text(item.get("angle_multiplier_angle"), 80),
                "angle_multiplier_hook": _clip_text(item.get("angle_multiplier_hook"), 140),
                "angle_diversity_contract": _clip_text(item.get("angle_diversity_contract"), 220),
                "aspect_ratio": item.get("aspect_ratio"),
                "funnel_stage": item.get("funnel_stage"),
                "budget_share_percent": item.get("budget_share_percent"),
                "layout": _clip_text(item.get("layout"), 180),
                "concept": _clip_text(item.get("concept"), 180),
                "why_this_angle": _clip_text(item.get("why_this_angle"), 220),
                "visual_prompt": _clip_text(item.get("visual_prompt"), 520),
                "overlay_text": _clip_text(item.get("overlay_text"), 48),
                "headline": _clip_text(item.get("headline"), 64),
                "primary_text": _clip_text(item.get("primary_text"), 360),
            }
        )
    return compact


def _compact_carousel_ad(carousel: Any) -> dict[str, Any]:
    if not isinstance(carousel, dict):
        return {}
    cards = []
    for card in (carousel.get("cards") or [])[:5]:
        if not isinstance(card, dict):
            continue
        cards.append(
            {
                "card_number": card.get("card_number"),
                "role": _clip_text(card.get("role"), 100),
                "angle_family": _clip_text(card.get("angle_family"), 40),
                "angle_multiplier_angle": _clip_text(card.get("angle_multiplier_angle"), 80),
                "angle_multiplier_hook": _clip_text(card.get("angle_multiplier_hook"), 140),
                "angle_diversity_contract": _clip_text(card.get("angle_diversity_contract"), 180),
                "visual_prompt": _clip_text(card.get("visual_prompt"), 320),
                "overlay_text": _clip_text(card.get("overlay_text"), 48),
            }
        )
    return {
        "set_id": carousel.get("set_id"),
        "creative_type": carousel.get("creative_type"),
        "angle": carousel.get("angle"),
        "aspect_ratio": carousel.get("aspect_ratio"),
        "funnel_stage": carousel.get("funnel_stage"),
        "budget_share_percent": carousel.get("budget_share_percent"),
        "primary_text": _clip_text(carousel.get("primary_text"), 420),
        "cards": cards,
    }


def _compact_ad_description_suggestions(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    variants = _clip_dict_list(
        value.get("variants"),
        4,
        {
            "variant_id": 60,
            "angle": 80,
            "primary_text": 420,
            "headline": 64,
            "description": 130,
            "hypothesis": 180,
        },
    )
    return {"usage_note": _clip_text(value.get("usage_note"), 220), "variants": variants}


def _compact_google_ads_assets(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "rsa_headlines": _clip_list(value.get("rsa_headlines"), 8, 40),
        "rsa_descriptions": _clip_list(value.get("rsa_descriptions"), 4, 110),
        "pmax_long_headlines": _clip_list(value.get("pmax_long_headlines"), 4, 110),
    }


def _prompt_budget_report(user_payload: dict[str, Any]) -> dict[str, Any]:
    content = json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))
    before_chars = len(content)
    truncated_for_budget = False
    if before_chars > STATIC_CREATIVE_PROMPT_MAX_USER_CHARS:
        budgeted_payload = json.loads(json.dumps(user_payload, ensure_ascii=False))
        _shrink_static_prompt_payload(budgeted_payload)
        content = json.dumps(budgeted_payload, ensure_ascii=False, separators=(",", ":"))
        truncated_for_budget = True
    if len(content) > STATIC_CREATIVE_PROMPT_MAX_USER_CHARS:
        minimal_payload = _minimal_static_prompt_payload(user_payload)
        content = json.dumps(minimal_payload, ensure_ascii=False, separators=(",", ":"))
        truncated_for_budget = True
    hard_fit_applied = False
    if len(content) > STATIC_CREATIVE_PROMPT_MAX_USER_CHARS:
        fitted_payload = _ultra_minimal_static_prompt_payload(user_payload)
        content = json.dumps(fitted_payload, ensure_ascii=False, separators=(",", ":"))
        truncated_for_budget = True
        hard_fit_applied = True
    return {
        "content": content,
        "metadata": {
            "max_user_chars": STATIC_CREATIVE_PROMPT_MAX_USER_CHARS,
            "user_chars_before_budget": before_chars,
            "user_chars_sent": len(content),
            "truncated_for_budget": truncated_for_budget,
            "hard_fit_applied": hard_fit_applied,
            "field_limits": STATIC_CREATIVE_PROMPT_FIELD_LIMITS,
        },
    }


def _minimal_static_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ads = payload.get("ads_creative_set") if isinstance(payload.get("ads_creative_set"), dict) else {}
    product = (
        payload.get("product_analysis")
        if isinstance(payload.get("product_analysis"), dict)
        else {}
    )
    result = {
        "task": _clip_text(payload.get("task"), 900),
        "output_size_contract": STATIC_CREATIVE_PROMPT_FIELD_LIMITS,
        "product_analysis": {
            "product_name": _clip_text(product.get("product_name"), 120),
            "likely_product_category": product.get("likely_product_category"),
            "known_product_facts": product.get("known_product_facts") or {},
            "static_material_fidelity_rule": _clip_text(
                product.get("static_material_fidelity_rule"), 500
            ),
            "visual_product_understanding": product.get("visual_product_understanding") or {},
            "user_provided_facts": _clip_list(product.get("user_provided_facts"), 5, 100),
            "safe_benefits": _clip_list(product.get("safe_benefits"), 4, 120),
            "ad_safe_detail_phrases": _clip_list(
                product.get("ad_safe_detail_phrases"), 5, 90
            ),
        },
        "ugc_strategy_context": _minimal_ugc_prompt_payload(payload.get("ugc_strategy_context")),
        "ads_creative_set": {
            "platform": ads.get("platform"),
            "market": ads.get("market"),
            "language": ads.get("language"),
            "selected_product_category": ads.get("selected_product_category"),
            "static_product_material_fidelity_lock": _clip_text(
                ads.get("static_product_material_fidelity_lock"), 500
            ),
            "static_visual_classifier_directive": _clip_text(
                ads.get("static_visual_classifier_directive"), 500
            ),
            "creative_plan": ads.get("creative_plan") or [],
            "static_image_ads": ads.get("static_image_ads") or [],
            "carousel_ad": ads.get("carousel_ad") or {},
            "cta_link_policy": ads.get("cta_link_policy"),
        },
        "_truncated_for_prompt_budget": True,
    }
    if isinstance(payload.get("prompt_shard"), dict):
        result["prompt_shard"] = payload["prompt_shard"]
    return result


def _minimal_ugc_prompt_payload(value: Any) -> dict[str, Any]:
    ugc = value if isinstance(value, dict) else {}
    selector = ugc.get("ad_angle_selector") if isinstance(ugc.get("ad_angle_selector"), dict) else {}
    selected_slots = {}
    for slot, selection in (selector.get("slot_selection") or {}).items():
        if not isinstance(selection, dict):
            continue
        selected_slots[slot] = {
            "family": selection.get("family") or selection.get("selected_family"),
            "hook": _clip_text(selection.get("hook") or selection.get("selected_hook"), 100),
            "reason": _clip_text(selection.get("reason") or selection.get("selection_reason"), 140),
        }
    competitor = ugc.get("competitor_strategy") if isinstance(ugc.get("competitor_strategy"), dict) else {}
    extraction = competitor.get("strategy_extraction") if isinstance(competitor.get("strategy_extraction"), dict) else {}
    return {
        "hook": _clip_text(ugc.get("hook"), 140),
        "voice_profile": _clip_text(ugc.get("voice_profile"), 140),
        "market": ugc.get("market"),
        "language": ugc.get("language"),
        "platform": ugc.get("platform"),
        "selected_angle": _clip_text(ugc.get("selected_angle"), 120),
        "ad_detail_phrases": _clip_list(ugc.get("ad_detail_phrases"), 4, 90),
        "on_screen_text": _clip_list(ugc.get("on_screen_text"), 4, 60),
        "ad_angle_selector": {
            "strategy": selector.get("strategy"),
            "slot_selection": selected_slots,
        },
        "competitor_strategy": {
            "status": competitor.get("status"),
            "adaptation_brief": _clip_text(competitor.get("adaptation_brief"), 260),
            "strategic_patterns": _clip_list(extraction.get("strategic_patterns"), 3, 90),
        },
    }


def _ultra_minimal_static_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    minimal = _minimal_static_prompt_payload(payload)
    ads = minimal.get("ads_creative_set") if isinstance(minimal.get("ads_creative_set"), dict) else {}
    product = minimal.get("product_analysis") if isinstance(minimal.get("product_analysis"), dict) else {}
    ugc = minimal.get("ugc_strategy_context") if isinstance(minimal.get("ugc_strategy_context"), dict) else {}
    result = {
        "task": (
            "Rewrite only the selected static image and carousel prompt fields. "
            "Keep IDs and return compact valid JSON."
        ),
        "output_size_contract": STATIC_CREATIVE_PROMPT_FIELD_LIMITS,
        "product_analysis": {
            "product_name": _clip_text(product.get("product_name"), 100),
            "likely_product_category": product.get("likely_product_category"),
            "known_product_facts": product.get("known_product_facts") or {},
            "static_material_fidelity_rule": _clip_text(
                product.get("static_material_fidelity_rule"), 260
            ),
            "visual_product_understanding": product.get("visual_product_understanding") or {},
            "safe_benefits": _clip_list(product.get("safe_benefits"), 3, 90),
            "ad_safe_detail_phrases": _clip_list(product.get("ad_safe_detail_phrases"), 4, 70),
        },
        "ugc_strategy_context": {
            "hook": _clip_text(ugc.get("hook"), 100),
            "market": ugc.get("market"),
            "language": ugc.get("language"),
            "platform": ugc.get("platform"),
            "selected_angle": _clip_text(ugc.get("selected_angle"), 80),
        },
        "ads_creative_set": {
            "platform": ads.get("platform"),
            "market": ads.get("market"),
            "language": ads.get("language"),
            "selected_product_category": ads.get("selected_product_category"),
            "static_product_material_fidelity_lock": _clip_text(
                ads.get("static_product_material_fidelity_lock"), 260
            ),
            "static_visual_classifier_directive": _clip_text(
                ads.get("static_visual_classifier_directive"), 260
            ),
            "static_image_ads": _ultra_compact_static_image_ads(ads.get("static_image_ads")),
            "carousel_ad": _ultra_compact_carousel_ad(ads.get("carousel_ad")),
        },
        "_truncated_for_prompt_budget": True,
        "_hard_fit_applied": True,
    }
    if isinstance(payload.get("prompt_shard"), dict):
        result["prompt_shard"] = payload["prompt_shard"]
    return result


def _ultra_compact_static_image_ads(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compact = []
    for item in items[:4]:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "creative_id": item.get("creative_id"),
                "set_id": item.get("set_id"),
                "creative_type": item.get("creative_type"),
                "angle": _clip_text(item.get("angle"), 80),
                "angle_family": _clip_text(item.get("angle_family"), 40),
                "angle_multiplier_hook": _clip_text(item.get("angle_multiplier_hook"), 100),
                "visual_prompt": _clip_text(item.get("visual_prompt"), 180),
                "overlay_text": _clip_text(item.get("overlay_text"), 48),
                "headline": _clip_text(item.get("headline"), 56),
                "primary_text": _clip_text(item.get("primary_text"), 120),
            }
        )
    return compact


def _ultra_compact_carousel_ad(carousel: Any) -> dict[str, Any]:
    if not isinstance(carousel, dict):
        return {}
    cards = []
    for card in (carousel.get("cards") or [])[:5]:
        if not isinstance(card, dict):
            continue
        cards.append(
            {
                "card_number": card.get("card_number"),
                "role": _clip_text(card.get("role"), 60),
                "angle_family": _clip_text(card.get("angle_family"), 40),
                "angle_multiplier_hook": _clip_text(card.get("angle_multiplier_hook"), 100),
                "visual_prompt": _clip_text(card.get("visual_prompt"), 120),
                "overlay_text": _clip_text(card.get("overlay_text"), 48),
            }
        )
    return {
        "set_id": carousel.get("set_id"),
        "creative_type": carousel.get("creative_type"),
        "primary_text": _clip_text(carousel.get("primary_text"), 140),
        "cards": cards,
    }


def _shrink_static_prompt_payload(payload: dict[str, Any]) -> None:
    product = payload.get("product_analysis")
    if isinstance(product, dict):
        product["safe_benefits"] = _clip_list(product.get("safe_benefits"), 4, 120)
        product["internal_brief_notes_summary"] = _clip_text(
            product.get("internal_brief_notes_summary"), 300
        )
        product["safest_creative_angle"] = _clip_text(
            product.get("safest_creative_angle"), 140
        )
    ads = payload.get("ads_creative_set")
    if isinstance(ads, dict):
        ads["category_image_directive"] = _clip_text(
            ads.get("category_image_directive"), 450
        )
        ads["static_visual_classifier_directive"] = _clip_text(
            ads.get("static_visual_classifier_directive"), 450
        )
        for item in ads.get("static_image_ads") or []:
            if isinstance(item, dict):
                item["visual_prompt"] = _clip_text(item.get("visual_prompt"), 320)
                item["primary_text"] = _clip_text(item.get("primary_text"), 220)
                item["why_this_angle"] = _clip_text(item.get("why_this_angle"), 140)
        carousel = ads.get("carousel_ad")
        if isinstance(carousel, dict):
            carousel["primary_text"] = _clip_text(carousel.get("primary_text"), 240)
            for card in carousel.get("cards") or []:
                if isinstance(card, dict):
                    card["visual_prompt"] = _clip_text(card.get("visual_prompt"), 180)
        ads["ad_description_suggestions"] = {}
        ads["google_ads_assets"] = {}
        ads["meme_style_creatives"] = _clip_dict_list(
            ads.get("meme_style_creatives"),
            2,
            {"creative_id": 60, "layout": 120, "visual_prompt": 180, "copy": 160},
        )


def _clip_dict_list(items: Any, max_items: int, field_limits: dict[str, int]) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    clipped = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            continue
        clipped.append(
            {
                key: _clip_text(item.get(key), limit)
                for key, limit in field_limits.items()
                if item.get(key) is not None
            }
        )
    return clipped


def _clip_list(items: Any, max_items: int, item_limit: int) -> list[str]:
    if not isinstance(items, list):
        return []
    return [
        clipped
        for clipped in (_clip_text(item, item_limit) for item in items[:max_items])
        if clipped
    ]


def _clip_text(value: Any, limit: int) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 16)].rstrip() + " ...[truncated]"


def _merge_static_ads_prompt_enhancement(
    ads_creative_set: dict[str, Any],
    enhanced: dict[str, Any],
    product_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = json.loads(json.dumps(ads_creative_set, ensure_ascii=False))
    if isinstance(enhanced.get("creative_angles"), list):
        result["creative_angles"] = _merge_list_by_key(
            result.get("creative_angles") or [],
            enhanced.get("creative_angles") or [],
            key="angle",
            allowed_fields={"motivation", "hook", "variation_rule"},
        )
    if isinstance(enhanced.get("hook_bank"), list):
        result["hook_bank"] = _merge_list_by_key(
            result.get("hook_bank") or [],
            enhanced.get("hook_bank") or [],
            key="pattern",
            allowed_fields={"hook"},
        )
    static_updates = {
        item.get("creative_id"): item
        for item in enhanced.get("static_image_ads") or []
        if isinstance(item, dict) and item.get("creative_id")
    }
    allowed_static_fields = {"layout", "visual_prompt", "overlay_text", "primary_text", "headline"}
    for item in result.get("static_image_ads") or []:
        update = static_updates.get(item.get("creative_id")) or {}
        for field in allowed_static_fields:
            if isinstance(update.get(field), str) and update[field].strip():
                cleaned = _clean_ad_creative_text(update[field])
                if field == "visual_prompt":
                    cleaned = _static_visual_prompt_or_fallback(
                        cleaned,
                        fallback=item.get(field),
                        product_analysis=product_analysis,
                    )
                item[field] = _clean_overlay_text(cleaned, item.get(field)) if field == "overlay_text" else cleaned

    carousel_update = enhanced.get("carousel_ad") if isinstance(enhanced.get("carousel_ad"), dict) else {}
    carousel = result.get("carousel_ad") if isinstance(result.get("carousel_ad"), dict) else {}
    if isinstance(carousel_update.get("primary_text"), str) and carousel_update["primary_text"].strip():
        carousel["primary_text"] = _clean_ad_creative_text(carousel_update["primary_text"])
    card_updates = {
        card.get("card_number"): card
        for card in carousel_update.get("cards") or []
        if isinstance(card, dict) and card.get("card_number") is not None
    }
    allowed_card_fields = {"visual_prompt", "overlay_text"}
    for card in carousel.get("cards") or []:
        update = card_updates.get(card.get("card_number")) or {}
        for field in allowed_card_fields:
            if isinstance(update.get(field), str) and update[field].strip():
                cleaned = _clean_ad_creative_text(update[field])
                if field == "visual_prompt":
                    cleaned = _static_visual_prompt_or_fallback(
                        cleaned,
                        fallback=card.get(field),
                        product_analysis=product_analysis,
                    )
                card[field] = _clean_overlay_text(cleaned, card.get(field)) if field == "overlay_text" else cleaned
    result["carousel_ad"] = carousel
    if isinstance(enhanced.get("meme_style_creatives"), list):
        result["meme_style_creatives"] = _merge_list_by_key(
            result.get("meme_style_creatives") or [],
            enhanced.get("meme_style_creatives") or [],
            key="creative_id",
            allowed_fields={"layout", "visual_prompt", "copy", "fatigue_note"},
        )
    if isinstance(enhanced.get("primary_text_variants"), list):
        result["primary_text_variants"] = _merge_indexed_list(
            result.get("primary_text_variants") or [],
            enhanced.get("primary_text_variants") or [],
            allowed_fields={"framework", "primary_text"},
        )
    if isinstance(enhanced.get("ad_description_suggestions"), dict):
        _merge_ad_description_suggestions(result, enhanced["ad_description_suggestions"])
    if isinstance(enhanced.get("google_ads_assets"), dict):
        _merge_google_ads_assets(result, enhanced["google_ads_assets"])
    return result


_STATIC_MATERIAL_TERMS = {
    "leather",
    "suede",
    "silk",
    "fabric",
    "canvas",
    "plastic",
    "metal",
    "steel",
    "aluminium",
    "aluminum",
    "wood",
    "wooden",
    "ceramic",
    "rubber",
    "acrylic",
    "cotton",
    "polyester",
    "nylon",
    "matte",
    "glossy",
    "transparent",
    "translucent",
    "opaque",
    "frosted",
    "pebbled",
    "woven",
    "quilted",
    "padded",
    "grained",
}


def _static_visual_prompt_or_fallback(
    value: str,
    *,
    fallback: Any,
    product_analysis: dict[str, Any] | None,
) -> str:
    if _has_unverified_static_material_instruction(value, product_analysis or {}):
        return _clean_ad_creative_text(fallback)
    return value


def _has_unverified_static_material_instruction(
    value: str,
    product_analysis: dict[str, Any],
) -> bool:
    text = str(value or "").lower()
    if not text:
        return False
    allowed_text = _allowed_static_material_text(product_analysis)
    if _has_unverified_glass_instruction(text, allowed_text):
        return True
    for term in _STATIC_MATERIAL_TERMS:
        if not re.search(rf"\b{re.escape(term)}\b", text):
            continue
        if term in allowed_text:
            continue
        if _is_static_protective_material_context(text, term):
            continue
        return True
    return False


def _allowed_static_material_text(product_analysis: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(str(product_analysis.get("product_name") or ""))
    facts = product_analysis.get("known_product_facts") or {}
    if isinstance(facts, dict):
        parts.extend(str(value) for value in facts.values() if value)
    parts.extend(str(item) for item in product_analysis.get("user_provided_facts") or [])
    parts.extend(str(item) for item in product_analysis.get("ad_safe_detail_phrases") or [])
    return " ".join(parts).lower()


def _has_unverified_glass_instruction(text: str, allowed_text: str) -> bool:
    glass_verified = "glass material" in allowed_text or "made of glass" in allowed_text
    glass_material_patterns = [
        r"\bglass-like\b",
        r"\bglass (material|finish|transparency|clarity|body|texture|walls?)\b",
        r"\btransparent glass\b",
        r"\bmake (it|the product)[^.;]*\bglass\b",
        r"\blook(s|ing)? like glass\b",
    ]
    return not glass_verified and any(re.search(pattern, text) for pattern in glass_material_patterns)


def _is_static_protective_material_context(text: str, term: str) -> bool:
    windows = []
    for match in re.finditer(rf"\b{re.escape(term)}\b", text):
        windows.append(text[max(0, match.start() - 90) : match.end() + 90])
    protective_markers = [
        "do not",
        "never",
        "avoid",
        "unless",
        "only if",
        "only when",
        "if verified",
        "if visible",
        "from the reference",
        "not ",
        "non-",
    ]
    return bool(windows) and all(any(marker in window for marker in protective_markers) for window in windows)


def _merge_list_by_key(
    base: list[Any],
    updates: list[Any],
    key: str,
    allowed_fields: set[str],
) -> list[Any]:
    if not all(isinstance(item, dict) for item in base):
        return base
    update_map = {
        item.get(key): item
        for item in updates
        if isinstance(item, dict) and item.get(key) is not None
    }
    merged = json.loads(json.dumps(base, ensure_ascii=False))
    for item in merged:
        update = update_map.get(item.get(key)) or {}
        for field in allowed_fields:
            value = update.get(field)
            if isinstance(value, str) and value.strip():
                item[field] = _clean_ad_creative_text(value)
    return merged


def _merge_indexed_list(
    base: list[Any],
    updates: list[Any],
    allowed_fields: set[str],
) -> list[Any]:
    if not all(isinstance(item, dict) for item in base):
        return base
    merged = json.loads(json.dumps(base, ensure_ascii=False))
    for index, item in enumerate(merged):
        update = updates[index] if index < len(updates) and isinstance(updates[index], dict) else {}
        for field in allowed_fields:
            value = update.get(field)
            if isinstance(value, str) and value.strip():
                item[field] = _clean_ad_creative_text(value)
    return merged


def _merge_ad_description_suggestions(result: dict[str, Any], update: dict[str, Any]) -> None:
    target = result.get("ad_description_suggestions")
    if not isinstance(target, dict):
        return
    variants = target.get("variants")
    update_variants = update.get("variants")
    if not isinstance(variants, list) or not isinstance(update_variants, list):
        return
    updates_by_id = {
        item.get("variant_id"): item
        for item in update_variants
        if isinstance(item, dict) and item.get("variant_id")
    }
    allowed = {"primary_text", "headline", "description", "hypothesis"}
    for item in variants:
        if not isinstance(item, dict):
            continue
        patch = updates_by_id.get(item.get("variant_id")) or {}
        for field in allowed:
            value = patch.get(field)
            if isinstance(value, str) and value.strip():
                item[field] = _clean_ad_creative_text(value)


def _merge_google_ads_assets(result: dict[str, Any], update: dict[str, Any]) -> None:
    target = result.get("google_ads_assets")
    if not isinstance(target, dict):
        return
    for group_name in ["responsive_search_ad", "performance_max"]:
        target_group = target.get(group_name)
        update_group = update.get(group_name)
        if not isinstance(target_group, dict) or not isinstance(update_group, dict):
            continue
        for field in ["headlines", "long_headlines", "descriptions"]:
            target_items = target_group.get(field)
            update_items = update_group.get(field)
            if not isinstance(target_items, list) or not isinstance(update_items, list):
                continue
            for index, item in enumerate(target_items):
                if index >= len(update_items) or not isinstance(item, dict) or not isinstance(update_items[index], dict):
                    continue
                value = update_items[index].get("text")
                if isinstance(value, str) and value.strip():
                    item["text"] = _limit_for_google_field(field, _clean_ad_creative_text(value))
                    item["char_count"] = len(item["text"])


def _limit_for_google_field(field: str, value: str) -> str:
    limit = 90 if field in {"descriptions", "long_headlines"} else 30
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ,.;:-")


_FORBIDDEN_AD_CREATIVE_PHRASES = [
    "use the ad button",
    "ad button",
    "cta button",
    "learn more",
    "shop now",
    "view details",
    "open detail",
    "open the detail",
    "tap to",
    "click to",
    "click here",
    "klikni",
    "tlačítko",
    "tlacitko",
    "cta tlacitko",
    "cta tlačítko",
    "zobrazit detail",
    "zjistit vice",
    "zjistit více",
]


def _forbidden_ad_creative_phrase(value: str) -> str:
    lowered = str(value or "").lower()
    return next((phrase for phrase in _FORBIDDEN_AD_CREATIVE_PHRASES if phrase in lowered), "")


def _forbidden_scenario_delivery_phrase(value: str) -> str:
    lowered = str(value or "").lower()
    phrases = [
        "angle:",
        "hook intent",
        "visual direction",
        "creative test",
        "scene summary",
        "voiceover=",
        "on_screen_text",
        "structured prompt",
        "caption contract",
        "product_rules",
        "i'd show",
        "i would show",
        "i'd check",
        "i would check",
        "here, i'd",
        "then i'd",
        "tady bych",
        "hier wuerde ich",
        "hier würde ich",
    ]
    return next((phrase for phrase in phrases if phrase in lowered), "")


def _clean_ad_creative_text(value: str) -> str:
    text = " ".join(str(value).replace("\r", "\n").split())
    lowered = text.lower()
    for phrase in _FORBIDDEN_AD_CREATIVE_PHRASES:
        if phrase in lowered:
            text = _remove_phrase_case_insensitive(text, phrase)
            lowered = text.lower()
    text = " ".join(text.split()).strip(" -|,.;:")
    if text.lower().endswith("with no"):
        text = f"{text[:-7].rstrip()} without fake platform controls"
    return text


def _clean_overlay_text(value: str, fallback: Any = "") -> str:
    text = _clean_ad_creative_text(value)
    fallback_text = _clean_ad_creative_text(str(fallback or ""))
    if not text or _looks_like_internal_overlay_text(text):
        return fallback_text if fallback_text and not _looks_like_internal_overlay_text(fallback_text) else "Check the details"
    return text


def _looks_like_internal_overlay_text(value: str) -> bool:
    normalized = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    internal_markers = {
        "hero view",
        "main view",
        "hauptansicht",
        "hlavni pohled",
        "product hero",
        "product first",
        "use context",
        "outfit context",
        "detail proof",
        "proof detail",
        "buying guide",
        "final check",
        "static image",
        "creative angle",
        "angle family",
        "desire angle",
        "identity angle",
        "proof angle",
        "pain angle",
        "urgency angle",
        "contrarian angle",
        "carousel",
        "product view",
    }
    return any(marker in normalized for marker in internal_markers) or normalized in {"c2", "c3", "c4", "c5"}


def _remove_phrase_case_insensitive(text: str, phrase: str) -> str:
    start = text.lower().find(phrase.lower())
    while start >= 0:
        end = start + len(phrase)
        text = f"{text[:start]} {text[end:]}"
        start = text.lower().find(phrase.lower())
    return text


def _compile_structured_prompt(
    structured_prompt: dict[str, Any],
    fallback_package: dict[str, Any],
) -> str:
    variant = structured_prompt["variants"][0]
    scenes = variant.get("scenes") or []
    finance_mode = fallback_package.get("creative_mode") == "finance_personal_brand"
    lines = [
        "Create a realistic creator product video from this structured scene plan.",
        f"Platform: {variant.get('platform')}. Market: {variant.get('market')}. Language: {variant.get('language')}.",
        f"Duration: {variant.get('total_duration_seconds')} seconds. Aspect ratio: {variant.get('aspect_ratio')}.",
        f"Seedance mode: {variant.get('seedance_mode')}. Reference strategy: {variant.get('reference_image_strategy')}.",
        "Preserve product fidelity and, when avatar reference image is supplied, preserve the user's AI avatar identity without facial morphing or appearance drift.",
    ]
    voice_profile = fallback_package.get("voice_profile")
    if voice_profile:
        lines.append(f"Voice profile: {voice_profile}.")
    category_prompt = fallback_package.get("category_prompt_directive")
    if category_prompt:
        lines.append(f"Category-specific product prompt: {category_prompt}.")
    environment_control = fallback_package.get("environment_control_directive")
    if environment_control:
        lines.append(f"Environment control: {environment_control}.")
    video_extra = fallback_package.get("ugc_video_extra_prompt")
    if video_extra:
        lines.append(f"Extra creator video direction: {video_extra}.")
    scenario_lock = fallback_package.get("user_scenario_lock") or {}
    if isinstance(scenario_lock, dict) and scenario_lock.get("enabled"):
        lines.append(
            "User scenario lock: "
            f"template={scenario_lock.get('template_id')}; hook={scenario_lock.get('hook_text')}; "
            f"rules={scenario_lock.get('rules')}; forbidden={scenario_lock.get('forbidden')}."
        )
    scene_chaining = fallback_package.get("scene_chaining") or {}
    if scene_chaining.get("seedance_prompt_addendum"):
        lines.append(f"Scene chaining: {scene_chaining.get('seedance_prompt_addendum')}.")
    for index, scene in enumerate(scenes):
        visible_text_rule = _structured_visible_text_rule(scene, finance_mode, index)
        lines.append(
            " | ".join(
                [
                    f"Scene {scene.get('scene_id')} ({scene.get('duration')}s, {scene.get('purpose')})",
                    f"avatar_on_camera={scene.get('avatar_on_camera')}",
                    f"use_reference_image={scene.get('use_reference_image')}",
                    f"reference_image_source={scene.get('reference_image_source')}",
                    f"avatar_instruction={scene.get('avatar_instruction')}",
                    f"scene_summary={scene.get('scene_summary')}",
                    f"fidelity={scene.get('fidelity')}",
                    f"voiceover={scene.get('voiceover')}",
                    visible_text_rule,
                    f"framing_notes={scene.get('framing_notes')}",
                    f"continuity_notes={scene.get('continuity_notes')}",
                ]
            )
        )
    stitching = variant.get("stitching") or {}
    if stitching:
        lines.append(
            f"Stitching: {stitching.get('transition_style')}; {stitching.get('cut_timing_notes')}"
        )
    if variant.get("safety_rewrites"):
        lines.append(f"Safety rewrites applied: {variant.get('safety_rewrites')}")
    negative = fallback_package.get("negative_prompt")
    if negative:
        lines.append(f"Negative prompt: {negative}")
    return " ".join(str(line).replace("\n", " ").strip() for line in lines if line)


def _structured_visible_text_rule(scene: dict[str, Any], finance_mode: bool, index: int) -> str:
    on_screen_text = scene.get("on_screen_text") or {}
    text = str(on_screen_text.get("text") or "").strip() if isinstance(on_screen_text, dict) else ""
    position = str(on_screen_text.get("position") or "upper_third_center") if isinstance(on_screen_text, dict) else "upper_third_center"
    if finance_mode:
        return f"approved_visible_text={text} at {position}"
    return (
        "no_generated_text=true; on_screen_text is post-production metadata only; do not render hook stickers, subtitles, captions, lower thirds, CTA text, labels, floating text, platform UI, prompt terms, random words, or later-scene text"
    )


def _normalize_seedance_prompt(prompt: str) -> str:
    return (
        prompt.replace("4:5 aspect ratio", "9:16 aspect ratio")
        .replace("aspect ratio 4:5", "aspect ratio 9:16")
        .replace("in 4:5", "in 9:16")
        .replace("4:5 vertical", "9:16 vertical")
    )


def _append_video_extra_direction(prompt: str, fallback_package: dict[str, Any]) -> str:
    video_extra = str(fallback_package.get("ugc_video_extra_prompt") or "").strip()
    if not video_extra or video_extra in prompt:
        return prompt
    return _normalize_seedance_prompt(f"{prompt} Extra UGC video direction: {video_extra}")


def _append_environment_control(prompt: str, fallback_package: dict[str, Any]) -> str:
    environment_control = str(fallback_package.get("environment_control_directive") or "").strip()
    if not environment_control or environment_control in prompt:
        return prompt
    return _normalize_seedance_prompt(f"{prompt} Environment control: {environment_control}")


def _sanitize_for_prompt_model(value: dict[str, Any]) -> dict[str, Any]:
    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            cleaned = {}
            for key, child in item.items():
                if key == "input_references":
                    cleaned[key] = "[image references available to video generator; omitted from prompt model request]"
                else:
                    cleaned[key] = clean(child)
            return cleaned
        if isinstance(item, list):
            return [clean(child) for child in item]
        if isinstance(item, str) and item.startswith("data:image/"):
            return "[image data url omitted]"
        return item

    return clean(value)


def _parse_json_object(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("OpenRouter prompt model did not return a JSON object.")
    return parsed
