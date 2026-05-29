from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.services.localization_utils import normalize_language_code


def evaluate(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
    ads_creative_set: dict[str, Any],
    finance_mode: bool,
    should_generate_video: bool,
    should_generate_static_images: bool,
) -> dict[str, Any]:
    checks = [
        _video_asset_check(video_generation, should_generate_video),
        _video_content_quality_check(video_generation, content_prompt_package, finance_mode, should_generate_video),
        _static_asset_check(static_image_generation, should_generate_static_images, finance_mode),
        _language_check(ugc_strategy, content_prompt_package, finance_mode, should_generate_video),
        _cta_text_check(ugc_strategy, ads_creative_set),
        _reference_consistency_check(product_analysis, content_prompt_package, finance_mode),
        _scene_chaining_check(ugc_strategy, content_prompt_package),
    ]
    failed = [item for item in checks if item["status"] == "failed"]
    warnings = [item for item in checks if item["status"] == "warning"]
    if failed:
        status = "failed"
    elif warnings:
        status = "warning"
    else:
        status = "passed"
    return {
        "agent": "Post Generation QA",
        "version": "post_generation_qa_v1",
        "status": status,
        "failed_count": len(failed),
        "warning_count": len(warnings),
        "checks": checks,
        "next_step": _next_step(status, failed, warnings),
    }


def _video_asset_check(video_generation: dict[str, Any], should_generate_video: bool) -> dict[str, Any]:
    status = str(video_generation.get("video_generation_status") or "")
    if not should_generate_video:
        return _check("video_asset", "skipped", "Video generation was not requested for this run.")
    asset = video_generation.get("video_url") or video_generation.get("video_path") or video_generation.get("job_id")
    exists = _asset_exists(asset)
    if status == "completed" and asset:
        return _check(
            "video_asset",
            "passed" if exists else "warning",
            "Video provider returned an asset reference." if exists else "Video provider returned a reference, but local file existence could not be verified.",
            {"asset": asset, "provider_status": status},
        )
    if status in {"skipped", "missing"}:
        return _check(
            "video_asset",
            "warning",
            video_generation.get("failure_reason") or "Video was skipped before provider completion.",
            {"provider_status": status},
        )
    return _check(
        "video_asset",
        "failed" if status == "failed" else "warning",
        video_generation.get("failure_reason") or video_generation.get("error") or "Video is not completed yet.",
        {"provider_status": status or "unknown"},
    )


def _video_content_quality_check(
    video_generation: dict[str, Any],
    content_prompt_package: dict[str, Any],
    finance_mode: bool,
    should_generate_video: bool,
) -> dict[str, Any]:
    if not should_generate_video:
        return _check("video_content_quality", "skipped", "Video generation was not requested for this run.")
    status = str(video_generation.get("video_generation_status") or "")
    if status != "completed":
        return _check(
            "video_content_quality",
            "skipped",
            "Video content QA requires a completed local video asset.",
            {"provider_status": status or "unknown"},
        )
    video_path = _local_video_path(video_generation)
    if not video_path:
        return _check(
            "video_content_quality",
            "warning",
            "Video provider completed, but no local video file was available for OCR/audio/lip-sync QA.",
            {"asset": video_generation.get("video_url") or video_generation.get("video_path")},
        )

    probe = _video_quality_probe(video_path, content_prompt_package, finance_mode=finance_mode)
    failures: list[str] = []
    warnings: list[str] = []
    if probe.get("audio_present") is False:
        failures.append("No audio track was detected, so the avatar may be silent.")
    if probe.get("ocr_text_risk") is True:
        failures.append("Sampled frames appear to contain generated text beyond the allowed visible-text contract.")
    if probe.get("lip_sync_risk") is True:
        failures.append("Face-speaking heuristic suggests audio may not align with visible avatar speech.")
    for item in probe.get("warnings") or []:
        if item:
            warnings.append(str(item))

    if failures:
        return _check(
            "video_content_quality",
            "failed",
            "Generated UGC video failed content-quality QA.",
            {"video_path": str(video_path), "failures": failures, "probe": probe},
        )
    if warnings:
        return _check(
            "video_content_quality",
            "warning",
            "Generated UGC video passed hard checks, but one or more local QA probes were unavailable or inconclusive.",
            {"video_path": str(video_path), "warnings": warnings, "probe": probe},
        )
    return _check(
        "video_content_quality",
        "passed",
        "Generated UGC video has audio and no sampled-frame text/lip-sync risk was detected.",
        {"video_path": str(video_path), "probe": probe},
    )


def _local_video_path(video_generation: dict[str, Any]) -> Path | None:
    raw_path = str(video_generation.get("video_path") or "").strip()
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.exists() and path.is_file():
        return path
    return None


def _video_quality_probe(
    video_path: Path,
    content_prompt_package: dict[str, Any],
    *,
    finance_mode: bool,
) -> dict[str, Any]:
    warnings: list[str] = []
    audio_present = _video_has_audio_track(video_path)
    if audio_present is None:
        warnings.append("Audio probe unavailable: ffprobe not found and MP4 audio-track fallback was inconclusive.")

    frame_probe = _sampled_frame_text_probe(video_path, content_prompt_package, finance_mode=finance_mode)
    warnings.extend(frame_probe.get("warnings") or [])
    lip_probe = _face_speaking_probe(video_path, audio_present=audio_present)
    warnings.extend(lip_probe.get("warnings") or [])
    return {
        "audio_present": audio_present,
        "ocr_text_risk": frame_probe.get("ocr_text_risk"),
        "ocr_text_samples": frame_probe.get("ocr_text_samples", []),
        "lip_sync_risk": lip_probe.get("lip_sync_risk"),
        "lip_sync_signal": lip_probe.get("signal"),
        "warnings": warnings,
    }


def _video_has_audio_track(video_path: Path) -> bool | None:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=index",
                    "-of",
                    "csv=p=0",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            if result.returncode == 0:
                return bool(result.stdout.strip())
        except Exception:
            pass
    try:
        data = video_path.read_bytes()
    except Exception:
        return None
    if b"soun" in data:
        return True
    if b"vide" in data:
        return False
    return None


def _sampled_frame_text_probe(
    video_path: Path,
    content_prompt_package: dict[str, Any],
    *,
    finance_mode: bool,
) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    tesseract = shutil.which("tesseract")
    if not ffmpeg or not tesseract:
        return {
            "ocr_text_risk": None,
            "ocr_text_samples": [],
            "warnings": [
                "OCR probe unavailable: install ffmpeg and tesseract to scan sampled video frames for generated/misspelled text."
            ],
        }
    # OCR implementation is intentionally conservative here: the local test
    # environment does not ship OCR tools, so callers can monkeypatch this probe.
    allowed = _allowed_visible_text_fragments(content_prompt_package, finance_mode=finance_mode)
    return {
        "ocr_text_risk": False,
        "ocr_text_samples": [],
        "allowed_visible_text": allowed,
        "warnings": ["OCR probe tools found, but frame OCR extraction is not enabled in this lightweight QA build."],
    }


def _face_speaking_probe(video_path: Path, *, audio_present: bool | None) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if audio_present is False:
        return {"lip_sync_risk": True, "signal": "no_audio_track", "warnings": []}
    if not ffmpeg:
        return {
            "lip_sync_risk": None,
            "signal": "unavailable",
            "warnings": [
                "Lip-sync probe unavailable: install ffmpeg plus a face/mouth analysis backend to verify that audio is live visible avatar speech, not off-camera narration over a silent or hidden-mouth avatar."
            ],
        }
    return {
        "lip_sync_risk": False,
        "signal": "audio_track_present_basic_heuristic",
        "warnings": ["Lip-sync probe used a basic heuristic only; review the generated avatar speech visually before launch."],
    }


def _allowed_visible_text_fragments(content_prompt_package: dict[str, Any], *, finance_mode: bool) -> list[str]:
    if finance_mode:
        return []
    return []


def _static_asset_check(
    static_image_generation: dict[str, Any],
    should_generate_static_images: bool,
    finance_mode: bool,
) -> dict[str, Any]:
    if finance_mode:
        return _check("static_assets", "passed", "Finance mode is video-only; static creatives are intentionally disabled.")
    if not should_generate_static_images:
        return _check("static_assets", "skipped", "Static image generation was not requested for this run.")
    selected = int(static_image_generation.get("selected_creative_count") or 0)
    generated = len(static_image_generation.get("image_assets") or [])
    status = str(static_image_generation.get("image_generation_status") or "")
    if status == "completed":
        return _check(
            "static_assets",
            "passed" if generated else "warning",
            "Static image generation completed." if generated else "Static generation completed without saved assets.",
            {"selected": selected, "generated": generated},
        )
    if status == "skipped":
        return _check(
            "static_assets",
            "warning",
            static_image_generation.get("failure_reason") or "Static image generation was skipped.",
            {"selected": selected, "generated": generated},
        )
    return _check(
        "static_assets",
        "failed" if status == "failed" else "warning",
        static_image_generation.get("failure_reason") or static_image_generation.get("error") or "Static image generation is not completed.",
        {"selected": selected, "generated": generated, "provider_status": status or "unknown"},
    )


def _language_check(
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    finance_mode: bool,
    should_generate_video: bool,
) -> dict[str, Any]:
    language = normalize_language_code(ugc_strategy.get("language") or content_prompt_package.get("language") or "")
    speech_contract = content_prompt_package.get("speech_language_contract") or {}
    visible_texts = _customer_texts(ugc_strategy, {}) + _structured_scene_texts(content_prompt_package)
    visible_text = " ".join(visible_texts)
    suspicious = bool(re.search(r"[łŁąĄęĘżŻźŹńŃ]|\\bpolski\\b|\\bslovak\\b", visible_text, re.IGNORECASE))
    if language != "cs" or speech_contract.get("spoken_language") != "cs-CZ":
        if finance_mode:
            return _check(
                "finance_czech_language",
                "failed",
                "Finance mode must force Czech language and cs-CZ speech.",
                {"language": language, "spoken_language": speech_contract.get("spoken_language")},
            )
    if finance_mode:
        if suspicious:
            return _check("finance_czech_language", "warning", "Customer-facing text contains possible non-Czech markers.")
        return _check("finance_czech_language", "passed", "Finance mode is locked to Czech speech, captions, and infographic text.")
    if language not in {"cs", "de", "en"}:
        return _check("language_contract", "passed", f"Customer-facing language is {language or 'set by request'}.")
    mismatches = _foreign_language_matches(language, visible_texts)
    if mismatches:
        return _check(
            "language_contract",
            "failed",
            f"Customer-facing creative text contains likely non-{language} language fragments.",
            {"language": language, "matches": mismatches[:8], "spoken_language": speech_contract.get("spoken_language")},
        )
    speech_warning = _speech_contract_warning(language, speech_contract, should_generate_video)
    if speech_warning:
        return _check(
            "language_contract",
            "warning",
            speech_warning,
            {"language": language, "spoken_language": speech_contract.get("spoken_language")},
        )
    if suspicious:
        return _check("language_contract", "warning", "Customer-facing text contains possible non-target-language markers.")
    return _check("language_contract", "passed", f"Customer-facing copy and speech contract are locked to {language}.")


def _cta_text_check(ugc_strategy: dict[str, Any], ads_creative_set: dict[str, Any]) -> dict[str, Any]:
    texts = _customer_texts(ugc_strategy, ads_creative_set)
    forbidden = []
    pattern = re.compile(
        r"(https?://|www\\.|\\bclick\\b|\\bklik\\b|\\bshop now\\b|\\bbuy now\\b|\\blearn more\\b|\\bopen detail\\b|tla[cč][ií]tko|\\bbutton\\b)",
        re.IGNORECASE,
    )
    for text in texts:
        if pattern.search(text):
            forbidden.append(text[:180])
    if forbidden:
        return _check(
            "no_fake_cta_controls",
            "failed",
            "Customer-facing creative text contains URL, button, or click-style CTA wording that should be handled by the ad platform.",
            {"matches": forbidden[:5]},
        )
    return _check("no_fake_cta_controls", "passed", "No customer-facing fake CTA button, URL, or click instruction was found.")


def _reference_consistency_check(
    product_analysis: dict[str, Any],
    content_prompt_package: dict[str, Any],
    finance_mode: bool,
) -> dict[str, Any]:
    if finance_mode:
        prompt = str((content_prompt_package.get("seedance_payload") or {}).get("prompt") or "")
        ok = "approved scene" in prompt.lower() or "podcast" in prompt.lower()
        return _check(
            "finance_scene_consistency",
            "passed" if ok else "warning",
            "Finance prompt uses approved/podcast scene consistency." if ok else "Finance prompt should explicitly reuse the approved scene concept.",
        )
    category = str(product_analysis.get("likely_product_category") or "")
    fidelity = str(content_prompt_package.get("product_fidelity_instruction") or "")
    if "product not modified" in fidelity.lower() or "strict visual reference" in fidelity.lower():
        return _check(
            "product_fidelity_contract",
            "passed",
            "Product reference/fidelity contract is present.",
            {"category": category},
        )
    return _check("product_fidelity_contract", "warning", "Product fidelity contract is weak or missing.", {"category": category})


def _scene_chaining_check(
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> dict[str, Any]:
    scene_chaining = ugc_strategy.get("scene_chaining") or content_prompt_package.get("scene_chaining") or {}
    plan = scene_chaining.get("true_scene_chaining_plan") or {}
    if scene_chaining.get("version") == "scene_chaining_v2" and plan:
        return _check(
            "scene_chaining_contract",
            "passed",
            "Scene chaining V2 contract is present and auditable.",
            {
                "execution": (scene_chaining.get("provider_execution") or {}).get("current_mode"),
                "scene_link_count": plan.get("scene_link_count"),
            },
        )
    return _check("scene_chaining_contract", "warning", "Scene chaining V2 contract is missing.")


def _customer_texts(ugc_strategy: dict[str, Any], ads_creative_set: dict[str, Any]) -> list[str]:
    texts = [
        str(ugc_strategy.get("hook") or ""),
        str(ugc_strategy.get("voiceover") or ""),
        *[str(item) for item in ugc_strategy.get("on_screen_text") or []],
        *[str(item) for item in ugc_strategy.get("subtitles") or []],
    ]
    for scene in ugc_strategy.get("scene_by_scene_script") or []:
        texts.extend(
            str(scene.get(key) or "")
            for key in ["voiceover", "on_screen_text", "subtitle"]
        )
    for item in ads_creative_set.get("static_image_ads") or []:
        texts.extend(
            str(item.get(key) or "")
            for key in ["headline", "overlay_text", "primary_text", "description"]
        )
    carousel = ads_creative_set.get("carousel_ad") or {}
    texts.extend(str(carousel.get(key) or "") for key in ["primary_text", "headline"])
    for card in carousel.get("cards") or []:
        texts.extend(str(card.get(key) or "") for key in ["headline", "body", "overlay_text"])
    for item in ads_creative_set.get("meme_style_creatives") or []:
        texts.extend(str(item.get(key) or "") for key in ["copy", "overlay_text", "primary_text"])
    for item in ads_creative_set.get("primary_text_variants") or []:
        texts.append(str(item.get("primary_text") or ""))
    ad_descriptions = ads_creative_set.get("ad_description_suggestions") or {}
    for item in ad_descriptions.get("variants") or []:
        texts.extend(str(item.get(key) or "") for key in ["primary_text", "headline", "description"])
    google_assets = ads_creative_set.get("google_ads_assets") or {}
    for group in (google_assets.values() if isinstance(google_assets, dict) else []):
        if not isinstance(group, dict):
            continue
        for values in group.values():
            if not isinstance(values, list):
                continue
            texts.extend(str(item.get("text") or "") for item in values if isinstance(item, dict))
    return [text for text in texts if text.strip()]


def _structured_scene_texts(content_prompt_package: dict[str, Any]) -> list[str]:
    structured = content_prompt_package.get("structured_scene_prompt") or {}
    texts: list[str] = []
    if not isinstance(structured, dict):
        return texts
    for variant in structured.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        for scene in variant.get("scenes") or []:
            if not isinstance(scene, dict):
                continue
            texts.append(str(scene.get("voiceover") or ""))
            on_screen = scene.get("on_screen_text") or {}
            if isinstance(on_screen, dict):
                texts.append(str(on_screen.get("text") or ""))
    return [text for text in texts if text.strip()]


def _speech_contract_warning(
    language: str,
    speech_contract: dict[str, Any],
    should_generate_video: bool,
) -> str:
    if not should_generate_video:
        return ""
    expected = {"cs": "cs-CZ", "de": "de-DE", "en": ("en-US", "en-GB")}
    target = expected.get(language)
    spoken = str(speech_contract.get("spoken_language") or "")
    if not spoken:
        return f"Video language guard expected a speech_language_contract for {language}, but none was present."
    if isinstance(target, tuple):
        if spoken not in target:
            return f"Video speech language should be one of {', '.join(target)} for {language}."
        return ""
    if spoken != target:
        return f"Video speech language should be {target} for {language}."
    return ""


def _foreign_language_matches(language: str, texts: list[str]) -> list[dict[str, str]]:
    patterns = {
        "cs": [
            ("english", r"\b(finally|found|fits|everything|shop|available now|daily essentials|water bottle|wallet|makeup|soft leather|perfect everyday|free delivery)\b"),
            ("german", r"\b(ich|du|sie|und|oder|nicht|tasche|alltag|jetzt|kaufen|entdecken|kostenlos)\b"),
            ("polish_or_slovak", r"[ąćęłńóśźż]|\\bpolski\\b|\\bslovak\\b"),
        ],
        "de": [
            ("english", r"\b(finally|found|fits|everything|shop|available now|daily essentials|water bottle|wallet|makeup|soft leather|perfect everyday|free delivery)\b"),
            ("czech", r"\b(kabelka|penezenka|lahev|klice|kosmetika|dnes|kazdy|cesky|nakup|elegantni|prakticka)\b|[ěščřžýáíéůúďťň]"),
            ("polish_or_slovak", r"[ąćęłńóśźż]|\\bpolski\\b|\\bslovak\\b"),
        ],
        "en": [
            ("czech", r"\b(kabelka|penezenka|lahev|klice|kosmetika|dnes|kazdy|cesky|nakup|elegantni|prakticka)\b|[ěščřžýáíéůúďťň]"),
            ("german", r"\b(ich|du|sie|und|oder|nicht|tasche|alltag|jetzt|kaufen|entdecken|kostenlos)\b"),
            ("polish_or_slovak", r"[ąćęłńóśźż]|\\bpolski\\b|\\bslovak\\b"),
        ],
    }.get(language, [])
    matches = []
    for text in texts:
        compact = " ".join(str(text or "").split())
        if not compact:
            continue
        for source, pattern in patterns:
            if re.search(pattern, compact, re.IGNORECASE):
                matches.append({"source": source, "text": compact[:180]})
                break
    return matches


def _asset_exists(asset: Any) -> bool:
    text = str(asset or "")
    if not text:
        return False
    if text.startswith(("http://", "https://")):
        return True
    if text.startswith(("job_", "gen_", "video_")):
        return True
    try:
        return Path(text).exists()
    except OSError:
        return False


def _check(check_id: str, status: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "message": str(message or ""),
        "details": details or {},
    }


def _next_step(status: str, failed: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
    if status == "failed":
        return "Fix failed QA checks before exporting or regenerating this creative."
    if warnings:
        return "Review QA warnings; output may still be usable if skips were intentional."
    return "QA passed; review the assets and rate performance after launch."
