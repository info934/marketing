from __future__ import annotations

from typing import Any

from app.services import marketing_skill_router


ORCHESTRATOR_VERSION = "creative_orchestrator_v1"

PHASES: list[dict[str, Any]] = [
    {
        "id": "brief",
        "title": "Brief",
        "purpose": "Collect the minimum context needed for a strong ad: brand, subject, audience, avatar, references, and output mode.",
        "user_gate": "The agent asks for missing context instead of guessing major facts.",
        "outputs": ["brand_context", "ad_subject", "reference_assets", "campaign_constraints"],
        "specialists": ["brief_parser", "brand_context", "marketing_skill_router"],
    },
    {
        "id": "strategy",
        "title": "Strategy",
        "purpose": "Choose the buyer tension, angle family, hook direction, proof moments, and claim boundaries.",
        "user_gate": "The strategy must be clear enough to explain before any provider generation.",
        "outputs": ["audience_trigger", "angle", "hook", "claim_safety"],
        "specialists": ["audience_strategy", "hook_strategy", "claim_safety"],
    },
    {
        "id": "plan",
        "title": "Creative Plan",
        "purpose": "Create reviewable UGC video scenarios and static ad concepts before generation.",
        "user_gate": "Generation should wait until a plan or scenario is approved.",
        "outputs": ["ugc_video_scenarios", "static_ad_concepts", "approved_direction"],
        "specialists": ["ugc_video_scenarios", "static_ad_concepts", "scenario_integrity"],
    },
    {
        "id": "generate",
        "title": "Generate",
        "purpose": "Send only approved, provider-ready prompts and references to video and image models.",
        "user_gate": "If brand, avatar, scenario, or reference fidelity is weak, block generation and explain why.",
        "outputs": ["video_generation", "static_image_generation", "provider_trace"],
        "specialists": ["provider_validation", "video_generator", "static_image_generator"],
    },
    {
        "id": "review",
        "title": "Review",
        "purpose": "Score the output, explain failures, save learnings, and prepare the next iteration.",
        "user_gate": "Review should produce a simple next action, not another wall of diagnostics.",
        "outputs": ["quality_review", "learning_signal", "next_action"],
        "specialists": ["creative_review", "memory_learning"],
    },
]

SPECIALISTS: list[dict[str, Any]] = [
    {
        "id": "marketing_skill_router",
        "label": "Marketing Skill Router",
        "phase": "brief",
        "role": "Selects the relevant Corey Haines marketing skills and keeps product-marketing context as the foundation.",
        "modules": ["marketing_skill_router", "company_loader"],
        "visible": True,
    },
    {
        "id": "brief_parser",
        "label": "Brief Parser",
        "phase": "brief",
        "role": "Turns chat, URLs, and attachments into a structured ad brief.",
        "modules": ["chat_brief_parser_agent", "product_intake_agent"],
        "visible": False,
    },
    {
        "id": "brand_context",
        "label": "Brand Context",
        "phase": "brief",
        "role": "Applies saved company/brand facts, voice, proof points, and forbidden claims.",
        "modules": ["company_loader", "audience_research_agent"],
        "visible": True,
    },
    {
        "id": "audience_strategy",
        "label": "Audience Strategy",
        "phase": "strategy",
        "role": "Finds the buyer trigger and objection that should drive the ad.",
        "modules": ["audience_research_agent", "creative_psychology_agent", "emotional_angle_engine"],
        "visible": False,
    },
    {
        "id": "hook_strategy",
        "label": "Hook Strategy",
        "phase": "strategy",
        "role": "Creates hook families and decides the first-second promise.",
        "modules": ["ugc_hook_agent", "ad_angle_multiplier", "ad_angle_selector"],
        "visible": True,
    },
    {
        "id": "claim_safety",
        "label": "Claim Safety",
        "phase": "strategy",
        "role": "Keeps claims inside supplied facts and platform-safe language.",
        "modules": ["compliance_guard", "product_fidelity_guard"],
        "visible": True,
    },
    {
        "id": "ugc_video_scenarios",
        "label": "UGC Video Scenarios",
        "phase": "plan",
        "role": "Creates UGC scripts, beats, visual sequence, avatar use, and spoken hook.",
        "modules": ["ugc_agent", "scene_director_agent", "scene_chaining_agent", "content_prompt_engineer_agent"],
        "visible": True,
    },
    {
        "id": "static_ad_concepts",
        "label": "Static Ad Concepts",
        "phase": "plan",
        "role": "Creates distinct static ad angles, visual prompts, copy, carousel concepts, and variations.",
        "modules": ["ads_creative_set_agent", "openrouter_prompt_client"],
        "visible": True,
    },
    {
        "id": "scenario_integrity",
        "label": "Scenario Integrity",
        "phase": "plan",
        "role": "Blocks generation when the provider-ready prompt does not respect the approved scenario.",
        "modules": ["scenario_integrity_guard", "structured_prompt_v2"],
        "visible": True,
    },
    {
        "id": "provider_validation",
        "label": "Provider Validation",
        "phase": "generate",
        "role": "Checks references, model compatibility, image counts, prompt size, and output mode before spending credits.",
        "modules": ["preflight_validator"],
        "visible": True,
    },
    {
        "id": "video_generator",
        "label": "Video Generator",
        "phase": "generate",
        "role": "Generates UGC video only from the approved prompt package and references.",
        "modules": ["openrouter_seedance_client", "finance_video_agent"],
        "visible": True,
    },
    {
        "id": "static_image_generator",
        "label": "Static Image Generator",
        "phase": "generate",
        "role": "Generates static paid-social images from approved static concepts.",
        "modules": ["openrouter_image_client", "vision_quality_client"],
        "visible": True,
    },
    {
        "id": "creative_review",
        "label": "Creative Review",
        "phase": "review",
        "role": "Summarizes creative quality, blockers, and what should change next.",
        "modules": ["post_generation_qa", "creative_self_critique", "workflow_reporter"],
        "visible": True,
    },
    {
        "id": "memory_learning",
        "label": "Memory Learning",
        "phase": "review",
        "role": "Saves useful patterns and ratings for future ad iterations.",
        "modules": ["creative_memory_db", "performance_memory", "creative_memory_learning_service"],
        "visible": False,
    },
]


def schema() -> dict[str, Any]:
    return {
        "version": ORCHESTRATOR_VERSION,
        "name": "AI Creative Orchestrator",
        "marketing_skill_registry": marketing_skill_router.registry(),
        "principles": [
            "one visible pipeline, many internal specialist skills",
            "product-marketing context before specialist creative skills",
            "plan before generate",
            "block weak or misaligned generation instead of spending credits",
            "separate UGC video scenario skills from static ad concept skills",
            "review and learn after every run",
        ],
        "phases": PHASES,
        "specialists": [_with_skill_route(specialist) for specialist in SPECIALISTS],
    }


def snapshot(run: dict[str, Any] | None = None) -> dict[str, Any]:
    current_phase = _current_phase(run)
    terminal_status = str((run or {}).get("status") or "").lower()
    blocked = terminal_status in {"blocked", "failed", "cancelled"}
    phases = []
    for phase in PHASES:
        phase_id = phase["id"]
        phases.append(
            {
                **phase,
                "status": _phase_status(phase_id, current_phase, terminal_status, blocked),
                "specialists": [
                    _with_skill_route(specialist)
                    for specialist in SPECIALISTS
                    if specialist.get("phase") == phase_id and specialist.get("visible")
                ],
            }
        )
    return {
        **schema(),
        "current_phase": current_phase,
        "run_id": (run or {}).get("run_id"),
        "run_status": (run or {}).get("status") or "idle",
        "phases": phases,
        "next_action": _next_action(run, current_phase),
    }


def _current_phase(run: dict[str, Any] | None) -> str:
    if not run:
        return "brief"
    stage = str(run.get("current_stage") or "").lower()
    status = str(run.get("status") or "").lower()
    if status in {"completed", "blocked", "failed", "cancelled"}:
        return "review"
    if stage in {"generating_video", "generating_images"}:
        return "generate"
    if stage in {"prompting", "creative_plan"}:
        return "plan"
    if stage in {"planning", "product_understanding", "visual_product_classifier", "product_understanding_done", "visual_product_classifier_done"}:
        return "strategy"
    if stage in {"submitted", "started", "product_intake", "provider_preflight"}:
        return "brief"
    return "brief"


def _with_skill_route(specialist: dict[str, Any]) -> dict[str, Any]:
    route = marketing_skill_router.route_for_specialist(str(specialist.get("id") or ""))
    return {
        **specialist,
        "marketing_skills": route.get("skills") or [],
        "skill_contract": route.get("contract"),
    }


def _phase_status(phase_id: str, current_phase: str, terminal_status: str, blocked: bool) -> str:
    order = [phase["id"] for phase in PHASES]
    phase_index = order.index(phase_id)
    current_index = order.index(current_phase)
    if blocked and phase_id == current_phase:
        return "blocked"
    if terminal_status == "completed":
        return "done"
    if phase_index < current_index:
        return "done"
    if phase_id == current_phase:
        return "active"
    return "waiting"


def _next_action(run: dict[str, Any] | None, current_phase: str) -> str:
    if not run:
        return "Add a brand and ad brief, then let the orchestrator build a creative plan."
    status = str(run.get("status") or "").lower()
    if status == "completed":
        return "Review the output, rate useful creatives, then create the next iteration."
    if status in {"blocked", "failed"}:
        return _run_problem(run) or "Fix the blocker shown in review before generating again."
    if status == "cancelled":
        return "Start a new agent run when the brief is ready."
    if current_phase == "plan":
        return "Review and approve the creative plan before generation."
    if current_phase == "generate":
        return "Wait for provider generation to finish."
    return "Continue filling the brief and strategy inputs."


def _run_problem(run: dict[str, Any]) -> str:
    monitor = run.get("monitor") if isinstance(run.get("monitor"), dict) else {}
    if monitor.get("terminal_reason"):
        return str(monitor["terminal_reason"])
    final_output = run.get("final_output") if isinstance(run.get("final_output"), dict) else {}
    return str(final_output.get("problem") or final_output.get("failure_reason") or "")
