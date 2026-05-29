from __future__ import annotations

from app.services import (
    ad_angle_multiplier,
    ad_angle_selector,
    ads_creative_set_agent,
    chat_brief_parser_agent,
    compliance_guard,
    competitor_strategy_agent,
    content_prompt_engineer_agent,
    product_fidelity_guard,
    prompt_defaults,
    product_intake_agent,
    quality_scorer,
    scenario_integrity_guard,
    structured_prompt_v2,
    ugc_agent,
)


def test_agents_return_safe_shapes_for_minimal_input(tmp_path):
    image_path = tmp_path / "product.jpg"
    image_path.write_bytes(b"fake-image")
    input_data = {"product_name": "Everyday Tote", "product_info": "Roomy daily bag with clean minimal design"}
    avatar = {"name": "Default Creator", "style": "natural creator"}
    settings = {"platform": "tiktok", "language": "en", "market": "US", "video_length": 15}

    product_analysis = product_intake_agent.analyse(input_data, image_path)
    ugc_strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis, ugc_strategy, avatar, str(image_path), settings
    )
    fidelity = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)
    compliance = compliance_guard.check(product_analysis, ugc_strategy, prompt_package)
    quality = quality_scorer.score(product_analysis, ugc_strategy, prompt_package, fidelity, compliance)

    assert product_analysis["agent"] == "Product Intake Agent"
    assert ugc_strategy["hook"]
    assert "strict visual reference" in prompt_package["seedance_video_prompt"]
    assert "avatar" in prompt_package["seedance_video_prompt"].lower()
    assert "user's own ai avatar" in prompt_package["seedance_video_prompt"].lower()
    assert prompt_package["seedance_payload"]["avatar_reference_mode"] == "prompt_only_not_image_input"
    assert prompt_package["structured_scene_prompt"]["variants"][0]["scenes"][0]["purpose"] == "hook"
    assert fidelity["product_fidelity_status"] == "pass"
    assert compliance["compliance_status"] == "pass"
    assert quality["export_status"] in {"approved", "warning"}


def test_ad_angle_multiplier_generates_distinct_family_bank():
    product_analysis = {
        "product_name": "BELLA | LEATHER TOTE BAG",
        "likely_product_category": "handbag",
        "ad_safe_detail_phrases": ["leather texture", "stitching", "interior lining"],
        "safest_creative_angle": "Show visible handbag construction",
    }
    result = ad_angle_multiplier.generate(
        product_analysis=product_analysis,
        ugc_strategy={"language": "en", "hook": "Finally, a tote that looks elegant but fits daily essentials."},
        settings={"market": "UK"},
    )

    families = {item["angle_family"] for item in result["angles"]}
    hooks = [item["hook"] for item in result["angles"]]
    assert result["version"] == "ad_angle_multiplier_v1"
    assert result["angle_count"] >= 10
    assert families == {"Pain", "Desire", "Proof", "Identity", "Contrarian", "Urgency"}
    assert len(hooks) == len(set(hooks))
    assert all(item["source"] == "ad-angle-multiplier" for item in result["angles"])
    assert "fake scarcity" in " ".join(result["rules"]).lower()


def test_competitor_strategy_chat_extracts_temporary_strategy():
    result = competitor_strategy_agent.analyze(
        enabled=True,
        competitor_name="Example Rival",
        competitor_url="https://example-rival.test",
        competitor_chat_brief=(
            "They open with a strong hook about checking details before buying.\n"
            "Visuals: close-up leather texture, mirror lifestyle shot, clear shop CTA."
        ),
        competitor_screenshot_notes="Screenshot shows close-up stitching and natural UGC home lighting.",
        screenshot_assets=[{"filename": "rival.png", "path": "output/rival.png"}],
        product_analysis={
            "product_name": "BELLA | LEATHER TOTE BAG",
            "likely_product_category": "handbag",
        },
        settings={"language": "en"},
    )

    assert result["version"] == "competitor_strategy_chat_v1"
    assert result["status"] == "ready"
    assert "strategic patterns" in result["system_prompt"].lower()
    assert result["temporary_context_only"] is True
    assert result["selector_bias"]["families"]
    assert "Example Rival" in result["originality_guard"]["do_not_copy_terms"]
    assert "copy exact competitor wording" in " ".join(result["originality_guard"]["rules"]).lower()


def test_chat_brief_parser_builds_structured_campaign_draft_without_api_key():
    result = chat_brief_parser_agent.parse(
        {
            "chatBriefItems": [
                {
                    "id": "p1",
                    "text": "BELLA Leather Tote\nStructured handbag for UK Meta, English. Video + statiky.\nhttps://example.com/bella.jpg",
                    "file_count": 1,
                    "file_names": ["bella.png"],
                    "applied_as": ["product"],
                },
                {
                    "id": "c1",
                    "text": "Competitor: Rival Bags. Their ads use close-up stitching and mirror outfit shots. https://rival.example/ad",
                    "file_count": 1,
                    "file_names": ["rival.png"],
                    "applied_as": ["competitor"],
                },
            ],
            "current_form": {},
        },
        api_key="",
        model="openai/gpt-5.4-mini",
    )

    draft = result["campaign_draft"]
    assert result["version"] == "chat_brief_parser_v1"
    assert result["status"] == "deterministic"
    assert draft["product_name"] == "BELLA Leather Tote"
    assert draft["product_reference_url"] == "https://example.com/bella.jpg"
    assert draft["competitor_strategy_enabled"] is True
    assert draft["competitor_url"] == "https://rival.example/ad"
    assert draft["platform"] == "meta"
    assert draft["market"] == "UK"
    assert draft["language"] == "en"
    assert draft["generation_mode"] == "both"
    assert {item["role"] for item in result["attachment_roles"]} == {"product", "competitor"}


def test_chat_brief_parser_does_not_treat_docs_url_as_product_image_reference():
    result = chat_brief_parser_agent.parse(
        {
            "chatBriefItems": [
                {
                    "id": "p1",
                    "text": (
                        "Sklenice s potiskem\n"
                        "Produktovy brief a poznamky.\n"
                        "https://openrouter.ai/docs/guides/overview/multimodal/video-generation"
                    ),
                    "file_count": 0,
                    "file_names": [],
                    "applied_as": ["product"],
                },
            ],
            "current_form": {},
        },
        api_key="",
        model="openai/gpt-5.4-mini",
    )

    draft = result["campaign_draft"]
    assert draft["product_reference_url"] == ""
    assert "Produktovy brief" in draft["product_info"]


def test_chat_brief_parser_extracts_labeled_product_name_url_description_and_image():
    result = chat_brief_parser_agent.parse(
        {
            "chatBriefItems": [
                {
                    "id": "p1",
                    "text": (
                        "Nazev produktu: BELLA Leather Tote\n"
                        "Product URL: https://shop.example/products/bella-tote\n"
                        "Obrazek produktu: https://cdn.example.com/bella-tote.webp\n"
                        "Popis: Structured tote bag for daily essentials.\n"
                        "Material: smooth black leather look, clean stitching."
                    ),
                    "file_count": 0,
                    "file_names": [],
                    "applied_as": ["product"],
                },
            ],
            "current_form": {},
        },
        api_key="",
        model="openai/gpt-5.4-mini",
    )

    draft = result["campaign_draft"]
    assert draft["product_name"] == "BELLA Leather Tote"
    assert draft["product_reference_url"] == "https://cdn.example.com/bella-tote.webp"
    assert "Structured tote bag" in draft["product_info"]
    assert "smooth black leather" in draft["product_info"]
    assert "Product URL: https://shop.example/products/bella-tote" in draft["product_info"]


def test_chat_brief_parser_keeps_non_image_product_url_out_of_video_reference():
    result = chat_brief_parser_agent.parse(
        {
            "chatBriefItems": [
                {
                    "id": "p1",
                    "text": (
                        "Produkt: MIA Sneakers URL: https://shop.example/products/mia-sneakers "
                        "Popis: Lightweight everyday sneakers with a clean white silhouette."
                    ),
                    "file_count": 0,
                    "file_names": [],
                    "applied_as": ["product"],
                },
            ],
            "current_form": {},
        },
        api_key="",
        model="openai/gpt-5.4-mini",
    )

    draft = result["campaign_draft"]
    assert draft["product_name"] == "MIA Sneakers"
    assert draft["product_reference_url"] == ""
    assert "Lightweight everyday sneakers" in draft["product_info"]
    assert "Product URL: https://shop.example/products/mia-sneakers" in draft["product_info"]
    assert draft["product_info"].count("https://shop.example/products/mia-sneakers") == 1


def test_chat_brief_parser_ai_merge_canonicalizes_product_page_url():
    merged = chat_brief_parser_agent._merge_with_deterministic(
        {
            "campaign_draft": {
                "product_name": "MIA Sneakers",
                "product_info": (
                    "Lightweight everyday sneakers https://shop.example/products/mia-sneakers "
                    "Product URL: https://shop.example/products/mia-sneakers"
                ),
                "product_reference_url": "https://shop.example/products/mia-sneakers",
            },
            "attachment_roles": [],
            "warnings": [],
        },
        {
            "campaign_draft": {
                "product_name": "MIA Sneakers",
                "product_info": "Lightweight everyday sneakers",
                "product_reference_url": "",
            },
            "attachment_roles": [],
            "warnings": [],
        },
    )

    draft = merged["campaign_draft"]
    assert draft["product_reference_url"] == ""
    assert draft["product_info"].count("https://shop.example/products/mia-sneakers") == 1
    assert "Product URL: https://shop.example/products/mia-sneakers" in draft["product_info"]


def test_ad_angle_multiplier_adds_competitor_inspired_angles_when_supplied():
    product_analysis = {
        "product_name": "BELLA | LEATHER TOTE BAG",
        "likely_product_category": "handbag",
        "ad_safe_detail_phrases": ["leather texture", "stitching", "interior lining"],
    }
    competitor_strategy = competitor_strategy_agent.analyze(
        enabled=True,
        competitor_name="Rival",
        competitor_chat_brief="Strong hook, close-up proof details, lifestyle mirror shot, shop today CTA.",
        product_analysis=product_analysis,
        settings={"language": "en"},
    )
    result = ad_angle_multiplier.generate(
        product_analysis=product_analysis,
        ugc_strategy={"language": "en", "competitor_strategy": competitor_strategy},
        settings={"competitor_strategy": competitor_strategy},
    )

    competitor_angles = [
        item for item in result["angles"] if item["source"] == "ad-angle-multiplier/competitor-strategy"
    ]
    assert competitor_angles
    assert all("originality_guard" in item for item in competitor_angles)


def test_ad_angle_selector_uses_competitor_strategy_as_weak_bias():
    multiplier = {
        "angles": [
            {
                "id": "proof_1",
                "angle_family": "Proof",
                "angle": "Proof - detail before decision",
                "hook": "The detail that matters: leather texture.",
                "visual_direction": "Close-up proof detail.",
                "creative_test_hypothesis": "Proof detail wins.",
            },
            {
                "id": "identity_1",
                "angle_family": "Identity",
                "angle": "Identity - careful buyer",
                "hook": "For people who check details",
                "visual_direction": "Careful buyer detail check",
                "creative_test_hypothesis": "Identity test",
            },
        ],
    }
    competitor_strategy = competitor_strategy_agent.analyze(
        enabled=True,
        competitor_name="Rival",
        competitor_chat_brief="Close-up proof details, texture demo, stitching proof, shop CTA.",
        product_analysis={"product_name": "BELLA", "likely_product_category": "handbag"},
        settings={},
    )
    selector = ad_angle_selector.select(
        angle_multiplier=multiplier,
        product_analysis={"likely_product_category": "handbag"},
        ugc_strategy={"competitor_strategy": competitor_strategy},
        settings={"competitor_strategy": competitor_strategy},
    )

    assert selector["competitor_bias_used"] is True
    assert selector["competitor_bias_summary"]["status"] == "ready"
    assert selector["slot_selection"]["C4"]["selected_family"] == "Proof"
    assert selector["slot_selection"]["C4"]["score_breakdown"]["competitor_bias_score"] > 0


def test_ad_angle_selector_uses_memory_over_role_prior_when_confident():
    multiplier = {
        "angles": [
            {
                "id": "desire_1",
                "angle_family": "Desire",
                "angle": "Desire - everyday upgrade",
                "hook": "Everyday upgrade",
                "visual_direction": "Lifestyle context",
                "creative_test_hypothesis": "Desire test",
            },
            {
                "id": "proof_1",
                "angle_family": "Proof",
                "angle": "Proof - detail before decision",
                "hook": "Before you decide, zoom in on leather texture.",
                "visual_direction": "Macro close-up of leather texture and stitching",
                "creative_test_hypothesis": "Proof detail wins",
            },
            {
                "id": "identity_1",
                "angle_family": "Identity",
                "angle": "Identity - careful buyer",
                "hook": "For people who check details",
                "visual_direction": "Careful buyer detail check",
                "creative_test_hypothesis": "Identity test",
            },
        ],
    }
    selector = ad_angle_selector.select(
        angle_multiplier=multiplier,
        product_analysis={"likely_product_category": "handbag"},
        ugc_strategy={
            "platform": "meta",
            "market": "UK",
            "creative_memory_rag": {
                "winning_patterns": ["angle:DETAIL_PROOF", "leather texture", "close-up"],
                "avoid_patterns": ["angle:PRODUCT_HERO"],
                "learning_layer": {
                    "confidence": "high",
                    "winner_count": 6,
                    "rejected_count": 2,
                    "best_historical_creatives": [
                        {"angle": "DETAIL_PROOF", "tags": ["close-up", "texture"]}
                    ],
                },
            },
        },
        settings={},
    )

    assert selector["version"] == "ad_angle_selector_v1"
    assert selector["memory_used"] is True
    assert selector["slot_selection"]["C2"]["selected_family"] == "Proof"
    assert selector["slot_selection"]["C2"]["score_breakdown"]["memory_match_score"] > 0
    assert "memory match" in selector["slot_selection"]["C2"]["selection_reason"]


def test_product_intake_flags_unsupported_medical_claims(tmp_path):
    image_path = tmp_path / "shoe.jpg"
    image_path.write_bytes(b"fake-image")
    result = product_intake_agent.analyse(
        {"product_name": "Walking Shoes", "product_info": "Orthopedic shoes that cure foot pain"},
        image_path,
    )

    assert result["likely_product_category"] == "shoes"
    assert result["unsupported_claims"]


def test_compliance_ignores_negated_internal_medical_safety_language():
    product_analysis = {
        "unsupported_claims": [],
        "possible_trademark_or_counterfeit_risks": [],
        "likely_product_category": "shoes",
    }
    ugc_strategy = {
        "market": "UK",
        "voiceover": "A clean everyday trainer with a simple side profile.",
        "avatar_direction": {"personal_use_claims_allowed": False},
        "audience_research": {
            "rationale": "wants shoes that look easy to wear without needing medical or comfort claims"
        },
    }
    prompt_package = {
        "seedance_video_prompt": "Show styling and visible construction only, no medical or comfort labels, no treatment claims."
    }

    result = compliance_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["compliance_status"] == "pass"
    assert result["unsupported_claims"] == []


def test_compliance_ignores_instructional_treat_language_but_blocks_medical_treat_claims():
    product_analysis = {
        "unsupported_claims": [],
        "possible_trademark_or_counterfeit_risks": [],
        "likely_product_category": "apparel",
    }
    ugc_strategy = {
        "market": "UK",
        "voiceover": "A clean look at the garment cut and visible finish.",
        "avatar_direction": {"personal_use_claims_allowed": False},
        "user_scenario_lock": {
            "rules": [
                "treat product names, colours, and garment specifics inside the note as examples only"
            ]
        },
    }
    prompt_package = {
        "seedance_video_prompt": (
            "If input reference image 2 is present, do not treat any object, room, "
            "clothing detail, or prop in the avatar image as the product."
        )
    }

    result = compliance_guard.check(product_analysis, ugc_strategy, prompt_package)
    assert result["compliance_status"] == "pass"
    assert "treat" not in result["unsupported_claims"]

    medical_result = compliance_guard.check(
        product_analysis,
        {
            **ugc_strategy,
            "voiceover": "These shoes treat foot pain during long walks.",
        },
        {"seedance_video_prompt": "These shoes treat foot pain during long walks."},
    )
    assert medical_result["compliance_status"] == "fail"
    assert "treat" in medical_result["unsupported_claims"]


def test_compliance_ignores_negated_internal_scarcity_safety_language():
    product_analysis = {
        "unsupported_claims": [],
        "possible_trademark_or_counterfeit_risks": [],
        "likely_product_category": "home",
    }
    ugc_strategy = {
        "market": "CZ",
        "voiceover": "KrĂˇtkĂ˝ pohled na plastovou sklenici s vlastnĂ­m popisem.",
        "avatar_direction": {"personal_use_claims_allowed": False},
        "ad_angle_multiplier": {
            "angles": [
                {
                    "angle_family": "Urgency",
                    "variation_rule": "Nepouzivej limited stock, slevy ani odpocet.",
                    "motivation": "Okamzita pozornost bez falesne scarcity.",
                }
            ]
        },
    }
    prompt_package = {
        "seedance_video_prompt": "Never invent limited stock, free delivery, discounts, prices, or availability unless supplied by the input.",
        "negative_prompt": "Do not create fake scarcity or discount claims.",
    }

    result = compliance_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["compliance_status"] == "pass"
    assert result["unsupported_claims"] == []


def test_compliance_warns_instead_of_blocking_raw_designer_note_when_output_is_safe():
    product_analysis = {
        "unsupported_claims": [],
        "possible_trademark_or_counterfeit_risks": ["possible unverified brand or luxury implication"],
        "likely_product_category": "handbag",
    }
    ugc_strategy = {
        "market": "UK",
        "voiceover": "A clean everyday tote with a simple shape and visible carry scale.",
        "avatar_direction": {"personal_use_claims_allowed": False},
    }
    prompt_package = {
        "seedance_video_prompt": (
            "Show the exact tote from the product reference. "
            "Spoken line: VIVIENNE Tote: elegant, practical, everyday."
        )
    }

    result = compliance_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["compliance_status"] == "warning"
    assert result["trademark_risks"] == []
    assert result["trademark_warnings"] == ["possible unverified brand or luxury implication"]


def test_compliance_blocks_generated_designer_or_luxury_claims():
    product_analysis = {
        "unsupported_claims": [],
        "possible_trademark_or_counterfeit_risks": ["possible unverified brand or luxury implication"],
        "likely_product_category": "handbag",
    }
    ugc_strategy = {
        "market": "UK",
        "voiceover": "It looks like a designer handbag without the designer price.",
        "avatar_direction": {"personal_use_claims_allowed": False},
    }
    prompt_package = {
        "seedance_video_prompt": "Create a creator video that calls this a luxury designer tote."
    }

    result = compliance_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["compliance_status"] == "fail"
    assert "designer handbag" in result["trademark_risks"]
    assert "luxury designer" in result["trademark_risks"]


def test_ugc_strategy_uses_natural_handbag_voiceover(tmp_path):
    image_path = tmp_path / "bag.jpg"
    image_path.write_bytes(b"fake-image")
    product_analysis = product_intake_agent.analyse(
        {
            "product_name": "BELLA | LEATHER TOTE BAG",
            "product_info": (
                "Crafted from genuine two-layer cowhide leather with a spacious waterproof interior "
                "and clean minimalist shape for work, errands, and travel."
            ),
        },
        image_path,
    )
    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Avatar1", "style": "natural creator"},
        {"platform": "meta", "language": "en", "market": "UK", "video_length": 15},
    )

    assert product_analysis["likely_product_category"] == "handbag"
    assert product_analysis["known_product_facts"]["material"] == "two-layer cowhide leather"
    assert "two-layer cowhide leather" in product_analysis["user_provided_facts"]
    assert "comparing handbag" not in strategy["voiceover"]
    assert "It is shown" not in strategy["voiceover"]
    assert "I'd show" not in strategy["voiceover"]
    assert "I'd get close" not in strategy["voiceover"]
    assert "angle:" not in strategy["voiceover"].lower()
    assert "Finally, a tote" in strategy["hook"]
    assert "tablet, bottle, wallet, phone, keys, and makeup pouch" in strategy["voiceover"]
    assert "leather texture, stitching, handles, and lining" in strategy["voiceover"]
    assert "BELLA Leather Tote: elegant, spacious, everyday" in strategy["voiceover"]
    assert "British English" in strategy["voice_profile"]
    assert "British accent" in strategy["language_instruction"]
    assert strategy["on_screen_text"][0] == strategy["subtitles"][0]
    assert "Fits daily essentials" in strategy["on_screen_text"]
    assert strategy["category_video_recipe"]["handbag_capacity_supported"] is True
    assert strategy["ugc_prompt_skill"]["source"] == "local skill/claude-arcads creative rules; Arcads API ignored"
    assert strategy["ugc_prompt_skill"]["template_id"] == "talking_head_product_check"
    assert strategy["category_video_recipe"]["ugc_template"] == "talking_head_product_check"
    assert all(len(subtitle.split()) <= 8 for subtitle in strategy["subtitles"])
    assert strategy["subtitles"][0] != strategy["scene_by_scene_script"][0]["voiceover"]
    assert "click" not in " ".join(strategy["subtitles"]).lower()
    assert "same body-to-bag scale" in " ".join(scene["visual"] for scene in strategy["scene_by_scene_script"])
    assert "water bottle" in " ".join(scene["visual"] for scene in strategy["scene_by_scene_script"])
    assert "closing overlay" not in " ".join(scene["visual"] for scene in strategy["scene_by_scene_script"]).lower()
    assert "plain spoken product-name closing recap" in " ".join(scene["visual"] for scene in strategy["scene_by_scene_script"])

    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        {"name": "Avatar1", "style": "natural creator"},
        str(image_path),
        {"platform": "meta", "language": "en", "market": "UK", "video_length": 15},
    )
    fidelity = product_fidelity_guard.check(product_analysis, strategy, prompt_package)
    assert "British English creator voice" in prompt_package["seedance_video_prompt"]
    assert "British English creator voice" in prompt_package["voiceover_tts_prompt"]
    assert "Handbag and tote bag preset" in prompt_package["category_prompt_directive"]
    assert "Handbag size lock" in prompt_package["product_fidelity_instruction"]
    assert "same bag size" in prompt_package["seedance_video_prompt"]
    assert "No generated text contract" in prompt_package["seedance_video_prompt"]
    assert "Creator prompt skill guidance" in prompt_package["seedance_video_prompt"]
    assert "Talking head product-check" in prompt_package["seedance_video_prompt"]
    assert "Arcads API" in prompt_package["seedance_video_prompt"]
    assert "Render no generated text" in prompt_package["subtitle_contract"]
    assert "post-production" in prompt_package["subtitle_contract"]
    assert "all captions should be added later in post-production" in prompt_package["seedance_video_prompt"].lower()
    assert "Category prompt:" in prompt_package["seedance_video_prompt"]
    assert fidelity["product_fidelity_status"] == "pass"


def test_ugc_video_prompt_locks_verified_material_in_every_scene(tmp_path):
    image_path = tmp_path / "cup.jpg"
    image_path.write_bytes(b"fake-image")
    product_analysis = product_intake_agent.analyse(
        {
            "product_name": "Personalised Plastic Cup",
            "product_info": "Transparent plastic cup with custom name inscription, 460 ml",
        },
        image_path,
    )
    avatar = {"name": "Creator", "style": "natural creator"}
    settings = {"platform": "meta", "language": "en", "market": "UK", "video_length": 15}
    strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        avatar,
        str(image_path),
        settings,
    )
    prompt_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=prompt_package,
        product_analysis=product_analysis,
        ugc_strategy=strategy,
        settings=settings,
    )

    prompt = prompt_package["seedance_video_prompt"].lower()
    assert "material fidelity hard lock" in prompt
    assert "verified material=plastic" in prompt
    assert "product not modified" in prompt
    assert "not rematerialized" in prompt
    assert "do not make the product look like: leather" in prompt


def test_product_fidelity_guard_blocks_material_substitution_for_ugc():
    product_analysis = {
        "product_image_path": "https://example.com/cup.png",
        "likely_product_category": "home",
        "known_product_facts": {"material": "plastic", "color": "transparent"},
        "user_provided_facts": ["transparent plastic cup"],
        "ad_safe_detail_phrases": ["custom name inscription"],
    }
    ugc_strategy = {"market": "UK", "voiceover": "A quick look at the cup."}
    prompt_package = {
        "product_fidelity_instruction": (
            "Use the product image reference at https://example.com/cup.png as the strict visual reference. "
            f"{prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK} "
            "Product not modified, not restyled, not recolored, not rebranded, not rematerialized."
        ),
        "seedance_payload": {"product_image_path": "https://example.com/cup.png"},
        "negative_prompt": "Do not redesign the product. Do not change material.",
        "structured_scene_prompt": {
            "variants": [
                {
                    "scenes": [
                        {
                            "scene_summary": "creator holds the cup, make it look like glass with premium shine",
                            "fidelity": "strict visual reference",
                        }
                    ]
                }
            ]
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "fail"
    assert any("glass" in detail for detail in result["changed_or_invented_details"])


def test_product_category_override_takes_priority(tmp_path):
    image_path = tmp_path / "product.jpg"
    image_path.write_bytes(b"fake-image")

    result = product_intake_agent.analyse(
        {
            "product_name": "Minimal Product",
            "product_info": "Simple black item with clean shape",
            "product_category": "apparel",
        },
        image_path,
    )

    assert result["likely_product_category"] == "apparel"
    assert result["product_category_source"] == "user_selected"
    assert "confirmed_product_category" not in result["missing_information"]


def test_product_notes_are_localized_for_german_campaign(tmp_path):
    image_path = tmp_path / "glass.jpg"
    image_path.write_bytes(b"fake-image")
    product_analysis = product_intake_agent.analyse(
        {
            "product_name": "Nerozbitna plastova sklenice s vlastnim napisem",
            "product_info": "Nerozbitna plastova sklenice s vlastnim napisem 460 ml",
            "language": "de",
            "market": "DE",
        },
        image_path,
    )

    assert product_analysis["likely_product_category"] == "home"
    assert "custom name inscription" in product_analysis["user_provided_facts"]
    assert "personalisierter Namensaufdruck" in product_analysis["user_provided_facts_localized"]
    assert "460 ml Fassungsvermoegen" in product_analysis["ad_safe_detail_phrases_localized"]

    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Simana", "style": "natural creator", "voice": "warm German voice"},
        {"platform": "meta", "language": "de", "market": "DE", "video_length": 15},
    )

    assert strategy["customer_language_name"] == "German"
    assert "Aus der Naehe" in strategy["voiceover"]
    assert "personalisierter Namensaufdruck" in strategy["voiceover"]
    assert "Here, I'd" not in strategy["voiceover"]
    assert "wuerde ich" not in strategy["voiceover"].lower()
    assert "Check the detail" not in " ".join(strategy["on_screen_text"])


def test_czech_video_prompt_stays_czech_and_prioritizes_product_reference(tmp_path):
    image_path = tmp_path / "glass.jpg"
    image_path.write_bytes(b"fake-image")
    product_analysis = product_intake_agent.analyse(
        {
            "product_name": "Plastova sklenice s vlastnim napisem",
            "product_info": "Plastova sklenice s vlastnim napisem 460 ml",
            "language": "cs",
            "market": "CZ",
        },
        image_path,
    )
    avatar = {
        "name": "My AI avatar",
        "style": "natural creator",
        "voice": "natural British English creator voice, relaxed and conversational",
        "image_url": "https://example.com/avatar.jpg",
        "own_person_confirmed": True,
    }
    settings = {
        "platform": "meta",
        "language": "cs",
        "market": "CZ",
        "video_length": 8,
        "use_avatar_image_reference": True,
        "input_references": [
            {"type": "image_url", "image_url": {"url": "https://example.com/product.jpg"}},
            {"type": "image_url", "image_url": {"url": "https://example.com/avatar.jpg"}},
        ],
    }

    strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        avatar,
        "https://example.com/product.jpg",
        settings,
    )
    structured_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=prompt_package,
        product_analysis=product_analysis,
        ugc_strategy=strategy,
        settings=settings,
    )
    final_prompt = structured_package["seedance_payload"]["prompt"]

    assert "With " not in strategy["hook"]
    assert "I'd" not in strategy["voiceover"]
    assert "clear product scale" not in strategy["voiceover"]
    assert "British English" not in strategy["voice_profile"]
    assert prompt_package["seedance_payload"]["speech_language"] == "cs-CZ"
    assert "British English" not in prompt_package["seedance_payload"]["prompt"]
    assert "CZECH LANGUAGE HARD LOCK" in final_prompt
    assert "cs-CZ" in final_prompt
    assert "input_references image 1 is the product identity source" in final_prompt
    assert "input_references image 2 is the avatar identity source only" in final_prompt
    assert "British English" not in final_prompt


def test_structured_prompt_v2_uses_ai_rewritten_scene_copy():
    content_prompt_package = {
        "seedance_video_prompt": "Fallback prompt",
        "seedance_payload": {"prompt": "Fallback prompt"},
        "structured_scene_prompt": {
            "variants": [
                {
                    "scenes": [
                        {
                            "scene_id": "s1",
                            "purpose": "hook",
                            "duration": 5,
                            "avatar_on_camera": True,
                            "use_reference_image": True,
                            "avatar_instruction": "subject from reference image, identity preserved, no facial morphing, no appearance drift, speaking naturally",
                            "scene_summary": "creator casually holds the exact product near a kitchen window",
                            "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                            "voiceover": "Hele, tohle bych si pred koupi chtel zkontrolovat zblizka.",
                            "on_screen_text": {"text": "Mrkni zblizka", "position": "bottom_center"},
                        }
                    ]
                }
            ]
        },
    }
    ugc_strategy = {
        "platform": "meta",
        "market": "CZ",
        "language": "cs",
        "duration_seconds": 5,
        "aspect_ratio": "9:16",
        "voiceover": "Puvodni mechanicka veta.",
        "scene_by_scene_script": [
            {
                "visual": "original deterministic visual",
                "shot_type": "medium shot",
                "psychology_step": "hook",
                "voiceover": "Puvodni mechanicka veta.",
                "on_screen_text": "Puvodni text",
            }
        ],
    }

    structured = structured_prompt_v2.build(
        product_analysis={},
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        settings={},
    )

    first_scene = structured["scenes"][0]
    assert first_scene["voiceover"] == "Hele, tohle bych si pred koupi chtel zkontrolovat zblizka."
    assert first_scene["scene"]["summary"].startswith(
        "creator casually holds the exact product near a kitchen window"
    )
    assert "no product-only insert shot" in first_scene["scene"]["summary"]
    assert first_scene["on_screen_text"] == ""
    assert "no generated text" in first_scene["scene"]["safe_area"]


def test_structured_prompt_v2_rejects_internal_voiceover_and_blocks_generated_text():
    content_prompt_package = {
        "seedance_video_prompt": "Fallback prompt",
        "seedance_payload": {"prompt": "Fallback prompt"},
        "structured_scene_prompt": {
            "variants": [
                {
                    "scenes": [
                        {
                            "scene_id": "s1",
                            "purpose": "hook",
                            "duration": 5,
                            "avatar_on_camera": True,
                            "use_reference_image": True,
                            "avatar_instruction": "subject from reference image, identity preserved, no facial morphing, no appearance drift, speaking naturally",
                            "scene_summary": "creator holds the exact tote on shoulder",
                            "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                            "voiceover": "angle:creator-style I'd show the opening with daily items beside it",
                            "on_screen_text": {"text": "visual direction: hook label", "position": "bottom_center"},
                        }
                    ]
                }
            ]
        },
    }
    ugc_strategy = {
        "platform": "meta",
        "market": "UK",
        "language": "en",
        "duration_seconds": 5,
        "aspect_ratio": "9:16",
        "voiceover": "Finally, a tote that looks elegant and still fits the daily essentials.",
        "subtitles": ["Finally, a tote that looks elegant"],
        "scene_by_scene_script": [
            {
                "visual": "creator holds the exact tote on shoulder",
                "shot_type": "medium shot",
                "psychology_step": "hook",
                "voiceover": "Finally, a tote that looks elegant and still fits the daily essentials.",
                "on_screen_text": "Finally, a tote that looks elegant",
                "subtitle": "Finally, a tote that looks elegant",
            }
        ],
    }

    structured_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=content_prompt_package,
        product_analysis={},
        ugc_strategy=ugc_strategy,
        settings={},
    )

    first_scene = structured_package["structured_prompt_v2"]["scenes"][0]
    prompt = structured_package["seedance_payload"]["prompt"]
    assert first_scene["voiceover"] == "Finally, a tote that looks elegant and still fits the daily essentials."
    assert first_scene["on_screen_text"] == ""
    assert "angle:creator-style" not in prompt
    assert "I'd show" not in prompt
    assert "no generated text" in prompt
    assert "hook sticker text" not in prompt
    assert "visual direction: hook label" not in prompt


def test_structured_prompt_v2_strips_all_ecommerce_generated_visible_text():
    content_prompt_package = {
        "seedance_video_prompt": "Fallback prompt",
        "seedance_payload": {"prompt": "Fallback prompt"},
        "structured_scene_prompt": {
            "variants": [
                {
                    "scenes": [
                        {
                            "scene_id": "s1",
                            "purpose": "hook",
                            "duration": 3,
                            "avatar_on_camera": True,
                            "scene_summary": "creator holds product",
                            "voiceover": "This is the first spoken line.",
                            "on_screen_text": {"text": "First hook", "position": "bottom_center"},
                        },
                        {
                            "scene_id": "s2",
                            "purpose": "detail",
                            "duration": 5,
                            "avatar_on_camera": True,
                            "scene_summary": "creator shows product detail",
                            "voiceover": "This line should be spoken, not rendered.",
                            "on_screen_text": {"text": "Overlay only", "position": "bottom_center"},
                        },
                    ]
                }
            ]
        },
    }
    ugc_strategy = {
        "platform": "meta",
        "market": "UK",
        "language": "en",
        "duration_seconds": 8,
        "aspect_ratio": "9:16",
        "voiceover": "This is the first spoken line. This line should be spoken, not rendered.",
        "subtitles": ["First hook", "This line should be spoken"],
        "scene_by_scene_script": [
            {
                "visual": "creator holds product",
                "shot_type": "medium shot",
                "psychology_step": "hook",
                "voiceover": "This is the first spoken line.",
                "on_screen_text": "First hook",
                "subtitle": "First hook",
            },
            {
                "visual": "creator shows product detail",
                "shot_type": "close-up",
                "psychology_step": "detail",
                "voiceover": "This line should be spoken, not rendered.",
                "on_screen_text": "Overlay only",
                "subtitle": "Do not render me",
            },
        ],
    }

    structured_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=content_prompt_package,
        product_analysis={},
        ugc_strategy=ugc_strategy,
        settings={},
    )

    scenes = structured_package["structured_prompt_v2"]["scenes"]
    prompt = structured_package["seedance_payload"]["prompt"]
    assert scenes[0]["on_screen_text"] == ""
    assert scenes[1]["on_screen_text"] == ""
    assert scenes[1]["infographic"]["labels"] is None
    assert "hook sticker text" not in prompt
    assert "Overlay only" not in prompt
    assert "no generated text" in prompt


def test_structured_prompt_v2_forces_creator_visible_for_ecommerce_product_insert():
    content_prompt_package = {
        "seedance_video_prompt": "Fallback prompt",
        "avatar_scene_instruction": (
            "subject from reference image, identity preserved, no facial morphing, no appearance drift, "
            "looking into camera and speaking naturally"
        ),
        "seedance_payload": {"prompt": "Fallback prompt"},
        "structured_scene_prompt": {
            "variants": [
                {
                    "scenes": [
                        {
                            "scene_id": "s1",
                            "purpose": "hook",
                            "duration": 5,
                            "avatar_on_camera": True,
                            "use_reference_image": True,
                            "avatar_instruction": "subject from reference image, identity preserved, no facial morphing, no appearance drift, speaking naturally",
                            "scene_summary": "creator shows the shoe in hand",
                            "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                            "voiceover": "Quick look.",
                            "on_screen_text": {"text": "Quick look", "position": "bottom_center"},
                        },
                        {
                            "scene_id": "s2",
                            "purpose": "proof",
                            "duration": 5,
                            "avatar_on_camera": False,
                            "use_reference_image": False,
                            "avatar_instruction": "no person visible, product-only insert shot, no reference image identity required",
                            "scene_summary": "no person visible, product-only insert shot of the shoe side profile",
                            "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                            "voiceover": "The side profile is the bit I would check.",
                            "on_screen_text": {"text": "Side profile", "position": "bottom_center"},
                        },
                    ]
                }
            ]
        },
    }
    ugc_strategy = {
        "platform": "meta",
        "market": "UK",
        "language": "en",
        "duration_seconds": 10,
        "aspect_ratio": "9:16",
        "voiceover": "Quick look. The side profile is the bit I would check.",
        "scene_by_scene_script": [
            {
                "visual": "creator shows the shoe in hand",
                "shot_type": "medium shot",
                "psychology_step": "hook",
                "voiceover": "Quick look.",
                "on_screen_text": "Quick look",
            },
            {
                "visual": "shoe side profile detail",
                "shot_type": "close-up",
                "psychology_step": "proof",
                "voiceover": "The side profile is the bit I would check.",
                "on_screen_text": "Side profile",
            },
        ],
    }

    structured = structured_prompt_v2.build(
        product_analysis={},
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        settings={},
    )

    second_scene = structured["scenes"][1]
    assert second_scene["avatar_rules"]["on_camera"] is True
    assert "creator" in second_scene["scene"]["summary"].lower()
    assert "no person visible" not in second_scene["scene"]["summary"].lower()
    assert "no reference image identity required" not in second_scene["avatar_rules"]["instruction"].lower()


def test_content_prompt_fallback_keeps_avatar_visible_in_every_ecommerce_scene(tmp_path):
    image_path = tmp_path / "shoe.jpg"
    image_path.write_bytes(b"fake-image")
    product_analysis = product_intake_agent.analyse(
        {
            "product_name": "MIA Sneakers",
            "product_info": "Lightweight slip-on sneakers",
            "product_category": "shoes",
        },
        image_path,
    )
    settings = {
        "platform": "meta",
        "language": "en",
        "market": "UK",
        "video_length": 15,
        "use_avatar_image_reference": True,
        "input_references": [
            {"type": "image_url", "image_url": {"url": "https://example.com/product.jpg"}},
            {"type": "image_url", "image_url": {"url": "https://example.com/avatar.jpg"}},
        ],
    }
    avatar = {
        "name": "Creator",
        "style": "natural creator",
        "voice": "relaxed English creator voice",
        "image_url": "https://example.com/avatar.jpg",
        "own_person_confirmed": True,
    }
    ugc_strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        ugc_strategy,
        avatar,
        "https://example.com/product.jpg",
        settings,
    )

    scenes = prompt_package["structured_scene_prompt"]["variants"][0]["scenes"]
    assert all(scene["avatar_on_camera"] is True for scene in scenes)
    assert all("product-only insert" not in scene["avatar_instruction"].lower() for scene in scenes)
    assert all("creator/avatar remains visibly present" in scene["scene_summary"] for scene in scenes)


def test_ads_copy_uses_german_fallback_for_de_language():
    product_analysis = {
        "product_name": "Personalisierte Glastasse",
        "product_image_path": "https://example.com/glass.jpg",
        "likely_product_category": "home",
        "ad_safe_detail_phrases": ["custom name inscription", "460 ml capacity"],
        "ad_safe_detail_phrases_localized": ["personalisierter Namensaufdruck", "460 ml Fassungsvermoegen"],
    }
    ugc_strategy = {"platform": "meta", "market": "DE", "language": "de", "aspect_ratio": "9:16", "hook": "hook"}

    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={},
        settings={
            "platform": "meta",
            "language": "de",
            "market": "DE",
            "product_reference_url": "https://example.com/glass.jpg",
        },
    )

    overlays = [item["overlay_text"] for item in ad_set["static_image_ads"]]
    carousel_overlays = [card["overlay_text"] for card in ad_set["carousel_ad"]["cards"]]
    assert ad_set["static_image_ads"][0]["overlay_text"] == "Personalisierter Namensaufdruck"
    assert "Hauptansicht" not in overlays
    assert "Finaler Check" not in carousel_overlays
    assert "Achte auf" in ad_set["static_image_ads"][0]["primary_text"]
    assert "What can you" not in ad_set["ad_description_suggestions"]["variants"][0]["primary_text"]
    assert "Was sieht man" in ad_set["ad_description_suggestions"]["variants"][0]["primary_text"]


def test_product_fidelity_guard_ignores_protective_no_luxury_language():
    product_analysis = {
        "product_image_path": "https://example.com/product.jpg",
        "likely_product_category": "handbag",
    }
    ugc_strategy = {"platform": "tiktok"}
    prompt_package = {
        "product_fidelity_instruction": f"Use https://example.com/product.jpg as the strict visual reference. {prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK}",
        "negative_prompt": "Do not redesign the product. No luxury/designer branding.",
        "seedance_payload": {
            "product_image_path": "https://example.com/product.jpg",
            "prompt": "Avoid any hype, luxury, or testimonial claims. Keep the product unchanged.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "pass"


def test_product_fidelity_guard_ignores_avatar_luxury_descriptor():
    product_analysis = {
        "product_image_path": "https://example.com/glass.jpg",
        "likely_product_category": "home",
        "known_product_facts": {"material": "plastic"},
    }
    ugc_strategy = {
        "platform": "meta",
        "voiceover": "This personalised plastic glass shows the name clearly on the front.",
        "voice_profile": "natural German creator voice; selected creator voice: Slight luxury commercial vibe",
        "voice_personality": {"tone": "warm, Slight luxury commercial vibe"},
    }
    avatar_context = (
        "Creator label=Simana. persona=Professional German ecommerce consultant avatar, "
        "luxury minimal office background. voice=Male German voice. Slight luxury commercial vibe. "
        "Scene prompts should describe only motion."
    )
    prompt_package = {
        "product_fidelity_instruction": f"Use https://example.com/glass.jpg as the strict visual reference. {prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK}",
        "avatar_consistency_instruction": avatar_context,
        "avatar_identity_contract": {
            "persona": "Professional avatar, luxury minimal office background",
            "voice": "Slight luxury commercial vibe",
        },
        "negative_prompt": "Do not redesign the product.",
        "seedance_video_prompt": (
            f"Use https://example.com/glass.jpg as the strict visual reference. {avatar_context} "
            "Dialogue: This personalised plastic glass shows the name clearly on the front."
        ),
        "seedance_payload": {
            "product_image_path": "https://example.com/glass.jpg",
            "prompt": (
                f"Use https://example.com/glass.jpg as the strict visual reference. {avatar_context} "
                "Dialogue: This personalised plastic glass shows the name clearly on the front."
            ),
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "pass"


def test_product_fidelity_guard_still_blocks_positive_luxury_claim():
    product_analysis = {
        "product_image_path": "https://example.com/glass.jpg",
        "likely_product_category": "home",
    }
    ugc_strategy = {"platform": "meta"}
    prompt_package = {
        "product_fidelity_instruction": "Use https://example.com/glass.jpg as the strict visual reference.",
        "negative_prompt": "Do not redesign the product.",
        "seedance_video_prompt": "Create a luxury designer drinking glass ad from the product reference.",
        "seedance_payload": {
            "product_image_path": "https://example.com/glass.jpg",
            "prompt": "Create a luxury designer drinking glass ad from the product reference.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "fail"
    assert "luxury" in result["changed_or_invented_details"]


def test_product_fidelity_guard_ignores_memory_ids_and_negative_redesign_language():
    product_analysis = {
        "product_image_path": "https://example.com/knitted-bag.jpg",
        "likely_product_category": "handbag",
        "known_product_facts": {"material": "unknown"},
        "user_provided_facts": [],
        "ad_safe_detail_phrases": ["woven texture", "shoulder bag form"],
    }
    ugc_strategy = {
        "platform": "meta",
        "creative_memory_rag": {
            "best_historical_creatives": [
                {"creative_id": "cr_cmp_prd_bella-leather-to_dee68014054e06ec"}
            ],
            "winning_patterns": ["close-up", "outfit"],
        },
    }
    prompt_package = {
        "product_fidelity_instruction": f"Use https://example.com/knitted-bag.jpg as the strict visual reference. {prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK}",
        "environment_control_directive": "No room redesign; preserve product position when visible.",
        "seedance_video_prompt": (
            "Use the product reference as source of truth. "
            "Do not redesign the product. No room redesign. Avoid any change to leather, finish, colour, hardware, shape, or brand markings. "
            "Show woven texture and shoulder bag form."
        ),
        "negative_prompt": "Do not redesign the product. Do not change material.",
        "seedance_payload": {
            "product_image_path": "https://example.com/knitted-bag.jpg",
            "prompt": "Do not redesign the product. Show woven texture.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "pass"
    assert result["changed_or_invented_details"] == []


def test_product_fidelity_guard_still_blocks_invented_material_claim():
    product_analysis = {
        "product_image_path": "https://example.com/knitted-bag.jpg",
        "likely_product_category": "handbag",
        "known_product_facts": {"material": "unknown"},
        "user_provided_facts": [],
        "ad_safe_detail_phrases": ["woven texture", "shoulder bag form"],
    }
    ugc_strategy = {"platform": "meta"}
    prompt_package = {
        "product_fidelity_instruction": "Use https://example.com/knitted-bag.jpg as the strict visual reference.",
        "seedance_video_prompt": "Create a premium leather shoulder bag lifestyle ad with the product reference.",
        "negative_prompt": "Do not redesign the product.",
        "seedance_payload": {
            "product_image_path": "https://example.com/knitted-bag.jpg",
            "prompt": "Create a premium leather shoulder bag lifestyle ad.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "fail"
    assert "leather" in result["changed_or_invented_details"]


def test_product_fidelity_guard_ignores_unverified_material_avoid_examples():
    product_analysis = {
        "product_image_path": "https://example.com/bum-bag.jpg",
        "likely_product_category": "handbag",
        "known_product_facts": {"material": "unknown"},
        "user_provided_facts": [],
        "ad_safe_detail_phrases": ["zippered pockets", "adjustable strap"],
    }
    ugc_strategy = {
        "platform": "meta",
        "visual_understanding": (
            "Avoid: Do not make unverified claims about the fabric material "
            "(e.g., 'canvas', 'vegan leather'); show strap and pocket details."
        ),
    }
    prompt_package = {
        "product_fidelity_instruction": (
            "Use https://example.com/bum-bag.jpg as the strict visual reference. "
            f"{prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK}"
        ),
        "category_prompt_directive": (
            "Avoid: overstuffing the bag; Making unverified claims about the material "
            "(e.g., waterproof, leather)."
        ),
        "seedance_video_prompt": (
            "Material lock: material is not confidently verified, so copy only the visible finish; "
            "do not name or depict leather, suede, fabric, canvas, plastic, glass, metal, ceramic, "
            "wood, rubber, glossy, matte, transparent, opaque, pebbled, woven, quilted, padded, "
            "smooth, or grained material unless visible in the reference. "
            "Show the adjustable strap and zippered pockets."
        ),
        "negative_prompt": "Do not redesign the product. Do not change material.",
        "seedance_payload": {
            "product_image_path": "https://example.com/bum-bag.jpg",
            "prompt": "Show the adjustable strap and zippered pockets.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "pass"
    assert result["changed_or_invented_details"] == []


def test_product_fidelity_guard_allows_safe_apparel_drape_language():
    product_analysis = {
        "product_image_path": "https://example.com/jumpsuit.jpg",
        "likely_product_category": "apparel",
        "known_product_facts": {"material": "unknown"},
        "user_provided_facts": ["modern jumpsuit"],
        "ad_safe_detail_phrases": ["worn cut", "seam detail", "visible finish from reference"],
    }
    ugc_strategy = {
        "platform": "meta",
        "voiceover": "Up close, you can see how the fabric actually drapes and how clean the seams are.",
    }
    prompt_package = {
        "product_fidelity_instruction": (
            "Use https://example.com/jumpsuit.jpg as the strict visual reference. "
            f"{prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK}"
        ),
        "seedance_video_prompt": (
            "Avatar shows a worn cut. Shot type: fabric movement and seam detail. "
            "Hands gently smooth the fabric while the garment stays exactly as the reference."
        ),
        "negative_prompt": "Do not redesign the product. Do not change material.",
        "seedance_payload": {
            "product_image_path": "https://example.com/jumpsuit.jpg",
            "prompt": "Show fabric drape and clean seams while preserving the exact reference.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "pass"
    assert result["changed_or_invented_details"] == []


def test_product_fidelity_guard_allows_mirror_scenario_generic_fabric_handling():
    product_analysis = {
        "product_name": "Jumpsuit",
        "product_image_path": "https://example.com/jumpsuit.jpg",
        "likely_product_category": "apparel",
        "known_product_facts": {"material": "unknown", "color": "unknown"},
        "user_provided_facts": [],
        "ad_safe_detail_phrases": ["visible cut", "drape", "visible finish from reference"],
        "safest_creative_angle": "mirror try-on review",
    }
    settings = {
        "platform": "meta",
        "language": "en",
        "market": "UK",
        "video_length": 15,
        "ugc_video_extra_prompt": (
            "UGC type: mirror selfie / try-on review. "
            "Avatar is filming herself in a mirror using an iPhone. "
            "Avatar behavior: talks naturally, slight handheld camera shake, adjusts the fabric casually, turns sideways once. "
            "Hook: I wanted a jumpsuit that actually looks flattering without feeling overdressed."
        ),
    }
    avatar = {"name": "Avatar1", "style": "natural creator"}

    strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        avatar,
        "https://example.com/jumpsuit.jpg",
        settings,
    )
    structured_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=prompt_package,
        product_analysis=product_analysis,
        ugc_strategy=strategy,
        settings=settings,
    )
    result = product_fidelity_guard.check(product_analysis, strategy, structured_package)

    prompt = structured_package["seedance_payload"]["prompt"].lower()
    assert "adjusts the fabric casually" not in prompt
    assert "adjusts the garment" in prompt
    assert result["product_fidelity_status"] == "pass"
    assert result["changed_or_invented_details"] == []


def test_product_fidelity_guard_allows_visual_classifier_apparel_fabric_motion_language():
    product_analysis = {
        "product_image_path": "https://example.com/jumpsuit.jpg",
        "likely_product_category": "apparel",
        "known_product_facts": {"material": "unknown"},
        "user_provided_facts": ["modern jumpsuit"],
        "ad_safe_detail_phrases": ["worn cut", "visible finish from reference"],
    }
    ugc_strategy = {
        "platform": "meta",
        "scene_by_scene_script": [
            {
                "visual": (
                    "Visual product classifier guard: Highlight the comfort and movement of the fabric "
                    "through walking or turning shots. Do not use poor lighting that obscures the fabric texture."
                )
            }
        ],
    }
    prompt_package = {
        "product_fidelity_instruction": (
            "Use https://example.com/jumpsuit.jpg as the strict visual reference. "
            f"{prompt_defaults.PRODUCT_IDENTITY_HARD_LOCK}"
        ),
        "category_prompt_directive": (
            "Scenario rules: Highlight the comfort and movement of the fabric through walking or turning shots. "
            "Include movement, such as walking or turning, to show how the fabric flows. "
            "Avoid flat lays and isolated fabric-only shots."
        ),
        "seedance_video_prompt": (
            "Show garment movement, cut, drape, and visible finish from reference while preserving the exact reference."
        ),
        "negative_prompt": "Do not redesign the product. Do not change material.",
        "seedance_payload": {
            "product_image_path": "https://example.com/jumpsuit.jpg",
            "prompt": "Show garment movement and visible finish from reference.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "pass"
    assert result["changed_or_invented_details"] == []


def test_product_fidelity_guard_still_blocks_specific_apparel_material_claim():
    product_analysis = {
        "product_image_path": "https://example.com/jumpsuit.jpg",
        "likely_product_category": "apparel",
        "known_product_facts": {"material": "unknown"},
        "user_provided_facts": ["modern jumpsuit"],
        "ad_safe_detail_phrases": ["worn cut", "seam detail"],
    }
    ugc_strategy = {"platform": "meta"}
    prompt_package = {
        "product_fidelity_instruction": "Use https://example.com/jumpsuit.jpg as the strict visual reference.",
        "seedance_video_prompt": "Create a polished silk jumpsuit ad with a premium shine.",
        "negative_prompt": "Do not redesign the product.",
        "seedance_payload": {
            "product_image_path": "https://example.com/jumpsuit.jpg",
            "prompt": "Create a polished silk jumpsuit ad.",
        },
    }

    result = product_fidelity_guard.check(product_analysis, ugc_strategy, prompt_package)

    assert result["product_fidelity_status"] == "fail"
    assert "silk" in result["changed_or_invented_details"]


def test_ads_static_prompts_are_category_aware_for_shoes():
    product_analysis = {
        "product_name": "Everyday Sneakers",
        "product_image_path": "https://example.com/shoes.jpg",
        "likely_product_category": "shoes",
        "ad_safe_detail_phrases": ["side profile", "upper texture", "sole edge"],
    }
    ugc_strategy = {"platform": "meta", "market": "UK", "language": "en"}
    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={},
        settings={
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "product_reference_url": "https://example.com/shoes.jpg",
        },
    )

    static_text = " ".join(item["visual_prompt"].lower() for item in ad_set["static_image_ads"])
    carousel_text = " ".join(card["visual_prompt"].lower() for card in ad_set["carousel_ad"]["cards"])
    assert "wearing the shoes" in static_text
    assert "no table" in static_text
    assert "no desk" in static_text
    assert "worn" in carousel_text
    assert "flat lay" in carousel_text


def test_ads_static_prompts_lock_handbag_scale():
    product_analysis = {
        "product_name": "Tilly Shoulder Bag",
        "product_image_path": "https://example.com/bag.jpg",
        "likely_product_category": "handbag",
        "ad_safe_detail_phrases": ["woven texture", "shoulder bag form", "handle detail"],
    }
    ugc_strategy = {"platform": "meta", "market": "UK", "language": "en"}
    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={},
        settings={
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "product_reference_url": "https://example.com/bag.jpg",
        },
    )

    static_text = " ".join(item["visual_prompt"].lower() for item in ad_set["static_image_ads"])
    carousel_text = " ".join(card["visual_prompt"].lower() for card in ad_set["carousel_ad"]["cards"])

    assert "handbag scale lock" in static_text
    assert "same physical bag size" in static_text
    assert "do not resize into mini bag" in static_text
    assert "same physical bag size" in carousel_text
    assert "dropshipping static realism" in static_text
    assert "buyer-proof product check" in static_text
    assert "not a polished catalogue" in static_text
    assert "dropshipping static realism" in carousel_text


def test_ads_static_prompts_do_not_default_to_apartment_interiors():
    cases = [
        ("handbag", "Tilly Shoulder Bag", "https://example.com/bag.jpg"),
        ("apparel", "Leg Jumpsuit", "https://example.com/jumpsuit.jpg"),
        ("shoes", "Everyday Sneakers", "https://example.com/shoes.jpg"),
    ]

    for category, product_name, product_url in cases:
        ad_set = ads_creative_set_agent.generate_ad_set(
            product_analysis={
                "product_name": product_name,
                "product_image_path": product_url,
                "likely_product_category": category,
                "ad_safe_detail_phrases": ["visible detail", "scale", "finish"],
            },
            ugc_strategy={"platform": "meta", "market": "UK", "language": "en"},
            content_prompt_package={"seedance_video_prompt": "video prompt"},
            avatar={},
            settings={
                "platform": "meta",
                "language": "en",
                "market": "UK",
                "product_reference_url": product_url,
            },
        )

        prompts = " ".join(item["visual_prompt"].lower() for item in ad_set["static_image_ads"])
        carousel = " ".join(card["visual_prompt"].lower() for card in ad_set["carousel_ad"]["cards"])

        assert "apartment" not in prompts
        assert "bedroom" not in prompts
        assert any(
            marker in f"{prompts} {carousel}"
            for marker in ["cafe", "office", "quiet street", "pavement", "outdoor doorway", "commute"]
        )


def test_ads_static_set_adds_material_opacity_lock_for_static_images():
    product_analysis = {
        "product_name": "White Travel Cup",
        "product_image_path": "https://example.com/cup.jpg",
        "likely_product_category": "home",
        "known_product_facts": {"material": "opaque ceramic", "color": "white"},
        "user_provided_facts": ["opaque white cup"],
        "ad_safe_detail_phrases": ["white finish", "simple rim"],
    }
    ugc_strategy = {"platform": "meta", "market": "CZ", "language": "cs"}
    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={},
        settings={
            "platform": "meta",
            "language": "cs",
            "market": "CZ",
            "product_reference_url": "https://example.com/cup.jpg",
        },
    )

    lock = ad_set["static_product_material_fidelity_lock"].lower()

    assert "verified material=opaque ceramic" in lock
    assert "do not make an opaque product transparent" in lock
    assert "never invent clear walls" in lock


def test_ads_static_set_preserves_mom_subject_from_user_scenario():
    product_url = "https://example.com/bum-bag.jpg"
    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis={
            "product_name": "The Roomiest Bum Bag",
            "product_image_path": product_url,
            "likely_product_category": "handbag",
            "known_product_facts": {"material": "unknown"},
            "ad_safe_detail_phrases": ["zippered pockets", "wide strap", "body scale"],
        },
        ugc_strategy={
            "platform": "meta",
            "market": "UK",
            "language": "en",
            "user_scenario_lock": {
                "enabled": True,
                "raw_user_direction": "Busy mom casually filming herself. She wears the crossbody.",
            },
        },
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={},
        settings={
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "product_reference_url": product_url,
            "ugc_video_extra_prompt": "Must feel like a real busy mom. She wears the GoFree crossbody.",
        },
    )

    static_text = " ".join(item["visual_prompt"].lower() for item in ad_set["static_image_ads"])
    carousel_text = " ".join(card["visual_prompt"].lower() for card in ad_set["carousel_ad"]["cards"])

    assert "adult woman/mom" in static_text
    assert "adult woman/mom" in carousel_text
    assert "do not generate a male-presenting model" in f"{static_text} {carousel_text}"
    assert ad_set["static_subject_lock"]


def test_ads_static_set_preserves_avatar_gender_for_static_images():
    product_url = "https://example.com/bag.jpg"
    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis={
            "product_name": "Everyday Bag",
            "product_image_path": product_url,
            "likely_product_category": "handbag",
            "known_product_facts": {"material": "unknown"},
            "ad_safe_detail_phrases": ["strap", "opening", "body scale"],
        },
        ugc_strategy={"platform": "meta", "market": "DE", "language": "de"},
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={
            "name": "Avatar 02",
            "voice": "Male German voice, age around 38-45, calm and trustworthy tone",
            "style": "premium casual business outfit",
        },
        settings={
            "platform": "meta",
            "language": "de",
            "market": "DE",
            "product_reference_url": product_url,
        },
    )

    static_text = " ".join(item["visual_prompt"].lower() for item in ad_set["static_image_ads"])
    carousel_text = " ".join(card["visual_prompt"].lower() for card in ad_set["carousel_ad"]["cards"])

    assert "adult man/male-presenting creator" in static_text
    assert "adult man/male-presenting creator" in carousel_text
    assert "do not generate a female-presenting model" in f"{static_text} {carousel_text}"


def test_scenario_integrity_guard_blocks_when_approved_scenario_is_lost():
    result = scenario_integrity_guard.check(
        product_analysis={"likely_product_category": "handbag"},
        ugc_strategy={
            "user_scenario_lock": {
                "enabled": True,
                "raw_user_direction": "Mom Bag Without The Diaper Bag. Show diapers, wipes, snacks, phone, wallet, keys.",
            }
        },
        content_prompt_package={
            "seedance_video_prompt": "Generic handbag video in a cafe entrance with phone, wallet, and keys.",
            "seedance_payload": {"prompt": "Generic handbag video."},
        },
        avatar={"voice": "female creator voice"},
        ads_creative_set={
            "static_image_ads": [
                {"visual_prompt": "adult woman carrying the bag"},
            ],
            "carousel_ad": {"cards": []},
        },
    )

    assert result["status"] == "failed"
    assert any(item["id"] == "scenario_parent_items_missing" for item in result["failures"])


def test_scenario_integrity_guard_blocks_avatar_gender_conflict():
    result = scenario_integrity_guard.check(
        product_analysis={"likely_product_category": "handbag"},
        ugc_strategy={
            "user_scenario_lock": {
                "enabled": True,
                "raw_user_direction": "Busy mom filming herself with the crossbody bag.",
            }
        },
        content_prompt_package={
            "seedance_video_prompt": "Busy mom creator shows the crossbody bag in a phone selfie.",
            "seedance_payload": {"prompt": "Busy mom creator shows the bag."},
        },
        avatar={"voice": "Male German voice, calm and trustworthy"},
        ads_creative_set={
            "static_image_ads": [
                {"visual_prompt": "adult man/male-presenting creator carrying the bag"},
            ],
            "carousel_ad": {"cards": []},
        },
    )

    assert result["status"] == "failed"
    assert any(item["id"] == "scenario_avatar_gender_conflict" for item in result["failures"])


def test_ads_static_set_uses_visual_classifier_for_static_images():
    product_analysis = {
        "product_name": "Everyday Shoulder Bag",
        "product_image_path": "https://example.com/bag.jpg",
        "likely_product_category": "handbag",
        "known_product_facts": {"material": "unknown", "color": "black"},
        "ad_safe_detail_phrases": ["handle detail", "structured shape", "opening"],
        "visual_product_understanding": {
            "status": "completed",
            "detected_object": "shoulder bag",
            "subcategory": "handbag",
            "category_confidence": 0.88,
            "recommended_template_id": "carry_capacity_check",
            "scenario_rules": ["show adult body scale"],
            "shot_requirements": ["bag carried on shoulder", "handle and opening detail"],
            "avoid_in_generation": ["flat studio product-only render"],
            "qa_expectations": ["same bag silhouette and carry scale"],
        },
    }

    ad_set = ads_creative_set_agent.generate_ad_set(
        product_analysis=product_analysis,
        ugc_strategy={"platform": "meta", "market": "UK", "language": "en"},
        content_prompt_package={"seedance_video_prompt": "video prompt"},
        avatar={},
        settings={
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "product_reference_url": "https://example.com/bag.jpg",
        },
    )

    directive = ad_set["static_visual_classifier_directive"]
    c4_prompt = ad_set["static_image_ads"][2]["visual_prompt"]

    assert "Visual classifier static directive" in directive
    assert "carry_capacity_check" not in directive
    assert "bag carried on shoulder" in directive
    assert "Visual classifier static directive" in ad_set["category_image_directive"]
    assert "bag carried on shoulder" in c4_prompt
    assert "tiny annotation labels" not in c4_prompt
    assert "subtle non-text pointer marks" in c4_prompt


def test_ugc_strategy_uses_category_specific_video_recipe_for_shoes():
    product_analysis = {
        "product_name": "Everyday Sneakers",
        "likely_product_category": "shoes",
        "safest_creative_angle": "Show visible shoe construction",
        "ad_safe_detail_phrases": ["side profile", "upper texture", "sole edge"],
        "user_provided_facts": ["side profile", "upper texture"],
    }
    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Avatar1", "style": "natural creator"},
        {"platform": "meta", "language": "en", "market": "UK", "video_length": 15},
    )

    visuals = " ".join(scene["visual"].lower() for scene in strategy["scene_by_scene_script"])
    assert strategy["category_video_recipe"]["category"] == "shoes"
    assert "side profile on foot" in strategy["hook"]
    assert "low-angle worn close-ups" in visuals
    assert "no table" in visuals
    assert "no flat lay" in visuals
    assert "Worn with outfit" in strategy["on_screen_text"]


def test_apparel_ugc_requires_full_body_worn_view():
    product_analysis = {
        "product_name": "Wide Leg Jumpsuit",
        "likely_product_category": "apparel",
        "safest_creative_angle": "Show the worn cut and drape",
        "ad_safe_detail_phrases": ["wide leg cut", "drape", "hem"],
        "user_provided_facts": ["wide leg cut", "visible drape"],
    }
    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Avatar1", "style": "natural creator"},
        {"platform": "meta", "language": "en", "market": "UK", "video_length": 15},
    )
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        {"name": "Avatar1", "style": "natural creator"},
        "jumpsuit.jpg",
        {"platform": "meta", "language": "en", "market": "UK", "video_length": 15},
    )

    visuals = " ".join(scene["visual"].lower() for scene in strategy["scene_by_scene_script"])
    prompt = prompt_package["seedance_payload"]["prompt"].lower()
    assert strategy["category_video_recipe"]["category"] == "apparel"
    assert strategy["ugc_prompt_skill"]["template_id"] == "creator_connected_lifestyle"
    assert "See the cut worn" in strategy["on_screen_text"]
    assert "full-body or near full-body" in visuals
    assert "head-to-toe" in visuals
    assert "polished ecommerce model" in prompt
    assert "normal phone try-on check" in prompt
    assert "full-body or near full-body" in prompt
    assert "head-to-toe" in prompt
    assert "no_generated_text=true" not in prompt
    assert "no generated text" in prompt


def test_custom_ugc_scenario_lock_prioritizes_mirror_selfie_try_on():
    scenario = (
        "UGC type: mirror selfie / try-on review. Length about 15s. "
        "Vertical authentic mobile footage in a simple room with a neutral wall. "
        "Camera: phone in hand, mirror shot. Creator speaks directly to camera, gestures, shows the outfit. "
        "Feeling: real customer review, one continuous take, soft indoor light, calm friend tone. "
        "on screan hook: I didn't expect this to fit so well... "
        "Do not start too ad-like, no luxury studio, light imperfection is good."
    )
    product_analysis = {
        "product_name": "Wide Leg Jumpsuit",
        "likely_product_category": "apparel",
        "safest_creative_angle": "Show the worn cut and drape",
        "ad_safe_detail_phrases": ["wide leg cut", "drape", "waist detail"],
        "user_provided_facts": ["wide leg cut", "visible drape"],
    }
    settings = {
        "platform": "meta",
        "language": "en",
        "market": "UK",
        "video_length": 15,
        "ugc_video_extra_prompt": scenario,
    }
    avatar = {"name": "Avatar1", "style": "natural creator"}
    strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        avatar,
        "jumpsuit.jpg",
        settings,
    )
    structured_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=prompt_package,
        product_analysis=product_analysis,
        ugc_strategy=strategy,
        settings=settings,
    )

    lock = strategy["user_scenario_lock"]
    visuals = " ".join(scene["visual"].lower() for scene in strategy["scene_by_scene_script"])
    prompt = structured_package["seedance_video_prompt"].lower()

    assert lock["enabled"] is True
    assert lock["template_id"] == "mirror_selfie_try_on_review"
    assert strategy["ugc_prompt_skill"]["template_id"] == "mirror_selfie_try_on_review"
    assert prompt_package["environment_control"]["environment_selection"] == "user_scenario_mirror_selfie"
    assert strategy["scene_by_scene_script"][0]["voiceover"] == "I didn't expect this to fit so well"
    assert strategy["on_screen_text"][0] == ""
    assert "mirror selfie" in visuals
    assert "one continuous" in visuals
    assert "simple bedroom or ordinary room" in visuals
    assert "full-body or near full-body" in visuals
    assert prompt_package["user_scenario_lock"]["hook_text"] == "I didn't expect this to fit so well"
    assert structured_package["structured_prompt_v2"]["user_scenario_lock"]["template"] == "mirror_selfie_try_on_review"
    assert "user scenario lock" in prompt
    assert "mirror selfie" in prompt
    assert "smartphone visibly held" in prompt
    assert "visible speaking guard" in prompt
    assert "not off-camera narration" in prompt
    assert "mouth remains visible" in prompt
    assert "mirror-selfie camera lock" in prompt
    assert "only camera source is the creator's iphone mirror-selfie recording" in prompt
    assert "never switch to third-person camera" in prompt
    assert "cinematic b-roll" in prompt
    assert "perspective switch" in prompt
    assert "mirror-selfie opening motion guard" in prompt
    assert "first frame must not look like a frozen still" in prompt
    assert "tiny phone sway" in prompt
    assert "poster frame" in prompt
    assert "human proportion guard" in prompt
    assert "normal smartphone 9:16 framing" in prompt
    assert "no fisheye" in prompt
    assert "i didn't expect this to fit so well" in prompt
    assert "hook sticker text" not in prompt
    assert "environment_selection=category_auto" not in prompt
    for conflicting_location in [
        "cafe entrance",
        "quiet street",
        "office lift",
        "outdoor doorway",
        "category-selected clean mirror",
        "hallway-only",
    ]:
        assert conflicting_location not in prompt


def test_generic_ugc_extra_direction_does_not_override_skill_template():
    product_analysis = {
        "product_name": "Wide Leg Jumpsuit",
        "likely_product_category": "apparel",
        "safest_creative_angle": "Show the worn cut and drape",
        "ad_safe_detail_phrases": ["wide leg cut", "drape", "hem"],
        "user_provided_facts": ["wide leg cut", "visible drape"],
    }
    settings = {
        "platform": "meta",
        "language": "en",
        "market": "UK",
        "video_length": 15,
        "ugc_video_extra_prompt": "Midway through the video, the background light shifts from warm to cool blue and the creator reacts naturally",
    }
    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Avatar1", "style": "natural creator"},
        settings,
    )
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        {"name": "Avatar1", "style": "natural creator"},
        "jumpsuit.jpg",
        settings,
    )

    assert strategy["ugc_prompt_skill"]["template_id"] == "creator_connected_lifestyle"
    assert strategy["user_scenario_lock"]["enabled"] is False
    assert "User scenario lock" not in prompt_package["seedance_video_prompt"]
    assert "background light shifts from warm to cool blue" in prompt_package["seedance_video_prompt"]


def test_mom_bag_scenario_does_not_trigger_apparel_try_on_from_fits_word():
    scenario = (
        "=== CHAT APPROVED SCENARIO START === "
        "Title: Mom Bag Without The Diaper Bag. "
        "Must feel like a real busy mom casually filming herself during a normal day. "
        "Scene: Mom standing in kitchen preparing to leave the house. "
        "She wears the GoFree Crossbody. "
        "Camera: Handheld iPhone front camera. "
        "Dialogue: Everything fits in one crossbody. "
        "Show: diapers, wipes, snacks, phone, wallet, keys."
    )
    product_analysis = {
        "product_name": "The Roomiest Bum Bag",
        "likely_product_category": "handbag",
        "safest_creative_angle": "parent everyday carry",
        "ad_safe_detail_phrases": ["zippered pockets", "wide strap", "body scale"],
        "user_provided_facts": [],
    }
    settings = {
        "platform": "meta",
        "language": "en",
        "market": "UK",
        "video_length": 15,
        "ugc_video_extra_prompt": scenario,
    }
    avatar = {"name": "Avatar1", "style": "natural creator"}

    strategy = ugc_agent.generate_strategy(product_analysis, avatar, settings)
    prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis,
        strategy,
        avatar,
        "bag.jpg",
        settings,
    )
    structured_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=prompt_package,
        product_analysis=product_analysis,
        ugc_strategy=strategy,
        settings=settings,
    )

    lock = strategy["user_scenario_lock"]
    prompt = structured_package["seedance_video_prompt"].lower()

    assert lock["enabled"] is True
    assert lock["detected_traits"]["apparel_like"] is False
    assert "adult woman/mom creator subject lock" in lock["compiled_direction"]
    assert "diapers, wipes, snacks, phone, wallet, and keys" in lock["compiled_direction"]
    assert "mom bag without the diaper bag" in prompt
    assert "everything fits in one crossbody" in prompt
    assert "apparel full-body worn view required" not in prompt


def test_ugc_strategy_subtitles_are_short_caption_fragments():
    product_analysis = {
        "product_name": "Everyday Sneakers",
        "likely_product_category": "shoes",
        "safest_creative_angle": "Show visible shoe construction",
        "ad_safe_detail_phrases": ["side profile", "upper texture", "sole edge"],
        "user_provided_facts": ["side profile", "upper texture"],
    }
    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Avatar1", "style": "natural creator"},
        {"platform": "meta", "language": "en", "market": "UK", "video_length": 15},
    )

    subtitles = strategy["subtitles"]
    voiceovers = [scene["voiceover"] for scene in strategy["scene_by_scene_script"]]

    assert len(subtitles) == len(voiceovers)
    assert all(0 < len(subtitle.split()) <= 8 for subtitle in subtitles)
    assert any(subtitle != voiceover for subtitle, voiceover in zip(subtitles, voiceovers))
    forbidden = "click tap cta button product_info"
    joined = " ".join(subtitles).lower()
    assert not any(word in joined for word in forbidden.split())


def test_ugc_strategy_rejects_non_english_hook_and_overlay_for_english():
    product_analysis = {
        "product_name": "Wide Leg Jumpsuit",
        "likely_product_category": "apparel",
        "safest_creative_angle": "Show the worn cut and drape",
        "ad_safe_detail_phrases": ["wide leg cut", "drape", "hem"],
        "user_provided_facts": ["wide leg cut", "visible drape"],
    }
    strategy = ugc_agent.generate_strategy(
        product_analysis,
        {"name": "Avatar1", "style": "natural creator"},
        {
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "video_length": 15,
            "ugc_hook_strategy": {
                "selected_hook": "U Wide Leg Jumpsuit je nejdulezitejsi strih primo na postave.",
            },
            "scene_direction": {
                "directed_scenes": [
                    {"visual": "scene 1", "overlay": "Strih na postave", "shot_type": "hook"},
                    {"visual": "scene 2", "overlay": "Material zblizka", "shot_type": "detail"},
                    {"visual": "scene 3", "overlay": "Outfit v realu", "shot_type": "context"},
                    {"visual": "scene 4", "overlay": "Detail v klidu", "shot_type": "close"},
                ]
            },
        },
    )

    joined_text = " ".join(strategy["on_screen_text"])
    assert strategy["hook"] == "With this piece, the cut matters most when you see it worn."
    assert "Strih" not in joined_text
    assert "Material zblizka" not in joined_text
    assert "Detail close-up" in joined_text
    assert strategy["subtitle_rules"]["max_words_per_caption"] == 8
