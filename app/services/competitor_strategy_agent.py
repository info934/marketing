from __future__ import annotations

import re
from typing import Any


VERSION = "competitor_strategy_chat_v1"

SYSTEM_PROMPT = """
You are a Competitor Strategy Agent for ecommerce ad generation.

Your job is not to copy competitor ads. Your job is to identify strategic patterns and translate them into original creative direction for the user's own product.

Find:
- the main hook pattern
- the problem or desire being opened
- the benefit being sold
- the visual style and shot pattern
- the offer or CTA pattern
- the audience signal
- the objections the ad tries to reduce

Then create an original adaptation brief for our product:
- keep the strategic lesson
- rewrite all copy in our own language
- use only our verified product facts
- do not copy slogans, layouts, logos, brand names, characters, trademarks, claims, or confusingly similar visual identity
- do not make direct competitor comparisons unless the user explicitly provides permitted comparison claims

Output structured strategy only. Treat competitor inputs as temporary context for this generation run.
""".strip()

FAMILY_KEYWORDS = {
    "Pain": [
        "problem",
        "pain",
        "struggle",
        "annoying",
        "frustrating",
        "tired",
        "hard to",
        "chybi",
        "problem",
        "nejist",
        "frustr",
    ],
    "Desire": [
        "elegant",
        "style",
        "beautiful",
        "upgrade",
        "aesthetic",
        "clean",
        "minimal",
        "everyday",
        "wish",
        "want",
        "fits",
    ],
    "Proof": [
        "detail",
        "texture",
        "stitching",
        "inside",
        "capacity",
        "review",
        "proof",
        "close",
        "before after",
        "demo",
        "show",
    ],
    "Identity": [
        "for people",
        "for women",
        "busy",
        "minimalist",
        "professional",
        "student",
        "mum",
        "people who",
        "those who",
    ],
    "Contrarian": [
        "not",
        "unlike",
        "stop",
        "less",
        "no hype",
        "instead",
        "without",
        "skip",
        "neslib",
    ],
    "Urgency": [
        "today",
        "now",
        "limited",
        "before",
        "quick",
        "seconds",
        "scroll",
        "available",
        "shop",
    ],
}

VISUAL_KEYWORDS = [
    "ugc",
    "creator",
    "mirror",
    "close-up",
    "close up",
    "handheld",
    "home",
    "lifestyle",
    "flatlay",
    "carousel",
    "before after",
    "demo",
    "unboxing",
    "outfit",
    "minimal",
]

CTA_KEYWORDS = [
    "shop",
    "buy",
    "order",
    "try",
    "discover",
    "learn more",
    "available",
    "today",
    "now",
    "delivery",
]


def analyze(
    *,
    enabled: bool,
    competitor_name: str = "",
    competitor_url: str = "",
    competitor_chat_brief: str = "",
    competitor_screenshot_notes: str = "",
    screenshot_assets: list[dict[str, Any]] | None = None,
    product_analysis: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = _clean_text("\n".join([competitor_name, competitor_url, competitor_chat_brief, competitor_screenshot_notes]))
    screenshots = screenshot_assets or []
    if not enabled and not text and not screenshots:
        return {
            "version": VERSION,
            "status": "disabled",
            "enabled": False,
            "system_prompt": SYSTEM_PROMPT,
            "rule": "Competitor inputs are ignored unless the run enables competitor strategy mode.",
        }
    if not text and not screenshots:
        return {
            "version": VERSION,
            "status": "empty",
            "enabled": bool(enabled),
            "system_prompt": SYSTEM_PROMPT,
            "rule": "No competitor chat, URL, notes, or screenshots were supplied.",
        }

    product = product_analysis or {}
    config = settings or {}
    family_bias = _family_bias(text)
    strategic_patterns = _strategic_patterns(text)
    hook_patterns = _line_patterns(competitor_chat_brief, limit=6)
    visual_patterns = _keyword_patterns(text, VISUAL_KEYWORDS, fallback=["product-led UGC", "natural lifestyle context"])
    cta_patterns = _keyword_patterns(text, CTA_KEYWORDS, fallback=["clear ecommerce CTA"])
    offer_patterns = _offer_patterns(text)
    risk_terms = _risk_terms(competitor_name, text)
    top_family = max(family_bias.items(), key=lambda item: item[1])[0] if family_bias else "Proof"
    product_name = str(product.get("product_name") or config.get("product_name") or "our product").strip()
    category = str(product.get("likely_product_category") or config.get("product_category") or "product").strip()
    adaptation_brief = _adaptation_brief(
        product_name=product_name,
        category=category,
        top_family=top_family,
        strategic_patterns=strategic_patterns,
        visual_patterns=visual_patterns,
        cta_patterns=cta_patterns,
    )
    return {
        "version": VERSION,
        "status": "ready",
        "enabled": bool(enabled),
        "system_prompt": SYSTEM_PROMPT,
        "input_summary": {
            "competitor_name": _clip(competitor_name, 120),
            "competitor_url": _clip(competitor_url, 300),
            "chat_chars": len(competitor_chat_brief or ""),
            "screenshot_note_chars": len(competitor_screenshot_notes or ""),
            "screenshot_count": len(screenshots),
            "screenshot_assets": screenshots[:8],
        },
        "strategy_extraction": {
            "primary_angle_family": top_family,
            "angle_family_bias": family_bias,
            "strategic_patterns": strategic_patterns,
            "hook_patterns": hook_patterns,
            "visual_patterns": visual_patterns,
            "offer_patterns": offer_patterns,
            "cta_patterns": cta_patterns,
            "objection_patterns": _objection_patterns(text),
            "audience_signals": _audience_signals(text),
        },
        "selector_bias": {
            "families": family_bias,
            "hook_patterns": hook_patterns + strategic_patterns,
            "visual_patterns": visual_patterns,
            "cta_patterns": cta_patterns,
            "confidence": "low",
            "rule": "Use as a weak strategic bias for this run only; product facts, memory, compliance, and slot role remain stronger.",
        },
        "adaptation_brief": adaptation_brief,
        "originality_guard": {
            "status": "active",
            "do_not_copy_terms": risk_terms[:12],
            "rules": [
                "Do not copy exact competitor wording, slogans, layouts, logos, or brand codes.",
                "Do not use competitor brand names inside generated customer-facing ad copy.",
                "Use competitor patterns only as abstract strategy, not as visual reference for generation.",
                "Do not make direct comparative claims unless explicitly permitted by the user.",
            ],
        },
        "temporary_context_only": True,
    }


def _family_bias(text: str) -> dict[str, int]:
    lowered = text.lower()
    scores = {}
    for family, keywords in FAMILY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score:
            scores[family] = min(5, score)
    if not scores:
        scores = {"Proof": 2, "Desire": 1}
    return {family: scores[family] for family in sorted(scores, key=scores.get, reverse=True)}


def _strategic_patterns(text: str) -> list[str]:
    lowered = text.lower()
    patterns = []
    if any(word in lowered for word in ["hook", "first", "zacatek", "scroll", "attention"]):
        patterns.append("strong first-frame hook")
    if any(word in lowered for word in ["problem", "pain", "frustr", "chybi", "struggle"]):
        patterns.append("open with buyer friction")
    if any(word in lowered for word in ["capacity", "inside", "fits", "demo", "ukaz", "show"]):
        patterns.append("demonstrate the product in use")
    if any(word in lowered for word in ["detail", "texture", "stitch", "material", "close"]):
        patterns.append("prove quality through close detail")
    if any(word in lowered for word in ["lifestyle", "outfit", "home", "mirror", "routine"]):
        patterns.append("place product in a believable routine")
    if any(word in lowered for word in ["cta", "shop", "available", "delivery", "today"]):
        patterns.append("end with a clear low-friction CTA")
    return patterns[:8] or ["extract competitor messaging structure without copying it"]


def _line_patterns(value: str, *, limit: int) -> list[str]:
    result = []
    for line in str(value or "").splitlines():
        cleaned = _clean_text(line.strip(" -#*\t"))
        if len(cleaned) < 8:
            continue
        if _looks_like_url(cleaned):
            continue
        result.append(_clip(cleaned, 120))
        if len(result) >= limit:
            break
    return _unique(result)


def _keyword_patterns(text: str, keywords: list[str], *, fallback: list[str]) -> list[str]:
    lowered = text.lower()
    found = [keyword for keyword in keywords if keyword in lowered]
    return _unique(found[:8] or fallback)


def _offer_patterns(text: str) -> list[str]:
    lowered = text.lower()
    patterns = []
    if "free" in lowered and "delivery" in lowered:
        patterns.append("free delivery offer pattern")
    if "limited" in lowered or "stock" in lowered:
        patterns.append("scarcity/availability pattern; only use if verified for our product")
    if "bundle" in lowered:
        patterns.append("bundle offer pattern")
    if "discount" in lowered or "%" in lowered:
        patterns.append("discount pattern; only use if verified for our product")
    return patterns[:6]


def _objection_patterns(text: str) -> list[str]:
    lowered = text.lower()
    patterns = []
    if any(word in lowered for word in ["quality", "material", "texture", "stitch"]):
        patterns.append("quality/material doubt")
    if any(word in lowered for word in ["fits", "capacity", "inside", "size"]):
        patterns.append("capacity/size doubt")
    if any(word in lowered for word in ["price", "expensive", "worth"]):
        patterns.append("price/value doubt")
    if any(word in lowered for word in ["delivery", "returns", "shipping"]):
        patterns.append("delivery/returns friction")
    return patterns[:6]


def _audience_signals(text: str) -> list[str]:
    lowered = text.lower()
    signals = []
    for phrase in ["women", "busy", "professional", "minimalist", "student", "travel", "work", "everyday", "scandinavian", "uk"]:
        if phrase in lowered:
            signals.append(phrase)
    return signals[:8]


def _risk_terms(competitor_name: str, text: str) -> list[str]:
    terms = []
    name = _clean_text(competitor_name)
    if name:
        terms.append(name)
    quoted = re.findall(r"['\"]([^'\"]{8,80})['\"]", text)
    terms.extend(_clip(item, 100) for item in quoted)
    for line in _line_patterns(text, limit=8):
        if len(line.split()) <= 14:
            terms.append(line)
    return _unique(terms)


def _adaptation_brief(
    *,
    product_name: str,
    category: str,
    top_family: str,
    strategic_patterns: list[str],
    visual_patterns: list[str],
    cta_patterns: list[str],
) -> str:
    strategy = ", ".join(strategic_patterns[:3])
    visuals = ", ".join(visual_patterns[:3])
    cta = ", ".join(cta_patterns[:2])
    return (
        f"Create an original {top_family.lower()}-leaning ecommerce ad set for {product_name}. "
        f"Use the competitor input only as strategy: {strategy}. "
        f"Translate that into our own {category} creative with product-first proof, believable UGC/lifestyle context, "
        f"and visual direction inspired only at the pattern level ({visuals}). "
        f"CTA pattern may be {cta}, but only with verified claims and our own wording."
    )


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", "\n").split())


def _clip(value: Any, limit: int) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://")) or "." in value and " " not in value


def _unique(values: list[Any]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = _clean_text(value)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
