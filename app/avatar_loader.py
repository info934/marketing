from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app import config


DEFAULT_AVATAR = {
    "id": "default_creator",
    "name": "Default Creator",
    "style": "natural creator",
    "appearance": "AI avatar reference image, identity controlled by supplied public image URL",
    "voice": "warm, clear, conversational",
    "image_url": "https://i.ibb.co/6082rzf9/newkoi.png",
}


def load_avatar(avatar_id: str | None, inline_avatar: str | None = None) -> dict[str, Any]:
    if inline_avatar:
        try:
            avatar = json.loads(inline_avatar)
            if isinstance(avatar, dict):
                return _merge_avatar_defaults(avatar)
        except json.JSONDecodeError:
            pass

    avatars = list_avatars()
    requested_id = avatar_id or default_avatar_id()
    if requested_id:
        for avatar in avatars:
            if avatar.get("id") == requested_id:
                return _merge_avatar_defaults(avatar)
    return DEFAULT_AVATAR


def list_avatars() -> list[dict[str, Any]]:
    avatars = _read_avatar_registry(config.AVATAR_DATA_PATH)
    if not avatars:
        return [DEFAULT_AVATAR]
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for avatar in avatars:
        merged = _merge_avatar_defaults(avatar)
        avatar_id = str(merged.get("id") or "").strip() or "default_creator"
        if avatar_id in seen:
            continue
        seen.add(avatar_id)
        merged["id"] = avatar_id
        result.append(merged)
    return result


def default_avatar_id() -> str:
    avatars = list_avatars()
    for avatar in avatars:
        if avatar.get("is_default"):
            return str(avatar.get("id") or DEFAULT_AVATAR["id"])
    return str((avatars[0] if avatars else DEFAULT_AVATAR).get("id") or DEFAULT_AVATAR["id"])


def upsert_avatar(profile: dict[str, Any]) -> dict[str, Any]:
    avatars = list_avatars()
    avatar_id = str(profile.get("id") or "").strip()
    if not avatar_id:
        raise ValueError("Avatar id is required")
    clean = _clean_avatar(profile)
    found = False
    for index, avatar in enumerate(avatars):
        if avatar.get("id") == avatar_id:
            clean["is_default"] = bool(clean.get("is_default") or avatar.get("is_default"))
            avatars[index] = {**avatar, **clean}
            found = True
            break
    if not found:
        avatars.append(clean)
    if clean.get("is_default"):
        avatars = _with_single_default(avatars, avatar_id)
    _write_avatar_registry(config.AVATAR_DATA_PATH, avatars)
    return load_avatar(avatar_id)


def set_default_avatar(avatar_id: str) -> dict[str, Any]:
    avatars = list_avatars()
    if not any(avatar.get("id") == avatar_id for avatar in avatars):
        raise ValueError(f"Unknown avatar_id: {avatar_id}")
    avatars = _with_single_default(avatars, avatar_id)
    _write_avatar_registry(config.AVATAR_DATA_PATH, avatars)
    return load_avatar(avatar_id)


def _read_avatar_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return [DEFAULT_AVATAR]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [DEFAULT_AVATAR]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return [DEFAULT_AVATAR]


def _write_avatar_registry(path: Path, avatars: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(avatars, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge_avatar_defaults(avatar: dict[str, Any]) -> dict[str, Any]:
    merged = {**DEFAULT_AVATAR, **avatar}
    has_own_visual_reference = bool(avatar.get("image_url") or avatar.get("preview_url") or avatar.get("image_path"))
    if has_own_visual_reference and not avatar.get("image_url"):
        merged.pop("image_url", None)
    return merged


def _clean_avatar(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "id",
        "name",
        "style",
        "persona",
        "appearance",
        "voice",
        "gender",
        "presenting_gender",
        "image_path",
        "image_url",
        "preview_url",
        "wardrobe_policy",
        "identity_note",
        "is_default",
    }
    clean = {key: value for key, value in profile.items() if key in allowed and value not in (None, "")}
    clean["id"] = str(clean.get("id") or "").strip()
    clean["name"] = str(clean.get("name") or clean["id"]).strip()
    clean.setdefault("style", "natural UGC creator")
    clean.setdefault("appearance", "AI avatar reference image, identity controlled by supplied public image URL")
    clean.setdefault("voice", "natural conversational creator voice")
    return clean


def _with_single_default(avatars: list[dict[str, Any]], avatar_id: str) -> list[dict[str, Any]]:
    return [{**avatar, "is_default": avatar.get("id") == avatar_id} for avatar in avatars]
