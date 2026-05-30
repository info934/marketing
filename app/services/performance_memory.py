from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app import config


MEMORY_PATH = config.BASE_DIR / "data" / "performance_memory.json"
MEMORY_VERSION = "performance_memory_v2_clean_start"

DEFAULT_MEMORY = {
    "version": MEMORY_VERSION,
    "records": [],
    "generated_candidates": [],
    "seed_insights": {},
    "reset_reason": "Clean start for the new creative marketing agent portal. Old workflow learning data is ignored.",
    "reset_at": "2026-05-30",
    "legacy_seed_priors_enabled": False,
    "memory_policy": {
        "mode": "new_agent_data_only",
        "legacy_workflow_data": "ignored",
        "rule": "Use only records, ratings, and performance imported after the clean portal reset.",
    },
}


def load_memory(path: Path | None = None) -> dict[str, Any]:
    path = path or MEMORY_PATH
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_MEMORY))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return json.loads(json.dumps(DEFAULT_MEMORY))
        payload.setdefault("version", MEMORY_VERSION)
        payload.setdefault("records", [])
        payload.setdefault("generated_candidates", [])
        payload["seed_insights"] = {}
        payload["legacy_seed_priors_enabled"] = False
        payload.setdefault("memory_policy", DEFAULT_MEMORY["memory_policy"])
        return payload
    except Exception:
        return json.loads(json.dumps(DEFAULT_MEMORY))


def save_memory(memory: dict[str, Any], path: Path | None = None) -> None:
    path = path or MEMORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


def select_insights(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    actual_path = path or MEMORY_PATH
    memory = load_memory(actual_path)
    category = str(product_analysis.get("likely_product_category") or "unknown")
    platform = str(settings.get("platform") or "").lower()
    market = str(settings.get("market") or "").upper()
    seed = (memory.get("seed_insights") or {}).get(category, {})
    records = [
        record
        for record in memory.get("records") or []
        if _matches(record, category=category, platform=platform, market=market)
    ]
    winners = [record for record in records if _is_winner(record)]
    return {
        "agent": "Performance Memory Layer",
        "status": "active",
        "memory_path": str(actual_path),
        "category": category,
        "platform": platform,
        "market": market,
        "matching_record_count": len(records),
        "winner_count": len(winners),
        "seed_insights": seed,
        "legacy_seed_priors_enabled": False,
        "memory_policy": memory.get("memory_policy") or DEFAULT_MEMORY["memory_policy"],
        "winning_hooks": _top_values(winners, "hook"),
        "winning_shot_types": _top_values(winners, "shot_type"),
        "winning_overlays": _top_values(winners, "overlay_text"),
        "metric_bias": _metric_bias(winners),
        "learning_rule": (
            "Use only validated records from the new agent portal. If no records exist, diversify without legacy memory priors."
        ),
    }


def add_record(record: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    memory = load_memory(path)
    payload = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "creative_id": record.get("creative_id"),
        "product_name": record.get("product_name"),
        "product_category": record.get("product_category"),
        "platform": record.get("platform"),
        "market": record.get("market"),
        "hook": record.get("hook"),
        "shot_type": record.get("shot_type"),
        "overlay_text": record.get("overlay_text"),
        "metrics": {
            "ctr": _number_or_none(record.get("ctr")),
            "cpc": _number_or_none(record.get("cpc")),
            "cpa": _number_or_none(record.get("cpa")),
            "engagement": _number_or_none(record.get("engagement")),
        },
        "outcome": record.get("outcome") or "unknown",
        "notes": record.get("notes") or "",
    }
    memory.setdefault("records", []).append(payload)
    save_memory(memory, path)
    return payload


def record_generated_candidates(final_output: dict[str, Any], path: Path | None = None) -> None:
    memory = load_memory(path)
    generated = memory.setdefault("generated_candidates", [])
    product = final_output.get("product_analysis") or {}
    ugc = final_output.get("ugc_strategy") or {}
    ads = final_output.get("ads_creative_set") or {}
    generated.append(
        {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "session_folder": (final_output.get("user_input") or {}).get("session_folder_name"),
            "product_name": product.get("product_name"),
            "product_category": product.get("likely_product_category"),
            "platform": ugc.get("platform"),
            "market": ugc.get("market"),
            "ugc_hook": ugc.get("hook"),
            "primary_archetype": (ugc.get("audience_research") or {}).get("primary_archetype"),
            "creative_driver": (ugc.get("creative_psychology") or {}).get("primary_driver"),
            "static_creatives": [
                {
                    "creative_id": item.get("creative_id"),
                    "set_id": item.get("set_id"),
                    "angle": item.get("angle"),
                    "overlay_text": item.get("overlay_text"),
                }
                for item in ads.get("static_image_ads") or []
            ],
        }
    )
    del generated[:-100]
    save_memory(memory, path)


def _matches(record: dict[str, Any], *, category: str, platform: str, market: str) -> bool:
    record_category = str(record.get("product_category") or "").lower()
    record_platform = str(record.get("platform") or "").lower()
    record_market = str(record.get("market") or "").upper()
    return (
        (not record_category or record_category == category.lower())
        and (not record_platform or record_platform == platform)
        and (not record_market or record_market == market)
    )


def _is_winner(record: dict[str, Any]) -> bool:
    outcome = str(record.get("outcome") or "").lower()
    metrics = record.get("metrics") or {}
    ctr = _number_or_none(metrics.get("ctr"))
    engagement = _number_or_none(metrics.get("engagement"))
    return outcome in {"winner", "winning", "win"} or (ctr is not None and ctr >= 1.5) or (
        engagement is not None and engagement >= 3
    )


def _top_values(records: list[dict[str, Any]], key: str, limit: int = 5) -> list[str]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key) or "").strip()
        if value:
            counts[value] = counts.get(value, 0) + 1
    return [
        value
        for value, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _metric_bias(winners: list[dict[str, Any]]) -> dict[str, Any]:
    if not winners:
        return {
            "source": "clean_start",
            "instruction": "No validated new-version winners yet; diversify hooks and shots without legacy workflow priors.",
        }
    return {
        "source": "winning_records",
        "instruction": "Prefer hooks, shot types, and overlays seen in winning records before exploring new variants.",
        "sample_size": len(winners),
    }


def _number_or_none(value: Any) -> float | None:
    try:
        if value in {"", None}:
            return None
        return float(value)
    except Exception:
        return None
