from __future__ import annotations

from typing import Any

from app.services import ad_angle_multiplier, ad_angle_selector, prompt_defaults
from app.services.localization_utils import (
    is_czech as _is_czech_language,
    is_german,
    localize_category,
    localize_phrases,
    localize_phrase,
)

STATIC_DROPSHIPPING_REALISM_DIRECTIVE = (
    "Dropshipping static realism: buyer-proof product check, not a polished catalogue or luxury brand shoot. "
    "Use ordinary natural light, real shadows, simple surroundings, honest scale/fit/detail proof, and slight "
    "real-camera imperfection. Avoid showroom or studio staging, glossy retouch, cinematic grading, fake reviews, "
    "ratings, discounts, scarcity, luxury cues, platform UI, and overproduced DTC perfection. Keep overlay text "
    "minimal and preferably post-production; if rendered, one short safe-area label only."
)


def generate_ad_set(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    avatar: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    language = str(settings.get("language", "en")).lower()
    product_name = product_analysis["product_name"]
    product_url = str(settings.get("product_reference_url") or product_analysis.get("product_image_path") or "")
    safe_benefits = (
        product_analysis.get("ad_safe_detail_phrases_localized")
        or localize_phrases(product_analysis.get("ad_safe_detail_phrases") or [], language)
        or [localize_phrase("clear product details", language)]
    )
    category = product_analysis.get("likely_product_category", "product")
    first_benefit = safe_benefits[0]
    platform = str(ugc_strategy.get("platform") or settings.get("platform") or "meta").lower()
    static_visual_classifier_directive = _static_visual_classifier_directive(product_analysis)
    category_image_directive = _append_once(
        _category_image_directive(product_analysis, settings),
        static_visual_classifier_directive,
    )
    static_material_fidelity_lock = _static_material_fidelity_lock(product_analysis)
    emotional_angle = ugc_strategy.get("emotional_angle") or settings.get("emotional_angle") or {}
    emotional_directive = _emotional_directive(emotional_angle)
    creative_memory = (
        ugc_strategy.get("creative_memory_rag")
        or (ugc_strategy.get("performance_insights") or {}).get("creative_memory_rag")
        or settings.get("creative_memory_guidance")
        or {}
    )
    memory_directive = _memory_directive(creative_memory)
    static_subject_lock = _static_subject_lock(settings, ugc_strategy, content_prompt_package, avatar)
    competitor_strategy = ugc_strategy.get("competitor_strategy") or settings.get("competitor_strategy") or {}
    angle_multiplier = (
        settings.get("ad_angle_multiplier")
        or ugc_strategy.get("ad_angle_multiplier")
        or ad_angle_multiplier.generate(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            settings=settings,
        )
    )
    angle_selector = (
        settings.get("ad_angle_selector")
        or ugc_strategy.get("ad_angle_selector")
        or ad_angle_selector.select(
            angle_multiplier=angle_multiplier,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            settings=settings,
        )
    )
    static_image_ads = _static_image_ads(
        language=language,
        product_name=product_name,
        product_url=product_url,
        first_benefit=first_benefit,
        benefits=safe_benefits,
        category=category,
        category_image_directive=category_image_directive,
        emotional_directive=emotional_directive,
    )
    static_image_ads = _apply_angle_multiplier_to_static_ads(static_image_ads, angle_multiplier, angle_selector)
    if memory_directive:
        static_image_ads = _apply_memory_to_static_ads(static_image_ads, memory_directive)
    if static_subject_lock:
        static_image_ads = _apply_static_subject_lock_to_static_ads(static_image_ads, static_subject_lock)
    static_image_ads = _apply_static_dropshipping_realism_to_static_ads(static_image_ads)
    carousel_ad = _carousel_ad(
        language=language,
        product_url=product_url,
        benefits=safe_benefits,
        testimonial_source=str(settings.get("testimonial_source") or ""),
        category=category,
        category_image_directive=category_image_directive,
    )
    carousel_ad = _apply_angle_multiplier_to_carousel(carousel_ad, angle_multiplier, angle_selector)
    if memory_directive:
        carousel_ad = _apply_memory_to_carousel(carousel_ad, memory_directive)
    if static_subject_lock:
        carousel_ad = _apply_static_subject_lock_to_carousel(carousel_ad, static_subject_lock)
    carousel_ad = _apply_static_dropshipping_realism_to_carousel(carousel_ad)
    static_creative_director = _static_creative_director_audit(
        static_image_ads=static_image_ads,
        carousel_ad=carousel_ad,
        category=category,
    )
    ad_set = {
        "agent": "Ads Creative Set Agent",
        "objective": _objective_for_platform(platform),
        "platform": platform,
        "market": ugc_strategy.get("market"),
        "language": ugc_strategy.get("language"),
        "cta_link_policy": _cta_link_policy(platform),
        "selected_product_category": category,
        "category_image_directive": category_image_directive,
        "static_visual_classifier_directive": static_visual_classifier_directive,
        "static_product_material_fidelity_lock": static_material_fidelity_lock,
        "static_subject_lock": static_subject_lock,
        "marketing_skill_applied": {
            "source": "coreyhaines31/marketingskills skills/ad-creative",
            "principles": [
                "define 3-5 distinct creative angles before writing variations",
                "generate variations per angle instead of near-duplicate copy",
                "validate copy against platform character limits",
                "organize assets in platform-ready structures",
            ],
        },
        "angle_multiplier_skill_applied": {
            "source": "ad-angle-multiplier",
            "version": angle_multiplier.get("version"),
            "families": angle_multiplier.get("families") or [],
            "angle_count": angle_multiplier.get("angle_count") or len(angle_multiplier.get("angles") or []),
            "rule": "Generate materially distinct Pain/Desire/Proof/Identity/Contrarian/Urgency angles instead of minor rewrites.",
        },
        "angle_selector_applied": {
            "source": "ad-angle-selector",
            "version": angle_selector.get("version"),
            "strategy": angle_selector.get("selection_strategy"),
            "memory_used": angle_selector.get("memory_used"),
            "memory_confidence": angle_selector.get("memory_confidence"),
            "competitor_bias_used": angle_selector.get("competitor_bias_used"),
            "rule": "Select the best angle for each C1-C5 slot using slot role priors plus memory winners and avoid patterns.",
        },
        "competitor_strategy_applied": {
            "source": "competitor-strategy-chat",
            "version": competitor_strategy.get("version"),
            "status": competitor_strategy.get("status"),
            "adaptation_brief": competitor_strategy.get("adaptation_brief"),
            "originality_guard": competitor_strategy.get("originality_guard") or {},
            "temporary_context_only": bool(competitor_strategy.get("temporary_context_only")),
            "rule": "Competitor inputs inform strategy only for this ad set; generated assets must stay original.",
        },
        "platform_copy_specs": _platform_copy_specs(platform),
        "creative_brain": {
            "audience_research": ugc_strategy.get("audience_research"),
            "emotional_angle": emotional_angle,
            "creative_psychology": ugc_strategy.get("creative_psychology"),
            "voice_personality": ugc_strategy.get("voice_personality"),
            "scene_chaining": ugc_strategy.get("scene_chaining"),
            "hook_strategy": ugc_strategy.get("hook_strategy"),
            "scene_direction": ugc_strategy.get("scene_direction"),
            "performance_insights": ugc_strategy.get("performance_insights"),
            "creative_memory_rag": creative_memory,
            "competitor_strategy": competitor_strategy,
        },
        "prompt_learning_directive": memory_directive,
        "ad_angle_multiplier": angle_multiplier,
        "ad_angle_selector": angle_selector,
        "creative_angles": _creative_angles_from_multiplier(angle_multiplier)
        or _creative_angles(language, product_name, first_benefit, category, emotional_angle),
        "creative_plan": _creative_plan(),
        "ugc_video_ad": {
            "set_id": "C1",
            "creative_type": "UGC video",
            "angle": "UGC",
            "aspect_ratio": ugc_strategy.get("aspect_ratio"),
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 55,
            "format": "UGC video",
            "hook": ugc_strategy.get("hook"),
            "selected_angle_family": (ad_angle_selector.selected_for(angle_selector, "C1") or {}).get("selected_family"),
            "angle_selector_hook": (ad_angle_selector.selected_for(angle_selector, "C1") or {}).get("selected_hook"),
            "creative_test_hypothesis": (ad_angle_selector.selected_for(angle_selector, "C1") or {}).get("creative_test_hypothesis"),
            "angle_selection_reason": (ad_angle_selector.selected_for(angle_selector, "C1") or {}).get("selection_reason"),
            "seedance_prompt": content_prompt_package.get("seedance_video_prompt"),
            "structured_scene_prompt": content_prompt_package.get("structured_scene_prompt"),
            "usage": "Primary cold-traffic creative and retargeting anchor.",
        },
        "hook_bank": _hook_bank_from_multiplier(angle_multiplier)
        or _hook_bank(language, product_name, first_benefit, category),
        "static_image_ads": static_image_ads,
        "carousel_ad": carousel_ad,
        "static_creative_director": static_creative_director,
        "meme_style_creatives": _meme_style_creatives(
            language=language,
            product_name=product_name,
            first_benefit=first_benefit,
        ),
        "ad_description_suggestions": _ad_description_suggestions(
            language=language,
            platform=platform,
            product_name=product_name,
            first_benefit=first_benefit,
            category=category,
        ),
        "primary_text_variants": _copy_pack(language, product_name, first_benefit, category),
        "google_ads_assets": _google_ads_assets(language, product_name, first_benefit, category),
        "compliance_notes": [
            "Do not invent reviews, ratings, discounts, scarcity, statistics, medical effects, or status-signaling claims.",
            "Use social proof only when the source is supplied and verified.",
            "If using before/after framing, compare awareness or selection context, not product performance or body/health outcomes.",
            _destination_url_note(platform),
        ],
    }
    ad_set["copy_validation"] = _copy_validation(ad_set)
    return ad_set


def _memory_directive(creative_memory: dict[str, Any]) -> str:
    if not creative_memory:
        return ""
    guidance = str(creative_memory.get("prompt_guidance") or "").strip()
    if guidance and "No historical winners yet" not in guidance:
        return guidance[:700]
    winners = creative_memory.get("winning_patterns") or []
    avoid = creative_memory.get("avoid_patterns") or []
    parts = []
    if winners:
        parts.append("Prefer learned patterns: " + ", ".join(str(item) for item in winners[:5]))
    if avoid:
        parts.append("Avoid rejected patterns: " + ", ".join(str(item) for item in avoid[:5]))
    return ". ".join(parts)[:700]


def _apply_memory_to_static_ads(items: list[dict[str, Any]], directive: str) -> list[dict[str, Any]]:
    updated = []
    for item in items:
        copied = dict(item)
        copied["visual_prompt"] = _append_once(
            copied.get("visual_prompt"),
            f"Creative memory guidance: {directive}",
        )
        copied["memory_guidance_applied"] = directive
        updated.append(copied)
    return updated


def _apply_memory_to_carousel(carousel: dict[str, Any], directive: str) -> dict[str, Any]:
    copied = dict(carousel)
    copied["memory_guidance_applied"] = directive
    copied["cards"] = [
        {
            **card,
            "visual_prompt": _append_once(
                card.get("visual_prompt"),
                f"Creative memory guidance: {directive}",
            ),
        }
        for card in carousel.get("cards") or []
    ]
    return copied


def _apply_static_dropshipping_realism_to_static_ads(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updated = []
    for item in items:
        copied = dict(item)
        copied["visual_prompt"] = _append_once(
            copied.get("visual_prompt"),
            STATIC_DROPSHIPPING_REALISM_DIRECTIVE,
        )
        copied["dropshipping_realism_guard"] = STATIC_DROPSHIPPING_REALISM_DIRECTIVE
        updated.append(copied)
    return updated


def _apply_static_dropshipping_realism_to_carousel(carousel: dict[str, Any]) -> dict[str, Any]:
    copied = dict(carousel)
    copied["dropshipping_realism_guard"] = STATIC_DROPSHIPPING_REALISM_DIRECTIVE
    copied["cards"] = [
        {
            **card,
            "visual_prompt": _append_once(
                card.get("visual_prompt"),
                STATIC_DROPSHIPPING_REALISM_DIRECTIVE,
            ),
        }
        for card in carousel.get("cards") or []
    ]
    return copied


def _creative_angles_from_multiplier(angle_multiplier: dict[str, Any]) -> list[dict[str, Any]]:
    angles = angle_multiplier.get("angles") if isinstance(angle_multiplier, dict) else []
    if not isinstance(angles, list):
        return []
    return [
        {
            "angle": item.get("angle"),
            "angle_family": item.get("angle_family"),
            "motivation": item.get("motivation"),
            "hook": item.get("hook"),
            "creative_test_hypothesis": item.get("creative_test_hypothesis"),
            "visual_direction": item.get("visual_direction"),
            "variation_rule": item.get("variation_rule"),
            "claim_safety": item.get("claim_safety"),
            "source": item.get("source") or "ad-angle-multiplier",
        }
        for item in angles
        if isinstance(item, dict) and item.get("hook")
    ]


def _hook_bank_from_multiplier(angle_multiplier: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = angle_multiplier.get("hook_bank") if isinstance(angle_multiplier, dict) else []
    if not isinstance(hooks, list):
        return []
    return [
        {
            "pattern": item.get("pattern") or f"angle_{index}",
            "angle_family": item.get("angle_family"),
            "hook": item.get("hook"),
            "source": item.get("source") or "ad-angle-multiplier",
        }
        for index, item in enumerate(hooks, start=1)
        if isinstance(item, dict) and item.get("hook")
    ]


def _apply_angle_multiplier_to_static_ads(
    items: list[dict[str, Any]],
    angle_multiplier: dict[str, Any],
    angle_selector: dict[str, Any],
) -> list[dict[str, Any]]:
    family_by_set = {"C2": "Desire", "C3": "Identity", "C4": "Proof", "C6": "Pain", "C7": "Contrarian"}
    updated = []
    for item in items:
        copied = dict(item)
        set_id = str(copied.get("set_id") or "")
        selected = ad_angle_selector.selected_for(angle_selector, set_id, family_by_set.get(set_id))
        angle = _angle_from_selection(angle_multiplier, selected) or _pick_multiplier_angle(
            angle_multiplier,
            family_by_set.get(set_id),
        )
        if angle:
            copied["angle_family"] = angle.get("angle_family")
            copied["angle_multiplier_angle"] = angle.get("angle")
            copied["angle_multiplier_hook"] = angle.get("hook")
            copied["creative_test_hypothesis"] = angle.get("creative_test_hypothesis")
            copied["angle_selector_score"] = selected.get("score")
            copied["angle_selection_reason"] = selected.get("selection_reason")
            copied["variation_rule"] = angle.get("variation_rule")
            copied["angle_diversity_contract"] = _angle_diversity_contract(
                set_id=set_id,
                family=angle.get("angle_family"),
                hook=angle.get("hook"),
                visual_direction=angle.get("visual_direction"),
            )
            copied["why_this_angle"] = _append_once(
                copied.get("why_this_angle"),
                (
                    f"Ad-angle selector chose {angle.get('angle_family')} "
                    f"(score {selected.get('score')}): {angle.get('creative_test_hypothesis')}"
                ),
            )
            copied["visual_prompt"] = _append_once(
                copied.get("visual_prompt"),
                (
                    f"Ad-angle selector bias: {angle.get('angle_family')} angle; "
                    f"hook intent: {angle.get('hook')}; visual direction: {angle.get('visual_direction')}"
                ),
            )
        updated.append(copied)
    return updated


def _apply_angle_multiplier_to_carousel(
    carousel: dict[str, Any],
    angle_multiplier: dict[str, Any],
    angle_selector: dict[str, Any],
) -> dict[str, Any]:
    copied = dict(carousel)
    selected = ad_angle_selector.selected_for(angle_selector, "C5", "Contrarian")
    angle = _angle_from_selection(angle_multiplier, selected) or _pick_multiplier_angle(angle_multiplier, "Contrarian") or _pick_multiplier_angle(angle_multiplier, "Pain")
    if angle:
        copied["angle_family"] = angle.get("angle_family")
        copied["angle_multiplier_angle"] = angle.get("angle")
        copied["angle_multiplier_hook"] = angle.get("hook")
        copied["creative_test_hypothesis"] = angle.get("creative_test_hypothesis")
        copied["angle_selector_score"] = selected.get("score")
        copied["angle_selection_reason"] = selected.get("selection_reason")
    family_rotation = ["Pain", "Desire", "Proof", "Identity", "Urgency"]
    cards = []
    for index, card in enumerate(copied.get("cards") or []):
        card_copy = dict(card)
        card_angle = _pick_multiplier_angle(angle_multiplier, family_rotation[index % len(family_rotation)])
        if card_angle:
            card_copy["angle_family"] = card_angle.get("angle_family")
            card_copy["angle_multiplier_angle"] = card_angle.get("angle")
            card_copy["angle_multiplier_hook"] = card_angle.get("hook")
            card_copy["creative_test_hypothesis"] = card_angle.get("creative_test_hypothesis")
            card_copy["variation_rule"] = card_angle.get("variation_rule")
            card_copy["angle_diversity_contract"] = _angle_diversity_contract(
                set_id="C5",
                family=card_angle.get("angle_family"),
                hook=card_angle.get("hook"),
                visual_direction=card_angle.get("visual_direction"),
            )
            card_copy["visual_prompt"] = _append_once(
                card_copy.get("visual_prompt"),
                f"Card angle bias: {card_angle.get('angle_family')}; {card_angle.get('visual_direction')}",
            )
        cards.append(card_copy)
    copied["cards"] = cards
    return copied


def _angle_from_selection(angle_multiplier: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    selected_id = str(selected.get("selected_angle_id") or "")
    selected_family = str(selected.get("selected_family") or "")
    angles = angle_multiplier.get("angles") if isinstance(angle_multiplier, dict) else []
    if not isinstance(angles, list):
        return {}
    for item in angles:
        if isinstance(item, dict) and selected_id and item.get("id") == selected_id:
            return item
    for item in angles:
        if isinstance(item, dict) and selected_family and item.get("angle_family") == selected_family:
            return item
    return {}


def _pick_multiplier_angle(angle_multiplier: dict[str, Any], family: str | None) -> dict[str, Any]:
    angles = angle_multiplier.get("angles") if isinstance(angle_multiplier, dict) else []
    if not isinstance(angles, list) or not angles:
        return {}
    if family:
        for item in angles:
            if isinstance(item, dict) and item.get("angle_family") == family:
                return item
    first = angles[0]
    return first if isinstance(first, dict) else {}


def _angle_diversity_contract(
    *,
    set_id: str,
    family: Any,
    hook: Any,
    visual_direction: Any,
) -> str:
    family_text = str(family or "distinct").strip()
    hook_text = _limit_text(hook, 140)
    visual_text = _limit_text(visual_direction, 180)
    return (
        f"{set_id} must test a materially different {family_text} angle, not just a new crop of the same static ad. "
        f"Hook intent: {hook_text}. Visual direction: {visual_text}. "
        "Keep product fidelity locked, but vary buyer motivation, composition, camera distance, and proof focus from the other static assets."
    )


def _static_creative_director_audit(
    *,
    static_image_ads: list[dict[str, Any]],
    carousel_ad: dict[str, Any],
    category: str,
) -> dict[str, Any]:
    assets = []
    for item in static_image_ads:
        assets.append(_static_director_asset(item))
    for card in carousel_ad.get("cards") or []:
        merged = {
            **card,
            "creative_id": f"{carousel_ad.get('set_id') or 'C5'}_card_{card.get('card_number')}",
            "set_id": carousel_ad.get("set_id"),
            "creative_type": "Carousel card",
            "angle": carousel_ad.get("angle"),
            "funnel_stage": carousel_ad.get("funnel_stage"),
            "aspect_ratio": carousel_ad.get("aspect_ratio"),
        }
        assets.append(_static_director_asset(merged))
    diversity_dimensions = ["environment", "composition", "funnel_role", "camera_distance", "human_context"]
    dimension_scores = {
        key: _dimension_diversity_score([asset.get(key) for asset in assets])
        for key in diversity_dimensions
    }
    dimension_average = round(sum(dimension_scores.values()) / max(1, len(dimension_scores)))
    asset_average = round(
        sum(int(asset.get("visual_diversity_score") or 0) for asset in assets)
        / max(1, len(assets))
    )
    average_score = round((dimension_average + asset_average) / 2)
    return {
        "version": "static_creative_director_v3",
        "status": "ready",
        "category": category,
        "policy": "Ecommerce static v2: product-first hero, real-use context, proof detail, objection check, anti-hype check, and buying-guide carousel; no duplicate padding, product fidelity and realism remain locked.",
        "max_static_images_policy": "cap_only_no_padding",
        "duplicate_policy": "skip duplicate prompts instead of replacing them with similar filler images",
        "category_rules": _static_category_rules(category),
        "asset_count": len(assets),
        "visual_diversity_score": average_score,
        "dimension_diversity_score": dimension_average,
        "asset_brief_strength_score": asset_average,
        "dimension_scores": dimension_scores,
        "assets": assets,
    }


def _static_director_asset(item: dict[str, Any]) -> dict[str, Any]:
    prompt = " ".join(str(item.get(key) or "") for key in ["layout", "visual_prompt", "concept"]).lower()
    return {
        "creative_id": item.get("creative_id"),
        "set_id": item.get("set_id"),
        "creative_type": item.get("creative_type"),
        "angle": item.get("angle"),
        "funnel_role": item.get("funnel_stage") or item.get("role"),
        "environment": _detect_static_environment(prompt),
        "composition": _detect_static_composition(prompt),
        "camera_distance": _detect_camera_distance(prompt),
        "human_context": _detect_human_context(prompt),
        "overlay_text": item.get("overlay_text"),
        "why_this_exists": item.get("why_this_angle") or item.get("purpose"),
        "visual_diversity_score": _static_director_asset_score(prompt),
    }


def _detect_static_environment(prompt: str) -> str:
    markers = [
        ("entryway", ["entryway", "threshold", "hallway"]),
        ("office_or_commute", ["office", "commute", "lift lobby", "travel card", "notebook", "laptop"]),
        ("cafe_or_street", ["cafe", "street", "pavement", "outdoor doorway", "street-facing"]),
        ("car_transition", ["car seat", "car console", "parked-car-seat"]),
        ("mirror_or_wardrobe", ["mirror", "wardrobe"]),
        ("outdoor_threshold", ["outdoor", "pavement", "courtyard", "doorway"]),
        ("macro_neutral", ["macro", "close-up", "detail fills", "neutral clean background"]),
        ("desk_or_counter", ["desk", "counter", "kitchen table", "shelf"]),
    ]
    for label, needles in markers:
        if any(needle in prompt for needle in needles):
            return label
    return "category_context"


def _detect_static_composition(prompt: str) -> str:
    if "macro" in prompt or "fills at least 70" in prompt:
        return "macro_detail"
    if "lower-body" in prompt or "on feet" in prompt:
        return "worn_lower_body"
    if "shoulder" in prompt or "held in hand" in prompt or "carried" in prompt:
        return "carried_or_held"
    if "hero" in prompt or "center crop" in prompt:
        return "product_hero"
    return "lifestyle_context"


def _detect_camera_distance(prompt: str) -> str:
    if "macro" in prompt or "extreme close-up" in prompt:
        return "macro"
    if "low 45-degree" in prompt:
        return "low_close"
    if "eye-level" in prompt:
        return "medium_eye_level"
    if "full lower-body" in prompt:
        return "full_lower_body"
    return "medium_context"


def _detect_human_context(prompt: str) -> str:
    if "adult person" in prompt and ("wearing" in prompt or "worn" in prompt):
        return "adult_wearing_product"
    if "adult person" in prompt and ("carried" in prompt or "holding" in prompt or "held" in prompt):
        return "adult_holding_or_carrying"
    if "adult hand" in prompt:
        return "adult_hand_scale"
    if "face cropped" in prompt or "face out of frame" in prompt:
        return "cropped_adult_context"
    return "minimal_human_context"


def _dimension_diversity_score(values: list[Any]) -> int:
    cleaned = [str(value or "").strip().lower() for value in values if str(value or "").strip()]
    if not cleaned:
        return 0
    unique_count = len(set(cleaned))
    return max(0, min(100, round(100 * unique_count / max(1, len(cleaned)))))


def _static_director_asset_score(prompt: str) -> int:
    markers = [
        "adult person",
        "face cropped",
        "held",
        "carried",
        "wearing",
        "macro",
        "entryway",
        "office",
        "outfit",
        "distinct",
        "scale",
        "no table",
        "no platform ui",
    ]
    return max(0, min(100, 45 + 5 * sum(1 for marker in markers if marker in prompt)))


def _static_category_rules(category: str) -> list[str]:
    normalized = str(category or "").strip().lower()
    if normalized == "handbag":
        return [
            "show the bag carried, on shoulder, in hand, or against an adult outfit/body context",
            "preserve realistic bag size relative to torso, hand, shoulder, and outfit",
            "do not morph tote/shoulder/clutch/crossbody bag type across assets",
            "avoid making every static image an apartment/home interior; rotate at least one office, commute, cafe, street doorway, or travel-adjacent context when appropriate",
        ]
    if normalized == "shoes":
        return [
            "show shoes worn on feet or in real movement/context, not primarily on a table",
            "preserve exact upper, sole, toe shape, side profile, and closure",
            "avoid medical, orthopaedic, pain-relief, or comfort-guarantee claims",
            "avoid making every static image an apartment/home interior; use pavement, outdoor doorway, office lift lobby, or street-threshold context for at least one use-context asset",
        ]
    if normalized == "apparel":
        return [
            "show apparel worn on an adult person with natural outfit context",
            "preserve cut, drape, seam placement, visible material finish from reference, pattern, and colour",
            "avoid body transformation, slimming, sizing guarantee, and fit-result claims",
            "avoid making every static image an apartment/home interior; use cafe entrance, quiet street, office lift lobby, outdoor doorway, or commute context for at least one use-context asset",
        ]
    return [
        "use adult human context whenever physically plausible",
        "vary environment, camera distance, and composition across C2/C3/C4/C5; do not default every asset to home or apartment interiors",
        "preserve product shape, colour, proportions, visible markings, and scale",
    ]


def _append_once(value: Any, addition: str) -> str:
    text = str(value or "").strip()
    if not addition or addition in text:
        return text
    return f"{text}, {addition}" if text else addition


def refresh_copy_validation(ad_set: dict[str, Any]) -> dict[str, Any]:
    """Recompute copy validation after optional prompt-model creative refinement."""
    refreshed = dict(ad_set)
    refreshed["copy_validation"] = _copy_validation(refreshed)
    return refreshed


def _platform_copy_specs(platform: str) -> dict[str, Any]:
    if platform == "google_ads":
        return {
            "platform": "google_ads",
            "responsive_search_ads": {
                "headline_char_limit": 30,
                "headline_quantity": "3 minimum, 15 maximum",
                "description_char_limit": 90,
                "description_quantity": "2 minimum, 4 maximum",
                "display_path_char_limit": 15,
            },
            "performance_max": {
                "headline_char_limit": 30,
                "long_headline_char_limit": 90,
                "description_char_limit": 90,
                "business_name_char_limit": 25,
            },
        }
    if platform == "meta":
        return {
            "platform": "meta",
            "single_image_video_carousel": {
                "primary_text_visible_chars": 125,
                "primary_text_max_chars": 2200,
                "headline_recommended_chars": 40,
                "description_recommended_chars": 30,
            },
        }
    return {
        "platform": platform,
        "paid_social": {
            "primary_text_visible_chars": 125,
            "headline_recommended_chars": 40,
            "description_recommended_chars": 30,
        },
    }


def _creative_plan() -> list[dict[str, Any]]:
    return [
        {
            "set_id": "C1",
            "creative_type": "UGC video",
            "angle": "UGC",
            "aspect_ratio": "9:16",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 55,
            "generation_target": "Seedance video",
            "notes": "Primary creator-led ad set.",
        },
        {
            "set_id": "C2",
            "creative_type": "Static product hero",
            "angle": "PRODUCT_HERO",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 10,
            "generation_target": "Static image",
            "notes": "Product-first thumb-stopping hero image with clear scale, shape, and scroll-safe overlay.",
        },
        {
            "set_id": "C3",
            "creative_type": "Static use context",
            "angle": "USE_CONTEXT",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 10,
            "generation_target": "Static image",
            "notes": "Real-use context image showing how the product fits into a believable everyday moment.",
        },
        {
            "set_id": "C4",
            "creative_type": "Static proof detail",
            "angle": "DETAIL_PROOF",
            "aspect_ratio": "1:1",
            "funnel_stage": "Retargeting",
            "budget_share_percent": 10,
            "generation_target": "Static image",
            "notes": "Close-up proof image for visible material, construction, texture, fit, or scale cues.",
        },
        {
            "set_id": "C5",
            "creative_type": "Carousel buying guide",
            "angle": "BUYING_GUIDE",
            "aspect_ratio": "1:1",
            "funnel_stage": "MOFU",
            "budget_share_percent": 15,
            "generation_target": "Carousel cards",
            "notes": "Five-card buyer guide: hero, key cue, use context, proof detail, final consideration.",
        },
        {
            "set_id": "C6",
            "creative_type": "Static objection check",
            "angle": "PAIN_POINT",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 7,
            "generation_target": "Static image",
            "notes": "Problem-aware static image that shows the buyer doubt or decision friction without inventing claims.",
        },
        {
            "set_id": "C7",
            "creative_type": "Static anti-hype check",
            "angle": "CONTRARIAN_CHECK",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 8,
            "generation_target": "Static image",
            "notes": "Low-polish anti-ad frame that makes the product feel inspected, not glamorized.",
        },
    ]


def _creative_angles(
    language: str,
    product_name: str,
    first_benefit: str,
    category: str,
    emotional_angle: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    emotional = emotional_angle or {}
    emotional_entry = {
        "angle": str(emotional.get("primary_angle") or "curiosity"),
        "motivation": str(emotional.get("driver") or "selected emotional driver for this product and audience"),
        "hook": str(emotional.get("hook_bias") or first_benefit),
        "variation_rule": "Use as internal creative direction only; keep customer-facing copy claim-safe and product-specific.",
    }
    if _is_czech(language):
        return [emotional_entry] + [
            {
                "angle": "curiosity",
                "motivation": "user wants to inspect the product before deciding",
                "hook": f"Co je u {product_name} videt teprve zblizka?",
                "variation_rule": "Test question, direct statement, and short command versions.",
            },
            {
                "angle": "pain_point",
                "motivation": "user does not trust polished product photos",
                "hook": "Vetsinou vybiras podle jedne fotky a pak chybi detail",
                "variation_rule": "Lead with uncertainty, then resolve with product detail.",
            },
            {
                "angle": "contrarian",
                "motivation": "user rejects hype-heavy ads",
                "hook": "Hype nech stranou. Nejdriv detail.",
                "variation_rule": "Keep copy blunt and low-polish without unsupported claims.",
            },
            {
                "angle": "feature_detail",
                "motivation": "user wants a concrete visible attribute",
                "hook": first_benefit,
                "variation_rule": "Use only visible or user-supplied details.",
            },
            {
                "angle": "identity",
                "motivation": "user sees themselves as a careful buyer",
                "hook": f"Pro lidi, co si {category} chteji rozmyslet",
                "variation_rule": "Frame as careful selection, not superiority or status.",
            },
            {
                "angle": "demonstration",
                "motivation": "user wants to see the product without ad polish",
                "hook": f"{product_name} bez filtru - jak vypada doopravdy",
                "variation_rule": "Use product-led visuals and avoid performance claims.",
            },
            {
                "angle": "comparison",
                "motivation": "user compares options and needs one extra detail",
                "hook": f"Misto dalsi {category} reklamy, jen detail navic",
                "variation_rule": "Compare viewing context only, not competitor quality or outcomes.",
            },
        ]
    if _is_german(language):
        category_label = localize_category(category, language)
        return [emotional_entry] + [
            {
                "angle": "curiosity",
                "motivation": "user wants to inspect the product before deciding",
                "hook": f"Was sieht man bei {product_name} erst aus der Naehe?",
                "variation_rule": "Test question, direct statement, and short command versions.",
            },
            {
                "angle": "pain_point",
                "motivation": "user does not trust polished product photos",
                "hook": "Ein Produktfoto aus der Ferne reicht oft nicht",
                "variation_rule": "Lead with uncertainty, then resolve with product detail.",
            },
            {
                "angle": "contrarian",
                "motivation": "user rejects hype-heavy ads",
                "hook": "Weniger Hype. Erst der Detailcheck.",
                "variation_rule": "Keep copy blunt and low-polish without unsupported claims.",
            },
            {
                "angle": "feature_detail",
                "motivation": "user wants a concrete visible attribute",
                "hook": first_benefit,
                "variation_rule": "Use only visible or user-supplied details.",
            },
            {
                "angle": "identity",
                "motivation": "user sees themselves as a careful buyer",
                "hook": f"Fuer Menschen, die {category_label} in Ruhe pruefen wollen",
                "variation_rule": "Frame as careful selection, not superiority or status.",
            },
            {
                "angle": "demonstration",
                "motivation": "user wants to see the product without ad polish",
                "hook": f"{product_name} ohne Filter - so wirkt es wirklich",
                "variation_rule": "Use product-led visuals and avoid performance claims.",
            },
            {
                "angle": "comparison",
                "motivation": "user compares options and needs one extra detail",
                "hook": f"Statt noch einer {category_label}-Anzeige: ein kurzer Detailblick",
                "variation_rule": "Compare viewing context only, not competitor quality or outcomes.",
            },
        ]
    return [emotional_entry] + [
        {
            "angle": "curiosity",
            "motivation": "user wants to inspect the product before deciding",
            "hook": f"What can you actually see up close on {product_name}?",
            "variation_rule": "Test question, direct statement, and short command versions.",
        },
        {
            "angle": "pain_point",
            "motivation": "user does not trust polished product photos",
            "hook": "A distant product photo is not enough",
            "variation_rule": "Lead with uncertainty, then resolve with product detail.",
        },
        {
            "angle": "contrarian",
            "motivation": "user rejects hype-heavy ads",
            "hook": "Skip the hype. Detail first.",
            "variation_rule": "Keep copy blunt and low-polish without unsupported claims.",
        },
        {
            "angle": "feature_detail",
            "motivation": "user wants a concrete visible attribute",
            "hook": first_benefit,
            "variation_rule": "Use only visible or user-supplied details.",
        },
        {
            "angle": "identity",
            "motivation": "user sees themselves as a careful buyer",
            "hook": f"For people who want to think about {category}, not impulse-buy it",
            "variation_rule": "Frame as careful selection, not superiority or status.",
        },
        {
            "angle": "demonstration",
            "motivation": "user wants to see the product without ad polish",
            "hook": f"{product_name} without filters - what it actually looks like",
            "variation_rule": "Use product-led visuals and avoid performance claims.",
        },
        {
            "angle": "comparison",
            "motivation": "user compares options and needs one extra detail",
            "hook": f"Instead of another {category} ad, a quick close-up",
            "variation_rule": "Compare viewing context only, not competitor quality or outcomes.",
        },
    ]


def _is_czech(language: str) -> bool:
    return _is_czech_language(language)


def _is_german(language: str) -> bool:
    return is_german(language)


def _emotional_directive(emotional_angle: dict[str, Any]) -> str:
    if not emotional_angle:
        return ""
    return (
        f"emotional angle {emotional_angle.get('primary_safe_label') or emotional_angle.get('primary_angle')}: "
        f"{emotional_angle.get('driver')}; {emotional_angle.get('hook_bias')}"
    )


def _category_image_directive(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
) -> str:
    category = str(product_analysis.get("likely_product_category") or "").strip().lower()
    overrides = settings.get("category_prompt_overrides") or {}
    override = " ".join(str(overrides.get(category) or "").split()).strip()
    if override:
        return override
    preset = prompt_defaults.CATEGORY_PROMPT_PRESETS.get(category) or {}
    return " ".join(str(preset.get("image_directive") or "").split()).strip()


def _static_visual_classifier_directive(product_analysis: dict[str, Any]) -> str:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return ""
    detected = str(visual.get("detected_object") or "").strip()
    subcategory = str(visual.get("subcategory") or "").strip()
    template = str(visual.get("recommended_template_id") or "").strip()
    category_confidence = visual.get("category_confidence")
    parts = [
        "Visual classifier static directive: use image understanding for static creative shot choice and QA only, not as a customer-facing claim.",
    ]
    if detected or subcategory:
        confidence = f" confidence={category_confidence}" if category_confidence is not None else ""
        parts.append(f"Detected product appears to be {detected or subcategory}{confidence}.")
    if template:
        parts.append(f"Recommended static proof template: {_static_template_instruction(template)}")
    for label, key in [
        ("Scenario rules", "scenario_rules"),
        ("Required static shots", "shot_requirements"),
        ("Avoid in static generation", "avoid_in_generation"),
        ("Static QA expectations", "qa_expectations"),
    ]:
        values = [str(item).strip() for item in (visual.get(key) or [])[:4] if str(item).strip()]
        if values:
            parts.append(f"{label}: {'; '.join(values)}.")
    return " ".join(parts)[:1400]


def _static_template_instruction(template: str) -> str:
    if template == "apparel_try_on_full_body":
        return (
            "show the garment worn by an adult person, include full-body or near-full-body outfit proof before detail crops, "
            "avoid flat lays and isolated fabric-only shots"
        )
    if template == "worn_footwear_check":
        return (
            "show footwear worn on adult feet with side profile, sole edge, upper texture, toe shape, and real floor/outfit scale; "
            "avoid tabletop flat lays"
        )
    if template == "carry_capacity_check":
        return (
            "show the bag carried on shoulder or in hand with adult body scale, handle/strap/opening/detail proof, "
            "and capacity cues only when verified"
        )
    if template == "product_unboxing":
        return "show packaging/unboxing only when packaging is visible or verified, then a realistic held product proof shot"
    if template == "creator_connected_lifestyle":
        return "show the product held, worn, carried, or used by an adult person in a simple real context"
    if template == "app_promo":
        return "show a real phone/app screen only when a screen reference is supplied; otherwise use creator-with-phone context, no fake UI"
    return template.replace("_", " ")


def _objective_for_platform(platform: str) -> str:
    if platform == "google_ads":
        return "Complete Google Ads creative set around the UGC video concept for YouTube, Display, and Performance Max asset testing."
    if platform == "meta":
        return "Complete Meta Ads creative set around the UGC video concept."
    return "Complete paid social creative set around the UGC video concept."


def _cta_link_policy(platform: str) -> str:
    if platform == "google_ads":
        return "No URL, button label, or click instruction is written into creative copy; configure final URL and CTA controls inside Google Ads."
    if platform == "meta":
        return "No URL, button label, or click instruction is written into creative copy; configure destination link and CTA controls inside Meta Ads Manager."
    return "No URL, button label, or click instruction is written into creative copy; configure destination URL and CTA controls inside the selected ad platform."


def _destination_url_note(platform: str) -> str:
    if platform == "google_ads":
        return "Do not include destination URLs, button labels, or click/tap instructions in creative copy; Google Ads adds final URL and CTA controls through campaign or asset setup."
    if platform == "meta":
        return "Do not include destination URLs, button labels, or click/tap instructions in creative copy; Meta adds links and CTA controls through ad setup."
    return "Do not include destination URLs, button labels, or click/tap instructions in creative copy; the selected ad platform adds them during campaign setup."


def _hook_bank(language: str, product_name: str, first_benefit: str, category: str) -> list[dict[str, str]]:
    if _is_czech(language):
        return [
            {"pattern": "calling_out", "hook": f"Pokud zvazujes {category}, podivej se nejdriv na tohle."},
            {"pattern": "contrarian_claim", "hook": "Nekupuj podle jedne fotky z dalky. Mrkni na realny detail."},
            {"pattern": "visual_shock", "hook": "Zoom na detail, ktery bys pri rychlem scrollu preskocila."},
            {"pattern": "before_after", "hook": "Pred vyberem vs. po kontrole detailu."},
            {"pattern": "question", "hook": f"Vis, co u {product_name} zkontrolovat jako prvni?"},
            {"pattern": "number", "hook": f"3 veci na {product_name}, ktere se vyplati overit pred rozhodnutim."},
            {"pattern": "pov", "hook": f"POV: poprve vidis {product_name} zblizka bez filtru."},
            {"pattern": "feature_detail", "hook": f"{first_benefit} - tohle je videt teprve zblizka."},
            {"pattern": "skipped_detail", "hook": f"Tohle je {category} detail, ktery vetsina reklam preskoci."},
            {"pattern": "comparison", "hook": f"Misto dalsi {category} reklamy, kratky detail navic."},
        ]
    if _is_german(language):
        category_label = localize_category(category, language)
        return [
            {"pattern": "calling_out", "hook": f"Wenn du {category_label} vergleichst, fang mit diesem Detail an."},
            {"pattern": "contrarian_claim", "hook": "Nicht nach einem Foto aus der Ferne entscheiden. Erst die Details pruefen."},
            {"pattern": "visual_shock", "hook": "Zoom auf das Detail, das man beim Scrollen uebersieht."},
            {"pattern": "before_after", "hook": "Vor dem Kauf vs. nach dem Detailcheck."},
            {"pattern": "question", "hook": f"Was sollte man bei {product_name} zuerst pruefen?"},
            {"pattern": "number", "hook": f"3 Dinge an {product_name}, die man vorher pruefen sollte."},
            {"pattern": "pov", "hook": f"POV: du siehst {product_name} endlich aus der Naehe."},
            {"pattern": "feature_detail", "hook": f"{first_benefit} - das sieht man erst aus der Naehe."},
            {"pattern": "skipped_detail", "hook": f"Das {category_label}-Detail, das viele Anzeigen auslassen."},
            {"pattern": "comparison", "hook": f"Statt noch einer {category_label}-Anzeige: ein kurzer Detailblick."},
        ]
    return [
        {"pattern": "calling_out", "hook": f"If you are comparing {category}, start with this detail."},
        {"pattern": "contrarian_claim", "hook": "Do not buy from a distant photo. Check the real details first."},
        {"pattern": "visual_shock", "hook": "Zoom in on the detail most people miss while scrolling."},
        {"pattern": "before_after", "hook": "Before choosing vs. after checking the details."},
        {"pattern": "question", "hook": f"What should you check first on {product_name}?"},
        {"pattern": "number", "hook": f"3 things on {product_name} worth checking before deciding."},
        {"pattern": "pov", "hook": f"POV: you finally see {product_name} up close without the hype."},
        {"pattern": "feature_detail", "hook": f"{first_benefit} - this is only visible when you look closer."},
        {"pattern": "skipped_detail", "hook": f"The {category} detail most ads skip over."},
        {"pattern": "comparison", "hook": f"Instead of another {category} ad, a quick close-up."},
    ]


def _static_image_ads(
    language: str,
    product_name: str,
    product_url: str,
    first_benefit: str,
    benefits: list[str],
    category: str,
    category_image_directive: str = "",
    emotional_directive: str = "",
) -> list[dict[str, Any]]:
    second_benefit = benefits[1] if len(benefits) > 1 else first_benefit
    third_benefit = benefits[2] if len(benefits) > 2 else first_benefit
    category_suffix = (
        f", category-specific direction: {category_image_directive}"
        if category_image_directive
        else ""
    )
    if emotional_directive:
        category_suffix = f"{category_suffix}, emotional direction: {emotional_directive}"
    contexts = _static_category_contexts(
        category=category,
        product_url=product_url,
        first_benefit=first_benefit,
        second_benefit=second_benefit,
        third_benefit=third_benefit,
        category_suffix=category_suffix,
    )
    if _is_czech(language):
        return [
            {
                "creative_id": "C2_static_product_hero",
                "set_id": "C2",
                "creative_type": "Static product hero",
                "angle": "PRODUCT_HERO",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 10,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c2_layout"],
                "concept": "product-first hero: fast product recognition with scale and one clear visual reason",
                "why_this_angle": "PRODUCT_HERO should stop the scroll with immediate product clarity, strong composition, and a concrete visible cue without inventing claims.",
                "visual_prompt": contexts["c2_visual"],
                "overlay_text": contexts["c2_overlay_cs"],
                "primary_text": contexts["c2_primary_cs"],
                "headline": contexts["c2_headline_cs"],
                "cta": "",
            },
            {
                "creative_id": "C3_static_use_context",
                "set_id": "C3",
                "creative_type": "Static use context",
                "angle": "USE_CONTEXT",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 10,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c3_layout"],
                "concept": "real-use context: the product belongs in a believable daily moment",
                "why_this_angle": "USE_CONTEXT should make scale, styling, and use feel real while staying visually distinct from the product hero.",
                "visual_prompt": contexts["c3_visual"],
                "overlay_text": contexts["c3_overlay_cs"],
                "primary_text": contexts["c3_primary_cs"],
                "headline": contexts["c3_headline_cs"],
                "cta": "",
            },
            {
                "creative_id": "C4_static_detail_proof",
                "set_id": "C4",
                "creative_type": "Static proof detail",
                "angle": "DETAIL_PROOF",
                "aspect_ratio": "1:1",
                "funnel_stage": "Retargeting",
                "budget_share_percent": 10,
                "format": "Static image",
                "role": "Retargeting",
                "layout": contexts["c4_layout"],
                "concept": "detail proof: turn one visible product detail into a retargeting reason",
                "why_this_angle": "DETAIL_PROOF should give product-aware users a close visual reason to keep considering the product, using only what is visible.",
                "visual_prompt": contexts["c4_visual"],
                "overlay_text": contexts["c4_overlay_cs"],
                "primary_text": contexts["c4_primary_cs"],
                "headline": contexts["c4_headline_cs"],
                "cta": "",
            },
            {
                "creative_id": "C6_static_objection_check",
                "set_id": "C6",
                "creative_type": "Static objection check",
                "angle": "PAIN_POINT",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 7,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c6_layout"],
                "concept": "objection check: make one buyer doubt visible and answer it through product scale or context",
                "why_this_angle": "PAIN_POINT should feel different from the hero by showing the practical hesitation a buyer has before deciding, using only visible proof.",
                "visual_prompt": contexts["c6_visual"],
                "overlay_text": contexts["c6_overlay_cs"],
                "primary_text": contexts["c6_primary_cs"],
                "headline": contexts["c6_headline_cs"],
                "cta": "",
            },
            {
                "creative_id": "C7_static_contrarian_check",
                "set_id": "C7",
                "creative_type": "Static anti-hype check",
                "angle": "CONTRARIAN_CHECK",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 8,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c7_layout"],
                "concept": "anti-hype check: intentionally low-polish product inspection instead of a glossy ad",
                "why_this_angle": "CONTRARIAN_CHECK should stop buyers who distrust polished ads by showing a grounded product check in a distinct scene.",
                "visual_prompt": contexts["c7_visual"],
                "overlay_text": contexts["c7_overlay_cs"],
                "primary_text": contexts["c7_primary_cs"],
                "headline": contexts["c7_headline_cs"],
                "cta": "",
            },
        ]
    if _is_german(language):
        return [
            {
                "creative_id": "C2_static_product_hero",
                "set_id": "C2",
                "creative_type": "Static product hero",
                "angle": "PRODUCT_HERO",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 10,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c2_layout"],
                "concept": "product-first hero: fast product recognition with scale and one clear visual reason",
                "why_this_angle": "PRODUCT_HERO should stop the scroll with immediate product clarity, strong composition, and a concrete visible cue without inventing claims.",
                "visual_prompt": contexts["c2_visual"],
                "overlay_text": contexts["c2_overlay_de"],
                "primary_text": contexts["c2_primary_de"],
                "headline": contexts["c2_headline_de"],
                "cta": "",
            },
            {
                "creative_id": "C3_static_use_context",
                "set_id": "C3",
                "creative_type": "Static use context",
                "angle": "USE_CONTEXT",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 10,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c3_layout"],
                "concept": "real-use context: the product belongs in a believable daily moment",
                "why_this_angle": "USE_CONTEXT should make scale, styling, and use feel real while staying visually distinct from the product hero.",
                "visual_prompt": contexts["c3_visual"],
                "overlay_text": contexts["c3_overlay_de"],
                "primary_text": contexts["c3_primary_de"],
                "headline": contexts["c3_headline_de"],
                "cta": "",
            },
            {
                "creative_id": "C4_static_detail_proof",
                "set_id": "C4",
                "creative_type": "Static proof detail",
                "angle": "DETAIL_PROOF",
                "aspect_ratio": "1:1",
                "funnel_stage": "Retargeting",
                "budget_share_percent": 10,
                "format": "Static image",
                "role": "Retargeting",
                "layout": contexts["c4_layout"],
                "concept": "detail proof: turn one visible product detail into a retargeting reason",
                "why_this_angle": "DETAIL_PROOF should give product-aware users a close visual reason to keep considering the product, using only what is visible.",
                "visual_prompt": contexts["c4_visual"],
                "overlay_text": contexts["c4_overlay_de"],
                "primary_text": contexts["c4_primary_de"],
                "headline": contexts["c4_headline_de"],
                "cta": "",
            },
            {
                "creative_id": "C6_static_objection_check",
                "set_id": "C6",
                "creative_type": "Static objection check",
                "angle": "PAIN_POINT",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 7,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c6_layout"],
                "concept": "objection check: make one buyer doubt visible and answer it through product scale or context",
                "why_this_angle": "PAIN_POINT should feel different from the hero by showing the practical hesitation a buyer has before deciding, using only visible proof.",
                "visual_prompt": contexts["c6_visual"],
                "overlay_text": contexts["c6_overlay_de"],
                "primary_text": contexts["c6_primary_de"],
                "headline": contexts["c6_headline_de"],
                "cta": "",
            },
            {
                "creative_id": "C7_static_contrarian_check",
                "set_id": "C7",
                "creative_type": "Static anti-hype check",
                "angle": "CONTRARIAN_CHECK",
                "aspect_ratio": "1:1",
                "funnel_stage": "TOFU + retargeting",
                "budget_share_percent": 8,
                "format": "Static image",
                "role": "TOFU + retargeting",
                "layout": contexts["c7_layout"],
                "concept": "anti-hype check: intentionally low-polish product inspection instead of a glossy ad",
                "why_this_angle": "CONTRARIAN_CHECK should stop buyers who distrust polished ads by showing a grounded product check in a distinct scene.",
                "visual_prompt": contexts["c7_visual"],
                "overlay_text": contexts["c7_overlay_de"],
                "primary_text": contexts["c7_primary_de"],
                "headline": contexts["c7_headline_de"],
                "cta": "",
            },
        ]
    if _is_german(language):
        return [
            {
                "creative_id": "meme_dm",
                "format": "Meme-style static",
                "layout": "low-fi DM screenshot",
                "visual_prompt": "Generic direct-message screenshot style, neutral grey and blue chat bubbles, no recognizable platform branding, product thumbnail as an attached image inside the conversation, mobile aspect framing, low-fi authentic feel",
                "copy": f"ich: nur kurz den detailcheck\n\nauch ich: okay, {product_name} macht Sinn",
                "cta_line": "",
                "fatigue_note": "Rotate quickly; meme-style creatives wear out faster.",
            },
            {
                "creative_id": "meme_tweet",
                "format": "Meme-style static",
                "layout": "social post screenshot style, no platform branding",
                "visual_prompt": "Generic plain-text social post screenshot style with neutral typography, no recognizable platform logos or UI, product image embedded below the text block, low-fi authentic crop, slightly desaturated to feel like a real screenshot",
                "copy": f"ich brauche keinen Hype, ich will {first_benefit} sehen",
                "cta_line": "",
                "fatigue_note": "Use as CTR tester, refresh copy often.",
            },
        ]
    if _is_german(language):
        category_label = localize_category(category, language)
        return [
            {
                "framework": "PAS",
                "primary_text": f"Unsicher, was du bei {category_label} zuerst pruefen sollst?\n\nProblem: Produktfotos zeigen oft zu wenig.\n\nAgitation: Dann fehlt genau das Detail, das bei der Entscheidung hilft.\n\nLoesung:\n- {first_benefit}\n- Produkt aus der Naehe\n- kein Hype",
            },
            {
                "framework": "AIDA",
                "primary_text": f"{product_name}, ohne unnoetigen Hype.\n\nAttention: kurzer Produktdetail-Check.\n\nInterest:\n- {first_benefit}\n- klarer Blick auf Form und Verarbeitung\n\nAction: Ruhig nach sichtbaren Details einschaetzen.",
            },
        ]
    return [
        {
            "creative_id": "C2_static_product_hero",
            "set_id": "C2",
            "creative_type": "Static product hero",
            "angle": "PRODUCT_HERO",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 10,
            "format": "Static image",
            "role": "TOFU + retargeting",
            "layout": contexts["c2_layout"],
            "concept": "product-first hero: fast product recognition with scale and one clear visual reason",
            "why_this_angle": "PRODUCT_HERO should stop the scroll with immediate product clarity, strong composition, and a concrete visible cue without inventing claims.",
            "visual_prompt": contexts["c2_visual"],
            "overlay_text": contexts["c2_overlay_en"],
            "primary_text": contexts["c2_primary_en"],
            "headline": contexts["c2_headline_en"],
            "cta": "",
        },
        {
            "creative_id": "C3_static_use_context",
            "set_id": "C3",
            "creative_type": "Static use context",
            "angle": "USE_CONTEXT",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 10,
            "format": "Static image",
            "role": "TOFU + retargeting",
            "layout": contexts["c3_layout"],
            "concept": "real-use context: the product belongs in a believable daily moment",
            "why_this_angle": "USE_CONTEXT should make scale, styling, and use feel real while staying visually distinct from the product hero.",
            "visual_prompt": contexts["c3_visual"],
            "overlay_text": contexts["c3_overlay_en"],
            "primary_text": contexts["c3_primary_en"],
            "headline": contexts["c3_headline_en"],
            "cta": "",
        },
        {
            "creative_id": "C4_static_detail_proof",
            "set_id": "C4",
            "creative_type": "Static proof detail",
            "angle": "DETAIL_PROOF",
            "aspect_ratio": "1:1",
            "funnel_stage": "Retargeting",
            "budget_share_percent": 10,
            "format": "Static image",
            "role": "Retargeting",
            "layout": contexts["c4_layout"],
            "concept": "detail proof: turn one visible product detail into a retargeting reason",
            "why_this_angle": "DETAIL_PROOF should give product-aware users a close visual reason to keep considering the product, using only what is visible.",
            "visual_prompt": contexts["c4_visual"],
            "overlay_text": contexts["c4_overlay_en"],
            "primary_text": contexts["c4_primary_en"],
            "headline": contexts["c4_headline_en"],
            "cta": "",
        },
        {
            "creative_id": "C6_static_objection_check",
            "set_id": "C6",
            "creative_type": "Static objection check",
            "angle": "PAIN_POINT",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 7,
            "format": "Static image",
            "role": "TOFU + retargeting",
            "layout": contexts["c6_layout"],
            "concept": "objection check: make one buyer doubt visible and answer it through product scale or context",
            "why_this_angle": "PAIN_POINT should feel different from the hero by showing the practical hesitation a buyer has before deciding, using only visible proof.",
            "visual_prompt": contexts["c6_visual"],
            "overlay_text": contexts["c6_overlay_en"],
            "primary_text": contexts["c6_primary_en"],
            "headline": contexts["c6_headline_en"],
            "cta": "",
        },
        {
            "creative_id": "C7_static_contrarian_check",
            "set_id": "C7",
            "creative_type": "Static anti-hype check",
            "angle": "CONTRARIAN_CHECK",
            "aspect_ratio": "1:1",
            "funnel_stage": "TOFU + retargeting",
            "budget_share_percent": 8,
            "format": "Static image",
            "role": "TOFU + retargeting",
            "layout": contexts["c7_layout"],
            "concept": "anti-hype check: intentionally low-polish product inspection instead of a glossy ad",
            "why_this_angle": "CONTRARIAN_CHECK should stop buyers who distrust polished ads by showing a grounded product check in a distinct scene.",
            "visual_prompt": contexts["c7_visual"],
            "overlay_text": contexts["c7_overlay_en"],
            "primary_text": contexts["c7_primary_en"],
            "headline": contexts["c7_headline_en"],
            "cta": "",
        },
    ]


def _static_category_contexts(
    category: str,
    product_url: str,
    first_benefit: str,
    second_benefit: str,
    third_benefit: str,
    category_suffix: str,
) -> dict[str, str]:
    normalized = str(category or "").lower()
    if normalized == "shoes":
        return {
            "c2_layout": "square product-first worn shoe hero, adult person wearing product, clean floor, outdoor doorway, or entryway crop, bold negative space, no tabletop styling",
            "c2_visual": f"Use product reference {product_url}, C2 PRODUCT_HERO creative, commerce-grade product-first static for shoes, realistic adult person wearing the shoes on a clean floor, outdoor doorway threshold, or simple pavement edge, low 45-degree camera angle near floor, one foot slightly forward to show side profile, toe shape, and silhouette, product occupies the central hero area with clear negative space for a 3-5 word overlay, casual outfit hem visible for scale, no table, no desk, no product flat lay, focus cue on {first_benefit}, crisp natural daylight, real floor or pavement texture, rule of thirds, face out of frame, no children, no platform UI, realistic photography with real shadows and exact shoe shape preserved, must look visually different from C3 use-context scene and C4 detail proof{category_suffix}",
            "c3_layout": "square everyday outfit use-context scene, adult person wearing shoes, full lower-body scale, outdoor or commute-adjacent location distinct from hero",
            "c3_visual": f"Use product reference {product_url}, C3 USE_CONTEXT creative, realistic adult person wearing the shoes as part of an everyday outfit near a quiet street crossing, office lift lobby, cafe entrance, or outdoor pavement edge, lower-body crop only, shoes clearly visible on feet, outfit hem and ground provide scale, focus cue on {second_benefit}, no table, no desk, no isolated product still life, softer late-afternoon natural light, no children, no platform UI, no crowded public scene, realistic photography with believable depth and shadows, different crop, light, and location from C2{category_suffix}",
            "c4_layout": "square worn macro shoe proof, product fills most of frame, sole or upper detail while on foot or held in adult hand",
            "c4_visual": f"Use product reference {product_url}, C4 DETAIL_PROOF creative, realistic close-up macro crop of the shoes while worn on an adult foot or held in an adult hand, show one or two visible details such as upper texture, stitching, closure, side profile, sole edge, or toe shape, product detail fills at least 70 percent of the square frame, no room scene, no table, no desk, use crop/focus or subtle non-text pointer marks only to emphasize visible details, focus cue on {third_benefit}, natural side light, very sharp focus, real lens depth of field, no medical or comfort claim labels, no children, distinct from C2 and C3{category_suffix}",
            **_static_extra_angle_contexts("shoes", product_url, first_benefit, second_benefit, third_benefit, category_suffix),
            **_static_text_pack("shoes", first_benefit, second_benefit, third_benefit),
        }
    if normalized == "apparel":
        return {
            "c2_layout": "square product-first worn apparel hero, adult person wearing garment, clean mirror, neutral wall, or outdoor doorway crop, bold negative space",
            "c2_visual": f"Use product reference {product_url}, C2 PRODUCT_HERO creative, commerce-grade product-first apparel static, realistic adult person wearing the garment in a clean mirror, neutral wall, or outdoor doorway crop, garment visible on body with natural drape, cut, color, and silhouette preserved, one hand adjusting sleeve, hem, or collar only if relevant, product occupies the central hero area with clear negative space for a 3-5 word overlay, no table, no desk, no product flat lay, focus cue on {first_benefit}, clean daylight, rule of thirds, face cropped or turned away, no children, no platform UI, realistic photography with exact garment shape and color preserved, must look visually different from C3 use-context scene and C4 detail proof{category_suffix}",
            "c3_layout": "square everyday outfit use-context scene, adult person wearing garment in outdoor, cafe, office, or commute-adjacent context",
            "c3_visual": f"Use product reference {product_url}, C3 USE_CONTEXT creative, realistic adult person wearing the apparel as part of an everyday outfit near a cafe entrance, office lift lobby, quiet street doorway, or outdoor pavement edge, garment remains the hero with restrained styling context, focus cue on {second_benefit}, no table, no flat lay, warm natural light, face cropped or turned away, no children, no crowded public scene, no platform UI, no sizing or body outcome claims, believable depth and shadows, different crop, light, and location from C2{category_suffix}",
            "c4_layout": "square worn macro apparel proof, adult hand or body context visible, seam/closure/visible finish fills most of frame",
            "c4_visual": f"Use product reference {product_url}, C4 DETAIL_PROOF creative, realistic close-up macro crop of the apparel while worn or held by an adult person, show one or two visible details such as exact visible finish from reference, seam, closure, neckline, sleeve, hem, or pattern, product detail fills at least 70 percent of the square frame, no room scene, no table, no desk, use crop/focus or subtle non-text pointer marks only to emphasize visible details, focus cue on {third_benefit}, natural side light, sharp focus, real lens depth of field, no sizing or body transformation claim labels, no children, distinct from C2 and C3{category_suffix}",
            **_static_extra_angle_contexts("apparel", product_url, first_benefit, second_benefit, third_benefit, category_suffix),
            **_static_text_pack("apparel", first_benefit, second_benefit, third_benefit),
        }
    if normalized == "handbag":
        scale_lock = _handbag_scale_lock()
        return {
            "c2_layout": "square product-first handbag hero, adult carrying or holding bag, neutral wall, street-facing doorway, or office lift crop, strong silhouette and scale",
            "c2_visual": f"Use product reference {product_url}, C2 PRODUCT_HERO creative, commerce-grade product-first handbag static, bag carried on shoulder or held in hand by an adult person near a neutral wall, street-facing doorway, office lift lobby, or clean cafe entrance, full silhouette, handles, strap drop, and width/height/depth visible, product occupies the central hero area with clear negative space for a 3-5 word overlay, keys, notebook, or coat edge may appear only as secondary scale cues, focus cue on {first_benefit}, crisp directional daylight, rule of thirds, face cropped or turned away, no children, no platform UI, no fake brand badges, realistic photography with exact bag silhouette, handles, and scale preserved, {scale_lock}, must look visually different from C3 use-context scene and C4 detail proof{category_suffix}",
            "c3_layout": "square handbag use-context scene, bag carried by adult person in commute, outfit, or daily routine moment",
            "c3_visual": f"Use product reference {product_url}, C3 USE_CONTEXT creative, realistic calm commute, cafe entrance, office doorway, street-crossing pause, or parked-car-seat transition for handbag, bag carried on shoulder or held naturally by an adult person with simple outfit context, one coat sleeve, notebook edge, phone, keys, or travel card allowed for scale, focus cue on {second_benefit}, eye-level composition, warmer natural light, single overlay headline inside safe area, face cropped or turned away, no children, no stock-photo glamour pose, no platform UI, no crowded public scene, realistic photography with believable depth and shadows, {scale_lock}, different crop, light, and location from C2{category_suffix}",
            "c4_layout": "square macro handbag proof, adult hand holding or carrying bag, product fills most of frame, no in-image text labels",
            "c4_visual": f"Use product reference {product_url}, C4 DETAIL_PROOF creative, realistic extreme close-up macro crop of one or two visible handbag details from the reference while the bag is being held or carried by an adult person, adult hand/forearm or outfit edge visible for scale, product detail fills at least 70 percent of the square frame, no full room scene, use crop/focus or subtle non-text pointer marks only to emphasize visible details, focus cue on {third_benefit}, soft directional light, very sharp focus, exact visible material finish from the reference, real lens depth of field, no invented details, no claim labels, no children, {scale_lock}, distinct from C2 and C3{category_suffix}",
            **_static_extra_angle_contexts("handbag", product_url, first_benefit, second_benefit, third_benefit, category_suffix),
            **_static_text_pack("handbag", first_benefit, second_benefit, third_benefit),
        }
    return {
        "c2_layout": "square product-first commerce hero, adult holding or using product near category-relevant surface or real-world threshold, clear negative space",
        "c2_visual": f"Use product reference {product_url}, C2 PRODUCT_HERO creative, commerce-grade product-first static for {category}, product held, used, or positioned naturally by an adult person in the most plausible context such as a desk, kitchen table, shelf, counter, bathroom counter, cafe table, car console, gym bench, or category-relevant outdoor threshold, product occupies the central hero area with clear negative space for a 3-5 word overlay, relevant everyday prop nearby but secondary, phone or laptop edge visible but no readable UI, focus cue on {first_benefit}, crisp directional daylight, rule of thirds, face cropped or turned away, no children, no platform UI, no fake brand badges, realistic photography with real shadows and product scale, must look visually different from C3 use-context scene and C4 detail proof{category_suffix}",
        "c3_layout": "square distinct everyday use-context scene, adult person using or holding product in a real routine",
        "c3_visual": f"Use product reference {product_url}, C3 USE_CONTEXT creative, realistic everyday use-context scene for {category}, product used or held naturally by an adult person in a different plausible context than C2 such as workspace, cafe table, outdoor threshold, commute moment, bathroom counter, kitchen, gym bag area, or car seat depending on category, focus cue on {second_benefit}, eye-level composition, warmer natural light, single overlay headline inside safe area, face cropped or turned away, no children, no stock-photo glamour pose, no crowded public scene, no platform UI, realistic photography with believable depth and shadows, different crop, light, and location from C2{category_suffix}",
        "c4_layout": "square macro product proof, adult hand or usage context visible, product fills most of frame, no in-image text labels",
        "c4_visual": f"Use product reference {product_url}, C4 DETAIL_PROOF creative, realistic extreme close-up macro crop of one or two visible product details from the reference while the product is held or used by an adult person when plausible, adult hand or context edge visible for scale, product detail fills at least 70 percent of the square frame, no full room scene, use crop/focus or subtle non-text pointer marks only to emphasize visible details, focus cue on {third_benefit}, neutral clean background, soft directional light, very sharp focus, exact visible material finish from the reference, real lens depth of field, no invented details, no claim labels, no children, distinct from C2 and C3{category_suffix}",
        **_static_extra_angle_contexts(category, product_url, first_benefit, second_benefit, third_benefit, category_suffix),
        **_static_text_pack(category, first_benefit, second_benefit, third_benefit),
    }


def _static_extra_angle_contexts(
    category: str,
    product_url: str,
    first_benefit: str,
    second_benefit: str,
    third_benefit: str,
    category_suffix: str,
) -> dict[str, str]:
    normalized = str(category or "").lower()
    if normalized == "handbag":
        scale_lock = _handbag_scale_lock()
        return {
            "c6_layout": "square handbag objection-check scene, buyer decision friction made visible with scale props and adult carry context",
            "c6_visual": f"Use product reference {product_url}, C6 PAIN_POINT creative, realistic buyer-objection static for handbag, show an adult person checking the bag before leaving home, at a cafe table edge, office doorway, or parked-car-seat transition, bag clearly carried or held with one or two everyday objects nearby for scale such as phone, keys, travel card, notebook, or wipes only if relevant, composition should answer the doubt 'will this actually work in my day?' through visible scale and access cues, focus cue on {first_benefit}, natural handheld-feeling photo, slightly imperfect crop, face cropped or turned away, no children, no fake capacity claim unless visibly demonstrated, no platform UI, {scale_lock}, must look visually different from C2/C3/C4{category_suffix}",
            "c7_layout": "square anti-hype handbag check, low-polish handheld product inspection in a real doorway or mirror moment",
            "c7_visual": f"Use product reference {product_url}, C7 CONTRARIAN_CHECK creative, anti-gloss low-polish handbag static, adult person doing a quick honest product check in a hallway mirror, outdoor doorway, cafe entrance, or lift lobby, bag held close enough to inspect but still readable as a full product, one visible skipped-ad detail such as opening, strap, zipper, handle, silhouette, or pattern gets attention, focus cue on {second_benefit}, real phone-camera perspective, ordinary natural light, not a catalogue pose, not luxury styling, no fake review or claim labels, no children, {scale_lock}, clearly different setting and camera distance from C2/C3/C4/C6{category_suffix}",
        }
    if normalized == "shoes":
        return {
            "c6_layout": "square shoe objection-check scene, adult lower-body context at threshold with practical decision cue",
            "c6_visual": f"Use product reference {product_url}, C6 PAIN_POINT creative, realistic buyer-objection static for shoes, adult person pauses at an outdoor doorway, office lift lobby, pavement edge, or entryway as if checking the pair before heading out, shoes worn on feet and clearly visible, ground texture and outfit hem show scale, composition answers the doubt 'do these look right in a real day?' through side profile, toe shape, sole edge, or closure, focus cue on {first_benefit}, natural handheld-feeling photo, no table, no desk, no medical or comfort labels, no children, no platform UI, must look visually different from C2/C3/C4{category_suffix}",
            "c7_layout": "square anti-hype shoe check, low-polish floor-level inspection instead of studio product styling",
            "c7_visual": f"Use product reference {product_url}, C7 CONTRARIAN_CHECK creative, anti-gloss shoe static, adult person wearing the shoes in a quick honest floor-level check near a doorway, pavement edge, or simple hallway, one visible skipped-ad detail such as toe shape, side profile, closure, upper texture, or sole edge gets attention, focus cue on {second_benefit}, real phone-camera perspective, ordinary daylight, imperfect crop, not a catalogue pose, no fake review or claim labels, no children, clearly different setting and camera distance from C2/C3/C4/C6{category_suffix}",
        }
    if normalized == "apparel":
        return {
            "c6_layout": "square apparel objection-check scene, adult mirror or doorway try-on context with practical decision cue",
            "c6_visual": f"Use product reference {product_url}, C6 PAIN_POINT creative, realistic buyer-objection static for apparel, adult person wearing the garment in a mirror, quiet street doorway, cafe entrance, or office lift lobby as if checking it before leaving, garment visible enough to judge silhouette, drape, hem, sleeve, neckline, or closure, composition answers the doubt 'will this work in a real outfit?' through worn scale and styling context, focus cue on {first_benefit}, natural handheld-feeling photo, face cropped or turned away, no body transformation, sizing, or comfort labels, no children, no platform UI, must look visually different from C2/C3/C4{category_suffix}",
            "c7_layout": "square anti-hype apparel check, low-polish mirror or doorway inspection instead of fashion shoot",
            "c7_visual": f"Use product reference {product_url}, C7 CONTRARIAN_CHECK creative, anti-gloss apparel static, adult person doing a quick honest outfit check in a hallway mirror, outdoor doorway, or simple neutral wall, one visible skipped-ad detail such as silhouette, seam, closure, hem, neckline, sleeve, pattern, or visible surface finish gets attention, focus cue on {second_benefit}, real phone-camera perspective, ordinary daylight, imperfect crop, not a catalogue pose, no fake review or claim labels, no children, clearly different setting and camera distance from C2/C3/C4/C6{category_suffix}",
        }
    return {
        "c6_layout": "square objection-check scene, adult real-use context showing a buyer doubt through scale, handling, or setup",
        "c6_visual": f"Use product reference {product_url}, C6 PAIN_POINT creative, realistic buyer-objection static for {category}, adult person holding, using, or checking the product in a practical real-world moment such as workspace, counter, doorway, commute, car seat, gym bag area, bathroom counter, kitchen, shelf, or cafe table depending on category, composition answers one practical doubt through scale, handling, placement, or visible setup, focus cue on {first_benefit}, natural handheld-feeling photo, slightly imperfect crop, face cropped or turned away, no children, no fake performance claim, no platform UI, must look visually different from C2/C3/C4{category_suffix}",
        "c7_layout": "square anti-hype product check, low-polish handheld inspection instead of glossy ad styling",
        "c7_visual": f"Use product reference {product_url}, C7 CONTRARIAN_CHECK creative, anti-gloss static for {category}, adult person doing a quick honest product check in a simple everyday place, product held or used close enough to inspect while remaining readable as the same product, one visible skipped-ad detail gets attention, focus cue on {second_benefit or third_benefit}, real phone-camera perspective, ordinary daylight, imperfect crop, not a catalogue pose, no fake review or claim labels, no children, clearly different setting and camera distance from C2/C3/C4/C6{category_suffix}",
    }


def _static_text_pack(
    category: str,
    first_benefit: str,
    second_benefit: str,
    third_benefit: str,
) -> dict[str, str]:
    noun = _category_noun(category)
    noun_cs = _category_noun_cs(category)
    noun_de = localize_category(category, "de")
    c2_en = _short_hook(first_benefit, _fallback_overlay(category, "c2", "en"))
    c3_en = _short_hook(second_benefit, _fallback_overlay(category, "c3", "en"))
    c4_en = _short_hook(third_benefit, _fallback_overlay(category, "c4", "en"))
    c6_en = _fallback_overlay(category, "c6", "en")
    c7_en = _fallback_overlay(category, "c7", "en")
    c2_cs = _short_hook(first_benefit, _fallback_overlay(category, "c2", "cs"))
    c3_cs = _short_hook(second_benefit, _fallback_overlay(category, "c3", "cs"))
    c4_cs = _short_hook(third_benefit, _fallback_overlay(category, "c4", "cs"))
    c6_cs = _fallback_overlay(category, "c6", "cs")
    c7_cs = _fallback_overlay(category, "c7", "cs")
    c2_de = _short_hook(first_benefit, _fallback_overlay(category, "c2", "de"))
    c3_de = _short_hook(second_benefit, _fallback_overlay(category, "c3", "de"))
    c4_de = _short_hook(third_benefit, _fallback_overlay(category, "c4", "de"))
    c6_de = _fallback_overlay(category, "c6", "de")
    c7_de = _fallback_overlay(category, "c7", "de")
    return {
        "c2_overlay_en": c2_en,
        "c2_primary_en": (
            f"Product-first view for a fast scroll read.\n\n"
            f"Look for:\n- {first_benefit}\n- shape and scale\n- the main visual cue"
        ),
        "c2_headline_en": c2_en,
        "c3_overlay_en": c3_en,
        "c3_primary_en": (
            f"A real-use frame for judging the {noun} in context.\n\n"
            f"Look at:\n- {second_benefit}\n- how it sits in a believable moment\n- the overall shape"
        ),
        "c3_headline_en": c3_en,
        "c4_overlay_en": c4_en,
        "c4_primary_en": (
            f"Retargeting proof: zoom in on the visible cue.\n\n"
            f"- {third_benefit}\n- visible construction\n- exact product shape"
        ),
        "c4_headline_en": c4_en,
        "c6_overlay_en": c6_en,
        "c6_primary_en": (
            f"One practical doubt, shown visually.\n\n"
            f"Check:\n- {first_benefit}\n- real scale\n- how the {noun} fits the moment"
        ),
        "c6_headline_en": c6_en,
        "c7_overlay_en": c7_en,
        "c7_primary_en": (
            f"Less polish, more product check.\n\n"
            f"Look for:\n- {second_benefit}\n- one skipped detail\n- the same exact {noun}"
        ),
        "c7_headline_en": c7_en,
        "c2_overlay_cs": c2_cs,
        "c2_primary_cs": (
            f"Produktovy pohled pro rychle zastaveni ve feedu.\n\n"
            f"Vsimni si:\n- {first_benefit}\n- tvaru a meritka\n- hlavniho vizualniho detailu"
        ),
        "c2_headline_cs": c2_cs,
        "c3_overlay_cs": c3_cs,
        "c3_primary_cs": (
            f"Realny kontext, ve kterem jde {noun_cs} posoudit prakticky.\n\n"
            f"Vsimni si:\n- {second_benefit}\n- jak pusobi v beznem momentu\n- celkoveho tvaru"
        ),
        "c3_headline_cs": c3_cs,
        "c4_overlay_cs": c4_cs,
        "c4_primary_cs": (
            f"Retargeting proof: priblizeni na viditelny detail.\n\n"
            f"- {third_benefit}\n- viditelne provedeni\n- presny tvar produktu"
        ),
        "c4_headline_cs": c4_cs,
        "c6_overlay_cs": c6_cs,
        "c6_primary_cs": (
            f"Jedna prakticka pochybnost ukazana obrazem.\n\n"
            f"Zkontroluj:\n- {first_benefit}\n- realne meritko\n- jak {noun_cs} sedi v momentu"
        ),
        "c6_headline_cs": c6_cs,
        "c7_overlay_cs": c7_cs,
        "c7_primary_cs": (
            f"Min lesku, vic kontroly produktu.\n\n"
            f"Vsimni si:\n- {second_benefit}\n- detailu, ktery reklamy preskakuji\n- stejneho produktu"
        ),
        "c7_headline_cs": c7_cs,
        "c2_overlay_de": c2_de,
        "c2_primary_de": (
            f"Produktansicht fuer den schnellen Feed-Check.\n\n"
            f"Achte auf:\n- {first_benefit}\n- Form und Groesse\n- den wichtigsten sichtbaren Hinweis"
        ),
        "c2_headline_de": c2_de,
        "c3_overlay_de": c3_de,
        "c3_primary_de": (
            f"Ein echter Kontext, um {noun_de} besser einzuschaetzen.\n\n"
            f"Achte auf:\n- {second_benefit}\n- wie es im Alltag wirkt\n- die Gesamtform"
        ),
        "c3_headline_de": c3_de,
        "c4_overlay_de": c4_de,
        "c4_primary_de": (
            f"Retargeting proof: Nahaufnahme eines sichtbaren Details.\n\n"
            f"- {third_benefit}\n- sichtbare Verarbeitung\n- exakte Produktform"
        ),
        "c4_headline_de": c4_de,
        "c6_overlay_de": c6_de,
        "c6_primary_de": (
            f"Ein praktischer Zweifel, visuell gezeigt.\n\n"
            f"Pruefen:\n- {first_benefit}\n- reale Groesse\n- wie {noun_de} in den Moment passt"
        ),
        "c6_headline_de": c6_de,
        "c7_overlay_de": c7_de,
        "c7_primary_de": (
            f"Weniger Glanz, mehr Produktcheck.\n\n"
            f"Achte auf:\n- {second_benefit}\n- ein oft uebersehenes Detail\n- dasselbe exakte Produkt"
        ),
        "c7_headline_de": c7_de,
    }


def _short_hook(value: Any, fallback: str) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = " ".join(text.split())
    text = text.strip(" -.,;:")
    if not text:
        return fallback
    text = text.split(" - ", 1)[0].split(":", 1)[0].strip(" -.,;:")
    words = text.split()
    if 2 <= len(words) <= 5 and len(text) <= 32 and not _looks_like_internal_overlay(text):
        return text[:1].upper() + text[1:]
    return fallback


def _fallback_overlay(category: str, slot: str, language: str) -> str:
    category = str(category or "").lower()
    by_language = {
        "cs": {
            "c2": {"handbag": "Na kazdy den", "shoes": "Na kazdy den", "apparel": "Na kazdy den", "default": "Vidis hlavni detail"},
            "c3": {"handbag": "Sedne k outfitu", "shoes": "Do bezneho dne", "apparel": "Sedne k outfitu", "default": "V beznem pouziti"},
            "c4": {"default": "Mrkni na detail"},
            "c6": {"handbag": "Vejde se do dne", "shoes": "Pred odchodem", "apparel": "Pred odchodem", "default": "Prakticka kontrola"},
            "c7": {"handbag": "Bez reklamniho lesku", "shoes": "Bez studioveho lesku", "apparel": "Bez fashion pozy", "default": "Bez reklamniho lesku"},
        },
        "de": {
            "c2": {"handbag": "Fuer jeden Tag", "shoes": "Fuer jeden Tag", "apparel": "Fuer jeden Tag", "default": "Das Detail sehen"},
            "c3": {"handbag": "Passt zum Outfit", "shoes": "Im Alltag leicht", "apparel": "Passt zum Outfit", "default": "Im Alltag"},
            "c4": {"default": "Details kurz checken"},
            "c6": {"handbag": "Passt in den Tag", "shoes": "Vor dem Losgehen", "apparel": "Vor dem Losgehen", "default": "Praktisch geprueft"},
            "c7": {"handbag": "Ohne Werbeglanz", "shoes": "Ohne Studioglanz", "apparel": "Ohne Fashion-Pose", "default": "Ohne Werbeglanz"},
        },
        "en": {
            "c2": {"handbag": "Your everyday bag", "shoes": "Your daily pair", "apparel": "Your everyday fit", "default": "See the key detail"},
            "c3": {"handbag": "Fits your outfit", "shoes": "Fits your routine", "apparel": "Fits your routine", "default": "Fits real life"},
            "c4": {"default": "Check the details"},
            "c6": {"handbag": "Fits your day", "shoes": "Before you leave", "apparel": "Before you leave", "default": "Practical check"},
            "c7": {"handbag": "Less ad polish", "shoes": "Less studio polish", "apparel": "No fashion pose", "default": "Less ad polish"},
        },
    }
    slot_map = by_language.get(language, by_language["en"]).get(slot, {})
    return slot_map.get(category) or slot_map.get("default") or "Check the details"


def _looks_like_internal_overlay(value: str) -> bool:
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
        "carousel",
    }
    return any(marker in normalized for marker in internal_markers) or normalized in {"c2", "c3", "c4", "c5"}


def _handbag_scale_lock() -> str:
    return (
        "handbag scale lock: same physical bag size relative to adult torso, hands, shoulder, and outfit in every asset; "
        "preserve width/height/depth ratio, handle length, strap drop, carry position, and shoulder-vs-hand scale; "
        "do not resize into mini bag, clutch, tote, crossbody, oversized shopper, or any other bag type"
    )


def _static_material_fidelity_lock(product_analysis: dict[str, Any]) -> str:
    facts = product_analysis.get("known_product_facts") or {}
    material = _known_fact_value(facts.get("material"))
    color = _known_fact_value(facts.get("color"))
    user_text = " ".join(str(item) for item in product_analysis.get("user_provided_facts") or [])
    detail_text = " ".join(str(item) for item in product_analysis.get("ad_safe_detail_phrases") or [])
    evidence_text = " ".join(part for part in [material, color, user_text, detail_text] if part).lower()
    opacity_clues = [
        term
        for term in [
            "transparent",
            "translucent",
            "clear",
            "see-through",
            "see through",
            "opaque",
            "matte",
            "glossy",
            "frosted",
        ]
        if term in evidence_text
    ]
    verified_parts = []
    if material:
        verified_parts.append(f"verified material={material}")
    if color:
        verified_parts.append(f"verified colour={color}")
    if opacity_clues:
        verified_parts.append("verified opacity/finish clue=" + ", ".join(opacity_clues[:4]))
    verified = "; ".join(verified_parts) if verified_parts else "material/opacity must be copied only from the product reference"
    return (
        f"Static product material/opacity lock: {verified}. "
        "The reference image controls the exact material family, surface texture, shine, thickness, edge behaviour, and transparency/opacity. "
        "Do not make an opaque product transparent, do not make a transparent product opaque, and do not turn the product into glass-like, plastic-looking, metallic, ceramic, leather, fabric, matte, or glossy material unless that exact property is verified by the product reference or user facts. "
        "For cups, glasses, bottles, jars, and packaging, keep the body opacity and rim/edge look exactly as shown; never invent clear walls, see-through liquid visibility, or premium glass clarity unless verified."
    )


def _static_subject_lock(
    settings: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    avatar: dict[str, Any] | None = None,
) -> str:
    scenario_lock = (
        content_prompt_package.get("user_scenario_lock")
        or ugc_strategy.get("user_scenario_lock")
        or {}
    )
    raw_parts = [
        settings.get("ugc_video_extra_prompt"),
        content_prompt_package.get("ugc_video_extra_prompt"),
        scenario_lock.get("raw_user_direction") if isinstance(scenario_lock, dict) else "",
        scenario_lock.get("summary") if isinstance(scenario_lock, dict) else "",
    ]
    text = " ".join(str(part or "") for part in raw_parts).lower()
    avatar_gender = _avatar_presenting_gender(avatar or {})
    if avatar_gender == "female":
        return (
            "Static human subject lock: show the same avatar gender as an adult woman/female-presenting creator. "
            "Do not generate a male-presenting model for these static assets."
        )
    if avatar_gender == "male":
        return (
            "Static human subject lock: show the same avatar gender as an adult man/male-presenting creator. "
            "Do not generate a female-presenting model for these static assets."
        )
    if not text.strip():
        return ""
    if any(term in text for term in ["mom", "mother", "mum", "mama"]):
        return (
            "Static human subject lock: show an adult woman/mom as the human context. "
            "Do not generate a male-presenting model for these static assets. "
            "Keep the scene aligned with the user-approved mom UGC scenario when human context is shown."
        )
    if any(term in text for term in ["woman", "female", "she ", " her ", "girlboss"]):
        return (
            "Static human subject lock: show an adult woman/female-presenting creator as the human context. "
            "Do not generate a male-presenting model for these static assets."
        )
    if any(term in text for term in ["man", "male", "father", "dad", "he ", " him "]):
        return (
            "Static human subject lock: show an adult man/male-presenting creator as the human context. "
            "Do not generate a female-presenting model for these static assets."
        )
    return ""


def _avatar_presenting_gender(avatar: dict[str, Any]) -> str:
    text = " ".join(
        str(avatar.get(key) or "")
        for key in [
            "gender",
            "presenting_gender",
            "style",
            "persona",
            "appearance",
            "voice",
            "identity_note",
            "name",
        ]
    ).lower()
    if not text.strip():
        return ""
    female_terms = [
        "female",
        "woman",
        "women",
        "female-presenting",
        "woman-presenting",
        "creatorin",
        "žena",
        "zena",
        "žensk",
        "zens",
    ]
    male_terms = [
        "male",
        "man",
        "men",
        "male-presenting",
        "man-presenting",
        "muž",
        "muz",
        "mužsk",
        "muzsk",
    ]
    if any(term in text for term in female_terms):
        return "female"
    if any(term in text for term in male_terms):
        return "male"
    return ""


def _apply_static_subject_lock_to_static_ads(
    ads: list[dict[str, Any]],
    subject_lock: str,
) -> list[dict[str, Any]]:
    return [_apply_static_subject_lock_to_creative(ad, subject_lock) for ad in ads]


def _apply_static_subject_lock_to_carousel(
    carousel: dict[str, Any],
    subject_lock: str,
) -> dict[str, Any]:
    updated = dict(carousel)
    updated["static_subject_lock"] = subject_lock
    cards = []
    for card in updated.get("cards") or []:
        cards.append(_apply_static_subject_lock_to_creative(card, subject_lock))
    updated["cards"] = cards
    return updated


def _apply_static_subject_lock_to_creative(
    creative: dict[str, Any],
    subject_lock: str,
) -> dict[str, Any]:
    updated = dict(creative)
    visual = str(updated.get("visual_prompt") or "")
    if not visual:
        return updated
    replacement = _subject_replacement(subject_lock)
    if replacement:
        visual = visual.replace("adult person", replacement)
        visual = visual.replace("adult body", f"{replacement} body")
        visual = visual.replace("adult hand", f"{replacement} hand")
        visual = visual.replace("adult hands", f"{replacement} hands")
    if subject_lock not in visual:
        visual = f"{subject_lock} {visual}"
    updated["visual_prompt"] = visual
    updated["static_subject_lock"] = subject_lock
    return updated


def _subject_replacement(subject_lock: str) -> str:
    lower = str(subject_lock or "").lower()
    if "woman/mom" in lower:
        return "adult woman/mom"
    if "woman/female" in lower or "female-presenting" in lower:
        return "adult woman/female-presenting creator"
    if "man/male" in lower or "male-presenting" in lower:
        return "adult man/male-presenting creator"
    return ""


def _known_fact_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"unknown", "none", "null", "n/a"}:
        return ""
    return " ".join(text.split())[:140]


def _category_noun(category: str) -> str:
    value = str(category or "product").lower()
    return {
        "handbag": "bag",
        "shoes": "shoes",
        "apparel": "garment",
    }.get(value, value or "product")


def _category_noun_cs(category: str) -> str:
    value = str(category or "produkt").lower()
    return {
        "handbag": "kabelky",
        "shoes": "bot",
        "apparel": "obleceni",
    }.get(value, value or "produktu")


def _carousel_ad(
    language: str,
    product_url: str,
    benefits: list[str],
    testimonial_source: str,
    category: str,
    category_image_directive: str = "",
) -> dict[str, Any]:
    has_social = bool(testimonial_source.strip())
    visuals = _carousel_category_visuals(category)
    if _is_czech(language):
        card_overlays = _carousel_overlays(benefits, category, "cs", has_social)
        cards = [
            _card(1, "hero_frame", product_url, card_overlays[0], visuals[0], category_image_directive),
            _card(2, "feature_proof", product_url, card_overlays[1], visuals[1], category_image_directive),
            _card(3, "use_context", product_url, card_overlays[2], visuals[2], category_image_directive),
            _card(4, "detail_proof", product_url, card_overlays[3], visuals[3], category_image_directive),
            _card(5, "buyer_wrap", product_url, card_overlays[4], visuals[4], category_image_directive),
        ]
        return {
            "set_id": "C5",
            "creative_type": "Carousel buying guide",
            "angle": "BUYING_GUIDE",
            "aspect_ratio": "1:1",
            "funnel_stage": "MOFU",
            "budget_share_percent": 15,
            "format": "Carousel",
            "card_count": 5,
            "cards": cards,
            "primary_text": "Projed si produkt pres kratke vizualni duvody.\n\n- Co je videt hned\n- Detail zblizka\n- Pouziti v realnem dni\n- Posledni check pred vyberem",
            "social_proof_policy": "Use testimonial_source only if supplied; otherwise keep card 5 as a final trust/detail card without button text.",
        }
    if _is_german(language):
        card_overlays = _carousel_overlays(benefits, category, "de", has_social)
        cards = [
            _card(1, "hero_frame", product_url, card_overlays[0], visuals[0], category_image_directive),
            _card(2, "feature_proof", product_url, card_overlays[1], visuals[1], category_image_directive),
            _card(3, "use_context", product_url, card_overlays[2], visuals[2], category_image_directive),
            _card(4, "detail_proof", product_url, card_overlays[3], visuals[3], category_image_directive),
            _card(5, "buyer_wrap", product_url, card_overlays[4], visuals[4], category_image_directive),
        ]
        return {
            "set_id": "C5",
            "creative_type": "Carousel buying guide",
            "angle": "BUYING_GUIDE",
            "aspect_ratio": "1:1",
            "funnel_stage": "MOFU",
            "budget_share_percent": 15,
            "format": "Carousel",
            "card_count": 5,
            "cards": cards,
            "primary_text": "Kurzer visueller Produktcheck.\n\n- Was sofort auffaellt\n- Detail aus der Naehe\n- Im Alltag gesehen\n- Letzter Check vor der Auswahl",
            "social_proof_policy": "Use testimonial_source only if supplied; otherwise keep card 5 as a final trust/detail card without button text.",
        }
    card_overlays = _carousel_overlays(benefits, category, "en", has_social)
    cards = [
        _card(1, "hero_frame", product_url, card_overlays[0], visuals[0], category_image_directive),
        _card(2, "feature_proof", product_url, card_overlays[1], visuals[1], category_image_directive),
        _card(3, "use_context", product_url, card_overlays[2], visuals[2], category_image_directive),
        _card(4, "detail_proof", product_url, card_overlays[3], visuals[3], category_image_directive),
        _card(5, "buyer_wrap", product_url, card_overlays[4], visuals[4], category_image_directive),
    ]
    return {
        "set_id": "C5",
        "creative_type": "Carousel buying guide",
        "angle": "BUYING_GUIDE",
        "aspect_ratio": "1:1",
        "funnel_stage": "MOFU",
        "budget_share_percent": 15,
        "format": "Carousel",
        "card_count": 5,
        "cards": cards,
        "primary_text": "Swipe through the product by visual reasons.\n\n- What stands out first\n- The close-up detail\n- How it fits real life\n- One last check before deciding",
        "social_proof_policy": "Use testimonial_source only if supplied; otherwise keep card 5 as a final trust/detail card without button text.",
    }


def _carousel_overlays(benefits: list[str], category: str, language: str, has_social: bool) -> list[str]:
    padded = (benefits + benefits[:1] + ["visible product details"])[:3]
    return [
        _short_hook(padded[0], _fallback_overlay(category, "c2", language)),
        _short_hook(padded[1], _feature_fallback(language)),
        _fallback_overlay(category, "c3", language),
        _short_hook(padded[2], _fallback_overlay(category, "c4", language)),
        _final_check_overlay(language, has_social),
    ]


def _feature_fallback(language: str) -> str:
    if language == "cs":
        return "Jeden viditelny duvod"
    if language == "de":
        return "Ein sichtbarer Grund"
    return "One visible reason"


def _final_check_overlay(language: str, has_social: bool) -> str:
    if language == "cs":
        return "Overeny detail" if has_social else "Vyber podle detailu"
    if language == "de":
        return "Geprueftes Detail" if has_social else "Nach Details waehlen"
    return "Verified detail" if has_social else "Decide by detail"


def _carousel_category_visuals(category: str) -> list[str]:
    normalized = str(category or "").lower()
    if normalized == "shoes":
        return [
            "product-first worn hero shot, adult person wearing the shoes on a clean floor, outdoor doorway, or simple pavement edge, low angle, no table, no flat lay",
            "worn feature proof on adult foot, side profile, upper texture, stitching, closure, or sole edge only, sharp focus",
            "adult lower-body everyday outfit scene with shoes on feet near cafe entrance, office lift lobby, or quiet pavement edge, natural light",
            "macro detail proof beside doorway, pavement, or neutral floor, no tabletop props, no comfort or medical claims",
            "final worn buying-guide card with adult person standing naturally near an outdoor threshold or commute context, shoes visible and accurate, no invented reviews, no buttons",
        ]
    if normalized == "apparel":
        return [
            "product-first worn hero shot, adult person wearing the garment in a clean mirror, neutral wall, or outdoor doorway scene, no flat lay",
            "worn feature proof with seam, closure, neckline, sleeve, hem, visible finish, or pattern detail, sharp focus",
            "adult everyday outfit scene with garment worn naturally near a cafe entrance, quiet street doorway, or office lift lobby, natural light",
            "macro detail proof showing silhouette, drape, or exact visible reference finish without body outcome claims, face cropped or turned away",
            "final worn buying-guide card with adult person in a simple commute or street-facing context, garment accurate, no invented reviews, no buttons",
        ]
    if normalized == "handbag":
        scale_lock = _handbag_scale_lock()
        return [
            f"product-first handbag hero shot, adult person carrying the bag on shoulder or in hand near a neutral wall, cafe entrance, or office lift lobby, full silhouette visible, {scale_lock}",
            f"feature proof close-up of handle, stitching, opening, texture, or hardware while adult hand holds the bag, {scale_lock}",
            f"adult outfit use-context scene with bag carried naturally in commute, cafe entrance, office doorway, street-crossing pause, or parked-car-seat transition, natural light, {scale_lock}",
            f"macro detail proof with bag on shoulder or in hand beside coat, notebook, phone, or keys as secondary props, {scale_lock}",
            f"final buying-guide card with adult person carrying the bag in a simple office, commute, or street-facing context, structure, finish, and handles visible, no invented reviews, no buttons, {scale_lock}",
        ]
    return [
        "product-first hero composition with adult person holding or using the product in its most plausible real-life context",
        "feature proof close-up of one visible detail while product is held or used when plausible, sharp focus",
        "everyday use-context placement with adult person interacting naturally with product, accurate reference fidelity",
        "macro detail proof with real human scale or use-context reference, neutral believable background",
        "final buying-guide card with product in realistic adult use context, no invented reviews, no buttons",
    ]


def _card(number: int, role: str, product_url: str, overlay: str, visual: str, category_image_directive: str = "") -> dict[str, Any]:
    category_suffix = (
        f", category-specific direction: {category_image_directive}"
        if category_image_directive
        else ""
    )
    return {
        "card_number": number,
        "role": role,
        "visual_prompt": (
            f"Use product reference {product_url}, C5 buying-guide carousel card {number}, role {role}, "
            f"visual focus must match overlay text '{_limit_text(overlay, 40)}', {visual}, "
            f"keep this card visually distinct from the other carousel cards{category_suffix}"
        ),
        "overlay_text": _limit_text(overlay, 40),
        "cta": None,
    }


def _meme_style_creatives(
    language: str,
    product_name: str,
    first_benefit: str,
) -> list[dict[str, Any]]:
    if _is_czech(language):
        return [
            {
                "creative_id": "meme_dm",
                "format": "Meme-style static",
                "layout": "low-fi DM screenshot",
                "visual_prompt": "Generic direct-message screenshot style, neutral grey and blue chat bubbles, no recognizable platform branding, product thumbnail as an attached image inside the conversation, mobile aspect framing, low-fi authentic feel",
                "copy": f"ja: jen rychle mrknu na detail\n\ntaky ja: ok, {product_name} dava smysl",
                "cta_line": "",
                "fatigue_note": "Rotate quickly; meme-style creatives wear out faster.",
            },
            {
                "creative_id": "meme_tweet",
                "format": "Meme-style static",
                "layout": "social post screenshot style, no platform branding",
                "visual_prompt": "Generic plain-text social post screenshot style with neutral typography, no recognizable platform logos or UI, product image embedded below the text block, low-fi authentic crop, slightly desaturated to feel like a real screenshot",
                "copy": f"nepotrebuju hype, staci mi videt {first_benefit}",
                "cta_line": "",
                "fatigue_note": "Use as CTR tester, refresh copy often.",
            },
        ]
    return [
        {
            "creative_id": "meme_dm",
            "format": "Meme-style static",
            "layout": "low-fi DM screenshot",
            "visual_prompt": "Generic direct-message screenshot style, neutral grey and blue chat bubbles, no recognizable platform branding, product thumbnail as an attached image inside the conversation, mobile aspect framing, low-fi authentic feel",
            "copy": f"me: just quickly checking the detail\n\nalso me: ok, {product_name} actually makes sense",
            "cta_line": "",
            "fatigue_note": "Rotate quickly; meme-style creatives wear out faster.",
        },
        {
            "creative_id": "meme_tweet",
            "format": "Meme-style static",
            "layout": "social post screenshot style, no platform branding",
            "visual_prompt": "Generic plain-text social post screenshot style with neutral typography, no recognizable platform logos or UI, product image embedded below the text block, low-fi authentic crop, slightly desaturated to feel like a real screenshot",
            "copy": f"I do not need hype, I just want to see {first_benefit}",
            "cta_line": "",
            "fatigue_note": "Use as CTR tester, refresh copy often.",
        },
    ]


def _ad_description_suggestions(
    language: str,
    platform: str,
    product_name: str,
    first_benefit: str,
    category: str,
) -> dict[str, Any]:
    if _is_czech(language):
        variants = _czech_ad_description_variants(product_name, first_benefit, category)
    elif _is_german(language):
        variants = _german_ad_description_variants(product_name, first_benefit, category)
    else:
        variants = _english_ad_description_variants(product_name, first_benefit, category)
    if platform == "google_ads":
        return {
            "platform": platform,
            "format": "Google Ads RSA / Performance Max descriptions",
            "usage_note": "Use these as Google description assets. Final URL stays in Google Ads setup, not in copy.",
            "variants": [
                _description_variant(
                    variant_id=item["variant_id"],
                    angle=item["angle"],
                    format_name="google_description",
                    primary_text=None,
                    headline=item["headline"],
                    description=_limit_text(item["description"], 90),
                    cta=item["cta"],
                    hypothesis=item["hypothesis"],
                    limits={
                        "headline": 30,
                        "description": 90,
                    },
                )
                for item in variants[:4]
            ],
        }
    return {
        "platform": platform,
        "format": "Paid social ad descriptions",
        "usage_note": "Use primary_text as the ad description/caption. Destination URL is configured inside the ad platform.",
        "variants": [
            _description_variant(
                variant_id=item["variant_id"],
                angle=item["angle"],
                format_name="social_primary_text",
                primary_text=item["primary_text"],
                headline=item["headline"],
                description=item["description"],
                cta=item["cta"],
                hypothesis=item["hypothesis"],
                limits={
                    "primary_text_visible": 125,
                    "primary_text_max": 2200,
                    "headline": 40,
                    "description": 30,
                },
            )
            for item in variants
        ],
    }


def _czech_ad_description_variants(
    product_name: str,
    first_benefit: str,
    category: str,
) -> list[dict[str, str]]:
    return [
        {
            "variant_id": "desc_curiosity",
            "angle": "curiosity",
            "primary_text": f"Co je u {product_name} videt zblizka?\n\n- {first_benefit}\n- realny detail produktu\n- bez vymyslenych slibu",
            "headline": "Podivej se zblizka",
            "description": "Detail bez hype",
            "cta": "",
            "hypothesis": "Question-led copy can lift attention from users who need one clear reason to inspect the product.",
        },
        {
            "variant_id": "desc_pain_point",
            "angle": "pain_point",
            "primary_text": f"Fotka z dalky casto nestaci.\n\nU {category} se vyplati zkontrolovat detail jeste pred rozhodnutim:\n- {first_benefit}\n- tvar a provedeni\n- jasny pohled bez hype",
            "headline": "Nejdriv detail",
            "description": "Jasny prehled",
            "cta": "",
            "hypothesis": "Pain-point framing speaks to careful buyers who do not trust generic product photos.",
        },
        {
            "variant_id": "desc_contrarian",
            "angle": "contrarian",
            "primary_text": f"Bez hype. Bez velkych slibu.\n\nJen rychly pohled na {product_name}, kde je hlavni {first_benefit}. Detail ma pomoct s klidnym posouzenim.",
            "headline": "Bez hype",
            "description": "Produkt zblizka",
            "cta": "",
            "hypothesis": "Low-polish direct copy can stand out against overproduced ads.",
        },
        {
            "variant_id": "desc_feature_detail",
            "angle": "feature_detail",
            "primary_text": f"Rychla kontrola produktu pred dalsim krokem.\n\nZamer se hlavne na:\n- {first_benefit}\n- viditelne provedeni\n- celkovy detail produktu",
            "headline": "Rychla kontrola",
            "description": "Viditelny detail",
            "cta": "",
            "hypothesis": "Feature-detail copy supports retargeting and product-aware users.",
        },
        {
            "variant_id": "desc_identity",
            "angle": "identity",
            "primary_text": f"Pro lidi, co si {category} radsi nejdriv zkontroluji.\n\n{product_name} ukazujeme jednoduse: detail, tvar, provedeni a zadne vymyslene sliby.",
            "headline": "Klidny vyber",
            "description": "Bez slibu navic",
            "cta": "",
            "hypothesis": "Identity framing can work for careful shoppers who want control before clicking.",
        },
    ]


def _english_ad_description_variants(
    product_name: str,
    first_benefit: str,
    category: str,
) -> list[dict[str, str]]:
    return [
        {
            "variant_id": "desc_curiosity",
            "angle": "curiosity",
            "primary_text": f"What can you actually see up close on {product_name}?\n\n- {first_benefit}\n- real product detail\n- no invented promises",
            "headline": "See it up close",
            "description": "No hype, just detail",
            "cta": "",
            "hypothesis": "Question-led copy can lift attention from users who need one clear reason to inspect the product.",
        },
        {
            "variant_id": "desc_pain_point",
            "angle": "pain_point",
            "primary_text": f"A distant product photo is not enough.\n\nBefore deciding on this {category}, check:\n- {first_benefit}\n- shape and finish\n- a clear no-hype product look",
            "headline": "Check detail first",
            "description": "Clear product look",
            "cta": "",
            "hypothesis": "Pain-point framing speaks to careful buyers who do not trust generic product photos.",
        },
        {
            "variant_id": "desc_contrarian",
            "angle": "contrarian",
            "primary_text": f"No hype. No big claims.\n\nJust a quick look at {product_name}, focused on {first_benefit}. Built for a calmer product check.",
            "headline": "No hype",
            "description": "Product up close",
            "cta": "",
            "hypothesis": "Low-polish direct copy can stand out against overproduced ads.",
        },
        {
            "variant_id": "desc_feature_detail",
            "angle": "feature_detail",
            "primary_text": f"A quick product check before the next step.\n\nFocus on:\n- {first_benefit}\n- visible finish\n- the overall product detail",
            "headline": "Quick detail check",
            "description": "Visible product detail",
            "cta": "",
            "hypothesis": "Feature-detail copy supports retargeting and product-aware users.",
        },
        {
            "variant_id": "desc_identity",
            "angle": "identity",
            "primary_text": f"For people who check the {category} carefully before deciding.\n\n{product_name} is shown simply: detail, shape, finish, and no invented promises.",
            "headline": "Careful buying check",
            "description": "No extra claims",
            "cta": "",
            "hypothesis": "Identity framing can work for careful shoppers who want control before clicking.",
        },
    ]


def _german_ad_description_variants(
    product_name: str,
    first_benefit: str,
    category: str,
) -> list[dict[str, str]]:
    category_label = localize_category(category, "de")
    return [
        {
            "variant_id": "desc_curiosity",
            "angle": "curiosity",
            "primary_text": f"Was sieht man bei {product_name} aus der Naehe?\n\n- {first_benefit}\n- echte Produktdetails\n- keine erfundenen Versprechen",
            "headline": "Nah ansehen",
            "description": "Detail ohne Hype",
            "cta": "",
            "hypothesis": "Question-led copy can lift attention from users who need one clear reason to inspect the product.",
        },
        {
            "variant_id": "desc_pain_point",
            "angle": "pain_point",
            "primary_text": f"Ein Foto aus der Ferne reicht oft nicht.\n\nBei {category_label} lohnt sich ein kurzer Check:\n- {first_benefit}\n- Form und Verarbeitung\n- ein klarer Blick ohne Hype",
            "headline": "Erst Details pruefen",
            "description": "Klarer Produktblick",
            "cta": "",
            "hypothesis": "Pain-point framing speaks to careful buyers who do not trust generic product photos.",
        },
        {
            "variant_id": "desc_contrarian",
            "angle": "contrarian",
            "primary_text": f"Kein Hype. Keine grossen Versprechen.\n\nNur ein kurzer Blick auf {product_name}, mit Fokus auf {first_benefit}.",
            "headline": "Kein Hype",
            "description": "Produkt nah",
            "cta": "",
            "hypothesis": "Low-polish direct copy can stand out against overproduced ads.",
        },
        {
            "variant_id": "desc_feature_detail",
            "angle": "feature_detail",
            "primary_text": f"Kurzer Produktcheck vor dem naechsten Schritt.\n\nFokus auf:\n- {first_benefit}\n- sichtbare Verarbeitung\n- den Gesamteindruck",
            "headline": "Kurzer Check",
            "description": "Sichtbares Detail",
            "cta": "",
            "hypothesis": "Feature-detail copy supports retargeting and product-aware users.",
        },
        {
            "variant_id": "desc_identity",
            "angle": "identity",
            "primary_text": f"Fuer Menschen, die {category_label} vor der Entscheidung genau pruefen.\n\n{product_name} wird schlicht gezeigt: Detail, Form, Verarbeitung und keine erfundenen Versprechen.",
            "headline": "Ruhiger Check",
            "description": "Ohne Zusatzclaims",
            "cta": "",
            "hypothesis": "Identity framing can work for careful shoppers who want control before clicking.",
        },
    ]


def _description_variant(
    variant_id: str,
    angle: str,
    format_name: str,
    primary_text: str | None,
    headline: str,
    description: str,
    cta: str,
    hypothesis: str,
    limits: dict[str, int],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "variant_id": variant_id,
        "angle": angle,
        "format": format_name,
        "headline": _limit_text(headline, limits.get("headline", 40)),
        "description": _limit_text(description, limits.get("description", 90)),
        "cta": cta,
        "hypothesis": hypothesis,
        "validation": [],
    }
    if primary_text is not None:
        payload["primary_text"] = primary_text
        payload["first_125_chars"] = primary_text[:125]
        payload["validation"].append(_check_copy("primary_text_visible", _first_line(primary_text), limits.get("primary_text_visible", 125)))
        payload["validation"].append(_check_copy("primary_text_max", primary_text, limits.get("primary_text_max", 2200)))
    payload["validation"].append(_check_copy("headline", payload["headline"], limits.get("headline", 40)))
    payload["validation"].append(_check_copy("description", payload["description"], limits.get("description", 90)))
    payload["validation_status"] = (
        "ok"
        if all(item["status"] == "ok" for item in payload["validation"])
        else "needs_trim"
    )
    return payload


def _copy_pack(
    language: str,
    product_name: str,
    first_benefit: str,
    category: str,
) -> list[dict[str, str]]:
    if _is_czech(language):
        return [
            {
                "framework": "PAS",
                "primary_text": f"Nevis, co si u {category} zkontrolovat jako prvni?\n\nProblem: fotky casto ukazou malo.\n\nAgitace: pak chybi detail, ktery pomaha pri rozhodovani.\n\nReseni:\n- {first_benefit}\n- produkt zblizka\n- bez hype",
            },
            {
                "framework": "AIDA",
                "primary_text": f"{product_name} bez zbytecneho hype.\n\nPozornost: rychly detail produktu.\n\nZajem:\n- {first_benefit}\n- jasny pohled na tvar a provedeni\n\nAkce: Klidne posouzeni podle viditelnych detailu.",
            },
        ]
    return [
        {
            "framework": "PAS",
            "primary_text": f"Not sure what to check first in this {category}?\n\nProblem: product photos can hide the details.\n\nAgitate: then you decide without the things that matter.\n\nSolution:\n- {first_benefit}\n- close product look\n- no hype",
        },
        {
            "framework": "AIDA",
            "primary_text": f"{product_name}, without the unnecessary hype.\n\nAttention: a quick product detail check.\n\nInterest:\n- {first_benefit}\n- clear look at shape and finish\n\nAction: Calmly judge the visible details.",
        },
    ]


def _google_ads_assets(
    language: str,
    product_name: str,
    first_benefit: str,
    category: str,
) -> dict[str, Any]:
    if _is_czech(language):
        headlines = [
            ("Detail pred rozhodnutim", "benefit"),
            (f"{product_name} zblizka", "product"),
            ("Realny pohled, ne stock", "differentiator"),
            (f"Co u {category} videt", "curiosity"),
            ("3 detaily k overeni", "number"),
            (first_benefit, "feature"),
            ("Bez hype, jen detail", "differentiator"),
            ("Zoom na produkt", "visual"),
            ("Detail v 5 sekundach", "benefit"),
            ("Co overit pred vyberem", "curiosity"),
            (f"Pohled na {product_name}", "product"),
            ("Klid na rozmyslenou", "identity"),
            ("Kratky produktovy nahled", "benefit"),
            ("Vidis to az zblizka", "curiosity"),
            (product_name, "product"),
        ]
        descriptions = [
            "Realny detail produktu pred rozhodnutim. Zadne vymyslene sliby, jen to, co je videt.",
            "Kratky produktovy nahled. Pomuze rozhodnout se v klidu bez tlaku z reklamy.",
            "Zkontroluj tvar, povrch a viditelne provedeni bez vymyslenych tvrzeni.",
            f"Realny pohled na {product_name} pred dalsim krokem v par vterinach.",
        ]
        long_headlines = [
            f"Podivej se na {product_name} zblizka bez zbytecneho hype",
            f"Rychly produktovy detail pro {category} v par vterinach",
            f"Co u {product_name} videt pred vyberem: {first_benefit}",
            "Realny pohled na produkt, ne stock fotka",
            "Kratke shrnuti detailu pred vyberem",
        ]
    elif _is_german(language):
        category_label = localize_category(category, language)
        headlines = [
            ("Detail Vor Entscheidung", "benefit"),
            (f"{product_name} Nah", "product"),
            ("Echter Blick, Kein Stock", "differentiator"),
            ("Was Zuerst Pruefen", "curiosity"),
            ("3 Details Zum Pruefen", "number"),
            (first_benefit, "feature"),
            ("Kein Hype, Nur Detail", "differentiator"),
            ("Zoom Auf Das Produkt", "visual"),
            ("Nahaufnahme In Sekunden", "benefit"),
            ("Vorher Details Pruefen", "curiosity"),
            (f"Blick Auf {product_name}", "product"),
            ("In Ruhe Einschaetzen", "identity"),
            ("Kurzer Produktcheck", "benefit"),
            ("Erst Nah Sichtbar", "curiosity"),
            (product_name, "product"),
        ]
        descriptions = [
            "Echtes Produktdetail vor der Entscheidung. Keine erfundenen Versprechen, nur Sichtbares.",
            "Kurzer Produktcheck. Hilft ruhig zu entscheiden, ohne Werbedruck.",
            "Form, Verarbeitung und sichtbare Details ohne erfundene Claims pruefen.",
            f"Ein echter Blick auf {product_name} vor dem naechsten Schritt.",
        ]
        long_headlines = [
            f"{product_name} aus der Naehe ansehen ohne unnoetigen Hype",
            f"Kurzer Produktdetail-Check fuer {category_label} in Sekunden",
            f"Was bei {product_name} zuerst auffaellt: {first_benefit}",
            "Ein echter Produktblick, kein Stockfoto",
            "Kurze Detailuebersicht vor der Auswahl",
        ]
    else:
        headlines = [
            ("Detail Before Deciding", "benefit"),
            (f"{product_name} Up Close", "product"),
            ("Real Look, Not A Stock", "differentiator"),
            ("What To Check First", "curiosity"),
            ("3 Details Worth Checking", "number"),
            (first_benefit, "feature"),
            ("No Hype, Just Detail", "differentiator"),
            ("Zoom On The Product", "visual"),
            ("A Close-Up In 5 Seconds", "benefit"),
            ("Check Before Deciding", "curiosity"),
            ("Up-Close Product View", "benefit"),
            ("Time To Think It Over", "identity"),
            ("Quick Product Preview", "benefit"),
            ("Only Visible Up Close", "curiosity"),
            (product_name, "product"),
        ]
        descriptions = [
            "A real product detail before deciding. No invented promises, only what is visible.",
            "A quick product preview. Helps you decide calmly, without ad pressure.",
            "Check shape, finish, and visible build without invented claims.",
            f"A real look at {product_name} before the next step, in just seconds.",
        ]
        long_headlines = [
            f"See {product_name} up close without unnecessary hype",
            f"A quick product detail for {category} in just seconds",
            f"What to check on {product_name} first: {first_benefit}",
            "A real product look, not a stock photo",
            "A short detail preview before deciding",
        ]

    rsa_headlines = [
        {"text": _limit_text(text, 30), "role": role, "char_count": len(_limit_text(text, 30))}
        for text, role in headlines
    ]
    rsa_descriptions = [
        {"text": _limit_text(text, 90), "char_count": len(_limit_text(text, 90))}
        for text in descriptions
    ]
    pmax_long_headlines = [
        {"text": _limit_text(text, 90), "char_count": len(_limit_text(text, 90))}
        for text in long_headlines
    ]
    return {
        "responsive_search_ad": {
            "headlines": rsa_headlines,
            "descriptions": rsa_descriptions,
            "display_paths": [
                _limit_text(_slug_path(category), 15),
                _limit_text("detail", 15),
            ],
            "pinning_note": "Leave unpinned unless brand or legal requirements force a fixed position.",
        },
        "performance_max": {
            "headlines": rsa_headlines[:5],
            "long_headlines": pmax_long_headlines,
            "descriptions": rsa_descriptions,
            "business_name": _limit_text(product_name, 25),
        },
        "upload_note": "Final URL is intentionally omitted from creative copy and should be configured inside Google Ads.",
    }


def _copy_validation(ad_set: dict[str, Any]) -> dict[str, Any]:
    platform = str(ad_set.get("platform") or "")
    checks: list[dict[str, Any]] = []
    if platform == "google_ads":
        google_assets = ad_set.get("google_ads_assets") or {}
        rsa = google_assets.get("responsive_search_ad") or {}
        pmax = google_assets.get("performance_max") or {}
        for index, item in enumerate(rsa.get("headlines") or [], start=1):
            checks.append(_check_copy(f"rsa.headline_{index}", item.get("text"), 30))
        for index, item in enumerate(rsa.get("descriptions") or [], start=1):
            checks.append(_check_copy(f"rsa.description_{index}", item.get("text"), 90))
        for index, item in enumerate(rsa.get("display_paths") or [], start=1):
            checks.append(_check_copy(f"rsa.display_path_{index}", item, 15))
        for index, item in enumerate(pmax.get("long_headlines") or [], start=1):
            checks.append(_check_copy(f"pmax.long_headline_{index}", item.get("text"), 90))
        checks.append(_check_copy("pmax.business_name", pmax.get("business_name"), 25))
    else:
        for item in ad_set.get("static_image_ads") or []:
            creative_id = item.get("creative_id", "static")
            checks.append(_check_copy(f"{creative_id}.primary_text_visible", _first_line(item.get("primary_text")), 125))
            checks.append(_check_copy(f"{creative_id}.primary_text_max", item.get("primary_text"), 2200))
            checks.append(_check_copy(f"{creative_id}.headline", item.get("headline"), 40))
        carousel = ad_set.get("carousel_ad") or {}
        checks.append(_check_copy("carousel.primary_text_visible", _first_line(carousel.get("primary_text")), 125))
        for card in carousel.get("cards") or []:
            checks.append(_check_copy(f"carousel.card_{card.get('card_number')}.overlay", card.get("overlay_text"), 40))
        for index, item in enumerate(ad_set.get("primary_text_variants") or [], start=1):
            checks.append(_check_copy(f"primary_text_variant_{index}.visible", _first_line(item.get("primary_text")), 125))
            checks.append(_check_copy(f"primary_text_variant_{index}.max", item.get("primary_text"), 2200))

    failed = [item for item in checks if item["status"] == "over_limit"]
    return {
        "passed": not failed,
        "platform": platform,
        "checked_count": len(checks),
        "failed_count": len(failed),
        "checks": checks,
        "note": "Character limits are checked before export. Suggested trims are included for any over-limit field.",
    }


def _check_copy(field: str, value: Any, limit: int) -> dict[str, Any]:
    text = str(value or "")
    char_count = len(text)
    status = "ok" if char_count <= limit else "over_limit"
    result = {
        "field": field,
        "char_count": char_count,
        "limit": limit,
        "status": status,
    }
    if status == "over_limit":
        result["suggested_trim"] = _limit_text(text, limit)
    return result


def _first_line(value: Any) -> str:
    return str(value or "").splitlines()[0].strip()


def _limit_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ,.;:-")


def _slug_path(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "product"
