from __future__ import annotations

from typing import Any


ARCHETYPES = {
    "shoes": {
        "comfort": "wants shoes that look easy to wear without needing medical or comfort claims",
        "aesthetic": "chooses footwear by outfit compatibility and visual detail",
        "refined": "responds to refined finish and premium-looking restraint without brand-status claims",
        "sporty": "looks for movement-ready styling without performance promises",
        "minimalist": "prefers clean shape, low visual noise, and practical versatility",
    },
    "handbag": {
        "elegance": "wants the bag to look polished through shape, finish, and outfit context",
        "practicality": "wants daily usability signals without unverified capacity claims",
        "office": "imagines workday outfits, desk context, and structured carry moments",
        "travel": "looks for on-the-go context, scale, and easy-carry cues",
        "fashion": "cares about silhouette, outfit pairing, and styling relevance",
    },
    "apparel": {
        "aesthetic": "cares about the cut and how the piece reads in a real outfit",
        "office": "imagines smart everyday styling without formal status claims",
        "minimalist": "responds to simple shape, garment movement, and restrained detail",
        "fashion": "wants styling inspiration and visual identity",
        "practicality": "needs clear worn context before deciding",
    },
}


def generate(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    performance_insights: dict[str, Any],
) -> dict[str, Any]:
    category = str(product_analysis.get("likely_product_category") or "unknown")
    company = product_analysis.get("company_profile") or settings.get("company_profile") or {}
    facts = " ".join(product_analysis.get("user_provided_facts") or []).lower()
    safe_use_cases = " ".join(product_analysis.get("safe_use_cases") or []).lower()
    archetype_map = ARCHETYPES.get(category) or {
        "practicality": "wants to understand the product in a real use context",
        "aesthetic": "cares about how the product looks in a normal environment",
        "minimalist": "prefers clear details and low-hype presentation",
    }
    scored = _score_archetypes(category, archetype_map, facts, safe_use_cases, performance_insights)
    primary = scored[0]["archetype"]
    secondary = [item["archetype"] for item in scored[1:3]]
    return {
        "agent": "Audience Research Agent",
        "category": category,
        "company_profile": {
            "company_id": company.get("company_id") or company.get("id"),
            "company_name": company.get("company_name") or company.get("name"),
            "ad_vertical": company.get("ad_vertical"),
            "audience": company.get("audience"),
            "positioning": company.get("positioning"),
        },
        "market": settings.get("market"),
        "platform": settings.get("platform"),
        "primary_archetype": primary,
        "secondary_archetypes": secondary,
        "archetype_scores": scored,
        "audience_summary": _audience_summary(archetype_map[primary], company),
        "decision_triggers": _decision_triggers(category, primary),
        "objections": _objections(category, primary),
        "content_bias": _company_content_bias(_content_bias(category, primary), company),
        "memory_signal": {
            "winning_archetypes": (performance_insights.get("seed_insights") or {}).get(
                "winning_archetypes", []
            ),
            "winning_record_count": performance_insights.get("winner_count", 0),
        },
    }


def _audience_summary(default: str, company: dict[str, Any]) -> str:
    audience = str(company.get("audience") or "").strip()
    positioning = str(company.get("positioning") or "").strip()
    if audience and positioning:
        return f"{audience} Positioning lens: {positioning}"
    return audience or default


def _company_content_bias(default: str, company: dict[str, Any]) -> str:
    proof_points = company.get("proof_points") or []
    brand_voice = str(company.get("brand_voice") or "").strip()
    parts = [default]
    if proof_points:
        parts.append("prefer brand proof points: " + ", ".join(str(item) for item in proof_points[:4]))
    if brand_voice:
        parts.append(f"brand voice: {brand_voice}")
    return ". ".join(parts)


def _score_archetypes(
    category: str,
    archetype_map: dict[str, str],
    facts: str,
    safe_use_cases: str,
    performance_insights: dict[str, Any],
) -> list[dict[str, Any]]:
    winners = (performance_insights.get("seed_insights") or {}).get("winning_archetypes") or []
    scores = []
    for archetype in archetype_map:
        score = 10
        if archetype in winners:
            score += 5
        if archetype in facts or archetype in safe_use_cases:
            score += 6
        if category == "handbag" and archetype in {"office", "travel"} and any(
            word in facts for word in ["work", "travel", "errands"]
        ):
            score += 8
        if category == "handbag" and archetype == "practicality" and any(
            word in facts for word in ["interior", "structured", "waterproof"]
        ):
            score += 8
        if category == "shoes" and archetype == "minimalist" and "clean" in facts:
            score += 5
        if category == "apparel" and archetype in {"aesthetic", "fashion"}:
            score += 3
        scores.append({"archetype": archetype, "score": score, "rationale": archetype_map[archetype]})
    return sorted(scores, key=lambda item: (-item["score"], item["archetype"]))


def _decision_triggers(category: str, archetype: str) -> list[str]:
    defaults = ["clear product scale", "visible material or finish", "real-life context"]
    by_category = {
        "handbag": {
            "practicality": ["shape holds visually", "opening and handle details", "daily carry scale"],
            "office": ["desk-to-hallway context", "structured silhouette", "outfit compatibility"],
            "travel": ["in-hand carry context", "scale next to everyday objects", "secure-looking opening"],
            "elegance": ["clean silhouette", "subtle finish detail", "polished outfit context"],
            "fashion": ["outfit styling", "silhouette from a distance", "close hardware/detail crop"],
        },
        "shoes": {
            "comfort": ["side profile on foot", "sole shape", "walking-context visual without claims"],
            "aesthetic": ["outfit pairing", "toe shape", "side profile"],
            "sporty": ["movement-ready framing", "sole detail", "casual outfit context"],
            "minimalist": ["clean side profile", "low-clutter floor shot", "simple styling"],
            "refined": ["finish detail", "restrained lighting", "close construction crop"],
        },
        "apparel": {
            "aesthetic": ["worn cut", "mirror view", "garment movement"],
            "office": ["smart outfit context", "sleeve and hem detail", "hallway/mirror shot"],
            "minimalist": ["simple silhouette", "detail close-up", "neutral styling"],
            "fashion": ["layering idea", "movement", "outfit context"],
            "practicality": ["clear worn view", "seam detail", "easy everyday styling"],
        },
    }
    return (by_category.get(category) or {}).get(archetype, defaults)


def _objections(category: str, archetype: str) -> list[str]:
    by_category = {
        "handbag": ["Will it look bulky?", "Can I judge scale from one photo?", "Does the structure look right?"],
        "shoes": ["Do they look right when worn?", "Is the side profile clear?", "Is this just a table shot?"],
        "apparel": ["How does the cut look worn?", "Does the garment move naturally?", "Is the flat-lay hiding the fit?"],
    }
    return by_category.get(category, ["Can I judge the product from this ad?", "Is the detail real enough?"])


def _content_bias(category: str, archetype: str) -> str:
    if category == "handbag" and archetype in {"office", "travel", "practicality"}:
        return "show carried scale and practical detail before aesthetic close-ups"
    if category == "shoes":
        return "show worn side profile before macro detail"
    if category == "apparel":
        return "show the piece worn before any close-up"
    return "show real-life context before product-only detail"
