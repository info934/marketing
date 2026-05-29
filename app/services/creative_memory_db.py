from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app import config
from app.services import embedding_service
from app.services.text_utils import detect_category, safe_slug, split_notes, unique_preserve_order


SCHEMA_VERSION = "creative_memory_sqlite_v1"


def init_db(path: str | Path | None = None) -> Path:
    db_path = Path(path or config.CREATIVE_MEMORY_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT,
                market TEXT,
                language TEXT,
                workspace TEXT DEFAULT 'ecommerce',
                app_mode TEXT DEFAULT 'ecommerce',
                product_facts TEXT,
                reference_images TEXT,
                target_audience TEXT,
                positioning TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                campaign_id TEXT PRIMARY KEY,
                product_id TEXT NOT NULL,
                platform TEXT,
                market TEXT,
                workspace TEXT DEFAULT 'ecommerce',
                app_mode TEXT DEFAULT 'ecommerce',
                goal TEXT,
                creative_strategy TEXT,
                session_folder TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(product_id)
            );

            CREATE TABLE IF NOT EXISTS creatives (
                creative_id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                set_id TEXT,
                type TEXT,
                angle TEXT,
                workspace TEXT DEFAULT 'ecommerce',
                app_mode TEXT DEFAULT 'ecommerce',
                prompt TEXT,
                negative_prompt TEXT,
                model_used TEXT,
                asset_url TEXT,
                generation_cost REAL,
                status TEXT,
                source_payload TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id)
            );

            CREATE TABLE IF NOT EXISTS ratings (
                rating_id TEXT PRIMARY KEY,
                creative_id TEXT NOT NULL,
                user_rating INTEGER,
                fidelity_score INTEGER,
                realism_score INTEGER,
                hook_score INTEGER,
                brand_fit_score INTEGER,
                comment TEXT,
                status TEXT,
                reasons TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(creative_id) REFERENCES creatives(creative_id)
            );

            CREATE TABLE IF NOT EXISTS performance (
                performance_id TEXT PRIMARY KEY,
                creative_id TEXT NOT NULL,
                ctr REAL,
                cpc REAL,
                cpa REAL,
                roas REAL,
                spend REAL,
                impressions INTEGER,
                clicks INTEGER,
                conversions INTEGER,
                platform TEXT,
                date_range TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(creative_id) REFERENCES creatives(creative_id)
            );

            CREATE TABLE IF NOT EXISTS knowledge_items (
                item_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                product_id TEXT,
                campaign_id TEXT,
                creative_id TEXT,
                category TEXT,
                market TEXT,
                platform TEXT,
                workspace TEXT DEFAULT 'ecommerce',
                app_mode TEXT DEFAULT 'ecommerce',
                angle TEXT,
                status TEXT,
                content TEXT NOT NULL,
                tags TEXT,
                score REAL,
                embedding TEXT,
                embedding_model TEXT,
                embedding_provider TEXT,
                embedding_status TEXT,
                embedding_dimensions INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_products_category_market
                ON products(category, market, language);
            CREATE INDEX IF NOT EXISTS idx_campaigns_product_platform
                ON campaigns(product_id, platform, market);
            CREATE INDEX IF NOT EXISTS idx_creatives_campaign_angle
                ON creatives(campaign_id, type, angle);
            CREATE INDEX IF NOT EXISTS idx_ratings_creative_status
                ON ratings(creative_id, status);
            CREATE INDEX IF NOT EXISTS idx_performance_creative
                ON performance(creative_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_lookup
                ON knowledge_items(workspace, category, market, platform, status, angle);
            CREATE INDEX IF NOT EXISTS idx_knowledge_creative
                ON knowledge_items(creative_id, source_type);
            """
        )
        _ensure_column(conn, "products", "workspace", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "products", "app_mode", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "campaigns", "workspace", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "campaigns", "app_mode", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "creatives", "workspace", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "creatives", "app_mode", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "knowledge_items", "workspace", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "knowledge_items", "app_mode", "TEXT DEFAULT 'ecommerce'")
        _ensure_column(conn, "knowledge_items", "embedding_model", "TEXT")
        _ensure_column(conn, "knowledge_items", "embedding_provider", "TEXT")
        _ensure_column(conn, "knowledge_items", "embedding_status", "TEXT")
        _ensure_column(conn, "knowledge_items", "embedding_dimensions", "INTEGER")
    return db_path


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {
        str(row["name"])
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def save_generation(final_output: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    now = _now()
    product = final_output.get("product_analysis") or {}
    ugc = final_output.get("ugc_strategy") or {}
    prompts = final_output.get("content_prompt_package") or {}
    ads = final_output.get("ads_creative_set") or {}
    user_input = final_output.get("user_input") or {}
    workspace = _workspace_from_input(user_input)
    app_mode = str(user_input.get("app_mode") or ("finance_personal_brand" if workspace == "finance" else "ecommerce"))

    product_id = _product_id(product, ugc)
    campaign_id = _campaign_id(user_input, product_id)
    product_payload = _product_payload(product, ugc, now, workspace=workspace, app_mode=app_mode)
    campaign_payload = _campaign_payload(product_id, final_output, now, workspace=workspace, app_mode=app_mode)
    creative_rows = _creative_rows(
        campaign_id=campaign_id,
        final_output=final_output,
        now=now,
        workspace=workspace,
        app_mode=app_mode,
    )

    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO products (
                product_id, product_name, category, market, language, product_facts,
                workspace, app_mode, reference_images, target_audience, positioning, created_at, updated_at
            ) VALUES (
                :product_id, :product_name, :category, :market, :language, :product_facts,
                :workspace, :app_mode, :reference_images, :target_audience, :positioning, :created_at, :updated_at
            )
            ON CONFLICT(product_id) DO UPDATE SET
                product_name=excluded.product_name,
                category=excluded.category,
                market=excluded.market,
                language=excluded.language,
                workspace=excluded.workspace,
                app_mode=excluded.app_mode,
                product_facts=excluded.product_facts,
                reference_images=excluded.reference_images,
                target_audience=excluded.target_audience,
                positioning=excluded.positioning,
                updated_at=excluded.updated_at
            """,
            {"product_id": product_id, **product_payload},
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO campaigns (
                campaign_id, product_id, platform, market, workspace, app_mode, goal, creative_strategy,
                session_folder, created_at
            ) VALUES (
                :campaign_id, :product_id, :platform, :market, :workspace, :app_mode, :goal, :creative_strategy,
                :session_folder, :created_at
            )
            """,
            {"campaign_id": campaign_id, **campaign_payload},
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO creatives (
                creative_id, campaign_id, set_id, type, angle, workspace, app_mode, prompt, negative_prompt,
                model_used, asset_url, generation_cost, status, source_payload, created_at
            ) VALUES (
                :creative_id, :campaign_id, :set_id, :type, :angle, :workspace, :app_mode, :prompt, :negative_prompt,
                :model_used, :asset_url, :generation_cost, :status, :source_payload, :created_at
            )
            """,
            creative_rows,
        )
        conn.executemany(
            _knowledge_insert_sql(),
            _knowledge_from_generation(
                product_id=product_id,
                campaign_id=campaign_id,
                product=product,
                ugc=ugc,
                creative_rows=creative_rows,
                now=now,
                workspace=workspace,
                app_mode=app_mode,
            ),
        )

    guidance = retrieve_guidance(
        product_analysis=product,
        settings={
            "platform": ugc.get("platform"),
            "market": ugc.get("market"),
            "language": ugc.get("language"),
            "workspace": workspace,
            "app_mode": app_mode,
        },
        path=db_path,
    )
    return {
        "version": SCHEMA_VERSION,
        "status": "saved",
        "db_path": str(db_path),
        "product_id": product_id,
        "campaign_id": campaign_id,
        "creative_count": len(creative_rows),
        "creatives": [
            {
                "creative_id": row["creative_id"],
                "set_id": row["set_id"],
                "type": row["type"],
                "angle": row["angle"],
                "status": row["status"],
                "asset_url": row["asset_url"],
            }
            for row in creative_rows
        ],
        "rag_guidance": guidance,
        "learning_layer": guidance.get("learning_layer"),
        "schema": {
            "products": "product_id, product_name, category, market, language, product_facts, reference_images, target_audience, positioning",
            "campaigns": "campaign_id, product_id, platform, market, goal, creative_strategy, created_at",
            "creatives": "creative_id, campaign_id, type, angle, prompt, negative_prompt, model_used, asset_url, generation_cost, created_at",
            "ratings": "creative_id, user_rating, fidelity_score, realism_score, hook_score, brand_fit_score, comment, approved/rejected",
            "performance": "creative_id, CTR, CPC, CPA, ROAS, spend, impressions, clicks, conversions, platform, date_range",
        },
    }


def retrieve_guidance(
    *,
    product_analysis: dict[str, Any],
    settings: dict[str, Any],
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    category = str(product_analysis.get("likely_product_category") or "").lower()
    market = str(settings.get("market") or "").upper()
    platform = str(settings.get("platform") or "").lower()
    workspace = _workspace_from_input(settings)
    with _connect(db_path) as conn:
        approved = conn.execute(
            """
            SELECT c.creative_id, c.set_id, c.type, c.angle, c.prompt, c.source_payload,
                   r.user_rating, r.fidelity_score, r.realism_score, r.hook_score, r.brand_fit_score,
                   p.category, p.market, ca.platform
            FROM creatives c
            JOIN campaigns ca ON ca.campaign_id = c.campaign_id
            JOIN products p ON p.product_id = ca.product_id
            LEFT JOIN ratings r ON r.creative_id = c.creative_id
            WHERE (lower(p.category) = ? OR ? = '')
              AND (upper(p.market) = ? OR ? = '')
              AND (lower(ca.platform) = ? OR ? = '')
              AND (lower(COALESCE(ca.workspace, 'ecommerce')) = ?)
              AND (r.status = 'approved' OR r.user_rating >= 4)
            ORDER BY COALESCE(r.user_rating, 0) DESC, c.created_at DESC
            LIMIT 12
            """,
            (category, category, market, market, platform, platform, workspace),
        ).fetchall()
        rejected = conn.execute(
            """
            SELECT c.creative_id, c.angle, c.source_payload, r.comment, r.reasons
            FROM creatives c
            JOIN campaigns ca ON ca.campaign_id = c.campaign_id
            JOIN products p ON p.product_id = ca.product_id
            JOIN ratings r ON r.creative_id = c.creative_id
            WHERE (lower(p.category) = ? OR ? = '')
              AND (upper(p.market) = ? OR ? = '')
              AND (lower(ca.platform) = ? OR ? = '')
              AND (lower(COALESCE(ca.workspace, 'ecommerce')) = ?)
              AND r.status = 'rejected'
            ORDER BY r.created_at DESC
            LIMIT 12
            """,
            (category, category, market, market, platform, platform, workspace),
        ).fetchall()
        knowledge_rows = conn.execute(
            """
            SELECT *
            FROM knowledge_items
            WHERE (lower(category) = ? OR ? = '')
              AND (upper(market) = ? OR ? = '')
              AND (lower(platform) = ? OR ? = '')
              AND (lower(COALESCE(workspace, 'ecommerce')) = ?)
            ORDER BY score DESC, created_at DESC
            LIMIT 40
            """,
            (category, category, market, market, platform, platform, workspace),
        ).fetchall()
        query_text = _knowledge_content(
            [
                product_analysis.get("product_name"),
                product_analysis.get("likely_product_category"),
                product_analysis.get("suggested_target_audience"),
                ", ".join(product_analysis.get("user_provided_facts") or []),
                ", ".join(product_analysis.get("ad_safe_detail_phrases") or []),
            ]
        )
        query_embedding = embedding_service.embed_text(query_text)
        query_vector = query_embedding.get("vector") or []
        fallback_query_vector = embedding_service.semantic_fingerprint(query_text)
        knowledge = []
        for row in knowledge_rows:
            item = dict(row)
            item_vector = _json_loads(item.get("embedding"))
            item["similarity_score"] = _embedding_similarity(
                query_vector=query_vector,
                fallback_query_vector=fallback_query_vector,
                item_vector=item_vector,
            )
            item["retrieval_score"] = round(
                float(item.get("score") or 0) + float(item["similarity_score"] or 0),
                4,
            )
            knowledge.append(item)
        knowledge.sort(key=lambda item: (item.get("retrieval_score") or 0), reverse=True)

    winning_patterns = unique_preserve_order(
        _patterns_from_rows(approved) + _knowledge_patterns(knowledge, {"winner", "approved", "performance_winner"})
    )[:12]
    avoid_patterns = unique_preserve_order(
        _avoid_patterns_from_rows(rejected) + _knowledge_patterns(knowledge, {"rejected", "avoid", "performance_loser"})
    )[:12]
    learning_layer = _learning_layer_from_knowledge(
        knowledge=knowledge,
        winning_patterns=winning_patterns,
        avoid_patterns=avoid_patterns,
    )
    return {
        "version": "creative_memory_rag_v1",
        "status": "active",
        "storage": "sqlite_embedding_pgvector_ready",
        "query": {
            "category": category or "unknown",
            "market": market or "unknown",
            "platform": platform or "unknown",
            "workspace": workspace,
            "embedding_model": query_embedding.get("model"),
            "embedding_provider": query_embedding.get("provider"),
            "embedding_status": query_embedding.get("status"),
            "embedding_dimensions": query_embedding.get("dimensions"),
            "embedding_fallback_used": query_embedding.get("fallback_used"),
        },
        "matching_winner_count": len(approved),
        "matching_rejected_count": len(rejected),
        "knowledge_item_count": len(knowledge),
        "winning_patterns": winning_patterns,
        "avoid_patterns": avoid_patterns,
        "learning_layer": learning_layer,
        "prompt_guidance": _prompt_guidance(winning_patterns, avoid_patterns, learning_layer),
    }


def preview_guidance(brief: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    product_name = str(brief.get("product_name") or "").strip()
    product_info = str(brief.get("product_info") or "").strip()
    selected_category = str(brief.get("product_category") or "auto").strip().lower()
    category = (
        detect_category(product_name, product_info)
        if selected_category in {"", "auto", "automatic"}
        else selected_category
    )
    facts = split_notes(product_info)
    product_analysis = {
        "product_name": product_name or "Current product",
        "likely_product_category": category or "unknown",
        "suggested_target_audience": brief.get("target_audience"),
        "user_provided_facts": facts,
        "ad_safe_detail_phrases": facts[:5],
    }
    settings = {
        "platform": brief.get("platform"),
        "market": brief.get("market"),
        "language": brief.get("language"),
        "workspace": brief.get("workspace") or brief.get("app_mode"),
        "app_mode": brief.get("app_mode"),
    }
    guidance = retrieve_guidance(product_analysis=product_analysis, settings=settings, path=path)
    return {
        "version": "creative_intelligence_preview_v1",
        "status": "ready",
        "product_name": product_analysis["product_name"],
        "detected_category": product_analysis["likely_product_category"],
        "category_source": "auto_detected" if selected_category in {"", "auto", "automatic"} else "user_selected",
        "platform": settings.get("platform"),
        "market": settings.get("market"),
        "language": settings.get("language"),
        "rag_guidance": guidance,
        "next_generation_guidance": {
            "winning_patterns": guidance.get("winning_patterns") or [],
            "avoid_patterns": guidance.get("avoid_patterns") or [],
            "prompt_guidance": guidance.get("prompt_guidance"),
            "confidence": (guidance.get("learning_layer") or {}).get("confidence"),
        },
    }


def add_rating(record: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    creative_id = str(record.get("creative_id") or "").strip()
    if not creative_id:
        raise ValueError("creative_id is required")
    status = str(record.get("status") or "rated").strip().lower()
    if status not in {"approved", "rejected", "rated"}:
        status = "rated"
    now = _now()
    payload = {
        "rating_id": _hash_id("rat", [creative_id, now, record.get("comment")]),
        "creative_id": creative_id,
        "user_rating": _score_or_none(record.get("user_rating")),
        "fidelity_score": _score_or_none(record.get("fidelity_score")),
        "realism_score": _score_or_none(record.get("realism_score")),
        "hook_score": _score_or_none(record.get("hook_score")),
        "brand_fit_score": _score_or_none(record.get("brand_fit_score")),
        "comment": _clean_memory_pattern(record.get("comment")),
        "status": status,
        "reasons": _json_dumps(_clean_reason_list(record.get("reasons") or [])),
        "created_at": now,
    }
    with _connect(db_path) as conn:
        exists = conn.execute(
            "SELECT creative_id FROM creatives WHERE creative_id = ?",
            (creative_id,),
        ).fetchone()
        if not exists:
            raise ValueError(f"Unknown creative_id: {creative_id}")
        conn.execute(
            """
            INSERT INTO ratings (
                rating_id, creative_id, user_rating, fidelity_score, realism_score,
                hook_score, brand_fit_score, comment, status, reasons, created_at
            ) VALUES (
                :rating_id, :creative_id, :user_rating, :fidelity_score, :realism_score,
                :hook_score, :brand_fit_score, :comment, :status, :reasons, :created_at
            )
            """,
            payload,
        )
        context = _creative_context(conn, creative_id)
        knowledge_item = _knowledge_from_rating(payload, context)
        conn.execute(
            _knowledge_insert_sql(),
            knowledge_item,
        )
    return {
        "status": "saved",
        "rating": payload,
        "knowledge_item": _public_knowledge_item(knowledge_item),
        "learning_signal": _learning_signal(knowledge_item),
        "db_path": str(db_path),
    }


def import_performance(record: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    creative_id = str(record.get("creative_id") or "").strip()
    if not creative_id:
        raise ValueError("creative_id is required")
    now = _now()
    payload = {
        "performance_id": _hash_id("perf", [creative_id, now, record.get("date_range")]),
        "creative_id": creative_id,
        "ctr": _number(record.get("CTR", record.get("ctr"))),
        "cpc": _number(record.get("CPC", record.get("cpc"))),
        "cpa": _number(record.get("CPA", record.get("cpa"))),
        "roas": _number(record.get("ROAS", record.get("roas"))),
        "spend": _number(record.get("spend")),
        "impressions": _int_or_none(record.get("impressions")),
        "clicks": _int_or_none(record.get("clicks")),
        "conversions": _int_or_none(record.get("conversions")),
        "platform": str(record.get("platform") or ""),
        "date_range": str(record.get("date_range") or ""),
        "created_at": now,
    }
    with _connect(db_path) as conn:
        exists = conn.execute(
            "SELECT creative_id FROM creatives WHERE creative_id = ?",
            (creative_id,),
        ).fetchone()
        if not exists:
            raise ValueError(f"Unknown creative_id: {creative_id}")
        conn.execute(
            """
            INSERT INTO performance (
                performance_id, creative_id, ctr, cpc, cpa, roas, spend, impressions,
                clicks, conversions, platform, date_range, created_at
            ) VALUES (
                :performance_id, :creative_id, :ctr, :cpc, :cpa, :roas, :spend,
                :impressions, :clicks, :conversions, :platform, :date_range, :created_at
            )
            """,
            payload,
        )
        context = _creative_context(conn, creative_id)
        knowledge_item = _knowledge_from_performance(payload, context)
        conn.execute(
            _knowledge_insert_sql(),
            knowledge_item,
        )
    return {
        "status": "saved",
        "performance": payload,
        "knowledge_item": _public_knowledge_item(knowledge_item),
        "learning_signal": _learning_signal(knowledge_item),
        "db_path": str(db_path),
    }


def import_performance_batch(payload: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    saved = []
    learning_signals = []
    errors = []
    for index, record in enumerate(records):
        try:
            result = import_performance(record, path=path)
            saved.append(result.get("performance"))
            learning_signals.append(result.get("learning_signal"))
        except ValueError as exc:
            errors.append({"index": index, "error": str(exc), "creative_id": record.get("creative_id")})
    return {
        "status": "partial" if errors else "saved",
        "saved_count": len(saved),
        "error_count": len(errors),
        "saved": saved,
        "learning_signals": [signal for signal in learning_signals if signal],
        "errors": errors,
    }


def list_creatives(
    *,
    limit: int = 50,
    product_id: str = "",
    campaign_id: str = "",
    workspace: str = "",
    path: str | Path | None = None,
) -> dict[str, Any]:
    db_path = init_db(path)
    clauses = []
    params: list[Any] = []
    if product_id:
        clauses.append("p.product_id = ?")
        params.append(product_id)
    if campaign_id:
        clauses.append("ca.campaign_id = ?")
        params.append(campaign_id)
    normalized_workspace = _workspace_filter(workspace)
    if normalized_workspace:
        clauses.append("lower(COALESCE(ca.workspace, 'ecommerce')) = ?")
        params.append(normalized_workspace)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(max(1, min(int(limit or 50), 200)))
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT c.creative_id, c.set_id, c.type, c.angle, c.status, c.asset_url,
                   c.model_used, c.generation_cost, c.created_at,
                   ca.campaign_id, ca.platform, ca.market, ca.workspace, ca.app_mode, ca.session_folder, ca.creative_strategy,
                   p.product_id, p.product_name, p.category,
                   (
                     SELECT r.status
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_rating_status,
                   (
                     SELECT r.user_rating
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_user_rating,
                   (
                     SELECT r.created_at
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_rating_at,
                   (
                     SELECT COUNT(*)
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                   ) AS rating_count,
                   (
                     SELECT COUNT(*)
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                   ) AS performance_count,
                   (
                     SELECT pf.ctr
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_ctr,
                   (
                     SELECT pf.cpc
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_cpc,
                   (
                     SELECT pf.cpa
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_cpa,
                   (
                     SELECT pf.roas
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_roas,
                   (
                     SELECT pf.spend
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_spend,
                   (
                     SELECT pf.date_range
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_performance_date_range
            FROM creatives c
            JOIN campaigns ca ON ca.campaign_id = c.campaign_id
            JOIN products p ON p.product_id = ca.product_id
            {where}
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    creative_items = []
    for row in rows:
        item = dict(row)
        avatar = _avatar_from_strategy(item.get("creative_strategy"))
        item["avatar_id"] = avatar.get("id")
        item["avatar_name"] = avatar.get("name")
        item["avatar_image_url"] = avatar.get("image_url")
        item.pop("creative_strategy", None)
        creative_items.append(item)
    return {
        "version": "creative_memory_creative_list_v1",
        "db_path": str(db_path),
        "count": len(rows),
        "creatives": creative_items,
    }


def avatar_statistics(avatars: list[dict[str, Any]], path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    stats = {
        str(avatar.get("id") or ""): {
            "ad_sets_used": 0,
            "creative_count": 0,
            "video_count": 0,
            "static_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "performance_count": 0,
            "rating_values": [],
            "ctr_values": [],
            "roas_values": [],
            "angles": {},
            "categories": {},
            "markets": {},
            "platforms": {},
        }
        for avatar in avatars
    }
    campaign_sets: dict[str, set[str]] = {avatar_id: set() for avatar_id in stats}
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT c.creative_id, c.campaign_id, c.type, c.angle,
                   ca.platform, ca.market, ca.creative_strategy,
                   p.category,
                   (
                     SELECT r.status
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_rating_status,
                   (
                     SELECT r.user_rating
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_user_rating,
                   (
                     SELECT pf.ctr
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_ctr,
                   (
                     SELECT pf.roas
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_roas,
                   (
                     SELECT COUNT(*)
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                   ) AS performance_count
            FROM creatives c
            JOIN campaigns ca ON ca.campaign_id = c.campaign_id
            JOIN products p ON p.product_id = ca.product_id
            ORDER BY c.created_at DESC
            """
        ).fetchall()
    for row in rows:
        avatar = _avatar_from_strategy(row["creative_strategy"])
        avatar_id = str(avatar.get("id") or "")
        if avatar_id not in stats:
            continue
        item = stats[avatar_id]
        item["creative_count"] += 1
        campaign_sets[avatar_id].add(str(row["campaign_id"]))
        if row["type"] == "video":
            item["video_count"] += 1
        else:
            item["static_count"] += 1
        status = str(row["latest_rating_status"] or "")
        if status == "approved":
            item["approved_count"] += 1
        if status == "rejected":
            item["rejected_count"] += 1
        rating = _number(row["latest_user_rating"])
        if rating is not None:
            item["rating_values"].append(rating)
        ctr = _number(row["latest_ctr"])
        if ctr is not None:
            item["ctr_values"].append(ctr)
        roas = _number(row["latest_roas"])
        if roas is not None:
            item["roas_values"].append(roas)
        item["performance_count"] += int(row["performance_count"] or 0)
        _count_dimension(item["angles"], row["angle"])
        _count_dimension(item["categories"], row["category"])
        _count_dimension(item["markets"], row["market"])
        _count_dimension(item["platforms"], row["platform"])

    result = {}
    for avatar_id, item in stats.items():
        item["ad_sets_used"] = len(campaign_sets.get(avatar_id, set()))
        item["avg_rating"] = _avg(item.pop("rating_values"))
        item["avg_ctr"] = _avg(item.pop("ctr_values"))
        item["avg_roas"] = _avg(item.pop("roas_values"))
        item["best_angles"] = _top_dimension(item["angles"])
        item["best_categories"] = _top_dimension(item["categories"])
        item["best_markets"] = _top_dimension(item["markets"])
        item["best_platforms"] = _top_dimension(item["platforms"])
        result[avatar_id] = item
    return {
        "version": "avatar_library_stats_v1",
        "db_path": str(db_path),
        "stats": result,
    }


def intelligence_summary(workspace: str = "", path: str | Path | None = None) -> dict[str, Any]:
    db_path = init_db(path)
    workspace_filter = _workspace_filter(workspace)
    product_where, product_params = _workspace_where("p", workspace_filter)
    campaign_where, campaign_params = _workspace_where("ca", workspace_filter)
    creative_where, creative_params = _workspace_where("c", workspace_filter)
    knowledge_where, knowledge_params = _workspace_where(None, workspace_filter)
    with _connect(db_path) as conn:
        counts = {
            "products": conn.execute(
                f"SELECT COUNT(*) AS count FROM products p {product_where}", product_params
            ).fetchone()["count"],
            "campaigns": conn.execute(
                f"SELECT COUNT(*) AS count FROM campaigns ca {campaign_where}", campaign_params
            ).fetchone()["count"],
            "creatives": conn.execute(
                f"SELECT COUNT(*) AS count FROM creatives c {creative_where}", creative_params
            ).fetchone()["count"],
            "ratings": conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM ratings r
                JOIN creatives c ON c.creative_id = r.creative_id
                {creative_where}
                """,
                creative_params,
            ).fetchone()["count"],
            "performance_records": conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM performance pf
                JOIN creatives c ON c.creative_id = pf.creative_id
                {creative_where}
                """,
                creative_params,
            ).fetchone()["count"],
        }
        best_angles = conn.execute(
            f"""
            SELECT c.angle, COUNT(*) AS count, AVG(r.user_rating) AS avg_rating
            FROM creatives c
            JOIN ratings r ON r.creative_id = c.creative_id
            {_append_where(creative_where, "(r.status = 'approved' OR r.user_rating >= 4)")}
            GROUP BY c.angle
            ORDER BY avg_rating DESC, count DESC
            LIMIT 8
            """,
            creative_params,
        ).fetchall()
        rejected = conn.execute(
            f"""
            SELECT r.comment, r.reasons
            FROM ratings r
            JOIN creatives c ON c.creative_id = r.creative_id
            WHERE r.status = 'rejected'
            {_and_workspace("c", workspace_filter)}
            ORDER BY r.created_at DESC
            LIMIT 12
            """,
            creative_params,
        ).fetchall()
        recent = conn.execute(
            f"""
            SELECT c.creative_id, c.set_id, c.type, c.angle, c.status, p.product_name, ca.platform, p.market, ca.workspace
            FROM creatives c
            JOIN campaigns ca ON ca.campaign_id = c.campaign_id
            JOIN products p ON p.product_id = ca.product_id
            {campaign_where}
            ORDER BY c.created_at DESC
            LIMIT 12
            """,
            campaign_params,
        ).fetchall()
        perf = conn.execute(
            f"""
            SELECT c.creative_id, c.angle, p.ctr, p.cpc, p.cpa, p.roas, p.spend
            FROM performance p
            JOIN creatives c ON c.creative_id = p.creative_id
            {creative_where}
            ORDER BY COALESCE(p.roas, 0) DESC, COALESCE(p.ctr, 0) DESC
            LIMIT 8
            """,
            creative_params,
        ).fetchall()
        knowledge = conn.execute(
            f"""
            SELECT source_type, category, market, platform, workspace, angle, status,
                   substr(content, 1, 900) AS content, tags, score
            FROM knowledge_items
            {knowledge_where}
            ORDER BY score DESC, created_at DESC
            LIMIT 30
            """,
            knowledge_params,
        ).fetchall()
    return {
        "version": SCHEMA_VERSION,
        "db_path": str(db_path),
        "workspace": workspace_filter or "all",
        "counts": counts,
        "learning_loop": _learning_loop_status(counts),
        "best_performing_angles": [dict(row) for row in best_angles],
        "rejected_patterns": _avoid_patterns_from_rows(rejected),
        "best_hooks": _best_hooks_from_knowledge(knowledge),
        "best_avatars": _best_avatars(db_path, workspace=workspace_filter),
        "best_product_categories": _best_categories(db_path, workspace=workspace_filter),
        "market_specific_insights": _market_insights(db_path, workspace=workspace_filter),
        "prompt_recommendations": _summary_recommendations(counts, knowledge),
        "knowledge_base": {
            "status": "active",
            "storage": "sqlite_embedding_pgvector_ready",
            "item_count": len(knowledge),
            "top_items": [dict(row) for row in knowledge[:10]],
        },
        "winning_pattern_extractor": _winning_pattern_extractor_summary(knowledge),
        "prompt_learning_agent": _prompt_learning_agent_summary(counts, knowledge),
        "recent_creatives": [dict(row) for row in recent],
        "performance_leaders": [dict(row) for row in perf],
    }


def _product_payload(
    product: dict[str, Any],
    ugc: dict[str, Any],
    now: str,
    *,
    workspace: str,
    app_mode: str,
) -> dict[str, Any]:
    understanding = product.get("automatic_product_understanding") or {}
    facts = {
        "known_product_facts": product.get("known_product_facts"),
        "user_provided_facts": product.get("user_provided_facts"),
        "safe_benefits": product.get("safe_benefits"),
        "ad_safe_detail_phrases": product.get("ad_safe_detail_phrases"),
    }
    references = [product.get("product_image_path")]
    return {
        "product_name": product.get("product_name") or "Product",
        "category": product.get("likely_product_category"),
        "market": ugc.get("market"),
        "language": ugc.get("language"),
        "workspace": workspace,
        "app_mode": app_mode,
        "product_facts": _json_dumps(facts),
        "reference_images": _json_dumps([item for item in references if item]),
        "target_audience": (
            understanding.get("target_audience")
            or (ugc.get("audience_research") or {}).get("primary_archetype")
            or product.get("suggested_target_audience")
        ),
        "positioning": understanding.get("market_position") or product.get("safest_creative_angle"),
        "created_at": now,
        "updated_at": now,
    }


def _campaign_payload(
    product_id: str,
    final_output: dict[str, Any],
    now: str,
    *,
    workspace: str,
    app_mode: str,
) -> dict[str, Any]:
    ugc = final_output.get("ugc_strategy") or {}
    user_input = final_output.get("user_input") or {}
    avatar = final_output.get("avatar") or {}
    strategy = {
        "hook": ugc.get("hook"),
        "voice_profile": ugc.get("voice_profile"),
        "emotional_angle": ugc.get("emotional_angle"),
        "creative_psychology": ugc.get("creative_psychology"),
        "creative_plan": (final_output.get("ads_creative_set") or {}).get("creative_plan"),
        "rag_guidance": ugc.get("creative_memory_rag"),
        "selected_avatar": {
            "id": avatar.get("id") or user_input.get("avatar_id"),
            "name": avatar.get("name"),
            "style": avatar.get("style"),
            "voice": avatar.get("voice"),
            "image_url": avatar.get("image_url"),
            "wardrobe_policy": avatar.get("wardrobe_policy"),
            "identity_type": avatar.get("identity_type"),
            "use_avatar_image_reference": user_input.get("use_avatar_image_reference"),
        },
    }
    return {
        "product_id": product_id,
        "platform": ugc.get("platform"),
        "market": ugc.get("market"),
        "workspace": workspace,
        "app_mode": app_mode,
        "goal": "paid_social_ugc_ad_set",
        "creative_strategy": _json_dumps(strategy),
        "session_folder": user_input.get("session_folder_name"),
        "created_at": now,
    }


def _creative_rows(
    campaign_id: str,
    final_output: dict[str, Any],
    now: str,
    *,
    workspace: str,
    app_mode: str,
) -> list[dict[str, Any]]:
    prompts = final_output.get("content_prompt_package") or {}
    seedance_payload = final_output.get("seedance_payload") or prompts.get("seedance_payload") or {}
    ads = final_output.get("ads_creative_set") or {}
    static_images = final_output.get("static_image_generation") or {}
    video = final_output.get("video_generation") or {}
    avatar = final_output.get("avatar") or {}
    user_input = final_output.get("user_input") or {}
    avatar_payload = {
        "id": avatar.get("id") or user_input.get("avatar_id"),
        "name": avatar.get("name"),
        "style": avatar.get("style"),
        "voice": avatar.get("voice"),
        "image_url": avatar.get("image_url"),
        "use_avatar_image_reference": user_input.get("use_avatar_image_reference"),
    }
    cost_by_component = _cost_by_component(final_output.get("session_cost_summary") or {})
    rows = [
        {
            "creative_id": _hash_id("cr", [campaign_id, "C1", "video"]),
            "campaign_id": campaign_id,
            "set_id": "C1",
            "type": "video",
            "angle": ((ads.get("ugc_video_ad") or {}).get("angle") or "ugc"),
            "workspace": workspace,
            "app_mode": app_mode,
            "prompt": seedance_payload.get("prompt"),
            "negative_prompt": seedance_payload.get("negative_prompt") or prompts.get("negative_prompt"),
            "model_used": seedance_payload.get("model"),
            "asset_url": video.get("video_url") or video.get("video_path") or video.get("job_id"),
            "generation_cost": cost_by_component.get("Seedance video"),
            "status": video.get("video_generation_status") or "planned",
            "source_payload": _json_dumps(
                {
                    "ugc_video_ad": ads.get("ugc_video_ad"),
                    "avatar": avatar_payload,
                    "submitted_payload": video.get("submitted_payload"),
                    "prompt_audit": final_output.get("prompt_audit"),
                }
            ),
            "created_at": now,
        }
    ]
    asset_by_id = {
        str(asset.get("creative_id")): asset
        for asset in static_images.get("image_assets") or []
        if asset.get("creative_id")
    }
    plans = static_images.get("generation_plan") or []
    if not plans:
        plans = _fallback_static_plan(ads)
    for item in plans:
        creative_key = str(item.get("creative_id") or item.get("set_id") or "static")
        asset = asset_by_id.get(creative_key, {})
        rows.append(
            {
                "creative_id": _hash_id("cr", [campaign_id, creative_key]),
                "campaign_id": campaign_id,
                "set_id": item.get("set_id"),
                "type": item.get("asset_type") or item.get("type") or "static",
                "angle": item.get("angle"),
                "workspace": workspace,
                "app_mode": app_mode,
                "prompt": item.get("prompt") or item.get("prompt_preview") or asset.get("prompt"),
                "negative_prompt": prompts.get("negative_prompt"),
                "model_used": static_images.get("model"),
                "asset_url": asset.get("image_url") or asset.get("image_path"),
                "generation_cost": cost_by_component.get("Static ad images"),
                "status": "generated" if asset else static_images.get("image_generation_status") or "planned",
                "source_payload": _json_dumps({**item, "asset": asset, "avatar": avatar_payload}),
                "created_at": now,
            }
        )
    return rows


def _fallback_static_plan(ads: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in ads.get("static_image_ads") or []:
        result.append(
            {
                "creative_id": item.get("creative_id"),
                "set_id": item.get("set_id"),
                "asset_type": "static_image",
                "angle": item.get("angle"),
                "prompt": item.get("visual_prompt"),
            }
        )
    carousel = ads.get("carousel_ad") or {}
    for card in carousel.get("cards") or []:
        number = card.get("card_number")
        result.append(
            {
                "creative_id": f"{carousel.get('set_id') or 'C5'}_card_{number}",
                "set_id": carousel.get("set_id"),
                "asset_type": "carousel_card",
                "angle": carousel.get("angle"),
                "prompt": card.get("visual_prompt"),
            }
        )
    return result


def _patterns_from_rows(rows: list[sqlite3.Row]) -> list[str]:
    patterns: list[str] = []
    for row in rows:
        payload = _json_loads(row["source_payload"] if "source_payload" in row.keys() else None)
        if row["angle"]:
            patterns.append(f"angle:{row['angle']}")
        if row["type"]:
            patterns.append(f"asset:{row['type']}")
        for key in [
            "overlay_text",
            "headline",
            "layout",
            "concept",
            "set_id",
            "angle_family",
            "angle_multiplier_hook",
            "creative_test_hypothesis",
            "angle_selection_reason",
        ]:
            value = payload.get(key)
            if value:
                patterns.append(str(value))
        prompt = str(row["prompt"] or "")
        for marker in ["mirror shot", "natural window light", "product visible", "outfit", "close-up", "handheld", "British"]:
            if marker.lower() in prompt.lower():
                patterns.append(marker)
    return unique_preserve_order(patterns)[:10]


def _avoid_patterns_from_rows(rows: list[sqlite3.Row]) -> list[str]:
    patterns: list[str] = []
    for row in rows:
        comment = row["comment"] if "comment" in row.keys() else None
        cleaned_comment = _clean_memory_pattern(comment)
        if cleaned_comment:
            patterns.append(cleaned_comment)
        reasons = _json_loads(row["reasons"] if "reasons" in row.keys() else None)
        if isinstance(reasons, list):
            patterns.extend(item for item in (_clean_memory_pattern(reason) for reason in reasons) if item)
    return unique_preserve_order(patterns)[:10]


def _knowledge_insert_sql() -> str:
    return """
        INSERT OR REPLACE INTO knowledge_items (
            item_id, source_type, source_id, product_id, campaign_id, creative_id,
            category, market, platform, workspace, app_mode, angle, status, content, tags, score,
            embedding, embedding_model, embedding_provider, embedding_status, embedding_dimensions, created_at
        ) VALUES (
            :item_id, :source_type, :source_id, :product_id, :campaign_id, :creative_id,
            :category, :market, :platform, :workspace, :app_mode, :angle, :status, :content, :tags, :score,
            :embedding, :embedding_model, :embedding_provider, :embedding_status, :embedding_dimensions, :created_at
        )
    """


def _knowledge_from_generation(
    *,
    product_id: str,
    campaign_id: str,
    product: dict[str, Any],
    ugc: dict[str, Any],
    creative_rows: list[dict[str, Any]],
    now: str,
    workspace: str,
    app_mode: str,
) -> list[dict[str, Any]]:
    rows = []
    for creative in creative_rows:
        content = _knowledge_content(
            [
                f"Generated {creative.get('type')} creative",
                f"set {creative.get('set_id')}",
                f"angle {creative.get('angle')}",
                creative.get("prompt"),
            ]
        )
        tags = _extract_tags(content, creative.get("angle"), creative.get("type"))
        rows.append(
            {
                "item_id": _hash_id("ki", [creative.get("creative_id"), "generated_prompt"]),
                "source_type": "generated_prompt",
                "source_id": str(creative.get("creative_id")),
                "product_id": product_id,
                "campaign_id": campaign_id,
                "creative_id": creative.get("creative_id"),
                "category": product.get("likely_product_category"),
                "market": ugc.get("market"),
                "platform": ugc.get("platform"),
                "workspace": workspace,
                "app_mode": app_mode,
                "angle": creative.get("angle"),
                "status": "generated",
                "content": content,
                "tags": _json_dumps(tags),
                "score": 0.35,
                "created_at": now,
            }
        )
    return _attach_embeddings(rows)


def _knowledge_from_rating(rating: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    score = _rating_score(rating)
    status = str(rating.get("status") or "rated")
    if status == "approved":
        knowledge_status = "approved"
    elif status == "rejected":
        knowledge_status = "rejected"
        score = -abs(score or 0.6)
    else:
        knowledge_status = "rated"
    content = _knowledge_content(
        [
            f"User {status} creative",
            f"rating {rating.get('user_rating')}",
            f"fidelity {rating.get('fidelity_score')}",
            f"realism {rating.get('realism_score')}",
            f"hook {rating.get('hook_score')}",
            f"brand fit {rating.get('brand_fit_score')}",
            rating.get("comment"),
            ", ".join(_json_loads(rating.get("reasons")) or []),
            _source_payload_text(context.get("source_payload")),
            context.get("prompt"),
        ]
    )
    return _with_embedding(
        {
        "item_id": _hash_id("ki", [rating.get("rating_id"), context.get("creative_id")]),
        "source_type": "rating",
        "source_id": rating.get("rating_id"),
        "product_id": context.get("product_id"),
        "campaign_id": context.get("campaign_id"),
        "creative_id": context.get("creative_id"),
        "category": context.get("category"),
        "market": context.get("market"),
        "platform": context.get("platform"),
        "workspace": context.get("workspace") or "ecommerce",
        "app_mode": context.get("app_mode") or "ecommerce",
        "angle": context.get("angle"),
        "status": knowledge_status,
        "content": content,
        "tags": _json_dumps(_extract_tags(content, context.get("angle"), context.get("type"))),
        "score": score,
        "created_at": rating.get("created_at") or _now(),
        }
    )


def _knowledge_from_performance(performance: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    ctr = _number(performance.get("ctr"))
    roas = _number(performance.get("roas"))
    cpa = _number(performance.get("cpa"))
    status = "performance_winner" if (roas is not None and roas >= 2) or (ctr is not None and ctr >= 1.5) else "performance_observed"
    if cpa is not None and roas is not None and roas < 1:
        status = "performance_loser"
    score = _performance_score(ctr=ctr, roas=roas, cpa=cpa)
    content = _knowledge_content(
        [
            f"Performance {status}",
            f"CTR {ctr}",
            f"CPC {performance.get('cpc')}",
            f"CPA {cpa}",
            f"ROAS {roas}",
            f"spend {performance.get('spend')}",
            _source_payload_text(context.get("source_payload")),
            context.get("prompt"),
        ]
    )
    return _with_embedding(
        {
        "item_id": _hash_id("ki", [performance.get("performance_id"), context.get("creative_id")]),
        "source_type": "performance",
        "source_id": performance.get("performance_id"),
        "product_id": context.get("product_id"),
        "campaign_id": context.get("campaign_id"),
        "creative_id": context.get("creative_id"),
        "category": context.get("category"),
        "market": context.get("market"),
        "platform": context.get("platform") or performance.get("platform"),
        "workspace": context.get("workspace") or "ecommerce",
        "app_mode": context.get("app_mode") or "ecommerce",
        "angle": context.get("angle"),
        "status": status,
        "content": content,
        "tags": _json_dumps(_extract_tags(content, context.get("angle"), context.get("type"))),
        "score": score,
        "created_at": performance.get("created_at") or _now(),
        }
    )


def _attach_embeddings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    embeddings = embedding_service.embed_texts([str(row.get("content") or "") for row in rows])
    for row, embedding in zip(rows, embeddings):
        row.update(_embedding_columns(embedding))
    return rows


def _with_embedding(row: dict[str, Any]) -> dict[str, Any]:
    return _attach_embeddings([row])[0]


def _embedding_columns(embedding: dict[str, Any]) -> dict[str, Any]:
    vector = embedding.get("vector") if isinstance(embedding, dict) else []
    return {
        "embedding": _json_dumps(vector if isinstance(vector, list) else []),
        "embedding_model": embedding.get("model") if isinstance(embedding, dict) else embedding_service.FALLBACK_MODEL,
        "embedding_provider": embedding.get("provider") if isinstance(embedding, dict) else embedding_service.FALLBACK_PROVIDER,
        "embedding_status": embedding.get("status") if isinstance(embedding, dict) else "fallback",
        "embedding_dimensions": embedding.get("dimensions") if isinstance(embedding, dict) else 0,
    }


def _public_knowledge_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": item.get("item_id"),
        "source_type": item.get("source_type"),
        "creative_id": item.get("creative_id"),
        "workspace": item.get("workspace"),
        "app_mode": item.get("app_mode"),
        "category": item.get("category"),
        "market": item.get("market"),
        "platform": item.get("platform"),
        "angle": item.get("angle"),
        "status": item.get("status"),
        "score": item.get("score"),
        "content": item.get("content"),
        "tags": _json_loads(item.get("tags")) if isinstance(item.get("tags"), str) else item.get("tags"),
        "embedding_model": item.get("embedding_model"),
        "embedding_provider": item.get("embedding_provider"),
        "embedding_status": item.get("embedding_status"),
        "embedding_dimensions": item.get("embedding_dimensions"),
    }


def _learning_signal(item: dict[str, Any]) -> dict[str, Any]:
    status = str(item.get("status") or "")
    tags = _json_loads(item.get("tags")) if isinstance(item.get("tags"), str) else item.get("tags") or []
    if status in {"approved", "performance_winner"}:
        direction = "prefer"
        prompt_effect = "Use this as positive prompt bias for similar workspace/category/market/platform."
    elif status in {"rejected", "performance_loser"}:
        direction = "avoid"
        prompt_effect = "Use this as negative prompt guidance for similar workspace/category/market/platform."
    else:
        direction = "observe"
        prompt_effect = "Store as weak evidence until more ratings or performance records confirm the pattern."
    return {
        "direction": direction,
        "status": status,
        "workspace": item.get("workspace"),
        "category": item.get("category"),
        "market": item.get("market"),
        "platform": item.get("platform"),
        "angle": item.get("angle"),
        "score": item.get("score"),
        "tags": tags,
        "embedding_model": item.get("embedding_model"),
        "embedding_provider": item.get("embedding_provider"),
        "embedding_status": item.get("embedding_status"),
        "prompt_effect": prompt_effect,
    }


def _creative_context(conn: sqlite3.Connection, creative_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT c.creative_id, c.campaign_id, c.type, c.angle, c.prompt, c.source_payload,
               ca.product_id, ca.platform, ca.workspace, ca.app_mode, p.category, p.market
        FROM creatives c
        JOIN campaigns ca ON ca.campaign_id = c.campaign_id
        JOIN products p ON p.product_id = ca.product_id
        WHERE c.creative_id = ?
        """,
        (creative_id,),
    ).fetchone()
    return dict(row) if row else {"creative_id": creative_id}


def _source_payload_text(value: Any) -> str:
    payload = _json_loads(value)
    if not isinstance(payload, dict):
        return ""
    parts = []
    for key in ["angle_family", "angle_multiplier_hook", "creative_test_hypothesis", "angle_selection_reason"]:
        if payload.get(key):
            parts.append(str(payload.get(key)))
    return _knowledge_content(parts)


def _knowledge_patterns(rows: list[sqlite3.Row], statuses: set[str]) -> list[str]:
    patterns: list[str] = []
    for row in rows:
        status = str(row["status"] or "")
        if status not in statuses:
            continue
        tags = _json_loads(row["tags"])
        if isinstance(tags, list):
            patterns.extend(tag for tag in (_clean_memory_pattern(tag) for tag in tags) if tag)
        if row["angle"]:
            angle = _clean_memory_pattern(row["angle"])
            if angle:
                patterns.append(f"angle:{angle}")
    return unique_preserve_order(patterns)


def _learning_layer_from_knowledge(
    *,
    knowledge: list[sqlite3.Row],
    winning_patterns: list[str],
    avoid_patterns: list[str],
) -> dict[str, Any]:
    winners = [dict(row) for row in knowledge if str(row["status"] or "") in {"approved", "performance_winner"}]
    rejected = [dict(row) for row in knowledge if str(row["status"] or "") in {"rejected", "performance_loser"}]
    confidence = "low"
    if len(winners) >= 5 and len(rejected) >= 2:
        confidence = "medium"
    if len(winners) >= 12 and len(rejected) >= 5:
        confidence = "high"
    return {
        "agent": "Prompt Learning Agent",
        "confidence": confidence,
        "winner_count": len(winners),
        "rejected_count": len(rejected),
        "best_historical_creatives": [
            {
                "creative_id": row.get("creative_id"),
                "angle": row.get("angle"),
                "status": row.get("status"),
                "score": row.get("score"),
                "tags": _json_loads(row.get("tags")),
            }
            for row in winners[:8]
        ],
        "worst_historical_creatives": [
            {
                "creative_id": row.get("creative_id"),
                "angle": row.get("angle"),
                "status": row.get("status"),
                "score": row.get("score"),
                "tags": _json_loads(row.get("tags")),
            }
            for row in rejected[:8]
        ],
        "winning_patterns": winning_patterns,
        "avoid_patterns": avoid_patterns,
        "rule": "Use winners as bias, not a copy source. Preserve product facts and safety rules over memory.",
    }


def _prompt_guidance(
    winning_patterns: list[str],
    avoid_patterns: list[str],
    learning_layer: dict[str, Any] | None = None,
) -> str:
    winning_patterns = [item for item in (_clean_memory_pattern(pattern) for pattern in winning_patterns) if item]
    avoid_patterns = [item for item in (_clean_memory_pattern(pattern) for pattern in avoid_patterns) if item]
    if not winning_patterns and not avoid_patterns:
        return "No historical winners yet; use category presets, diversify hooks and shots, and store user ratings after review."
    parts = []
    if winning_patterns:
        parts.append("Prefer historical winners: " + ", ".join(winning_patterns[:6]))
    if avoid_patterns:
        parts.append("Avoid rejected patterns: " + ", ".join(avoid_patterns[:6]))
    if learning_layer:
        parts.append(f"Memory confidence: {learning_layer.get('confidence')}")
    return ". ".join(parts)


def _workspace_where(alias: str | None, workspace: str) -> tuple[str, list[Any]]:
    if not workspace:
        return "", []
    prefix = f"{alias}." if alias else ""
    return f"WHERE lower(COALESCE({prefix}workspace, 'ecommerce')) = ?", [workspace]


def _append_where(where: str, condition: str) -> str:
    if where:
        return f"{where} AND {condition}"
    return f"WHERE {condition}"


def _and_workspace(alias: str, workspace: str) -> str:
    if not workspace:
        return ""
    return f"AND lower(COALESCE({alias}.workspace, 'ecommerce')) = ?"


def _best_categories(db_path: Path, workspace: str = "") -> list[dict[str, Any]]:
    where, params = _workspace_where("p", workspace)
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT p.category, COUNT(*) AS creative_count, AVG(r.user_rating) AS avg_rating
            FROM products p
            JOIN campaigns ca ON ca.product_id = p.product_id
            JOIN creatives c ON c.campaign_id = ca.campaign_id
            LEFT JOIN ratings r ON r.creative_id = c.creative_id
            {where}
            GROUP BY p.category
            ORDER BY creative_count DESC, avg_rating DESC
            LIMIT 8
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _market_insights(db_path: Path, workspace: str = "") -> list[dict[str, Any]]:
    where, params = _workspace_where("ca", workspace)
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT p.market, ca.platform, COUNT(*) AS creative_count, AVG(r.user_rating) AS avg_rating
            FROM products p
            JOIN campaigns ca ON ca.product_id = p.product_id
            JOIN creatives c ON c.campaign_id = ca.campaign_id
            LEFT JOIN ratings r ON r.creative_id = c.creative_id
            {where}
            GROUP BY p.market, ca.platform
            ORDER BY creative_count DESC
            LIMIT 8
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _best_avatars(db_path: Path, workspace: str = "") -> list[dict[str, Any]]:
    where, params = _workspace_where("c", workspace)
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT c.creative_id, ca.campaign_id, ca.creative_strategy,
                   (
                     SELECT r.user_rating
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_user_rating,
                   (
                     SELECT r.status
                     FROM ratings r
                     WHERE r.creative_id = c.creative_id
                     ORDER BY r.created_at DESC
                     LIMIT 1
                   ) AS latest_rating_status,
                   (
                     SELECT pf.ctr
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_ctr,
                   (
                     SELECT pf.roas
                     FROM performance pf
                     WHERE pf.creative_id = c.creative_id
                     ORDER BY pf.created_at DESC
                     LIMIT 1
                   ) AS latest_roas
            FROM creatives c
            JOIN campaigns ca ON ca.campaign_id = c.campaign_id
            {where}
            ORDER BY c.created_at DESC
            LIMIT 1000
            """,
            params,
        ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        avatar = _avatar_from_strategy(row["creative_strategy"])
        avatar_id = str(avatar.get("id") or "")
        if not avatar_id:
            continue
        item = grouped.setdefault(
            avatar_id,
            {
                "avatar_id": avatar_id,
                "avatar_name": avatar.get("name") or avatar_id,
                "creative_count": 0,
                "campaign_ids": set(),
                "approved_count": 0,
                "rating_values": [],
                "ctr_values": [],
                "roas_values": [],
            },
        )
        item["creative_count"] += 1
        item["campaign_ids"].add(row["campaign_id"])
        if row["latest_rating_status"] == "approved":
            item["approved_count"] += 1
        rating = _number(row["latest_user_rating"])
        if rating is not None:
            item["rating_values"].append(rating)
        ctr = _number(row["latest_ctr"])
        if ctr is not None:
            item["ctr_values"].append(ctr)
        roas = _number(row["latest_roas"])
        if roas is not None:
            item["roas_values"].append(roas)
    result = []
    for item in grouped.values():
        avg_rating = _avg(item.pop("rating_values"))
        avg_ctr = _avg(item.pop("ctr_values"))
        avg_roas = _avg(item.pop("roas_values"))
        campaign_ids = item.pop("campaign_ids")
        score = (avg_rating or 0) + min((avg_ctr or 0) / 2, 2) + min((avg_roas or 0), 3) + item["approved_count"] * 0.1
        result.append(
            {
                **item,
                "ad_sets_used": len(campaign_ids),
                "avg_rating": avg_rating,
                "avg_ctr": avg_ctr,
                "avg_roas": avg_roas,
                "score": round(score, 3),
            }
        )
    return sorted(result, key=lambda item: (-item["score"], -item["creative_count"], item["avatar_name"]))[:8]


def _summary_recommendations(counts: dict[str, int], knowledge: list[sqlite3.Row]) -> list[str]:
    recommendations = []
    if counts.get("ratings", 0) == 0:
        recommendations.append("Rate generated creatives so the next generation can learn what to prefer or avoid.")
    if counts.get("performance_records", 0) == 0:
        recommendations.append("Import CTR, CPC, CPA, ROAS and spend once ads run to unlock performance-led RAG.")
    if counts.get("creatives", 0) < 10:
        recommendations.append("Generate and rate more creative sets before trusting winner patterns strongly.")
    if knowledge:
        top_tags = _best_hooks_from_knowledge(knowledge)
        if top_tags:
            recommendations.append("Current strongest memory signals: " + ", ".join(top_tags[:5]) + ".")
    return recommendations or ["Use approved creatives and performance leaders as guidance for the next generation."]


def _learning_loop_status(counts: dict[str, int]) -> dict[str, Any]:
    steps = [
        {"step": "Generate creative", "status": "done" if counts.get("creatives", 0) else "waiting"},
        {"step": "User rates creative", "status": "done" if counts.get("ratings", 0) else "waiting"},
        {
            "step": "Performance data imported",
            "status": "done" if counts.get("performance_records", 0) else "waiting",
        },
        {
            "step": "RAG knowledge base updated",
            "status": "done" if counts.get("performance_records", 0) or counts.get("ratings", 0) else "seed",
        },
        {
            "step": "Next generation uses winners",
            "status": "ready" if counts.get("ratings", 0) or counts.get("performance_records", 0) else "needs feedback",
        },
    ]
    return {
        "status": "ready" if steps[-1]["status"] == "ready" else "collecting_feedback",
        "steps": steps,
    }


def _winning_pattern_extractor_summary(knowledge: list[sqlite3.Row]) -> dict[str, Any]:
    approved_tags = []
    rejected_tags = []
    performance_tags = []
    for row in knowledge:
        status = str(row["status"] or "")
        tags = _json_loads(row["tags"])
        if not isinstance(tags, list):
            continue
        if status in {"approved"}:
            approved_tags.extend(str(tag) for tag in tags)
        if status in {"performance_winner"}:
            performance_tags.extend(str(tag) for tag in tags)
        if status in {"rejected", "performance_loser"}:
            rejected_tags.extend(str(tag) for tag in tags)
    return {
        "agent": "Winning Pattern Extractor",
        "approved_patterns": _top_list(approved_tags, 10),
        "performance_patterns": _top_list(performance_tags, 10),
        "rejected_patterns": _top_list(rejected_tags, 10),
        "rule": "Prefer patterns validated by rating and performance; generated-only prompts remain weak evidence.",
    }


def _prompt_learning_agent_summary(counts: dict[str, int], knowledge: list[sqlite3.Row]) -> dict[str, Any]:
    extractor = _winning_pattern_extractor_summary(knowledge)
    confidence = "low"
    if counts.get("ratings", 0) >= 5 and counts.get("performance_records", 0) >= 3:
        confidence = "medium"
    if counts.get("ratings", 0) >= 20 and counts.get("performance_records", 0) >= 10:
        confidence = "high"
    return {
        "agent": "Prompt Learning Agent",
        "confidence": confidence,
        "next_generation_bias": {
            "prefer": unique_preserve_order(
                extractor["performance_patterns"] + extractor["approved_patterns"]
            )[:8],
            "avoid": extractor["rejected_patterns"][:8],
        },
        "recommendation": _prompt_guidance(
            unique_preserve_order(extractor["performance_patterns"] + extractor["approved_patterns"]),
            extractor["rejected_patterns"],
            {"confidence": confidence},
        ),
    }


def _best_hooks_from_knowledge(rows: list[sqlite3.Row]) -> list[str]:
    tags: list[str] = []
    for row in rows:
        if str(row["status"] or "") not in {"approved", "performance_winner"}:
            continue
        parsed = _json_loads(row["tags"])
        if isinstance(parsed, list):
            tags.extend(str(tag) for tag in parsed if tag)
    return _top_list(tags, limit=8)


def _knowledge_content(parts: list[Any]) -> str:
    cleaned = [_clean_memory_text(part) for part in parts]
    return " | ".join(part for part in cleaned if part)[:12000]


def _extract_tags(content: str, angle: Any = None, asset_type: Any = None) -> list[str]:
    text = str(content or "").lower()
    tags = []
    for marker in [
        "natural window light",
        "mirror shot",
        "outfit scale",
        "product visible",
        "close-up",
        "handheld",
        "british",
        "soft hook",
        "minimal overlay",
        "lifestyle",
        "detail zoom",
        "avatar",
        "human",
        "ugc",
    ]:
        if marker in text:
            tags.append(marker)
    if angle:
        tags.append(f"angle:{angle}")
    if asset_type:
        tags.append(f"asset:{asset_type}")
    return unique_preserve_order(tags)[:16]


def _embedding_similarity(
    *,
    query_vector: list[Any],
    fallback_query_vector: list[Any],
    item_vector: Any,
) -> float:
    if isinstance(item_vector, list) and len(item_vector) == len(query_vector):
        return embedding_service.cosine_similarity(query_vector, item_vector)
    if isinstance(item_vector, list) and len(item_vector) == len(fallback_query_vector):
        return round(embedding_service.cosine_similarity(fallback_query_vector, item_vector) * 0.6, 4)
    return 0.0


def _rating_score(rating: dict[str, Any]) -> float:
    values = [
        _number(rating.get("user_rating")),
        _number(rating.get("fidelity_score")),
        _number(rating.get("realism_score")),
        _number(rating.get("hook_score")),
        _number(rating.get("brand_fit_score")),
    ]
    known = [value for value in values if value is not None]
    if not known:
        return 0.5
    return round(sum(known) / (len(known) * 5), 3)


def _performance_score(*, ctr: float | None, roas: float | None, cpa: float | None) -> float:
    score = 0.4
    if ctr is not None:
        score += min(0.25, ctr / 10)
    if roas is not None:
        score += min(0.35, roas / 10)
    if cpa is not None and cpa > 0:
        score -= min(0.2, cpa / 100)
    return round(max(-1.0, min(1.0, score)), 3)


def _top_list(values: list[str], limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        clean = str(value or "").strip()
        if clean:
            counts[clean] = counts.get(clean, 0) + 1
    return [value for value, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _avatar_from_strategy(value: Any) -> dict[str, Any]:
    strategy = _json_loads(value)
    if isinstance(strategy, dict):
        avatar = strategy.get("selected_avatar")
        if isinstance(avatar, dict):
            return avatar
    return {}


def _count_dimension(target: dict[str, int], value: Any) -> None:
    key = str(value or "").strip()
    if key:
        target[key] = target.get(key, 0) + 1


def _top_dimension(values: dict[str, int], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _cost_by_component(cost_summary: dict[str, Any]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for component in cost_summary.get("components") or []:
        result[str(component.get("component"))] = _number(component.get("cost"))
    return result


def _product_id(product: dict[str, Any], ugc: dict[str, Any]) -> str:
    return _hash_id(
        "prd",
        [
            product.get("product_name"),
            product.get("likely_product_category"),
            ugc.get("market"),
            ugc.get("language"),
        ],
    )


def _workspace_from_input(values: dict[str, Any]) -> str:
    return _workspace_filter(
        values.get("workspace") or values.get("session_workspace") or values.get("app_mode")
    ) or "ecommerce"


def _workspace_filter(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"finance", "finance_personal_brand"}:
        return "finance"
    if normalized == "ecommerce":
        return "ecommerce"
    return ""


def _campaign_id(user_input: dict[str, Any], product_id: str) -> str:
    return _hash_id("cmp", [product_id, user_input.get("session_folder_name"), time.time_ns()])


def _hash_id(prefix: str, values: list[Any]) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    readable = safe_slug(str(values[0] or prefix), fallback=prefix)[:24]
    return f"{prefix}_{readable}_{digest}"


def _connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(path))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: Any) -> Any:
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


_GENERIC_MEMORY_PATTERNS = {
    "approved",
    "generated",
    "rated",
    "rejected",
    "performance_observed",
}


def _clean_reason_list(value: Any) -> list[str]:
    items = value if isinstance(value, list) else [value]
    return [item for item in (_clean_memory_pattern(reason) for reason in items) if item]


def _clean_memory_pattern(value: Any) -> str:
    text = _clean_memory_text(value)
    if text.lower() in _GENERIC_MEMORY_PATTERNS:
        return ""
    return text


def _clean_memory_text(value: Any) -> str:
    text = _repair_mojibake(str(value or ""))
    return " ".join(text.replace("\r", "\n").split()).strip(" -|,.;:")


def _repair_mojibake(value: str) -> str:
    text = str(value or "")
    if not _has_mojibake_markers(text):
        return text
    best = text
    best_score = _mojibake_score(text)
    for encoding in ("latin1", "cp1250"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except Exception:
            continue
        score = _mojibake_score(repaired)
        if score < best_score:
            best = repaired
            best_score = score
    return best


def _has_mojibake_markers(value: str) -> bool:
    return any(marker in value for marker in ["Ã", "Ä", "Å", "Ă", "ˇ", "�"])


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in ["Ã", "Ä", "Å", "Ă", "ˇ", "�"])


def _number(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in ("", None):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _score_or_none(value: Any) -> int | None:
    score = _int_or_none(value)
    if score is None:
        return None
    if score < 1 or score > 5:
        raise ValueError("Rating scores must be between 1 and 5")
    return score
