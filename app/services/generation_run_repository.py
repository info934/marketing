from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import config


SCHEMA_VERSION = "generation_runs_sqlite_v1"
ACTIVE_STATUSES = {"queued", "validating", "planning", "prompting", "generating_video", "generating_images", "qa", "saving", "running"}


def init_db(path: str | Path | None = None) -> Path:
    db_path = Path(path or config.CREATIVE_MEMORY_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generation_runs (
                run_id TEXT PRIMARY KEY,
                idempotency_key TEXT,
                workspace TEXT NOT NULL,
                app_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                current_stage TEXT,
                input_snapshot TEXT,
                stage_results TEXT,
                prompt_audit TEXT,
                provider_validation TEXT,
                cost_summary TEXT,
                output_dir TEXT,
                final_output TEXT,
                error TEXT,
                cancel_requested INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_generation_runs_workspace_status ON generation_runs(workspace, status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_generation_runs_idempotency ON generation_runs(workspace, idempotency_key, status)"
        )
    return db_path


def create_run(
    *,
    workspace: str,
    app_mode: str,
    input_snapshot: dict[str, Any] | None = None,
    idempotency_key: str = "",
    output_dir: str = "",
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    now = _now()
    normalized_workspace = _workspace(workspace, app_mode)
    normalized_app_mode = app_mode or ("finance_personal_brand" if normalized_workspace == "finance" else "ecommerce")
    key = str(idempotency_key or "").strip()
    with _connect(db_path) as conn:
        if key:
            row = conn.execute(
                """
                SELECT * FROM generation_runs
                WHERE workspace = ? AND idempotency_key = ? AND status IN (
                    'queued','validating','planning','prompting','generating_video','generating_images','qa','saving','running'
                )
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (normalized_workspace, key),
            ).fetchone()
            if row:
                reused = _row(row)
                reused["idempotency_reused"] = True
                return reused
        run_id = _run_id(normalized_workspace, key, now, input_snapshot or {})
        payload = {
            "run_id": run_id,
            "idempotency_key": key,
            "workspace": normalized_workspace,
            "app_mode": normalized_app_mode,
            "status": "queued",
            "current_stage": "queued",
            "input_snapshot": _json_dumps(input_snapshot or {}),
            "stage_results": _json_dumps([]),
            "prompt_audit": _json_dumps({}),
            "provider_validation": _json_dumps({}),
            "cost_summary": _json_dumps({}),
            "output_dir": output_dir,
            "final_output": _json_dumps({}),
            "error": "",
            "cancel_requested": 0,
            "created_at": now,
            "updated_at": now,
        }
        conn.execute(
            """
            INSERT INTO generation_runs (
                run_id, idempotency_key, workspace, app_mode, status, current_stage,
                input_snapshot, stage_results, prompt_audit, provider_validation, cost_summary,
                output_dir, final_output, error, cancel_requested, created_at, updated_at
            ) VALUES (
                :run_id, :idempotency_key, :workspace, :app_mode, :status, :current_stage,
                :input_snapshot, :stage_results, :prompt_audit, :provider_validation, :cost_summary,
                :output_dir, :final_output, :error, :cancel_requested, :created_at, :updated_at
            )
            """,
            payload,
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id, **payload}


def update_stage(
    run_id: str,
    stage: str,
    *,
    status: str | None = None,
    data: dict[str, Any] | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    now = _now()
    with _connect(db_path) as conn:
        row = conn.execute("SELECT stage_results FROM generation_runs WHERE run_id = ?", (run_id,)).fetchone()
        if not row:
            raise ValueError(f"Unknown generation run: {run_id}")
        stages = _json_loads(row["stage_results"])
        if not isinstance(stages, list):
            stages = []
        stages.append(
            {
                "stage": stage,
                "status": status or stage,
                "data": data or {},
                "updated_at": now,
            }
        )
        conn.execute(
            """
            UPDATE generation_runs
            SET status = ?, current_stage = ?, stage_results = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (status or stage, stage, _json_dumps(stages), now, run_id),
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id}


def update_input_snapshot(
    run_id: str,
    input_snapshot: dict[str, Any],
    *,
    output_dir: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    now = _now()
    updates = ["input_snapshot = ?", "updated_at = ?"]
    params: list[Any] = [_json_dumps(input_snapshot or {}), now]
    if output_dir is not None:
        updates.append("output_dir = ?")
        params.append(output_dir)
    params.append(run_id)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE generation_runs SET {', '.join(updates)} WHERE run_id = ?",
            params,
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id}


def attach_audit(
    run_id: str,
    *,
    prompt_audit: dict[str, Any] | None = None,
    provider_validation: dict[str, Any] | None = None,
    cost_summary: dict[str, Any] | None = None,
    output_dir: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    updates = []
    params: list[Any] = []
    if prompt_audit is not None:
        updates.append("prompt_audit = ?")
        params.append(_json_dumps(prompt_audit))
    if provider_validation is not None:
        updates.append("provider_validation = ?")
        params.append(_json_dumps(provider_validation))
    if cost_summary is not None:
        updates.append("cost_summary = ?")
        params.append(_json_dumps(cost_summary))
    if output_dir is not None:
        updates.append("output_dir = ?")
        params.append(output_dir)
    if not updates:
        return get_run(run_id, path=db_path) or {"run_id": run_id}
    updates.append("updated_at = ?")
    params.append(_now())
    params.append(run_id)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE generation_runs SET {', '.join(updates)} WHERE run_id = ?",
            params,
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id}


def complete_run(
    run_id: str,
    final_output: dict[str, Any],
    *,
    status: str | None = None,
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    final_status = status or _status_from_final_output(final_output)
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE generation_runs
            SET status = ?, current_stage = ?, final_output = ?, prompt_audit = ?,
                provider_validation = ?, cost_summary = ?, output_dir = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (
                final_status,
                final_status,
                _json_dumps(_compact_final_output(final_output)),
                _json_dumps(final_output.get("prompt_audit") or {}),
                _json_dumps(final_output.get("provider_validation") or {}),
                _json_dumps(final_output.get("session_cost_summary") or {}),
                str((final_output.get("user_input") or {}).get("session_output_dir") or ""),
                now,
                run_id,
            ),
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id}


def fail_run(run_id: str, error: str, *, path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE generation_runs
            SET status = 'failed', current_stage = 'failed', error = ?, updated_at = ?
            WHERE run_id = ?
            """,
            (str(error or ""), now, run_id),
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id}


def request_cancel(run_id: str, *, path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE generation_runs SET cancel_requested = 1, updated_at = ? WHERE run_id = ?",
            (_now(), run_id),
        )
    return get_run(run_id, path=db_path) or {"run_id": run_id, "status": "missing"}


def is_cancel_requested(run_id: str, *, path: str | Path | None = None) -> bool:
    row = get_run(run_id, path=path)
    return bool(row and row.get("cancel_requested"))


def get_run(run_id: str, *, path: str | Path | None = None) -> dict[str, Any] | None:
    db_path = init_db(path)
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM generation_runs WHERE run_id = ?", (run_id,)).fetchone()
    return _row(row) if row else None


def latest_run(workspace: str = "", *, path: str | Path | None = None) -> dict[str, Any] | None:
    db_path = init_db(path)
    clauses = []
    params: list[Any] = []
    normalized_workspace = str(workspace or "").strip().lower()
    if normalized_workspace in {"ecommerce", "finance", "finance_personal_brand"}:
        clauses.append("workspace = ?")
        params.append("finance" if normalized_workspace == "finance_personal_brand" else normalized_workspace)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    with _connect(db_path) as conn:
        row = conn.execute(
            f"SELECT * FROM generation_runs {where} ORDER BY updated_at DESC LIMIT 1",
            params,
        ).fetchone()
    return _row(row) if row else None


def list_runs(workspace: str = "", *, limit: int = 80, path: str | Path | None = None) -> list[dict[str, Any]]:
    db_path = init_db(path)
    clauses = []
    params: list[Any] = []
    normalized_workspace = str(workspace or "").strip().lower()
    if normalized_workspace in {"ecommerce", "finance", "finance_personal_brand"}:
        clauses.append("workspace = ?")
        params.append("finance" if normalized_workspace == "finance_personal_brand" else normalized_workspace)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    safe_limit = max(1, min(int(limit or 80), 250))
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM generation_runs {where} ORDER BY updated_at DESC LIMIT ?",
            [*params, safe_limit],
        ).fetchall()
    return [_row(row) for row in rows]


def active_run(workspace: str = "", *, path: str | Path | None = None) -> dict[str, Any] | None:
    db_path = init_db(path)
    clauses = [
        "status IN ('queued','validating','planning','prompting','generating_video','generating_images','qa','saving','running')"
    ]
    params: list[Any] = []
    normalized_workspace = str(workspace or "").strip().lower()
    if normalized_workspace in {"ecommerce", "finance", "finance_personal_brand"}:
        clauses.append("workspace = ?")
        params.append("finance" if normalized_workspace == "finance_personal_brand" else normalized_workspace)
    where = "WHERE " + " AND ".join(clauses)
    with _connect(db_path) as conn:
        row = conn.execute(
            f"SELECT * FROM generation_runs {where} ORDER BY updated_at DESC LIMIT 1",
            params,
        ).fetchone()
    return _row(row) if row else None


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ["input_snapshot", "stage_results", "prompt_audit", "provider_validation", "cost_summary", "final_output"]:
        item[key] = _json_loads(item.get(key))
    item["cancel_requested"] = bool(item.get("cancel_requested"))
    item["version"] = SCHEMA_VERSION
    return item


def _workspace(workspace: str, app_mode: str) -> str:
    value = str(workspace or "").strip().lower()
    if value in {"finance", "finance_personal_brand"}:
        return "finance"
    if str(app_mode or "").strip() == "finance_personal_brand":
        return "finance"
    return "ecommerce"


def _run_id(workspace: str, key: str, now: str, snapshot: dict[str, Any]) -> str:
    digest = hashlib.sha1(
        json.dumps([workspace, key, now, snapshot], sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:14]
    return f"run_{workspace}_{digest}"


def _status_from_final_output(final_output: dict[str, Any]) -> str:
    status = str(final_output.get("final_export_status") or "").lower()
    if status in {"blocked", "cancelled", "failed", "needs_confirmation", "needs_scene_approval"}:
        return status
    return "completed"


def _compact_final_output(final_output: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_export_status": final_output.get("final_export_status"),
        "user_input": final_output.get("user_input"),
        "creative_plan_preview": final_output.get("creative_plan_preview"),
        "ads_creative_set": _compact_ads_creative_set(final_output.get("ads_creative_set") or {}),
        "video_generation": final_output.get("video_generation"),
        "static_image_generation": _compact_static_image_generation(
            final_output.get("static_image_generation") or {}
        ),
        "session_cost_summary": final_output.get("session_cost_summary"),
        "provider_validation": final_output.get("provider_validation"),
        "prompt_audit": final_output.get("prompt_audit"),
        "self_critique": final_output.get("self_critique"),
        "creative_memory": final_output.get("creative_memory"),
        "output_files": final_output.get("output_files"),
        "product_fidelity_result": final_output.get("product_fidelity_result"),
        "compliance_result": final_output.get("compliance_result"),
        "quality_result": final_output.get("quality_result"),
        "workflow_report": final_output.get("workflow_report"),
    }


def _compact_ads_creative_set(ad_set: dict[str, Any]) -> dict[str, Any]:
    return {
        "creative_plan": ad_set.get("creative_plan") or [],
        "creative_angles": ad_set.get("creative_angles") or [],
        "ad_description_suggestions": ad_set.get("ad_description_suggestions") or {},
        "static_prompt_generation": ad_set.get("static_prompt_generation") or {},
        "prompt_learning_directive": ad_set.get("prompt_learning_directive"),
        "static_creative_director": ad_set.get("static_creative_director") or {},
    }


def _compact_static_image_generation(static_generation: dict[str, Any]) -> dict[str, Any]:
    return {
        **{
            key: value
            for key, value in static_generation.items()
            if key not in {"image_assets"}
        },
        "image_assets": [
            _compact_image_asset(asset)
            for asset in (static_generation.get("image_assets") or [])
        ],
    }


def _compact_image_asset(asset: dict[str, Any]) -> dict[str, Any]:
    keep = [
        "creative_id",
        "set_id",
        "asset_type",
        "image_url",
        "image_path",
        "status",
        "angle",
        "funnel_stage",
        "visual_diversity_score",
        "failure_reason",
        "error",
        "prompt",
        "prompt_preview",
    ]
    return {key: asset.get(key) for key in keep if key in asset}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: Any) -> Any:
    if value in (None, ""):
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
