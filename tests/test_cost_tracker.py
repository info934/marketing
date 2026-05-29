from __future__ import annotations

from app.services import cost_tracker


def test_build_session_cost_summary_sums_known_openrouter_costs():
    result = cost_tracker.build_session_cost_summary(
        content_prompt_package={
            "prompt_generation": {
                "status": "completed",
                "model": "openai/gpt-4.1-mini",
                "usage": {"cost": 0.001},
            }
        },
        static_image_generation={
            "image_generation_status": "completed",
            "model": "google/gemini-3-pro-image-preview",
            "generated_count": 2,
            "usage_records": [
                {"usage": {"cost": 0.02}},
                {"usage": {"cost": 0.03}},
            ],
        },
        video_generation={
            "video_generation_status": "completed",
            "submitted_payload": {"model": "bytedance/seedance-2.0-fast"},
            "job_id": "job_1",
            "generation_metadata": {"id": "gen_1", "total_cost": 0.5},
        },
    )

    assert result["status"] == "complete"
    assert result["version"] == "openrouter_cost_summary_v2"
    assert result["total_known_cost"] == 0.551
    assert result["total_known_cost_usd_display"] == "$0.551"
    assert result["request_count"] == 4
    assert result["unknown_cost_components"] == []


def test_build_session_cost_summary_marks_missing_provider_costs_unknown():
    result = cost_tracker.build_session_cost_summary(
        content_prompt_package={"prompt_generation": {"status": "skipped"}},
        static_image_generation={
            "image_generation_status": "completed",
            "usage_records": [{"usage": None}],
        },
        video_generation={"video_generation_status": "failed", "job_id": "job_1"},
    )

    assert result["status"] == "unknown"
    assert result["total_known_cost"] == 0.0
    assert "Static ad images" in result["unknown_cost_components"]
    assert "Seedance video" in result["unknown_cost_components"]


def test_build_session_cost_summary_includes_full_openrouter_pipeline():
    result = cost_tracker.build_session_cost_summary(
        content_prompt_package={
            "prompt_generation": {
                "status": "completed",
                "model": "openai/gpt-5.4-mini",
                "usage": {"cost": "$0.002", "prompt_tokens": 100, "completion_tokens": 40},
            }
        },
        static_image_generation={
            "image_generation_status": "completed",
            "model": "google/gemini-3-pro-image-preview",
            "usage_records": [{"usage": {"cost": 0.03}}],
            "vision_quality_status": "completed",
            "vision_model": "google/gemini-3-pro-image-preview",
            "vision_quality_checks": [
                {"creative_id": "C2", "attempt": "initial", "result": {"status": "passed", "usage": {"cost": 0.004}}}
            ],
        },
        video_generation={
            "video_generation_status": "completed",
            "submitted_payload": {"model": "bytedance/seedance-2.0-fast"},
            "job_id": "job_1",
            "generation_metadata": {"id": "gen_1", "total_cost": 0.4},
        },
        product_analysis={
            "automatic_product_understanding": {
                "ai_refinement": {"status": "completed", "model": "openai/gpt-5.4-mini", "usage": {"cost": 0.001}}
            }
        },
        input_data={
            "finance_script_agent": {
                "status": "ai_refined",
                "model": "openai/gpt-5.4-mini",
                "usage": {"cost": 0.003},
            }
        },
        self_critique={
            "ai_critique": {
                "status": "completed",
                "model": "openai/gpt-5.4-mini",
                "usage": {"cost": 0.005},
            }
        },
    )

    assert result["total_known_cost"] == 0.445
    assert result["request_count"] == 7
    assert result["by_group"]["planning"]["known_cost"] == 0.004
    assert result["by_group"]["quality"]["known_cost"] == 0.009
    assert not result["unknown_cost_components"]


def test_finance_scene_preview_cost_summary():
    result = cost_tracker.build_finance_scene_preview_cost_summary(
        finance_script_agent={
            "status": "ai_refined",
            "model": "openai/gpt-5.4-mini",
            "usage": {"cost": 0.002},
        },
        scene_image_generation={
            "image_generation_status": "completed",
            "model": "google/gemini-3-pro-image-preview",
            "usage": {"cost": 0.08},
            "image_assets": [{"image_url": "/output/scene.png"}],
        },
    )

    assert result["status"] == "complete"
    assert result["total_known_cost"] == 0.082
    assert result["request_count"] == 2
