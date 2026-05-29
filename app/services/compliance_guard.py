from __future__ import annotations

import json
import re
from typing import Any

from app.services.text_utils import RISKY_CLAIM_PATTERNS, find_pattern_matches


PLATFORM_RISK_PATTERNS = [
    r"\bguaranteed\b",
    r"\bmiracle\b",
    r"\binstant results\b",
    r"\bhidden ad\b",
    r"\bsponsored but pretend\b",
]

FINANCE_RISK_PATTERNS = [
    r"\bgarantovan(ý|é|a|ou)?\s+výnos(y|ů)?\b",
    r"\bjist(ý|á|é)?\s+zisk\b",
    r"\bbez rizika\b",
    r"\bzbohatne(š|te)\b",
    r"\bprofit guaranteed\b",
    r"\bguaranteed returns?\b",
    r"\brisk[- ]?free\b",
    r"\bkup(te)?\s+hned\b",
]

UK_MARKET_PATTERNS = [
    r"\bfree\b",
    r"\bwas £?\d+\b",
    r"\blimited time\b",
    r"\bclinically proven\b",
]


def check(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> dict[str, Any]:
    combined = json.dumps(
        {
            "ugc_strategy": ugc_strategy,
            "content_prompt_package": content_prompt_package,
        },
        ensure_ascii=False,
    )
    claim_text = _remove_negative_prompt_language(combined)
    claim_text = _remove_safety_context_language(claim_text)
    claim_text = _remove_instructional_treat_language(claim_text)
    unsupported_claims = product_analysis.get("unsupported_claims", [])
    fake_review_risks = find_pattern_matches(claim_text, RISKY_CLAIM_PATTERNS["testimonial"])
    product_trademark_risks = list(product_analysis.get("possible_trademark_or_counterfeit_risks", []))
    claim_trademark_risks = find_pattern_matches(claim_text, RISKY_CLAIM_PATTERNS["trademark"])
    generated_brand_risks = _positive_generated_brand_risks(claim_text)
    trademark_warnings = [
        risk
        for risk in product_trademark_risks
        if _is_soft_product_brand_warning(str(risk))
    ]
    trademark_risks = [
        risk
        for risk in product_trademark_risks
        if not _is_soft_product_brand_warning(str(risk))
    ]
    trademark_risks.extend(claim_trademark_risks)
    trademark_risks.extend(generated_brand_risks)
    platform_policy_risks = find_pattern_matches(claim_text, PLATFORM_RISK_PATTERNS)
    medical_risks = find_pattern_matches(claim_text, RISKY_CLAIM_PATTERNS["medical"])
    scarcity_risks = find_pattern_matches(claim_text, RISKY_CLAIM_PATTERNS["scarcity"])
    discount_risks = find_pattern_matches(claim_text, RISKY_CLAIM_PATTERNS["discount"])
    market = ugc_strategy.get("market", "").upper()
    uk_market_risks = find_pattern_matches(claim_text, UK_MARKET_PATTERNS) if market in {"UK", "GB"} else []
    finance_risks = []
    if (
        str(product_analysis.get("likely_product_category") or "").lower() == "finance"
        or bool(ugc_strategy.get("finance_compliance"))
    ):
        finance_risks = find_pattern_matches(claim_text, FINANCE_RISK_PATTERNS)

    testimonial_allowed = ugc_strategy.get("avatar_direction", {}).get("personal_use_claims_allowed", False)
    avatar_personal_claims = []
    if not testimonial_allowed:
        avatar_personal_claims = find_pattern_matches(
            ugc_strategy.get("voiceover", ""),
            [r"\bi (love|used|tried|tested|wear|wore)\b", r"\bmy results\b"],
        )

    recommended_fixes = []
    if unsupported_claims or medical_risks:
        recommended_fixes.append("Remove unsupported or medical/health claims and replace with visible-detail wording.")
    if fake_review_risks or avatar_personal_claims:
        recommended_fixes.append("Remove fake review, testimonial, and personal-use language.")
    if trademark_risks or trademark_warnings:
        recommended_fixes.append("Remove famous brand comparisons, counterfeit, replica, or designer-dupe wording.")
    if scarcity_risks or discount_risks:
        recommended_fixes.append("Remove scarcity or discount claims unless they are verified by store data.")
    if uk_market_risks:
        recommended_fixes.append("For UK market, substantiate pricing/free/clinical claims or remove them.")
    if finance_risks:
        recommended_fixes.append("Remove guaranteed returns, risk-free language, direct buy-now pressure, or individualized financial advice.")

    fail_reasons = (
        unsupported_claims
        + fake_review_risks
        + trademark_risks
        + medical_risks
        + scarcity_risks
        + discount_risks
        + avatar_personal_claims
        + finance_risks
    )
    if fail_reasons:
        status = "fail"
        risk_level = "high"
    elif platform_policy_risks or uk_market_risks or trademark_warnings:
        status = "warning"
        risk_level = "medium"
    else:
        status = "pass"
        risk_level = "low"

    return {
        "compliance_status": status,
        "risk_level": risk_level,
        "unsupported_claims": sorted(set(unsupported_claims + medical_risks + scarcity_risks + discount_risks)),
        "fake_review_risks": sorted(set(fake_review_risks + avatar_personal_claims)),
        "trademark_risks": sorted(set(trademark_risks)),
        "trademark_warnings": sorted(set(trademark_warnings)),
        "platform_policy_risks": sorted(set(platform_policy_risks)),
        "uk_market_risks": sorted(set(uk_market_risks)),
        "finance_risks": sorted(set(finance_risks)),
        "recommended_fixes": recommended_fixes,
    }


def _is_soft_product_brand_warning(value: str) -> bool:
    return value.strip().lower() == "possible unverified brand or luxury implication"


def _positive_generated_brand_risks(text: str) -> list[str]:
    return find_pattern_matches(
        text,
        [
            r"\bluxury\s+(designer|handbag|tote|bag|product|look|style|ad)\b",
            r"\bdesigner\s+(handbag|tote|bag|product|look|style|ad)\b",
            r"\bfamous[- ]brand\b",
        ],
    )


def _remove_negative_prompt_language(text: str) -> str:
    text = re.sub(r"data:image/[^\"']+", "", text, flags=re.IGNORECASE)
    text = re.sub(r'"negative_prompt"\s*:\s*"[^"]*"', "", text, flags=re.IGNORECASE)
    text = re.sub(r"Negative prompt:.*?(?=(Variation|$))", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"Do not [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAvoid [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNever [^.]+[.]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNo [^.]+[.]", "", text, flags=re.IGNORECASE)
    return text


def _remove_safety_context_language(text: str) -> str:
    medical_terms = (
        r"medical|health|therapeutic|orthop(a|ae)dic|pain[- ]?free|"
        r"cure[sd]?|treats?|heals?|doctor[- ]?recommended"
    )
    commercial_terms = (
        r"limited[- ]stock|only\s+\d+\s+left|selling\s+out|last\s+chance|"
        r"limited\s+time|fake\s+scarcity|scarcity|discounts?|slevy|sleva|"
        r"odpocet|odpo[cč]et|countdown|deadline|flash\s+sale|free\s+today|"
        r"\d+%\s+off|was\s+\$?\d+"
    )
    risky_terms = f"{medical_terms}|{commercial_terms}"
    negation = (
        r"without|no|avoid(?:s|ing)?|do not|don't|never|not|remove|forbidden|"
        r"nepou[zž][ií]vej|nepou[zž][ií]vat|nepouzivej|nepouzivat|"
        r"[zž][aá]dn[aáeéyý]?|bez|zak[aá]zan[eéyý]?|zakaz|zak[aá]zat"
    )
    text = re.sub(
        rf"\b(?:{negation})\b[^.{{}}\"']{{0,180}}\b(?:{risky_terms})\b[^.{{}}\"']{{0,140}}",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"\b(?:{risky_terms})\b[^.{{}}\"']{{0,140}}\b(?:claims?|labels?|effects?|benefits?)\b[^.{{}}\"']{{0,80}}\b(?:are\s+)?(?:not|forbidden|removed|unsafe)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"\b(?:{commercial_terms})\b[^.{{}}\"']{{0,140}}\b(?:claims?|wording|language|phrases?|patterns?|rules?)\b[^.{{}}\"']{{0,80}}\b(?:are\s+)?(?:not|forbidden|removed|unsafe|disallowed)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _remove_instructional_treat_language(text: str) -> str:
    """Do not treat prompt-control wording as medical treatment claims."""

    patterns = [
        r"\bdo\s+not\s+treat\b[^.{}\"']{0,220}",
        r"\bnever\s+treat\b[^.{}\"']{0,220}",
        r"\btreat\s+(?:planned\s+)?on_screen_text\b[^.{}\"']{0,220}",
        r"\btreat\s+competitor\s+inputs\b[^.{}\"']{0,220}",
        r"\btreat\s+(?:product_info|internal_brief_notes|product\s+names?|colou?rs?|garment\s+specifics|object|room|clothing\s+detail|prop|reference|image|note|this|that|it|them)\b[^.{}\"']{0,220}",
        r"\btreat\s+[^.{}\"']{0,120}\s+as\s+(?:internal|examples?|product-only|guidance|source\s+of\s+truth)\b[^.{}\"']{0,160}",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text
