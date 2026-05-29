from __future__ import annotations

import re
from typing import Any


def build(
    lock: dict[str, Any] | None,
    *,
    avatar: dict[str, Any] | None = None,
    product_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(lock, dict) or not lock.get("enabled"):
        return {"enabled": False}

    raw = _clean(" ".join(str(lock.get(key) or "") for key in ["raw_user_direction", "summary", "compiled_direction"]))
    normalized = _norm(raw)
    avatar_gender = _avatar_gender(avatar or {})
    scenario_gender = _scenario_gender(normalized)
    category = str((product_analysis or {}).get("likely_product_category") or "").strip().lower()

    forbidden_checks: list[dict[str, Any]] = []
    prompt_locks: list[str] = []
    static_locks: list[str] = []
    must_include_any: list[dict[str, Any]] = []
    contract_tags: list[str] = []

    if _mentions_parent_context(normalized):
        must_include_any.append(
            {
                "id": "parent_context",
                "label": "mom/parent routine",
                "terms": ["mom", "mother", "mum", "mama", "parent"],
                "scope": "video",
            }
        )
        static_locks.append("when human context is shown, use the approved adult woman/mom or parent-routine context")
        contract_tags.append("parent_context")

    if _mentions_parent_items(normalized):
        must_include_any.append(
            {
                "id": "parent_items",
                "label": "diapers/wipes/snacks/phone/wallet/keys proof items",
                "terms": ["diaper", "diapers", "wipes", "snacks", "phone", "wallet", "keys"],
                "minimum": 2,
                "scope": "video_or_static_set",
            }
        )
        static_locks.append("show approved proof props beside the product when useful: diapers, wipes, snacks, phone, wallet, keys")
        contract_tags.append("parent_items")

    bag_closed_requested = _contains_any(
        normalized,
        [
            "bag stays closed",
            "bag stay closed",
            "keep the bag closed",
            "taska zustava zavrena",
            "taška zůstává zavřená",
            "neotevirat",
            "neotvirat",
            "neotevírat",
            "do not open or close the zipper",
            "do not open the zipper",
        ],
    )
    no_insert_requested = _contains_any(
        normalized,
        [
            "do not show items being inserted",
            "do not show items inserted",
            "do not put items",
            "do not place items inside",
            "nevkladat",
            "nevkládat",
            "nedavat veci dovnitr",
            "nedávat věci dovnitř",
        ],
    )
    if bag_closed_requested:
        forbidden_checks.extend(
            [
                {
                    "id": "product_action_opening_forbidden",
                    "label": "opening the bag or zipper",
                    "patterns": [
                        r"\b(open|opening|opens|opened|unzip|unzipping|unzipped)\b[^.;]{0,90}\b(zip|zipper|zipped|compartment|main compartment|bag)\b",
                        r"\b(zip|zipper|zipped|compartment|main compartment|bag)\b[^.;]{0,90}\b(open|opening|opens|opened|unzip|unzipping|unzipped)\b",
                        r"\b(show|reveal|revealing|showing)\b[^.;]{0,90}\b(interior|inside|inner compartment|internal compartment)\b",
                    ],
                },
            ]
        )
        prompt_locks.append("Product action lock: keep the bag closed; do not open, unzip, close, or reveal compartments.")
        static_locks.append("keep the bag closed; use exterior scale, carry, strap, silhouette, and beside-the-bag props instead of interior or zipper-opening proof")
        contract_tags.append("bag_closed")

    if no_insert_requested:
        forbidden_checks.append(
            {
                "id": "product_action_insert_forbidden",
                "label": "putting items inside the bag",
                "patterns": [
                    r"\b(insert|inserting|put|putting|place|placing|pack|packing|slide|sliding)\b[^.;]{0,90}\b(in|inside|into)\b[^.;]{0,60}\b(bag|compartment|main compartment|opening)\b",
                    r"\b(items?|phone|keys|wallet|snacks?|wipes|diapers?)\b[^.;]{0,90}\b(in|inside|into)\b[^.;]{0,60}\b(bag|compartment|main compartment|opening)\b",
                ],
            }
        )
        prompt_locks.append("Product action lock: do not show items inserted into the bag; place proof items next to the bag.")
        static_locks.append("place proof items next to the bag, not inside it")
        contract_tags.append("no_insert_items")

    if _contains_any(
        normalized,
        [
            "do not describe this as apparel",
            "do not use try-on",
            "do not use try on",
            "do not show clothing try-on",
            "not apparel",
            "not clothing",
            "nepopisuj jako obleceni",
            "neni to obleceni",
        ],
    ):
        forbidden_checks.append(
            {
                "id": "category_apparel_try_on_forbidden",
                "label": "apparel/try-on framing for a non-apparel scenario",
                "patterns": [
                    r"\bapparel full-body\b",
                    r"\bclothing try[- ]?on\b",
                    r"\btry[- ]?on\b",
                    r"\boutfit check\b",
                    r"\bwearing\b[^.;]{0,80}\b(garment|clothing|apparel)\b",
                    r"\bgarment\b[^.;]{0,80}\b(worn|wearing|fit|drape)\b",
                ],
            }
        )
        prompt_locks.append("Category lock: do not frame this as apparel, clothing try-on, outfit fit, or garment proof.")
        static_locks.append("do not use apparel, clothing try-on, outfit-fit, or garment-proof framing")
        contract_tags.append("not_apparel")

    expected_gender = avatar_gender or scenario_gender
    if expected_gender:
        contract_tags.append(f"gender_{expected_gender}")

    return {
        "enabled": True,
        "version": "scenario_contract_v1",
        "source": lock.get("source") or "user_scenario_lock",
        "raw_user_direction": raw,
        "category": category,
        "subject_gender": expected_gender,
        "scenario_gender": scenario_gender,
        "avatar_gender": avatar_gender,
        "must_include_any": must_include_any,
        "forbidden_checks": forbidden_checks,
        "video_prompt_lock": " ".join(prompt_locks),
        "static_prompt_lock": _static_prompt_lock_text(static_locks),
        "tags": sorted(set(contract_tags)),
    }


def validate_text(
    text: str,
    contract: dict[str, Any],
    *,
    scope: str,
    location: str,
) -> list[dict[str, str]]:
    if not contract.get("enabled"):
        return []
    search_text = _strip_protective_language(_norm(text))
    failures: list[dict[str, str]] = []
    for check in contract.get("forbidden_checks") or []:
        for pattern in check.get("patterns") or []:
            if re.search(pattern, search_text, flags=re.IGNORECASE):
                failures.append(
                    {
                        "id": str(check.get("id") or "scenario_contract_forbidden"),
                        "reason": (
                            f"{location} contains {check.get('label')}, which conflicts with the approved user scenario."
                        ),
                        "next_step": "Rewrite the final prompt to obey the approved scenario contract before provider generation.",
                    }
                )
                break

    if scope in {"video", "video_or_static_set"}:
        for required in contract.get("must_include_any") or []:
            if required.get("scope") not in {"video", "video_or_static_set"}:
                continue
            terms = [str(term).lower() for term in required.get("terms") or [] if str(term).strip()]
            minimum = int(required.get("minimum") or 1)
            count = len([term for term in terms if term in search_text])
            if terms and count < minimum:
                failures.append(
                    {
                        "id": f"scenario_required_{required.get('id')}_missing",
                        "reason": f"{location} lost the required approved scenario detail: {required.get('label')}.",
                        "next_step": "Preserve the approved scenario detail or block provider generation.",
                    }
                )
    return _dedupe_failures(failures)


def validate_static_gender(text: str, contract: dict[str, Any], *, location: str = "Static prompts") -> list[dict[str, str]]:
    expected = str(contract.get("subject_gender") or "")
    if not expected:
        return []
    normalized = _norm(text)
    if expected == "female" and not _contains_any(normalized, ["woman", "female-presenting", "mom", "mother", "mum"]):
        return [
            {
                "id": "static_avatar_gender_missing",
                "reason": f"{location} do not preserve the selected female-presenting avatar gender.",
                "next_step": "Add a static subject lock before image generation.",
            }
        ]
    if expected == "male" and not _contains_any(normalized, ["man", "male-presenting", "father", "dad"]):
        return [
            {
                "id": "static_avatar_gender_missing",
                "reason": f"{location} do not preserve the selected male-presenting avatar gender.",
                "next_step": "Add a static subject lock before image generation.",
            }
        ]
    return []


def remove_conflicting_directives(text: str, contract: dict[str, Any]) -> str:
    if not contract.get("enabled") or not text:
        return str(text or "")
    parts = re.split(r"(?<=[.;])\s+", str(text))
    kept = []
    for part in parts:
        if not part.strip():
            continue
        if validate_text(part, contract, scope="directive", location="Visual classifier directive"):
            continue
        kept.append(part.strip())
    return " ".join(kept)


def rewrite_for_contract(text: str, contract: dict[str, Any]) -> str:
    if not contract.get("enabled") or not text:
        return str(text or "")
    rewritten = str(text)
    tags = set(contract.get("tags") or [])
    if "bag_closed" in tags:
        rewritten = re.sub(r"\bmain compartment\b", "exterior zipper line", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bzippered compartments?\b", "exterior zipper lines", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bcompartments?\b", "exterior zipper lines", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\btop opening\b", "exterior zipper line", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bopening detail\b", "exterior zipper-line detail", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bopening proof\b", "exterior scale proof", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\binterior proof\b", "exterior scale proof", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bvisible interior\b", "visible exterior scale", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\binterior space\b", "outside scale", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\baccess cues\b", "outside scale cues", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bcapacity cues\b", "beside-the-bag scale cues", rewritten, flags=re.IGNORECASE)
    if "no_insert_items" in tags:
        rewritten = re.sub(
            r"\b(place|placing|put|putting|insert|inserting|pack|packing|slide|sliding)\b([^.;]{0,45})\b(in|inside|into)\b",
            r"place\2 beside",
            rewritten,
            flags=re.IGNORECASE,
        )
        rewritten = re.sub(r"\binside the bag\b", "next to the bag", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\binto the bag\b", "next to the bag", rewritten, flags=re.IGNORECASE)
    if "not_apparel" in tags:
        rewritten = re.sub(r"\bapparel full-body\b", "creator product", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bclothing try[- ]?on\b", "product check", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\btry[- ]?on\b", "product check", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\boutfit check\b", "carry check", rewritten, flags=re.IGNORECASE)
        rewritten = re.sub(r"\bgarment proof\b", "product proof", rewritten, flags=re.IGNORECASE)
    return _clean(rewritten)


def filter_conflicting_items(items: Any, contract: dict[str, Any]) -> list[str]:
    if not isinstance(items, list):
        return []
    filtered = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        text = rewrite_for_contract(text, contract)
        if contract.get("enabled") and validate_text(text, contract, scope="directive", location="Visual classifier item"):
            continue
        filtered.append(text)
    return filtered


def static_prompt_lock(contract: dict[str, Any]) -> str:
    return str(contract.get("static_prompt_lock") or "").strip() if contract.get("enabled") else ""


def video_prompt_lock(contract: dict[str, Any]) -> str:
    return str(contract.get("video_prompt_lock") or "").strip() if contract.get("enabled") else ""


def _static_prompt_lock_text(parts: list[str]) -> str:
    if not parts:
        return ""
    return "Static scenario contract: " + "; ".join(dict.fromkeys(part for part in parts if part)) + "."


def _dedupe_failures(failures: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    deduped = []
    for failure in failures:
        key = (failure.get("id"), failure.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(failure)
    return deduped


def _mentions_parent_context(text: str) -> bool:
    return _contains_any(text, ["mom", "mother", "mum", "mama", "parent"])


def _mentions_parent_items(text: str) -> bool:
    return _contains_any(text, ["diaper", "diapers", "wipes", "snacks", "wallet", "keys"])


def _scenario_gender(text: str) -> str:
    if _contains_any(text, ["mom", "mother", "mum", "mama", "woman", "female", "she ", " her "]):
        return "female"
    if _contains_any(text, ["dad", "father", "man", "male", "he ", " him "]):
        return "male"
    return ""


def _avatar_gender(avatar: dict[str, Any]) -> str:
    text = _norm(
        " ".join(
            str(avatar.get(key) or "")
            for key in ["gender", "presenting_gender", "style", "persona", "appearance", "voice", "identity_note", "name"]
        )
    )
    if _contains_any(text, ["female", "woman", "female-presenting", "creatorin", "zena"]):
        return "female"
    if _contains_any(text, ["male", "man", "male-presenting", "muz"]):
        return "male"
    return ""


def _strip_protective_language(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"\bnegative prompt\s*:.*?(?=(\bscene\b|\bshot\b|\bvisual\b|\bproduct instructions\b|$))", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\b(do not|don't|never|avoid|no)\b[^.;]*(?:[.;]|$)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bwithout\b[^.;]*(?:[.;]|$)", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", "\n").split()).strip()


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", text).strip()
