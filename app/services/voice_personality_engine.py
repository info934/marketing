from __future__ import annotations

from typing import Any

from app.services.localization_utils import is_german, language_safe_voice_descriptor
from app.services.text_utils import sanitize_avatar_descriptor


def generate(
    avatar: dict[str, Any],
    product_analysis: dict[str, Any],
    audience_research: dict[str, Any],
    emotional_angle: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    language = str(settings.get("language") or "en")
    market = str(settings.get("market") or "US").upper()
    category = str(product_analysis.get("likely_product_category") or "product")
    archetype = str(audience_research.get("primary_archetype") or "careful shopper")
    angle = str(emotional_angle.get("primary_angle") or "curiosity")
    voice_bias = emotional_angle.get("voice_bias") or {}
    avatar_voice = language_safe_voice_descriptor(
        sanitize_avatar_descriptor(avatar.get("voice")),
        language,
    )
    accent = _accent_profile(language, market)
    creator_style = _creator_style(category, archetype, angle)
    tone = _tone(angle, avatar_voice)
    energy = _energy(angle)
    confidence = voice_bias.get("confidence") or _confidence(angle)
    pacing = voice_bias.get("pacing") or "medium conversational pacing"
    gesture_style = voice_bias.get("gesture") or "small natural hand gestures"
    return {
        "agent": "Voice Personality Engine",
        "language": language,
        "market": market,
        "accent_profile": accent,
        "tone": tone,
        "energy": energy,
        "confidence": confidence,
        "creator_style": creator_style,
        "pacing": pacing,
        "gesture_style": gesture_style,
        "subtitle_style": _subtitle_style(language, angle),
        "hook_delivery": _hook_delivery(angle),
        "spoken_delivery_rules": [
            "Use first-person creator delivery only when testimonial rules allow it",
            "Keep phrasing conversational and slightly imperfect, not broadcast",
            "Match market vocabulary and accent cues",
            "Keep spoken lines, post-production captions, hooks, gestures, and pacing consistent across scenes",
        ],
        "prompt_fragment": _prompt_fragment(
            language=language,
            accent=accent,
            tone=tone,
            energy=energy,
            confidence=confidence,
            creator_style=creator_style,
            pacing=pacing,
            gesture_style=gesture_style,
        ),
    }


def _accent_profile(language: str, market: str) -> str:
    value = language.lower()
    if value.startswith("en") and market in {"UK", "GB", "GBR"}:
        return "subtle everyday British accent, British phrasing, not American"
    if value.startswith("en") and market in {"US", "USA"}:
        return "natural American English accent"
    if value.startswith(("cs", "cz")):
        return "natural Czech accent and phrasing"
    if is_german(language):
        return "natural German accent and phrasing"
    return f"natural accent and phrasing for market {market}"


def _creator_style(category: str, archetype: str, angle: str) -> str:
    if category in {"handbag", "apparel"} and archetype in {"fashion", "elegance", "aesthetic"}:
        return "style-aware friend, polished but still casual"
    if angle in {"convenience", "fear"}:
        return "practical girl-next-door product checker"
    if angle == "status":
        return "quietly polished everyday creator"
    return "girl-next-door product explainer"


def _tone(angle: str, avatar_voice: str) -> str:
    if avatar_voice:
        return f"warm, {avatar_voice}"
    return {
        "fear": "calm and reassuring",
        "aspiration": "warm and lightly aspirational",
        "identity": "relatable and knowing",
        "convenience": "practical and clear",
        "status": "warm and quietly confident",
        "curiosity": "curious and conversational",
        "transformation": "observational and grounded",
    }.get(angle, "warm and conversational")


def _energy(angle: str) -> str:
    return {
        "fear": "low-medium",
        "aspiration": "medium",
        "identity": "medium",
        "convenience": "medium",
        "status": "low-medium",
        "curiosity": "medium-high in hook, medium after",
        "transformation": "medium",
    }.get(angle, "medium")


def _confidence(angle: str) -> str:
    return {
        "fear": "casual reassurance",
        "aspiration": "soft confidence",
        "identity": "casual confidence",
        "convenience": "practical confidence",
        "status": "quiet confidence",
        "curiosity": "curious confidence",
        "transformation": "observational confidence",
    }.get(angle, "casual confidence")


def _subtitle_style(language: str, angle: str) -> str:
    if language.lower().startswith(("cs", "cz")):
        return "short Czech captions, natural spoken wording, no hype"
    if is_german(language):
        return "short German captions, natural spoken wording, no hype, avoid long compound text overlays"
    if angle == "curiosity":
        return "short punchy captions that preserve the question or detail reveal"
    return "short conversational captions, British spelling when market is UK"


def _hook_delivery(angle: str) -> str:
    return {
        "fear": "start calm, like a useful warning from a friend",
        "aspiration": "start warm, visual-first, with a small smile",
        "identity": "start like calling out someone who shops carefully",
        "convenience": "start with a practical check someone can copy",
        "status": "start understated and polished, no bragging",
        "curiosity": "start with a lean-in question and quick product glance",
        "transformation": "start with a before-check versus after-check contrast",
    }.get(angle, "start naturally and directly")


def _prompt_fragment(
    language: str,
    accent: str,
    tone: str,
    energy: str,
    confidence: str,
    creator_style: str,
    pacing: str,
    gesture_style: str,
) -> str:
    return (
        f"Voice personality: language={language}, accent={accent}, tone={tone}, energy={energy}, "
        f"confidence={confidence}, creator_style={creator_style}, pacing={pacing}, gestures={gesture_style}"
    )
