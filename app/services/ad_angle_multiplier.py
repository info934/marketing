from __future__ import annotations

from typing import Any

from app.services.localization_utils import (
    is_czech,
    is_german,
    localize_category,
    localize_phrases,
)


VERSION = "ad_angle_multiplier_v1"
SKILL_SOURCE = "local skill/ad-angle-multiplier"
ANGLE_FAMILIES = ["Pain", "Desire", "Proof", "Identity", "Contrarian", "Urgency"]


def generate(
    *,
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expand one core product idea into a distinct angle bank for creative testing."""
    ugc = ugc_strategy or {}
    config = settings or {}
    language = str(ugc.get("language") or config.get("language") or "en").lower()
    product_name = str(product_analysis.get("product_name") or "the product").strip()
    category = str(product_analysis.get("likely_product_category") or "product").strip().lower()
    category_label = localize_category(category, language)
    details = (
        product_analysis.get("ad_safe_detail_phrases_localized")
        or localize_phrases(product_analysis.get("ad_safe_detail_phrases") or [], language)
        or localize_phrases(product_analysis.get("user_provided_facts") or [], language)
        or [category_label]
    )
    detail = _clean(details[0] if details else category_label)
    secondary_detail = _clean(details[1] if len(details) > 1 else detail)
    core_idea = _clean(
        ugc.get("hook")
        or product_analysis.get("safest_creative_angle")
        or _first(product_analysis.get("safe_benefits"))
        or detail
    )
    templates = _templates(language)
    angles: list[dict[str, Any]] = []
    for family in ANGLE_FAMILIES:
        for index, template in enumerate(templates[family], start=1):
            item = {
                key: _format(value, product_name, category_label, detail, secondary_detail)
                for key, value in template.items()
            }
            angles.append(
                {
                    "id": f"{family.lower()}_{index}",
                    "angle_family": family,
                    "angle": item["angle"],
                    "hook": _limit(item["hook"], 140),
                    "motivation": item["motivation"],
                    "creative_test_hypothesis": item["hypothesis"],
                    "visual_direction": item["visual_direction"],
                    "variation_rule": item["variation_rule"],
                    "claim_safety": "Use only visible or user-supplied product facts; no invented scarcity, proof, discounts, reviews, or performance claims.",
                    "source": "ad-angle-multiplier",
                }
            )
    competitor_strategy = config.get("competitor_strategy") or ugc.get("competitor_strategy") or {}
    angles.extend(
        _competitor_inspired_angles(
            competitor_strategy=competitor_strategy,
            product_name=product_name,
            category_label=category_label,
            detail=detail,
            secondary_detail=secondary_detail,
            language=language,
        )
    )
    angles = _dedupe_angles(angles)[:15]
    return {
        "version": VERSION,
        "skill_source": SKILL_SOURCE,
        "role": "multiply winning ideas into materially distinct ad angles",
        "core_idea": _limit(core_idea, 180),
        "families": ANGLE_FAMILIES,
        "angle_count": len(angles),
        "rules": [
            "Each angle must feel new, not a minor rewrite.",
            "Every hook must stay product-specific and claim-safe.",
            "Urgency means attention urgency, not fake scarcity.",
        ],
        "angles": angles,
        "hook_bank": [
            {
                "pattern": f"angle_{item['id']}",
                "angle_family": item["angle_family"],
                "hook": item["hook"],
                "source": "ad-angle-multiplier",
            }
            for item in angles
        ],
    }


def _competitor_inspired_angles(
    *,
    competitor_strategy: dict[str, Any],
    product_name: str,
    category_label: str,
    detail: str,
    secondary_detail: str,
    language: str,
) -> list[dict[str, Any]]:
    if not isinstance(competitor_strategy, dict) or competitor_strategy.get("status") != "ready":
        return []
    extraction = competitor_strategy.get("strategy_extraction") or {}
    family_bias = extraction.get("angle_family_bias") or {}
    families = [
        family
        for family, _score in sorted(family_bias.items(), key=lambda item: item[1], reverse=True)
        if family in ANGLE_FAMILIES
    ][:3]
    if not families:
        families = [extraction.get("primary_angle_family") or "Proof"]
    patterns = extraction.get("strategic_patterns") or []
    pattern = _clean(patterns[0] if patterns else "competitor strategy pattern")
    angles = []
    for index, family in enumerate(families, start=1):
        copy = _competitor_angle_copy(
            family=family,
            product_name=product_name,
            category_label=category_label,
            detail=detail,
            secondary_detail=secondary_detail,
            language=language,
        )
        angles.append(
            {
                "id": f"competitor_{family.lower()}_{index}",
                "angle_family": family,
                "angle": copy["angle"],
                "hook": _limit(copy["hook"], 140),
                "motivation": copy["motivation"],
                "creative_test_hypothesis": copy["hypothesis"],
                "visual_direction": copy["visual_direction"],
                "variation_rule": "Adapt the competitor pattern at strategy level only; never copy text, layouts, logos, brand codes, or claims.",
                "claim_safety": "Use only visible or user-supplied product facts; competitor inputs are inspiration, not claim evidence.",
                "source": "ad-angle-multiplier/competitor-strategy",
                "competitor_pattern_basis": pattern,
                "originality_guard": (competitor_strategy.get("originality_guard") or {}).get("rules") or [],
            }
        )
    return angles


def _competitor_angle_copy(
    *,
    family: str,
    product_name: str,
    category_label: str,
    detail: str,
    secondary_detail: str,
    language: str,
) -> dict[str, str]:
    if is_czech(language):
        by_family = {
            "Pain": {
                "angle": "Competitor-inspired Pain - vlastni problemovy hook",
                "hook": f"Nez vyberes {category_label}, zkontroluj hlavne {detail}.",
                "motivation": "Prevest konkurencni problemovy vzor do vlastniho produktoveho detailu.",
                "hypothesis": "Problem-first vstup muze zvednout pozornost bez kopirovani konkurencniho claimu.",
                "visual_direction": f"Zacit realnou pochybnosti kupujiciho a ukazat {detail}.",
            },
            "Desire": {
                "angle": "Competitor-inspired Desire - vlastni lifestyle touha",
                "hook": f"{product_name} v realnem dni, ne jen jako dokonala produktova fotka.",
                "motivation": "Zachovat aspiracni rytmus, ale postavit ho na vlastnim produktu.",
                "hypothesis": "Lifestyle kontext muze zvysit predstavitelnost produktu.",
                "visual_direction": f"Ukazat {category_label} v prirozene rutine, se zretelnym detailem {detail}.",
            },
            "Proof": {
                "angle": "Competitor-inspired Proof - vlastni detailni dukaz",
                "hook": f"Detail rozhoduje: {detail}.",
                "motivation": "Konkurencni proof strukturu nahradit vlastnim overitelnym detailem.",
                "hypothesis": "Detail proof snizi nejistotu pred rozhodnutim.",
                "visual_direction": f"Close-up {detail}, potom druhy detail {secondary_detail}.",
            },
            "Identity": {
                "angle": "Competitor-inspired Identity - vlastni buyer signal",
                "hook": f"Pro lidi, co si {category_label} pred nakupem opravdu prohlidnou.",
                "motivation": "Prevest audience signal do vlastniho, neelitarskeho tonu.",
                "hypothesis": "Identity framing muze zvysit relevanci bez status claims.",
                "visual_direction": "Klidny detail-check, realne ruce a prirozene svetlo.",
            },
            "Contrarian": {
                "angle": "Competitor-inspired Contrarian - vlastni anti-hype",
                "hook": "Mene reklamniho slibu. Vic realneho detailu.",
                "motivation": "Vzit anti-hype rytmus a oprit ho o vlastni produkt.",
                "hypothesis": "Nizkopolishovy ton muze pusobit duveryhodneji.",
                "visual_direction": f"Handheld zaber, kratky detail {detail}, zadna imitace konkurencniho layoutu.",
            },
            "Urgency": {
                "angle": "Competitor-inspired Urgency - vlastni scroll-stop",
                "hook": f"Zastav se na 10 sekund u detailu: {detail}.",
                "motivation": "Pouzit rychlou pozornost, ne falesnou nedostupnost.",
                "hypothesis": "Kratky detail-check muze zlepsit zastaveni scrollu.",
                "visual_direction": "Rychly prvni zaber, potom konkretni detail produktu.",
            },
        }
    else:
        by_family = {
            "Pain": {
                "angle": "Competitor-inspired Pain - original problem hook",
                "hook": f"Before choosing a {category_label}, check {detail}.",
                "motivation": "Translate the competitor problem pattern into our own product detail.",
                "hypothesis": "A problem-first entry can increase attention without copying competitor claims.",
                "visual_direction": f"Open on a real buyer doubt, then show {detail}.",
            },
            "Desire": {
                "angle": "Competitor-inspired Desire - original lifestyle desire",
                "hook": f"{product_name} in a real day, not just a perfect product photo.",
                "motivation": "Keep the aspirational rhythm while making it specific to our product.",
                "hypothesis": "Lifestyle context can make the product easier to imagine owning.",
                "visual_direction": f"Show the {category_label} in a natural routine with clear {detail}.",
            },
            "Proof": {
                "angle": "Competitor-inspired Proof - original detail proof",
                "hook": f"The detail that matters: {detail}.",
                "motivation": "Replace competitor proof structure with our own verifiable product detail.",
                "hypothesis": "Detail proof can reduce uncertainty before purchase.",
                "visual_direction": f"Close-up on {detail}, then a second check on {secondary_detail}.",
            },
            "Identity": {
                "angle": "Competitor-inspired Identity - original buyer signal",
                "hook": f"For people who check the {category_label} before buying.",
                "motivation": "Translate audience signal into our own grounded tone.",
                "hypothesis": "Identity framing can increase relevance without status claims.",
                "visual_direction": "Calm product check with real hands and natural light.",
            },
            "Contrarian": {
                "angle": "Competitor-inspired Contrarian - original anti-hype",
                "hook": "Less ad polish. More real product detail.",
                "motivation": "Use an anti-hype rhythm grounded in our product.",
                "hypothesis": "A lower-polish tone can feel more credible than a classic ad claim.",
                "visual_direction": f"Handheld shot, short {detail} detail, no competitor layout imitation.",
            },
            "Urgency": {
                "angle": "Competitor-inspired Urgency - original scroll-stop",
                "hook": f"Pause for 10 seconds and check {detail}.",
                "motivation": "Use attention urgency, not fake scarcity.",
                "hypothesis": "A short detail-check can improve scroll-stop power.",
                "visual_direction": "Fast first frame, then one concrete product detail.",
            },
        }
    return by_family.get(family) or by_family["Proof"]


def _templates(language: str) -> dict[str, list[dict[str, str]]]:
    if is_czech(language):
        return {
            "Pain": [
                {
                    "angle": "Pain - chybejici detail",
                    "hook": "Vetsina reklam ukaze {category}. Mne zajima detail: {detail}.",
                    "motivation": "Kupujici neveri jedne dokonale produktove fotce.",
                    "hypothesis": "Pojmenovani nejistoty zvysi ochotu zastavit scroll a zkontrolovat produkt.",
                    "visual_direction": "Zacit realnym pohledem na produkt, potom detail {detail}.",
                    "variation_rule": "Testuj otazku, primou vetu a kratky detail-check.",
                },
                {
                    "angle": "Pain - vypada dobre, ale funguje v praxi?",
                    "hook": "Vypada dobre na fotce. Ale sedne do bezneho dne?",
                    "motivation": "Kupujici potrebuje videt realny kontext pouziti.",
                    "hypothesis": "Use-context snizi pochybnost, jestli produkt patri do rutiny zakaznika.",
                    "visual_direction": "Ukazat {category} v beznem prostredi, bez prehnane reklamni stylizace.",
                    "variation_rule": "Drz se prakticke sceny a jednoho viditelneho detailu.",
                },
            ],
            "Desire": [
                {
                    "angle": "Desire - kazdodenni upgrade",
                    "hook": "{product} udela obycejny moment trochu promyslenejsi.",
                    "motivation": "Kupujici chce produkt, ktery zlepsi bezny den bez velkych slibu.",
                    "hypothesis": "Aspirace v beznem kontextu muze zvysit brand fit bez luxusnich tvrzeni.",
                    "visual_direction": "Teple prirozene svetlo, produkt v ruce nebo v realne rutine.",
                    "variation_rule": "Ukaz benefit jako pocit poradku, stylu nebo jednoduchosti, ne jako status.",
                },
                {
                    "angle": "Desire - produkt, ktery zapadne",
                    "hook": "{category} pro realny den, ne jen produktovou stranku.",
                    "motivation": "Zakaznik chce videt, zda produkt zapadne do jeho stylu/rutiny.",
                    "hypothesis": "Lifestyle zaber s jasnym meritkem zlepsi predstavitelnost produktu.",
                    "visual_direction": "Produkt v prirozenem okoli s jasnym meritkem a bez rusivych props.",
                    "variation_rule": "Men prostredi, ne claim; produkt zustava presne stejny.",
                },
            ],
            "Proof": [
                {
                    "angle": "Proof - detail pred rozhodnutim",
                    "hook": "Nez se rozhodnes, pribliz si {detail}.",
                    "motivation": "Viditelny detail dava duvod verit produktu bez falesneho social proof.",
                    "hypothesis": "Detail proof bude lepsi pro retargeting a teple publikum.",
                    "visual_direction": "Makro nebo tesny detail, produkt zabira vetsinu zaberu.",
                    "variation_rule": "Pouzij jen vizualne overitelne vlastnosti.",
                },
                {
                    "angle": "Proof - druha kontrola",
                    "hook": "Druhy pohled: {secondary_detail}.",
                    "motivation": "Kupujici porovnava detaily mezi variantami.",
                    "hypothesis": "Druhy konkretni detail vytvori novy duvod ke kliknuti/review bez opakovani.",
                    "visual_direction": "Jiny uhel kamery nez hero; ukaz {secondary_detail} ve svetle bez filtru.",
                    "variation_rule": "Nekopiruj stejny detail jako C2/C3.",
                },
            ],
            "Identity": [
                {
                    "angle": "Identity - peclivy vyber",
                    "hook": "Pro lidi, co pred nakupem kontroluji detaily.",
                    "motivation": "Zakaznik se vidi jako premyslivy kupujici, ne impulzivni shopper.",
                    "hypothesis": "Identity framing zvysi relevanci bez statusovych nebo elitarskych claims.",
                    "visual_direction": "Klidny detail-check, ruce nebo telo jen jako meritko.",
                    "variation_rule": "Mluv k opatrnosti a vkusu, ne k nadrazenosti.",
                },
                {
                    "angle": "Identity - prakticky, ale vybiravy",
                    "hook": "Kdyz chces prakticky vyber, ale nechces slevit z detailu.",
                    "motivation": "Zakaznik chce kombinovat prakticnost a vizualni fit.",
                    "hypothesis": "Spojeni prakticnosti a detailu pomuze u produktu s everyday use casem.",
                    "visual_direction": "Produkt v jednoduchem outfitu/rutine; zadna dokonala stock poza.",
                    "variation_rule": "Bez slibu, ze produkt vyresi zivotni problem.",
                },
            ],
            "Contrarian": [
                {
                    "angle": "Contrarian - mene hype",
                    "hook": "Mene hype. Vic realneho detailu.",
                    "motivation": "Publikum ignoruje prehnane reklamni sliby.",
                    "hypothesis": "Nizkopolishovy ton muze pusobit duveryhodneji nez klasicky ad claim.",
                    "visual_direction": "Handheld zaber, prirozene svetlo, kratky realny detail produktu.",
                    "variation_rule": "Text musi znit jako doporuceni, ne billboard.",
                },
                {
                    "angle": "Contrarian - hero fotka nestaci",
                    "hook": "Hero fotka je hezka. Detail rozhoduje.",
                    "motivation": "Kupujici potrebuje vic nez esteticky prvni dojem.",
                    "hypothesis": "Kontrast hero vs detail zastavi lidi, kteri uz produkt rychle presli.",
                    "visual_direction": "Prejit z celeho produktu na detail {detail}.",
                    "variation_rule": "Nesrovnavej s konkurenci, jen s typickou produktovou fotkou.",
                },
            ],
            "Urgency": [
                {
                    "angle": "Urgency - nez scrollujes dal",
                    "hook": "Nez scrollujes dal, zkontroluj {detail}.",
                    "motivation": "Okamzita pozornost bez falesne scarcity.",
                    "hypothesis": "Casovy signal v prvnich sekundach zvysi stop-rate bez policy rizika.",
                    "visual_direction": "Rychly detail-check v prvnich 2 sekundach.",
                    "variation_rule": "Nepouzivej limited stock, slevy ani odpocet.",
                },
                {
                    "angle": "Urgency - desetisekundova kontrola",
                    "hook": "10 sekund na detail, ktery u {category} nechces minout.",
                    "motivation": "Kupujici chce rychlou, uzitecnou kontrolu bez dlouheho vysvetlovani.",
                    "hypothesis": "Kratsi utility framing muze zvysit dokoukani a ulozeni kreativy.",
                    "visual_direction": "Jednoduchy rychly sled: celek, meritko, detail.",
                    "variation_rule": "Zustat vecny, nepouzivat tlak na nakup.",
                },
            ],
        }
    if is_german(language):
        return {
            "Pain": [
                {
                    "angle": "Pain - fehlendes Detail",
                    "hook": "Die meisten Anzeigen zeigen {category}. Wichtig ist aber {detail}.",
                    "motivation": "Kaeufer vertrauen einem perfekten Produktfoto nicht allein.",
                    "hypothesis": "Ein konkreter Zweifel kann den Scroll-Stopp erhoehen.",
                    "visual_direction": "Erst das ganze Produkt, dann ein klarer Blick auf {detail}.",
                    "variation_rule": "Frage, direkte Aussage und kurzer Detailcheck testen.",
                },
                {
                    "angle": "Pain - schoen im Foto, brauchbar im Alltag?",
                    "hook": "Sieht gut aus. Aber passt es in einen echten Alltag?",
                    "motivation": "Kaeufer brauchen einen glaubwuerdigen Nutzungskontext.",
                    "hypothesis": "Real-use Kontext reduziert Unsicherheit ohne neue Claims.",
                    "visual_direction": "{category} in einer einfachen Alltagsszene zeigen.",
                    "variation_rule": "Praktische Szene plus ein sichtbares Detail.",
                },
            ],
            "Desire": [
                {
                    "angle": "Desire - Everyday Upgrade",
                    "hook": "{product} macht einen normalen Moment etwas durchdachter.",
                    "motivation": "Kaeufer wollen ein Produkt, das in den Alltag passt.",
                    "hypothesis": "Alltagsaspiration kann Brand Fit staerken ohne Luxusclaims.",
                    "visual_direction": "Natuerliches Licht, Produkt in Hand oder Routine.",
                    "variation_rule": "Gefuehl von Ordnung oder Einfachheit zeigen, kein Statusversprechen.",
                },
                {
                    "angle": "Desire - passt in die Routine",
                    "hook": "{category} fuer einen echten Tag, nicht nur fuer die Produktseite.",
                    "motivation": "Kaeufer wollen sich die Nutzung vorstellen.",
                    "hypothesis": "Lifestyle mit Massstab erhoeht Vorstellbarkeit.",
                    "visual_direction": "Produkt in natuerlichem Umfeld mit klarem Massstab.",
                    "variation_rule": "Umfeld variieren, Produkt nicht veraendern.",
                },
            ],
            "Proof": [
                {
                    "angle": "Proof - Detail vor Entscheidung",
                    "hook": "Vor der Entscheidung: ein naeherer Blick auf {detail}.",
                    "motivation": "Sichtbare Details schaffen Vertrauen ohne erfundene Belege.",
                    "hypothesis": "Detail proof eignet sich fuer Retargeting.",
                    "visual_direction": "Makro oder enger Detailshot, Produkt dominiert den Frame.",
                    "variation_rule": "Nur sichtbare oder angegebene Fakten verwenden.",
                },
                {
                    "angle": "Proof - zweiter Check",
                    "hook": "Zweiter Blick: {secondary_detail}.",
                    "motivation": "Kaeufer vergleichen konkrete Details.",
                    "hypothesis": "Ein zweites Detail liefert einen neuen Review-Grund.",
                    "visual_direction": "Anderer Kamerawinkel als Hero; {secondary_detail} klar zeigen.",
                    "variation_rule": "Nicht denselben Detailgrund wiederholen.",
                },
            ],
            "Identity": [
                {
                    "angle": "Identity - bewusste Auswahl",
                    "hook": "Fuer Menschen, die vor dem Kauf Details pruefen.",
                    "motivation": "Der Kaeufer sieht sich als bewusster Entscheider.",
                    "hypothesis": "Identity framing kann Relevanz ohne Statusclaims erhoehen.",
                    "visual_direction": "Ruhiger Detailcheck, Haende oder Koerper nur als Massstab.",
                    "variation_rule": "Sorgfalt ansprechen, nicht Ueberlegenheit.",
                },
                {
                    "angle": "Identity - praktisch, aber waehlerisch",
                    "hook": "Wenn es praktisch sein soll, aber der Detailblick zaehlt.",
                    "motivation": "Kaeufer verbinden Alltagstauglichkeit mit visueller Auswahl.",
                    "hypothesis": "Practical plus detail kann Everyday-Produkte staerken.",
                    "visual_direction": "Produkt in einfacher Routine, keine Stock-Pose.",
                    "variation_rule": "Kein Versprechen, dass das Produkt ein Lebensproblem loest.",
                },
            ],
            "Contrarian": [
                {
                    "angle": "Contrarian - weniger Hype",
                    "hook": "Weniger Hype. Mehr echter Produktblick.",
                    "motivation": "Publikum ignoriert uebertriebene Werbesprache.",
                    "hypothesis": "Ein ruhiger Ton kann glaubwuerdiger wirken.",
                    "visual_direction": "Handheld, natuerliches Licht, kurzer echter Detailblick.",
                    "variation_rule": "Wie Empfehlung, nicht wie Billboard schreiben.",
                },
                {
                    "angle": "Contrarian - Hero Foto reicht nicht",
                    "hook": "Das Hero Foto ist schoen. Der Detailblick entscheidet.",
                    "motivation": "Kaeufer brauchen mehr als einen ersten Eindruck.",
                    "hypothesis": "Hero-vs-Detail Kontrast kann uebersprungene Nutzer zurueckholen.",
                    "visual_direction": "Vom Gesamtprodukt zum Detail {detail} wechseln.",
                    "variation_rule": "Nicht mit Wettbewerbern vergleichen.",
                },
            ],
            "Urgency": [
                {
                    "angle": "Urgency - bevor du weiter scrollst",
                    "hook": "Bevor du weiter scrollst: pruefe {detail}.",
                    "motivation": "Sofortige Aufmerksamkeit ohne falsche Knappheit.",
                    "hypothesis": "Ein frueher Zeitsignal-Hook kann Stop-Rate verbessern.",
                    "visual_direction": "Detailcheck in den ersten zwei Sekunden.",
                    "variation_rule": "Keine Limited-Stock-, Rabatt- oder Countdown-Sprache.",
                },
                {
                    "angle": "Urgency - 10 Sekunden Check",
                    "hook": "10 Sekunden fuer ein Detail, das man bei {category} nicht uebersehen sollte.",
                    "motivation": "Kaeufer wollen schnelle nuetzliche Pruefung.",
                    "hypothesis": "Kurzer Utility-Frame kann Completion verbessern.",
                    "visual_direction": "Schnelle Sequenz: Gesamtbild, Massstab, Detail.",
                    "variation_rule": "Sachlich bleiben, kein Kaufdruck.",
                },
            ],
        }
    return {
        "Pain": [
            {
                "angle": "Pain - missing detail",
                "hook": "Most {category} ads skip the detail you actually need to see.",
                "motivation": "The buyer does not fully trust a polished product photo.",
                "hypothesis": "Naming the missing-detail problem should increase scroll-stop intent.",
                "visual_direction": "Start with the product, then move into a close check of {detail}.",
                "variation_rule": "Test question, direct statement, and short detail-check versions.",
            },
            {
                "angle": "Pain - looks good, but fits real life?",
                "hook": "It looks good in a photo. But does it fit a real day?",
                "motivation": "The buyer needs use-context before they can picture ownership.",
                "hypothesis": "A believable use-context should reduce purchase uncertainty.",
                "visual_direction": "Show {category} in a simple everyday scene with realistic scale.",
                "variation_rule": "Lead with practical doubt, then resolve with one visible product cue.",
            },
        ],
        "Desire": [
            {
                "angle": "Desire - everyday upgrade",
                "hook": "{product} makes an ordinary moment feel more considered.",
                "motivation": "The buyer wants a small everyday upgrade without exaggerated claims.",
                "hypothesis": "Everyday aspiration should improve brand fit without status-signaling.",
                "visual_direction": "Natural light, product in hand or in a real routine.",
                "variation_rule": "Show ease, order, or style without implying luxury or superiority.",
            },
            {
                "angle": "Desire - fits the routine",
                "hook": "A {category} for a real day, not just a product page.",
                "motivation": "The buyer wants to imagine the product in their own routine.",
                "hypothesis": "Lifestyle context with scale should make the product easier to picture.",
                "visual_direction": "Product in a natural setting with one clear scale cue.",
                "variation_rule": "Change the context, not the product facts or appearance.",
            },
        ],
        "Proof": [
            {
                "angle": "Proof - detail before decision",
                "hook": "Before you decide, zoom in on {detail}.",
                "motivation": "A visible detail gives a reason to trust without fake social proof.",
                "hypothesis": "Detail proof should work well for retargeting and warm audiences.",
                "visual_direction": "Macro or tight close-up; product fills most of the frame.",
                "variation_rule": "Use only visible or user-supplied attributes.",
            },
            {
                "angle": "Proof - second check",
                "hook": "Second look: {secondary_detail}.",
                "motivation": "The buyer compares concrete cues before committing.",
                "hypothesis": "A second proof point creates a materially new ad reason.",
                "visual_direction": "Different camera angle from the hero; show {secondary_detail} clearly.",
                "variation_rule": "Do not repeat the same proof cue used in the hero static.",
            },
        ],
        "Identity": [
            {
                "angle": "Identity - careful buyer",
                "hook": "For people who check the details before they buy.",
                "motivation": "The buyer sees themselves as careful, not impulsive.",
                "hypothesis": "Identity framing should improve relevance without superiority claims.",
                "visual_direction": "Calm detail-check, hands or body used only as scale context.",
                "variation_rule": "Speak to careful taste, not status or exclusivity.",
            },
            {
                "angle": "Identity - practical but picky",
                "hook": "When you want practical, but still care about the details.",
                "motivation": "The buyer wants practical use and visual fit together.",
                "hypothesis": "Combining practical and detail language should help everyday products.",
                "visual_direction": "Simple routine or outfit context; no perfect stock-photo pose.",
                "variation_rule": "Avoid claiming the product solves a life problem.",
            },
        ],
        "Contrarian": [
            {
                "angle": "Contrarian - less hype",
                "hook": "Less hype. More real product detail.",
                "motivation": "The audience filters out overproduced ad claims.",
                "hypothesis": "A low-polish tone can feel more trustworthy than a classic ad claim.",
                "visual_direction": "Handheld-feeling shot, natural light, short real product check.",
                "variation_rule": "Make it sound like a recommendation, not a billboard.",
            },
            {
                "angle": "Contrarian - hero photo is not enough",
                "hook": "The hero photo is nice. The detail is what matters.",
                "motivation": "The buyer needs more than a first visual impression.",
                "hypothesis": "Hero-vs-detail contrast should re-engage people who skipped the product.",
                "visual_direction": "Move from full product to {detail}.",
                "variation_rule": "Compare viewing context only, never competitor quality.",
            },
        ],
        "Urgency": [
            {
                "angle": "Urgency - before you scroll",
                "hook": "Before you scroll, check {detail}.",
                "motivation": "Immediate attention without fake scarcity.",
                "hypothesis": "A time-sensitive attention cue should improve the first two seconds.",
                "visual_direction": "Fast detail-check inside the opening two seconds.",
                "variation_rule": "No limited-stock, discount, deadline, or countdown wording.",
            },
            {
                "angle": "Urgency - 10-second check",
                "hook": "A 10-second detail check for a {category} you do not want to miss.",
                "motivation": "The buyer wants a quick useful review, not a long pitch.",
                "hypothesis": "Short utility framing should improve completion and save intent.",
                "visual_direction": "Quick sequence: full product, scale, detail.",
                "variation_rule": "Stay useful and factual; avoid purchase pressure.",
            },
        ],
    }


def _format(value: str, product: str, category: str, detail: str, secondary_detail: str) -> str:
    return _clean(
        value.format(
            product=product,
            category=category,
            detail=detail,
            secondary_detail=secondary_detail,
        )
    )


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _first(values: Any) -> Any:
    if isinstance(values, (list, tuple)) and values:
        return values[0]
    return ""


def _limit(value: Any, limit: int) -> str:
    text = _clean(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip(" ,.;:-") + "..."


def _dedupe_angles(angles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    seen_hooks: set[str] = set()
    for item in angles:
        hook_key = str(item.get("hook") or "").lower()
        if not hook_key or hook_key in seen_hooks:
            continue
        seen_hooks.add(hook_key)
        result.append(item)
    return result
