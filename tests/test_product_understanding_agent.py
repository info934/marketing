import json

from app.services import (
    arcads_ugc_guidance,
    product_intake_agent,
    product_understanding_agent,
    visual_product_classifier_agent,
)


def test_product_understanding_detects_handbag_context_without_api_key(tmp_path):
    product = product_intake_agent.analyse(
        {
            "product_name": "BELLA | LEATHER TOTE BAG",
            "product_info": (
                "Structured two-layer cowhide leather bag for work, errands, and travel "
                "with waterproof interior and clean minimalist shape"
            ),
            "product_category": "auto",
        },
        tmp_path / "product.png",
    )

    enriched = product_understanding_agent.enrich(
        product_analysis=product,
        settings={"market": "UK", "language": "en", "platform": "meta"},
        api_key="",
    )

    understanding = enriched["automatic_product_understanding"]
    assert understanding["category"] == "handbag"
    assert understanding["material"] == "two-layer cowhide leather"
    assert understanding["market_position"] == "mid-premium"
    assert "work commute" in understanding["usage_contexts"]
    assert "handbag" in enriched["likely_product_category"]
    assert "automatic_product_understanding" in enriched["prompt_data_sources"]["derived_from_user_input"]


def test_visual_product_classifier_guides_category_and_template(monkeypatch, tmp_path):
    image_path = tmp_path / "product.jpg"
    image_path.write_bytes(b"fake-image")
    product = product_intake_agent.analyse(
        {
            "product_name": "Red outfit",
            "product_info": "Red product",
            "product_category": "auto",
        },
        image_path,
    )
    product["likely_product_category"] = "unknown"

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "detected_object": "red wide-leg jumpsuit",
                                    "category": "apparel",
                                    "subcategory": "jumpsuit",
                                    "category_confidence": 0.91,
                                    "visual_evidence": ["one-piece garment", "wide-leg silhouette"],
                                    "reference_style": "packshot",
                                    "recommended_template_id": "apparel_try_on_full_body",
                                    "scenario_rules": [
                                        "show the garment worn before detail close-ups",
                                        "Highlight the comfort and movement of the fabric through walking or turning shots.",
                                        "Include movement, such as walking or turning, to show how the fabric flows.",
                                    ],
                                    "shot_requirements": ["full-body or near-full-body worn view first"],
                                    "avoid_in_generation": [
                                        "flat lay only",
                                        "Do not use poor lighting that obscures the fabric texture.",
                                    ],
                                    "qa_expectations": ["first frames show complete outfit silhouette"],
                                }
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 123},
            }

    def fake_post(url, headers, json, timeout):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(visual_product_classifier_agent.requests, "post", fake_post)

    visual = visual_product_classifier_agent.classify(
        product_analysis=product,
        product_image_path=image_path,
        settings={"market": "UK", "language": "en"},
        api_key="key",
        model="vision-model",
    )
    enriched = visual_product_classifier_agent.apply_to_product_analysis(product, visual)
    guidance = arcads_ugc_guidance.build_guidance(enriched, {})

    assert visual["status"] == "completed"
    assert captured["payload"]["messages"][1]["content"][1]["image_url"]["url"].startswith("data:image/")
    assert enriched["likely_product_category"] == "apparel"
    assert enriched["product_category_source"] == "visual_product_classifier"
    assert enriched["visual_subcategory"] == "jumpsuit"
    assert "comfort and movement of the fabric" not in " ".join(visual["scenario_rules"]).lower()
    assert "fabric flows" not in " ".join(visual["scenario_rules"]).lower()
    assert "movement, drape, and visible finish" in " ".join(visual["scenario_rules"]).lower()
    assert "garment drapes and moves" in " ".join(visual["scenario_rules"]).lower()
    assert "fabric texture" not in " ".join(visual["avoid_in_generation"]).lower()
    assert guidance["template_id"] == "apparel_try_on_full_body"
    assert "full-body" in " ".join(guidance["beat_structure"]).lower()


def test_visual_product_classifier_neutralizes_unverified_handbag_material_words(monkeypatch, tmp_path):
    image_path = tmp_path / "product.jpg"
    image_path.write_bytes(b"fake-image")
    product = product_intake_agent.analyse(
        {
            "product_name": "The Roomiest Bum Bag",
            "product_info": "Roomy crossbody bag for everyday use",
            "product_category": "auto",
        },
        image_path,
    )
    product["known_product_facts"]["material"] = "unknown"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "detected_object": "Green and white checkered bum bag",
                                    "category": "handbag",
                                    "subcategory": "Bum bag / Crossbody bag",
                                    "category_confidence": 1,
                                    "visual_evidence": ["Green and white checkered pattern"],
                                    "reference_style": "lifestyle",
                                    "recommended_template_id": "carry_capacity_check",
                                    "scenario_rules": [],
                                    "shot_requirements": [
                                        "Close-up on the zippers and the checkered fabric texture."
                                    ],
                                    "avoid_in_generation": [
                                        "Making unverified claims about the material (e.g., waterproof, leather)."
                                    ],
                                    "qa_expectations": [],
                                }
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 123},
            }

    def fake_post(url, headers, json, timeout):
        return FakeResponse()

    monkeypatch.setattr(visual_product_classifier_agent.requests, "post", fake_post)

    visual = visual_product_classifier_agent.classify(
        product_analysis=product,
        product_image_path=image_path,
        settings={"market": "UK", "language": "en"},
        api_key="key",
        model="vision-model",
    )

    shot_text = " ".join(visual["shot_requirements"]).lower()
    avoid_text = " ".join(visual["avoid_in_generation"]).lower()
    assert "fabric" not in shot_text
    assert "checkered pattern and visible surface texture" in shot_text
    assert "leather" not in avoid_text


def test_visual_product_classifier_does_not_override_user_selected_category(tmp_path):
    product = {
        "product_name": "Manual category item",
        "likely_product_category": "handbag",
        "requested_product_category": "handbag",
        "prompt_data_sources": {"derived_from_user_input": []},
    }
    visual = {
        "status": "completed",
        "category": "apparel",
        "category_confidence": 0.95,
        "recommended_template_id": "apparel_try_on_full_body",
    }

    enriched = visual_product_classifier_agent.apply_to_product_analysis(product, visual)

    assert enriched["likely_product_category"] == "handbag"
    assert enriched["visual_product_understanding"] == visual
