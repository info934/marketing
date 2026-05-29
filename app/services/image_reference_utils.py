from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


def local_image_to_data_url(path: str | Path | None) -> str | None:
    if not path:
        return None
    image_path = Path(path)
    if not image_path.exists() or not image_path.is_file():
        return None
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def image_url_reference(url: str | None) -> dict[str, object] | None:
    if not url:
        return None
    value = normalize_public_image_url(url.strip())
    if not value:
        return None
    return {"type": "image_url", "image_url": {"url": value}}


def data_url_reference(path: str | Path | None) -> dict[str, object] | None:
    data_url = local_image_to_data_url(path)
    if not data_url:
        return None
    return {"type": "image_url", "image_url": {"url": data_url}}


def normalize_public_image_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return url
    if parsed.netloc.lower() in {"ibb.co", "www.ibb.co"}:
        resolved = _resolve_imgbb_page_url(url)
        if resolved:
            return resolved
    normalized = url.replace("/format/avif", "/format/jpeg")
    normalized = normalized.replace("format=avif", "format=jpeg")
    return normalized


def _resolve_imgbb_page_url(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CreativeAdsApp/1.0)"},
            timeout=8,
        )
        response.raise_for_status()
    except Exception:
        return ""
    html = response.text or ""
    candidates = [
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'<link\s+rel=["\']image_src["\']\s+href=["\']([^"\']+)["\']',
        r'"url"\s*:\s*"((?:https?:)?\\?/\\?/i\.ibb\.co\\?/[^"]+)"',
        r'https://i\.ibb\.co/[^\s"\'<>]+',
    ]
    for pattern in candidates:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1) if match.groups() else match.group(0)
        value = value.replace("\\/", "/")
        if value.startswith("//"):
            value = f"https:{value}"
        if urlparse(value).netloc.lower() == "i.ibb.co":
            return value
    return ""
