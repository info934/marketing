from __future__ import annotations

import json
import re
from typing import Any

from app.services.text_utils import find_pattern_matches


FORBIDDEN_FIDELITY_PATTERNS = [
    r"\bredesign\b",
    r"\bchange (the )?color\b",
    r"\bnew material\b",
    r"\bleather\b",
    r"\bsuede\b",
    r"\bsilk\b",
    r"\bfabric\b",
    r"\bcanvas\b",
    r"\bplastic\b",
    r"\bglass (material|finish|transparency|look|shine|body|texture)\b",
    r"\blook(s|ing)? like glass\b",
    r"\bmake (it|the product)[^.;]*\bglass\b",
    r"\bglass-like\b",
    r"\bmetal\b",
    r"\bsteel\b",
    r"\balumin(i)?um\b",
    r"\bwood(en)?\b",
    r"\bceramic\b",
    r"\brubber\b",
    r"\bacrylic\b",
    r"\bcotton\b",
    r"\bpolyester\b",
    r"\bnylon\b",
    r"\bmatte\b",
    r"\bglossy\b",
    r"\btransparent\b",
    r"\bopaque\b",
    r"\bpebbled\b",
    r"\bwoven\b",
    r"\bquilted\b",
    r"\bpadded\b",
    r"\bgrained\b",
    r"\bdesigner\b",
    r"\bluxury\b",
    r"\blike (nike|adidas|gucci|prada|chanel|louis vuitton|lv|hermes|dior)\b",
]

MATERIAL_TERMS = {
    "leather",
    "suede",
    "silk",
    "fabric",
    "canvas",
    "plastic",
    "glass",
    "metal",
    "steel",
    "aluminium",
    "aluminum",
    "wood",
    "wooden",
    "ceramic",
    "rubber",
    "acrylic",
    "cotton",
    "polyester",
    "nylon",
    "matte",
    "glossy",
    "transparent",
    "opaque",
    "pebbled",
    "woven",
    "quilted",
    "padded",
    "grained",
}


def check(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> dict[str, Any]:
    if _is_finance_mode(product_analysis, ugc_strategy, content_prompt_package):
        return {
            "product_fidelity_status": "pass",
            "changed_or_invented_details": [],
            "missing_fidelity_instructions": [],
            "recommended_fixes": [],
            "finance_mode_note": "No physical ecommerce product is being preserved; factual finance content and avatar identity are checked by compliance and prompt rules.",
        }
    raw_combined = json.dumps(
        {
            "ugc_strategy": ugc_strategy,
            "content_prompt_package": content_prompt_package,
        },
        ensure_ascii=False,
    )
    guard_payload = _sanitize_guard_payload(
        {
            "ugc_strategy": ugc_strategy,
            "content_prompt_package": content_prompt_package,
        }
    )
    combined = json.dumps(guard_payload, ensure_ascii=False)
    combined = _remove_unverified_material_example_language(combined)
    claim_text = _remove_negative_prompt_language(combined)
    claim_text = _remove_unverified_material_example_language(claim_text)
    claim_text = _remove_protective_clauses(claim_text, FORBIDDEN_FIDELITY_PATTERNS)
    claim_text = _remove_safe_apparel_fabric_language(claim_text, product_analysis)
    changed_or_invented = find_pattern_matches(claim_text, FORBIDDEN_FIDELITY_PATTERNS)
    changed_or_invented = [
        match for match in changed_or_invented if not _allowed_user_fact_match(match, product_analysis)
    ]
    missing = []
    expected_image_path = str(product_analysis.get("product_image_path", ""))
    referenced_image_path = str(content_prompt_package.get("seedance_payload", {}).get("product_image_path", ""))
    fidelity_instruction = content_prompt_package.get("product_fidelity_instruction", "")
    if expected_image_path and expected_image_path != referenced_image_path and expected_image_path not in fidelity_instruction:
        missing.append("uploaded product image is not referenced as strict visual reference")
    if "strict visual reference" not in raw_combined.lower():
        missing.append("strict product fidelity instruction is missing")
    if "product identity hard lock" not in raw_combined.lower():
        missing.append("product identity hard lock is missing")
    if "do not redesign" not in raw_combined.lower() and "do not alter the product" not in raw_combined.lower():
        missing.append("negative prompt does not clearly prevent product redesign")
    if "negative prompt" not in raw_combined.lower() and "negative_prompt" not in raw_combined.lower():
        missing.append("negative prompt is missing")

    category = product_analysis.get("likely_product_category")
    if category == "shoes":
        medical = find_pattern_matches(claim_text, [r"\borthop(a|ae)dic\b", r"\bmedical\b", r"\bpain[- ]?free\b"])
        changed_or_invented.extend(medical)
    if category == "handbag":
        luxury = find_pattern_matches(claim_text, [r"\bdesigner\b", r"\bluxury\b", r"\bdupe\b"])
        changed_or_invented.extend(luxury)

    recommended_fixes = []
    if changed_or_invented:
        recommended_fixes.append("Remove invented product, material, medical, luxury, or brand comparison language.")
    if missing:
        recommended_fixes.append("Add strict product image reference, product preservation, and negative prompt wording.")

    status = "pass"
    if changed_or_invented or missing:
        status = "fail" if missing or _has_hard_fail(changed_or_invented) else "warning"

    return {
        "product_fidelity_status": status,
        "changed_or_invented_details": sorted(set(changed_or_invented)),
        "missing_fidelity_instructions": missing,
        "recommended_fixes": recommended_fixes,
    }


def _is_finance_mode(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> bool:
    return (
        str(product_analysis.get("likely_product_category") or "").lower() == "finance"
        or str((content_prompt_package.get("seedance_payload") or {}).get("creative_mode") or "") == "finance_personal_brand"
        or bool(ugc_strategy.get("finance_compliance"))
    )


def _has_hard_fail(matches: list[str]) -> bool:
    hard_terms = [
        "designer",
        "luxury",
        "orthopedic",
        "orthopaedic",
        "medical",
        *MATERIAL_TERMS,
    ]
    text = " ".join(matches).lower()
    return any(term in text for term in hard_terms)


def _allowed_user_fact_match(match: str, product_analysis: dict[str, Any]) -> bool:
    matched = str(match or "").lower()
    if not matched:
        return False
    allowed_text_parts = []
    known_facts = product_analysis.get("known_product_facts") or {}
    if isinstance(known_facts, dict):
        allowed_text_parts.extend(str(value) for value in known_facts.values() if value)
    allowed_text_parts.extend(str(value) for value in product_analysis.get("user_provided_facts") or [])
    allowed_text_parts.extend(str(value) for value in product_analysis.get("ad_safe_detail_phrases") or [])
    allowed_text = " ".join(allowed_text_parts).lower()
    normalized_match = _normalize_material_match(matched)
    return normalized_match in MATERIAL_TERMS and normalized_match in allowed_text


def _normalize_material_match(value: str) -> str:
    return str(value or "").strip().lower()


def _remove_negative_prompt_language(text: str) -> str:
    text = re.sub(r"data:image/[^\"']+", "", text, flags=re.IGNORECASE)
    text = re.sub(r'"negative_prompt"\s*:\s*"[^"]*"', "", text, flags=re.IGNORECASE)
    text = re.sub(r"Negative prompt:.*?(?=(Variation|$))", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"Do not [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNo [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAvoid [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNever [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwithout [^.]*\b(luxury|designer|medical|orthop(a|ae)dic)[^.]*[.]", "", text, flags=re.IGNORECASE)
    return text


def _remove_unverified_material_example_language(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(
        r"\((?:e\.g\.|eg|for example)[^)]*(?:canvas|leather|fabric|suede|nylon|polyester|waterproof)[^)]*\)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:do not|avoid|never)\s+[^;\"\n]*(?:unverified\s+(?:claims?|material)|fabric\s+material)[^;\"\n]*(?:;|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bmaking\s+unverified\s+claims?\s+about\s+[^.;\"\n]*(?:[.;]|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bavoid:\s*(?:(?:e\.?\s*)?g\.?,?\s*)?['\"]?[^.;\"\n]*(?:canvas|leather|fabric|suede|nylon|polyester)[^.;\"\n]*(?:[.;]|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bvisual\s*,\s*['\"]?[^.;\"\n]*(?:canvas|leather|fabric|suede|nylon|polyester)[^.;\"\n]*\)\.?",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _remove_safe_apparel_fabric_language(text: str, product_analysis: dict[str, Any]) -> str:
    category = str(product_analysis.get("likely_product_category") or "").lower()
    if category != "apparel":
        return text
    cleaned = str(text or "")
    safe_patterns = [
        r"\bfabric\s+(look|movement|drape|drapes|draping|detail|details|texture|finish|touch|close[- ]?up)\b",
        r"\bfabric\s+actually\s+drapes\b",
        r"\bmovement\s+of\s+the\s+fabric\b",
        r"\bflow\s+of\s+the\s+fabric\b",
        r"\bfabric\s+(flow|flows|flowing)\b",
        r"\bfabric\s*/\s*(seam|cut|closure)\b",
        r"\b(seam|cut|closure)\s*/\s*fabric\b",
        r"\b(seam|cut|closure)\s+and\s+fabric\b",
        r"\bfabric\s+(while\s+)?worn\b",
        r"\bfabric\s+through\s+(walking|turning|twirling|motion|movement)\b",
        r"\bfabric\s+or\s+(cut|seam|closure)\b",
        r"\bfabric[- ]only\s+shots?\b",
        r"\bsmooth(?:ing)?\s+the\s+fabric\b",
        r"\badjusts?\s+(?:the\s+)?fabric\b(?:\s+(?:casually|naturally|slightly|gently))?",
        r"\btouches?\s+(?:the\s+)?fabric\b(?:\s+(?:casually|naturally|slightly|gently))?",
        r"\bholds?\s+(?:the\s+)?fabric\b(?:\s+(?:casually|naturally|slightly|gently))?",
        r"\bchecks?\s+(?:the\s+)?fabric\b(?:\s+(?:movement|drape|fall|fit|naturally|gently))?",
        r"\bfabric\s+(moves|falls|sits|drapes)\b",
    ]
    for pattern in safe_patterns:
        cleaned = re.sub(pattern, "visible garment detail", cleaned, flags=re.IGNORECASE)
    return cleaned


_IGNORED_GUARD_KEYS = {
    "creative_memory_guidance",
    "creative_memory_rag",
    "performance_insights",
    "prompt_generation",
    "prompt_compression",
    "prompt_source_inventory",
    "negative_prompt",
    "avoid_in_generation",
    "material_lock",
    "forbidden_material_substitution",
    "product_material_fidelity_lock",
    "static_material_fidelity_lock",
    "negative_material_examples",
    "generation_id",
    "id",
    "product_id",
    "campaign_id",
    "creative_id",
    "avatar_consistency_instruction",
    "avatar_scene_instruction",
    "avatar_identity_contract",
    "voice_profile",
    "voice_personality",
    "voiceover_tts_prompt",
    "best_historical_creatives",
    "worst_historical_creatives",
    "knowledge_item_count",
    "memory_path",
    "storage",
}


def _sanitize_guard_payload(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            key_text = str(key)
            if key_text in _IGNORED_GUARD_KEYS or key_text.endswith("_id"):
                continue
            cleaned[key_text] = _sanitize_guard_payload(child)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_guard_payload(item) for item in value]
    if isinstance(value, str):
        return _remove_avatar_context_language(value)
    return value


def _remove_avatar_context_language(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(
        r"\bCreator label\s*=\s*[^.;{}\"\\]*(?:[.;]+|\s|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bpersona\s*=\s*[^{}]{0,900}?(?=\bvoice\s*=|\bScene prompts\b|\bdialogue\b|\bVoice profile\b|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bvoice\s*=\s*[^{}]{0,900}?(?=\bScene prompts\b|\bdialogue\b|\bVoice profile\b|\bGenerate audible\b|\bSubtitle\b|\bCategory\b|\bExtra\b|\bNegative\b|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bVoice profile:\s*[^{}]{0,900}?(?=\bGenerate audible\b|\bSubtitle\b|\bCategory\b|\bExtra\b|\bNegative\b|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bselected creator voice:\s*[^.;{}]{0,500}",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bVoice personality:\s*[^{}]{0,900}?(?=\bScenes\b|\bProduct\b|\bSubtitle\b|\bCategory\b|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _remove_protective_clauses(text: str, patterns: list[str]) -> str:
    pieces = re.split(r"([.;\n])", text)
    cleaned: list[str] = []
    for index in range(0, len(pieces), 2):
        clause = pieces[index]
        separator = pieces[index + 1] if index + 1 < len(pieces) else ""
        if _is_protective_clause(clause, patterns):
            continue
        cleaned.append(clause + separator)
    return "".join(cleaned)


def _is_protective_clause(clause: str, patterns: list[str]) -> bool:
    lower = clause.lower()
    if not any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in patterns):
        return False
    protective_cues = [
        "do not",
        "don't",
        "no ",
        "avoid",
        "never",
        "without",
        "unless",
        "prevent",
        "preserve",
        "unchanged",
        "not ",
        "must not",
        "should not",
        "cannot",
        "forbid",
        "forbidden",
        "source of truth",
        "only when",
        "when confirmed",
        "when supplied",
        "when visible",
        "unless visible",
        "unless supplied",
        "not modified",
        "not restyled",
        "not recolored",
        "not rebranded",
    ]
    return any(cue in lower for cue in protective_cues)
