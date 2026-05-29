from __future__ import annotations

from typing import Any


def build_session_cost_summary(
    content_prompt_package: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
    *,
    product_analysis: dict[str, Any] | None = None,
    input_data: dict[str, Any] | None = None,
    self_critique: dict[str, Any] | None = None,
) -> dict[str, Any]:
    components = [
        _product_understanding_component(product_analysis or {}),
        _finance_script_component((input_data or {}).get("finance_script_agent") or {}),
        _prompt_component(content_prompt_package.get("prompt_generation") or {}),
        _static_prompt_component(static_image_generation.get("static_prompt_generation") or {}),
        _image_component(static_image_generation),
        _vision_qa_component(static_image_generation),
        _video_component(video_generation),
        _self_critique_component(self_critique or {}),
    ]
    components = [component for component in components if component]
    known_costs = [component["cost"] for component in components if component["cost"] is not None]
    total_known = round(sum(known_costs), 10) if known_costs else 0.0
    unknown_components = [
        component["component"]
        for component in components
        if component.get("billable_attempted") and component["cost"] is None
    ]
    request_count = sum(int(component.get("request_count") or 0) for component in components)
    known_request_count = sum(
        int(component.get("request_count") or 0)
        for component in components
        if component.get("cost") is not None
    )
    return {
        "version": "openrouter_cost_summary_v2",
        "status": "complete" if not unknown_components else "partial" if known_costs else "unknown",
        "currency": "OpenRouter-reported cost, usually USD",
        "billing_unit": "OpenRouter cost as returned by usage.cost, usage.total_cost, or /generation total_cost",
        "total_known_cost": total_known,
        "total_known_cost_display": _format_cost(total_known),
        "total_known_cost_usd_display": _format_usd(total_known),
        "unknown_cost_components": unknown_components,
        "request_count": request_count,
        "known_request_count": known_request_count,
        "unknown_request_count": max(0, request_count - known_request_count),
        "component_count": len(components),
        "components": components,
        "by_group": _group_totals(components),
        "note": "This uses OpenRouter-reported usage/cost data only. If a provider does not return cost metadata, that component is marked unknown instead of estimated.",
    }


def build_finance_scene_preview_cost_summary(
    *,
    finance_script_agent: dict[str, Any],
    scene_image_generation: dict[str, Any],
) -> dict[str, Any]:
    components = [
        _finance_script_component(finance_script_agent),
        _single_image_component(scene_image_generation, component="Finance scene concept image"),
    ]
    known_costs = [component["cost"] for component in components if component["cost"] is not None]
    total_known = round(sum(known_costs), 10) if known_costs else 0.0
    unknown_components = [
        component["component"]
        for component in components
        if component.get("billable_attempted") and component["cost"] is None
    ]
    return {
        "version": "openrouter_cost_summary_v2",
        "status": "complete" if not unknown_components else "partial" if known_costs else "unknown",
        "currency": "OpenRouter-reported cost, usually USD",
        "billing_unit": "OpenRouter cost as returned by usage.cost or usage.total_cost",
        "total_known_cost": total_known,
        "total_known_cost_display": _format_cost(total_known),
        "total_known_cost_usd_display": _format_usd(total_known),
        "unknown_cost_components": unknown_components,
        "request_count": sum(int(component.get("request_count") or 0) for component in components),
        "known_request_count": sum(
            int(component.get("request_count") or 0)
            for component in components
            if component.get("cost") is not None
        ),
        "component_count": len(components),
        "components": components,
        "by_group": _group_totals(components),
        "note": "Finance scene preview is a separate OpenRouter cost event before the final Seedance video run.",
    }


def _product_understanding_component(product_analysis: dict[str, Any]) -> dict[str, Any]:
    understanding = product_analysis.get("automatic_product_understanding") or {}
    refinement = understanding.get("ai_refinement") or {}
    if not refinement:
        return _skipped_component(
            "Product understanding",
            group="planning",
            status="skipped",
            model=None,
            reason="No AI product understanding refinement was recorded.",
        )
    return _usage_component(
        component="Product understanding",
        group="planning",
        status=refinement.get("status", "unknown"),
        model=refinement.get("model"),
        usage=refinement.get("usage"),
        generation_id=refinement.get("generation_id"),
        billable_statuses={"completed"},
    )


def _finance_script_component(finance_script_agent: dict[str, Any]) -> dict[str, Any]:
    if not finance_script_agent:
        return _skipped_component(
            "Finance script agent",
            group="planning",
            status="skipped",
            model=None,
            reason="Not a finance personal brand run.",
        )
    return _usage_component(
        component="Finance script agent",
        group="planning",
        status=finance_script_agent.get("status", "unknown"),
        model=finance_script_agent.get("model"),
        usage=finance_script_agent.get("usage"),
        generation_id=finance_script_agent.get("generation_id"),
        billable_statuses={"ai_refined", "completed"},
    )


def _prompt_component(prompt_generation: dict[str, Any]) -> dict[str, Any]:
    return _usage_component(
        component="Prompt generation",
        group="prompting",
        status=prompt_generation.get("status", "unknown"),
        model=prompt_generation.get("model"),
        usage=prompt_generation.get("usage") if isinstance(prompt_generation, dict) else None,
        generation_id=prompt_generation.get("generation_id"),
        billable_statuses={"completed"},
    )


def _static_prompt_component(static_prompt_generation: dict[str, Any]) -> dict[str, Any]:
    if not static_prompt_generation:
        static_prompt_generation = {"status": "skipped"}
    return _usage_component(
        component="Static creative prompt generation",
        group="prompting",
        status=static_prompt_generation.get("status", "unknown"),
        model=static_prompt_generation.get("model"),
        usage=static_prompt_generation.get("usage") if isinstance(static_prompt_generation, dict) else None,
        generation_id=static_prompt_generation.get("generation_id"),
        billable_statuses={"completed", "completed_with_fallback"},
    )


def _image_component(static_image_generation: dict[str, Any]) -> dict[str, Any]:
    usage_records = static_image_generation.get("usage_records") or []
    costs = [_usage_cost(record.get("usage")) for record in usage_records if isinstance(record, dict)]
    known_costs = [cost for cost in costs if cost is not None]
    cost = round(sum(known_costs), 10) if known_costs else None
    request_count = len(usage_records)
    return {
        "component": "Static ad images",
        "group": "image_generation",
        "status": static_image_generation.get("image_generation_status", "unknown"),
        "model": static_image_generation.get("model"),
        "request_count": request_count,
        "generated_assets": static_image_generation.get("generated_count", len(static_image_generation.get("image_assets") or [])),
        "cost": cost,
        "cost_display": _format_cost(cost),
        "cost_usd_display": _format_usd(cost),
        "known_usage_records": len(known_costs),
        "usage_records": usage_records,
        "cost_source": "sum(usage_records[].usage.cost)" if cost is not None else None,
        "billable_attempted": request_count > 0,
    }


def _single_image_component(image_generation: dict[str, Any], *, component: str) -> dict[str, Any]:
    usage = image_generation.get("usage") if isinstance(image_generation, dict) else None
    return _usage_component(
        component=component,
        group="image_generation",
        status=image_generation.get("image_generation_status", "unknown"),
        model=image_generation.get("model"),
        usage=usage,
        generation_id=image_generation.get("generation_id"),
        billable_statuses={"completed"},
        generated_assets=len(image_generation.get("image_assets") or []),
    )


def _vision_qa_component(static_image_generation: dict[str, Any]) -> dict[str, Any]:
    checks = static_image_generation.get("vision_quality_checks") or []
    usage_records = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        result = check.get("result") or {}
        usage_records.append(
            {
                "creative_id": check.get("creative_id"),
                "attempt": check.get("attempt"),
                "model": result.get("model"),
                "usage": result.get("usage"),
                "status": result.get("status"),
            }
        )
    costs = [_usage_cost(record.get("usage")) for record in usage_records]
    known_costs = [cost for cost in costs if cost is not None]
    cost = round(sum(known_costs), 10) if known_costs else None
    return {
        "component": "Vision QA",
        "group": "quality",
        "status": static_image_generation.get("vision_quality_status", "skipped"),
        "model": static_image_generation.get("vision_model"),
        "request_count": len(usage_records),
        "cost": cost,
        "cost_display": _format_cost(cost),
        "cost_usd_display": _format_usd(cost),
        "known_usage_records": len(known_costs),
        "usage_records": usage_records,
        "cost_source": "sum(vision_quality_checks[].result.usage.cost)" if cost is not None else None,
        "billable_attempted": bool(usage_records),
    }


def _video_component(video_generation: dict[str, Any]) -> dict[str, Any]:
    generation_metadata = video_generation.get("generation_metadata") or {}
    usage = video_generation.get("usage")
    cost = _generation_cost(generation_metadata)
    cost_source = "generation_metadata.total_cost" if cost is not None else None
    if cost is None:
        cost = _usage_cost(usage)
        cost_source = "usage.cost" if cost is not None else None
    if cost is None:
        cost = _usage_cost((video_generation.get("raw_response") or {}).get("usage"))
        cost_source = "raw_response.usage.cost" if cost is not None else None
    request_count = 1 if video_generation.get("job_id") else 0
    return {
        "component": "Seedance video",
        "group": "video_generation",
        "status": video_generation.get("video_generation_status", "unknown"),
        "model": (video_generation.get("submitted_payload") or {}).get("model"),
        "request_count": request_count,
        "cost": cost,
        "cost_display": _format_cost(cost),
        "cost_usd_display": _format_usd(cost),
        "job_id": video_generation.get("job_id"),
        "generation_id": generation_metadata.get("id") or (video_generation.get("raw_response") or {}).get("generation_id"),
        "usage": usage,
        "generation_metadata": generation_metadata or None,
        "cost_source": cost_source,
        "billable_attempted": request_count > 0,
    }


def _self_critique_component(self_critique: dict[str, Any]) -> dict[str, Any]:
    ai_critique = self_critique.get("ai_critique") or {}
    return _usage_component(
        component="AI self critique",
        group="quality",
        status=ai_critique.get("status", "skipped"),
        model=ai_critique.get("model"),
        usage=ai_critique.get("usage"),
        generation_id=ai_critique.get("generation_id"),
        billable_statuses={"completed"},
    )


def _usage_component(
    *,
    component: str,
    group: str,
    status: Any,
    model: Any,
    usage: Any,
    generation_id: Any = None,
    billable_statuses: set[str] | None = None,
    generated_assets: int | None = None,
) -> dict[str, Any]:
    status_text = str(status or "unknown")
    cost = _usage_cost(usage)
    billable_statuses = billable_statuses or {"completed"}
    request_count = 1 if status_text in billable_statuses else 0
    payload = {
        "component": component,
        "group": group,
        "status": status_text,
        "model": model,
        "request_count": request_count,
        "cost": cost,
        "cost_display": _format_cost(cost),
        "cost_usd_display": _format_usd(cost),
        "usage": usage,
        "tokens": _usage_tokens(usage),
        "generation_id": generation_id,
        "cost_source": _usage_cost_source(usage) if cost is not None else None,
        "billable_attempted": request_count > 0,
    }
    if generated_assets is not None:
        payload["generated_assets"] = generated_assets
    return payload


def _skipped_component(
    component: str,
    *,
    group: str,
    status: str,
    model: Any,
    reason: str,
) -> dict[str, Any]:
    return {
        "component": component,
        "group": group,
        "status": status,
        "model": model,
        "request_count": 0,
        "cost": None,
        "cost_display": "unknown",
        "cost_usd_display": "unknown",
        "usage": None,
        "tokens": {},
        "reason": reason,
        "cost_source": None,
        "billable_attempted": False,
    }


def _usage_cost(usage: Any) -> float | None:
    if not isinstance(usage, dict):
        return None
    for key in ["cost", "total_cost", "openrouter_cost", "provider_cost"]:
        number = _number(usage.get(key))
        if number is not None:
            return number
    nested = usage.get("cost_details") or usage.get("billing")
    if isinstance(nested, dict):
        for key in ["cost", "total_cost", "total"]:
            number = _number(nested.get(key))
            if number is not None:
                return number
    return None


def _usage_cost_source(usage: Any) -> str | None:
    if not isinstance(usage, dict):
        return None
    for key in ["cost", "total_cost", "openrouter_cost", "provider_cost"]:
        if _number(usage.get(key)) is not None:
            return f"usage.{key}"
    nested = usage.get("cost_details") or usage.get("billing")
    if isinstance(nested, dict):
        for key in ["cost", "total_cost", "total"]:
            if _number(nested.get(key)) is not None:
                return f"usage.cost_details.{key}"
    return None


def _generation_cost(generation_metadata: Any) -> float | None:
    if not isinstance(generation_metadata, dict):
        return None
    number = _number(generation_metadata.get("total_cost"))
    if number is not None:
        return number
    usage = generation_metadata.get("usage")
    if isinstance(usage, dict):
        return _usage_cost(usage)
    return _number(usage)


def _usage_tokens(usage: Any) -> dict[str, int]:
    if not isinstance(usage, dict):
        return {}
    tokens = {}
    for source_key, target_key in [
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
        ("total_tokens", "total_tokens"),
        ("input_tokens", "input_tokens"),
        ("output_tokens", "output_tokens"),
    ]:
        value = _int_number(usage.get(source_key))
        if value is not None:
            tokens[target_key] = value
    return tokens


def _group_totals(components: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for component in components:
        group = str(component.get("group") or "other")
        item = groups.setdefault(
            group,
            {
                "known_cost": 0.0,
                "known_cost_display": "0",
                "known_cost_usd_display": "$0",
                "request_count": 0,
                "unknown_components": [],
            },
        )
        item["request_count"] += int(component.get("request_count") or 0)
        if component.get("cost") is None:
            if component.get("billable_attempted"):
                item["unknown_components"].append(component.get("component"))
            continue
        item["known_cost"] = round(float(item["known_cost"]) + float(component["cost"]), 10)
    for item in groups.values():
        item["known_cost_display"] = _format_cost(item["known_cost"])
        item["known_cost_usd_display"] = _format_usd(item["known_cost"])
    return groups


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace("$", "")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_number(value: Any) -> int | None:
    number = _number(value)
    if number is None:
        return None
    return int(number)


def _format_cost(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value == 0:
        return "0"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _format_usd(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"${value:.6f}".rstrip("0").rstrip(".")
