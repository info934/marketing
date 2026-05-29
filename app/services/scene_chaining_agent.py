from __future__ import annotations

from typing import Any


def generate(
    product_analysis: dict[str, Any],
    avatar: dict[str, Any],
    settings: dict[str, Any],
    scene_direction: dict[str, Any],
    voice_personality: dict[str, Any],
) -> dict[str, Any]:
    finance_mode = str(settings.get("app_mode") or "").strip() == "finance_personal_brand"
    category = "finance" if finance_mode else str(product_analysis.get("likely_product_category") or "product")
    use_reference = bool(settings.get("use_avatar_image_reference"))
    directed_scenes = scene_direction.get("directed_scenes") or []
    environment = _environment_anchor(category)
    wardrobe = _wardrobe_anchor(avatar)
    scene_links = []
    for index, scene in enumerate(directed_scenes):
        scene_links.append(
            {
                "scene_index": index + 1,
                "purpose": scene.get("purpose") or ("hook" if index == 0 else "cta"),
                "continuity_source": "original_avatar_reference" if index == 0 else "previous_scene_last_frame",
                "last_frame_capture": _last_frame_capture(index, len(directed_scenes), category),
                "next_scene_start": _next_scene_start(index, scene, category),
                "motion_bridge": _motion_bridge(index, category),
                "environment_anchor": environment,
                "wardrobe_anchor": wardrobe,
                "reference_role": _reference_role(index, use_reference, category),
            }
        )
    provider_execution = _provider_execution_contract(settings, use_reference)
    true_scene_chaining_plan = _true_scene_chaining_plan(
        category=category,
        use_reference=use_reference,
        provider_execution=provider_execution,
        scene_links=scene_links,
        environment=environment,
        wardrobe=wardrobe,
    )
    return {
        "version": "scene_chaining_v2",
        "agent": "Scene Chaining Agent",
        "creative_mode": "finance_personal_brand" if finance_mode else "ecommerce_ugc",
        "mode": "true_scene_chaining" if use_reference else "prompt_level_chaining",
        "reference_strategy": (
            "original avatar for scene 1, then previous scene last frame for avatar-on-camera scenes"
            if use_reference
            else "prompt-level continuity only; enable public avatar reference URL for stronger chaining"
        ),
        "provider_execution": provider_execution,
        "true_scene_chaining_plan": true_scene_chaining_plan,
        "audit_summary": _audit_summary(true_scene_chaining_plan),
        "identity_continuity": "preserve face identity, expression dynamics, voice, and wardrobe across avatar scenes; avatar reference background is ignored",
        "wardrobe_continuity": wardrobe,
        "environment_continuity": environment,
        "motion_continuity": [
            "end each avatar scene with a stable face/product frame suitable as next reference",
            "start the next avatar scene from a similar head angle and product position",
            "use hard cuts on natural sentence endings",
            "avoid aggressive camera moves that break identity lock",
        ],
        "scene_links": scene_links,
        "seedance_prompt_addendum": _prompt_addendum(use_reference, environment, wardrobe, category),
    }


def _environment_anchor(category: str) -> str:
    if category == "finance":
        return "same modern podcast studio layout across all scenes, approved scene concept frame when supplied, Czech infographic positions preserved"
    if category == "handbag":
        return "one category-selected commute, office doorway, cafe entrance, quiet street doorway, parked-car-seat, hallway, mirror, or leaving-home context with consistent natural light direction; do not default to a bedroom/living-room apartment unless the product brief implies home use; do not copy avatar or product reference background"
    if category == "shoes":
        return "one category-selected pavement edge, outdoor doorway, office lift lobby, cafe entrance, clean floor, or outfit-scale context with consistent natural light direction; do not default to a bedroom/living-room apartment unless the product brief implies home use; do not copy avatar or product reference background"
    if category == "apparel":
        return "one category-selected cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, mirror, hallway, or wardrobe-edge context with consistent natural light direction; do not default to a bedroom/living-room apartment unless the product brief implies home use; do not copy avatar or product reference background"
    return "one category-selected minimal real-space context with consistent natural light direction; choose from product type and use case, not avatar reference background, and avoid defaulting to home/apartment interiors unless the product is home-use"


def _wardrobe_anchor(avatar: dict[str, Any]) -> str:
    policy = str(avatar.get("wardrobe_policy") or "reference_unchanged")
    if policy == "allow_controlled_change":
        return "controlled wardrobe continuity, one simple outfit family, no distracting changes"
    if policy == "consistent_simple":
        return "simple consistent wardrobe across all avatar scenes"
    return "wardrobe as in reference image, unchanged across avatar scenes"


def _last_frame_capture(index: int, total: int, category: str) -> str:
    if index == total - 1:
        return "final frame holds stable face and product-visible pose for clean export review"
    if category == "finance":
        return "hold last frame with avatar face stable, hands visible, and active Czech infographic card still readable"
    if category == "handbag":
        return "hold last frame with avatar face stable and same-size bag still visible near shoulder or torso"
    if category == "shoes":
        return "hold last frame with avatar face stable and shoes or lower-frame product cue still visible"
    if category == "apparel":
        return "hold last frame with avatar face stable and garment still visible in worn context"
    return "hold last frame with avatar face stable and product still visible"


def _next_scene_start(index: int, scene: dict[str, Any], category: str) -> str:
    if index == 0:
        return "start from original avatar reference, direct-to-camera hook, product visible early"
    if scene.get("purpose") == "cta":
        return "start from previous avatar/product pose, return to direct-to-camera closing beat"
    if category == "finance":
        return "start from the same podcast studio angle, continue the Czech infographic layout, and let the creator gesture toward the next highlighted card"
    if category == "handbag":
        return "start close to previous product position, then cut into bag detail without changing product orientation, bag size class, handle length, or carry scale"
    if category == "shoes":
        return "start from similar floor and outfit context, then move into worn shoe detail"
    if category == "apparel":
        return "start from similar mirror/body angle, then move into worn garment cut detail"
    return "start from the previous environment and product position, then move into the next planned detail"


def _motion_bridge(index: int, category: str) -> str:
    if index == 0:
        return "small glance from camera to product creates bridge into first detail scene"
    if category == "finance":
        return "creator glances toward the current infographic card, small air-tap triggers the next card, then hard cut"
    if category == "handbag":
        return "hand adjusts handle or bag angle gently, then hard cut"
    if category == "shoes":
        return "small foot turn or weight shift, then hard cut"
    if category == "apparel":
        return "small garment adjustment or shoulder turn, then hard cut"
    return "small product glance or hand gesture, then hard cut"


def _prompt_addendum(use_reference: bool, environment: str, wardrobe: str, category: str) -> str:
    if category == "finance":
        mode = (
            "Use avatar reference for identity and hold stable frames between scenes; if provider supports last-frame chaining, later scenes reuse the previous stable face/infographic frame."
            if use_reference
            else "Maintain prompt-level avatar and podcast-studio continuity; exact last-frame identity chaining requires a public avatar reference."
        )
        return (
            f"Scene continuity: {mode} Keep {wardrobe}. Keep environment continuity: {environment}. "
            "Modern Czech finance infographics must keep consistent positions, typography style, color palette, and gesture timing across cuts. "
            "The avatar interacts with cards by gaze, pointing, and subtle air-tap gestures; all speech and readable text are Czech only. "
            "End each scene on a stable, non-blurry face and infographic frame."
        )
    mode = (
        "Use last-frame continuity between avatar-on-camera scenes: scene 1 uses original avatar reference, later avatar scenes use previous scene last frame as continuity reference."
        if use_reference
        else "Maintain prompt-level continuity across scenes; exact last-frame chaining requires public avatar reference mode."
    )
    return (
        f"True scene chaining: {mode} Keep {wardrobe}. Keep environment continuity: {environment}. "
        "Use the avatar reference for identity only; do not copy its room, furniture, decor, props, or lighting. Do not add random furniture or decorative props; creator-video style comes from camera motion and delivery. "
        f"For {category}, maintain product position, scale, lighting direction, and natural motion continuity across cuts. "
        + (
            "For handbag, keep the same bag size, body-to-bag proportion, handle length, strap drop, silhouette, and carry position across all cuts. "
            if category == "handbag"
            else ""
        )
        + "End each avatar scene on a stable, non-blurry frame suitable for identity chaining."
    )


def _reference_role(index: int, use_reference: bool, category: str) -> str:
    if not use_reference:
        return "prompt-only continuity; no avatar image is sent for this scene"
    if index == 0:
        return "original avatar reference anchors identity for the opening scene"
    if category == "finance":
        return "previous stable frame should anchor avatar identity and infographic layout when per-scene chaining is available"
    return "previous stable frame should anchor avatar identity and product scale when per-scene chaining is available"


def _provider_execution_contract(settings: dict[str, Any], use_reference: bool) -> dict[str, Any]:
    input_references = [item for item in settings.get("input_references", []) if item]
    frame_images = [item for item in settings.get("frame_images", []) if item]
    per_scene_enabled = bool(settings.get("enable_per_scene_last_frame_chaining"))
    return {
        "current_mode": "per_scene_last_frame_requests" if per_scene_enabled else "single_video_request_with_prompted_continuity",
        "per_scene_last_frame_calls_enabled": per_scene_enabled,
        "avatar_reference_supplied": use_reference,
        "input_reference_count": len(input_references),
        "frame_image_count": len(frame_images),
        "actual_last_frame_reuse": (
            "enabled by orchestrator flag"
            if per_scene_enabled
            else "not yet executed as separate provider calls; prompt requests stable end frames for future chaining"
        ),
        "provider_note": (
            "Seedance-style prompting supports reference roles and first/last-frame continuity, but this app currently sends one consolidated /videos request unless per-scene chaining is explicitly enabled."
        ),
    }


def _true_scene_chaining_plan(
    *,
    category: str,
    use_reference: bool,
    provider_execution: dict[str, Any],
    scene_links: list[dict[str, Any]],
    environment: str,
    wardrobe: str,
) -> dict[str, Any]:
    product_rule = (
        "keep bag body size, strap drop, handle length, silhouette, and carry scale consistent"
        if category == "handbag"
        else "keep product shape, scale, colour, visible markings, and handling position consistent"
    )
    if category == "finance":
        product_rule = "no ecommerce product; keep Czech infographic layout, disclaimer, cards, and avatar-personal-brand set consistent"
    return {
        "strategy": "original_avatar_for_first_scene_then_last_frame_chain",
        "current_execution_mode": provider_execution.get("current_mode"),
        "identity_lock": (
            "avatar reference image controls identity; text controls only motion/expression/speech"
            if use_reference
            else "prompt-only identity continuity; lower consistency confidence"
        ),
        "environment_lock": environment,
        "wardrobe_lock": wardrobe,
        "product_or_graphic_lock": product_rule,
        "scene_link_count": len(scene_links),
        "scene_links": [
            {
                "scene_index": link.get("scene_index"),
                "purpose": link.get("purpose"),
                "continuity_source": link.get("continuity_source"),
                "last_frame_capture": link.get("last_frame_capture"),
                "next_scene_start": link.get("next_scene_start"),
                "motion_bridge": link.get("motion_bridge"),
            }
            for link in scene_links
        ],
        "quality_requirements": [
            "stable non-blurry end frame",
            "simple camera motion only",
            "hard cut on natural sentence ending",
            "same lighting direction between linked scenes",
        ],
        "limitations": [
            provider_execution.get("actual_last_frame_reuse"),
            "provider can still drift if it ignores reference-role instructions",
        ],
    }


def _audit_summary(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": plan.get("strategy"),
        "execution": plan.get("current_execution_mode"),
        "scene_link_count": plan.get("scene_link_count"),
        "identity_lock": plan.get("identity_lock"),
        "product_or_graphic_lock": plan.get("product_or_graphic_lock"),
    }
