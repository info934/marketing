from __future__ import annotations

import math
import json
import re
from typing import Any

import requests

from app import config


DEFAULT_FINANCE_DISCLAIMER = (
    "Vzdělávací obsah, nejde o individuální investiční ani finanční doporučení."
)


DEFAULT_SERIES_SECONDS = 15
WORDS_PER_15S_VIDEO = 42


def is_finance_mode(settings: dict[str, Any] | None) -> bool:
    return str((settings or {}).get("app_mode") or "").strip() == "finance_personal_brand"


def normalize_settings(
    *,
    product_name: str,
    product_info: str,
    product_category: str,
    language: str,
    generation_mode: str,
    generate_static_images: bool,
    finance_video_topic: str,
    finance_video_script: str,
    finance_disclaimer: str,
) -> dict[str, Any]:
    topic = _clean_text(finance_video_topic) or "Finanční osobní brand video"
    script = _clean_text(finance_video_script)
    notes = _clean_text(product_info)
    merged_notes = "\n\n".join(part for part in [script, notes] if part)
    return {
        "product_name": _clean_text(product_name) or topic,
        "product_info": merged_notes or topic,
        "product_category": "finance",
        "language": "cs",
        "generation_mode": "video",
        "generate_static_images": False,
        "finance_video_topic": topic,
        "finance_video_script": script,
        "finance_disclaimer": _clean_text(finance_disclaimer) or DEFAULT_FINANCE_DISCLAIMER,
        "was_finance_mode": True,
        "original_language": language,
        "original_generation_mode": generation_mode,
        "original_generate_static_images": generate_static_images,
        "original_product_category": product_category,
    }


def prepare_script_plan(
    *,
    topic: str,
    user_script: str,
    disclaimer: str,
    platform: str,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
) -> dict[str, Any]:
    fallback = _deterministic_script_plan(
        topic=topic,
        user_script=user_script,
        disclaimer=disclaimer,
        platform=platform,
    )
    if not api_key:
        return {
            **fallback,
            "status": "deterministic_fallback",
            "model": model or config.OPENROUTER_PROMPT_MODEL,
            "reason": "OPENROUTER_API_KEY is missing; deterministic finance script agent was used.",
        }

    prompt_model = model or config.OPENROUTER_PROMPT_MODEL
    system = (
        "You are a Finance Personal Brand Video Script Agent for Czech Meta Ads and Instagram. "
        "Create a professional short-form personal-brand ad script plan before any video generation. This is not UGC. "
        "Default visual world: modern podcast studio, expert interview set, desk microphone or boom arm visible, acoustic panels, warm key light, subtle LED accent, premium but realistic. "
        "Return ONLY valid JSON. No markdown. The content must be strict standard Czech, compliant, calm, personal-brand, and suitable for a trustworthy finance educator. "
        "Language guard: use only natural Czech with Czech diacritics; do not use Polish, Slovak, English filler, malformed Slavic words, or machine-translated phrasing. "
        "Do not promise returns, use risk-free wording, give individualized financial advice, invent numbers, mention fake client results, or use pressure selling. "
        "Each 15s episode voiceover must be max 42 words. If the user content has too many distinct ideas, split into multiple 15s episodes. "
        "Each episode needs: title, hook, voiceover, scenes with time/visual/on_screen_text/infographic, and why_this_episode_exists. "
        "Modern infographics should be premium motion design: clean lower thirds, kinetic Czech typography, glassmorphism finance cards, timelines, simple charts without invented numbers, and readable Czech labels. "
        "The creator must interact with infographics naturally: glancing at them, pointing beside the body, lightly tapping or swiping in the air, and timing hand gestures so cards highlight, slide, or tick on cue. "
        "Keep interactions physically plausible and subtle; no sci-fi hologram, no giant UI panels covering the face, no unreadable dense charts."
    )
    user = {
        "task": "Prepare the final script plan first, then decide whether it fits one 15s video or needs a short series.",
        "topic": _clean_text(topic),
        "user_script": _clean_text(user_script)[:7000],
        "platform": platform if platform in {"meta", "instagram"} else "meta",
        "language": "cs",
        "language_quality_rules": [
            "Use clean Czech only, with Czech diacritics",
            "No Polish, Slovak, English filler, or mixed-language captions",
            "Infographic labels and on-screen text must also be Czech",
        ],
        "default_scene_style": "modern podcast studio personal-brand ad, expert interview setup, warm key light, acoustic panels, subtle LED accent, modern financial infographics that react to creator gestures",
        "disclaimer": _clean_text(disclaimer) or DEFAULT_FINANCE_DISCLAIMER,
        "output_contract": {
            "status": "ai_refined",
            "recommended_video_count": "integer",
            "canonical_script": "string",
            "episodes": [
                {
                    "episode_id": "finance_video_1",
                    "title": "string",
                    "hook": "string",
                    "voiceover": "max 42 Czech words",
                    "duration_seconds": 15,
                    "position": 1,
                    "total": "integer",
                    "scenes": [
                        {"time": "0-5s", "visual": "string", "on_screen_text": "max 6 words", "infographic": "string"}
                    ],
                    "why_this_episode_exists": "string",
                }
            ],
            "safety_notes": ["string"],
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Finance Script Agent",
    }
    payload = {
        "model": prompt_model,
        "temperature": 0.25,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "usage": {"include": True},
    }
    try:
        response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
        parsed = _parse_json_object(content)
        normalized = _normalize_script_plan(parsed, fallback=fallback)
        normalized["status"] = "ai_refined"
        normalized["model"] = prompt_model
        normalized["generation_id"] = raw.get("id")
        normalized["usage"] = raw.get("usage")
        return normalized
    except Exception as exc:
        return {
            **fallback,
            "status": "deterministic_fallback",
            "model": prompt_model,
            "error": _format_prompt_error(exc),
            "reason": "Finance script AI refinement failed; deterministic finance script agent was used.",
        }


def plan_video_series(
    *,
    topic: str,
    script: str,
    script_plan: dict[str, Any] | None = None,
    allow_series: bool,
    confirmed: bool,
    target_seconds: int = DEFAULT_SERIES_SECONDS,
) -> dict[str, Any]:
    prepared = script_plan or {}
    prepared_episodes = [
        episode for episode in (prepared.get("episodes") or []) if isinstance(episode, dict)
    ]
    clean_script = _sanitize_finance_script(
        _clean_text(prepared.get("canonical_script") or script)
    )
    words = sum(_word_count(episode.get("voiceover") or episode.get("script") or "") for episode in prepared_episodes) or _word_count(clean_script)
    words_per_video = max(28, int(WORDS_PER_15S_VIDEO * max(1, target_seconds) / DEFAULT_SERIES_SECONDS))
    video_count = max(1, len(prepared_episodes) or math.ceil(words / words_per_video)) if words else 1
    episodes = _prepared_series_episodes(prepared_episodes, target_seconds) or _series_episodes(
        topic=_clean_text(topic) or "Finanční osobní brand video",
        script=clean_script,
        video_count=video_count,
        words_per_video=words_per_video,
        target_seconds=target_seconds,
    )
    return {
        "enabled": bool(allow_series),
        "confirmed": bool(confirmed),
        "target_seconds_per_video": target_seconds,
        "words_per_video_budget": words_per_video,
        "script_word_count": words,
        "video_count": video_count,
        "needs_confirmation": bool(allow_series and video_count > 1 and not confirmed),
        "reason": (
            f"Text má přibližně {words} slov, jedno {target_seconds}s video bezpečně unese asi {words_per_video} slov."
            if video_count > 1
            else "Text se vejde do jednoho finance videa."
        ),
        "episodes": episodes,
        "script_agent_status": prepared.get("status"),
    }


def generate_strategy(
    *,
    product_analysis: dict[str, Any],
    avatar: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    duration = int(settings.get("video_length") or 30)
    topic = _clean_text(settings.get("finance_video_topic")) or product_analysis.get("product_name") or "Finanční téma"
    raw_script = _clean_text(settings.get("finance_video_script")) or _clean_text(product_analysis.get("internal_brief_notes"))
    safe_script = _sanitize_finance_script(raw_script) or (
        "Vysvětli jednoduchým jazykem, jak nad financemi přemýšlet bez zbytečného stresu."
    )
    series_plan = settings.get("finance_video_series") or {}
    approved_scene_concept = settings.get("finance_scene_concept") or {}
    if series_plan.get("confirmed") and series_plan.get("episodes"):
        safe_script = _clean_text(series_plan["episodes"][0].get("script")) or safe_script
    disclaimer = _clean_text(settings.get("finance_disclaimer")) or DEFAULT_FINANCE_DISCLAIMER
    scene_count = 4 if duration >= 20 else 3
    chunks = _script_chunks(safe_script, scene_count)
    overlays = _overlay_texts(topic, chunks, disclaimer)
    scene_durations = _scene_durations(duration, scene_count)
    scene_times = _scene_times(scene_durations)
    visuals = [
        "creator speaks directly to camera in a modern podcast studio, desk microphone visible, warm key light, acoustic panels and subtle LED accent, animated Czech headline lower third appears beside the creator as the creator briefly glances toward it and points to the first keyword",
        "creator explains the core idea from the podcast desk, modern glassmorphism infographic cards appear one by one, the creator taps the air beside each card so it highlights in sync with the spoken point",
        "creator gestures lightly toward a floating checklist and timeline, premium podcast-studio background stays consistent, the checklist ticks and the timeline marker moves when the creator points, readable Czech labels",
        "creator closes calmly in the same podcast studio setup, disclaimer lower third slides in after a small hand cue, minimal chart icons and brand-safe motion graphics remain below face level",
    ][:scene_count]
    concept_beats = approved_scene_concept.get("scene_beats") if isinstance(approved_scene_concept, dict) else []
    concept_elements = approved_scene_concept.get("infographic_elements") if isinstance(approved_scene_concept, dict) else []
    scenes = []
    purposes = ["hook", "education", "framework", "cta"][:scene_count]
    for index in range(scene_count):
        voiceover = chunks[index] if index < len(chunks) else disclaimer
        if index == scene_count - 1 and disclaimer.lower() not in voiceover.lower():
            voiceover = f"{voiceover} {disclaimer}"
        concept_beat = concept_beats[min(index, len(concept_beats) - 1)] if concept_beats else {}
        visual = visuals[index]
        infographic = _finance_scene_infographic_for_index(
            index=index,
            concept_beat=concept_beat if isinstance(concept_beat, dict) else {},
            concept_elements=concept_elements if isinstance(concept_elements, list) else [],
        )
        if approved_scene_concept:
            visual = _clean_text(
                f"{visual}, reuse approved scene concept layout and infographic positions exactly: {approved_scene_concept.get('visual_brief', '')}"
            )
        scenes.append(
            {
                "time": scene_times[index],
                "visual": visual,
                "voiceover": voiceover,
                "on_screen_text": overlays[index],
                "infographic": infographic,
                "subtitle": voiceover,
                "shot_type": ["personal brand hook", "infographic explainer", "framework breakdown", "compliant close"][index],
                "psychology_step": purposes[index],
            }
        )

    return {
        "agent": "Finance Personal Brand Video Agent",
        "selected_angle": "finance_personal_brand_education",
        "ad_detail_phrases": ["educational finance explanation", "personal brand trust", "clear compliance disclaimer"],
        "platform": str(settings.get("platform") or "meta").lower(),
        "market": str(settings.get("market") or "CZ"),
        "language": "cs",
        "language_instruction": "Veškerý mluvený text, titulky a grafika musí být kvalitní čeština. Nepoužívej polštinu, slovenštinu ani smíšený jazyk.",
        "voice_profile": (
            "spisovná, ale přirozená čeština pro osobní brand, klidný odborný tón, srozumitelně a lidsky, "
            "žádná polština, slovenština ani anglické výplně, bez agresivního prodeje a bez garancí výsledků"
        ),
        "voice_personality": {
            "tone": "důvěryhodný, klidný, odborný",
            "energy": "střední",
            "creator_style": "osobní brand finančního edukátora v moderním podcastovém studiu",
        },
        "duration_seconds": duration,
        "aspect_ratio": "9:16",
        "platform_adaptation": {
            "style": "personal brand finance ad from a modern podcast studio, not UGC",
            "safe_area": "keep face, hands, captions, disclaimer, and interactive infographic labels inside central safe area",
            "hook_timing": "Hook appears in the first 3 seconds",
        },
        "category_video_recipe": {
            "category": "finance",
            "source": "finance personal brand mode",
            "scene_visuals": visuals,
            "scene_shot_types": [scene["shot_type"] for scene in scenes],
        },
        "performance_insights": settings.get("performance_insights") or {},
        "audience_research": settings.get("audience_research") or {},
        "creative_psychology": settings.get("creative_psychology") or {},
        "hook_strategy": {"selected_hook": chunks[0], "source": "user_finance_script"},
        "scene_direction": {"directed_scenes": scenes, "source": "finance_personal_brand_mode"},
        "scene_chaining": settings.get("scene_chaining") or {},
        "hook": chunks[0],
        "scene_by_scene_script": scenes,
        "voiceover": " ".join(scene["voiceover"] for scene in scenes),
        "on_screen_text": [scene["on_screen_text"] for scene in scenes],
        "subtitles": [scene["subtitle"] for scene in scenes],
        "cta": "handled_by_ad_platform",
        "tone": "finance education, personal brand, trustworthy, compliant, modern podcast studio, interactive premium infographics, strict Czech",
        "finance_compliance": {
            "mode": "finance_personal_brand",
            "disclaimer": disclaimer,
            "forbidden": [
                "outcome_promises",
                "individual_financial_advice",
                "direct_buy_pressure",
                "invented_client_results",
            ],
        },
        "finance_video_series": series_plan,
        "finance_scene_concept": approved_scene_concept,
        "avatar_direction": {
            "avatar_name": avatar.get("name", "Creator"),
            "testimonial_mode": False,
            "personal_use_claims_allowed": False,
            "instruction": "Creator speaks as an educator/personal brand, not as a client promising outcomes. The creator naturally interacts with infographic cards through eye-line, pointing, small air taps, and paced gestures.",
        },
    }


def generate_video_only_ad_set(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    avatar: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    series_plan = ugc_strategy.get("finance_video_series") or {}
    video_count = int(series_plan.get("video_count") or 1)
    creative_plan = [
        {
            "set_id": f"C{index + 1}",
            "creative_type": (
                "Personal brand finance video"
                if video_count == 1
                else f"Personal brand finance video {index + 1}/{video_count}"
            ),
            "angle": "EDUCATION",
            "aspect_ratio": "9:16",
            "funnel_stage": "Meta Ads + Instagram",
            "budget_share_percent": round(100 / max(1, video_count)),
            "generation_target": "Seedance video",
            "notes": "Video-only finance personal brand ad with strict Czech voiceover, modern podcast-studio look, and interactive premium infographic overlays.",
        }
        for index in range(video_count)
    ]
    return {
        "agent": "Finance Personal Brand Creative Set Agent",
        "creative_set_type": "finance_personal_brand_video_only",
        "language": "cs",
        "platform": settings.get("platform") or "meta",
        "market": settings.get("market") or "CZ",
        "creative_plan": creative_plan,
        "ugc_video_ad": {
            "set_id": "C1",
            "creative_id": "C1_finance_personal_brand_video",
            "type": "video",
            "angle": "EDUCATION",
            "seedance_prompt": content_prompt_package.get("seedance_video_prompt"),
            "structured_scene_prompt": content_prompt_package.get("structured_scene_prompt"),
            "why_this_creative_exists": [
                "Buduje důvěru přes osobní brand",
                "Vysvětluje finanční téma česky a srozumitelně",
                "Avatar fyzicky reaguje na infografiku pohledem, gestem a jemným ukázáním",
            ],
        },
        "static_image_ads": [],
        "carousel_ad": {"cards": [], "card_count": 0},
        "meme_style_creatives": [],
        "primary_text_variants": [],
        "google_ads_assets": {},
        "static_prompt_generation": {
            "status": "skipped",
            "reason": "Finance personal brand mode generates video only.",
        },
        "finance_video_series": series_plan,
        "copy_validation": {
            "status": "pass",
            "checks": [],
        },
    }


def build_scene_concept(
    *,
    topic: str,
    script_plan: dict[str, Any],
    avatar: dict[str, Any],
    platform: str,
) -> dict[str, Any]:
    episodes = script_plan.get("episodes") or []
    first_episode = episodes[0] if episodes else {}
    voiceover = _enforce_czech_language(
        first_episode.get("voiceover")
        or first_episode.get("script")
        or script_plan.get("canonical_script")
        or topic
    )
    hook = _enforce_czech_language(first_episode.get("hook") or _clip_words(voiceover, 10))
    scene_beats = [
        _normalize_scene_beat(item)
        for item in (
            first_episode.get("scenes")
            or _default_episode_scenes(
                _clip_words(voiceover, WORDS_PER_15S_VIDEO),
                DEFAULT_FINANCE_DISCLAIMER,
            )
        )
        if isinstance(item, dict)
    ]
    if not scene_beats:
        scene_beats = _default_episode_scenes(
            _clip_words(voiceover, WORDS_PER_15S_VIDEO),
            DEFAULT_FINANCE_DISCLAIMER,
        )
    avatar_label = avatar.get("name") or avatar.get("id") or "aktivní avatar"
    infographic_elements = _infographic_elements(topic=topic, hook=hook, scene_beats=scene_beats)
    visual_brief = (
        "Moderní podcastové studio pro český finanční osobní brand: vertikální 9:16, "
        "důvěryhodný expert u podcastového stolu, viditelný stolní mikrofon nebo boom arm, "
        "akustické panely, teplé klíčové světlo, decentní LED akcent, prémiová ale realistická atmosféra. "
        "Scéna musí mít prostor vedle avatara pro interaktivní infografiku, karty a timeline."
    )
    interaction_plan = [
        "0-3s: avatar se podívá do kamery, potom krátce na headline kartu a ukáže na první klíčové slovo; headline karta se jemně rozsvítí",
        "3-10s: avatar vysvětluje hlavní myšlenku, drobný air-tap postupně zvýrazní dvě až tři informační karty",
        "10-15s: avatar malým gestem spustí spodní disclaimer lištu, grafika zůstává pod úrovní obličeje",
    ]
    infographic_system = {
        "style": "moderní motion design, čistý glassmorphism, jemné linkové ikony, decentní datové tvary bez falešných čísel",
        "layout": "avatar vlevo nebo uprostřed, infographic cluster vpravo od těla, spodní lišta pro disclaimer, vše v centrální safe area",
        "language_lock": "všechny viditelné texty pouze česky s diakritikou; pokud model neumí přesný text, má použít abstraktní UI tvary bez čitelného cizího textu",
        "do_not_use": "žádná polština, slovenština, angličtina, falešné bankovní logo, výnosová čísla, graf s garantovaným růstem, CTA tlačítko",
    }
    image_prompt = (
        "Create one photorealistic vertical 9:16 scene concept image for a Czech finance personal-brand Meta/Instagram video. "
        "This is a previsualization image, not the final ad frame. "
        f"Topic: {topic}. Hook: {hook}. Active avatar/creator label for context: {avatar_label}. "
        "Use the supplied avatar reference image as the identity source for the person in the scene concept. Preserve the same face, identity, and recognizable creator look from the reference image; do not invent a different presenter. "
        f"{visual_brief} "
        "Show the creator framed medium close-up at a podcast desk with hands visible and enough negative space beside the body for gesture-synced infographics. "
        "Include a clearly designed modern infographic system: one headline card, two small glassmorphism explanation cards, one simple timeline/checklist strip, and one lower-third disclaimer zone. "
        f"Use only these exact Czech labels where text is visible: {', '.join(item['label'] for item in infographic_elements[:5])}. "
        "Infographics should look interactive and anchored to the creator's gestures: one card subtly highlighted near the pointing hand, one timeline marker ready to move, one lower third area reserved. "
        "No fake bank branding, no logos, no numbers implying returns, no investment promises, no platform UI, no CTA button, no Polish or Slovak text. "
        "If readable typography is uncertain, prefer clean abstract card shapes and icons over wrong-language text. "
        "Real camera look, realistic skin, natural shadows, premium podcast studio lighting, not sci-fi hologram, not corporate stock photo, not a cluttered dashboard."
    )
    return {
        "status": "ready_for_scene_image",
        "agent": "Finance Scene Concept Agent",
        "topic": _clean_text(topic),
        "hook": hook,
        "voiceover_preview": _clip_words(voiceover, WORDS_PER_15S_VIDEO),
        "visual_brief": visual_brief,
        "infographic_system": infographic_system,
        "infographic_elements": infographic_elements,
        "interaction_plan": interaction_plan,
        "scene_beats": scene_beats,
        "image_prompt": image_prompt,
        "video_prompt_addendum_compiled": _compile_scene_concept_for_video(
            visual_brief=visual_brief,
            infographic_system=infographic_system,
            infographic_elements=infographic_elements,
            interaction_plan=interaction_plan,
            scene_beats=scene_beats,
        ),
        "video_prompt_addendum": (
            "Use the approved scene concept as visual grounding for the podcast studio layout, lighting, "
            "interactive infographic placement, and gesture timing. Preserve avatar identity from the avatar reference, "
            "keep Czech captions readable, and do not introduce fake financial claims."
        ),
        "approval_required": True,
        "platform": platform if platform in {"meta", "instagram"} else "meta",
    }


def approved_scene_concept_from_settings(
    *,
    topic: str,
    script_plan: dict[str, Any],
    avatar: dict[str, Any],
    platform: str,
    approved_image_prompt: str = "",
) -> dict[str, Any]:
    concept = build_scene_concept(
        topic=topic,
        script_plan=script_plan,
        avatar=avatar,
        platform=platform,
    )
    prompt = _clean_text(approved_image_prompt)
    if prompt:
        concept["approved_image_prompt"] = prompt
        concept["image_prompt"] = prompt
        concept["video_prompt_addendum_compiled"] = (
            concept.get("video_prompt_addendum_compiled", "")
            + " Approved visual previsualization prompt to preserve: "
            + prompt[:1400]
        )
    concept["status"] = "approved_for_video"
    return concept


def _normalize_scene_beat(item: dict[str, Any]) -> dict[str, str]:
    return {
        "time": _clean_text(item.get("time")) or "0-5s",
        "visual": _enforce_czech_language(item.get("visual")) or "avatar vysvětluje v moderním podcastovém studiu",
        "on_screen_text": _clip_words(_enforce_czech_language(item.get("on_screen_text")), 6),
        "infographic": _enforce_czech_language(item.get("infographic"))
        or "moderní česká informační karta se zvýrazní podle gesta",
    }


def _finance_scene_infographic_for_index(
    *,
    index: int,
    concept_beat: dict[str, Any],
    concept_elements: list[dict[str, Any]],
) -> str:
    if concept_beat.get("infographic"):
        base = _enforce_czech_language(concept_beat.get("infographic"))
    else:
        defaults = [
            "schválená headline karta se zvýrazní podle pohledu a ukázání rukou",
            "schválené glassmorphism karty se rozsvěcí v pořadí podle řeči",
            "schválená timeline nebo checklist reaguje na malé air-tap gesto",
            "schválená spodní disclaimer lišta se zobrazí po závěrečném gestu",
        ]
        base = defaults[min(index, len(defaults) - 1)]
    labels = [
        str(item.get("label"))
        for item in concept_elements
        if isinstance(item, dict) and item.get("label")
    ]
    if labels:
        return _clean_text(f"{base}; používej přesné české labely: {', '.join(labels[:5])}")
    return base


def _infographic_elements(
    *,
    topic: str,
    hook: str,
    scene_beats: list[dict[str, str]],
) -> list[dict[str, str]]:
    labels = [
        _clip_words(hook or topic, 4),
        *_topic_infographic_labels(topic),
        "Klíčová myšlenka",
        "Plán",
        "Riziko",
        "Vzdělávací obsah",
    ]
    for beat in scene_beats:
        text = _clip_words(_enforce_czech_language(beat.get("on_screen_text")), 4)
        if text and text not in labels:
            labels.insert(max(1, len(labels) - 1), text)
    labels = _dedupe_keep_order([_safe_czech_label(label) for label in labels if label])[:6]
    roles = ["headline_card", "explanation_card", "timeline_card", "risk_note", "disclaimer_lower_third", "supporting_icon"]
    motion = [
        "rozsvítí se po krátkém pohledu avatara",
        "vysune se po ukázání rukou",
        "marker se posune po jemném air-tap gestu",
        "zvýrazní se jen decentně, bez strašení",
        "objeví se dole po závěrečném gestu",
        "zůstane dekorativní a bez čísel",
    ]
    return [
        {
            "role": roles[index],
            "label": label,
            "motion": motion[index],
            "safe_area": "mimo obličej, ruce a titulky",
        }
        for index, label in enumerate(labels)
    ]


def _topic_infographic_labels(topic: str) -> list[str]:
    lower = _clean_text(topic).lower()
    labels = []
    if "rezerv" in lower:
        labels.append("Rezerva")
    if "invest" in lower:
        labels.append("Investice")
    if "dluh" in lower or "úvěr" in lower or "uver" in lower:
        labels.append("Dluhy")
    if "rizik" in lower:
        labels.append("Riziko")
    return labels


def _compile_scene_concept_for_video(
    *,
    visual_brief: str,
    infographic_system: dict[str, str],
    infographic_elements: list[dict[str, str]],
    interaction_plan: list[str],
    scene_beats: list[dict[str, str]],
) -> str:
    labels = "; ".join(
        f"{item['role']} label='{item['label']}' motion='{item['motion']}'"
        for item in infographic_elements
    )
    beats = "; ".join(
        f"{beat.get('time')}: visual={beat.get('visual')}; infographic={beat.get('infographic')}; text={beat.get('on_screen_text')}"
        for beat in scene_beats[:4]
    )
    return _clean_text(
        "APPROVED FINANCE SCENE BLUEPRINT. "
        f"Scene layout: {visual_brief} "
        f"Infographic style: {infographic_system.get('style')}. "
        f"Infographic layout: {infographic_system.get('layout')}. "
        f"Language lock: {infographic_system.get('language_lock')}. "
        f"Forbidden infographic output: {infographic_system.get('do_not_use')}. "
        f"Approved infographic elements: {labels}. "
        f"Gesture sync plan: {'; '.join(interaction_plan)}. "
        f"Scene beats: {beats}. "
        "The final video must reuse this approved infographic system and not replace it with a generic dashboard."
    )


def _safe_czech_label(value: str) -> str:
    text = _clip_words(_enforce_czech_language(value), 5).strip(" .,:;")
    replacements = {
        "": "Vzdělávací obsah",
        "finance": "Finance jednoduše",
        "financial": "Finance jednoduše",
        "investment": "Investice",
        "risk": "Riziko",
        "plan": "Plán",
    }
    return replacements.get(text.lower(), text)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _word_count(value: str) -> int:
    return len(_clean_text(value).split())


def _deterministic_script_plan(
    *,
    topic: str,
    user_script: str,
    disclaimer: str,
    platform: str,
) -> dict[str, Any]:
    safe_script = _sanitize_finance_script(user_script) or (
        "Vysvětli jednoduchým jazykem jednu finanční myšlenku bez tlaku a bez slibů."
    )
    words_per_video = WORDS_PER_15S_VIDEO
    word_count = _word_count(safe_script)
    video_count = max(1, math.ceil(word_count / words_per_video))
    episodes = _series_episodes(
        topic=_clean_text(topic) or "Finanční osobní brand video",
        script=safe_script,
        video_count=video_count,
        words_per_video=words_per_video,
        target_seconds=DEFAULT_SERIES_SECONDS,
    )
    if not episodes:
        episodes = [
            {
                "episode_id": "finance_video_1",
                "title": _clean_text(topic) or "Finanční osobní brand video",
                "hook": _clip_words(safe_script, 8),
                "voiceover": _clip_words(safe_script, words_per_video),
                "script": _clip_words(safe_script, words_per_video),
                "duration_seconds": DEFAULT_SERIES_SECONDS,
                "position": 1,
                "total": 1,
                "scenes": _default_episode_scenes(_clip_words(safe_script, words_per_video), disclaimer),
                "why_this_episode_exists": "Rychle otevře téma, vysvětlí jednu praktickou myšlenku a uzavře compliance-safe kontextem.",
            }
        ]
    return _normalize_script_plan(
        {
            "recommended_video_count": len(episodes),
            "canonical_script": " ".join((episode.get("voiceover") or episode.get("script") or "") for episode in episodes),
            "episodes": episodes,
            "safety_notes": [
                "Bez slibů výnosů, bez individuálního doporučení, bez tlaku na okamžitý nákup.",
                "Používat pouze kvalitní češtinu, žádnou polštinu, slovenštinu ani smíšený jazyk.",
                "Výchozí vizuální styl je moderní podcastové studio s čitelnou finanční infografikou.",
                "Avatar má s infografikou interagovat pohledem, gestem, ukázáním a jemným air-tap pohybem.",
            ],
            "platform": platform if platform in {"meta", "instagram"} else "meta",
        },
        fallback=None,
    )


def _normalize_script_plan(value: dict[str, Any], fallback: dict[str, Any] | None) -> dict[str, Any]:
    episodes = []
    raw_episodes = value.get("episodes") if isinstance(value, dict) else None
    for index, episode in enumerate(raw_episodes or [], start=1):
        if not isinstance(episode, dict):
            continue
        voiceover = _clip_words(_sanitize_finance_script(episode.get("voiceover") or episode.get("script") or ""), WORDS_PER_15S_VIDEO)
        if not voiceover:
            continue
        scenes = episode.get("scenes") if isinstance(episode.get("scenes"), list) else []
        episodes.append(
            {
                "episode_id": str(episode.get("episode_id") or f"finance_video_{index}"),
                "title": _clean_text(episode.get("title")) or f"Finance video {index}",
                "hook": _clip_words(_enforce_czech_language(episode.get("hook") or voiceover), 10),
                "voiceover": voiceover,
                "script": voiceover,
                "duration_seconds": DEFAULT_SERIES_SECONDS,
                "position": _safe_int(episode.get("position"), index),
                "total": _safe_int(episode.get("total"), len(raw_episodes or []) or 1),
                "scenes": scenes[:4] or _default_episode_scenes(voiceover, DEFAULT_FINANCE_DISCLAIMER),
                "why_this_episode_exists": _enforce_czech_language(
                    _clean_text(episode.get("why_this_episode_exists"))
                    or "Vysvětluje jednu část tématu v krátkém personal-brand formátu."
                ),
            }
        )
    if not episodes and fallback:
        return fallback
    total = len(episodes) or 1
    for index, episode in enumerate(episodes, start=1):
        episode["position"] = index
        episode["total"] = total
        episode["episode_id"] = f"finance_video_{index}"
    canonical = _enforce_czech_language(_clean_text(value.get("canonical_script"))) if isinstance(value, dict) else ""
    if not canonical:
        canonical = " ".join(episode["voiceover"] for episode in episodes)
    return {
        "agent": "Finance Script Agent",
        "recommended_video_count": total,
        "canonical_script": canonical,
        "episodes": episodes,
        "safety_notes": value.get("safety_notes") if isinstance(value.get("safety_notes"), list) else [],
    }


def _prepared_series_episodes(items: list[dict[str, Any]], target_seconds: int) -> list[dict[str, Any]]:
    episodes = []
    for index, episode in enumerate(items, start=1):
        voiceover = _enforce_czech_language(episode.get("voiceover") or episode.get("script"))
        if not voiceover:
            continue
        episodes.append(
            {
                "episode_id": f"finance_video_{index}",
                "title": _clean_text(episode.get("title")) or f"Finance video {index}/{len(items)}",
                "script": voiceover,
                "voiceover": voiceover,
                "duration_seconds": target_seconds,
                "position": index,
                "total": len(items),
                "scenes": episode.get("scenes") or [],
                "why_this_episode_exists": episode.get("why_this_episode_exists"),
            }
        )
    return episodes


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _series_episodes(
    *,
    topic: str,
    script: str,
    video_count: int,
    words_per_video: int,
    target_seconds: int,
) -> list[dict[str, Any]]:
    if video_count <= 1:
        return []
    words = _clean_text(script).split()
    episodes = []
    for index in range(video_count):
        chunk = _enforce_czech_language(" ".join(words[index * words_per_video : (index + 1) * words_per_video]).strip())
        if not chunk:
            continue
        episodes.append(
            {
                "episode_id": f"finance_video_{index + 1}",
                "title": f"{topic} {index + 1}/{video_count}",
                "script": chunk,
                "voiceover": chunk,
                "duration_seconds": target_seconds,
                "position": index + 1,
                "total": video_count,
                "scenes": _default_episode_scenes(chunk, DEFAULT_FINANCE_DISCLAIMER),
                "why_this_episode_exists": "Udrží jednu krátkou finanční myšlenku v délce vhodné pro 15s Meta/Instagram video.",
            }
        )
    return episodes


def _default_episode_scenes(voiceover: str, disclaimer: str) -> list[dict[str, str]]:
    return [
        {
            "time": "0-5s",
            "visual": "creator opens directly to camera in a modern podcast studio, desk microphone visible, warm key light and acoustic panels, then points toward a headline card",
            "on_screen_text": _clip_words(voiceover, 5),
            "infographic": "animated Czech headline lower third reacts to the pointing gesture",
        },
        {
            "time": "5-10s",
            "visual": "creator explains one point from the podcast desk while clean cards build beside the face and the creator taps the air toward each card",
            "on_screen_text": "Jednoduše a přehledně",
            "infographic": "glassmorphism checklist cards or simple timeline with Czech labels highlight in sync with hand gestures",
        },
        {
            "time": "10-15s",
            "visual": "creator closes calmly in the same podcast studio and gives a small hand cue before the disclaimer appears",
            "on_screen_text": _clip_words(disclaimer, 6),
            "infographic": "small Czech disclaimer bar and subtle chart icon animate in after the hand cue",
        },
    ]


def _parse_json_object(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Prompt model did not return a JSON object.")
    return parsed


def _format_prompt_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        body = ""
        try:
            body = response.text[:600]
        except Exception:
            body = ""
        return f"{type(exc).__name__}: HTTP {response.status_code}. {body}".strip()
    return f"{type(exc).__name__}: {exc}"


def _sanitize_finance_script(value: str) -> str:
    text = _enforce_czech_language(_clean_text(value))
    replacements = [
        (r"\bgarantovan(ý|é|a|ou)?\s+výnos(y|ů)?\b", "možný scénář"),
        (r"\bjist(ý|á|é)?\s+zisk\b", "potenciální výsledek"),
        (r"\bbez rizika\b", "s jasným vysvětlením rizik"),
        (r"\bzbohatne(š|te)\b", "můžeš lépe plánovat"),
        (r"\bprofit guaranteed\b", "educational context"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return _enforce_czech_language(text)


def _enforce_czech_language(value: Any) -> str:
    text = _clean_text(value)
    replacements = [
        (r"\bpieniądze\b", "peníze"),
        (r"\bpieniadze\b", "peníze"),
        (r"\bpeniaze\b", "peníze"),
        (r"\bfinansow[a-ząćęłńóśźż]*\b", "finanční"),
        (r"\bfinansov[a-záäčďéíĺľňóôŕšťúýž]*\b", "finanční"),
        (r"\binwestycj[a-ząćęłńóśźż]*\b", "investice"),
        (r"\binvestíci[a-záäčďéíĺľňóôŕšťúýž]*\b", "investice"),
        (r"\boszczędno[a-ząćęłńóśźż]*\b", "spoření"),
        (r"\boszczedno[a-ząćęłńóśźż]*\b", "spoření"),
        (r"\bjeśli\b", "když"),
        (r"\bjesli\b", "když"),
        (r"\bprečo\b", "proč"),
        (r"\bdlaczego\b", "proč"),
        (r"\bzobacz\b", "podívej se"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _script_chunks(script: str, count: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", script)
    sentences = [item.strip(" .") for item in sentences if item.strip(" .")]
    if not sentences:
        sentences = [script]
    chunks = ["" for _ in range(count)]
    for index, sentence in enumerate(sentences):
        target = min(count - 1, index * count // max(1, len(sentences)))
        chunks[target] = (chunks[target] + " " + sentence).strip()
    for index in range(count):
        if not chunks[index]:
            chunks[index] = chunks[index - 1] if index else script
        chunks[index] = _clip_words(chunks[index], 34 if count >= 4 else 42)
    return chunks


def _overlay_texts(topic: str, chunks: list[str], disclaimer: str) -> list[str]:
    base = [
        _clip_words(topic, 5),
        "Jednoduše a bez slibů",
        "Riziko a plán",
        "Vzdělávací obsah",
    ]
    if chunks:
        base[0] = _clip_words(chunks[0], 5)
    base[-1] = _clip_words(disclaimer, 6)
    return base[: len(chunks)]


def _scene_durations(duration: int, count: int) -> list[int]:
    if count == 4:
        if duration >= 30:
            return [8, 8, 7, duration - 23]
        return [5, 5, 5, max(5, duration - 15)]
    if count == 3:
        return [5, 5, max(5, duration - 10)]
    return [duration]


def _scene_times(durations: list[int]) -> list[str]:
    result = []
    start = 0
    for duration in durations:
        end = start + duration
        result.append(f"{start}-{end}s")
        start = end
    return result


def _clip_words(value: str, max_words: int) -> str:
    words = _clean_text(value).split()
    return " ".join(words[:max_words])
