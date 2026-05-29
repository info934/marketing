from __future__ import annotations

from typing import Any

from app.services.localization_utils import is_czech as _is_czech_language, is_german


def generate(
    product_analysis: dict[str, Any],
    audience_research: dict[str, Any],
    creative_psychology: dict[str, Any],
    performance_insights: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    category = str(product_analysis.get("likely_product_category") or "product")
    archetype = str(audience_research.get("primary_archetype") or "practicality")
    is_czech = _is_czech_language(language)
    is_de = is_german(language)
    winning_shots = performance_insights.get("winning_shot_types") or []
    scenes = _scene_plan(category, archetype, is_czech, product_analysis, is_de=is_de)
    visual_direction = _visual_direction(product_analysis)
    if visual_direction:
        for scene in scenes:
            scene["visual"] = f"{scene.get('visual', '')} Visual product classifier guard: {visual_direction}"
    if winning_shots:
        scenes[1]["memory_note"] = f"Prefer proven shot type: {winning_shots[0]}"
    camera_rules = [
        "simple movement only: static, slight handheld sway, or slow push-in",
        "choose one category-appropriate environment from product type and use case; never copy the avatar reference background or use a blank studio",
        "show product on/with a person whenever the category allows it",
        "one buyer objection resolved per scene",
    ]
    camera_rules.extend(_visual_camera_rules(product_analysis))
    return {
        "agent": "Scene Director Agent",
        "category": category,
        "primary_archetype": archetype,
        "scene_logic": creative_psychology.get("behavior_tree", {}).get("sequence", []),
        "directed_scenes": scenes,
        "camera_rules": camera_rules,
    }


def _visual_direction(product_analysis: dict[str, Any]) -> str:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return ""
    parts = []
    detected = str(visual.get("detected_object") or "").strip()
    subcategory = str(visual.get("subcategory") or "").strip()
    if detected or subcategory:
        parts.append(
            f"image appears to show {detected or subcategory}; use this as scenario context, not as an unsupported claim"
        )
    for label, key in [
        ("scenario", "scenario_rules"),
        ("shots", "shot_requirements"),
        ("avoid", "avoid_in_generation"),
    ]:
        values = [
            str(item).strip()
            for item in (visual.get(key) or [])[:3]
            if str(item).strip()
        ]
        if values:
            parts.append(f"{label}: {'; '.join(values)}")
    return " ".join(parts)


def _visual_camera_rules(product_analysis: dict[str, Any]) -> list[str]:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return []
    rules = []
    template = str(visual.get("recommended_template_id") or "").strip()
    if template:
        rules.append(f"honour visual classifier template recommendation: {template}")
    for requirement in (visual.get("shot_requirements") or [])[:3]:
        text = str(requirement).strip()
        if text:
            rules.append(f"visual shot requirement: {text}")
    for avoid in (visual.get("avoid_in_generation") or [])[:2]:
        text = str(avoid).strip()
        if text:
            rules.append(f"visual avoid rule: {text}")
    return rules


def _scene_plan(
    category: str,
    archetype: str,
    is_czech: bool,
    product_analysis: dict[str, Any] | None = None,
    *,
    is_de: bool = False,
) -> list[dict[str, str]]:
    capacity_supported = _handbag_capacity_supported(product_analysis or {})
    material_focus = _handbag_material_focus(product_analysis or {})
    labels = _labels(category, is_czech, material_focus, product_analysis or {}, is_de=is_de)
    capacity_visual = (
        "Capacity demonstration: tablet or slim notebook, water bottle, wallet, phone, keys, and makeup pouch going inside one by one, top opening and interior lining visible, adult hands only, same bag shape and size preserved, no overstuffed distortion."
        if capacity_supported
        else "Opening and scale demonstration: phone, keys, and wallet near the top opening or briefly placed inside as scale context, no unverified capacity claim, same bag shape and size preserved."
    )
    plans = {
        "handbag": [
            {
                "purpose": "hook",
                "shot_type": "avatar with bag carried",
                "visual": "Avatar speaks the main buyer hook in a category-selected commute, office doorway, cafe entrance, quiet street doorway, hallway, mirror, or leaving-home context, bag on shoulder and then in hand against outfit, silhouette, handles, and same body-to-bag scale visible in the first two seconds, off-center smartphone framing, slight handheld sway, natural expression with a small pause, available natural light, no copied avatar-reference background, do not default to apartment interiors unless the product brief implies home use.",
                "overlay": labels[0],
            },
            {
                "purpose": "demonstration",
                "shot_type": "capacity and opening proof",
                "visual": f"{capacity_visual} Use a simple surface such as office desk, cafe table, parked car seat, hallway console, or clean counter according to the chosen context, not a studio flat lay.",
                "overlay": labels[1],
            },
            {
                "purpose": "context",
                "shot_type": "premium detail and outfit scale",
                "visual": f"Macro handheld detail sequence: {material_focus}, stitching, handles, opening, and interior lining when visible, then an outfit-scale shot in the chosen office, cafe, commute, street doorway, mirror, or hallway context, same bag size relative to torso and hands, UK/Scandinavian minimalist styling, warm neutral colours, no cluttered tabletop layout.",
                "overlay": labels[2],
            },
            {
                "purpose": "cta",
                "shot_type": "lifestyle closing recap",
                "visual": "Avatar leaves home, steps through an office doorway, pauses at a cafe entrance, or does a natural mirror outfit check with the bag on shoulder, then back on camera for a plain product-name closing recap, same wardrobe continuity, same bag size and carry position near torso, authentic relaxed face, no exaggerated smile, no fake button or URL.",
                "overlay": labels[3],
            },
        ],
        "shoes": [
            {
                "purpose": "hook",
                "shot_type": "avatar plus shoes on feet",
                "visual": "Avatar speaks in outdoor doorway, pavement edge, office lift lobby, cafe entrance, clean floor, or entryway context, shoes visible on adult feet in lower frame, off-center framing, slight handheld sway, available natural light.",
                "overlay": labels[0],
            },
            {
                "purpose": "demonstration",
                "shot_type": "worn side profile",
                "visual": "Low-angle close-ups of shoes worn on adult feet, side profile, toe shape, upper texture, sole edge and closure visible, no table, no flat lay.",
                "overlay": labels[1],
            },
            {
                "purpose": "context",
                "shot_type": "outfit mirror",
                "visual": "Outdoor doorway, cafe entrance, office lift lobby, quiet pavement edge, mirror, or entryway outfit context, shoes worn with everyday outfit hem visible, natural floor texture and realistic scale, no performance claim.",
                "overlay": labels[2],
            },
            {
                "purpose": "cta",
                "shot_type": "calm worn detail close",
                "visual": "Avatar back on camera with shoes visible on feet in lower frame, calm closing beat, same wardrobe continuity, no button instruction.",
                "overlay": labels[3],
            },
        ],
        "apparel": [
            {
                "purpose": "hook",
                "shot_type": "worn mirror intro",
                "visual": "Avatar speaks in a clean mirror, hallway, cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, or wardrobe-edge context with garment worn, full-body or near full-body head-to-toe silhouette visible from the first beat, modest expression, relaxed arms, small natural turn, off-center phone framing, slight handheld sway, available natural light, not a polished ecommerce model pose.",
                "overlay": labels[0],
            },
            {
                "purpose": "demonstration",
                "shot_type": "garment drape and seam detail",
                "visual": "Show the whole garment worn first, then brief handheld detail close-ups while worn: cut, drape, sleeve, hem, seam and exact visible finish from reference, no flat lay, soft natural light, full outfit context still understandable.",
                "overlay": labels[1],
            },
            {
                "purpose": "context",
                "shot_type": "outfit context",
                "visual": "Everyday outfit context in a category-selected cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, mirror, hallway, or wardrobe-edge setting, garment worn by adult person, full body or near full body visible, natural movement and styling, no copied avatar-reference background, no body outcome claim.",
                "overlay": labels[2],
            },
            {
                "purpose": "cta",
                "shot_type": "calm worn close",
                "visual": "Avatar back on camera with garment worn, full outfit silhouette visible again, same wardrobe continuity where possible, calm closing beat without button instruction.",
                "overlay": labels[3],
            },
        ],
    }
    return plans.get(category) or [
        {
            "purpose": "hook",
            "shot_type": "avatar with product in context",
            "visual": "Avatar speaks directly to camera in one category-selected minimal real-space context based on product type and use case, product held, worn, or used naturally at frame edge, off-center framing, slight handheld sway, available natural light, no copied avatar-reference background, avoid defaulting to home/apartment interiors unless the product is home-use.",
            "overlay": labels[0],
        },
        {
            "purpose": "demonstration",
            "shot_type": "product detail close-up",
            "visual": "Handheld close-ups of visible product shape, finish, controls, texture, construction or packaging if present, product held or used when plausible, soft directional light.",
            "overlay": labels[1],
        },
        {
            "purpose": "context",
            "shot_type": "real-life scale",
            "visual": "Everyday context shot adapted to the product category, product used or held by an adult person in a plausible minimal real space, no studio look, no copied avatar-reference background.",
            "overlay": labels[2],
        },
        {
            "purpose": "cta",
            "shot_type": "calm detail close",
            "visual": "Avatar back on camera with product visible and handled naturally, same setting and wardrobe continuity, subtle smile, no button instruction.",
            "overlay": labels[3],
        },
    ]


def _labels(
    category: str,
    is_czech: bool,
    material_focus: str = "material texture",
    product_analysis: dict[str, Any] | None = None,
    *,
    is_de: bool = False,
) -> list[str]:
    material_label_cs = "Detail kuze" if "leather" in material_focus else "Detail materialu"
    material_label_en = "Soft leather look" if "leather" in material_focus else "Material close-up"
    product_name = str((product_analysis or {}).get("product_name") or "")
    product_label = product_name.split("|", 1)[0].strip() or "BELLA"
    closing_label_cs = f"{product_label} na kazdy den"
    closing_label_en = product_label if "tote" in product_label.lower() else f"{product_label} everyday tote"
    if is_czech:
        return {
            "handbag": ["Elegantni a prakticka", "Vejde se den", material_label_cs, closing_label_cs],
            "shoes": ["Profil na noze", "Detail podrazky", "Outfit v realu", "Detail v klidu"],
            "apparel": ["Strih na postave", "Material v pohybu", "Outfit v realu", "Detail v klidu"],
        }.get(category, ["Zacni detailem", "Detail zblizka", "Meritko v realu", "Detail v klidu"])
    if is_de:
        material_label_de = "Lederdetail" if "leather" in material_focus else "Materialdetail"
        closing_label_de = product_label if "tote" in product_label.lower() else f"{product_label} im Alltag"
        return {
            "handbag": ["Elegant und praktisch", "Passt in den Alltag", material_label_de, closing_label_de],
            "shoes": ["Profil am Fuss", "Sohlendetail", "Im Outfit", "Ruhiger Detailcheck"],
            "apparel": ["Schnitt getragen", "Detail in Bewegung", "Im Outfit", "Ruhiger Detailcheck"],
        }.get(category, ["Detail zuerst", "Nahes Detail", "Echte Groesse", "Ruhiger Check"])
    return {
        "handbag": ["Elegant but practical", "Fits daily essentials", material_label_en, closing_label_en],
        "shoes": ["Worn profile", "Sole detail", "Outfit context", "Calm detail check"],
        "apparel": ["Worn cut", "Garment movement", "Outfit context", "Calm detail check"],
    }.get(category, ["Check the detail", "Close-up detail", "Real-life scale", "Calm detail check"])


def _handbag_capacity_supported(product_analysis: dict[str, Any]) -> bool:
    text = " ".join(
        str(item)
        for item in [
            product_analysis.get("internal_brief_notes"),
            *(product_analysis.get("user_provided_facts") or []),
            *(product_analysis.get("safe_benefits") or []),
            *((product_analysis.get("known_product_facts") or {}).values()),
        ]
        if item
    ).lower()
    return any(
        phrase in text
        for phrase in [
            "spacious",
            "roomy",
            "capacity",
            "interior",
            "waterproof interior",
            "tablet",
            "laptop",
            "daily essentials",
            "work errands and travel",
        ]
    )


def _handbag_material_focus(product_analysis: dict[str, Any]) -> str:
    text = " ".join(
        str(item)
        for item in [
            *((product_analysis.get("known_product_facts") or {}).values()),
            *(product_analysis.get("user_provided_facts") or []),
            *(product_analysis.get("ad_safe_detail_phrases") or []),
            product_analysis.get("internal_brief_notes"),
        ]
        if item
    ).lower()
    if "vegan leather" in text:
        return "vegan leather finish"
    if "leather" in text:
        return "leather texture"
    return "material texture"
