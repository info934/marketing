# Multi-Agent UGC Workflow

FastAPI backend for creating product-faithful UGC ad prompt packages and optional Seedance videos through OpenRouter.

## Mandatory Workflow

The app always follows this sequence inside `/generate`:

```text
Product Intake Agent
-> UGC Strategy Agent
-> Content Prompt Engineer Agent
-> Ads Creative Set Agent
-> Product Fidelity Guard
-> Compliance Guard
-> Quality Scorer
-> Static Image Generation
-> Seedance Video Generation
-> Export JSON/Markdown
```

If Product Fidelity Guard or Compliance Guard fails, video and static image generation are blocked and the exported result records `final_export_status: "blocked"`.

## Project Structure

```text
app/
  main.py
  config.py
  avatar_loader.py
app/services/
  product_intake_agent.py
  ugc_agent.py
  ads_creative_set_agent.py
  content_prompt_engineer_agent.py
  product_fidelity_guard.py
  compliance_guard.py
  quality_scorer.py
  openrouter_image_client.py
  openrouter_seedance_client.py
  output_writer.py
data/
  avatars.json
uploads/
output/
tests/
```

## Configuration

```text
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_SEEDANCE_MODEL=bytedance/seedance-2.0-fast
OPENROUTER_PROMPT_MODEL=openai/gpt-5.5-pro
OPENROUTER_IMAGE_MODEL=google/gemini-3-pro-image-preview
OUTPUT_DIR=output
UPLOAD_DIR=uploads
```

`OPENROUTER_API_KEY` is required for live video generation, static image generation, and automatic OpenRouter prompt-model enhancement. If it is missing, `/generate` still returns the deterministic agent output, ads creative set, Seedance payload, JSON report, and Markdown report with generation statuses marked as `skipped`.

You can also paste the OpenRouter API key directly into the UI for a single request. The key is not written into JSON or Markdown exports.

Default models:

```text
Seedance video: bytedance/seedance-2.0-fast
Prompt generation: openai/gpt-5.5-pro
Static image generation: google/gemini-3-pro-image-preview
```

Default platform:

```text
Meta Ads
```

Supported platform values: `meta`, `google_ads`, `tiktok`, `instagram`, `youtube`.

Prompt generation is automatic. The Content Prompt Engineer Agent first creates a deterministic safe prompt package, then runs the OpenRouter-backed `Seedance UGC Video Prompt Skill` to improve Seedance video prompts and UGC style. If that AI prompt step fails, the deterministic prompt package is used as the fallback and the failure is recorded in `content_prompt_package.prompt_generation`.

Avatar1 is registered as:

```text
data/avatars/Avatar1.PNG
```

For Seedance references, the app sends uploaded product and selected avatar images as `input_references` data URLs. If the provider rejects local data URLs, use the UI fields for public HTTPS product/avatar reference URLs.

Generated videos are saved to:

```text
output/{timestamp}_{safe_product_name}_{job_id}.mp4
```

Generated static ads images are saved to:

```text
output/{timestamp}_{safe_product_name}_{creative_id}_{index}.png
```

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Example upload:

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -F "product_image=@product.jpg" \
  -F "product_name=Everyday Tote" \
  -F "product_info=Roomy daily bag with clean minimal design" \
  -F "avatar_id=default_creator" \
  -F "market=US" \
  -F "language=en" \
  -F "platform=meta" \
  -F "video_length=15"
```

## Export Contents

Each export includes:

1. User input
2. Avatar data
3. Product Intake Agent output
4. UGC Strategy Agent output
5. Content Prompt Engineer Agent output
6. Product Fidelity Guard result
7. Compliance Guard result
8. Quality Scorer result
9. Ads creative set
10. Static image generation result
11. Seedance payload
12. Video generation result
13. Final export status
