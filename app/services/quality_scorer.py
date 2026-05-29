from __future__ import annotations

from typing import Any


def score(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    product_fidelity_result: dict[str, Any],
    compliance_result: dict[str, Any],
) -> dict[str, Any]:
    product_fidelity_score = 100
    product_fidelity_score -= 20 * len(product_fidelity_result.get("changed_or_invented_details", []))
    product_fidelity_score -= 25 * len(product_fidelity_result.get("missing_fidelity_instructions", []))
    product_fidelity_score = _clamp(product_fidelity_score)

    compliance_score = 100
    compliance_score -= 25 * len(compliance_result.get("unsupported_claims", []))
    compliance_score -= 25 * len(compliance_result.get("fake_review_risks", []))
    compliance_score -= 20 * len(compliance_result.get("trademark_risks", []))
    compliance_score -= 10 * len(compliance_result.get("trademark_warnings", []))
    compliance_score -= 10 * len(compliance_result.get("platform_policy_risks", []))
    compliance_score = _clamp(compliance_score)

    ugc_authenticity_score = 92 if "corporate" not in ugc_strategy.get("tone", "").lower() else 75
    ad_conversion_score = 88 if ugc_strategy.get("hook") and ugc_strategy.get("cta") else 70
    platform_fit_score = 95 if ugc_strategy.get("aspect_ratio") and "safe_area" in ugc_strategy.get("platform_adaptation", {}) else 82
    clarity_score = 94 if product_analysis.get("safe_benefits") and ugc_strategy.get("scene_by_scene_script") else 78
    prompt_engineering_score = 96
    prompt_text = content_prompt_package.get("seedance_video_prompt", "")
    for required in ["strict visual reference", "Negative prompt", "Aspect ratio"]:
        if required not in prompt_text:
            prompt_engineering_score -= 12
    prompt_engineering_score -= _visual_template_penalty(product_analysis, ugc_strategy)
    prompt_engineering_score -= _category_prompt_penalty(product_analysis, prompt_text, content_prompt_package)
    prompt_engineering_score = _clamp(prompt_engineering_score)

    scores = {
        "product_fidelity_score": product_fidelity_score,
        "ugc_authenticity_score": ugc_authenticity_score,
        "ad_conversion_score": ad_conversion_score,
        "platform_fit_score": platform_fit_score,
        "compliance_score": compliance_score,
        "clarity_score": clarity_score,
        "prompt_engineering_score": prompt_engineering_score,
    }
    overall_quality_score = int(round(sum(scores.values()) / len(scores)))
    export_status = "approved"
    if (
        product_fidelity_result.get("product_fidelity_status") == "fail"
        or compliance_result.get("compliance_status") == "fail"
    ):
        export_status = "blocked"
    elif overall_quality_score < 90 or compliance_result.get("compliance_status") == "warning":
        export_status = "warning"

    recommended_improvements = []
    if product_fidelity_score < 95:
        recommended_improvements.append("Improve product fidelity wording.")
    if compliance_score < 90:
        recommended_improvements.append("Remove risky claims and replace with safer wording.")
    if platform_fit_score < 90:
        recommended_improvements.append("Improve aspect ratio, duration, pacing, and safe area instructions.")
    if prompt_engineering_score < 90:
        recommended_improvements.append("Improve prompt specificity.")
    visual_recommendation = _visual_template_recommendation(product_analysis, ugc_strategy)
    if visual_recommendation:
        recommended_improvements.append(visual_recommendation)
    category_recommendation = _category_prompt_recommendation(product_analysis, prompt_text, content_prompt_package)
    if category_recommendation:
        recommended_improvements.append(category_recommendation)
    if overall_quality_score < 85:
        recommended_improvements.append("Overall quality is below 85; improve once automatically.")

    return {
        "overall_quality_score": overall_quality_score,
        **scores,
        "export_status": export_status,
        "should_improve_once": (
            overall_quality_score < 85
            or product_fidelity_score < 95
            or compliance_score < 90
            or platform_fit_score < 90
            or prompt_engineering_score < 90
        )
        and export_status != "blocked",
        "recommended_improvements": recommended_improvements,
    }


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def _visual_template_penalty(product_analysis: dict[str, Any], ugc_strategy: dict[str, Any]) -> int:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return 0
    expected = str(visual.get("recommended_template_id") or "").strip()
    actual = str((ugc_strategy.get("category_video_recipe") or {}).get("ugc_template") or "").strip()
    if expected and actual and expected != actual:
        return 15
    return 0


def _visual_template_recommendation(product_analysis: dict[str, Any], ugc_strategy: dict[str, Any]) -> str:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return ""
    expected = str(visual.get("recommended_template_id") or "").strip()
    actual = str((ugc_strategy.get("category_video_recipe") or {}).get("ugc_template") or "").strip()
    if expected and actual and expected != actual:
        return f"Align UGC template with visual classifier recommendation: expected {expected}, got {actual}."
    return ""


def _category_prompt_penalty(
    product_analysis: dict[str, Any],
    prompt_text: str,
    content_prompt_package: dict[str, Any],
) -> int:
    if content_prompt_package.get("creative_mode") == "finance_personal_brand":
        return 0
    lowered = str(prompt_text or "").lower()
    penalty = 0
    if "no generated text" not in lowered:
        penalty += 15
    hook_mode = content_prompt_package.get("ecommerce_hook_text_mode") or {}
    if isinstance(hook_mode, dict) and hook_mode.get("enabled", False) and "hook sticker" not in lowered:
        penalty += 10
    category = str(product_analysis.get("likely_product_category") or "").lower()
    if category == "apparel" and not (
        "full-body" in lowered and ("try-on" in lowered or "head-to-toe" in lowered)
    ):
        penalty += 15
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") == "completed" and visual.get("shot_requirements"):
        if "visual classifier" not in lowered and "visual_understanding" not in lowered:
            penalty += 10
    return penalty


def _category_prompt_recommendation(
    product_analysis: dict[str, Any],
    prompt_text: str,
    content_prompt_package: dict[str, Any],
) -> str:
    if content_prompt_package.get("creative_mode") == "finance_personal_brand":
        return ""
    lowered = str(prompt_text or "").lower()
    category = str(product_analysis.get("likely_product_category") or "").lower()
    if "no generated text" not in lowered:
        return "Add a no-generated-text contract to the ecommerce video prompt; hooks should be spoken or added in post-production."
    hook_mode = content_prompt_package.get("ecommerce_hook_text_mode") or {}
    if isinstance(hook_mode, dict) and hook_mode.get("enabled", False) and "hook sticker" not in lowered:
        return "Require only one exact first-scene hook sticker and no later generated text."
    if category == "apparel" and not (
        "full-body" in lowered and ("try-on" in lowered or "head-to-toe" in lowered)
    ):
        return "For apparel, require full-body/near-full-body try-on framing before any detail close-up."
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") == "completed" and visual.get("shot_requirements"):
        if "visual classifier" not in lowered and "visual_understanding" not in lowered:
            return "Inject visual classifier shot requirements into the final provider prompt."
    return ""
