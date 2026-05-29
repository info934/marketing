# Prompt Inventory

Refined snapshot of prompt templates currently used by the app.

Generated on: 2026-05-20

Primary source files:

- `app/services/prompt_defaults.py`
- `app/services/content_prompt_engineer_agent.py`
- `app/services/openrouter_prompt_client.py`
- `app/services/openrouter_image_client.py`
- `app/services/openrouter_seedance_client.py`
- `app/services/ugc_agent.py`
- `app/services/ads_creative_set_agent.py`

## Runtime Flow

1. `UGC Strategy Agent` creates a safe script, hook, scene plan, voiceover, subtitles, and on-screen text.
2. `Content Prompt Engineer Agent` creates a deterministic fallback prompt package.
3. `OpenRouter Prompt Client` optionally sends the system prompt plus a JSON user payload to the prompt model (`openai/gpt-5.5-pro` by default).
4. If the prompt model returns structured scene JSON, it is compiled into the final Seedance prompt.
5. `OpenRouter Seedance Client` sends the final `seedance_payload.prompt` to `/videos`.
6. `Ads Creative Set Agent` creates UGC video, static image, carousel, meme-style, Meta, and Google Ads copy/visual prompt data.
7. `OpenRouter Prompt Client` optionally refines static image and carousel prompt fields with the same prompt model.
8. `OpenRouter Image Client` converts each selected image creative into an image generation prompt.

## Editable UI Prompt Fields

The UI loads these defaults from `GET /prompt-settings`.

- `content_prompt_system`
- `content_prompt_task`
- `base_video_prompt_template`
- `negative_prompt`
- `category_prompt_handbag`
- `prompt_model`
- `category_prompt_shoes`
- `category_prompt_apparel`

The user can override them per request. Overrides are not written back to source code.

`base_video_prompt_template` also receives `{voice_profile}` and `{category_prompt}`. For `language=en`
and `market=UK`/`GB`, this resolves to a natural British English creator voice
with a subtle everyday UK accent and non-American phrasing.

The selected `product_category` can be `auto`, `handbag`, `shoes`, or `apparel`.
When a category is selected manually, Product Intake uses it before auto-detection
and the matching category prompt preset is injected into video and static image prompts.

## Prompt/Data Source Trace

The app exposes this inventory from `GET /prompt-settings` as `prompt_source_inventory`
and writes the same contract into every export as `prompt_source_trace`.

Data priority:

1. `product_name`
2. `product_info`
3. `product_reference_url` or uploaded `product_image`
4. `avatar_reference_url` or selected avatar
5. selected `product_category` and category prompt override
6. UI prompt overrides
7. Backend defaults only when a required field is missing or safety structure is needed

Runtime layers:

- `Product Intake Agent`: extracts `known_product_facts`, `user_provided_facts`, `safe_benefits`, and `ad_safe_detail_phrases` from user input, with `product_category` as an optional manual override.
- `UGC Strategy Agent`: builds script/voiceover/on-screen text from `product_analysis`, preferring `user_provided_facts` before category fallbacks.
- `Content Prompt Engineer Agent`: builds the local prompt package from UGC strategy, product analysis, avatar, editable base/negative prompts, and selected category prompt directive.
- `OpenRouter Prompt Client`: optionally enhances structured video scenes and static creative prompt fields with `openai/gpt-5.5-pro` by default.
- `Ads Creative Set Agent`: creates C1-C5 creative plans, static image prompts, carousel, meme creatives, and copy, with category-specific visual direction.
- `OpenRouter Image Client`: converts selected, optionally GPT-refined creatives into image prompts and deduplicates identical prompts.
- `OpenRouter Seedance Client`: submits only the visible final `seedance_payload.prompt` and public input references.

## 1. Negative Prompt

Source: `app/services/prompt_defaults.py`

```text
Do not redesign the product. Do not change color, shape, material, logo, packaging, proportions, or visible markings. Do not add luxury or designer branding, famous-brand comparisons, brand names not present in the product reference, medical, therapeutic, orthopaedic, weight-loss, or before/after claims, fake reviews, ratings, star counts, fake discounts, prices, fake scarcity or urgency, personal ownership or first-person usage testimonials, or invented certifications, awards, lab results, or endorsements. Do not show children under 16, public figures, copyrighted characters, brand logos, or copyrighted music references. Do not introduce a different person, swap or morph the avatar face, age, gender, ethnicity, hair, eye color, skin tone, body type, or wardrobe across scenes. Do not produce cinematic studio lighting, ring-light beauty look, gimbal-smooth camera moves, magazine retouch, glossy commercial polish, stock-footage feel, watermarks, on-frame logos, distorted hands, extra or missing fingers, morphing backgrounds, floating objects, melting edges, uncanny faces, mannequin poses, frozen expressions, or lip-sync mismatch.
```

## 2. OpenRouter Prompt Model: System Prompt

Source: `app/services/prompt_defaults.py`

Used as the `system` message for OpenRouter chat completions when enhancing the deterministic prompt package.

```text
# ROLE
You are the AI Prompt Skill inside the Content Prompt Engineer Agent. Your function is to take a product brief plus the user's selected AI avatar and produce per-scene structured content that can be templated into Seedance image-to-video prompts for paid UGC ad creative across Meta Ads, Google Ads, TikTok, Instagram, and YouTube. The avatar may be supplied as a reference image; preserve that identity and never override it with conflicting textual descriptions.

# OUTPUT CONTRACT
Return ONLY a single valid JSON object. No prose, markdown fences, commentary, or trailing commas. All schema fields must be present. Use null where genuinely not applicable. The values for avatar_instruction, scene_summary, fidelity, and voiceover are injected directly into a downstream template, so write clean inline fragments with no leading/trailing punctuation, no line breaks, and no surrounding quotes. Customer-facing strings must be in the requested output language. Internal labels remain English.

# CORE PRINCIPLES
Every output is a paid UGC ad: conversational, slightly imperfect, never broadcast. The avatar is the creator, not an actor playing one. First-person delivery only, unless testimonial rules prohibit ownership or usage claims. Avatar must appear on camera in the first scene with purpose=hook and the last scene with purpose=cta. Middle scenes may cut to product b-roll or environment. Product fidelity is non-negotiable: no recoloring, restyling, rebranding, or material substitution. Never invent missing facts. The avatar reference image is the source of truth for identity. Match avatar voice and register to the audience and market: vocabulary, cadence, slang, and energy should sound like this persona, not a generic creator.

# PRODUCT BRIEF USAGE
Product notes, product_info, and internal_brief_notes are internal guidance only. Never copy those notes verbatim into voiceover, on_screen_text, scene_summary, primary text, meme copy, or carousel text. Convert them into neutral, verified, visually grounded product-detail language. If a note is informal, messy, comparative, or unsupported, use it only to infer category and context and write clean ad-safe wording.

# AVATAR_INSTRUCTION RULES
When use_reference_image=true, avatar_instruction must describe motion, action, expression dynamics, speaking state, and wardrobe continuity only. It must not describe age, gender, ethnicity, hair, eyes, skin, face shape, body type, build, height, weight, or new physical features. Always begin with this exact literal token: subject from reference image, identity preserved, no facial morphing, no appearance drift. Then add comma-separated action and motion, expression dynamics, speaking state, and wardrobe as in reference image, unchanged unless outfit change is explicitly allowed.

For scenes without avatar, set avatar_instruction to one of: no person visible, product-only insert shot, no reference image identity required | hands only entering frame from edge, no face visible, casual everyday hands, natural skin, no identity reference needed | environment shot, no person, atmospheric context. For those scenes set use_reference_image=false and reference_image_source=none.

# SCENE_SUMMARY RULES
scene_summary is a single comma-separated descriptor sequence in this exact order: [ACTION CONTEXT], [SETTING], [CAMERA - angle, distance, movement], [LIGHTING], [MOOD]. When avatar is on camera, do not repeat person action if already in avatar_instruction. Camera movement is simple only: static, slight handheld sway, or slow push-in. Avatar-on-camera scenes include at least three UGC authenticity markers such as available natural window light, warm lamp light mixed color temperature, slight handheld camera sway, off-center framing, lived-in domestic setting, occasional brief glance away from camera, natural conversational pacing. Setting must be a specific real space such as messy kitchen with coffee mug, bathroom mirror, living room couch with throw blanket, car driver seat parked, or bedroom with unmade bed, never empty studio or white cyclorama.

# FIDELITY RULES
fidelity is a short comma-separated directive locking product appearance. Build from the verified product brief: shape, color, finish, visible markings, and packaging if present. Always include product not modified, not restyled, not recolored, not rebranded at the end.

# VOICEOVER RULES
voiceover is the exact spoken line in the output language, in the avatar's voice with age-appropriate vocabulary, market-appropriate phrasing, and persona-appropriate energy. Max 25 words per 5s scene and max 50 words per 10s scene. Write like a real creator talking on camera: natural contractions, clear articles, and short spoken clauses. Avoid robotic category labels such as "comparing handbag", passive phrasing such as "it is shown", and generic filler such as "real detail" as a full sentence. No medical claims, no fake proof, no forbidden testimonial claims. If persona_allows_first_person_testimonial=false, do not say I bought, I've used, I own, I tried, for me it, or similar ownership or usage claims. Use observational, demonstrative, or descriptive first-person framing such as "I'd check", "I'd look at", or "I'd show", without implying ownership or use.

# ON_SCREEN_TEXT RULES
on_screen_text should feel like a paid social overlay, not a label from a prompt. Keep it 2-4 words when possible, max 6 words, concrete and scannable: "Check the shape", "Close-up details", "Real-life scale", "See full detail". Avoid vague overlays such as "No hype" unless the scene is explicitly contrarian.

# SAFETY
Never produce medical, therapeutic, curative, transformation, invented brand, certification, award, review, rating, social proof, discount, scarcity, superlative, luxury status, competitor comparison, children under 16, public figure, copyrighted character, or copyrighted music claims unless explicitly whitelisted by input.permitted_claims. Rewrite unsafe claims into curiosity, demonstration, sensory description, aesthetic appeal, or lifestyle fit and log each change in safety_rewrites with original_claim, reason_removed, and replacement_angle.

# SAFE AREAS
For 9:16 keep avatar face, product, and on_screen_text within central 80% vertical band, with top 14% reserved and bottom 20% reserved. For 1:1 and 16:9 use central 90% on all sides.

# DURATION COMPOSITION
Use native Seedance segments: 15s -> [5,5,5] or [5,10]; 20s -> [10,10] or [5,5,10]; 30s -> [10,10,10] or [5,10,10,5]. First scene is purpose=hook and avatar_on_camera=true. Last scene is purpose=cta and avatar_on_camera=true.

# MULTI-SCENE IDENTITY CHAIN
For multi-scene variants, scene 1 uses original_avatar reference. Avatar-on-camera scenes 2+ use previous_scene_last_frame. Non-avatar scenes use none. Each scene prompt must be self-contained and not refer to "the first frame" or "as shown before".

# OUTPUT SCHEMA
Return exactly this JSON shape: {"variants":[{"variant_id":"v1","total_duration_seconds":15,"language":"en","market":"UK","platform":"meta","aspect_ratio":"9:16","seedance_mode":"image_to_video","reference_image_strategy":"original_avatar_for_first_scene_then_last_frame_chain","scenes":[{"scene_id":"s1","purpose":"hook","duration":5,"avatar_on_camera":true,"use_reference_image":true,"reference_image_source":"original_avatar","avatar_instruction":"subject from reference image, identity preserved, no facial morphing, no appearance drift, looking directly into camera and speaking naturally, neutral relaxed expression with subtle smile forming, lips moving in sync with voiceover, wardrobe as in reference image, unchanged","scene_summary":"creator intro with product visible, lived-in domestic setting with realistic background details, medium close shot with slight handheld camera sway and off-center framing, available natural window light, natural conversational pacing","fidelity":"visible product shape and colors preserved, product not modified, not restyled, not recolored, not rebranded","voiceover":"Exact spoken line","on_screen_text":{"text":"Max six words","position":"bottom_center"},"framing_notes":"Keep avatar face and product inside central safe area"}],"stitching":{"transition_style":"hard cut","cut_timing_notes":"Cut on natural sentence endings"},"safety_rewrites":[],"hypothesis":"Why this variant may work"}]}.

# ABSOLUTE RULES
avatar_instruction never contains static appearance descriptors when use_reference_image=true. It always begins with subject from reference image, identity preserved, no facial morphing, no appearance drift when use_reference_image=true. Durations sum exactly to total_duration_seconds. Output is only the JSON object.
```

## 3. OpenRouter Prompt Model: Task Prompt

Source: `app/services/prompt_defaults.py`

```text
Create one structured variant for the selected product and the user's AI avatar. Use the requested language, market, platform, aspect ratio, and duration from the input. Build scenes that compile into a single OpenRouter /videos prompt while keeping the scene schema intact. Pull product details only from the verified product brief; treat product_info and internal_brief_notes as guidance, never as voiceover or on-screen text. Match avatar voice and register to the audience and market - sound like this specific persona, not a generic creator. Keep every line within permitted claims; rewrite any unsafe beat into a curiosity, demonstration, sensory, or aesthetic-fit frame and log it in safety_rewrites with original_claim, reason_removed, and replacement_angle. Return only the JSON object defined in the system prompt output schema.
```

## 4. OpenRouter Prompt Model: User Payload Template

Source: `app/services/openrouter_prompt_client.py`

```json
{
  "task": "<CONTENT_PROMPT_TASK or UI override>",
  "required_schema": "Return the variants JSON object described in the system prompt.",
  "brief_usage_rule": "Treat product_info/internal_brief_notes as internal guidance only. Do not copy user notes verbatim into voiceover, on_screen_text, scene_summary, meme copy, carousel text, or primary text.",
  "avatar_runtime": {
    "persona_allows_first_person_testimonial": "<bool from UGC strategy>",
    "allow_outfit_change": false,
    "image_to_video_reference_enabled": "<bool: seedance_payload.avatar_reference_mode == exact_image_input_reference>"
  },
  "product_analysis": "<Product Intake Agent output>",
  "ugc_strategy": "<UGC Strategy Agent output>",
  "avatar": "<selected avatar data>",
  "current_prompt_package": "<sanitized deterministic prompt package; image data URLs omitted>"
}
```

OpenRouter request shape:

```json
{
  "model": "<prompt_model>",
  "temperature": 0.2,
  "messages": [
    {"role": "system", "content": "<CONTENT_PROMPT_SYSTEM or UI override>"},
    {"role": "user", "content": "<JSON user payload above>"}
  ],
  "usage": {"include": true}
}
```

## 5. Base Seedance Video Prompt Template

Source: `app/services/prompt_defaults.py`

```text
Seedance image-to-video paid UGC ad, Aspect ratio {aspect_ratio}, {duration}s duration, platform {platform}, market {market}, language {language}. {avatar_instruction}, {scene_summary}, {fidelity}, dialogue "{voiceover}" spoken in {language}. Voice profile: {voice_profile}. Category prompt: {category_prompt}. Use natural conversational pacing and slight breath sounds, identity locked to reference image when avatar reference is supplied, no face morphing, no feature drift, smartphone footage shot on phone front camera, available natural light, slightly imperfect framing, unpolished, raw, no cinematic grading, no color correction, amateur creator self-recording. Use the avatar reference image only when use_reference_image is true. Use the product reference image for strict product fidelity. Keep all critical content inside platform safe areas. Negative prompt: {negative_prompt}
```

Available variables:

- `{duration}`
- `{platform}`
- `{language}`
- `{market}`
- `{voice_profile}`
- `{category_prompt}`
- `{fidelity}`
- `{avatar_instruction}`
- `{voiceover}`
- `{scene_summary}`
- `{aspect_ratio}`
- `{negative_prompt}`

## 5.1 Category Prompt Presets

Source: `app/services/prompt_defaults.py`

Loaded into the Prompt UI as editable per-session category presets. The selected
`product_category` chooses which preset is injected as `{category_prompt}` for
Seedance video and as category-specific direction for static image/carousel prompts.

- `handbag`: exact silhouette, handles, strap attachment, stitching, opening,
  structure, scale, visible interior only when verified, desk-check, outfit-scale,
  and macro detail directions.
- `shoes`: exact upper shape, sole profile, closure, side profile, outsole,
  outfit styling, and macro construction directions; no medical/comfort claims.
- `apparel`: exact cut, drape, seams, neckline, sleeve, hem, closure, fabric look,
  movement and styling context; no body transformation or sizing claims.

## 6. Deterministic Content Prompt Engineer Templates

Source: `app/services/content_prompt_engineer_agent.py`

### Product Fidelity Instruction

```text
Use the product image reference at {product_image_path} as the strict visual reference. Preserve the exact visible product shape, color, proportions, packaging, and any visible markings. Known brand is {known_product_facts.brand}; do not invent brand or material.
```

### Avatar Consistency Instruction

Base:

```text
Use the user's own AI avatar on camera as the UGC creator and keep the avatar identity consistent: name={avatar.name}, style={avatar.style}, appearance={avatar.appearance}. Do not change age, face, hair, skin tone, or recognizable features across scenes.
```

When `use_avatar_image_reference=true` and an avatar image exists, append:

```text
 Use avatar image reference={image_reference} as an exact identity reference. Match the same face, hair, outfit, body framing, and overall creator look consistently across scenes.
```

When an avatar image exists but `use_avatar_image_reference=false`, append:

```text
 Avatar visual reference for prompt style only={image_reference}; do not send this avatar image as a video input reference.
```

### Supporting Prompt Templates

```text
Generate product close-up shots using {product_image_path} as the strict visual reference. Show only visible details from the reference. {fidelity} Negative prompt: {negative_prompt}
```

```text
Create a clean paid-social cover image with the product from {product_image_path} as the strict reference, avatar consistent with {avatar.name}, readable text: '{ugc_strategy.on_screen_text[0]}'. Do not alter the product. Negative prompt: {negative_prompt}
```

```text
Read in a natural creator voice, {language}, market {market}. Avoid hype and testimonial claims. Script: {ugc_strategy.voiceover}
```

```text
Create concise {language} subtitles from the voiceover. Keep lines short and safe for {platform} UI.
```

```text
Place these text overlays inside safe areas for {platform}: {ugc_strategy.on_screen_text}. Use clear, non-claim-heavy ad copy.
```

### AB Testing Variation Prompts

```text
Variation A: lead with product close-up in first second. {fidelity} Negative prompt: {negative_prompt}
```

```text
Variation B: lead with avatar holding product and text '{ugc_strategy.on_screen_text[0]}'. {fidelity} Negative prompt: {negative_prompt}
```

```text
Variation C: lead with everyday context shot while keeping product unchanged. {fidelity} Negative prompt: {negative_prompt}
```

### Quality Improvement Appendix

```text
 Additional strict improvement pass: prioritize exact product fidelity, verified claims only, clear platform safe areas, readable captions, and specific shot timing. 
```

## 7. Structured Scene Fallback Template

Source: `app/services/content_prompt_engineer_agent.py`

```json
{
  "variants": [
    {
      "variant_id": "v1",
      "total_duration_seconds": "<sum(scene_durations)>",
      "language": "{language}",
      "market": "{market}",
      "platform": "{platform}",
      "aspect_ratio": "{aspect_ratio}",
      "seedance_mode": "image_to_video",
      "reference_image_strategy": "original_avatar_for_first_scene_then_last_frame_chain",
      "scenes": [
        {
          "scene_id": "s{index}",
          "purpose": "hook | demonstration | cta",
          "duration": "<5 or 10 or remaining duration>",
          "avatar_on_camera": "<true for first and last scene>",
          "use_reference_image": "<true only if avatar reference is enabled and avatar is on camera>",
          "reference_image_source": "original_avatar | previous_scene_last_frame | none",
          "avatar_instruction": "{avatar_instruction or no person visible, product-only insert shot, no reference image identity required}",
          "scene_summary": "{selected_scene.visual}, lived-in domestic setting with realistic background details, medium close shot with slight handheld camera sway, available natural window light, natural conversational pacing",
          "fidelity": "{fidelity}, product not modified, not restyled, not recolored, not rebranded",
          "voiceover": "{selected_scene.voiceover}",
          "on_screen_text": {
            "text": "{selected_scene.on_screen_text}",
            "position": "bottom_center"
          },
          "framing_notes": "Keep avatar face, product, and text inside central safe area"
        }
      ],
      "stitching": {
        "transition_style": "hard cut",
        "cut_timing_notes": "Cut on natural sentence endings"
      },
      "safety_rewrites": [],
      "hypothesis": "Authentic creator framing with verified product details lowers perceived ad-ness and improves consideration for {product_name}."
    }
  ]
}
```

Duration fallback:

```text
duration >= 30 -> [10, 10, duration - 20]
duration >= 20 -> [10, duration - 10]
duration >= 15 -> [5, 5, duration - 10]
otherwise -> [duration]
```

## 8. Compiled Structured Seedance Prompt

Source: `app/services/openrouter_prompt_client.py`

```text
Create a paid UGC ad video from this structured scene plan. Platform: {variant.platform}. Market: {variant.market}. Language: {variant.language}. Duration: {variant.total_duration_seconds} seconds. Aspect ratio: {variant.aspect_ratio}. Seedance mode: {variant.seedance_mode}. Reference strategy: {variant.reference_image_strategy}. Preserve product fidelity and, when avatar reference image is supplied, preserve the user's AI avatar identity without facial morphing or appearance drift. Scene {scene.scene_id} ({scene.duration}s, {scene.purpose}) | avatar_on_camera={scene.avatar_on_camera} | use_reference_image={scene.use_reference_image} | reference_image_source={scene.reference_image_source} | avatar_instruction={scene.avatar_instruction} | scene_summary={scene.scene_summary} | fidelity={scene.fidelity} | voiceover={scene.voiceover} | on_screen_text={scene.on_screen_text.text} at {scene.on_screen_text.position} | framing_notes={scene.framing_notes} Stitching: {stitching.transition_style}; {stitching.cut_timing_notes} Safety rewrites applied: {safety_rewrites} Negative prompt: {negative_prompt}
```

## 9. Seedance Video Payload

Source: `app/services/openrouter_seedance_client.py`

```json
{
  "model": "{seedance_model}",
  "prompt": "{seedance_video_prompt}",
  "duration": "{duration}",
  "aspect_ratio": "{aspect_ratio}",
  "resolution": "{resolution}",
  "input_references": "<public image references only, if available>",
  "frame_images": "<public frame images only, if available>",
  "generate_audio": "<optional>",
  "seed": "<optional>",
  "callback_url": "<optional>",
  "provider": "<optional>"
}
```

Local data URLs and localhost image URLs are stripped before sending to the video API.

## 10. UGC Strategy Script Templates

Source: `app/services/ugc_agent.py`

### Hooks

```text
CZ default/category: U {spoken_product_label} bych zacal detailem, ne jen hezkou fotkou.
EN default/category: With {spoken_product_label}, I'd check the shape first, not just the polished product photo.
```

### Scene 1

```text
Time: 0-3s
Visual: Avatar speaks directly to camera in natural domestic setting, product held casually or visible just at edge of frame, off-center composition, slight handheld sway, available window light.
Voiceover: {hook}
On-screen text CZ: Zacni tvarem
On-screen text EN: Check the shape
Subtitle: {hook}
```

### Scene 2

```text
Time: 3-{max(7, duration // 2)}s
Visual: Slow close-ups from the product reference: shape, finish, visible construction, packaging if present, slight handheld sway, soft directional light.
Voiceover CZ: Zblizka lip uvidis {detail_focus}, nez se rozhodnes.
Voiceover EN: The close-up is where you notice {detail_focus}, before deciding if the style makes sense.
On-screen text CZ: Detail zblizka
On-screen text EN: Close-up details
```

### Scene 3

```text
Time: {max(7, duration // 2)}-{max(11, duration - 3)}s
Visual: Creator-style everyday context shot adapted to the product category, product visible and used in context, lived-in setting, no studio look.
Voiceover CZ: Ukazal bych produkt v beznem prostredi, aby se lip posoudilo meritko a styl.
Voiceover EN: I'd place it in a normal everyday setting, so the scale and style feel easier to judge.
On-screen text CZ: Meritko v realu
On-screen text EN: Real-life scale
```

### Scene 4

```text
Time: {max(11, duration - 3)}-{duration}s
Visual: Avatar back on camera with product visible, subtle smile, clean CTA text overlay, same lived-in setting and wardrobe continuity, slight handheld sway.
Voiceover CZ: Detail otevres pres tlacitko v reklame a v klidu si ho projdes.
Voiceover EN: Use the ad button for the full product details and take your time with it.
On-screen text CZ: Otevri detail
On-screen text EN: See full detail
```

## 11. Static Image Generation Prompt

Source: `app/services/openrouter_image_client.py`

```text
Create one finished paid social static ad creative image.
Generate exactly one image for this one creative; do not create a collage, contact sheet, multi-panel set, or multiple variants in one image.
Asset type: {creative.asset_type}.
Format: {creative.format}.
Layout: {creative.layout}.
Visual direction: {creative.visual_prompt}.
Aspect ratio: {creative.aspect_ratio}.
Aim for the level of polish typical of a strong DTC brand ad: natural lighting, real materials, mid-saturation color, rule of thirds, clear central safe area, readable typography, no clutter, no platform UI mockups, no fake app chrome, no watermarks, no stock-photo feel, scroll-stopping but not overproduced.
Do not invent reviews, ratings, star counts, discounts, scarcity claims, certifications, medical effects, brand badges that are not in the product reference, or platform logos.
Preserve the product from the reference exactly: product not modified, not restyled, not recolored, not rebranded; exact shape, color, proportions, and visible markings.
Use the supplied product reference image as the source of truth for product appearance.
Render this overlay text exactly if legible: {overlay_text}
Optional small CTA text: {cta}
Use this copy only as context, not as a large block of text in the image: {primary_text[:700]}
```

Conditional lines are included only when the related product reference, overlay, CTA, or primary text exists.

Default generation scope: C2, C3, C4, and all five C5 carousel cards. Meme-style
creatives stay in `ads_creative_set.meme_style_creatives` as concepts/copy unless
`include_meme_images` is explicitly enabled in the image client.

`max_static_images` is a cap only. It selects up to that many planned creatives in
priority order and never pads the count with duplicates or unrelated creative
types. When the cap is low, selection favors a diverse mix over two similar
lifestyle renders. If the plan has 8 image creatives and the cap is 10, only 8
image API requests are selected.

## 12. Ads Creative Set Visual Prompt Templates

Source: `app/services/ads_creative_set_agent.py`

### Creative Media Plan

```text
C1 UGC video | UGC | 9:16 | TOFU + retargeting | 55%
C2 Static lifestyle | PAIN | 1:1 | TOFU + retargeting | 10%
C3 Static lifestyle | IDENTITY | 1:1 | TOFU + retargeting | 10%
C4 Static detail zoom | DEMONSTRATION | 1:1 | Retargeting | 10%
C5 Carousel 5 cards | DEMONSTRATION | 1:1 | MOFU | 15%
```

### Static Image Ads

`C2_static_lifestyle_pain`

```text
Use product reference {product_url}, C2 PAIN creative, overhead square desk or kitchen-table scene for {category}, product placed beside a handwritten detail-check note, keys and everyday carry items nearby, visual idea is that one polished product photo is not enough, focus cue on {first_benefit}, natural directional window light from one side, rule of thirds, single short overlay headline inside safe area, no person face, no platform UI, no fake brand badges
```

`C3_static_lifestyle_identity`

```text
Use product reference {product_url}, C3 IDENTITY creative, calm hallway or bedroom outfit-planning scene for {category}, product staged next to a coat or folded neutral outfit plus notebook and travel card, aimed at careful shoppers judging style and scale, focus cue on {second_benefit}, 45-degree eye-level composition, warm natural window light, mid-saturation palette, single overlay headline inside safe area, no person face, no stock-photo people, no platform UI
```

`C4_static_detail_zoom_demonstration`

```text
Use product reference {product_url}, C4 DEMONSTRATION creative, extreme close-up macro crop of one or two visible product details from the reference, product detail fills at least 70 percent of the square frame, annotation labels point only to visible details, focus cue on {third_benefit}, neutral clean background, soft directional light, very sharp focus, no invented details, no claim labels
```

### Carousel Card Visual Prompt

```text
Use product reference {product_url}, C5 carousel card {number}, role {role}, visual focus must match overlay text '{overlay_text}', {visual}, keep this card visually distinct from the other carousel cards
```

Card visual values:

```text
product hero shot, clean center crop, neutral background, minimal headline overlay
macro detail close-up of one visible feature, single small text annotation, sharp focus
everyday lifestyle placement, product visible and accurate to reference, no styling change, natural light
product shown next to a size or context reference for scale, neutral background, clear comparison
verified-only review excerpt block when input provides one, otherwise a clean CTA card with the headline only and no invented reviews
```

### Meme-Style Static Visual Prompts

```text
meme_dm: Generic direct-message screenshot style, neutral grey and blue chat bubbles, no recognizable platform branding, product thumbnail as an attached image inside the conversation, mobile aspect framing, low-fi authentic feel
meme_tweet: Generic plain-text social post screenshot style with neutral typography, no recognizable platform logos or UI, product image embedded below the text block, low-fi authentic crop, slightly desaturated to feel like a real screenshot
```

## 13. Ads Creative Copy Templates Used As Image Context

Source: `app/services/ads_creative_set_agent.py`

### Czech Static Copy

```text
Nekoukej jen na jednu fotku. Tady je rozdil zblizka.

- {first_benefit}
- Realny detail, ne stock fotka
- Jasny pohled pred kliknutim

Detail otevres pres tlacitko v reklame.
```

```text
Pri vyberu pomaha videt produkt v realnem prostredi.

- {first_benefit}
- Bez vymyslenych tvrzeni
- Rychly detail pred rozhodnutim

Detail otevres pres CTA tlacitko.
```

```text
Tohle je rychla kontrola detailu pred klikem.

- Tvar a viditelne provedeni
- {first_benefit}
- Bez hype, jen co je videt

Detail v reklame otevres jednim klikem.
```

### English Static Copy

```text
Do not judge it from one photo. Here is the close-up difference.

- {first_benefit}
- Real detail, not a stock photo
- A clearer look before you click

Open the detail from the ad button.
```

```text
Seeing a product in a real setting helps you decide.

- {first_benefit}
- No invented claims
- Quick detail before deciding

Open the detail from the CTA button.
```

```text
A fast close-up check before you click.

- Shape and visible finish
- {first_benefit}
- No hype, just what is visible

Open the detail from the ad button.
```

### Carousel Primary Text

```text
CZ: Projed si detaily krok za krokem. / Kratky hook / Viditelne vlastnosti / CTA bez vymyslenych slibu
EN: Swipe through the details before you decide. / Quick hook / Visible product features / Clear CTA, no invented claims
```

### Meme Copy

```text
CZ meme_dm: ja: jen rychle mrknu na detail / taky ja: ok, {product_name} dava smysl
CZ meme_tweet: nepotrebuju hype, staci mi videt {first_benefit}
EN meme_dm: me: just quickly checking the detail / also me: ok, {product_name} actually makes sense
EN meme_tweet: I do not need hype, I just want to see {first_benefit}
```

## 14. Hook Bank Templates

Source: `app/services/ads_creative_set_agent.py`

### Czech

```text
Pokud zvazujes {category}, podivej se nejdriv na tohle.
Nekupuj podle jedne fotky z dalky. Mrkni na realny detail.
Zoom na detail, ktery bys pri rychlem scrollu preskocila.
Pred vyberem vs. po kontrole detailu.
Vis, co u {product_name} zkontrolovat jako prvni?
3 veci na {product_name}, ktere se vyplati overit pred klikem.
POV: poprve vidis {product_name} zblizka bez filtru.
{first_benefit} - tohle je videt teprve zblizka.
Tohle je {category} detail, ktery vetsina reklam preskoci.
Misto dalsi {category} reklamy, kratky detail navic.
```

### English

```text
If you are comparing {category}, start with this detail.
Do not buy from a distant photo. Check the real details first.
Zoom in on the detail most people miss while scrolling.
Before choosing vs. after checking the details.
What should you check first on {product_name}?
3 things on {product_name} worth checking before you click.
POV: you finally see {product_name} up close without the hype.
{first_benefit} - this is only visible when you look closer.
The {category} detail most ads skip over.
Instead of another {category} ad, a quick close-up.
```

## 15. Creative Angle Templates

Source: `app/services/ads_creative_set_agent.py`

### Czech

```text
curiosity: Co je u {product_name} videt teprve zblizka?
pain_point: Vetsinou vybiras podle jedne fotky a pak chybi detail
contrarian: Hype nech stranou. Nejdriv detail.
feature_detail: {first_benefit}
identity: Pro lidi, co si {category} chteji rozmyslet
demonstration: {product_name} bez filtru - jak vypada doopravdy
comparison: Misto dalsi {category} reklamy, jen detail navic
```

### English

```text
curiosity: What can you actually see up close on {product_name}?
pain_point: A distant product photo is not enough
contrarian: Skip the hype. Detail first.
feature_detail: {first_benefit}
identity: For people who want to think about {category}, not impulse-buy it
demonstration: {product_name} without filters - what it actually looks like
comparison: Instead of another {category} ad, a quick close-up
```

## 16. Ad Description Suggestion Templates

Source: `app/services/ads_creative_set_agent.py`

These are exported as `ads_creative_set.ad_description_suggestions`.

The app currently generates 5 social variants (`curiosity`, `pain_point`, `contrarian`, `feature_detail`, `identity`) or 4 Google description variants, with validation metadata and first-line/character-limit checks.

## 17. Google Ads Asset Templates

Source: `app/services/ads_creative_set_agent.py`

Character limits are enforced before export.

### Czech RSA Headlines

```text
Detail pred klikem
{product_name} zblizka
Realny pohled, ne stock
Co u {category} videt
3 detaily k overeni
{first_benefit}
Bez hype, jen detail
Zoom na produkt
Detail v 5 sekundach
Co overit pred klikem
Pohled na {product_name}
Klid na rozmyslenou
Kratky produktovy nahled
Vidis to az zblizka
{product_name}
```

### English RSA Headlines

```text
Detail Before You Click
{product_name} Up Close
Real Look, Not A Stock
What To Check First
3 Details Worth Checking
{first_benefit}
No Hype, Just Detail
Zoom On The Product
A Close-Up In 5 Seconds
Check Before You Click
Up-Close Product View
Time To Think It Over
Quick Product Preview
Only Visible Up Close
{product_name}
```

### Czech RSA Descriptions

```text
Realny detail produktu pred kliknutim. Zadne vymyslene sliby, jen to, co je videt.
Kratky produktovy nahled. Pomuze rozhodnout se v klidu bez tlaku z reklamy.
Zkontroluj tvar, povrch a viditelne provedeni pres tlacitko v reklame.
Realny pohled na {product_name} pred dalsim krokem v par vterinach.
```

### English RSA Descriptions

```text
A real product detail before you click. No invented promises, only what is visible.
A quick product preview. Helps you decide calmly, without ad pressure.
Check shape, finish, and visible build from the ad CTA button.
A real look at {product_name} before the next step, in just seconds.
```

### PMax Long Headlines

```text
CZ: Podivej se na {product_name} zblizka bez zbytecneho hype
CZ: Rychly produktovy detail pro {category} v par vterinach
CZ: Co u {product_name} videt pred klikem: {first_benefit}
CZ: Realny pohled na produkt, ne stock fotka
CZ: Kratke shrnuti detailu pred kliknutim

EN: See {product_name} up close without unnecessary hype
EN: A quick product detail for {category} in just seconds
EN: What to check on {product_name} first: {first_benefit}
EN: A real product look, not a stock photo
EN: A short detail preview before you click
```

## 18. Meta And Google Copy In Content Prompt Package

Source: `app/services/content_prompt_engineer_agent.py`

### Meta Ads Copy

```json
{
  "cs": {
    "primary_text": "Misto jedne vzdalene fotky se podivej na {product_name} zblizka. Realny detail, zadne vymyslene sliby. Detail otevres pres tlacitko v reklame.",
    "headline": "Podivej se zblizka",
    "description": "Realny detail, bez hype."
  },
  "en": {
    "primary_text": "Instead of one distant photo, see {product_name} up close. Real detail, no invented promises. Open the detail from the ad button.",
    "headline": "See it up close",
    "description": "Real detail, no hype."
  }
}
```

### Google / YouTube Ads Copy

```json
{
  "headline": "See {product_name} up close",
  "description": "A short product detail overview focused on what is actually visible.",
  "cta": "Learn more"
}
```

## 19. Platform Adaptation Prompts/Directives

Source: `app/services/ugc_agent.py`

```json
{
  "tiktok": {
    "aspect_ratio": "9:16",
    "style": "fast creator edit",
    "safe_area": "keep captions centered above lower UI"
  },
  "instagram": {
    "aspect_ratio": "9:16",
    "style": "polished Reels edit",
    "safe_area": "avoid top and bottom interface zones"
  },
  "youtube": {
    "aspect_ratio": "16:9",
    "style": "clear YouTube Shorts or in-stream pacing",
    "safe_area": "keep key text away from edges"
  },
  "meta": {
    "aspect_ratio": "9:16",
    "style": "direct paid social creative",
    "safe_area": "leave margin for ad UI"
  },
  "google_ads": {
    "aspect_ratio": "16:9",
    "style": "Google Ads video asset with product-led clarity",
    "safe_area": "keep product, subtitles, and CTA text inside central safe area for YouTube and Display placements"
  }
}
```

## 20. Prompt Output Locations In Final Export

Every generation export includes these prompt-related fields:

```text
content_prompt_package.product_fidelity_instruction
content_prompt_package.avatar_consistency_instruction
content_prompt_package.negative_prompt
content_prompt_package.seedance_video_prompt
content_prompt_package.structured_scene_prompt
content_prompt_package.product_closeup_prompt
content_prompt_package.thumbnail_cover_image_prompt
content_prompt_package.voiceover_tts_prompt
content_prompt_package.subtitle_prompt
content_prompt_package.on_screen_text_prompt
content_prompt_package.meta_ads_copy
content_prompt_package.google_youtube_ads_copy
content_prompt_package.ab_testing_variation_prompts
content_prompt_package.seedance_payload.prompt
seedance_payload.prompt
ads_creative_set.creative_plan
ads_creative_set.ugc_video_ad.seedance_prompt
ads_creative_set.ugc_video_ad.structured_scene_prompt
ads_creative_set.static_image_ads[*].visual_prompt
ads_creative_set.carousel_ad.cards[*].visual_prompt
ads_creative_set.meme_style_creatives[*].visual_prompt
ads_creative_set.ad_description_suggestions
static_image_generation.image_assets[*].prompt
video_generation.submitted_payload.prompt
```

## 21. Safety Notes

- Product notes are internal guidance only and should not be copied verbatim into ad copy or video script.
- CTA URLs are not written into creative copy. Meta/Google destination URL is configured inside the ad platform.
- Product image reference is the source of truth for product appearance.
- Avatar image reference is provider-sensitive. Exact avatar reference mode only attaches public avatar URLs when enabled.
- Static image prompts may receive product references as public URLs or local uploads converted to data URLs.
- Seedance video prompts receive only public image references; local data URLs and localhost URLs are removed before `/videos`.
