from __future__ import annotations

from typing import Any


ANGLE_LIBRARY = {
    "fear": {
        "safe_label": "uncertainty_reduction",
        "driver": "reduce the worry of judging from one polished image",
        "hook_bias": "call out the risk of missing visible details",
    },
    "aspiration": {
        "safe_label": "aspirational_fit",
        "driver": "help the buyer imagine the product fitting a better everyday routine",
        "hook_bias": "show the product in a polished but realistic context",
    },
    "identity": {
        "safe_label": "identity_fit",
        "driver": "make the product feel relevant to how this buyer sees themselves",
        "hook_bias": "call out the careful shopper or style-aware buyer",
    },
    "convenience": {
        "safe_label": "practical_ease",
        "driver": "make everyday use and evaluation feel easier to judge",
        "hook_bias": "show the product clearly in a practical buying context",
    },
    "status": {
        "safe_label": "polished_self_presentation",
        "driver": "signal polish through styling and finish without status-signaling claims",
        "hook_bias": "lead with outfit compatibility and restrained finish",
    },
    "curiosity": {
        "safe_label": "detail_curiosity",
        "driver": "make the viewer want to inspect the product closer",
        "hook_bias": "lead with a specific detail question or zoom cue",
    },
    "transformation": {
        "safe_label": "context_shift",
        "driver": "show a change in evaluation context, not a product or body transformation claim",
        "hook_bias": "frame before/after as before checking details vs after seeing context",
    },
}


def generate(
    product_analysis: dict[str, Any],
    audience_research: dict[str, Any],
    performance_insights: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    category = str(product_analysis.get("likely_product_category") or "unknown")
    archetype = str(audience_research.get("primary_archetype") or "practicality")
    understanding = product_analysis.get("automatic_product_understanding") or {}
    facts = " ".join(
        str(item)
        for item in (
            product_analysis.get("user_provided_facts") or []
        )
        + (understanding.get("style_tags") or [])
        + (understanding.get("usage_contexts") or [])
    ).lower()
    scores = _score_angles(category, archetype, facts, performance_insights)
    primary = scores[0]["angle"]
    secondary = [item["angle"] for item in scores[1:4]]
    library_item = ANGLE_LIBRARY[primary]
    return {
        "agent": "Emotional Angle Engine",
        "category": category,
        "primary_archetype": archetype,
        "primary_angle": primary,
        "primary_safe_label": library_item["safe_label"],
        "secondary_angles": secondary,
        "angle_scores": scores,
        "driver": library_item["driver"],
        "hook_bias": library_item["hook_bias"],
        "creative_set_bias": _creative_set_bias(primary, category),
        "voice_bias": _voice_bias(primary),
        "scene_bias": _scene_bias(primary, category),
        "safety_rule": (
            "Emotional angle is internal strategy only. Do not invent outcomes, social proof, "
            "medical effects, status-signaling claims, or body/product transformation claims."
        ),
    }


def _score_angles(
    category: str,
    archetype: str,
    facts: str,
    performance_insights: dict[str, Any],
) -> list[dict[str, Any]]:
    weights = {angle: 10 for angle in ANGLE_LIBRARY}
    if archetype in {"practicality", "office", "travel", "comfort"}:
        weights["convenience"] += 7
        weights["fear"] += 4
    if archetype in {"fashion", "aesthetic", "elegance", "minimalist"}:
        weights["identity"] += 6
        weights["aspiration"] += 5
        weights["status"] += 3
    if category in {"handbag", "apparel"}:
        weights["identity"] += 4
        weights["aspiration"] += 3
    if category == "shoes":
        weights["fear"] += 4
        weights["convenience"] += 3
    if any(word in facts for word in ["work", "office", "commute", "errands", "travel", "interior"]):
        weights["convenience"] += 6
    if any(word in facts for word in ["minimal", "polished", "structured", "outfit"]):
        weights["identity"] += 4
        weights["status"] += 2
    if any(word in facts for word in ["detail", "shape", "handle", "sole", "cut", "finish"]):
        weights["curiosity"] += 4

    memory_angles = (performance_insights.get("seed_insights") or {}).get("winning_emotional_angles") or []
    for angle in memory_angles:
        if angle in weights:
            weights[angle] += 5

    return [
        {
            "angle": angle,
            "score": score,
            "safe_label": ANGLE_LIBRARY[angle]["safe_label"],
            "rationale": ANGLE_LIBRARY[angle]["driver"],
        }
        for angle, score in sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    ]


def _creative_set_bias(angle: str, category: str) -> dict[str, str]:
    return {
        "C1": f"UGC video leads with {ANGLE_LIBRARY[angle]['safe_label']} through creator-led inspection",
        "C2": "static product hero slot should make product shape, scale, and one visible cue obvious fast",
        "C3": "static use-context slot should show person/product/category fit in a real context",
        "C4": "detail proof slot should resolve the emotional tension through visible product evidence",
        "C5": f"buying-guide carousel should move from hero to cue to context to proof for {category}",
    }


def _voice_bias(angle: str) -> dict[str, str]:
    biases = {
        "fear": {"confidence": "calm", "pacing": "slightly slower", "gesture": "small point-to-detail gestures"},
        "aspiration": {"confidence": "warm", "pacing": "medium", "gesture": "soft open-hand gestures"},
        "identity": {"confidence": "casual", "pacing": "medium", "gesture": "relatable outfit/product gestures"},
        "convenience": {"confidence": "practical", "pacing": "clear medium", "gesture": "show-and-tell gestures"},
        "status": {"confidence": "quietly confident", "pacing": "measured", "gesture": "restrained detail gestures"},
        "curiosity": {"confidence": "curious", "pacing": "slightly quicker hook", "gesture": "lean-in and point gestures"},
        "transformation": {"confidence": "observational", "pacing": "before-after contrast", "gesture": "contrast gestures"},
    }
    return biases.get(angle, biases["curiosity"])


def _scene_bias(angle: str, category: str) -> list[str]:
    return [
        f"Scene 1 should make the {ANGLE_LIBRARY[angle]['safe_label']} angle obvious without overexplaining it",
        f"Middle scenes should use {category} category evidence instead of generic b-roll",
        "Final scene should close the emotional loop with calm consideration, not urgency",
    ]
