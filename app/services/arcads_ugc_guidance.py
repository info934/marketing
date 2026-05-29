from __future__ import annotations

from typing import Any

from app.services import scenario_contract


AVOID_POLISHED_WORDS = [
    "cinematic",
    "professional",
    "stunning",
    "8k",
    "studio",
    "perfect",
]

SOURCE = "local skill/claude-arcads creative rules; Arcads API ignored"


def build_guidance(
    product_analysis: dict[str, Any],
    settings: dict[str, Any] | None = None,
    user_scenario_lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt the claude-arcads UGC creative rules to this app's own video pipeline."""

    settings = settings or {}
    category = str(product_analysis.get("likely_product_category") or settings.get("product_category") or "general").lower()
    visual = product_analysis.get("visual_product_understanding") or {}
    contract = scenario_contract.build(
        user_scenario_lock,
        product_analysis=product_analysis,
    )
    product_text = " ".join(
        str(product_analysis.get(key) or "")
        for key in ("product_name", "product_info", "category", "likely_product_category")
    ).lower()
    template = _select_template(category, product_text, settings, visual, user_scenario_lock)
    beats = _beats_for_contract(template, contract)
    return {
        "source": SOURCE,
        "template_id": template["id"],
        "template_name": template["name"],
        "template_reason": template["reason"],
        "arcads_api": "not used by this app",
        "prompt_rules": {
            "word_budget": "keep provider-facing direction concise; avoid bloated prose when possible",
            "no_generated_text": "No generated on-screen text, hook stickers, subtitles, captions, lower thirds, labels, floating text, or later text inside the generated ecommerce video; the hook is spoken aloud.",
            "realism": (
                "handheld phone framing, natural room or outdoor light, simple real setting, real product handling, "
                "small imperfections, plain spoken dialogue"
            ),
            "avoid_words": AVOID_POLISHED_WORDS,
            "avoid_style": "polished fashion-ad staging, fake luxury sets, over-choreographed movement, fake UI, title cards, floating text, subtitle overlays",
        },
        "beat_structure": beats,
        "camera_style": template["camera_style"],
        "closing_emotion": template["closing_emotion"],
        "visual_classifier": {
            "status": visual.get("status"),
            "detected_object": visual.get("detected_object"),
            "subcategory": visual.get("subcategory"),
            "category_confidence": visual.get("category_confidence"),
            "recommended_template_id": visual.get("recommended_template_id"),
            "shot_requirements": scenario_contract.filter_conflicting_items(
                visual.get("shot_requirements") or [],
                contract,
            ),
        },
    }


def _beats_for_contract(template: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    beats = [str(beat) for beat in template.get("beats") or []]
    tags = set(contract.get("tags") or [])
    if template.get("id") == "carry_capacity_check" and {"bag_closed", "no_insert_items"} & tags:
        return [
            "0-2s bag visible on shoulder or in hand with adult body scale",
            "2-6s exterior proof only: strap, silhouette, zipper line, pattern, and scale while the bag stays closed",
            "6-11s approved proof items placed beside the closed bag, never inserted inside",
            "11s-end everyday carry recap in hallway, office doorway, cafe entrance, or commute context",
        ]
    if contract.get("enabled"):
        lock = scenario_contract.video_prompt_lock(contract)
        if lock:
            return [f"{beat}; {lock}" if index == 0 else beat for index, beat in enumerate(beats)]
    return beats


def _select_template(
    category: str,
    product_text: str,
    settings: dict[str, Any],
    visual: dict[str, Any] | None = None,
    user_scenario_lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        isinstance(user_scenario_lock, dict)
        and user_scenario_lock.get("enabled")
        and user_scenario_lock.get("template_id") == "mirror_selfie_try_on_review"
    ):
        return _mirror_selfie_try_on("user-approved mirror selfie try-on scenario")

    requested = str(settings.get("ugc_template") or settings.get("arcads_ugc_template") or "").lower().strip()
    if requested:
        if "unbox" in requested:
            return _product_unboxing("requested by settings")
        if "face" in requested or "lifestyle" in requested:
            return _creator_connected_lifestyle("requested by settings")
        if "app" in requested:
            return _app_promo("requested by settings")
        return _talking_head("requested by settings")

    visual = visual or {}
    recommended = str(visual.get("recommended_template_id") or "").strip()
    confidence = float(visual.get("category_confidence") or 0)
    if visual.get("status") == "completed" and confidence >= 0.65:
        if recommended == "apparel_try_on_full_body":
            return _apparel_try_on("visual classifier detected apparel that needs full-body worn proof")
        if recommended == "worn_footwear_check":
            return _worn_footwear("visual classifier detected footwear that needs worn foot proof")
        if recommended == "carry_capacity_check":
            return _carry_capacity("visual classifier detected a bag that needs carry/scale proof")
        if recommended == "product_unboxing":
            return _product_unboxing("visual classifier found packaging/unboxing context")
        if recommended == "creator_connected_lifestyle":
            return _creator_connected_lifestyle("visual classifier recommended product-in-use proof")
        if recommended == "app_promo":
            return _app_promo("visual classifier recommended app/software proof")

    if category in {"app", "software", "saas", "mobile_app"} or any(word in product_text for word in ["app ", "iphone", "android", "software"]):
        return _app_promo("product appears to be an app or software offer")
    if any(word in product_text for word in ["box", "boxed", "packaging", "package", "unbox", "bundle", "kit"]):
        return _product_unboxing("product/brief mentions packaging or unboxing context")
    if category in {"apparel", "clothing", "beauty", "home", "electronics"}:
        return _creator_connected_lifestyle("category benefits from close product handling and lifestyle context")
    return _talking_head("default ecommerce dropshipping format with creator trust")


def _apparel_try_on(reason: str) -> dict[str, Any]:
    return {
        "id": "apparel_try_on_full_body",
        "name": "Apparel full-body try-on proof",
        "reason": reason,
        "beats": [
            "0-2s full-body or near-full-body phone/mirror try-on view with garment worn",
            "2-6s small natural turn showing cut, drape, hem, sleeve/strap, and scale on body",
            "6-11s brief worn detail close-up only after full silhouette is established",
            "11s-end full outfit recap in the same simple real setting, no runway posing",
        ],
        "camera_style": "normal handheld phone or mirror try-on framing, head-to-toe when possible, natural light, modest expression",
        "closing_emotion": "The feeling of checking how the garment really sits on a person before buying.",
    }


def _mirror_selfie_try_on(reason: str) -> dict[str, Any]:
    return {
        "id": "mirror_selfie_try_on_review",
        "name": "Mirror selfie try-on review",
        "reason": reason,
        "beats": [
            "0-2s full-body or near-full-body mirror reflection hook, smartphone visibly held in one hand but not covering the speaking mouth, garment worn, live motion from first frame with tiny phone sway, blink, or mouth movement",
            "2-6s same mirror setup, free hand points to waist, neckline, cut, drape, or silhouette",
            "6-11s small partial side-turn in front of mirror while still facing the mirror, slight phone shake, full outfit scale remains visible, no back turn",
            "11s-end calm friend-to-friend recap in the same mirror reflection, no studio, external camera, b-roll, cutaway, or perspective switch",
        ],
        "camera_style": "handheld mirror selfie through a bedroom mirror for the entire duration, smartphone visible in creator's hand but low or to the side during speech so the mouth is visible, normal 9:16 smartphone framing, natural human proportions, no fisheye or mirror stretch, natural indoor light, slight imperfect framing, no third-person camera, no side filming, no room camera, no b-roll, no cutaway, no perspective switch, no frozen opening",
        "closing_emotion": "The feeling of checking how the outfit really looks in a normal bedroom mirror before buying.",
    }


def _worn_footwear(reason: str) -> dict[str, Any]:
    return {
        "id": "worn_footwear_check",
        "name": "Worn footwear buyer check",
        "reason": reason,
        "beats": [
            "0-2s shoes already worn on adult feet in a real outfit context",
            "2-6s side profile, toe shape, closure, upper texture, and sole edge proof",
            "6-11s low-angle outfit context with natural floor scale, no running or medical claims",
            "11s-end calm worn detail recap with the same shoes visible",
        ],
        "camera_style": "low handheld phone angle, shoes worn on feet, small natural stance shift, realistic floor texture",
        "closing_emotion": "The feeling of checking shape and styling on real feet before buying.",
    }


def _carry_capacity(reason: str) -> dict[str, Any]:
    return {
        "id": "carry_capacity_check",
        "name": "Carry and capacity buyer check",
        "reason": reason,
        "beats": [
            "0-2s bag visible on shoulder or in hand with adult body scale",
            "2-6s handle, strap drop, opening, structure, stitching, and material proof",
            "6-11s capacity or interior proof only if verified; otherwise use nearby items as scale context",
            "11s-end everyday carry recap in hallway, office doorway, cafe entrance, or commute context",
        ],
        "camera_style": "handheld phone, adult hand/shoulder carry, stable scale, natural light, no luxury/status staging",
        "closing_emotion": "The feeling of checking real size, carry, and details before buying.",
    }


def _talking_head(reason: str) -> dict[str, Any]:
    return {
        "id": "talking_head_product_check",
        "name": "Talking head product-check",
        "reason": reason,
        "beats": [
            "0-2s spoken hook with product visible in creator's hand, worn, or at frame edge",
            "2-6s practical buyer-check proof: scale, fit, capacity, handling, or visible finish",
            "6-11s close creator-connected detail: hands/torso/shoulder remain visible with the product",
            "11s-end normal-use context and plain product-name recap",
        ],
        "camera_style": "front-phone or handheld phone framing, off-center crop, slight handheld sway, natural exposure",
        "closing_emotion": "The feeling of checking the product like a real buyer before deciding.",
    }


def _product_unboxing(reason: str) -> dict[str, Any]:
    return {
        "id": "product_unboxing",
        "name": "Product unboxing",
        "reason": reason,
        "beats": [
            "0-2s creator opens with product/package already visible, no fake surprise",
            "2-6s simple packaging or first-look handling if packaging is verified",
            "6-11s product proof close-up: finish, scale, label, parts, or texture from the reference",
            "11s-end practical recap with the product held steady in normal light",
        ],
        "camera_style": "handheld table/desk/counter phone shot, creator hands visible, slow movements, one object per action",
        "closing_emotion": "The feeling of seeing what actually arrives before buying.",
    }


def _creator_connected_lifestyle(reason: str) -> dict[str, Any]:
    return {
        "id": "creator_connected_lifestyle",
        "name": "Creator-connected lifestyle proof",
        "reason": reason,
        "beats": [
            "0-2s product in use or held naturally with creator presence visible",
            "2-6s hands-on proof in a simple real environment",
            "6-11s detail or use-context shot, never isolated product-only b-roll",
            "11s-end calm recap with product still visible",
        ],
        "camera_style": "handheld phone close-ups, natural light, face/torso/hands connected to the product",
        "closing_emotion": "The feeling of seeing the product in a normal day, not a brand shoot.",
    }


def _app_promo(reason: str) -> dict[str, Any]:
    return {
        "id": "app_promo",
        "name": "App promo creator proof",
        "reason": reason,
        "beats": [
            "0-2s creator states the practical app problem",
            "2-6s phone/app screen proof if supplied by the user",
            "6-11s one simple outcome or workflow step, no fake UI if no screen reference exists",
            "11s-end creator recap without fake buttons or platform UI",
        ],
        "camera_style": "creator-to-camera plus phone-in-hand framing, simple cuts, real screen reference only when supplied",
        "closing_emotion": "The feeling of checking whether the app solves the job quickly.",
    }
