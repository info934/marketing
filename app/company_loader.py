from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app import config
from app.services.text_utils import safe_slug


BASE_COMPANY_DEFAULTS = {
    "id": "",
    "name": "",
    "ad_vertical": "ads",
    "business_model": "",
    "market": config.DEFAULT_MARKET,
    "language": config.DEFAULT_LANGUAGE,
    "default_platform": config.DEFAULT_PLATFORM,
    "creative_channels": [],
    "product_categories": [],
    "audience": "",
    "positioning": "",
    "brand_voice": "",
    "proof_points": [],
    "forbidden_claims": [],
    "compliance_notes": "",
    "creative_quality_rules": [],
    "notes": "",
    "is_default": False,
}


DEFAULT_COMPANY = {
    **BASE_COMPANY_DEFAULTS,
    "id": "kimlondon",
    "name": "Kimlondon",
    "ad_vertical": "fashion_ecommerce",
    "business_model": "dropshipping",
    "market": "UK",
    "language": "en",
    "default_platform": "meta",
    "creative_channels": ["meta", "instagram", "tiktok"],
    "product_categories": ["apparel", "handbags", "shoes"],
    "audience": "UK shoppers comparing practical fashion, handbags, and shoes through believable creator proof.",
    "positioning": "Accessible fashion and accessories shown in honest everyday contexts instead of luxury catalogue styling.",
    "brand_voice": "British English, direct, natural, practical, low-hype, and buyer-proof.",
    "proof_points": [
        "real worn or carried context",
        "visible scale, fit, shape, and detail proof",
        "ordinary daily scenes for UK shoppers",
    ],
    "forbidden_claims": [
        "invented reviews or ratings",
        "fake discounts or fake scarcity",
        "unverified material, comfort, or performance claims",
        "luxury brand or designer implications",
    ],
    "compliance_notes": "Use only supplied product facts. Keep dropshipping creatives realistic and do not imply verified UK stock, delivery time, reviews, or discounts unless provided.",
    "creative_quality_rules": [
        "make every ad angle visibly different",
        "show practical proof before aesthetic polish",
        "avoid catalogue-looking images",
        "prefer believable creator scenes over generic brand ads",
    ],
    "notes": "Default brand profile for ads creative generation.",
    "is_default": True,
}


LIST_FIELDS = {
    "product_categories",
    "creative_channels",
    "proof_points",
    "forbidden_claims",
    "creative_quality_rules",
    "target_locations",
}


def list_companies() -> list[dict[str, Any]]:
    companies = _read_company_registry(config.COMPANY_DATA_PATH)
    if not companies:
        return [DEFAULT_COMPANY]
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for company in companies:
        merged = _merge_company_defaults(company)
        company_id = str(merged.get("id") or "").strip() or safe_slug(str(merged.get("name") or ""), "company")
        if company_id in seen:
            continue
        seen.add(company_id)
        merged["id"] = company_id
        result.append(merged)
    return result


def default_company_id() -> str:
    companies = list_companies()
    for company in companies:
        if company.get("is_default"):
            return str(company.get("id") or DEFAULT_COMPANY["id"])
    return str((companies[0] if companies else DEFAULT_COMPANY).get("id") or DEFAULT_COMPANY["id"])


def load_company(company_id: str | None, inline_company: str | None = None) -> dict[str, Any]:
    if inline_company:
        try:
            company = json.loads(inline_company)
            if isinstance(company, dict):
                return _merge_company_defaults(company)
        except json.JSONDecodeError:
            pass
    requested_id = (company_id or "").strip()
    if requested_id:
        for company in list_companies():
            if company.get("id") == requested_id:
                return _merge_company_defaults(company)
    return {}


def upsert_company(profile: dict[str, Any]) -> dict[str, Any]:
    companies = list_companies()
    clean = _clean_company(profile)
    company_id = str(clean.get("id") or "").strip()
    if not company_id:
        raise ValueError("Company id is required")
    now = _timestamp()
    found = False
    for index, company in enumerate(companies):
        if company.get("id") == company_id:
            clean["created_at"] = company.get("created_at") or clean.get("created_at") or now
            clean["updated_at"] = now
            clean["is_default"] = bool(clean.get("is_default") or company.get("is_default"))
            companies[index] = {**company, **clean}
            found = True
            break
    if not found:
        clean["created_at"] = clean.get("created_at") or now
        clean["updated_at"] = now
        companies.append(clean)
    if clean.get("is_default"):
        companies = _with_single_default(companies, company_id)
    _write_company_registry(config.COMPANY_DATA_PATH, companies)
    return load_company(company_id)


def set_default_company(company_id: str) -> dict[str, Any]:
    companies = list_companies()
    if not any(company.get("id") == company_id for company in companies):
        raise ValueError(f"Unknown company_id: {company_id}")
    companies = _with_single_default(companies, company_id)
    _write_company_registry(config.COMPANY_DATA_PATH, companies)
    return load_company(company_id)


def company_context(profile: dict[str, Any]) -> dict[str, Any]:
    if not profile:
        return {}
    return {
        "company_id": profile.get("id"),
        "company_name": profile.get("name"),
        "ad_vertical": profile.get("ad_vertical"),
        "business_model": profile.get("business_model"),
        "market": profile.get("market"),
        "language": profile.get("language"),
        "default_platform": profile.get("default_platform"),
        "creative_channels": profile.get("creative_channels") or [],
        "product_categories": profile.get("product_categories") or [],
        "audience": profile.get("audience"),
        "positioning": profile.get("positioning"),
        "brand_voice": profile.get("brand_voice"),
        "proof_points": profile.get("proof_points") or [],
        "forbidden_claims": profile.get("forbidden_claims") or [],
        "creative_quality_rules": profile.get("creative_quality_rules") or [],
        "compliance_notes": profile.get("compliance_notes"),
        "landing_page_url": profile.get("landing_page_url"),
        "website_url": profile.get("website_url"),
        "default_avatar_id": profile.get("default_avatar_id"),
    }


def company_context_text(profile: dict[str, Any]) -> str:
    context = company_context(profile)
    if not context:
        return ""
    parts = [
        f"Brand/client: {context.get('company_name')} ({context.get('ad_vertical') or 'ads'}; {context.get('business_model') or 'business'}).",
        f"Market/language/platform defaults: {context.get('market') or '-'} / {context.get('language') or '-'} / {context.get('default_platform') or '-'}.",
    ]
    channels = context.get("creative_channels") or []
    if channels:
        parts.append("Primary ad channels: " + ", ".join(str(item) for item in channels[:6]) + ".")
    categories = context.get("product_categories") or []
    if categories:
        parts.append("Ad category focus: " + ", ".join(str(item) for item in categories[:8]) + ".")
    for label, key in [
        ("Audience", "audience"),
        ("Positioning", "positioning"),
        ("Brand voice", "brand_voice"),
        ("Compliance", "compliance_notes"),
    ]:
        value = str(context.get(key) or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    proof = context.get("proof_points") or []
    if proof:
        parts.append("Proof points to prefer: " + ", ".join(str(item) for item in proof[:6]) + ".")
    quality_rules = context.get("creative_quality_rules") or []
    if quality_rules:
        parts.append("Creative quality rules: " + ", ".join(str(item) for item in quality_rules[:6]) + ".")
    forbidden = context.get("forbidden_claims") or []
    if forbidden:
        parts.append("Forbidden claims: " + ", ".join(str(item) for item in forbidden[:8]) + ".")
    return "\n".join(parts)[:2500]


def _read_company_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return [DEFAULT_COMPANY]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [DEFAULT_COMPANY]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return [DEFAULT_COMPANY]


def _write_company_registry(path: Path, companies: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(companies, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge_company_defaults(company: dict[str, Any]) -> dict[str, Any]:
    merged = {**BASE_COMPANY_DEFAULTS, **company}
    for field in LIST_FIELDS:
        merged[field] = _clean_list(merged.get(field))
    return merged


def _clean_company(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "id",
        "name",
        "legal_name",
        "ad_vertical",
        "business_model",
        "market",
        "language",
        "default_platform",
        "creative_channels",
        "website_url",
        "landing_page_url",
        "product_categories",
        "audience",
        "positioning",
        "brand_voice",
        "proof_points",
        "forbidden_claims",
        "creative_quality_rules",
        "compliance_notes",
        "target_locations",
        "default_avatar_id",
        "notes",
        "is_default",
        "created_at",
        "updated_at",
    }
    clean = {key: value for key, value in profile.items() if key in allowed and value not in (None, "")}
    name = str(clean.get("name") or "").strip()
    company_id = str(clean.get("id") or "").strip() or safe_slug(name, "company")
    clean["id"] = safe_slug(company_id, "company")
    clean["name"] = name or clean["id"]
    clean["ad_vertical"] = str(clean.get("ad_vertical") or "ads").strip().lower()
    clean["business_model"] = str(clean.get("business_model") or "").strip()
    clean["market"] = str(clean.get("market") or config.DEFAULT_MARKET).strip().upper()
    clean["language"] = str(clean.get("language") or config.DEFAULT_LANGUAGE).strip().lower()
    clean["default_platform"] = str(clean.get("default_platform") or config.DEFAULT_PLATFORM).strip().lower()
    for field in LIST_FIELDS:
        clean[field] = _clean_list(clean.get(field))
    return clean


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value or "").replace("\r", "\n").replace(",", "\n").split("\n")
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item or "").strip(" -\t\r\n")
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text[:180])
    return result[:20]


def _with_single_default(companies: list[dict[str, Any]], company_id: str) -> list[dict[str, Any]]:
    return [{**company, "is_default": company.get("id") == company_id} for company in companies]


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
