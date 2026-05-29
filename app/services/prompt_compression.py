from __future__ import annotations

import re
from typing import Any


REUSABLE_BLOCKS = {
    "product_lock": "product not modified, not restyled, not recolored, not rebranded",
    "identity_lock": "identity preserved, no facial morphing, no appearance drift",
    "creator_camera": "phone footage, slight handheld sway, off-center framing, natural light",
    "safe_area": "keep face, product, and hands inside platform safe areas; text is post-production only for ecommerce",
}


def compress_prompt(prompt: str, reusable_blocks: dict[str, str] | None = None) -> dict[str, Any]:
    blocks = {**REUSABLE_BLOCKS, **(reusable_blocks or {})}
    original = str(prompt or "")
    deduped = _dedupe_clauses(original)
    compressed = _apply_block_tokens(deduped, blocks)
    compressed = _trim_whitespace(compressed)
    before = len(original)
    after = len(compressed)
    return {
        "version": "prompt_compression_v1",
        "status": "completed",
        "method": "semantic_clause_deduplication_plus_reusable_blocks",
        "chars_before": before,
        "chars_after": after,
        "chars_saved": max(0, before - after),
        "reduction_percent": round(((before - after) / before) * 100, 2) if before else 0,
        "reusable_blocks": blocks,
        "compressed_prompt": compressed,
    }


def _dedupe_clauses(text: str) -> str:
    parts = re.split(r"(?<=[.;|])\s+|,\s+(?=(?:product|identity|no |not |keep |use |scene|avatar|camera|lighting|motion)\b)", text)
    seen = set()
    result = []
    for part in parts:
        cleaned = _trim_whitespace(part).strip(" ,;|")
        if not cleaned:
            continue
        key = re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    separator = ". "
    return separator.join(result)


def _apply_block_tokens(text: str, blocks: dict[str, str]) -> str:
    result = text
    for token, phrase in sorted(blocks.items(), key=lambda item: len(item[1]), reverse=True):
        pattern = re.compile(re.escape(phrase), flags=re.IGNORECASE)
        result = pattern.sub(f"@{token}", result)
    return result


def expand_block_tokens(text: str, blocks: dict[str, str] | None = None) -> str:
    result = str(text or "")
    for token, phrase in {**REUSABLE_BLOCKS, **(blocks or {})}.items():
        result = result.replace(f"@{token}", phrase)
    return result


def _trim_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()
