from __future__ import annotations

from typing import Any


def strict_response_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": True,
            "schema": schema,
        },
    }


def _string(max_length: int | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string"}
    if max_length:
        schema["maxLength"] = max_length
    return schema


def _string_array(max_items: int = 12, max_length: int = 220) -> dict[str, Any]:
    return {
        "type": "array",
        "maxItems": max_items,
        "items": _string(max_length),
    }


CAMPAIGN_DRAFT_FIELD_NAMES = [
    "product_name",
    "product_info",
    "product_reference_url",
    "competitor_strategy_enabled",
    "competitor_name",
    "competitor_url",
    "competitor_chat_brief",
    "avatar_reference_url",
    "custom_avatar_persona",
    "avatar_identity_note",
    "ugc_video_extra_prompt",
    "platform",
    "market",
    "language",
    "generation_mode",
]


CHAT_BRIEF_PARSER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["campaign_draft", "attachment_roles", "field_sources", "warnings"],
    "properties": {
        "campaign_draft": {
            "type": "object",
            "additionalProperties": False,
            "required": CAMPAIGN_DRAFT_FIELD_NAMES,
            "properties": {
                "product_name": _string(120),
                "product_info": _string(4000),
                "product_reference_url": _string(500),
                "competitor_strategy_enabled": {"type": "boolean"},
                "competitor_name": _string(120),
                "competitor_url": _string(500),
                "competitor_chat_brief": _string(5000),
                "avatar_reference_url": _string(500),
                "custom_avatar_persona": _string(1200),
                "avatar_identity_note": _string(1200),
                "ugc_video_extra_prompt": _string(3500),
                "platform": _string(40),
                "market": _string(20),
                "language": _string(20),
                "generation_mode": _string(20),
            },
        },
        "attachment_roles": {
            "type": "array",
            "maxItems": 30,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item_id", "role", "reason"],
                "properties": {
                    "item_id": _string(80),
                    "role": {"type": "string", "enum": ["product", "competitor", "avatar", "direction"]},
                    "reason": _string(180),
                },
            },
        },
        "field_sources": {
            "type": "object",
            "additionalProperties": False,
            "required": CAMPAIGN_DRAFT_FIELD_NAMES,
            "properties": {field: _string(80) for field in CAMPAIGN_DRAFT_FIELD_NAMES},
        },
        "warnings": _string_array(12, 220),
    },
}


PRODUCT_UNDERSTANDING_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "category",
        "category_confidence",
        "material",
        "style",
        "style_tags",
        "market_position",
        "target_audience",
        "usage_contexts",
        "season",
        "fashion_style",
        "prompt_grounding_details",
        "creative_implications",
    ],
    "properties": {
        "category": {
            "type": "string",
            "enum": ["handbag", "shoes", "apparel", "beauty", "home", "electronics", "unknown"],
        },
        "category_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "material": _string(160),
        "style": _string(220),
        "style_tags": _string_array(8, 80),
        "market_position": {
            "type": "string",
            "enum": ["value", "mid-market", "mid-premium", "premium-coded", "unknown"],
        },
        "target_audience": _string(240),
        "usage_contexts": _string_array(8, 120),
        "season": {
            "type": "string",
            "enum": ["all-season", "spring", "summer", "autumn", "winter", "unknown"],
        },
        "fashion_style": _string(180),
        "prompt_grounding_details": _string_array(10, 140),
        "creative_implications": _string_array(8, 180),
    },
}

VISUAL_PRODUCT_CLASSIFIER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "detected_object",
        "category",
        "subcategory",
        "category_confidence",
        "visual_evidence",
        "reference_style",
        "recommended_template_id",
        "scenario_rules",
        "shot_requirements",
        "avoid_in_generation",
        "qa_expectations",
    ],
    "properties": {
        "detected_object": _string(120),
        "category": {
            "type": "string",
            "enum": ["handbag", "shoes", "apparel", "beauty", "home", "electronics", "unknown"],
        },
        "subcategory": _string(120),
        "category_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "visual_evidence": _string_array(8, 140),
        "reference_style": {
            "type": "string",
            "enum": ["packshot", "catalog_model", "lifestyle", "closeup_detail", "unclear"],
        },
        "recommended_template_id": {
            "type": "string",
            "enum": [
                "apparel_try_on_full_body",
                "worn_footwear_check",
                "carry_capacity_check",
                "creator_connected_lifestyle",
                "product_unboxing",
                "talking_head_product_check",
                "app_promo",
            ],
        },
        "scenario_rules": _string_array(8, 180),
        "shot_requirements": _string_array(8, 180),
        "avoid_in_generation": _string_array(8, 180),
        "qa_expectations": _string_array(8, 180),
    },
}


SCENE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "scene_id",
        "purpose",
        "duration",
        "avatar_on_camera",
        "use_reference_image",
        "reference_image_source",
        "avatar_instruction",
        "scene_summary",
        "fidelity",
        "voiceover",
        "on_screen_text",
        "framing_notes",
        "continuity_notes",
        "environment_notes",
    ],
    "properties": {
        "scene_id": _string(20),
        "purpose": _string(60),
        "duration": {"type": "integer", "minimum": 1, "maximum": 30},
        "avatar_on_camera": {"type": "boolean"},
        "use_reference_image": {"type": "boolean"},
        "reference_image_source": {
            "type": "string",
            "enum": ["original_avatar", "previous_scene_last_frame", "product_reference", "none"],
        },
        "avatar_instruction": _string(900),
        "scene_summary": _string(1100),
        "fidelity": _string(800),
        "voiceover": _string(420),
        "on_screen_text": {
            "type": "object",
            "additionalProperties": False,
            "required": ["text", "position"],
            "properties": {
                "text": _string(48),
                "position": _string(60),
            },
        },
        "framing_notes": _string(900),
        "continuity_notes": {
            "type": "object",
            "additionalProperties": False,
            "required": ["last_frame_capture", "next_scene_start", "motion_bridge"],
            "properties": {
                "last_frame_capture": _string(260),
                "next_scene_start": _string(260),
                "motion_bridge": _string(260),
            },
        },
        "environment_notes": _string(900),
    },
}


SCENARIO_WRITER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["variants"],
    "properties": {
        "variants": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "variant_id",
                    "total_duration_seconds",
                    "language",
                    "market",
                    "platform",
                    "aspect_ratio",
                    "seedance_mode",
                    "reference_image_strategy",
                    "environment_control",
                    "approved_scene_concept",
                    "scenes",
                    "stitching",
                    "safety_rewrites",
                    "hypothesis",
                ],
                "properties": {
                    "variant_id": _string(40),
                    "total_duration_seconds": {"type": "integer", "minimum": 1, "maximum": 60},
                    "language": _string(20),
                    "market": _string(30),
                    "platform": _string(40),
                    "aspect_ratio": _string(20),
                    "seedance_mode": _string(60),
                    "reference_image_strategy": _string(180),
                    "environment_control": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "background_consistency",
                            "environment_override",
                            "preserve_original_scene_layout",
                            "environment_selection",
                            "directive",
                        ],
                        "properties": {
                            "background_consistency": _string(40),
                            "environment_override": {"type": "boolean"},
                            "preserve_original_scene_layout": {"type": "boolean"},
                            "environment_selection": _string(80),
                            "directive": _string(600),
                        },
                    },
                    "approved_scene_concept": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "properties": {},
                    },
                    "scenes": {"type": "array", "minItems": 1, "maxItems": 8, "items": SCENE_SCHEMA},
                    "stitching": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["transition_style", "cut_timing_notes"],
                        "properties": {
                            "transition_style": _string(180),
                            "cut_timing_notes": _string(360),
                        },
                    },
                    "safety_rewrites": _string_array(8, 240),
                    "hypothesis": _string(420),
                },
            },
        },
    },
}


def _google_text_items(max_items: int, max_length: int) -> dict[str, Any]:
    return {
        "type": "array",
        "maxItems": max_items,
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {"text": _string(max_length)},
        },
    }


ADS_CREATIVE_SET_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "creative_angles",
        "hook_bank",
        "static_image_ads",
        "carousel_ad",
        "meme_style_creatives",
        "primary_text_variants",
        "ad_description_suggestions",
        "google_ads_assets",
    ],
    "properties": {
        "creative_angles": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["angle", "motivation", "hook", "variation_rule"],
                "properties": {
                    "angle": _string(120),
                    "motivation": _string(260),
                    "hook": _string(140),
                    "variation_rule": _string(220),
                },
            },
        },
        "hook_bank": {
            "type": "array",
            "maxItems": 16,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["pattern", "hook"],
                "properties": {"pattern": _string(120), "hook": _string(140)},
            },
        },
        "static_image_ads": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["creative_id", "layout", "visual_prompt", "overlay_text", "primary_text", "headline"],
                "properties": {
                    "creative_id": _string(80),
                    "layout": _string(160),
                    "visual_prompt": _string(700),
                    "overlay_text": _string(48),
                    "primary_text": _string(520),
                    "headline": _string(64),
                },
            },
        },
        "carousel_ad": {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary_text", "cards"],
            "properties": {
                "primary_text": _string(520),
                "cards": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["card_number", "visual_prompt", "overlay_text"],
                        "properties": {
                            "card_number": {"type": "integer", "minimum": 1, "maximum": 12},
                            "visual_prompt": _string(700),
                            "overlay_text": _string(48),
                        },
                    },
                },
            },
        },
        "meme_style_creatives": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["creative_id", "layout", "visual_prompt", "copy", "fatigue_note"],
                "properties": {
                    "creative_id": _string(80),
                    "layout": _string(160),
                    "visual_prompt": _string(700),
                    "copy": _string(260),
                    "fatigue_note": _string(240),
                },
            },
        },
        "primary_text_variants": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["framework", "primary_text"],
                "properties": {"framework": _string(80), "primary_text": _string(520)},
            },
        },
        "ad_description_suggestions": {
            "type": "object",
            "additionalProperties": False,
            "required": ["usage_note", "variants"],
            "properties": {
                "usage_note": _string(220),
                "variants": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["variant_id", "primary_text", "headline", "description", "hypothesis"],
                        "properties": {
                            "variant_id": _string(80),
                            "primary_text": _string(520),
                            "headline": _string(64),
                            "description": _string(90),
                            "hypothesis": _string(240),
                        },
                    },
                },
            },
        },
        "google_ads_assets": {
            "type": "object",
            "additionalProperties": False,
            "required": ["responsive_search_ad", "performance_max"],
            "properties": {
                "responsive_search_ad": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["headlines", "descriptions"],
                    "properties": {
                        "headlines": _google_text_items(15, 30),
                        "descriptions": _google_text_items(4, 90),
                    },
                },
                "performance_max": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["headlines", "long_headlines", "descriptions"],
                    "properties": {
                        "headlines": _google_text_items(15, 30),
                        "long_headlines": _google_text_items(5, 90),
                        "descriptions": _google_text_items(5, 90),
                    },
                },
            },
        },
    },
}


CHAT_BRIEF_PARSER_RESPONSE_FORMAT = strict_response_format(
    "chat_brief_parser", CHAT_BRIEF_PARSER_SCHEMA
)
PRODUCT_UNDERSTANDING_RESPONSE_FORMAT = strict_response_format(
    "product_understanding", PRODUCT_UNDERSTANDING_SCHEMA
)
VISUAL_PRODUCT_CLASSIFIER_RESPONSE_FORMAT = strict_response_format(
    "visual_product_classifier", VISUAL_PRODUCT_CLASSIFIER_SCHEMA
)
SCENARIO_WRITER_RESPONSE_FORMAT = strict_response_format(
    "scenario_writer", SCENARIO_WRITER_SCHEMA
)
ADS_CREATIVE_SET_RESPONSE_FORMAT = strict_response_format(
    "ads_creative_set_enhancer", ADS_CREATIVE_SET_SCHEMA
)
