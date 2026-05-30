from __future__ import annotations

import re
from typing import Any


VERSION = "ad_angle_selector_v1"

SLOT_ROLE_PRIORS = {
    "C1": {"Pain": 4, "Desire": 3, "Proof": 2, "Identity": 3, "Contrarian": 4, "Urgency": 5},
    "C2": {"Pain": 1, "Desire": 5, "Proof": 3, "Identity": 3, "Contrarian": 2, "Urgency": 2},
    "C3": {"Pain": 2, "Desire": 3, "Proof": 3, "Identity": 5, "Contrarian": 2, "Urgency": 1},
    "C4": {"Pain": 3, "Desire": 1, "Proof": 5, "Identity": 2, "Contrarian": 3, "Urgency": 2},
    "C5": {"Pain": 5, "Desire": 2, "Proof": 4, "Identity": 3, "Contrarian": 5, "Urgency": 4},
}

SLOT_ROLE_LABELS = {
    "C1": "UGC video hook needs the strongest scroll-stop angle.",
    "C2": "Product hero needs desire and immediate product appeal.",
    "C3": "Use context needs identity and everyday fit.",
    "C4": "Detail proof needs visible proof and inspection logic.",
    "C5": "Buying guide carousel needs objection, contrast, proof, and decision support.",
}

FAMILY_KEYWORDS = {
    "Pain": ["pain", "doubt", "problem", "missing", "chybi", "nejistota", "detail missing", "not enough"],
    "Desire": ["desire", "upgrade", "everyday", "aspiration", "want", "fits", "zapadne", "routine"],
    "Proof": ["proof", "detail", "close-up", "texture", "stitching", "scale", "check", "macro", "material"],
    "Identity": ["identity", "careful", "people who", "for people", "vyber", "style", "practical", "picky"],
    "Contrarian": ["contrarian", "less hype", "hype", "hero photo", "not another", "mene hype", "skip"],
    "Urgency": ["urgency", "before you scroll", "10-second", "quick", "scroll", "nez scrollujes", "first seconds"],
}

LEGACY_ANGLE_FAMILY = {
    "UGC": "Urgency",
    "PRODUCT_HERO": "Desire",
    "USE_CONTEXT": "Identity",
    "DETAIL_PROOF": "Proof",
    "BUYING_GUIDE": "Contrarian",
    "PAIN": "Pain",
    "IDENTITY": "Identity",
    "PROOF": "Proof",
    "DESIRE": "Desire",
    "CONTRARIAN": "Contrarian",
    "URGENCY": "Urgency",
}


def select(
    *,
    angle_multiplier: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ugc = ugc_strategy or {}
    config = settings or {}
    angles = [
        item for item in (angle_multiplier.get("angles") or [])
        if isinstance(item, dict) and item.get("hook") and item.get("angle_family")
    ]
    performance_insights = ugc.get("performance_insights") or config.get("performance_insights") or {}
    creative_memory = (
        ugc.get("creative_memory_rag")
        or performance_insights.get("creative_memory_rag")
        or config.get("creative_memory_guidance")
        or {}
    )
    competitor_strategy = ugc.get("competitor_strategy") or config.get("competitor_strategy") or {}
    memory_signals = _memory_signals(performance_insights, creative_memory, competitor_strategy)
    used_angle_ids: set[str] = set()
    slot_selection = {}
    for slot in ["C1", "C2", "C3", "C4", "C5"]:
        selected = _select_for_slot(
            slot=slot,
            angles=angles,
            used_angle_ids=used_angle_ids,
            memory_signals=memory_signals,
        )
        if selected:
            used_angle_ids.add(str(selected.get("angle_id") or ""))
            slot_selection[slot] = selected

    return {
        "version": VERSION,
        "status": "ready" if slot_selection else "empty",
        "selection_strategy": "role_prior_plus_memory_scoring",
        "product_category": product_analysis.get("likely_product_category"),
        "platform": ugc.get("platform") or config.get("platform"),
        "market": ugc.get("market") or config.get("market"),
        "memory_confidence": memory_signals["confidence"],
        "memory_used": memory_signals["has_memory"],
        "memory_summary": {
            "winning_patterns": memory_signals["winning_patterns"][:8],
            "avoid_patterns": memory_signals["avoid_patterns"][:8],
            "winner_count": memory_signals["winner_count"],
            "rejected_count": memory_signals["rejected_count"],
        },
        "competitor_bias_used": memory_signals["competitor_bias_used"],
        "competitor_bias_summary": {
            "status": memory_signals["competitor_status"],
            "patterns": memory_signals["competitor_patterns"][:8],
            "family_bias": memory_signals["competitor_family_bias"],
            "rule": "Competitor strategy is a weak run-level bias, not performance evidence.",
        },
        "slot_selection": slot_selection,
        "rules": [
            "If memory is weak, choose by slot role prior.",
            "If new memory has winners, boost matching family, hook, visual direction, and validated angle signals.",
            "If memory has rejects, penalize matching family, hook, and avoid-pattern text.",
            "If competitor strategy is supplied, use it only as a weak pattern-level bias for this generation run.",
            "Do not override product facts, language, compliance, or product/avatar fidelity.",
        ],
    }


def selected_for(selector: dict[str, Any], set_id: str, fallback_family: str | None = None) -> dict[str, Any]:
    selection = ((selector or {}).get("slot_selection") or {}).get(set_id) or {}
    if selection:
        return selection
    return {"selected_family": fallback_family or "", "selection_reason": "Fallback family role prior; selector unavailable."}


def _select_for_slot(
    *,
    slot: str,
    angles: list[dict[str, Any]],
    used_angle_ids: set[str],
    memory_signals: dict[str, Any],
) -> dict[str, Any]:
    scored = [_score_angle(slot, angle, memory_signals) for angle in angles]
    scored.sort(key=lambda item: (item["score"], item["breakdown"]["memory_match_score"]), reverse=True)
    selected = None
    for item in scored:
        angle_id = str(item.get("angle_id") or "")
        if angle_id and angle_id not in used_angle_ids:
            selected = item
            break
    selected = selected or (scored[0] if scored else {})
    if not selected:
        return {}
    return {
        "set_id": slot,
        "selected_angle_id": selected["angle_id"],
        "selected_family": selected["family"],
        "selected_angle": selected["angle"],
        "selected_hook": selected["hook"],
        "visual_direction": selected["visual_direction"],
        "creative_test_hypothesis": selected["creative_test_hypothesis"],
        "score": selected["score"],
        "score_breakdown": selected["breakdown"],
        "selection_reason": _selection_reason(slot, selected, memory_signals),
        "top_candidates": [
            {
                "angle_id": item["angle_id"],
                "family": item["family"],
                "hook": item["hook"],
                "score": item["score"],
            }
            for item in scored[:4]
        ],
    }


def _score_angle(slot: str, angle: dict[str, Any], memory_signals: dict[str, Any]) -> dict[str, Any]:
    family = str(angle.get("angle_family") or "")
    text = _angle_text(angle)
    role_score = SLOT_ROLE_PRIORS.get(slot, {}).get(family, 0) * 10
    winner_matches = _pattern_matches(text, memory_signals["winning_patterns"])
    avoid_matches = _pattern_matches(text, memory_signals["avoid_patterns"])
    family_winner_score = memory_signals["family_winners"].get(family, 0) * 12
    family_avoid_score = memory_signals["family_avoids"].get(family, 0) * 14
    seed_score = _seed_score(text, family, memory_signals)
    competitor_match_score = _competitor_score(text, family, memory_signals)
    memory_match_score = winner_matches * 8 + family_winner_score + seed_score
    memory_penalty = avoid_matches * 10 + family_avoid_score
    confidence_multiplier = {"none": 0.0, "low": 0.45, "medium": 0.75, "high": 1.0}.get(
        memory_signals["confidence"],
        0.45,
    )
    total = (
        role_score
        + round(memory_match_score * confidence_multiplier)
        + competitor_match_score
        - round(memory_penalty * max(0.55, confidence_multiplier))
    )
    return {
        "angle_id": angle.get("id"),
        "family": family,
        "angle": angle.get("angle"),
        "hook": angle.get("hook"),
        "visual_direction": angle.get("visual_direction"),
        "creative_test_hypothesis": angle.get("creative_test_hypothesis"),
        "score": total,
        "breakdown": {
            "role_prior_score": role_score,
            "memory_match_score": memory_match_score,
            "memory_penalty": memory_penalty,
            "winner_text_matches": winner_matches,
            "avoid_text_matches": avoid_matches,
            "family_winner_score": family_winner_score,
            "family_avoid_score": family_avoid_score,
            "seed_score": seed_score,
            "competitor_bias_score": competitor_match_score,
            "confidence_multiplier": confidence_multiplier,
        },
    }


def _memory_signals(
    performance_insights: dict[str, Any],
    creative_memory: dict[str, Any],
    competitor_strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    learning_layer = creative_memory.get("learning_layer") or {}
    competitor = competitor_strategy or {}
    selector_bias = competitor.get("selector_bias") or {}
    competitor_patterns = _unique(
        (selector_bias.get("hook_patterns") or [])
        + (selector_bias.get("visual_patterns") or [])
        + (selector_bias.get("cta_patterns") or [])
    )
    competitor_family_bias = {
        family: int(score or 0)
        for family, score in (selector_bias.get("families") or {}).items()
        if family in SLOT_ROLE_PRIORS["C1"] and int(score or 0) > 0
    }
    winning_patterns = _unique(
        (creative_memory.get("winning_patterns") or [])
        + (performance_insights.get("winning_hooks") or [])
        + (performance_insights.get("winning_shot_types") or [])
        + (performance_insights.get("winning_overlays") or [])
    )
    avoid_patterns = _unique(
        (creative_memory.get("avoid_patterns") or [])
        + (performance_insights.get("avoid_patterns") or [])
    )
    winner_rows = learning_layer.get("best_historical_creatives") or []
    rejected_rows = learning_layer.get("worst_historical_creatives") or []
    family_winners = _family_counts(winning_patterns, winner_rows)
    family_avoids = _family_counts(avoid_patterns, rejected_rows)
    confidence = str(learning_layer.get("confidence") or "").lower() or "none"
    if confidence not in {"none", "low", "medium", "high"}:
        confidence = "low"
    winner_count = int(learning_layer.get("winner_count") or performance_insights.get("winner_count") or 0)
    rejected_count = int(learning_layer.get("rejected_count") or 0)
    if confidence == "none" and (winning_patterns or avoid_patterns or winner_count or rejected_count):
        confidence = "low"
    seed = performance_insights.get("seed_insights") or {}
    return {
        "has_memory": bool(winning_patterns or avoid_patterns or winner_count or rejected_count),
        "confidence": confidence,
        "winner_count": winner_count,
        "rejected_count": rejected_count,
        "winning_patterns": winning_patterns,
        "avoid_patterns": avoid_patterns,
        "family_winners": family_winners,
        "family_avoids": family_avoids,
        "seed_hooks": _unique(seed.get("hook_patterns") or []),
        "seed_shots": _unique(seed.get("shot_types") or []),
        "seed_overlays": _unique(seed.get("overlay_patterns") or []),
        "competitor_bias_used": bool(competitor.get("status") == "ready" and (competitor_patterns or competitor_family_bias)),
        "competitor_status": competitor.get("status") or "disabled",
        "competitor_patterns": competitor_patterns,
        "competitor_family_bias": competitor_family_bias,
    }


def _family_counts(patterns: list[str], rows: list[Any]) -> dict[str, int]:
    counts = {family: 0 for family in SLOT_ROLE_PRIORS["C1"]}
    for pattern in patterns:
        family = _family_from_text(pattern)
        if family:
            counts[family] = counts.get(family, 0) + 1
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        family = _family_from_text(row.get("angle"))
        if family:
            counts[family] = counts.get(family, 0) + 2
        for tag in row.get("tags") or []:
            family = _family_from_text(tag)
            if family:
                counts[family] = counts.get(family, 0) + 1
    return counts


def _family_from_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    upper = text.upper().replace("ANGLE:", "").strip()
    if upper in LEGACY_ANGLE_FAMILY:
        return LEGACY_ANGLE_FAMILY[upper]
    lowered = text.lower()
    for family, keywords in FAMILY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return family
    return ""


def _seed_score(text: str, family: str, memory_signals: dict[str, Any]) -> int:
    seed_patterns = memory_signals["seed_hooks"] + memory_signals["seed_shots"] + memory_signals["seed_overlays"]
    score = _pattern_matches(text, seed_patterns) * 3
    if family == "Proof" and _pattern_matches(text, memory_signals["seed_shots"]):
        score += 5
    if family == "Desire" and _pattern_matches(text, memory_signals["seed_overlays"]):
        score += 3
    return score


def _competitor_score(text: str, family: str, memory_signals: dict[str, Any]) -> int:
    if not memory_signals.get("competitor_bias_used"):
        return 0
    pattern_score = min(3, _pattern_matches(text, memory_signals["competitor_patterns"])) * 3
    family_score = min(5, int((memory_signals.get("competitor_family_bias") or {}).get(family, 0))) * 2
    return min(18, pattern_score + family_score)


def _pattern_matches(text: str, patterns: list[Any]) -> int:
    tokens = set(_tokens(text))
    count = 0
    for pattern in patterns:
        pattern_text = str(pattern or "").lower()
        if not pattern_text:
            continue
        if pattern_text in text:
            count += 1
            continue
        pattern_tokens = set(_tokens(pattern_text))
        if pattern_tokens and len(tokens & pattern_tokens) >= min(2, len(pattern_tokens)):
            count += 1
    return count


def _angle_text(angle: dict[str, Any]) -> str:
    return " ".join(
        str(angle.get(key) or "")
        for key in ["id", "angle_family", "angle", "hook", "motivation", "creative_test_hypothesis", "visual_direction", "variation_rule"]
    ).lower()


def _tokens(value: Any) -> list[str]:
    return [
        token
        for token in re.split(r"[^a-z0-9]+", str(value or "").lower())
        if len(token) >= 3
    ]


def _unique(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _selection_reason(slot: str, selected: dict[str, Any], memory_signals: dict[str, Any]) -> str:
    family = selected.get("family")
    role = SLOT_ROLE_LABELS.get(slot, "Slot role prior selected this angle.")
    breakdown = selected.get("breakdown") or {}
    if memory_signals["has_memory"]:
        return (
            f"{role} Selected {family} with score {selected.get('score')} because role prior="
            f"{breakdown.get('role_prior_score')}, memory match={breakdown.get('memory_match_score')}, "
            f"competitor bias={breakdown.get('competitor_bias_score')}, memory penalty={breakdown.get('memory_penalty')}, "
            f"confidence={memory_signals['confidence']}."
        )
    if memory_signals.get("competitor_bias_used"):
        return (
            f"{role} Selected {family} with score {selected.get('score')} from slot role priors plus weak "
            f"competitor strategy bias={breakdown.get('competitor_bias_score')}; no reliable winner/reject memory exists yet."
        )
    return (
        f"{role} Selected {family} with score {selected.get('score')} from slot role priors because no reliable "
        "winner/reject memory exists yet."
    )
