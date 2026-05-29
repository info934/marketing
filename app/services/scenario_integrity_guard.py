from __future__ import annotations

import re
from typing import Any

from app.services import scenario_contract


def check(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    avatar: dict[str, Any],
    ads_creative_set: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lock = content_prompt_package.get("user_scenario_lock") or ugc_strategy.get("user_scenario_lock") or {}
    if not isinstance(lock, dict) or not lock.get("enabled"):
        return _result("passed", [])

    contract = scenario_contract.build(lock, avatar=avatar, product_analysis=product_analysis)
    raw = _norm(lock.get("raw_user_direction") or "")
    prompt = _norm(
        " ".join(
            str(value or "")
            for value in [
                content_prompt_package.get("seedance_video_prompt"),
                (content_prompt_package.get("seedance_payload") or {}).get("prompt"),
            ]
        )
    )
    category = str(product_analysis.get("likely_product_category") or "").strip().lower()
    failures: list[dict[str, str]] = []

    failures.extend(
        scenario_contract.validate_text(
            prompt,
            contract,
            scope="video",
            location="Final video prompt",
        )
    )

    if category != "apparel" and "apparel full-body worn view required" in prompt:
        failures.append(
            _failure(
                "scenario_wrong_category_prompt",
                "Video prompt contains an apparel try-on instruction for a non-apparel product.",
                "Regenerate the prompt package; do not call video or image providers with this prompt.",
            )
        )

    if _looks_like_parent_mom_scenario(raw):
        if not _contains_any(prompt, ["mom", "mother", "mum", "parent", "diaper", "diapers", "wipes"]):
            failures.append(
                _failure(
                    "scenario_mom_context_missing",
                    "User scenario is a mom/parent routine, but the final video prompt lost that context.",
                    "Keep the approved mom/parent scenario in the final prompt or block generation.",
                )
            )
        if _contains_any(raw, ["diaper", "diapers", "wipes"]) and not _contains_any(prompt, ["diaper", "diapers", "wipes"]):
            failures.append(
                _failure(
                    "scenario_parent_items_missing",
                    "User scenario includes diaper/wipes proof, but the final video prompt no longer includes those items.",
                    "Preserve the approved product-proof items before generating.",
                )
            )

    if _contains_any(raw, ["handheld iphone", "front camera", "phone selfie"]) and not _contains_any(
        prompt, ["handheld", "iphone", "phone", "selfie"]
    ):
        failures.append(
            _failure(
                "scenario_camera_style_missing",
                "User scenario asks for handheld phone/selfie style, but the final prompt lost the camera style.",
                "Preserve the approved camera style before generating.",
            )
        )

    scenario_gender = _scenario_gender(raw)
    avatar_gender = _avatar_gender(avatar)
    if scenario_gender and avatar_gender and scenario_gender != avatar_gender:
        failures.append(
            _failure(
                "scenario_avatar_gender_conflict",
                f"User scenario expects {scenario_gender}, but the selected avatar profile reads as {avatar_gender}.",
                "Choose a matching avatar or adjust the approved scenario before generating.",
            )
        )

    ad_text = _static_prompt_text(ads_creative_set or {})
    if ad_text:
        failures.extend(
            scenario_contract.validate_text(
                ad_text,
                contract,
                scope="static_set",
                location="Static creative prompts",
            )
        )
    expected_static_gender = avatar_gender or scenario_gender
    contract_with_gender = dict(contract)
    if expected_static_gender and not contract_with_gender.get("subject_gender"):
        contract_with_gender["subject_gender"] = expected_static_gender
    if ad_text:
        failures.extend(scenario_contract.validate_static_gender(ad_text, contract_with_gender))

    return _result("failed" if failures else "passed", _dedupe_failures(failures), contract=contract)


def provider_check(result: dict[str, Any]) -> dict[str, Any]:
    status = "failed" if result.get("status") == "failed" else "passed"
    return {
        "id": "scenario_integrity_guard",
        "status": status,
        "reason": result.get("reason") or "User scenario integrity passed.",
        "next_step": result.get("next_step"),
        "details": result.get("failures") or [],
    }


def _result(status: str, failures: list[dict[str, str]], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "failures": failures,
        "scenario_contract": contract or {"enabled": False},
        "reason": "; ".join(item["reason"] for item in failures) if failures else None,
        "next_step": (
            "Generation was blocked before provider calls because the final prompts no longer matched the approved scenario."
            if failures
            else None
        ),
    }


def _failure(check_id: str, reason: str, next_step: str) -> dict[str, str]:
    return {"id": check_id, "reason": reason, "next_step": next_step}


def _dedupe_failures(failures: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    deduped: list[dict[str, str]] = []
    for failure in failures:
        key = (failure.get("id"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)
    return deduped


def _static_prompt_text(ads_creative_set: dict[str, Any]) -> str:
    parts: list[str] = []
    for creative in ads_creative_set.get("static_image_ads") or []:
        parts.append(str(creative.get("visual_prompt") or ""))
        parts.append(str(creative.get("static_subject_lock") or ""))
    carousel = ads_creative_set.get("carousel_ad") or {}
    parts.append(str(carousel.get("static_subject_lock") or ""))
    for card in carousel.get("cards") or []:
        parts.append(str(card.get("visual_prompt") or ""))
        parts.append(str(card.get("static_subject_lock") or ""))
    return _norm(" ".join(parts))


def _looks_like_parent_mom_scenario(text: str) -> bool:
    return _contains_any(text, ["mom", "mother", "mum", "mama", "diaper", "diapers", "wipes"])


def _scenario_gender(text: str) -> str:
    if _contains_any(text, ["mom", "mother", "mum", "mama", "woman", "female", "she ", " her "]):
        return "female"
    if _contains_any(text, ["dad", "father", "man", "male", "he ", " him "]):
        return "male"
    return ""


def _avatar_gender(avatar: dict[str, Any]) -> str:
    text = _norm(
        " ".join(
            str(avatar.get(key) or "")
            for key in ["gender", "presenting_gender", "style", "persona", "appearance", "voice", "identity_note", "name"]
        )
    )
    if _contains_any(text, ["female", "woman", "female-presenting", "creatorin", "žena", "zena"]):
        return "female"
    if _contains_any(text, ["male", "man", "male-presenting", "muž", "muz"]):
        return "male"
    return ""


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()
