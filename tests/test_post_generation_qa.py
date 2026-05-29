from __future__ import annotations

from app.services import post_generation_qa


def _base_kwargs(tmp_path):
    video = tmp_path / "ugc.mp4"
    video.write_bytes(b"ftypmp42....vide")
    return {
        "product_analysis": {"likely_product_category": "apparel"},
        "ugc_strategy": {
            "language": "en",
            "voiceover": "This is the approved spoken script.",
            "scene_by_scene_script": [],
            "on_screen_text": ["First hook"],
            "subtitles": ["First hook"],
        },
        "content_prompt_package": {
            "speech_language_contract": {"spoken_language": "en-GB"},
            "product_fidelity_instruction": "Product not modified, strict visual reference.",
            "structured_prompt_v2": {"scenes": [{"on_screen_text": "First hook"}]},
        },
        "static_image_generation": {"image_generation_status": "skipped"},
        "video_generation": {
            "video_generation_status": "completed",
            "video_path": str(video),
            "video_url": "/output/ugc.mp4",
        },
        "ads_creative_set": {},
        "finance_mode": False,
        "should_generate_video": True,
        "should_generate_static_images": False,
    }


def test_post_generation_qa_fails_completed_video_without_audio(tmp_path, monkeypatch):
    kwargs = _base_kwargs(tmp_path)
    monkeypatch.setattr(post_generation_qa, "_video_has_audio_track", lambda path: False)
    monkeypatch.setattr(
        post_generation_qa,
        "_sampled_frame_text_probe",
        lambda path, package, finance_mode: {"ocr_text_risk": False, "ocr_text_samples": [], "warnings": []},
    )

    result = post_generation_qa.evaluate(**kwargs)

    check = next(item for item in result["checks"] if item["id"] == "video_content_quality")
    assert result["status"] == "failed"
    assert check["status"] == "failed"
    assert "No audio track" in check["details"]["failures"][0]


def test_post_generation_qa_flags_ocr_text_risk(tmp_path, monkeypatch):
    kwargs = _base_kwargs(tmp_path)
    monkeypatch.setattr(post_generation_qa, "_video_has_audio_track", lambda path: True)
    monkeypatch.setattr(
        post_generation_qa,
        "_sampled_frame_text_probe",
        lambda path, package, finance_mode: {
            "ocr_text_risk": True,
            "ocr_text_samples": ["This line should be spoken, not rendered."],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        post_generation_qa,
        "_face_speaking_probe",
        lambda path, audio_present: {"lip_sync_risk": False, "signal": "test", "warnings": []},
    )

    result = post_generation_qa.evaluate(**kwargs)

    check = next(item for item in result["checks"] if item["id"] == "video_content_quality")
    assert check["status"] == "failed"
    assert "generated text" in check["details"]["failures"][0]
