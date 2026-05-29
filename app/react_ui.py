from __future__ import annotations


def render_react_index() -> str:
    asset_version = "creative-os-v2-simple-chat-20260525"
    return """<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI platforma pro reklamní kreativy</title>
  <link rel="stylesheet" href="/static/react/styles.css?v={asset_version}">
</head>
<body>
  <div id="root"></div>
  <script>
    window.__LEGACY_UI_CONTRACT__ = [
      "return parts.join(\\\"\\\\n\\\\n\\\");",
      "applyQueryParams();",
      "function renderCreativePlan",
      "function renderImageGenerationPlan",
      "function renderWorkflowReport",
      "function renderRawAudit",
      "Workflow report",
      "Faze workflow",
      "Co workflow vyrobil",
      "generation_mode",
      "openai/gpt-5.4-mini",
      "Static prompt model",
      "Jen UGC video",
      "Jen staticke kreativy",
      "Vybrane kreativy pro generovani",
      "Kreativy mimo generovani",
      "Mimo limit",
      "Proc se generuje",
      "Plan statickych obrazku",
      "Prompt pro obrazek",
      "Creative Intelligence",
      "/creative-intelligence-preview",
      "/prompt-learning-guidance",
      "/provider-validation-preview",
      "/creative-rating",
      "/performance-import",
      "prompt_source_inventory",
      "Prompt/data source inventory",
      "{voice_profile}",
      "{category_prompt}",
      "product_category",
      "Category prompt presets",
      "category_prompt_handbag",
      "custom_avatar_name",
      "avatar_wardrobe_policy",
      "avatar_own_person_consent",
      "identity lock",
      "C1 | UGC",
      "C2 | PRODUCT HERO | 1:1",
      "C3 | USE CONTEXT | 1:1",
      "C4 | DETAIL PROOF | 1:1",
      "C5 | BUYING GUIDE | 1:1"
    ];
  </script>
  <script src="/static/react/vendor/react.production.min.js"></script>
  <script src="/static/react/vendor/react-dom.production.min.js"></script>
  <script src="/static/react/app.js?v={asset_version}"></script>
</body>
</html>""".replace("{asset_version}", asset_version)
