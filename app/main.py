from __future__ import annotations

import concurrent.futures
import json
import shutil
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Body, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.avatar_loader import default_avatar_id, list_avatars, load_avatar, set_default_avatar, upsert_avatar
from app.company_loader import (
    company_context,
    company_context_text,
    default_company_id,
    list_companies,
    load_company,
    set_default_company,
    upsert_company,
)
from app.react_ui import render_react_index
from app.ui import render_index
from app.services import (
    ads_creative_set_agent,
    ad_angle_multiplier,
    ad_angle_selector,
    audit_builder,
    audience_research_agent,
    chat_brief_parser_agent,
    compliance_guard,
    competitor_strategy_agent,
    content_prompt_engineer_agent,
    creative_orchestrator,
    cost_tracker,
    creative_memory_db,
    creative_memory_learning_service,
    creative_plan_service,
    creative_self_critique,
    creative_psychology_agent,
    emotional_angle_engine,
    finance_video_agent,
    generation_run_repository,
    openrouter_seedance_client,
    openrouter_image_client,
    openrouter_prompt_client,
    output_writer,
    performance_memory,
    post_generation_qa,
    preflight_validator,
    prompt_defaults,
    prompt_graph_service,
    provider_capability_service,
    product_fidelity_guard,
    product_intake_agent,
    product_understanding_agent,
    quality_scorer,
    scenario_integrity_guard,
    scene_director_agent,
    scene_chaining_agent,
    structured_prompt_v2,
    ugc_hook_agent,
    ugc_agent,
    visual_product_classifier_agent,
    voice_personality_engine,
    workflow_reporter,
)
from app.services.image_reference_utils import (
    data_url_reference,
    image_url_reference,
    normalize_public_image_url,
)
from app.services.avatar_authorization import AUTHORIZED_AVATAR_CONSENT_STATEMENT
from app.services.text_utils import safe_slug, sanitize_avatar_descriptor


app = FastAPI(title="Multi-Agent UGC Workflow", version="1.0.0")
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR, check_dir=False), name="output")
app.mount("/static", StaticFiles(directory=Path("app/static"), check_dir=False), name="static")
_generation_lock = threading.Lock()
_generation_submission_lock = threading.Lock()
PRODUCT_UNDERSTANDING_TIMEOUT_SECONDS = 85
VISUAL_PRODUCT_CLASSIFIER_TIMEOUT_SECONDS = 115


@app.middleware("http")
async def single_generation_guard(request: Request, call_next):
    if request.method.upper() == "POST" and request.url.path == "/generate":
        if not _generation_lock.acquire(blocking=False):
            return JSONResponse(
                content={
                    "status": "blocked",
                    "error": "Generation already in progress.",
                    "reason": "A previous creative generation is still running, so this request was not started.",
                    "next_step": "Wait for the current generation to finish, or stop/restart the local server if it is stuck.",
                },
                status_code=409,
            )
        try:
            return await call_next(request)
        finally:
            _generation_lock.release()
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse(render_react_index())


@app.get("/legacy", response_class=HTMLResponse)
def legacy_index() -> HTMLResponse:
    return HTMLResponse(render_index())


@app.get("/prompt-settings")
def prompt_settings() -> dict[str, Any]:
    return prompt_defaults.defaults()


@app.get("/performance-memory")
def get_performance_memory() -> dict[str, Any]:
    return performance_memory.load_memory()


@app.get("/orchestrator")
def orchestrator() -> dict[str, Any]:
    latest_run = generation_run_repository.latest_run()
    return creative_orchestrator.snapshot(latest_run)


@app.get("/companies")
def companies() -> dict[str, Any]:
    default_id = default_company_id()
    company_items = []
    for company in list_companies():
        item = _company_public_payload(company, default_id=default_id)
        company_items.append(item)
    return {
        "version": "company_library_v1",
        "default_company_id": default_id,
        "companies": company_items,
    }


def _company_public_payload(company: dict[str, Any], default_id: str | None = None) -> dict[str, Any]:
    item = dict(company)
    if default_id is None:
        default_id = default_company_id()
    item["is_default"] = item.get("id") == default_id
    item["context_text"] = company_context_text(item)
    return item


@app.post("/companies")
def save_company(profile: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        saved = upsert_company(profile)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    return JSONResponse(content={"status": "saved", "company": _company_public_payload(saved)})


@app.put("/companies/{company_id}")
def update_company(company_id: str, profile: dict[str, Any] = Body(...)) -> JSONResponse:
    payload = dict(profile)
    payload["id"] = company_id
    try:
        saved = upsert_company(payload)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    return JSONResponse(content={"status": "saved", "company": _company_public_payload(saved)})


@app.post("/companies/{company_id}/default")
def make_default_company(company_id: str) -> JSONResponse:
    try:
        saved = set_default_company(company_id)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=404)
    return JSONResponse(content={"status": "saved", "company": _company_public_payload(saved), "default_company_id": company_id})


@app.get("/avatars")
def avatars() -> dict[str, Any]:
    default_id = default_avatar_id()
    avatar_items = []
    for avatar in list_avatars():
        item = _avatar_public_payload(avatar, default_id=default_id)
        avatar_items.append(item)
    stats = creative_memory_db.avatar_statistics(avatar_items)
    for avatar in avatar_items:
        avatar["stats"] = stats["stats"].get(str(avatar.get("id") or ""), {})
    return {
        "version": "avatar_library_v1",
        "default_avatar_id": default_id,
        "avatars": avatar_items,
        "stats": stats,
    }


def _avatar_public_payload(avatar: dict[str, Any], default_id: str | None = None) -> dict[str, Any]:
    item = dict(avatar)
    if default_id is None:
        default_id = default_avatar_id()
    item["is_default"] = item.get("id") == default_id
    image_url = normalize_public_image_url(str(item.get("image_url") or "").strip())
    if image_url:
        item["image_url"] = image_url
    if item.get("image_path"):
        item["preview_url"] = f"/avatar-image/{item.get('id')}"
        item["local_image_only"] = not bool(item.get("image_url"))
    else:
        item["preview_url"] = image_url or item.get("image_url")
        item["local_image_only"] = False
    return item


@app.post("/avatars")
def save_avatar(profile: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        saved = upsert_avatar(profile)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    return JSONResponse(content={"status": "saved", "avatar": _avatar_public_payload(saved)})


@app.put("/avatars/{avatar_id}")
def update_avatar(avatar_id: str, profile: dict[str, Any] = Body(...)) -> JSONResponse:
    payload = dict(profile)
    payload["id"] = avatar_id
    try:
        saved = upsert_avatar(payload)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    return JSONResponse(content={"status": "saved", "avatar": _avatar_public_payload(saved)})


@app.post("/avatars/{avatar_id}/default")
def make_default_avatar(avatar_id: str) -> JSONResponse:
    try:
        saved = set_default_avatar(avatar_id)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=404)
    return JSONResponse(content={"status": "saved", "avatar": _avatar_public_payload(saved), "default_avatar_id": avatar_id})


@app.post("/avatars/upload")
def upload_avatar(
    avatar_id: str = Form(""),
    id: str = Form(""),
    name: str = Form(""),
    style: str = Form("natural UGC creator"),
    voice: str = Form("natural conversational creator voice"),
    image_url: str = Form(""),
    is_default: bool = Form(False),
    avatar_image: UploadFile | None = File(None),
) -> JSONResponse:
    avatar_name = name.strip() or "Custom Avatar"
    requested_id = (avatar_id or id).strip()
    clean_avatar_id = safe_slug(requested_id or avatar_name, "avatar") or f"avatar_{int(time.time())}"
    payload: dict[str, Any] = {
        "id": clean_avatar_id,
        "name": avatar_name,
        "style": style,
        "voice": voice,
        "is_default": is_default,
    }
    normalized_image_url = normalize_public_image_url(image_url.strip()) or image_url.strip()
    if normalized_image_url:
        payload["image_url"] = normalized_image_url
    if avatar_image and avatar_image.filename:
        suffix = Path(avatar_image.filename).suffix or ".png"
        target = config.AVATAR_DATA_PATH.parent / "avatars" / f"{clean_avatar_id}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as file_obj:
            shutil.copyfileobj(avatar_image.file, file_obj)
        payload["image_path"] = str(target)
    try:
        saved = upsert_avatar(payload)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    return JSONResponse(content={"status": "saved", "avatar": _avatar_public_payload(saved)})


@app.get("/avatar-image/{avatar_id}", response_model=None)
def avatar_image(avatar_id: str):
    avatar = load_avatar(avatar_id)
    image_path = Path(str(avatar.get("image_path") or ""))
    if not image_path.exists() or not image_path.is_file():
        return JSONResponse(
            content={"status": "failed", "error": "Avatar image file not found"},
            status_code=404,
        )
    return FileResponse(image_path)


@app.post("/performance-memory")
def add_performance_memory(record: dict[str, Any] = Body(...)) -> dict[str, Any]:
    saved = performance_memory.add_record(record)
    return {"status": "saved", "record": saved}


@app.get("/creative-intelligence")
def creative_intelligence(workspace: str = "") -> dict[str, Any]:
    return creative_memory_db.intelligence_summary(workspace=workspace)


@app.get("/creative-memory/learning")
def creative_memory_learning(workspace: str = "") -> dict[str, Any]:
    return creative_memory_learning_service.learning_snapshot(workspace=workspace)


@app.get("/openrouter-cost/latest")
def openrouter_cost_latest(workspace: str = "ecommerce") -> JSONResponse:
    run = generation_run_repository.latest_run(workspace=workspace)
    if not run:
        return JSONResponse(
            content={
                "status": "missing",
                "workspace": workspace,
                "reason": "No generation run is available for this workspace.",
            },
            status_code=404,
        )
    final_output = run.get("final_output") or {}
    summary = run.get("cost_summary") or final_output.get("session_cost_summary") or {}
    return JSONResponse(
        content={
            "status": summary.get("status") or "unknown",
            "workspace": run.get("workspace") or workspace,
            "run_id": run.get("run_id"),
            "cost_summary": summary,
        }
    )


@app.get("/generation-runs/{run_id}/cost")
def generation_run_cost(run_id: str) -> JSONResponse:
    run = generation_run_repository.get_run(run_id)
    if not run:
        return JSONResponse(
            content={"status": "missing", "run_id": run_id, "reason": "Generation run was not found."},
            status_code=404,
        )
    final_output = run.get("final_output") or {}
    summary = run.get("cost_summary") or final_output.get("session_cost_summary") or {}
    return JSONResponse(
        content={
            "status": summary.get("status") or "unknown",
            "workspace": run.get("workspace"),
            "run_id": run_id,
            "cost_summary": summary,
        }
    )


@app.post("/finance-scene-preview")
def finance_scene_preview(
    avatar_id: str = Form("default_creator"),
    avatar_data: str | None = Form(None),
    custom_avatar_name: str = Form(""),
    custom_avatar_persona: str = Form(""),
    custom_avatar_voice: str = Form(""),
    avatar_wardrobe_policy: str = Form("reference_unchanged"),
    avatar_identity_note: str = Form(""),
    avatar_own_person_consent: bool = Form(True),
    avatar_reference_url: str = Form(""),
    platform: str = Form("meta"),
    finance_video_topic: str = Form(""),
    finance_video_script: str = Form(""),
    finance_disclaimer: str = Form(""),
    openrouter_api_key: str = Form(""),
    prompt_model: str = Form(config.OPENROUTER_PROMPT_MODEL),
    image_model: str = Form(config.OPENROUTER_IMAGE_MODEL),
    image_size: str = Form("1K"),
) -> JSONResponse:
    topic = finance_video_topic.strip() or "Finanční osobní brand video"
    script = finance_video_script.strip()
    if not script:
        return JSONResponse(
            content={
                "status": "blocked",
                "error": "Finance script is required before preparing a scene concept.",
                "next_step": "Vyplň text, který má osobní brand říkat, a potom připrav scénu.",
            },
            status_code=400,
        )
    if platform not in {"meta", "instagram"}:
        platform = "meta"
    avatar = load_avatar(avatar_id, avatar_data)
    avatar = _apply_custom_avatar_profile(
        avatar=avatar,
        custom_avatar_name=custom_avatar_name,
        custom_avatar_persona=custom_avatar_persona,
        custom_avatar_voice=custom_avatar_voice,
        avatar_wardrobe_policy=avatar_wardrobe_policy,
        avatar_identity_note=avatar_identity_note,
        avatar_own_person_consent=avatar_own_person_consent,
    )
    avatar_reference = normalize_public_image_url(avatar_reference_url.strip())
    if avatar_reference:
        avatar["image_url"] = avatar_reference
    avatar_scene_references = [
        str(item)
        for item in [
            avatar_reference,
            avatar.get("image_url"),
            avatar.get("image_path"),
        ]
        if str(item or "").strip()
    ][:1]
    script_plan = finance_video_agent.prepare_script_plan(
        topic=topic,
        user_script=script,
        disclaimer=finance_disclaimer,
        platform=platform,
        api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
        model=prompt_model,
    )
    scene_concept = finance_video_agent.build_scene_concept(
        topic=topic,
        script_plan=script_plan,
        avatar=avatar,
        platform=platform,
    )
    output_dir = _create_session_output_dir(
        f"{topic} scene concept",
        config.OUTPUT_DIR,
        app_mode="finance_personal_brand",
        session_prefix="FIN_SCENE",
        subfolder="scene concepts",
    )
    image_generation = openrouter_image_client.generate_single_image(
        prompt=scene_concept["image_prompt"],
        creative_id="finance_scene_concept",
        product_name=topic,
        output_dir=output_dir,
        api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
        model=image_model,
        aspect_ratio="9:16",
        image_size=image_size,
        reference_image_urls=avatar_scene_references,
    )
    asset = (image_generation.get("image_assets") or [{}])[0]
    source_reference_url = str(asset.get("source_image_url") or "")
    scene_reference_url = source_reference_url if _is_public_http_url(source_reference_url) else ""
    if not scene_reference_url:
        scene_reference_url = str(asset.get("image_url") or "")
    scene_cost_summary = cost_tracker.build_finance_scene_preview_cost_summary(
        finance_script_agent=script_plan,
        scene_image_generation=image_generation,
    )
    return JSONResponse(
        content={
            "status": "ready_for_approval",
            "final_export_status": "needs_scene_approval",
            "next_step": "Schval návrh scény. Teprve potom se odešle video do Seedance.",
            "finance_script_agent": script_plan,
            "finance_scene_concept": scene_concept,
            "scene_image_generation": image_generation,
            "scene_cost_summary": scene_cost_summary,
            "scene_reference_url": scene_reference_url,
            "scene_reference_public_for_video": bool(_is_public_http_url(source_reference_url)),
            "scene_reference_video_url": source_reference_url if _is_public_http_url(source_reference_url) else "",
            "avatar_reference_used_for_scene": bool(avatar_scene_references),
            "avatar_scene_reference_type": (
                "public_url"
                if avatar_scene_references and _is_public_http_url(avatar_scene_references[0])
                else "local_or_data_url"
                if avatar_scene_references
                else "none"
            ),
            "output_dir": str(output_dir),
        }
    )


@app.post("/creative-intelligence-preview")
def creative_intelligence_preview(brief: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return creative_memory_db.preview_guidance(brief)


@app.post("/prompt-learning-guidance")
def prompt_learning_guidance(brief: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return creative_memory_learning_service.guidance_for_brief(brief)


@app.get("/creative-memory/creatives")
def creative_memory_creatives(
    limit: int = 50,
    product_id: str = "",
    campaign_id: str = "",
    workspace: str = "",
) -> dict[str, Any]:
    return creative_memory_db.list_creatives(
        limit=limit,
        product_id=product_id,
        campaign_id=campaign_id,
        workspace=workspace,
    )


@app.get("/provider-capabilities")
def provider_capabilities() -> dict[str, Any]:
    return provider_capability_service.registry()


@app.post("/provider-validation-preview")
def provider_validation_preview(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    app_mode = _form_str(payload, "app_mode", "ecommerce")
    finance_mode = app_mode.strip() == "finance_personal_brand"
    generation_mode = "video" if finance_mode else _form_str(payload, "generation_mode", "both")
    max_static_images = 0 if finance_mode else _form_int(payload, "max_static_images", openrouter_image_client.DEFAULT_MAX_IMAGES)
    should_generate_video = generation_mode in {"both", "video"}
    should_generate_static_images = (not finance_mode) and generation_mode in {"both", "static"} and max_static_images > 0
    validation = preflight_validator.validate(
        generation_mode=generation_mode,
        should_generate_video=should_generate_video,
        should_generate_static_images=should_generate_static_images,
        product_reference_url=normalize_public_image_url(_form_str(payload, "product_reference_url").strip()),
        avatar_reference_url=normalize_public_image_url(_form_str(payload, "avatar_reference_url").strip()),
        use_avatar_image_reference=_form_bool(payload, "use_avatar_image_reference", True),
        seedance_model=_form_str(payload, "seedance_model", config.OPENROUTER_SEEDANCE_MODEL),
        image_model=_form_str(payload, "image_model", config.OPENROUTER_IMAGE_MODEL),
        max_static_images=max_static_images,
        image_size=_form_str(payload, "image_size", "1K"),
        require_product_reference_for_video=not finance_mode,
    )
    return {
        "version": "provider_validation_preview_v1",
        "workspace": "finance" if finance_mode else "ecommerce",
        "app_mode": "finance_personal_brand" if finance_mode else "ecommerce",
        "generation_mode": generation_mode,
        "should_generate_video": should_generate_video,
        "should_generate_static_images": should_generate_static_images,
        **validation,
    }


@app.post("/creative-plan-preview")
async def creative_plan_preview(request: Request) -> JSONResponse:
    form = await request.form()
    app_mode = _form_str(form, "app_mode", "ecommerce")
    payload = creative_plan_service.preview(
        app_mode=app_mode,
        generation_mode=_form_str(form, "generation_mode", "both"),
        max_static_images=_form_int(form, "max_static_images", openrouter_image_client.DEFAULT_MAX_IMAGES),
        image_model=_form_str(form, "image_model", config.OPENROUTER_IMAGE_MODEL),
        seedance_model=_form_str(form, "seedance_model", config.OPENROUTER_SEEDANCE_MODEL),
        api_key_available=bool(_form_str(form, "openrouter_api_key") or config.OPENROUTER_API_KEY),
    )
    return JSONResponse(content=payload)


@app.post("/chat-brief-parser")
def chat_brief_parser(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    result = chat_brief_parser_agent.parse(
        payload,
        api_key=_form_str(payload, "openrouter_api_key") or config.OPENROUTER_API_KEY,
        model=_form_str(payload, "prompt_model", config.OPENROUTER_PROMPT_MODEL),
    )
    return JSONResponse(content=result)


@app.post("/generation-runs")
async def create_generation_run(request: Request) -> JSONResponse:
    form = await request.form()
    staged_upload = None
    staged_static_product_images: list[Any] = []
    staged_competitor_screenshots: list[Any] = []
    try:
        app_mode = _form_str(form, "app_mode", "ecommerce")
        workspace = "finance" if app_mode.strip() == "finance_personal_brand" else "ecommerce"
        with _generation_submission_lock:
            active = generation_run_repository.active_run(workspace=workspace)
            if active:
                return JSONResponse(
                    content={
                        "status": "blocked",
                        "error": "Generation already in progress for this workspace.",
                        "reason": "A previous creative generation is still running in the same workspace, so this request was not started.",
                        "next_step": "Wait for the current run to finish, or cancel it if it is still interruptible.",
                        "generation_run": _generation_run_response(active),
                    },
                    status_code=409,
                )
            staged_upload = _stage_upload_for_background(_form_upload(form, "product_image"))
            staged_static_product_images = _stage_uploads_for_background(_form_uploads(form, "product_static_images"))
            staged_competitor_screenshots = _stage_uploads_for_background(_form_uploads(form, "competitor_screenshots"))
            product_reference = normalize_public_image_url(_form_str(form, "product_reference_url").strip())
            if workspace == "ecommerce" and not staged_upload and not staged_static_product_images and not product_reference:
                return JSONResponse(
                    content={"error": "Upload a product image or provide a public HTTPS product reference URL."},
                    status_code=400,
                )
            idempotency_key = _form_str(form, "idempotency_key") or _generated_idempotency_key(workspace)
            generation_run = generation_run_repository.create_run(
                workspace=workspace,
                app_mode="finance_personal_brand" if workspace == "finance" else "ecommerce",
                input_snapshot=_generation_run_form_snapshot(form, staged_upload),
                idempotency_key=idempotency_key,
            )
            if generation_run.get("idempotency_reused"):
                _cleanup_staged_upload(staged_upload)
                _cleanup_staged_upload(staged_static_product_images)
                _cleanup_staged_upload(staged_competitor_screenshots)
                return JSONResponse(
                    content={
                        "status": "blocked",
                        "error": "Generation with this idempotency key is already running.",
                        "reason": "A matching active generation run already exists, so duplicate provider calls were not started.",
                        "generation_run": _generation_run_response(generation_run),
                    },
                    status_code=409,
                )

            kwargs = _generation_kwargs_from_form(
                form,
                product_image=staged_upload,
                product_static_images=staged_static_product_images,
                competitor_screenshots=staged_competitor_screenshots,
                idempotency_key=idempotency_key,
                existing_generation_run_id=generation_run["run_id"],
            )
            generation_run_repository.update_stage(
                generation_run["run_id"],
                "queued",
                status="queued",
                data={"message": "Run accepted and background worker is starting."},
            )
        thread = threading.Thread(
            target=_run_generation_background,
            args=(generation_run["run_id"], kwargs, [staged_upload, *staged_static_product_images, *staged_competitor_screenshots]),
            name=f"generation-run-{generation_run['run_id']}",
            daemon=True,
        )
        thread.start()
        run = generation_run_repository.get_run(generation_run["run_id"]) or generation_run
        return JSONResponse(
            content={
                "status": "queued",
                "final_export_status": "queued",
                "run_id": run["run_id"],
                "generation_run": run,
                "next_step": "Monitor this run via GET /generation-runs/{run_id}.",
            },
            status_code=202,
        )
    except Exception as exc:
        _cleanup_staged_upload(staged_upload)
        _cleanup_staged_upload(staged_static_product_images)
        _cleanup_staged_upload(staged_competitor_screenshots)
        return JSONResponse(
            content={"status": "failed", "error": str(exc)},
            status_code=500,
        )


@app.get("/generation-runs/latest")
def latest_generation_run(workspace: str = "") -> JSONResponse:
    run = generation_run_repository.latest_run(workspace=workspace)
    if not run:
        return JSONResponse(content={"status": "missing", "error": "No generation run found."}, status_code=404)
    return JSONResponse(content=_generation_run_response(run))


@app.get("/generation-runs")
def generation_runs(workspace: str = "", limit: int = 80) -> JSONResponse:
    runs = generation_run_repository.list_runs(workspace=workspace, limit=limit)
    items = [_generation_run_cost_item(run) for run in runs]
    known_total = round(
        sum(float((item.get("cost_summary") or {}).get("total_known_cost") or 0) for item in items),
        10,
    )
    return JSONResponse(
        content={
            "status": "ok",
            "workspace": workspace or "all",
            "count": len(items),
            "total_known_cost": known_total,
            "total_known_cost_usd_display": _format_cost_usd(known_total),
            "runs": items,
        }
    )


@app.get("/generation-runs/{run_id}")
def generation_run(run_id: str) -> JSONResponse:
    run = generation_run_repository.get_run(run_id)
    if not run:
        return JSONResponse(content={"status": "missing", "error": f"Unknown generation run: {run_id}"}, status_code=404)
    return JSONResponse(content=_generation_run_response(run))


@app.post("/generation-runs/{run_id}/cancel")
def cancel_generation_run(run_id: str) -> JSONResponse:
    run = generation_run_repository.request_cancel(run_id)
    if run.get("status") in generation_run_repository.ACTIVE_STATUSES:
        generation_run_repository.update_stage(
            run_id,
            "cancel_requested",
            status="cancelled",
            data={"reason": "User requested cancellation. The next generation stage will stop before calling another provider."},
        )
        run = generation_run_repository.get_run(run_id) or run
    return JSONResponse(content=_generation_run_response(run))


def _generation_run_response(run: dict[str, Any]) -> dict[str, Any]:
    final_output = run.get("final_output") if isinstance(run.get("final_output"), dict) else {}
    payload = dict(run)
    payload["final_export_status"] = final_output.get("final_export_status") or run.get("status")
    for key in [
        "creative_plan_preview",
        "ads_creative_set",
        "video_generation",
        "static_image_generation",
        "session_cost_summary",
        "workflow_report",
        "self_critique",
        "creative_memory",
        "output_files",
        "product_fidelity_result",
        "compliance_result",
        "quality_result",
    ]:
        payload[key] = final_output.get(key) or {}
    payload["prompt_audit"] = run.get("prompt_audit") or final_output.get("prompt_audit") or {}
    payload["provider_validation"] = run.get("provider_validation") or final_output.get("provider_validation") or {}
    payload["cost_summary"] = run.get("cost_summary") or final_output.get("session_cost_summary") or {}
    payload["last_error"] = _generation_run_error(payload)
    payload["partial_outputs"] = _generation_run_partial_outputs(payload)
    payload["monitor"] = _generation_run_monitor(payload)
    return payload


def _generation_run_monitor(run: dict[str, Any]) -> dict[str, Any]:
    status = str(run.get("status") or "").lower()
    stage = str(run.get("current_stage") or status or "queued")
    stages = run.get("stage_results") if isinstance(run.get("stage_results"), list) else []
    latest_stage = stages[-1] if stages else {}
    partial_outputs = run.get("partial_outputs") if isinstance(run.get("partial_outputs"), dict) else {}
    latest_message = (latest_stage.get("data") or {}).get("message") or (latest_stage.get("data") or {}).get("reason") or ""
    if not latest_message and stage == "generating_images" and partial_outputs.get("image_count"):
        latest_message = f"Statiky se generuji: {partial_outputs.get('image_count')} souboru uz ulozeno."
    if not latest_message and stage == "generating_video" and partial_outputs.get("video_count"):
        latest_message = f"Video provider ulozil {partial_outputs.get('video_count')} video soubor."
    blockers = _generation_run_blockers(run)
    hard_blockers = [
        blocker
        for blocker in blockers
        if str(blocker.get("id") or "").lower() in {"blocked", "failed"}
    ]
    if status == "completed" and hard_blockers:
        status = "blocked"
        stage = "completed"
    terminal_reason = _generation_run_error(run) if status not in generation_run_repository.ACTIVE_STATUSES else ""
    return {
        "status": status,
        "status_label": _run_status_label(status),
        "stage": stage,
        "stage_label": _run_stage_label(stage),
        "progress_percent": _run_progress_percent(status, stage),
        "is_active": status in generation_run_repository.ACTIVE_STATUSES,
        "is_terminal": status not in generation_run_repository.ACTIVE_STATUSES,
        "can_cancel": status in generation_run_repository.ACTIVE_STATUSES and not run.get("cancel_requested"),
        "latest_message": latest_message,
        "latest_stage": latest_stage,
        "stage_count": len(stages),
        "terminal_reason": terminal_reason,
        "next_step": _generation_run_next_step(run),
        "blockers": blockers,
        "partial_outputs": partial_outputs,
    }


def _generation_run_partial_outputs(run: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(str(run.get("output_dir") or ""))
    if not output_dir:
        return {}
    try:
        output_dir = output_dir.resolve()
        output_root = config.OUTPUT_DIR.resolve()
        output_dir.relative_to(output_root)
    except Exception:
        return {}
    if not output_dir.exists() or not output_dir.is_dir():
        return {}

    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
    video_suffixes = {".mp4", ".webm", ".mov"}
    assets: list[dict[str, Any]] = []
    try:
        files = [path for path in output_dir.rglob("*") if path.is_file()]
    except Exception:
        return {}
    for path in files:
        suffix = path.suffix.lower()
        if suffix not in image_suffixes and suffix not in video_suffixes:
            continue
        try:
            relative = path.resolve().relative_to(output_dir)
        except Exception:
            continue
        if "inputs" in relative.parts:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        asset_type = "image" if suffix in image_suffixes else "video"
        assets.append(
            {
                "type": asset_type,
                "name": path.name,
                "path": str(path),
                "url": _output_file_url(path),
                "bytes": stat.st_size,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(stat.st_mtime)),
            }
        )
    assets.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    images = [asset for asset in assets if asset.get("type") == "image"]
    videos = [asset for asset in assets if asset.get("type") == "video"]
    return {
        "output_dir": str(output_dir),
        "image_count": len(images),
        "video_count": len(videos),
        "images": images[:24],
        "videos": videos[:8],
        "latest_asset_updated_at": assets[0].get("updated_at") if assets else "",
    }


def _output_file_url(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(config.OUTPUT_DIR.resolve())
        return f"/output/{relative.as_posix()}"
    except Exception:
        return f"/output/{path.name}"


def _generation_run_cost_item(run: dict[str, Any]) -> dict[str, Any]:
    final_output = run.get("final_output") if isinstance(run.get("final_output"), dict) else {}
    cost_summary = run.get("cost_summary") or final_output.get("session_cost_summary") or {}
    input_snapshot = run.get("input_snapshot") if isinstance(run.get("input_snapshot"), dict) else {}
    total_cost = cost_summary.get("total_known_cost")
    return {
        "run_id": run.get("run_id"),
        "workspace": run.get("workspace"),
        "app_mode": run.get("app_mode"),
        "status": run.get("status"),
        "current_stage": run.get("current_stage"),
        "product_name": input_snapshot.get("product_name") or (final_output.get("user_input") or {}).get("product_name") or "",
        "generation_mode": input_snapshot.get("generation_mode") or "",
        "created_at": run.get("created_at"),
        "updated_at": run.get("updated_at"),
        "cost_summary": cost_summary,
        "total_known_cost": total_cost,
        "total_known_cost_usd_display": cost_summary.get("total_known_cost_usd_display") or _format_cost_usd(total_cost),
        "request_count": cost_summary.get("request_count") or 0,
        "unknown_request_count": cost_summary.get("unknown_request_count") or 0,
        "component_count": cost_summary.get("component_count") or 0,
        "monitor": _generation_run_monitor(run),
    }


def _format_cost_usd(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "unknown"
    return f"${number:.6f}".rstrip("0").rstrip(".")


def _run_progress_percent(status: str, stage: str) -> int:
    if status == "completed":
        return 100
    if status in {"blocked", "failed", "cancelled", "needs_confirmation", "needs_scene_approval"}:
        return 88
    order = {
        "queued": 5,
        "validating": 12,
        "planning": 24,
        "prompting": 42,
        "creative_plan": 50,
        "generating_video": 68,
        "generating_images": 80,
        "qa": 90,
        "saving": 96,
    }
    return order.get(stage, order.get(status, 10))


def _generation_run_error(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return str(payload.get("error"))
    compliance_failure = _specific_compliance_failure(payload)
    for section_key in ["video_generation", "static_image_generation", "provider_validation"]:
        section = payload.get(section_key) or {}
        if _section_skipped_by_generation_mode(payload, section_key, section):
            continue
        for field in ["failure_reason", "error", "reason"]:
            if section.get(field):
                message = str(section[field])
                if compliance_failure and _is_generic_compliance_message(message):
                    return compliance_failure
                return message
    if compliance_failure:
        return compliance_failure
    return ""


def _generation_run_next_step(payload: dict[str, Any]) -> str:
    provider = payload.get("provider_validation") or {}
    for check in provider.get("checks") or []:
        if check.get("status") == "failed":
            return str(check.get("next_step") or check.get("reason") or "")
    for section_key in ["video_generation", "static_image_generation"]:
        section = payload.get(section_key) or {}
        if _section_skipped_by_generation_mode(payload, section_key, section):
            continue
        if section.get("next_step"):
            return str(section.get("next_step"))
    status = str(payload.get("status") or payload.get("final_export_status") or "").lower()
    if status == "needs_scene_approval":
        return "Připrav a schval finance scénu, potom spusť video znovu."
    if status == "needs_confirmation":
        return "Potvrď navrženou sérii; appka následně vygeneruje první ukázkové video."
    if status == "cancelled":
        return "Spusť nový run, až budeš chtít pokračovat."
    return ""


def _generation_run_blockers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = []
    provider = payload.get("provider_validation") or {}
    for check in provider.get("checks") or []:
        if check.get("status") == "failed":
            blockers.append(
                {
                    "source": "provider_validation",
                    "id": check.get("id"),
                    "reason": check.get("reason"),
                    "next_step": check.get("next_step"),
                }
            )
    for section_key in ["video_generation", "static_image_generation"]:
        section = payload.get(section_key) or {}
        if _section_skipped_by_generation_mode(payload, section_key, section):
            continue
        if section.get("failure_reason") or section.get("error"):
            reason = section.get("failure_reason") or section.get("error")
            compliance_failure = _specific_compliance_failure(payload)
            if compliance_failure and _is_generic_compliance_message(str(reason or "")):
                reason = compliance_failure
            blockers.append(
                {
                    "source": section_key,
                    "id": section.get("video_generation_status") or section.get("image_generation_status"),
                    "reason": reason,
                    "next_step": section.get("next_step"),
                }
            )
    return blockers[:8]


def _section_skipped_by_generation_mode(
    payload: dict[str, Any],
    section_key: str,
    section: dict[str, Any],
) -> bool:
    if section.get("skipped_by_generation_mode"):
        return True
    if section_key not in {"video_generation", "static_image_generation"}:
        return False
    input_snapshot = payload.get("input_snapshot") if isinstance(payload.get("input_snapshot"), dict) else {}
    final_output = payload.get("final_output") if isinstance(payload.get("final_output"), dict) else {}
    user_input = final_output.get("user_input") if isinstance(final_output.get("user_input"), dict) else {}
    mode = str(input_snapshot.get("generation_mode") or user_input.get("generation_mode") or "").lower()
    if section_key == "video_generation" and mode == "static":
        return True
    if section_key == "static_image_generation" and mode == "video":
        return True
    return False


def _specific_compliance_failure(payload: dict[str, Any]) -> str:
    compliance_result = payload.get("compliance_result") or {}
    if compliance_result.get("compliance_status") != "fail":
        return ""
    details = _compliance_block_details(compliance_result)
    return f"Compliance Guard failed: {', '.join(details) if details else 'compliance requirements were not met'}"


def _is_generic_compliance_message(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized == "compliance guard failed: compliance requirements were not met"


def _run_status_label(status: str) -> str:
    labels = {
        "queued": "Zařazeno",
        "validating": "Validace",
        "planning": "Plánování",
        "prompting": "Promptování",
        "creative_plan": "Creative plán",
        "generating_video": "Generování videa",
        "generating_images": "Generování obrázků",
        "qa": "QA",
        "saving": "Ukládání",
        "completed": "Dokončeno",
        "blocked": "Blokováno",
        "failed": "Chyba",
        "cancelled": "Zastaveno",
        "needs_confirmation": "Čeká na potvrzení",
        "needs_scene_approval": "Čeká na scénu",
    }
    return labels.get(status, status or "neznámý")


def _run_stage_label(stage: str) -> str:
    return _run_status_label(str(stage or "").lower())


def _form_upload(form: Any, key: str) -> UploadFile | None:
    value = form.get(key)
    return value if hasattr(value, "filename") else None


def _form_uploads(form: Any, key: str) -> list[UploadFile]:
    values = form.getlist(key) if hasattr(form, "getlist") else [form.get(key)]
    uploads = []
    for value in values:
        if hasattr(value, "filename") and getattr(value, "filename", ""):
            uploads.append(value)
    return uploads


def _form_str(form: Any, key: str, default: str = "") -> str:
    value = form.get(key)
    if value is None:
        return default
    return str(value)


def _form_optional_str(form: Any, key: str) -> str | None:
    value = form.get(key)
    if value in (None, ""):
        return None
    return str(value)


def _form_bool(form: Any, key: str, default: bool = False) -> bool:
    value = form.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _form_int(form: Any, key: str, default: int = 0) -> int:
    try:
        return int(form.get(key, default))
    except (TypeError, ValueError):
        return default


class _StagedUpload:
    def __init__(self, path: Path, filename: str) -> None:
        self.staged_path = path
        self.filename = filename


def _stage_upload_for_background(upload: UploadFile | None) -> _StagedUpload | None:
    if not upload:
        return None
    suffix = Path(upload.filename or "product.jpg").suffix or ".jpg"
    target_dir = config.UPLOAD_DIR / "_generation_run_staging"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(upload.filename or 'product')}_{threading.get_ident()}{suffix}"
    upload.file.seek(0)
    with target.open("wb") as file_obj:
        shutil.copyfileobj(upload.file, file_obj)
    return _StagedUpload(target, upload.filename or target.name)


def _stage_uploads_for_background(uploads: list[UploadFile]) -> list[_StagedUpload]:
    staged = []
    for upload in uploads:
        item = _stage_upload_for_background(upload)
        if item:
            staged.append(item)
    return staged


def _cleanup_staged_upload(upload: Any) -> None:
    if isinstance(upload, (list, tuple)):
        for item in upload:
            _cleanup_staged_upload(item)
        return
    path_value = getattr(upload, "staged_path", None)
    path = Path(path_value) if path_value else None
    if path and path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _generated_idempotency_key(workspace: str) -> str:
    return f"server-{workspace}-{time.time_ns()}"


def _generation_run_form_snapshot(form: Any, staged_upload: Any = None) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key in form.keys():
        if "api_key" in str(key).lower():
            snapshot[key] = bool(_form_str(form, key))
            continue
        value = form.get(key)
        if hasattr(value, "filename"):
            snapshot[key] = {
                "filename": getattr(value, "filename", ""),
                "staged": bool(staged_upload),
            }
        else:
            snapshot[key] = str(value)
    return snapshot


def _generation_kwargs_from_form(
    form: Any,
    *,
    product_image: Any,
    product_static_images: list[Any] | None = None,
    competitor_screenshots: list[Any] | None = None,
    idempotency_key: str,
    existing_generation_run_id: str = "",
) -> dict[str, Any]:
    return {
        "product_image": product_image,
        "product_static_images": product_static_images or [],
        "company_id": _form_str(form, "company_id"),
        "company_data": _form_optional_str(form, "company_data"),
        "ad_vertical": _form_str(form, "ad_vertical"),
        "brand_context": _form_str(form, "brand_context"),
        "product_name": _form_str(form, "product_name"),
        "product_info": _form_str(form, "product_info"),
        "product_category": _form_str(form, "product_category", "auto"),
        "avatar_id": _form_str(form, "avatar_id", "default_creator"),
        "avatar_data": _form_optional_str(form, "avatar_data"),
        "custom_avatar_name": _form_str(form, "custom_avatar_name"),
        "custom_avatar_persona": _form_str(form, "custom_avatar_persona"),
        "custom_avatar_voice": _form_str(form, "custom_avatar_voice"),
        "avatar_wardrobe_policy": _form_str(form, "avatar_wardrobe_policy", "reference_unchanged"),
        "avatar_identity_note": _form_str(form, "avatar_identity_note"),
        "avatar_own_person_consent": _form_bool(form, "avatar_own_person_consent", True),
        "market": _form_str(form, "market", config.DEFAULT_MARKET),
        "language": _form_str(form, "language", config.DEFAULT_LANGUAGE),
        "platform": _form_str(form, "platform", config.DEFAULT_PLATFORM),
        "video_length": _form_int(form, "video_length", config.DEFAULT_VIDEO_LENGTH),
        "testimonial_mode": _form_bool(form, "testimonial_mode", False),
        "testimonial_source": _form_str(form, "testimonial_source"),
        "resolution": _form_str(form, "resolution", "720p"),
        "openrouter_api_key": _form_str(form, "openrouter_api_key"),
        "seedance_model": _form_str(form, "seedance_model", config.OPENROUTER_SEEDANCE_MODEL),
        "prompt_model": _form_str(form, "prompt_model", config.OPENROUTER_PROMPT_MODEL),
        "ugc_scenario_model": _form_str(form, "ugc_scenario_model", config.OPENROUTER_UGC_SCENARIO_MODEL),
        "static_prompt_model": _form_str(form, "static_prompt_model", config.OPENROUTER_STATIC_PROMPT_MODEL),
        "image_model": _form_str(form, "image_model", config.OPENROUTER_IMAGE_MODEL),
        "generation_mode": _form_str(form, "generation_mode", "both"),
        "generate_static_images": _form_bool(form, "generate_static_images", True),
        "max_static_images": _form_int(form, "max_static_images", openrouter_image_client.DEFAULT_MAX_IMAGES),
        "image_size": _form_str(form, "image_size", "1K"),
        "product_reference_url": _form_str(form, "product_reference_url"),
        "avatar_reference_url": _form_str(form, "avatar_reference_url"),
        "landing_page_url": _form_str(form, "landing_page_url"),
        "competitor_strategy_enabled": _form_bool(form, "competitor_strategy_enabled", False),
        "competitor_name": _form_str(form, "competitor_name"),
        "competitor_url": _form_str(form, "competitor_url"),
        "competitor_chat_brief": _form_str(form, "competitor_chat_brief"),
        "competitor_screenshot_notes": _form_str(form, "competitor_screenshot_notes"),
        "competitor_screenshots": competitor_screenshots or [],
        "use_avatar_image_reference": _form_bool(form, "use_avatar_image_reference", False),
        "negative_prompt": _form_str(form, "negative_prompt"),
        "content_prompt_system": _form_str(form, "content_prompt_system"),
        "content_prompt_task": _form_str(form, "content_prompt_task"),
        "base_video_prompt_template": _form_str(form, "base_video_prompt_template"),
        "ugc_video_extra_prompt": _form_str(form, "ugc_video_extra_prompt"),
        "app_mode": _form_str(form, "app_mode", "ecommerce"),
        "finance_video_topic": _form_str(form, "finance_video_topic"),
        "finance_video_script": _form_str(form, "finance_video_script"),
        "finance_disclaimer": _form_str(form, "finance_disclaimer"),
        "finance_allow_series": _form_bool(form, "finance_allow_series", True),
        "finance_series_confirmed": _form_bool(form, "finance_series_confirmed", False),
        "finance_generate_sample_first": _form_bool(form, "finance_generate_sample_first", True),
        "finance_scene_approved": _form_bool(form, "finance_scene_approved", False),
        "finance_scene_reference_url": _form_str(form, "finance_scene_reference_url"),
        "finance_scene_video_reference_url": _form_str(form, "finance_scene_video_reference_url"),
        "finance_scene_prompt": _form_str(form, "finance_scene_prompt"),
        "finance_scene_concept_json": _form_str(form, "finance_scene_concept_json"),
        "background_consistency": _form_str(form, "background_consistency", "strict"),
        "environment_override": _form_bool(form, "environment_override", False),
        "preserve_original_scene_layout": _form_bool(form, "preserve_original_scene_layout", False),
        "category_prompt_handbag": _form_str(form, "category_prompt_handbag"),
        "category_prompt_shoes": _form_str(form, "category_prompt_shoes"),
        "category_prompt_apparel": _form_str(form, "category_prompt_apparel"),
        "idempotency_key": idempotency_key,
        "existing_generation_run_id": existing_generation_run_id,
    }


def _run_generation_background(
    run_id: str,
    kwargs: dict[str, Any],
    staged_upload: Any = None,
    *,
    release_generation_lock: bool = False,
) -> None:
    try:
        generate(**kwargs)
    except Exception as exc:
        generation_run_repository.fail_run(run_id, str(exc))
    finally:
        _cleanup_staged_upload(staged_upload)
        if release_generation_lock:
            _generation_lock.release()


def _run_planning_call_with_watchdog(
    task,
    *,
    fallback,
    timeout_seconds: int,
    label: str,
):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix=label)
    future = executor.submit(task)
    try:
        result = future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        return fallback()
    except Exception:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    executor.shutdown(wait=False, cancel_futures=True)
    return result


def _product_understanding_timeout_fallback(
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    fallback = product_understanding_agent.enrich(
        product_analysis=product_analysis,
        settings=settings,
        api_key="",
        model=model,
    )
    understanding = dict(fallback.get("automatic_product_understanding") or {})
    understanding["source"] = "deterministic_timeout_fallback"
    understanding["status"] = "fallback"
    understanding["ai_refinement"] = {
        "status": "timed_out",
        "reason": f"AI product understanding exceeded {PRODUCT_UNDERSTANDING_TIMEOUT_SECONDS}s; deterministic fallback used.",
        "model": model,
    }
    fallback["automatic_product_understanding"] = understanding
    return fallback


def _visual_classifier_timeout_fallback(model: str) -> dict[str, Any]:
    return {
        "agent": "Visual Product Classifier Agent",
        "status": "skipped",
        "reason": f"Visual product classifier exceeded {VISUAL_PRODUCT_CLASSIFIER_TIMEOUT_SECONDS}s; deterministic planning continued.",
        "model": model,
    }


def _run_brief_intake_phase(
    *,
    run_id: str,
    input_data: dict[str, Any],
    product_image_path: str | Path,
    saved_static_product_image_paths: list[Path],
    company_ctx: dict[str, Any],
    brand_context_text_value: str,
    settings: dict[str, Any],
    openrouter_api_key: str,
    prompt_model: str,
) -> dict[str, Any]:
    generation_run_repository.update_stage(
        run_id,
        "product_intake",
        status="planning",
        data={"message": "Product Intake Agent is parsing product notes and safe facts."},
    )
    product_analysis = product_intake_agent.analyse(input_data, product_image_path)
    if company_ctx:
        product_analysis["company_profile"] = company_ctx
        product_analysis["brand_context"] = brand_context_text_value
        product_analysis["ad_vertical"] = settings["ad_vertical"]
    product_analysis["static_product_reference_paths"] = [str(path) for path in saved_static_product_image_paths]
    product_analysis["static_product_reference_count"] = len(saved_static_product_image_paths)

    generation_run_repository.update_stage(
        run_id,
        "product_understanding",
        status="planning",
        data={
            "message": "Automatic Product Understanding is running with deterministic fallback watchdog.",
            "timeout_seconds": PRODUCT_UNDERSTANDING_TIMEOUT_SECONDS,
        },
    )
    product_analysis = _run_planning_call_with_watchdog(
        lambda: product_understanding_agent.enrich(
            product_analysis=product_analysis,
            settings=settings,
            api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
            model=prompt_model,
        ),
        fallback=lambda: _product_understanding_timeout_fallback(
            product_analysis,
            settings,
            prompt_model,
        ),
        timeout_seconds=PRODUCT_UNDERSTANDING_TIMEOUT_SECONDS,
        label="product_understanding",
    )
    generation_run_repository.update_stage(
        run_id,
        "product_understanding_done",
        status="planning",
        data={
            "message": "Automatic Product Understanding finished.",
            "status": (product_analysis.get("automatic_product_understanding") or {}).get("status"),
            "source": (product_analysis.get("automatic_product_understanding") or {}).get("source"),
        },
    )

    generation_run_repository.update_stage(
        run_id,
        "visual_product_classifier",
        status="planning",
        data={
            "message": "Visual Product Classifier is checking the product image.",
            "timeout_seconds": VISUAL_PRODUCT_CLASSIFIER_TIMEOUT_SECONDS,
        },
    )
    visual_product_understanding = _run_planning_call_with_watchdog(
        lambda: visual_product_classifier_agent.classify(
            product_analysis=product_analysis,
            product_image_path=product_image_path,
            settings=settings,
            api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
            model=config.OPENROUTER_VISION_MODEL,
        ),
        fallback=lambda: _visual_classifier_timeout_fallback(config.OPENROUTER_VISION_MODEL),
        timeout_seconds=VISUAL_PRODUCT_CLASSIFIER_TIMEOUT_SECONDS,
        label="visual_product_classifier",
    )
    generation_run_repository.update_stage(
        run_id,
        "visual_product_classifier_done",
        status="planning",
        data={
            "message": "Visual Product Classifier finished.",
            "status": visual_product_understanding.get("status"),
            "reason": visual_product_understanding.get("reason"),
        },
    )
    return visual_product_classifier_agent.apply_to_product_analysis(
        product_analysis,
        visual_product_understanding,
    )


@app.post("/creative-rating")
def creative_rating(record: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        saved = creative_memory_db.add_rating(record)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    saved["learning_snapshot"] = creative_memory_learning_service.learning_snapshot(
        workspace=(saved.get("learning_signal") or {}).get("workspace") or ""
    )
    return JSONResponse(content=saved)


@app.post("/performance-import")
def performance_import(record: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        saved = creative_memory_db.import_performance(record)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    saved["learning_snapshot"] = creative_memory_learning_service.learning_snapshot(
        workspace=(saved.get("learning_signal") or {}).get("workspace") or ""
    )
    return JSONResponse(content=saved)


@app.post("/performance-import-batch")
def performance_import_batch(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    try:
        saved = creative_memory_db.import_performance_batch(payload)
    except ValueError as exc:
        return JSONResponse(content={"status": "failed", "error": str(exc)}, status_code=400)
    workspace = ""
    for item in saved.get("learning_signals") or saved.get("saved") or []:
        if isinstance(item, dict):
            workspace = item.get("workspace") or workspace
    saved["learning_snapshot"] = creative_memory_learning_service.learning_snapshot(workspace=workspace)
    return JSONResponse(content=saved)


@app.get("/latest-output")
def latest_output() -> JSONResponse:
    latest = _latest_output_json(config.OUTPUT_DIR)
    if not latest:
        return JSONResponse(content={"error": "No saved output is available."}, status_code=404)
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as exc:
        return JSONResponse(
            content={"error": f"Could not read latest output: {exc}"},
            status_code=500,
        )
    payload["_recovered_from_latest_output"] = True
    return JSONResponse(content=payload)


@app.post("/generate")
def generate(
    product_image: UploadFile | None = File(None),
    product_static_images: list[UploadFile] | None = File(None),
    company_id: str = Form(""),
    company_data: str | None = Form(None),
    ad_vertical: str = Form(""),
    brand_context: str = Form(""),
    product_name: str = Form(""),
    product_info: str = Form(""),
    product_category: str = Form("auto"),
    avatar_id: str = Form("default_creator"),
    avatar_data: str | None = Form(None),
    custom_avatar_name: str = Form(""),
    custom_avatar_persona: str = Form(""),
    custom_avatar_voice: str = Form(""),
    avatar_wardrobe_policy: str = Form("reference_unchanged"),
    avatar_identity_note: str = Form(""),
    avatar_own_person_consent: bool = Form(True),
    market: str = Form(config.DEFAULT_MARKET),
    language: str = Form(config.DEFAULT_LANGUAGE),
    platform: str = Form(config.DEFAULT_PLATFORM),
    video_length: int = Form(config.DEFAULT_VIDEO_LENGTH),
    testimonial_mode: bool = Form(False),
    testimonial_source: str = Form(""),
    resolution: str = Form("720p"),
    openrouter_api_key: str = Form(""),
    seedance_model: str = Form(config.OPENROUTER_SEEDANCE_MODEL),
    prompt_model: str = Form(config.OPENROUTER_PROMPT_MODEL),
    ugc_scenario_model: str = Form(config.OPENROUTER_UGC_SCENARIO_MODEL),
    static_prompt_model: str = Form(config.OPENROUTER_STATIC_PROMPT_MODEL),
    image_model: str = Form(config.OPENROUTER_IMAGE_MODEL),
    generation_mode: str = Form("both"),
    generate_static_images: bool = Form(True),
    max_static_images: int = Form(openrouter_image_client.DEFAULT_MAX_IMAGES),
    image_size: str = Form("1K"),
    product_reference_url: str = Form(""),
    avatar_reference_url: str = Form(""),
    landing_page_url: str = Form(""),
    competitor_strategy_enabled: bool = Form(False),
    competitor_name: str = Form(""),
    competitor_url: str = Form(""),
    competitor_chat_brief: str = Form(""),
    competitor_screenshot_notes: str = Form(""),
    competitor_screenshots: list[UploadFile] | None = File(None),
    use_avatar_image_reference: bool = Form(False),
    negative_prompt: str = Form(""),
    content_prompt_system: str = Form(""),
    content_prompt_task: str = Form(""),
    base_video_prompt_template: str = Form(""),
    ugc_video_extra_prompt: str = Form(""),
    app_mode: str = Form("ecommerce"),
    finance_video_topic: str = Form(""),
    finance_video_script: str = Form(""),
    finance_disclaimer: str = Form(""),
    finance_allow_series: bool = Form(True),
    finance_series_confirmed: bool = Form(False),
    finance_generate_sample_first: bool = Form(True),
    finance_scene_approved: bool = Form(False),
    finance_scene_reference_url: str = Form(""),
    finance_scene_video_reference_url: str = Form(""),
    finance_scene_prompt: str = Form(""),
    finance_scene_concept_json: str = Form(""),
    background_consistency: str = Form("strict"),
    environment_override: bool = Form(False),
    preserve_original_scene_layout: bool = Form(False),
    category_prompt_handbag: str = Form(""),
    category_prompt_shoes: str = Form(""),
    category_prompt_apparel: str = Form(""),
    idempotency_key: str = Form(""),
    existing_generation_run_id: str = "",
) -> JSONResponse:
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    finance_mode = app_mode.strip() == "finance_personal_brand"
    workspace = "finance" if finance_mode else "ecommerce"
    ugc_scenario_model = ugc_scenario_model.strip() or config.OPENROUTER_UGC_SCENARIO_MODEL
    static_prompt_model = static_prompt_model.strip() or config.OPENROUTER_STATIC_PROMPT_MODEL
    company_profile = load_company(company_id, company_data)
    company_ctx = company_context(company_profile)
    brand_context_text_value = brand_context.strip() or company_context_text(company_profile)
    if company_profile:
        ad_vertical = ad_vertical.strip() or str(company_profile.get("ad_vertical") or "")
        if not market.strip() or market == config.DEFAULT_MARKET:
            market = str(company_profile.get("market") or market)
        if not language.strip() or language == config.DEFAULT_LANGUAGE:
            language = str(company_profile.get("language") or language)
        if not platform.strip() or platform == config.DEFAULT_PLATFORM:
            platform = str(company_profile.get("default_platform") or platform)
        default_company_avatar = str(company_profile.get("default_avatar_id") or "").strip()
        if default_company_avatar and avatar_id in {"", "default_creator", "avatar1"}:
            avatar_id = default_company_avatar
    if not existing_generation_run_id:
        active_run = generation_run_repository.active_run(workspace=workspace)
        if active_run:
            return JSONResponse(
                content={
                    "status": "blocked",
                    "reason": "A matching active generation run already exists in the same workspace.",
                    "active_run_id": active_run.get("run_id"),
                    "workspace": workspace,
                    "next_step": "Cancel the active run or wait until it completes before starting another generation.",
                },
                status_code=409,
            )
    if finance_mode:
        normalized = finance_video_agent.normalize_settings(
            product_name=product_name,
            product_info=product_info,
            product_category=product_category,
            language=language,
            generation_mode=generation_mode,
            generate_static_images=generate_static_images,
            finance_video_topic=finance_video_topic,
            finance_video_script=finance_video_script,
            finance_disclaimer=finance_disclaimer,
        )
        product_name = normalized["product_name"]
        product_info = normalized["product_info"]
        product_category = normalized["product_category"]
        language = normalized["language"]
        generation_mode = normalized["generation_mode"]
        generate_static_images = normalized["generate_static_images"]
        finance_video_topic = normalized["finance_video_topic"]
        finance_video_script = normalized["finance_video_script"]
        finance_disclaimer = normalized["finance_disclaimer"]
        video_length = finance_video_agent.DEFAULT_SERIES_SECONDS
        if platform not in {"meta", "instagram"}:
            platform = "meta"
        finance_script_plan = finance_video_agent.prepare_script_plan(
            topic=finance_video_topic,
            user_script=finance_video_script,
            disclaimer=finance_disclaimer,
            platform=platform,
            api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
            model=prompt_model,
        )
        prepared_finance_script = finance_script_plan.get("canonical_script") or finance_video_script
        finance_series_plan = finance_video_agent.plan_video_series(
            topic=finance_video_topic,
            script=prepared_finance_script,
            script_plan=finance_script_plan,
            allow_series=finance_allow_series,
            confirmed=finance_series_confirmed,
            target_seconds=finance_video_agent.DEFAULT_SERIES_SECONDS,
        )
        if finance_series_plan.get("needs_confirmation"):
            pending_run = _get_or_create_generation_run(
                existing_generation_run_id=existing_generation_run_id,
                workspace="finance",
                app_mode="finance_personal_brand",
                input_snapshot={
                    "app_mode": "finance_personal_brand",
                    "platform": platform,
                    "language": "cs",
                    "generation_mode": "video",
                    "finance_video_topic": finance_video_topic,
                    "finance_allow_series": finance_allow_series,
                    "finance_generate_sample_first": finance_generate_sample_first,
                    "reason": "series_confirmation_required",
                },
                idempotency_key=idempotency_key,
            )
            generation_run_repository.update_stage(
                pending_run["run_id"],
                "needs_confirmation",
                status="needs_confirmation",
                data={"finance_video_series": finance_series_plan},
            )
            return JSONResponse(
                content={
                    "final_export_status": "needs_confirmation",
                    "status": "needs_confirmation",
                    "reason": "Finance script is too long for one 15s video.",
                    "next_step": "Confirm generation of the first sample video before the app calls any model.",
                    "finance_script_agent": finance_script_plan,
                    "finance_video_series": finance_series_plan,
                    "user_input": {
                        "app_mode": "finance_personal_brand",
                        "platform": platform,
                        "language": "cs",
                        "generation_mode": "video",
                        "finance_video_topic": finance_video_topic,
                        "finance_allow_series": finance_allow_series,
                        "finance_generate_sample_first": finance_generate_sample_first,
                    },
                    "generation_run": generation_run_repository.get_run(pending_run["run_id"]),
                }
            )
        if not finance_scene_approved:
            pending_run = _get_or_create_generation_run(
                existing_generation_run_id=existing_generation_run_id,
                workspace="finance",
                app_mode="finance_personal_brand",
                input_snapshot={
                    "app_mode": "finance_personal_brand",
                    "platform": platform,
                    "language": "cs",
                    "generation_mode": "video",
                    "finance_video_topic": finance_video_topic,
                    "finance_scene_approved": False,
                    "reason": "scene_approval_required",
                },
                idempotency_key=idempotency_key,
            )
            generation_run_repository.update_stage(
                pending_run["run_id"],
                "needs_scene_approval",
                status="needs_scene_approval",
                data={"finance_script_agent": finance_script_plan},
            )
            return JSONResponse(
                content={
                    "final_export_status": "needs_scene_approval",
                    "status": "needs_scene_approval",
                    "reason": "Finance scene concept must be prepared and approved before video generation.",
                    "next_step": "Klikni na 'Připravit scénář a scénu', schval návrh a potom spusť video.",
                    "finance_script_agent": finance_script_plan,
                    "user_input": {
                        "app_mode": "finance_personal_brand",
                        "platform": platform,
                        "language": "cs",
                        "generation_mode": "video",
                        "finance_video_topic": finance_video_topic,
                        "finance_scene_approved": False,
                    },
                    "generation_run": generation_run_repository.get_run(pending_run["run_id"]),
                }
            )
        finance_scene_concept = _approved_finance_scene_concept(
            topic=finance_video_topic,
            script_plan=finance_script_plan,
            avatar=load_avatar(avatar_id, avatar_data),
            platform=platform,
            approved_prompt=finance_scene_prompt,
            concept_json=finance_scene_concept_json,
        )
    else:
        finance_series_plan = {}
        finance_script_plan = {}
        finance_scene_concept = {}
        prepared_finance_script = finance_video_script
    generation_mode = _normalize_generation_mode(generation_mode)
    should_generate_video = generation_mode in {"both", "video"}
    should_generate_static_images = (
        (not finance_mode)
        and bool(generate_static_images)
        and generation_mode in {"both", "static"}
        and max_static_images > 0
    )
    product_reference = normalize_public_image_url(product_reference_url.strip())
    avatar_reference = normalize_public_image_url(avatar_reference_url.strip())
    static_product_uploads = product_static_images or []
    if not finance_mode and not product_image and not static_product_uploads and not product_reference:
        return JSONResponse(
            content={"error": "Upload a product image or provide a public HTTPS product reference URL."},
            status_code=400,
        )
    session_label = finance_video_topic if finance_mode else product_name
    session_output_dir = _create_session_output_dir(
        session_label,
        config.OUTPUT_DIR,
        app_mode="finance_personal_brand" if finance_mode else "ecommerce",
        session_prefix="FIN_BRAND" if finance_mode else "ADS_ST",
    )
    input_asset_dir = session_output_dir / "inputs"
    saved_product_image_path = _save_upload(product_image, input_asset_dir, product_name) if product_image else None
    saved_static_product_image_paths = _save_product_static_images(
        uploads=static_product_uploads,
        upload_dir=input_asset_dir / "static_product_variants",
        product_name=product_name,
    )
    competitor_screenshot_assets = _save_competitor_screenshots(
        uploads=competitor_screenshots or [],
        upload_dir=input_asset_dir / "competitor",
        competitor_name=competitor_name or "competitor",
    )
    product_image_path = (
        product_reference
        or saved_product_image_path
        or (saved_static_product_image_paths[0] if saved_static_product_image_paths else None)
        or "finance_personal_brand_no_product_reference"
    )
    avatar = load_avatar(avatar_id, avatar_data)
    avatar = _apply_custom_avatar_profile(
        avatar=avatar,
        custom_avatar_name=custom_avatar_name,
        custom_avatar_persona=custom_avatar_persona,
        custom_avatar_voice=custom_avatar_voice,
        avatar_wardrobe_policy=avatar_wardrobe_policy,
        avatar_identity_note=avatar_identity_note,
        avatar_own_person_consent=avatar_own_person_consent,
    )
    if avatar_reference:
        avatar["image_url"] = avatar_reference
    input_data = {
        "company_id": company_ctx.get("company_id") or company_id,
        "company_profile": company_ctx,
        "brand_context": brand_context_text_value,
        "ad_vertical": ad_vertical.strip() or company_ctx.get("ad_vertical") or ("finance" if finance_mode else "ads"),
        "product_name": product_name,
        "product_info": product_info,
        "product_category": product_category,
        "avatar_id": avatar_id,
        "custom_avatar_name_provided": bool(custom_avatar_name.strip()),
        "custom_avatar_persona_provided": bool(custom_avatar_persona.strip()),
        "custom_avatar_voice_provided": bool(custom_avatar_voice.strip()),
        "avatar_wardrobe_policy": avatar.get("wardrobe_policy"),
        "avatar_identity_note_provided": bool(avatar_identity_note.strip()),
        "avatar_own_person_consent": avatar_own_person_consent,
        "market": market,
        "language": language,
        "platform": platform,
        "video_length": video_length,
        "product_category": product_category,
        "testimonial_mode": testimonial_mode,
        "testimonial_source": testimonial_source,
        "resolution": resolution,
        "product_image_path": str(product_image_path),
        "static_product_reference_paths": [str(path) for path in saved_static_product_image_paths],
        "openrouter_api_key_provided": bool(openrouter_api_key),
        "seedance_model": seedance_model,
        "image_model": image_model,
        "prompt_model": prompt_model,
        "ugc_scenario_model": ugc_scenario_model if not finance_mode else "",
        "static_prompt_model": static_prompt_model if not finance_mode else "",
        "app_mode": "finance_personal_brand" if finance_mode else "ecommerce",
        "finance_video_topic": finance_video_topic if finance_mode else "",
        "finance_video_script_provided": bool(finance_video_script.strip()) if finance_mode else False,
        "finance_prepared_script_provided": bool(prepared_finance_script.strip()) if finance_mode else False,
        "finance_disclaimer": finance_disclaimer if finance_mode else "",
        "finance_allow_series": finance_allow_series if finance_mode else False,
        "finance_series_confirmed": finance_series_confirmed if finance_mode else False,
        "finance_generate_sample_first": finance_generate_sample_first if finance_mode else False,
        "finance_scene_approved": finance_scene_approved if finance_mode else False,
        "finance_scene_reference_url": finance_scene_reference_url.strip() if finance_mode else "",
        "finance_scene_video_reference_url": finance_scene_video_reference_url.strip() if finance_mode else "",
        "finance_scene_concept_provided": bool(finance_scene_concept_json.strip()) if finance_mode else False,
        "finance_video_series": finance_series_plan if finance_mode else {},
        "finance_script_agent": finance_script_plan if finance_mode else {},
        "generation_mode": generation_mode,
        "generate_video": should_generate_video,
        "generate_static_images": should_generate_static_images,
        "max_static_images": max_static_images,
        "image_size": image_size,
        "prompt_generation_mode": "automatic_openrouter_with_deterministic_fallback",
        "prompt_model": prompt_model,
        "ugc_scenario_model": ugc_scenario_model if not finance_mode else "",
        "static_prompt_model": static_prompt_model if not finance_mode else "",
        "idempotency_key_provided": bool(idempotency_key.strip()),
        "session_type": "FIN_BRAND" if finance_mode else "ADS_ST",
        "session_output_dir": str(session_output_dir),
        "session_folder_name": session_output_dir.name,
        "session_workspace": "finance" if finance_mode else "ecommerce",
        "product_reference_url_provided": bool(product_reference),
        "static_product_reference_count": len(saved_static_product_image_paths),
        "cta_link_policy": "Destination URL is not written into ad copy; configure it inside the selected ad platform.",
        "competitor_strategy_enabled": bool(competitor_strategy_enabled) if not finance_mode else False,
        "competitor_name": competitor_name.strip()[:120] if not finance_mode else "",
        "competitor_url": competitor_url.strip()[:300] if not finance_mode else "",
        "competitor_chat_brief_provided": bool(competitor_chat_brief.strip()) if not finance_mode else False,
        "competitor_screenshot_notes_provided": bool(competitor_screenshot_notes.strip()) if not finance_mode else False,
        "competitor_screenshot_count": len(competitor_screenshot_assets) if not finance_mode else 0,
        "competitor_screenshot_assets": competitor_screenshot_assets if not finance_mode else [],
        "avatar_reference_url_provided": bool(avatar_reference or avatar.get("image_url")),
        "use_avatar_image_reference": use_avatar_image_reference,
        "ugc_video_extra_prompt": ugc_video_extra_prompt.strip()[:1200],
        "ugc_video_extra_prompt_provided": bool(ugc_video_extra_prompt.strip()),
        "background_consistency": background_consistency,
        "environment_override": environment_override,
        "preserve_original_scene_layout": preserve_original_scene_layout,
        "prompt_overrides": {
            "negative_prompt": bool(negative_prompt.strip()),
            "content_prompt_system": bool(content_prompt_system.strip()),
            "content_prompt_task": bool(content_prompt_task.strip()),
            "base_video_prompt_template": bool(base_video_prompt_template.strip()),
            "ugc_video_extra_prompt": bool(ugc_video_extra_prompt.strip()),
            "background_consistency": background_consistency != "strict",
            "environment_override": environment_override,
            "preserve_original_scene_layout": not preserve_original_scene_layout,
            "category_prompt_handbag": bool(category_prompt_handbag.strip()),
            "category_prompt_shoes": bool(category_prompt_shoes.strip()),
            "category_prompt_apparel": bool(category_prompt_apparel.strip()),
            "competitor_strategy": bool(competitor_strategy_enabled and not finance_mode),
            "finance_personal_brand_mode": finance_mode,
        },
    }
    generation_run = _get_or_create_generation_run(
        existing_generation_run_id=existing_generation_run_id,
        workspace=input_data["session_workspace"],
        app_mode=input_data["app_mode"],
        input_snapshot=input_data,
        idempotency_key=idempotency_key,
        output_dir=str(session_output_dir),
    )
    run_id = generation_run["run_id"]
    if generation_run.get("idempotency_reused"):
        return JSONResponse(
            content={
                "status": "blocked",
                "error": "Generation with this idempotency key is already running.",
                "reason": "A matching active generation run already exists, so duplicate provider calls were not started.",
                "generation_run": generation_run,
            },
            status_code=409,
        )
    input_data["generation_run_id"] = run_id
    generation_run_repository.update_stage(
        run_id,
        "validating",
        status="validating",
        data={"message": "Provider and input validation started."},
    )
    input_references = _build_input_references(
        product_image_path=product_image_path,
        avatar=avatar,
        product_reference_url=product_reference,
        avatar_reference_url=avatar_reference,
        use_avatar_image_reference=use_avatar_image_reference,
    )
    finance_scene_reference_for_video = (
        finance_scene_video_reference_url.strip() or finance_scene_reference_url.strip()
        if finance_mode and finance_scene_approved
        else ""
    )
    if _is_public_http_url(finance_scene_reference_for_video):
        scene_ref = image_url_reference(finance_scene_reference_for_video)
        if scene_ref:
            input_references.insert(0, scene_ref)
    finance_scene_frame_images = []
    if finance_mode and finance_scene_approved and _is_public_http_url(finance_scene_reference_for_video):
        frame_ref = image_url_reference(finance_scene_reference_for_video)
        if frame_ref:
            finance_scene_frame_images = [frame_ref]
    finance_scene_addendum = ""
    if finance_mode and finance_scene_approved:
        finance_scene_addendum = (
            "Approved scene concept workflow: use the approved modern podcast-studio scene concept as a locked layout and infographic blueprint "
            "for camera, lighting, Czech infographic placement, exact label language, and gesture timing. Do not replace the approved infographic system with generic dashboard graphics. "
        )
        compiled_scene_lock = str(finance_scene_concept.get("video_prompt_addendum_compiled") or "")
        if compiled_scene_lock:
            finance_scene_addendum += compiled_scene_lock[:1600]
        elif finance_scene_prompt.strip():
            finance_scene_addendum += f"Approved scene prompt: {finance_scene_prompt.strip()[:1600]}"
    settings = {
        "company_id": company_ctx.get("company_id") or company_id,
        "company_profile": company_ctx,
        "brand_context": brand_context_text_value,
        "ad_vertical": ad_vertical.strip() or company_ctx.get("ad_vertical") or ("finance" if finance_mode else "ads"),
        "market": market,
        "language": language,
        "platform": platform,
        "video_length": video_length,
        "testimonial_mode": testimonial_mode,
        "testimonial_source": testimonial_source,
        "resolution": resolution,
        "seedance_model": seedance_model,
        "image_model": image_model,
        "app_mode": "finance_personal_brand" if finance_mode else "ecommerce",
        "finance_video_topic": finance_video_topic,
        "finance_video_script": prepared_finance_script if finance_mode else finance_video_script,
        "finance_raw_video_script": finance_video_script,
        "finance_script_agent": finance_script_plan if finance_mode else {},
        "finance_disclaimer": finance_disclaimer,
        "finance_allow_series": finance_allow_series,
        "finance_series_confirmed": finance_series_confirmed,
        "finance_generate_sample_first": finance_generate_sample_first,
        "finance_scene_approved": finance_scene_approved,
        "finance_scene_reference_url": finance_scene_reference_url.strip(),
        "finance_scene_video_reference_url": finance_scene_video_reference_url.strip(),
        "finance_scene_prompt": finance_scene_prompt.strip()[:1800],
        "finance_scene_concept": finance_scene_concept if finance_mode else {},
        "finance_video_series": finance_series_plan if finance_mode else {},
        "generation_mode": generation_mode,
        "generate_video": should_generate_video,
        "generate_static_images": should_generate_static_images,
        "max_static_images": max_static_images,
        "image_size": image_size,
        "input_references": input_references,
        "frame_images": finance_scene_frame_images,
        "product_reference_url": product_reference,
        "cta_link_policy": "selected_platform_destination_url",
        "competitor_strategy_enabled": bool(competitor_strategy_enabled) if not finance_mode else False,
        "competitor_name": competitor_name.strip()[:120] if not finance_mode else "",
        "competitor_url": competitor_url.strip()[:300] if not finance_mode else "",
        "competitor_chat_brief": competitor_chat_brief.strip()[:6000] if not finance_mode else "",
        "competitor_screenshot_notes": competitor_screenshot_notes.strip()[:2200] if not finance_mode else "",
        "competitor_screenshot_assets": competitor_screenshot_assets if not finance_mode else [],
        "use_avatar_image_reference": use_avatar_image_reference,
        "avatar_wardrobe_policy": avatar.get("wardrobe_policy"),
        "avatar_own_person_consent": avatar_own_person_consent,
        "negative_prompt": negative_prompt.strip(),
        "base_video_prompt_template": base_video_prompt_template.strip(),
        "ugc_video_extra_prompt": (f"{finance_scene_addendum} {ugc_video_extra_prompt.strip()}").strip()[:3500],
        "background_consistency": background_consistency,
        "environment_override": environment_override,
        "preserve_original_scene_layout": preserve_original_scene_layout,
        "category_prompt_overrides": {
            key: value
            for key, value in {
                "handbag": category_prompt_handbag.strip(),
                "shoes": category_prompt_shoes.strip(),
                "apparel": category_prompt_apparel.strip(),
            }.items()
            if value
        },
    }
    early_provider_validation = preflight_validator.validate(
        generation_mode=generation_mode,
        should_generate_video=should_generate_video,
        should_generate_static_images=should_generate_static_images,
        product_reference_url=product_reference,
        avatar_reference_url=avatar_reference or str(avatar.get("image_url") or ""),
        use_avatar_image_reference=use_avatar_image_reference,
        seedance_model=seedance_model,
        image_model=image_model,
        max_static_images=max_static_images,
        image_size=image_size,
        require_product_reference_for_video=not finance_mode,
    )
    if early_provider_validation.get("status") == "blocked":
        final_output = _early_provider_block_output(
            input_data=input_data,
            avatar=avatar,
            provider_validation=early_provider_validation,
            session_output_dir=session_output_dir,
        )
        final_output["generation_run"] = generation_run_repository.complete_run(run_id, final_output, status="blocked")
        output_writer.save(final_output, output_dir=session_output_dir)
        return JSONResponse(content=final_output)

    generation_run_repository.attach_audit(run_id, provider_validation=early_provider_validation)
    generation_run_repository.update_stage(
        run_id,
        "planning",
        status="planning",
        data={"message": "Product understanding and creative brain started."},
    )
    product_analysis = _run_brief_intake_phase(
        run_id=run_id,
        input_data=input_data,
        product_image_path=product_image_path,
        saved_static_product_image_paths=saved_static_product_image_paths,
        company_ctx=company_ctx,
        brand_context_text_value=brand_context_text_value,
        settings=settings,
        openrouter_api_key=openrouter_api_key,
        prompt_model=prompt_model,
    )
    competitor_strategy = competitor_strategy_agent.analyze(
        enabled=bool(competitor_strategy_enabled) and not finance_mode,
        competitor_name=competitor_name,
        competitor_url=competitor_url,
        competitor_chat_brief=competitor_chat_brief,
        competitor_screenshot_notes=competitor_screenshot_notes,
        screenshot_assets=competitor_screenshot_assets,
        product_analysis=product_analysis,
        settings=settings,
    )
    competitor_strategy_runtime = {
        key: value
        for key, value in competitor_strategy.items()
        if key not in {"system_prompt"}
    }
    settings["competitor_strategy"] = competitor_strategy_runtime
    settings["competitor_strategy_system_prompt"] = competitor_strategy_agent.SYSTEM_PROMPT
    input_data["competitor_strategy"] = competitor_strategy_runtime
    input_data["competitor_strategy_system_prompt"] = (
        competitor_strategy_agent.SYSTEM_PROMPT if competitor_strategy_runtime.get("status") == "ready" else ""
    )
    performance_insights = performance_memory.select_insights(product_analysis, settings)
    creative_memory_guidance = creative_memory_db.retrieve_guidance(
        product_analysis=product_analysis,
        settings=settings,
    )
    performance_insights["creative_memory_rag"] = creative_memory_guidance
    performance_insights["winning_hooks"] = _merge_unique(
        performance_insights.get("winning_hooks") or [],
        creative_memory_guidance.get("winning_patterns") or [],
    )
    performance_insights["avoid_patterns"] = creative_memory_guidance.get("avoid_patterns") or []
    audience_research = audience_research_agent.generate(
        product_analysis=product_analysis,
        settings=settings,
        performance_insights=performance_insights,
    )
    emotional_angle = emotional_angle_engine.generate(
        product_analysis=product_analysis,
        audience_research=audience_research,
        performance_insights=performance_insights,
        settings=settings,
    )
    creative_psychology = creative_psychology_agent.generate(
        product_analysis=product_analysis,
        audience_research=audience_research,
        performance_insights=performance_insights,
        emotional_angle=emotional_angle,
    )
    voice_personality = voice_personality_engine.generate(
        avatar=avatar,
        product_analysis=product_analysis,
        audience_research=audience_research,
        emotional_angle=emotional_angle,
        settings=settings,
    )
    ugc_hook_strategy = ugc_hook_agent.generate(
        product_analysis=product_analysis,
        audience_research=audience_research,
        creative_psychology=creative_psychology,
        performance_insights=performance_insights,
        language=language,
    )
    scene_direction = scene_director_agent.generate(
        product_analysis=product_analysis,
        audience_research=audience_research,
        creative_psychology=creative_psychology,
        performance_insights=performance_insights,
        language=language,
    )
    scene_chaining = scene_chaining_agent.generate(
        product_analysis=product_analysis,
        avatar=avatar,
        settings=settings,
        scene_direction=scene_direction,
        voice_personality=voice_personality,
    )
    settings.update(
        {
            "performance_insights": performance_insights,
            "creative_memory_guidance": creative_memory_guidance,
            "audience_research": audience_research,
            "emotional_angle": emotional_angle,
            "creative_psychology": creative_psychology,
            "voice_personality": voice_personality,
            "ugc_hook_strategy": ugc_hook_strategy,
            "scene_direction": scene_direction,
            "scene_chaining": scene_chaining,
        }
    )
    ugc_strategy = ugc_agent.generate_strategy(
        product_analysis=product_analysis,
        avatar=avatar,
        settings=settings,
    )
    if not finance_mode:
        ugc_strategy["competitor_strategy"] = competitor_strategy_runtime
    if finance_mode:
        ugc_strategy = finance_video_agent.generate_strategy(
            product_analysis=product_analysis,
            avatar=avatar,
            settings=settings,
        )
        scene_chaining = scene_chaining_agent.generate(
            product_analysis=product_analysis,
            avatar=avatar,
            settings=settings,
            scene_direction=ugc_strategy.get("scene_direction") or {},
            voice_personality=ugc_strategy.get("voice_personality") or voice_personality,
        )
        settings["scene_chaining"] = scene_chaining
        ugc_strategy["scene_chaining"] = scene_chaining
    if not finance_mode:
        angle_multiplier = ad_angle_multiplier.generate(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            settings=settings,
        )
        angle_selector = ad_angle_selector.select(
            angle_multiplier=angle_multiplier,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            settings=settings,
        )
        settings["ad_angle_multiplier"] = angle_multiplier
        settings["ad_angle_selector"] = angle_selector
        ugc_strategy["ad_angle_multiplier"] = angle_multiplier
        ugc_strategy["ad_angle_selector"] = angle_selector
    ugc_strategy["creative_memory_rag"] = creative_memory_guidance
    content_prompt_package = content_prompt_engineer_agent.generate_prompt_package(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        avatar=avatar,
        product_image_path=str(product_image_path),
        settings=settings,
    )
    generation_run_repository.update_stage(
        run_id,
        "prompting",
        status="prompting",
        data={"message": "Content prompt package created; optional AI refinement follows."},
    )
    deterministic_content_prompt_package = deepcopy(content_prompt_package)
    if finance_mode:
        content_prompt_package["prompt_generation"] = {
            "status": "finance_mode_deterministic",
            "reason": "Finance personal brand mode uses a dedicated compliant video prompt compiler.",
            "model": prompt_model,
        }
    else:
        content_prompt_package = openrouter_prompt_client.enhance_prompt_package(
            content_prompt_package=content_prompt_package,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            avatar=avatar,
            api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
            model=ugc_scenario_model,
            system_prompt=content_prompt_system.strip() or None,
            task_prompt=content_prompt_task.strip() or None,
        )
    content_prompt_package = structured_prompt_v2.apply_to_prompt_package(
        content_prompt_package=content_prompt_package,
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        settings=settings,
    )
    content_prompt_package["creative_memory_guidance"] = creative_memory_guidance
    content_prompt_package["prompt_graph"] = prompt_graph_service.build_prompt_graph(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        settings=settings,
    )
    product_fidelity_result = product_fidelity_guard.check(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
    )
    compliance_result = compliance_guard.check(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
    )
    quality_result = quality_scorer.score(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        product_fidelity_result=product_fidelity_result,
        compliance_result=compliance_result,
    )

    if quality_result.get("should_improve_once"):
        content_prompt_package = content_prompt_engineer_agent.improve_prompt_package(
            content_prompt_package, quality_result
        )
        content_prompt_package = structured_prompt_v2.apply_to_prompt_package(
            content_prompt_package=content_prompt_package,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            settings=settings,
        )
        product_fidelity_result = product_fidelity_guard.check(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            content_prompt_package=content_prompt_package,
        )
        compliance_result = compliance_guard.check(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            content_prompt_package=content_prompt_package,
        )
        quality_result = quality_scorer.score(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            content_prompt_package=content_prompt_package,
            product_fidelity_result=product_fidelity_result,
            compliance_result=compliance_result,
        )

    content_prompt_package["creative_memory_guidance"] = creative_memory_guidance
    content_prompt_package["prompt_graph"] = prompt_graph_service.build_prompt_graph(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        settings=settings,
    )
    generation_run_repository.update_stage(
        run_id,
        "creative_plan",
        status="planning",
        data={"message": "Prompt graph ready; building C1-C5 creative set."},
    )
    ads_creative_set = ads_creative_set_agent.generate_ad_set(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        avatar=avatar,
        settings=settings,
    )
    if finance_mode:
        ads_creative_set = finance_video_agent.generate_video_only_ad_set(
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            content_prompt_package=content_prompt_package,
            avatar=avatar,
            settings=settings,
        )
    deterministic_ads_creative_set = deepcopy(ads_creative_set)
    if not finance_mode:
        ads_creative_set = openrouter_prompt_client.enhance_ads_creative_set(
            ads_creative_set=ads_creative_set,
            product_analysis=product_analysis,
            ugc_strategy=ugc_strategy,
            api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
            model=static_prompt_model,
        )
        ads_creative_set = ads_creative_set_agent.refresh_copy_validation(ads_creative_set)
    final_export_status = quality_result["export_status"]
    prompt_api_key_available = bool(openrouter_api_key or config.OPENROUTER_API_KEY)
    static_prompt_generation = ads_creative_set.get("static_prompt_generation") or {}
    provider_validation = preflight_validator.validate(
        generation_mode=generation_mode,
        should_generate_video=should_generate_video,
        should_generate_static_images=should_generate_static_images,
        product_reference_url=product_reference,
        avatar_reference_url=avatar_reference or str(avatar.get("image_url") or ""),
        use_avatar_image_reference=use_avatar_image_reference,
        seedance_model=seedance_model,
        image_model=image_model,
        max_static_images=max_static_images,
        image_size=image_size,
        require_product_reference_for_video=not finance_mode,
        content_prompt_package=content_prompt_package,
        ads_creative_set=ads_creative_set,
    )
    scenario_integrity_result = scenario_integrity_guard.check(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        avatar=avatar,
        ads_creative_set=ads_creative_set,
    )
    provider_validation = _provider_validation_with_scenario_integrity(
        provider_validation,
        scenario_integrity_result,
    )
    generation_run_repository.attach_audit(run_id, provider_validation=provider_validation)
    if provider_validation.get("status") == "blocked":
        final_export_status = "blocked"
    if generation_run_repository.is_cancel_requested(run_id):
        final_export_status = "cancelled"
        static_image_generation = {
            "image_generation_status": "cancelled",
            "error": "Generation cancelled before static image provider calls.",
            "failure_reason": "User requested cancellation.",
            "next_step": "Start a new run when you are ready.",
            "model": image_model,
            "image_assets": [],
            "attempted_count": 0,
            "output_dir": str(session_output_dir),
            "generation_mode": generation_mode,
        }
        video_generation = {
            "video_generation_status": "cancelled",
            "error": "Generation cancelled before Seedance provider call.",
            "failure_reason": "User requested cancellation.",
            "next_step": "Start a new run when you are ready.",
            "video_path": None,
            "job_id": None,
            "output_dir": str(session_output_dir),
            "generation_mode": generation_mode,
        }
        generation_run_repository.update_stage(
            run_id,
            "cancelled",
            status="cancelled",
            data={"reason": "Cancellation was requested before provider generation."},
        )
    elif final_export_status == "blocked":
        blocked_reason = _blocked_reason(product_fidelity_result, compliance_result, quality_result)
        if provider_validation.get("status") == "blocked":
            blocked_reason = provider_validation.get("reason") or blocked_reason
        if should_generate_static_images:
            static_image_generation = {
                "image_generation_status": "blocked",
                "error": "Static image generation blocked before API call.",
                "failure_reason": blocked_reason,
                "next_step": _blocked_next_step(provider_validation)
                or "Review Product Fidelity, Compliance, and Provider Validation results, then adjust settings.",
                "model": image_model,
                "image_assets": [],
                "attempted_count": 0,
                "output_dir": str(session_output_dir),
                "generation_mode": generation_mode,
                "static_prompt_generation": ads_creative_set.get("static_prompt_generation"),
                "provider_validation": provider_validation,
            }
        else:
            static_image_generation = _static_generation_skipped_by_mode(
                ads_creative_set=ads_creative_set,
                image_model=image_model,
                session_output_dir=session_output_dir,
                generation_mode=generation_mode,
            )
        if should_generate_video:
            video_generation = {
                "video_generation_status": "blocked",
                "error": "Video generation blocked before API call.",
                "failure_reason": blocked_reason,
                "next_step": _blocked_next_step(provider_validation)
                or "Review Product Fidelity, Compliance, and Provider Validation results, then adjust settings.",
                "video_path": None,
                "job_id": None,
                "output_dir": str(session_output_dir),
                "generation_mode": generation_mode,
                "provider_validation": provider_validation,
            }
        else:
            video_generation = _video_generation_skipped_by_mode(
                content_prompt_package=content_prompt_package,
                session_output_dir=session_output_dir,
                generation_mode=generation_mode,
            )
    else:
        if should_generate_video:
            generation_run_repository.update_stage(
                run_id,
                "generating_video",
                status="generating_video",
                data={"model": seedance_model, "finance_mode": finance_mode},
            )
            if finance_mode and content_prompt_package.get("seedance_series_payloads"):
                all_series_payloads = content_prompt_package["seedance_series_payloads"]
                series_payloads_to_generate = (
                    all_series_payloads[:1]
                    if finance_generate_sample_first and len(all_series_payloads) > 1
                    else all_series_payloads
                )
                video_generation = _generate_finance_video_series(
                    series_payloads=series_payloads_to_generate,
                    product_name=product_analysis["product_name"],
                    output_dir=session_output_dir,
                    api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
                )
                video_generation["series_sample_first"] = bool(
                    finance_generate_sample_first and len(all_series_payloads) > 1
                )
                video_generation["planned_series_count"] = len(all_series_payloads)
                video_generation["generated_series_count"] = len(series_payloads_to_generate)
                video_generation["remaining_series_count"] = max(
                    0, len(all_series_payloads) - len(series_payloads_to_generate)
                )
                if video_generation["series_sample_first"]:
                    video_generation["sample_next_step"] = (
                        "Review the first sample video. If the style, avatar, pace, and infographic direction are approved, generate the remaining finance series episodes."
                    )
            else:
                video_generation = openrouter_seedance_client.generate_video(
                    seedance_payload=content_prompt_package["seedance_payload"],
                    product_name=product_analysis["product_name"],
                    output_dir=session_output_dir,
                    api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
                )
            video_generation["generation_mode"] = generation_mode
        else:
            video_generation = _video_generation_skipped_by_mode(
                content_prompt_package=content_prompt_package,
                session_output_dir=session_output_dir,
                generation_mode=generation_mode,
            )
        if should_generate_static_images and generation_run_repository.is_cancel_requested(run_id):
            final_export_status = "cancelled"
            static_image_generation = _static_generation_cancelled(
                image_model=image_model,
                session_output_dir=session_output_dir,
                generation_mode=generation_mode,
            )
            generation_run_repository.update_stage(
                run_id,
                "cancelled",
                status="cancelled",
                data={"reason": "Cancellation was requested after video generation; static image provider calls were skipped."},
            )
        elif should_generate_static_images:
            generation_run_repository.update_stage(
                run_id,
                "generating_images",
                status="generating_images",
                data={"model": image_model, "max_static_images": max_static_images},
            )
            if (
                config.REQUIRE_PROMPT_MODEL_FOR_STATIC_CREATIVES
                and prompt_api_key_available
                and static_prompt_generation.get("status")
                not in {"completed", "completed_with_fallback"}
            ):
                static_image_generation = _static_generation_blocked_by_prompt_model(
                    ads_creative_set=ads_creative_set,
                    image_model=image_model,
                    session_output_dir=session_output_dir,
                    generation_mode=generation_mode,
                )
            else:
                static_image_generation = openrouter_image_client.generate_ad_images(
                    ads_creative_set=ads_creative_set,
                    product_name=product_analysis["product_name"],
                    output_dir=session_output_dir,
                    api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
                    model=image_model,
                    product_reference_url=str(product_image_path),
                    reference_image_urls=[str(path) for path in saved_static_product_image_paths],
                    enabled=True,
                    max_images=max_static_images,
                    image_size=image_size,
                    enable_vision_quality_check=True,
                    vision_model=config.OPENROUTER_VISION_MODEL,
                    vision_retry_on_fail=True,
                )
                static_image_generation["generation_mode"] = generation_mode
                static_image_generation["static_prompt_generation"] = ads_creative_set.get(
                    "static_prompt_generation"
                )
        else:
            static_image_generation = _static_generation_skipped_by_mode(
                ads_creative_set=ads_creative_set,
                image_model=image_model,
                session_output_dir=session_output_dir,
                generation_mode=generation_mode,
            )
            static_image_generation["static_prompt_generation"] = ads_creative_set.get(
                "static_prompt_generation"
            )
    if (
        generation_run_repository.is_cancel_requested(run_id)
        and final_export_status not in {"blocked", "cancelled"}
    ):
        final_export_status = "cancelled"
        generation_run_repository.update_stage(
            run_id,
            "cancelled",
            status="cancelled",
            data={"reason": "Cancellation was requested before the run was saved."},
        )
    final_export_status = _final_status_with_generation_result(
        final_export_status=final_export_status,
        video_generation=video_generation,
        static_image_generation=static_image_generation,
        should_generate_video=should_generate_video,
        should_generate_static_images=should_generate_static_images,
        finance_mode=finance_mode,
    )
    generation_run_repository.update_stage(
        run_id,
        "qa",
        status="qa",
        data={
            "final_export_status": final_export_status,
            "video_status": video_generation.get("video_generation_status"),
            "static_status": static_image_generation.get("image_generation_status"),
        },
    )
    self_critique = creative_self_critique.critique(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        ads_creative_set=ads_creative_set,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
        api_key=openrouter_api_key or config.OPENROUTER_API_KEY,
        model=prompt_model,
    )
    post_generation_quality = post_generation_qa.evaluate(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
        ads_creative_set=ads_creative_set,
        finance_mode=finance_mode,
        should_generate_video=should_generate_video,
        should_generate_static_images=should_generate_static_images,
    )
    session_cost_summary = cost_tracker.build_session_cost_summary(
        content_prompt_package=content_prompt_package,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
        product_analysis=product_analysis,
        input_data=input_data,
        self_critique=self_critique,
    )
    prompt_audit = audit_builder.build_prompt_audit(
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        deterministic_content_prompt_package=deterministic_content_prompt_package,
        final_content_prompt_package=content_prompt_package,
        deterministic_ads_creative_set=deterministic_ads_creative_set,
        final_ads_creative_set=ads_creative_set,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
        prompt_model=prompt_model,
    )
    generation_run_repository.attach_audit(
        run_id,
        prompt_audit=prompt_audit,
        provider_validation=provider_validation,
        cost_summary=session_cost_summary,
        output_dir=str(session_output_dir),
    )
    creative_plan_preview = audit_builder.build_creative_plan_preview(
        ads_creative_set=ads_creative_set,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
        provider_validation=provider_validation,
        generation_mode=generation_mode,
        prompt_api_key_available=prompt_api_key_available,
        max_static_images=max_static_images,
        product_reference_url=str(product_image_path),
    )

    final_output = build_final_output(
        input_data=input_data,
        avatar=avatar,
        product_analysis=product_analysis,
        ugc_strategy=ugc_strategy,
        content_prompt_package=content_prompt_package,
        product_fidelity_result=product_fidelity_result,
        compliance_result=compliance_result,
        quality_result=quality_result,
        ads_creative_set=ads_creative_set,
        static_image_generation=static_image_generation,
        video_generation=video_generation,
        session_cost_summary=session_cost_summary,
        final_export_status=final_export_status,
        provider_validation=provider_validation,
        creative_plan_preview=creative_plan_preview,
        prompt_audit=prompt_audit,
        self_critique=self_critique,
        post_generation_qa=post_generation_quality,
        scenario_integrity_result=scenario_integrity_result,
    )
    performance_memory.record_generated_candidates(final_output)
    final_output["creative_memory"] = creative_memory_db.save_generation(final_output)
    final_output["workflow_report"] = workflow_reporter.build(final_output)
    generation_run_repository.update_stage(
        run_id,
        "saving",
        status="saving",
        data={"creative_memory": final_output.get("creative_memory")},
    )
    final_output["generation_run"] = generation_run_repository.complete_run(run_id, final_output)
    output_writer.save(final_output, output_dir=session_output_dir)

    return JSONResponse(content=final_output)


def _blocked_reason(
    product_fidelity_result: dict[str, Any],
    compliance_result: dict[str, Any],
    quality_result: dict[str, Any],
) -> str:
    reasons = []
    if product_fidelity_result.get("product_fidelity_status") == "fail":
        details = product_fidelity_result.get("changed_or_invented_details") or product_fidelity_result.get("missing_fidelity_instructions") or []
        reasons.append(f"Product Fidelity Guard failed: {', '.join(details) if details else 'product fidelity requirements were not met'}")
    if compliance_result.get("compliance_status") == "fail":
        details = _compliance_block_details(compliance_result)
        reasons.append(f"Compliance Guard failed: {', '.join(details) if details else 'compliance requirements were not met'}")
    if not reasons:
        recommendations = quality_result.get("recommended_improvements") or []
        reasons.append(
            "Quality scorer blocked export"
            + (f": {', '.join(recommendations)}" if recommendations else ".")
        )
    return " | ".join(reasons)


def _provider_validation_with_scenario_integrity(
    provider_validation: dict[str, Any],
    scenario_integrity_result: dict[str, Any],
) -> dict[str, Any]:
    validation = dict(provider_validation or {})
    checks = list(validation.get("checks") or [])
    check = scenario_integrity_guard.provider_check(scenario_integrity_result)
    checks.append(check)
    validation["checks"] = checks
    if scenario_integrity_result.get("status") == "failed":
        validation["status"] = "blocked"
        validation["reason"] = scenario_integrity_result.get("reason") or "Scenario Integrity Guard blocked generation."
    return validation


def _compliance_block_details(compliance_result: dict[str, Any]) -> list[str]:
    details: list[str] = []
    for key in [
        "unsupported_claims",
        "fake_review_risks",
        "trademark_risks",
        "platform_policy_risks",
        "uk_market_risks",
        "finance_risks",
    ]:
        for value in compliance_result.get(key) or []:
            text = str(value or "").strip()
            if text and text not in details:
                details.append(text)
    return details


def _blocked_next_step(provider_validation: dict[str, Any]) -> str | None:
    for check in provider_validation.get("checks") or []:
        if check.get("status") == "failed":
            return check.get("next_step") or check.get("reason")
    return None


def _early_provider_block_output(
    input_data: dict[str, Any],
    avatar: dict[str, Any],
    provider_validation: dict[str, Any],
    session_output_dir: Path,
) -> dict[str, Any]:
    reason = provider_validation.get("reason") or "Provider capability validation blocked the workflow."
    return {
        "workflow_sequence": [
            "Provider Capability Validation",
            "Prompt Source Trace",
            "Export JSON/Markdown",
        ],
        "status": "blocked",
        "error": reason,
        "final_export_status": "blocked",
        "prompt_source_trace": prompt_defaults.PROMPT_SOURCE_INVENTORY,
        "user_input": input_data,
        "avatar": avatar,
        "product_analysis": {},
        "ugc_strategy": {},
        "content_prompt_package": {},
        "product_fidelity_result": {},
        "compliance_result": {},
        "quality_result": {
            "export_status": "blocked",
            "recommended_improvements": [reason],
        },
        "ads_creative_set": {},
        "static_image_generation": {
            "image_generation_status": "blocked",
            "failure_reason": reason,
            "next_step": _blocked_next_step(provider_validation),
            "image_assets": [],
            "output_dir": str(session_output_dir),
            "provider_validation": provider_validation,
        },
        "seedance_payload": {},
        "video_generation": {
            "video_generation_status": "blocked",
            "failure_reason": reason,
            "next_step": _blocked_next_step(provider_validation),
            "video_path": None,
            "provider_validation": provider_validation,
        },
        "session_cost_summary": {
            "version": "openrouter_cost_summary_v2",
            "status": "not_started",
            "currency": "OpenRouter-reported cost, usually USD",
            "total_known_cost": 0,
            "total_known_cost_display": "0",
            "total_known_cost_usd_display": "$0",
            "unknown_cost_components": [],
            "request_count": 0,
            "known_request_count": 0,
            "unknown_request_count": 0,
            "component_count": 0,
            "components": [],
            "by_group": {},
        },
        "provider_validation": provider_validation,
        "creative_plan_preview": {
            "version": "creative_plan_preview_v1",
            "generation_mode": input_data.get("generation_mode"),
            "items": [],
        },
        "prompt_audit": {
            "version": "prompt_audit_v1",
            "status": "not_started",
            "reason": reason,
        },
    }


def _apply_custom_avatar_profile(
    avatar: dict[str, Any],
    custom_avatar_name: str,
    custom_avatar_persona: str,
    custom_avatar_voice: str,
    avatar_wardrobe_policy: str,
    avatar_identity_note: str,
    avatar_own_person_consent: bool,
) -> dict[str, Any]:
    profile = dict(avatar)
    if custom_avatar_name.strip():
        profile["name"] = custom_avatar_name.strip()
    if custom_avatar_persona.strip():
        profile["style"] = sanitize_avatar_descriptor(custom_avatar_persona)
        profile["persona"] = sanitize_avatar_descriptor(custom_avatar_persona)
    if custom_avatar_voice.strip():
        profile["voice"] = sanitize_avatar_descriptor(custom_avatar_voice)
    if profile.get("style"):
        profile["style"] = sanitize_avatar_descriptor(profile.get("style"))
    if profile.get("persona"):
        profile["persona"] = sanitize_avatar_descriptor(profile.get("persona"))
    if profile.get("voice"):
        profile["voice"] = sanitize_avatar_descriptor(profile.get("voice"))
    wardrobe_policy = avatar_wardrobe_policy.strip() or "reference_unchanged"
    if wardrobe_policy not in {"reference_unchanged", "consistent_simple", "allow_controlled_change"}:
        wardrobe_policy = "reference_unchanged"
    profile["wardrobe_policy"] = wardrobe_policy
    profile["identity_note"] = avatar_identity_note.strip()
    profile["own_person_confirmed"] = bool(avatar_own_person_consent)
    profile["identity_type"] = "own_person_or_authorized_avatar" if avatar_own_person_consent else "selected_avatar"
    profile["authorization_statement"] = AUTHORIZED_AVATAR_CONSENT_STATEMENT if avatar_own_person_consent else ""
    return profile


def _normalize_generation_mode(value: str) -> str:
    normalized = str(value or "both").strip().lower()
    aliases = {
        "ugc_video": "video",
        "video_only": "video",
        "videos": "video",
        "static_images": "static",
        "static_only": "static",
        "images": "static",
        "all": "both",
        "both": "both",
        "oboji": "both",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"both", "video", "static"}:
        return "both"
    return normalized


def _get_or_create_generation_run(
    *,
    existing_generation_run_id: str,
    workspace: str,
    app_mode: str,
    input_snapshot: dict[str, Any],
    idempotency_key: str,
    output_dir: str = "",
) -> dict[str, Any]:
    existing_id = str(existing_generation_run_id or "").strip()
    if existing_id:
        run = generation_run_repository.get_run(existing_id)
        if not run:
            raise ValueError(f"Unknown generation run: {existing_id}")
        generation_run_repository.update_input_snapshot(
            existing_id,
            input_snapshot,
            output_dir=output_dir or None,
        )
        return generation_run_repository.get_run(existing_id) or run
    return generation_run_repository.create_run(
        workspace=workspace,
        app_mode=app_mode,
        input_snapshot=input_snapshot,
        idempotency_key=idempotency_key,
        output_dir=output_dir,
    )


def _merge_unique(primary: list[Any], secondary: list[Any], limit: int = 8) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in [*primary, *secondary]:
        text = str(item or "").strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _static_generation_skipped_by_mode(
    ads_creative_set: dict[str, Any],
    image_model: str,
    session_output_dir: Path,
    generation_mode: str,
) -> dict[str, Any]:
    source_creative_count = len(ads_creative_set.get("static_image_ads") or [])
    carousel = ads_creative_set.get("carousel_ad") or {}
    source_creative_count += len(carousel.get("cards") or [])
    return {
        "image_generation_status": "skipped",
        "error": "Static image generation skipped by selected generation mode.",
        "failure_reason": "Generation mode is UGC video only, so static ad images were not generated.",
        "next_step": "Switch generation mode to Static images only or Both if you want image files.",
        "model": image_model,
        "image_assets": [],
        "attempted_count": 0,
        "selected_creative_count": 0,
        "source_creative_count": source_creative_count,
        "generation_plan": [],
        "skipped_creatives": [],
        "output_dir": str(session_output_dir),
        "generation_mode": generation_mode,
        "skipped_by_generation_mode": True,
        "max_images_policy": "not_applicable_video_only",
    }


def _static_generation_cancelled(
    *,
    image_model: str,
    session_output_dir: Path,
    generation_mode: str,
) -> dict[str, Any]:
    return {
        "image_generation_status": "cancelled",
        "error": "Static image generation cancelled before image provider calls.",
        "failure_reason": "User requested cancellation after the previous stage.",
        "next_step": "Start a new run when you are ready, or regenerate only the missing static assets.",
        "model": image_model,
        "image_assets": [],
        "attempted_count": 0,
        "selected_creative_count": 0,
        "source_creative_count": 0,
        "generation_plan": [],
        "skipped_creatives": [],
        "output_dir": str(session_output_dir),
        "generation_mode": generation_mode,
        "cancelled_before_provider_call": True,
        "max_images_policy": "cap_only_no_padding",
    }


def _static_generation_blocked_by_prompt_model(
    ads_creative_set: dict[str, Any],
    image_model: str,
    session_output_dir: Path,
    generation_mode: str,
) -> dict[str, Any]:
    static_prompt_generation = ads_creative_set.get("static_prompt_generation") or {}
    attempts = static_prompt_generation.get("attempts") or []
    reason = static_prompt_generation.get("error") or "Static creative prompt model did not complete."
    if attempts:
        reason = " | ".join(
            f"{item.get('model')}: {item.get('error') or item.get('status')}"
            for item in attempts
        )
    return {
        "image_generation_status": "blocked",
        "error": "Static image generation requires successful creative prompt generation.",
        "failure_reason": reason,
        "next_step": (
            "Fix the prompt model access or choose a working prompt model. "
            "Images were not generated from deterministic fallback templates."
        ),
        "model": image_model,
        "image_assets": [],
        "attempted_count": 0,
        "selected_creative_count": 0,
        "source_creative_count": len(ads_creative_set.get("static_image_ads") or [])
        + len((ads_creative_set.get("carousel_ad") or {}).get("cards") or []),
        "generation_plan": [],
        "skipped_creatives": [],
        "output_dir": str(session_output_dir),
        "generation_mode": generation_mode,
        "blocked_by_prompt_model": True,
        "static_prompt_generation": static_prompt_generation,
    }


def _video_generation_skipped_by_mode(
    content_prompt_package: dict[str, Any],
    session_output_dir: Path,
    generation_mode: str,
) -> dict[str, Any]:
    payload = content_prompt_package.get("seedance_payload") or {}
    return {
        "video_generation_status": "skipped",
        "error": "Seedance video generation skipped by selected generation mode.",
        "failure_reason": "Generation mode is static images only, so the Seedance video API was not called.",
        "next_step": "Switch generation mode to UGC video only or Both if you want video generation.",
        "video_path": None,
        "job_id": None,
        "output_dir": str(session_output_dir),
        "generation_mode": generation_mode,
        "skipped_by_generation_mode": True,
        "submitted_payload": {
            "model": payload.get("model"),
            "prompt": payload.get("prompt"),
            "duration": payload.get("duration"),
            "aspect_ratio": payload.get("aspect_ratio"),
            "resolution": payload.get("resolution"),
        },
    }


def _final_status_with_generation_result(
    *,
    final_export_status: str,
    video_generation: dict[str, Any],
    static_image_generation: dict[str, Any],
    should_generate_video: bool,
    should_generate_static_images: bool,
    finance_mode: bool,
) -> str:
    if final_export_status in {"blocked", "cancelled"}:
        return final_export_status
    video_status = str(video_generation.get("video_generation_status") or "").lower()
    if should_generate_video and video_status == "cancelled":
        return "cancelled"
    if should_generate_video and video_status in {"failed", "blocked"}:
        return "blocked"
    if finance_mode and should_generate_video and video_status in {"skipped", "missing", "unknown", ""}:
        return "blocked"
    static_status = str(static_image_generation.get("image_generation_status") or "").lower()
    if should_generate_static_images and static_status == "cancelled":
        return "cancelled"
    if should_generate_static_images and static_status in {"failed", "blocked"}:
        return "blocked"
    if finance_mode and should_generate_video:
        return "warning"
    if should_generate_video and video_status in {"skipped", "missing", "unknown", ""}:
        return "warning"
    if should_generate_static_images and static_status in {"skipped", "missing", "unknown", ""}:
        return "warning"
    return final_export_status


def _generate_finance_video_series(
    *,
    series_payloads: list[dict[str, Any]],
    product_name: str,
    output_dir: Path,
    api_key: str,
) -> dict[str, Any]:
    items = []
    for index, seedance_payload in enumerate(series_payloads, start=1):
        episode_dir = output_dir / f"finance_video_{index:02d}"
        result = openrouter_seedance_client.generate_video(
            seedance_payload=seedance_payload,
            product_name=f"{product_name} {index}",
            output_dir=episode_dir,
            api_key=api_key,
        )
        result["series_episode"] = index
        result["series_total"] = len(series_payloads)
        result["series_title"] = seedance_payload.get("series_title") or f"Finance video {index}"
        items.append(result)

    statuses = [item.get("video_generation_status") for item in items]
    if all(status == "completed" for status in statuses):
        status = "completed"
        error = None
        failure_reason = None
        next_step = None
    elif all(status == "skipped" for status in statuses):
        status = "skipped"
        error = items[0].get("error") if items else "Video generation skipped."
        failure_reason = items[0].get("failure_reason") if items else "Video generation skipped."
        next_step = items[0].get("next_step") if items else None
    elif any(status == "completed" for status in statuses):
        status = "partial"
        error = "Some finance series videos did not complete."
        failure_reason = "At least one finance series episode failed or was skipped."
        next_step = "Review each finance_video_* folder and regenerate failed episodes."
    else:
        status = "failed"
        error = items[0].get("error") if items else "Finance video series failed."
        failure_reason = items[0].get("failure_reason") if items else "Finance video series failed."
        next_step = items[0].get("next_step") if items else None

    first_completed = next((item for item in items if item.get("video_generation_status") == "completed"), items[0] if items else {})
    return {
        "video_generation_status": status,
        "error": error,
        "failure_reason": failure_reason,
        "next_step": next_step,
        "video_path": first_completed.get("video_path"),
        "video_url": first_completed.get("video_url"),
        "job_id": first_completed.get("job_id"),
        "output_dir": str(output_dir),
        "series_count": len(series_payloads),
        "series_items": items,
        "submitted_payload": {
            "series_count": len(series_payloads),
            "payloads": [
                {
                    "model": payload.get("model"),
                    "duration": payload.get("duration"),
                    "aspect_ratio": payload.get("aspect_ratio"),
                    "resolution": payload.get("resolution"),
                    "series_episode": payload.get("series_episode"),
                    "series_total": payload.get("series_total"),
                    "series_title": payload.get("series_title"),
                    "prompt": payload.get("prompt"),
                }
                for payload in series_payloads
            ],
        },
    }


def build_final_output(
    input_data: dict[str, Any],
    avatar: dict[str, Any],
    product_analysis: dict[str, Any],
    ugc_strategy: dict[str, Any],
    content_prompt_package: dict[str, Any],
    product_fidelity_result: dict[str, Any],
    compliance_result: dict[str, Any],
    quality_result: dict[str, Any],
    ads_creative_set: dict[str, Any],
    static_image_generation: dict[str, Any],
    video_generation: dict[str, Any],
    session_cost_summary: dict[str, Any],
    final_export_status: str,
    provider_validation: dict[str, Any],
    creative_plan_preview: dict[str, Any],
    prompt_audit: dict[str, Any],
    self_critique: dict[str, Any],
    post_generation_qa: dict[str, Any],
    scenario_integrity_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_content_prompt_package = _redact_large_references(content_prompt_package)
    final_output = {
        "workflow_sequence": [
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
            "UGC Strategy Agent",
            "Content Prompt Engineer Agent",
            "Structured Prompt Architecture V2",
            "Prompt Compression Layer",
            "Ads Creative Set Agent",
            "Product Fidelity Guard",
            "Compliance Guard",
            "Quality Scorer",
            "Scenario Integrity Guard",
            "Static Image Generation",
            "Seedance Video Generation",
            "Post Generation QA",
            "AI Self Critique",
            "Creative Intelligence Memory",
            "Session Cost Summary",
            "Prompt Source Trace",
            "Export JSON/Markdown",
        ],
        "prompt_source_trace": prompt_defaults.PROMPT_SOURCE_INVENTORY,
        "user_input": input_data,
        "finance_script_agent": input_data.get("finance_script_agent") or {},
        "avatar": avatar,
        "product_analysis": product_analysis,
        "ugc_strategy": ugc_strategy,
        "content_prompt_package": safe_content_prompt_package,
        "product_fidelity_result": product_fidelity_result,
        "compliance_result": compliance_result,
        "quality_result": quality_result,
        "scenario_integrity_result": scenario_integrity_result or {},
        "ads_creative_set": ads_creative_set,
        "static_image_generation": static_image_generation,
        "seedance_payload": safe_content_prompt_package.get("seedance_payload"),
        "video_generation": video_generation,
        "session_cost_summary": session_cost_summary,
        "provider_validation": provider_validation,
        "creative_plan_preview": creative_plan_preview,
        "prompt_audit": prompt_audit,
        "self_critique": self_critique,
        "post_generation_qa": post_generation_qa,
        "final_export_status": final_export_status,
    }
    if input_data.get("app_mode") == "finance_personal_brand":
        final_output["workflow_sequence"].insert(
            final_output["workflow_sequence"].index("UGC Strategy Agent"),
            "Finance Script Agent",
        )
    if (input_data.get("competitor_strategy") or {}).get("status") == "ready":
        final_output["workflow_sequence"].insert(
            final_output["workflow_sequence"].index("Performance Memory Layer"),
            "Competitor Strategy Chat Agent",
        )
    final_output["workflow_report"] = workflow_reporter.build(final_output)
    return final_output


def _save_upload(upload: UploadFile, upload_dir: Path, product_name: str) -> Path:
    suffix = Path(upload.filename or "product.jpg").suffix or ".jpg"
    filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}{suffix}"
    target = upload_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    staged_path_value = getattr(upload, "staged_path", None)
    staged_path = Path(staged_path_value) if staged_path_value else None
    if staged_path and staged_path.exists():
        shutil.copyfile(staged_path, target)
        return target
    with target.open("wb") as file_obj:
        shutil.copyfileobj(upload.file, file_obj)
    return target


def _save_product_static_images(
    *,
    uploads: list[UploadFile],
    upload_dir: Path,
    product_name: str,
) -> list[Path]:
    saved = []
    for index, upload in enumerate(uploads[:8], start=1):
        if not getattr(upload, "filename", ""):
            continue
        suffix = Path(upload.filename or "variant.jpg").suffix or ".jpg"
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}_static_variant_{index}{suffix}"
        target = upload_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        staged_path_value = getattr(upload, "staged_path", None)
        staged_path = Path(staged_path_value) if staged_path_value else None
        if staged_path and staged_path.exists():
            shutil.copyfile(staged_path, target)
        else:
            upload.file.seek(0)
            with target.open("wb") as file_obj:
                shutil.copyfileobj(upload.file, file_obj)
        saved.append(target)
    return saved


def _save_competitor_screenshots(
    *,
    uploads: list[UploadFile],
    upload_dir: Path,
    competitor_name: str,
) -> list[dict[str, Any]]:
    saved = []
    for index, upload in enumerate(uploads, start=1):
        if not getattr(upload, "filename", ""):
            continue
        suffix = Path(upload.filename or "screenshot.png").suffix or ".png"
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(competitor_name)}_{index}{suffix}"
        target = upload_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        staged_path_value = getattr(upload, "staged_path", None)
        staged_path = Path(staged_path_value) if staged_path_value else None
        if staged_path and staged_path.exists():
            shutil.copyfile(staged_path, target)
        else:
            upload.file.seek(0)
            with target.open("wb") as file_obj:
                shutil.copyfileobj(upload.file, file_obj)
        saved.append(
            {
                "filename": upload.filename or filename,
                "path": str(target),
                "role": "competitor_strategy_reference_only",
                "rule": "Stored for audit and human review; not passed as direct visual reference to image/video generation.",
            }
        )
    return saved


def _create_session_output_dir(
    product_name: str,
    output_root: str | Path,
    *,
    app_mode: str = "ecommerce",
    session_prefix: str | None = None,
    subfolder: str | None = None,
) -> Path:
    root = _workspace_output_root(output_root, app_mode, subfolder=subfolder)
    prefix = session_prefix or ("FIN_BRAND" if app_mode == "finance_personal_brand" else "ADS_ST")
    folder_stem = f"{time.strftime('%Y%m%d_%H%M%S')}_{prefix}_{safe_slug(product_name)}"
    target = root / folder_stem
    suffix = 2
    while target.exists():
        target = root / f"{folder_stem}_{suffix}"
        suffix += 1
    target.mkdir(parents=True, exist_ok=True)
    return target


def _workspace_output_root(
    output_root: str | Path,
    app_mode: str,
    *,
    subfolder: str | None = None,
) -> Path:
    workspace = "finance" if app_mode == "finance_personal_brand" else "ecommerce"
    root = Path(output_root) / workspace
    if subfolder:
        root = root / safe_slug(subfolder, "sessions")
    return root


def _latest_output_json(output_dir: str | Path) -> Path | None:
    target_dir = Path(output_dir)
    if not target_dir.exists():
        return None
    files = [path for path in target_dir.rglob("*.json") if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def _build_input_references(
    product_image_path: str | Path | None,
    avatar: dict[str, Any],
    product_reference_url: str,
    avatar_reference_url: str,
    use_avatar_image_reference: bool,
) -> list[dict[str, object]]:
    product_ref = image_url_reference(product_reference_url) or data_url_reference(product_image_path)
    avatar_ref = (
        image_url_reference(avatar_reference_url or avatar.get("image_url"))
        if use_avatar_image_reference
        else None
    )
    return [ref for ref in [product_ref, avatar_ref] if ref]


def _approved_finance_scene_concept(
    *,
    topic: str,
    script_plan: dict[str, Any],
    avatar: dict[str, Any],
    platform: str,
    approved_prompt: str,
    concept_json: str,
) -> dict[str, Any]:
    parsed = {}
    if concept_json.strip():
        try:
            parsed = json.loads(concept_json)
            if not isinstance(parsed, dict):
                parsed = {}
        except Exception:
            parsed = {}
    concept = finance_video_agent.approved_scene_concept_from_settings(
        topic=topic,
        script_plan=script_plan,
        avatar=avatar,
        platform=platform,
        approved_image_prompt=approved_prompt or str(parsed.get("image_prompt") or ""),
    )
    if parsed:
        for key in [
            "visual_brief",
            "infographic_system",
            "infographic_elements",
            "interaction_plan",
            "scene_beats",
            "video_prompt_addendum_compiled",
        ]:
            if parsed.get(key):
                concept[key] = parsed[key]
        concept["status"] = "approved_for_video"
    return concept


def _is_public_http_url(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname not in {"localhost", "127.0.0.1", "::1"}


def _redact_large_references(value: dict[str, Any]) -> dict[str, Any]:
    copied = _deep_copy_without_data_urls(value)
    payload = copied.get("seedance_payload")
    if isinstance(payload, dict) and isinstance(payload.get("input_references"), list):
        payload["input_references"] = [
            {
                "type": ref.get("type", "image_url") if isinstance(ref, dict) else "unknown",
                "image_url": {"url": "[redacted image reference]"},
            }
            for ref in payload["input_references"]
        ]
        payload["input_reference_count"] = len(payload["input_references"])
    return copied


def _deep_copy_without_data_urls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deep_copy_without_data_urls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy_without_data_urls(item) for item in value]
    if isinstance(value, str) and value.startswith("data:image/"):
        return "[redacted image data url]"
    return value
