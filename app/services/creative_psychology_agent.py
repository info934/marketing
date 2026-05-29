from __future__ import annotations

from typing import Any


def generate(
    product_analysis: dict[str, Any],
    audience_research: dict[str, Any],
    performance_insights: dict[str, Any],
    emotional_angle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = str(product_analysis.get("likely_product_category") or "unknown")
    archetype = str(audience_research.get("primary_archetype") or "practicality")
    emotional_angle = emotional_angle or {}
    behavior_tree = _behavior_tree(category, archetype)
    behavior_tree = _apply_emotional_angle(behavior_tree, emotional_angle)
    memory_hooks = performance_insights.get("winning_hooks") or []
    memory_shots = performance_insights.get("winning_shot_types") or []
    return {
        "agent": "Creative Psychology Agent",
        "category": category,
        "primary_archetype": archetype,
        "emotional_angle": emotional_angle,
        "primary_driver": behavior_tree["driver"],
        "behavior_tree": behavior_tree,
        "hook_psychology": _hook_psychology(category, archetype),
        "variation_rules": _variation_rules(category, archetype),
        "memory_influence": {
            "winning_hooks": memory_hooks,
            "winning_shot_types": memory_shots,
            "rule": "Use winning memory patterns when present; otherwise diversify across the behavior tree.",
        },
    }


def _behavior_tree(category: str, archetype: str) -> dict[str, Any]:
    trees = {
        "handbag": {
            "practicality": {
                "driver": "reduce uncertainty about daily carry usefulness without capacity claims",
                "sequence": ["interrupt polished-photo trust", "show carried scale", "show opening/handles", "close calmly"],
                "emotional_curve": "doubt -> inspection -> confidence to evaluate",
            },
            "office": {
                "driver": "make the bag feel compatible with a workday outfit and desk-to-door routine",
                "sequence": ["call out workday context", "show structured silhouette", "show handle/opening detail", "close with calm check"],
                "emotional_curve": "recognition -> relevance -> detail reassurance",
            },
            "travel": {
                "driver": "make scale and on-the-go handling easy to judge",
                "sequence": ["start with carry moment", "show in-hand scale", "show top opening", "close with travel-context detail"],
                "emotional_curve": "curiosity -> imagined use -> practical evaluation",
            },
            "elegance": {
                "driver": "signal polish through silhouette and finish, not brand-status claims",
                "sequence": ["show outfit silhouette", "show finish detail", "show carried movement", "close on shape"],
                "emotional_curve": "style interest -> proof by detail -> calm desire",
            },
        },
        "shoes": {
            "comfort": {
                "driver": "replace abstract comfort claims with visible worn construction cues",
                "sequence": ["reject table shot", "show side profile on foot", "show sole/upper detail", "close on worn evaluation"],
                "emotional_curve": "skepticism -> visible check -> calmer decision",
            },
            "aesthetic": {
                "driver": "help the viewer judge outfit compatibility quickly",
                "sequence": ["show worn profile", "show outfit context", "show toe/sole detail", "close on style check"],
                "emotional_curve": "visual interest -> relevance -> detail confirmation",
            },
            "sporty": {
                "driver": "suggest movement-ready styling without performance promises",
                "sequence": ["show on-foot stance", "show sole edge", "show casual movement", "close on visible details"],
                "emotional_curve": "energy -> inspection -> grounded interest",
            },
            "minimalist": {
                "driver": "make clean shape and low-clutter styling easy to judge",
                "sequence": ["show simple side profile", "show texture/closure", "show outfit line", "close calmly"],
                "emotional_curve": "clarity -> detail -> quiet confidence",
            },
        },
        "apparel": {
            "aesthetic": {
                "driver": "prove the piece through worn cut and movement, not flat-lay polish",
                "sequence": ["show worn cut", "show movement", "show seam/detail close-up", "close on styling check"],
                "emotional_curve": "style curiosity -> fit visibility -> detail confidence",
            },
            "office": {
                "driver": "make the piece feel plausible for an everyday smart outfit",
                "sequence": ["show mirror outfit", "show sleeve/hem", "show hallway context", "close calmly"],
                "emotional_curve": "relevance -> detail -> consideration",
            },
            "minimalist": {
                "driver": "let simple silhouette and visible garment detail carry the ad",
                "sequence": ["show clean worn silhouette", "show garment movement", "show seam/hem", "close on calm detail"],
                "emotional_curve": "clarity -> appreciation -> consideration",
            },
        },
    }
    category_tree = trees.get(category) or {}
    return category_tree.get(archetype) or {
        "driver": "reduce product uncertainty with visible detail and real context",
        "sequence": ["call out detail check", "show close-up", "show context", "close calmly"],
        "emotional_curve": "curiosity -> inspection -> consideration",
    }


def _apply_emotional_angle(
    behavior_tree: dict[str, Any],
    emotional_angle: dict[str, Any],
) -> dict[str, Any]:
    if not emotional_angle:
        return behavior_tree
    angle = emotional_angle.get("primary_angle")
    safe_label = emotional_angle.get("primary_safe_label")
    driver = emotional_angle.get("driver")
    scene_bias = emotional_angle.get("scene_bias") or []
    enhanced = dict(behavior_tree)
    if driver:
        enhanced["driver"] = f"{behavior_tree['driver']}; emotional driver: {driver}"
    enhanced["emotional_angle"] = angle
    enhanced["emotional_safe_label"] = safe_label
    enhanced["scene_bias"] = scene_bias
    enhanced["emotional_curve"] = f"{behavior_tree.get('emotional_curve', '')}; angle={safe_label or angle}".strip("; ")
    return enhanced


def _hook_psychology(category: str, archetype: str) -> list[str]:
    hooks = {
        "handbag": ["polished-photo skepticism", "scale curiosity", "daily routine relevance"],
        "shoes": ["worn-not-table contrast", "side-profile curiosity", "outfit relevance"],
        "apparel": ["flat-lay skepticism", "worn cut curiosity", "garment movement"],
    }
    return hooks.get(category, ["detail curiosity", "context relevance", "visual proof"])


def _variation_rules(category: str, archetype: str) -> list[str]:
    return [
        "Start with a specific product-evaluation behavior, not a generic product label.",
        "One scene should resolve one buyer objection.",
        "Use visible detail instead of unsupported performance claims.",
        "Keep overlays short and tied to the scene action.",
        f"Primary archetype: {archetype}; category: {category}.",
    ]
