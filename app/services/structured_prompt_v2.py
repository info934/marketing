from __future__ import annotations

import re
from typing import Any

from app.services import prompt_compression, prompt_defaults
from app.services.localization_utils import is_czech as _is_czech_language


PROMPT_HARD_LIMIT_CHARS = 18000
PROMPT_TARGET_LIMIT_CHARS = 17000
VISIBLE_TEXT_GUARD = (
    "Visible text guard: ecommerce creator video must render no generated on-screen text. "
    "Do not render title cards, intro labels, technical instruction text, schema field names, "
    "workflow terms, model names, platform names, internal production labels, subtitles, captions, lower thirds, "
    "floating text, CTA text, hook stickers, or any extra scene text. Spoken audio carries the message; all captions must be added later in post-production, not generated inside the video. "
    "The only visible words allowed are verified product markings already present on the product reference, or an exact requested personalization word printed on the product. "
    "Keep allowed product text still, correctly spelled, and inside safe area; no scrambled letters, mirrored text, melting text, partial words, or random extra words."
)

FINANCE_VISIBLE_TEXT_GUARD = (
    "Visible text guard: finance mode may use only the approved Czech infographic labels, compliance disclaimer, and concise Czech captions. "
    "Keep every visible word inside the central safe area, correctly spelled with Czech diacritics, and never render prompt labels, schema field names, platform UI, fake buttons, URLs, or random text."
)

HAND_QUALITY_GUARD = (
    "Hand quality guard: hands appear only when useful for product handling. Use relaxed adult hands, natural five-finger anatomy, stable grip, slow motion, and one object per action. "
    "Crop hands at frame edge if uncertain; no fused, extra, missing, twisted, elongated, or melting fingers."
)

ECOMMERCE_CREATOR_PRESENCE_GUARD = (
    "Creator presence guard: for ecommerce UGC, the selected avatar/creator must remain visibly present in every scene for trust. "
    "Use face plus product, upper body plus product, shoulder/torso with product, or natural creator hands holding/wearing the product. "
    "During spoken beats, keep the creator's face and mouth visible enough to read natural speech. "
    "Do not cut to product-only inserts, no-person b-roll, isolated product-on-table shots, or environment-only shots."
)

VISIBLE_SPEAKING_GUARD = (
    "Visible speaking guard: ecommerce creator audio must be on-camera speech from the visible avatar, not off-camera narration over silent footage. "
    "In the opening hook and every spoken scene, show natural mouth, jaw, cheek, and small facial-expression movement articulating the exact spoken line. "
    "Keep the mouth unobstructed by phone, product, hair, hand, or crop; no frozen face, no closed-mouth talking, no delayed dubbing, and no silent avatar with audio laid over it."
)

HUMAN_PROPORTION_GUARD = (
    "Human proportion guard: keep natural adult human body, face, head, torso, arm, hand, hip, leg, and garment proportions throughout the clip. "
    "Use a normal phone-lens perspective with no fisheye, ultra-wide, anamorphic, mirror-warp, vertical stretch, horizontal squeeze, elongated limbs, oversized head, tiny hands, or distorted body scale. "
    "Keep the vertical 9:16 frame like a normal smartphone video; do not crop, letterbox, pillarbox, stretch, or reframe into a different aspect ratio."
)

MIRROR_SELFIE_SPEAKING_GUARD = (
    "Mirror-selfie speaking guard: the phone stays visible in one hand inside the mirror reflection, but it must sit low or to the side so the creator's mouth remains visible while speaking. "
    "Use a full-body or near full-body mirror view with a readable speaking face; do not place the phone directly over the mouth or crop the face out during the spoken hook."
)

MIRROR_SELFIE_CAMERA_LOCK_GUARD = (
    "Mirror-selfie camera lock: for the entire duration, the only camera source is the creator's iPhone mirror-selfie recording. "
    "The avatar is always seen through the mirror reflection while holding the phone visibly in one hand. "
    "Never switch to third-person camera, external camera angle, side filming, over-the-shoulder shot, back-view tracking, room camera, observer perspective, tripod perspective, cinematic b-roll, cutaway, product-only insert, fashion-commercial shot, scene change, or perspective change. "
    "The avatar must never walk away from the mirror or turn fully back; only a partial side-turn is allowed while still facing the mirror."
)

MIRROR_SELFIE_OPENING_MOTION_GUARD = (
    "Mirror-selfie opening motion guard: the first frame must not look like a frozen still, poster frame, or held reference image. "
    "Start already in live motion with tiny phone sway, a blink, visible mouth/jaw beginning the spoken hook, or a small free-hand movement near the waist, neckline, cut, drape, or silhouette. "
    "No frozen face, closed-mouth first seconds, static hold, or delayed speech start."
)

APPAREL_FULL_BODY_GUARD = (
    "Apparel full-body guard: when the product category is apparel or clothing, every generated video must include a clear full-body or near full-body head-to-toe view of the adult creator wearing the garment. "
    "Show the complete outfit silhouette, garment length, hem, sleeves/straps, drape, and body-to-garment scale in a mirror, doorway, hallway, or simple standing phone shot with natural human proportions. "
    "Make it feel like a normal phone try-on check, not a polished ecommerce model shoot: modest expression, small natural turn, relaxed arms, no runway posing, no glamour smile, no beauty-retouch look. "
    "Do not crop the clothing video to only face, chest, waist, hands, flat lay, or isolated fabric details; detail close-ups may appear only after the full worn silhouette is established."
)

MIRROR_SELFIE_APPAREL_FULL_BODY_GUARD = (
    "Mirror-selfie apparel guard: keep the entire clothing video in one simple bedroom mirror reflection setup. "
    "The creator films herself through the mirror with the smartphone visibly held in one hand inside the reflection, low or to the side when speaking so the mouth remains visible. "
    "Show a full-body or near full-body head-to-toe reflected outfit view first, with garment length, waist, neckline, hem, sleeves/straps, drape, cut, body-to-garment scale, and natural human proportions visible. "
    "The free hand may point to waist, neckline, cut, drape, or silhouette; no non-bedroom/public/work/outdoor location, no secondary room setup, no external camera, no tripod, no third-person camera, no face/chest-only crop."
)

DROPSHIPPING_REALISM_GUARD = (
    "Dropshipping realism guard: real buyer-check clip, not polished brand commercial. "
    "Use ordinary phone exposure, slight handheld imperfection, modest expression, simple real spaces, and practical product proof. "
    "Prefer one stable selfie/mirror/product-check setup with simple hard cuts over complex fashion-ad choreography. "
    "Avoid luxury staging, cinematic grading, glossy retouch, runway posing, exaggerated reactions, fake social proof, fake discounts, and overproduced ad energy. "
    "Do not describe the ecommerce UGC video as cinematic, professional, stunning, 8k, studio, perfect, premium commercial, or fashion editorial. "
    "If motion risks product/avatar distortion, simplify to a stable creator-held, creator-worn, or mirror-check proof shot."
)

CZECH_LANGUAGE_HARD_LOCK = (
    "CZECH LANGUAGE HARD LOCK: generated ecommerce video must be Czech-only for every spoken customer-facing line. "
    "Use cs-CZ pronunciation, Czech sentence rhythm, and the approved Czech spoken script only. "
    "Do not speak English, Polish, Slovak, German, bilingual filler, pseudo-Czech, or translated leftovers from avatar voice/persona notes."
)

PROVIDER_BLOCK_LABELS = {
    "product_rules": "Product instructions",
    "avatar_rules": "Creator instructions",
    "voice": "Voice instructions",
    "language_guard": "Language instructions",
    "speech_audio_contract": "Speech and audio instructions",
    "seedance_provider_contract": "Video generation instructions",
    "emotion": "Emotion notes",
    "learning": "Learning notes",
    "environment_control": "Environment instructions",
    "camera_global": "Camera instructions",
    "lighting_global": "Lighting instructions",
    "motion_global": "Motion instructions",
    "ugc_prompt_skill": "Creator prompt skill guidance",
    "user_scenario_lock": "User scenario lock",
    "video_extra_direction": "Extra video direction",
    "approved_scene_concept": "Approved scene concept",
    "scene": "Shot",
    "infographic": "Optional graphic guidance",
    "environment": "Environment",
    "camera": "Camera",
    "lighting": "Lighting",
    "motion": "Motion",
}


def apply_to_prompt_package(
    *,
    content_prompt_package: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    structured = build(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        settings=settings,
    )
    compiled = compile_prompt(
        structured,
        legacy_preamble=_legacy_preamble(content_prompt_package, settings),
    )
    final_prompt, compression = _provider_safe_prompt(
        compiled,
        structured=structured,
        legacy_preamble=_legacy_preamble(content_prompt_package, settings),
    )
    updated = dict(content_prompt_package)
    updated["structured_prompt_v2"] = structured
    updated["prompt_compression"] = compression
    updated["seedance_video_prompt_uncompressed_v2"] = compiled
    updated["seedance_video_prompt"] = final_prompt
    updated["seedance_payload"] = dict(content_prompt_package.get("seedance_payload") or {})
    updated["seedance_payload"]["prompt"] = final_prompt
    updated["seedance_payload"]["structured_prompt_architecture"] = "v2"
    updated["seedance_payload"]["prompt_compression"] = {
        key: compression[key]
        for key in [
            "status",
            "chars_before",
            "chars_after",
            "chars_provider_final",
            "chars_saved",
            "reduction_percent",
            "fit_strategy",
            "target_limit",
            "hard_limit",
        ]
        if key in compression
    }
    return updated


def _provider_safe_prompt(
    compiled: str,
    *,
    structured: dict[str, Any],
    legacy_preamble: str,
) -> tuple[str, dict[str, Any]]:
    compiled = _sanitize_provider_meta_text(compiled)
    compression = prompt_compression.compress_prompt(compiled)
    final_prompt = _with_reusable_block_glossary(compression)
    fit_strategy = "compressed_with_glossary"

    if len(final_prompt) > PROMPT_TARGET_LIMIT_CHARS:
        compact_compiled = compile_prompt(
            structured,
            legacy_preamble=legacy_preamble,
            compact=True,
        )
        compact_compiled = _sanitize_provider_meta_text(compact_compiled)
        compact_compression = prompt_compression.compress_prompt(compact_compiled)
        compact_prompt = _with_reusable_block_glossary(compact_compression)
        if len(compact_prompt) < len(final_prompt):
            compression = compact_compression
            final_prompt = compact_prompt
            fit_strategy = "compact_structured_prompt"

    if len(final_prompt) > PROMPT_TARGET_LIMIT_CHARS:
        final_prompt = _fit_prompt_to_limit(final_prompt, PROMPT_TARGET_LIMIT_CHARS)
        fit_strategy = "hard_trimmed_to_target"

    final_prompt = _sanitize_provider_meta_text(final_prompt)
    final_prompt = _ensure_critical_provider_lines(final_prompt, structured)
    if len(final_prompt) > PROMPT_HARD_LIMIT_CHARS:
        final_prompt = _fit_prompt_to_limit(final_prompt, PROMPT_HARD_LIMIT_CHARS)
        fit_strategy = "critical_lines_then_hard_trimmed"

    compression = {
        **compression,
        "chars_provider_final": len(final_prompt),
        "target_limit": PROMPT_TARGET_LIMIT_CHARS,
        "hard_limit": PROMPT_HARD_LIMIT_CHARS,
        "fit_strategy": fit_strategy,
        "fits_hard_limit": len(final_prompt) <= PROMPT_HARD_LIMIT_CHARS,
    }
    return final_prompt, compression


def _ensure_critical_provider_lines(prompt: str, structured: dict[str, Any]) -> str:
    result = str(prompt or "")
    finance_mode = structured.get("creative_mode") == "finance_personal_brand"
    if not finance_mode and VISIBLE_SPEAKING_GUARD not in result:
        result = _insert_near_start(result, VISIBLE_SPEAKING_GUARD)
    if not finance_mode and HUMAN_PROPORTION_GUARD not in result:
        result = _insert_near_start(result, HUMAN_PROPORTION_GUARD)
    if not finance_mode and _structured_mirror_selfie_lock(structured) and MIRROR_SELFIE_SPEAKING_GUARD not in result:
        result = _insert_near_start(result, MIRROR_SELFIE_SPEAKING_GUARD)
    if not finance_mode and _structured_mirror_selfie_lock(structured) and MIRROR_SELFIE_CAMERA_LOCK_GUARD not in result:
        result = _insert_near_start(result, MIRROR_SELFIE_CAMERA_LOCK_GUARD)
    if not finance_mode and _structured_mirror_selfie_lock(structured) and MIRROR_SELFIE_OPENING_MOTION_GUARD not in result:
        result = _insert_near_start(result, MIRROR_SELFIE_OPENING_MOTION_GUARD)
    contract = structured.get("seedance_provider_contract") or {}
    for role in contract.get("reference_roles") or []:
        role_text = str(role or "").strip()
        if role_text and "avatar identity source only" in role_text and role_text not in result:
            result = f"{result} {role_text}"
        if role_text and "product identity source" in role_text and role_text not in result:
            result = f"{result} {role_text}"
    scenario_lock = structured.get("user_scenario_lock") or {}
    if isinstance(scenario_lock, dict) and scenario_lock.get("template") and "User scenario lock" not in result:
        result = f"{result} User scenario lock: {_compact(scenario_lock, max_value_chars=900)}."
    return result


def _insert_near_start(prompt: str, sentence: str) -> str:
    text = str(prompt or "").strip()
    addition = str(sentence or "").strip()
    if not addition:
        return text
    cut = text.find(". ")
    if cut <= 0 or cut > 220:
        return f"{addition} {text}".strip()
    return f"{text[: cut + 2]}{addition} {text[cut + 2:]}".strip()


def _sanitize_provider_meta_text(prompt: str) -> str:
    text = str(prompt or "")
    replacements = [
        (r"\b(\d+\s*s)\s+UGC\s+with avatar\b", r"\1 creator product video with avatar"),
        (r"\bpaid\s+UGC\s+ad\b", "creator product video"),
        (r"\bUGC\s+ad\b", "creator product video"),
        (r"\bUGC\s+video\b", "creator video"),
        (r"\bUGC\s+creator\b", "natural creator"),
        (r"\bUGC\b", "creator-style"),
        (r"\buser[- ]generated content\b", "creator-style"),
        (r"\bstructured prompt architecture\b", "video direction"),
        (r"\bstructured prompt\b", "video direction"),
        (r"\bvoiceover\b", "spoken script"),
        (r"\bcaption contract\b", "subtitle guidance"),
        (r"\bsubtitle contract\b", "subtitle guidance"),
        (r"\bproduct_rules\b", "product instructions"),
        (r"\btime_range\b", "timing"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def build(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    scenes = _scene_blocks(product_analysis, ugc_strategy, content_prompt_package)
    return {
        "version": "structured_prompt_architecture_v2",
        "creative_mode": content_prompt_package.get("creative_mode") or "ecommerce_ugc",
        "platform": ugc_strategy.get("platform"),
        "market": ugc_strategy.get("market"),
        "language": ugc_strategy.get("language"),
        "duration_seconds": ugc_strategy.get("duration_seconds"),
        "aspect_ratio": ugc_strategy.get("aspect_ratio"),
        "scene_count": len(scenes),
        "product_rules": _product_rules(product_analysis, content_prompt_package),
        "avatar_rules": _avatar_rules(content_prompt_package, ugc_strategy),
        "voice": _voice_block(ugc_strategy),
        "language_guard": _language_guard(ugc_strategy, content_prompt_package),
        "speech_audio_contract": _speech_audio_contract(ugc_strategy, content_prompt_package),
        "seedance_provider_contract": _seedance_provider_contract(content_prompt_package, ugc_strategy),
        "emotion": _emotion_block(ugc_strategy),
        "learning": _learning_block(ugc_strategy, content_prompt_package),
        "environment_control": _environment_control(content_prompt_package),
        "camera_global": _camera_global(ugc_strategy, content_prompt_package),
        "lighting_global": _lighting_global(content_prompt_package),
        "motion_global": _motion_global(ugc_strategy),
        "ugc_prompt_skill": _ugc_prompt_skill(ugc_strategy),
        "user_scenario_lock": _user_scenario_lock(content_prompt_package, ugc_strategy),
        "video_extra_direction": content_prompt_package.get("ugc_video_extra_prompt"),
        "approved_scene_concept": _approved_scene_concept(content_prompt_package, ugc_strategy),
        "scenes": scenes,
        "negative_prompt": content_prompt_package.get("negative_prompt"),
        "compiler_contract": {
            "target": "Seedance/OpenRouter video prompt",
            "mode": "structured_blocks_then_prompt_compiler",
            "avoid": "large duplicated prose prompts",
        },
    }


def compile_prompt(
    structured: dict[str, Any],
    legacy_preamble: str = "",
    *,
    compact: bool = False,
) -> str:
    lines = []
    finance_mode = structured.get("creative_mode") == "finance_personal_brand"
    mirror_selfie_lock = _structured_mirror_selfie_lock(structured)
    apparel_guard = (
        MIRROR_SELFIE_APPAREL_FULL_BODY_GUARD
        if mirror_selfie_lock
        else APPAREL_FULL_BODY_GUARD
    )
    if legacy_preamble:
        lines.append(legacy_preamble.strip())
    lines.extend(
        [
            (
                "Create a realistic short-form personal-brand video with the approved spoken script."
                if finance_mode
                else "Create a realistic smartphone-style creator product video with the approved spoken script."
            ),
            "Spoken audio is required: the on-camera avatar must speak out loud and lip-sync exactly to the approved voiceover; no silent avatar, no silent mouthing, no text-only delivery.",
            FINANCE_VISIBLE_TEXT_GUARD if finance_mode else VISIBLE_TEXT_GUARD,
            "" if finance_mode else prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK,
            "" if finance_mode else prompt_defaults.PRODUCT_REFERENCE_ROLE_LOCK,
            CZECH_LANGUAGE_HARD_LOCK if _is_czech_language(structured.get("language")) else "",
            HAND_QUALITY_GUARD,
            "" if finance_mode else ECOMMERCE_CREATOR_PRESENCE_GUARD,
            "" if finance_mode else VISIBLE_SPEAKING_GUARD,
            "" if finance_mode else HUMAN_PROPORTION_GUARD,
            MIRROR_SELFIE_SPEAKING_GUARD if mirror_selfie_lock and not finance_mode else "",
            MIRROR_SELFIE_CAMERA_LOCK_GUARD if mirror_selfie_lock and not finance_mode else "",
            MIRROR_SELFIE_OPENING_MOTION_GUARD if mirror_selfie_lock and not finance_mode else "",
            apparel_guard if _is_apparel_category(structured.get("product_rules")) and not finance_mode else "",
            "" if finance_mode else DROPSHIPPING_REALISM_GUARD,
            "" if finance_mode else prompt_defaults.MATERIAL_FIDELITY_HARD_LOCK,
            f"Global: platform={structured.get('platform')}, market={structured.get('market')}, language={structured.get('language')}, duration={structured.get('duration_seconds')}s. Aspect ratio: {structured.get('aspect_ratio')}.",
            _block_line("environment_control", structured.get("environment_control"), compact=compact),
            _block_line("user_scenario_lock", structured.get("user_scenario_lock"), compact=compact),
            _block_line("ugc_prompt_skill", structured.get("ugc_prompt_skill"), compact=compact),
            _block_line("video_extra_direction", structured.get("video_extra_direction"), compact=compact),
            _block_line("approved_scene_concept", structured.get("approved_scene_concept"), compact=compact),
        ]
    )
    for scene in structured.get("scenes") or []:
        visible_caption_instruction = (
            f"approved visible caption=\"{_clip(scene.get('on_screen_text'), 80)}\"."
            if finance_mode
            else _ecommerce_visible_text_instruction(scene)
        )
        if compact:
            lines.append(
                " ".join(
                    [
                        f"{scene.get('time_range')}: {scene.get('purpose')} beat, {scene.get('duration')}s.",
                        _short_block_line("scene", scene.get("scene"), ["summary", "shot_type", "setting"]),
                        _short_block_line("infographic", scene.get("infographic"), ["notes", "labels", "motion"]),
                        _short_block_line("environment", scene.get("environment"), ["background_consistency", "preserve_original_scene_layout"]),
                        _short_block_line("motion", scene.get("motion"), ["avatar", "product"]),
                        _short_block_line("product_rules", scene.get("product_rules"), ["fidelity", "lock"]),
                        _short_block_line("avatar_rules", scene.get("avatar_rules"), ["on_camera", "identity", "instruction"]),
                        f"spoken line=\"{_clip(scene.get('voiceover'), 260)}\".",
                        visible_caption_instruction,
                    ]
                )
            )
        else:
            lines.append(
                " ".join(
                    [
                        f"{scene.get('time_range')}: {scene.get('purpose')} beat, {scene.get('duration')}s.",
                        _block_line("scene", scene.get("scene")),
                        _block_line("environment", scene.get("environment")),
                        _block_line("camera", scene.get("camera")),
                        _block_line("lighting", scene.get("lighting")),
                        _block_line("emotion", scene.get("emotion")),
                        _block_line("infographic", scene.get("infographic")),
                        _block_line("motion", scene.get("motion")),
                        _block_line("product_rules", scene.get("product_rules")),
                        _block_line("avatar_rules", scene.get("avatar_rules")),
                        f"spoken line=\"{scene.get('voiceover')}\".",
                        visible_caption_instruction,
                    ]
                )
            )
    lines.extend(
        [
            _block_line("product_rules", structured.get("product_rules"), compact=compact),
            _block_line("avatar_rules", structured.get("avatar_rules"), compact=compact),
            _block_line("voice", structured.get("voice"), compact=compact),
            _block_line("language_guard", structured.get("language_guard"), compact=compact),
            _block_line("speech_audio_contract", structured.get("speech_audio_contract"), compact=compact),
            _block_line("seedance_provider_contract", structured.get("seedance_provider_contract"), compact=compact),
            _block_line("emotion", structured.get("emotion"), compact=compact),
            _block_line("learning", structured.get("learning"), compact=compact),
            _block_line("camera_global", structured.get("camera_global"), compact=compact),
            _block_line("lighting_global", structured.get("lighting_global"), compact=compact),
            _block_line("motion_global", structured.get("motion_global"), compact=compact),
        ]
    )
    if structured.get("negative_prompt"):
        lines.append(f"Negative prompt: {structured.get('negative_prompt')}")
    return " ".join(line for line in lines if line)


def _ecommerce_visible_text_instruction(scene: dict[str, Any]) -> str:
    return (
        "no generated text: do not render subtitles, captions, hook text, lower thirds, CTA text, labels, floating text, "
        "platform UI, prompt terms, or random words in this scene; spoken audio only, captions are post-production only."
    )


def _scene_blocks(
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> list[dict[str, Any]]:
    structured_scene = content_prompt_package.get("structured_scene_prompt") or {}
    variant = ((structured_scene.get("variants") or [{}])[0]) if isinstance(structured_scene, dict) else {}
    structured_scenes = variant.get("scenes") or []
    script_scenes = ugc_strategy.get("scene_by_scene_script") or []
    scene_chaining = ugc_strategy.get("scene_chaining") or content_prompt_package.get("scene_chaining") or {}
    scene_links = scene_chaining.get("scene_links") or []
    durations = [scene.get("duration") for scene in structured_scenes] or [5 for _ in script_scenes]
    blocks = []
    finance_mode = content_prompt_package.get("creative_mode") == "finance_personal_brand"
    mirror_selfie_lock = _is_mirror_selfie_lock(content_prompt_package, ugc_strategy)
    mirror_environment = _mirror_selfie_environment_lock()
    elapsed = 0
    for index, script in enumerate(script_scenes[: max(1, len(durations))]):
        structured = structured_scenes[min(index, len(structured_scenes) - 1)] if structured_scenes else {}
        link = scene_links[min(index, len(scene_links) - 1)] if scene_links else {}
        avatar_on_camera = True if not finance_mode else bool(
            structured.get("avatar_on_camera", index == 0 or index == len(script_scenes) - 1)
        )
        infographic_notes = script.get("infographic") or structured.get("infographic_notes")
        structured_on_screen = (
            structured.get("on_screen_text")
            if isinstance(structured.get("on_screen_text"), dict)
            else {}
        )
        scene_summary = structured.get("scene_summary") or script.get("visual")
        if not finance_mode:
            scene_summary = _ensure_creator_presence_summary(scene_summary)
            if _is_apparel_category(product_analysis):
                scene_summary = _ensure_apparel_full_body_summary(
                    scene_summary,
                    index,
                    mirror_selfie_lock=mirror_selfie_lock,
                )
        scene_voiceover = _delivery_voiceover(
            structured.get("voiceover"),
            script.get("voiceover"),
        )
        scene_on_screen_text = _delivery_scene_text(
            structured_on_screen.get("text"),
            script.get("on_screen_text"),
            script.get("subtitle"),
            scene_voiceover,
            is_hook=(index == 0),
            finance_mode=finance_mode,
        )
        hook_sticker_allowed = (
            not finance_mode
            and index == 0
            and _ecommerce_hook_sticker_enabled(content_prompt_package)
            and bool(scene_on_screen_text)
        )
        generated_text_allowed = bool(finance_mode or hook_sticker_allowed)
        scene_duration = structured.get("duration") or durations[min(index, len(durations) - 1)] if durations else 5
        scene_duration = int(scene_duration or 5)
        time_range = f"{elapsed}-{elapsed + scene_duration}s"
        elapsed += scene_duration
        if finance_mode:
            safe_area = "central safe area for face, hands, Czech subtitles, disclaimer, and interactive infographic labels"
        elif hook_sticker_allowed:
            safe_area = (
                "central safe area for creator face or upper body/hands and product; "
                "one exact first-scene hook sticker in the upper third for first 1-2 seconds only; no later generated text"
            )
        else:
            safe_area = "central safe area for creator face, unobstructed speaking mouth, upper body/hands, and product; no generated text"
        blocks.append(
            {
                "scene_id": structured.get("scene_id") or f"s{index + 1}",
                "purpose": structured.get("purpose") or script.get("psychology_step") or "scene",
                "duration": scene_duration,
                "time_range": time_range,
                "scene": {
                    "summary": scene_summary,
                    "shot_type": script.get("shot_type"),
                    "setting": (mirror_environment if mirror_selfie_lock else link.get("environment_anchor"))
                    or ("modern podcast studio with desk microphone, acoustic panels, warm key light, and subtle LED accent" if finance_mode else None),
                    "safe_area": safe_area,
                },
                "environment": {
                    **_environment_control(content_prompt_package),
                    "scene_rule": structured.get("environment_notes")
                    or (
                        "default to modern podcast studio; preserve avatar identity; do not create fake financial institution branding"
                        if finance_mode
                        else mirror_environment
                        if mirror_selfie_lock
                        else "use category-auto environment selected from product type, use case, market, and campaign context; do not copy avatar-reference or product-reference background"
                    ),
                },
        "camera": {
            "movement": "static locked-off camera or slow push-in only" if finance_mode else (
                "handheld mirror selfie phone movement only: slight phone shake, tiny sway, no tripod, no external camera move, no side filming, no cutaway, no perspective switch, and no frozen opening hold"
                if mirror_selfie_lock
                else "slight handheld sway or slow push-in only"
            ),
            "framing": "medium close-up creator framing, desk microphone may be visible, hands visible for pointing, infographics beside face, hands anatomically correct" if finance_mode else (
                "mirror reflection framing for the entire clip: smartphone visibly held in one hand inside the reflected frame but low or to the side so the mouth stays visible while speaking, creator films herself, full-body or near full-body garment visible head-to-toe with natural body proportions and normal phone-lens perspective, face/torso/product not hidden by generated text, no third-person, front-facing talking-head, over-the-shoulder, side camera, room camera, back shot, b-roll, or product-only insert"
                if mirror_selfie_lock
                else
                "full-body or near full-body head-to-toe creator framing for apparel/clothing; garment worn, complete outfit silhouette, garment length, hem, sleeves/straps, drape, body-to-garment scale, and natural human proportions visible; no face/chest-only crop"
                if _is_apparel_category(product_analysis)
                else "off-center creator framing, creator always visibly present with face, upper body, shoulder, or natural hands in frame, product clearly visible, no product-only insert shots"
            ),
            "continuity": link.get("next_scene_start"),
        },
                "lighting": {
                    "source": "warm podcast-studio key light with subtle LED accent" if finance_mode else "available natural window light or warm domestic lamp light",
                    "continuity": "keep direction and colour temperature stable between chained scenes",
                },
                "emotion": {
                    "angle": (ugc_strategy.get("emotional_angle") or {}).get("primary_safe_label"),
                    "scene_step": script.get("psychology_step"),
                    "delivery": (ugc_strategy.get("voice_personality") or {}).get("hook_delivery"),
                },
                "infographic": {
                    "notes": infographic_notes,
                    "labels": scene_on_screen_text if finance_mode else None,
                    "motion": (
                        "reuse approved scene concept infographic positions; gesture-synced highlight, slide, tick, or lower-third reveal"
                        if finance_mode
                        else None
                    ),
                    "language_rule": (
                        "Czech-only text with diacritics; no Polish, Slovak, English, pseudo-Czech, fake returns, or fake financial numbers"
                        if finance_mode
                        else None
                    ),
                },
                "motion": {
                    "avatar": (
                        "natural speaking motion with occasional blink, glance toward infographic, point beside body, light air-tap or small swipe to trigger highlights"
                        if finance_mode and avatar_on_camera
                        else "mirror-selfie live speaking motion starts immediately: tiny phone sway, blink, mouth/jaw/cheek movement matching the spoken line, and occasional free-hand garment gesture; no frozen face, no closed-mouth first seconds, no walking away, no full back turn"
                        if mirror_selfie_lock and avatar_on_camera
                        else "visible on-camera speaking motion with lips, jaw, cheeks, and small expression changes matching the spoken line; no closed-mouth or frozen-face narration; if the shot is a detail close-up, keep creator hands/torso visibly connected to the product"
                        if avatar_on_camera
                        else "no face visible unless planned"
                    ),
                    "product": link.get("motion_bridge")
                    or (
                        "no physical product; interactive infographic motion synced to hand gestures"
                        if finance_mode
                        else "small free-hand garment adjustment or pointing gesture while the phone remains visible in the mirror; relaxed adult hand, stable finger count, no hand distortion"
                        if mirror_selfie_lock
                        else "small natural product handling with relaxed adult hands, stable grip, natural finger count, no hand distortion"
                    ),
                    "last_frame": (
                        "brief stable-but-live mirror pose with blink or phone sway, not a frozen hold-frame"
                        if mirror_selfie_lock
                        else link.get("last_frame_capture")
                    ),
                },
                "product_rules": {
                    "fidelity": structured.get("fidelity") or content_prompt_package.get("product_fidelity_instruction"),
                    "material_lock": _material_lock(product_analysis),
                    "forbidden_material_substitution": _forbidden_material_substitution_rule(product_analysis),
                    "visual_classifier_requirements": _visual_classifier_requirements(product_analysis),
                    "reference": "no physical ecommerce product in finance mode" if finance_mode else "use product reference as source of truth",
                    "lock": "finance facts, Czech language, disclaimer, avatar identity, and compliance are locked" if finance_mode else "product not modified, not restyled, not recolored, not rebranded, not rematerialized",
                },
                "avatar_rules": {
                    "on_camera": avatar_on_camera,
                    "use_reference_image": structured.get("use_reference_image"),
                    "identity": "identity preserved, no facial morphing, no appearance drift",
                    "wardrobe": link.get("wardrobe_anchor"),
                    "instruction": _creator_presence_avatar_instruction(
                        structured.get("avatar_instruction"),
                        content_prompt_package.get("avatar_scene_instruction"),
                        finance_mode=finance_mode,
                    ),
                },
                "voiceover": scene_voiceover,
                "on_screen_text": scene_on_screen_text if generated_text_allowed else "",
            }
        )
    return blocks


def _ecommerce_hook_sticker_enabled(content_prompt_package: dict[str, Any]) -> bool:
    if content_prompt_package.get("creative_mode") == "finance_personal_brand":
        return False
    mode = content_prompt_package.get("ecommerce_hook_text_mode")
    if not isinstance(mode, dict):
        return False
    return bool(mode.get("enabled", False))


def _delivery_voiceover(preferred: Any, fallback: Any) -> str:
    preferred_text = str(preferred or "").strip()
    fallback_text = str(fallback or "").strip()
    if preferred_text and not _looks_like_internal_delivery_text(preferred_text):
        return preferred_text
    return fallback_text or preferred_text


def _delivery_scene_text(preferred: Any, fallback: Any, subtitle: Any, voiceover: Any, *, is_hook: bool, finance_mode: bool) -> str:
    if finance_mode:
        for value in [preferred, fallback, subtitle]:
            text = str(value or "").strip()
            if text:
                return text
        return ""
    candidates = [subtitle, preferred, fallback] if is_hook else [preferred, fallback, subtitle]
    for value in candidates:
        text = str(value or "").strip()
        if text and not _looks_like_internal_delivery_text(text):
            return _caption_from_voiceover(text) if is_hook else text
    if is_hook:
        return _caption_from_voiceover(voiceover)
    return ""


def _caption_from_voiceover(value: Any) -> str:
    words = [word.strip(" ,.;:!?\"'") for word in str(value or "").split() if word.strip(" ,.;:!?\"'")]
    return " ".join(words[:8])


def _looks_like_internal_delivery_text(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    markers = [
        "angle:",
        "hook intent",
        "visual direction",
        "creative test",
        "scene summary",
        "voiceover=",
        "on_screen_text",
        "structured prompt",
        "product_rules",
        "caption contract",
        "i'd show",
        "i would show",
        "i'd check",
        "i would check",
        "here, i'd",
        "then i'd",
        "tady bych",
        "hier wuerde ich",
        "hier würde ich",
    ]
    return any(marker in normalized for marker in markers)


def _ensure_creator_presence_summary(summary: Any) -> str:
    text = str(summary or "").strip()
    guard = (
        "creator/avatar remains visibly present in frame with face, upper body, shoulder, "
        "or natural hands connected to the product; spoken scenes keep face and mouth visible with natural lip and jaw movement; no product-only insert shot"
    )
    if not text:
        return guard
    lowered = text.lower()
    if "product-only" in lowered or "no person visible" in lowered or "environment shot" in lowered:
        text = re.sub(r"\bproduct-only\b", "creator-held product detail", text, flags=re.IGNORECASE)
        text = re.sub(r"\bno person visible\b", "creator visibly present", text, flags=re.IGNORECASE)
        text = re.sub(r"\benvironment shot\b", "creator-led scene", text, flags=re.IGNORECASE)
    if "creator" not in lowered and "avatar" not in lowered and "hands" not in lowered:
        return f"{text}, {guard}"
    if "product-only" not in lowered and "no person visible" not in lowered:
        return f"{text}, no product-only insert shot"
    return f"{text}, {guard}"


def _is_apparel_category(value: Any) -> bool:
    if isinstance(value, dict):
        haystack = " ".join(str(item or "") for item in value.values()).lower()
    else:
        haystack = str(value or "").lower()
    return any(
        token in haystack
        for token in [
            "apparel",
            "clothing",
            "garment",
            "dress",
            "jumpsuit",
            "shirt",
            "top",
            "trousers",
            "pants",
            "jacket",
            "coat",
        ]
    )


def _ensure_apparel_full_body_summary(
    summary: Any,
    index: int,
    *,
    mirror_selfie_lock: bool = False,
) -> str:
    text = str(summary or "").strip()
    lock = (
        "apparel mirror-selfie worn view required: adult creator wearing the garment in the same simple bedroom mirror reflection; "
        "smartphone visibly held in one hand inside the reflection but not covering the mouth while speaking; show full-body or near full-body head-to-toe reflected silhouette, natural body proportions, garment length, waist, neckline, hem, sleeves or straps, drape, cut, and body-to-garment scale; "
        "normal phone try-on check, modest expression, relaxed arms, small natural turn, not a polished ecommerce model pose or runway try-on; "
        "do not crop to only face, chest, waist, hands, flat lay, isolated fabric detail, or external-camera talking-head framing"
        if mirror_selfie_lock
        else (
            "apparel full-body worn view required: adult creator wearing the garment in a mirror, doorway, hallway, or simple standing phone shot; "
            "show full-body or near full-body head-to-toe silhouette, natural body proportions, garment length, hem, sleeves or straps, drape, and body-to-garment scale; "
            "normal phone try-on check, modest expression, relaxed arms, small natural turn, not a polished ecommerce model pose or runway try-on; "
            "do not crop to only face, chest, waist, hands, flat lay, or isolated fabric detail"
        )
    )
    if index > 0:
        lock += "; any detail close-up must follow or include a clear worn full-body context"
    return f"{text}, {lock}" if text else lock


def _creator_presence_avatar_instruction(
    structured_instruction: Any,
    fallback_instruction: Any,
    *,
    finance_mode: bool,
) -> str:
    instruction = str(structured_instruction or fallback_instruction or "").strip()
    if finance_mode:
        return instruction
    lowered = instruction.lower()
    if (
        not instruction
        or "no person visible" in lowered
        or "product-only" in lowered
        or "no reference image identity required" in lowered
        or "environment shot" in lowered
    ):
        instruction = str(fallback_instruction or "").strip() or (
            "same creator persona throughout the video, visibly present in frame, speaking naturally, "
            "subtle expression changes, creator hands/upper body connected to the product"
        )
    return _ensure_creator_presence_summary(instruction)


def _product_rules(product_analysis: dict[str, Any], content_prompt_package: dict[str, Any]) -> dict[str, Any]:
    facts = product_analysis.get("known_product_facts") or {}
    return {
        "category": product_analysis.get("likely_product_category"),
        "visual_understanding": _visual_classifier_requirements(product_analysis),
        "material": facts.get("material"),
        "color": facts.get("color"),
        "reference": product_analysis.get("product_image_path"),
        "category_prompt": content_prompt_package.get("category_prompt_directive"),
        "fidelity": content_prompt_package.get("product_fidelity_instruction"),
        "material_lock": _material_lock(product_analysis),
        "forbidden_material_substitution": _forbidden_material_substitution_rule(product_analysis),
        "lock": "product not modified, not restyled, not recolored, not rebranded, not rematerialized",
    }


def _visual_classifier_requirements(product_analysis: dict[str, Any]) -> dict[str, Any]:
    visual = product_analysis.get("visual_product_understanding") or {}
    if visual.get("status") != "completed":
        return {}
    return {
        "detected_object": visual.get("detected_object"),
        "subcategory": visual.get("subcategory"),
        "recommended_template_id": visual.get("recommended_template_id"),
        "scenario_rules": (visual.get("scenario_rules") or [])[:4],
        "shot_requirements": (visual.get("shot_requirements") or [])[:4],
        "avoid_in_generation": (visual.get("avoid_in_generation") or [])[:4],
        "qa_expectations": (visual.get("qa_expectations") or [])[:4],
        "rule": "use visual classifier requirements to choose proof shots and QA expectations; do not turn them into unsupported customer-facing claims",
    }


def _material_lock(product_analysis: dict[str, Any]) -> str:
    facts = product_analysis.get("known_product_facts") or {}
    material = str(facts.get("material") or "").strip()
    color = str(facts.get("color") or "").strip()
    if material and material.lower() != "unknown":
        color_part = f"; verified color={color}" if color and color.lower() != "unknown" else ""
        return (
            f"verified material={material}{color_part}; preserve exact material appearance, finish, texture scale, opacity/transparency, and gloss level from product reference in every scene; "
            "no category-default material styling"
        )
    return (
        "material unknown or not confidently verified; copy only visible material finish from product reference; "
        "do not introduce leather, suede, fabric, canvas, plastic, glass, metal, ceramic, wood, rubber, glossy, matte, transparent, opaque, pebbled, woven, quilted, padded, smooth, or grained material"
    )


def _forbidden_material_substitution_rule(product_analysis: dict[str, Any]) -> str:
    facts = product_analysis.get("known_product_facts") or {}
    material = str(facts.get("material") or "").strip().lower()
    forbidden = [
        "leather",
        "suede",
        "fabric",
        "canvas",
        "plastic",
        "glass",
        "metal",
        "ceramic",
        "wood",
        "rubber",
        "glossy",
        "matte",
        "transparent",
        "opaque",
        "pebbled",
        "woven",
        "quilted",
        "padded",
        "smooth",
        "grained",
    ]
    allowed = {item for item in forbidden if item in material}
    blocked = [item for item in forbidden if item not in allowed]
    return "do not make the product look like: " + ", ".join(blocked)


def _avatar_rules(content_prompt_package: dict[str, Any], ugc_strategy: dict[str, Any]) -> dict[str, Any]:
    scene_chaining = ugc_strategy.get("scene_chaining") or content_prompt_package.get("scene_chaining")
    return {
        "identity_contract": content_prompt_package.get("avatar_identity_contract"),
        "scene_instruction": content_prompt_package.get("avatar_scene_instruction"),
        "scene_chaining": _scene_chaining_contract(scene_chaining),
    }


def _voice_block(ugc_strategy: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile": ugc_strategy.get("voice_profile"),
        "personality": ugc_strategy.get("voice_personality"),
    }


def _language_guard(
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> dict[str, Any]:
    if content_prompt_package.get("creative_mode") == "finance_personal_brand":
        return {
            "rule": "CZECH LANGUAGE HARD LOCK",
            "spoken": "clean standard Czech with Czech diacritics",
            "visible_text": "all subtitles, lower thirds, chart labels, cards, and infographic text must be Czech only",
            "forbidden": "no Polish, Slovak, English filler, mixed-language text, pseudo-Czech, malformed Slavic words, fake return numbers",
            "fallback": "if readable Czech text is uncertain, use abstract UI shapes/icons without legible wrong-language text",
        }
    if _is_czech_language(ugc_strategy.get("language")):
        return {
            "rule": "CZECH LANGUAGE HARD LOCK",
            "spoken": "Czech only, cs-CZ pronunciation, Czech phrasing and sentence rhythm",
            "voice_profile_priority": "target language overrides avatar voice/persona notes; ignore any British, American, English, German, Polish, or Slovak language cue",
            "customer_copy": "product-note-derived phrases, hooks, spoken lines, post-production captions, and ad text must be Czech only",
            "forbidden": "no English, Polish, Slovak, German, bilingual filler, mixed-language text, pseudo-Czech, malformed Slavic words, or untranslated product notes",
            "visible_text_fallback": "for ecommerce video render no generated text; use spoken Czech audio and verified product markings already present on the reference only",
        }
    return {
        "language": ugc_strategy.get("language"),
        "rule": "customer-facing copy, product-note-derived phrases, spoken audio, post-production captions, and ad text must use the requested language; translate internal product notes naturally instead of copying raw notes",
        "visible_text_fallback": "for ecommerce video render no generated text; only verified product markings or an exact requested personalization word may remain visible",
    }


def _speech_audio_contract(
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> dict[str, Any]:
    if content_prompt_package.get("creative_mode") == "finance_personal_brand":
        return {
            "rule": "SPOKEN AUDIO REQUIREMENT",
            "avatar_speech": "the visible avatar must speak Czech only",
            "audio_generation": "generate audio in natural Czech, cs-CZ, with Czech pronunciation and sentence rhythm",
            "approved_script": ugc_strategy.get("voiceover"),
            "lip_sync": "lips must sync to the Czech voiceover exactly",
            "forbidden": "do not translate, dub, paraphrase, or switch to English, Polish, Slovak, mixed Slavic, or pseudo-Czech speech",
        }
    if _is_czech_language(ugc_strategy.get("language")):
        return {
            "rule": "SPOKEN AUDIO REQUIREMENT - CZECH ONLY",
            "avatar_speech": "the visible avatar must speak Czech only",
            "audio_generation": "generate audio in natural Czech, cs-CZ, with Czech pronunciation and sentence rhythm",
            "approved_script": ugc_strategy.get("voiceover"),
            "lip_sync": "avatar lips must sync to the approved Czech voiceover exactly",
            "visible_speaking": "speech must come from the on-camera avatar with visible mouth, jaw, cheek, and expression movement",
            "forbidden": "do not translate, dub, paraphrase, switch language, hide the mouth, freeze the face, or create off-camera narration over silent footage",
        }
    return {
        "rule": "spoken language follows requested output language",
        "language": ugc_strategy.get("language"),
        "voiceover": ugc_strategy.get("voiceover"),
        "audio_generation": "generate audible natural on-camera creator speech for every avatar-on-camera scene, not off-camera narration",
        "lip_sync": "avatar lips must match the approved voiceover exactly; no silent avatar, no silent mouthing, no text-only delivery",
        "visible_speaking": "keep the speaking face and mouth visible with natural lip, jaw, cheek, blink, and micro-expression movement",
        "forbidden": "no frozen face, no closed-mouth speech, no delayed dubbing, no audio laid over a silent avatar",
    }


def _seedance_provider_contract(
    content_prompt_package: dict[str, Any],
    ugc_strategy: dict[str, Any],
) -> dict[str, Any]:
    payload = content_prompt_package.get("seedance_payload") or {}
    reference_count = len(payload.get("input_references") or [])
    frame_count = len(payload.get("frame_images") or [])
    avatar_reference_mode = payload.get("avatar_reference_mode")
    reference_roles = [
        "product reference image controls product shape, colour, material, markings, scale, and fidelity; input_references image 1 is the product identity source; exact product identity also locks finish, texture, transparency/opacity, proportions, print, size class, and physical dimensions"
    ]
    if avatar_reference_mode == "exact_image_input_reference":
        reference_roles.append(
            "input_references image 2 is the avatar identity source only; avatar reference image controls creator identity only, not product choice, object shape, room props, or product material; prompt controls motion, expression, speech, and simple camera behaviour"
        )
    if frame_count:
        reference_roles.append(
            "frame image is an approved scene/layout reference; preserve its composition and do not replace it with generic charts or a new set"
        )
    hook_sticker_text = _approved_hook_sticker_text(content_prompt_package, ugc_strategy)
    return {
        "source": "video generation prompt adaptation",
        "reference_count": reference_count,
        "frame_image_count": frame_count,
        "reference_roles": reference_roles,
        "timing_rule": "use explicit cumulative time ranges for each scene; for 13-15s assets keep 3-4 simple segments",
        "prompt_shape": (
            "subject/action sequence + environment/lighting + camera language + spoken script + no generated on-screen text"
            if content_prompt_package.get("creative_mode") != "finance_personal_brand"
            else "subject/action sequence + podcast studio/infographic layout + camera language + spoken script + approved Czech visible text"
        ),
        "continuity_rule": "use references as source of truth for their roles only: product reference controls product fidelity, avatar reference controls identity; never substitute a generic category product or change material, size, proportions, finish, markings, print, or scale; do not copy avatar-reference background as the scene environment",
        "motion_rule": (
            "simple creator-video motion only: static shot, slight handheld sway, slow push-in, natural visible speaking motion with lips and jaw articulating the spoken line"
            if content_prompt_package.get("creative_mode") != "finance_personal_brand"
            else "podcast-studio motion only: static camera or slow push-in, gesture-synced infographic highlights"
        ),
        "audio_delivery_rule": (
            "audio must read as live on-camera speech from the visible avatar; no off-camera narrator feel, no silent avatar with audio laid over it, no mouth hidden by phone or crop"
            if content_prompt_package.get("creative_mode") != "finance_personal_brand"
            else "audio must be live Czech presenter speech from the visible avatar, synced to face movement"
        ),
        "geometry_rule": (
            "preserve normal smartphone 9:16 framing and natural human proportions; no fisheye, ultra-wide stretch, mirror warp, elongated limbs, oversized head, or body squeeze"
            if content_prompt_package.get("creative_mode") != "finance_personal_brand"
            else "preserve normal presenter proportions and frame geometry"
        ),
        "creator_presence_rule": (
            "creator/avatar must be visibly present in every ecommerce UGC scene; product proof may be a close-up, but it must be creator-held, creator-worn, or framed with face/torso/hands visible; no product-only inserts"
            if content_prompt_package.get("creative_mode") != "finance_personal_brand"
            else "creator stays visible as the personal-brand presenter unless an approved infographic-only cutaway is explicitly part of the finance scene concept"
        ),
        "hand_rule": "use relaxed adult hands, natural five-finger anatomy, stable grip, and slow product handling; no extra, missing, fused, warped, or melting fingers",
        "visible_text_rule": (
            "render no generated on-screen text: no hook sticker, subtitles, captions, lower thirds, labels, CTA text, fake buttons, URLs, click/tap wording, platform UI, title cards, prompt labels, scene labels, internal production labels, random words, or later-scene text; spoken audio carries the message and all captions are post-production only; only verified product markings already present on the reference or an exact requested personalization word printed on the product may remain visible"
            if content_prompt_package.get("creative_mode") != "finance_personal_brand"
            else "all visible text must be Czech with diacritics and reuse the approved infographic plan"
        ),
        "spoken_hook": hook_sticker_text if content_prompt_package.get("creative_mode") != "finance_personal_brand" else None,
        "subtitle_fragments": (
            (ugc_strategy.get("subtitles") or [])[:4]
            if content_prompt_package.get("creative_mode") == "finance_personal_brand"
            else []
        ),
    }


def _approved_hook_sticker_text(
    content_prompt_package: dict[str, Any],
    ugc_strategy: dict[str, Any],
) -> str:
    if not _ecommerce_hook_sticker_enabled(content_prompt_package):
        return ""
    mode = content_prompt_package.get("ecommerce_hook_text_mode") or {}
    if isinstance(mode, dict):
        text = str(mode.get("text") or "").strip()
        if text:
            return _caption_from_voiceover(text)
    for value in [
        (ugc_strategy.get("on_screen_text") or [None])[0]
        if isinstance(ugc_strategy.get("on_screen_text"), list)
        else None,
        (ugc_strategy.get("subtitles") or [None])[0]
        if isinstance(ugc_strategy.get("subtitles"), list)
        else None,
        ugc_strategy.get("hook"),
    ]:
        text = str(value or "").strip()
        if text and not _looks_like_internal_delivery_text(text):
            return _caption_from_voiceover(text)
    return ""


def _emotion_block(ugc_strategy: dict[str, Any]) -> dict[str, Any]:
    return ugc_strategy.get("emotional_angle") or {}


def _learning_block(
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
) -> dict[str, Any]:
    guidance = (
        ugc_strategy.get("creative_memory_rag")
        or content_prompt_package.get("creative_memory_guidance")
        or ((ugc_strategy.get("performance_insights") or {}).get("creative_memory_rag"))
        or {}
    )
    return {
        "source": "creative_memory_rag",
        "prompt_guidance": guidance.get("prompt_guidance"),
        "winning_patterns": (guidance.get("winning_patterns") or [])[:8],
        "avoid_patterns": (guidance.get("avoid_patterns") or [])[:8],
        "confidence": ((guidance.get("learning_layer") or {}).get("confidence")),
        "rule": "use memory as bias only, never invent claims or override product/avatar fidelity",
    }


def _approved_scene_concept(
    content_prompt_package: dict[str, Any],
    ugc_strategy: dict[str, Any],
) -> dict[str, Any]:
    concept = content_prompt_package.get("finance_scene_concept") or ugc_strategy.get("finance_scene_concept") or {}
    if not isinstance(concept, dict) or not concept:
        return {}
    return {
        "status": concept.get("status"),
        "visual_brief": concept.get("visual_brief"),
        "infographic_system": concept.get("infographic_system"),
        "infographic_elements": concept.get("infographic_elements"),
        "interaction_plan": concept.get("interaction_plan"),
        "compiled_video_lock": concept.get("video_prompt_addendum_compiled"),
        "rule": "must be reused in final video; do not replace with generic charts or wrong-language graphics",
    }


def _environment_control(content_prompt_package: dict[str, Any]) -> dict[str, Any]:
    control = content_prompt_package.get("environment_control") or {}
    directive = content_prompt_package.get("environment_control_directive") or control.get("directive")
    finance_mode = content_prompt_package.get("creative_mode") == "finance_personal_brand"
    lock = content_prompt_package.get("user_scenario_lock") or {}
    mirror_selfie_lock = isinstance(lock, dict) and lock.get("template_id") == "mirror_selfie_try_on_review"
    background_consistency = control.get("background_consistency") or "strict"
    environment_override = bool(control.get("environment_override", False))
    preserve_original_scene_layout = bool(control.get("preserve_original_scene_layout", False))
    environment_selection = (
        "user_scenario_mirror_selfie"
        if mirror_selfie_lock
        else control.get("environment_selection") or "category_auto"
    )
    return {
        "settings": (
            f"background_consistency={background_consistency}; "
            f"environment_override={str(environment_override).lower()}; "
            f"preserve_original_scene_layout={str(bool(preserve_original_scene_layout)).lower()}; "
            f"environment_selection={environment_selection}"
        ),
        "background_consistency": background_consistency,
        "environment_override": environment_override,
        "preserve_original_scene_layout": preserve_original_scene_layout,
        "environment_selection": environment_selection,
        "directive": directive,
        "rule": (
            "finance mode is a personal-brand ad, not UGC; use podcast-studio consistency, clean Czech labels, and compliance-safe infographic motion that reacts to creator gaze, pointing, and air-tap gestures"
            if finance_mode
            else "User-approved mirror selfie overrides normal automatic location selection: keep one simple bedroom mirror reflection setup with smartphone visibly held by the creator in one hand; continuous mirror perspective only; no non-bedroom/public/work/outdoor locations, tripod, external camera setup, side filming, b-roll, cutaway, or perspective switch."
            if mirror_selfie_lock
            else "Creator-video authenticity comes from camera motion, speaking cadence, natural delivery, and product handling. Use a category-selected real environment from product type and context; avatar reference controls identity only and product reference controls product fidelity only."
        ),
    }


def _camera_global(ugc_strategy: dict[str, Any], content_prompt_package: dict[str, Any] | None = None) -> dict[str, Any]:
    if (content_prompt_package or {}).get("creative_mode") == "finance_personal_brand":
        return {
            "style": "personal-brand podcast studio ad, not UGC",
            "safe_area": (ugc_strategy.get("platform_adaptation") or {}).get("safe_area"),
            "environment_rule": "default to the modern podcast studio setup; no fake bank, broker, or institution branding; keep hands visible when the creator interacts with infographics",
        }
    if _is_mirror_selfie_lock(content_prompt_package or {}, ugc_strategy):
        return {
            "style": "authentic handheld mirror selfie try-on, not studio commercial",
            "safe_area": (ugc_strategy.get("platform_adaptation") or {}).get("safe_area"),
            "environment_rule": "single simple bedroom mirror setup; the smartphone is visible in creator's hand in the mirror reflection but low or to the side so the mouth remains visible while speaking; continuous mirror perspective only; no external camera, talking-head setup, third-person angle, side filming, over-the-shoulder shot, room camera, tripod, b-roll, cutaway, or perspective switch",
            "opening_motion": "first frame starts live with tiny phone sway, blink, mouth/jaw beginning the spoken hook, or a small free-hand gesture; no frozen still frame",
            "hands": "one hand holds the smartphone naturally; free hand points to waist, neckline, cut, or fit; avoid distorted fingers",
        }
    return {
        "style": "smartphone creator footage, not studio commercial",
        "safe_area": (ugc_strategy.get("platform_adaptation") or {}).get("safe_area"),
        "environment_rule": "choose one minimal category-appropriate real environment; do not copy avatar reference background, product reference background, or create a random lifestyle set",
        "hands": "avoid complex finger poses; use stable product grip or crop hands if uncertain",
    }


def _lighting_global(content_prompt_package: dict[str, Any] | None = None) -> dict[str, Any]:
    if (content_prompt_package or {}).get("creative_mode") == "finance_personal_brand":
        return {
            "style": "warm podcast-studio key light, subtle LED accent, professional but realistic skin tones",
            "environment_rule": "keep podcast-studio lighting consistent across scenes",
        }
    lock = (content_prompt_package or {}).get("user_scenario_lock") or {}
    if isinstance(lock, dict) and lock.get("template_id") == "mirror_selfie_try_on_review":
        return {
            "style": "natural indoor daylight or soft bedroom lamp light, realistic colour temperature",
            "environment_lock": "same simple bedroom mirror reflection setup across scenes",
            "avoid": "studio lighting, ring-light beauty look, cinematic grading, glossy fashion lighting",
        }
    return {
        "style": "natural domestic light, realistic colour temperature",
        "environment_lock": "keep lighting consistent in the selected category-auto environment; choose one minimal category-appropriate physical context and do not copy the avatar reference background",
        "avoid": "ring-light beauty look, cinematic grading, glossy studio lighting",
    }


def _motion_global(ugc_strategy: dict[str, Any]) -> dict[str, Any]:
    scene_chaining = ugc_strategy.get("scene_chaining") or {}
    lock = ugc_strategy.get("user_scenario_lock") or {}
    mirror_selfie_lock = isinstance(lock, dict) and lock.get("template_id") == "mirror_selfie_try_on_review"
    return {
        "scene_chaining": scene_chaining.get("seedance_prompt_addendum"),
        "continuity_plan": _scene_chaining_contract(scene_chaining),
        "camera_movement": (
            "mirror-selfie phone movement only: slight handheld shake, tiny sway, partial side-turn while still facing mirror; no static opening hold, no walking away, no full back turn, no external camera"
            if mirror_selfie_lock
            else "simple only: static, slight handheld sway, slow push-in"
        ),
    }


def _is_mirror_selfie_lock(
    content_prompt_package: dict[str, Any],
    ugc_strategy: dict[str, Any],
) -> bool:
    lock = content_prompt_package.get("user_scenario_lock") or ugc_strategy.get("user_scenario_lock") or {}
    return isinstance(lock, dict) and lock.get("enabled") and lock.get("template_id") == "mirror_selfie_try_on_review"


def _structured_mirror_selfie_lock(structured: dict[str, Any]) -> bool:
    lock = structured.get("user_scenario_lock") or {}
    return isinstance(lock, dict) and lock.get("template") == "mirror_selfie_try_on_review"


def _mirror_selfie_environment_lock() -> str:
    return (
        "single simple bedroom mirror-selfie environment with plain neutral wall and minimal background; "
        "creator films herself through the mirror with smartphone visibly held in one hand inside the reflection, low or to the side while speaking so the mouth remains visible; "
        "natural indoor daylight, slight handheld phone shake; continuous mirror perspective only; no non-bedroom/public/work/outdoor locations, no secondary room setup, no studio, no tripod, no external camera, no ordinary talking-head setup, no side filming, no over-the-shoulder shot, no room camera, no cinematic b-roll, no cutaway, no perspective switch, and no avatar walking away from the mirror"
    )


def _ugc_prompt_skill(ugc_strategy: dict[str, Any]) -> dict[str, Any] | None:
    guidance = ugc_strategy.get("ugc_prompt_skill")
    if not isinstance(guidance, dict) or not guidance:
        return None
    prompt_rules = guidance.get("prompt_rules") or {}
    return {
        "source": guidance.get("source"),
        "template": guidance.get("template_name") or guidance.get("template_id"),
        "template_reason": guidance.get("template_reason"),
        "arcads_api": "ignored; use this app's video pipeline",
        "beat_structure": guidance.get("beat_structure"),
        "camera_style": guidance.get("camera_style"),
        "no_generated_text": prompt_rules.get("no_generated_text"),
        "realism": prompt_rules.get("realism"),
        "avoid_style": prompt_rules.get("avoid_style"),
        "avoid_words": prompt_rules.get("avoid_words"),
        "closing_emotion": guidance.get("closing_emotion"),
    }


def _user_scenario_lock(
    content_prompt_package: dict[str, Any],
    ugc_strategy: dict[str, Any],
) -> dict[str, Any] | None:
    lock = content_prompt_package.get("user_scenario_lock") or ugc_strategy.get("user_scenario_lock")
    if not isinstance(lock, dict) or not lock.get("enabled"):
        return None
    return {
        "source": lock.get("source"),
        "priority": lock.get("priority"),
        "template": lock.get("template_id"),
        "spoken_hook": lock.get("hook_text"),
        "raw_user_direction": lock.get("raw_user_direction"),
        "detected_traits": lock.get("detected_traits"),
        "rules": (lock.get("rules") or [])[:12],
        "forbidden": (lock.get("forbidden") or [])[:8],
        "rule": (
            "preserve the user-provided camera setup, setting, pacing, shot style, and creator behaviour; "
            "override it only for product fidelity, avatar identity, safety, target language, or verified product facts"
        ),
    }


def _scene_chaining_contract(scene_chaining: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(scene_chaining, dict) or not scene_chaining:
        return {}
    plan = scene_chaining.get("true_scene_chaining_plan") or {}
    execution = scene_chaining.get("provider_execution") or {}
    return {
        "version": scene_chaining.get("version"),
        "mode": scene_chaining.get("mode"),
        "strategy": plan.get("strategy") or scene_chaining.get("reference_strategy"),
        "execution": execution.get("current_mode"),
        "actual_last_frame_reuse": execution.get("actual_last_frame_reuse"),
        "identity_lock": plan.get("identity_lock") or scene_chaining.get("identity_continuity"),
        "environment_lock": plan.get("environment_lock") or scene_chaining.get("environment_continuity"),
        "wardrobe_lock": plan.get("wardrobe_lock") or scene_chaining.get("wardrobe_continuity"),
        "product_or_graphic_lock": plan.get("product_or_graphic_lock"),
        "scene_link_count": plan.get("scene_link_count") or len(scene_chaining.get("scene_links") or []),
        "quality_requirements": (plan.get("quality_requirements") or [])[:4],
    }


def _block_line(name: str, value: Any, *, compact: bool = False) -> str:
    compact_limit = 1100 if name in {"video_extra_direction", "user_scenario_lock"} else 320
    label = PROVIDER_BLOCK_LABELS.get(name, str(name).replace("_", " ").title())
    return f"{label}: {_compact(value, max_value_chars=compact_limit if compact else None)}."


def _short_block_line(name: str, value: Any, keys: list[str]) -> str:
    if not isinstance(value, dict):
        return _block_line(name, value, compact=True)
    short = {key: value.get(key) for key in keys if value.get(key) not in (None, "", [], {})}
    return _block_line(name, short, compact=True)


def _compact(value: Any, *, max_value_chars: int | None = None) -> str:
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item in (None, "", [], {}):
                continue
            parts.append(f"{key}:{_compact(item, max_value_chars=max_value_chars)}")
        return "{" + "; ".join(parts) + "}"
    if isinstance(value, list):
        return (
            "["
            + "; ".join(
                _compact(item, max_value_chars=max_value_chars)
                for item in value
                if item not in (None, "", [], {})
            )
            + "]"
        )
    return _clip(" ".join(str(value or "").split()), max_value_chars)


def _clip(value: Any, limit: int | None) -> str:
    text = " ".join(str(value or "").split())
    if not limit or len(text) <= limit:
        return text
    trimmed = text[: max(0, limit - 3)].rstrip(" ,.;:")
    return f"{trimmed}..."


def _with_reusable_block_glossary(compression: dict[str, Any]) -> str:
    prompt = str(compression.get("compressed_prompt") or "").strip()
    blocks = compression.get("reusable_blocks") or {}
    used_tokens = [
        (token, phrase)
        for token, phrase in blocks.items()
        if f"@{token}" in prompt
    ]
    if not used_tokens:
        return prompt
    glossary = "; ".join(f"@{token} means {phrase}" for token, phrase in used_tokens)
    return f"{prompt} Reusable blocks glossary: {glossary}."


def _fit_prompt_to_limit(prompt: str, limit: int) -> str:
    text = " ".join(str(prompt or "").split())
    if len(text) <= limit:
        return text

    suffix_candidates = [
        text.rfind("Negative prompt:"),
        text.rfind("Reusable blocks glossary:"),
    ]
    suffix_start = max(index for index in suffix_candidates if index >= 0) if any(
        index >= 0 for index in suffix_candidates
    ) else -1
    suffix = text[suffix_start:] if suffix_start >= 0 else ""
    if len(suffix) > 3200:
        suffix = _clip(suffix, 3200)

    marker = (
        " Provider prompt shortened to fit API size limit; preserve the structured scene intent, "
        "strict visual reference, avatar identity lock, product fidelity, safe areas, and negative prompt."
    )
    prefix_budget = max(1200, limit - len(suffix) - len(marker) - 2)
    prefix = text[:prefix_budget].rstrip()
    sentence_cut = max(prefix.rfind(". "), prefix.rfind("| "))
    if sentence_cut > 1200:
        prefix = prefix[: sentence_cut + 1].rstrip()
    fitted = f"{prefix}{marker}"
    if suffix:
        fitted = f"{fitted} {suffix}"
    if len(fitted) > limit:
        fitted = fitted[:limit].rstrip()
    return fitted


def _legacy_preamble(content_prompt_package: dict[str, Any], settings: dict[str, Any]) -> str:
    if settings.get("base_video_prompt_template"):
        return str(content_prompt_package.get("seedance_video_prompt") or "")
    return ""
