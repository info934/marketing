from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.react_ui import render_react_index
from app.ui import render_index


def test_index_script_contains_valid_newline_join_escape():
    html = render_index()

    assert 'return parts.join("\\n\\n");' in html
    assert 'return parts.join("\n\n");' not in html


def test_index_applies_query_parameters_to_form():
    html = render_index()

    assert "function applyQueryParams()" in html
    assert "new URLSearchParams(window.location.search)" in html
    assert "if (!window.location.search) return;" in html
    assert "applyQueryParams();" in html


def test_index_shows_creative_plan_sets():
    html = render_index()

    assert "C1 | UGC" in html
    assert "C2 | PRODUCT HERO | 1:1" in html
    assert "C3 | USE CONTEXT | 1:1" in html
    assert "C4 | DETAIL PROOF | 1:1" in html
    assert "C5 | BUYING GUIDE | 1:1" in html
    assert "function renderCreativePlan" in html
    assert "function renderImageGenerationPlan" in html
    assert "function renderWorkflowReport" in html
    assert "function renderRawAudit" in html
    assert "Workflow report" in html
    assert "Faze workflow" in html
    assert "Co workflow vyrobil" in html
    assert "generation_mode" in html
    assert "openai/gpt-5.4-mini" in html
    assert "Static prompt model" in html
    assert "Jen UGC video" in html
    assert "Jen statické kreativy" in html
    assert "Vybrane kreativy pro generovani" in html
    assert "Kreativy mimo generovani" in html
    assert "Mimo limit" in html
    assert "Proc se generuje" in html
    assert "Plan statickych obrazku" in html
    assert "Prompt pro obrazek" in html
    assert "Creative Intelligence" in html
    assert "/creative-intelligence" in html
    assert "/creative-intelligence-preview" in html
    assert "/creative-rating" in html
    assert "/performance-import" in html


def test_index_shows_prompt_source_inventory():
    html = render_index()

    assert "prompt_source_inventory" in html
    assert "Prompt/data source inventory" in html
    assert "{voice_profile}" in html
    assert "{category_prompt}" in html
    assert "product_category" in html
    assert "Category prompt presets" in html
    assert "category_prompt_handbag" in html
    assert "custom_avatar_name" in html
    assert "avatar_wardrobe_policy" in html
    assert "avatar_own_person_consent" in html
    assert "identity lock" in html
    assert "Souhlasím s použitím mé podoby" in html


def test_react_avatar_authorization_consent_copy_is_hardcoded():
    app_js = Path("app/static/react/app.js").read_text(encoding="utf-8")

    assert "Souhlasím s použitím mé podoby jako AI avatara" in app_js
    assert "authorizedAvatarConsent" in app_js


def test_react_new_campaign_simple_chat_mode_is_available():
    app_js = Path("app/static/react/app.js").read_text(encoding="utf-8")

    assert "campaign_input_mode" in app_js
    assert "Simple Chat Mode" in app_js
    assert "chatBriefItems" in app_js
    assert "/chat-brief-parser" in app_js
    assert "AI vyplnit brief" in app_js
    assert "Chat" in app_js
    assert "Expert" in app_js
    assert "Produkt" in app_js
    assert "Konkurence" in app_js
    assert "AI Brief Parser" in app_js


def test_next_orchestrator_surfaces_marketing_skill_stack():
    page_tsx = Path("frontend/app/page.tsx").read_text(encoding="utf-8")
    types_ts = Path("frontend/lib/types.ts").read_text(encoding="utf-8")
    api_ts = Path("frontend/lib/api.ts").read_text(encoding="utf-8")

    assert "MarketingSkillStackCard" in page_tsx
    assert "marketingSkillStackData" in page_tsx
    assert "Plan gate" in page_tsx
    assert "APPROVED_CREATIVE_MISSION_CONTRACT_V1" in page_tsx
    assert "hasApprovedCreativePlan" in page_tsx
    assert "Static ad concepts" in page_tsx
    assert "Quality gates" in page_tsx
    assert "Old portal fallback is disabled" in page_tsx
    assert "Clean memory mode" in page_tsx
    assert "Clean RAG start" in page_tsx
    assert 'body.set("creative_mission_contract_required", "true")' in api_ts
    assert "active_marketing_skill_plan" in types_ts
    assert "marketing_skill_registry" in types_ts
    assert "memory_epoch" in types_ts


def test_react_index_is_default_app_shell():
    html = render_react_index()

    assert "AI platforma pro reklamní kreativy" in html
    assert "/static/react/vendor/react.production.min.js" in html
    assert "/static/react/app.js" in html
    assert "__LEGACY_UI_CONTRACT__" in html


def test_root_serves_react_and_legacy_stays_available():
    client = TestClient(app)

    root = client.get("/")
    legacy = client.get("/legacy")

    assert root.status_code == 200
    assert "AI platforma pro reklamní kreativy" in root.text
    assert "/static/react/app.js" in root.text
    assert legacy.status_code == 200
    assert "function renderCreativePlan" in legacy.text
