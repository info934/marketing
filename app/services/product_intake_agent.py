from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.localization_utils import localize_phrases
from app.services.text_utils import (
    RISKY_CLAIM_PATTERNS,
    detect_category,
    find_pattern_matches,
    normalize_text,
    split_notes,
    unique_preserve_order,
)

CATEGORY_OVERRIDES = {"handbag", "shoes", "apparel", "beauty", "home", "electronics", "finance"}


def analyse(input_data: dict[str, Any], product_image_path: str | Path) -> dict[str, Any]:
    product_name = normalize_text(input_data.get("product_name")) or "Unknown product"
    notes = normalize_text(input_data.get("product_info") or input_data.get("notes"))
    language = normalize_text(input_data.get("language")) or "en"
    requested_category = normalize_text(input_data.get("product_category")).lower()
    if requested_category in CATEGORY_OVERRIDES:
        category = requested_category
        category_source = "user_selected"
    else:
        category = detect_category(product_name, notes)
        category_source = "auto_detected"
    note_parts = split_notes(notes)
    risky_matches = {
        risk: find_pattern_matches(notes, patterns)
        for risk, patterns in RISKY_CLAIM_PATTERNS.items()
    }
    unsupported_claims = unique_preserve_order(
        match for matches in risky_matches.values() for match in matches
    )
    safe_benefits = [
        part
        for part in note_parts
        if not any(part.lower().find(claim.lower()) >= 0 for claim in unsupported_claims)
        and not find_pattern_matches(part, RISKY_CLAIM_PATTERNS["medical"])
        and not find_pattern_matches(part, RISKY_CLAIM_PATTERNS["testimonial"])
    ]
    if not safe_benefits:
        safe_benefits = ["Shows the product clearly in a practical everyday context"]
    user_provided_facts = _brief_fact_phrases(
        notes=notes,
        safe_benefits=safe_benefits,
        unsupported_claims=unsupported_claims,
    )

    missing_information = []
    if product_name == "Unknown product":
        missing_information.append("product_name")
    if not notes:
        missing_information.append("product_info_or_notes")
    if category == "unknown":
        missing_information.append("confirmed_product_category")

    trademark_or_counterfeit_risks = risky_matches["trademark"]
    if any(word in notes.lower() for word in ["logo", "designer", "luxury"]):
        trademark_or_counterfeit_risks.append("possible unverified brand or luxury implication")

    safe_use_cases = _safe_use_cases_for_category(category)
    ad_safe_detail_phrases = unique_preserve_order(
        user_provided_facts + _ad_safe_detail_phrases_for_category(category)
    )
    localized_user_provided_facts = localize_phrases(user_provided_facts, language)
    localized_safe_benefits = localize_phrases(safe_benefits, language)
    localized_ad_safe_detail_phrases = localize_phrases(ad_safe_detail_phrases, language)
    target_audience = _target_audience_for_category(category)
    safest_creative_angle = _creative_angle(category, ad_safe_detail_phrases)
    known_facts = _known_product_facts(
        product_name=product_name,
        category=category,
        notes=notes,
    )

    return {
        "agent": "Product Intake Agent",
        "product_name": product_name,
        "product_image_path": str(product_image_path),
        "likely_product_category": category,
        "requested_product_category": requested_category or "auto",
        "product_category_source": category_source,
        "known_product_facts": known_facts,
        "user_provided_facts": user_provided_facts,
        "user_provided_facts_localized": localized_user_provided_facts,
        "safe_benefits": safe_benefits,
        "safe_benefits_localized": localized_safe_benefits,
        "internal_brief_notes": notes,
        "ad_safe_detail_phrases": ad_safe_detail_phrases,
        "ad_safe_detail_phrases_localized": localized_ad_safe_detail_phrases,
        "customer_language": language,
        "missing_information": missing_information,
        "unsupported_claims": unsupported_claims,
        "possible_trademark_or_counterfeit_risks": unique_preserve_order(
            trademark_or_counterfeit_risks
        ),
        "safe_use_cases": safe_use_cases,
        "suggested_target_audience": target_audience,
        "safest_creative_angle": safest_creative_angle,
        "rules_applied": [
            "No invented brand, material, reviews, or medical benefits",
            "Unknown details are marked as unknown",
            "Risky claims are separated from safe product direction",
            "Product notes are used as internal prompt guidance, not copied verbatim into ad copy",
            "Short product facts are extracted from user input and marked as user-provided prompt grounding",
        ],
        "prompt_data_sources": {
            "primary_user_inputs": [
                "product_name",
                "product_info",
                "product_category",
                "product_reference_url or uploaded product_image",
            ],
            "derived_from_user_input": [
                "likely_product_category",
                "known_product_facts",
                "user_provided_facts",
                "safe_benefits",
                "ad_safe_detail_phrases",
            ],
            "backend_defaults_used_only_as_fallback": [
                "category use cases",
                "generic detail phrases when user facts are missing",
                "safety and compliance guardrails",
            ],
        },
    }


def _known_product_facts(product_name: str, category: str, notes: str) -> dict[str, str]:
    if category == "finance":
        return {
            "name": product_name,
            "category": "finance",
            "brand": "personal brand",
            "product_line_or_label": "financial education or financial product explanation",
            "material": "not applicable",
            "color": "not applicable",
            "source": "user_input_finance_script",
        }
    return {
        "name": product_name,
        "category": category,
        "brand": "unknown",
        "product_line_or_label": _product_line_or_label(product_name),
        "material": _extract_material(notes),
        "color": _extract_color(notes),
        "source": "user_input_and_uploaded_image",
    }


def _product_line_or_label(product_name: str) -> str:
    if "|" in product_name:
        label = product_name.split("|", 1)[0].strip()
        if label:
            return label
    return "unknown"


def _extract_material(notes: str) -> str:
    lowered = notes.lower()
    material_rules = [
        ("two-layer cowhide leather", ["two-layer cowhide leather", "two layer cowhide leather"]),
        ("cowhide leather", ["cowhide leather"]),
        ("vegan leather", ["vegan leather"]),
        ("leather", ["leather"]),
        ("plastic", ["plastic", "plastova", "plastová", "plastovy", "plastový", "kunststoff"]),
        ("cotton", ["cotton"]),
        ("linen", ["linen"]),
        ("wool", ["wool"]),
        ("metal", ["metal"]),
        ("wood", ["wood"]),
        ("ceramic", ["ceramic"]),
    ]
    for material, needles in material_rules:
        if any(needle in lowered for needle in needles):
            return material
    return "unknown"


def _extract_color(notes: str) -> str:
    lowered = notes.lower()
    colors = [
        "black",
        "white",
        "brown",
        "tan",
        "beige",
        "cream",
        "grey",
        "gray",
        "navy",
        "blue",
        "green",
        "red",
        "pink",
        "gold",
        "silver",
    ]
    for color in colors:
        if f" {color} " in f" {lowered} ":
            return color
    return "unknown"


def _brief_fact_phrases(
    notes: str,
    safe_benefits: list[str],
    unsupported_claims: list[str],
) -> list[str]:
    lowered = notes.lower()
    facts: list[str] = []
    if "two-layer cowhide leather" in lowered or "two layer cowhide leather" in lowered:
        facts.append("two-layer cowhide leather")
    elif "cowhide leather" in lowered:
        facts.append("cowhide leather")
    elif "vegan leather" in lowered:
        facts.append("vegan leather")
    elif "leather" in lowered:
        facts.append("leather finish")
    if "waterproof interior" in lowered:
        facts.append("waterproof interior")
    elif "spacious interior" in lowered:
        facts.append("spacious interior")
    if any(phrase in lowered for phrase in ["custom name", "personalized name", "personalised name", "vlastnim napisem", "vlastním nápisem", "vlastni napis", "vlastní nápis", "namensaufdruck"]):
        facts.append("custom name inscription")
    ml_match = re.search(r"\b(\d{2,4})\s*ml\b", lowered)
    if ml_match:
        facts.append(f"{ml_match.group(1)} ml capacity")
    if any(phrase in lowered for phrase in ["plastic", "plastova", "plastová", "plastovy", "plastový", "kunststoff"]):
        facts.append("plastic material")
    if any(phrase in lowered for phrase in ["nerozbit", "shatter resistant", "shatter-resistant", "unbreakable", "bruchfest"]):
        facts.append("shatter resistant plastic")
    if any(phrase in lowered for phrase in ["clear", "transparent", "cira", "čirá", "cire", "číre", "klar", "transparent"]):
        facts.append("clear product body")
    if "minimalist shape" in lowered:
        facts.append("clean minimalist shape")
    elif "minimalist" in lowered:
        facts.append("minimalist design")
    if "structured" in lowered:
        facts.append("structured shape")
    if all(word in lowered for word in ["work", "errands", "travel"]):
        facts.append("work errands and travel context")

    for benefit in safe_benefits:
        if len(facts) >= 5:
            break
        cleaned = normalize_text(benefit).strip(" .")
        if 4 <= len(cleaned.split()) <= 8 and cleaned.lower() not in lowered:
            facts.append(cleaned)
    return [
        fact
        for fact in unique_preserve_order(facts)
        if not any(claim.lower() in fact.lower() for claim in unsupported_claims)
    ][:5]


def _safe_use_cases_for_category(category: str) -> list[str]:
    defaults = ["Product overview", "Unboxing-style reveal", "Everyday styling or setup"]
    by_category = {
        "shoes": ["Casual outfit styling", "Close-up of fit and design details"],
        "handbag": ["Daily carry setup", "Outfit pairing and storage overview"],
        "beauty": ["Texture and packaging close-up", "Routine placement without results claims"],
        "home": ["Room setup", "Before placement and after placement without performance claims"],
        "electronics": ["Desk or travel setup", "Feature walkthrough based only on provided facts"],
        "apparel": ["Outfit styling", "Garment movement and fit overview without material claims"],
    }
    return by_category.get(category, defaults)


def _ad_safe_detail_phrases_for_category(category: str) -> list[str]:
    defaults = [
        "visible product shape",
        "product details shown clearly",
        "everyday context without extra claims",
    ]
    by_category = {
        "shoes": ["visible shape and sole details", "fit context without comfort claims", "everyday styling view"],
        "handbag": ["visible shape and carry details", "storage context without capacity claims", "everyday styling view"],
        "beauty": ["visible texture and packaging", "routine context without results claims", "close-up product details"],
        "home": ["visible size and placement", "room context without performance claims", "material details only if visible"],
        "electronics": ["visible ports and controls", "setup context without performance claims", "feature walkthrough from supplied facts"],
        "apparel": ["visible cut and fit context", "garment movement without material claims", "styling view"],
    }
    return by_category.get(category, defaults)


def _target_audience_for_category(category: str) -> str:
    audiences = {
        "shoes": "Style-conscious shoppers looking for everyday footwear",
        "handbag": "Shoppers looking for practical outfit accessories",
        "beauty": "Beauty shoppers comparing routine-friendly products",
        "home": "Home shoppers looking for practical visual inspiration",
        "electronics": "Shoppers looking for simple product setup and use context",
        "apparel": "Fashion shoppers looking for styling ideas",
    }
    return audiences.get(category, "General shoppers who want a clear, trustworthy product overview")


def _creative_angle(category: str, safe_benefits: list[str]) -> str:
    benefit = safe_benefits[0]
    if category == "unknown":
        return f"A clear creator-led product reveal focused on visible details: {benefit}"
    return f"Natural creator walkthrough showing how the {category} fits into everyday use: {benefit}"
