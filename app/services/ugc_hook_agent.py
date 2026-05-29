from __future__ import annotations

from typing import Any

from app.services.localization_utils import is_czech as _is_czech_language, is_german


def generate(
    product_analysis: dict[str, Any],
    audience_research: dict[str, Any],
    creative_psychology: dict[str, Any],
    performance_insights: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    is_czech = _is_czech_language(language)
    is_de = is_german(language)
    category = str(product_analysis.get("likely_product_category") or "product")
    product_label = _product_label(product_analysis, category, language)
    archetype = audience_research.get("primary_archetype") or "practicality"
    memory_hooks = performance_insights.get("winning_hooks") or []
    hooks = _category_hooks(
        category,
        product_label,
        archetype,
        is_czech,
        is_de=is_de,
        capacity_supported=_handbag_capacity_supported(product_analysis),
        material_focus=_handbag_material_focus(product_analysis),
    )
    if memory_hooks:
        hooks = [{"pattern": "memory_winner", "hook": memory_hooks[0], "source": "performance_memory"}] + hooks
    selected = hooks[0]
    return {
        "agent": "UGC Hook Agent",
        "selected_hook": selected["hook"],
        "selected_pattern": selected["pattern"],
        "hook_bank": hooks[:8],
        "hook_strategy": {
            "archetype": archetype,
            "psychology": creative_psychology.get("hook_psychology") or [],
            "rule": "Lead with a concrete viewing/evaluation behavior, not a generic product promise.",
        },
    }


def _category_hooks(
    category: str,
    product_label: str,
    archetype: str,
    is_czech: bool,
    *,
    is_de: bool = False,
    capacity_supported: bool = False,
    material_focus: str = "material texture",
) -> list[dict[str, str]]:
    if is_czech:
        handbag_primary = (
            f"Konecne {product_label}, ktera vypada elegantne a pritom pobere denni veci."
            if capacity_supported
            else f"Konecne {product_label}, ktera vypada elegantne a dava smysl na kazdy den."
        )
        premium_hook = (
            "Elegantni tvar je fajn, ale detail kuze a siti rozhoduje."
            if "leather" in material_focus
            else "Elegantni tvar je fajn, ale detail materialu a siti rozhoduje."
        )
        hooks = {
            "handbag": [
                ("elegant_practical", handbag_primary),
                ("daily_capacity", f"U {product_label} chci hned videt, co se do ni realne vejde."),
                ("premium_proof", premium_hook),
                ("not_product_demo", "Nechci jen produktovou ukazku. Chci videt, jak funguje v realu."),
            ],
            "shoes": [
                ("worn_not_table", f"U {product_label} je nejdulezitejsi profil primo na noze, ne fotka na stole."),
                ("sole_check", "Nejdriv bok, podrazka a jak sedi k outfitu."),
                ("style_check", "Tohle je detail bot, ktery z produktove fotky casto nepoznas."),
            ],
            "apparel": [
                ("worn_cut", f"U {product_label} je nejdulezitejsi strih primo na postave."),
                ("not_flat_lay", "Flat lay je hezky, ale strih ukaze az zrcadlo."),
                ("movement", "Nejdriv chci videt, jak se material hybe v realu."),
            ],
        }
    elif is_de:
        handbag_primary = (
            f"Endlich {product_label}, die elegant aussieht und trotzdem die Alltagsdinge aufnimmt."
            if capacity_supported
            else f"Endlich {product_label}, die elegant aussieht und im Alltag Sinn ergibt."
        )
        premium_hook = (
            "Eine klare Form ist gut, aber Lederdetail und Naehte entscheiden."
            if "leather" in material_focus
            else "Eine klare Form ist gut, aber Materialdetail und Naehte entscheiden."
        )
        hooks = {
            "handbag": [
                ("elegant_practical", handbag_primary),
                ("daily_capacity", "Bei dieser Tasche will ich zuerst sehen, was wirklich hineinpasst."),
                ("premium_proof", premium_hook),
                ("not_product_demo", "Ich brauche keine perfekte Produktshow. Ich will sehen, wie es im Alltag wirkt."),
            ],
            "shoes": [
                ("worn_not_table", "Bei diesen Schuhen zaehlt zuerst das Profil am Fuss, nicht ein Tischfoto."),
                ("sole_check", "Seitenprofil, Sohlenkante, dann das Outfit. Das macht die Form klar."),
                ("style_check", "Das ist das Schuhdetail, das ein Produktfoto oft versteckt."),
            ],
            "apparel": [
                ("worn_cut", "Bei diesem Kleidungsstueck zaehlt zuerst, wie der Schnitt getragen aussieht."),
                ("not_flat_lay", "Ein Flatlay ist sauber, aber der Spiegel zeigt den Schnitt."),
                ("movement", "Zuerst will ich sehen, wie sich der Stoff im Alltag bewegt."),
            ],
        }
    else:
        handbag_primary = (
            "Finally, a tote that looks elegant and still fits the daily essentials."
            if capacity_supported
            else "Finally, a tote that looks elegant without feeling too dressed-up for every day."
        )
        premium_hook = (
            "A clean shape is nice, but the leather detail is what decides it."
            if "leather" in material_focus
            else "A clean shape is nice, but the material detail is what decides it."
        )
        hooks = {
            "handbag": [
                ("elegant_practical", handbag_primary),
                ("daily_capacity", f"With {product_label}, I want to see what actually fits inside first."),
                ("premium_proof", premium_hook),
                ("not_product_demo", "I do not need a perfect product shot. I need to see how it works in real life."),
            ],
            "shoes": [
                ("worn_not_table", f"With {product_label}, the side profile on foot matters more than a table shot."),
                ("sole_check", "Side profile, sole edge, then the outfit. That is where the shape becomes clear."),
                ("style_check", "This is the shoe detail a product photo usually hides."),
            ],
            "apparel": [
                ("worn_cut", f"With {product_label}, the cut matters most when you see it worn."),
                ("not_flat_lay", "A flat lay is tidy, but the mirror shows the cut."),
                ("movement", "First I want to see how the garment moves in real life."),
            ],
        }
    if is_czech:
        fallback = [
            ("detail_first", f"U {product_label} rozhoduje detail, ne jen hezka produktova fotka."),
            ("context_first", "V realnem kontextu je hned jasnejsi, jak produkt pusobi."),
            ("skeptic", "Jedna produktova fotka nikdy neukaze cely pribeh."),
        ]
    elif is_de:
        fallback = [
            ("detail_first", "Bei diesem Produkt zaehlt zuerst der Detailblick, nicht nur das Produktfoto."),
            ("context_first", "Im echten Kontext wird sofort klarer, wie das Produkt wirkt."),
            ("skeptic", "Ein Produktfoto erzaehlt nie die ganze Geschichte."),
        ]
    else:
        fallback = [
            ("detail_first", f"With {product_label}, the detail matters more than the polished product photo."),
            ("context_first", "In a real setting, the product makes much more sense."),
            ("skeptic", "One product photo never tells the whole story."),
        ]
    return [
        {"pattern": pattern, "hook": hook, "source": f"{category}_{archetype}"}
        for pattern, hook in hooks.get(category, fallback)
    ]


def _product_label(product_analysis: dict[str, Any], category: str, language: str) -> str:
    is_czech = _is_czech_language(language)
    is_de = is_german(language)
    name = str(product_analysis.get("product_name") or "").split("|", 1)[0].strip()
    if category == "handbag":
        if is_de:
            return "diese Tasche"
        return "tahle kabelka" if is_czech else "this bag"
    if category == "shoes":
        if is_de:
            return "diesen Schuhen"
        return "tyhle boty" if is_czech else "these shoes"
    if category == "apparel":
        if is_de:
            return "diesem Kleidungsstueck"
        return "tenhle kousek" if is_czech else "this piece"
    if is_de:
        return "diesem Produkt"
    return name or ("tenhle produkt" if is_czech else "this product")


def _handbag_capacity_supported(product_analysis: dict[str, Any]) -> bool:
    if str(product_analysis.get("likely_product_category") or "").lower() != "handbag":
        return False
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
    if str(product_analysis.get("likely_product_category") or "").lower() != "handbag":
        return "material texture"
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
