from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Any

import requests

from app import config
from app.services.text_utils import safe_slug


TERMINAL_FAILURES = {"failed", "cancelled", "expired"}
SUPPORTED_ASPECT_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3", "21:9", "9:21"}
ASPECT_RATIO_FALLBACKS = {
    "4:5": "9:16",
    "5:4": "1:1",
}


def generate_video(
    seedance_payload: dict[str, Any],
    product_name: str,
    output_dir: str | Path = config.OUTPUT_DIR,
    api_key: str | None = None,
    base_url: str = config.OPENROUTER_BASE_URL,
    timeout_seconds: int = 600,
    poll_interval_seconds: int = 5,
) -> dict[str, Any]:
    key = api_key if api_key is not None else config.OPENROUTER_API_KEY
    if not key:
        return {
            "video_generation_status": "skipped",
            "error": "OPENROUTER_API_KEY is missing; video generation was skipped.",
            "failure_reason": "OpenRouter API key is missing, so video generation was skipped.",
            "next_step": "Add OPENROUTER_API_KEY to .env or paste the key in the UI before generating.",
            "video_path": None,
            "video_url": None,
            "output_dir": str(output_dir),
            "job_id": None,
        }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-OpenRouter-Title": "Multi-Agent UGC Workflow",
    }
    submitted_payload = _api_payload(seedance_payload)
    trace_id = f"video_{int(time.time() * 1000)}"
    product_reference_block = _local_product_reference_block(seedance_payload, submitted_payload)
    _write_trace(
        output_dir,
        {
            "trace_id": trace_id,
            "event": "create_request",
            "url": f"{base_url.rstrip('/')}/videos",
            "model": submitted_payload.get("model"),
            "has_api_key": bool(key),
            "payload_keys": sorted(submitted_payload.keys()),
            "requested_input_reference_count": len(seedance_payload.get("input_references") or []),
            "input_reference_count": len(submitted_payload.get("input_references", [])),
            "dropped_input_reference_count": max(
                0,
                len(seedance_payload.get("input_references") or [])
                - len(submitted_payload.get("input_references", [])),
            ),
            "aspect_ratio": submitted_payload.get("aspect_ratio"),
            "duration": submitted_payload.get("duration"),
            "resolution": submitted_payload.get("resolution"),
            "product_reference_block": product_reference_block,
        },
    )
    if product_reference_block:
        _write_trace(
            output_dir,
            {
                "trace_id": trace_id,
                "event": "create_blocked_local_product_reference",
                "provider_restriction": product_reference_block,
            },
        )
        return {
            "video_generation_status": "blocked",
            "error": "Seedance video generation was blocked before the provider call because the product image reference is local-only.",
            "failure_reason": (
                "The exact product image was uploaded locally, but this Seedance/OpenRouter video path can only send "
                "public HTTP(S) image references. Without that public product reference, the video model would improvise "
                "a generic product."
            ),
            "next_step": (
                "Paste a direct public HTTPS product image URL into Product reference URL, or generate static images only "
                "until CDN upload is configured."
            ),
            "video_path": None,
            "video_url": None,
            "output_dir": str(output_dir),
            "job_id": None,
            "submitted_payload": submitted_payload,
            "provider_restriction": product_reference_block,
        }
    try:
        create_response = requests.post(
            f"{base_url.rstrip('/')}/videos",
            json=submitted_payload,
            headers=headers,
            timeout=60,
        )
        create_response.raise_for_status()
        job = create_response.json()
        _write_trace(
            output_dir,
            {
                "trace_id": trace_id,
                "event": "create_response",
                "status_code": create_response.status_code,
                "response": _redact_trace_value(job),
            },
        )
    except Exception as exc:
        error_text = _format_request_error(exc)
        restriction = _provider_restriction(error_text, seedance_payload, submitted_payload)
        _write_trace(
            output_dir,
            {
                "trace_id": trace_id,
                "event": "create_exception",
                "error": error_text,
                "provider_restriction": restriction,
            },
        )
        return {
            "video_generation_status": "failed",
            "error": error_text,
            "failure_reason": _human_failure_reason(error_text),
            "next_step": _next_step_for_error(error_text),
            "video_path": None,
            "video_url": None,
            "output_dir": str(output_dir),
            "job_id": None,
            "submitted_payload": submitted_payload,
            "provider_restriction": restriction,
        }
    job_id = job.get("id")
    polling_url = job.get("polling_url")
    if not job_id or not polling_url:
        _write_trace(
            output_dir,
            {
                "trace_id": trace_id,
                "event": "create_missing_job_fields",
                "response": _redact_trace_value(job),
            },
        )
        return {
            "video_generation_status": "failed",
            "error": "OpenRouter response did not include id and polling_url.",
            "failure_reason": _job_error(job, "failed") if job.get("error") else "OpenRouter did not return a video job id.",
            "next_step": _next_step_for_error(str(job.get("error") or job)),
            "video_path": None,
            "video_url": None,
            "output_dir": str(output_dir),
            "raw_response": job,
            "job_id": None,
            "submitted_payload": submitted_payload,
            "provider_restriction": _provider_restriction(str(job.get("error") or job), seedance_payload, submitted_payload),
        }

    deadline = time.time() + timeout_seconds
    final_job = job
    while time.time() < deadline:
        try:
            poll_response = requests.get(_absolute_url(polling_url, base_url), headers=headers, timeout=60)
            poll_response.raise_for_status()
            final_job = poll_response.json()
            _write_trace(
                output_dir,
                {
                    "trace_id": trace_id,
                    "event": "poll_response",
                    "job_id": job_id,
                    "status_code": poll_response.status_code,
                    "job_status": final_job.get("status"),
                    "error": final_job.get("error"),
                },
            )
        except Exception as exc:
            error_text = _format_request_error(exc)
            return {
                "video_generation_status": "failed",
                "error": error_text,
                "failure_reason": _human_failure_reason(error_text),
                "next_step": _next_step_for_error(error_text),
                "video_path": None,
                "video_url": None,
                "output_dir": str(output_dir),
                "raw_response": final_job,
                "job_id": job_id,
                "submitted_payload": submitted_payload,
                "provider_restriction": _provider_restriction(error_text, seedance_payload, submitted_payload),
            }
        status = str(final_job.get("status", "")).lower()
        if status == "completed":
            break
        if status in TERMINAL_FAILURES:
            error_text = _job_error(final_job, status)
            return {
                "video_generation_status": "failed",
                "error": error_text,
                "failure_reason": _human_failure_reason(error_text),
                "next_step": _next_step_for_error(error_text),
                "video_path": None,
                "video_url": None,
                "output_dir": str(output_dir),
                "raw_response": final_job,
                "job_id": job_id,
                "submitted_payload": submitted_payload,
                "provider_restriction": _provider_restriction(error_text, seedance_payload, submitted_payload),
            }
        time.sleep(poll_interval_seconds)
    else:
        return {
            "video_generation_status": "failed",
            "error": "OpenRouter video generation timed out.",
            "failure_reason": "OpenRouter video job did not complete before the local timeout.",
            "next_step": "Check OpenRouter video logs for the job id, or retry with shorter duration/lower resolution.",
            "video_path": None,
            "video_url": None,
            "output_dir": str(output_dir),
            "raw_response": final_job,
            "job_id": job_id,
            "submitted_payload": submitted_payload,
        }

    generation_metadata = None
    try:
        generation_metadata = _fetch_generation_metadata(
            final_job.get("generation_id") or job.get("generation_id"),
            base_url,
            headers,
        )
        video_url = _first_video_url(final_job)
        video_bytes = _download_video(video_url, job_id, base_url, headers)
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_slug(product_name)}_{safe_slug(str(job_id), 'job')}.mp4"
        video_path = target_dir / filename
        video_path.write_bytes(video_bytes)
    except Exception as exc:
        error_text = _format_request_error(exc)
        return {
            "video_generation_status": "failed",
            "error": error_text,
            "failure_reason": _human_failure_reason(error_text),
            "next_step": _next_step_for_error(error_text),
            "video_path": None,
            "video_url": None,
            "output_dir": str(output_dir),
            "job_id": job_id,
            "raw_response": final_job,
            "generation_metadata": generation_metadata,
            "submitted_payload": submitted_payload,
            "provider_restriction": _provider_restriction(error_text, seedance_payload, submitted_payload),
        }
    return {
        "video_generation_status": "completed",
        "error": None,
        "failure_reason": None,
        "next_step": None,
        "video_path": str(video_path),
        "video_url": _output_url(video_path),
        "output_dir": str(output_dir),
        "job_id": job_id,
        "raw_response": final_job,
        "generation_metadata": generation_metadata,
        "submitted_payload": submitted_payload,
    }


def _write_trace(output_dir: str | Path, event: dict[str, Any]) -> None:
    try:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        trace_path = target_dir / "openrouter_video_trace.jsonl"
        event = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **event}
        with trace_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _redact_trace_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_trace_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_trace_value(item) for item in value]
    if isinstance(value, str) and value.startswith("data:image/"):
        return "[redacted image data url]"
    return value


def _first_video_url(job: dict[str, Any]) -> str | None:
    for key in ("unsigned_urls", "urls", "video_urls"):
        value = job.get(key)
        if isinstance(value, list) and value:
            return value[0]
    outputs = job.get("outputs") or job.get("data")
    if isinstance(outputs, list):
        for item in outputs:
            if isinstance(item, dict):
                for key in ("url", "unsigned_url", "video_url"):
                    if item.get(key):
                        return item[key]
    return None


def _download_video(
    video_url: str | None,
    job_id: str | None,
    base_url: str,
    headers: dict[str, str],
) -> bytes:
    if video_url:
        request_headers = headers if _should_send_auth(video_url, base_url) else None
        response = requests.get(video_url, headers=request_headers, timeout=180)
    else:
        response = requests.get(
            f"{base_url.rstrip('/')}/videos/{job_id}/content?index=0",
            headers=headers,
            timeout=180,
        )
    response.raise_for_status()
    return response.content


def _fetch_generation_metadata(
    generation_id: str | None,
    base_url: str,
    headers: dict[str, str],
) -> dict[str, Any] | None:
    if not generation_id:
        return None
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/generation?id={generation_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _should_send_auth(url: str, base_url: str) -> bool:
    target_host = urlparse(url).netloc.lower()
    base_host = urlparse(base_url).netloc.lower()
    return target_host == base_host or target_host.endswith(".openrouter.ai")


def _output_url(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(config.OUTPUT_DIR.resolve())
        return f"/output/{relative.as_posix()}"
    except Exception:
        return f"/output/{path.name}"


def _api_payload(seedance_payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "model",
        "prompt",
        "aspect_ratio",
        "duration",
        "resolution",
        "size",
        "frame_images",
        "input_references",
        "generate_audio",
        "seed",
        "callback_url",
        "provider",
    }
    payload = {key: value for key, value in seedance_payload.items() if key in allowed and value}
    if isinstance(payload.get("input_references"), list):
        payload["input_references"] = _public_image_references(payload["input_references"])
        if not payload["input_references"]:
            payload.pop("input_references")
    if isinstance(payload.get("frame_images"), list):
        payload["frame_images"] = _public_image_references(payload["frame_images"])
        if not payload["frame_images"]:
            payload.pop("frame_images")
    ratio = _normalize_aspect_ratio(str(payload.get("aspect_ratio") or ""))
    if ratio:
        payload["aspect_ratio"] = ratio
        if isinstance(payload.get("prompt"), str):
            payload["prompt"] = _replace_unsupported_prompt_ratios(payload["prompt"], ratio)
    return payload


def _normalize_aspect_ratio(value: str) -> str | None:
    ratio = value.strip()
    if not ratio:
        return None
    ratio = ASPECT_RATIO_FALLBACKS.get(ratio, ratio)
    if ratio in SUPPORTED_ASPECT_RATIOS:
        return ratio
    return "9:16"


def _replace_unsupported_prompt_ratios(prompt: str, ratio: str) -> str:
    updated = prompt
    for unsupported in ASPECT_RATIO_FALLBACKS:
        updated = updated.replace(f"{unsupported} aspect ratio", f"{ratio} aspect ratio")
        updated = updated.replace(f"aspect ratio {unsupported}", f"aspect ratio {ratio}")
        updated = updated.replace(f"in {unsupported}", f"in {ratio}")
        updated = updated.replace(f"{unsupported} vertical", f"{ratio} vertical")
    return updated


def _public_image_references(references: list[Any]) -> list[Any]:
    public_refs = []
    for ref in references:
        if not isinstance(ref, dict):
            continue
        image_url = ref.get("image_url")
        url = image_url.get("url") if isinstance(image_url, dict) else None
        if isinstance(url, str) and _is_public_http_url(url):
            public_refs.append(ref)
    return public_refs


def _local_product_reference_block(
    seedance_payload: dict[str, Any],
    submitted_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if seedance_payload.get("creative_mode") == "finance_personal_brand":
        return None
    requested_refs = seedance_payload.get("input_references") or []
    if not isinstance(requested_refs, list) or not requested_refs:
        return None
    product_url = _reference_url(requested_refs[0])
    if not isinstance(product_url, str) or not product_url.startswith("data:image/"):
        return None
    submitted_urls = {
        url
        for ref in (submitted_payload.get("input_references") or [])
        if isinstance((url := _reference_url(ref)), str)
    }
    if product_url in submitted_urls:
        return None
    return {
        "status": "blocked",
        "type": "local_product_reference_not_provider_accessible",
        "likely_trigger": "uploaded_product_image",
        "product_reference_mode": "local_data_url_removed_before_provider_call",
        "requested_input_reference_count": len(requested_refs),
        "submitted_input_reference_count": len(submitted_payload.get("input_references") or []),
        "safe_fallback": "Use a direct public HTTPS product image URL for UGC video, or generate static images only.",
        "can_retry_with_public_product_url": True,
    }


def _reference_url(ref: Any) -> str | None:
    if not isinstance(ref, dict):
        return None
    image_url = ref.get("image_url")
    if not isinstance(image_url, dict):
        return None
    url = image_url.get("url")
    return url if isinstance(url, str) else None


def _is_public_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname not in {"localhost", "127.0.0.1", "::1"}


def _absolute_url(value: str, base_url: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return value
    return urljoin(f"{base_url.rstrip('/')}/", value.lstrip("/"))


def _format_request_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        body = ""
        try:
            body = response.text[:1200]
        except Exception:
            body = ""
        return f"{type(exc).__name__}: HTTP {response.status_code}. {body}".strip()
    return f"{type(exc).__name__}: {exc}"


def _job_error(job: dict[str, Any], status: str) -> str:
    error = job.get("error")
    if isinstance(error, dict):
        return error.get("message") or str(error)
    if error:
        return str(error)
    return f"OpenRouter video job ended with status: {status}"


def _provider_restriction(
    error_text: str,
    seedance_payload: dict[str, Any],
    submitted_payload: dict[str, Any],
) -> dict[str, Any] | None:
    lowered = str(error_text or "").lower()
    sensitive_image = (
        "inputimagesensitivecontentdetected" in lowered
        or "privacyinformation" in lowered
        or "real person" in lowered
        or ("sensitive" in lowered and "image" in lowered)
    )
    if not sensitive_image:
        return None
    avatar_mode = seedance_payload.get("avatar_reference_mode")
    exact_avatar_reference = avatar_mode == "exact_image_input_reference"
    input_count = len(submitted_payload.get("input_references") or [])
    return {
        "status": "restricted",
        "type": "sensitive_or_real_person_image_reference",
        "likely_trigger": "avatar_reference_image" if exact_avatar_reference else "input_image_reference",
        "avatar_reference_mode": avatar_mode,
        "input_reference_count": input_count,
        "provider_message": str(error_text)[:1200],
        "safe_fallback": (
            "Disable exact avatar image reference for this run and use prompt-only avatar consistency, "
            "or use a provider-safe generated/non-photographic authorized avatar reference."
        ),
        "can_retry_without_avatar_reference": exact_avatar_reference,
        "retry_changes": {
            "use_avatar_image_reference": False,
            "avatar_reference_mode": "prompt_only_not_image_input",
            "keep_product_reference": True,
            "keep_avatar_identity_contract_in_prompt": True,
        },
    }


def _is_billing_overdue_error(lowered_error_text: str) -> bool:
    return (
        "accountoverdueerror" in lowered_error_text
        or "overdue balance" in lowered_error_text
        or ("account" in lowered_error_text and "overdue" in lowered_error_text)
    )


def _human_failure_reason(error_text: str) -> str:
    lowered = error_text.lower()
    if _is_billing_overdue_error(lowered):
        return (
            "The selected video provider/model returned AccountOverdueError, even though other OpenRouter "
            "models may still have usable credit on the same key."
        )
    if "inputimagesensitivecontentdetected" in lowered or "real person" in lowered:
        return "Seedance rejected an input image because it may contain a real person or privacy-sensitive content."
    if "unsupportedimageformat" in lowered or "image format is not supported" in lowered:
        return "Seedance rejected the image format. Use a direct JPEG or PNG URL instead of AVIF/WebP/CDN transforms."
    if "invalid ratio" in lowered:
        return "Seedance rejected the aspect ratio."
    if "nameresolutionerror" in lowered or "failed to resolve" in lowered or "getaddrinfo failed" in lowered:
        return "The local machine could not resolve openrouter.ai while polling the video job. This is a network/DNS issue, not an image generation failure."
    if "api key" in lowered:
        return "OpenRouter API key is missing or invalid."
    return error_text


def _next_step_for_error(error_text: str) -> str:
    lowered = error_text.lower()
    if _is_billing_overdue_error(lowered):
        return (
            "If OpenRouter credits are available, switch the video model/provider, for example to google/veo-3.1-fast, "
            "or contact OpenRouter support with the provider request id. Also verify the UI is using the intended API key."
        )
    if "inputimagesensitivecontentdetected" in lowered or "real person" in lowered:
        return "Turn off avatar image reference and keep the avatar in the prompt only, or use a provider-safe AI avatar image."
    if "unsupportedimageformat" in lowered or "image format is not supported" in lowered:
        return "Replace the product/avatar URL with a direct .jpg or .png image URL."
    if "invalid ratio" in lowered:
        return "Use 9:16, 16:9, or 1:1 aspect ratio."
    if "nameresolutionerror" in lowered or "failed to resolve" in lowered or "getaddrinfo failed" in lowered:
        return "Check internet/DNS connectivity and retry video generation. Static images may already be saved in the output section."
    if "api key" in lowered:
        return "Set OPENROUTER_API_KEY or paste a valid key in the UI."
    return "Open the Video generování section and OpenRouter logs for the raw provider response."
