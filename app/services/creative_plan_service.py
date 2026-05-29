from __future__ import annotations

from typing import Any

from app.services import provider_capability_service


VERSION = "creative_plan_service_v1"


def preview(
    *,
    app_mode: str = "ecommerce",
    generation_mode: str = "both",
    max_static_images: int = 8,
    image_model: str = "",
    seedance_model: str = "",
    api_key_available: bool = False,
) -> dict[str, Any]:
    workspace = "finance" if str(app_mode or "").strip() == "finance_personal_brand" else "ecommerce"
    mode = _generation_mode(generation_mode, workspace)
    max_images = _cap(max_static_images)
    rows = _finance_rows(mode, seedance_model, api_key_available) if workspace == "finance" else _ecommerce_rows(
        mode=mode,
        max_images=max_images,
        image_model=image_model,
        seedance_model=seedance_model,
        api_key_available=api_key_available,
    )
    return {
        "version": VERSION,
        "workspace": workspace,
        "generation_mode": mode,
        "max_static_images": 0 if workspace == "finance" else max_images,
        "image_count_policy": "cap_only_no_padding",
        "selected_video_count": sum(1 for item in rows if item["media"] == "video" and item["status"] == "YES"),
        "selected_image_count": sum(int(item.get("image_cost") or 0) for item in rows if item["media"] == "image" and item["status"] in {"YES", "PARTIAL"}),
        "items": rows,
    }


def _ecommerce_rows(
    *,
    mode: str,
    max_images: int,
    image_model: str,
    seedance_model: str,
    api_key_available: bool,
) -> list[dict[str, Any]]:
    video_capability = provider_capability_service.video_model_capability(seedance_model)
    image_capability = provider_capability_service.image_model_capability(image_model)
    rows = [_video_row(mode, video_capability, api_key_available)]
    image_rows = [
        _row("C2", "Static product hero", "PRODUCT_HERO", "1:1", "TOFU + retargeting", 10, "image", 1, "product-first hero frame"),
        _row("C4", "Static proof detail", "DETAIL_PROOF", "1:1", "Retargeting", 10, "image", 1, "detail proof pro produktove teple publikum"),
        _row("C3", "Static use context", "USE_CONTEXT", "1:1", "TOFU + retargeting", 10, "image", 1, "real-use context se scale/context cue"),
        _row("C5", "Carousel buying guide", "BUYING_GUIDE", "1:1", "MOFU", 15, "image", 5, "petikartovy buying guide"),
    ]
    used = 0
    for row in image_rows:
        if mode == "video":
            row.update(status="SKIPPED", reason="generation mode=video")
        elif not api_key_available:
            row.update(status="SKIPPED", reason="no API key")
        elif not image_capability.get("supports_image_output"):
            row.update(status="BLOCKED", reason="Selected image model does not support image generation")
        else:
            cost = int(row.get("image_cost") or 1)
            remaining = max_images - used
            if remaining <= 0:
                row.update(status="SKIPPED", reason="max_static_images cap")
            elif remaining < cost:
                used += remaining
                row.update(status="PARTIAL", reason=f"{remaining}/{cost} image slots available because of max_static_images cap")
            else:
                used += cost
                row.update(status="YES", reason=row["reason"])
        rows.append(row)
    return _display_order(rows)


def _finance_rows(mode: str, seedance_model: str, api_key_available: bool) -> list[dict[str, Any]]:
    video_capability = provider_capability_service.video_model_capability(seedance_model)
    row = _row(
        "C1",
        "Finance podcast studio video",
        "EDUCATION",
        "9:16",
        "TOFU + retargeting",
        100,
        "video",
        0,
        "česká osobní brand reklama z podcastového studia s interaktivní infografikou",
    )
    if mode == "static":
        row.update(status="SKIPPED", reason="finance mode supports video only")
    elif not api_key_available:
        row.update(status="SKIPPED", reason="no API key")
    elif not video_capability.get("supports_videos_endpoint"):
        row.update(status="BLOCKED", reason="Selected video model does not support OpenRouter /videos")
    else:
        row.update(status="YES", reason=row["reason"])
    return [row]


def _video_row(mode: str, capability: dict[str, Any], api_key_available: bool) -> dict[str, Any]:
    row = _row("C1", "UGC video", "UGC", "9:16", "TOFU + retargeting", 55, "video", 0, "creator-led anchor s avatarem")
    if mode == "static":
        row.update(status="SKIPPED", reason="generation mode=static")
    elif not api_key_available:
        row.update(status="SKIPPED", reason="no API key")
    elif not capability.get("supports_videos_endpoint"):
        row.update(status="BLOCKED", reason="Selected video model does not support OpenRouter /videos")
    else:
        row.update(status="YES", reason=row["reason"])
    return row


def _row(
    set_id: str,
    creative_type: str,
    angle: str,
    aspect_ratio: str,
    funnel_stage: str,
    budget_share_percent: int,
    media: str,
    image_cost: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "set_id": set_id,
        "creative_type": creative_type,
        "angle": angle,
        "aspect_ratio": aspect_ratio,
        "funnel_stage": funnel_stage,
        "budget_share_percent": budget_share_percent,
        "media": media,
        "image_cost": image_cost,
        "status": "PLANNED",
        "reason": reason,
    }


def _display_order(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {"C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5}
    return sorted(rows, key=lambda item: order.get(str(item.get("set_id")), 99))


def _generation_mode(value: str, workspace: str) -> str:
    if workspace == "finance":
        return "video"
    mode = str(value or "both").strip().lower()
    aliases = {
        "ugc_video": "video",
        "video_only": "video",
        "static_images": "static",
        "static_only": "static",
        "all": "both",
    }
    mode = aliases.get(mode, mode)
    return mode if mode in {"both", "video", "static"} else "both"


def _cap(value: int) -> int:
    try:
        return max(0, min(int(value), provider_capability_service.MAX_STATIC_IMAGE_CAP))
    except (TypeError, ValueError):
        return provider_capability_service.MAX_STATIC_IMAGE_CAP
