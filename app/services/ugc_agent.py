from __future__ import annotations

import re
from typing import Any

from app.services.localization_utils import (
    is_czech as _is_czech_language,
    is_german,
    language_copy_policy,
    language_safe_voice_descriptor,
    localize_category,
    localize_phrase,
    target_language_name,
)
from app.services import arcads_ugc_guidance, scenario_contract
from app.services.text_utils import sanitize_avatar_descriptor


PLATFORM_DEFAULTS = {
    "tiktok": {"aspect_ratio": "9:16", "style": "fast creator edit", "safe_area": "keep creator face, product, and hands away from top and bottom UI zones; captions are post-production only"},
    "instagram": {"aspect_ratio": "9:16", "style": "polished Reels edit", "safe_area": "keep creator face, product, and hands inside central frame; captions are post-production only"},
    "youtube": {"aspect_ratio": "16:9", "style": "clear YouTube Shorts or in-stream pacing", "safe_area": "keep creator face, product, and hands away from edges; captions are post-production only"},
    "meta": {"aspect_ratio": "9:16", "style": "direct paid social creative", "safe_area": "leave margin for ad UI; keep creator face, product, and hands central; captions are post-production only"},
    "google_ads": {"aspect_ratio": "16:9", "style": "Google Ads video asset with product-led clarity", "safe_area": "keep creator, product, and hands inside central safe area for YouTube and Display placements; captions are post-production only"},
}

MIRROR_SELFIE_LOCK_RULES = [
    "camera source is only the creator's iPhone mirror-selfie recording for the entire duration",
    "the avatar is always seen through the mirror reflection while holding the iPhone visibly in one hand",
    "never switch to third-person camera, external camera angle, side filming, over-the-shoulder shot, back-view tracking, room camera, observer perspective, tripod perspective, cinematic b-roll, cutaway, product-only insert, or fashion-commercial shot",
    "no scene changes, no perspective changes, no alternate camera angles, and no cinematic transitions",
    "the avatar must not walk away from the mirror or turn fully back to the camera; any rotation is only a partial side-turn while still facing the mirror",
    "opening anti-freeze rule: the first frame starts already live with tiny phone sway, a blink, visible mouth/jaw beginning the spoken hook, or a small free-hand movement; no still poster frame, no frozen face, and no static hold at the start",
    "natural mirror-selfie behaviour: relaxed posture, slight handheld shake, casual body language, free hand naturally adjusts the garment or points to waist, neckline, cut, drape, or silhouette, then a soft natural smile at the end",
    "visual style stays raw and believable: simple bedroom or apartment, natural daylight or soft room light, slight autofocus breathing allowed, no beauty-commercial look",
]

MIRROR_SELFIE_FORBIDDEN = [
    "no third-person camera, external camera, side camera, over-the-shoulder shot, room camera, observer camera, tripod shot, cinematic cutaway, cinematic b-roll, or perspective switch",
    "no back shot, no avatar walking away from the mirror, no full back turn, no missing phone, no cropped phone, no cropped head, no cropped outfit, no cropped legs or feet",
    "no frozen face, closed-mouth speech, broken lip-sync, distorted mouth, identity morphing, AI skin texture, unrealistic body proportions, extra fingers, or deformed hands",
    "no subtitles, overlay text, floating graphics, title cards, lower thirds, hook stickers, or generated CTA text inside the video",
]


def _is_czech(language: str) -> bool:
    return _is_czech_language(language)


def _is_german(language: str) -> bool:
    return is_german(language)


def _spoken_product_label(product_name: str, category: str, language: str) -> str:
    is_czech = _is_czech(language)
    is_de = _is_german(language)
    lower_name = product_name.lower()
    if category == "handbag":
        if is_de:
            return "diese Tasche"
        if "tote" in lower_name:
            return "tahle tote kabelka" if is_czech else "this tote"
        return "tahle kabelka" if is_czech else "this bag"
    if category == "shoes":
        if is_de:
            return "diese Schuhe"
        return "tyhle boty" if is_czech else "these shoes"
    if category == "apparel":
        if is_de:
            return "dieses Kleidungsstueck"
        return "tenhle kousek" if is_czech else "this piece"
    if category == "beauty":
        if is_de:
            return "diesem Produkt"
        return "tenhle produkt" if is_czech else "this product"
    if category == "home":
        if is_de:
            return "diesem Produkt"
        return "tenhle doplnek" if is_czech else "this home item"
    if category == "electronics":
        if is_de:
            return "diesem Produkt"
        return "tenhle produkt" if is_czech else "this product"
    cleaned_name = product_name.split("|", 1)[0].strip()
    return cleaned_name or ("tenhle produkt" if is_czech else "this product")


def _join_fact_phrases(facts: list[str], language: str = "en") -> str:
    trimmed = [fact for fact in facts if fact][:3]
    if not trimmed:
        return ""
    if len(trimmed) == 1:
        return trimmed[0]
    joiner = " und " if _is_german(language) else " a " if _is_czech(language) else " and "
    if len(trimmed) == 2:
        return f"{trimmed[0]}{joiner}{trimmed[1]}"
    serial_joiner = "und" if _is_german(language) else "a" if _is_czech(language) else "and"
    comma = "," if not _is_german(language) else ""
    return f"{trimmed[0]}, {trimmed[1]}{comma} {serial_joiner} {trimmed[2]}"


def _shorten_words(text: str, max_words: int) -> str:
    words = [word.strip(" ,.;:!?") for word in str(text or "").split() if word.strip(" ,.;:!?")]
    if not words:
        return ""
    shortened = " ".join(words[:max_words])
    return shortened.strip()


def _sentence_case(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _subtitle_line(voiceover: str, language: str | bool) -> str:
    text = str(voiceover or "").strip()
    if not text:
        return ""
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    lower = text.lower()
    replacements = {
        "before judging the style": "first",
        "calmly before deciding": "before deciding",
        "in a normal context": "in context",
    }
    for old, new in replacements.items():
        lower = lower.replace(old, new)
    if is_czech:
        text = (
            lower.replace("tady bych si zblizka zkontroloval hlavne", "zkontrolovat zblizka")
            .replace("tady bych si v klidu zkontroloval", "zkontrolovat v klidu")
            .replace("je dulezite videt", "videt")
        )
        return _sentence_case(_shorten_words(text, 8))
    if is_de:
        text = (
            lower.replace("hier wuerde ich vor allem", "")
            .replace("hier wuerde ich diese details aus der naehe pruefen:", "details nah pruefen")
            .replace("aus der naehe pruefen", "nah pruefen")
            .replace("wichtig ist,", "")
            .replace("in einem normalen kontext zu sehen", "im alltag sehen")
            .replace("dieses produktdetail wuerde ich", "produktdetail")
            .replace("vor der entscheidung in ruhe pruefen", "ruhig pruefen")
        )
        return _sentence_case(_shorten_words(text, 8))
    text = (
        lower.replace("with ", "")
        .replace("here, i'd check ", "check ")
        .replace("i'd show ", "show ")
        .replace("i'd check ", "check ")
        .replace("this is the kind of ", "")
    )
    text = (
        text.replace("this piece, the cut matters most when you see it worn", "see the cut worn")
        .replace("this piece the cut matters most when you see it worn", "see the cut worn")
        .replace("the cut matters most when you see it worn", "see the cut worn")
    )
    return _sentence_case(_shorten_words(text, 8))


def _detail_focus(category: str, language: str, user_facts: list[str] | None = None) -> str:
    is_czech = _is_czech(language)
    is_de = _is_german(language)
    if user_facts:
        joined = _join_fact_phrases(user_facts, language)
        if joined:
            return joined
    if is_de:
        by_category = {
            "handbag": "Form, Griffe und Verarbeitung",
            "shoes": "Form, Sohlenkante und sichtbare Verarbeitung",
            "apparel": "Schnitt, Materialoptik und Verarbeitung",
            "beauty": "Verpackung, Textur und sichtbare Details",
            "home": "Groesse, Platzierung und sichtbare Verarbeitung",
            "electronics": "Bedienelemente, Anschluesse und sichtbare Details",
        }
        return by_category.get(category, "Form, Groesse und sichtbare Details")
    if is_czech:
        by_category = {
            "handbag": "tvar, drzadla a celkove provedeni",
            "shoes": "tvar, podrazku a viditelne provedeni",
            "apparel": "strih, materialovy vzhled a celkove provedeni",
            "beauty": "obal, texturu a viditelne detaily",
            "home": "velikost, umisteni a viditelne provedeni",
            "electronics": "ovladaci prvky, porty a viditelne detaily",
        }
        return by_category.get(category, "tvar, meritko a viditelne detaily")
    by_category = {
        "handbag": "the shape, handle details, and overall finish",
        "shoes": "the shape, sole details, and visible construction",
        "apparel": "the cut, drape, and visible finish",
        "beauty": "the packaging, texture, and visible details",
        "home": "the size, placement, and visible finish",
        "electronics": "the controls, ports, and visible details",
    }
    return by_category.get(category, "the shape, scale, and visible details")


def _context_line(category: str, language: str | bool) -> str:
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    if is_czech:
        if category == "handbag":
            return "Na rameni je hned videt meritko a jak sedi k outfitu."
        if category == "shoes":
            return "Na noze a s normalnim outfitem dava tvar mnohem vetsi smysl."
        if category == "apparel":
            return "V zrcadle je dobre videt strih i to, jak se hybe."
        return "V beznem kontextu je hned jasne meritko."
    if is_de:
        if category == "handbag":
            return "Auf der Schulter sieht man sofort Groesse und Styling."
        if category == "shoes":
            return "Am Fuss mit einem normalen Outfit wirkt die Form viel klarer."
        if category == "apparel":
            return "Im Spiegel sieht man Schnitt und Bewegung viel besser."
        return "Im normalen Kontext wird die Groesse sofort klar."
    if category == "handbag":
        return "On the shoulder, the scale and styling are clear straight away."
    if category == "shoes":
        return "On foot with a normal outfit, the shape makes much more sense."
    if category == "apparel":
        return "In a mirror shot, the cut and movement are much easier to see."
    return "In a normal setting, the scale is clear straight away."


def _product_display_name(product_name: str, fallback: str) -> str:
    label = str(product_name or "").split("|", 1)[0].strip()
    return label or fallback


def _handbag_capacity_supported(product_analysis: dict[str, Any]) -> bool:
    text = " ".join(
        str(item)
        for item in [
            product_analysis.get("internal_brief_notes"),
            *(product_analysis.get("user_provided_facts") or []),
            *(product_analysis.get("safe_benefits") or []),
            *((product_analysis.get("known_product_facts") or {}).values()),
        ]
        if item
    ).lower()
    return any(
        phrase in text
        for phrase in [
            "spacious",
            "roomy",
            "capacity",
            "interior",
            "waterproof interior",
            "tablet",
            "laptop",
            "daily essentials",
            "work errands and travel",
        ]
    )


def _handbag_material_focus(product_analysis: dict[str, Any]) -> str:
    text = " ".join(
        str(item)
        for item in [
            *((product_analysis.get("known_product_facts") or {}).values()),
            *(product_analysis.get("user_provided_facts") or []),
            *(product_analysis.get("ad_safe_detail_phrases") or []),
            product_analysis.get("internal_brief_notes"),
        ]
        if item
    ).lower()
    if "vegan leather" in text:
        return "vegan leather finish"
    if "leather" in text:
        return "leather texture"
    return "material texture"


def _hook_line(
    product_label: str,
    category: str,
    language: str | bool,
    *,
    capacity_supported: bool = False,
) -> str:
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    if is_czech:
        if category == "handbag":
            if capacity_supported:
                return f"Konecne {product_label}, ktera vypada elegantne a pritom pobere denni veci."
            return f"Konecne {product_label}, ktera vypada elegantne a dava smysl na kazdy den."
        if category == "shoes":
            return f"U {product_label} je nejdulezitejsi profil primo na noze."
        if category == "apparel":
            return f"U {product_label} je nejdulezitejsi strih primo na postave."
        return f"U {product_label} rozhoduje detail, ne jen hezka fotka."
    if is_de:
        if category == "handbag":
            if capacity_supported:
                return f"Endlich {product_label}, die elegant aussieht und trotzdem die Alltagsdinge aufnimmt."
            return f"Endlich {product_label}, die elegant aussieht und im Alltag Sinn ergibt."
        if category == "shoes":
            return "Bei diesen Schuhen zaehlt zuerst das Profil am Fuss, nicht ein Tischfoto."
        if category == "apparel":
            return "Bei diesem Kleidungsstueck zaehlt zuerst, wie der Schnitt getragen aussieht."
        return "Bei diesem Produkt zaehlt zuerst der Detailblick, nicht nur das schoene Foto."
    if category == "handbag":
        if capacity_supported:
            return "Finally, a tote that looks elegant and still fits the daily essentials."
        return "Finally, a tote that looks elegant without feeling too dressed-up for every day."
    if category == "shoes":
        return f"With {product_label}, the side profile on foot matters more than a table shot."
    if category == "apparel":
        return f"With {product_label}, the cut matters most when you see it worn."
    return f"With {product_label}, the shape matters more than a polished product photo."


def _closing_line(category: str, language: str | bool) -> str:
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    if is_czech:
        by_category = {
            "handbag": "Tady je tvar, drzadla a meritko pekne pohromade.",
            "shoes": "Tady je profil, podrazka a styling na noze pekne pohromade.",
            "apparel": "Tady je strih, viditelne provedeni a pohyb pekne pohromade.",
        }
        return by_category.get(
            category, "Tady je detail produktu pekne pohromade."
        )
    if is_de:
        by_category = {
            "handbag": "Hier sieht man Form, Griffe und Groesse auf einen Blick.",
            "shoes": "Hier sieht man Profil, Sohle und Styling am Fuss auf einen Blick.",
            "apparel": "Hier sieht man Schnitt, sichtbare Verarbeitung und Bewegung auf einen Blick.",
        }
        return by_category.get(category, "Hier sieht man das Produktdetail auf einen Blick.")
    by_category = {
        "handbag": "Here is the shape, scale, and bag detail in one clear look.",
        "shoes": "Here is the profile, sole, and worn styling in one clear look.",
        "apparel": "Here is the cut, drape, and visible finish in one clear look.",
    }
    return by_category.get(
        category, "Here is the product detail in one clear look."
    )


def _customer_hook_from_strategy(
    hook_strategy: dict[str, Any],
    fallback_hook: str,
    language: str,
) -> str:
    selected = str(hook_strategy.get("selected_hook") or "").strip()
    if not selected:
        return fallback_hook
    if _looks_like_internal_direction(selected):
        return fallback_hook
    if not _matches_selected_language(selected, language):
        return fallback_hook
    return selected


def _looks_like_internal_direction(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    markers = [
        "angle:",
        "hook intent",
        "visual direction",
        "creative test",
        "scene summary",
        "voiceover=",
        "on_screen_text",
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


def _looks_english_customer_copy(value: str) -> bool:
    lowered = f" {str(value or '').lower()} "
    english_markers = [
        " with ",
        " i'd ",
        " i would ",
        " i ",
        " this ",
        " that ",
        " product ",
        " detail ",
        " polished ",
        " first ",
        " the ",
        " and ",
        " not ",
        " didn't ",
        " expect ",
        " fit ",
        " well ",
    ]
    return any(marker in lowered for marker in english_markers)


def _looks_czech_customer_copy(value: str) -> bool:
    lowered = f" {str(value or '').lower()} "
    czech_markers = [
        " konecne ",
        " u ",
        " tahle ",
        " tenhle ",
        " tyhle ",
        " strih ",
        " postave ",
        " zrcadle ",
        " detail ",
        " videt ",
        " realu ",
        " pohybu ",
        " zblizka ",
        " klidu ",
        " podrazka ",
        " rameni ",
        " denni ",
        " veci ",
        " meritko ",
        " kabelka ",
        " boty ",
    ]
    return any(marker in lowered for marker in czech_markers)


def _looks_german_customer_copy(value: str) -> bool:
    lowered = f" {str(value or '').lower()} "
    german_markers = [
        " endlich ",
        " bei ",
        " diese ",
        " diesen ",
        " diesem ",
        " schnitt ",
        " getragen ",
        " kleidungsstueck ",
        " fuss ",
        " groesse ",
        " naehte ",
        " alltag ",
        " detailcheck ",
        " outfit ",
        " ruhig ",
    ]
    return any(marker in lowered for marker in german_markers)


def _matches_selected_language(value: str, language: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if _is_czech(language):
        return not _looks_english_customer_copy(text) and not _looks_german_customer_copy(text)
    if _is_german(language):
        return not _looks_english_customer_copy(text) and not _looks_czech_customer_copy(text)
    return not _looks_czech_customer_copy(text) and not _looks_german_customer_copy(text)


def _language_safe_scene_texts(
    scene_texts: list[str],
    fallback_texts: list[str],
    language: str,
) -> list[str]:
    result = []
    for index in range(4):
        candidate = str(scene_texts[index] if index < len(scene_texts) else "").strip()
        fallback = str(fallback_texts[index] if index < len(fallback_texts) else "").strip()
        result.append(candidate if candidate and _matches_selected_language(candidate, language) else fallback)
    return result


def _handbag_capacity_voiceover(language: str | bool, capacity_supported: bool) -> str:
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    if is_czech:
        if capacity_supported:
            return "Tablet, lahev, penezenka, telefon, klice a kosmeticka tasticka jdou prehledne dovnitr."
        return "Otevreni a denni veci vedle kabelky dobre ukazou meritko bez slibu navic."
    if is_de:
        if capacity_supported:
            return "Tablet, Flasche, Portemonnaie, Handy, Schluessel und Make-up-Tasche passen sichtbar hinein."
        return "Die Oeffnung mit Alltagsdingen daneben zeigt die Groesse ohne extra Versprechen."
    if capacity_supported:
        return "A tablet, bottle, wallet, phone, keys, and makeup pouch go inside without changing the shape."
    return "The opening with daily items beside it makes the scale clear without guessing."


def _handbag_quality_voiceover(language: str | bool, material_focus: str) -> str:
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    if is_czech:
        if "leather" in material_focus:
            return "Zblizka je videt kuze, siti, drzadla a vnitrni podsivka."
        return "Zblizka je videt material, siti, drzadla a vnitrni podsivka."
    if is_de:
        material = "Lederstruktur" if "leather" in material_focus else "Materialstruktur"
        return f"Aus der Naehe sieht man {material}, Naehte, Griffe und Innenfutter."
    return f"Up close, you can see the {material_focus}, stitching, handles, and lining."


def _handbag_product_title(product_name: str, material_focus: str) -> str:
    display_name = _product_display_name(product_name, "BELLA")
    lower = display_name.lower()
    if "tote" in lower or "bag" in lower or "kabelka" in lower:
        return display_name
    if "leather" in material_focus:
        return f"{display_name} Leather Tote"
    return f"{display_name} Tote"


def _handbag_closing_line(
    product_name: str,
    language: str | bool,
    capacity_supported: bool,
    material_focus: str,
) -> str:
    product_title = _handbag_product_title(product_name, material_focus)
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    if is_czech:
        if capacity_supported:
            return f"{product_title}: elegantni, prostorna kabelka na kazdy den."
        return f"{product_title}: elegantni kabelka na kazdy den."
    if is_de:
        if capacity_supported:
            return f"{product_title}: elegant, geraeumig, jeden Tag."
        return f"{product_title}: elegant, praktisch, jeden Tag."
    if capacity_supported:
        return f"{product_title}: elegant, spacious, everyday."
    return f"{product_title}: elegant, practical, everyday."


def _scene_recipe(
    category: str,
    language: str | bool,
    capacity_supported: bool = False,
    material_focus: str = "material texture",
    product_name: str = "",
) -> dict[str, list[str]]:
    is_czech = bool(language) if isinstance(language, bool) else _is_czech(language)
    is_de = False if isinstance(language, bool) else _is_german(language)
    capacity_visual_cs = (
        "Capacity demonstration: tablet or slim notebook, water bottle, wallet, phone, keys, and makeup pouch going inside one by one, top opening and interior lining visible, adult hands only, same bag shape and size preserved, no overstuffed distortion."
        if capacity_supported
        else "Opening and scale demonstration: phone, keys, and wallet near the top opening or briefly placed inside as scale context, no unverified capacity claim, same bag shape and size preserved."
    )
    capacity_visual_en = capacity_visual_cs
    material_label_cs = "Detail kuze" if "leather" in material_focus else "Detail materialu"
    material_label_en = "Soft leather look" if "leather" in material_focus else "Material close-up"
    product_label = _product_display_name(product_name, "BELLA")
    closing_label_cs = f"{product_label} na kazdy den"
    closing_label_en = product_label if "tote" in product_label.lower() else f"{product_label} everyday tote"
    material_label_de = "Lederdetail" if "leather" in material_focus else "Materialdetail"
    closing_label_de = product_label if "tote" in product_label.lower() else f"{product_label} everyday tote"
    if is_czech:
        recipes = {
            "handbag": {
                "visuals": [
                    "Avatar speaks the main buyer hook in a category-selected commute, office doorway, cafe entrance, quiet street doorway, hallway, mirror, or leaving-home context, handbag on shoulder and then in hand against outfit, handles, silhouette, and same body-to-bag scale visible in the first two seconds, off-center smartphone composition, slight handheld sway, natural expression with a small pause, available natural light, no copied avatar-reference background, do not default to apartment interiors unless the product brief implies home use.",
                    f"{capacity_visual_cs} Use a simple surface such as office desk, cafe table, parked car seat, hallway console, or clean counter according to the chosen context, not a studio flat lay.",
                    f"Macro handheld detail sequence: {material_focus}, stitching, handles, opening, and interior lining when visible, then an outfit-scale shot in the chosen office, cafe, commute, street doorway, mirror, or hallway context, same bag size relative to torso and hands, UK/Scandinavian minimalist styling, warm neutral colours, no cluttered tabletop layout.",
                    "Avatar leaving home or doing a natural mirror outfit check with handbag on shoulder, then back on camera for a plain spoken product-name closing recap with no generated overlay, same wardrobe continuity, same bag size and carry position near torso, authentic relaxed face, no exaggerated smile, no fake button or URL.",
                ],
                "texts": ["Elegantni a prakticka", "Vejde se den", material_label_cs, closing_label_cs],
            },
            "shoes": {
                "visuals": [
                    "Avatar speaks directly to camera in a category-selected outdoor doorway, pavement edge, office lift lobby, cafe entrance, clean floor, or entryway context, shoes visible on feet in lower frame or held briefly at frame edge, off-center composition, slight handheld sway, available natural light, no copied avatar-reference background.",
                    "Low-angle worn close-ups of shoes on adult feet: side profile, toe shape, upper texture, sole edge, stitching or closure, no table, no flat lay, slight handheld sway, natural floor texture.",
                    "Worn outfit context shot in a category-selected outdoor doorway, cafe entrance, office lift lobby, quiet pavement edge, clean floor, or mirror setting, adult person wearing the shoes with everyday trousers or skirt hem visible, natural light, no tabletop styling, no copied avatar-reference background.",
                    "Avatar back on camera with shoes visible on feet in lower frame or held naturally, same wardrobe continuity, calm closing beat, no button or click instruction.",
                ],
                "texts": ["Profil na noze", "Podrazka zblizka", "Outfit v realu", "Detail v klidu"],
            },
            "apparel": {
                "visuals": [
                    "Avatar speaks directly to camera in a category-selected clean mirror, hallway, cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, or wardrobe-edge context, garment worn on body, full-body or near full-body head-to-toe silhouette visible from the first beat, off-center smartphone composition, slight handheld sway, available natural light, no copied avatar-reference background.",
                    "Mirror or handheld worn view of the whole garment first, then brief close details only if the full outfit remains understandable: cut, drape, sleeve, hem, seam, exact visible finish from reference, simple movement, no flat lay, soft natural light.",
                    "Everyday outfit context shot in a category-selected cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, mirror, hallway, or wardrobe-edge setting, garment worn by adult person, full body or near full body visible, natural movement and styling context, no copied avatar-reference background, no body outcome claims.",
                    "Avatar back on camera with garment worn, full outfit silhouette visible again, same wardrobe continuity when possible, calm closing beat, product detail visible, no button or click instruction.",
                ],
                "texts": ["Strih na postave", "Material zblizka", "Outfit v realu", "Detail v klidu"],
            },
        }
        return recipes.get(
            category,
            {
                "visuals": [
                    "Avatar speaks directly to camera in one category-selected minimal real-space context based on product type and use case, product held, worn, or used naturally at frame edge, off-center composition, slight handheld sway, available natural light, no copied avatar-reference background, avoid defaulting to home/apartment interiors unless the product is home-use.",
                    "Handheld close-ups from the product reference: visible shape, finish, controls, texture, construction or packaging if present, product held or used when plausible, soft directional light.",
                    "Everyday context shot adapted to the product category, product used or held by an adult person in a plausible minimal real space, no studio look, no copied avatar-reference background.",
                    "Avatar back on camera with product visible and handled naturally, same setting and wardrobe continuity, subtle smile, plain spoken closing recap with no generated overlay, button, or click instruction.",
                ],
                "texts": ["Zacni detailem", "Detail zblizka", "Meritko v realu", "Detail v klidu"],
            },
        )
    if is_de:
        recipes = {
            "handbag": {
                "visuals": [
                    "Avatar speaks the main buyer hook in a category-selected commute, office doorway, cafe entrance, quiet street doorway, hallway, mirror, or leaving-home context, handbag on shoulder and then in hand against outfit, handles, silhouette, and same body-to-bag scale visible in the first two seconds, off-center smartphone composition, slight handheld sway, natural expression with a small pause, available natural light, hands relaxed and anatomically correct, no copied avatar-reference background, do not default to apartment interiors unless the product brief implies home use.",
                    f"{capacity_visual_en} Use a simple surface such as office desk, cafe table, parked car seat, hallway console, or clean counter according to the chosen context, not a studio flat lay. Hands move slowly, only one object at a time, fingers natural and not covering the product label.",
                    f"Macro handheld detail sequence: {material_focus}, stitching, handles, opening, and interior lining when visible, then an outfit-scale shot in the chosen office, cafe, commute, street doorway, mirror, or hallway context, same bag size relative to torso and hands, UK/Scandinavian minimalist styling, warm neutral colours, no cluttered tabletop layout, stable hands and no finger distortion.",
                    "Avatar leaving home or doing a natural mirror outfit check with handbag on shoulder, then back on camera for a plain spoken product-name closing recap with no generated overlay, same wardrobe continuity, same bag size and carry position near torso, authentic relaxed face, no exaggerated smile, no fake button or URL.",
                ],
                "texts": ["Elegant und praktisch", "Passt in den Alltag", material_label_de, closing_label_de],
            },
            "shoes": {
                "visuals": [
                    "Avatar speaks directly to camera in a category-selected outdoor doorway, pavement edge, office lift lobby, cafe entrance, clean floor, or entryway context, shoes visible on feet in lower frame or held briefly at frame edge, off-center composition, slight handheld sway, available natural light, no copied avatar-reference background.",
                    "Low-angle worn close-ups of shoes on adult feet: side profile, toe shape, upper texture, sole edge, stitching or closure, no table, no flat lay, slight handheld sway, natural floor texture.",
                    "Worn outfit context shot in a category-selected outdoor doorway, cafe entrance, office lift lobby, quiet pavement edge, clean floor, or mirror setting, adult person wearing the shoes with everyday trousers or skirt hem visible, natural light, no tabletop styling, no copied avatar-reference background.",
                    "Avatar back on camera with shoes visible on feet in lower frame or held naturally, same wardrobe continuity, calm closing beat, no button or click instruction.",
                ],
                "texts": ["Profil am Fuss", "Sohlendetail", "Im Outfit", "Ruhiger Detailcheck"],
            },
            "apparel": {
                "visuals": [
                    "Avatar speaks directly to camera in a category-selected clean mirror, hallway, cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, or wardrobe-edge context, garment worn on body, full-body or near full-body head-to-toe silhouette visible from the first beat, off-center smartphone composition, slight handheld sway, available natural light, no copied avatar-reference background.",
                    "Mirror or handheld worn view of the whole garment first, then brief close details only if the full outfit remains understandable: cut, drape, sleeve, hem, seam, exact visible finish from reference, simple movement, no flat lay, soft natural light.",
                    "Everyday outfit context shot in a category-selected cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, mirror, hallway, or wardrobe-edge setting, garment worn by adult person, full body or near full body visible, natural movement and styling context, no copied avatar-reference background, no body outcome claims.",
                    "Avatar back on camera with garment worn, full outfit silhouette visible again, same wardrobe continuity when possible, calm closing beat, product detail visible, no button or click instruction.",
                ],
                "texts": ["Schnitt getragen", "Material nah", "Im Outfit", "Ruhiger Detailcheck"],
            },
        }
        return recipes.get(
            category,
            {
                "visuals": [
                    "Avatar speaks directly to camera in one category-selected minimal real-space context based on product type and use case, product held, worn, or used naturally at frame edge, off-center composition, slight handheld sway, available natural light, hands relaxed and anatomically correct, no copied avatar-reference background, avoid defaulting to home/apartment interiors unless the product is home-use.",
                    "Handheld close-ups from the product reference: visible shape, finish, controls, texture, construction or packaging if present, product held or used when plausible, soft directional light, stable adult hands, no extra fingers, no warped grip.",
                    "Everyday context shot adapted to the product category, product used or held by an adult person in a plausible minimal real space, no studio look, no copied avatar-reference background.",
                    "Avatar back on camera with product visible and handled naturally, same setting and wardrobe continuity, subtle smile, plain spoken closing recap with no generated overlay, button, or click instruction.",
                ],
                "texts": ["Detail zuerst", "Nahes Detail", "Echte Groesse", "Ruhiger Check"],
            },
        )
    recipes = {
        "handbag": {
            "visuals": [
                "Avatar speaks the main buyer hook in a category-selected commute, office doorway, cafe entrance, quiet street doorway, hallway, mirror, or leaving-home context, handbag on shoulder and then in hand against outfit, handles, silhouette, and same body-to-bag scale visible in the first two seconds, off-center smartphone composition, slight handheld sway, natural expression with a small pause, available natural light, no copied avatar-reference background, do not default to apartment interiors unless the product brief implies home use.",
                f"{capacity_visual_en} Use a simple surface such as office desk, cafe table, parked car seat, hallway console, or clean counter according to the chosen context, not a studio flat lay.",
                    f"Macro handheld detail sequence: {material_focus}, stitching, handles, opening, and interior lining when visible, then an outfit-scale shot in the chosen office, cafe, commute, street doorway, mirror, or hallway context, same bag size relative to torso and hands, UK/Scandinavian minimalist styling, warm neutral colours, no cluttered tabletop layout.",
                "Avatar leaving home or doing a natural mirror outfit check with handbag on shoulder, then back on camera for a plain spoken product-name closing recap with no generated overlay, same wardrobe continuity, same bag size and carry position near torso, authentic relaxed face, no exaggerated smile, no fake button or URL.",
            ],
            "texts": ["Elegant but practical", "Fits daily essentials", material_label_en, closing_label_en],
        },
        "shoes": {
            "visuals": [
                "Avatar speaks directly to camera in a category-selected outdoor doorway, pavement edge, office lift lobby, cafe entrance, clean floor, or entryway context, shoes visible on feet in lower frame or held briefly at frame edge, off-center composition, slight handheld sway, available natural light, no copied avatar-reference background.",
                "Low-angle worn close-ups of shoes on adult feet: side profile, toe shape, upper texture, sole edge, stitching or closure, no table, no flat lay, slight handheld sway, natural floor texture.",
                "Worn outfit context shot in a category-selected outdoor doorway, cafe entrance, office lift lobby, quiet pavement edge, clean floor, or mirror setting, adult person wearing the shoes with everyday trousers or skirt hem visible, natural light, no tabletop styling, no copied avatar-reference background.",
                "Avatar back on camera with shoes visible on feet in lower frame or held naturally, same wardrobe continuity, calm closing beat, no button or click instruction.",
            ],
            "texts": ["Side profile", "Sole close-up", "Worn with outfit", "Calm detail check"],
        },
        "apparel": {
            "visuals": [
                "Avatar speaks directly to camera in a category-selected clean mirror, hallway, cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, or wardrobe-edge context, garment worn on body, full-body or near full-body head-to-toe silhouette visible from the first beat, off-center smartphone composition, slight handheld sway, available natural light, no copied avatar-reference background.",
                "Mirror or handheld worn view of the whole garment first, then brief close details only if the full outfit remains understandable: cut, drape, sleeve, hem, seam, exact visible finish from reference, simple movement, no flat lay, soft natural light.",
                "Everyday outfit context shot in a category-selected cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, mirror, hallway, or wardrobe-edge setting, garment worn by adult person, full body or near full body visible, natural movement and styling context, no copied avatar-reference background, no body outcome claims.",
                "Avatar back on camera with garment worn, full outfit silhouette visible again, same wardrobe continuity when possible, calm closing beat, product detail visible, no button or click instruction.",
            ],
                "texts": ["Check the cut", "Detail close-up", "Worn in context", "Calm detail check"],
        },
    }
    return recipes.get(
        category,
        {
            "visuals": [
                "Avatar speaks directly to camera in one category-selected minimal real-space context based on product type and use case, product held, worn, or used naturally at frame edge, off-center composition, slight handheld sway, available natural light, no copied avatar-reference background, avoid defaulting to home/apartment interiors unless the product is home-use.",
                "Handheld close-ups from the product reference: visible shape, finish, controls, texture, construction or packaging if present, product held or used when plausible, soft directional light.",
                "Everyday context shot adapted to the product category, product used or held by an adult person in a plausible minimal real space, no studio look, no copied avatar-reference background.",
                "Avatar back on camera with product visible and handled naturally, same setting and wardrobe continuity, subtle smile, plain spoken closing recap with no generated overlay, button, or click instruction.",
            ],
            "texts": ["Check the detail", "Close-up details", "Real-life scale", "Calm detail check"],
        },
    )


def _voice_profile(language: str, market: str) -> str:
    language_value = str(language or "").lower()
    market_value = str(market or "").upper()
    if language_value.startswith("en") and market_value in {"UK", "GB", "GBR"}:
        return (
            "Natural British English creator voice with a subtle everyday British accent, "
            "British phrasing and spelling, relaxed conversational delivery, not American"
        )
    if language_value.startswith("en") and market_value in {"US", "USA"}:
        return "Natural American English creator voice, relaxed conversational delivery"
    if _is_czech(language):
        return "Natural Czech creator voice, relaxed conversational delivery"
    if _is_german(language):
        return "Natural German creator voice for the selected market, relaxed conversational delivery, German phrasing"
    return f"Natural creator voice for market {market}, relaxed conversational delivery"


def _user_scenario_lock(
    settings: dict[str, Any],
    *,
    category: str,
    language: str,
) -> dict[str, Any]:
    raw = str(settings.get("ugc_video_extra_prompt") or "").strip()
    if not raw:
        return {"enabled": False}
    text = " ".join(raw.replace("\r", "\n").split())[:2600]
    text = _sanitize_user_scenario_generic_fabric_words(text, category)
    lowered = text.lower()
    if not _looks_like_user_scenario_direction(lowered):
        return {"enabled": False}
    mirror_selfie = any(marker in lowered for marker in ["mirror selfie", "zrcad", "pres zrcad", "přes zrcad"])
    try_on = any(marker in lowered for marker in ["try-on", "try on", "outfit", "oblecen", "obleceni", "oblečení", "overall", "overal", "dress", "saty", "šaty", "fit"])
    one_take = any(marker in lowered for marker in ["one continuous", "souvisly zaber", "souvislý záběr", "bez strihu", "bez střihu", "prakticky bez"])
    home_room = any(marker in lowered for marker in ["simple room", "neutral wall", "jednoduch", "neutralni stena", "neutrální stěna", "domaci", "domácí", "bezny domov", "běžný domov"])
    handheld = any(marker in lowered for marker in ["handheld", "phone in hand", "telefon v ruce", "rucne", "ručně", "kamera ma pusobit", "kamera má působit"])
    natural_tone = any(marker in lowered for marker in ["friend", "kamarad", "kamarád", "prirozen", "přirozen", "short sentences", "kratke vety", "krátké věty"])
    if try_on and re.search(r"\bfits?\s+in\b", lowered) and not any(marker in lowered for marker in ["try-on", "try on", "outfit", "dress"]):
        try_on = False
    is_apparel_like = category == "apparel" or try_on

    template_id = "mirror_selfie_try_on_review" if mirror_selfie and try_on else "custom_user_scenario"
    hook_text = _extract_user_scenario_hook(text)
    if hook_text and not _matches_selected_language(hook_text, language):
        hook_text = ""

    rules = [
        "USER SCENARIO LOCK: preserve this user-provided creator video style as high-priority scene direction unless it conflicts with product fidelity, avatar identity, target language, safety, or verified product facts",
        "treat product names, colours, and garment specifics inside the note as examples only when they conflict with the actual product reference",
        "do not turn the opening into a polished ad; keep it like a real buyer-check clip",
    ]
    if mirror_selfie:
        rules.append(
            "hard mirror-selfie camera lock: the creator is filming herself in a mirror with a smartphone visibly held in one hand; "
            "the viewer sees the mirror reflection, the phone in hand, and the creator/garment in the same reflected composition; "
            "during spoken lines the phone sits low or to the side so the mouth remains visible and actively speaking; "
            "keep normal smartphone 9:16 framing and natural human body proportions like a real mirror selfie"
        )
        rules.extend(MIRROR_SELFIE_LOCK_RULES)
    if try_on:
        rules.append("try-on review logic; creator actively shows the product worn or used on body when category allows")
    if one_take:
        rules.append("mostly one continuous take; avoid complex cuts, scene changes, and cinematic transitions")
    if home_room:
        rules.append("simple bedroom or ordinary room, neutral wall, minimal background, domestic atmosphere, no luxury studio")
    if handheld:
        rules.append("handheld smartphone feel with slight sway and imperfect framing")
    if natural_tone:
        rules.append("short relaxed sentences, calm friend-to-friend tone, personal recommendation energy")
    bag_closed_requested = any(
        marker in lowered
        for marker in [
            "bag stays closed",
            "keep the bag closed",
            "do not open",
            "do not open or close the zipper",
            "neotevirat",
            "neotevírat",
        ]
    )
    no_insert_requested = any(
        marker in lowered
        for marker in [
            "do not show items being inserted",
            "do not show items inserted",
            "do not place items inside",
            "nevkladat",
            "nevkládat",
        ]
    )
    if any(marker in lowered for marker in ["mom", "mother", "mum", "mama"]):
        rules.append("adult woman/mom creator subject lock; keep the parent-routine context when safe and product-relevant")
        if any(marker in lowered for marker in ["child", "kid", "baby", "diaper", "diapers", "wipes"]):
            if bag_closed_requested or no_insert_requested:
                rules.append("parent routine proof: place diapers, wipes, snacks, phone, wallet, and keys beside the closed bag; never insert them into the bag")
            else:
                rules.append("parent routine proof: use diapers, wipes, snacks, phone, wallet, and keys as bag contents where plausible; do not require a visible child")
    if bag_closed_requested:
        rules.append("product action lock: the bag stays closed; do not open, unzip, close, or reveal compartments")
    if no_insert_requested:
        rules.append("product action lock: proof items stay beside the bag; do not put, pack, place, or insert items inside")
    if is_apparel_like:
        rules.append("full-body or near full-body garment view first; show cut, waist, neckline, hem, drape, and overall fit by turning slightly")

    forbidden = [
        "do not copy conflicting example product colour/category from the note",
        "no luxury studio, runway posing, glossy fashion editorial, or overproduced commercial look",
        "no generated on-screen text, captions, subtitles, lower thirds, or hook stickers; the hook is spoken aloud",
    ]
    if mirror_selfie:
        forbidden.extend(MIRROR_SELFIE_FORBIDDEN)

    return {
        "enabled": True,
        "source": "ugc_video_extra_prompt",
        "priority": "hard_lock_except_safety_product_fidelity_language_avatar_identity",
        "template_id": template_id,
        "hook_text": hook_text,
        "raw_user_direction": text,
        "detected_traits": {
            "mirror_selfie": mirror_selfie,
            "try_on_review": try_on,
            "one_take": one_take,
            "simple_home_room": home_room,
            "handheld_phone": handheld,
            "natural_friend_tone": natural_tone,
            "apparel_like": is_apparel_like,
        },
        "rules": rules,
        "forbidden": forbidden,
        "compiled_direction": "; ".join(rules),
    }


def _sanitize_user_scenario_generic_fabric_words(text: str, category: str) -> str:
    if str(category or "").strip().lower() != "apparel":
        return text
    # In apparel scenario notes, "fabric" is usually generic garment handling
    # ("adjusts the fabric") rather than a verified material claim.
    return re.sub(r"\bfabric\b", "garment", str(text or ""), flags=re.IGNORECASE)


def _mirror_selfie_environment_lock() -> str:
    return (
        "single simple bedroom mirror-selfie environment: plain neutral wall, minimal background, visible mirror reflection, "
        "creator holds smartphone in one hand and films herself through the mirror, phone low or to the side during speech so the mouth remains visible, normal 9:16 smartphone framing, natural human proportions, no mirror stretch or fisheye distortion, natural indoor daylight, slight handheld shake; "
        "no non-bedroom/public/work/outdoor locations, no secondary room setup, no studio, no tripod, no third-person camera setup, no external camera, no perspective switch, no cutaway, no cinematic b-roll, and no avatar walking away from the mirror"
    )


def _looks_like_user_scenario_direction(lowered_text: str) -> bool:
    markers = [
        "chat approved scenario",
        "approved chat scenario",
        "scenar",
        "scenario",
        "script:",
        "visual plan:",
        "mirror selfie",
        "try-on",
        "try on",
        "one continuous",
        "souvisly zaber",
        "souvislý záběr",
        "on screen hook",
        "on screan hook",
        "scene direction",
        "ugc type",
    ]
    return any(marker in lowered_text for marker in markers)


def _extract_user_scenario_hook(text: str) -> str:
    normalized = (
        str(text or "")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
    )
    patterns = [
        r"on\s*scr(?:ee|ea)n\s*hook\s*[:=\-]\s*(.+)",
        r"on[-\s]*screen\s+hook\s*[:=\-]\s*(.+)",
        r"\bhook\s*[:=\-]\s*(.+)",
    ]
    candidate = ""
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1)
            break
    if not candidate:
        return ""
    candidate = re.split(
        r"(?:\.\.\.|\s+ber\s+to\b|\s+co\s+je\s+dulezite\b|\s+co\s+je\s+důležité\b|\s+nezacinat\b|\s+nezačínat\b)",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    candidate = re.split(
        r"(?:\s+script\s*:|\s+visual\s+plan\s*:|\s+cta\s*:|\s+keep\s+the\b|\s+do\s+not\b)",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    candidate = candidate.strip(" \t\n\r\"'`.,;:-")
    return _shorten_words(candidate, 10)


def _apply_user_scenario_lock_to_scenes(
    scenes: list[dict[str, Any]],
    scenario_lock: dict[str, Any],
    *,
    category: str,
) -> list[dict[str, Any]]:
    if not scenario_lock.get("enabled"):
        return scenes
    updated: list[dict[str, Any]] = []
    template_id = scenario_lock.get("template_id")
    rules = scenario_lock.get("compiled_direction") or ""
    hook_text = scenario_lock.get("hook_text") or ""
    for index, scene in enumerate(scenes):
        copied = dict(scene)
        scene_direction = _scenario_lock_scene_direction(index, template_id, category)
        visual_parts = (
            [scene_direction, rules]
            if template_id == "mirror_selfie_try_on_review"
            else [scene.get("visual"), scene_direction, rules]
        )
        copied["visual"] = _clean_scene_direction(
            " ".join(part for part in visual_parts if part)
        )
        if template_id == "mirror_selfie_try_on_review":
            copied["shot_type"] = [
                "mirror selfie hook",
                "same-take try-on detail",
                "same-take outfit proof",
                "same-take calm recommendation",
            ][min(index, 3)]
        if index == 0 and hook_text:
            copied["voiceover"] = hook_text
            copied["on_screen_text"] = ""
            copied["subtitle"] = hook_text
        updated.append(copied)
    return updated


def _apply_user_scenario_lock_to_scene_chaining(
    scene_chaining: dict[str, Any],
    scenario_lock: dict[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(scene_chaining, dict)
        or not scenario_lock.get("enabled")
        or scenario_lock.get("template_id") != "mirror_selfie_try_on_review"
    ):
        return scene_chaining
    environment = _mirror_selfie_environment_lock()
    updated = dict(scene_chaining)
    updated["environment_continuity"] = environment
    updated["seedance_prompt_addendum"] = _clean_scene_direction(
        " ".join(
            part
            for part in [
                scene_chaining.get("seedance_prompt_addendum"),
                "MIRROR SELFIE HARD LOCK:",
                environment,
                "Every scene should feel like the same self-filmed mirror try-on, with the smartphone visible in the mirror reflection and the creator controlling the camera herself.",
                "Do not use a visible freeze or hold-frame as the opening; each segment starts with live phone sway, blink, mouth movement, or a small natural hand gesture.",
            ]
            if part
        )
    )
    links = []
    for link in scene_chaining.get("scene_links") or []:
        copied = dict(link)
        copied["environment_anchor"] = environment
        copied["next_scene_start"] = (
            "continue from the same mirror reflection setup; creator still holds the smartphone visibly in one hand and starts with live mouth, blink, phone sway, or hand movement, not a frozen hold"
        )
        copied["motion_bridge"] = "small phone sway, partial side turn while still facing the mirror, or hand gesture toward waist/neckline; no full back turn, no walking away, no perspective change"
        copied["last_frame_capture"] = "end on a brief stable-but-live mirror pose with face and garment visible, subtle blink or phone sway, not a frozen hold-frame"
        links.append(copied)
    if links:
        updated["scene_links"] = links
    plan = dict(updated.get("true_scene_chaining_plan") or {})
    if plan:
        plan["environment_lock"] = environment
        plan["scene_links"] = [
            {
                **dict(link),
                "environment_anchor": environment,
                "next_scene_start": "same mirror reflection setup with smartphone visible in creator hand, live motion from the first frame",
                "motion_bridge": "small phone sway or partial side turn in mirror, then simple cut; no external camera or back shot",
                "last_frame_capture": "brief stable-but-live mirror pose, not a frozen hold-frame",
            }
            for link in (plan.get("scene_links") or [])
        ]
        updated["true_scene_chaining_plan"] = plan
    return updated


def _scenario_lock_scene_direction(index: int, template_id: Any, category: str) -> str:
    if template_id == "mirror_selfie_try_on_review":
        common = (
            "USER SCENARIO LOCK scene execution: vertical mirror selfie try-on review in a simple bedroom or ordinary room with a neutral wall and minimal background; "
            "the shot is filmed by the creator herself through a mirror, smartphone visibly held in one hand inside the mirror reflection but low or to the side while speaking so the mouth remains visible, normal smartphone 9:16 framing with natural body proportions, soft indoor daylight, slight handheld phone shake, relaxed real customer review energy; "
            "camera source is only the iPhone mirror selfie recording for the entire duration; no external camera, no tripod, no third-person camera operator, no ordinary front-facing talking-head framing, no side filming, no over-the-shoulder shot, no room camera, no cinematic b-roll, no cutaway, no perspective switch, no phone covering the speaking mouth; "
            "opening anti-freeze: visible live motion starts immediately with tiny phone sway, blink, mouth/jaw movement, or a small free-hand gesture"
        )
        if index == 0:
            apparel = (
                "full-body or near full-body head-to-toe reflected view from the first beat, creator wearing the garment, natural body-to-garment proportions, phone visible in hand, speaking mouth visible, not cropped to face/chest"
                if category == "apparel"
                else "product visible naturally from the first beat"
            )
            return f"{common}; start non-advertorial, creator visibly speaks to her phone while looking at the mirror reflection, mouth and jaw naturally moving with the hook, no still poster frame, {apparel}"
        if index == 1:
            return f"{common}; stay in the same mirror reflection shot, creator keeps phone visible, gestures with the free hand and points to waist, neckline, cut, or visible details without leaving the mirror setup"
        if index == 2:
            return f"{common}; creator turns only partially sideways in front of the mirror while still facing it, never fully back to camera and never walking away, keeping the phone in hand visible, showing real-life scale, cut, fit, movement, and overall silhouette in the same simple room"
        return f"{common}; calm friend-to-friend closing in the same mirror reflection, phone still visible in hand, still one-take feeling, no button-like CTA, no studio polish"
    return (
        "USER SCENARIO LOCK scene execution: follow the user-provided camera, setting, pacing, and creator behaviour as the primary scene style; "
        "keep the actual product reference and avatar identity unchanged"
    )


def _apply_scenario_contract_to_video_scenes(
    scenes: list[dict[str, Any]],
    contract: dict[str, Any],
    *,
    language: str,
    category: str,
) -> list[dict[str, Any]]:
    if not contract.get("enabled"):
        return scenes
    tags = set(contract.get("tags") or [])
    updated: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes):
        copied = dict(scene)
        copied["visual"] = _contract_safe_scene_visual(
            copied.get("visual"),
            contract,
            index=index,
            language=language,
            category=category,
        )
        copied["voiceover"] = _contract_safe_voiceover(
            copied.get("voiceover"),
            contract,
            index=index,
            language=language,
            category=category,
        )
        copied["shot_type"] = _contract_safe_shot_type(copied.get("shot_type"), contract, index=index)
        copied["scenario_contract_tags"] = sorted(tags)
        copied["scenario_contract_status"] = "applied"
        updated.append(copied)
    return updated


def _contract_safe_scene_visual(
    visual: Any,
    contract: dict[str, Any],
    *,
    index: int,
    language: str,
    category: str,
) -> str:
    text = scenario_contract.rewrite_for_contract(str(visual or ""), contract)
    text = scenario_contract.remove_conflicting_directives(text, contract)
    tags = set(contract.get("tags") or [])
    if category == "handbag" and {"bag_closed", "no_insert_items"} & tags:
        role = [
            "closed-bag hook with adult woman/mom creator, bag worn crossbody or held in hand, exterior silhouette and body scale visible",
            "closed-bag proof: diapers, wipes, snacks, phone, wallet, and keys placed beside the bag for scale; no zipper opening and no items inserted",
            "exterior detail proof only: strap, zipper line, checkered pattern, stitching, silhouette, and scale while the bag stays closed",
            "everyday carry recap with the closed bag on shoulder or in hand, same product size and identity preserved",
        ][min(index, 3)]
        text = f"{role}. {text}"
    lock = scenario_contract.video_prompt_lock(contract)
    if lock and lock not in text:
        text = f"{text} Approved scenario contract: {lock}"
    return _clean_scene_direction(text)


def _contract_safe_voiceover(
    voiceover: Any,
    contract: dict[str, Any],
    *,
    index: int,
    language: str,
    category: str,
) -> str:
    text = scenario_contract.rewrite_for_contract(str(voiceover or ""), contract)
    tags = set(contract.get("tags") or [])
    if category == "handbag" and {"bag_closed", "no_insert_items"} & tags:
        if index == 1:
            if _is_czech(language):
                return "Plenky, ubrousky, telefon a klice ukazou meritko vedle zavrene tasky."
            if _is_german(language):
                return "Windeln, Tuecher, Handy und Schluessel zeigen die Groesse neben der geschlossenen Tasche."
            return "Diapers, wipes, phone, and keys beside the closed bag make the scale clear."
        if index == 2:
            if _is_czech(language):
                return "Zblizka jde videt popruh, zipova linie, tvar a vzor bez otevirani."
            if _is_german(language):
                return "Aus der Naehe sieht man Riemen, Reissverschlusslinie, Form und Muster ohne Oeffnen."
            return "Up close, you can check the strap, zipper line, shape, and pattern without opening it."
    return _clean_scene_direction(text)


def _contract_safe_shot_type(value: Any, contract: dict[str, Any], *, index: int) -> str:
    text = scenario_contract.rewrite_for_contract(str(value or ""), contract)
    text = scenario_contract.remove_conflicting_directives(text, contract)
    tags = set(contract.get("tags") or [])
    if {"bag_closed", "no_insert_items"} & tags:
        return [
            "closed-bag hook",
            "beside-the-bag scale proof",
            "closed exterior detail proof",
            "closed-bag carry recap",
        ][min(index, 3)]
    return _clean_scene_direction(text)


def _scenario_contract_video_plan(contract: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    if not contract.get("enabled"):
        return {"enabled": False}
    return {
        "enabled": True,
        "source": contract.get("source"),
        "version": contract.get("version"),
        "tags": contract.get("tags") or [],
        "subject_gender": contract.get("subject_gender"),
        "must_include_any": contract.get("must_include_any") or [],
        "forbidden_checks": [
            {"id": item.get("id"), "label": item.get("label")}
            for item in contract.get("forbidden_checks") or []
        ],
        "scene_contract": [
            {
                "time": scene.get("time"),
                "shot_type": scene.get("shot_type"),
                "visual_contract": scene.get("visual"),
            }
            for scene in scenes
        ],
        "qa": [
            "final provider prompt must pass scenario_integrity_guard before generation",
            "visual classifier suggestions are advisory only when they conflict with this contract",
            "spoken audio carries the hook; generated text overlays remain post-production metadata",
        ],
    }


def _clean_scene_direction(value: str) -> str:
    return " ".join(str(value or "").split())


def generate_strategy(
    product_analysis: dict[str, Any],
    avatar: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    platform = settings.get("platform", "meta").lower()
    language = settings.get("language", "en")
    market = settings.get("market", "US")
    duration = int(settings.get("video_length") or 15)
    platform_spec = PLATFORM_DEFAULTS.get(platform, PLATFORM_DEFAULTS["meta"])
    product_name = product_analysis["product_name"]
    category = product_analysis["likely_product_category"]
    angle = product_analysis["safest_creative_angle"]
    ad_detail_phrases = (
        product_analysis.get("ad_safe_detail_phrases_localized")
        or product_analysis.get("ad_safe_detail_phrases")
        or [localize_phrase("visible product details", language)]
    )
    user_facts = product_analysis.get("user_provided_facts_localized") or product_analysis.get("user_provided_facts") or []
    avatar_name = avatar.get("name", "Creator")
    testimonial_enabled = bool(settings.get("testimonial_mode"))
    is_czech = _is_czech(language)
    voice_profile = _voice_profile(language, market)
    avatar_voice = language_safe_voice_descriptor(
        sanitize_avatar_descriptor(avatar.get("voice")),
        language,
    )
    if avatar_voice:
        voice_profile = f"{voice_profile}; selected creator voice: {avatar_voice}"
    audience_research = settings.get("audience_research") or {}
    emotional_angle = settings.get("emotional_angle") or {}
    creative_psychology = settings.get("creative_psychology") or {}
    voice_personality = settings.get("voice_personality") or {}
    hook_strategy = settings.get("ugc_hook_strategy") or {}
    scene_direction = settings.get("scene_direction") or {}
    scene_chaining = settings.get("scene_chaining") or {}
    performance_insights = settings.get("performance_insights") or {}
    visual_product_understanding = product_analysis.get("visual_product_understanding") or {}
    if voice_personality.get("prompt_fragment"):
        voice_profile = f"{voice_profile}; {voice_personality['prompt_fragment']}"
    product_label = _spoken_product_label(product_name, category, language)
    capacity_supported = category == "handbag" and _handbag_capacity_supported(product_analysis)
    material_focus = _handbag_material_focus(product_analysis) if category == "handbag" else "material texture"
    detail_focus = _detail_focus(category, language, user_facts)
    scene_recipe = _scene_recipe(
        category,
        language,
        capacity_supported=capacity_supported,
        material_focus=material_focus,
        product_name=product_name,
    )
    directed_scenes = scene_direction.get("directed_scenes") or []
    if len(directed_scenes) >= 4:
        scene_visuals = [str(scene.get("visual") or "") for scene in directed_scenes[:4]]
        scene_texts = [str(scene.get("overlay") or "") for scene in directed_scenes[:4]]
        scene_shot_types = [str(scene.get("shot_type") or "") for scene in directed_scenes[:4]]
    else:
        scene_visuals = scene_recipe["visuals"]
        scene_texts = scene_recipe["texts"]
        scene_shot_types = ["hook", "detail close-up", "context", "closing detail"]
    scene_texts = _language_safe_scene_texts(scene_texts, scene_recipe["texts"], language)

    fallback_hook = _hook_line(
        product_label,
        category,
        language,
        capacity_supported=capacity_supported,
    )
    hook = _customer_hook_from_strategy(hook_strategy, fallback_hook, language)
    primary_archetype = audience_research.get("primary_archetype") or "detail-focused shopper"
    behavior_tree = creative_psychology.get("behavior_tree") or {}
    primary_driver = creative_psychology.get("primary_driver") or ""
    emotional_safe_label = emotional_angle.get("primary_safe_label") or emotional_angle.get("primary_angle")
    decision_triggers = audience_research.get("decision_triggers") or []
    first_trigger = localize_phrase(decision_triggers[0], language) if decision_triggers else detail_focus

    if category == "handbag":
        scene_2_voiceover = _handbag_capacity_voiceover(language, capacity_supported)
        scene_3_voiceover = _handbag_quality_voiceover(language, material_focus)
        scene_4_voiceover = _handbag_closing_line(
            product_name,
            language,
            capacity_supported,
            material_focus,
        )
    else:
        if is_czech:
            scene_2_voiceover = f"Zblizka je nejdulezitejsi {detail_focus}."
            scene_3_voiceover = (
                f"Dulezite je videt {first_trigger} v normalnim kontextu."
                if primary_archetype != "detail-focused shopper"
                else _context_line(category, language)
            )
        elif _is_german(language):
            scene_2_voiceover = f"Aus der Naehe zaehlt vor allem {detail_focus}."
            localized_trigger = localize_phrase(first_trigger, language)
            scene_3_voiceover = (
                f"Wichtig ist, {localized_trigger} in einem normalen Kontext zu sehen."
                if primary_archetype != "detail-focused shopper"
                else _context_line(category, language)
            )
        else:
            scene_3_voiceover = (
                f"The useful bit is seeing {first_trigger} in a normal context."
                if primary_archetype != "detail-focused shopper"
                else _context_line(category, language)
            )
            scene_2_voiceover = f"Up close, the key details are {detail_focus}."
        scene_4_voiceover = _closing_line(category, language)

    hook_caption = _subtitle_line(hook, language) or scene_texts[0]
    scenes = [
        {
            "time": "0-3s",
            "visual": scene_visuals[0],
            "voiceover": hook,
            "on_screen_text": hook_caption,
            "subtitle": _subtitle_line(hook, language),
            "shot_type": scene_shot_types[0],
            "psychology_step": (behavior_tree.get("sequence") or ["hook"])[0],
        },
        {
            "time": f"3-{max(7, duration // 2)}s",
            "visual": scene_visuals[1],
            "voiceover": scene_2_voiceover,
            "on_screen_text": scene_texts[1],
            "subtitle": _subtitle_line(scene_2_voiceover, language),
            "shot_type": scene_shot_types[1],
            "psychology_step": ((behavior_tree.get("sequence") or []) + ["detail"] * 4)[1],
        },
        {
            "time": f"{max(7, duration // 2)}-{max(11, duration - 3)}s",
            "visual": scene_visuals[2],
            "voiceover": scene_3_voiceover,
            "on_screen_text": scene_texts[2],
            "subtitle": _subtitle_line(scene_3_voiceover, language),
            "shot_type": scene_shot_types[2],
            "psychology_step": ((behavior_tree.get("sequence") or []) + ["context"] * 4)[2],
        },
        {
            "time": f"{max(11, duration - 3)}-{duration}s",
            "visual": scene_visuals[3],
            "voiceover": scene_4_voiceover,
            "on_screen_text": scene_texts[3],
            "subtitle": _subtitle_line(scene_4_voiceover, language),
            "shot_type": scene_shot_types[3],
            "psychology_step": ((behavior_tree.get("sequence") or []) + ["close"] * 4)[3],
        },
    ]
    scenario_lock = _user_scenario_lock(settings, category=category, language=language)
    if scenario_lock.get("enabled"):
        scenes = _apply_user_scenario_lock_to_scenes(scenes, scenario_lock, category=category)
        scene_chaining = _apply_user_scenario_lock_to_scene_chaining(scene_chaining, scenario_lock)
    user_scenario_contract = scenario_contract.build(
        scenario_lock,
        avatar=avatar,
        product_analysis=product_analysis,
    )
    scenes = _apply_scenario_contract_to_video_scenes(
        scenes,
        user_scenario_contract,
        language=language,
        category=category,
    )
    voiceover = " ".join(scene["voiceover"] for scene in scenes)
    ugc_prompt_skill = arcads_ugc_guidance.build_guidance(
        product_analysis,
        settings,
        user_scenario_lock=scenario_lock,
    )

    return {
        "agent": "UGC Strategy Agent",
        "selected_angle": angle,
        "ad_detail_phrases": ad_detail_phrases,
        "platform": platform,
        "market": market,
        "language": language,
        "language_instruction": (
            f"{language_copy_policy(language)} "
            f"Voice profile: {voice_profile}."
        ),
        "customer_language_name": target_language_name(language),
        "voice_profile": voice_profile,
        "voice_personality": voice_personality,
        "emotional_angle": emotional_angle,
        "duration_seconds": duration,
        "aspect_ratio": platform_spec["aspect_ratio"],
        "platform_adaptation": {
            "style": platform_spec["style"],
            "safe_area": platform_spec["safe_area"],
            "hook_timing": "Hook appears in the first 3 seconds",
        },
        "category_video_recipe": {
            "category": category,
            "source": "multi-agent deterministic fallback: audience research + psychology + hook + scene direction before optional OpenRouter prompt enhancement",
            "scene_visuals": scene_visuals,
            "scene_shot_types": scene_shot_types,
            "handbag_capacity_supported": capacity_supported if category == "handbag" else None,
            "ugc_template": ugc_prompt_skill["template_id"],
            "ugc_template_source": ugc_prompt_skill["source"],
            "visual_classifier_status": visual_product_understanding.get("status"),
            "visual_detected_object": visual_product_understanding.get("detected_object"),
            "visual_subcategory": visual_product_understanding.get("subcategory"),
            "visual_recommended_template": visual_product_understanding.get("recommended_template_id"),
            "visual_shot_requirements": scenario_contract.filter_conflicting_items(
                visual_product_understanding.get("shot_requirements") or [],
                user_scenario_contract,
            ),
            "user_scenario_lock_template": scenario_lock.get("template_id") if scenario_lock.get("enabled") else None,
        },
        "user_scenario_lock": scenario_lock,
        "user_scenario_contract": user_scenario_contract,
        "videoagent_workflow": {
            "source": "local skill/videoagent",
            "intent": "UGC ad scene direction and provider-ready prompt planning",
            "steps": [
                "parse user and product intent",
                "choose product/category proof template",
                "compile scene-by-scene beat plan",
                "apply approved scenario contract",
                "run provider preflight and scenario integrity before generation",
            ],
            "scenario_contract_plan": _scenario_contract_video_plan(user_scenario_contract, scenes),
        },
        "ugc_prompt_skill": ugc_prompt_skill,
        "performance_insights": performance_insights,
        "audience_research": audience_research,
        "creative_psychology": creative_psychology,
        "hook_strategy": hook_strategy,
        "scene_direction": scene_direction,
        "scene_chaining": scene_chaining,
        "hook": hook,
        "scene_by_scene_script": scenes,
        "voiceover": voiceover,
        "on_screen_text": [scene["on_screen_text"] for scene in scenes],
        "subtitles": [scene["subtitle"] for scene in scenes],
        "subtitle_rules": {
            "source": "derived from the matching scene voiceover, never from product notes or overlay labels",
            "max_words_per_caption": 8,
            "style": "short spoken caption fragments, no CTA buttons, no click/tap language, no invented facts",
        },
        "cta": "handled_by_ad_platform",
        "tone": (
            f"natural, practical, creator-led, trustworthy, archetype-aware: {primary_archetype}; "
            f"emotional angle: {emotional_safe_label or 'detail_curiosity'}"
        ),
        "fallback_quality_upgrade": {
            "behavior_tree_driver": primary_driver,
            "audience_archetype": primary_archetype,
            "emotional_angle": emotional_safe_label,
            "decision_triggers": decision_triggers,
            "memory_matching_records": performance_insights.get("matching_record_count"),
        },
        "avatar_direction": {
            "avatar_name": avatar_name,
            "testimonial_mode": testimonial_enabled,
            "personal_use_claims_allowed": testimonial_enabled and bool(settings.get("testimonial_source")),
            "instruction": "Do not imply personal product use unless testimonial source is supplied.",
        },
    }
