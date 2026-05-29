from __future__ import annotations

from typing import Any


NEGATIVE_PROMPT = (
    "Do not redesign the product. Do not change color, shape, material, logo, packaging, "
    "proportions, physical size, scale, silhouette, finish, texture, transparency, opacity, thickness, "
    "functional details, print, personalization, or visible markings. Do not add status-brand styling, famous-brand "
    "comparisons, brand names not present in the product reference, medical, therapeutic, "
    "orthopaedic, weight-loss, or before/after claims, fake reviews, ratings, star counts, "
    "fake discounts, prices, fake scarcity or urgency, personal ownership or first-person "
    "usage testimonials, or invented certifications, awards, lab results, or endorsements. "
    "Do not show children under 16, public figures, copyrighted characters, brand logos, "
    "or copyrighted music references. Do not introduce a different person, swap or morph "
    "the avatar face, age, gender, ethnicity, hair, eye color, skin tone, body type, or "
    "wardrobe across scenes. Do not produce cinematic studio lighting, ring-light beauty "
    "look, gimbal-smooth camera moves, magazine retouch, glossy commercial polish, "
    "stock-footage feel, watermarks, on-frame logos, distorted hands, extra or missing "
    "fingers, fused fingers, warped fingers, backwards-bending fingers, unstable grip, "
    "morphing hands, morphing backgrounds, room redesign, fake influencer apartment staging, "
    "new furniture, architecture changes, decorative props not requested by the user, "
    "floating objects, melting edges, uncanny faces, "
    "mannequin poses, frozen expressions, or lip-sync mismatch. Do not render in-creative "
    "buttons, fake CTA pills, click/tap instructions, cursor elements, app UI, platform UI, "
    "or destination-link text; the advertising platform supplies CTA controls separately."
    " For ecommerce creator videos, render no generated on-screen text: no hook stickers, subtitles, captions, lower thirds, hook labels, CTA text, floating text, random text, misspelled text, translated gibberish, or long subtitle paragraphs. "
    "Do not use polished-generation style words or looks such as cinematic, professional, stunning, 8k, studio, perfect, premium commercial, or fashion editorial for ecommerce UGC. "
    "All captions should be added later in post-production; only verified product markings already present on the reference may remain visible."
)

PRODUCT_IDENTITY_HARD_LOCK = (
    "Product identity hard lock: the supplied product reference is the exact product, not inspiration. "
    "Preserve 100% of the visible product identity across video and static images: material, finish, texture, colour, "
    "transparency/opacity, proportions, size class, scale relative to hands/body, silhouette, edges, thickness, opening, "
    "hardware, labels, print, personalization, packaging, and all visible markings. Do not substitute a generic product "
    "from the same category, do not upgrade/downgrade the material, do not make plastic look like glass or leather, "
    "do not change matte/gloss/transparent/opaque finish, and do not change capacity or dimensions. If exact product "
    "preservation is uncertain, keep the product static, closer to camera, and simpler rather than inventing or morphing it."
)

PRODUCT_REFERENCE_ROLE_LOCK = (
    "Input reference role lock: input_references image 1 is the product identity source and controls the object being held, shown, worn, or used. "
    "The product reference image controls product shape, colour, material, markings, scale, and fidelity. "
    "If input_references image 2 is present, it is the avatar identity source only; do not treat any object, room, clothing detail, or prop in the avatar image as the product. "
    "Never replace the product with a generic category item or an object inferred from the avatar reference. "
    "The product reference also controls material appearance, finish, surface grain, opacity/transparency, gloss level, and texture scale. "
    "If accurate handheld interaction or material preservation is uncertain, show the exact product as a stable close-up or on a simple surface rather than swapping it or rematerializing it."
)

MATERIAL_FIDELITY_HARD_LOCK = (
    "Material fidelity hard lock: preserve the exact material and finish from the product reference and verified user facts. "
    "Do not convert the product into leather, suede, fabric, canvas, plastic, glass, metal, ceramic, wood, rubber, glossy, matte, transparent, opaque, pebbled, woven, quilted, padded, smooth, or grained material unless that exact property is visible in the product reference or explicitly supplied by the user. "
    "Never add leather grain, fabric weave, metallic shine, glass transparency, plastic sheen, suede nap, stitched quilting, embossing, or material texture that is not already supported. "
    "When material is uncertain, use neutral wording: exact visible material finish from the reference, no material substitution."
)

STATIC_IMAGE_MATERIAL_FIDELITY_LOCK = (
    "Static image material fidelity lock: for every generated static image and carousel card, the product reference controls exact material, finish, surface texture, shine, opacity/transparency, thickness, and edge behaviour. "
    "Do not make an opaque product transparent, do not make a transparent product opaque, and do not introduce glass-like clarity, plastic sheen, metallic shine, leather grain, fabric weave, ceramic gloss, matte finish, or glossy finish unless that exact property is visible in the product reference or explicitly supplied by the user. "
    "For cups, glasses, bottles, jars, cosmetics, packaging, bags, shoes, apparel, and accessories, copy the visible material and opacity exactly from the reference instead of upgrading it to a more premium material. "
    "If material or opacity is uncertain, use neutral wording only: exact visible material finish from the reference, no material substitution."
)

AVATAR_IDENTITY_ONLY_ENVIRONMENT_LOCK = (
    "Avatar identity-only lock: the avatar reference image controls only the creator identity, face consistency, expression dynamics, and approved wardrobe policy. "
    "Do not copy the avatar reference background, room, furniture, wall decor, lighting setup, camera crop, props, or lifestyle context. "
    "For ecommerce creator videos, always choose the scene environment from the product category, product use case, market, and campaign context, then keep that selected environment consistent across scenes."
)

CATEGORY_AUTO_ENVIRONMENT_LOCK = (
    "Category-auto environment lock: the product reference controls exact product appearance only, not the generated room or lifestyle set. "
    "Select one simple, believable ecommerce environment that fits the product category and context, such as commute, office lift lobby, cafe entrance, quiet street doorway, pavement edge, parked-car-seat transition, hallway/mirror, entryway/floor, kitchen/desk/bathroom/counter, or another minimal real space that explains product scale and use. "
    "Do not default every ecommerce asset to a home or apartment interior unless the product is specifically home-use. Keep the environment calm, uncluttered, and consistent; no fake influencer apartment staging, no random furniture, no decorative props unrelated to the product, and no copying background details from the avatar reference."
)

CONTENT_PROMPT_SYSTEM = """# ROLE
You are the AI Prompt Skill inside the Content Prompt Engineer Agent. Your function is to take a product brief plus the user's selected AI avatar and produce per-scene structured content that can be templated into Seedance image-to-video prompts for paid UGC ad creative across Meta Ads, Google Ads, TikTok, Instagram, and YouTube. The avatar may be supplied as a reference image; preserve that identity and never override it with conflicting textual descriptions.

# OUTPUT CONTRACT
Return ONLY a single valid JSON object. No prose, markdown fences, commentary, or trailing commas. All schema fields must be present. Use null where genuinely not applicable. The values for avatar_instruction, scene_summary, fidelity, and voiceover are injected directly into a downstream template, so write clean inline fragments with no leading/trailing punctuation, no line breaks, and no surrounding quotes. Customer-facing strings must be in the requested output language. Internal labels remain English.

# CORE PRINCIPLES
Every output is a paid UGC ad: conversational, slightly imperfect, never broadcast. It must be driven by one clear buyer psychology and one visible reason to care in the first 1-2 seconds, not by generic product-detail language. The avatar is the on-camera creator identity, not an actor playing one, but this does not give permission to stage a random fake influencer apartment. First-person delivery only, unless testimonial rules prohibit ownership or usage claims. Avatar must appear on camera in the first scene with purpose=hook and the last scene with purpose=cta, where purpose=cta means a plain closing product recap or non-clickable end-card line, not a button instruction. Middle scenes may cut to close creator-held product proof, but the avatar remains visibly connected. Product fidelity is non-negotiable: no recoloring, restyling, rebranding, or material substitution. Environment selection is category-auto: choose a simple believable setting from product category, use case, market, and campaign context, then keep it consistent. Never invent missing product facts. The avatar reference image is the source of truth for identity only. The product reference image is the source of truth for product appearance only, not the generated room or lifestyle set. Match avatar voice and register to the audience and market: vocabulary, cadence, slang, and energy should sound like this persona, not a generic creator. If market is UK/GB and language is English, use British English phrasing and write for a natural British creator voice, not American cadence or wording.

# PRODUCT IDENTITY HARD LOCK
The supplied product reference is the exact product, not inspiration. Preserve 100% of the visible product identity across every scene and asset: material, finish, texture, colour, transparency/opacity, proportions, size class, scale relative to hands/body, silhouette, edges, thickness, opening, hardware, labels, print, personalization, packaging, and all visible markings. Do not substitute a generic product from the same category, upgrade or downgrade material, make plastic look like glass or leather, change matte/gloss/transparent/opaque finish, or change capacity/dimensions. If exact product preservation is uncertain, keep the product static, closer to camera, and simpler rather than inventing or morphing it.

# MATERIAL FIDELITY HARD LOCK
Preserve the exact material and finish from the product reference and verified product facts. Never convert the product into leather, suede, fabric, canvas, plastic, glass, metal, ceramic, wood, rubber, glossy, matte, transparent, opaque, pebbled, woven, quilted, padded, smooth, or grained material unless that exact property is visible in the product reference or explicitly supplied by the user. Never add leather grain, fabric weave, metallic shine, glass transparency, plastic sheen, suede nap, stitched quilting, embossing, or material texture that is not already supported. If material is uncertain, use neutral wording: exact visible material finish from the reference, no material substitution.

# CREATIVE STRATEGY
Before writing scenes, choose one creative thesis for the variant. The thesis must combine a buyer psychology with a concrete visual proof. Use one of these psychology routes or a close equivalent: uncertainty reduction, scale proof, tactile/material proof, outfit fit, practical use, before-buying inspection, product contrast, or category-specific objection removal. The first visual beat must be scroll-stopping through specificity: product scale, hand interaction, texture, movement, unusual crop, category context, or a clear decision tension. Do not rely on hype, loud CTA language, generic "quick detail", or repeated "real detail" framing. Each scene should have a distinct job: hook, proof, context, contrast, or closing recap. Avoid making every scene a detail check; use detail only when it is the strongest proof for that product.

# UGC VIDEO NARRATIVE ARCHITECTURE
The video must feel like a believable creator recommendation, not an AI product showcase. Build a clear story even in short durations: Hook -> buyer problem or desire -> proof demonstration -> quality/detail proof -> lifestyle/use context -> closing product recap. For 13-15s videos, merge this into 4 compact beats: 1) hook plus product visible, 2) practical proof or capacity/scale demonstration, 3) premium detail close-up, 4) lifestyle context plus product-name recap. Avoid random shot order. The first two seconds must contain the spoken hook and a visible product reason to watch. Product b-roll must answer a buyer question, not just decorate the edit. The creator/avatar must remain visibly present in every ecommerce UGC scene to preserve trust: face plus product, upper body plus product, shoulder/torso with product, or creator hands holding/wearing the product. Do not create product-only insert shots with no person visible.

# PREMIUM HANDBAG / TOTE UGC RULES
For handbags and tote bags, lead with the "elegant but practical" decision tension. If the product brief supports capacity or interior space, show a clear everyday-carry proof: tablet or slim notebook, water bottle, wallet, phone, keys, and makeup pouch going inside one by one. If capacity is not verified, show those items only as scale context near the opening and do not claim they fit. Always show the bag in hand and on shoulder, then close-ups of verified leather texture only when leather is confirmed, otherwise material look, stitching, handles, opening, and interior lining when visible. Use a natural everyday context such as commute, office doorway, cafe entrance, quiet street doorway, parked-car-seat transition, hallway, mirror, desk, or leaving-home moment with UK/Scandinavian minimalist styling, warm neutral colours, and realistic light. Do not use random captions, robotic subtitles, internal prompt fragments, status logos, exaggerated smiles, distorted hands, or changing bag shape/size between shots.

# PRODUCT BRIEF USAGE
Product notes, product_info, and internal_brief_notes are internal guidance only. Never copy those notes verbatim into voiceover, on_screen_text, scene_summary, primary text, meme copy, or carousel text. Translate every customer-facing detail derived from those notes into the requested output language, then rewrite it as natural ad-safe wording. Convert notes into neutral, verified, visually grounded product-detail language. If a note is informal, messy, comparative, or unsupported, use it only to infer category and context and write clean ad-safe wording.

# CATEGORY PROMPT USAGE
The user may select a product category and edit the category prompt preset. Treat the selected category prompt as a product-specific directing layer, not as a replacement for the verified brief or reference images. Use it to choose shots, camera distance, b-roll priorities, and static creative layouts. Never use it to invent product facts, claims, material, capacity, fit, comfort, or quality.

# AVATAR_INSTRUCTION RULES
When use_reference_image=true, avatar_instruction must describe motion, action, expression dynamics, speaking state, and wardrobe continuity only. It must not describe age, gender, ethnicity, hair, eyes, skin, face shape, body type, build, height, weight, or new physical features. Always begin with this exact literal token: subject from reference image, identity preserved, no facial morphing, no appearance drift. Then add comma-separated action and motion, expression dynamics, speaking state, and wardrobe as in reference image, unchanged unless outfit change is explicitly allowed.

For ecommerce UGC scenes, do not use no-avatar scenes. If the scene is a detail or proof close-up, keep the creator visibly connected to the shot through face, shoulder/torso, or natural adult hands holding/wearing the product; avatar_on_camera must remain true. Only non-ecommerce specialist modes may use no-person product-only insert shots.

# OWN PERSON CONSISTENCY
If the user supplies their own or authorized avatar reference image, treat that image as the source of truth for identity only. Do not infer, restyle, beautify, age-shift, gender-shift, or re-cast the person. Keep the same creator label, persona, voice, wardrobe policy, and identity lock across all avatar-on-camera scenes. In image-to-video mode, appearance belongs to the reference image; text should control only motion, expression dynamics, speaking state, camera behaviour, product handling, and the category-selected environment. Never copy the avatar reference background, room, furniture, wall decor, lighting setup, camera crop, props, or lifestyle context.

# ENVIRONMENT CONTROL
Default environment settings are background_consistency=strict, environment_override=false, preserve_original_scene_layout=false, environment_selection=category_auto. Always choose one simple category-appropriate real environment from product category, target audience, market, campaign context, and creative angle. Keep it calm, plausible, and consistent across scenes. Do not preserve or copy the avatar reference background. Do not preserve product-reference room/background unless the user explicitly requests reference-scene preservation. Only enhance realism, lighting consistency, camera behaviour, and subtle handheld motion. No random fake influencer apartments, architecture changes, decorative props unrelated to the product context, blank studio, or catalog background.

# PRODUCT ENVIRONMENT LOCK
Treat the product reference as a product-only identity source for generated ecommerce scenes. It controls the product appearance, material, colour, markings, dimensions, and scale, but not the generated environment. Pick the simplest category-appropriate real context, target-audience context, and human scale context. For ecommerce and dropshipping fidelity, scene_summary must support product visibility, realistic scale, and safe framing without competing with product fidelity.

# CAMERA STYLE
UGC style belongs to camera behaviour, not to background invention: phone camera framing, slight handheld sway, static shot, slow push-in, imperfect centering, natural focus, and real-camera exposure. Avoid complex camera moves that cause identity drift or product shape drift.

# UGC AUTHENTICITY
Authenticity comes from motion, expression dynamics, speaking cadence, micro-pauses, occasional brief glance away, natural pacing, and simple product handling. Do not create authenticity by adding lifestyle clutter, new props, or a redesigned room.

# DROPSHIPPING REALISM
For dropshipping ecommerce, make the output feel like a real buyer-check clip, not a polished brand commercial. Prioritize believable product scale, visible finish, fit, handling, and simple use context. Keep expression modest, camera ordinary, and motion simple. Avoid luxury staging, showroom lighting, glossy retouching, cinematic grading, fake social proof, fake discounts, and overproduced ad energy. Do not describe ecommerce UGC as cinematic, professional, stunning, 8k, studio, perfect, premium commercial, or fashion editorial.

# BACKGROUND FREEDOM LEVEL
Use strict background consistency by default for the selected category-auto environment. Background freedom is allowed only when the user explicitly asks for an environment change or sets environment_override=true. The avatar reference background is never a scene reference. Product references are treated as product identity references unless the user explicitly asks to preserve a specific product-scene background.

# SCENE_SUMMARY RULES
scene_summary is a single comma-separated descriptor sequence in this exact order: [ACTION CONTEXT], [SETTING], [CAMERA - angle, distance, movement], [LIGHTING], [MOOD]. When avatar is on camera, do not repeat person action if already in avatar_instruction. Camera movement is simple only: static, slight handheld sway, or slow push-in. Avatar-on-camera scenes include UGC authenticity markers from camera/delivery only: available natural window light, warm lamp light mixed color temperature, slight handheld camera sway, off-center framing, occasional brief glance away from camera, natural conversational pacing. Setting must be category-selected, not copied from the avatar reference. Choose one simple specific real space fitting the product category, audience, market, and angle; keep it minimal and do not add lifestyle clutter. Never use empty studio, white cyclorama, fake influencer apartment, copied avatar background, redesigned room, or unrequested decorative props.

# FIDELITY RULES
fidelity is a short comma-separated directive locking product appearance. Build from the verified product brief: shape, color, finish, visible markings, and packaging if present. Always include product not modified, not restyled, not recolored, not rebranded at the end.

# VOICEOVER RULES
voiceover is the exact spoken line in the output language, delivered as visible on-camera avatar speech, not off-camera narration over silent footage. The generated creator must visibly speak the line with natural mouth, jaw, cheek, blink, and micro-expression movement. For UK/GB English, use natural British English phrasing and assume a subtle everyday British accent in delivery. Max 25 words per 5s scene and max 50 words per 10s scene. Write like a real creator talking on camera: natural contractions, clear articles, and short spoken clauses. Avoid robotic category labels such as "comparing handbag", passive phrasing such as "it is shown", generic filler such as "real detail" as a full sentence, and production-direction phrases such as "I'd show", "I'd check", "this scene shows", "angle:", "visual direction", or "hook intent". No medical claims, no fake proof, no forbidden testimonial claims. If persona_allows_first_person_testimonial=false, do not say I bought, I've used, I own, I tried, for me it, or similar ownership or usage claims. Use customer-facing creator speech about the product and why the viewer should care, not a description of what the prompt or skill is doing.

# GENERATED TEXT RULES
For ecommerce UGC videos, render no generated on-screen text. Do not render hook stickers, subtitles, captions, lower thirds, hook labels, CTA text, floating text, title cards, or random words inside the generated video. The spoken avatar audio carries the hook and message. All captions should be added later in post-production where typography, spelling, and safe-area placement can be controlled. Never render product_info notes, prompt labels, JSON keys, platform instructions, random text, button-like CTA text, "click", "tap", URLs, platform UI, or ad-control wording. The only visible words allowed are verified product markings already present on the product reference, or an exact requested personalization word printed on the product.

# ON_SCREEN_TEXT RULES
For ecommerce, on_screen_text.text is post-production metadata only. Keep it short, concrete, scannable, and in the requested language for later editing, but do not ask the video model to draw it inside the generated ecommerce UGC video. Put the hook into voiceover when it needs to appear in the generated video.

# NO IN-CREATIVE CTA BUTTONS
The ad platform supplies the final button, destination URL, and click target. Do not put button-like CTA text, fake UI, clickable controls, "click", "tap", "ad button", "CTA button", "learn more", "shop now", "view details", "open detail", or equivalent wording into voiceover, on_screen_text, scene_summary, static image overlay, carousel card text, or image prompts. A scene may have purpose="cta" only as a legacy schema label for a closing beat; it should be phrased as decision support, final product recap, or a plain non-clickable product-name CTA such as "BELLA Leather Tote" or "Shop BELLA today" when the product label is verified. Never invent limited stock, free delivery, discounts, prices, or availability unless supplied by the input.

# SAFETY
Never produce medical, therapeutic, curative, transformation, invented brand, certification, award, review, rating, social proof, discount, scarcity, superlative, status-signaling, competitor comparison, children under 16, public figure, copyrighted character, or copyrighted music claims unless explicitly whitelisted by input.permitted_claims. Rewrite unsafe claims into curiosity, demonstration, sensory description, aesthetic appeal, or lifestyle fit and log each change in safety_rewrites with original_claim, reason_removed, and replacement_angle.

# SAFE AREAS
For 9:16 keep avatar face and product within central 80% vertical band, with top 14% reserved and bottom 20% reserved. Do not place generated text over the video. For 1:1 and 16:9 use central 90% on all sides. Ecommerce UGC safe areas are primarily for face/product; no generated text is allowed.

# DURATION COMPOSITION
Use native Seedance segments: 15s -> [5,5,5] or [5,10]; 20s -> [10,10] or [5,5,10]; 30s -> [10,10,10] or [5,10,10,5]. For ecommerce UGC, every scene must set avatar_on_camera=true and keep the creator visible. First scene is purpose=hook. Last scene is purpose=cta, with cta interpreted as closing product recap.

# MULTI-SCENE IDENTITY CHAIN
For multi-scene ecommerce UGC variants, scene 1 uses original_avatar reference and all later scenes keep avatar_on_camera=true using previous_scene_last_frame. Each scene prompt must be self-contained and not refer to "the first frame" or "as shown before". Avoid non-avatar product-only scenes.

# OUTPUT SCHEMA
Return exactly this JSON shape: {"variants":[{"variant_id":"v1","total_duration_seconds":15,"language":"en","market":"UK","platform":"meta","aspect_ratio":"9:16","seedance_mode":"image_to_video","reference_image_strategy":"original_avatar_for_first_scene_then_last_frame_chain","environment_control":{"background_consistency":"strict","environment_override":false,"preserve_original_scene_layout":false,"environment_selection":"category_auto","directive":"choose one simple category-appropriate real setting; avatar reference controls identity only"},"scenes":[{"scene_id":"s1","purpose":"hook","duration":5,"avatar_on_camera":true,"use_reference_image":true,"reference_image_source":"original_avatar","avatar_instruction":"subject from reference image, identity preserved, no facial morphing, no appearance drift, looking directly into camera and speaking naturally, neutral relaxed expression with subtle smile forming, mouth, jaw, and lips visibly moving in sync with the approved spoken script, wardrobe as in reference image, unchanged","scene_summary":"creator intro with product visible, category-selected minimal real setting, medium close shot with slight handheld camera sway and off-center framing, consistent natural light, natural conversational pacing","fidelity":"visible product shape and colors preserved, product not modified, not restyled, not recolored, not rebranded","voiceover":"Exact spoken line","on_screen_text":{"text":"Max six words","position":"bottom_center"},"framing_notes":"Keep avatar face, speaking mouth, and product inside central safe area; environment selected from category/context, not copied from avatar reference"}],"stitching":{"transition_style":"hard cut","cut_timing_notes":"Cut on natural sentence endings"},"safety_rewrites":[],"hypothesis":"Buyer psychology + visual proof + why this variant may work"}]}.

# ABSOLUTE RULES
avatar_instruction never contains static appearance descriptors when use_reference_image=true. It always begins with subject from reference image, identity preserved, no facial morphing, no appearance drift when use_reference_image=true. Ecommerce variants must set avatar_on_camera=true for every scene and must not use product-only/no-person insert shots. Durations sum exactly to total_duration_seconds. Output is only the JSON object."""

CONTENT_PROMPT_TASK = (
    "Create one structured variant for the selected product and the user's AI avatar. "
    "Use the requested language, market, platform, aspect ratio, and duration from the input. "
    "Build scenes that compile into a single OpenRouter /videos prompt while keeping the scene schema intact. "
    "Use a clear UGC narrative: hook, buyer problem/desire, practical proof, quality/detail proof, lifestyle context, and closing product recap; for short videos merge these into compact beats without random shot order. "
    "Voiceover must be the ad message the avatar says to the viewer, never production direction about what the model or skill should show. "
    "Keep the selected avatar/creator visibly present in every scene for trust; product proof can be close-up, but it must be creator-held, creator-worn, or framed with face/torso/hands visible, never a no-person product-only insert. "
    "Choose one creative thesis before writing: buyer psychology plus visible proof. Make the first 1-2 seconds "
    "visually specific enough to stop scrolling through scale, texture, hand interaction, movement, category context, "
    "or a clear before-buying decision tension. "
    "Pull product details only from the verified product brief; treat product_info and internal_brief_notes "
    "as guidance, never as raw voiceover or on-screen text. Translate any note-derived detail into the selected output language before using it in voiceover, post-production captions, ad copy, or scene text. Match avatar voice and register to the audience "
    "and market - for UK/GB English use natural British English phrasing and a subtle everyday British creator accent; "
    "sound like this specific persona, not a generic creator. Keep every line within "
    "permitted claims. Use category-auto environment selection: choose a simple product-appropriate setting from category, use case, market, and campaign context. "
    "Do not copy the avatar reference background, and do not preserve a product-reference room unless the user explicitly asks for reference-scene preservation. Keep background_consistency=strict, environment_override=false, "
    "preserve_original_scene_layout=false as default scene rules; put UGC style into camera, motion, "
    "speaking cadence, and product handling rather than random furniture, props, or room redesign. "
    "For handbags/totes, prioritize an elegant-but-practical hook, bag in hand and on shoulder, capacity or scale proof, verified material texture, stitching, handles, interior lining, lifestyle carry context, and a plain product-name recap when supported by the brief. "
    "Avoid robotic category wording like comparing handbag, passive phrasing like "
    "it is shown, and production-direction phrasing like I'd check, I'd show, this scene shows, angle:, visual direction, or hook intent. "
    "Use natural customer-facing creator speech about the product and why the viewer should care, without implying ownership or personal use. Avoid repeating the same detail-check framing across all scenes; give each scene a distinct "
    "job such as hook, proof, context, contrast, or closing recap. Rewrite any unsafe beat into a curiosity, demonstration, sensory, or aesthetic-fit "
    "frame and log it in safety_rewrites with original_claim, reason_removed, and replacement_angle. "
    "Return only the JSON object defined in the system prompt output schema."
)

BASE_VIDEO_PROMPT_TEMPLATE = (
    "Seedance image-to-video realistic creator product video, Aspect ratio {aspect_ratio}, {duration}s duration, platform {platform}, market {market}, language {language}. "
    "{avatar_instruction}, {scene_summary}, {fidelity}, dialogue \"{voiceover}\" spoken out loud in {language}. Voice profile: {voice_profile}. Generate audible natural speech, exact lip-sync, natural conversational pacing, and slight breath sounds; the avatar must not be silent. "
    "This must read as live on-camera speech from the visible avatar, not off-camera narration: keep the creator face and mouth visible during spoken beats, with lips, jaw, cheeks, blink, and small expression movement articulating the line. Do not hide the mouth behind phone, product, hand, hair, or crop. "
    "Geometry contract: preserve normal smartphone 9:16 framing and natural adult human proportions; no fisheye, ultra-wide stretch, anamorphic scaling, mirror warp, elongated limbs, oversized head, tiny hands, squeezed torso, letterboxing, pillarboxing, or aspect-ratio stretch. "
    "Category prompt: {category_prompt}. "
    "Environment control: {environment_control}. "
    "Optional extra video direction: {video_extra_prompt}. "
    f"{AVATAR_IDENTITY_ONLY_ENVIRONMENT_LOCK} "
    f"{CATEGORY_AUTO_ENVIRONMENT_LOCK} "
    f"{PRODUCT_IDENTITY_HARD_LOCK} "
    "Story contract: first 2 seconds must contain one clear spoken hook and product visible; then show practical proof, quality/detail proof, lifestyle context, and final product recap. For handbags/totes, show hand/shoulder carry, capacity or scale proof, verified material texture, stitching, handles, opening/interior when visible, and one simple real context such as office doorway, cafe entrance, hallway, mirror, commute, parked-car-seat transition, or leaving-home moment when relevant. "
    "Reference contract: product reference image controls product shape, colour, material, markings, scale, and fidelity. "
    "Dropshipping realism contract: real buyer-check clip, not polished brand commercial. Use ordinary phone exposure, modest expression, simple real spaces, practical product proof, believable scale, and visible product finish. Avoid luxury staging, glossy retouch, cinematic grading, fake social proof, fake discounts, and overproduced ad energy. Do not describe ecommerce UGC as cinematic, professional, stunning, 8k, studio, perfect, premium commercial, or fashion editorial. "
    "Visible text contract: render no generated on-screen text in ecommerce creator video. Do not render hook stickers, subtitles, captions, title cards, prompt labels, scene labels, JSON/key names, lower thirds, hook labels, CTA text, floating text, internal words such as UGC, ad, structured prompt, voiceover, caption contract, product_rules, or time_range. Spoken audio carries the hook and message; all captions are for post-production only. "
    "Text quality contract: if product text is visible, keep only verified product markings from the reference or an exact requested personalization word printed on the product, stable, correctly spelled, and fully inside safe area. No scrambled letters, mirrored text, melting text, partial letters, or random extra words. If clean product text is uncertain, render no visible text. "
    f"{PRODUCT_REFERENCE_ROLE_LOCK} "
    "Hand quality contract: show hands only when needed for product handling; use relaxed adult hands, one object per hand action, natural finger count, stable grip, and slow motion. Crop hands at frame edge if uncertain; no fused, extra, missing, twisted, elongated, or melting fingers. "
    "identity locked to reference image when avatar reference is supplied, no face morphing, no feature drift, no frozen face, no closed-mouth speech, no distorted body proportions, smartphone footage shot on phone front camera, "
    "available natural light, slightly imperfect framing, unpolished, raw, no cinematic grading, no color correction, amateur creator self-recording. "
    "Authenticity must come from motion, camera sway, expression dynamics, and speaking cadence, not from redesigning the background. "
    "Use the avatar reference image only when use_reference_image is true and only for identity. Use the product reference image for strict product fidelity only; choose environment from product category/context. "
    "Keep all critical content inside platform safe areas. Negative prompt: {negative_prompt}"
)

ENVIRONMENT_CONTROL_DEFAULTS: dict[str, Any] = {
    "background_consistency": "strict",
    "environment_override": False,
    "preserve_original_scene_layout": False,
    "environment_selection": "category_auto",
    "directive": (
        "Use category-auto environment selection for ecommerce creator videos. "
        "Avatar reference controls identity only and must not supply the room, furniture, wall decor, props, lighting setup, or lifestyle context. "
        "Product reference controls product appearance only and must not supply the generated room/background unless the user explicitly requests reference-scene preservation. "
        "Choose one simple category-appropriate environment from product type, use case, market, and campaign context, then keep it consistent across scenes. "
        "Do not automatically choose a home/apartment interior for every ecommerce product; use commute, office, cafe, street doorway, outdoor threshold, or product-specific real contexts when they better explain the product. "
        "Only enhance realism, lighting consistency, camera behaviour, and subtle handheld motion. "
        "No random furniture, architecture changes, decorative props unrelated to the product, fake influencer apartment staging, or copied avatar-reference background."
    ),
}

CATEGORY_PROMPT_PRESETS: dict[str, dict[str, str]] = {
    "handbag": {
        "label": "Handbags / tote bags",
        "system_prompt": (
            "Handbag and tote bag preset: prioritise exact silhouette, handles, strap attachment, stitching, opening, structure, scale, and visible interior only when supplied by the verified brief or image. "
            "Handbag size consistency is critical: preserve the same bag size, body-to-bag proportion, handle length, strap drop, width/height/depth ratio, and shoulder/hand carry scale across every scene and every generated asset. Do not turn a shoulder bag into a tote, clutch, mini bag, crossbody, oversized shopper, or different bag type. "
            "Show the bag as a practical everyday accessory for work, errands, and travel context when supported. Avoid status-brand framing, fake capacity claims, and any change to leather, finish, colour, hardware, shape, or brand markings."
        ),
        "video_directive": (
            "For handbag creator video, use the fixed buyer story: hook -> practical problem/desire -> capacity or scale proof -> premium detail proof -> outfit/lifestyle context -> product-name closing recap. "
            "Open with a strong elegant-but-practical hook such as 'Finally, a tote that looks elegant and still fits the daily essentials' when capacity is supported. "
            "Show the bag in hand and on shoulder. If the brief supports capacity/interior space, show tablet or slim notebook, water bottle, wallet, phone, keys, and makeup pouch going inside one by one; otherwise use those items only as nearby scale context and do not claim they fit. "
            "Show close-ups of verified material texture, stitching, handles, opening, and interior lining when visible. End with lifestyle carry such as leaving home, mirror outfit check, or natural walk, plus a plain product recap like 'PRODUCT_NAME tote - elegant, spacious, everyday' when spaciousness is supported. "
            "Keep the same bag size and carry scale from shot to shot. Use simple camera movement, natural light, UK/Scandinavian minimalist styling, warm neutral colours, and specific real spaces such as office doorway, cafe entrance, quiet street doorway, commute moment, hallway, desk, kitchen table, or parked car seat. No random text, robotic subtitles, exaggerated smile, status logos, distorted hands, or changing bag shape."
        ),
        "image_directive": (
            "For handbag static images, default to the bag being carried, worn on shoulder, held in hand, or placed directly against an adult person's outfit/body context so every image has human scale and styling relevance. "
            "C2 should show a person-led decision moment, C3 an outfit-and-scale lifestyle creative on or beside a person, C4 a close detail of handles, stitching, hardware, opening, or material texture while the bag is being held/carried, and C5 a card-by-card detail sequence with human context on every card. "
            "Across C2, C3, C4, and C5, keep the handbag the same size relative to the adult body and hands; preserve silhouette, width, height, depth, handle length, strap drop, and carry position. "
            "Faces may be cropped or turned away; use adults only, no public figures, no children, no stock-photo glamour poses. Use keys, notebook, coat, phone, travel card, or laptop only as secondary scale/context props; never imply unverified capacity."
        ),
    },
    "shoes": {
        "label": "Shoes / footwear",
        "system_prompt": (
            "Shoes preset: prioritise exact upper shape, sole profile, closure, stitching, visible texture, toe shape, heel height, outsole view, and side profile from the product reference. "
            "Show styling and visible construction only. Avoid orthopaedic, pain relief, posture, medical, comfort, fit guarantee, weight-loss, or transformation claims unless explicitly permitted."
        ),
        "video_directive": (
            "For shoes creator video, use a quick on-camera hook, then low-angle or hand-held close-ups of side profile, sole, upper, and styling context, then a creator closing beat. "
            "Keep movement simple: static, slight handheld sway, or slow push-in. Do not show aggressive walking/running claims unless supplied and permitted."
        ),
        "image_directive": (
            "For shoes static images, default to shoes being worn by an adult person in a real outfit context. Make C2 a person-led detail-confidence check, C3 a real outfit styling/scale scene, C4 a macro sole or upper construction crop while worn or held, and C5 a sequence from worn hero, side profile, material detail, scale, and final product-detail reminder. "
            "Faces may be cropped out; use adults only, no children. No medical or comfort labels; annotate only visible features."
        ),
    },
    "apparel": {
        "label": "Apparel / clothing",
        "system_prompt": (
            "Apparel preset: prioritise exact garment cut, drape, seam placement, neckline, sleeve, hem, visible material finish from the reference, closure, pattern, and colour from the product reference and verified brief. "
            "Show movement, layering, and outfit context without body transformation, slimming, sizing guarantee, age, gender, or performance claims."
        ),
        "video_directive": (
            "For apparel creator video, always show the garment worn on a full-body or near full-body adult creator view first: head-to-toe or complete outfit silhouette, garment length, hem, sleeves/straps, drape, and body-to-garment scale visible. "
            "Use avatar-on-camera intro, then simple mirror or outfit-detail b-roll showing drape, seam, visible reference finish, and styling context, then an avatar closing beat. Detail close-ups may appear only after the full worn silhouette is established, and the video must not crop only to face, chest, waist, hands, flat lay, or isolated fabric. "
            "Make the apparel video feel like a normal phone try-on check, not a polished ecommerce model shoot: modest expression, small natural turn, relaxed arms, no runway posing, no glamour smile, no beauty-retouch look. "
            "Use one category-selected minimal outfit context such as cafe entrance, quiet street doorway, office lift lobby, outdoor doorway, clean mirror, or wardrobe edge with natural light and slight handheld camera sway; do not copy avatar-reference background or preserve product-reference room unless explicitly requested."
        ),
        "image_directive": (
            "For apparel static images, default to the garment being worn by an adult person in a real outfit context. Make C2 a person-led detail-check creative around garment cut, C3 an outfit identity creative, C4 a macro seam/closure/visible-finish crop while worn or held, and C5 a sequence from worn hero, fit context, visible detail, styling idea, and final product-detail reminder. "
            "Faces may be cropped out; use adults only, no children. Do not invent fit, sizing, material, or body outcome claims."
        ),
    },
}

PROMPT_SOURCE_INVENTORY: dict[str, Any] = {
    "purpose": "Make every prompt/copy layer visible and show which parts come from user input versus backend safety defaults.",
    "data_priority": [
        "product_name",
        "product_info",
        "product_reference_url or uploaded product_image",
        "visual_product_understanding from product image classifier when available",
        "avatar_reference_url or selected avatar",
        "selected product_category and category prompt override",
        "UI prompt overrides",
        "backend defaults only when a required field is missing or safety structure is needed",
    ],
    "editable_ui_fields": [
        "content_prompt_system",
        "content_prompt_task",
        "base_video_prompt_template",
        "ugc_video_extra_prompt",
        "negative_prompt",
        "category_prompt_handbag",
        "category_prompt_shoes",
        "category_prompt_apparel",
        "custom_avatar_name",
        "custom_avatar_persona",
        "custom_avatar_voice",
        "avatar_wardrobe_policy",
        "avatar_identity_note",
        "use_avatar_image_reference",
        "background_consistency",
        "environment_override",
        "preserve_original_scene_layout",
    ],
    "runtime_prompt_layers": [
        {
            "layer": "Product Intake Agent",
            "source": "user product_name, product_info, product_category, and product image reference",
            "editable_in_ui": "product_category",
            "output_fields": [
                "known_product_facts",
                "user_provided_facts",
                "safe_benefits",
                "ad_safe_detail_phrases",
            ],
            "backend_role": "Extract safe product facts and classify risky claims; does not create ad copy.",
        },
        {
            "layer": "Visual Product Classifier Agent",
            "source": "product_reference_url or uploaded product_image plus safe product context",
            "editable_in_ui": "product image/reference URL and product_category; user-selected category remains authoritative",
            "output_fields": [
                "visual_product_understanding",
                "visual_subcategory",
                "visual_scenario_rules",
                "visual_shot_requirements",
                "visual_qa_expectations",
            ],
            "backend_role": "Uses a vision model to classify what is actually in the product image and recommend category-specific UGC template, shot requirements, and QA expectations.",
        },
        {
            "layer": "UGC Strategy Agent",
            "source": "product_analysis plus selected platform/language/duration/avatar settings",
            "editable_in_ui": "custom_avatar_voice influences voice profile direction; avatar persona influences creator tone",
            "output_fields": [
                "hook",
                "scene_by_scene_script",
                "voiceover",
                "voice_profile",
                "on_screen_text",
                "subtitles",
            ],
            "backend_role": "Deterministic fallback script using user_provided_facts first, category defaults only when facts are missing.",
        },
        {
            "layer": "Ad Angle Multiplier",
            "source": "product_analysis, UGC hook, safe product details, language and market settings",
            "editable_in_ui": "indirectly via product notes, selected language, category and creative memory signals",
            "output_fields": [
                "ad_angle_multiplier.angles",
                "ad_angle_multiplier.hook_bank",
                "creative_angles",
            ],
            "backend_role": "Expands one core idea into 10-15 materially distinct Pain/Desire/Proof/Identity/Contrarian/Urgency angles for creative testing.",
        },
        {
            "layer": "Ad Angle Selector",
            "source": "ad_angle_multiplier, performance memory, creative_memory_rag, seed category priors, and C1-C5 slot roles",
            "editable_in_ui": "indirectly via ratings, performance import, product category, platform, market and language",
            "output_fields": [
                "ad_angle_selector.slot_selection",
                "ads_creative_set.static_image_ads[*].angle_selection_reason",
                "ads_creative_set.carousel_ad.angle_selection_reason",
            ],
            "backend_role": "Scores every angle and chooses the best slot-specific angle using role priors plus memory winners and avoid patterns.",
        },
        {
            "layer": "Content Prompt Engineer Agent",
            "source": "UGC strategy, product_analysis, avatar, editable base_video_prompt_template/negative_prompt, and optional extra UGC video direction",
            "editable_in_ui": "base_video_prompt_template, ugc_video_extra_prompt, and negative_prompt",
            "output_fields": [
                "product_fidelity_instruction",
                "avatar_consistency_instruction",
                "avatar_identity_contract",
                "seedance_video_prompt",
                "structured_scene_prompt",
                "ugc_video_extra_prompt",
                "meta_ads_copy",
                "google_youtube_ads_copy",
                "category_prompt_directive",
                "environment_control",
            ],
            "backend_role": "Builds the local prompt package before optional OpenRouter prompt enhancement and injects the selected category prompt into Seedance prompts.",
        },
        {
            "layer": "OpenRouter Prompt Client",
            "source": "editable content_prompt_system/content_prompt_task plus JSON payload containing current prompt package",
            "editable_in_ui": "prompt_model, content_prompt_system and content_prompt_task",
            "output_fields": [
                "prompt_generation",
                "structured_scene_prompt",
                "seedance_payload.prompt",
            ],
            "backend_role": "Optional model enhancement. If it fails or no API key exists, deterministic prompts remain visible.",
        },
        {
            "layer": "Ads Creative Set Agent",
            "source": "product_analysis, UGC strategy, C1-C5 media plan, and platform copy specs",
            "editable_in_ui": "category prompt preset fields influence category-specific visual direction",
            "output_fields": [
                "creative_plan",
                "static_image_ads",
                "carousel_ad",
                "meme_style_creatives",
                "primary_text_variants",
                "ad_description_suggestions",
                "category_image_directive",
            ],
            "backend_role": "Creates the complete ads set from user-provided product facts and safe marketing templates.",
        },
        {
            "layer": "OpenRouter Image Client",
            "source": "ads_creative_set visual prompts refined by prompt_model when an API key is available, plus product reference image",
            "editable_in_ui": "image_model, max_static_images as cap only, image_size",
            "output_fields": [
                "static_image_generation.static_prompt_generation",
                "static_image_generation.image_assets[*].prompt",
            ],
            "backend_role": "Turns each selected creative into an image generation prompt and deduplicates identical prompts after optional GPT prompt refinement.",
        },
        {
            "layer": "OpenRouter Seedance Client",
            "source": "content_prompt_package.seedance_payload.prompt and public input references",
            "editable_in_ui": "seedance_model, resolution, use_avatar_image_reference, avatar_reference_url, avatar_wardrobe_policy",
            "output_fields": [
                "video_generation.submitted_payload",
            ],
            "backend_role": "Submits only the final visible prompt/payload to /videos.",
        },
    ],
    "guardrails": [
        "product_info is internal guidance and is converted into short verified facts, not copied verbatim into ad copy",
        "product reference image is the source of truth for product appearance",
        "avatar reference is used only when explicitly enabled for image-to-video",
        "CTA URLs, button labels, and click/tap instructions are not written into creative copy or visual prompts because the ad platform supplies those controls",
        "compliance and fidelity guards can block generation and return failure_reason",
    ],
}


def defaults() -> dict[str, Any]:
    return {
        "negative_prompt": NEGATIVE_PROMPT,
        "content_prompt_system": CONTENT_PROMPT_SYSTEM,
        "content_prompt_task": CONTENT_PROMPT_TASK,
        "base_video_prompt_template": BASE_VIDEO_PROMPT_TEMPLATE,
        "environment_control_defaults": ENVIRONMENT_CONTROL_DEFAULTS,
        "prompt_source_inventory": PROMPT_SOURCE_INVENTORY,
        "category_prompt_presets": CATEGORY_PROMPT_PRESETS,
    }
