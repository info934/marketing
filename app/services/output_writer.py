from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app import config
from app.services.text_utils import safe_slug


def save(final_output: dict[str, Any], output_dir: str | Path | None = None) -> dict[str, str]:
    target_dir = Path(output_dir or config.OUTPUT_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    product_name = final_output.get("user_input", {}).get("product_name", "product")
    workspace = final_output.get("user_input", {}).get("session_workspace") or (
        "finance" if final_output.get("user_input", {}).get("app_mode") == "finance_personal_brand" else "ecommerce"
    )
    stem = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}"
    json_path = target_dir / f"{stem}.json"
    markdown_path = target_dir / f"{stem}.md"
    final_output["output_files"] = {
        "workspace": workspace,
        "folder_path": str(target_dir),
        "folder_name": target_dir.name,
        "workspace_root": str(target_dir.parent),
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
    }
    json_path.write_text(json.dumps(final_output, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_to_markdown(final_output), encoding="utf-8")
    return final_output["output_files"]


def _to_markdown(final_output: dict[str, Any]) -> str:
    sections = [
        "# Multi-Agent UGC Export",
        f"Export status: **{final_output.get('final_export_status')}**",
        f"Video status: **{final_output.get('video_generation', {}).get('video_generation_status')}**",
        f"Static image status: **{final_output.get('static_image_generation', {}).get('image_generation_status')}**",
        f"Known session cost: **{final_output.get('session_cost_summary', {}).get('total_known_cost_display')}**",
        "## Workflow Report",
        "```json",
        json.dumps(final_output.get("workflow_report"), ensure_ascii=False, indent=2),
        "```",
        "## Workflow",
        "Product Intake Agent -> Automatic Product Understanding -> Visual Product Classifier Agent -> UGC Strategy Agent -> Content Prompt Engineer Agent -> Ads Creative Set Agent -> Product Fidelity Guard -> Compliance Guard -> Quality Scorer -> Static Image Generation -> Seedance Video Generation -> Post Generation QA -> Session Cost Summary -> Export JSON/Markdown",
    ]
    for title, key in [
        ("User Input", "user_input"),
        ("Avatar Data", "avatar"),
        ("Product Intake Agent Output", "product_analysis"),
        ("UGC Strategy Agent Output", "ugc_strategy"),
        ("Content Prompt Engineer Agent Output", "content_prompt_package"),
        ("Product Fidelity Guard Result", "product_fidelity_result"),
        ("Compliance Guard Result", "compliance_result"),
        ("Quality Scorer Result", "quality_result"),
        ("Ads Creative Set", "ads_creative_set"),
        ("Static Image Generation", "static_image_generation"),
        ("Seedance Payload", "seedance_payload"),
        ("Video Generation", "video_generation"),
        ("Provider Validation", "provider_validation"),
        ("Creative Plan Preview", "creative_plan_preview"),
        ("Creative Memory", "creative_memory"),
        ("Prompt Audit", "prompt_audit"),
        ("Session Cost Summary", "session_cost_summary"),
    ]:
        sections.append(f"## {title}")
        sections.append("```json")
        sections.append(json.dumps(final_output.get(key), ensure_ascii=False, indent=2))
        sections.append("```")
    return "\n\n".join(sections) + "\n"
