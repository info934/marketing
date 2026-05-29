from __future__ import annotations

import json

from app.services import openrouter_seedance_client
from app.services import openrouter_prompt_client


class FakeResponse:
    def __init__(self, payload=None, content=b"", status_code=200):
        self.payload = payload or {}
        self.content = content
        self.status_code = status_code
        self.text = str(self.payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def json(self):
        return self.payload


def test_prompt_client_compiles_structured_variants(monkeypatch):
    structured = {
        "variants": [
            {
                "variant_id": "v1",
                "total_duration_seconds": 5,
                "language": "en",
                "market": "UK",
                "platform": "meta",
                "aspect_ratio": "9:16",
                "seedance_mode": "image_to_video",
                "reference_image_strategy": "original_avatar_for_first_scene_then_last_frame_chain",
                "scenes": [
                    {
                        "scene_id": "s1",
                        "purpose": "hook",
                        "duration": 5,
                        "avatar_on_camera": True,
                        "use_reference_image": True,
                        "reference_image_source": "original_avatar",
                        "avatar_instruction": "subject from reference image, identity preserved, no facial morphing, no appearance drift, looking into camera, subtle smile forming, lips moving in sync with voiceover, wardrobe as in reference image, unchanged",
                        "scene_summary": "creator intro, lived-in kitchen, medium close shot with slight handheld camera sway, available natural window light, natural conversational pacing",
                        "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                        "voiceover": "Here is the quick look.",
                        "on_screen_text": {"text": "Quick look", "position": "bottom_center"},
                        "framing_notes": "Keep safe areas",
                    }
                ],
                "stitching": {"transition_style": "hard cut", "cut_timing_notes": "Cut naturally"},
                "safety_rewrites": [],
                "hypothesis": "Clear hook",
            }
        ]
    }

    def fake_post(url, headers, json, timeout):
        return FakeResponse({"choices": [{"message": {"content": __import__("json").dumps(structured)}}]})

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    package = {
        "seedance_video_prompt": "Fallback prompt",
        "negative_prompt": "Do not change product.",
        "seedance_payload": {"model": "bytedance/seedance-2.0-fast", "prompt": "Fallback prompt"},
    }
    result = openrouter_prompt_client.enhance_prompt_package(
        content_prompt_package=package,
        product_analysis={},
        ugc_strategy={},
        avatar={},
        api_key="test-key",
    )

    assert result["structured_scene_prompt"] == structured
    assert "Scene s1" in result["seedance_payload"]["prompt"]
    assert result["prompt_generation"]["status"] == "completed"


def test_prompt_client_rejects_invalid_structured_variants(monkeypatch):
    structured = {
        "variants": [
            {
                "variant_id": "v1",
                "total_duration_seconds": 15,
                "language": "en",
                "market": "UK",
                "platform": "meta",
                "aspect_ratio": "9:16",
                "seedance_mode": "image_to_video",
                "reference_image_strategy": "original_avatar_for_first_scene_then_last_frame_chain",
                "scenes": [
                    {
                        "scene_id": "s1",
                        "purpose": "hook",
                        "duration": 5,
                        "avatar_on_camera": True,
                        "use_reference_image": True,
                        "reference_image_source": "original_avatar",
                        "avatar_instruction": "subject from reference image, identity preserved, no facial morphing, no appearance drift, looking into camera, subtle smile forming, lips moving in sync with voiceover, wardrobe as in reference image, unchanged",
                        "scene_summary": "creator intro, kitchen counter, medium close shot, natural light, conversational pacing",
                        "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                        "voiceover": "Tap to learn more.",
                        "on_screen_text": {"text": "Learn more", "position": "bottom_center"},
                        "framing_notes": "Keep safe areas",
                    }
                ],
                "stitching": {"transition_style": "hard cut", "cut_timing_notes": "Cut naturally"},
                "safety_rewrites": [],
                "hypothesis": "Clear hook",
            }
        ]
    }

    def fake_post(url, headers, json, timeout):
        return FakeResponse({"choices": [{"message": {"content": __import__("json").dumps(structured)}}]})

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    package = {
        "seedance_video_prompt": "Fallback prompt",
        "negative_prompt": "Do not change product.",
        "seedance_payload": {"model": "bytedance/seedance-2.0-fast", "prompt": "Fallback prompt"},
    }
    result = openrouter_prompt_client.enhance_prompt_package(
        content_prompt_package=package,
        product_analysis={},
        ugc_strategy={},
        avatar={},
        api_key="test-key",
    )

    assert result["seedance_payload"]["prompt"] == "Fallback prompt"
    assert result["prompt_generation"]["status"] == "completed_with_fallback"
    assert "forbidden CTA" in result["prompt_generation"]["error"]


def test_prompt_client_uses_ugc_scenario_model_and_humanizer(monkeypatch):
    captured = {}
    structured = {
        "variants": [
            {
                "variant_id": "v1",
                "total_duration_seconds": 5,
                "language": "cs",
                "market": "CZ",
                "platform": "meta",
                "aspect_ratio": "9:16",
                "seedance_mode": "image_to_video",
                "reference_image_strategy": "original_avatar_for_first_scene_then_last_frame_chain",
                "scenes": [
                    {
                        "scene_id": "s1",
                        "purpose": "hook",
                        "duration": 5,
                        "avatar_on_camera": True,
                        "use_reference_image": True,
                        "reference_image_source": "original_avatar",
                        "avatar_instruction": "subject from reference image, identity preserved, no facial morphing, no appearance drift, looking into camera, subtle smile forming, lips moving in sync with voiceover, wardrobe as in reference image, unchanged",
                        "scene_summary": "tvurce drzi produkt doma u okna, kratky pohled do ruky, prirozene svetlo, uvolnene tempo",
                        "fidelity": "product not modified, not restyled, not recolored, not rebranded",
                        "voiceover": "Hele, tohle bych si pred koupi chtel zkontrolovat zblizka.",
                        "on_screen_text": {"text": "Mrkni zblizka", "position": "bottom_center"},
                        "framing_notes": "Keep safe areas",
                    }
                ],
                "stitching": {"transition_style": "hard cut", "cut_timing_notes": "Cut naturally"},
                "safety_rewrites": [],
                "hypothesis": "Natural proof hook",
            }
        ]
    }

    def fake_post(url, headers, json, timeout):
        captured["payload"] = json
        return FakeResponse({"choices": [{"message": {"content": __import__("json").dumps(structured)}}]})

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    result = openrouter_prompt_client.enhance_prompt_package(
        content_prompt_package={
            "seedance_video_prompt": "Fallback prompt",
            "negative_prompt": "Do not change product.",
            "seedance_payload": {"model": "bytedance/seedance-2.0-fast", "prompt": "Fallback prompt"},
        },
        product_analysis={},
        ugc_strategy={"language": "cs"},
        avatar={},
        api_key="test-key",
        model="google/gemini-3.5-flash",
    )

    user_message = json.loads(captured["payload"]["messages"][1]["content"])
    assert captured["payload"]["model"] == "google/gemini-3.5-flash"
    assert "UGC SCENARIO HUMANIZER WORKFLOW" in captured["payload"]["messages"][0]["content"]
    assert "phase_1_internal_skeleton" in user_message["scenario_generation_workflow"]
    assert "u piva" in user_message["scenario_generation_workflow"]["phase_2_required_rewrite"]
    assert result["prompt_generation"]["scenario_generation_workflow"] == "skeleton_then_conversational_rewrite"
    assert "u piva" in result["prompt_generation"]["humanizer_instruction"]


def test_prompt_client_refines_static_creative_prompts(monkeypatch):
    enhanced = {
        "creative_angles": [
            {
                "angle": "curiosity",
                "hook": "What is actually visible on the product?",
                "motivation": "User wants a specific visual reason to inspect the product",
            }
        ],
        "hook_bank": [
            {"pattern": "question", "hook": "What detail would you check first?"}
        ],
        "static_image_ads": [
            {
                "creative_id": "C2_static_lifestyle_pain",
                "set_id": "C2",
                "visual_prompt": "Refined C2 prompt with no ad button",
                "overlay_text": "Check this first",
            }
        ],
        "carousel_ad": {
            "set_id": "C5",
            "primary_text": "Refined carousel text",
            "cards": [
                {
                    "card_number": 1,
                    "visual_prompt": "Refined card prompt",
                    "overlay_text": "First detail",
                }
            ],
        },
    }

    def fake_post(url, headers, json, timeout):
        assert json["model"] == "openai/gpt-5.5"
        system_prompt = json["messages"][0]["content"]
        assert "as realistic as possible" in system_prompt
        assert "real-camera photography" in system_prompt
        assert "customer-facing hook copy" in system_prompt
        return FakeResponse(
            {
                "id": "chat_1",
                "choices": [{"message": {"content": __import__("json").dumps(enhanced)}}],
                "usage": {"cost": 0.002},
            }
        )

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "static_image_ads": [
                {
                    "creative_id": "C2_static_lifestyle_pain",
                    "set_id": "C2",
                    "visual_prompt": "Original C2 prompt",
                    "overlay_text": "Original",
                    "aspect_ratio": "1:1",
                }
            ],
            "carousel_ad": {
                "set_id": "C5",
                "cards": [
                    {
                        "card_number": 1,
                        "visual_prompt": "Original card prompt",
                        "overlay_text": "Original card",
                    }
                ],
            },
            "creative_angles": [
                {"angle": "curiosity", "hook": "Original hook", "motivation": "Original motivation"}
            ],
            "hook_bank": [
                {"pattern": "question", "hook": "Original question"}
            ],
        },
        product_analysis={},
        ugc_strategy={},
        api_key="test-key",
        model="openai/gpt-5.5",
    )

    assert result["creative_angles"][0]["hook"] == "What is actually visible on the product?"
    assert result["hook_bank"][0]["hook"] == "What detail would you check first?"
    assert result["static_image_ads"][0]["visual_prompt"] == "Refined C2 prompt without fake platform controls"
    assert "ad button" not in str(result).lower()
    assert result["carousel_ad"]["cards"][0]["overlay_text"] == "First detail"
    assert result["static_prompt_generation"]["status"] == "completed"


def test_prompt_client_omits_provider_schema_for_gemini_static_prompts(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["payload"] = json
        return FakeResponse(
            {
                "id": "chat_gemini_static",
                "choices": [
                    {
                        "message": {
                            "content": __import__("json").dumps(
                                {
                                    "creative_angles": [],
                                    "hook_bank": [],
                                    "static_image_ads": [
                                        {
                                            "creative_id": "C2_static_lifestyle_pain",
                                            "layout": "creator product frame",
                                            "visual_prompt": "Refined static prompt",
                                            "overlay_text": "Check the fit",
                                            "primary_text": "A simple look at the product.",
                                            "headline": "Check the fit",
                                        }
                                    ],
                                    "carousel_ad": {"primary_text": "", "cards": []},
                                    "meme_style_creatives": [],
                                    "primary_text_variants": [],
                                    "ad_description_suggestions": {"usage_note": "", "variants": []},
                                    "google_ads_assets": {
                                        "responsive_search_ad": {"headlines": [], "descriptions": []},
                                        "performance_max": {"headlines": [], "long_headlines": [], "descriptions": []},
                                    },
                                }
                            )
                        }
                    }
                ],
                "usage": {"cost": 0.001},
            }
        )

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "static_image_ads": [
                {
                    "creative_id": "C2_static_lifestyle_pain",
                    "set_id": "C2",
                    "visual_prompt": "Original C2 prompt",
                    "overlay_text": "Original",
                }
            ],
            "carousel_ad": {"cards": []},
        },
        product_analysis={},
        ugc_strategy={},
        api_key="test-key",
        model="google/gemini-3.5-flash",
    )

    assert captured["payload"]["model"] == "google/gemini-3.5-flash"
    assert "response_format" not in captured["payload"]
    assert "JSON OUTPUT CONTRACT" in captured["payload"]["messages"][0]["content"]
    assert result["static_image_ads"][0]["overlay_text"] == "Check the fit"
    assert result["static_prompt_generation"]["status"] == "completed"


def test_prompt_client_rejects_internal_overlay_labels(monkeypatch):
    enhanced = {
        "static_image_ads": [
            {
                "creative_id": "C2_static_lifestyle_pain",
                "visual_prompt": "Refined prompt",
                "overlay_text": "Hero view",
            }
        ],
        "carousel_ad": {
            "primary_text": "Refined carousel text",
            "cards": [
                {
                    "card_number": 1,
                    "visual_prompt": "Refined card prompt",
                    "overlay_text": "Final check",
                }
            ],
        },
    }

    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            {
                "id": "chat_1",
                "choices": [{"message": {"content": __import__("json").dumps(enhanced)}}],
                "usage": {"cost": 0.002},
            }
        )

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "static_image_ads": [
                {
                    "creative_id": "C2_static_lifestyle_pain",
                    "set_id": "C2",
                    "visual_prompt": "Original C2 prompt",
                    "overlay_text": "Check scale first",
                }
            ],
            "carousel_ad": {
                "set_id": "C5",
                "cards": [
                    {
                        "card_number": 1,
                        "visual_prompt": "Original card prompt",
                        "overlay_text": "Fits your routine",
                    }
                ],
            },
        },
        product_analysis={},
        ugc_strategy={},
        api_key="test-key",
        model="openai/gpt-5.5",
    )

    assert result["static_image_ads"][0]["overlay_text"] == "Check scale first"
    assert result["carousel_ad"]["cards"][0]["overlay_text"] == "Fits your routine"


def test_prompt_client_reports_static_prompt_model_failure_without_default_fallback(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json["model"])
        raise RuntimeError("402 Client Error: Payment Required")

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "static_image_ads": [
                {
                    "creative_id": "C2_static_lifestyle_pain",
                    "set_id": "C2",
                    "visual_prompt": "Original C2 prompt",
                    "overlay_text": "Original",
                }
            ],
            "carousel_ad": {"cards": []},
        },
        product_analysis={},
        ugc_strategy={},
        api_key="test-key",
        model="openai/gpt-5.5",
    )

    assert calls == ["openai/gpt-5.5"]
    assert result["static_prompt_generation"]["status"] == "failed"
    assert result["static_prompt_generation"]["model"] == "openai/gpt-5.5"
    assert result["static_prompt_generation"]["attempts"][0]["model"] == "openai/gpt-5.5"
    assert result["static_image_ads"][0]["visual_prompt"] == "Original C2 prompt"


def test_prompt_client_allows_static_fallback_after_invalid_json(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            {
                "id": "gen_static",
                "usage": {"cost": 0.01},
                "choices": [{"message": {"content": '{"static_image_ads": ['}}],
            }
        )

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "static_image_ads": [
                {
                    "creative_id": "C2_static_lifestyle_pain",
                    "set_id": "C2",
                    "visual_prompt": "Original C2 prompt",
                    "overlay_text": "Original",
                }
            ],
            "carousel_ad": {"cards": []},
        },
        product_analysis={},
        ugc_strategy={},
        api_key="test-key",
        model="openai/gpt-5.4-mini",
    )

    assert result["static_prompt_generation"]["status"] == "completed_with_fallback"
    assert "invalid JSON" in result["static_prompt_generation"]["fallback_reason"]
    assert result["static_prompt_generation"]["usage"]["cost"] == 0.01
    assert result["static_image_ads"][0]["visual_prompt"] == "Original C2 prompt"


def test_static_creative_prompt_payload_is_budgeted(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["payload"] = json
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"static_image_ads":[{"creative_id":"C2_static_lifestyle_pain","visual_prompt":"Short refined prompt"}]}'
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)
    huge_text = "Visible product detail. " * 3000

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "platform": "meta",
            "market": "UK",
            "language": "en",
            "static_image_ads": [
                {
                    "creative_id": "C2_static_lifestyle_pain",
                    "set_id": "C2",
                    "visual_prompt": huge_text,
                    "primary_text": huge_text,
                    "overlay_text": "Original",
                }
            ],
            "carousel_ad": {"cards": [{"card_number": 1, "visual_prompt": huge_text}]},
        },
        product_analysis={
            "product_name": "Large Brief Product",
            "safe_benefits": [huge_text],
            "internal_brief_notes": huge_text,
        },
        ugc_strategy={"hook": huge_text, "voice_profile": huge_text},
        api_key="test-key",
        model="openai/gpt-5.4-mini",
    )

    user_content = captured["payload"]["messages"][1]["content"]
    assert captured["payload"]["response_format"]["type"] == "json_schema"
    assert captured["payload"]["response_format"]["json_schema"]["name"] == "ads_creative_set_enhancer"
    assert len(user_content) <= openrouter_prompt_client.STATIC_CREATIVE_PROMPT_MAX_USER_CHARS
    assert result["static_prompt_generation"]["prompt_budget"]["user_chars_sent"] == len(user_content)
    assert result["static_image_ads"][0]["visual_prompt"] == "Short refined prompt"


def test_static_creative_prompt_payload_hard_fits_under_budget(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json)
        user_payload = __import__("json").loads(json["messages"][1]["content"])
        shard_name = (user_payload.get("prompt_shard") or {}).get("name")
        if shard_name == "static_images_1":
            content = {
                "static_image_ads": [
                    {"creative_id": "C2_static_lifestyle_pain", "visual_prompt": "Short refined C2 prompt"},
                    {"creative_id": "C3_static_lifestyle_pain", "visual_prompt": "Short refined C3 prompt"},
                    {"creative_id": "C4_static_lifestyle_pain", "visual_prompt": "Short refined C4 prompt"},
                ]
            }
        else:
            content = {
                "static_image_ads": [
                    {"creative_id": "C5_static_lifestyle_pain", "visual_prompt": "Short refined C5 prompt"}
                ],
                "carousel_ad": {
                    "primary_text": "Refined carousel primary",
                    "cards": [{"card_number": 1, "visual_prompt": "Refined card one", "overlay_text": "Card hook"}],
                },
            }
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": __import__("json").dumps(content)
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_prompt_client.requests, "post", fake_post)
    huge_text = "Specific product and creative detail. " * 2500
    static_ads = [
        {
            "creative_id": f"C{index}_static_lifestyle_pain",
            "set_id": f"C{index}",
            "creative_type": "static",
            "angle": huge_text,
            "visual_prompt": huge_text,
            "primary_text": huge_text,
            "overlay_text": "Original",
        }
        for index in range(2, 7)
    ]

    result = openrouter_prompt_client.enhance_ads_creative_set(
        ads_creative_set={
            "platform": "meta",
            "market": "CZ",
            "language": "cs",
            "static_image_ads": static_ads,
            "carousel_ad": {
                "primary_text": huge_text,
                "cards": [
                    {"card_number": index, "role": huge_text, "visual_prompt": huge_text, "overlay_text": "Card"}
                    for index in range(1, 6)
                ],
            },
            "creative_angles": [
                {"angle": huge_text, "hook": huge_text, "motivation": huge_text}
                for _ in range(10)
            ],
        },
        product_analysis={
            "product_name": "Budget Stress Product",
            "safe_benefits": [huge_text] * 8,
            "internal_brief_notes": huge_text,
        },
        ugc_strategy={
            "language": "cs",
            "hook": huge_text,
            "voice_profile": huge_text,
            "ad_angle_selector": {
                "slot_selection": {
                    f"C{index}": {
                        "selected_family": huge_text,
                        "selected_hook": huge_text,
                        "selection_reason": huge_text,
                    }
                    for index in range(2, 8)
                }
            },
            "performance_insights": {
                "creative_memory_rag": {
                    "prompt_guidance": huge_text,
                    "winning_patterns": [huge_text] * 8,
                    "avoid_patterns": [huge_text] * 8,
                }
            },
        },
        api_key="test-key",
        model="openai/gpt-5.4-mini",
    )

    user_contents = [call["messages"][1]["content"] for call in calls]
    shard_names = [__import__("json").loads(content)["prompt_shard"]["name"] for content in user_contents]
    assert shard_names == ["static_images_1", "static_images_2_carousel_copy"]
    assert all(len(content) <= openrouter_prompt_client.STATIC_CREATIVE_PROMPT_MAX_USER_CHARS for content in user_contents)
    assert result["static_prompt_generation"]["sharded"] is True
    assert result["static_prompt_generation"]["shard_count"] == 2
    assert result["static_prompt_generation"]["prompt_budget"]["user_chars_sent"] == max(len(content) for content in user_contents)
    assert result["static_image_ads"][0]["visual_prompt"] == "Short refined C2 prompt"
    assert result["static_image_ads"][1]["visual_prompt"] == "Short refined C3 prompt"
    assert result["static_image_ads"][2]["visual_prompt"] == "Short refined C4 prompt"
    assert result["carousel_ad"]["cards"][0]["visual_prompt"] == "Refined card one"


def test_static_prompt_merge_rejects_unverified_material_change():
    ads = {
        "static_image_ads": [
            {
                "creative_id": "C2_static_product_hero",
                "set_id": "C2",
                "visual_prompt": "Use product reference, adult hand holding the exact opaque cup.",
                "overlay_text": "Daily cup",
            }
        ],
        "carousel_ad": {"cards": []},
    }
    enhanced = {
        "static_image_ads": [
            {
                "creative_id": "C2_static_product_hero",
                "visual_prompt": "Make the cup transparent glass-like with premium glass clarity.",
            }
        ]
    }

    result = openrouter_prompt_client._merge_static_ads_prompt_enhancement(
        ads,
        enhanced,
        product_analysis={
            "product_name": "White Travel Cup",
            "known_product_facts": {"material": "opaque ceramic", "color": "white"},
            "user_provided_facts": ["opaque white cup"],
        },
    )

    assert result["static_image_ads"][0]["visual_prompt"] == "Use product reference, adult hand holding the exact opaque cup"


def test_generate_video_follows_openrouter_polling_flow(monkeypatch, tmp_path):
    calls = {"post": None, "get": []}

    def fake_post(url, json, headers, timeout):
        calls["post"] = {"url": url, "json": json, "headers": headers}
        return FakeResponse({"id": "job_1", "polling_url": "https://poll.example/job_1"})

    def fake_get(url, headers=None, timeout=None):
        calls["get"].append({"url": url, "headers": headers})
        if url == "https://poll.example/job_1":
            return FakeResponse({"status": "completed", "unsigned_urls": ["https://cdn.example/video.mp4"]})
        return FakeResponse(content=b"mp4")

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_seedance_client.requests, "get", fake_get)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={
            "model": "bytedance/seedance-2.0",
            "prompt": "A clean product UGC video",
            "duration": 15,
            "input_references": [
                {"type": "image_url", "image_url": {"url": "https://example.com/product.jpg"}}
            ],
        },
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    assert calls["post"]["url"] == "https://openrouter.ai/api/v1/videos"
    assert calls["post"]["json"] == {
        "model": "bytedance/seedance-2.0",
        "prompt": "A clean product UGC video",
        "duration": 15,
        "input_references": [
            {"type": "image_url", "image_url": {"url": "https://example.com/product.jpg"}}
        ],
    }
    assert [call["url"] for call in calls["get"]] == [
        "https://poll.example/job_1",
        "https://cdn.example/video.mp4",
    ]
    assert calls["get"][1]["headers"] is None
    assert result["video_generation_status"] == "completed"
    assert result["submitted_payload"] == calls["post"]["json"]


def test_generate_video_sends_auth_when_downloading_openrouter_content(monkeypatch, tmp_path):
    download_headers = {}

    def fake_post(url, json, headers, timeout):
        return FakeResponse({"id": "job_2", "polling_url": "https://openrouter.ai/api/v1/videos/job_2"})

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/videos/job_2"):
            return FakeResponse(
                {
                    "status": "completed",
                    "unsigned_urls": ["https://openrouter.ai/api/v1/videos/job_2/content?index=0"],
                }
            )
        download_headers.update(headers or {})
        return FakeResponse(content=b"mp4")

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_seedance_client.requests, "get", fake_get)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={"model": "bytedance/seedance-2.0-fast", "prompt": "Prompt"},
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    assert result["video_generation_status"] == "completed"
    assert download_headers["Authorization"] == "Bearer test-key"


def test_generate_video_normalizes_unsupported_aspect_ratio(monkeypatch, tmp_path):
    calls = {"post": None}

    def fake_post(url, json, headers, timeout):
        calls["post"] = json
        return FakeResponse({"id": "job_3", "polling_url": "https://poll.example/job_3"})

    def fake_get(url, headers=None, timeout=None):
        if url == "https://poll.example/job_3":
            return FakeResponse({"status": "completed", "unsigned_urls": ["https://cdn.example/video.mp4"]})
        return FakeResponse(content=b"mp4")

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_seedance_client.requests, "get", fake_get)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={
            "model": "bytedance/seedance-2.0-fast",
            "prompt": "Create a paid social video in 4:5 aspect ratio",
            "aspect_ratio": "4:5",
            "resolution": "720p",
        },
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    assert result["video_generation_status"] == "completed"
    assert calls["post"]["aspect_ratio"] == "9:16"
    assert "4:5" not in calls["post"]["prompt"]
    assert "9:16 aspect ratio" in calls["post"]["prompt"]


def test_generate_video_writes_trace(monkeypatch, tmp_path):
    def fake_post(url, json, headers, timeout):
        return FakeResponse({"id": "job_trace", "polling_url": "https://poll.example/job_trace"})

    def fake_get(url, headers=None, timeout=None):
        if url == "https://poll.example/job_trace":
            return FakeResponse({"status": "completed", "unsigned_urls": ["https://cdn.example/video.mp4"]})
        return FakeResponse(content=b"mp4")

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_seedance_client.requests, "get", fake_get)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={"model": "bytedance/seedance-2.0-fast", "prompt": "Prompt"},
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    trace = (tmp_path / "openrouter_video_trace.jsonl").read_text(encoding="utf-8")
    assert result["video_generation_status"] == "completed"
    assert "create_request" in trace
    assert "create_response" in trace


def test_generate_video_blocks_local_product_data_url_reference(monkeypatch, tmp_path):
    calls = {"post": None}

    def fake_post(url, json, headers, timeout):
        calls["post"] = json
        return FakeResponse({"id": "job_4", "polling_url": "https://poll.example/job_4"})

    def fake_get(url, headers=None, timeout=None):
        if url == "https://poll.example/job_4":
            return FakeResponse({"status": "completed", "unsigned_urls": ["https://cdn.example/video.mp4"]})
        return FakeResponse(content=b"mp4")

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_seedance_client.requests, "get", fake_get)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={
            "model": "bytedance/seedance-2.0-fast",
            "prompt": "Prompt",
            "input_references": [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/2Q=="}},
                {"type": "image_url", "image_url": {"url": "http://127.0.0.1:8000/uploads/product.jpg"}},
            ],
        },
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    assert result["video_generation_status"] == "blocked"
    assert calls["post"] is None
    assert result["provider_restriction"]["type"] == "local_product_reference_not_provider_accessible"
    assert "public HTTPS product image URL" in result["next_step"]


def test_generate_video_explains_sensitive_image_rejection(monkeypatch, tmp_path):
    def fake_post(url, json, headers, timeout):
        return FakeResponse(
            {
                "error": {
                    "message": "HTTP 400: InputImageSensitiveContentDetected.PrivacyInformation real person",
                    "code": 400,
                }
            },
            status_code=202,
        )

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={
            "model": "bytedance/seedance-2.0-fast",
            "prompt": "Prompt",
            "avatar_reference_mode": "exact_image_input_reference",
            "input_references": [
                {"type": "image_url", "image_url": {"url": "https://example.com/avatar.jpg"}}
            ],
        },
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
    )

    assert result["video_generation_status"] == "failed"
    assert "real person" in result["failure_reason"].lower()
    assert "turn off avatar image reference" in result["next_step"].lower()
    assert result["provider_restriction"]["status"] == "restricted"
    assert result["provider_restriction"]["likely_trigger"] == "avatar_reference_image"
    assert result["provider_restriction"]["can_retry_without_avatar_reference"] is True
    assert result["provider_restriction"]["retry_changes"]["use_avatar_image_reference"] is False


def test_generate_video_explains_dns_polling_failure(monkeypatch, tmp_path):
    def fake_post(url, json, headers, timeout):
        return FakeResponse({"id": "job_dns", "polling_url": "https://openrouter.ai/api/v1/videos/job_dns"})

    def fake_get(url, headers=None, timeout=None):
        raise RuntimeError("NameResolutionError: Failed to resolve 'openrouter.ai' getaddrinfo failed")

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_seedance_client.requests, "get", fake_get)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={"model": "bytedance/seedance-2.0-fast", "prompt": "Prompt"},
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    assert result["video_generation_status"] == "failed"
    assert "network/dns" in result["failure_reason"].lower()
    assert "static images may already be saved" in result["next_step"].lower()


def test_generate_video_explains_openrouter_overdue_balance(monkeypatch, tmp_path):
    def fake_post(url, json, headers, timeout):
        raise RuntimeError(
            'HTTP 403: {"error":{"code":"AccountOverdueError","message":"The request failed because your account has an overdue balance."}}'
        )

    monkeypatch.setattr(openrouter_seedance_client.requests, "post", fake_post)

    result = openrouter_seedance_client.generate_video(
        seedance_payload={"model": "bytedance/seedance-2.0-fast", "prompt": "Prompt"},
        product_name="Daily Bag",
        output_dir=tmp_path,
        api_key="test-key",
        poll_interval_seconds=0,
    )

    assert result["video_generation_status"] == "failed"
    assert "accountoverdueerror" in result["failure_reason"].lower()
    assert "usable credit" in result["failure_reason"].lower()
    assert "switch the video model" in result["next_step"].lower()
