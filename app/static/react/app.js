/* global React, ReactDOM */
(() => {
  const { useEffect, useMemo, useRef, useState } = React;
  const h = React.createElement;

  const qs = new URLSearchParams(window.location.search);
  if ("scrollRestoration" in window.history) {
    window.history.scrollRestoration = "manual";
  }
  const AUTHORIZED_AVATAR_CONSENT_TEXT = "Souhlasím s použitím mé podoby jako AI avatara pro tvorbu reklamních videí pro zvolený brand/projekt, včetně úprav, lip-syncu a generování nových scén.";
  const AUTHORIZED_AVATAR_CONSENT_HELP = "Zapni jen pro svoji podobu nebo pro osobu/avatara, kde máš souhlas k reklamnímu použití.";
  const storedAvatarId = window.localStorage.getItem("active_avatar_id") || "";
  const hasInitialAvatarOverride = qs.has("avatar_id") || Boolean(storedAvatarId);
  let storedAvatarProfile = {};
  try {
    storedAvatarProfile = JSON.parse(window.localStorage.getItem("active_avatar_profile") || "{}");
  } catch (error) {
    storedAvatarProfile = {};
  }
  const initialForm = {
    app_mode: qs.get("app_mode") || "ecommerce",
    product_name: qs.get("product_name") || "",
    product_info: qs.get("product_info") || "",
    product_category: qs.get("product_category") || "auto",
    product_reference_url: qs.get("product_reference_url") || qs.get("product_image") || "",
    competitor_strategy_enabled: (qs.get("competitor_strategy_enabled") || "false") === "true",
    competitor_name: qs.get("competitor_name") || "",
    competitor_url: qs.get("competitor_url") || "",
    competitor_chat_brief: qs.get("competitor_chat_brief") || "",
    competitor_screenshot_notes: qs.get("competitor_screenshot_notes") || "",
    avatar_id: qs.get("avatar_id") || storedAvatarId || "avatar1",
    custom_avatar_name: qs.get("custom_avatar_name") || storedAvatarProfile.name || "Můj AI avatar",
    custom_avatar_persona: qs.get("custom_avatar_persona") || storedAvatarProfile.style || "natural UGC creator, calm and direct, slightly imperfect delivery",
    custom_avatar_voice: qs.get("custom_avatar_voice") || storedAvatarProfile.voice || "natural British English creator voice, relaxed and conversational",
    avatar_wardrobe_policy: qs.get("avatar_wardrobe_policy") || "reference_unchanged",
    avatar_reference_url: qs.get("avatar_reference_url") || storedAvatarProfile.image_url || "https://i.ibb.co/6082rzf9/newkoi.png",
    avatar_identity_note: qs.get("avatar_identity_note") || "",
    avatar_own_person_consent: (qs.get("avatar_own_person_consent") || "true") !== "false",
    use_avatar_image_reference: (qs.get("use_avatar_image_reference") || "true") !== "false",
    platform: qs.get("platform") || "meta",
    market: qs.get("market") || "UK",
    language: qs.get("language") || "en",
    generation_mode: qs.get("generation_mode") || "both",
    video_length: qs.get("video_length") || "15",
    resolution: qs.get("resolution") || "720p",
    seedance_model: qs.get("seedance_model") || "bytedance/seedance-2.0-fast",
    prompt_model: qs.get("prompt_model") || "openai/gpt-5.4-mini",
    image_model: qs.get("image_model") || "google/gemini-3-pro-image-preview",
    max_static_images: qs.get("max_static_images") || "8",
    image_size: qs.get("image_size") || "1K",
    openrouter_api_key: qs.get("openrouter_api_key") || "",
    landing_page_url: qs.get("landing_page_url") || "",
    content_prompt_system: "",
    content_prompt_task: "",
    base_video_prompt_template: "",
    ugc_video_extra_prompt: qs.get("ugc_video_extra_prompt") || "",
    finance_video_topic: qs.get("finance_video_topic") || "",
    finance_video_script: qs.get("finance_video_script") || "",
    finance_disclaimer: qs.get("finance_disclaimer") || "Vzdělávací obsah, nejde o individuální investiční ani finanční doporučení.",
    finance_allow_series: (qs.get("finance_allow_series") || "true") !== "false",
    finance_series_confirmed: false,
    finance_generate_sample_first: true,
    finance_scene_approved: false,
    finance_scene_reference_url: "",
    finance_scene_video_reference_url: "",
    finance_scene_prompt: "",
    finance_scene_concept_json: "",
    background_consistency: qs.get("background_consistency") || "strict",
    environment_override: (qs.get("environment_override") || "false") === "true",
    preserve_original_scene_layout: (qs.get("preserve_original_scene_layout") || "true") !== "false",
    negative_prompt: "",
    category_prompt_handbag: "",
    category_prompt_shoes: "",
    category_prompt_apparel: ""
  };

  const navItems = [
    ["dashboard", "D", "Přehled"],
    ["studio", "N", "Nová kampaň"],
    ["avatars", "V", "Avatar set"],
    ["library", "C", "Creative sety"],
    ["prompt-lab", "P", "Prompt laboratoř"],
    ["analytics", "A", "Analýza"],
    ["settings", "S", "Nastavení"]
  ];

  const pipelineSteps = [
    "Analýza produktu",
    "Analýza publika",
    "Psychologie kreativy",
    "UGC strategie",
    "Tvorba promptů",
    "Generování videa",
    "Generování obrázků",
    "Učení kreativ"
  ];

  const financePipelineSteps = [
    "Finance Script Agent",
    "Kontrola délky scénáře",
    "Banana scene concept",
    "Schválení scény",
    "Tvorba promptů",
    "Compliance guard",
    "Seedance video",
    "Export ukázky",
    "Učení kreativ"
  ];

  function viewFromHash() {
    const hash = (window.location.hash || "").replace("#", "");
    const routes = {
      "dashboard": "dashboard",
      "new-campaign": "studio",
      "studio": "studio",
      "avatars": "avatars",
      "avatar-set": "avatars",
      "creative-sets": "library",
      "library": "library",
      "prompt-lab": "prompt-lab",
      "analytics": "analytics",
      "settings": "settings"
    };
    return routes[hash] || "dashboard";
  }

  function apiJson(url, options) {
    return fetch(url, options).then(async (response) => {
      const text = await response.text();
      const data = text ? JSON.parse(text) : {};
      if (!response.ok) throw new Error(data.error || data.reason || `HTTP ${response.status}`);
      return data;
    });
  }

  function cls(...items) {
    return items.filter(Boolean).join(" ");
  }

  function text(value, fallback = "n/a") {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  }

  function limit(value, size = 110) {
    const str = text(value, "");
    return str.length > size ? `${str.slice(0, size)}...` : str;
  }

  function categoryPresetText(preset) {
    if (!preset) return "";
    if (typeof preset === "string") return preset;
    return [
      preset.system_prompt,
      preset.video_directive,
      preset.image_directive
    ].filter(Boolean).join("\n\n");
  }

  function applyAvatarToForm(form, avatar) {
    const imageUrl = avatarReferenceUrl(avatar);
    return {
      ...form,
      avatar_id: avatar.id || form.avatar_id,
      custom_avatar_name: avatar.name || form.custom_avatar_name,
      custom_avatar_persona: avatar.style || avatar.persona || form.custom_avatar_persona,
      custom_avatar_voice: avatar.voice || form.custom_avatar_voice,
      avatar_reference_url: imageUrl,
      use_avatar_image_reference: Boolean(isPublicHttpUrl(imageUrl) && form.use_avatar_image_reference)
    };
  }

  function App() {
    const [view, setViewState] = useState(viewFromHash);
    const [form, setForm] = useState(initialForm);
    const [file, setFile] = useState(null);
    const [competitorFiles, setCompetitorFiles] = useState([]);
    const [intelligence, setIntelligence] = useState(null);
    const [learning, setLearning] = useState(null);
    const [providerCapabilities, setProviderCapabilities] = useState(null);
    const [providerValidationPreview, setProviderValidationPreview] = useState(null);
    const [serverPlanPreview, setServerPlanPreview] = useState(null);
    const [promptLearningGuidance, setPromptLearningGuidance] = useState(null);
    const [latestRun, setLatestRun] = useState(null);
    const [creatives, setCreatives] = useState([]);
    const [avatars, setAvatars] = useState([]);
    const [latest, setLatest] = useState(null);
    const [currentRun, setCurrentRun] = useState(null);
    const [settings, setSettings] = useState(null);
    const [status, setStatus] = useState("Připraveno");
    const [busy, setBusy] = useState(false);
    const [sceneBusy, setSceneBusy] = useState(false);
    const [progress, setProgress] = useState(0);
    const [toast, setToast] = useState("");
    const [commandOpen, setCommandOpen] = useState(false);
    const [theme, setTheme] = useState(() => window.localStorage.getItem("creative_os_theme") || "dark");
    const [pendingFinanceSeries, setPendingFinanceSeries] = useState(null);
    const [financeScenePreview, setFinanceScenePreview] = useState(null);
    const [filters, setFilters] = useState({ search: "", mode: initialForm.app_mode === "finance_personal_brand" ? "finance_personal_brand" : "ecommerce", type: "all", angle: "all", status: "all", product: "all", performance: "all" });
    const [libraryLayout, setLibraryLayout] = useState(() => window.localStorage.getItem("creative_layout") || "grid");

    const setView = (nextView) => {
      if (nextView === "studio") {
        const activeRun = currentRun?.generation_run || latestRun;
        if (!isActiveRunStatus(activeRun?.status)) {
          setCurrentRun(null);
          setProgress(0);
          setStatus("Připraveno");
          setToast("");
        }
      }
      setViewState(nextView);
      const hashes = {
        dashboard: "dashboard",
        studio: "new-campaign",
        avatars: "avatar-set",
        library: "creative-sets",
        "prompt-lab": "prompt-lab",
        analytics: "analytics",
        settings: "settings"
      };
      const nextHash = hashes[nextView] || nextView;
      if (window.location.hash !== `#${nextHash}`) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${nextHash}`);
      }
      window.requestAnimationFrame(() => window.scrollTo({ top: 0, left: 0, behavior: "auto" }));
    };

    useEffect(() => {
      const onHashChange = () => setViewState(viewFromHash());
      window.addEventListener("hashchange", onHashChange);
      return () => window.removeEventListener("hashchange", onHashChange);
    }, []);

    useEffect(() => {
      window.scrollTo(0, 0);
    }, []);

    useEffect(() => {
      window.scrollTo(0, 0);
    }, [view]);

    useEffect(() => {
      document.documentElement.dataset.theme = theme;
      window.localStorage.setItem("creative_os_theme", theme);
    }, [theme]);

    useEffect(() => {
      const onKeyDown = (event) => {
        const key = String(event.key || "").toLowerCase();
        if ((event.ctrlKey || event.metaKey) && key === "k") {
          event.preventDefault();
          setCommandOpen(true);
        }
        if (key === "escape") setCommandOpen(false);
      };
      window.addEventListener("keydown", onKeyDown);
      return () => window.removeEventListener("keydown", onKeyDown);
    }, []);
    const [previewAsset, setPreviewAsset] = useState(null);
    const generationInFlight = useRef(false);
    const handledRunIds = useRef(new Set());
    const confirmedSeriesRunIds = useRef(new Set());

    useEffect(() => {
      refreshAll();
      apiJson("/prompt-settings").then((payload) => {
        setSettings(payload);
        setForm((current) => ({
          ...current,
          content_prompt_system: payload.content_prompt_system || "",
          content_prompt_task: payload.content_prompt_task || "",
          base_video_prompt_template: payload.base_video_prompt_template || "",
          negative_prompt: payload.negative_prompt || "",
          background_consistency: current.background_consistency || payload.environment_control_defaults?.background_consistency || "strict",
          environment_override: current.environment_override ?? !!payload.environment_control_defaults?.environment_override,
          preserve_original_scene_layout: current.preserve_original_scene_layout ?? (payload.environment_control_defaults?.preserve_original_scene_layout !== false),
          category_prompt_handbag: current.category_prompt_handbag || categoryPresetText(payload.category_prompt_presets?.handbag),
          category_prompt_shoes: current.category_prompt_shoes || categoryPresetText(payload.category_prompt_presets?.shoes),
          category_prompt_apparel: current.category_prompt_apparel || categoryPresetText(payload.category_prompt_presets?.apparel)
        }));
      }).catch(showError);
    }, []);

    useEffect(() => {
      if (!avatars.length) return;
      const active = avatars.find((avatar) => avatar.id === form.avatar_id);
      if (!active) return;
      setForm((current) => {
        const avatarUrl = avatarReferenceUrl(active);
        if (current.avatar_id === active.id && current.avatar_reference_url === avatarUrl) return current;
        return applyAvatarToForm(current, active);
      });
    }, [avatars.length, form.avatar_id]);

    useEffect(() => {
      const activeMode = form.app_mode === "finance_personal_brand" ? "finance_personal_brand" : "ecommerce";
      setFilters((current) => (
        current.mode === activeMode
          ? current
          : { ...current, mode: activeMode, product: "all", type: "all", angle: "all", status: "all", performance: "all" }
      ));
      apiJson(`/creative-memory/creatives?limit=120&workspace=${activeMode === "finance_personal_brand" ? "finance" : "ecommerce"}`)
        .then((payload) => setCreatives(payload.creatives || []))
        .catch(() => null);
      const workspace = activeMode === "finance_personal_brand" ? "finance" : "ecommerce";
      apiJson(`/creative-intelligence?workspace=${workspace}`).then(setIntelligence).catch(() => null);
      apiJson(`/creative-memory/learning?workspace=${workspace}`).then(setLearning).catch(() => null);
      apiJson(`/generation-runs/latest?workspace=${workspace}`).then(setLatestRun).catch(() => setLatestRun(null));
    }, [form.app_mode]);

    useEffect(() => {
      if (!busy) return undefined;
      const timer = window.setInterval(() => setProgress((value) => Math.min(92, value + 7)), 900);
      return () => window.clearInterval(timer);
    }, [busy]);

    useEffect(() => {
      const activeRun = currentRun?.generation_run || latestRun;
      if (!busy && !isActiveRunStatus(activeRun?.status)) return undefined;
      const workspace = financeModeEnabled(form) ? "finance" : "ecommerce";
      const pollLatestRun = () => {
        apiJson(`/generation-runs/latest?workspace=${encodeURIComponent(workspace)}`)
          .then((run) => {
            setLatestRun(run);
            setCurrentRun((previous) => ({ ...(previous || {}), ...run, ...(run.final_output || {}), generation_run: run }));
            if (run?.monitor?.progress_percent) setProgress((value) => Math.max(value, run.monitor.progress_percent));
            if (isActiveRunStatus(run?.status)) setStatus("Generování běží");
          })
          .catch(() => null);
      };
      pollLatestRun();
      const timer = window.setInterval(pollLatestRun, 1200);
      return () => window.clearInterval(timer);
    }, [busy, form.app_mode, latestRun?.run_id, latestRun?.status, currentRun?.generation_run?.run_id, currentRun?.generation_run?.status]);

    useEffect(() => {
      const body = new FormData();
      const payloadForm = financeModeEnabled(form) ? financeModeForm(form) : form;
      ["app_mode", "generation_mode", "max_static_images", "image_model", "seedance_model", "openrouter_api_key"].forEach((key) => {
        body.set(key, payloadForm[key] ?? "");
      });
      apiJson("/creative-plan-preview", { method: "POST", body })
        .then(setServerPlanPreview)
        .catch(() => setServerPlanPreview(null));
    }, [form.app_mode, form.generation_mode, form.max_static_images, form.image_model, form.seedance_model, form.openrouter_api_key]);

    useEffect(() => {
      const payloadForm = financeModeEnabled(form) ? financeModeForm(form) : form;
      const payload = {
        app_mode: payloadForm.app_mode,
        workspace: financeModeEnabled(form) ? "finance" : "ecommerce",
        product_name: financeModeEnabled(form) ? (form.finance_video_topic || "Finance osobní brand") : form.product_name,
        product_info: financeModeEnabled(form) ? form.finance_video_script : form.product_info,
        product_category: financeModeEnabled(form) ? "finance" : form.product_category,
        platform: payloadForm.platform,
        market: payloadForm.market,
        language: payloadForm.language,
        target_audience: payloadForm.target_audience || ""
      };
      apiJson("/prompt-learning-guidance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(setPromptLearningGuidance)
        .catch(() => setPromptLearningGuidance(null));
    }, [
      form.app_mode,
      form.product_name,
      form.product_info,
      form.product_category,
      form.finance_video_topic,
      form.finance_video_script,
      form.platform,
      form.market,
      form.language
    ]);

    useEffect(() => {
      const payloadForm = financeModeEnabled(form) ? financeModeForm(form) : form;
      const payload = {
        app_mode: payloadForm.app_mode,
        generation_mode: payloadForm.generation_mode,
        product_reference_url: payloadForm.product_reference_url || "",
        avatar_reference_url: payloadForm.avatar_reference_url || "",
        use_avatar_image_reference: payloadForm.use_avatar_image_reference,
        seedance_model: payloadForm.seedance_model,
        image_model: payloadForm.image_model,
        max_static_images: payloadForm.max_static_images,
        image_size: payloadForm.image_size
      };
      apiJson("/provider-validation-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(setProviderValidationPreview)
        .catch(() => setProviderValidationPreview(null));
    }, [
      form.app_mode,
      form.generation_mode,
      form.product_reference_url,
      form.avatar_reference_url,
      form.use_avatar_image_reference,
      form.seedance_model,
      form.image_model,
      form.max_static_images,
      form.image_size
    ]);

    useEffect(() => {
      const run = currentRun?.generation_run || latestRun;
      if (!busy || !run?.run_id || isActiveRunStatus(run.status)) return;
      if (run.status === "needs_confirmation" && financeModeEnabled(form) && !confirmedSeriesRunIds.current.has(run.run_id)) {
        confirmedSeriesRunIds.current.add(run.run_id);
        const plan = run?.monitor?.latest_stage?.data?.finance_video_series || run?.final_output?.finance_video_series || {};
        generationInFlight.current = false;
        setBusy(false);
        setProgress(run?.monitor?.progress_percent || 36);
        setStatus("Čeká na potvrzení série");
        const confirmed = window.confirm(
          `Text se nevejde do jednoho 15s videa.\n\nNavržená série: ${plan.video_count || "více"} videí po 15s.\nDůvod: ${plan.reason || "obsah je delší než jedno video"}\n\nTeď se vygeneruje jen první ukázkové video. Chceš pokračovat?`
        );
        if (confirmed) {
          startGenerationRequest(true, `Generuji první ukázkové video${plan.video_count ? ` z ${plan.video_count}` : ""}`, true);
        } else {
          setToast("Generování zastaveno. Série nebyla potvrzena.");
        }
        return;
      }
      if (handledRunIds.current.has(run.run_id)) return;
      handledRunIds.current.add(run.run_id);
      generationInFlight.current = false;
      setBusy(false);
      setProgress(run?.monitor?.progress_percent || (run.status === "completed" ? 100 : 88));
      setStatus(runTerminalStatus(run));
      setToast(runTerminalToast(run));
      refreshAll().then(() => {
        if (run.status === "completed") setView("library");
      });
    }, [busy, latestRun?.run_id, latestRun?.status, currentRun?.generation_run?.run_id, currentRun?.generation_run?.status]);

    function showError(error) {
      setToast(String(error.message || error));
      setStatus("Vyžaduje pozornost");
    }

    function generationOutcome(payload, financeMode) {
      const video = payload?.video_generation || {};
      const videoStatus = String(video.video_generation_status || "").toLowerCase();
      const exportStatus = String(payload?.final_export_status || "").toLowerCase();
      const reason = video.failure_reason || video.error || payload?.provider_validation?.reason || "";
      const nextStep = video.next_step || payload?.provider_validation?.next_step || "";
      if (financeMode && videoStatus !== "completed") {
        const label = videoStatus === "skipped"
          ? "Finance video nebylo odesláno do Seedance"
          : videoStatus === "failed" || videoStatus === "blocked"
            ? "Finance video skončilo chybou"
            : "Finance video nemá hotový výsledek";
        return {
          progress: 88,
          status: label,
          openLibrary: false,
          toast: [label, reason, nextStep].filter(Boolean).join(" | ")
        };
      }
      if (exportStatus === "blocked" || videoStatus === "failed" || videoStatus === "blocked") {
        return {
          progress: 88,
          status: "Generování vyžaduje opravu",
          openLibrary: false,
          toast: ["Výsledek není hotový.", reason, nextStep].filter(Boolean).join(" | ")
        };
      }
      return {
        progress: 100,
        status: payload?.final_export_status || "Vygenerováno",
        openLibrary: true,
        toast: "Creative set uložený do memory. Můžeš hodnotit a doplnit performance."
      };
    }

    function refreshAll() {
      const workspace = financeModeEnabled(form) ? "finance" : "ecommerce";
      return Promise.allSettled([
        apiJson(`/creative-intelligence?workspace=${encodeURIComponent(workspace)}`).then(setIntelligence),
        apiJson(`/creative-memory/learning?workspace=${encodeURIComponent(workspace)}`).then(setLearning),
        apiJson("/provider-capabilities").then(setProviderCapabilities),
        apiJson(`/generation-runs/latest?workspace=${encodeURIComponent(workspace)}`).then(setLatestRun).catch(() => setLatestRun(null)),
        apiJson(`/creative-memory/creatives?limit=120&workspace=${encodeURIComponent(workspace)}`).then((payload) => setCreatives(payload.creatives || [])),
        loadAvatars(),
        apiJson("/latest-output").then(setLatest).catch(() => null)
      ]);
    }

    async function loadAvatars() {
      const payload = await apiJson("/avatars");
      const items = payload.avatars || [];
      setAvatars(items);
      if (!hasInitialAvatarOverride && payload.default_avatar_id) {
        const selected = items.find((avatar) => avatar.id === payload.default_avatar_id);
        if (selected) setForm((current) => applyAvatarToForm(current, selected));
      }
      return payload;
    }

    function update(name, value) {
      setForm((current) => ({ ...current, [name]: value }));
    }

    function setLibraryLayoutMode(mode) {
      setLibraryLayout(mode);
      window.localStorage.setItem("creative_layout", mode);
    }

    function activateAvatar(avatar) {
      if (!avatar) return;
      window.localStorage.setItem("active_avatar_id", avatar.id || "");
      window.localStorage.setItem("active_avatar_profile", JSON.stringify({
        id: avatar.id || "",
        name: avatar.name || "",
        style: avatar.style || avatar.persona || "",
        voice: avatar.voice || "",
        image_url: avatarReferenceUrl(avatar),
        preview_url: avatarPreviewUrl(avatar)
      }));
      setForm((current) => applyAvatarToForm(current, avatar));
      setToast(`Aktivní avatar: ${avatar.name || avatar.id}. Bude použitý pro další UGC generování.`);
      setStatus("Avatar aktivován");
    }

    function activateExternalAvatar(profile) {
      const avatar = {
        id: "custom_external",
        name: profile.name || "Vlastní avatar",
        style: profile.style || "authorized UGC creator avatar",
        voice: profile.voice || form.custom_avatar_voice,
        image_url: profile.image_url || "",
        preview_url: profile.image_url || ""
      };
      window.localStorage.setItem("active_avatar_id", avatar.id);
      window.localStorage.setItem("active_avatar_profile", JSON.stringify(avatar));
      setForm((current) => applyAvatarToForm(current, avatar));
      setToast("Vlastní externí avatar je aktivní pro další generování.");
      setStatus("Avatar aktivován");
    }

    async function saveAvatarProfile(profile) {
      const method = profile.id && avatars.some((avatar) => avatar.id === profile.id) ? "PUT" : "POST";
      const url = method === "PUT" ? `/avatars/${encodeURIComponent(profile.id)}` : "/avatars";
      const payload = await apiJson(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile)
      });
      await loadAvatars();
      if (payload.avatar) activateAvatar(payload.avatar);
      setToast(`Avatar uložen: ${payload.avatar?.name || profile.name || profile.id}`);
      return payload;
    }

    async function uploadAvatarProfile(profile, file) {
      const body = new FormData();
      body.set("id", profile.id || clientSlug(profile.name || "avatar"));
      body.set("avatar_id", profile.id || clientSlug(profile.name || "avatar"));
      body.set("name", profile.name || "");
      body.set("style", profile.style || "");
      body.set("voice", profile.voice || "");
      body.set("image_url", profile.image_url || "");
      body.set("is_default", profile.is_default ? "true" : "false");
      if (file) body.set("avatar_image", file);
      const payload = await apiJson("/avatars/upload", { method: "POST", body });
      await loadAvatars();
      if (payload.avatar) activateAvatar(payload.avatar);
      setToast(`Avatar přidán: ${payload.avatar?.name || profile.name}`);
      return payload;
    }

    async function makeDefaultAvatar(avatar) {
      const payload = await apiJson(`/avatars/${encodeURIComponent(avatar.id)}/default`, { method: "POST" });
      await loadAvatars();
      if (payload.avatar) activateAvatar(payload.avatar);
      setToast(`Výchozí avatar: ${payload.avatar?.name || avatar.name || avatar.id}`);
      return payload;
    }

    function buildGenerationBody(seriesConfirmed = false) {
      const body = new FormData();
      const payloadForm = financeModeEnabled(form) ? financeModeForm({ ...form, finance_series_confirmed: seriesConfirmed }) : form;
      Object.entries(payloadForm).forEach(([key, value]) => body.set(key, value));
      body.set("generate_static_images", financeModeEnabled(form) ? "false" : "true");
      body.set("testimonial_mode", "false");
      body.set("avatar_own_person_consent", payloadForm.avatar_own_person_consent ? "true" : "false");
      body.set("use_avatar_image_reference", payloadForm.use_avatar_image_reference ? "true" : "false");
      body.set("environment_override", payloadForm.environment_override ? "true" : "false");
      body.set("preserve_original_scene_layout", payloadForm.preserve_original_scene_layout ? "true" : "false");
      body.set("finance_allow_series", payloadForm.finance_allow_series ? "true" : "false");
      body.set("finance_series_confirmed", seriesConfirmed ? "true" : "false");
      body.set("finance_generate_sample_first", payloadForm.finance_generate_sample_first ? "true" : "false");
      body.set("idempotency_key", `ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}${seriesConfirmed ? "-confirmed" : ""}`);
      if (file && !financeModeEnabled(form)) body.set("product_image", file);
      if (!financeModeEnabled(form)) {
        (competitorFiles || []).forEach((item) => body.append("competitor_screenshots", item));
      }
      return body;
    }

    function handleQueuedPayload(payload) {
      if (!(payload.status === "queued" && payload.generation_run)) return false;
      handledRunIds.current.delete(payload.generation_run.run_id);
      setLatestRun(payload.generation_run);
      setCurrentRun({ ...payload, generation_run: payload.generation_run });
      setProgress(12);
      setStatus("Run spuštěn na pozadí");
      setToast("Generování běží na pozadí. Sleduj pipeline a případně použij Zastavit.");
      return true;
    }

    async function startGenerationRequest(seriesConfirmed = false, statusText = "Generuji creative set", ignoreBusy = false) {
      if (generationInFlight.current || (busy && !ignoreBusy)) {
        setToast("Generování už běží. Druhý požadavek nebyl spuštěn.");
        return;
      }
      generationInFlight.current = true;
      setBusy(true);
      setProgress(5);
      setStatus(statusText);
      setToast("");
      setCurrentRun(null);
      let backgroundQueued = false;
      try {
        let payload = await apiJson("/generation-runs", { method: "POST", body: buildGenerationBody(seriesConfirmed) });
        if (handleQueuedPayload(payload)) {
          backgroundQueued = true;
          return;
        }
        if (payload.final_export_status === "needs_confirmation" && payload.finance_video_series?.needs_confirmation) {
          const plan = payload.finance_video_series;
          setLatest(payload);
          setCurrentRun(payload);
          setStatus("Čeká na potvrzení série");
          setProgress(36);
          await new Promise((resolve) => window.setTimeout(resolve, 120));
          const confirmed = window.confirm(
            `Text se nevejde do jednoho 15s videa.\n\nNavržená série: ${plan.video_count} videí po 15s.\nDůvod: ${plan.reason}\n\nTeď se vygeneruje jen první ukázkové video 1/${plan.video_count}. Chceš pokračovat?`
          );
          if (!confirmed) {
            setToast("Generování zastaveno. Série nebyla potvrzena.");
            return;
          }
          setStatus(`Generuji první ukázkové video z ${plan.video_count}`);
          payload = await apiJson("/generation-runs", { method: "POST", body: buildGenerationBody(true) });
        }
        setLatest(payload);
        setCurrentRun({ ...payload, generation_run: payload.generation_run || payload });
        const outcome = generationOutcome(payload, financeModeEnabled(form));
        setProgress(outcome.progress);
        setStatus(outcome.status);
        setToast(outcome.toast);
        setLatestRun(payload.generation_run || null);
        await refreshAll();
        if (outcome.openLibrary) setView("library");
      } catch (error) {
        showError(error);
      } finally {
        if (!backgroundQueued) {
          generationInFlight.current = false;
          setBusy(false);
        }
      }
    }

    async function generate(event) {
      event.preventDefault();
      if (financeModeEnabled(form) && !form.finance_scene_approved) {
        setToast("Nejdřív připrav a schval návrh scény. Video se spustí až po schválení podkladu.");
        setStatus("Čeká na schválení scény");
        return;
      }
      return startGenerationRequest(false, "Generuji creative set");
    }

    async function cancelGenerationRun(run) {
      const runId = run?.run_id || currentRun?.generation_run?.run_id || latestRun?.run_id;
      if (!runId) {
        setToast("Není aktivní run ke zrušení.");
        return;
      }
      try {
        const payload = await apiJson(`/generation-runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
        setLatestRun(payload);
        setCurrentRun((previous) => previous ? { ...previous, generation_run: payload } : { generation_run: payload });
        setStatus("Run byl označen ke zrušení");
        setToast("Cancel uložen. Další provider call se už nespustí.");
      } catch (error) {
        showError(error);
      }
    }

    async function prepareFinanceScene() {
      if (!form.finance_video_topic || !form.finance_video_script) {
        setToast("Vyplň téma a text finance videa, potom připrav scénu.");
        return;
      }
      setSceneBusy(true);
      setStatus("Připravuji scénář a návrh scény");
      setToast("");
      try {
        const body = new FormData();
        const payloadForm = financeModeForm(form);
        [
          "avatar_id",
          "avatar_data",
          "custom_avatar_name",
          "custom_avatar_persona",
          "custom_avatar_voice",
          "avatar_wardrobe_policy",
          "avatar_identity_note",
          "avatar_own_person_consent",
          "avatar_reference_url",
          "platform",
          "finance_video_topic",
          "finance_video_script",
          "finance_disclaimer",
          "openrouter_api_key",
          "prompt_model",
          "image_model",
          "image_size"
        ].forEach((key) => body.set(key, payloadForm[key] ?? ""));
        const payload = await apiJson("/finance-scene-preview", { method: "POST", body });
        setFinanceScenePreview(payload);
        const asset = payload.scene_image_generation?.image_assets?.[0] || {};
        setForm((current) => ({
          ...current,
          finance_scene_approved: false,
          finance_scene_reference_url: payload.scene_reference_url || asset.image_url || "",
          finance_scene_video_reference_url: payload.scene_reference_video_url || "",
          finance_scene_prompt: payload.finance_scene_concept?.image_prompt || "",
          finance_scene_concept_json: JSON.stringify(payload.finance_scene_concept || {})
        }));
        setToast(payload.next_step || "Návrh scény připravený ke schválení.");
      } catch (error) {
        showError(error);
      } finally {
        setSceneBusy(false);
      }
    }

    function approveFinanceScene() {
      if (!financeScenePreview && !form.finance_scene_prompt) {
        setToast("Nejdřív připrav návrh scény.");
        return;
      }
      setForm((current) => ({ ...current, finance_scene_approved: true }));
      setStatus("Scéna schválená");
      setToast("Scéna je schválená. Teď můžeš spustit generování finance videa.");
    }

    async function saveRating(record) {
      try {
        const payload = await apiJson("/creative-rating", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(record)
        });
        setToast(`Hodnocení uloženo: ${payload.status}`);
        await refreshAll();
        return payload;
      } catch (error) {
        showError(error);
        throw error;
      }
    }

    async function savePerformance(record) {
      try {
        const payload = await apiJson("/performance-import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(record)
        });
        setToast(`Performance uložena: ${payload.status}`);
        await refreshAll();
        return payload;
      } catch (error) {
        showError(error);
        throw error;
      }
    }

    const activeCreativeMode = form.app_mode === "finance_personal_brand" ? "finance_personal_brand" : "ecommerce";
    const moduleCreatives = useMemo(() => {
      return creatives.filter((item) => creativeModule(item) === activeCreativeMode);
    }, [creatives, activeCreativeMode]);

    const filteredCreatives = useMemo(() => {
      return creatives.filter((item) => {
        const haystack = `${item.product_name} ${item.creative_id} ${item.set_id} ${item.angle} ${item.type}`.toLowerCase();
        if (filters.search && !haystack.includes(filters.search.toLowerCase())) return false;
        if (filters.mode !== "all" && creativeModule(item) !== filters.mode) return false;
        if (filters.type !== "all" && item.type !== filters.type) return false;
        if (filters.angle !== "all" && item.angle !== filters.angle) return false;
        const itemStatus = item.latest_rating_status || item.status;
        if (filters.status === "unrated" && item.latest_rating_status) return false;
        if (filters.status !== "all" && filters.status !== "unrated" && itemStatus !== filters.status) return false;
        if (filters.product !== "all" && item.product_name !== filters.product) return false;
        if (filters.performance === "missing" && Number(item.performance_count || 0) > 0) return false;
        if (filters.performance === "has" && Number(item.performance_count || 0) === 0) return false;
        return true;
      });
    }, [creatives, filters]);

    const filterScopeCreatives = filters.mode === "all" ? creatives : moduleCreatives;
    const products = [...new Set(filterScopeCreatives.map((item) => item.product_name).filter(Boolean))];
    const angles = [...new Set(filterScopeCreatives.map((item) => item.angle).filter(Boolean))];
    const statuses = ["unrated", ...new Set(filterScopeCreatives.flatMap((item) => [item.latest_rating_status, item.status]).filter(Boolean))];
    const generatedAssets = currentRun?.static_image_generation?.image_assets || [];
    const latestVideo = currentRun?.video_generation || null;
    const latestPlan = currentRun?.ads_creative_set?.creative_plan || [];
    const activeShellAvatar = (avatars || []).find((avatar) => avatar.id === form.avatar_id);
    const shellCost = latestRun?.cost_summary?.total_known_cost_usd_display || latestRun?.cost_summary?.total_known_cost_display || latest?.session_cost_summary?.total_known_cost_display || "čeká";
    const commandItems = useMemo(() => {
      const nav = [
        ["Přehled", "Dashboard s KPI, posledním runem a doporučeným dalším krokem", "dashboard"],
        ["Nová kampaň", "Wizard pro ecommerce nebo finance brand generování", "studio"],
        ["Avatar set", "Knihovna avatarů, aktivace, default a performance signály", "avatars"],
        ["Creative sety", "Review assetů, rating, performance a kampaně ve skupinách", "library"],
        ["Prompt laboratoř", "Prompt graph, diff, finální payloady a provider audit", "prompt-lab"],
        ["Analýza", "Creative Intelligence, winners, avoid patterns a performance", "analytics"],
        ["Nastavení", "Modely, kvalita, safety a provider capabilities", "settings"]
      ].map(([label, detail, target]) => ({
        group: "Navigace",
        label,
        detail,
        action: () => setView(target)
      }));
      const actions = [
        {
          group: "Akce",
          label: theme === "dark" ? "Přepnout na světlý režim" : "Přepnout na tmavý režim",
          detail: "Změní vizuální režim aplikace bez zásahu do dat nebo workflow",
          action: () => setTheme((current) => current === "dark" ? "light" : "dark")
        },
        {
          group: "Akce",
          label: "Vytvořit ecommerce creative set",
          detail: "Přepne workspace do ecommerce a otevře kampaňový wizard",
          action: () => { update("app_mode", "ecommerce"); setView("studio"); }
        },
        {
          group: "Akce",
          label: "Vytvořit finance brand video",
          detail: "Přepne workspace do finance režimu a otevře finance workflow",
          action: () => { update("app_mode", "finance_personal_brand"); setView("studio"); }
        },
        {
          group: "Akce",
          label: "Zobraz kreativy bez performance",
          detail: "Uložený pohled: assety, které ještě nemají CTR/CPC/ROAS",
          action: () => { setFilters((current) => ({ ...current, mode: activeCreativeMode, status: "all", performance: "missing" })); setView("library"); }
        },
        {
          group: "Akce",
          label: "Otevřít poslední prompt audit",
          detail: latestRun?.run_id ? `${latestRun.status} / ${latestRun.current_stage}` : "čeká na první run",
          action: () => setView("prompt-lab")
        }
      ];
      const creativeItems = (creatives || []).slice(0, 80).map((creative) => ({
        group: "Kreativy",
        label: `${creative.set_id || "set"} · ${creative.product_name || creative.creative_id}`,
        detail: `${creative.type || "asset"} / ${creative.angle || "angle"} / ${creative.latest_rating_status || creative.status || "stav"}`,
        action: () => {
          setFilters((current) => ({
            ...current,
            mode: creativeModule(creative),
            search: creative.creative_id || creative.product_name || "",
            product: "all",
            type: "all",
            angle: "all",
            status: "all",
            performance: "all"
          }));
          setView("library");
          if (creative.asset_url) setPreviewAsset(creative);
        }
      }));
      const avatarItems = (avatars || []).slice(0, 40).map((avatar) => ({
        group: "Avataři",
        label: avatar.name || avatar.id,
        detail: `${avatar.voice || "hlas nenastaven"} / ${avatar.stats?.ad_sets_used || 0} ad setů`,
        action: () => { activateAvatar(avatar); setView("avatars"); }
      }));
      return [...nav, ...actions, ...creativeItems, ...avatarItems];
    }, [creatives, avatars, latestRun?.run_id, latestRun?.status, latestRun?.current_stage, activeCreativeMode, theme]);

    const workspacePulse = buildWorkspacePulse({
      view,
      form,
      status,
      latestRun,
      latest,
      moduleCreatives,
      filteredCreatives,
      shellCost,
      activeShellAvatar,
      setView,
      update,
      setFilters,
      activeCreativeMode,
      setCommandOpen
    });
    const activeRunForBanner = currentRun?.generation_run || latestRun;
    const runIsActive = busy || isActiveRunStatus(activeRunForBanner?.status);

    return h("div", { className: "app" },
      h(Sidebar, { view, setView, form, update }),
      h("main", { className: "main" },
        h("div", { className: "topbar" },
          h("div", null,
            h("div", { className: "eyebrow" }, "AI platforma pro reklamní kreativy"),
            h("h2", null, titleForView(view)),
            h("div", { className: "topbar-module" }, moduleBadge(form.app_mode), h("span", null, moduleMeta(form.app_mode).short))
          ),
          h("div", { className: "topbar-actions" },
            h("button", { type: "button", className: "command-trigger secondary", onClick: () => setCommandOpen(true), title: "Otevřít globální hledání (Ctrl+K)" },
              h("span", null, "Hledat"),
              h("kbd", null, "Ctrl K")
            ),
            h("button", { type: "button", className: "theme-toggle secondary", onClick: () => setTheme((current) => current === "dark" ? "light" : "dark"), title: "Přepnout světlý/tmavý režim" },
              theme === "dark" ? "Light" : "Dark"
            ),
            h("div", { className: "status-pill" }, h("span", { className: cls("dot", runIsActive && "active") }), runIsActive ? "Generování běží" : status)
          )
        ),
        runIsActive && h(ActiveRunBanner, { run: activeRunForBanner, progress, busy, onCancel: cancelGenerationRun, setView }),
        h(WorkspaceCommandBar, { pulse: workspacePulse }),
        view === "dashboard" && h(Dashboard, { intelligence, creatives, latest, latestRun, setView, form, update }),
        view === "studio" && h(Studio, { form, update, file, setFile, competitorFiles, setCompetitorFiles, generate, busy, sceneBusy, progress, latestPlan, generatedAssets, latestVideo, avatars, activateAvatar, setView, financeScenePreview, prepareFinanceScene, approveFinanceScene, currentRun, latestRun, cancelGenerationRun, serverPlanPreview, promptLearningGuidance, providerValidationPreview }),
        view === "avatars" && h(AvatarLibrary, { avatars, activeAvatarId: form.avatar_id, form, update, activateAvatar, activateExternalAvatar, saveAvatarProfile, uploadAvatarProfile, makeDefaultAvatar, setView }),
        view === "library" && h(Library, {
          creatives: filteredCreatives,
          allCreatives: creatives,
          activeMode: activeCreativeMode,
          filters,
          setFilters,
          products,
          angles,
          statuses,
          generatedAssets,
          layout: libraryLayout,
          setLayout: setLibraryLayoutMode,
          openPreview: setPreviewAsset,
          saveRating,
          savePerformance
        }),
        view === "prompt-lab" && h(PromptLab, { latest, latestRun, settings, form, update, promptLearningGuidance, providerValidationPreview }),
        view === "analytics" && h(Analytics, { intelligence, learning, creatives }),
        view === "settings" && h(Settings, { form, update, settings, providerCapabilities, latestRun, providerValidationPreview }),
        toast && h("div", { className: "toast", onClick: () => setToast("") }, toast),
        previewAsset && h(PreviewModal, { asset: previewAsset, onClose: () => setPreviewAsset(null) }),
        commandOpen && h(CommandPalette, { items: commandItems, onClose: () => setCommandOpen(false) })
      )
    );
  }

  function WorkspaceCommandBar({ pulse }) {
    return h("section", { className: "workspace-command-bar", "aria-label": "Workspace context" },
      h("div", { className: "workspace-command-main" },
        h("div", { className: "workspace-command-icon" }, pulse.icon),
        h("div", null,
          h("div", { className: "workspace-command-kicker" },
            moduleBadge(pulse.mode),
            h("span", null, pulse.viewLabel)
          ),
          h("h3", null, pulse.title),
          h("p", null, pulse.body)
        )
      ),
      h("div", { className: "workspace-command-meta" },
        pulse.meta.map((item) =>
          h("div", { className: "workspace-context-item", key: item.label },
            h("span", null, item.label),
            h("b", null, item.value)
          )
        )
      ),
      h("div", { className: "workspace-command-actions" },
        h("button", { type: "button", onClick: pulse.primary.action }, pulse.primary.label),
        h("button", { type: "button", className: "secondary", onClick: pulse.secondary.action }, pulse.secondary.label)
      )
    );
  }

  function ActiveRunBanner({ run, progress, busy, onCancel, setView }) {
    const monitor = run?.monitor || {};
    const percent = Math.min(100, Math.max(0, Number(monitor.progress_percent || progress || 0)));
    const stageLabel = monitor.stage_label || runStageLabel(run?.current_stage || run?.status);
    const statusLabel = monitor.status_label || run?.status || (busy ? "běží" : "aktivní");
    const runId = run?.run_id || "aktivní run";
    const canCancel = isActiveRunStatus(run?.status) && !run?.cancel_requested;
    return h("section", { className: "active-run-banner", "aria-live": "polite" },
      h("div", { className: "active-run-pulse" }, h("span", null)),
      h("div", { className: "active-run-main" },
        h("div", { className: "active-run-kicker" }, "Aktivní generování"),
        h("b", null, `${statusLabel} / ${stageLabel}`),
        h("small", null, runId)
      ),
      h("div", { className: "active-run-progress" },
        h("div", { className: "active-run-progress-head" },
          h("span", null, `${Math.round(percent)}%`),
          h("small", null, generationPhaseForRun(run, percent, run?.workspace === "finance"))
        ),
        h("div", { className: "run-progress-track" },
          h("span", { style: { width: `${percent}%` } })
        )
      ),
      h("div", { className: "active-run-actions" },
        h("button", { type: "button", className: "secondary small", onClick: () => setView?.("studio") }, "Monitor"),
        canCancel && h("button", { type: "button", className: "danger small", onClick: () => onCancel?.(run) }, "Zastavit")
      )
    );
  }

  function ModeSwitcher({ form, update, compact = false }) {
    const active = form.app_mode === "finance_personal_brand" ? "finance_personal_brand" : "ecommerce";
    return h("div", { className: cls("workspace-mode-switch", compact && "compact") },
      ["ecommerce", "finance_personal_brand"].map((id) => {
        const meta = moduleMeta(id);
        return h("button", {
          key: id,
          type: "button",
          className: cls(active === id && "active"),
          onClick: () => update("app_mode", id),
          "aria-pressed": active === id
        },
          h("span", { className: "mode-icon" }, meta.icon),
          h("span", null,
            h("b", null, meta.label),
            !compact && h("small", null, meta.short)
          )
        );
      })
    );
  }

  function ModuleLane({ id, active, count, approved, onClick }) {
    const meta = moduleMeta(id);
    return h("button", { type: "button", className: cls("module-lane", active && "active"), onClick },
      h("div", { className: "module-lane-icon" }, meta.icon),
      h("div", null,
        h("span", { className: "eyebrow" }, meta.label),
        h("b", null, meta.laneTitle),
        h("small", null, meta.laneCopy)
      ),
      h("div", { className: "module-lane-stats" },
        h("span", null, `${count} assetů`),
        h("span", null, `${approved} schváleno`)
      )
    );
  }

  function Sidebar({ view, setView, form, update }) {
    return h("aside", { className: "sidebar" },
      h("div", { className: "brand" },
        h("div", { className: "brand-mark" }),
        h("div", null,
          h("div", { className: "eyebrow" }, "Creative OS"),
          h("h1", null, "Reklamní intelligence")
        )
      ),
      h("div", { className: "module-shell" },
        h("div", { className: "nav-section module-section" }, "Pracovní modul"),
        h(ModeSwitcher, { form, update, compact: true }),
        h("div", { className: "module-note" }, moduleMeta(form.app_mode).note)
      ),
      h("div", { className: "nav-section" }, "Pracovní prostor"),
      h("nav", { className: "nav" },
        navItems.map(([key, icon, label]) =>
          h("button", { key, type: "button", className: cls(view === key && "active"), onClick: () => setView(key) },
            h("code", null, icon),
            h("span", null, label)
          )
        )
      ),
      h("div", { className: "side-note" },
        form.app_mode === "finance_personal_brand"
          ? "Finance workflow: scénář -> návrh scény -> schválení -> video -> review -> performance -> memory."
          : "E-commerce workflow: produkt -> kampaň -> creative set -> asset -> hodnocení -> performance -> memory."
      )
    );
  }

  function Dashboard({ intelligence, creatives, latest, latestRun, setView, form, update }) {
    const counts = intelligence?.counts || {};
    const leaders = intelligence?.performance_leaders || [];
    const activeMeta = moduleMeta(form.app_mode);
    const commerceCreatives = creatives.filter((item) => creativeModule(item) === "ecommerce");
    const financeCreatives = creatives.filter((item) => creativeModule(item) === "finance_personal_brand");
    const latestProduct = latest?.product_analysis?.product_name || latest?.user_input?.product_name || "Žádný poslední run";
    const latestStatus = latest?.final_export_status || latest?.workflow_report?.executive_summary?.status || "bez dat";
    const latestCost = latest?.session_cost_summary?.total_known_cost_display || "zatím bez ceny";
    const approvedCount = creatives.filter((item) => item.latest_rating_status === "approved").length;
    const rejectedCount = creatives.filter((item) => item.latest_rating_status === "rejected").length;
    const generatedCount = counts.creatives || creatives.length || 0;
    const performanceCount = counts.performance_records || 0;
    const planPreview = latest?.creative_plan_preview?.items || [];
    const visiblePlan = planPreview.length ? planPreview : creativePlanRows(form).map((row) => ({ ...row, status: "planned", reason: row.reason }));
    const lastAssets = [
      ...((latest?.video_generation && !latest?.video_generation?.skipped_by_generation_mode) ? [latest.video_generation] : []),
      ...((latest?.static_image_generation?.image_assets) || [])
    ].length;
    const topCtr = leaders[0]?.ctr ? `${leaders[0].ctr}%` : "čeká na data";
    const needsAttention = creatives
      .filter((item) => {
        const status = String(item.latest_rating_status || item.status || "").toLowerCase();
        return status === "failed" || status === "blocked" || status === "rejected" || Number(item.performance_count || 0) === 0;
      })
      .slice(0, 5);
    const recommendations = intelligence?.prompt_recommendations || [];
    const bestHooks = intelligence?.best_hooks || [];
    const rejectedPatterns = intelligence?.rejected_patterns || [];
    const recentCreatives = (intelligence?.recent_creatives || creatives || []).slice(0, 4);
    const nextActionTitle = needsAttention.length
      ? `Vyřešit ${needsAttention.length} položek v review inboxu`
      : performanceCount
      ? "Vytvořit další variantu z winners"
      : "Doplnit první performance data";
    const nextActionBody = needsAttention.length
      ? "Nejdřív projdi blokace, zamítnuté assety nebo kreativy bez performance. Tím se zlepší další doporučení."
      : performanceCount
      ? "Learning loop má signály. Další nejlepší krok je nový creative set nebo varianta podle winnerů."
      : "Bez CTR/CPC/ROAS je dashboard jen inventář. Začni doplněním výkonu u schválených kreativ.";

    return h("div", { className: "dashboard-page" },
      h("section", { className: "dashboard-hero" },
        h("div", { className: "dashboard-copy" },
          h("div", { className: "eyebrow" }, activeMeta.label),
          h("h2", null, nextActionTitle),
          h("p", null, nextActionBody),
          h("div", { className: "hero-actions" },
            h("button", { type: "button", onClick: () => setView(needsAttention.length ? "library" : "studio") }, needsAttention.length ? "Otevřít review" : "Nová kampaň"),
            h("button", { type: "button", className: "secondary", onClick: () => setView("analytics") }, "Zobrazit učení")
          )
        ),
        h("div", { className: "run-snapshot" },
          h("div", { className: "eyebrow" }, "Poslední session"),
          h("h3", null, latestProduct),
          h("div", { className: "snapshot-grid" },
            snapshotItem("Status", latestStatus),
            snapshotItem("Cena", latestCost),
            snapshotItem("Assety", lastAssets ? `${lastAssets}` : "0"),
            snapshotItem("Složka", latest?.output_files?.folder_name || "nevytvořeno")
          ),
          h("div", { className: "snapshot-actions" },
            h("button", { type: "button", className: "secondary", onClick: () => setView("prompt-lab") }, "Audit promptů"),
            h("button", { type: "button", className: "secondary", onClick: () => setView("analytics") }, "Učení")
          )
        )
      ),

      h("section", { className: "kpi-grid" },
        metricCard("Kreativy", generatedCount, "celkem uložené assety", "blue"),
        metricCard("Schválené", approvedCount, `${rejectedCount} zamítnuté`, "green"),
        metricCard("Top CTR", topCtr, performanceCount ? `${performanceCount} performance záznamů` : "doplnit performance", "yellow"),
        metricCard("Učení", intelligence?.learning_loop?.status || "collecting", `${counts.ratings || 0} rating signálů`, "purple")
      ),

      h("section", { className: "dashboard-insight-grid" },
        h("div", { className: "panel dashboard-panel insight-panel" },
          h("div", { className: "eyebrow" }, "Doporučení pro další generaci"),
          h("h4", null, limit(recommendations[0] || "Získej víc ratingů a performance dat.", 130)),
          h("p", null, "Krátké vodítko pro další creative set. Detailní logika zůstává v Analýze a Prompt laboratoři.")
        ),
        h("div", { className: "panel dashboard-panel" },
          h("div", { className: "eyebrow" }, "Best hooks"),
          chips(bestHooks.slice(0, 6).length ? bestHooks.slice(0, 6) : ["čeká na schválené kreativy", "čeká na CTR/ROAS"])
        ),
        h("div", { className: "panel dashboard-panel" },
          h("div", { className: "eyebrow" }, "Avoid patterns"),
          chips(rejectedPatterns.slice(0, 6).length ? rejectedPatterns.slice(0, 6) : ["zatím bez zamítnutých patternů"])
        ),
        h("div", { className: "panel dashboard-panel recent-panel" },
          h("div", { className: "eyebrow" }, "Nedávné kreativy"),
          h("div", { className: "mini-table compact" },
            recentCreatives.length ? recentCreatives.map((item, index) =>
              h("div", { key: item.creative_id || index },
                h("b", null, item.set_id || item.type || "asset"),
                h("span", null, `${item.product_name || item.angle || "kreativa"} / ${item.latest_rating_status || item.status || "stav"}`)
              )
            ) : h("div", null, h("b", null, "Zatím nic"), h("span", null, "Vygeneruj první set."))
          )
        )
      ),

      h("section", { className: "section dashboard-activity" },
        h(SectionHead, { title: "Aktivita workspace", subtitle: "Poslední důležité události bez nutnosti otevírat debug nebo výstupní soubory." }),
        h(ActivityTimeline, { latestRun, creatives: recentCreatives })
      ),

      h("section", { className: "dashboard-grid" },
        h("div", { className: "panel dashboard-panel" },
          h(SectionHead, { title: "Creative plan", subtitle: "Co appka generuje a proč. Status je vidět ještě před debugováním výstupu." }),
          h("div", { className: "plan-list" },
            visiblePlan.map((item) =>
              h("div", { className: "plan-row", key: item.set_id },
                h("div", { className: "plan-id" }, item.set_id),
                h("div", { className: "plan-main" },
                  h("b", null, item.creative_type || item.name),
                  h("span", null, `${item.angle || "angle"} / ${item.funnel_stage || "funnel"} / ${item.aspect_ratio || "ratio"}`)
                ),
                h("div", { className: "plan-meta" },
                  h("span", { className: cls("pill", statusClass(item.status)) }, item.status || "planned"),
                  h("small", null, item.reason || "součást setu")
                )
              )
            )
          )
        ),
        h("div", { className: "panel dashboard-panel next-panel" },
          h(SectionHead, { title: "Další nejlepší krok", subtitle: "Minimum chaosu: appka ukazuje, co teď posune kvalitu." }),
          h("div", { className: "next-actions" },
            workflowItem("1", "Vygeneruj nový set", "Vyber produkt, avatara, trh a quality mode.", () => setView("studio")),
            workflowItem("2", "Ohodnoť kreativy", "Schválit / zamítnout stačí pro první learning signál.", () => setView("library")),
            workflowItem("3", "Doplň performance", "CTR, CPC, CPA a ROAS z reklamní platformy zlepší další generace.", () => setView("analytics"))
          )
        ),
        h("div", { className: "panel dashboard-panel attention-panel" },
          h(SectionHead, { title: "Vyžaduje pozornost", subtitle: "Rychlý inbox pro selhané, zamítnuté nebo performance-nevyplněné kreativy." }),
          needsAttention.length
            ? h("div", { className: "attention-list" },
              needsAttention.map((item) =>
                h("button", { key: item.creative_id, type: "button", className: "attention-row", onClick: () => setView("library") },
                  h("span", null,
                    h("b", null, item.product_name || item.creative_id),
                    h("small", null, `${item.set_id || "set"} / ${item.type || "asset"} / ${item.angle || "angle"}`)
                  ),
                  h("code", null, item.latest_rating_status || item.status || (Number(item.performance_count || 0) === 0 ? "bez performance" : "review"))
                )
              )
            )
            : h("div", { className: "empty compact" }, "Žádné blokace ani obvious follow-up. Dobrá chvíle pro nový test.")
        )
      )
    );
  }

  function Studio({ form, update, file, setFile, competitorFiles, setCompetitorFiles, generate, busy, sceneBusy, progress, latestPlan, generatedAssets, latestVideo, avatars, activateAvatar, setView, financeScenePreview, prepareFinanceScene, approveFinanceScene, currentRun, latestRun, cancelGenerationRun, serverPlanPreview, promptLearningGuidance, providerValidationPreview }) {
    const avatarOptions = (avatars && avatars.length ? avatars : [
      { id: "avatar1", name: "Avatar1" },
      { id: "default_creator", name: "Výchozí creator" },
      { id: "premium_creator", name: "Premium creator" }
    ]).map((avatar) => [avatar.id, avatar.name || avatar.id]);
    const [campaignStep, setCampaignStep] = useState(1);
    const [campaignInputMode, setCampaignInputMode] = useState(() => window.localStorage.getItem("campaign_input_mode") || "expert");
    const [chatBriefItems, setChatBriefItems] = useState([]);
    const activeAvatar = (avatars || []).find((avatar) => avatar.id === form.avatar_id);
    const displayAvatar = activeAvatar || {
      id: form.avatar_id,
      name: form.custom_avatar_name,
      style: form.custom_avatar_persona,
      voice: form.custom_avatar_voice,
      image_url: form.avatar_reference_url,
      preview_url: form.avatar_reference_url,
      stats: {}
    };
    const isFinanceMode = financeModeEnabled(form);
    const effectiveForm = isFinanceMode ? financeModeForm(form) : form;
    const activePipelineSteps = isFinanceMode ? financePipelineSteps : pipelineSteps;
    const module = moduleMeta(effectiveForm.app_mode);
    const railLabels = isFinanceMode
      ? [
        ["1", "Scénář", "Téma, text, compliance"],
        ["2", "Avatar", "Osobní brand identity"],
        ["3", "Distribuce", "Meta, Instagram, čeština"],
        ["4", "Scéna", "Návrh, schválení, modely"]
      ]
      : [
        ["1", "Produkt", "Název, reference, poznámky"],
        ["2", "Avatar", "Creator identity lock"],
        ["3", "Trh", "Platforma, jazyk, cílovka"],
        ["4", "Kvalita", "Modely, limity, režie"]
      ];
    const stepTitles = isFinanceMode
      ? ["Finance scénář", "Avatar osobního brandu", "Distribuce a trh", "Scéna a modely"]
      : ["Produktový vstup", "Avatar", "Platforma a trh", "Modely a kvalita"];
    const [competitorPasteStatus, setCompetitorPasteStatus] = useState("");
    const draftPlan = (serverPlanPreview?.items?.length ? serverPlanPreview.items : creativePlanRows(effectiveForm).map((row) => ({ ...row, ...planDecisionForForm(effectiveForm, row) })));
    const selectedImageSlots = draftPlan.filter((item) => item.media !== "video" && item.status !== "SKIPPED").length;
    const modeLabel = effectiveForm.generation_mode === "video" ? "Jen video" : effectiveForm.generation_mode === "static" ? "Jen statiky" : "Video + statiky";
    const activeRun = currentRun?.generation_run || latestRun;
    const runActive = busy || isActiveRunStatus(activeRun?.status);
    const effectiveCampaignInputMode = isFinanceMode ? "expert" : campaignInputMode;
    const displayProgress = Math.max(progress || 0, Number(activeRun?.monitor?.progress_percent || 0));
    const activeRunStages = Array.isArray(activeRun?.stage_results) ? activeRun.stage_results : [];
    const stepComplete = (step) => {
      if (step === 1) return isFinanceMode
        ? Boolean(form.finance_video_topic && form.finance_video_script)
        : Boolean(form.product_name && (form.product_reference_url || file || form.product_info));
      if (step === 2) return Boolean(form.avatar_id);
      if (step === 3) return Boolean(form.platform && form.market && form.language);
      if (step === 4) return Boolean(form.prompt_model && (form.generation_mode === "video" || form.image_model) && (form.generation_mode === "static" || form.seedance_model));
      return false;
    };
    const railState = (step) => campaignStep === step ? "active" : (step < campaignStep && stepComplete(step) ? "done" : "");
    const goNext = () => setCampaignStep((step) => Math.min(4, step + 1));
    const goBack = () => setCampaignStep((step) => Math.max(1, step - 1));
    const submitWizard = (event) => {
      event.preventDefault();
      if (campaignStep < 4) {
        if (!runActive && stepComplete(campaignStep)) goNext();
        return;
      }
      setToast("Generování spusť tlačítkem ve finálním kroku.");
    };
    const launchGeneration = (event) => {
      event.preventDefault();
      generate(event);
    };
    const switchCampaignInputMode = (value) => {
      setCampaignInputMode(value);
      window.localStorage.setItem("campaign_input_mode", value);
    };
    const appendCompetitorFiles = (files, source = "file") => {
      const imageFiles = Array.from(files || []).filter((item) => item && String(item.type || "").startsWith("image/"));
      if (!imageFiles.length) return;
      setCompetitorFiles((current) => [...(current || []), ...imageFiles].slice(0, 12));
      setCompetitorPasteStatus(source === "paste" ? `${imageFiles.length} vložených obrázků ze schránky` : `${imageFiles.length} přidaných screenshotů`);
    };
    const handleCompetitorPaste = (event) => {
      if (!form.competitor_strategy_enabled) return;
      const items = Array.from(event.clipboardData?.items || []);
      const pastedImages = items
        .filter((item) => item.kind === "file" && String(item.type || "").startsWith("image/"))
        .map((item, index) => {
          const fileItem = item.getAsFile();
          if (!fileItem) return null;
          const extension = String(fileItem.type || "image/png").split("/")[1]?.replace("jpeg", "jpg") || "png";
          const filename = fileItem.name && fileItem.name !== "image.png"
            ? fileItem.name
            : `competitor-paste-${Date.now()}-${index + 1}.${extension}`;
          return new File([fileItem], filename, { type: fileItem.type || "image/png", lastModified: Date.now() });
        })
        .filter(Boolean);
      if (!pastedImages.length) return;
      event.preventDefault();
      appendCompetitorFiles(pastedImages, "paste");
    };
    const removeCompetitorFile = (index) => {
      setCompetitorFiles((current) => (current || []).filter((_item, itemIndex) => itemIndex !== index));
      setCompetitorPasteStatus("");
    };
    const competitorFileLabel = (item, index) => {
      const sizeKb = Math.max(1, Math.round(Number(item?.size || 0) / 1024));
      return `${item?.name || `screenshot-${index + 1}.png`} / ${sizeKb} KB`;
    };
    useEffect(() => {
      window.scrollTo(0, 0);
    }, [campaignStep]);
    return h("div", { className: "campaign-workspace" },
      h("section", { className: "campaign-command studio-brief" },
        h("div", null,
          h("div", { className: "eyebrow" }, module.label),
          h("h2", null, module.studioTitle),
          h("p", null, module.studioCopy)
        ),
        h("div", { className: "command-side-stack" },
          h("div", { className: "command-summary" },
            summaryPill(isFinanceMode ? "Téma" : "Produkt", (isFinanceMode ? form.finance_video_topic : form.product_name) || "není zadán"),
            summaryPill("Trh", `${effectiveForm.market} / ${effectiveForm.language}`),
            summaryPill("Režim", modeLabel),
            summaryPill(isFinanceMode ? "Výstup" : "Statiky", isFinanceMode ? "pouze video" : `${selectedImageSlots} setů`)
          ),
          h(BriefQualityCard, { form: effectiveForm, rawForm: form, isFinanceMode, activeAvatar })
        )
      ),
      h("div", { className: "campaign-mode-switch" },
        h("div", null,
          h("b", null, "Vstup kampaně"),
          h("span", null, "Chat mode pro rychlé zadání, Expert pro plnou kontrolu.")
        ),
        segmented(effectiveCampaignInputMode, switchCampaignInputMode, [["chat", "Chat"], ["expert", "Expert"]])
      ),
      effectiveCampaignInputMode === "chat"
        ? h(SimpleCampaignChatMode, {
          form,
          update,
          file,
          setFile,
          competitorFiles,
          appendCompetitorFiles,
          removeCompetitorFile,
          competitorFileLabel,
          chatBriefItems,
          setChatBriefItems,
          avatars,
          avatarOptions,
          activateAvatar,
          setView,
          displayAvatar,
          activeAvatar,
          draftPlan,
          selectedImageSlots,
          runActive,
          launchGeneration
        })
        : h("div", { className: "studio-layout wizard-layout" },
      h("aside", { className: "wizard-rail" },
        railLabels.map(([number, title, meta]) => campaignRailItem(number, title, railState(Number(number)), meta, () => setCampaignStep(Number(number))))
      ),
      h("form", { className: "panel wizard campaign-form", onSubmit: submitWizard },
        h("div", { className: "wizard-head" },
          h("div", null,
            h("div", { className: "eyebrow" }, "Tvůrce kampaně"),
            h("h3", null, stepTitles[campaignStep - 1])
          ),
          h("span", { className: cls("pill", runActive ? "warn" : "pass") }, runActive ? "generuje se" : "připraveno")
        ),
        campaignStep === 1 && wizardStep("1", stepTitles[0], [
          isFinanceMode
            ? h("div", { className: "finance-mode-panel", key: "finance-mode-panel" },
              h("div", { className: "eyebrow" }, "Finance osobní brand"),
              h("h4", null, "Podcast studio finanční reklama"),
              h("p", null, "V tomto režimu aplikace generuje jen osobní brand video v kvalitní češtině. Výchozí look je moderní podcastové studio s mikrofonem, teplým světlem a interaktivní infografikou, na kterou avatar ukazuje a reaguje."),
              field("Téma videa", h("input", { value: form.finance_video_topic, onChange: (e) => update("finance_video_topic", e.target.value), required: true, placeholder: "např. Jak vysvětlit pravidelné investování bez zbytečného stresu" })),
              field("Co má osobní brand říkat", h("textarea", { value: form.finance_video_script, onChange: (e) => update("finance_video_script", e.target.value), required: true, placeholder: "Vlož hlavní sdělení nebo rough script. Agent připraví čistý český scénář, rozdělí ho do scén a navrhne infografiku, se kterou avatar gesty interaguje." })),
              field("Disclaimer", h("textarea", { value: form.finance_disclaimer, onChange: (e) => update("finance_disclaimer", e.target.value), placeholder: "Vzdělávací obsah, nejde o individuální investiční ani finanční doporučení." })),
              h(FinanceSceneApproval, { form, sceneBusy, preview: financeScenePreview, prepareFinanceScene, approveFinanceScene })
            )
            : [
              field("Název produktu", h("input", { value: form.product_name, onChange: (e) => update("product_name", e.target.value), required: true, placeholder: "např. BELLA | Leather Tote Bag" })),
              field("Poznámky k produktu", h("textarea", { value: form.product_info, onChange: (e) => update("product_info", e.target.value), placeholder: "Interní guidance: viditelné vlastnosti, materiál, cílovka, použití. Text se nekopíruje přímo do reklamy." })),
              h("div", { className: "grid-2", key: "pgrid" },
                field("Kategorie", segmented(form.product_category, (v) => update("product_category", v), [["auto", "Auto"], ["handbag", "Kabelka"], ["shoes", "Boty"], ["apparel", "Oblečení"]])),
                field("Obrázek produktu", h("input", { type: "file", accept: "image/*", onChange: (e) => setFile(e.target.files?.[0] || null) }))
              ),
              field("Veřejná referenční URL produktu", h("input", { value: form.product_reference_url, onChange: (e) => update("product_reference_url", e.target.value), placeholder: "https://..." })),
              h("div", { className: "competitor-strategy-panel", key: "competitor-strategy-panel" },
                checkbox("Competitor-inspired ad set pro toto generování", form.competitor_strategy_enabled, (v) => update("competitor_strategy_enabled", v)),
                form.competitor_strategy_enabled && h("div", { className: "competitor-chat-fields", onPaste: handleCompetitorPaste },
                  h("div", { className: "environment-card" },
                    h("b", null, "Competitor strategy chat"),
                    h("span", null, "Vlož konkurenci jako do chatu. Systém hledá strategické vzory: hook, problém/touhu, benefit, vizuální styl, nabídku, CTA a námitky. Výstup se použije jen pro tento run a nesmí kopírovat texty, loga ani layout konkurenta.")
                  ),
                  h("div", { className: "competitor-paste-zone", tabIndex: 0 },
                    h("b", null, "Paste screenshotů"),
                    h("span", null, competitorPasteStatus || "Klikni sem a vlož obrázek ze schránky, nebo přidej soubory níže.")
                  ),
                  h("div", { className: "grid-2" },
                    field("Konkurent", h("input", { value: form.competitor_name, onChange: (e) => update("competitor_name", e.target.value), placeholder: "např. značka / shop / produkt" })),
                    field("URL konkurenta", h("input", { value: form.competitor_url, onChange: (e) => update("competitor_url", e.target.value), placeholder: "https://..." }))
                  ),
                  field("Chat brief konkurence", h("textarea", {
                    value: form.competitor_chat_brief,
                    onChange: (e) => update("competitor_chat_brief", e.target.value),
                    placeholder: "Nakopíruj popisy reklam, headline, CTA, positioning, co se ti líbí, co nechceš kopírovat, a proč to podle tebe funguje."
                  })),
                  h("div", { className: "grid-2" },
                    field("Screenshoty konkurence", h("input", {
                      type: "file",
                      accept: "image/*",
                      multiple: true,
                      onChange: (e) => {
                        appendCompetitorFiles(e.target.files, "file");
                        e.target.value = "";
                      }
                    })),
                    field("Poznámky ke screenshotům", h("textarea", {
                      value: form.competitor_screenshot_notes,
                      onChange: (e) => update("competitor_screenshot_notes", e.target.value),
                      placeholder: "Popiš, co je na screenshotech důležité: layout, první text, záběr, CTA, produktový detail."
                    }))
                  ),
                  Boolean((competitorFiles || []).length) && h("div", { className: "competitor-file-list" },
                    (competitorFiles || []).map((item, index) =>
                      h("span", { className: "competitor-file-pill", key: `${item.name || "paste"}-${item.size || 0}-${index}` },
                        h("small", null, competitorFileLabel(item, index)),
                        h("button", { type: "button", onClick: () => removeCompetitorFile(index), "aria-label": `Odebrat ${item.name || "screenshot"}` }, "x")
                      )
                    )
                  ),
                  Boolean((competitorFiles || []).length) && h("p", { className: "hint" }, `${competitorFiles.length} screenshotů bude uložených jen jako competitor reference pro tento run.`)
                )
              )
            ]
        ]),
        campaignStep === 2 && wizardStep("2", "Avatar", [
          h("div", { className: "avatar-picker-row", key: "avatar-picker" },
            field("Vybraný avatar", select(form.avatar_id, (v) => {
              const selected = (avatars || []).find((avatar) => avatar.id === v);
              if (selected) activateAvatar(selected);
              else update("avatar_id", v);
            }, avatarOptions)),
            h("button", { type: "button", className: "secondary", onClick: () => setView("avatars") }, "Knihovna")
          ),
          (avatars || []).length ? h("div", { className: "avatar-choice-grid", key: "avatar-choice-grid" },
            (avatars || []).slice(0, 8).map((avatar) =>
              h("button", {
                type: "button",
                key: avatar.id,
                className: cls("avatar-choice", avatar.id === form.avatar_id && "active"),
                onClick: () => activateAvatar(avatar)
              },
                h("span", { className: "avatar-choice-img" },
                  avatarPreviewUrl(avatar)
                    ? h("img", { src: avatarPreviewUrl(avatar), alt: avatar.name || avatar.id })
                    : h("span", null, "AI")
                ),
                h("span", { className: "avatar-choice-copy" },
                  h("b", null, avatar.name || avatar.id),
                  h("small", null, `${avatar.voice || "hlas"} / ${avatar.stats?.ad_sets_used || 0} setů`)
                )
              )
            )
          ) : h("div", { className: "empty", key: "avatar-empty" }, "V knihovně zatím nejsou avatary. Otevři Avatar Set a přidej referenci."),
          (activeAvatar || form.avatar_reference_url) && h("div", { className: "active-avatar-strip", key: "active-avatar" },
            avatarPreviewUrl(displayAvatar)
              ? h("img", { src: avatarPreviewUrl(displayAvatar), alt: displayAvatar.name || "avatar" })
              : h("div", { className: "avatar-mini-placeholder" }, "AI"),
            h("div", null,
              h("b", null, `${displayAvatar.name || displayAvatar.id}${displayAvatar.is_default ? " / výchozí" : ""}`),
              h("span", null, `${displayAvatar.style || "UGC creator"} | ${displayAvatar.voice || "hlas není nastaven"} | použití: ${displayAvatar.stats?.ad_sets_used || 0} ad setů`)
            )
          ),
          authorizedAvatarConsent(form.avatar_own_person_consent, (v) => update("avatar_own_person_consent", v)),
          checkbox("Použít referenční obrázek avatara pro identity lock", form.use_avatar_image_reference, (v) => update("use_avatar_image_reference", v))
        ]),
        campaignStep === 3 && wizardStep("3", "Platforma a trh", [
          h("div", { className: "grid-2", key: "mgrid1" },
            field("Platforma", segmented(form.platform, (v) => update("platform", v), isFinanceMode ? [["meta", "Meta"], ["instagram", "Instagram"]] : [["meta", "Meta"], ["google_ads", "Google"], ["tiktok", "TikTok"], ["instagram", "IG"], ["youtube", "YouTube"]])),
            field("Trh", select(form.market, (v) => update("market", v), [["UK", "UK"], ["US", "US"], ["CZ", "CZ"], ["DE", "DE"], ["FR", "FR"], ["EU", "EU"]]))
          ),
          h("div", { className: "grid-2", key: "mgrid2" },
            field("Jazyk", isFinanceMode
              ? h("input", { value: "Čeština (vynuceno pro finance mode)", disabled: true })
              : select(form.language, (v) => update("language", v), [["en", "Angličtina"], ["cs", "Čeština"], ["de", "Němčina"], ["fr", "Francouzština"], ["pl", "Polština"]])),
            field("Režim generování", isFinanceMode
              ? h("input", { value: "Jen video reklama (vynuceno)", disabled: true })
              : segmented(form.generation_mode, (v) => update("generation_mode", v), [["both", "Video + statiky"], ["video", "Jen video"], ["static", "Jen statiky"]]))
          )
        ]),
        campaignStep === 4 && wizardStep("4", "Modely a kvalita", [
          field("Prompt model", h("input", { value: form.prompt_model, onChange: (e) => update("prompt_model", e.target.value) })),
          h("div", { className: "grid-2", key: "models" },
            field("Obrázkový model", h("input", { value: form.image_model, onChange: (e) => update("image_model", e.target.value) })),
            field("Video model", h("input", { value: form.seedance_model, onChange: (e) => update("seedance_model", e.target.value) }))
          ),
          h("div", { className: "grid-2", key: "limits" },
            field("Max statických obrázků", h("input", { type: "number", min: "0", max: "10", value: isFinanceMode ? "0" : form.max_static_images, disabled: isFinanceMode, onChange: (e) => update("max_static_images", e.target.value) })),
            field("Délka videa", h("input", { type: "number", min: "6", max: "60", value: form.video_length, onChange: (e) => update("video_length", e.target.value) }))
          ),
          h("div", { className: "environment-card", key: "environment-lock" },
            h("b", null, "Prostředí a product fidelity"),
            h("span", null, "Když je reference jen produktová fotka, appka vybere vhodné prostředí podle kategorie, audience a angle. Product shape, barva, logo a velikost zůstávají uzamčené.")
          ),
          h("div", { className: "grid-2", key: "environment-controls" },
            field("Konzistence scény", select(form.background_consistency, (v) => update("background_consistency", v), [["strict", "Strict - jen relevantní reference"], ["balanced", "Balanced - category-smart"], ["free", "Free - s ruční režií"]])),
            checkbox("Povolit kreativní změnu prostředí", form.environment_override, (v) => update("environment_override", v))
          ),
          checkbox("Použít scénu z reference jen když je relevantní", form.preserve_original_scene_layout, (v) => update("preserve_original_scene_layout", v)),
          field(isFinanceMode ? "Volitelná režie finance videa" : "Volitelná režie UGC videa", h("textarea", {
            value: form.ugc_video_extra_prompt,
            onChange: (e) => update("ugc_video_extra_prompt", e.target.value),
            placeholder: isFinanceMode
              ? "Např. avatar ukáže na kartu Rezerva, ta se zvýrazní; potom air-tap spustí checklist. Nesmí měnit identitu avatara ani přidávat nepravdivá čísla."
              : "Např. uprostřed videa jemná změna světla, reakce avatara, konkrétní akce s produktem. Nesmí měnit produkt ani identitu avatara."
          })),
          h("p", { className: "hint" }, isFinanceMode
            ? "Použije se jen jako režie finance videa. Backend stále vynucuje češtinu, compliance a podcast-studio základ."
            : "Použije se jen pro UGC video prompt. Nepřebíjí product fidelity ani identitu avatara."),
          field("OpenRouter API key", h("input", { type: "password", value: form.openrouter_api_key, onChange: (e) => update("openrouter_api_key", e.target.value), placeholder: "volitelné, pokud je klíč v .env" }))
        ]),
        h(WizardFocusPanel, { step: campaignStep, form: effectiveForm, rawForm: form, isFinanceMode, activeAvatar, selectedImageSlots, draftPlan }),
        h("div", { className: "wizard-footer" },
          h("div", { className: "wizard-nav" },
            h("button", { type: "button", className: "secondary", disabled: campaignStep === 1 || runActive, onClick: goBack }, "Zpět"),
            campaignStep < 4
              ? h("button", { type: "button", key: "next-step", disabled: runActive || (campaignStep === 1 && !stepComplete(1)), onClick: goNext }, "Další krok")
              : h("button", { type: "button", key: "launch-generation", disabled: runActive || !stepComplete(1) || (isFinanceMode && !form.finance_scene_approved), onClick: launchGeneration }, runActive ? "Generuji..." : (isFinanceMode ? "Vygenerovat schválené finance video" : "Vygenerovat creative set"))
          ),
          file && h("div", { className: "hint" }, `Vybraný soubor: ${file.name}`),
          Boolean((competitorFiles || []).length) && h("div", { className: "hint" }, `Competitor screenshoty: ${competitorFiles.length}`)
        )
      ),
      h("div", { className: "studio-inspector" },
        h("section", { className: "section panel generation-plan-panel primary-plan-panel" },
          h(SectionHead, { title: "Plán před generací", subtitle: "Co vznikne, co se přeskočí a proč. Max obrázků je limit, ne požadavek na duplicity." }),
          h("div", { className: "generation-plan-summary" },
            summaryPill("Video", draftPlan.some((item) => item.media === "video" && item.status !== "SKIPPED") ? "ano" : "ne"),
            summaryPill("Statické sety", `${selectedImageSlots}`),
            summaryPill("Cap obrázků", isFinanceMode ? "0" : String(form.max_static_images)),
            summaryPill("Výstup", modeLabel)
          ),
          h("div", { className: "mini-pipeline-strip" },
            h("span", null, h("b", null, runActive ? "Pipeline běží" : "Pipeline idle"), runActive ? generationPhaseForRun(activeRun, displayProgress, isFinanceMode) : "spustí se po kliknutí na generovat"),
            h("span", null, h("b", null, "Průběh"), `${activePipelineSteps.length} kroků`),
            h("span", null, h("b", null, "Audit"), "finální prompty v Prompt laboratoři")
          ),
          h("div", { className: "generation-plan-cards preview-plan" },
            draftPlan.map((item) => generationPlanCard(item))
          ),
          h(PromptLearningGuidanceCard, { guidance: promptLearningGuidance })
        ),
        h("section", { className: "panel generation-cockpit" },
          h("div", { className: "cockpit-head" },
            h("div", null,
              h("div", { className: "eyebrow" }, "Řídicí panel generování"),
              h("h3", null, runActive ? "Generování běží" : "Připraveno ke generování"),
              h("p", null, runActive ? "Sleduj aktivní krok. Detailní prompty a payload jsou v Prompt laboratoři." : "Než klikneš na generovat, tady vidíš readiness, modely a přesný plán výstupů.")
            ),
            h("div", { className: "cockpit-progress" },
              h("b", null, runActive ? `${Math.round(displayProgress)}%` : "idle"),
              h("span", null, runActive ? generationPhaseForRun(activeRun, displayProgress, isFinanceMode) : "čeká na spuštění")
            )
          ),
          h("div", { className: "readiness-grid" },
            readinessItem(isFinanceMode ? "Scénář" : "Produkt", isFinanceMode ? (form.finance_video_script ? "připraveno" : "chybí") : (form.product_name ? "připraveno" : "chybí"), isFinanceMode ? Boolean(form.finance_video_script) : Boolean(form.product_name)),
            readinessItem("Avatar", activeAvatar?.name || form.avatar_id || "nevybrán", Boolean(form.avatar_id)),
            readinessItem("Režim", modeLabel, true),
            readinessItem("API key", form.openrouter_api_key ? "form" : ".env / runtime", true)
          ),
          h("div", { className: "model-strip compact" },
            summaryPill("Prompt", form.prompt_model),
            summaryPill("Image", form.generation_mode === "video" ? "přeskočeno" : form.image_model),
            summaryPill("Video", form.generation_mode === "static" ? "přeskočeno" : form.seedance_model)
          ),
          h(ProviderValidationCard, { validation: providerValidationPreview }),
          activeRunStages.length
            ? h(ActualRunTimeline, { run: activeRun })
            : (runActive || isFinanceMode)
            ? h("div", { className: "pipeline-timeline" },
              activePipelineSteps.map((step, index) => {
                const state = pipelineStepState(displayProgress, index, runActive, activePipelineSteps.length);
                return pipelineTimelineItem(step, index + 1, state);
              })
            )
            : h("div", { className: "pipeline-idle" },
              h("b", null, "Pipeline se spustí až po generování"),
              h("span", null, "V idle stavu appka ukazuje jen readiness a plán. Detailní průběh se rozbalí automaticky během běhu.")
            ),
          h(GenerationRunPanel, { run: activeRun, onCancel: cancelGenerationRun })
        ),
        h(ResultPreview, { latestPlan, generatedAssets, latestVideo })
      )
      )
    );
  }

  function ActualRunTimeline({ run }) {
    const stages = Array.isArray(run?.stage_results) ? run.stage_results : [];
    if (!stages.length) return null;
    const activeIndex = stages.length - 1;
    return h("div", { className: "actual-run-timeline" },
      h("div", { className: "actual-run-timeline-head" },
        h("div", null,
          h("b", null, "Skutečný průběh backendu"),
          h("span", null, `${stages.length} uložených kroků / aktuálně ${runStageLabel(run.current_stage || run.status)}`)
        ),
        h("span", { className: cls("pill", statusClass(run.status) || (isActiveRunStatus(run.status) ? "warn" : "pass")) }, run.status || "run")
      ),
      h("div", { className: "actual-run-stage-list" },
        stages.map((stage, index) => {
          const terminalTone = statusClass(stage.status);
          const state = terminalTone || (index < activeIndex ? "pass" : isActiveRunStatus(run.status) ? "warn" : statusClass(run.status) || "pass");
          const message = runStageMessage(stage);
          return h("div", { className: cls("actual-run-stage", state), key: `${stage.stage}-${index}` },
            h("span", { className: "stage-index" }, index + 1),
            h("div", null,
              h("b", null, runStageLabel(stage.stage)),
              h("small", null, `${stage.status || "stav"}${stage.updated_at ? ` / ${formatTime(stage.updated_at)}` : ""}`),
              message && h("p", null, message)
            )
          );
        })
      )
    );
  }

  function BriefQualityCard({ form, rawForm, isFinanceMode, activeAvatar }) {
    const checks = isFinanceMode
      ? [
        ["Scénář", Boolean(rawForm.finance_video_topic && rawForm.finance_video_script), "téma + hlavní sdělení"],
        ["Avatar", Boolean(activeAvatar || form.avatar_id), "osobní brand identita"],
        ["Scéna", Boolean(rawForm.finance_scene_approved), "schválený podcast podklad"],
        ["Compliance", Boolean(rawForm.finance_disclaimer), "disclaimer a čeština"]
      ]
      : [
        ["Produkt", Boolean(form.product_name), "název a category context"],
        ["Reference", Boolean(form.product_reference_url), "produktový obrázek / URL"],
        ["Avatar", Boolean(activeAvatar || form.avatar_id), "creator identity"],
        ["Plan", Boolean(form.generation_mode && form.prompt_model), "výstupy + modely"]
      ];
    const done = checks.filter((item) => item[1]).length;
    const percent = Math.round((done / checks.length) * 100);
    const tone = percent >= 75 ? "pass" : percent >= 50 ? "warn" : "danger";
    return h("div", { className: cls("brief-quality-card", tone) },
      h("div", { className: "brief-quality-head" },
        h("span", null, "Readiness"),
        h("b", null, `${percent}%`)
      ),
      h("div", { className: "brief-quality-track" },
        h("span", { style: { width: `${percent}%` } })
      ),
      h("div", { className: "brief-quality-list" },
        checks.map(([label, ready, body]) =>
          h("div", { className: cls("brief-quality-item", ready && "ready"), key: label },
            h("code", null, ready ? "OK" : "—"),
            h("span", null, h("b", null, label), h("small", null, body))
          )
        )
      )
    );
  }

  function SimpleCampaignChatMode({
    form,
    update,
    file,
    setFile,
    competitorFiles,
    appendCompetitorFiles,
    removeCompetitorFile,
    competitorFileLabel,
    chatBriefItems,
    setChatBriefItems,
    avatars,
    avatarOptions,
    activateAvatar,
    setView,
    displayAvatar,
    activeAvatar,
    draftPlan,
    selectedImageSlots,
    runActive,
    launchGeneration
  }) {
    const [chatDraft, setChatDraft] = useState("");
    const [pendingFiles, setPendingFiles] = useState([]);
    const [dragActive, setDragActive] = useState(false);
    const [parserBusy, setParserBusy] = useState(false);
    const [parserResult, setParserResult] = useState(null);
    const [localStatus, setLocalStatus] = useState("Phase 1: ruční chipy, Phase 2: AI Brief Parser.");

    const appendTextBlock = (current, addition) => {
      const clean = String(addition || "").trim();
      if (!clean) return current || "";
      const existing = String(current || "").trim();
      return existing ? `${existing}\n\n${clean}` : clean;
    };
    const urlsFromText = (text) => Array.from(new Set(String(text || "").match(/https?:\/\/[^\s)]+/g) || []));
    const firstTitleFromText = (text) => {
      const line = String(text || "").split(/\r?\n/).map((item) => item.trim()).find(Boolean) || "";
      return line.replace(/^[-*#\s]+/, "").slice(0, 80);
    };
    const appendPendingImages = (files) => {
      const images = Array.from(files || []).filter((item) => item && String(item.type || "").startsWith("image/"));
      if (!images.length) return;
      setPendingFiles((current) => [...(current || []), ...images].slice(0, 8));
      setLocalStatus(`${images.length} obrázků připravených v chatu.`);
    };
    const pastedImageFiles = (event) => Array.from(event.clipboardData?.items || [])
      .filter((item) => item.kind === "file" && String(item.type || "").startsWith("image/"))
      .map((item, index) => {
        const fileItem = item.getAsFile();
        if (!fileItem) return null;
        const extension = String(fileItem.type || "image/png").split("/")[1]?.replace("jpeg", "jpg") || "png";
        return new File([fileItem], `chat-paste-${Date.now()}-${index + 1}.${extension}`, {
          type: fileItem.type || "image/png",
          lastModified: Date.now(),
        });
      })
      .filter(Boolean);
    const handleChatPaste = (event) => {
      const images = pastedImageFiles(event);
      if (!images.length) return;
      event.preventDefault();
      appendPendingImages(images);
    };
    const addChatItem = (event) => {
      event?.preventDefault?.();
      const text = chatDraft.trim();
      if (!text && !pendingFiles.length) return;
      const item = {
        id: `chat-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        text,
        urls: urlsFromText(text),
        files: pendingFiles,
        applied_as: [],
        created_at: new Date().toISOString(),
      };
      setChatBriefItems((current) => [...(current || []), item]);
      setChatDraft("");
      setPendingFiles([]);
      setLocalStatus("Položka přidaná. Teď ji přiřaď chipem.");
    };
    const markApplied = (item, target) => {
      setChatBriefItems((current) => (current || []).map((entry) => entry.id === item.id
        ? { ...entry, applied_as: Array.from(new Set([...(entry.applied_as || []), target])) }
        : entry
      ));
    };
    const applyChatItem = (item, target) => {
      const text = String(item.text || "").trim();
      const urls = item.urls?.length ? item.urls : urlsFromText(text);
      const images = item.files || [];
      if (target === "product") {
        if (text) update("product_info", appendTextBlock(form.product_info, text));
        if (!form.product_name && text) update("product_name", firstTitleFromText(text));
        if (urls[0]) update("product_reference_url", urls[0]);
        if (!file && images[0]) setFile(images[0]);
        setLocalStatus("Položka použitá jako produktový brief.");
      }
      if (target === "competitor") {
        update("competitor_strategy_enabled", true);
        if (text) update("competitor_chat_brief", appendTextBlock(form.competitor_chat_brief, text));
        if (urls[0]) update("competitor_url", urls[0]);
        if (images.length) appendCompetitorFiles(images, "chat");
        setLocalStatus("Položka použitá jako competitor strategy.");
      }
      if (target === "avatar") {
        if (text) update("custom_avatar_persona", appendTextBlock(form.custom_avatar_persona, text));
        if (text) update("avatar_identity_note", appendTextBlock(form.avatar_identity_note, text));
        if (urls[0]) update("avatar_reference_url", urls[0]);
        setLocalStatus("Položka použitá jako avatar guidance.");
      }
      if (target === "direction") {
        const directionText = appendTextBlock(text, urls.filter((url) => !text.includes(url)).join("\n"));
        if (directionText) update("ugc_video_extra_prompt", appendTextBlock(form.ugc_video_extra_prompt, directionText));
        setLocalStatus("Položka použitá jako režie kreativy.");
      }
      markApplied(item, target);
    };
    const removePendingFile = (index) => setPendingFiles((current) => (current || []).filter((_item, itemIndex) => itemIndex !== index));
    const removeChatItem = (itemId) => setChatBriefItems((current) => (current || []).filter((item) => item.id !== itemId));
    const fileLabel = (item, index) => {
      const sizeKb = Math.max(1, Math.round(Number(item?.size || 0) / 1024));
      return `${item?.name || `image-${index + 1}.png`} / ${sizeKb} KB`;
    };
    const mergeField = (key, value) => {
      const clean = typeof value === "boolean" ? value : String(value || "").trim();
      if (clean === "" || clean === false || clean == null) return;
      if (typeof clean === "boolean") {
        update(key, clean);
        return;
      }
      if (["product_info", "competitor_chat_brief", "custom_avatar_persona", "avatar_identity_note", "ugc_video_extra_prompt"].includes(key)) {
        update(key, appendTextBlock(form[key], clean));
      } else if (!form[key] || ["platform", "market", "language", "generation_mode"].includes(key)) {
        update(key, clean);
      }
    };
    const applyParserResult = (result) => {
      const draft = result?.campaign_draft || {};
      Object.entries(draft).forEach(([key, value]) => mergeField(key, value));
      const itemsById = Object.fromEntries((chatBriefItems || []).map((item) => [item.id, item]));
      (result?.attachment_roles || []).forEach((role) => {
        const item = itemsById[role.item_id];
        const files = item?.files || [];
        if (!files.length) return;
        if (role.role === "product" && !file) setFile(files[0]);
        if (role.role === "competitor") {
          update("competitor_strategy_enabled", true);
          appendCompetitorFiles(files, "chat");
        }
      });
      setChatBriefItems((current) => (current || []).map((item) => {
        const roles = (result?.attachment_roles || []).filter((role) => role.item_id === item.id).map((role) => role.role);
        return roles.length ? { ...item, applied_as: Array.from(new Set([...(item.applied_as || []), ...roles])) } : item;
      }));
    };
    const parseChatBrief = async () => {
      if (!(chatBriefItems || []).length) {
        setLocalStatus("Nejdřív přidej aspoň jednu položku do chatu.");
        return;
      }
      setParserBusy(true);
      setLocalStatus("AI Brief Parser skládá strukturovaný draft...");
      try {
        const payload = {
          chatBriefItems: (chatBriefItems || []).map((item) => ({
            id: item.id,
            text: item.text || "",
            urls: item.urls || [],
            file_count: (item.files || []).length,
            file_names: (item.files || []).map((fileItem) => fileItem.name || "image"),
            applied_as: item.applied_as || [],
          })),
          current_form: {
            product_name: form.product_name,
            product_info: form.product_info,
            product_reference_url: form.product_reference_url,
            competitor_strategy_enabled: form.competitor_strategy_enabled,
            competitor_name: form.competitor_name,
            competitor_url: form.competitor_url,
            competitor_chat_brief: form.competitor_chat_brief,
            avatar_reference_url: form.avatar_reference_url,
            custom_avatar_persona: form.custom_avatar_persona,
            avatar_identity_note: form.avatar_identity_note,
            ugc_video_extra_prompt: form.ugc_video_extra_prompt,
            platform: form.platform,
            market: form.market,
            language: form.language,
            generation_mode: form.generation_mode,
          },
          openrouter_api_key: form.openrouter_api_key || "",
          prompt_model: form.prompt_model || "",
        };
        const result = await apiJson("/chat-brief-parser", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        setParserResult(result);
        applyParserResult(result);
        setLocalStatus(result.status === "ai_refined"
          ? "AI parser vyplnil brief."
          : "Deterministický parser vyplnil brief bez API klíče."
        );
      } catch (error) {
        setLocalStatus(`Parser selhal: ${error.message || error}`);
      } finally {
        setParserBusy(false);
      }
    };
    const generationLabel = form.generation_mode === "video" ? "Jen video" : form.generation_mode === "static" ? "Jen statiky" : "Video + statiky";

    return h("div", { className: "simple-chat-layout" },
      h("section", { className: "panel simple-chat-panel" },
        h(SectionHead, {
          title: "Simple Chat Mode",
          subtitle: "Vlož produkt, konkurenci, avatara nebo režii jako do chatu. Phase 1 používá ruční chipy; Phase 2 později přidá AI Brief Parser."
        }),
        h("div", { className: "simple-chat-settings" },
          field("Avatar", select(form.avatar_id, (v) => {
            const selected = (avatars || []).find((avatar) => avatar.id === v);
            if (selected) activateAvatar(selected);
            else update("avatar_id", v);
          }, avatarOptions)),
          field("Jazyk", select(form.language, (v) => update("language", v), [["en", "Angličtina"], ["cs", "Čeština"], ["de", "Němčina"], ["fr", "Francouzština"], ["pl", "Polština"]])),
          field("Trh", select(form.market, (v) => update("market", v), [["UK", "UK"], ["US", "US"], ["CZ", "CZ"], ["DE", "DE"], ["FR", "FR"], ["EU", "EU"]])),
          field("Platforma", select(form.platform, (v) => update("platform", v), [["meta", "Meta"], ["google_ads", "Google"], ["tiktok", "TikTok"], ["instagram", "IG"], ["youtube", "YouTube"]])),
          field("Výstup", segmented(form.generation_mode, (v) => update("generation_mode", v), [["both", "Video + statiky"], ["video", "Jen video"], ["static", "Jen statiky"]]))
        ),
        h("div", {
          className: cls("simple-chat-dropzone", dragActive && "active"),
          onPaste: handleChatPaste,
          onDragOver: (event) => {
            event.preventDefault();
            setDragActive(true);
          },
          onDragLeave: () => setDragActive(false),
          onDrop: (event) => {
            event.preventDefault();
            setDragActive(false);
            appendPendingImages(event.dataTransfer?.files);
          }
        },
          h("div", { className: "simple-chat-stream" },
            (chatBriefItems || []).length
              ? (chatBriefItems || []).map((item) => h("article", { className: "chat-brief-item", key: item.id },
                h("div", { className: "chat-brief-body" },
                  item.text && h("p", null, item.text),
                  Boolean(item.urls?.length) && h("div", { className: "chat-url-list" }, item.urls.map((url) => h("code", { key: url }, url))),
                  Boolean(item.files?.length) && h("div", { className: "competitor-file-list" }, item.files.map((image, index) =>
                    h("span", { className: "competitor-file-pill", key: `${image.name || "image"}-${index}` }, h("small", null, fileLabel(image, index)))
                  )),
                  Boolean(item.applied_as?.length) && h("small", { className: "chat-applied-label" }, `Použito: ${item.applied_as.join(", ")}`)
                ),
                h("div", { className: "chat-action-row" },
                  h("button", { type: "button", className: "secondary small", onClick: () => applyChatItem(item, "product") }, "Produkt"),
                  h("button", { type: "button", className: "secondary small", onClick: () => applyChatItem(item, "competitor") }, "Konkurence"),
                  h("button", { type: "button", className: "secondary small", onClick: () => applyChatItem(item, "avatar") }, "Avatar"),
                  h("button", { type: "button", className: "secondary small", onClick: () => applyChatItem(item, "direction") }, "Režie"),
                  h("button", { type: "button", className: "ghost-toggle", onClick: () => removeChatItem(item.id) }, "Odebrat")
                )
              ))
              : h("div", { className: "empty compact" }, "Vlož text, URL nebo obrázek. Potom vyber chip, kam se má položka propsat.")
          ),
          h("form", { className: "simple-chat-composer", onSubmit: addChatItem },
            h("textarea", {
              value: chatDraft,
              onChange: (event) => setChatDraft(event.target.value),
              onPaste: handleChatPaste,
              placeholder: "Např. Tady je produktový popis, URL konkurenta, poznámky k UGC stylu nebo text z reklamy konkurenta..."
            }),
            Boolean(pendingFiles.length) && h("div", { className: "competitor-file-list" }, pendingFiles.map((image, index) =>
              h("span", { className: "competitor-file-pill", key: `${image.name || "pending"}-${index}` },
                h("small", null, fileLabel(image, index)),
                h("button", { type: "button", onClick: () => removePendingFile(index), "aria-label": `Odebrat ${image.name || "image"}` }, "x")
              )
            )),
            h("div", { className: "simple-chat-actions" },
              h("label", { className: "secondary file-like-button" },
                "Vložit obrázek",
                h("input", { type: "file", accept: "image/*", multiple: true, onChange: (event) => {
                  appendPendingImages(event.target.files);
                  event.target.value = "";
                } })
              ),
              h("button", { type: "submit", disabled: !chatDraft.trim() && !pendingFiles.length }, "Přidat do chatu")
            )
          )
        ),
        h("div", { className: "simple-chat-footer" },
          h("span", null, localStatus),
          h("div", { className: "simple-chat-footer-actions" },
            h("button", { type: "button", className: "secondary", disabled: parserBusy || !(chatBriefItems || []).length, onClick: parseChatBrief }, parserBusy ? "Skládám brief..." : "AI vyplnit brief"),
            h("button", { type: "button", disabled: runActive || !form.product_name && !form.product_info && !file && !form.product_reference_url, onClick: launchGeneration }, runActive ? "Generuji..." : "Vygenerovat ad set")
          )
        )
      ),
      h("aside", { className: "simple-brief-sidebar" },
        simpleBriefCard("Product brief", [
          ["Název", form.product_name || "čeká"],
          ["Poznámky", form.product_info ? `${form.product_info.length} znaků` : "čeká"],
          ["Reference", form.product_reference_url || (file ? file.name : "čeká")]
        ]),
        simpleBriefCard("Avatar", [
          ["Vybraný", displayAvatar?.name || form.avatar_id || "čeká"],
          ["Reference", form.avatar_reference_url ? "URL připravena" : "prompt-only"],
          ["Persona", form.custom_avatar_persona ? `${form.custom_avatar_persona.length} znaků` : "výchozí"]
        ]),
        simpleBriefCard("Competitor strategy", [
          ["Mode", form.competitor_strategy_enabled ? "zapnuto" : "vypnuto"],
          ["Brief", form.competitor_chat_brief ? `${form.competitor_chat_brief.length} znaků` : "čeká"],
          ["Screenshoty", `${(competitorFiles || []).length}`]
        ]),
        simpleBriefCard("Generation settings", [
          ["Platforma", form.platform || "meta"],
          ["Trh / jazyk", `${form.market || "UK"} / ${form.language || "en"}`],
          ["Výstup", generationLabel]
        ]),
        h("section", { className: "simple-brief-card" },
          h("div", { className: "simple-brief-card-head" },
            h("b", null, "Generation plan"),
            h("small", null, `${selectedImageSlots} statik`)
          ),
          h("div", { className: "simple-plan-list" },
            (draftPlan || []).map((item) => h("span", { key: item.set_id },
              h("b", null, item.set_id),
              h("small", null, `${item.creative_type} / ${item.status}`)
            ))
          )
        ),
        parserResult && h("section", { className: "simple-brief-card" },
          h("div", { className: "simple-brief-card-head" },
            h("b", null, "AI Brief Parser"),
            h("small", null, parserResult.status || "draft")
          ),
          h("div", { className: "simple-brief-rows" },
            h("div", null, h("span", null, "Mode"), h("b", null, parserResult.parser_mode || "parser")),
            h("div", null, h("span", null, "Model"), h("b", null, parserResult.model || "fallback")),
            h("div", null, h("span", null, "Warnings"), h("b", null, `${(parserResult.warnings || []).length}`))
          )
        ),
        h("button", { type: "button", className: "secondary", onClick: () => setView("avatars") }, "Otevřít Avatar set")
      )
    );
  }

  function simpleBriefCard(title, rows) {
    return h("section", { className: "simple-brief-card" },
      h("div", { className: "simple-brief-card-head" }, h("b", null, title)),
      h("div", { className: "simple-brief-rows" },
        rows.map(([label, value]) => h("div", { key: label },
          h("span", null, label),
          h("b", null, value)
        ))
      )
    );
  }

  function WizardFocusPanel({ step, form, rawForm, isFinanceMode, activeAvatar, selectedImageSlots, draftPlan }) {
    const guidance = wizardGuidance(step, form, rawForm, isFinanceMode, activeAvatar, selectedImageSlots, draftPlan);
    return h("div", { className: cls("wizard-focus-panel", guidance.ready && "ready") },
      h("div", null,
        h("span", { className: "eyebrow" }, "Fokus kroku"),
        h("b", null, guidance.title),
        h("p", null, guidance.body)
      ),
      h("div", { className: "wizard-focus-checks" },
        guidance.items.map((item) => h("span", { key: item, className: "pill" }, item))
      )
    );
  }

  function wizardGuidance(step, form, rawForm, isFinanceMode, activeAvatar, selectedImageSlots, draftPlan) {
    if (step === 1 && isFinanceMode) {
      const ready = Boolean(rawForm.finance_video_topic && rawForm.finance_video_script);
      return {
        ready,
        title: ready ? "Scénář je připravený pro návrh scény" : "Začni tématem a čistým českým sdělením",
        body: ready
          ? "Další krok je připravit nebo schválit scénu. Video se nespustí, dokud není schválený vizuální podklad."
          : "Finance mód nejdřív skládá scénář a compliance, teprve potom generuje podcastovou scénu s infografikou.",
        items: ["čeština", "compliance", "podcast studio"]
      };
    }
    if (step === 1) {
      const hasReference = Boolean(form.product_reference_url || form.product_info);
      return {
        ready: Boolean(form.product_name && hasReference),
        title: hasReference ? "Produkt má dost kontextu pro creative plan" : "Doplň produktovou referenci nebo poznámky",
        body: "Poznámky jsou interní guidance pro prompt, nekopírují se přímo do reklam. Reference drží produktovou věrnost.",
        items: [form.product_category || "auto kategorie", hasReference ? "reference OK" : "chybí reference", "fidelity lock"]
      };
    }
    if (step === 2) {
      return {
        ready: Boolean(activeAvatar || form.avatar_id),
        title: activeAvatar ? `Vybraný avatar: ${activeAvatar.name || activeAvatar.id}` : "Vyber avatara z knihovny",
        body: "Avatar knihovna je zdroj pravdy pro identitu, hlas a reference. Aktivní avatar se uloží pro další generace.",
        items: [activeAvatar?.voice || "hlas", form.use_avatar_image_reference ? "image reference" : "prompt-only", "identity lock"]
      };
    }
    if (step === 3) {
      return {
        ready: Boolean(form.platform && form.market && form.language),
        title: `${form.platform || "platforma"} / ${form.market || "trh"} / ${form.language || "jazyk"}`,
        body: isFinanceMode
          ? "Finance brand je vynuceně česky a jen video pro Meta/Instagram."
          : "Trh a platforma ovlivní hook, jazyk, bezpečné zóny a creative mix.",
        items: [form.platform || "platforma", form.market || "trh", isFinanceMode ? "jen video" : form.generation_mode || "režim"]
      };
    }
    return {
      ready: true,
      title: isFinanceMode ? "Před spuštěním zkontroluj schválenou scénu" : "Před spuštěním zkontroluj plán výstupů",
      body: isFinanceMode
        ? "Generování vytvoří jedno ukázkové finance video. Statiky se v tomto modulu nespouští."
        : `Vybráno ${selectedImageSlots} image slotů. Max obrázků je limit, ne požadavek na doplnění duplicit.`,
      items: [form.prompt_model || "prompt model", isFinanceMode ? "0 statik" : `${selectedImageSlots} statik`, `${(draftPlan || []).length} plánů`]
    };
  }

  function ActivityTimeline({ latestRun, creatives }) {
    const stageItems = (Array.isArray(latestRun?.stage_results) ? latestRun.stage_results : [])
      .slice(-4)
      .map((stage) => ({
        type: "Run",
        title: runStageLabel(stage.stage),
        body: `${stage.status || "stav"}${stage.updated_at ? ` / ${formatTime(stage.updated_at)}` : ""}`,
        tone: stage.status
      }));
    const creativeItems = (creatives || []).slice(0, 4).map((creative) => ({
      type: creative.set_id || creative.type || "Asset",
      title: creative.product_name || creative.creative_id || "Kreativa",
      body: `${creative.angle || "angle"} / ${creative.latest_rating_status || creative.status || "stav"}`,
      tone: creative.latest_rating_status || creative.status
    }));
    const items = [...stageItems, ...creativeItems].slice(0, 6);
    if (!items.length) {
      return h("div", { className: "empty compact" }, "Zatím není aktivita. Spusť první kampaň nebo ohodnoť kreativu.");
    }
    return h("div", { className: "activity-timeline" },
      items.map((item, index) =>
        h("div", { className: "activity-item", key: `${item.type}-${item.title}-${index}` },
          h("span", { className: cls("activity-dot", statusClass(item.tone)) }),
          h("div", null,
            h("small", null, item.type),
            h("b", null, item.title),
            h("p", null, item.body)
          )
        )
      )
    );
  }

  function GenerationRunPanel({ run, onCancel }) {
    if (!run) {
      return h("div", { className: "generation-run-panel" },
        h("b", null, "Uložený běh generování"),
        h("span", null, "Po spuštění se tady zobrazí run_id, stav, fáze a uložený audit běhu.")
      );
    }
    const stages = Array.isArray(run.stage_results) ? run.stage_results : [];
    const latestStage = stages[stages.length - 1] || {};
    const canCancel = isActiveRunStatus(run.status) && !run.cancel_requested;
    const monitor = run.monitor || {};
    const cost = run.cost_summary || run.session_cost_summary || {};
    return h("div", { className: "generation-run-panel active" },
      h("div", { className: "run-panel-head" },
        h("div", null,
          h("b", null, run.run_id || "run"),
          h("span", null, `${run.workspace || "modul"} / ${monitor.status_label || run.status || "stav"} / ${monitor.stage_label || run.current_stage || "fáze"} / ${monitor.progress_percent || 0}%`)
        ),
        canCancel && h("button", { type: "button", className: "danger small", onClick: () => onCancel?.(run) }, "Zastavit")
      ),
      h("div", { className: "run-progress-track" },
        h("span", { style: { width: `${Math.min(100, Math.max(0, Number(monitor.progress_percent || 0)))}%` } })
      ),
      h("div", { className: "run-mini-metrics" },
        h("span", null, h("b", null, "Cena session"), h("small", null, cost.total_known_cost_usd_display || cost.total_known_cost_display || "zatím neznámá")),
        h("span", null, h("b", null, "Cena provideru"), h("small", null, cost.status || "čeká")),
        h("span", null, h("b", null, "API requesty"), h("small", null, `${cost.known_request_count || 0}/${cost.request_count || 0} známá cena`)),
        h("span", null, h("b", null, "Stage count"), h("small", null, monitor.stage_count || 0))
      ),
      h(CostBreakdown, { cost }),
      h("div", { className: "run-stage-list" },
        stages.slice(-5).map((stage, index) =>
          h("span", { key: `${stage.stage}-${index}` }, `${stage.stage}: ${stage.status}`)
        )
      ),
      run.final_export_status && h("p", { className: "hint" }, `Výsledek: ${run.final_export_status}`),
      (monitor.terminal_reason || run.last_error) && h("p", { className: "hint" }, monitor.terminal_reason || run.last_error),
      monitor.next_step && h("p", { className: "hint" }, `Další krok: ${monitor.next_step}`),
      Boolean((monitor.blockers || []).length) && h("div", { className: "run-blocker-list" },
        (monitor.blockers || []).map((blocker, index) =>
          h("span", { key: `${blocker.source}-${blocker.id}-${index}` },
            h("b", null, blocker.id || blocker.source || "blokace"),
            h("small", null, blocker.reason || blocker.next_step || "")
          )
        )
      ),
      run.cancel_requested && h("p", { className: "hint" }, "Cancel je uložený. Právě běžící provider request nemusí jít přerušit, ale další krok workflow se přeskočí."),
      latestStage?.data?.reason && h("p", { className: "hint" }, latestStage.data.reason)
    );
  }

  function CostBreakdown({ cost }) {
    const components = cost?.components || [];
    if (!cost || (!components.length && !cost.total_known_cost_display)) return null;
    return h("div", { className: "cost-breakdown" },
      h("div", { className: "cost-breakdown-head" },
        h("b", null, "OpenRouter cena celé generace"),
        h("span", { className: cls("pill", cost.status === "complete" ? "pass" : cost.status === "partial" ? "warn" : "") },
          `${cost.total_known_cost_usd_display || cost.total_known_cost_display || "unknown"} / ${cost.status || "unknown"}`
        )
      ),
      h("div", { className: "mini-table compact" },
        components.map((component, index) =>
          h("div", { key: `${component.component}-${index}` },
            h("b", null, component.component),
            h("span", null,
              `${component.cost_usd_display || component.cost_display || "unknown"} · ${component.status || "stav"} · ${component.request_count || 0} req`
            )
          )
        )
      ),
      Boolean((cost.unknown_cost_components || []).length) && h("p", { className: "hint" },
        `Neznámá cena: ${(cost.unknown_cost_components || []).join(", ")}`
      ),
      cost.note && h("p", { className: "hint" }, cost.note)
    );
  }

  function PromptLearningGuidanceCard({ guidance }) {
    if (!guidance) {
      return h("div", { className: "learning-guidance-card muted" },
        h("div", { className: "learning-guidance-head" },
          h("div", null,
            h("div", { className: "eyebrow" }, "Agent učení promptů"),
            h("h4", null, "Čekám na RAG guidance")
          ),
          h("span", { className: "pill" }, "načítám")
        ),
        h("p", null, "Jakmile vyplníš brief, aplikace zkontroluje memory pro stejný modul, kategorii, trh a platformu.")
      );
    }
    const query = guidance.query || {};
    const counts = guidance.memory_counts || {};
    const winning = guidance.winning_patterns || [];
    const avoid = guidance.avoid_patterns || [];
    return h("div", { className: cls("learning-guidance-card", guidance.has_memory && "active") },
      h("div", { className: "learning-guidance-head" },
        h("div", null,
          h("div", { className: "eyebrow" }, guidance.agent || "Prompt Learning Agent"),
          h("h4", null, guidance.has_memory ? "Guidance pro další generaci" : "Zatím bez historické shody")
        ),
        h("span", { className: cls("pill", guidance.has_memory ? "pass" : "warn") },
          guidance.workspace || "modul"
        )
      ),
      h("div", { className: "mini-table compact" },
        h("div", null, h("b", null, "Dotaz"), h("span", null, `${query.category || "auto"} / ${query.market || "-"} / ${query.platform || "-"}`)),
        h("div", null, h("b", null, "Memory"), h("span", null, `${counts.matching_winner_count || 0} winners / ${counts.matching_rejected_count || 0} avoid / ${counts.knowledge_item_count || 0} knowledge`))
      ),
      h("p", null, guidance.prompt_insert || "Bez uložených signálů. Generace pojede z aktuálního briefu a category presets."),
      (winning.length || avoid.length)
        ? h("div", { className: "learning-guidance-split" },
          h("div", null, h("b", null, "Preferovat"), chips(winning.slice(0, 6))),
          h("div", null, h("b", null, "Vyhnout se"), chips(avoid.slice(0, 6)))
        )
        : h("p", { className: "hint" }, "Po schválení/zamítnutí kreativ a uložení CTR/ROAS se tady objeví konkrétní doporučení.")
    );
  }

  function ProviderValidationCard({ validation }) {
    if (!validation) {
      return h("div", { className: "provider-validation-card muted" },
        h("b", null, "Kontrola providerů"),
        h("span", null, "Čekám na kontrolu modelů a limitů.")
      );
    }
    const checks = validation.checks || [];
    const failed = checks.filter((item) => item.status === "failed");
    const warnings = checks.filter((item) => item.status === "warning");
    const visibleChecks = [...failed, ...warnings, ...checks.filter((item) => item.status === "passed").slice(0, 3)];
    return h("div", { className: cls("provider-validation-card", validation.status === "blocked" ? "blocked" : "passed") },
      h("div", { className: "provider-validation-head" },
        h("div", null,
          h("b", null, validation.status === "blocked" ? "Blokace před generací" : "Připravenost providerů"),
          h("span", null, `${validation.workspace || "modul"} / ${validation.generation_mode || "režim"}`)
        ),
        h("span", { className: cls("pill", validation.status === "blocked" ? "danger" : warnings.length ? "warn" : "pass") },
          validation.status === "blocked" ? "blocked" : warnings.length ? `${warnings.length} warning` : "passed"
        )
      ),
      validation.reason && h("p", null, validation.reason),
      h("div", { className: "provider-check-list" },
        visibleChecks.map((item) =>
          h("span", { key: item.id, className: cls("provider-check", item.status) },
            h("b", null, item.id),
            h("small", null, item.reason || item.next_step || item.status)
          )
        )
      )
    );
  }

  function PromptDiffCard({ title, diff, emptyText }) {
    const isMapDiff = diff && Array.isArray(diff.items);
    const changed = isMapDiff ? Number(diff.changed_count || 0) > 0 : Boolean(diff?.changed);
    const preview = isMapDiff
      ? (diff.items || []).slice(0, 2).map((item) => `${item.key}\n${item.unified_diff_preview || ""}`).join("\n\n")
      : diff?.unified_diff_preview;
    return h("div", { className: cls("diff-card", changed ? "changed" : "clean") },
      h("div", { className: "diff-card-head" },
        h("b", null, title),
        h("span", { className: cls("pill", changed ? "warn" : "pass") },
          changed ? (isMapDiff ? `${diff.changed_count}/${diff.total_compared}` : "changed") : "no diff"
        )
      ),
      preview
        ? h("pre", null, preview)
        : h("p", null, emptyText || "Bez rozdílu.")
    );
  }

  function ResultPreview({ latestPlan, generatedAssets, latestVideo }) {
    const videoAsset = latestVideo ? {
      creative_id: "C1 UGC video",
      set_id: "C1",
      type: "video",
      asset_url: latestVideo.video_url || latestVideo.video_path || "",
      status: latestVideo.video_generation_status,
      failure_reason: latestVideo.failure_reason || latestVideo.error,
      next_step: latestVideo.next_step
    } : null;
    const assets = [
      ...(videoAsset ? [videoAsset] : []),
      ...generatedAssets
    ];
    if (!latestPlan.length && !assets.length) return null;
    return h("section", { className: "section" },
      h(SectionHead, { title: "Poslední vygenerovaný set", subtitle: "Čerstvý výstup se tady zobrazí hned po generování." }),
      h("div", { className: "creative-grid" },
        assets.slice(0, 9).map((asset) =>
          h("div", { className: "creative-card", key: asset.creative_id || asset.image_url },
            renderCreativePreview(asset),
            h("div", { className: "creative-body" },
              h("strong", null, asset.creative_id || asset.set_id || "Kreativa"),
              h("div", { className: "pill-row" }, h("span", { className: "pill" }, asset.set_id || "set"), h("span", { className: "pill" }, asset.angle || "angle")),
              h("p", { className: "hint" }, asset.failure_reason || limit(asset.prompt || asset.visual_prompt || asset.next_step || ""))
            )
          )
        )
      )
    );
  }

  function FinanceSceneApproval({ form, sceneBusy, preview, prepareFinanceScene, approveFinanceScene }) {
    const asset = preview?.scene_image_generation?.image_assets?.[0] || {};
    const imageUrl = normalizeAssetUrl(asset.image_url || preview?.scene_reference_url || form.finance_scene_reference_url || "");
    const concept = preview?.finance_scene_concept || {};
    const imageStatus = preview?.scene_image_generation?.image_generation_status;
    const approved = Boolean(form.finance_scene_approved);
    return h("div", { className: cls("finance-scene-approval", approved && "approved") },
      h("div", { className: "scene-approval-head" },
        h("div", null,
          h("div", { className: "eyebrow" }, "Finance scene gate"),
          h("h4", null, "1. Scénář + návrh scény"),
          h("p", null, "Nejdřív se připraví scénář a moderní podcast-studio podklad přes Banana/Gemini image model. Video se spustí až po schválení.")
        ),
        h("span", { className: cls("pill", approved ? "pass" : "warn") }, approved ? "schváleno" : "čeká")
      ),
      h("div", { className: "action-row" },
        h("button", { type: "button", className: "secondary", disabled: sceneBusy, onClick: prepareFinanceScene }, sceneBusy ? "Připravuji scénu..." : "Připravit scénář a scénu"),
        h("button", { type: "button", disabled: sceneBusy || (!preview && !form.finance_scene_prompt), onClick: approveFinanceScene }, approved ? "Scéna schválená" : "Schválit scénu")
      ),
      imageUrl && h("div", { className: "scene-concept-preview" },
        h("img", { src: imageUrl, alt: "Návrh podcastové finance scény" })
      ),
      imageStatus && h("p", { className: "hint" }, `Stav obrázku: ${imageStatus}${preview?.scene_reference_public_for_video ? " | veřejná reference URL půjde do videa" : " | lokální náhled se použije jako schválená režie v promptu"}`),
      preview?.avatar_reference_used_for_scene && h("p", { className: "hint" },
        `Avatar reference použita už pro návrh scény: ${preview.avatar_scene_reference_type === "public_url" ? "veřejná URL" : "lokální/reference obraz"}`
      ),
      concept.hook && h("div", { className: "scene-concept-copy" },
        h("b", null, "Hook"),
        h("span", null, concept.hook)
      ),
      concept.interaction_plan?.length ? h("div", { className: "scene-concept-copy" },
        h("b", null, "Interakce avatara s grafikou"),
        h("ul", null, concept.interaction_plan.map((item) => h("li", { key: item }, item)))
      ) : null,
      concept.infographic_elements?.length ? h("div", { className: "scene-concept-copy" },
        h("b", null, "Schvalovaná infografika"),
        h("ul", null, concept.infographic_elements.map((item) =>
          h("li", { key: item.role || item.label }, `${item.label} - ${item.motion || item.role}`)
        ))
      ) : null,
      concept.image_prompt && h("details", { className: "audit-details" },
        h("summary", null, "Scene image prompt"),
        h("pre", null, concept.image_prompt)
      )
    );
  }

  function AvatarLibrary({ avatars, activeAvatarId, form, update, activateAvatar, activateExternalAvatar, saveAvatarProfile, uploadAvatarProfile, makeDefaultAvatar, setView }) {
    const emptyDraft = { id: "", name: "", image_url: "", style: "natural UGC creator", voice: "natural British English creator voice", is_default: false };
    const [draft, setDraft] = useState(emptyDraft);
    const [editingId, setEditingId] = useState("");
    const [avatarFile, setAvatarFile] = useState(null);
    const [savingAvatar, setSavingAvatar] = useState(false);
    const [formOpen, setFormOpen] = useState(false);
    const [avatarSearch, setAvatarSearch] = useState("");
    const [avatarFilter, setAvatarFilter] = useState("all");
    const sorted = [...(avatars || [])].sort((a, b) => Number(b.is_default) - Number(a.is_default) || Number(b.stats?.ad_sets_used || 0) - Number(a.stats?.ad_sets_used || 0));
    const activeAvatar = sorted.find((avatar) => avatar.id === activeAvatarId) || sorted.find((avatar) => avatar.is_default) || sorted[0] || null;
    const visibleAvatars = sorted.filter((avatar) => {
      const normalized = avatarSearch.trim().toLowerCase();
      const stats = avatar.stats || {};
      const haystack = `${avatar.id || ""} ${avatar.name || ""} ${avatar.style || avatar.persona || ""} ${avatar.voice || ""}`.toLowerCase();
      const passSearch = !normalized || haystack.includes(normalized);
      const passFilter = avatarFilter === "all"
        || (avatarFilter === "active" && avatar.id === activeAvatarId)
        || (avatarFilter === "default" && avatar.is_default)
        || (avatarFilter === "used" && Number(stats.ad_sets_used || stats.creative_count || 0) > 0)
        || (avatarFilter === "top" && (Number(stats.avg_rating || 0) >= 4 || Number(stats.avg_ctr || 0) >= 1.5 || Number(stats.avg_roas || 0) >= 2));
      return passSearch && passFilter;
    });

    function startEdit(avatar) {
      setEditingId(avatar.id || "");
      setFormOpen(true);
      setAvatarFile(null);
      setDraft({
        id: avatar.id || "",
        name: avatar.name || "",
        image_url: avatar.image_url || "",
        style: avatar.style || avatar.persona || "natural UGC creator",
        voice: avatar.voice || "natural conversational creator voice",
        is_default: Boolean(avatar.is_default)
      });
    }

    function resetDraft() {
      setEditingId("");
      setAvatarFile(null);
      setDraft(emptyDraft);
      setFormOpen(false);
    }

    async function submitAvatar(event) {
      event.preventDefault();
      setSavingAvatar(true);
      try {
        const profile = { ...draft, id: draft.id || clientSlug(draft.name || "avatar") };
        if (avatarFile) await uploadAvatarProfile(profile, avatarFile);
        else await saveAvatarProfile(profile);
        resetDraft();
      } finally {
        setSavingAvatar(false);
      }
    }

    useEffect(() => {
      if (!formOpen) return undefined;
      const onKeyDown = (event) => {
        if (event.key === "Escape") resetDraft();
      };
      window.addEventListener("keydown", onKeyDown);
      return () => window.removeEventListener("keydown", onKeyDown);
    }, [formOpen]);

    return h("div", null,
      h("section", { className: "avatar-command" },
        h("div", { className: "avatar-command-copy" },
          h("div", { className: "eyebrow" }, "Avatar intelligence"),
          h("h2", null, "Knihovna avatarů pro konzistentní osobu v reklamách"),
          h("p", null, "Aktivní avatar se používá v nové kampani, finance scénách i UGC promptu. Knihovna je zdroj pravdy pro reference, hlas, styl a performance signály.")
        ),
        h("div", { className: "avatar-command-actions" },
          h("button", { type: "button", onClick: () => setView("studio") }, "Použít ve studiu"),
          h("button", { type: "button", className: "secondary", onClick: () => { setEditingId(""); setDraft(emptyDraft); setAvatarFile(null); setFormOpen(true); } }, "Přidat avatara"),
          h("button", { type: "button", className: "secondary", onClick: () => setView("analytics") }, "Výkon avatarů")
        )
      ),
      h("section", { className: "section avatar-overview" },
        h("div", { className: "active-avatar-panel" },
          activeAvatar
            ? [
              h("div", { className: "active-avatar-media", key: "media" },
                avatarPreviewUrl(activeAvatar)
                  ? h("img", { src: avatarPreviewUrl(activeAvatar), alt: activeAvatar.name || activeAvatar.id })
                  : h("div", { className: "avatar-placeholder" }, "Bez obrázku")
              ),
              h("div", { className: "active-avatar-copy", key: "copy" },
                h("div", { className: "eyebrow" }, activeAvatar.id === activeAvatarId ? "Aktivní avatar" : "Doporučený default"),
                h("h3", null, activeAvatar.name || activeAvatar.id),
                h("p", null, activeAvatar.style || activeAvatar.persona || "UGC creator"),
                h("div", { className: "pill-row" },
                  h("span", { className: "pill pass" }, activeAvatar.id === activeAvatarId ? "používá se" : "připraven"),
                  activeAvatar.is_default && h("span", { className: "pill warn" }, "výchozí"),
                  activeAvatar.voice && h("span", { className: "pill" }, activeAvatar.voice)
                ),
                h("div", { className: "avatar-stat-grid featured" },
                  avatarMetric("Ad sety", activeAvatar.stats?.ad_sets_used || 0, "použití"),
                  avatarMetric("Rating", activeAvatar.stats?.avg_rating ? `${activeAvatar.stats.avg_rating}/5` : "-", "průměr"),
                  avatarMetric("CTR", activeAvatar.stats?.avg_ctr ? `${activeAvatar.stats.avg_ctr}%` : "-", "průměr"),
                  avatarMetric("ROAS", activeAvatar.stats?.avg_roas || "-", "průměr")
                ),
                h("div", { className: "action-row" },
                  h("button", { type: "button", onClick: () => activateAvatar(activeAvatar) }, activeAvatar.id === activeAvatarId ? "Aktivní" : "Aktivovat"),
                  h("button", { type: "button", className: "secondary", onClick: () => startEdit(activeAvatar) }, "Upravit profil"),
                  !activeAvatar.is_default && h("button", { type: "button", className: "secondary", onClick: () => makeDefaultAvatar(activeAvatar) }, "Nastavit default")
                )
              )
            ]
            : h("div", { className: "empty" }, "Zatím není uložený žádný avatar. Přidej veřejnou URL nebo nahraj referenční obrázek.")
        ),
        h("div", { className: "avatar-side-stack" },
          h("div", { className: "avatar-consent-card panel card" },
            h("div", { className: "eyebrow" }, "Autorizace"),
            h("h4", null, "Souhlas pro použití podoby"),
            authorizedAvatarConsent(form.avatar_own_person_consent, (v) => update("avatar_own_person_consent", v)),
            h("p", { className: "hint" }, "Stejnou volbu najdeš i v Nová kampaň -> krok Avatar. Do generování se posílá jako avatar_own_person_consent.")
          ),
          h("div", { className: "avatar-guidance-card panel card" },
            h("h4", null, "Doporučení podle použití"),
            h("p", null, activeAvatar ? avatarFitRecommendation(activeAvatar, activeAvatar.stats || {}) : "Po prvních rating/performance signálech se tady objeví, pro jaký typ kampaní je avatar nejlepší."),
            h("div", { className: "avatar-guidance compact" },
              avatarGuidanceItem("Cold traffic", "Vyšší CTR, přirozený výraz, rychlý hook."),
              avatarGuidanceItem("Retargeting", "Brand fit, product fidelity, důvěryhodnost."),
              avatarGuidanceItem("Finance brand", "Klidný projev, čeština, gesta k infografice.")
            )
          )
        ),
        null
      ),
      formOpen && h("div", { className: "avatar-edit-overlay", role: "dialog", "aria-modal": "true", onClick: resetDraft },
        h("div", { className: "avatar-edit-dialog", onClick: (event) => event.stopPropagation() },
          h("div", { className: "avatar-edit-head" },
            h("div", null,
              h("div", { className: "eyebrow" }, editingId ? "Editace avatara" : "Nový avatar"),
              h("h3", null, editingId ? "Upravit profil avatara" : "Přidat avatara do knihovny"),
              h("p", null, "URL, upload, persona a hlas pro konzistentní UGC identitu.")
            ),
            h("button", { type: "button", className: "secondary small", onClick: resetDraft, "aria-label": "Zavřít editor avatara" }, "Zavřít")
          ),
          h("form", { className: "avatar-form avatar-edit-form", onSubmit: submitAvatar },
            h("p", null, "Ulož vlastní nebo autorizovaný avatar. Veřejná URL se použije pro video reference, lokální upload hlavně pro náhled a knihovnu."),
            h("div", { className: "grid-2" },
              field("ID", h("input", { value: draft.id, disabled: Boolean(editingId), onChange: (e) => setDraft({ ...draft, id: e.target.value }), placeholder: "např. british_creator_01", required: true })),
              field("Název", h("input", { value: draft.name, onChange: (e) => setDraft({ ...draft, name: e.target.value }), placeholder: "Můj AI avatar", required: true }))
            ),
            field("Image URL", h("input", { value: draft.image_url, onChange: (e) => setDraft({ ...draft, image_url: e.target.value }), placeholder: "https://..." })),
            field("Nahrát obrázek", h("input", { type: "file", accept: "image/*", onChange: (e) => setAvatarFile(e.target.files?.[0] || null) })),
            field("Persona / styl", h("input", { value: draft.style, onChange: (e) => setDraft({ ...draft, style: e.target.value }) })),
            field("Hlas / přízvuk", h("input", { value: draft.voice, onChange: (e) => setDraft({ ...draft, voice: e.target.value }) })),
            checkbox("Nastavit jako výchozího avatara", draft.is_default, (v) => setDraft({ ...draft, is_default: v })),
            h("div", { className: "action-row avatar-edit-actions" },
              h("button", { type: "submit", disabled: savingAvatar || !draft.name }, savingAvatar ? "Ukládám..." : (editingId ? "Uložit změny" : "Přidat avatara")),
              draft.image_url && h("button", { type: "button", className: "secondary", onClick: () => activateExternalAvatar(draft) }, "Aktivovat URL bez uložení"),
              h("button", { type: "button", className: "secondary", onClick: resetDraft }, editingId ? "Zrušit editaci" : "Zavřít")
            )
          )
        )
      ),
      h("section", { className: "section" },
        h(SectionHead, {
          title: "Avatar set",
          subtitle: "Výchozí avatar se použije v nové kampani, pokud není ručně aktivovaný jiný. Zelený rámeček ukazuje aktuálně aktivního avatara."
        }),
        h("div", { className: "avatar-toolbar" },
          h("div", { className: "search-field" },
            h("span", null, "Hledat"),
            h("input", { value: avatarSearch, onChange: (event) => setAvatarSearch(event.target.value), placeholder: "název, styl, hlas..." })
          ),
          h("div", { className: "layout-toggle avatar-filter" },
            ["all", "active", "default", "used", "top"].map((filter) =>
              h("button", { key: filter, type: "button", className: cls(avatarFilter === filter && "active"), onClick: () => setAvatarFilter(filter) }, avatarFilterLabel(filter))
            )
          )
        ),
        h("div", { className: "avatar-grid" },
          visibleAvatars.map((avatar) => h(AvatarCard, {
            key: avatar.id,
            avatar,
            active: avatar.id === activeAvatarId,
            activateAvatar,
            startEdit,
            makeDefaultAvatar
          }))
        ),
        !visibleAvatars.length && h("div", { className: "empty" }, "Žádný avatar neodpovídá filtru.")
      )
    );
  }

  function AvatarCard({ avatar, active, activateAvatar, startEdit, makeDefaultAvatar }) {
    const stats = avatar.stats || {};
    const preview = avatarPreviewUrl(avatar);
    const bestAngles = (stats.best_angles || []).map((item) => `${item.name} (${item.count})`).join(", ");
    const bestMarkets = (stats.best_markets || []).map((item) => item.name).join(", ");
    return h("article", { className: cls("avatar-card", active && "active") },
      h("div", { className: "avatar-preview" },
        preview
          ? h("img", { src: preview, alt: avatar.name || avatar.id })
          : h("div", { className: "avatar-placeholder" }, "Bez obrázku"),
        active && h("span", { className: "active-badge" }, "Aktivní")
      ),
      h("div", { className: "avatar-info" },
        h("div", { className: "creative-title" },
          h("div", null,
            h("strong", null, avatar.name || avatar.id),
            h("div", { className: "hint" }, avatar.id)
          ),
          h("span", { className: cls("pill", active ? "pass" : (avatar.is_default ? "warn" : "warn")) }, active ? "používá se" : (avatar.is_default ? "výchozí" : "neaktivní"))
        ),
        h("p", null, avatar.style || avatar.persona || "UGC creator"),
        h("div", { className: "avatar-stat-grid" },
          avatarMetric("Ad sety", stats.ad_sets_used || 0, "použití"),
          avatarMetric("Kreativy", stats.creative_count || 0, "assetů"),
          avatarMetric("Rating", stats.avg_rating ? `${stats.avg_rating}/5` : "-", "průměr"),
          avatarMetric("CTR", stats.avg_ctr ? `${stats.avg_ctr}%` : "-", "průměr"),
          avatarMetric("ROAS", stats.avg_roas || "-", "průměr"),
          avatarMetric("Schváleno", stats.approved_count || 0, "ks")
        ),
        h("div", { className: "memory-signal" },
          h("b", null, "Hodi se na"),
          h("span", null, avatarFitRecommendation(avatar, stats))
        ),
        h("div", { className: "pill-row" },
          bestAngles && h("span", { className: "pill" }, `angles: ${bestAngles}`),
          bestMarkets && h("span", { className: "pill" }, `markets: ${bestMarkets}`),
          avatar.local_image_only && h("span", { className: "pill warn" }, "lokální náhled"),
          avatar.voice && h("span", { className: "pill" }, avatar.voice)
        ),
        h("div", { className: "action-row" },
          h("button", { type: "button", onClick: () => activateAvatar(avatar) }, active ? "Aktivní avatar" : "Aktivovat"),
          h("button", { type: "button", className: "secondary", onClick: () => startEdit(avatar) }, "Upravit"),
          !avatar.is_default && h("button", { type: "button", className: "secondary", onClick: () => makeDefaultAvatar(avatar) }, "Nastavit default")
        )
      )
    );
  }

  function Library(props) {
    const { creatives, allCreatives, activeMode, filters, setFilters, products, angles, statuses, layout, setLayout, openPreview, saveRating, savePerformance } = props;
    const campaignGroups = groupCreativesByCampaign(creatives);
    const activeMeta = moduleMeta(activeMode);
    const [collapsedGroups, setCollapsedGroups] = useState({});
    const reviewCount = creatives.filter((item) => !item.latest_rating_status && !["approved", "rejected"].includes(String(item.status || "").toLowerCase())).length;
    const failedCount = creatives.filter((item) => ["failed", "blocked"].includes(String(item.status || item.latest_rating_status || "").toLowerCase())).length;
    const missingPerformanceCount = creatives.filter((item) => Number(item.performance_count || 0) === 0).length;
    const approvedCount = creatives.filter((item) => item.latest_rating_status === "approved").length;
    const nextAction = failedCount
      ? "Nejdřív otevři blokované/chybové assety a přečti důvod."
      : reviewCount
      ? "Začni rychlým approve/reject u assetů bez hodnocení."
      : missingPerformanceCount
      ? "Doplň CTR/CPC/ROAS u schválených kreativ."
      : "Workspace je uklizený. Vyber winner a vytvoř novou variantu.";
    function applySavedView(view) {
      const base = { ...filters, mode: activeMode, search: "", type: "all", angle: "all", status: "all", product: "all", performance: "all" };
      const presets = {
        current: base,
        review: { ...base, status: "unrated" },
        approved: { ...base, status: "approved" },
        rejected: { ...base, status: "rejected" },
        no_performance: { ...base, performance: "missing" },
        video: { ...base, type: "video" },
        static: { ...base, type: "static_image" }
      };
      setFilters(presets[view] || base);
    }
    function toggleGroup(groupId) {
      setCollapsedGroups((current) => ({ ...current, [groupId]: !current[groupId] }));
    }
    return h("div", null,
      h(SectionHead, {
        title: `${activeMeta.label}: creative sety`,
        subtitle: "Seznam se automaticky řídí pracovním modulem. Přepni modul v levém menu a uvidíš jen odpovídající kampaně."
      }),
      h("section", { className: "library-ops" },
        h("div", { className: "library-next-action" },
          h("div", { className: "eyebrow" }, "Doporučený další krok"),
          h("h3", null, nextAction),
          h("p", null, "Tahle stránka je review cockpit: nejdřív rozhodnutí, potom performance, potom učení pro další generaci."),
          h("div", { className: "action-row" },
            h("button", { type: "button", onClick: () => applySavedView("review") }, "Ke schválení"),
            h("button", { type: "button", className: "secondary", onClick: () => applySavedView("no_performance") }, "Bez performance"),
            h("button", { type: "button", className: "secondary", onClick: () => setFilters({ ...filters, status: "failed" }) }, "Chyby")
          )
        ),
        h("div", { className: "library-scoreboard" },
          libraryScore("Kampaně", campaignGroups.length, "skupiny"),
          libraryScore("Ke kontrole", reviewCount, "bez ratingu"),
          libraryScore("Schválené", approvedCount, "winners kandidáti"),
          libraryScore("Bez performance", missingPerformanceCount, "čeká na data")
        )
      ),
      h("div", { className: "library-toolbar" },
        h("div", { className: "filters" },
          h("input", { value: filters.search, onChange: (e) => setFilters({ ...filters, search: e.target.value }), placeholder: "Hledat produkt, ID, angle..." }),
          filterSelect(filters.mode, (v) => setFilters({ ...filters, mode: v }), ["all", "ecommerce", "finance_personal_brand"]),
          filterSelect(filters.type, (v) => setFilters({ ...filters, type: v }), ["all", ...new Set(allCreatives.map((x) => x.type).filter(Boolean))]),
          filterSelect(filters.angle, (v) => setFilters({ ...filters, angle: v }), ["all", ...angles]),
          filterSelect(filters.status, (v) => setFilters({ ...filters, status: v }), ["all", ...statuses]),
          filterSelect(filters.product, (v) => setFilters({ ...filters, product: v }), ["all", ...products]),
          filterSelect(filters.performance, (v) => setFilters({ ...filters, performance: v }), [["all", "Výkon: vše"], ["missing", "Bez performance"], ["has", "Má performance"]])
        ),
        h("div", { className: "layout-toggle", "aria-label": "Rozložení creative setů" },
          h("button", { type: "button", className: cls(layout === "grid" && "active"), "aria-pressed": layout === "grid", onClick: () => setLayout("grid") }, "Grid"),
          h("button", { type: "button", className: cls(layout === "row" && "active"), "aria-pressed": layout === "row", onClick: () => setLayout("row") }, "Řádky")
        )
      ),
      h("div", { className: "module-filter-note" },
        moduleBadge(activeMode),
        h("span", null, `${creatives.length} assetů v aktuálním modulu`),
        filters.mode !== activeMode && h("span", { className: "pill warn" }, "ruční filtr modulu")
      ),
      h("div", { className: "saved-view-bar" },
        savedViewButton("Aktuální modul", "current", applySavedView),
        savedViewButton("Ke schválení", "review", applySavedView),
        savedViewButton("Schválené", "approved", applySavedView),
        savedViewButton("Zamítnuté", "rejected", applySavedView),
        savedViewButton("Bez performance", "no_performance", applySavedView),
        savedViewButton("Videa", "video", applySavedView),
        savedViewButton("Statiky", "static", applySavedView)
      ),
      layout === "row" && h("div", { className: "hint layout-hint" }, "Řádkový pohled: klikni na obrázek nebo video pro větší náhled."),
      campaignGroups.length ? h("div", { className: "campaign-group-list" },
        campaignGroups.map((group, index) => {
          const collapsed = collapsedGroups[group.id] ?? index > 0;
          return h("section", { className: cls("campaign-group", collapsed && "collapsed"), key: group.id },
            h("div", { className: "campaign-group-head" },
              h("div", null,
                h("div", { className: "eyebrow" }, group.session || group.id),
                h("h3", null, group.product),
                h("p", null, `${moduleMeta(group.module).label} / ${group.platform} / ${group.market} / ${group.category} / ${group.items.length} assetů`),
                h("div", { className: "campaign-decision" },
                  h("b", null, campaignNextAction(group)),
                  h("span", null, campaignCoverage(group))
                )
              ),
              h("div", { className: "campaign-group-metrics" },
                campaignMetric("Schváleno", group.approved),
                campaignMetric("Performance", group.performance),
                campaignMetric("Cena", group.cost),
                h("button", { type: "button", className: "secondary small", onClick: () => toggleGroup(group.id) }, collapsed ? "Rozbalit" : "Sbalit")
              )
            ),
            !collapsed && h("div", { className: layout === "row" ? "creative-list" : "creative-grid" },
              group.items.map((creative) => h(CreativeCard, {
                key: creative.creative_id,
                creative,
                layout,
                openPreview,
                saveRating,
                savePerformance
              }))
            )
          );
        })
      ) : h("div", { className: "empty" }, "V creative memory zatím nejsou žádné kreativy. Nejprve vygeneruj kampaň.")
    );
  }

  function CreativeCard({ creative, layout, openPreview, saveRating, savePerformance }) {
    const [rating, setRating] = useState({
      user_rating: creative.latest_user_rating || "",
      fidelity_score: "",
      realism_score: "",
      hook_score: "",
      brand_fit_score: "",
      comment: ""
    });
    const [perf, setPerf] = useState({
      ctr: creative.latest_ctr ?? "",
      cpc: creative.latest_cpc ?? "",
      cpa: creative.latest_cpa ?? "",
      roas: creative.latest_roas ?? "",
      spend: creative.latest_spend ?? "",
      impressions: "",
      clicks: "",
      conversions: "",
      date_range: creative.latest_performance_date_range || ""
    });
    const [saving, setSaving] = useState("");
    const [localStatus, setLocalStatus] = useState("");
    const [localPerformanceCount, setLocalPerformanceCount] = useState(Number(creative.performance_count || 0));
    const [learningSignal, setLearningSignal] = useState(null);
    const [ratingOpen, setRatingOpen] = useState(false);
    const [performanceOpen, setPerformanceOpen] = useState(false);
    const [insightsOpen, setInsightsOpen] = useState(false);
    const preview = creative.asset_url;
    const displayStatus = localStatus || creative.latest_rating_status || creative.status || "neznámý";
    const displayedRating = creative.latest_user_rating || rating.user_rating;
    const performanceCount = localPerformanceCount || Number(creative.performance_count || 0);
    const displayCtr = creative.latest_ctr ?? perf.ctr ?? "-";
    const displayRoas = creative.latest_roas ?? perf.roas ?? "-";

    useEffect(() => {
      setLocalStatus("");
      setLocalPerformanceCount(Number(creative.performance_count || 0));
      setRating((current) => ({ ...current, user_rating: creative.latest_user_rating || current.user_rating || "" }));
      setPerf((current) => ({
        ...current,
        ctr: creative.latest_ctr ?? current.ctr,
        cpc: creative.latest_cpc ?? current.cpc,
        cpa: creative.latest_cpa ?? current.cpa,
        roas: creative.latest_roas ?? current.roas,
        spend: creative.latest_spend ?? current.spend,
        date_range: creative.latest_performance_date_range || current.date_range
      }));
    }, [creative.creative_id, creative.latest_rating_status, creative.latest_user_rating, creative.performance_count, creative.latest_ctr, creative.latest_cpc, creative.latest_cpa, creative.latest_roas, creative.latest_spend, creative.latest_performance_date_range]);

    async function handleRating(status) {
      setSaving(status);
      try {
        const payload = await saveRating({
          creative_id: creative.creative_id,
          status,
          ...rating,
          reasons: status === "rejected" ? [rating.comment || "rejected"] : []
        });
        setLearningSignal(payload.learning_signal || null);
        setLocalStatus(status);
      } finally {
        setSaving("");
      }
    }

    async function handlePerformance() {
      setSaving("performance");
      try {
        const payload = await savePerformance({ ...perf, creative_id: creative.creative_id, platform: creative.platform });
        setLearningSignal(payload.learning_signal || null);
        setLocalPerformanceCount((value) => value + 1);
      } finally {
        setSaving("");
      }
    }

    return h("article", { className: cls("creative-card", layout === "row" && "row-card") },
      renderCreativePreview({ ...creative, asset_url: preview }, layout === "row" ? openPreview : null),
      h("div", { className: "creative-body" },
        h("div", { className: "creative-title" },
          h("div", null,
            h("strong", null, creative.product_name || "Kreativa"),
            h("div", { className: "hint" }, creative.creative_id)
          ),
          h("span", { className: cls("pill", statusClass(displayStatus)) }, displayStatus)
        ),
        h("div", { className: "pill-row" },
          h("span", { className: "pill" }, creative.set_id || "set"),
          h("span", { className: "pill" }, moduleMeta(creativeModule(creative)).label),
          h("span", { className: "pill" }, creative.type || "type"),
          h("span", { className: "pill" }, creative.angle || "angle"),
          h("span", { className: "pill" }, `${creative.platform || "platform"} / ${creative.market || "market"}`),
          h("span", { className: "pill" }, `hodnocení ${displayedRating || "-"}/5`),
          h("span", { className: "pill" }, `${performanceCount} performance záznamů`)
        ),
        learningSignal && h("div", { className: cls("memory-signal", learningSignal.direction === "avoid" ? "avoid" : "learned") },
          h("b", null, learningSignal.direction === "avoid" ? "Naučeno: vyhnout se" : learningSignal.direction === "prefer" ? "Naučeno: preferovat" : "Naučeno: sledovat"),
          h("span", null, learningSignal.prompt_effect || "Signál byl uložen do Creative Intelligence."),
          h("small", null, [learningSignal.angle, learningSignal.category, learningSignal.market, learningSignal.platform].filter(Boolean).join(" / "))
        ),
        h("div", { className: "creative-compact-insights" },
          h("button", { type: "button", className: "ghost-toggle", onClick: () => setInsightsOpen(!insightsOpen), "aria-expanded": insightsOpen },
            insightsOpen ? "Sbalit strategii" : "Proč existuje + learning"
          ),
          insightsOpen && h("div", { className: "collapse-panel" },
            h("div", { className: "memory-signal" },
              h("b", null, "Memory signál"),
              h("span", null, `Stav hodnocení: ${displayStatus}. Performance: CTR ${displayCtr} / ROAS ${displayRoas}. Tyto hodnoty vstupují do Creative Intelligence a RAG guidance pro podobné produkty.`)
            ),
            h("div", { className: "why" }, h("b", null, "Proč tahle kreativa existuje"), h("br"), whyCreative(creative))
          )
        ),
        h("div", { className: "mini-form" },
          h("div", { className: "form-head" },
            h("div", null,
              h("strong", null, "Rychlé rozhodnutí"),
              h("span", null, "Komentář + schválit/zamítnout stačí pro learning. Skóre je volitelné.")
            ),
            h("button", { type: "button", className: "ghost-toggle", onClick: () => setRatingOpen(!ratingOpen), "aria-expanded": ratingOpen },
              ratingOpen ? "Sbalit skóre" : "Skóre 1-5"
            )
          ),
          field("Co zlepšit?", h("input", { value: rating.comment, onChange: (e) => setRating({ ...rating, comment: e.target.value }), placeholder: "produkt není přesný, moc AI vzhled, slabý hook..." })),
          ratingOpen && h("div", { className: "collapse-panel" },
            h("div", { className: "score-grid" },
              scoreInput("Celkově", rating.user_rating, (v) => setRating({ ...rating, user_rating: v })),
              scoreInput("Fidelity", rating.fidelity_score, (v) => setRating({ ...rating, fidelity_score: v })),
              scoreInput("Realismus", rating.realism_score, (v) => setRating({ ...rating, realism_score: v })),
              scoreInput("Hook", rating.hook_score, (v) => setRating({ ...rating, hook_score: v })),
              scoreInput("Brand fit", rating.brand_fit_score, (v) => setRating({ ...rating, brand_fit_score: v }))
            ),
            h("p", { className: "hint" }, "Prázdné hodnoty se neukládají jako falešný pozitivní signál. Vyplň jen to, co opravdu víš.")
          ),
          h("div", { className: "action-row" },
            h("button", { type: "button", disabled: !!saving, onClick: () => handleRating("approved") }, saving === "approved" ? "Ukládám..." : "Schválit"),
            h("button", { type: "button", disabled: !!saving, className: "danger", onClick: () => handleRating("rejected") }, saving === "rejected" ? "Ukládám..." : "Zamítnout")
          )
        ),
        h("div", { className: "mini-form" },
          h("div", { className: "form-head" },
            h("div", null,
              h("strong", null, "Ad performance"),
              h("span", null, performanceCount ? `Uloženo ${performanceCount} záznamů. CTR ${displayCtr || "-"} / ROAS ${displayRoas || "-"}.` : "Zbaleno. Vyplň až ve chvíli, kdy máš data z platformy.")
            ),
            h("button", { type: "button", className: "ghost-toggle", onClick: () => setPerformanceOpen(!performanceOpen), "aria-expanded": performanceOpen },
              performanceOpen ? "Sbalit performance" : "Zapsat performance"
            )
          ),
          performanceOpen && h("div", { className: "collapse-panel" },
            h("div", { className: "score-grid" },
              perfInput("CTR %", perf.ctr, (v) => setPerf({ ...perf, ctr: v })),
              perfInput("CPC", perf.cpc, (v) => setPerf({ ...perf, cpc: v })),
              perfInput("CPA", perf.cpa, (v) => setPerf({ ...perf, cpa: v })),
              perfInput("ROAS", perf.roas, (v) => setPerf({ ...perf, roas: v })),
              perfInput("Spend", perf.spend, (v) => setPerf({ ...perf, spend: v })),
              perfInput("Impr.", perf.impressions, (v) => setPerf({ ...perf, impressions: v })),
              perfInput("Clicks", perf.clicks, (v) => setPerf({ ...perf, clicks: v })),
              perfInput("Conv.", perf.conversions, (v) => setPerf({ ...perf, conversions: v }))
            ),
            field("Období", h("input", { value: perf.date_range, onChange: (e) => setPerf({ ...perf, date_range: e.target.value }), placeholder: "2026-05-01 až 2026-05-21" })),
            h("button", { type: "button", disabled: !!saving, className: "secondary", onClick: handlePerformance }, saving === "performance" ? "Ukládám..." : "Uložit performance")
          )
        )
      )
    );
  }

  function PromptLab({ latest, latestRun, settings, form, update, promptLearningGuidance, providerValidationPreview }) {
    const [tab, setTab] = useState("layers");
    const auditSource = latestRun?.run_id ? { ...(latest || {}), ...(latestRun || {}) } : (latest || {});
    const promptAudit = auditSource?.prompt_audit || {};
    const finalPrompt = auditSource?.seedance_payload?.prompt || auditSource?.content_prompt_package?.seedance_payload?.prompt || auditSource?.video_generation?.submitted_payload?.prompt || "";
    const imagePrompts = auditSource?.static_image_generation?.image_assets || [];
    const submittedVideoPayload = auditSource?.video_generation?.submitted_payload || auditSource?.seedance_payload || {};
    const imageGenerationPlan = auditSource?.static_image_generation?.generation_plan || auditSource?.creative_plan_preview?.items || [];
    const staticCreativeDirector = auditSource?.ads_creative_set?.static_creative_director || latest?.ads_creative_set?.static_creative_director || {};
    const ragGuidance = auditSource?.ugc_strategy?.creative_memory_rag || auditSource?.creative_memory?.rag_guidance || promptLearningGuidance?.rag_guidance || {};
    const promptGraph = auditSource?.prompt_audit?.prompt_graph || auditSource?.content_prompt_package?.prompt_graph || {};
    const sceneChainingAudit = promptAudit.scene_chaining || auditSource?.ugc_strategy?.scene_chaining || auditSource?.content_prompt_package?.scene_chaining || {};
    const angleMultiplier = auditSource?.ugc_strategy?.ad_angle_multiplier || auditSource?.ads_creative_set?.ad_angle_multiplier || {};
    const angleSelector = auditSource?.ugc_strategy?.ad_angle_selector || auditSource?.ads_creative_set?.ad_angle_selector || {};
    const competitorStrategy = auditSource?.ugc_strategy?.competitor_strategy || auditSource?.ads_creative_set?.competitor_strategy_applied || promptGraph?.competitor_strategy || {};
    const postGenerationQa = auditSource?.post_generation_qa || {};
    const sourceInventory = settings?.prompt_source_inventory || {};
    const promptModel = latest?.user_input?.prompt_model || form.prompt_model;
    const videoPromptStatus = finalPrompt.length > 0 ? `${finalPrompt.length} znaků` : "čeká";
    const imagePromptStatus = imagePrompts.length ? `${imagePrompts.length} promptů` : "čeká";
    return h("div", null,
      h(SectionHead, {
        title: "Prompt laboratoř",
        subtitle: "Prompt architektura od vstupních dat po finální payload: editovatelné vrstvy, RAG guidance, audit a přesné prompty poslané modelům."
      }),
      h("div", { className: "tabs" },
        promptTab("layers", "Editovatelné vrstvy", tab, setTab),
        promptTab("architecture", "Architektura", tab, setTab),
        promptTab("audit", "Audit", tab, setTab),
        promptTab("payloads", "Finální payloady", tab, setTab)
      ),
      h("div", { className: "prompt-meta-grid" },
        statusPanel("Aktuální run", latestRun?.run_id || "čeká", latestRun ? `${latestRun.status} / ${latestRun.current_stage} / ${latestRun.monitor?.progress_percent || 0}%` : "Po spuštění se napojí na generation_runs."),
        statusPanel("Prompt model", promptModel || "není nastaven", "Model použitý pro prompt refinement a plánování statických kreativ."),
        statusPanel("UGC prompt", promptAudit.ugc_prompt?.mode || promptAudit.ugc_prompt?.source || "fallback/neznámé", "Ukazuje, jestli UGC prompt prošel AI refinementem nebo fallbackem."),
        statusPanel("Static prompt", promptAudit.static_prompt?.mode || promptAudit.static_prompt?.source || "fallback/neznámé", "Ukazuje, jestli static prompty vznikly přes AI nebo deterministický fallback."),
        statusPanel("Angle multiplier", angleMultiplier.angle_count ? `${angleMultiplier.angle_count} angles` : "čeká", "Rozšiřuje jednu ideu do Pain/Desire/Proof/Identity/Contrarian/Urgency testů."),
        statusPanel("Angle selector", angleSelector.slot_selection ? `${Object.keys(angleSelector.slot_selection || {}).length} slotů` : "čeká", "Vybírá nejlepší angle pro C1-C5 podle role assetu a memory signálů."),
        statusPanel("Competitor chat", competitorStrategy.status || "vypnuto", competitorStrategy.adaptation_brief || "Dočasný strategický brief pro konkrétní ad set."),
        statusPanel("Post QA", postGenerationQa.status || "čeká", postGenerationQa.next_step || "Po generování zkontroluje assety, jazyk, CTA texty a kontinuitu scén."),
        statusPanel("Finální velikosti", `${videoPromptStatus} / ${imagePromptStatus}`, "Užitečné pro limity providerů a debugging.")
      ),
      tab === "layers" && h("div", { className: "prompt-grid" },
        promptEditor("Content system prompt", form.content_prompt_system, (v) => update("content_prompt_system", v)),
        promptEditor("Content task prompt", form.content_prompt_task, (v) => update("content_prompt_task", v)),
        promptEditor("Base video prompt šablona", form.base_video_prompt_template, (v) => update("base_video_prompt_template", v)),
        promptEditor("Extra režie UGC videa", form.ugc_video_extra_prompt || "", (v) => update("ugc_video_extra_prompt", v)),
        promptEditor("Negative prompt", form.negative_prompt, (v) => update("negative_prompt", v)),
        promptEditor("Kategoriový prompt: kabelky", form.category_prompt_handbag || "", (v) => update("category_prompt_handbag", v)),
        promptEditor("Kategoriový prompt: boty", form.category_prompt_shoes || "", (v) => update("category_prompt_shoes", v)),
        promptEditor("Kategoriový prompt: oblečení", form.category_prompt_apparel || "", (v) => update("category_prompt_apparel", v))
      ),
      tab === "architecture" && h("section", { className: "section" },
        h(SectionHead, { title: "Prompt flow", subtitle: "Jak má aplikace přemýšlet dřív, než model uvidí finální prompt." }),
        h(PromptGraphVisual, { promptGraph, ragGuidance, staticCreativeDirector, imageGenerationPlan, sceneChainingAudit, promptLearningGuidance }),
        h("div", { className: "prompt-flow compact-flow" },
          flowCard("1", "Produktová data", "Název, poznámky, obrázek produktu, odhad kategorie a bezpečné benefity."),
          flowCard("2", "Kategorie", "Prostředí, lidský kontext, měřítko produktu a creative angle."),
          flowCard("3", "Avatar", "Identity lock, hlas, persona a kontinuita scén."),
          flowCard("4", "Memory", "Schválení, zamítnutí a performance patterns jako guidance."),
          flowCard("5", "Safety", "Bez falešných CTA, recenzí, slev, medical claims a nepodloženého proof."),
          flowCard("6", "Compiler", "Strukturované bloky se zkrátí do provider promptů.")
        ),
        h("div", { className: "prompt-debug-details" },
          jsonDetails("Aktuální prompt graph", promptGraph),
          jsonDetails("Prompt Learning Agent", promptLearningGuidance),
          jsonDetails("Ad Angle Multiplier", angleMultiplier),
          jsonDetails("Ad Angle Selector", angleSelector),
          jsonDetails("Competitor Strategy Chat", competitorStrategy),
          jsonDetails("Aktuální RAG guidance", ragGuidance),
          jsonDetails("Kontinuita scén / Seedance chaining", sceneChainingAudit),
          jsonDetails("Static Creative Director V2", staticCreativeDirector),
          jsonDetails("Plán generování obrázků", imageGenerationPlan)
        )
      ),
      tab === "audit" && h("section", { className: "section" },
        h(SectionHead, { title: "Prompt audit", subtitle: "Prompt model, fallback/refined status, komprese a inventář zdrojů." }),
        h("div", { className: "diff-grid" },
          h(PromptDiffCard, {
            title: "UGC deterministic → AI refined",
            diff: promptAudit.ugc_prompt?.diff?.deterministic_to_ai_refined,
            emptyText: "UGC prompt se nezměnil nebo ještě není k dispozici."
          }),
          h(PromptDiffCard, {
            title: "UGC refined → final payload",
            diff: promptAudit.ugc_prompt?.diff?.ai_refined_to_final_payload,
            emptyText: "Finální video payload zatím není k dispozici."
          }),
          h(PromptDiffCard, {
            title: "Static deterministic → AI refined",
            diff: promptAudit.static_prompt?.diff?.deterministic_to_ai_refined,
            emptyText: "Static prompt se nezměnil nebo běží fallback."
          }),
          h(PromptDiffCard, {
            title: "Static refined → final image prompt",
            diff: promptAudit.static_prompt?.diff?.ai_refined_to_final_payload,
            emptyText: "Finální image prompty zatím nejsou k dispozici."
          })
        ),
        h("div", { className: "prompt-grid" },
          h("div", { className: "panel card" }, h("h4", null, "UGC Prompt"), h("pre", null, JSON.stringify(promptAudit.ugc_prompt || {}, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Static Prompt"), h("pre", null, JSON.stringify(promptAudit.static_prompt || {}, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Scene Chaining Audit"), h("pre", null, JSON.stringify(sceneChainingAudit || {}, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Post Generation QA"), h("pre", null, JSON.stringify(postGenerationQa || {}, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Run monitor"), h("pre", null, JSON.stringify(latestRun?.monitor || {}, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Kontrola providerů"), h("pre", null, JSON.stringify(auditSource?.provider_validation || providerValidationPreview || {}, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Inventář zdrojů promptů"), h("pre", null, JSON.stringify(sourceInventory, null, 2))),
          h("div", { className: "panel card" }, h("h4", null, "Komprese / guardrails"), h("pre", null, JSON.stringify(auditSource?.prompt_size_guard || auditSource?.provider_validation || auditSource?.preflight || {}, null, 2)))
        )
      ),
      tab === "payloads" && h("section", { className: "section" },
        h(SectionHead, { title: "Finální payloady", subtitle: "Toto aplikace skutečně připravila nebo poslala." }),
        h("div", { className: "payload-stack" },
          promptTextDetails("Finální video prompt", finalPrompt || "Video prompt zatím není k dispozici.", finalPrompt ? `${finalPrompt.length} znaků` : "čeká", true),
          promptTextDetails("Finální image prompty", imagePrompts.length ? imagePrompts.map((asset) => `${asset.creative_id || asset.set_id}\n${asset.prompt || asset.prompt_preview || ""}`).join("\n\n") : "Image prompty zatím nejsou k dispozici.", imagePrompts.length ? `${imagePrompts.length} promptů` : "čeká"),
          jsonDetails("Odeslaný video payload", submittedVideoPayload),
          jsonDetails("Výsledek statických obrázků", auditSource?.static_image_generation || {})
        )
      )
    );
  }

  function Analytics({ intelligence, learning, creatives }) {
    const counts = intelligence?.counts || {};
    const loop = intelligence?.learning_loop || {};
    const learner = intelligence?.prompt_learning_agent || {};
    const extractor = intelligence?.winning_pattern_extractor || {};
    const leaders = intelligence?.performance_leaders || [];
    const bestAngles = intelligence?.best_performing_angles || [];
    const marketInsights = intelligence?.market_specific_insights || [];
    const recent = intelligence?.recent_creatives || [];
    const recommendations = intelligence?.prompt_recommendations || [];
    const nextBias = learning?.next_generation_bias || learner.next_generation_bias || {};
    const winningPatterns = learning?.winning_patterns || extractor.performance_patterns || [];
    const avoidPatterns = learning?.avoid_patterns || extractor.rejected_patterns || [];
    const [tab, setTab] = useState("overview");
    return h("div", null,
      h(SectionHead, {
        title: "Analýza kreativ",
        subtitle: "Rozhodovací stránka pro iteraci kreativ: co funguje, čemu se vyhnout a jak má být další generace ovlivněná."
      }),
      h("div", { className: "stat-grid" },
        stat("Produkty", counts.products || 0, "uloženo"),
        stat("Kampaně", counts.campaigns || 0, "uloženo"),
        stat("Kreativy", counts.creatives || creatives.length || 0, "assety"),
        stat("Hodnocení", counts.ratings || 0, "feedback"),
        stat("Performance", counts.performance_records || 0, "záznamy")
      ),
      h("div", { className: "analytics-tabs tabs" },
        promptTab("overview", "Přehled", tab, setTab),
        promptTab("patterns", "Patterns", tab, setTab),
        promptTab("learning", "Agent učení", tab, setTab),
        promptTab("performance", "Performance", tab, setTab)
      ),
      tab === "overview" && h("div", { className: "analytics-tab-body" },
        h("section", { className: "section analytics-hero" },
          h("div", { className: "card insight-card" },
            h("div", { className: "eyebrow" }, "Další nejlepší krok"),
            h("h4", null, recommendations[0] || learner.recommendation || "Ohodnoť kreativy a vlož performance data, aby se učení zpřesnilo."),
            h("p", null, "Tohle je praktické rozhodnutí, pro které je stránka optimalizovaná. Model má používat winners jako bias, ne jako zdroj ke kopírování.")
          ),
          h("div", { className: "card insight-card" },
            h("div", { className: "eyebrow" }, "Připravenost učení"),
            h("h4", null, `${loop.status || "collecting"} / ${intelligence?.workspace || learning?.workspace || "all"}`),
            h("p", null, `Confidence: ${learner.confidence || "low"}. Hodnocení a performance záznamy zvyšují přesnost pro podobné produkty, trhy a platformy v aktuálním modulu.`)
          ),
          h("div", { className: "card insight-card" },
            h("div", { className: "eyebrow" }, "RAG bias pro další generaci"),
            h("h4", null, (nextBias.prefer || []).slice(0, 3).join(", ") || "Zatím nejsou silní winners"),
            h("p", null, (nextBias.avoid || []).length ? `Vyhnout se: ${(nextBias.avoid || []).slice(0, 3).join(", ")}` : "Zamítnuté patterns se tady objeví po zamítnutí nebo slabé performance.")
          )
        ),
        h("section", { className: "section" },
          h(SectionHead, { title: "Learning loop", subtitle: "Aplikace se učí jen ze signálů, které pomáhají kreativnímu rozhodnutí: schválení, zamítnutí a reálná performance reklam." }),
          h("div", { className: "learning-steps" },
            learningStep("Vygenerovat kreativu", "done"),
            learningStep("Uživatel hodnotí", counts.ratings ? "done" : "waiting"),
            learningStep("Performance vložena", counts.performance_records ? "done" : "waiting"),
            learningStep("RAG guidance aktualizována", counts.ratings || counts.performance_records ? "active" : "seed"),
            learningStep("Další prompt ovlivněn", learner.confidence || "low")
          )
        )
      ),
      tab === "patterns" && h("section", { className: "section analytics-split" },
        h("div", { className: "card" },
          h("h4", null, "Vítězné patterns"),
          h("p", null, "Schválené kreativy a performance winners. Tohle se stává pozitivním prompt bias."),
          chips(uniqueText([...winningPatterns, ...(extractor.approved_patterns || []), ...(intelligence?.best_hooks || [])]))
        ),
        h("div", { className: "card" },
          h("h4", null, "Patterns k vyhnutí"),
          h("p", null, "Zamítnuté komentáře a slabá performance. Tohle se stává negativní prompt guidance."),
          chips(uniqueText([...avoidPatterns, ...(intelligence?.rejected_patterns || [])]))
        ),
        h("div", { className: "card" },
          h("h4", null, "Nejlepší angles"),
          bestAngles.length
            ? h("div", { className: "mini-table" }, bestAngles.map((row) => h("div", { key: row.angle || row.count },
              h("b", null, row.angle || "angle"),
              h("span", null, `avg rating ${formatMetric(row.avg_rating)} / ${row.count} záznamů`)
            )))
            : h("p", null, "Schval kreativy nebo vlož performance, aby šlo seřadit angles.")
        ),
        h("div", { className: "card" },
          h("h4", null, "Tržní insighty"),
          marketInsights.length
            ? h("div", { className: "mini-table" }, marketInsights.map((row, index) => h("div", { key: index },
              h("b", null, `${row.market || "market"} / ${row.platform || "platform"}`),
              h("span", null, `${row.creative_count || 0} kreativ, avg rating ${formatMetric(row.avg_rating)}`)
            )))
            : h("p", null, "Market-level patterns se objeví po hodnoceních.")
        )
      ),
      tab === "learning" && h("section", { className: "section" },
          h(SectionHead, { title: "Agent učení promptů", subtitle: "Čitelné shrnutí toho, co ovlivní další generaci." }),
        h("div", { className: "card-grid" },
          h("div", { className: "card" }, h("h4", null, "Doporučení"), h("p", null, learning?.recommendation || learner.recommendation || "Sbírej hodnocení a performance pro lepší doporučení.")),
          h("div", { className: "card" }, h("h4", null, "Preferovat"), chips(nextBias.prefer || [])),
          h("div", { className: "card" }, h("h4", null, "Vyhnout se"), chips(nextBias.avoid || [])),
          h("div", { className: "card" }, h("h4", null, "Nedávné kreativy"), chips(recent.map((item) => `${item.set_id || "set"} ${item.angle || item.type || ""}`)))
        )
      ),
      tab === "performance" && h("section", { className: "section" },
        h(SectionHead, { title: "Výkonoví winners", subtitle: "Použij to pro rozhodnutí, co regenerovat, škálovat nebo zastavit." }),
        leaders.length ? h("table", { className: "table" },
          h("thead", null, h("tr", null, ["Kreativa", "Angle", "CTR", "CPC", "CPA", "ROAS", "Spend", "Rozhodnutí"].map((x) => h("th", { key: x }, x)))),
          h("tbody", null,
            leaders.map((row) =>
              h("tr", { key: row.creative_id },
                h("td", null, row.creative_id),
                h("td", null, row.angle),
                h("td", null, formatMetric(row.ctr)),
                h("td", null, formatMetric(row.cpc)),
                h("td", null, formatMetric(row.cpa)),
                h("td", null, formatMetric(row.roas)),
                h("td", null, formatMetric(row.spend)),
                h("td", null, performanceDecision(row))
              )
            )
          )
        ) : h("div", { className: "empty" }, "Zatím nejsou žádné performance záznamy. Ulož CTR/CPC/CPA/ROAS na kartách kreativ a odemkneš performance-led learning.")
      )
    );
  }

  function Settings({ form, update, settings, providerCapabilities, latestRun, providerValidationPreview }) {
    const limits = providerCapabilities?.limits || {};
    const imageCap = providerCapabilities?.image_models?.[form.image_model] || {};
    const videoCap = providerCapabilities?.video_models?.[form.seedance_model] || {};
    const [tab, setTab] = useState("models");
    return h("div", null,
      h(SectionHead, { title: "Nastavení", subtitle: "Srozumitelné ovládání bez JSON chaosu. Detailní prompty jsou v Prompt Labu." }),
      h("div", { className: "settings-tabs tabs" },
        promptTab("models", "AI modely", tab, setTab),
        promptTab("quality", "Kvalita", tab, setTab),
        promptTab("safety", "Safety", tab, setTab),
        promptTab("providers", "Provideři", tab, setTab),
        promptTab("run", "Poslední run", tab, setTab)
      ),
      h("div", { className: "settings-shell" },
        tab === "models" && h("div", { className: "card settings-card" },
          h("h4", null, "AI modely"),
          h("p", null, "Tady nastavuješ modely, které ovlivní prompt engineering, statické obrázky a Seedance video. Běžný creative workflow tyto hodnoty jen čte."),
          field("Prompt model", h("input", { value: form.prompt_model, onChange: (e) => update("prompt_model", e.target.value) })),
          field("Obrázkový model", h("input", { value: form.image_model, onChange: (e) => update("image_model", e.target.value) })),
          field("Video model", h("input", { value: form.seedance_model, onChange: (e) => update("seedance_model", e.target.value) }))
        ),
        tab === "quality" && h("div", { className: "card settings-card" },
          h("h4", null, "Kvalita"),
          h("p", null, "Kvalitativní guardrails: cap obrázků je horní limit, ne příkaz doplňovat duplicity. Finance režim statiky nepoužívá."),
          field("Max statických obrázků", h("input", { type: "number", value: form.max_static_images, onChange: (e) => update("max_static_images", e.target.value) })),
          field("Velikost obrázku", select(form.image_size, (v) => update("image_size", v), [["1K", "1K"], ["2K", "2K"], ["4K", "4K"]])),
          field("Konzistence scény", select(form.background_consistency, (v) => update("background_consistency", v), [["strict", "Strict"], ["balanced", "Balanced"], ["free", "Free"]])),
          checkbox("Povolit kreativní změnu prostředí", form.environment_override, (v) => update("environment_override", v)),
          h("p", null, "Realismus a strict product fidelity se hlídají v prompt defaults a vision QA.")
        ),
        tab === "safety" && h("div", { className: "card settings-card" },
          h("h4", null, "Safety"),
          h("p", null, "Bez in-creative CTA tlačítek, falešných slev, recenzí, medical claims, scarcity nebo vymyšleného social proof."),
          h("pre", null, settings?.negative_prompt || form.negative_prompt || "")
        ),
        tab === "providers" && h("div", { className: "card settings-card" },
          h("h4", null, "Možnosti providerů"),
          h("p", null, "Tohle je runtime registr modelů a limitů. Preflight podle něj blokuje nekompatibilní volby ještě před API callem."),
          h("div", { className: "mini-table" },
            h("div", null, h("b", null, "Limit promptu"), h("span", null, `${limits.max_prompt_chars || 18000} znaků`)),
            h("div", null, h("b", null, "Max statik"), h("span", null, `${limits.max_static_images || 10}`)),
            h("div", null, h("b", null, "Image model"), h("span", null, imageCap.supports_image_output ? "image output OK" : "neověřený / riziko")),
            h("div", null, h("b", null, "Video model"), h("span", null, videoCap.supports_videos_endpoint ? "/videos OK" : "neověřený / riziko")),
            h("div", null, h("b", null, "Avatar reference"), h("span", null, String(videoCap.supports_exact_avatar_reference || "provider_sensitive")))
          ),
          providerValidationPreview && h("pre", null, JSON.stringify(providerValidationPreview, null, 2))
        ),
        tab === "run" && h("div", { className: "card settings-card" },
          h("h4", null, "Poslední run"),
          latestRun
            ? h("div", { className: "mini-table" },
              h("div", null, h("b", null, "Run ID"), h("span", null, latestRun.run_id)),
              h("div", null, h("b", null, "Modul"), h("span", null, latestRun.workspace)),
              h("div", null, h("b", null, "Stav"), h("span", null, latestRun.status)),
              h("div", null, h("b", null, "Fáze"), h("span", null, latestRun.current_stage))
            )
            : h("p", null, "Zatím není uložený žádný běh pro aktuální modul.")
        )
      )
    );
  }

  function renderCreativePreview(asset, onOpen) {
    const rawUrl = asset?.image_url || asset?.asset_url || asset?.video_url || asset?.video_path || "";
    const src = normalizeAssetUrl(rawUrl);
    const isVideo = isVideoAsset(asset, src);
    const playable = isPlayableMediaUrl(src);
    const label = asset?.creative_id || asset?.set_id || asset?.type || "asset";
    const status = asset?.status || asset?.video_generation_status || "";
    const failure = asset?.failure_reason || asset?.error || "";
    const openProps = onOpen && playable ? {
      role: "button",
      tabIndex: 0,
      title: "Otevřít velký náhled",
      onClick: () => onOpen({ ...asset, asset_url: src }),
      onKeyDown: (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen({ ...asset, asset_url: src });
        }
      }
    } : {};
    if (isVideo && playable) {
      return h("div", { className: cls("creative-preview video-preview", onOpen && "clickable-preview"), ...openProps },
        h("video", { src, controls: true, preload: "metadata", playsInline: true }),
        h("div", { className: "media-caption" },
          h("span", null, status || "video"),
          h("a", { href: src, target: "_blank", rel: "noreferrer" }, "Otevřít video")
        )
      );
    }
    if (!isVideo && playable) {
      return h("div", { className: cls("creative-preview", onOpen && "clickable-preview"), ...openProps },
        h("img", { src, alt: label })
      );
    }
    return h("div", { className: cls("creative-preview", isVideo && "video-preview") },
      h("div", { className: "preview-placeholder" },
        h("strong", null, label),
        h("span", null, isVideo ? `Video ${status || "není dostupné"}` : "Bez náhledu"),
        failure && h("small", null, failure)
      )
    );
  }

  function PreviewModal({ asset, onClose }) {
    const src = normalizeAssetUrl(asset?.asset_url || asset?.image_url || asset?.video_url || asset?.video_path || "");
    const isVideo = isVideoAsset(asset, src);
    return h("div", { className: "preview-modal", role: "dialog", "aria-modal": "true", onClick: onClose },
      h("div", { className: "preview-modal-card", onClick: (event) => event.stopPropagation() },
        h("div", { className: "preview-modal-head" },
          h("div", null,
            h("div", { className: "eyebrow" }, asset?.set_id || asset?.type || "Náhled kreativy"),
            h("h3", null, asset?.creative_id || asset?.product_name || "Náhled")
          ),
          h("button", { type: "button", className: "secondary", onClick: onClose }, "Zavřít")
        ),
        h("div", { className: "preview-modal-media" },
          isVideo
            ? h("video", { src, controls: true, autoPlay: true, playsInline: true })
            : h("img", { src, alt: asset?.creative_id || "Náhled kreativy" })
        )
      )
    );
  }

  function CommandPalette({ items, onClose }) {
    const [query, setQuery] = useState("");
    const inputRef = useRef(null);
    useEffect(() => {
      const timer = window.setTimeout(() => inputRef.current?.focus(), 30);
      return () => window.clearTimeout(timer);
    }, []);
    const normalized = query.trim().toLowerCase();
    const visible = (items || [])
      .filter((item) => {
        if (!normalized) return true;
        const haystack = `${item.group} ${item.label} ${item.detail}`.toLowerCase();
        return haystack.includes(normalized);
      })
      .slice(0, 12);
    const grouped = visible.reduce((acc, item) => {
      const group = item.group || "Ostatní";
      acc[group] = acc[group] || [];
      acc[group].push(item);
      return acc;
    }, {});
    function run(item) {
      item.action?.();
      onClose();
    }
    return h("div", { className: "command-overlay", role: "dialog", "aria-modal": "true", onClick: onClose },
      h("div", { className: "command-card", onClick: (event) => event.stopPropagation() },
        h("div", { className: "command-search" },
          h("span", null, "Hledat"),
          h("input", {
            ref: inputRef,
            value: query,
            onChange: (event) => setQuery(event.target.value),
            onKeyDown: (event) => {
              if (event.key === "Enter" && visible[0]) run(visible[0]);
              if (event.key === "Escape") onClose();
            },
            placeholder: "Najít obrazovku, kreativu, avatara nebo akci..."
          }),
          h("kbd", null, "Esc")
        ),
        Object.keys(grouped).length
          ? h("div", { className: "command-results" },
            Object.entries(grouped).map(([group, groupItems]) =>
              h("section", { key: group },
                h("div", { className: "command-group" }, group),
                groupItems.map((item, index) =>
                  h("button", { key: `${group}-${item.label}-${index}`, type: "button", className: "command-item", onClick: () => run(item) },
                    h("span", null,
                      h("b", null, item.label),
                      h("small", null, item.detail)
                    ),
                    h("code", null, "Enter")
                  )
                )
              )
            )
          )
          : h("div", { className: "empty command-empty" }, "Nic jsem nenašel. Zkus produkt, set ID, avatara nebo název modulu.")
      )
    );
  }

  function promptTab(key, label, active, setActive) {
    return h("button", {
      type: "button",
      className: cls(active === key && "active", active !== key && "secondary"),
      "aria-pressed": active === key,
      onClick: () => setActive(key)
    }, label);
  }

  function statusPanel(title, value, body) {
    return h("div", { className: "status-panel" },
      h("span", null, title),
      h("b", null, value),
      h("small", null, body)
    );
  }

  function flowCard(number, title, body) {
    return h("div", { className: "flow-card" },
      h("code", null, number),
      h("h4", null, title),
      h("p", null, body)
    );
  }

  function PromptGraphVisual({ promptGraph, ragGuidance, staticCreativeDirector, imageGenerationPlan, sceneChainingAudit, promptLearningGuidance }) {
    const graphKeys = promptGraph && typeof promptGraph === "object" ? Object.keys(promptGraph).length : 0;
    const ragWins = (ragGuidance?.winning_patterns || promptLearningGuidance?.winning_patterns || []).length;
    const ragAvoid = (ragGuidance?.avoid_patterns || promptLearningGuidance?.avoid_patterns || []).length;
    const imageCount = Array.isArray(imageGenerationPlan) ? imageGenerationPlan.length : 0;
    const staticMode = staticCreativeDirector?.mode || staticCreativeDirector?.source || "čeká";
    const chainingStatus = sceneChainingAudit?.status || sceneChainingAudit?.mode || "čeká";
    const nodes = [
      ["Brief", `${graphKeys || "live"} vrstev`, "Produkt, trh, jazyk, poznámky a reference."],
      ["Audience", promptLearningGuidance?.query?.market || "market", "Kategorie, positioning a očekávaný kontext použití."],
      ["Avatar", chainingStatus, "Identity lock, voice profile a scéna bez driftu."],
      ["Memory", `${ragWins} prefer / ${ragAvoid} avoid`, "RAG guidance z ratingů a performance."],
      ["Creative", staticMode, "Video, static plan, image diversity a cap bez duplicity."],
      ["Compiler", `${imageCount} image plánů`, "Finální Seedance a image payloady pro provider."]
    ];
    return h("div", { className: "prompt-graph-visual" },
      h("div", { className: "prompt-graph-main" },
        nodes.map(([title, meta, body], index) =>
          h("div", { className: "prompt-graph-node", key: title },
            h("span", null, String(index + 1).padStart(2, "0")),
            h("b", null, title),
            h("code", null, meta),
            h("p", null, body)
          )
        )
      ),
      h("div", { className: "prompt-graph-output" },
        h("div", { className: "eyebrow" }, "Compiled output"),
        h("h4", null, "Provider prompty bez chaosu"),
        h("p", null, "Debug JSON je pořád dostupný níže, ale hlavní obrazovka ukazuje vztah vrstev a to, proč prompt vzniká právě takhle."),
        h("div", { className: "pill-row" },
          h("span", { className: "pill pass" }, "product rules"),
          h("span", { className: "pill pass" }, "avatar rules"),
          h("span", { className: "pill warn" }, "memory guidance"),
          h("span", { className: "pill" }, "provider payload")
        )
      )
    );
  }

  function jsonDetails(title, value) {
    return h("details", { className: "json-details" },
      h("summary", null,
        h("span", null, title),
        h("small", null, value && typeof value === "object" ? `${Array.isArray(value) ? value.length : Object.keys(value).length} položek` : "bez dat")
      ),
      h("pre", null, JSON.stringify(value || {}, null, 2))
    );
  }

  function promptTextDetails(title, value, meta, open = false) {
    return h("details", { className: "json-details prompt-text-details", open },
      h("summary", null,
        h("span", null, title),
        h("small", null, meta || "text")
      ),
      h("pre", null, value || "")
    );
  }

  function learningStep(label, state) {
    return h("div", { className: cls("learning-step", state === "done" && "done", state === "active" && "active") },
      h("span", null, label),
      h("b", null, stateLabel(state))
    );
  }

  function avatarGuidanceItem(title, body) {
    return h("div", { className: "avatar-guide-item" },
      h("b", null, title),
      h("span", null, body)
    );
  }

  function avatarFilterLabel(filter) {
    const labels = {
      all: "Vše",
      active: "Aktivní",
      default: "Výchozí",
      used: "Použité",
      top: "Top výkon"
    };
    return labels[filter] || filter;
  }

  function stateLabel(state) {
    const labels = {
      done: "hotovo",
      waiting: "čeká",
      active: "aktivní",
      seed: "seed",
      low: "nízká",
      medium: "střední",
      high: "vysoká",
      collecting: "sbírá data",
      ready: "připraveno"
    };
    return labels[state] || state;
  }

  function uniqueText(items) {
    return [...new Set((items || []).filter(Boolean).map((item) => String(item)))];
  }

  function formatMetric(value) {
    if (value === null || value === undefined || value === "") return "-";
    const number = Number(value);
    if (!Number.isFinite(number)) return String(value);
    return number % 1 === 0 ? String(number) : number.toFixed(2);
  }

  function performanceDecision(row) {
    const roas = Number(row.roas || 0);
    const ctr = Number(row.ctr || 0);
    if (roas >= 2 || ctr >= 1.5) return "Škálovat / vytvořit varianty";
    if (roas > 0 && roas < 1) return "Zastavit nebo přepracovat";
    return "Sledovat";
  }

  function isVideoAsset(asset, src) {
    const type = String(asset?.type || asset?.asset_type || "").toLowerCase();
    const id = String(asset?.set_id || asset?.creative_id || "").toLowerCase();
    const url = String(src || "").toLowerCase().split("?")[0];
    return type.includes("video") || id === "c1" || url.endsWith(".mp4") || url.endsWith(".webm") || url.endsWith(".mov");
  }

  function isPlayableMediaUrl(value) {
    const raw = String(value || "").trim();
    return /^https?:\/\//i.test(raw) || raw.startsWith("/output/") || raw.startsWith("data:");
  }

  function normalizeAssetUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    if (/^https?:\/\//i.test(raw) || raw.startsWith("/output/") || raw.startsWith("data:")) return raw;
    const normalized = raw.replace(/\\/g, "/");
    const marker = "/output/";
    const index = normalized.toLowerCase().indexOf(marker);
    if (index >= 0) return normalized.slice(index);
    return raw;
  }

  function isPublicHttpUrl(value) {
    return /^https?:\/\//i.test(String(value || ""));
  }

  function avatarPreviewUrl(avatar = {}) {
    return normalizeAssetUrl(avatar.preview_url || avatar.image_url || "");
  }

  function avatarReferenceUrl(avatar = {}) {
    const url = String(avatar.image_url || "").trim();
    return isPublicHttpUrl(url) ? url : "";
  }

  function clientSlug(value) {
    const slug = String(value || "avatar")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
    return slug || `avatar_${Date.now()}`;
  }

  function moduleMeta(mode) {
    const finance = mode === "finance_personal_brand";
    if (finance) {
      return {
        id: "finance_personal_brand",
        icon: "F",
        label: "Finance brand",
        short: "Osobní brand video",
        note: "Jen video, čeština, podcast studio, compliance a schválení scény před Seedance.",
        dashboardTitle: "Finance brand má vlastní workflow, ne produktový ads set.",
        dashboardCopy: "Tady se řeší scénář, avatar osobního brandu, moderní infografika a schválení scény před generováním videa pro Meta/Instagram.",
        studioTitle: "Vytvořit finance osobní brand video",
        studioCopy: "Nezadáváš produkt. Nejdřív vložíš téma a obsah, agent připraví český scénář, navrhne podcastovou scénu a video spustí až po schválení.",
        laneTitle: "Finance personal brand",
        laneCopy: "Scénář, scene concept, approved video, performance learning."
      };
    }
    return {
      id: "ecommerce",
      icon: "E",
      label: "E-commerce",
      short: "Produktové ads sety",
      note: "UGC video, statiky, carousel, produktová fidelity a creative memory pro e-shop.",
      dashboardTitle: "E-commerce creative OS pro produktové reklamy.",
      dashboardCopy: "Produkt, avatar, trh a strategie vedou k UGC videu, static ads, carouselu, ratingu a performance learningu.",
      studioTitle: "Vytvořit produktový ads set",
      studioCopy: "Vyplň produkt, referenci a poznámky. Appka z toho sestaví UGC video, statiky a carousel podle kategorie, trhu a aktivního avatara.",
      laneTitle: "Produktové kampaně",
      laneCopy: "UGC video, statiky, carousel, product fidelity, ecommerce RAG."
    };
  }

  function moduleBadge(mode) {
    const meta = moduleMeta(mode);
    return h("span", { className: cls("module-badge", meta.id === "finance_personal_brand" && "finance") },
      h("code", null, meta.icon),
      meta.label
    );
  }

  function buildWorkspacePulse({ view, form, status, latestRun, latest, moduleCreatives, filteredCreatives, shellCost, activeShellAvatar, setView, update, setFilters, activeCreativeMode, setCommandOpen }) {
    const meta = moduleMeta(form.app_mode);
    const reviewCount = moduleCreatives.filter((item) => !item.latest_rating_status && !["approved", "rejected"].includes(String(item.status || "").toLowerCase())).length;
    const missingPerformance = moduleCreatives.filter((item) => Number(item.performance_count || 0) === 0).length;
    const failedCount = moduleCreatives.filter((item) => ["failed", "blocked"].includes(String(item.status || item.latest_rating_status || "").toLowerCase())).length;
    const activeRunLabel = latestRun?.status ? `${latestRun.status} / ${runStageLabel(latestRun.current_stage)}` : "bez běhu";
    const latestName = latest?.product_analysis?.product_name || latest?.user_input?.product_name || (financeModeEnabled(form) ? form.finance_video_topic : form.product_name) || "bez aktivního briefu";
    const primaryByView = {
      dashboard: {
        label: financeModeEnabled(form) ? "Nové finance video" : "Nový creative set",
        action: () => setView("studio")
      },
      studio: {
        label: "Prompt audit",
        action: () => setView("prompt-lab")
      },
      avatars: {
        label: "Použít ve studiu",
        action: () => setView("studio")
      },
      library: {
        label: reviewCount ? "Filtrovat ke schválení" : "Nová varianta",
        action: () => {
          if (reviewCount) {
            setFilters((current) => ({ ...current, mode: activeCreativeMode, status: "unrated", performance: "all" }));
          } else {
            setView("studio");
          }
        }
      },
      "prompt-lab": {
        label: "Otevřít studio",
        action: () => setView("studio")
      },
      analytics: {
        label: missingPerformance ? "Doplnit performance" : "Creative sety",
        action: () => {
          setFilters((current) => ({ ...current, mode: activeCreativeMode, performance: missingPerformance ? "missing" : "all", status: "all" }));
          setView("library");
        }
      },
      settings: {
        label: "Testovat ve studiu",
        action: () => setView("studio")
      }
    };
    const pageTitles = {
      dashboard: "Přehled výkonu a dalších kroků",
      studio: financeModeEnabled(form) ? "Sestav finance video bez zbytečných polí" : "Sestav creative set krok za krokem",
      avatars: "Spravuj avatary a jejich performance signály",
      library: "Review cockpit pro creative sety",
      "prompt-lab": "Audit promptů a provider payloadů",
      analytics: "Learning loop, winners a avoid patterns",
      settings: "Modely, limity a bezpečnost workflow"
    };
    const attention = failedCount
      ? `${failedCount} chyb/blokací`
      : reviewCount
      ? `${reviewCount} ke kontrole`
      : missingPerformance
      ? `${missingPerformance} bez performance`
      : "připraveno";
    return {
      mode: form.app_mode,
      icon: meta.icon,
      viewLabel: titleForView(view),
      title: pageTitles[view] || titleForView(view),
      body: `${meta.short}: ${latestName}. Stav workspace: ${attention}.`,
      primary: primaryByView[view] || primaryByView.dashboard,
      secondary: {
        label: "Command menu",
        action: () => setCommandOpen(true)
      },
      meta: [
        { label: "Avatar", value: activeShellAvatar?.name || form.custom_avatar_name || form.avatar_id || "nevybrán" },
        { label: "Run", value: activeRunLabel },
        { label: "Cena", value: shellCost },
        { label: "Pozornost", value: attention },
        { label: "Zobrazeno", value: `${filteredCreatives.length}/${moduleCreatives.length} assetů` }
      ],
      status
    };
  }

  function creativeModule(creative = {}) {
    const raw = [
      creative.app_mode,
      creative.category,
      creative.product_category,
      creative.session_type,
      creative.session_folder,
      creative.creative_id,
      creative.type,
      creative.product_name
    ].join(" ").toLowerCase();
    if (raw.includes("finance") || raw.includes("fin_video") || raw.includes("podcast studio")) return "finance_personal_brand";
    return "ecommerce";
  }

  function titleForView(view) {
    return {
      dashboard: "Přehled",
      studio: "Nová kampaň",
      avatars: "Avatar set",
      library: "Creative sety",
      "prompt-lab": "Prompt laboratoř",
      analytics: "Analýza",
      settings: "Nastavení"
    }[view] || "Creative OS";
  }

  function financeModeEnabled(form) {
    return form.app_mode === "finance_personal_brand";
  }

  function financeModeForm(form) {
    const topic = form.finance_video_topic || "Finanční osobní brand video";
    const script = form.finance_video_script || "";
    return {
      ...form,
      app_mode: "finance_personal_brand",
      product_name: topic,
      product_info: script,
      product_category: "finance",
      language: "cs",
      market: form.market || "CZ",
      platform: ["meta", "instagram"].includes(form.platform) ? form.platform : "meta",
      generation_mode: "video",
      video_length: "15",
      finance_allow_series: form.finance_allow_series !== false,
      finance_series_confirmed: Boolean(form.finance_series_confirmed),
      finance_generate_sample_first: form.finance_generate_sample_first !== false,
      finance_scene_approved: Boolean(form.finance_scene_approved),
      finance_scene_reference_url: form.finance_scene_reference_url || "",
      finance_scene_video_reference_url: form.finance_scene_video_reference_url || "",
      finance_scene_prompt: form.finance_scene_prompt || "",
      finance_scene_concept_json: form.finance_scene_concept_json || "",
      max_static_images: "0"
    };
  }

  function creativePlanRows(form = {}) {
    if (financeModeEnabled(form)) {
      return [
        {
          set_id: "C1",
          creative_type: "Finance podcast studio video",
          angle: "EDUCATION",
          aspect_ratio: "9:16",
          funnel_stage: "TOFU + retargeting",
          budget_share_percent: 100,
          media: "video",
          reason: "česká osobní brand reklama z podcastového studia s interaktivní infografikou"
        }
      ];
    }
    return [
      { set_id: "C1", creative_type: "UGC video", angle: "UGC", aspect_ratio: "9:16", funnel_stage: "TOFU + retargeting", budget_share_percent: 55, media: "video", reason: "creator-led anchor s avatarem" },
      { set_id: "C2", creative_type: "Static product hero", angle: "PRODUCT_HERO", aspect_ratio: "1:1", funnel_stage: "TOFU + retargeting", budget_share_percent: 10, media: "image", image_cost: 1, reason: "product-first hero frame" },
      { set_id: "C3", creative_type: "Static use context", angle: "USE_CONTEXT", aspect_ratio: "1:1", funnel_stage: "TOFU + retargeting", budget_share_percent: 10, media: "image", image_cost: 1, reason: "real-use context se scale/context cue" },
      { set_id: "C4", creative_type: "Static proof detail", angle: "DETAIL_PROOF", aspect_ratio: "1:1", funnel_stage: "Retargeting", budget_share_percent: 10, media: "image", image_cost: 1, reason: "detail proof pro produktove teple publikum" },
      { set_id: "C5", creative_type: "Carousel buying guide", angle: "BUYING_GUIDE", aspect_ratio: "1:1", funnel_stage: "MOFU", budget_share_percent: 15, media: "image", image_cost: 5, reason: "petikartovy buying guide" }
    ];
  }

  function planDecisionForForm(form, row) {
    const mode = form.generation_mode || "both";
    const maxImages = Math.max(0, Number(form.max_static_images || 0));
    if (row.media === "video") {
      if (mode === "static") return { status: "SKIPPED", reason: "generation mode=static" };
      return { status: form.product_name ? "YES" : "PLANNED", reason: form.product_name ? "vybráno pro UGC video" : "čeká na produkt" };
    }
    if (mode === "video") return { status: "SKIPPED", reason: "generation mode=video" };
    const previousCost = creativePlanRows(form)
      .filter((item) => item.media !== "video")
      .slice(0, Math.max(0, Number(row.set_id.slice(1)) - 2))
      .reduce((sum, item) => sum + (item.image_cost || 1), 0);
    const remaining = maxImages - previousCost;
    if (remaining <= 0) return { status: "SKIPPED", reason: "max_static_images cap" };
    if (remaining < (row.image_cost || 1)) return { status: "PARTIAL", reason: `${remaining}/${row.image_cost} karet kvůli capu` };
    return { status: form.product_name ? "YES" : "PLANNED", reason: row.reason };
  }

  function statusClass(status) {
    const value = String(status || "").toLowerCase();
    if (value === "yes" || value === "completed" || value === "done" || value === "approved") return "pass";
    if (value === "blocked" || value === "failed" || value === "rejected") return "fail";
    if (value === "skipped" || value === "partial" || value === "planned") return "warn";
    return "";
  }

  function isActiveRunStatus(status) {
    return ["queued", "validating", "planning", "prompting", "creative_plan", "generating_video", "generating_images", "qa", "saving", "running"].includes(String(status || "").toLowerCase());
  }

  function runTerminalStatus(run) {
    const status = String(run?.status || "").toLowerCase();
    if (status === "completed") return "Generování dokončeno";
    if (status === "cancelled") return "Generování zastaveno";
    if (status === "needs_scene_approval") return "Čeká na schválení scény";
    if (status === "needs_confirmation") return "Čeká na potvrzení série";
    if (status === "blocked") return "Generování blokováno";
    return "Generování skončilo";
  }

  function runTerminalToast(run) {
    const status = String(run?.status || "").toLowerCase();
    const latestStage = Array.isArray(run?.stage_results) ? run.stage_results[run.stage_results.length - 1] : null;
    const reason = latestStage?.data?.reason || run?.error || "";
    if (status === "completed") return "Creative set je hotový a uložený. Přepínám na přehled kreativ.";
    if (status === "cancelled") return "Run byl zastaven. Další provider call už se nespustil.";
    if (status === "needs_scene_approval") return "Finance video čeká na schválený návrh scény.";
    if (status === "needs_confirmation") return "Finance scénář je delší. Potvrď sérii a spusť první ukázkové video.";
    if (status === "blocked") return ["Run je blokovaný.", reason].filter(Boolean).join(" ");
    return reason || "Run doběhl.";
  }

  function runStageLabel(stage) {
    const labels = {
      queued: "Zařazeno",
      validating: "Validace vstupů",
      planning: "Plánování",
      prompting: "Tvorba promptů",
      creative_plan: "Creative plán",
      generating_video: "Generování videa",
      generating_images: "Generování obrázků",
      qa: "QA kontrola",
      saving: "Ukládání",
      completed: "Dokončeno",
      failed: "Chyba",
      blocked: "Blokováno",
      cancelled: "Zastaveno",
      needs_confirmation: "Čeká na potvrzení série",
      needs_scene_approval: "Čeká na schválení scény",
      cancel_requested: "Zrušení vyžádáno"
    };
    return labels[String(stage || "").toLowerCase()] || text(stage, "Fáze");
  }

  function runStageMessage(stage) {
    const data = stage?.data || {};
    return data.message || data.reason || data.next_step || data.error || "";
  }

  function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleTimeString("cs-CZ", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function snapshotItem(label, value) {
    return h("div", { className: "snapshot-item" },
      h("span", null, label),
      h("b", null, text(value, "n/a"))
    );
  }

  function metricCard(label, value, meta, tone) {
    return h("div", { className: cls("metric-card", tone) },
      h("span", null, label),
      h("b", null, text(value)),
      h("small", null, meta)
    );
  }

  function summaryPill(label, value) {
    return h("div", { className: "summary-pill", key: label },
      h("span", null, label),
      h("b", null, limit(value, 34))
    );
  }

  function workflowItem(number, title, body, onClick) {
    return h("button", { type: "button", className: "workflow-action", onClick },
      h("span", null, number),
      h("b", null, title),
      h("small", null, body)
    );
  }

  function campaignRailItem(number, title, state, meta, onClick) {
    return h("button", { type: "button", className: cls("rail-item", state), key: title, onClick, "aria-current": state === "active" ? "step" : undefined },
      h("span", null, number),
      h("div", null,
        h("b", null, title),
        h("small", null, meta)
      )
    );
  }

  function groupCreativesByCampaign(creatives) {
    const groups = new Map();
    (creatives || []).forEach((creative) => {
      const id = creative.campaign_id || `${creative.product_id || creative.product_name || "campaign"}-${creative.created_at || "unknown"}`;
      if (!groups.has(id)) {
        groups.set(id, {
          id,
          session: creative.session_folder || "",
          product: creative.product_name || "Kampaň",
          module: creativeModule(creative),
          platform: creative.platform || "platforma",
          market: creative.market || "trh",
          category: creative.category || "kategorie",
          created_at: creative.created_at || "",
          items: []
        });
      }
      groups.get(id).items.push(creative);
    });
    return [...groups.values()]
      .map((group) => {
        const items = group.items.sort((a, b) => creativeSortKey(a) - creativeSortKey(b));
        const costValue = items.reduce((sum, item) => sum + (Number(item.generation_cost) || 0), 0);
        return {
          ...group,
          items,
          approved: items.filter((item) => item.latest_rating_status === "approved").length,
          rejected: items.filter((item) => item.latest_rating_status === "rejected").length,
          unrated: items.filter((item) => !item.latest_rating_status).length,
          failed: items.filter((item) => ["failed", "blocked"].includes(String(item.status || "").toLowerCase())).length,
          missingPerformance: items.filter((item) => Number(item.performance_count || 0) === 0).length,
          videos: items.filter((item) => item.type === "video" || item.set_id === "C1").length,
          statics: items.filter((item) => !(item.type === "video" || item.set_id === "C1")).length,
          performance: items.reduce((sum, item) => sum + (Number(item.performance_count) || 0), 0),
          cost: costValue ? `$${costValue.toFixed(4)}` : "n/a"
        };
      })
      .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  }

  function creativeSortKey(creative) {
    const setOrder = { C1: 10, C2: 20, C3: 30, C4: 40, C5: 50 };
    const set = creative.set_id || "";
    const cardMatch = String(creative.creative_id || "").match(/card_(\d+)/i);
    return (setOrder[set] || 90) + (cardMatch ? Number(cardMatch[1]) / 10 : 0);
  }

  function campaignMetric(label, value) {
    return h("div", { className: "campaign-metric", key: label },
      h("span", null, label),
      h("b", null, value)
    );
  }

  function libraryScore(label, value, meta) {
    return h("div", { className: "library-score", key: label },
      h("span", null, label),
      h("b", null, value),
      h("small", null, meta)
    );
  }

  function campaignNextAction(group) {
    if (group.failed) return "Vyřešit chybové nebo blokované assety";
    if (group.unrated) return `Ohodnotit ${group.unrated} assetů`;
    if (group.missingPerformance) return `Doplnit performance u ${group.missingPerformance} assetů`;
    if (group.approved) return "Vybrat winner a vytvořit variantu";
    return "Připravit první rozhodnutí";
  }

  function campaignCoverage(group) {
    const review = group.unrated ? `${group.unrated} bez hodnocení` : "rating hotový";
    const performance = group.missingPerformance ? `${group.missingPerformance} bez performance` : "performance pokryta";
    const media = `${group.videos || 0} video / ${group.statics || 0} statiky`;
    return `${media} / ${review} / ${performance}`;
  }

  function readinessItem(label, value, ready) {
    return h("div", { className: cls("readiness-item", ready ? "ready" : "missing"), key: label },
      h("span", null, label),
      h("b", null, value)
    );
  }

  function generationPhaseForRun(run, progress, financeMode = false) {
    const stage = String(run?.current_stage || run?.status || "").toLowerCase();
    const labels = {
      queued: "fronta",
      validating: "validace vstupů",
      planning: "creative plán",
      prompting: "prompt engineering",
      creative_plan: "creative plán",
      generating_images: "obrázky",
      generating_video: "video",
      qa: "QA",
      saving: "ukládání do memory",
      completed: "hotovo",
      blocked: "blokováno",
      failed: "chyba",
      cancelled: "zastaveno",
      needs_confirmation: "čeká na potvrzení",
      needs_scene_approval: "čeká na scénu"
    };
    return labels[stage] || generationPhase(progress, financeMode);
  }

  function generationPhase(progress, financeMode = false) {
    if (financeMode) {
      const financePhases = [
        [12, "příprava scénáře"],
        [24, "kontrola délky"],
        [40, "návrh scény"],
        [52, "schválený podklad"],
        [55, "prompt engineering"],
        [70, "compliance guard"],
        [88, "Seedance video"],
        [101, "export ukázky"]
      ];
      return financePhases.find(([limit]) => progress < limit)?.[1] || "finální export";
    }
    const phases = [
      [12, "validace vstupů"],
      [24, "analýza produktu"],
      [36, "audience a angle"],
      [48, "UGC strategie"],
      [62, "prompt engineering"],
      [76, "obrázky"],
      [90, "video"],
      [101, "ukládání do memory"]
    ];
    return phases.find(([limit]) => progress < limit)?.[1] || "finální export";
  }

  function pipelineStepState(progress, index, busy, stepCount = pipelineSteps.length) {
    if (!busy) return "waiting";
    const stepSize = 100 / Math.max(1, stepCount);
    const activeIndex = Math.min(stepCount - 1, Math.floor(progress / stepSize));
    if (index < activeIndex) return "done";
    if (index === activeIndex) return "active";
    return "waiting";
  }

  function pipelineTimelineItem(label, number, state) {
    const stateLabel = state === "done" ? "hotovo" : state === "active" ? "běží" : "čeká";
    return h("div", { className: cls("timeline-item", state), key: label },
      h("span", null, number),
      h("div", null,
        h("b", null, label),
        h("small", null, stateLabel)
      )
    );
  }

  function generationPlanCard(item) {
    return h("article", { className: cls("generation-plan-card", statusClass(item.status)), key: item.set_id },
      h("div", { className: "plan-card-top" },
        h("div", { className: "plan-id" }, item.set_id),
        h("span", { className: cls("pill", statusClass(item.status)) }, item.status)
      ),
      h("h4", null, item.creative_type),
      h("p", null, item.reason),
      h("div", { className: "plan-card-meta" },
        h("span", null, item.media === "video" ? "video" : `${item.image_cost || 1} image`),
        h("span", null, item.angle),
        h("span", null, item.funnel_stage),
        h("span", null, `${item.budget_share_percent}%`)
      )
    );
  }

  function SectionHead({ title, subtitle }) {
    return h("div", { className: "section-head" }, h("div", null, h("h3", null, title), subtitle && h("p", null, subtitle)));
  }

  function stat(value, label, meta) {
    return h("div", { className: "stat" }, h("b", null, value), h("span", null, `${label} ${meta ? ` / ${meta}` : ""}`));
  }

  function avatarMetric(label, value, meta) {
    return h("div", { className: "stat" }, h("b", null, value), h("span", null, `${label}${meta ? ` / ${meta}` : ""}`));
  }

  function card(title, body) {
    return h("div", { className: "card" }, h("h4", null, title), h("p", null, body));
  }

  function field(labelText, input) {
    const id = `field_${String(labelText).toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
    const canAttachLabel = React.isValidElement(input) && ["input", "textarea", "select"].includes(input.type);
    const control = canAttachLabel && !input.props?.id
      ? React.cloneElement(input, { id })
      : input;
    return h("div", { className: "field", key: labelText },
      h("label", canAttachLabel ? { htmlFor: input.props?.id || id } : null, labelText),
      control
    );
  }

  function select(value, onChange, options) {
    return h("select", { value, onChange: (e) => onChange(e.target.value) },
      options.map(([key, label]) => h("option", { key, value: key }, label))
    );
  }

  function segmented(value, onChange, options) {
    return h("div", { className: "segmented-control", role: "group" },
      options.map(([key, label]) =>
        h("button", {
          key,
          type: "button",
          className: cls(value === key && "active"),
          "aria-pressed": value === key,
          onClick: () => onChange(key)
        }, label)
      )
    );
  }

  function filterSelect(value, onChange, options) {
    return h("select", { value, onChange: (e) => onChange(e.target.value) },
      options.map((option) => {
        const key = Array.isArray(option) ? option[0] : option;
        const label = Array.isArray(option) ? option[1] : optionLabel(option);
        return h("option", { key, value: key }, label);
      })
    );
  }

  function savedViewButton(label, view, applySavedView) {
    return h("button", { type: "button", className: "secondary small", onClick: () => applySavedView(view) }, label);
  }

  function optionLabel(option) {
    const labels = {
      all: "Vše",
      ecommerce: "E-commerce",
      finance_personal_brand: "Finance brand",
      video: "Video",
      static: "Static",
      static_image: "Statický obrázek",
      carousel_card: "Carousel karta",
      generated: "Vygenerováno",
      completed: "Dokončeno",
      failed: "Chyba",
      blocked: "Blokováno",
      skipped: "Přeskočeno",
      planned: "Naplánováno",
      approved: "Schváleno",
      rejected: "Zamítnuto",
      saved: "Uloženo",
      unrated: "Bez hodnocení",
      missing: "Bez performance",
      has: "Má performance"
    };
    return labels[option] || option;
  }

  function checkbox(labelText, checked, onChange) {
    return h("label", { className: "checkbox-row", key: labelText },
      h("input", { type: "checkbox", checked, onChange: (e) => onChange(e.target.checked) }),
      labelText
    );
  }

  function authorizedAvatarConsent(checked, onChange) {
    return h("label", { className: "checkbox-row consent-row", key: "authorized-avatar-consent" },
      h("input", { type: "checkbox", checked, onChange: (e) => onChange(e.target.checked) }),
      h("span", null,
        h("b", null, "Autorizovaný AI avatar"),
        h("small", null, AUTHORIZED_AVATAR_CONSENT_TEXT),
        h("em", null, AUTHORIZED_AVATAR_CONSENT_HELP)
      )
    );
  }

  function wizardStep(number, title, children) {
    return h("div", { className: "wizard-step", key: title },
      h("div", { className: "eyebrow" }, `Krok ${number}`),
      h("h4", null, title),
      children
    );
  }

  function promptEditor(title, value, onChange) {
    return h("div", { className: "panel card" },
      h("h4", null, title),
      h("textarea", { value, onChange: (e) => onChange(e.target.value), style: { minHeight: "220px" } })
    );
  }

  function scoreInput(labelText, value, onChange) {
    return field(labelText, h("input", {
      type: "number",
      min: "1",
      max: "5",
      value,
      placeholder: "1-5",
      onChange: (e) => onChange(e.target.value === "" ? "" : Number(e.target.value))
    }));
  }

  function perfInput(labelText, value, onChange) {
    return field(labelText, h("input", { type: "number", step: "0.01", value, onChange: (e) => onChange(e.target.value) }));
  }

  function chips(items) {
    if (!items.length) return h("p", null, "Zatím nejsou data.");
    return h("div", { className: "pill-row" }, items.slice(0, 12).map((item) => h("span", { className: "pill", key: item }, item)));
  }

  function statusClass(status) {
    if (["completed", "generated", "approved", "saved"].includes(status)) return "pass";
    if (["failed", "blocked", "rejected"].includes(status)) return "fail";
    return "warn";
  }

  function planReason(name) {
    if (name.includes("UGC")) return "UGC anchor pro cold traffic a retargeting. Produkt musí být vidět rychle.";
    if (name.includes("Pain")) return "Zastaví scroll tím, že ukáže nákupní pochybnost bez vymýšlení claims.";
    if (name.includes("Identity")) return "Ukazuje lifestyle fit a to, že se v tom publikum pozná.";
    if (name.includes("Demo")) return "Retargeting proof přes viditelný detail produktu.";
    return "MOFU edukace: benefity a produktové detaily rozdělené do karet.";
  }

  function whyCreative(creative) {
    const angle = String(creative.angle || "").toLowerCase();
    if (creative.set_id === "C1" || creative.type === "video") return "UGC video anchor: důvěra přes avatara, rychlý hook, produktový kontext a reusable audience pro retargeting.";
    if (angle.includes("pain")) return "Pain angle: pojmenovává nákupní tření a získává klik jasnějším pohledem na produkt.";
    if (angle.includes("identity")) return "Identity angle: pomáhá kupujícímu představit si produkt ve vlastní rutině.";
    if (angle.includes("demo")) return "Demonstration angle: detailní vizuální důkaz pro warm audience.";
    return "Samostatný creative angle pro testování; rating a performance rozhodnou, jestli se z něj stane winner.";
  }

  function avatarFitRecommendation(avatar, stats) {
    const style = `${avatar.style || ""} ${avatar.voice || ""}`.toLowerCase();
    const topCategory = stats.best_categories?.[0]?.name;
    const topAngle = stats.best_angles?.[0]?.name;
    if (stats.avg_roas || stats.avg_ctr || stats.avg_rating) {
      return `Historicky nejsilnější signál: ${topAngle || "mixed angles"}${topCategory ? ` pro ${topCategory}` : ""}. Sleduj CTR, rating a schválení před scale.`;
    }
    if (style.includes("british") || style.includes("polished")) return "Premium UK fashion, kabelky, beauty a produkty, kde je důležitá důvěra a klidný hlas.";
    if (style.includes("natural") || style.includes("ugc")) return "Cold traffic a native UGC testy, kde má reklama působit méně produkčně a víc autenticky.";
    return "Univerzální testovací avatar; přesné doporučení vznikne po ratingu a performance záznamech.";
  }

  ReactDOM.createRoot(document.getElementById("root")).render(h(App));
})();
