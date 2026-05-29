from __future__ import annotations

import base64
from pathlib import Path

from app.services import openrouter_image_client
from app.services import vision_quality_client


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


def _ads_set():
    return {
        "static_image_ads": [
            {
                "creative_id": "static_side_by_side",
                "format": "Static image",
                "layout": "side-by-side comparison",
                "visual_prompt": "Use product reference, side-by-side layout",
                "overlay_text": "Before / After",
                "primary_text": "Use as context only",
                "headline": "Product detail",
                "cta": "View detail",
            }
        ],
        "carousel_ad": {"cards": []},
        "meme_style_creatives": [],
    }


def test_generate_ad_images_skips_without_api_key(tmp_path):
    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="",
    )

    assert result["image_generation_status"] == "skipped"
    assert result["failure_reason"]
    assert result["image_assets"] == []
    assert result["selected_creative_count"] == 1
    assert result["generation_plan"]
    assert result["prompt_respect_contract"]


def test_preview_ad_image_plan_uses_distinct_multiplier_angles():
    ads_set = {
        "static_image_ads": [
            {
                "creative_id": "C2_static_product_hero",
                "set_id": "C2",
                "creative_type": "Static product hero",
                "angle": "PRODUCT_HERO",
                "angle_family": "Desire",
                "angle_multiplier_angle": "Desire - daily upgrade",
                "angle_multiplier_hook": "Fits the everyday routine without looking generic.",
                "angle_diversity_contract": "C2 tests Desire with a product-first composition.",
                "format": "Static image",
                "layout": "product hero",
                "visual_prompt": "product-first hero",
                "overlay_text": "Fits real life",
                "aspect_ratio": "1:1",
            },
            {
                "creative_id": "C3_static_use_context",
                "set_id": "C3",
                "creative_type": "Static use context",
                "angle": "USE_CONTEXT",
                "angle_family": "Identity",
                "angle_multiplier_angle": "Identity - careful buyer",
                "angle_multiplier_hook": "For people who check the details first.",
                "angle_diversity_contract": "C3 tests Identity in a use-context frame.",
                "format": "Static image",
                "layout": "use context",
                "visual_prompt": "everyday use context",
                "overlay_text": "For detail people",
                "aspect_ratio": "1:1",
            },
            {
                "creative_id": "C4_static_detail_proof",
                "set_id": "C4",
                "creative_type": "Static proof detail",
                "angle": "DETAIL_PROOF",
                "angle_family": "Proof",
                "angle_multiplier_angle": "Proof - detail before deciding",
                "angle_multiplier_hook": "Look closer at the visible material.",
                "angle_diversity_contract": "C4 tests Proof with a macro crop.",
                "format": "Static image",
                "layout": "macro proof",
                "visual_prompt": "macro detail proof",
                "overlay_text": "Look closer",
                "aspect_ratio": "1:1",
            },
        ],
        "carousel_ad": {
            "set_id": "C5",
            "creative_type": "Carousel buying guide",
            "angle": "BUYING_GUIDE",
            "cards": [
                {
                    "card_number": 1,
                    "role": "hero_frame",
                    "visual_prompt": "buying guide hero card",
                    "overlay_text": "Before choosing",
                    "angle_family": "Pain",
                    "angle_multiplier_angle": "Pain - missing detail",
                    "angle_multiplier_hook": "Before choosing, check the detail most ads skip.",
                    "angle_diversity_contract": "C5 card tests Pain as a buying-guide opener.",
                }
            ],
        },
        "meme_style_creatives": [],
    }

    result = openrouter_image_client.preview_ad_image_plan(
        ads_creative_set=ads_set,
        product_reference_url="https://example.com/product.jpg",
        max_images=4,
    )

    angle_labels = [item["angle"] for item in result["selected"]]
    assert angle_labels == [
        "Desire - daily upgrade",
        "Identity - careful buyer",
        "Proof - detail before deciding",
        "Pain - missing detail",
    ]
    assert result["selected"][0]["slot_angle"] == "PRODUCT_HERO"
    assert result["selected"][0]["angle_family"] == "Desire"
    assert "Distinct marketing angle" in result["selected"][0]["prompt_preview"]
    assert "Angle diversity contract" in result["selected"][0]["prompt_preview"]


def test_generate_ad_images_saves_openrouter_data_url(monkeypatch, tmp_path):
    calls = {}
    encoded = base64.b64encode(b"png-bytes").decode("ascii")

    def fake_post(url, headers, json, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{encoded}"},
                                }
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        model="google/gemini-3-pro-image-preview",
        product_reference_url="https://example.com/product.jpg",
        max_images=1,
        image_size="2K",
    )

    asset_path = Path(result["image_assets"][0]["image_path"])
    assert calls["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls["headers"]["Authorization"] == "Bearer test-key"
    assert calls["json"]["model"] == "google/gemini-3-pro-image-preview"
    assert calls["json"]["modalities"] == ["image", "text"]
    assert "Generate exactly one image" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "Realism requirement" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "Human/product context requirement" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "Static creative v2 requirement" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "Variation contract" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "Creative-set diversity rule" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "adult person" in calls["json"]["messages"][0]["content"][0]["text"]
    assert "real photograph from a real camera" in calls["json"]["messages"][0]["content"][0]["text"]
    assert calls["json"]["image_config"] == {"aspect_ratio": "1:1", "image_size": "2K"}
    assert calls["json"]["messages"][0]["content"][1]["image_url"]["url"] == "https://example.com/product.jpg"
    assert result["image_generation_status"] == "completed"
    assert result["image_assets"][0]["image_url"].startswith("/output/")
    assert asset_path.exists()
    assert asset_path.read_bytes() == b"png-bytes"


def test_generate_ad_images_explains_openrouter_overdue_balance(monkeypatch, tmp_path):
    def fake_post(url, headers, json, timeout):
        raise RuntimeError(
            'HTTP 403: {"error":{"code":"AccountOverdueError","message":"The request failed because your account has an overdue balance."}}'
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        model="google/gemini-3-pro-image-preview",
        product_reference_url="https://example.com/product.jpg",
        max_images=1,
    )

    assert result["image_generation_status"] == "failed"
    assert "accountoverdueerror" in result["failure_reason"].lower()
    assert "usable credit" in result["failure_reason"].lower()
    assert "switch image model" in result["next_step"].lower()


def test_render_image_prompt_locks_handbag_scale():
    prompt = openrouter_image_client._render_image_prompt(
        {
            "creative_id": "C3_static_lifestyle_identity",
            "asset_type": "static_image",
            "set_id": "C3",
            "creative_type": "Static lifestyle",
            "angle": "IDENTITY",
            "format": "Static image",
            "layout": "handbag lifestyle",
            "visual_prompt": "adult person carrying the shoulder bag on shoulder",
            "overlay_text": "Fits the routine",
            "primary_text": "This bag shown in a real outfit context.",
            "aspect_ratio": "1:1",
            "product_reference_url": "https://example.com/bag.jpg",
        }
    )

    assert "Handbag scale consistency is mandatory" in prompt
    assert "same bag size relative to adult torso" in prompt
    assert "do not transform the bag into a mini bag" in prompt
    assert "Dropshipping static realism guard" in prompt
    assert "buyer-proof product check" in prompt
    assert "not a polished catalogue render" in prompt
    assert "Static no-text rule" in prompt
    assert "Fits the routine" not in prompt
    assert "This bag shown in a real outfit context." not in prompt


def test_render_image_prompt_locks_static_material_and_opacity():
    prompt = openrouter_image_client._render_image_prompt(
        {
            "creative_id": "C2_static_product_hero",
            "asset_type": "static_image",
            "set_id": "C2",
            "creative_type": "Static product hero",
            "angle": "PRODUCT_HERO",
            "format": "Static image",
            "layout": "cup hero",
            "visual_prompt": "adult hand holding the cup near a kitchen counter",
            "overlay_text": "Daily cup",
            "primary_text": "Simple cup detail.",
            "aspect_ratio": "1:1",
            "product_reference_url": "https://example.com/cup.jpg",
            "product_material_fidelity_lock": (
                "Static product material/opacity lock: verified material=opaque ceramic. "
                "Do not make an opaque product transparent."
            ),
        }
    )

    assert "Static image material fidelity lock" in prompt
    assert "Product-specific material/opacity lock" in prompt
    assert "verified material=opaque ceramic" in prompt
    assert "Do not make an opaque product transparent" in prompt


def test_render_image_prompt_includes_static_visual_classifier_directive():
    prompt = openrouter_image_client._render_image_prompt(
        {
            "creative_id": "C2_static_product_hero",
            "asset_type": "static_image",
            "set_id": "C2",
            "creative_type": "Static product hero",
            "angle": "PRODUCT_HERO",
            "format": "Static image",
            "layout": "apparel hero",
            "visual_prompt": "adult person wearing the garment in a real doorway",
            "overlay_text": "See the cut",
            "primary_text": "Show worn fit context.",
            "aspect_ratio": "1:1",
            "product_reference_url": "https://example.com/jumpsuit.jpg",
            "static_visual_classifier_directive": (
                "Detected product appears to be wide-leg jumpsuit. "
                "Required static shots: full-body or near-full-body worn proof; hem and drape detail."
            ),
        }
    )

    assert "Visual classifier static directive" in prompt
    assert "full-body or near-full-body worn proof" in prompt
    assert "never render classifier words as visible image text" in prompt


def test_render_image_prompt_compresses_oversized_agent_prompt():
    prompt = openrouter_image_client._render_image_prompt(
        {
            "creative_id": "C2_static_lifestyle_pain",
            "asset_type": "static_image",
            "set_id": "C2",
            "creative_type": "Static lifestyle",
            "angle": "PAIN",
            "format": "Static image",
            "layout": "handbag lifestyle " * 500,
            "visual_prompt": "adult person carrying the shoulder bag on shoulder in a real scene " * 900,
            "overlay_text": "Check scale first",
            "primary_text": "Context copy " * 900,
            "aspect_ratio": "1:1",
            "product_reference_url": "https://example.com/bag.jpg",
        }
    )

    assert len(prompt) <= openrouter_image_client.IMAGE_PROMPT_MAX_CHARS
    assert "Prompt compression applied" in prompt
    assert "Handbag scale consistency is mandatory" in prompt
    assert "Human/product context requirement" in prompt
    assert "Static creative v2 requirement" in prompt
    assert "Dropshipping static realism guard" in prompt
    assert "Static no-text rule" in prompt
    assert "post-production metadata only" in prompt
    assert "Render this overlay text" not in prompt
    assert "Check scale first" not in prompt


def test_generate_ad_images_sends_local_product_upload_as_data_url(monkeypatch, tmp_path):
    calls = {}
    product_image = tmp_path / "product.png"
    product_image.write_bytes(b"local-product")
    encoded = base64.b64encode(b"generated").decode("ascii")

    def fake_post(url, headers, json, timeout):
        calls["json"] = json
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [
                                {"image_url": {"url": f"data:image/png;base64,{encoded}"}},
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        product_reference_url=str(product_image),
        max_images=1,
    )

    image_input = calls["json"]["messages"][0]["content"][1]["image_url"]["url"]
    assert image_input.startswith("data:image/png;base64,")
    assert base64.b64decode(image_input.split(",", 1)[1]) == b"local-product"
    assert result["image_generation_status"] == "completed"


def test_generate_ad_images_sends_extra_static_reference_images(monkeypatch, tmp_path):
    calls = {}
    primary = tmp_path / "primary.png"
    variant = tmp_path / "variant.png"
    primary.write_bytes(b"primary-product")
    variant.write_bytes(b"variant-product")
    encoded = base64.b64encode(b"generated").decode("ascii")

    def fake_post(url, headers, json, timeout):
        calls["json"] = json
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [
                                {"image_url": {"url": f"data:image/png;base64,{encoded}"}},
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        product_reference_url=str(primary),
        reference_image_urls=[str(variant)],
        max_images=1,
    )

    content = calls["json"]["messages"][0]["content"]
    assert len([item for item in content if item["type"] == "image_url"]) == 2
    assert base64.b64decode(content[2]["image_url"]["url"].split(",", 1)[1]) == b"variant-product"
    assert "Additional static-only product reference images" in content[0]["text"]
    assert result["reference_image_count"] == 2


def test_generate_ad_images_uses_max_images_as_cap_without_padding(monkeypatch, tmp_path):
    calls = []
    encoded = base64.b64encode(b"generated").decode("ascii")
    ads = {
        "static_image_ads": [
            {"creative_id": f"static_{index}", "visual_prompt": f"static {index}", "overlay_text": f"static {index}"}
            for index in range(3)
        ],
        "carousel_ad": {
            "cards": [
                {"card_number": index, "role": "benefit", "visual_prompt": f"carousel {index}", "overlay_text": f"carousel {index}"}
                for index in range(1, 6)
            ]
        },
        "meme_style_creatives": [
            {"creative_id": f"meme_{index}", "visual_prompt": "meme", "copy": "meme"}
            for index in range(2)
        ],
    }

    def fake_post(url, headers, json, timeout):
        calls.append(json["messages"][0]["content"][0]["text"])
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [{"image_url": {"url": f"data:image/png;base64,{encoded}"}}]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=ads,
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        max_images=7,
        include_meme_images=True,
    )

    assert result["attempted_count"] == 7
    assert result["selected_creative_count"] == 7
    assert result["max_images_policy"] == "cap_only_no_padding"
    assert "never pads" in result["max_images_policy_note"]
    assert [asset["creative_id"] for asset in result["image_assets"]] == [
        "static_0",
        "static_1",
        "static_2",
        "carousel_card_1",
        "carousel_card_2",
        "carousel_card_3",
        "carousel_card_4",
    ]
    assert {asset["asset_type"] for asset in result["image_assets"]} == {"static_image", "carousel_card"}
    assert any(item["creative_id"] == "carousel_card_5" for item in result["skipped_creatives"])
    assert any(item["creative_id"] == "meme_0" for item in result["skipped_creatives"])


def test_generate_ad_images_defaults_to_media_plan_scope_without_memes(monkeypatch, tmp_path):
    calls = []
    encoded = base64.b64encode(b"generated").decode("ascii")
    ads = {
        "static_image_ads": [
            {"creative_id": "C2_static", "set_id": "C2", "visual_prompt": "static", "overlay_text": "static"}
        ],
        "carousel_ad": {
            "set_id": "C5",
            "cards": [
                {"card_number": 1, "role": "hook", "visual_prompt": "carousel", "overlay_text": "carousel"}
            ],
        },
        "meme_style_creatives": [
            {"creative_id": "meme_1", "visual_prompt": "meme", "copy": "meme"}
        ],
    }

    def fake_post(url, headers, json, timeout):
        calls.append(json["messages"][0]["content"][0]["text"])
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [{"image_url": {"url": f"data:image/png;base64,{encoded}"}}]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=ads,
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        max_images=10,
    )

    assert result["attempted_count"] == 2
    assert result["selected_creative_count"] == 2
    assert result["api_request_count"] == 2
    assert {asset["asset_type"] for asset in result["image_assets"]} == {"static_image", "carousel_card"}
    assert any(item["asset_type"] == "meme_style_static" for item in result["skipped_creatives"])
    assert "meme" not in "\n".join(calls).lower()


def test_generate_ad_images_reuses_duplicate_prompts(monkeypatch, tmp_path):
    calls = []
    encoded = base64.b64encode(b"deduped").decode("ascii")
    ads = {
        "static_image_ads": [
            {
                "creative_id": "static_a",
                "format": "Static image",
                "layout": "detail",
                "visual_prompt": "same visual",
                "overlay_text": "same overlay",
                "primary_text": "same context",
                "headline": "same headline",
                "cta": "View",
            },
            {
                "creative_id": "static_b",
                "format": "Static image",
                "layout": "detail",
                "visual_prompt": "same visual",
                "overlay_text": "same overlay",
                "primary_text": "same context",
                "headline": "same headline",
                "cta": "View",
            },
        ],
        "carousel_ad": {"cards": []},
        "meme_style_creatives": [],
    }

    def fake_post(url, headers, json, timeout):
        calls.append(json["messages"][0]["content"][0]["text"])
        return FakeResponse(
            {
                "id": "gen_1",
                "choices": [
                    {
                        "message": {
                            "images": [{"image_url": {"url": f"data:image/png;base64,{encoded}"}}]
                        }
                    }
                ],
                "usage": {"cost": 0.01},
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=ads,
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        product_reference_url="https://example.com/product.jpg",
        max_images=2,
    )

    assert len(calls) == 1
    assert result["api_request_count"] == 1
    assert result["attempted_count"] == 2
    assert result["generated_count"] == 1
    assert result["asset_count"] == 1
    assert result["reused_count"] == 0
    assert len(result["usage_records"]) == 1
    assert len(result["duplicate_skips"]) == 1
    assert result["image_assets"][0]["generation_reused"] is False
    assert result["duplicate_skips"][0]["duplicate_of_creative_id"] == "static_a"
    assert result["duplicate_skips"][0]["would_reuse_image_path"] == result["image_assets"][0]["image_path"]


def test_generate_ad_images_saves_one_asset_per_creative_when_provider_returns_multiple(monkeypatch, tmp_path):
    encoded_a = base64.b64encode(b"first").decode("ascii")
    encoded_b = base64.b64encode(b"second").decode("ascii")

    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [
                                {"image_url": {"url": f"data:image/png;base64,{encoded_a}"}},
                                {"image_url": {"url": f"data:image/png;base64,{encoded_b}"}},
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        max_images=1,
    )

    assert result["api_request_count"] == 1
    assert result["asset_count"] == 1
    assert result["generated_count"] == 1
    assert Path(result["image_assets"][0]["image_path"]).read_bytes() == b"first"


def test_generate_ad_images_retries_once_after_vision_quality_fail(monkeypatch, tmp_path):
    calls = []
    encoded_first = base64.b64encode(b"first").decode("ascii")
    encoded_retry = base64.b64encode(b"retry").decode("ascii")
    quality_calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json["messages"][0]["content"][0]["text"])
        encoded = encoded_first if len(calls) == 1 else encoded_retry
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [{"image_url": {"url": f"data:image/png;base64,{encoded}"}}]
                        }
                    }
                ]
            }
        )

    def fake_score(**kwargs):
        quality_calls.append(kwargs["generated_image_path"])
        if len(quality_calls) == 1:
            return {
                "status": "failed",
                "product_fidelity": {"shape_match": 50, "color_match": 90, "branding_match": 90, "material_finish_match": 80},
                "human_realism": {"overall": 85, "hands_fingers": 85, "anatomy": 85, "lighting_realism": 85},
                "regeneration_required": True,
                "regeneration_prompt_addendum": "fix shape match",
            }
        return {
            "status": "passed",
            "product_fidelity": {"shape_match": 92, "color_match": 91, "branding_match": 100, "material_finish_match": 88},
            "human_realism": {"overall": 90, "hands_fingers": 89, "anatomy": 90, "lighting_realism": 90},
            "regeneration_required": False,
            "regeneration_prompt_addendum": "",
        }

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_image_client.vision_quality_client, "score_generated_asset", fake_score)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        product_reference_url="https://example.com/product.jpg",
        max_images=2,
        enable_vision_quality_check=True,
        vision_retry_on_fail=True,
    )

    assert result["api_request_count"] == 2
    assert result["regeneration_attempts"] == 1
    assert result["vision_quality_status"] == "completed_with_regeneration"
    assert len(result["vision_quality_rejections"]) == 1
    assert len(result["image_assets"]) == 1
    assert result["image_assets"][0]["regenerated_after_vision_quality_fail"] is True
    assert "fix shape match" in calls[1]
    assert Path(result["image_assets"][0]["image_path"]).read_bytes() == b"retry"


def test_generate_ad_images_does_not_retry_past_max_images_cap(monkeypatch, tmp_path):
    calls = []
    encoded = base64.b64encode(b"first").decode("ascii")

    def fake_post(url, headers, json, timeout):
        calls.append(json["messages"][0]["content"][0]["text"])
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "images": [{"image_url": {"url": f"data:image/png;base64,{encoded}"}}]
                        }
                    }
                ]
            }
        )

    def fake_score(**kwargs):
        return {
            "status": "failed",
            "product_fidelity": {"shape_match": 50, "color_match": 90, "branding_match": 90, "material_finish_match": 80},
            "human_realism": {"overall": 85, "hands_fingers": 85, "anatomy": 85, "lighting_realism": 85},
            "regeneration_required": True,
            "regeneration_prompt_addendum": "fix shape match",
        }

    monkeypatch.setattr(openrouter_image_client.requests, "post", fake_post)
    monkeypatch.setattr(openrouter_image_client.vision_quality_client, "score_generated_asset", fake_score)

    result = openrouter_image_client.generate_ad_images(
        ads_creative_set=_ads_set(),
        product_name="Desk Lamp",
        output_dir=tmp_path,
        api_key="test-key",
        product_reference_url="https://example.com/product.jpg",
        max_images=1,
        enable_vision_quality_check=True,
        vision_retry_on_fail=True,
    )

    assert result["api_request_count"] == 1
    assert result["regeneration_attempts"] == 0
    assert len(calls) == 1
    assert len(result["image_assets"]) == 1
    assert not result["image_assets"][0].get("regenerated_after_vision_quality_fail")
    assert Path(result["image_assets"][0]["image_path"]).read_bytes() == b"first"


def test_vision_quality_ignores_unexplained_retry_when_scores_pass():
    result = vision_quality_client._normalize_score(
        {
            "status": "failed",
            "product_fidelity": {
                "shape_match": 100,
                "color_match": 100,
                "branding_match": 100,
                "material_finish_match": 100,
                "notes": [],
            },
            "human_realism": {
                "overall": 100,
                "face_artifacts": 0,
                "hands_fingers": 0,
                "anatomy": 100,
                "lighting_realism": 100,
                "reflection_realism": 100,
                "skin_texture": 100,
                "non_applicable": False,
                "notes": [],
            },
            "regeneration_required": True,
            "regeneration_prompt_addendum": "",
        }
    )

    assert result["status"] == "passed"
    assert result["regeneration_required"] is False
    assert result["model_retry_ignored"] is True


def test_vision_quality_still_regenerates_for_low_core_score():
    result = vision_quality_client._normalize_score(
        {
            "status": "failed",
            "product_fidelity": {
                "shape_match": 100,
                "color_match": 100,
                "branding_match": 0,
                "material_finish_match": 100,
                "notes": ["Visible tongue branding is missing."],
            },
            "human_realism": {
                "overall": 95,
                "hands_fingers": 95,
                "anatomy": 95,
                "lighting_realism": 95,
                "non_applicable": False,
                "notes": [],
            },
            "regeneration_required": True,
            "regeneration_prompt_addendum": "Ensure the visible tongue branding is present.",
        }
    )

    assert result["status"] == "failed"
    assert result["regeneration_required"] is True
    assert result["model_retry_ignored"] is False
