from __future__ import annotations

from pathlib import Path
import json
import os
import time

from fastapi.testclient import TestClient

from app import config
from app import main as main_module
from app.main import app
from app.services import (
    creative_memory_db,
    generation_run_repository,
    image_reference_utils,
    openrouter_image_client,
    performance_memory,
)


def _configure_tmp_dirs(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    output_dir = tmp_path / "output"
    monkeypatch.setattr(config, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(config, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(performance_memory, "MEMORY_PATH", tmp_path / "performance_memory.json")
    monkeypatch.setattr(config, "CREATIVE_MEMORY_DB_PATH", tmp_path / "creative_memory.sqlite")
    monkeypatch.setattr(config, "COMPANY_DATA_PATH", tmp_path / "companies.json")
    return upload_dir, output_dir


def _image_file():
    return {"product_image": ("product.jpg", b"fake-image", "image/jpeg")}


def test_planning_watchdog_uses_fallback_on_timeout():
    result = main_module._run_planning_call_with_watchdog(
        lambda: time.sleep(0.2),
        fallback=lambda: {"status": "fallback"},
        timeout_seconds=0,
        label="test_watchdog",
    )

    assert result == {"status": "fallback"}


def test_brief_intake_phase_keeps_brand_static_refs_and_visual_output(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    product_image = tmp_path / "product.jpg"
    static_ref = tmp_path / "static-angle.jpg"
    product_image.write_bytes(b"fake-product")
    static_ref.write_bytes(b"fake-static")
    run = generation_run_repository.create_run(
        workspace="ecommerce",
        app_mode="ecommerce",
        input_snapshot={"product_name": "The Roomiest Bum Bag"},
        output_dir=str(tmp_path),
    )

    def run_immediately(task, *, fallback, timeout_seconds, label):
        return task()

    def fake_analyse(input_data, image_path):
        return {
            "product_name": input_data["product_name"],
            "likely_product_category": "unknown",
            "received_image_path": str(image_path),
        }

    def fake_enrich(*, product_analysis, settings, api_key, model):
        enriched = {**product_analysis}
        enriched["automatic_product_understanding"] = {"status": "ok", "source": "unit_test"}
        enriched["understanding_model"] = model
        enriched["understanding_api_key"] = api_key
        return enriched

    def fake_classify(**kwargs):
        assert kwargs["product_analysis"]["static_product_reference_count"] == 1
        return {"status": "ok", "reason": "matched", "recommended_category": "handbag"}

    def fake_apply(product_analysis, visual_product_understanding):
        enriched = {**product_analysis}
        enriched["visual_product_understanding"] = visual_product_understanding
        return enriched

    monkeypatch.setattr(main_module, "_run_planning_call_with_watchdog", run_immediately)
    monkeypatch.setattr(main_module.product_intake_agent, "analyse", fake_analyse)
    monkeypatch.setattr(main_module.product_understanding_agent, "enrich", fake_enrich)
    monkeypatch.setattr(main_module.visual_product_classifier_agent, "classify", fake_classify)
    monkeypatch.setattr(main_module.visual_product_classifier_agent, "apply_to_product_analysis", fake_apply)

    result = main_module._run_brief_intake_phase(
        run_id=run["run_id"],
        input_data={"product_name": "The Roomiest Bum Bag"},
        product_image_path=product_image,
        saved_static_product_image_paths=[static_ref],
        company_ctx={"company_id": "kimlondon", "company_name": "Kimlondon"},
        brand_context_text_value="UK dropshipping fashion brand.",
        settings={"ad_vertical": "fashion_ecommerce"},
        openrouter_api_key="test-key",
        prompt_model="test-prompt-model",
    )

    assert result["company_profile"]["company_name"] == "Kimlondon"
    assert result["brand_context"] == "UK dropshipping fashion brand."
    assert result["ad_vertical"] == "fashion_ecommerce"
    assert result["static_product_reference_paths"] == [str(static_ref)]
    assert result["static_product_reference_count"] == 1
    assert result["understanding_model"] == "test-prompt-model"
    assert result["understanding_api_key"] == "test-key"
    assert result["visual_product_understanding"]["recommended_category"] == "handbag"

    saved_run = generation_run_repository.get_run(run["run_id"])
    assert [stage["stage"] for stage in saved_run["stage_results"]] == [
        "product_intake",
        "product_understanding",
        "product_understanding_done",
        "visual_product_classifier",
        "visual_product_classifier_done",
    ]


def test_orchestrator_exposes_simple_pipeline_and_specialist_skills(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/orchestrator")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "creative_orchestrator_v1"
    assert [phase["id"] for phase in payload["phases"]] == ["brief", "strategy", "plan", "generate", "review"]
    specialist_ids = {specialist["id"] for specialist in payload["specialists"]}
    assert {"ugc_video_scenarios", "static_ad_concepts", "scenario_integrity"} <= specialist_ids
    plan_phase = next(phase for phase in payload["phases"] if phase["id"] == "plan")
    assert {specialist["id"] for specialist in plan_phase["specialists"]} >= {"ugc_video_scenarios", "static_ad_concepts"}
    assert payload["current_phase"] == "brief"


def test_avatar_upload_returns_local_preview_without_inheriting_default_url(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "AVATAR_DATA_PATH", tmp_path / "avatars.json")
    client = TestClient(app)

    response = client.post(
        "/avatars/upload",
        files={"avatar_image": ("creator.png", b"fake-avatar", "image/png")},
        data={
            "id": "finance_creator",
            "name": "Finance Creator",
            "style": "osobní brand finance",
            "voice": "klidná čeština",
        },
    )

    assert response.status_code == 200
    avatar = response.json()["avatar"]
    assert avatar["id"] == "finance_creator"
    assert avatar["preview_url"] == "/avatar-image/finance_creator"
    assert avatar["local_image_only"] is True
    assert "image_path" in avatar
    assert "image_url" not in avatar

    library = client.get("/avatars").json()["avatars"]
    uploaded = next(item for item in library if item["id"] == "finance_creator")
    assert uploaded["preview_url"] == "/avatar-image/finance_creator"
    assert uploaded["local_image_only"] is True


def test_avatar_upload_uses_public_url_as_generation_reference(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "AVATAR_DATA_PATH", tmp_path / "avatars.json")
    client = TestClient(app)

    response = client.post(
        "/avatars/upload",
        data={
            "id": "public_creator",
            "name": "Public Creator",
            "image_url": "https://example.com/avatar.png",
        },
    )

    assert response.status_code == 200
    avatar = response.json()["avatar"]
    assert avatar["id"] == "public_creator"
    assert avatar["image_url"] == "https://example.com/avatar.png"
    assert avatar["preview_url"] == "https://example.com/avatar.png"
    assert avatar["local_image_only"] is False


def test_company_library_saves_brand_ads_context(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/companies",
        json={
            "id": "solar-leads",
            "name": "Solar Leads",
            "ad_vertical": "solar_fve",
            "business_model": "lead_generation",
            "market": "CZ",
            "language": "cs",
            "default_platform": "meta",
            "creative_channels": ["meta", "instagram"],
            "audience": "Majitele domu, kteri resi drahou elektrinu.",
            "positioning": "Duveryhodna edukace a poptavkovy lead-gen.",
            "brand_voice": "vecny, konkretni, bez nadsazenych slibu",
            "proof_points": ["ucet za elektrinu", "strecha domu", "konzultace"],
            "forbidden_claims": ["garantovana uspora", "dotace pro kazdeho"],
            "creative_quality_rules": ["silny prvni vizual", "kazdy angle musi byt jiny"],
            "is_default": True,
        },
    )

    assert response.status_code == 200
    company = response.json()["company"]
    assert company["id"] == "solar-leads"
    assert company["ad_vertical"] == "solar_fve"
    assert "Brand/client: Solar Leads" in company["context_text"]

    library = client.get("/companies").json()
    saved = next(item for item in library["companies"] if item["id"] == "solar-leads")
    assert library["default_company_id"] == "solar-leads"
    assert saved["creative_quality_rules"] == ["silny prvni vizual", "kazdy angle musi byt jiny"]
    assert saved["product_categories"] == []


def test_generate_applies_brand_context_to_ads_creatives(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)
    client.post(
        "/companies",
        json={
            "id": "kimlondon-test",
            "name": "Kimlondon Test",
            "ad_vertical": "fashion_ecommerce",
            "business_model": "dropshipping",
            "market": "UK",
            "language": "en",
            "default_platform": "meta",
            "audience": "UK fashion shoppers who need believable proof before clicking.",
            "positioning": "Real creator proof for bags, clothing, and shoes.",
            "brand_voice": "British English, practical, direct, low-hype",
            "proof_points": ["worn context", "carried scale", "detail proof"],
            "creative_quality_rules": ["make every static angle visibly different"],
        },
    )

    response = client.post(
        "/generate",
        files=_image_file(),
        data={
            "company_id": "kimlondon-test",
            "product_name": "The Roomiest Bum Bag",
            "product_info": "Black everyday bum bag for errands and travel. Show carried scale and zipper detail.",
            "product_reference_url": "https://example.com/bum-bag.jpg",
            "platform": "tiktok",
            "language": "en",
            "generation_mode": "static",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_input"]["company_profile"]["company_name"] == "Kimlondon Test"
    assert payload["user_input"]["ad_vertical"] == "fashion_ecommerce"
    assert payload["product_analysis"]["brand_context"]
    assert payload["content_prompt_package"]["brand_ads_context"]["company_name"] == "Kimlondon Test"
    assert "Brand ads context" in payload["content_prompt_package"]["seedance_video_prompt"]
    first_static = payload["ads_creative_set"]["static_image_ads"][0]
    assert "brand_ads_context_applied" in first_static
    assert "Kimlondon Test" in first_static["visual_prompt"]


def test_finance_scene_preview_uses_avatar_reference_for_scene_image(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "AVATAR_DATA_PATH", tmp_path / "avatars.json")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    captured: dict[str, object] = {}

    def fake_generate_single_image(**kwargs):
        captured.update(kwargs)
        return {
            "image_generation_status": "skipped",
            "image_assets": [],
            "prompt": kwargs["prompt"],
            "reference_image_urls": kwargs.get("reference_image_urls") or [],
        }

    monkeypatch.setattr(openrouter_image_client, "generate_single_image", fake_generate_single_image)
    client = TestClient(app)

    response = client.post(
        "/finance-scene-preview",
        data={
            "avatar_id": "avatar1",
            "avatar_reference_url": "https://example.com/avatar.png",
            "platform": "meta",
            "finance_video_topic": "Finanční rezerva",
            "finance_video_script": "Vysvětli česky, proč má rezerva chránit klid, ne honit výnos.",
            "openrouter_api_key": "",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured["reference_image_urls"] == ["https://example.com/avatar.png"]
    assert payload["avatar_reference_used_for_scene"] is True
    assert payload["avatar_scene_reference_type"] == "public_url"
    assert "supplied avatar reference image" in payload["finance_scene_concept"]["image_prompt"]
    assert payload["scene_cost_summary"]["version"] == "openrouter_cost_summary_v2"
    assert any(component["component"] == "Finance scene concept image" for component in payload["scene_cost_summary"]["components"])
    assert Path(payload["output_dir"]).parent.name == "scene-concepts"
    assert Path(payload["output_dir"]).parent.parent.name == "finance"
    assert "FIN_SCENE" in Path(payload["output_dir"]).name


def test_avatars_resolve_imgbb_page_url_for_preview(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "AVATAR_DATA_PATH", tmp_path / "avatars.json")
    (tmp_path / "avatars.json").write_text(
        json.dumps(
            [
                {
                    "id": "bank",
                    "name": "Bankovník",
                    "image_url": "https://ibb.co/NgMw5hyf",
                }
            ]
        ),
        encoding="utf-8",
    )

    class FakeResponse:
        text = '<meta property="og:image" content="https://i.ibb.co/example/avatar.png" />'

        def raise_for_status(self):
            return None

    monkeypatch.setattr(image_reference_utils.requests, "get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)

    avatar = client.get("/avatars").json()["avatars"][0]

    assert avatar["image_url"] == "https://i.ibb.co/example/avatar.png"
    assert avatar["preview_url"] == "https://i.ibb.co/example/avatar.png"


def test_generate_minimal_skips_video_without_api_key(monkeypatch, tmp_path):
    _, output_dir = _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "Everyday Tote",
                "product_info": "Roomy daily bag with clean minimal design",
                "product_reference_url": "https://example.com/everyday-tote.jpg",
                "platform": "tiktok",
                "language": "en",
            },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_sequence"][:11] == [
        "Product Intake Agent",
        "Automatic Product Understanding",
        "Visual Product Classifier Agent",
        "Performance Memory Layer",
        "Audience Research Agent",
        "Emotional Angle Engine",
        "Creative Psychology Agent",
        "Voice Personality Engine",
        "UGC Hook Agent",
        "Scene Director Agent",
        "Scene Chaining Agent",
    ]
    assert payload["workflow_sequence"][11] == "UGC Strategy Agent"
    assert "Content Prompt Engineer Agent" in payload["workflow_sequence"]
    assert "Static Image Generation" in payload["workflow_sequence"]
    assert payload["static_image_generation"]["image_generation_status"] == "skipped"
    assert payload["static_image_generation"]["failure_reason"]
    assert payload["video_generation"]["video_generation_status"] == "skipped"
    assert payload["video_generation"]["failure_reason"]
    assert payload["session_cost_summary"]["total_known_cost"] == 0
    assert payload["session_cost_summary"]["version"] == "openrouter_cost_summary_v2"
    assert payload["session_cost_summary"]["components"]
    assert payload["ads_creative_set"]["static_image_ads"]
    assert payload["product_analysis"]["automatic_product_understanding"]["category"] == "handbag"
    assert payload["product_analysis"]["automatic_product_understanding"]["usage_contexts"]
    assert payload["ugc_strategy"]["audience_research"]["primary_archetype"]
    assert payload["ugc_strategy"]["emotional_angle"]["primary_angle"]
    assert payload["ugc_strategy"]["voice_personality"]["creator_style"]
    assert payload["ugc_strategy"]["scene_chaining"]["scene_links"]
    assert payload["ugc_strategy"]["scene_chaining"]["version"] == "scene_chaining_v2"
    assert payload["ugc_strategy"]["scene_chaining"]["true_scene_chaining_plan"]["strategy"] == "original_avatar_for_first_scene_then_last_frame_chain"
    assert payload["ugc_strategy"]["scene_chaining"]["provider_execution"]["current_mode"] == "single_video_request_with_prompted_continuity"
    assert payload["ugc_strategy"]["creative_psychology"]["behavior_tree"]["sequence"]
    assert payload["ugc_strategy"]["hook_strategy"]["selected_hook"] == payload["ugc_strategy"]["hook"]
    assert payload["ugc_strategy"]["scene_direction"]["directed_scenes"]
    assert payload["ugc_strategy"]["performance_insights"]["status"] == "active"
    assert payload["ugc_strategy"]["ugc_prompt_skill"]["source"] == "local skill/claude-arcads creative rules; Arcads API ignored"
    assert payload["ugc_strategy"]["ugc_prompt_skill"]["arcads_api"] == "not used by this app"
    assert payload["ugc_strategy"]["category_video_recipe"]["ugc_template"]
    assert payload["ads_creative_set"]["carousel_ad"]["card_count"] == 5
    assert payload["ads_creative_set"]["static_creative_director"]["version"] == "static_creative_director_v3"
    assert payload["ads_creative_set"]["static_creative_director"]["max_static_images_policy"] == "cap_only_no_padding"
    assert payload["ads_creative_set"]["static_creative_director"]["visual_diversity_score"] >= 40
    assert payload["ads_creative_set"]["meme_style_creatives"]
    assert payload["workflow_report"]["executive_summary"]["product_name"] == "Everyday Tote"
    assert payload["workflow_report"]["deliverables"]["static_images"]["planned_count"] >= 1
    assert payload["workflow_report"]["prompt_and_payload_map"]["seedance_video_payload"]["model"]
    assert payload["content_prompt_package"]["structured_prompt_v2"]["version"] == "structured_prompt_architecture_v2"
    seedance_contract = payload["content_prompt_package"]["structured_prompt_v2"]["seedance_provider_contract"]
    assert seedance_contract["source"] == "video generation prompt adaptation"
    assert "timing_rule" in seedance_contract
    assert payload["content_prompt_package"]["structured_prompt_v2"]["scenes"][0]["time_range"] == "0-5s"
    assert "0-5s" in payload["seedance_payload"]["prompt"]
    assert "product reference image controls product shape" in payload["seedance_payload"]["prompt"]
    assert "Creator prompt skill guidance" in payload["seedance_payload"]["prompt"]
    assert "Arcads API" in payload["seedance_payload"]["prompt"]
    assert "no generated text" in payload["seedance_payload"]["prompt"].lower()
    assert "Structured Prompt" not in payload["seedance_payload"]["prompt"]
    assert "paid UGC ad" not in payload["seedance_payload"]["prompt"]
    assert "product_rules" not in payload["seedance_payload"]["prompt"]
    assert payload["seedance_payload"]["generate_audio"] is True
    assert payload["content_prompt_package"]["prompt_compression"]["status"] == "completed"
    assert payload["seedance_payload"]["structured_prompt_architecture"] == "v2"
    assert payload["self_critique"]["scroll_stopping_score"] >= 0
    assert payload["post_generation_qa"]["version"] == "post_generation_qa_v1"
    assert payload["post_generation_qa"]["status"] in {"passed", "warning"}
    assert next(
        check for check in payload["post_generation_qa"]["checks"] if check["id"] == "no_fake_cta_controls"
    )["status"] == "passed"
    assert next(
        check for check in payload["post_generation_qa"]["checks"] if check["id"] == "scene_chaining_contract"
    )["status"] == "passed"
    assert payload["creative_memory"]["status"] == "saved"
    assert payload["creative_memory"]["product_id"].startswith("prd_")
    assert payload["creative_memory"]["campaign_id"].startswith("cmp_")
    assert payload["creative_memory"]["creative_count"] >= 1
    assert payload["generation_run"]["run_id"].startswith("run_ecommerce_")
    assert payload["generation_run"]["status"] == "completed"
    assert payload["prompt_audit"]["prompt_graph"]["version"] == "prompt_graph_v1"
    assert payload["prompt_audit"]["scene_chaining"]["available"] is True
    assert payload["prompt_audit"]["scene_chaining"]["version"] == "scene_chaining_v2"
    assert payload["prompt_audit"]["scene_chaining"]["current_execution_mode"] == "single_video_request_with_prompted_continuity"

    latest_run = client.get("/generation-runs/latest?workspace=ecommerce").json()
    assert latest_run["run_id"] == payload["generation_run"]["run_id"]
    assert latest_run["provider_validation"]["status"] == "passed"
    assert latest_run["compliance_result"]["compliance_status"] == payload["compliance_result"]["compliance_status"]
    assert latest_run["quality_result"]["export_status"] == payload["quality_result"]["export_status"]
    latest_cost = client.get("/openrouter-cost/latest?workspace=ecommerce").json()
    assert latest_cost["run_id"] == payload["generation_run"]["run_id"]
    assert latest_cost["cost_summary"]["version"] == "openrouter_cost_summary_v2"
    run_cost = client.get(f"/generation-runs/{payload['generation_run']['run_id']}/cost").json()
    assert run_cost["cost_summary"]["total_known_cost"] == payload["session_cost_summary"]["total_known_cost"]
    assert payload["creative_memory"]["rag_guidance"]["status"] == "active"
    assert "Creative Intelligence Memory" in payload["workflow_sequence"]
    assert payload["prompt_audit"]["structured_prompt_v2"]["available"] is True
    assert payload["user_input"]["ugc_scenario_model"] == "openai/gpt-5.4-mini"
    assert payload["content_prompt_package"]["prompt_generation"]["model"] == "openai/gpt-5.4-mini"
    assert [stage["stage_id"] for stage in payload["workflow_report"]["workflow_stages"]][:10] == [
        "product_intake",
        "automatic_product_understanding",
        "audience_research",
        "emotional_angle",
        "creative_psychology",
        "voice_personality",
        "ugc_hook",
        "scene_director",
        "scene_chaining",
        "ugc_strategy",
    ]
    assert any(stage["stage_id"] == "post_generation_qa" for stage in payload["workflow_report"]["workflow_stages"])
    assert "Prompt Source Trace" in payload["workflow_sequence"]
    assert payload["prompt_source_trace"]["data_priority"][0] == "product_name"
    assert "Product Intake Agent" in [
        item["layer"] for item in payload["prompt_source_trace"]["runtime_prompt_layers"]
    ]
    json_path = Path(payload["output_files"]["json_path"])
    markdown_path = Path(payload["output_files"]["markdown_path"])
    assert json_path.exists()
    assert markdown_path.exists()
    assert json_path.parent.parent.name == "ecommerce"
    assert json_path.parent.parent.parent == output_dir
    assert "ADS_ST" in json_path.parent.name
    assert "everyday-tote" in json_path.parent.name
    assert payload["user_input"]["session_workspace"] == "ecommerce"
    assert payload["output_files"]["workspace"] == "ecommerce"
    assert payload["output_files"]["folder_name"] == json_path.parent.name


def test_provider_capabilities_endpoint():
    local_client = TestClient(app)
    payload = local_client.get("/provider-capabilities").json()

    assert payload["version"] == "provider_capability_registry_v1"
    assert payload["limits"]["max_prompt_chars"] == 18000
    assert payload["image_models"]["google/gemini-3-pro-image-preview"]["supports_image_output"] is True
    assert payload["video_models"]["bytedance/seedance-2.0-fast"]["supports_videos_endpoint"] is True
    assert payload["video_models"]["google/veo-3.1-fast"]["supports_videos_endpoint"] is True
    assert payload["video_models"]["google/veo-3.1-fast"]["supports_native_audio"] is True


def test_provider_validation_preview_blocks_bad_image_model():
    local_client = TestClient(app)
    response = local_client.post(
        "/provider-validation-preview",
        json={
            "app_mode": "ecommerce",
            "generation_mode": "static",
            "product_reference_url": "https://example.com/product.png",
            "avatar_reference_url": "https://example.com/avatar.png",
            "use_avatar_image_reference": False,
            "image_model": "openai/gpt-4.1-mini",
            "seedance_model": "bytedance/seedance-2.0-fast",
            "max_static_images": 2,
            "image_size": "1K",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["version"] == "provider_validation_preview_v1"
    assert payload["status"] == "blocked"
    assert payload["reason"] == "Selected image model does not support image generation. Use google/gemini-3-pro-image-preview."
    assert payload["should_generate_static_images"] is True


def test_provider_validation_preview_blocks_non_image_product_reference_url():
    local_client = TestClient(app)
    response = local_client.post(
        "/provider-validation-preview",
        json={
            "app_mode": "ecommerce",
            "generation_mode": "both",
            "product_reference_url": "https://openrouter.ai/docs/guides/overview/multimodal/video-generation",
            "avatar_reference_url": "https://example.com/avatar.png",
            "use_avatar_image_reference": True,
            "image_model": "google/gemini-3-pro-image-preview",
            "seedance_model": "google/veo-3.1-fast",
            "max_static_images": 2,
            "image_size": "1K",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["reason"].startswith("Product reference URL must be a direct image file")
    failed_ids = {check["id"] for check in payload["checks"] if check["status"] == "failed"}
    assert "product_reference_direct_image_url" in failed_ids


def test_provider_validation_preview_blocks_video_without_public_product_reference():
    local_client = TestClient(app)
    response = local_client.post(
        "/provider-validation-preview",
        json={
            "app_mode": "ecommerce",
            "generation_mode": "video",
            "product_reference_url": "",
            "avatar_reference_url": "https://example.com/avatar.png",
            "use_avatar_image_reference": False,
            "image_model": "google/gemini-3-pro-image-preview",
            "seedance_model": "google/veo-3.1-fast",
            "max_static_images": 0,
            "image_size": "1K",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert "Video generation requires" in payload["reason"]
    failed_ids = {check["id"] for check in payload["checks"] if check["status"] == "failed"}
    assert "product_reference_public_url" in failed_ids


def test_provider_validation_preview_accepts_google_veo_video_model():
    local_client = TestClient(app)
    response = local_client.post(
        "/provider-validation-preview",
        json={
            "app_mode": "ecommerce",
            "generation_mode": "video",
            "product_reference_url": "https://example.com/product.png",
            "avatar_reference_url": "https://example.com/avatar.png",
            "use_avatar_image_reference": False,
            "image_model": "google/gemini-3-pro-image-preview",
            "seedance_model": "google/veo-3.1-fast",
            "max_static_images": 0,
            "image_size": "1K",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "passed"
    assert payload["should_generate_video"] is True
    assert payload["should_generate_static_images"] is False


def test_creative_plan_preview_is_server_side_cap_only(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    client = TestClient(app)

    response = client.post(
        "/creative-plan-preview",
        data={
            "app_mode": "ecommerce",
            "generation_mode": "both",
            "max_static_images": "2",
            "image_model": "google/gemini-3-pro-image-preview",
            "seedance_model": "bytedance/seedance-2.0-fast",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["version"] == "creative_plan_service_v1"
    assert payload["image_count_policy"] == "cap_only_no_padding"
    assert payload["selected_image_count"] == 2
    statuses = {item["set_id"]: item["status"] for item in payload["items"]}
    reasons = {item["set_id"]: item["reason"] for item in payload["items"]}
    assert statuses["C1"] == "YES"
    assert statuses["C2"] == "YES"
    assert statuses["C4"] == "YES"
    assert statuses["C3"] == "SKIPPED"
    assert statuses["C5"] == "SKIPPED"
    assert reasons["C3"] == "max_static_images cap"


def test_creative_plan_preview_finance_is_video_only(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    client = TestClient(app)

    response = client.post(
        "/creative-plan-preview",
        data={
            "app_mode": "finance_personal_brand",
            "generation_mode": "both",
            "max_static_images": "8",
            "seedance_model": "bytedance/seedance-2.0-fast",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["workspace"] == "finance"
    assert payload["generation_mode"] == "video"
    assert payload["selected_image_count"] == 0
    assert [item["set_id"] for item in payload["items"]] == ["C1"]
    assert payload["items"][0]["status"] == "YES"


def test_generation_runs_post_executes_compatible_workflow(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generation-runs",
        files=_image_file(),
            data={
                "product_name": "Run Tote",
                "product_info": "Minimal bag with clean shape",
                "product_reference_url": "https://example.com/run-tote.jpg",
                "platform": "meta",
                "language": "en",
                "idempotency_key": "run-tote-test",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["generation_run"]["run_id"].startswith("run_ecommerce_")
    assert payload["generation_run"]["status"] in {"queued", "validating", "planning", "prompting", "generating_video", "generating_images", "qa", "saving", "completed"}
    run_id = payload["generation_run"]["run_id"]
    run = payload["generation_run"]
    for _ in range(60):
        run = client.get(f"/generation-runs/{run_id}").json()
        if run["status"] not in generation_run_repository.ACTIVE_STATUSES:
            break
        time.sleep(0.05)
    assert run["status"] == "completed"
    assert run["final_output"]["user_input"]["idempotency_key_provided"] is True
    assert run["monitor"]["is_terminal"] is True
    assert run["monitor"]["progress_percent"] == 100
    assert run["final_export_status"]
    assert run["creative_plan_preview"]["items"]
    assert run["provider_validation"]["status"] == "passed"
    assert run["prompt_audit"]["version"] == "prompt_audit_v1"
    assert run["session_cost_summary"]


def test_chat_brief_parser_endpoint_returns_deterministic_draft_without_key(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/chat-brief-parser",
        json={
            "chatBriefItems": [
                {
                    "id": "item_1",
                    "text": "BELLA Leather Tote\nFor UK Meta in English. Video + statiky.\nhttps://example.com/product.jpg",
                    "file_count": 1,
                    "file_names": ["product.png"],
                    "applied_as": ["product"],
                },
                {
                    "id": "item_2",
                    "text": "Konkurence Rival uses UGC mirror shots and stitching close-ups. https://rival.example",
                    "file_count": 1,
                    "file_names": ["rival.png"],
                    "applied_as": ["competitor"],
                },
            ],
            "current_form": {},
            "prompt_model": "openai/gpt-5.4-mini",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "deterministic"
    assert payload["campaign_draft"]["product_name"] == "BELLA Leather Tote"
    assert payload["campaign_draft"]["product_reference_url"] == "https://example.com/product.jpg"
    assert payload["campaign_draft"]["competitor_strategy_enabled"] is True
    assert payload["campaign_draft"]["platform"] == "meta"
    assert payload["campaign_draft"]["market"] == "UK"
    assert payload["campaign_draft"]["language"] == "en"
    assert payload["attachment_roles"]


def test_finance_generation_run_requires_scene_approval(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generation-runs",
        data={
            "app_mode": "finance_personal_brand",
            "platform": "meta",
            "market": "CZ",
            "language": "cs",
            "finance_video_topic": "Finanční rezerva",
            "finance_video_script": "Vysvětli česky, proč má rezerva chránit klid, ne honit výnos.",
            "finance_scene_approved": "false",
            "idempotency_key": "finance-scene-gate-test",
        },
    )

    assert response.status_code == 202
    run_id = response.json()["run_id"]
    run = response.json()["generation_run"]
    for _ in range(60):
        run = client.get(f"/generation-runs/{run_id}").json()
        if run["status"] not in generation_run_repository.ACTIVE_STATUSES:
            break
        time.sleep(0.05)

    assert run["status"] == "needs_scene_approval"
    assert run["monitor"]["status_label"] == "Čeká na scénu"
    assert run["monitor"]["next_step"] == "Připrav a schval finance scénu, potom spusť video znovu."
    assert run["workspace"] == "finance"
    assert not run.get("video_generation")


def test_generation_runs_block_only_active_same_workspace(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    active = generation_run_repository.create_run(
        workspace="ecommerce",
        app_mode="ecommerce",
        input_snapshot={"product_name": "Active Tote"},
        idempotency_key="active-ecommerce-run",
    )
    client = TestClient(app)

    blocked = client.post(
        "/generation-runs",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "product_reference_url": "https://example.com/product.jpg",
            "platform": "meta",
            "language": "en",
        },
    )
    finance = client.post(
        "/generation-runs",
        data={
            "app_mode": "finance_personal_brand",
            "platform": "meta",
            "market": "CZ",
            "language": "cs",
            "finance_video_topic": "Finanční rezerva",
            "finance_video_script": "Vysvětli česky, proč má rezerva chránit klid.",
            "finance_scene_approved": "false",
            "idempotency_key": "finance-cross-workspace-allowed",
        },
    )

    assert blocked.status_code == 409
    assert blocked.json()["generation_run"]["run_id"] == active["run_id"]
    assert "same workspace" in blocked.json()["reason"]
    legacy_blocked = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "product_reference_url": "https://example.com/product.jpg",
            "platform": "meta",
            "language": "en",
        },
    )
    assert legacy_blocked.status_code == 409
    assert legacy_blocked.json()["active_run_id"] == active["run_id"]
    assert finance.status_code == 202


def test_creative_memory_workspace_filter(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    client = TestClient(app)

    def output(product_name: str, workspace: str, app_mode: str) -> dict:
        return {
            "user_input": {
                "session_workspace": workspace,
                "app_mode": app_mode,
                "session_folder_name": f"{workspace}_session",
            },
            "avatar": {"id": "avatar1", "name": "Avatar"},
            "product_analysis": {
                "product_name": product_name,
                "likely_product_category": "handbag" if workspace == "ecommerce" else "finance",
                "user_provided_facts": ["safe fact"],
                "ad_safe_detail_phrases": ["visible detail"],
            },
            "ugc_strategy": {
                "platform": "meta",
                "market": "UK" if workspace == "ecommerce" else "CZ",
                "language": "en" if workspace == "ecommerce" else "cs",
                "hook": "hook",
            },
            "content_prompt_package": {
                "seedance_payload": {"prompt": f"{workspace} prompt", "model": "bytedance/seedance-2.0-fast"},
                "negative_prompt": "negative",
            },
            "ads_creative_set": {
                "creative_plan": [],
                "ugc_video_ad": {"angle": "UGC"},
            },
            "static_image_generation": {"generation_plan": [], "image_assets": [], "image_generation_status": "skipped"},
            "video_generation": {"video_generation_status": "skipped"},
            "session_cost_summary": {"components": []},
            "prompt_audit": {},
        }

    creative_memory_db.save_generation(output("Bella Bag", "ecommerce", "ecommerce"))
    creative_memory_db.save_generation(output("Finance Brand", "finance", "finance_personal_brand"))

    ecommerce = client.get("/creative-memory/creatives?workspace=ecommerce&limit=50").json()["creatives"]
    finance = client.get("/creative-memory/creatives?workspace=finance&limit=50").json()["creatives"]

    assert ecommerce
    assert finance
    assert all(item["workspace"] == "ecommerce" for item in ecommerce)
    assert all(item["workspace"] == "finance" for item in finance)

    ecommerce_intel = client.get("/creative-intelligence?workspace=ecommerce").json()
    finance_learning = client.get("/creative-memory/learning?workspace=finance").json()
    assert ecommerce_intel["workspace"] == "ecommerce"
    assert finance_learning["workspace"] == "finance"
    assert finance_learning["rule"].startswith("Use learning as directional")


def test_creative_memory_rag_cleans_rejected_pattern_text(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    final_output = {
        "user_input": {
            "session_workspace": "ecommerce",
            "app_mode": "ecommerce",
            "session_folder_name": "ecommerce_session",
        },
        "avatar": {"id": "avatar1", "name": "Avatar"},
        "product_analysis": {
            "product_name": "Bella Bag",
            "likely_product_category": "handbag",
            "user_provided_facts": ["safe fact"],
            "ad_safe_detail_phrases": ["visible detail"],
        },
        "ugc_strategy": {
            "platform": "meta",
            "market": "UK",
            "language": "en",
            "hook": "hook",
        },
        "content_prompt_package": {
            "seedance_payload": {"prompt": "natural window light product visible prompt", "model": "bytedance/seedance-2.0-fast"},
            "negative_prompt": "negative",
        },
        "ads_creative_set": {
            "creative_plan": [],
            "ugc_video_ad": {"angle": "UGC"},
        },
        "static_image_generation": {"generation_plan": [], "image_assets": [], "image_generation_status": "skipped"},
        "video_generation": {"video_generation_status": "skipped"},
        "session_cost_summary": {"components": []},
        "prompt_audit": {},
    }
    saved = creative_memory_db.save_generation(final_output)
    creative_id = saved["creatives"][0]["creative_id"]

    creative_memory_db.add_rating(
        {
            "creative_id": creative_id,
            "status": "rejected",
            "comment": "spatn\u00c3\u00bd kanicky",
            "reasons": ["rejected", "spatn\u00c3\u00a9 po\u00c4\u008dty bot"],
        }
    )
    guidance = creative_memory_db.retrieve_guidance(
        product_analysis=final_output["product_analysis"],
        settings={"platform": "meta", "market": "UK", "workspace": "ecommerce"},
    )

    assert "rejected" not in guidance["avoid_patterns"]
    assert "spatný kanicky" in guidance["avoid_patterns"]
    assert "spatné počty bot" in guidance["avoid_patterns"]
    assert "spatnÃ" not in guidance["prompt_guidance"]


def test_creative_rating_and_intelligence_endpoints(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "Everyday Tote",
                "product_info": "Roomy daily bag with clean minimal design",
                "product_reference_url": "https://example.com/everyday-tote.jpg",
                "platform": "meta",
                "language": "en",
            },
    )

    payload = response.json()
    creative_id = payload["creative_memory"]["creatives"][0]["creative_id"]
    rating = client.post(
        "/creative-rating",
        json={
            "creative_id": creative_id,
            "status": "approved",
            "user_rating": 5,
            "fidelity_score": 5,
            "realism_score": 4,
            "hook_score": 4,
            "brand_fit_score": 5,
            "comment": "Strong product detail and natural hook",
            "reasons": [],
        },
    )
    performance = client.post(
        "/performance-import",
        json={
            "creative_id": creative_id,
            "ctr": 2.1,
            "cpc": 0.42,
            "cpa": 12.5,
            "roas": 2.4,
            "spend": 120,
            "impressions": 10000,
            "clicks": 210,
            "conversions": 9,
            "platform": "meta",
            "date_range": "2026-05-01 to 2026-05-14",
        },
    )
    performance_batch = client.post(
        "/performance-import-batch",
        json={
            "records": [
                {
                    "creative_id": creative_id,
                    "ctr": 1.9,
                    "roas": 2.2,
                    "platform": "meta",
                    "date_range": "2026-05-15 to 2026-05-21",
                }
            ]
        },
    )
    intelligence = client.get("/creative-intelligence")
    preview = client.post(
        "/creative-intelligence-preview",
        json={
            "product_name": "Everyday Tote",
            "product_info": "Roomy daily bag with clean minimal design",
            "product_category": "handbag",
            "platform": "meta",
            "market": "UK",
            "language": "en",
        },
    )
    prompt_guidance = client.post(
        "/prompt-learning-guidance",
        json={
            "product_name": "Everyday Tote",
            "product_info": "Roomy daily bag with clean minimal design",
            "product_category": "handbag",
            "platform": "meta",
            "market": "UK",
            "language": "en",
            "app_mode": "ecommerce",
        },
    )
    listing = client.get("/creative-memory/creatives")

    assert response.status_code == 200
    assert rating.status_code == 200
    assert performance.status_code == 200
    assert performance_batch.status_code == 200
    assert rating.json()["status"] == "saved"
    assert performance.json()["status"] == "saved"
    assert performance_batch.json()["saved_count"] == 1
    assert rating.json()["learning_signal"]["direction"] == "prefer"
    assert rating.json()["knowledge_item"]["workspace"] == "ecommerce"
    assert rating.json()["learning_snapshot"]["workspace"] == "ecommerce"
    assert performance.json()["learning_signal"]["status"] == "performance_winner"
    assert performance.json()["learning_snapshot"]["winning_patterns"]
    assert performance_batch.json()["learning_signals"][0]["direction"] == "prefer"
    assert performance_batch.json()["learning_snapshot"]["workspace"] == "ecommerce"
    assert intelligence.status_code == 200
    assert preview.status_code == 200
    assert prompt_guidance.status_code == 200
    assert listing.status_code == 200
    assert intelligence.json()["counts"]["ratings"] == 1
    assert intelligence.json()["counts"]["performance_records"] == 2
    assert intelligence.json()["knowledge_base"]["item_count"] >= 3
    assert intelligence.json()["learning_loop"]["status"] == "ready"
    assert intelligence.json()["winning_pattern_extractor"]["agent"] == "Winning Pattern Extractor"
    assert intelligence.json()["prompt_learning_agent"]["agent"] == "Prompt Learning Agent"
    assert intelligence.json()["counts"]["creatives"] >= 1
    assert preview.json()["next_generation_guidance"]["winning_patterns"]
    assert prompt_guidance.json()["agent"] == "Prompt Learning Agent"
    assert prompt_guidance.json()["workspace"] == "ecommerce"
    assert prompt_guidance.json()["winning_patterns"]
    assert prompt_guidance.json()["prompt_insert"]
    assert listing.json()["count"] >= 1
    listed_creative = next(item for item in listing.json()["creatives"] if item["creative_id"] == creative_id)
    assert listed_creative["latest_rating_status"] == "approved"
    assert listed_creative["latest_user_rating"] == 5
    assert listed_creative["rating_count"] == 1
    assert listed_creative["performance_count"] == 2
    assert listed_creative["latest_roas"] == 2.2
    assert listed_creative["latest_ctr"] == 1.9


def test_prompt_settings_returns_defaults():
    client = TestClient(app)

    response = client.get("/prompt-settings")

    assert response.status_code == 200
    payload = response.json()
    assert "content_prompt_system" in payload
    assert "base_video_prompt_template" in payload
    assert "prompt_source_inventory" in payload
    assert payload["prompt_source_inventory"]["editable_ui_fields"]
    assert "{avatar_instruction}" in payload["base_video_prompt_template"]
    assert "{voice_profile}" in payload["base_video_prompt_template"]
    assert "{category_prompt}" in payload["base_video_prompt_template"]
    assert "category_prompt_presets" in payload
    assert "handbag" in payload["category_prompt_presets"]
    assert "product-only" in payload["content_prompt_system"]
    assert payload["environment_control_defaults"]["environment_selection"] == "category_auto"
    assert payload["environment_control_defaults"]["preserve_original_scene_layout"] is False
    assert "Avatar reference controls identity only" in payload["environment_control_defaults"]["directive"]


def test_default_platform_is_meta():
    assert config.DEFAULT_PLATFORM == "meta"


def test_latest_output_returns_most_recent_saved_export(monkeypatch, tmp_path):
    _, output_dir = _configure_tmp_dirs(monkeypatch, tmp_path)
    older = output_dir / "20200101_old.json"
    newer_dir = output_dir / "20200102_ADS_ST_new"
    newer = newer_dir / "20200102_new.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    newer_dir.mkdir(parents=True, exist_ok=True)
    older.write_text(json.dumps({"workflow_sequence": ["old"]}), encoding="utf-8")
    newer.write_text(json.dumps({"workflow_sequence": ["new"]}), encoding="utf-8")
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))
    client = TestClient(app)

    response = client.get("/latest-output")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_sequence"] == ["new"]
    assert payload["_recovered_from_latest_output"] is True


def test_generate_blocks_medical_claims(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "Walking Shoes",
                "product_info": "Orthopedic shoes that cure foot pain",
                "product_reference_url": "https://example.com/walking-shoes.jpg",
                "platform": "tiktok",
                "language": "en",
            },
    )

    payload = response.json()
    assert payload["final_export_status"] == "blocked"
    assert payload["static_image_generation"]["image_generation_status"] == "blocked"
    assert payload["static_image_generation"]["failure_reason"]
    assert payload["video_generation"]["video_generation_status"] == "blocked"
    assert payload["video_generation"]["failure_reason"]
    assert payload["compliance_result"]["compliance_status"] == "fail"


def test_generate_comfort_shoes_does_not_block_on_internal_medical_safety_language(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "ROSA | AeroFlex Comfort Sneakers",
                "product_info": (
                    "The trainers you'll reach for every single morning. Stylish enough for brunch, "
                    "comfortable enough for a full day on your feet."
                ),
                "product_reference_url": "https://example.com/rosa-sneakers.jpg",
                "product_category": "shoes",
                "platform": "meta",
                "market": "UK",
            "language": "en",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["compliance_result"]["compliance_status"] == "pass"
    assert payload["compliance_result"]["unsupported_claims"] == []
    assert payload["final_export_status"] != "blocked"


def test_generate_mocked_video_success_saves_mp4(monkeypatch, tmp_path):
    _, output_dir = _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")

    def fake_generate_video(seedance_payload, product_name, output_dir, **kwargs):
        path = Path(output_dir) / "mock_video.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mp4")
        return {
            "video_generation_status": "completed",
            "error": None,
            "video_path": str(path),
            "job_id": "job_123",
            "submitted_payload": {"model": seedance_payload["model"], "prompt": seedance_payload["prompt"]},
        }

    monkeypatch.setattr("app.main.openrouter_seedance_client.generate_video", fake_generate_video)
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "Desk Lamp",
                "product_info": "Compact lamp for a clean desk setup",
                "product_reference_url": "https://example.com/desk-lamp.jpg",
                "platform": "instagram",
                "language": "en",
            },
    )

    payload = response.json()
    video_path = Path(payload["video_generation"]["video_path"])
    assert payload["video_generation"]["video_generation_status"] == "completed"
    assert video_path.exists()
    assert video_path.parent.parent.name == "ecommerce"
    assert video_path.parent.parent.parent == output_dir
    assert "ADS_ST" in video_path.parent.name
    assert set(payload["video_generation"]["submitted_payload"].keys()) == {"model", "prompt"}


def test_generate_both_submits_video_before_static_images(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    calls: list[str] = []

    def fake_generate_video(seedance_payload, product_name, output_dir, **kwargs):
        calls.append("video")
        return {
            "video_generation_status": "skipped",
            "failure_reason": "mocked video skip",
            "next_step": "mocked",
            "submitted_payload": seedance_payload,
        }

    def fake_generate_ad_images(*args, **kwargs):
        calls.append("images")
        return {
            "image_generation_status": "skipped",
            "failure_reason": "mocked image skip",
            "next_step": "mocked",
            "image_assets": [],
            "attempted_count": 0,
        }

    monkeypatch.setattr("app.main.openrouter_seedance_client.generate_video", fake_generate_video)
    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "Desk Lamp",
                "product_info": "Compact lamp for a clean desk setup",
                "product_reference_url": "https://example.com/desk-lamp.jpg",
                "generation_mode": "both",
                "platform": "meta",
                "language": "en",
        },
    )

    assert response.status_code == 200
    assert calls == ["video", "images"]


def test_generate_mocked_static_images_uses_image_controls(monkeypatch, tmp_path):
    _, output_dir = _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    calls = {}

    def fake_generate_ad_images(**kwargs):
        calls.update(kwargs)
        path = Path(kwargs["output_dir"]) / "mock_static.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")
        return {
            "image_generation_status": "completed",
            "error": None,
            "failure_reason": None,
            "next_step": None,
            "model": kwargs["model"],
            "image_assets": [
                {
                    "creative_id": "static_side_by_side",
                    "asset_type": "static_image",
                    "image_path": str(path),
                    "image_url": "/output/mock_static.png",
                }
            ],
            "attempted_count": 1,
            "generated_count": 1,
        }

    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
            data={
                "product_name": "Desk Lamp",
                "product_info": "Compact lamp for a clean desk setup",
                "generation_mode": "static",
                "platform": "instagram",
                "language": "en",
                "image_model": "google/gemini-3-pro-image-preview",
            "max_static_images": "2",
            "image_size": "4K",
        },
    )

    payload = response.json()
    assert payload["static_image_generation"]["image_generation_status"] == "completed"
    assert Path(calls["output_dir"]).parent.name == "ecommerce"
    assert Path(calls["output_dir"]).parent.parent == output_dir
    assert "ADS_ST" in Path(calls["output_dir"]).name
    assert calls["model"] == "google/gemini-3-pro-image-preview"
    assert calls["enabled"] is True
    assert calls["max_images"] == 2
    assert calls["image_size"] == "4K"


def test_generate_static_images_passes_multiple_product_variant_references(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    calls = {}

    def fake_generate_ad_images(**kwargs):
        calls.update(kwargs)
        return {"image_generation_status": "completed", "image_assets": [], "attempted_count": 0}

    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=[
            ("product_image", ("primary.png", b"primary", "image/png")),
            ("product_static_images", ("red.png", b"red", "image/png")),
            ("product_static_images", ("blue.png", b"blue", "image/png")),
        ],
        data={
            "product_name": "Desk Lamp",
            "product_info": "Same lamp in multiple colours",
            "generation_mode": "static",
            "platform": "instagram",
            "language": "en",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["product_analysis"]["static_product_reference_paths"]
    assert len(calls["reference_image_urls"]) == 2
    assert all("static_product_variants" in path for path in calls["reference_image_urls"])


def test_generate_blocks_static_images_when_prompt_model_fails_with_key(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")
    image_called = False

    def fake_enhance_ads_creative_set(**kwargs):
        ads = dict(kwargs["ads_creative_set"])
        ads["static_prompt_generation"] = {
            "status": "failed",
            "model": "openai/gpt-5.5",
            "error": "402 Client Error: Payment Required",
            "attempts": [
                {
                    "model": "openai/gpt-5.5",
                    "status": "failed",
                    "error": "402 Client Error: Payment Required",
                }
            ],
        }
        return ads

    def fake_generate_ad_images(**kwargs):
        nonlocal image_called
        image_called = True
        return {"image_generation_status": "completed", "image_assets": []}

    monkeypatch.setattr(
        "app.main.openrouter_prompt_client.enhance_ads_creative_set",
        fake_enhance_ads_creative_set,
    )
    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "generation_mode": "static",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert image_called is False
    assert payload["static_image_generation"]["image_generation_status"] == "blocked"
    assert payload["static_image_generation"]["blocked_by_prompt_model"] is True
    assert "openai/gpt-5.5" in payload["static_image_generation"]["failure_reason"]


def test_provider_validation_blocks_unsupported_image_model_before_api_calls(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "test-key")

    def fail_prompt_call(**kwargs):
        raise AssertionError("Prompt model should not be called after provider validation blocks.")

    def fail_image_call(**kwargs):
        raise AssertionError("Image API should not be called after provider validation blocks.")

    monkeypatch.setattr("app.main.openrouter_prompt_client.enhance_prompt_package", fail_prompt_call)
    monkeypatch.setattr("app.main.openrouter_prompt_client.enhance_ads_creative_set", fail_prompt_call)
    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fail_image_call)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "generation_mode": "static",
            "image_model": "openai/gpt-5.4-mini",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "blocked"
    assert payload["final_export_status"] == "blocked"
    assert payload["provider_validation"]["status"] == "blocked"
    assert payload["provider_validation"]["reason"] == (
        "Selected image model does not support image generation. Use google/gemini-3-pro-image-preview."
    )
    assert payload["static_image_generation"]["image_generation_status"] == "blocked"
    assert payload["prompt_audit"]["status"] == "not_started"
    assert payload["generation_run"]["status"] == "blocked"
    latest_run = client.get("/generation-runs/latest?workspace=ecommerce").json()
    assert latest_run["run_id"] == payload["generation_run"]["run_id"]
    assert latest_run["status"] == "blocked"
    assert latest_run["monitor"]["status_label"] == "Blokováno"
    assert latest_run["monitor"]["next_step"] == (
        "Selected image model does not support image generation. Use google/gemini-3-pro-image-preview."
    )
    assert latest_run["monitor"]["blockers"][0]["id"] == "image_model_supports_image_output"


def test_cancel_requested_after_video_skips_static_image_provider(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    image_called = False

    def fake_generate_video(seedance_payload, product_name, output_dir, **kwargs):
        latest = generation_run_repository.latest_run("ecommerce")
        assert latest is not None
        generation_run_repository.request_cancel(latest["run_id"])
        return {
            "video_generation_status": "completed",
            "error": None,
            "failure_reason": None,
            "video_path": None,
            "job_id": "job_video",
            "submitted_payload": {"model": seedance_payload["model"], "prompt": seedance_payload["prompt"]},
        }

    def fake_generate_ad_images(**kwargs):
        nonlocal image_called
        image_called = True
        raise AssertionError("Static image provider should not be called after cancellation.")

    monkeypatch.setattr("app.main.openrouter_seedance_client.generate_video", fake_generate_video)
    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "generation_mode": "both",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert image_called is False
    assert payload["final_export_status"] == "cancelled"
    assert payload["static_image_generation"]["image_generation_status"] == "cancelled"
    assert payload["static_image_generation"]["cancelled_before_provider_call"] is True
    assert payload["generation_run"]["status"] == "cancelled"


def test_cancel_requested_during_video_only_keeps_run_cancelled(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")

    def fake_generate_video(seedance_payload, product_name, output_dir, **kwargs):
        latest = generation_run_repository.latest_run("ecommerce")
        assert latest is not None
        generation_run_repository.request_cancel(latest["run_id"])
        return {
            "video_generation_status": "completed",
            "error": None,
            "failure_reason": None,
            "video_path": None,
            "job_id": "job_video",
            "submitted_payload": {"model": seedance_payload["model"], "prompt": seedance_payload["prompt"]},
        }

    monkeypatch.setattr("app.main.openrouter_seedance_client.generate_video", fake_generate_video)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "generation_mode": "video",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["final_export_status"] == "cancelled"
    assert payload["generation_run"]["status"] == "cancelled"
    assert payload["video_generation"]["video_generation_status"] == "completed"


def test_generation_mode_video_skips_static_image_api(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    image_called = False
    video_called = False

    def fake_generate_ad_images(**kwargs):
        nonlocal image_called
        image_called = True
        return {"image_generation_status": "completed", "image_assets": []}

    def fake_generate_video(seedance_payload, product_name, output_dir, **kwargs):
        nonlocal video_called
        video_called = True
        return {
            "video_generation_status": "completed",
            "error": None,
            "failure_reason": None,
            "video_path": None,
            "job_id": "job_video",
            "submitted_payload": {"model": seedance_payload["model"], "prompt": seedance_payload["prompt"]},
        }

    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    monkeypatch.setattr("app.main.openrouter_seedance_client.generate_video", fake_generate_video)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "generation_mode": "video",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert video_called is True
    assert image_called is False
    assert payload["user_input"]["generation_mode"] == "video"
    assert payload["user_input"]["generate_video"] is True
    assert payload["user_input"]["generate_static_images"] is False
    assert payload["static_image_generation"]["image_generation_status"] == "skipped"
    assert payload["static_image_generation"]["skipped_by_generation_mode"] is True
    assert payload["video_generation"]["video_generation_status"] == "completed"
    assert payload["workflow_report"]["executive_summary"]["generation_mode"] == "video"


def test_generation_mode_static_skips_video_api(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    image_called = False
    video_called = False

    def fake_generate_ad_images(**kwargs):
        nonlocal image_called
        image_called = True
        return {
            "image_generation_status": "completed",
            "error": None,
            "failure_reason": None,
            "model": kwargs["model"],
            "image_assets": [],
            "attempted_count": 1,
            "generated_count": 0,
        }

    def fake_generate_video(seedance_payload, product_name, output_dir, **kwargs):
        nonlocal video_called
        video_called = True
        return {"video_generation_status": "completed"}

    monkeypatch.setattr("app.main.openrouter_image_client.generate_ad_images", fake_generate_ad_images)
    monkeypatch.setattr("app.main.openrouter_seedance_client.generate_video", fake_generate_video)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "generation_mode": "static",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert image_called is True
    assert video_called is False
    assert payload["user_input"]["generation_mode"] == "static"
    assert payload["user_input"]["generate_video"] is False
    assert payload["user_input"]["generate_static_images"] is True
    assert payload["static_image_generation"]["image_generation_status"] == "completed"
    assert payload["video_generation"]["video_generation_status"] == "skipped"
    assert payload["video_generation"]["skipped_by_generation_mode"] is True
    assert payload["video_generation"]["submitted_payload"]["prompt"]
    assert payload["workflow_report"]["executive_summary"]["generation_mode"] == "static"
    latest_run = client.get("/generation-runs/latest?workspace=ecommerce").json()
    assert latest_run["monitor"]["status"] == "completed"
    assert latest_run["monitor"]["terminal_reason"] == ""
    assert not any(blocker["source"] == "video_generation" for blocker in latest_run["monitor"]["blockers"])


def test_static_mode_product_fidelity_block_does_not_report_video_blocker(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")

    def fake_fidelity(*args, **kwargs):
        return {
            "product_fidelity_status": "fail",
            "changed_or_invented_details": ["fabric"],
            "missing_fidelity_instructions": [],
            "recommended_fixes": ["Remove invented product material language."],
        }

    monkeypatch.setattr("app.main.product_fidelity_guard.check", fake_fidelity)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Leg Jumpsuit",
            "product_info": "Modern jumpsuit",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/jumpsuit.jpg",
            "generation_mode": "static",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["final_export_status"] == "blocked"
    assert payload["static_image_generation"]["image_generation_status"] == "blocked"
    assert payload["video_generation"]["video_generation_status"] == "skipped"
    assert payload["video_generation"]["skipped_by_generation_mode"] is True
    latest_run = client.get("/generation-runs/latest?workspace=ecommerce").json()
    assert latest_run["monitor"]["terminal_reason"] == "Product Fidelity Guard failed: fabric"
    assert [blocker["source"] for blocker in latest_run["monitor"]["blockers"]] == ["static_image_generation"]


def test_generate_accepts_public_product_reference_url_without_upload(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_analysis"]["product_image_path"] == "https://example.com/product.jpg"
    assert payload["seedance_payload"]["input_reference_count"] == 1
    assert payload["video_generation"]["video_generation_status"] == "skipped"


def test_static_generation_cap_is_reflected_in_report(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "max_static_images": "2",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    static_generation = payload["static_image_generation"]
    report_static = payload["workflow_report"]["deliverables"]["static_images"]
    assert len(static_generation["generation_plan"]) == 2
    assert [item["set_id"] for item in static_generation["generation_plan"]] == ["C2", "C6"]
    assert len(static_generation["skipped_creatives"]) > 0
    assert report_static["planned_count"] == 2
    assert report_static["source_creative_count"] > 2
    assert report_static["skipped_count"] > 0
    assert len(report_static["selected_creatives"]) == 2


def test_generate_accepts_prompt_overrides(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "negative_prompt": "Do not change the product. Keep the avatar consistent.",
            "base_video_prompt_template": "Create {duration}s UGC with avatar. {fidelity} {avatar_instruction} Negative prompt: {negative_prompt}",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_input"]["prompt_overrides"]["negative_prompt"] is True
    assert payload["seedance_payload"]["prompt"].startswith("Create 15s creator product video with avatar.")
    assert "UGC" not in payload["seedance_payload"]["prompt"]
    assert payload["seedance_payload"]["negative_prompt"] == "Do not change the product. Keep the avatar consistent."
    assert payload["content_prompt_package"]["structured_scene_prompt"]["variants"]


def test_generate_applies_optional_ugc_video_extra_prompt(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "ugc_video_extra_prompt": "Midway through the video, the background light shifts from warm to cool blue and the creator reacts naturally",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    prompt = payload["seedance_payload"]["prompt"]
    assert payload["user_input"]["ugc_video_extra_prompt_provided"] is True
    assert "background light shifts from warm to cool blue" in prompt
    assert "Do not alter product colour" in prompt
    assert payload["content_prompt_package"]["ugc_video_extra_prompt"]


def test_generate_applies_strict_environment_control_by_default(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "BELLA | LEATHER TOTE BAG",
            "product_info": "Structured leather tote photographed in a clean product scene",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "product_category": "handbag",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    prompt = payload["seedance_payload"]["prompt"]
    environment_control = payload["content_prompt_package"]["environment_control"]
    assert environment_control["background_consistency"] == "strict"
    assert environment_control["environment_override"] is False
    assert environment_control["preserve_original_scene_layout"] is False
    assert environment_control["environment_selection"] == "category_auto"
    assert "background_consistency=strict" in prompt
    assert "environment_override=false" in prompt
    assert "preserve_original_scene_layout=false" in prompt
    assert "environment_selection=category_auto" in prompt
    assert "Creator-video authenticity comes from camera motion" in prompt
    assert "UGC authenticity comes from camera motion" not in prompt
    assert "Dropshipping realism guard" in prompt
    assert "real buyer-check clip" in prompt
    assert "luxury staging" in prompt
    assert "Spoken audio is required" in prompt
    assert payload["seedance_payload"]["generate_audio"] is True
    first_scene = payload["content_prompt_package"]["structured_scene_prompt"]["variants"][0]["scenes"][0]
    assert "category-selected environment" in first_scene["scene_summary"]
    assert "not copied from avatar reference" in first_scene["scene_summary"]


def test_generate_uses_selected_category_prompt_override(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "BELLA | LEATHER TOTE BAG",
            "product_info": "Structured daily bag with clean minimalist shape",
            "platform": "meta",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
            "product_category": "handbag",
            "category_prompt_handbag": "CUSTOM HANDBAG PROMPT focus on handles and outfit-scale context",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_analysis"]["likely_product_category"] == "handbag"
    assert payload["product_analysis"]["product_category_source"] == "user_selected"
    assert payload["content_prompt_package"]["category_prompt_directive"].startswith("CUSTOM HANDBAG PROMPT")
    assert "CUSTOM HANDBAG PROMPT" in payload["seedance_payload"]["prompt"]
    assert payload["ads_creative_set"]["category_image_directive"].startswith("CUSTOM HANDBAG PROMPT")
    assert "CUSTOM HANDBAG PROMPT" in payload["ads_creative_set"]["static_image_ads"][0]["visual_prompt"]


def test_generate_keeps_final_video_prompt_under_provider_limit(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)
    long_negative_prompt = " ".join(
        [
            "Do not change product shape, colour, material, markings, scale, avatar identity, wardrobe, safe areas, lighting, realism, or product context."
            for _ in range(260)
        ]
    )

    response = client.post(
        "/generate",
        data={
            "product_name": "BELLA | LEATHER TOTE BAG",
            "product_info": "Structured daily bag with clean minimalist shape",
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "product_reference_url": "https://example.com/product.jpg",
            "negative_prompt": long_negative_prompt,
            "category_prompt_handbag": "CUSTOM HANDBAG PROMPT focus on handles and outfit-scale context",
        },
    )

    payload = response.json()
    prompt = payload["seedance_payload"]["prompt"]
    assert response.status_code == 200
    assert len(prompt) <= 18000
    assert "CUSTOM HANDBAG PROMPT" in prompt
    assert payload["provider_validation"]["status"] == "passed"
    assert payload["content_prompt_package"]["prompt_compression"]["fits_hard_limit"] is True
    assert payload["prompt_audit"]["structured_prompt_v2"]["final_prompt_chars"] == len(prompt)


def test_generate_includes_complete_ads_set_without_cta_links(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "meta",
            "language": "cs",
            "product_reference_url": "https://example.com/product.jpg",
            "landing_page_url": "https://shop.example.com/desk-lamp",
        },
    )

    assert response.status_code == 200
    ads = response.json()["ads_creative_set"]
    ads_text = str(ads)
    assert ads["cta_link_policy"]
    assert "https://shop.example.com/desk-lamp" not in ads_text
    assert "[vloz odkaz]" not in ads_text
    assert "[insert link]" not in ads_text
    assert len(ads["hook_bank"]) >= 5
    assert len(ads["creative_angles"]) >= 10
    assert ads["angle_multiplier_skill_applied"]["source"] == "ad-angle-multiplier"
    assert ads["ad_angle_multiplier"]["angle_count"] >= 10
    assert ads["angle_selector_applied"]["source"] == "ad-angle-selector"
    assert ads["ad_angle_selector"]["slot_selection"]["C2"]["selected_family"]
    assert ads["static_image_ads"][0]["angle_selection_reason"]
    assert len({item["angle_family"] for item in ads["static_image_ads"]}) >= 5
    assert all(item["angle_multiplier_angle"] for item in ads["static_image_ads"])
    assert all(item["angle_diversity_contract"] for item in ads["static_image_ads"])
    assert ads["carousel_ad"]["angle_selection_reason"]
    assert {
        item["angle_family"] for item in ads["ad_angle_multiplier"]["angles"]
    } == {"Pain", "Desire", "Proof", "Identity", "Contrarian", "Urgency"}
    assert response.json()["ugc_strategy"]["ad_angle_multiplier"]["skill_source"] == "local skill/ad-angle-multiplier"
    assert response.json()["ugc_strategy"]["ad_angle_selector"]["slot_selection"]["C4"]["score_breakdown"]
    assert response.json()["prompt_audit"]["prompt_graph"]["ad_angle_multiplier"]["angle_count"] >= 10
    assert response.json()["prompt_audit"]["prompt_graph"]["ad_angle_selector"]["slot_selection"]["C3"]["family"]
    assert ads["marketing_skill_applied"]["source"] == "coreyhaines31/marketingskills skills/ad-creative"
    assert ads["platform_copy_specs"]["platform"] == "meta"
    assert ads["copy_validation"]["passed"] is True
    assert ads["ad_description_suggestions"]["platform"] == "meta"
    assert len(ads["ad_description_suggestions"]["variants"]) == 5
    assert all(item["validation_status"] == "ok" for item in ads["ad_description_suggestions"]["variants"])
    assert [item["set_id"] for item in ads["creative_plan"]] == ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    assert ads["creative_plan"][0]["creative_type"] == "UGC video"
    assert ads["creative_plan"][1]["creative_type"] == "Static product hero"
    assert ads["creative_plan"][2]["angle"] == "USE_CONTEXT"
    assert ads["creative_plan"][3]["angle"] == "DETAIL_PROOF"
    assert ads["creative_plan"][4]["creative_type"] == "Carousel buying guide"
    assert ads["creative_plan"][3]["funnel_stage"] == "Retargeting"
    assert ads["creative_plan"][4]["budget_share_percent"] == 15
    assert len(ads["static_image_ads"]) == 5
    assert [item["set_id"] for item in ads["static_image_ads"]] == ["C2", "C3", "C4", "C6", "C7"]
    assert [item["angle"] for item in ads["static_image_ads"]] == [
        "PRODUCT_HERO",
        "USE_CONTEXT",
        "DETAIL_PROOF",
        "PAIN_POINT",
        "CONTRARIAN_CHECK",
    ]
    assert all(item["aspect_ratio"] == "1:1" for item in ads["static_image_ads"])
    assert "desk" in ads["static_image_ads"][0]["visual_prompt"].lower()
    assert "adult person" in ads["static_image_ads"][0]["visual_prompt"].lower()
    assert "use-context" in ads["static_image_ads"][1]["visual_prompt"].lower()
    assert "adult person" in ads["static_image_ads"][1]["visual_prompt"].lower()
    assert "70 percent" in ads["static_image_ads"][2]["visual_prompt"].lower()
    assert "adult" in ads["static_image_ads"][2]["visual_prompt"].lower()
    assert "must look visually different from C3 use-context scene" in ads["static_image_ads"][0]["visual_prompt"]
    assert "different plausible context than C2" in ads["static_image_ads"][1]["visual_prompt"]
    assert "distinct from C2 and C3" in ads["static_image_ads"][2]["visual_prompt"]
    assert "buyer-objection static" in ads["static_image_ads"][3]["visual_prompt"]
    assert "anti-gloss" in ads["static_image_ads"][4]["visual_prompt"]
    assert len({item["overlay_text"] for item in ads["static_image_ads"]}) == 5
    assert len({item["primary_text"].splitlines()[0] for item in ads["static_image_ads"]}) >= 4
    assert ads["carousel_ad"]["card_count"] == 5
    assert ads["carousel_ad"]["set_id"] == "C5"
    assert ads["carousel_ad"]["creative_type"] == "Carousel buying guide"
    assert ads["carousel_ad"]["aspect_ratio"] == "1:1"
    assert len(ads["meme_style_creatives"]) == 2
    assert ads["primary_text_variants"]


def test_generate_supports_google_ads_platform(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "google_ads",
            "language": "en",
            "product_reference_url": "https://example.com/product.jpg",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ugc_strategy"]["platform"] == "google_ads"
    assert payload["ugc_strategy"]["aspect_ratio"] == "16:9"
    assert "Google Ads" in payload["ugc_strategy"]["platform_adaptation"]["style"]
    assert "Google Ads" in payload["ads_creative_set"]["cta_link_policy"]
    assert "Meta Ads Manager" not in payload["ads_creative_set"]["cta_link_policy"]
    assert payload["ads_creative_set"]["platform_copy_specs"]["platform"] == "google_ads"
    assert payload["ads_creative_set"]["copy_validation"]["passed"] is True
    suggestions = payload["ads_creative_set"]["ad_description_suggestions"]
    assert suggestions["platform"] == "google_ads"
    assert len(suggestions["variants"]) == 4
    assert all(len(item["description"]) <= 90 for item in suggestions["variants"])
    rsa = payload["ads_creative_set"]["google_ads_assets"]["responsive_search_ad"]
    assert len(rsa["headlines"]) == 15
    assert len(rsa["descriptions"]) == 4
    assert all(len(item["text"]) <= 30 for item in rsa["headlines"])
    assert all(len(item["text"]) <= 90 for item in rsa["descriptions"])


def test_product_notes_are_internal_not_copied_to_ads(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Ona Bag",
            "product_info": "tajna interni poznamka NEKOPIROVAT do reklamy",
            "platform": "meta",
            "language": "cs",
            "product_reference_url": "https://example.com/product.jpg",
        },
    )

    assert response.status_code == 200
    payload_text = str(response.json())
    assert "NEKOPIROVAT do reklamy" in payload_text
    assert "NEKOPIROVAT do reklamy" not in str(response.json()["ugc_strategy"])
    assert "NEKOPIROVAT do reklamy" not in str(response.json()["ads_creative_set"])
    assert "NEKOPIROVAT do reklamy" not in response.json()["seedance_payload"]["prompt"]


def test_generate_prefers_public_reference_url_over_upload(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        files=_image_file(),
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
            "product_reference_url": "https://img.example.com/product.jpg?imageView2/2/format/avif",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["product_analysis"]["product_image_path"].endswith("/format/jpeg")
    assert payload["seedance_payload"]["input_reference_count"] == 1


def test_generate_uses_registered_avatar_public_url(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
            "avatar_id": "avatar1",
            "product_reference_url": "https://example.com/product.jpg",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["seedance_payload"]["input_reference_count"] == 1
    assert payload["seedance_payload"]["avatar_image_url"] == "https://i.ibb.co/6082rzf9/newkoi.png"
    assert payload["seedance_payload"]["avatar_reference_mode"] == "prompt_only_not_image_input"


def test_generate_can_disable_avatar_image_reference(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
            "avatar_id": "avatar1",
            "product_reference_url": "https://example.com/product.jpg",
            "use_avatar_image_reference": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["seedance_payload"]["input_reference_count"] == 1
    assert payload["seedance_payload"]["avatar_reference_mode"] == "prompt_only_not_image_input"


def test_generate_can_enable_avatar_image_reference(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
            "avatar_id": "avatar1",
            "product_reference_url": "https://example.com/product.jpg",
            "use_avatar_image_reference": "true",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["seedance_payload"]["input_reference_count"] == 2
    assert payload["seedance_payload"]["avatar_reference_mode"] == "exact_image_input_reference"
    assert payload["seedance_payload"]["avatar_identity_contract"]["identity_mode"] == "exact_image_reference"


def test_finance_approved_scene_blueprint_reaches_final_video_prompt(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "app_mode": "finance_personal_brand",
            "platform": "instagram",
            "market": "CZ",
            "language": "en",
            "avatar_id": "avatar1",
            "use_avatar_image_reference": "true",
            "avatar_reference_url": "https://example.com/avatar.jpg",
            "finance_video_topic": "Rezerva a investice",
            "finance_video_script": "Vysvětli, proč je dobré oddělit finanční rezervu od investic. Bez slibů a bez tlaku.",
            "finance_scene_approved": "true",
            "finance_scene_reference_url": "https://example.com/approved-finance-scene.png",
            "finance_scene_video_reference_url": "https://example.com/approved-finance-scene.png",
            "finance_scene_prompt": "Moderní podcastové studio, schválené karty Rezerva, Plán, Riziko a spodní lišta Vzdělávací obsah.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    prompt = payload["seedance_payload"]["prompt"]
    assert payload["ugc_strategy"]["language"] == "cs"
    assert "APPROVED FINANCE SCENE BLUEPRINT" in prompt
    assert "Rezerva" in prompt
    assert "Plán" in prompt
    assert "Riziko" in prompt
    assert "CZECH LANGUAGE HARD LOCK" in prompt
    assert "SPOKEN AUDIO REQUIREMENT" in prompt
    assert "avatar must speak Czech only" in prompt
    assert "Lip-sync" in prompt or "lip_sync" in prompt
    assert "no Polish" in prompt or "Polish" in prompt
    assert payload["content_prompt_package"]["finance_scene_concept"]["status"] == "approved_for_video"
    assert payload["content_prompt_package"]["speech_language_contract"]["spoken_language"] == "cs-CZ"
    assert payload["content_prompt_package"]["seedance_payload"]["speech_language"] == "cs-CZ"
    assert payload["ugc_strategy"]["scene_chaining"]["creative_mode"] == "finance_personal_brand"
    assert "Czech infographic" in payload["ugc_strategy"]["scene_chaining"]["true_scene_chaining_plan"]["product_or_graphic_lock"]
    assert next(
        check for check in payload["post_generation_qa"]["checks"] if check["id"] == "finance_czech_language"
    )["status"] == "passed"
    assert payload["content_prompt_package"]["seedance_payload"]["frame_images"]
    assert payload["content_prompt_package"]["structured_scene_prompt"]["variants"][0]["approved_scene_concept"]
    json_path = Path(payload["output_files"]["json_path"])
    assert json_path.parent.parent.name == "finance"
    assert "FIN_BRAND" in json_path.parent.name
    assert "rezerva-a-investice" in json_path.parent.name
    assert payload["user_input"]["session_workspace"] == "finance"
    assert payload["user_input"]["session_type"] == "FIN_BRAND"
    assert payload["output_files"]["workspace"] == "finance"


def test_generate_supports_custom_own_person_identity_lock(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "BELLA | LEATHER TOTE BAG",
            "product_info": "Structured daily bag with clean minimalist shape",
            "platform": "meta",
            "language": "en",
            "market": "UK",
            "avatar_id": "avatar1",
            "custom_avatar_name": "My UGC Person",
            "custom_avatar_persona": "calm British UGC creator, direct and natural",
            "custom_avatar_voice": "subtle British accent, conversational",
            "avatar_wardrobe_policy": "reference_unchanged",
            "avatar_identity_note": "Do not overact, keep delivery natural",
            "avatar_own_person_consent": "true",
            "avatar_reference_url": "https://example.com/avatar.jpg",
            "use_avatar_image_reference": "true",
            "product_reference_url": "https://example.com/product.jpg",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    contract = payload["seedance_payload"]["avatar_identity_contract"]
    first_scene = payload["content_prompt_package"]["structured_scene_prompt"]["variants"][0]["scenes"][0]
    assert contract["identity_mode"] == "exact_image_reference"
    assert contract["creator_label"] == "My UGC Person"
    assert contract["wardrobe_policy"] == "reference_unchanged"
    assert contract["own_person_or_authorized_avatar_confirmed"] is True
    assert "Souhlasím s použitím mé podoby" in contract["authorization_statement"]
    assert payload["seedance_payload"]["input_reference_count"] == 2
    assert first_scene["avatar_instruction"].startswith(
        "subject from reference image, identity preserved, no facial morphing, no appearance drift"
    )
    assert "wardrobe as in reference image, unchanged" in first_scene["avatar_instruction"]
    assert "friendly presenter" not in payload["seedance_payload"]["prompt"]


def test_generate_requires_upload_or_product_reference_url(monkeypatch, tmp_path):
    _configure_tmp_dirs(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "product_name": "Desk Lamp",
            "product_info": "Compact lamp for a clean desk setup",
            "platform": "tiktok",
            "language": "en",
        },
    )

    assert response.status_code == 400
    assert "product image" in response.json()["error"].lower()
