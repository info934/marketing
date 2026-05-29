from __future__ import annotations

from typing import Any


ROUTER_VERSION = "marketing_skill_router_v1"
CATALOG_SOURCE = "coreyhaines31/marketingskills"
CATALOG_URL = "https://github.com/coreyhaines31/marketingskills/tree/main"


SKILLS: dict[str, dict[str, Any]] = {
    "product-marketing": {
        "version": "2.0.0",
        "category": "foundation",
        "purpose": "shared product, audience, positioning, proof, voice, and constraint context",
        "source_path": "skills/product-marketing",
    },
    "customer-research": {
        "version": "2.0.0",
        "category": "strategy",
        "purpose": "buyer language, pains, triggers, awareness level, and objections",
        "source_path": "skills/customer-research",
    },
    "marketing-psychology": {
        "version": "2.0.0",
        "category": "strategy",
        "purpose": "ethical mental models behind hooks, motivation, and visual persuasion",
        "source_path": "skills/marketing-psychology",
    },
    "ads": {
        "version": "2.0.1",
        "category": "paid",
        "purpose": "paid channel strategy, campaign structure, platform rules, and optimization logic",
        "source_path": "skills/ads",
    },
    "ad-creative": {
        "version": "2.0.0",
        "category": "paid",
        "purpose": "platform-ready creative angles, copy variations, visual concepts, and testing loops",
        "source_path": "skills/ad-creative",
    },
    "copywriting": {
        "version": "2.0.0",
        "category": "copy",
        "purpose": "clear benefit, hook, body copy, and CTA language",
        "source_path": "skills/copywriting",
    },
    "copy-editing": {
        "version": "2.0.0",
        "category": "copy",
        "purpose": "remove vague, generic, or off-brand marketing copy",
        "source_path": "skills/copy-editing",
    },
    "image": {
        "version": "2.0.1",
        "category": "production",
        "purpose": "marketing image generation, prompt quality, dimensions, and visual asset rules",
        "source_path": "skills/image",
    },
    "video": {
        "version": "2.0.1",
        "category": "production",
        "purpose": "AI video production, UGC video structure, avatars, and provider choice",
        "source_path": "skills/video",
    },
    "ab-testing": {
        "version": "2.0.0",
        "category": "measurement",
        "purpose": "creative test design and one-variable-at-a-time learning",
        "source_path": "skills/ab-testing",
    },
    "analytics": {
        "version": "2.0.0",
        "category": "measurement",
        "purpose": "tracking, measurement, and performance feedback loops",
        "source_path": "skills/analytics",
    },
    "competitor-profiling": {
        "version": "2.0.0",
        "category": "strategy",
        "purpose": "extract competitive patterns without copying competitor claims or visuals",
        "source_path": "skills/competitor-profiling",
    },
    "competitors": {
        "version": "2.0.0",
        "category": "strategy",
        "purpose": "comparison and differentiation strategy",
        "source_path": "skills/competitors",
    },
    "sales-enablement": {
        "version": "2.0.0",
        "category": "sales",
        "purpose": "objection handling and proof framing for service or B2B offers",
        "source_path": "skills/sales-enablement",
    },
}


SPECIALIST_SKILLS: dict[str, list[str]] = {
    "marketing_skill_router": ["product-marketing", "ads", "ad-creative"],
    "brief_parser": ["product-marketing", "customer-research"],
    "brand_context": ["product-marketing", "copy-editing"],
    "audience_strategy": ["product-marketing", "customer-research", "marketing-psychology"],
    "hook_strategy": ["ad-creative", "marketing-psychology", "copywriting"],
    "claim_safety": ["product-marketing", "ads", "copy-editing"],
    "ugc_video_scenarios": ["product-marketing", "ad-creative", "video", "marketing-psychology", "copywriting"],
    "static_ad_concepts": ["product-marketing", "ad-creative", "image", "marketing-psychology", "copywriting"],
    "scenario_integrity": ["product-marketing", "ad-creative"],
    "provider_validation": ["image", "video", "ads"],
    "video_generator": ["video", "ad-creative"],
    "static_image_generator": ["image", "ad-creative"],
    "creative_review": ["ad-creative", "ab-testing", "analytics"],
    "memory_learning": ["analytics", "ab-testing"],
}


PHASE_SKILLS: dict[str, list[str]] = {
    "brief": ["product-marketing", "customer-research"],
    "strategy": ["product-marketing", "customer-research", "marketing-psychology", "ads", "ad-creative"],
    "plan": ["ad-creative", "video", "image", "copywriting", "copy-editing"],
    "generate": ["video", "image", "ads"],
    "review": ["ad-creative", "ab-testing", "analytics"],
}


def registry() -> dict[str, Any]:
    return {
        "version": ROUTER_VERSION,
        "source": CATALOG_SOURCE,
        "source_url": CATALOG_URL,
        "catalog_principle": "product-marketing context first, then specialist marketing skills by task",
        "foundation_skill": _skill_card("product-marketing"),
        "skills": [_skill_card(skill_id) for skill_id in SKILLS],
        "specialist_skill_map": {
            specialist_id: [_skill_card(skill_id) for skill_id in skill_ids]
            for specialist_id, skill_ids in SPECIALIST_SKILLS.items()
        },
        "phase_skill_map": {
            phase_id: [_skill_card(skill_id) for skill_id in skill_ids]
            for phase_id, skill_ids in PHASE_SKILLS.items()
        },
        "optional_catalog_skills_not_yet_used": ["prospecting", "sms"],
    }


def build_mission_plan(
    *,
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    ugc_strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ugc = ugc_strategy or {}
    platform = str(ugc.get("platform") or settings.get("platform") or "meta").lower()
    app_mode = str(settings.get("app_mode") or "ecommerce")
    generation_mode = str(settings.get("generation_mode") or "both").lower()
    finance_mode = app_mode == "finance_personal_brand"
    needs_video = finance_mode or generation_mode in {"both", "video"}
    needs_static = (not finance_mode) and generation_mode in {"both", "static"}
    selected_ids: list[str] = [
        "product-marketing",
        "customer-research",
        "marketing-psychology",
        "ads",
        "ad-creative",
        "copywriting",
        "copy-editing",
        "ab-testing",
        "analytics",
    ]
    if needs_video:
        selected_ids.append("video")
    if needs_static:
        selected_ids.append("image")
    if settings.get("competitor_strategy_enabled") or (ugc.get("competitor_strategy") or {}).get("status") == "ready":
        selected_ids.extend(["competitor-profiling", "competitors"])
    if finance_mode or _is_service_or_b2b(settings, product_analysis):
        selected_ids.append("sales-enablement")
    selected_ids = _dedupe(selected_ids)

    plan = {
        "version": ROUTER_VERSION,
        "source": CATALOG_SOURCE,
        "source_url": CATALOG_URL,
        "mode": app_mode,
        "platform": platform,
        "generation_mode": generation_mode,
        "product_category": product_analysis.get("likely_product_category") or settings.get("product_category"),
        "ad_vertical": settings.get("ad_vertical") or product_analysis.get("ad_vertical"),
        "foundation_context": product_marketing_context(product_analysis, settings),
        "selected_skills": [_skill_card(skill_id) for skill_id in selected_ids],
        "specialist_routes": {
            specialist_id: _route_payload(
                specialist_id=specialist_id,
                skill_ids=_filter_selected(skill_ids, selected_ids),
                product_analysis=product_analysis,
                settings=settings,
            )
            for specialist_id, skill_ids in SPECIALIST_SKILLS.items()
        },
        "generation_gate": {
            "rule": "Provider execution may only receive approved, scenario-safe, product-faithful creative plans.",
            "bad_or_unapproved_plan_action": "block_generation",
            "why": "Do not spend video/image credits on a plan that does not respect the brief, product reference, avatar contract, or selected marketing job.",
        },
        "creative_quality_contract": {
            "rule": "Every generated ad asset must map to a marketing job, buyer motivation, proof cue, and test hypothesis.",
            "source_skills": ["ad-creative", "marketing-psychology", "image", "video"],
        },
    }
    plan["active_routes"] = [
        route
        for route in plan["specialist_routes"].values()
        if route.get("skills")
    ]
    return plan


def product_marketing_context(product_analysis: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    company = settings.get("company_profile") or product_analysis.get("company_profile") or {}
    product_name = product_analysis.get("product_name") or settings.get("product_name")
    covered: list[str] = []
    missing: list[str] = []
    checks = {
        "product_overview": bool(product_name or product_analysis.get("summary")),
        "product_category": bool(product_analysis.get("likely_product_category") or settings.get("product_category")),
        "business_model": bool(company.get("business_model") or settings.get("ad_vertical")),
        "audience": bool(company.get("audience") or product_analysis.get("audience")),
        "positioning": bool(company.get("positioning") or product_analysis.get("positioning")),
        "brand_voice": bool(company.get("brand_voice")),
        "proof_points": bool(company.get("proof_points") or product_analysis.get("ad_safe_detail_phrases")),
        "forbidden_claims": bool(company.get("forbidden_claims") or product_analysis.get("unsupported_claims")),
    }
    for key, present in checks.items():
        (covered if present else missing).append(key)
    return {
        "version": "product_marketing_context_adapter_v1",
        "source_skill": _skill_card("product-marketing"),
        "storage_mode": "runtime_company_profile_and_product_analysis",
        "canonical_file_status": "not_required_for_app_runtime",
        "company_id": company.get("company_id") or settings.get("company_id"),
        "company_name": company.get("company_name") or company.get("name"),
        "product_name": product_name,
        "product_category": product_analysis.get("likely_product_category") or settings.get("product_category"),
        "business_model": company.get("business_model"),
        "market": settings.get("market") or company.get("market"),
        "language": settings.get("language") or company.get("language"),
        "platform": settings.get("platform") or company.get("default_platform"),
        "audience": company.get("audience") or product_analysis.get("audience"),
        "positioning": company.get("positioning") or product_analysis.get("positioning"),
        "brand_voice": company.get("brand_voice"),
        "proof_points": company.get("proof_points") or product_analysis.get("ad_safe_detail_phrases") or [],
        "forbidden_claims": company.get("forbidden_claims") or product_analysis.get("unsupported_claims") or [],
        "covered_sections": covered,
        "missing_sections": missing,
        "rule": "Use this context before any ad, image, video, or copy skill output.",
    }


def route_for_specialist(
    plan_or_specialist_id: dict[str, Any] | str,
    specialist_id: str | None = None,
) -> dict[str, Any]:
    if isinstance(plan_or_specialist_id, dict):
        plan = plan_or_specialist_id
        target = specialist_id or ""
        route = (plan.get("specialist_routes") or {}).get(target)
        if isinstance(route, dict):
            return route
        return _route_payload(
            specialist_id=target,
            skill_ids=SPECIALIST_SKILLS.get(target, []),
            product_analysis={},
            settings={},
        )
    target = str(plan_or_specialist_id or "")
    return _route_payload(
        specialist_id=target,
        skill_ids=SPECIALIST_SKILLS.get(target, []),
        product_analysis={},
        settings={},
    )


def compact_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict) or not plan.get("version"):
        return {}
    return {
        "version": plan.get("version"),
        "source": plan.get("source"),
        "mode": plan.get("mode"),
        "platform": plan.get("platform"),
        "generation_mode": plan.get("generation_mode"),
        "foundation_context": {
            key: value
            for key, value in (plan.get("foundation_context") or {}).items()
            if key
            in {
                "version",
                "source_skill",
                "storage_mode",
                "company_id",
                "company_name",
                "product_name",
                "product_category",
                "business_model",
                "market",
                "language",
                "platform",
                "covered_sections",
                "missing_sections",
                "rule",
            }
        },
        "selected_skills": plan.get("selected_skills") or [],
        "active_routes": [
            {
                "specialist_id": route.get("specialist_id"),
                "skills": route.get("skills") or [],
                "contract": route.get("contract"),
            }
            for route in (plan.get("active_routes") or [])
        ],
        "generation_gate": plan.get("generation_gate") or {},
        "creative_quality_contract": plan.get("creative_quality_contract") or {},
    }


def _route_payload(
    *,
    specialist_id: str,
    skill_ids: list[str],
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    return {
        "specialist_id": specialist_id,
        "skills": [_skill_card(skill_id) for skill_id in _dedupe(skill_ids)],
        "contract": _contract_for_specialist(specialist_id, product_analysis, settings),
    }


def _contract_for_specialist(
    specialist_id: str,
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
) -> str:
    category = str(product_analysis.get("likely_product_category") or settings.get("product_category") or "offer")
    platform = str(settings.get("platform") or "paid social")
    contracts = {
        "brief_parser": "Build the minimum product-marketing context before strategy or generation.",
        "marketing_skill_router": "Choose the smallest useful marketing skill set for this mission and make it visible in the audit.",
        "brand_context": "Apply saved company voice, proof points, and forbidden claims as creative constraints.",
        "audience_strategy": "Translate product context into buyer tension, awareness level, and decision triggers.",
        "hook_strategy": "Create distinct hooks and angle families before writing copy or prompts.",
        "claim_safety": "Use supplied facts only; unsupported claims become internal notes or are removed.",
        "ugc_video_scenarios": f"Create {platform} UGC video scenes for {category} with a first-3-second hook, product proof, and natural spoken copy.",
        "static_ad_concepts": f"Create visually distinct {platform} static ad concepts for {category}; no filler variants.",
        "scenario_integrity": "Block generation if provider prompts drift from the approved scenario contract.",
        "provider_validation": "Check references, prompt size, model capability, and output mode before provider calls.",
        "video_generator": "Generate only from the approved provider-ready video prompt and reference plan.",
        "static_image_generator": "Generate only from approved static concepts and product-fidelity locks.",
        "creative_review": "Turn results and blockers into a next iteration plan.",
        "memory_learning": "Save winning and rejected patterns for future creative selection.",
    }
    return contracts.get(specialist_id, "Use the selected marketing skills as internal creative direction.")


def _filter_selected(skill_ids: list[str], selected_ids: list[str]) -> list[str]:
    selected = set(selected_ids)
    return [skill_id for skill_id in skill_ids if skill_id in selected]


def _skill_card(skill_id: str) -> dict[str, Any]:
    skill = SKILLS.get(skill_id, {})
    return {
        "id": skill_id,
        "version": skill.get("version"),
        "category": skill.get("category"),
        "purpose": skill.get("purpose"),
        "source": CATALOG_SOURCE,
        "source_path": skill.get("source_path"),
    }


def _is_service_or_b2b(settings: dict[str, Any], product_analysis: dict[str, Any]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            settings.get("ad_vertical"),
            settings.get("business_model"),
            (settings.get("company_profile") or {}).get("business_model"),
            product_analysis.get("likely_product_category"),
            product_analysis.get("product_type"),
        ]
    ).lower()
    return any(term in text for term in ["service", "finance", "saas", "b2b", "solar", "fve", "lead"])


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = str(value or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result
