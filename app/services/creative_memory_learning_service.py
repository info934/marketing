from __future__ import annotations

from typing import Any

from app.services import creative_memory_db


def guidance_for_brief(brief: dict[str, Any]) -> dict[str, Any]:
    workspace = _workspace_from_brief(brief)
    normalized_brief = dict(brief or {})
    normalized_brief["workspace"] = workspace
    if workspace == "finance":
        normalized_brief["app_mode"] = "finance_personal_brand"
        normalized_brief["language"] = "cs"
        normalized_brief["market"] = normalized_brief.get("market") or "CZ"
        normalized_brief["product_category"] = normalized_brief.get("product_category") or "finance"

    preview = creative_memory_db.preview_guidance(normalized_brief)
    rag_guidance = preview.get("rag_guidance") or {}
    snapshot = learning_snapshot(workspace=workspace)
    learning_layer = rag_guidance.get("learning_layer") or {}
    winning_patterns = _unique(
        (rag_guidance.get("winning_patterns") or [])
        + (snapshot.get("winning_patterns") or [])
    )[:12]
    avoid_patterns = _unique(
        (rag_guidance.get("avoid_patterns") or [])
        + (snapshot.get("avoid_patterns") or [])
    )[:12]
    confidence = (
        learning_layer.get("confidence")
        or (rag_guidance.get("next_generation_guidance") or {}).get("confidence")
        or (snapshot.get("next_generation_bias") or {}).get("confidence")
        or "low"
    )
    prompt_insert = _prompt_insert(
        workspace=workspace,
        winning_patterns=winning_patterns,
        avoid_patterns=avoid_patterns,
        confidence=confidence,
    )
    return _repair_payload({
        "version": "prompt_learning_guidance_v1",
        "status": "ready",
        "agent": "Prompt Learning Agent",
        "workspace": workspace,
        "app_mode": "finance_personal_brand" if workspace == "finance" else "ecommerce",
        "query": {
            "product_name": preview.get("product_name"),
            "category": preview.get("detected_category"),
            "category_source": preview.get("category_source"),
            "market": preview.get("market"),
            "platform": preview.get("platform"),
            "language": preview.get("language"),
        },
        "source": "creative_memory_rag + learning_snapshot",
        "has_memory": bool(winning_patterns or avoid_patterns),
        "memory_counts": {
            "matching_winner_count": rag_guidance.get("matching_winner_count", 0),
            "matching_rejected_count": rag_guidance.get("matching_rejected_count", 0),
            "knowledge_item_count": rag_guidance.get("knowledge_item_count", 0),
        },
        "winning_patterns": winning_patterns,
        "avoid_patterns": avoid_patterns,
        "prompt_insert": prompt_insert,
        "prompt_priority_rule": (
            "Use these patterns as directional guidance only. Product facts, avatar identity, "
            "provider limits, language rules, and compliance are higher priority."
        ),
        "rag_guidance": rag_guidance,
        "learning_snapshot": snapshot,
    })


def learning_snapshot(workspace: str = "") -> dict[str, Any]:
    intelligence = creative_memory_db.intelligence_summary(workspace=workspace)
    extractor = intelligence.get("winning_pattern_extractor") or {}
    learner = intelligence.get("prompt_learning_agent") or {}
    return _repair_payload({
        "version": "creative_memory_learning_service_v1",
        "workspace": intelligence.get("workspace") or workspace or "all",
        "status": "active",
        "counts": intelligence.get("counts") or {},
        "learning_loop": intelligence.get("learning_loop") or {},
        "winning_patterns": _unique(
            (extractor.get("performance_patterns") or [])
            + (extractor.get("approved_patterns") or [])
            + (intelligence.get("best_hooks") or [])
        )[:12],
        "avoid_patterns": _unique(
            (extractor.get("rejected_patterns") or [])
            + (intelligence.get("rejected_patterns") or [])
        )[:12],
        "next_generation_bias": learner.get("next_generation_bias") or {},
        "recommendation": learner.get("recommendation")
        or "Add ratings and performance records to make future prompt guidance more precise.",
        "rule": "Use learning as directional prompt bias only; product facts, avatar identity, and compliance rules remain higher priority.",
    })


def _unique(values: list[Any]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = _repair_text(str(value or "").strip())
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _workspace_from_brief(brief: dict[str, Any]) -> str:
    raw = str(
        (brief or {}).get("workspace")
        or (brief or {}).get("session_workspace")
        or (brief or {}).get("app_mode")
        or ""
    ).strip().lower()
    if raw in {"finance", "finance_personal_brand"}:
        return "finance"
    return "ecommerce"


def _prompt_insert(
    *,
    workspace: str,
    winning_patterns: list[str],
    avoid_patterns: list[str],
    confidence: str,
) -> str:
    if not winning_patterns and not avoid_patterns:
        if workspace == "finance":
            return (
                "No finance memory yet. Use a Czech podcast-studio personal-brand structure, "
                "clear educational framing, modern infographics, and compliance-safe wording."
            )
        return (
            "No ecommerce memory yet. Use category presets, diversify human context and shot type, "
            "keep product fidelity strict, and store rating/performance after review."
        )
    parts = []
    if winning_patterns:
        parts.append("Prefer: " + ", ".join(winning_patterns[:6]))
    if avoid_patterns:
        parts.append("Avoid: " + ", ".join(avoid_patterns[:6]))
    parts.append(f"Memory confidence: {confidence}")
    return ". ".join(parts)


def _repair_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _repair_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_payload(item) for item in value]
    if isinstance(value, str):
        return _repair_text(value)
    return value


def _repair_text(value: str) -> str:
    text = str(value or "")
    markers = ["\u00c3", "\u00c4", "\u00c5", "\u0139", "\u008d", "\u0099", "\ufffd"]
    if not any(marker in text for marker in markers):
        return text
    for encoding in ("latin1", "cp1250"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except Exception:
            continue
        if _mojibake_score(repaired) < _mojibake_score(text):
            return repaired
    return text


def _mojibake_score(value: str) -> int:
    markers = ["\u00c3", "\u00c4", "\u00c5", "\u0139", "\u008d", "\u0099", "\ufffd"]
    return sum(value.count(marker) for marker in markers)
