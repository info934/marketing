"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  Bot,
  Boxes,
  BriefcaseBusiness,
  Check,
  Database,
  FlaskConical,
  GitBranch,
  Images,
  ImagePlus,
  LayoutDashboard,
  Library,
  Loader2,
  Mic,
  MessageSquare,
  Move,
  Paperclip,
  RefreshCw,
  Save,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Star,
  ThumbsDown,
  ThumbsUp,
  Upload,
  UserRound,
  Video,
  Volume2,
  Wand2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import type { ClipboardEvent, DragEvent, PointerEvent, ReactNode, WheelEvent } from "react";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  cancelGenerationRun,
  getAvatars,
  getCompanies,
  getCreativeIntelligence,
  getCreatives,
  getGenerationRuns,
  getLatestRun,
  getLearningSnapshot,
  getOrchestrator,
  getPromptSettings,
  getProviderCapabilities,
  makeDefaultAvatar,
  makeDefaultCompany,
  parseChatBrief,
  saveAvatar,
  saveCompany,
  saveCreativePerformance,
  saveCreativeRating,
  startGeneration,
  uploadAvatarProfile,
} from "@/lib/api";
import type {
  Avatar,
  CampaignForm,
  ChatItem,
  Company,
  Creative,
  IntelligenceSummary,
  LearningSnapshot,
  OrchestratorSnapshot,
  ParserResult,
  PromptSettings,
} from "@/lib/types";
import { appendBlock, cn, directImageUrlsFromText, urlsFromText } from "@/lib/utils";

type ApplyRole = "product" | "competitor" | "avatar" | "direction";
type SettingKey = "platform" | "market" | "language";
type AppView = "chat" | "dashboard" | "brands" | "avatars" | "creatives" | "prompt-lab" | "analytics" | "costs" | "settings";
type CreativeRatingStatus = "approved" | "rejected";
type CreativeRatingFeedback = {
  comment?: string;
  reasons?: string[];
};
type AgentVoiceMode = "idle" | "listening" | "speaking";
type RejectDraft = {
  open: boolean;
  comment: string;
  reasons: string[];
};
type GenerationOutputBranchState = "active" | "queued" | "completed" | "blocked" | "failed" | "cancelled" | "skipped" | "disabled" | "idle";
type GenerationOutputBranch = {
  title: string;
  enabled: boolean;
  state: GenerationOutputBranchState;
  badge: string;
  detail: string;
  meta: string;
};
type GenerationOutputPlanInfo = {
  mode: string;
  label: string;
  video: GenerationOutputBranch;
  staticImages: GenerationOutputBranch;
};
type WorkflowModelKey = "prompt_model" | "ugc_scenario_model" | "static_prompt_model" | "image_model" | "seedance_model";
type WorkflowNodeKind = "input" | "agent" | "model" | "guard" | "provider" | "memory" | "qa";
type WorkflowNode = {
  id: string;
  title: string;
  stage: string;
  kind: WorkflowNodeKind;
  summary: string;
  dependsOn: string[];
  outputs: string[];
  fields: string[];
  icon: typeof Bot;
  modelKey?: WorkflowModelKey;
  readonlyModel?: string;
  inventoryLayer?: string;
  inventory?: Record<string, unknown> | null;
};
type ScenarioDraft = {
  id: string;
  title: string;
  angle: string;
  hook: string;
  script: string;
  visualPlan: string[];
  cta: string;
  language: string;
  created_at: string;
};
type ChatWorkflowStepState = "done" | "active" | "blocked" | "waiting";
type ChatWorkflowStep = {
  id: string;
  title: string;
  detail: string;
  state: ChatWorkflowStepState;
  meta?: string;
};
type GeneratedChatAsset = {
  type: "image" | "video";
  url: string;
  name: string;
  meta?: string;
};

const defaultChatGptPromptModel = "openai/gpt-5.4-mini";
const previousGeminiScenarioModel = "google/gemini-3.5-flash";

const defaultForm: CampaignForm = {
  app_mode: "ecommerce",
  company_id: "kimlondon",
  ad_vertical: "fashion_ecommerce",
  brand_context: "",
  product_name: "",
  product_info: "",
  product_category: "auto",
  product_reference_url: "",
  competitor_strategy_enabled: false,
  competitor_name: "",
  competitor_url: "",
  competitor_chat_brief: "",
  competitor_screenshot_notes: "",
  avatar_id: "avatar1",
  custom_avatar_name: "My AI avatar",
  custom_avatar_persona: "natural UGC creator, calm and direct, slightly imperfect delivery",
  custom_avatar_voice: "natural British English creator voice, relaxed and conversational",
  avatar_identity_note: "",
  avatar_reference_url: "",
  avatar_own_person_consent: true,
  use_avatar_image_reference: true,
  platform: "meta",
  market: "UK",
  language: "en",
  generation_mode: "both",
  video_length: "15",
  seedance_model: "bytedance/seedance-2.0-fast",
  prompt_model: defaultChatGptPromptModel,
  ugc_scenario_model: defaultChatGptPromptModel,
  static_prompt_model: defaultChatGptPromptModel,
  image_model: "google/gemini-3-pro-image-preview",
  max_static_images: "8",
  image_size: "1K",
  openrouter_api_key: "",
  negative_prompt: "",
  content_prompt_system: "",
  content_prompt_task: "",
  base_video_prompt_template: "",
  ugc_video_extra_prompt: "",
  background_consistency: "strict",
  environment_override: false,
  preserve_original_scene_layout: false,
  category_prompt_handbag: "",
  category_prompt_shoes: "",
  category_prompt_apparel: "",
};

const settingRows: Array<{
  label: string;
  key: SettingKey;
  options: Array<{ value: string; label: string }>;
}> = [
  {
    label: "Platforma",
    key: "platform",
    options: [
      { value: "meta", label: "Meta" },
      { value: "google_ads", label: "Google" },
      { value: "tiktok", label: "TikTok" },
      { value: "instagram", label: "Instagram" },
      { value: "youtube", label: "YouTube" },
    ],
  },
  {
    label: "Trh",
    key: "market",
    options: [
      { value: "UK", label: "UK" },
      { value: "US", label: "US" },
      { value: "CZ", label: "CZ" },
      { value: "DE", label: "DE" },
      { value: "FR", label: "FR" },
      { value: "EU", label: "EU" },
    ],
  },
  {
    label: "Jazyk",
    key: "language",
    options: [
      { value: "en", label: "English" },
      { value: "cs", label: "Cestina" },
      { value: "de", label: "Deutsch" },
      { value: "fr", label: "Francais" },
      { value: "pl", label: "Polski" },
    ],
  },
];

const imageModelOptions = [
  { value: "google/gemini-3-pro-image-preview", label: "Gemini 3 Pro Image" },
  { value: "google/gemini-2.5-flash-image-preview", label: "Gemini 2.5 Flash Image Preview" },
  { value: "google/gemini-2.5-flash-image", label: "Gemini 2.5 Flash Image" },
] as const;

const promptModelOptions = [
  { value: defaultChatGptPromptModel, label: "GPT 5.4 Mini" },
  { value: "openai/gpt-4.1-mini", label: "GPT 4.1 Mini" },
  { value: "google/gemini-3.5-flash", label: "Gemini 3.5 Flash" },
] as const;

const videoModelOptions = [
  { value: "bytedance/seedance-2.0-fast", label: "Seedance 2.0 Fast" },
  { value: "bytedance/seedance-1.0-pro", label: "Seedance 1.0 Pro" },
  { value: "google/veo-3.1-fast", label: "Google Veo 3.1 Fast" },
] as const;

const workflowStageOrder = ["Input", "Understanding", "Strategy", "Prompting", "Generation", "QA / Learning"] as const;
const workflowGraphNodeWidth = 190;
const workflowGraphNodeHeight = 104;
const workflowGraphCanvasWidth = 1470;
const workflowGraphCanvasHeight = 1060;
const workflowGraphMinZoom = 0.35;
const workflowGraphMaxZoom = 1.35;
const workflowGraphStageLanes = [
  { stage: "Input", x: 0, width: 226, tone: "bg-cyan-50/80" },
  { stage: "Understanding", x: 226, width: 230, tone: "bg-emerald-50/70" },
  { stage: "Strategy", x: 456, width: 240, tone: "bg-violet-50/70" },
  { stage: "Prompting", x: 696, width: 300, tone: "bg-blue-50/70" },
  { stage: "Generation", x: 996, width: 236, tone: "bg-amber-50/70" },
  { stage: "QA / Learning", x: 1232, width: 238, tone: "bg-slate-100/80" },
] as const;
const workflowGraphLayout: Record<string, { x: number; y: number }> = {
  chat_brief_parser: { x: 24, y: 430 },
  product_intake: { x: 250, y: 140 },
  product_understanding: { x: 250, y: 290 },
  competitor_strategy: { x: 250, y: 440 },
  creative_memory_rag: { x: 250, y: 590 },
  audience_research: { x: 480, y: 70 },
  emotional_angle: { x: 480, y: 210 },
  creative_psychology: { x: 480, y: 350 },
  voice_personality: { x: 480, y: 490 },
  ugc_hook: { x: 480, y: 630 },
  scene_director: { x: 480, y: 770 },
  scene_chaining: { x: 480, y: 910 },
  ugc_strategy: { x: 735, y: 70 },
  angle_multiplier: { x: 735, y: 190 },
  angle_selector: { x: 735, y: 310 },
  content_prompt_engineer: { x: 735, y: 430 },
  ugc_scenario_writer: { x: 735, y: 550 },
  structured_prompt_v2: { x: 735, y: 670 },
  ads_creative_set: { x: 735, y: 790 },
  static_prompt_enhancer: { x: 735, y: 910 },
  provider_validation: { x: 1020, y: 440 },
  video_generation: { x: 1020, y: 280 },
  static_image_generation: { x: 1020, y: 600 },
  self_critique: { x: 1255, y: 260 },
  vision_quality: { x: 1255, y: 500 },
  memory_learning: { x: 1255, y: 740 },
};

const workflowNodeBlueprints: Array<Omit<WorkflowNode, "inventory">> = [
  {
    id: "chat_brief_parser",
    title: "Chat Brief Parser",
    stage: "Input",
    kind: "input",
    icon: MessageSquare,
    summary: "Turns pasted chat, URLs, and attachment roles into the campaign draft.",
    dependsOn: [],
    outputs: ["campaign_draft", "attachment_roles"],
    fields: ["prompt_model", "chatBriefItems"],
    modelKey: "prompt_model",
  },
  {
    id: "product_intake",
    title: "Ad Subject Intake Agent",
    stage: "Understanding",
    kind: "agent",
    icon: Boxes,
    summary: "Extracts verified product/service facts and safe ad benefits.",
    dependsOn: ["chat_brief_parser"],
    outputs: ["known_product_facts", "safe_benefits"],
    fields: ["product_name", "product_info", "product_category", "product_reference_url"],
    inventoryLayer: "Product Intake Agent",
  },
  {
    id: "product_understanding",
    title: "Product Understanding",
    stage: "Understanding",
    kind: "model",
    icon: Bot,
    summary: "Optional AI enrichment for category, use context, and visual facts.",
    dependsOn: ["product_intake"],
    outputs: ["automatic_product_understanding", "style_tags"],
    fields: ["prompt_model"],
    modelKey: "prompt_model",
  },
  {
    id: "competitor_strategy",
    title: "Competitor Strategy",
    stage: "Understanding",
    kind: "agent",
    icon: Search,
    summary: "Reads competitor notes/screenshots as strategic patterns, not copy targets.",
    dependsOn: ["product_understanding"],
    outputs: ["strategic_patterns", "hook_patterns", "visual_patterns"],
    fields: ["competitor_strategy_enabled", "competitor_chat_brief", "competitor_url"],
  },
  {
    id: "creative_memory_rag",
    title: "Creative Memory RAG",
    stage: "Understanding",
    kind: "memory",
    icon: Database,
    summary: "Retrieves winning and avoid patterns from creative memory.",
    dependsOn: ["product_understanding"],
    outputs: ["winning_patterns", "avoid_patterns", "creative_memory_guidance"],
    fields: ["ratings", "performance import"],
    readonlyModel: "text-embedding-3-small / SQLite",
  },
  {
    id: "audience_research",
    title: "Audience Research",
    stage: "Strategy",
    kind: "agent",
    icon: UserRound,
    summary: "Chooses the buyer archetype and decision triggers for the product.",
    dependsOn: ["product_understanding", "creative_memory_rag"],
    outputs: ["primary_archetype", "objections"],
    fields: ["market", "platform"],
  },
  {
    id: "emotional_angle",
    title: "Emotional Angle",
    stage: "Strategy",
    kind: "agent",
    icon: Sparkles,
    summary: "Selects the internal emotional driver without inventing unsafe claims.",
    dependsOn: ["audience_research"],
    outputs: ["primary_angle", "hook_bias", "creative_set_bias"],
    fields: ["product_info", "memory signals"],
  },
  {
    id: "creative_psychology",
    title: "Creative Psychology",
    stage: "Strategy",
    kind: "agent",
    icon: Sparkles,
    summary: "Builds the behavior tree: why the creative should move from hook to proof.",
    dependsOn: ["audience_research", "emotional_angle"],
    outputs: ["behavior_tree", "variation_rules"],
    fields: ["creative_memory_rag"],
  },
  {
    id: "voice_personality",
    title: "Voice Personality",
    stage: "Strategy",
    kind: "agent",
    icon: UserRound,
    summary: "Locks market language, accent, creator tone, pacing, and subtitle style.",
    dependsOn: ["audience_research", "emotional_angle"],
    outputs: ["voice_profile", "accent_profile", "prompt_fragment"],
    fields: ["language", "market", "custom_avatar_voice"],
  },
  {
    id: "ugc_hook",
    title: "UGC Hook Agent",
    stage: "Strategy",
    kind: "agent",
    icon: Star,
    summary: "Chooses a concrete first-second hook in the selected language.",
    dependsOn: ["creative_psychology", "creative_memory_rag"],
    outputs: ["selected_hook", "hook_bank"],
    fields: ["language", "product facts"],
  },
  {
    id: "scene_director",
    title: "Scene Director",
    stage: "Strategy",
    kind: "agent",
    icon: Video,
    summary: "Plans the shot sequence and product-visible scene logic.",
    dependsOn: ["creative_psychology", "ugc_hook"],
    outputs: ["directed_scenes", "camera_rules"],
    fields: ["video_length", "language"],
  },
  {
    id: "scene_chaining",
    title: "Scene Chaining",
    stage: "Strategy",
    kind: "agent",
    icon: GitBranch,
    summary: "Keeps avatar, wardrobe, environment, and scene transitions consistent.",
    dependsOn: ["scene_director", "voice_personality"],
    outputs: ["scene_links", "seedance_prompt_addendum"],
    fields: ["use_avatar_image_reference", "avatar_reference_url"],
  },
  {
    id: "ugc_strategy",
    title: "UGC Strategy Agent",
    stage: "Prompting",
    kind: "agent",
    icon: Bot,
    summary: "Assembles the deterministic UGC script, voiceover, hook, and scene plan.",
    dependsOn: ["ugc_hook", "scene_director", "scene_chaining", "competitor_strategy"],
    outputs: ["scene_by_scene_script", "voiceover", "subtitles"],
    fields: ["video_length", "language", "platform"],
    inventoryLayer: "UGC Strategy Agent",
  },
  {
    id: "angle_multiplier",
    title: "Ad Angle Multiplier",
    stage: "Prompting",
    kind: "agent",
    icon: SlidersHorizontal,
    summary: "Expands one idea into multiple angle families for creative testing.",
    dependsOn: ["ugc_strategy"],
    outputs: ["angles", "hook_bank"],
    fields: ["product notes", "language", "memory signals"],
    inventoryLayer: "Ad Angle Multiplier",
  },
  {
    id: "angle_selector",
    title: "Ad Angle Selector",
    stage: "Prompting",
    kind: "agent",
    icon: Check,
    summary: "Chooses angle families by creative slot, memory winners, and category priors.",
    dependsOn: ["angle_multiplier", "creative_memory_rag"],
    outputs: ["slot_selection", "angle_selection_reason"],
    fields: ["ratings", "performance import", "product_category"],
    inventoryLayer: "Ad Angle Selector",
  },
  {
    id: "content_prompt_engineer",
    title: "Content Prompt Engineer",
    stage: "Prompting",
    kind: "agent",
    icon: Wand2,
    summary: "Creates product fidelity, avatar, language, and Seedance prompt package.",
    dependsOn: ["ugc_strategy", "angle_selector"],
    outputs: ["seedance_payload", "structured_scene_prompt"],
    fields: ["base_video_prompt_template", "ugc_video_extra_prompt", "negative_prompt"],
    inventoryLayer: "Content Prompt Engineer Agent",
  },
  {
    id: "ugc_scenario_writer",
    title: "UGC Scenario Writer",
    stage: "Prompting",
    kind: "model",
    icon: Bot,
    summary: "Rewrites the scenario into relaxed spoken language before the final video prompt.",
    dependsOn: ["content_prompt_engineer"],
    outputs: ["prompt_generation", "approved_spoken_script"],
    fields: ["ugc_scenario_model", "content_prompt_system", "content_prompt_task"],
    modelKey: "ugc_scenario_model",
    inventoryLayer: "OpenRouter Prompt Client",
  },
  {
    id: "structured_prompt_v2",
    title: "Structured Prompt V2",
    stage: "Prompting",
    kind: "guard",
    icon: ShieldCheck,
    summary: "Compiles the final prompt with language, visible text, hand, and product guards.",
    dependsOn: ["ugc_scenario_writer"],
    outputs: ["compiled_video_prompt", "prompt_blocks"],
    fields: ["language", "background_consistency"],
  },
  {
    id: "ads_creative_set",
    title: "Ads Creative Set",
    stage: "Prompting",
    kind: "agent",
    icon: Images,
    summary: "Builds C1-C5 static creative plan, copy, carousel, and static prompts.",
    dependsOn: ["structured_prompt_v2", "angle_selector"],
    outputs: ["static_image_ads", "carousel_ad", "primary_text_variants"],
    fields: ["generation_mode", "category prompts"],
    inventoryLayer: "Ads Creative Set Agent",
  },
  {
    id: "static_prompt_enhancer",
    title: "Static Prompt Enhancer",
    stage: "Prompting",
    kind: "model",
    icon: Bot,
    summary: "Refines each static image scenario, hook, overlay, and prompt with the selected static prompt model.",
    dependsOn: ["ads_creative_set"],
    outputs: ["static_prompt_generation", "image_prompts"],
    fields: ["static_prompt_model"],
    modelKey: "static_prompt_model",
    inventoryLayer: "OpenRouter Prompt Client",
  },
  {
    id: "provider_validation",
    title: "Provider Validation",
    stage: "Generation",
    kind: "guard",
    icon: ShieldCheck,
    summary: "Hard-fails bad model/provider combos, prompt size, image count, and product references.",
    dependsOn: ["structured_prompt_v2", "static_prompt_enhancer"],
    outputs: ["provider_validation"],
    fields: ["generation_mode", "product_reference_url", "max_static_images"],
  },
  {
    id: "video_generation",
    title: "Video Generation",
    stage: "Generation",
    kind: "provider",
    icon: Video,
    summary: "Submits the final visible prompt and references to OpenRouter /videos.",
    dependsOn: ["provider_validation"],
    outputs: ["video_generation.submitted_payload", "video_path"],
    fields: ["seedance_model", "product_reference_url", "avatar_reference_url"],
    modelKey: "seedance_model",
    inventoryLayer: "OpenRouter Seedance Client",
  },
  {
    id: "static_image_generation",
    title: "Static Image Generation",
    stage: "Generation",
    kind: "provider",
    icon: ImagePlus,
    summary: "Generates each approved static creative with direct product reference images.",
    dependsOn: ["provider_validation"],
    outputs: ["image_assets", "static_image_generation"],
    fields: ["image_model", "max_static_images", "image_size"],
    modelKey: "image_model",
    inventoryLayer: "OpenRouter Image Client",
  },
  {
    id: "vision_quality",
    title: "Vision Quality QA",
    stage: "QA / Learning",
    kind: "qa",
    icon: Search,
    summary: "Compares generated static assets against the product reference when available.",
    dependsOn: ["static_image_generation"],
    outputs: ["vision_quality_status", "regeneration_attempts"],
    fields: ["product_reference_url"],
    readonlyModel: "OPENROUTER_VISION_MODEL / image fallback",
  },
  {
    id: "self_critique",
    title: "AI Self Critique",
    stage: "QA / Learning",
    kind: "model",
    icon: Bot,
    summary: "Reviews the final package for obvious creative and compliance issues.",
    dependsOn: ["video_generation", "static_image_generation"],
    outputs: ["ai_critique"],
    fields: ["prompt_model"],
    modelKey: "prompt_model",
  },
  {
    id: "memory_learning",
    title: "Prompt Learning Agent",
    stage: "QA / Learning",
    kind: "memory",
    icon: Database,
    summary: "Stores run outcomes, ratings, reject reasons, and embeddings for later RAG.",
    dependsOn: ["self_critique", "vision_quality"],
    outputs: ["learning_snapshot", "winning_patterns", "avoid_patterns"],
    fields: ["creative ratings", "performance import", "reject reason"],
    readonlyModel: "text-embedding-3-small / SQLite",
  },
];

const rejectReasonOptions = [
  { value: "produkt neni presny", label: "Produkt neni presny" },
  { value: "spatne ruce", label: "Spatne ruce" },
  { value: "rozpadly text", label: "Rozpadly text" },
  { value: "moc AI vzhled", label: "Moc AI vzhled" },
  { value: "slaby hook", label: "Slaby hook" },
  { value: "spatne prostredi", label: "Spatne prostredi" },
  { value: "avatar nepusobi autenticky", label: "Avatar neni autenticky" },
  { value: "produkt neni dobre videt", label: "Produkt neni videt" },
] as const;

const navItems = [
  {
    id: "chat",
    label: "Orchestrator",
    description: "AI agent pro ads",
    icon: Bot,
  },
  {
    id: "dashboard",
    label: "Dashboard",
    description: "Runy, KPI a dalsi krok",
    icon: LayoutDashboard,
  },
  {
    id: "brands",
    label: "Brands",
    description: "Brand a ads kontext",
    icon: BriefcaseBusiness,
  },
  {
    id: "avatars",
    label: "Avatar set",
    description: "Nastaveni creatoru",
    icon: UserRound,
  },
  {
    id: "creatives",
    label: "Creative sets",
    description: "Review a rating assets",
    icon: Library,
  },
  {
    id: "prompt-lab",
    label: "Prompt lab",
    description: "System prompt a provider audit",
    icon: FlaskConical,
  },
  {
    id: "analytics",
    label: "Analytics",
    description: "RAG learning a winners",
    icon: BarChart3,
  },
  {
    id: "costs",
    label: "Cost monitor",
    description: "Cena runu a marze",
    icon: BarChart3,
  },
  {
    id: "settings",
    label: "Settings",
    description: "Modely a vystupy",
    icon: Settings2,
  },
] as const satisfies ReadonlyArray<{
  id: AppView;
  label: string;
  description: string;
  icon: typeof MessageSquare;
}>;

const viewCopy: Record<AppView, { title: string; subtitle: string }> = {
  chat: {
    title: "AI Creative Agent",
    subtitle: "Orchestrator ridi brief, scenare, kreativy a generovani",
  },
  dashboard: {
    title: "Dashboard",
    subtitle: "Prehled runu, learning loopu a dalsich kroku",
  },
  brands: {
    title: "Brand context",
    subtitle: "Ulozene firmy, trhy, brand voice a pravidla pro tvorbu ads",
  },
  avatars: {
    title: "Avatar set",
    subtitle: "Nativni sprava avataru pro UGC workflow",
  },
  creatives: {
    title: "Creative sets",
    subtitle: "Knihovna assets, rating a performance signaly",
  },
  "prompt-lab": {
    title: "Prompt lab",
    subtitle: "Systemove prompty a provider pravidla pro dalsi generovani",
  },
  analytics: {
    title: "Analytics",
    subtitle: "Creative memory, RAG learning a winning patterns",
  },
  costs: {
    title: "Cost monitor",
    subtitle: "Prehled ceny generovani pro budouci monetizaci",
  },
  settings: {
    title: "Settings",
    subtitle: "Modely, jazyk, trh a vystupni rezim",
  },
};

function createIntroItem(): ChatItem {
  return {
    id: "intro",
    role: "assistant",
    text:
      "Vloz zadani reklamy, produkt/sluzbu, URL, screenshot konkurence nebo avatar poznamky. Portal z toho slozi brief a pripravi kreativy pro ads.",
    urls: [],
    files: [],
    applied_as: [],
    created_at: new Date().toISOString(),
  };
}

function createAssistantItem(text: string): ChatItem {
  return {
    id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role: "assistant",
    text,
    urls: [],
    files: [],
    applied_as: [],
    created_at: new Date().toISOString(),
  };
}

export default function CreativeOsApp() {
  const [view, setView] = useState<AppView>("chat");
  const [form, setForm] = useState<CampaignForm>(defaultForm);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [latestRun, setLatestRun] = useState<Record<string, unknown> | null>(null);
  const [generationRuns, setGenerationRuns] = useState<Array<Record<string, unknown>>>([]);
  const [lastRunPollAt, setLastRunPollAt] = useState("");
  const [runPollError, setRunPollError] = useState("");
  const [promptSettings, setPromptSettings] = useState<PromptSettings | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceSummary | null>(null);
  const [learning, setLearning] = useState<LearningSnapshot | null>(null);
  const [orchestrator, setOrchestrator] = useState<OrchestratorSnapshot | null>(null);
  const [providerCapabilities, setProviderCapabilities] = useState<Record<string, unknown> | null>(null);
  const [items, setItems] = useState<ChatItem[]>(() => [createIntroItem()]);
  const [scenarioDrafts, setScenarioDrafts] = useState<ScenarioDraft[]>([]);
  const [approvedScenarioId, setApprovedScenarioId] = useState("");
  const [scenarioMessageId, setScenarioMessageId] = useState("");
  const [activeChatRunId, setActiveChatRunId] = useState("");
  const [chatResultRun, setChatResultRun] = useState<Record<string, unknown> | null>(null);
  const [chatCompletionAnnouncedId, setChatCompletionAnnouncedId] = useState("");
  const [chatProblemAnnouncedKey, setChatProblemAnnouncedKey] = useState("");
  const [draft, setDraft] = useState("");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [productFile, setProductFile] = useState<File | null>(null);
  const [staticProductFiles, setStaticProductFiles] = useState<File[]>([]);
  const [competitorFiles, setCompetitorFiles] = useState<File[]>([]);
  const [parserResult, setParserResult] = useState<ParserResult | null>(null);
  const [runResult, setRunResult] = useState<Record<string, unknown> | null>(null);
  const [selectedCreativeId, setSelectedCreativeId] = useState("");
  const [companyDraft, setCompanyDraft] = useState<Partial<Company>>({});
  const [avatarDraft, setAvatarDraft] = useState<Partial<Avatar>>({});
  const [avatarImageFile, setAvatarImageFile] = useState<File | null>(null);
  const [status, setStatus] = useState("Pripraveno");
  const [dataStatus, setDataStatus] = useState("Nacitani dat...");
  const [busy, setBusy] = useState(false);
  const [dataBusy, setDataBusy] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const update = <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const selectView = (nextView: AppView) => {
    setView(nextView);
    replaceShellUrl(nextView);
  };

  useEffect(() => {
    setForm((current) => {
      const nextUgcModel =
        current.ugc_scenario_model === previousGeminiScenarioModel ? defaultChatGptPromptModel : current.ugc_scenario_model;
      const nextStaticModel =
        current.static_prompt_model === previousGeminiScenarioModel ? defaultChatGptPromptModel : current.static_prompt_model;
      if (nextUgcModel === current.ugc_scenario_model && nextStaticModel === current.static_prompt_model) {
        return current;
      }
      return {
        ...current,
        ugc_scenario_model: nextUgcModel,
        static_prompt_model: nextStaticModel,
      };
    });
  }, []);

  const pollLatestRun = useCallback(async (announce = false) => {
    try {
      const payload = await getLatestRun();
      const run = normalizeRunPayload(payload) || payload;
      setLatestRun(run);
      setGenerationRuns((current) => mergeRunList(current, run));
      setLastRunPollAt(new Date().toLocaleTimeString());
      setRunPollError("");
      getOrchestrator()
        .then(setOrchestrator)
        .catch(() => undefined);
      if (announce) setDataStatus("Latest run aktualizovan.");
      return run;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Latest run poll failed.";
      setRunPollError(message);
      if (announce) setDataStatus(message);
      return null;
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setDataBusy(true);
    setDataStatus("Synchronizuji workflow data...");
    const [companyResult, avatarResult, creativeResult, latestResult, runListResult, promptResult, intelligenceResult, learningResult, orchestratorResult, providerResult] =
      await Promise.allSettled([
        getCompanies(),
        getAvatars(),
        getCreatives(120),
        getLatestRun(),
        getGenerationRuns(120),
        getPromptSettings(),
        getCreativeIntelligence(),
        getLearningSnapshot(),
        getOrchestrator(),
        getProviderCapabilities(),
      ]);

    if (companyResult.status === "fulfilled") {
      setCompanies(companyResult.value.companies || []);
      const defaultCompanyId = companyResult.value.default_company_id;
      const defaultCompany = (companyResult.value.companies || []).find((company) => company.id === defaultCompanyId) || (companyResult.value.companies || [])[0];
      if (defaultCompany) {
        setCompanyDraft((current) => (current.id ? current : defaultCompany));
        setForm((current) => applyCompanyDefaults(current.company_id ? current : { ...current, company_id: defaultCompany.id }, defaultCompany));
      }
    }
    if (avatarResult.status === "fulfilled") {
      setAvatars(avatarResult.value.avatars || []);
      const defaultAvatarId = avatarResult.value.default_avatar_id;
      if (defaultAvatarId) {
        setForm((current) => ({ ...current, avatar_id: current.avatar_id || defaultAvatarId }));
      }
    }
    if (creativeResult.status === "fulfilled") setCreatives(creativeResult.value.creatives || []);
    if (latestResult.status === "fulfilled") {
      setLatestRun(normalizeRunPayload(latestResult.value) || latestResult.value);
      setLastRunPollAt(new Date().toLocaleTimeString());
      setRunPollError("");
    }
    if (runListResult.status === "fulfilled") setGenerationRuns(runListResult.value.runs || []);
    if (promptResult.status === "fulfilled") setPromptSettings(promptResult.value);
    if (intelligenceResult.status === "fulfilled") setIntelligence(intelligenceResult.value);
    if (learningResult.status === "fulfilled") setLearning(learningResult.value);
    if (orchestratorResult.status === "fulfilled") setOrchestrator(orchestratorResult.value);
    if (providerResult.status === "fulfilled") setProviderCapabilities(providerResult.value);

    const failed = [companyResult, avatarResult, creativeResult, latestResult, runListResult, promptResult, intelligenceResult, learningResult, orchestratorResult, providerResult].filter(
      (item) => item.status === "rejected",
    ).length;
    setDataStatus(failed ? `Nacteno, ${failed} endpointu selhalo.` : "Data synchronizovana.");
    setDataBusy(false);
  }, []);

  useEffect(() => {
    setView(initialView());
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    const pollMs = isRunActive(latestRun) ? 3000 : 8000;
    const id = window.setInterval(() => {
      void pollLatestRun(false);
    }, pollMs);
    return () => window.clearInterval(id);
  }, [latestRun, pollLatestRun]);

  useEffect(() => {
    const selected = creatives.find((creative) => creative.creative_id === selectedCreativeId);
    const firstReviewable = creatives.find((creative) => !isNonReviewableCreative(creative));
    if (!selected) {
      setSelectedCreativeId(firstReviewable?.creative_id || creatives[0]?.creative_id || "");
    }
  }, [creatives, selectedCreativeId]);

  useEffect(() => {
    const runId = String(latestRun?.run_id || "");
    if (!activeChatRunId || runId !== activeChatRunId || isRunActive(latestRun)) return;
    const status = String(readRecord(latestRun?.monitor)?.status || latestRun?.status || "").toLowerCase();
    const problem = generationRunProblem(latestRun);
    if (problem) {
      const problemKey = `${runId}:problem`;
      if (chatProblemAnnouncedKey === problemKey) return;
      setChatProblemAnnouncedKey(problemKey);
      setChatCompletionAnnouncedId(runId);
      const assets = generatedRunAssets(latestRun);
      setChatResultRun(assets.imageCount || assets.videoCount ? latestRun : null);
      setItems((current) => [...current, createAssistantItem(problem.message)]);
      setStatus("Generovani skoncilo s problemem. Detail je v agent timeline.");
      return;
    }
    if (status !== "completed") return;
    setChatResultRun(latestRun);
    if (chatCompletionAnnouncedId === runId) return;
    setChatCompletionAnnouncedId(runId);
    const assets = generatedRunAssets(latestRun);
    setItems((current) => [
      ...current,
      createAssistantItem(
        `Hotovo. Vysledek aktualniho generovani je pripraveny v agent timeline: ${assets.videoCount} video / ${assets.imageCount} statik.`,
      ),
    ]);
    setStatus("Generovani dokonceno. Vysledky jsou v agent timeline.");
  }, [activeChatRunId, latestRun, chatCompletionAnnouncedId, chatProblemAnnouncedKey]);

  const activeCompany = useMemo(() => companies.find((company) => company.id === form.company_id) || companies[0], [companies, form.company_id]);
  const activeAvatar = useMemo(() => avatars.find((avatar) => avatar.id === form.avatar_id) || avatars[0], [avatars, form.avatar_id]);
  const selectedCreative = useMemo(
    () =>
      creatives.find((creative) => creative.creative_id === selectedCreativeId) ||
      creatives.find((creative) => !isNonReviewableCreative(creative)) ||
      creatives[0],
    [creatives, selectedCreativeId],
  );

  const readiness = useMemo(
    () => [
      ["Brief", Boolean(form.product_info || form.product_reference_url || productFile || staticProductFiles.length)],
      ["Brand", Boolean(form.company_id || form.brand_context)],
      ["Avatar", Boolean(form.avatar_id)],
      ["Konkurence", Boolean(form.competitor_strategy_enabled && (form.competitor_chat_brief || competitorFiles.length))],
      ["Plan", Boolean(form.generation_mode && form.prompt_model)],
    ],
    [form, productFile, staticProductFiles.length, competitorFiles.length],
  );

  const companyOptions = useMemo(() => {
    const loaded = companies.map((company) => ({
      value: company.id,
      label: company.name || company.id,
    }));
    return loaded.length ? loaded : [{ value: form.company_id, label: form.company_id || "No brand" }];
  }, [companies, form.company_id]);

  const avatarOptions = useMemo(() => {
    const loaded = avatars.map((avatar) => ({
      value: avatar.id,
      label: avatar.name || avatar.id,
    }));
    return loaded.length ? loaded : [{ value: form.avatar_id, label: form.avatar_id || "Default avatar" }];
  }, [avatars, form.avatar_id]);

  const appendFiles = useCallback((files: FileList | File[] | null | undefined) => {
    const images = Array.from(files || []).filter((file) => file.type.startsWith("image/"));
    if (!images.length) return;
    setPendingFiles((current) => [...current, ...images].slice(0, 10));
    setStatus(`${images.length} obrazku pripravenych v composeru`);
  }, []);

  const applyProductFiles = useCallback((files: FileList | File[] | null | undefined) => {
    const imageFiles = Array.from(files || []).filter((file) => file.type.startsWith("image/"));
    if (!imageFiles.length) return;
    if (!productFile) {
      setProductFile(imageFiles[0]);
      setStaticProductFiles((current) => mergeFileList(current, imageFiles.slice(1), 8));
      return;
    }
    setStaticProductFiles((current) => mergeFileList(current, imageFiles.filter((file) => fileKey(file) !== fileKey(productFile)), 8));
  }, [productFile]);

  const addItem = () => {
    const text = draft.trim();
    if (!text && !pendingFiles.length) return;

    const item: ChatItem = {
      id: `item-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      role: "user",
      text,
      urls: urlsFromText(text),
      files: pendingFiles,
      applied_as: [],
      created_at: new Date().toISOString(),
    };

    const nextItems = [...items, item];
    setItems(nextItems);
    setDraft("");
    setPendingFiles([]);
    setStatus("Polozka pridana. Automaticky skladam brief...");
    void autoParseItems(nextItems.filter((chatItem) => chatItem.role === "user"));
  };

  const markApplied = (id: string, role: ApplyRole) => {
    setItems((current) =>
      current.map((item) =>
        item.id === id ? { ...item, applied_as: Array.from(new Set([...item.applied_as, role])) } : item,
      ),
    );
  };

  const applyItem = (item: ChatItem, role: ApplyRole) => {
    if (role === "product") {
      const directImageUrl = directImageUrlsFromText(item.text)[0] || "";
      setForm((current) => ({
        ...current,
        product_name: current.product_name || firstLine(item.text),
        product_info: appendBlock(current.product_info, item.text),
        product_reference_url: directImageUrl || current.product_reference_url,
      }));
      applyProductFiles(item.files);
      setStatus(directImageUrl || item.files[0] ? "Pouzito jako ad brief." : "Pouzito jako brief; URL neni direct image reference.");
    }

    if (role === "competitor") {
      setForm((current) => ({
        ...current,
        competitor_strategy_enabled: true,
        competitor_chat_brief: appendBlock(current.competitor_chat_brief, item.text),
        competitor_url: item.urls[0] || current.competitor_url,
      }));
      if (item.files.length) setCompetitorFiles((current) => [...current, ...item.files].slice(0, 12));
      setStatus("Pouzito jako competitor strategy.");
    }

    if (role === "avatar") {
      setForm((current) => ({
        ...current,
        custom_avatar_persona: appendBlock(current.custom_avatar_persona, item.text),
        avatar_identity_note: appendBlock(current.avatar_identity_note, item.text),
        avatar_reference_url: item.urls[0] || current.avatar_reference_url,
      }));
      setStatus("Pouzito jako avatar guidance.");
    }

    if (role === "direction") {
      setForm((current) => ({
        ...current,
        ugc_video_extra_prompt: appendBlock(current.ugc_video_extra_prompt, item.text),
      }));
      setStatus("Pouzito jako rezie kreativy.");
    }

    markApplied(item.id, role);
  };

  const applyParser = (result: ParserResult, sourceItems: ChatItem[] = items) => {
    const patch = result.campaign_draft || {};
    setForm((current) => ({
      ...current,
      ...nonEmptyPatch(current, patch),
      competitor_strategy_enabled: Boolean(patch.competitor_strategy_enabled || current.competitor_strategy_enabled),
    }));

    const byId = Object.fromEntries(sourceItems.map((item) => [item.id, item]));
    result.attachment_roles.forEach((role) => {
      const item = byId[role.item_id];
      if (!item?.files.length) return;
      if (role.role === "product") applyProductFiles(item.files);
      if (role.role === "competitor") setCompetitorFiles((current) => [...current, ...item.files].slice(0, 12));
      markApplied(role.item_id, role.role);
    });
  };

  const autoParseItems = async (userItems: ChatItem[]) => {
    if (!userItems.length) {
      return;
    }

    setBusy(true);
    setStatus("Automaticky rozpoznavam produkt, URL a brief...");
    try {
      const result = await parseChatBrief(userItems, form);
      setParserResult(result);
      applyParser(result, userItems);
      const summary = parserSummaryText(result);
      if (summary) {
        setItems((current) => [...current, createAssistantItem(summary)]);
      }
      setStatus("Brief automaticky vyplnen.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Automaticky parser selhal.");
    } finally {
      setBusy(false);
    }
  };

  const createScenarioDrafts = () => {
    if (!form.product_info && !form.product_reference_url && !productFile) {
      setStatus("Nejdriv dopln ad brief, URL nebo obrazek.");
      selectView("chat");
      return;
    }

    const drafts = buildChatScenarioDrafts(form, activeAvatar);
    const scenarioMessage = createAssistantItem(
      `Pripravil jsem ${drafts.length} scenare pro UGC. Vyber jednu variantu v agent timeline, po schvaleni se propise do rezie generovani.`,
    );
    setScenarioDrafts(drafts);
    setApprovedScenarioId("");
    setScenarioMessageId(scenarioMessage.id);
    setItems((current) => [...current, scenarioMessage]);
    setStatus("Scenare pripraveny ke schvaleni.");
  };

  const approveScenario = (draftId: string) => {
    const draftToApprove = scenarioDrafts.find((scenario) => scenario.id === draftId);
    if (!draftToApprove) return;
    setApprovedScenarioId(draftToApprove.id);
    setForm((current) => ({
      ...current,
      ugc_video_extra_prompt: upsertApprovedScenarioPrompt(current.ugc_video_extra_prompt, draftToApprove),
    }));
    setItems((current) => [
      ...current,
      createAssistantItem(`Schvaleno: ${draftToApprove.title}. Tento scenar je zapsany do rezie a pujde do dalsiho generation runu.`),
    ]);
    setStatus("Scenar schvalen. Ted muzes dat Generate v orchestratoru.");
  };

  const generate = async () => {
    if (!form.product_info && !form.product_reference_url && !productFile && staticProductFiles.length === 0) {
      setStatus("Dopln ad brief, URL nebo obrazek.");
      selectView("chat");
      return;
    }
    if (!approvedScenarioId && !form.ugc_video_extra_prompt.trim()) {
      setStatus("Nejdriv priprav a schval Creative Plan. Spoustim navrh scenaru.");
      createScenarioDrafts();
      return;
    }
    if (form.generation_mode !== "static" && !isVideoReadyProductReference(form.product_reference_url)) {
      setStatus("Pro video model dopln direct public visual URL (.jpg/.png/.webp/.avif). Lokalni upload pouzijeme jen pro statiky.");
      selectView("chat");
      return;
    }
    if (!form.avatar_own_person_consent) {
      setStatus("Potvrd autorizaci AI avatara pred generovanim.");
      selectView("chat");
      return;
    }

    selectView("chat");
    setBusy(true);
    setRunResult(null);
    setStatus("Spoustim generation run...");
    setItems((current) => [
      ...current,
      createAssistantItem(
        `Generovani zacalo. Odhad trvani: ${generationEstimateText(form)}. Vystup vratim do agent timeline hned po dokonceni.`,
      ),
    ]);
    try {
      const payload = await startGeneration(form, productFile, staticProductFiles, competitorFiles);
      const run = normalizeRunPayload(payload) || payload;
      const runId = String(run.run_id || "");
      setActiveChatRunId(runId);
      setChatResultRun(null);
      setChatCompletionAnnouncedId("");
      setChatProblemAnnouncedKey("");
      setRunResult(run);
      setLatestRun(run);
      setGenerationRuns((current) => mergeRunList(current, run));
      setLastRunPollAt(new Date().toLocaleTimeString());
      setRunPollError("");
      setStatus(`Run odeslan: ${String(run.run_id || run.status || "queued")}`);
      selectView("chat");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Generation request failed.";
      setItems((current) => [...current, createAssistantItem(`Generovani se nepodarilo spustit: ${message}`)]);
      setStatus(message);
    } finally {
      setBusy(false);
    }
  };

  const cancelRun = async () => {
    const runId = String(latestRun?.run_id || "");
    if (!runId) {
      setDataStatus("Neni aktivni run ke zruseni.");
      return;
    }

    setDataBusy(true);
    setDataStatus("Posilam cancel request...");
    try {
      const payload = await cancelGenerationRun(runId);
      const run = normalizeRunPayload(payload) || payload;
      setLatestRun(run);
      setRunResult(run);
      setGenerationRuns((current) => mergeRunList(current, run));
      setLastRunPollAt(new Date().toLocaleTimeString());
      setRunPollError("");
      setDataStatus("Cancel request ulozen.");
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Cancel failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const startNewChat = () => {
    setItems([createIntroItem()]);
    setScenarioDrafts([]);
    setApprovedScenarioId("");
    setScenarioMessageId("");
    setActiveChatRunId("");
    setChatResultRun(null);
    setChatCompletionAnnouncedId("");
    setChatProblemAnnouncedKey("");
    setDraft("");
    setPendingFiles([]);
    setProductFile(null);
    setStaticProductFiles([]);
    setCompetitorFiles([]);
    setParserResult(null);
    setRunResult(null);
    setForm((current) => resetCampaignDraftForNewChat(current));
    setStatus("Novy agent run pripraveny pro dalsi generovani.");
    selectView("chat");
  };

  const selectCompany = (company: Company) => {
    setForm((current) => applyCompanyDefaults({ ...current, company_id: company.id }, company));
    setCompanyDraft(company);
    setDataStatus(`Brand aktivni: ${company.name || company.id}`);
  };

  const editCompanyDraft = (company: Partial<Company>) => {
    setCompanyDraft(company);
    setDataStatus(`Editace brandu: ${company.name || company.id || "draft"}`);
  };

  const createCompanyDraft = () => {
    const id = `brand_${Date.now().toString(36)}`;
    setCompanyDraft({
      id,
      name: "New brand",
      ad_vertical: "ads",
      business_model: "",
      market: form.market || "UK",
      language: form.language || "en",
      default_platform: form.platform || "meta",
      creative_channels: ["meta", "instagram"],
      product_categories: [],
      brand_voice: "direct, practical, natural, performance-focused",
      creative_quality_rules: ["distinct angle per creative", "clear proof moment", "no generic stock ad look"],
    });
    selectView("brands");
    setDataStatus("Novy brand draft pripraven.");
  };

  const saveCompanyDraft = async () => {
    if (!companyDraft.name && !companyDraft.id) {
      setDataStatus("Dopln jmeno brandu.");
      return;
    }
    const draftToSave = companyDraft.id
      ? companyDraft
      : {
          ...companyDraft,
          id: companyIdFromName(companyDraft.name || "brand"),
        };
    setDataBusy(true);
    try {
      const saved = await saveCompany(normalizeCompanyDraft(draftToSave));
      selectCompany(saved.company);
      setDataStatus(`Brand ulozen: ${saved.company.name || saved.company.id}`);
      await refreshAll();
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Brand save failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const setDefaultCompany = async (company: Company) => {
    setDataBusy(true);
    try {
      const saved = await makeDefaultCompany(company.id);
      selectCompany(saved.company);
      setDataStatus(`Vychozi brand: ${saved.company.name || saved.company.id}`);
      await refreshAll();
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Default brand failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const selectAvatar = (avatar: Avatar) => {
    update("avatar_id", avatar.id);
    update("custom_avatar_name", avatar.name || "");
    update("custom_avatar_persona", avatar.style || "");
    update("custom_avatar_voice", avatar.voice || "");
    update("avatar_reference_url", avatar.image_url || avatar.preview_url || "");
    setAvatarImageFile(null);
    setAvatarDraft(avatar);
    setStatus(`Avatar aktivni: ${avatar.name || avatar.id}`);
  };

  const editAvatarDraft = (avatar: Partial<Avatar>) => {
    setAvatarImageFile(null);
    setAvatarDraft(avatar);
    setDataStatus(`Editace avatara: ${avatar.name || avatar.id || "draft"}`);
  };

  const createAvatarDraft = () => {
    const id = `avatar_${Date.now().toString(36)}`;
    setAvatarImageFile(null);
    setAvatarDraft({
      id,
      name: "New UGC avatar",
      style: "natural UGC creator, calm and direct, slightly imperfect delivery",
      voice: "natural conversational creator voice, relaxed and ad-safe",
      image_url: "",
    });
    setStatus("Novy avatar draft pripraven.");
    setDataStatus("Vypln jmeno, personu, voice a pripadne nahraj referencni obrazek.");
  };

  const saveAvatarDraft = async () => {
    if (!avatarDraft.name && !avatarDraft.id) {
      setDataStatus("Dopln jmeno avatara.");
      return;
    }
    const draftToSave = avatarDraft.id
      ? avatarDraft
      : {
          ...avatarDraft,
          id: avatarIdFromName(avatarDraft.name || "avatar"),
        };
    setDataBusy(true);
    try {
      const saved = avatarImageFile ? await uploadAvatarProfile(draftToSave, avatarImageFile) : await saveAvatar(draftToSave);
      selectAvatar(saved.avatar);
      setAvatarImageFile(null);
      setDataStatus(`Avatar ulozen: ${saved.avatar.name || saved.avatar.id}`);
      await refreshAll();
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Avatar save failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const setDefaultAvatar = async (avatar: Avatar) => {
    setDataBusy(true);
    try {
      const saved = await makeDefaultAvatar(avatar.id);
      selectAvatar(saved.avatar);
      setDataStatus(`Vychozi avatar: ${saved.avatar.name || saved.avatar.id}`);
      await refreshAll();
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Default avatar failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const rateCreative = async (creative: Creative, ratingStatus: CreativeRatingStatus, feedback: CreativeRatingFeedback = {}) => {
    const reasons = Array.from(new Set((feedback.reasons || []).map((reason) => reason.trim()).filter(Boolean)));
    const comment = String(feedback.comment || "").trim();
    setDataBusy(true);
    try {
      await saveCreativeRating({
        creative_id: creative.creative_id,
        status: ratingStatus,
        user_rating: ratingStatus === "approved" ? 5 : 1,
        comment: ratingStatus === "approved" ? comment || "approved in Next UI" : comment || reasons.join(", ") || "rejected in Next UI",
        reasons: ratingStatus === "rejected" ? reasons : [],
      });
      setDataStatus(`Rating ulozen: ${ratingStatus}`);
      await refreshAll();
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Rating failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const savePerformance = async (creative: Creative, payload: Record<string, unknown>) => {
    setDataBusy(true);
    try {
      await saveCreativePerformance({
        ...payload,
        creative_id: creative.creative_id,
        platform: creative.platform,
      });
      setDataStatus("Performance ulozena.");
      await refreshAll();
    } catch (error) {
      setDataStatus(error instanceof Error ? error.message : "Performance save failed.");
    } finally {
      setDataBusy(false);
    }
  };

  const applyPromptDefaults = () => {
    if (!promptSettings) return;
    setForm((current) => ({
      ...current,
      negative_prompt: promptSettings.negative_prompt || current.negative_prompt,
      content_prompt_system: promptSettings.content_prompt_system || current.content_prompt_system,
      content_prompt_task: promptSettings.content_prompt_task || current.content_prompt_task,
      base_video_prompt_template: promptSettings.base_video_prompt_template || current.base_video_prompt_template,
      category_prompt_handbag: promptSettings.category_prompt_presets?.handbag || current.category_prompt_handbag,
      category_prompt_shoes: promptSettings.category_prompt_presets?.shoes || current.category_prompt_shoes,
      category_prompt_apparel: promptSettings.category_prompt_presets?.apparel || current.category_prompt_apparel,
    }));
    setDataStatus("Prompt defaults propsane do aktualniho campaign formu.");
  };

  const handlePaste = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const images = Array.from(event.clipboardData.items)
      .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter(Boolean) as File[];
    if (!images.length) return;
    event.preventDefault();
    appendFiles(images);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    appendFiles(event.dataTransfer.files);
  };

  const activeViewCopy = viewCopy[view];
  const latestRunStatus = String(readRecord(latestRun?.monitor)?.status || latestRun?.status || "idle");
  const activePhase = orchestrator?.phases.find((phase) => phase.id === orchestrator.current_phase);
  const activePhaseLabel = activePhase?.title || "Brief";
  const activeRunId = String(latestRun?.run_id || "");

  return (
    <main className="h-dvh overflow-hidden bg-[#eef1f4] text-foreground">
      <div className="grid h-full min-h-0 overflow-hidden lg:grid-cols-[88px_minmax(0,1fr)] xl:grid-cols-[276px_minmax(0,1fr)_392px]">
        <aside className="hidden min-h-0 border-r border-slate-200 bg-[#101820] text-white lg:flex lg:flex-col">
          <div className="flex h-16 shrink-0 items-center gap-3 border-b border-white/10 px-4 xl:px-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#23c7a9] text-[#06211e]">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="hidden min-w-0 xl:block">
              <p className="truncate text-sm font-semibold">Creative Agent</p>
              <p className="truncate text-xs text-white/55">Ads orchestration portal</p>
            </div>
          </div>

          <nav className="chat-scroll min-h-0 flex-1 space-y-1 overflow-y-auto px-3 py-4 xl:px-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = view === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => selectView(item.id)}
                  title={item.label}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition-colors",
                    active ? "bg-white text-[#101820]" : "text-white/68 hover:bg-white/10 hover:text-white",
                  )}
                >
                  <Icon className={cn("h-4 w-4 shrink-0", active ? "text-[#101820]" : "text-white/58")} />
                  <span className="hidden min-w-0 xl:block">
                    <span className="block font-medium leading-4">{item.label}</span>
                    <span className={cn("block truncate text-xs", active ? "text-slate-500" : "text-white/45")}>
                      {item.description}
                    </span>
                  </span>
                </button>
              );
            })}
          </nav>

          <div className="hidden shrink-0 border-t border-white/10 p-4 xl:block">
            <div className="space-y-2 text-xs">
            {readiness.map(([label, ready]) => (
                <div key={String(label)} className="flex items-center justify-between rounded-md bg-white/[0.07] px-3 py-2">
                <span>{label}</span>
                {ready ? (
                    <Check className="h-4 w-4 text-[#23c7a9]" />
                ) : (
                    <span className="h-2 w-2 rounded-full bg-white/35" />
                )}
              </div>
            ))}
          </div>
          </div>
        </aside>

        <section className="flex min-h-0 flex-col overflow-hidden">
          <header className="z-20 shrink-0 border-b border-slate-200 bg-white/92 backdrop-blur">
            <div className="flex min-h-16 flex-col gap-3 px-3 py-3 md:px-5 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <Select
                  aria-label="Workspace"
                  className="h-9 w-44 lg:hidden"
                  value={view}
                  onChange={(event) => selectView(event.target.value as AppView)}
                  options={navItems.map((item) => ({ value: item.id, label: item.label }))}
                />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="truncate text-base font-semibold">{activeViewCopy.title}</h1>
                    <Badge variant="secondary">{activePhaseLabel}</Badge>
                    <Badge variant={isRunActive(latestRun) ? "default" : "outline"}>{latestRunStatus}</Badge>
                  </div>
                  <p className="mt-1 truncate text-xs text-muted-foreground">{activeViewCopy.subtitle}</p>
                </div>
              </div>
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <div className="hidden min-w-0 rounded-md border bg-slate-50 px-3 py-2 text-xs md:block">
                  <span className="text-muted-foreground">Run </span>
                  <span className="font-medium">{activeRunId ? activeRunId.slice(0, 22) : "not started"}</span>
                </div>
                <Button size="sm" variant="outline" onClick={refreshAll} disabled={dataBusy} title="Synchronizovat data">
                  {dataBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                  Sync
                </Button>
                <Button
                  size="sm"
                  variant={canCancelRun(latestRun) ? "destructive" : "outline"}
                  onClick={cancelRun}
                  disabled={!canCancelRun(latestRun) || dataBusy}
                  title={canCancelRun(latestRun) ? "Zrusit aktivni generation run" : "Zruseni je dostupne jen kdyz run aktivne bezi"}
                >
                  <X className="h-4 w-4" />
                  Stop
                </Button>
                <Button size="sm" onClick={generate} disabled={busy}>
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
                  Generate
                </Button>
              </div>
            </div>
          </header>

          {view === "chat" && (
            <ChatWorkspace
              form={form}
              update={update}
              items={items}
              draft={draft}
              pendingFiles={pendingFiles}
              productFile={productFile}
              staticProductFiles={staticProductFiles}
              scenarioDrafts={scenarioDrafts}
              approvedScenarioId={approvedScenarioId}
              scenarioMessageId={scenarioMessageId}
              chatResultRun={chatResultRun}
              dragActive={dragActive}
              status={status}
              busy={busy}
              activeCompany={activeCompany}
              orchestrator={orchestrator}
              fileInputRef={fileInputRef}
              setDraft={setDraft}
              setPendingFiles={setPendingFiles}
              setProductFile={setProductFile}
              setStaticProductFiles={setStaticProductFiles}
              onPaste={handlePaste}
              onDrop={handleDrop}
              onDragActive={setDragActive}
              appendFiles={appendFiles}
              addItem={addItem}
              createScenarioDrafts={createScenarioDrafts}
              approveScenario={approveScenario}
              generate={generate}
              onNewChat={startNewChat}
              applyItem={applyItem}
            />
          )}

          {view === "dashboard" && (
            <DashboardWorkspace
              intelligence={intelligence}
              learning={learning}
              latestRun={latestRun}
              lastRunPollAt={lastRunPollAt}
              runPollError={runPollError}
              creatives={creatives}
              onView={selectView}
              onRefreshRun={() => void pollLatestRun(true)}
              onCancelRun={cancelRun}
            />
          )}

          {view === "brands" && (
            <BrandWorkspace
              companies={companies}
              activeCompanyId={form.company_id}
              onSelect={selectCompany}
              onCreate={createCompanyDraft}
              onEdit={editCompanyDraft}
              onMakeDefault={setDefaultCompany}
            />
          )}

          {view === "avatars" && (
            <AvatarWorkspace
              avatars={avatars}
              activeAvatarId={form.avatar_id}
              onSelect={selectAvatar}
              onCreate={createAvatarDraft}
              onEdit={editAvatarDraft}
              onMakeDefault={setDefaultAvatar}
            />
          )}

          {view === "creatives" && (
            <CreativeWorkspace
              creatives={creatives}
              selectedCreativeId={selectedCreativeId}
              onSelect={setSelectedCreativeId}
              onRate={rateCreative}
            />
          )}

          {view === "prompt-lab" && (
            <PromptLabWorkspace form={form} update={update} settings={promptSettings} applyPromptDefaults={applyPromptDefaults} />
          )}

          {view === "analytics" && <AnalyticsWorkspace intelligence={intelligence} learning={learning} creatives={creatives} />}

          {view === "costs" && <CostMonitorWorkspace runs={generationRuns} latestRun={latestRun} onViewRun={setLatestRun} />}

          {view === "settings" && (
            <SettingsWorkspace
              form={form}
              update={update}
              avatarOptions={avatarOptions}
              providerCapabilities={providerCapabilities}
              settings={promptSettings}
            />
          )}
        </section>

        <aside className="chat-scroll hidden min-h-0 overflow-y-auto border-l border-slate-200 bg-[#f8fafb] xl:block">
          <div className="sticky top-0 z-10 border-b bg-[#f8fafb]/95 px-4 py-4 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">Mission Control</p>
                <p className="text-xs text-muted-foreground">Brief, rules, assets, output</p>
              </div>
              <Badge variant="outline">{dataStatus}</Badge>
            </div>
          </div>
          <div className="p-4">
          {view === "chat" && (
            <CampaignPanel
              form={form}
              update={update}
              companyOptions={companyOptions}
              activeCompany={activeCompany}
              onCompanySelect={(companyId) => {
                const company = companies.find((item) => item.id === companyId);
                if (company) selectCompany(company);
                else update("company_id", companyId);
              }}
              avatarOptions={avatarOptions}
              productFile={productFile}
              staticProductFiles={staticProductFiles}
              setProductFile={setProductFile}
              setStaticProductFiles={setStaticProductFiles}
              competitorFiles={competitorFiles}
              parserResult={parserResult}
              runResult={runResult}
              latestRun={latestRun}
              lastRunPollAt={lastRunPollAt}
              runPollError={runPollError}
              scenarioDrafts={scenarioDrafts}
              approvedScenarioId={approvedScenarioId}
              orchestrator={orchestrator}
              createScenarioDrafts={createScenarioDrafts}
              approveScenario={approveScenario}
              generate={generate}
              onRefreshRun={() => void pollLatestRun(true)}
              onCancelRun={cancelRun}
              busy={busy}
            />
          )}

          {view === "dashboard" && (
            <DashboardPanel
              dataStatus={dataStatus}
              intelligence={intelligence}
              latestRun={latestRun}
              lastRunPollAt={lastRunPollAt}
              runPollError={runPollError}
              learning={learning}
              onView={selectView}
              onRefreshRun={() => void pollLatestRun(true)}
              onCancelRun={cancelRun}
            />
          )}

          {view === "brands" && (
            <BrandEditorPanel
              draft={companyDraft}
              setDraft={setCompanyDraft}
              activeCompany={activeCompany}
              onCreate={createCompanyDraft}
              dataBusy={dataBusy}
              saveCompanyDraft={saveCompanyDraft}
            />
          )}

          {view === "avatars" && (
            <AvatarEditorPanel
              draft={avatarDraft}
              setDraft={setAvatarDraft}
              imageFile={avatarImageFile}
              setImageFile={setAvatarImageFile}
              activeAvatar={activeAvatar}
              consent={form.avatar_own_person_consent}
              onConsentChange={(value) => update("avatar_own_person_consent", value)}
              onCreate={createAvatarDraft}
              dataBusy={dataBusy}
              saveAvatarDraft={saveAvatarDraft}
            />
          )}

          {view === "creatives" && selectedCreative && (
            <CreativeDetailPanel
              creative={selectedCreative}
              dataBusy={dataBusy}
              onRate={rateCreative}
              onSavePerformance={savePerformance}
            />
          )}

          {view === "creatives" && !selectedCreative && <CreativeEmptyPanel creatives={creatives} />}

          {view === "prompt-lab" && (
            <PromptLabPanel settings={promptSettings} providerCapabilities={providerCapabilities} applyPromptDefaults={applyPromptDefaults} />
          )}

          {view === "analytics" && <AnalyticsPanel learning={learning} intelligence={intelligence} />}

          {view === "costs" && <CostMonitorPanel runs={generationRuns} latestRun={latestRun} />}

          {view === "settings" && (
            <SettingsPanel form={form} update={update} dataStatus={dataStatus} providerCapabilities={providerCapabilities} settings={promptSettings} />
          )}
          </div>
        </aside>
      </div>
    </main>
  );
}

function AgentCockpit(props: {
  form: CampaignForm;
  status: string;
  busy: boolean;
  activeCompany?: Company;
  orchestrator: OrchestratorSnapshot | null;
  productFile: File | null;
  staticProductFiles: File[];
  scenarioDrafts: ScenarioDraft[];
  approvedScenarioId: string;
}) {
  const hasBrief = Boolean(props.form.product_info || props.form.product_reference_url || props.productFile || props.staticProductFiles.length);
  const hasBrand = Boolean(props.form.company_id || props.form.brand_context);
  const hasReference = props.form.generation_mode === "static" || isVideoReadyProductReference(props.form.product_reference_url);
  const hasApprovedScenario = Boolean(props.approvedScenarioId || props.form.ugc_video_extra_prompt.trim());
  const statusLabel = props.busy ? "Working" : hasApprovedScenario ? "Ready" : props.scenarioDrafts.length ? "Review" : hasBrief ? "Planning" : "Listening";
  const mission = props.form.product_name || firstLine(props.form.product_info) || "New ads mission";
  const activeOrchestrator = isActionableOrchestrator(props.orchestrator) ? props.orchestrator : null;
  const steps =
    orchestratorWorkflowSteps(activeOrchestrator) ||
    agentCockpitSteps({ hasBrief, hasBrand, hasReference, scenarioCount: props.scenarioDrafts.length, hasApprovedScenario, busy: props.busy });
  const planSpecialists = props.orchestrator?.phases.find((phase) => phase.id === "plan")?.specialists || [];
  const visiblePlanSkills = planSpecialists.map((specialist) => specialist.label).slice(0, 3).join(" + ") || "UGC + static skills";

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.5fr)]">
      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b px-4 py-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant="secondary">Orchestrator</Badge>
              <Badge variant={props.busy ? "default" : "outline"}>{statusLabel}</Badge>
              {props.activeCompany?.name && <Badge variant="outline">{props.activeCompany.name}</Badge>}
            </div>
            <h2 className="truncate text-xl font-semibold">{mission}</h2>
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{activeOrchestrator?.next_action || props.status}</p>
          </div>
          <div className="grid min-w-[210px] grid-cols-2 gap-2 text-xs">
            <AgentMetric label="Output" value={modeLabel(props.form.generation_mode)} />
            <AgentMetric label="Channel" value={props.form.platform || "meta"} />
            <AgentMetric label="Market" value={props.form.market || "UK"} />
            <AgentMetric label="Static" value={props.form.max_static_images || "8"} />
          </div>
        </div>
        <div className="space-y-3 p-4">
          <div className="grid gap-2 md:grid-cols-5">
            {steps.map((step) => (
              <div key={step.id} className={cn("min-h-24 rounded-md border p-3", agentStepClass(step.state))}>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{step.title}</span>
                  {step.state === "done" ? <Check className="h-4 w-4 text-emerald-700" /> : <span className="h-2 w-2 rounded-full bg-current opacity-35" />}
                </div>
                <p className="line-clamp-3 text-xs leading-5 text-muted-foreground">{step.detail}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            <AgentSignal icon={<ShieldCheck className="h-4 w-4" />} label="Quality guard" value={hasBrand ? "Brand rules loaded" : "Waiting"} />
            <AgentSignal icon={<GitBranch className="h-4 w-4" />} label="Specialists" value={visiblePlanSkills} />
            <AgentSignal icon={<Images className="h-4 w-4" />} label="Assets" value={`${props.staticProductFiles.length + (props.productFile ? 1 : 0)} refs`} />
          </div>
        </div>
      </section>
      <AgentVoiceVisualizer busy={props.busy} />
    </div>
  );
}

function AgentMetric(props: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-slate-50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">{props.label}</p>
      <p className="truncate font-semibold">{props.value}</p>
    </div>
  );
}

function AgentSignal(props: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex min-h-14 items-center gap-2 rounded-md border bg-slate-50 px-3 py-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-[#116b5d]">{props.icon}</div>
      <div className="min-w-0">
        <p className="text-xs font-semibold">{props.label}</p>
        <p className="truncate text-xs text-muted-foreground">{props.value}</p>
      </div>
    </div>
  );
}

function AgentVoiceVisualizer(props: { busy: boolean }) {
  const [mode, setMode] = useState<AgentVoiceMode>("idle");
  const effectiveMode = props.busy ? "speaking" : mode;
  const active = effectiveMode !== "idle";
  const bars = [22, 36, 54, 30, 62, 46, 28, 58, 34, 48, 26, 40];

  return (
    <Card className="border-slate-200 bg-[#101820] text-white">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base">Voice agent</CardTitle>
            <CardDescription className="text-white/60">{voiceModeLabel(effectiveMode)}</CardDescription>
          </div>
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-md", active ? "bg-emerald-400 text-emerald-950" : "bg-white/10")}>
            {effectiveMode === "speaking" ? <Volume2 className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex h-24 items-center justify-center gap-1 rounded-md bg-white/5 px-4">
          {bars.map((height, index) => (
            <span
              key={`${height}-${index}`}
              className={cn("w-2 rounded-full bg-emerald-300 transition-all", active && "animate-pulse")}
              style={{
                height: `${active ? height : Math.max(10, height * 0.35)}px`,
                animationDelay: `${index * 70}ms`,
              }}
            />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[
            ["idle", "Idle"],
            ["listening", "Listen"],
            ["speaking", "Talk"],
          ].map(([value, label]) => (
            <Button
              key={value}
              type="button"
              size="sm"
              variant={effectiveMode === value ? "secondary" : "ghost"}
              className={cn("text-xs", effectiveMode !== value && "text-white hover:bg-white/10 hover:text-white")}
              onClick={() => setMode(value as AgentVoiceMode)}
            >
              {label}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function agentCockpitSteps(input: {
  hasBrief: boolean;
  hasBrand: boolean;
  hasReference: boolean;
  scenarioCount: number;
  hasApprovedScenario: boolean;
  busy: boolean;
}): ChatWorkflowStep[] {
  return [
    {
      id: "brief",
      title: "Brief",
      detail: input.hasBrief ? "Mission context loaded" : "Waiting for mission",
      state: input.hasBrief ? "done" : "active",
    },
    {
      id: "strategy",
      title: "Strategy",
      detail: input.hasBrand && input.hasBrief ? "Angle and claim boundaries ready" : "Needs brand and mission context",
      state: input.hasBrand && input.hasBrief ? "done" : input.hasBrief ? "active" : "waiting",
    },
    {
      id: "plan",
      title: "Creative Plan",
      detail: input.hasApprovedScenario ? "Approved direction" : input.scenarioCount ? `${input.scenarioCount} variants` : "UGC and static concepts not drafted",
      state: input.hasApprovedScenario ? "done" : input.scenarioCount ? "active" : input.hasBrief ? "waiting" : "waiting",
    },
    {
      id: "generate",
      title: "Generate",
      detail: input.busy ? "Generating assets" : input.hasReference ? "Provider-ready" : "Needs direct visual URL",
      state: input.busy ? "active" : input.hasReference ? (input.hasApprovedScenario ? "active" : "waiting") : input.hasBrief ? "blocked" : "waiting",
    },
    {
      id: "review",
      title: "Review",
      detail: "Quality review and learning after generation",
      state: "waiting",
    },
  ];
}

function orchestratorWorkflowSteps(orchestrator: OrchestratorSnapshot | null): ChatWorkflowStep[] | null {
  if (!orchestrator?.phases?.length) return null;
  if (!isActionableOrchestrator(orchestrator)) return null;
  return orchestrator.phases.map((phase) => ({
    id: phase.id,
    title: phase.title,
    detail: phase.purpose || phase.user_gate || "",
    state: normalizeStepState(phase.status),
    meta: (phase.specialists || []).map((specialist) => specialist.label).slice(0, 2).join(" + "),
  }));
}

function isActionableOrchestrator(orchestrator: OrchestratorSnapshot | null): orchestrator is OrchestratorSnapshot {
  if (!orchestrator) return false;
  return !["idle", "completed"].includes(String(orchestrator.run_status || "").toLowerCase());
}

function normalizeStepState(value: string | undefined): ChatWorkflowStepState {
  if (value === "done" || value === "active" || value === "blocked" || value === "waiting") return value;
  return "waiting";
}

function agentStepClass(state: ChatWorkflowStepState) {
  if (state === "done") return "border-emerald-200 bg-emerald-50 text-emerald-950";
  if (state === "active") return "border-blue-200 bg-blue-50 text-blue-950";
  if (state === "blocked") return "border-amber-300 bg-amber-50 text-amber-950";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function voiceModeLabel(mode: AgentVoiceMode) {
  if (mode === "listening") return "Nasloucha briefu";
  if (mode === "speaking") return "Mluvi k procesu";
  return "Pripraven";
}

function ChatWorkspace(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  items: ChatItem[];
  draft: string;
  pendingFiles: File[];
  productFile: File | null;
  staticProductFiles: File[];
  scenarioDrafts: ScenarioDraft[];
  approvedScenarioId: string;
  scenarioMessageId: string;
  chatResultRun: Record<string, unknown> | null;
  dragActive: boolean;
  status: string;
  busy: boolean;
  activeCompany?: Company;
  orchestrator: OrchestratorSnapshot | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  setDraft: (value: string) => void;
  setPendingFiles: React.Dispatch<React.SetStateAction<File[]>>;
  setProductFile: (file: File | null) => void;
  setStaticProductFiles: React.Dispatch<React.SetStateAction<File[]>>;
  onPaste: (event: ClipboardEvent<HTMLTextAreaElement>) => void;
  onDrop: (event: DragEvent<HTMLDivElement>) => void;
  onDragActive: (active: boolean) => void;
  appendFiles: (files: FileList | File[] | null | undefined) => void;
  addItem: () => void;
  createScenarioDrafts: () => void;
  approveScenario: (draftId: string) => void;
  generate: () => void;
  onNewChat: () => void;
  applyItem: (item: ChatItem, role: ApplyRole) => void;
}) {
  const timelineEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [props.items.length, props.scenarioDrafts.length, props.approvedScenarioId, props.scenarioMessageId, props.chatResultRun]);

  return (
    <div
      className={cn("flex min-h-0 flex-1 flex-col overflow-hidden bg-[#eef1f4] px-3 py-4 md:px-5", props.dragActive && "bg-teal-50")}
      onDragOver={(event) => {
        event.preventDefault();
        props.onDragActive(true);
      }}
      onDragLeave={() => props.onDragActive(false)}
      onDrop={props.onDrop}
    >
      <div className="mx-auto flex h-full min-h-0 w-full max-w-7xl flex-col gap-4">
        <AgentCockpit
          form={props.form}
          status={props.status}
          busy={props.busy}
          activeCompany={props.activeCompany}
          orchestrator={props.orchestrator}
          productFile={props.productFile}
          staticProductFiles={props.staticProductFiles}
          scenarioDrafts={props.scenarioDrafts}
          approvedScenarioId={props.approvedScenarioId}
        />

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex shrink-0 flex-col gap-3 border-b bg-white px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">Agent chat</Badge>
                <Badge variant={props.busy ? "default" : "outline"}>{props.busy ? "working" : "ready"}</Badge>
                <span className="text-xs text-muted-foreground">{props.items.length} messages</span>
              </div>
              <p className="mt-1 truncate text-sm font-medium">
                {props.form.product_name || firstLine(props.form.product_info) || "New creative mission"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={props.onNewChat} disabled={props.busy}>
                <MessageSquare className="h-4 w-4" />
                New
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={props.createScenarioDrafts} disabled={props.busy}>
                <FlaskConical className="h-4 w-4" />
                Plan
              </Button>
              <Button type="button" size="sm" onClick={props.generate} disabled={props.busy}>
                {props.busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
                Generate
              </Button>
            </div>
          </div>

      <div
            className="chat-scroll min-h-0 flex-1 overflow-y-auto bg-[#fbfcfd] px-4 py-5"
      >
            <div className="mx-auto flex max-w-4xl flex-col gap-4">
          <AnimatePresence initial={false}>
            {props.items.map((item) => (
              <Fragment key={item.id}>
                <motion.article
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.18 }}
                      className={cn("flex gap-3", item.role === "user" && "flex-row-reverse")}
                >
                  <div
                    className={cn(
                          "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border shadow-sm",
                          item.role === "assistant" ? "border-[#101820] bg-[#101820] text-white" : "border-slate-200 bg-white",
                    )}
                  >
                    {item.role === "assistant" ? <Bot className="h-4 w-4" /> : <UserRound className="h-4 w-4" />}
                  </div>

                  <div
                    className={cn(
                          "max-w-[88%] rounded-lg border bg-white p-3 text-sm shadow-sm md:max-w-[78%]",
                          item.role === "user" && "border-teal-200 bg-[#e8f7f4]",
                    )}
                  >
                    <p className="whitespace-pre-wrap break-words leading-6">{item.text || "Obrazkova priloha"}</p>
                    {!!item.urls.length && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.urls.map((url) => (
                          <code key={url} className="max-w-full break-all rounded bg-muted px-2 py-1 text-xs">
                            {url}
                          </code>
                        ))}
                      </div>
                    )}
                    {!!item.files.length && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {item.files.map((file) => (
                          <Badge key={`${item.id}-${file.name}-${file.size}`} variant="secondary">
                            {file.name}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {item.role === "user" && (
                      <div className="mt-3 flex flex-wrap gap-2">
                            <Chip onClick={() => props.applyItem(item, "product")} icon={<Boxes className="h-3 w-3" />}>
                          Ad brief
                        </Chip>
                        <Chip onClick={() => props.applyItem(item, "competitor")} icon={<BriefcaseBusiness className="h-3 w-3" />}>
                          Konkurence
                        </Chip>
                        <Chip onClick={() => props.applyItem(item, "avatar")} icon={<UserRound className="h-3 w-3" />}>
                          Avatar
                        </Chip>
                        <Chip onClick={() => props.applyItem(item, "direction")} icon={<Wand2 className="h-3 w-3" />}>
                          Rezie
                        </Chip>
                      </div>
                    )}
                    {!!item.applied_as.length && (
                      <p className="mt-2 text-xs text-emerald-700">Pouzito: {item.applied_as.join(", ")}</p>
                    )}
                  </div>
                </motion.article>
                {item.id === props.scenarioMessageId && !!props.scenarioDrafts.length && (
                  <ChatScenarioApprovalCard
                    scenarioDrafts={props.scenarioDrafts}
                    approvedScenarioId={props.approvedScenarioId}
                    busy={props.busy}
                    onApproveScenario={props.approveScenario}
                  />
                )}
              </Fragment>
            ))}
          </AnimatePresence>
          {!props.scenarioMessageId && !!props.scenarioDrafts.length && (
            <ChatScenarioApprovalCard
              scenarioDrafts={props.scenarioDrafts}
              approvedScenarioId={props.approvedScenarioId}
              busy={props.busy}
              onApproveScenario={props.approveScenario}
            />
          )}
          {props.chatResultRun && (
            <ChatGeneratedResultCard run={props.chatResultRun} onNewChat={props.onNewChat} />
          )}
          <div ref={timelineEndRef} />
        </div>
      </div>

          <footer className="shrink-0 border-t bg-white px-4 py-3">
            <div className="mx-auto max-w-4xl">
          {!!props.pendingFiles.length && (
            <div className="mb-2 flex flex-wrap gap-2">
              {props.pendingFiles.map((file, index) => (
                <Badge key={`${file.name}-${index}`} variant="secondary">
                  {file.name}
                  <button
                    className="ml-2 inline-flex"
                    onClick={() => props.setPendingFiles((current) => current.filter((_, i) => i !== index))}
                    type="button"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}

              <div className="rounded-lg border border-slate-200 bg-white p-2 shadow-sm">
            <Textarea
              value={props.draft}
              onChange={(event) => props.setDraft(event.target.value)}
              onPaste={props.onPaste}
                  placeholder="Napis agentovi produkt, sluzbu, cil, URL, konkurenci, avatar nebo kreativni smer..."
              className="min-h-20 resize-none border-0 shadow-none focus-visible:ring-0"
            />
            <ChatGenerationQuickControls form={props.form} update={props.update} />
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex min-w-0 items-center gap-2">
                <input
                  ref={props.fileInputRef}
                  hidden
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={(event) => props.appendFiles(event.target.files)}
                />
                <Button type="button" variant="ghost" size="sm" onClick={() => props.fileInputRef.current?.click()}>
                  <Paperclip className="h-4 w-4" />
                  Prilozit
                </Button>
                <span className="truncate text-xs text-muted-foreground">{props.status}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button type="button" onClick={props.addItem} disabled={props.busy || (!props.draft.trim() && !props.pendingFiles.length)}>
                  <Send className="h-4 w-4" />
                  Pridat
                </Button>
                <Button type="button" variant="secondary" onClick={props.createScenarioDrafts} disabled={props.busy}>
                  <FlaskConical className="h-4 w-4" />
                  Scenare
                </Button>
                <Button type="button" onClick={props.generate} disabled={props.busy}>
                  {props.busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
                  Generate
                </Button>
              </div>
            </div>
          </div>
            </div>
          </footer>
        </section>
      </div>
    </div>
  );
}

function ChatGenerationQuickControls(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
}) {
  const videoEnabled = props.form.generation_mode !== "static";
  const staticEnabled = props.form.generation_mode !== "video";
  const modes: Array<{ value: CampaignForm["generation_mode"]; label: string; icon: ReactNode }> = [
    { value: "both", label: "Oboje", icon: <Sparkles className="h-3.5 w-3.5" /> },
    { value: "video", label: "Video", icon: <Video className="h-3.5 w-3.5" /> },
    { value: "static", label: "Statiky", icon: <Images className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="mb-1 flex flex-wrap items-center gap-1.5 border-t px-1 pt-2">
      <div className="inline-flex h-8 items-center rounded-md border bg-slate-50 p-0.5">
        {modes.map((mode) => {
          const active = props.form.generation_mode === mode.value;
          return (
            <button
              key={mode.value}
              type="button"
              onClick={() => props.update("generation_mode", mode.value)}
              className={cn(
                "inline-flex h-7 items-center gap-1 rounded px-2 text-xs text-muted-foreground transition",
                active && "bg-white text-emerald-950 shadow-sm",
              )}
              title={mode.value === "both" ? "Generovat video i statiky" : mode.value === "video" ? "Generovat jen video" : "Generovat jen staticke obrazky"}
            >
              {mode.icon}
              {mode.label}
            </button>
          );
        })}
      </div>

      {videoEnabled && (
        <label className="inline-flex h-8 items-center gap-1 rounded-md border bg-slate-50 px-2 text-xs text-muted-foreground" title="Delka UGC videa">
          <Video className="h-3.5 w-3.5" />
          <Input
            type="number"
            min={5}
            max={60}
            step={1}
            value={props.form.video_length}
            onChange={(event) => props.update("video_length", event.target.value)}
            className="h-6 w-10 border-0 bg-transparent px-0 py-0 text-center text-xs text-foreground shadow-none focus-visible:ring-0"
          />
          s
        </label>
      )}

      {staticEnabled && (
        <label className="inline-flex h-8 items-center gap-1 rounded-md border bg-slate-50 px-2 text-xs text-muted-foreground" title="Pocet statickych obrazku">
          <Images className="h-3.5 w-3.5" />
          <Input
            type="number"
            min={1}
            max={20}
            step={1}
            value={props.form.max_static_images}
            onChange={(event) => props.update("max_static_images", event.target.value)}
            className="h-6 w-10 border-0 bg-transparent px-0 py-0 text-center text-xs text-foreground shadow-none focus-visible:ring-0"
          />
          ks
        </label>
      )}
    </div>
  );
}

function ChatWorkflowCard(props: {
  form: CampaignForm;
  steps: ChatWorkflowStep[];
  scenarioDrafts: ScenarioDraft[];
  approvedScenarioId: string;
  busy: boolean;
  onCreateScenarioDrafts: () => void;
  onApproveScenario: (draftId: string) => void;
  onGenerate: () => void;
  compact?: boolean;
}) {
  const approvedScenario = props.scenarioDrafts.find((scenario) => scenario.id === props.approvedScenarioId);
  const hasApprovedPlan = Boolean(approvedScenario || props.form.ugc_video_extra_prompt.trim());
  const hasScenarioDrafts = props.scenarioDrafts.length > 0;
  const generateDisabled = props.busy || !hasApprovedPlan;
  const outputLabel = modeLabel(props.form.generation_mode);

  return (
    <Card className={cn("border-emerald-200 bg-white shadow-sm", props.compact && "mb-3")}>
      <CardHeader className={cn("pb-3", props.compact && "p-3 pb-2")}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <GitBranch className="h-4 w-4" />
              Agent workflow
            </CardTitle>
            <CardDescription>
              {outputLabel} / {props.form.language || "jazyk"} / {props.form.market || "trh"}
            </CardDescription>
          </div>
          <div className={cn("flex flex-wrap gap-2", props.compact && "w-full")}>
            <Button type="button" variant="secondary" size="sm" className={props.compact ? "flex-1" : undefined} onClick={props.onCreateScenarioDrafts} disabled={props.busy}>
              <FlaskConical className="h-4 w-4" />
              Scenare
            </Button>
            <Button type="button" size="sm" className={props.compact ? "flex-1" : undefined} onClick={props.onGenerate} disabled={generateDisabled}>
              {props.busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
              Generate
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className={cn("space-y-4", props.compact && "p-3 pt-0")}>
        <div className={cn("grid gap-2", !props.compact && "md:grid-cols-5")}>
          {props.steps.map((step) => (
            <div key={step.id} className={cn("rounded-lg border p-3", chatWorkflowStepClass(step.state))}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold">{step.title}</span>
                {step.state === "done" && <Check className="h-4 w-4 text-emerald-700" />}
                {step.state === "active" && <Loader2 className="h-4 w-4 animate-spin text-emerald-700" />}
                {step.state === "blocked" && <X className="h-4 w-4 text-amber-700" />}
                {step.state === "waiting" && <span className="h-2 w-2 rounded-full bg-slate-300" />}
              </div>
              <p className="mt-2 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{step.detail}</p>
              {!!step.meta && <p className="mt-2 truncate font-mono text-[10px] text-slate-500">{step.meta}</p>}
            </div>
          ))}
        </div>

        {!!props.scenarioDrafts.length && (
          <div className="grid gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold">Scenare ke schvaleni</p>
              {approvedScenario && <Badge variant="secondary">Schvaleno: {approvedScenario.title}</Badge>}
            </div>
            <div className="grid gap-3">
              {props.scenarioDrafts.map((scenario) => {
                const approved = scenario.id === props.approvedScenarioId;
                return (
                  <div key={scenario.id} className={cn("rounded-lg border bg-white p-3", approved && "border-emerald-600 ring-2 ring-emerald-100")}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold">{scenario.title}</p>
                        <p className="text-xs text-muted-foreground">{scenario.angle}</p>
                      </div>
                      <Button type="button" size="sm" variant={approved ? "secondary" : "outline"} onClick={() => props.onApproveScenario(scenario.id)}>
                        <Check className="h-4 w-4" />
                        {approved ? "Schvaleno" : "Schvalit"}
                      </Button>
                    </div>
                    <div className={cn("mt-3 grid gap-2 text-sm leading-6", !props.compact && "md:grid-cols-[1fr_1fr]")}>
                      <div className="rounded-md bg-emerald-50 px-3 py-2">
                        <p className="text-[11px] font-semibold uppercase tracking-normal text-emerald-900">Hook</p>
                        <p>{scenario.hook}</p>
                      </div>
                      <div className="rounded-md bg-slate-50 px-3 py-2">
                        <p className="text-[11px] font-semibold uppercase tracking-normal text-slate-600">CTA</p>
                        <p>{scenario.cta}</p>
                      </div>
                    </div>
                    <p className={cn("mt-3 whitespace-pre-wrap rounded-md border bg-slate-50 px-3 py-2 text-sm leading-6", props.compact && "max-h-40 overflow-y-auto")}>{scenario.script}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {scenario.visualPlan.map((item) => (
                        <Badge key={`${scenario.id}-${item}`} variant="outline">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {!props.scenarioDrafts.length && (
          <div className="rounded-lg border border-dashed bg-slate-50 px-3 py-3 text-sm text-muted-foreground">
            Scenare se objevi v agent timeline pred generovanim. Po schvaleni se vybrany scenar propise do rezie kampane.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ChatScenarioApprovalCard(props: {
  scenarioDrafts: ScenarioDraft[];
  approvedScenarioId: string;
  busy: boolean;
  onApproveScenario: (draftId: string) => void;
}) {
  const approvedScenario = props.scenarioDrafts.find((scenario) => scenario.id === props.approvedScenarioId);

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="flex gap-3"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-emerald-950 bg-emerald-950 text-white">
        <FlaskConical className="h-4 w-4" />
      </div>
      <Card className="max-w-[92%] flex-1 border-emerald-200 bg-white shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-base">Scenare ke schvaleni</CardTitle>
              <CardDescription>Vyber jednu variantu, ktera se propise do rezie pro generovani.</CardDescription>
            </div>
            {approvedScenario && <Badge variant="secondary">Schvaleno: {approvedScenario.title}</Badge>}
          </div>
        </CardHeader>
        <CardContent className="grid gap-3">
          {props.scenarioDrafts.map((scenario) => {
            const approved = scenario.id === props.approvedScenarioId;
            return (
              <div key={scenario.id} className={cn("rounded-lg border bg-white p-3", approved && "border-emerald-600 ring-2 ring-emerald-100")}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">{scenario.title}</p>
                    <p className="text-xs text-muted-foreground">{scenario.angle}</p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant={approved ? "secondary" : "outline"}
                    onClick={() => props.onApproveScenario(scenario.id)}
                    disabled={props.busy}
                  >
                    <Check className="h-4 w-4" />
                    {approved ? "Schvaleno" : "Schvalit"}
                  </Button>
                </div>
                <div className="mt-3 grid gap-2 text-sm leading-6 md:grid-cols-[1fr_1fr]">
                  <div className="rounded-md bg-emerald-50 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-normal text-emerald-900">Hook</p>
                    <p>{scenario.hook}</p>
                  </div>
                  <div className="rounded-md bg-slate-50 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-normal text-slate-600">CTA</p>
                    <p>{scenario.cta}</p>
                  </div>
                </div>
                <p className="mt-3 whitespace-pre-wrap rounded-md border bg-slate-50 px-3 py-2 text-sm leading-6">{scenario.script}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {scenario.visualPlan.map((item) => (
                    <Badge key={`${scenario.id}-${item}`} variant="outline">
                      {item}
                    </Badge>
                  ))}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </motion.article>
  );
}

function ChatGeneratedResultCard(props: {
  run: Record<string, unknown>;
  onNewChat: () => void;
}) {
  const assets = generatedRunAssets(props.run);
  const problem = generationRunProblem(props.run);
  const productName = productNameFromRun(props.run) || "Generated campaign";
  const runId = String(props.run.run_id || "");
  const costSummary = costSummaryFromRun(props.run);
  const hasAssets = assets.images.length > 0 || assets.videos.length > 0;

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="flex gap-3"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-emerald-950 bg-emerald-950 text-white">
        <Sparkles className="h-4 w-4" />
      </div>
      <Card className="max-w-[92%] flex-1 border-emerald-200 bg-white shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="flex items-center gap-2 text-base">
                {problem ? <X className="h-4 w-4 text-destructive" /> : <Check className="h-4 w-4 text-emerald-700" />}
                {problem ? "Castecny vystup" : "Vygenerovany obsah"}
              </CardTitle>
              <CardDescription className="truncate">
                {productName} / {runId || "current agent run"}
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{assets.videoCount} video</Badge>
              <Badge variant="secondary">{assets.imageCount} statik</Badge>
              <Badge variant="outline">Cost {costDisplay(costSummary)}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!hasAssets && (
            <div className="rounded-lg border border-dashed bg-slate-50 px-3 py-3 text-sm text-muted-foreground">
              Run je hotovy, ale v ulozenych vystupech zatim nevidim media soubory. Detail zustava v pravem panelu a Creative sets.
            </div>
          )}

          {!!assets.videos.length && (
            <div className="grid gap-3">
              {assets.videos.map((asset, index) => {
                const url = mediaUrl(asset.url);
                return (
                  <div key={`${asset.url}-${index}`} className="overflow-hidden rounded-lg border bg-black">
                    <video src={url} controls className="aspect-[9/16] max-h-[520px] w-full bg-black object-contain" />
                    <div className="flex flex-wrap items-center justify-between gap-2 bg-white px-3 py-2 text-xs">
                      <span className="truncate font-medium">{asset.name || "UGC video"}</span>
                      <a href={url} target="_blank" rel="noreferrer" className="text-emerald-800 hover:underline">
                        Otevrit video
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!!assets.images.length && (
            <div className="grid gap-2 sm:grid-cols-2">
              {assets.images.map((asset, index) => {
                const url = mediaUrl(asset.url);
                return (
                  <a
                    key={`${asset.url}-${index}`}
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="group overflow-hidden rounded-lg border bg-slate-50"
                  >
                    <img src={url} alt={asset.name || "Generated static image"} className="aspect-square w-full object-cover transition group-hover:scale-[1.02]" />
                    <div className="px-3 py-2 text-xs">
                      <p className="truncate font-medium">{asset.name || "Static image"}</p>
                      {!!asset.meta && <p className="mt-1 line-clamp-2 text-muted-foreground">{asset.meta}</p>}
                    </div>
                  </a>
                );
              })}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-emerald-50/70 px-3 py-3">
            <p className="text-sm text-emerald-950">
              {problem ? "Cast vystupu je dostupna. Problem je vypsany v agent timeline." : "Hotovo. Pro dalsi variantu zacni novy agent run."}
            </p>
            <Button type="button" onClick={props.onNewChat}>
              <MessageSquare className="h-4 w-4" />
              Novy run
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.article>
  );
}

function DashboardWorkspace(props: {
  intelligence: IntelligenceSummary | null;
  learning: LearningSnapshot | null;
  latestRun: Record<string, unknown> | null;
  lastRunPollAt: string;
  runPollError: string;
  creatives: Creative[];
  onView: (view: AppView) => void;
  onRefreshRun: () => void;
  onCancelRun: () => void;
}) {
  const counts = props.intelligence?.counts || {};

  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-5xl gap-4">
        <GenerationMonitorCard
          run={props.latestRun}
          lastPollAt={props.lastRunPollAt}
          pollError={props.runPollError}
          onRefresh={props.onRefreshRun}
          onCancel={props.onCancelRun}
        />

        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label="Products" value={counts.products ?? 0} meta="memory" />
          <MetricCard label="Campaigns" value={counts.campaigns ?? 0} meta="runs" />
          <MetricCard label="Creatives" value={counts.creatives ?? props.creatives.length} meta="assets" />
          <MetricCard label="Ratings" value={counts.ratings ?? 0} meta="learning" />
        </div>

        <div className="grid gap-2 md:grid-cols-[1fr_220px]">
          <Card>
            <CardHeader>
              <CardTitle>Learning recommendation</CardTitle>
              <CardDescription>Used as directional bias for the next run</CardDescription>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-muted-foreground">
              {String(props.learning?.recommendation || "Creative memory is ready to bias the next generation when enough ratings exist.")}
            </CardContent>
          </Card>
          <div className="grid gap-2">
            <Button onClick={() => props.onView("chat")}>
              <MessageSquare className="h-4 w-4" />
              Orchestrator
            </Button>
            <Button variant="secondary" onClick={() => props.onView("creatives")}>
              <Library className="h-4 w-4" />
              Review creatives
            </Button>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Best angles</CardTitle>
              <CardDescription>Directional signal, not automatic winner selection</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {(props.intelligence?.best_performing_angles || []).slice(0, 8).map((item, index) => (
                <SignalRow
                  key={`${String(item.angle)}-${index}`}
                  label={String(item.angle || "angle")}
                  value={`${String(item.count || 0)} assets`}
                  meta={item.avg_rating ? `${Number(item.avg_rating).toFixed(1)}/5` : "no score"}
                />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent creatives</CardTitle>
              <CardDescription>Last memory records</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {props.creatives.slice(0, 8).map((creative) => (
                <button
                  key={creative.creative_id}
                  type="button"
                  onClick={() => props.onView("creatives")}
                  className="flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2 text-left text-sm hover:bg-muted"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{creative.product_name || "Creative"}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {creative.type || "type"} / {creative.angle || "angle"}
                    </span>
                  </span>
                  <Badge variant="outline">{creative.latest_rating_status || creative.status || "new"}</Badge>
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </WorkspaceScroll>
  );
}

function GenerationMonitorCard(props: {
  run: Record<string, unknown> | null;
  lastPollAt: string;
  pollError: string;
  onRefresh: () => void;
  onCancel: () => void;
  compact?: boolean;
}) {
  const monitor = readRecord(props.run?.monitor);
  const status = String(monitor?.status || props.run?.status || "missing");
  const statusLabel = String(monitor?.status_label || props.run?.status || "No run loaded");
  const stageLabel = String(monitor?.stage_label || props.run?.current_stage || "Waiting");
  const progress = clampProgress(monitor?.progress_percent);
  const active = isRunActive(props.run);
  const canCancel = canCancelRun(props.run);
  const latestMessage = String(monitor?.latest_message || "");
  const terminalReason = String(monitor?.terminal_reason || props.run?.last_error || props.run?.error || "");
  const nextStep = String(monitor?.next_step || "");
  const blockers = recordList(monitor?.blockers);
  const costSummary = costSummaryFromRun(props.run);
  const runId = String(props.run?.run_id || "");
  const latestStage = readRecord(monitor?.latest_stage);
  const updatedAt = String(latestStage?.updated_at || props.lastPollAt || "");
  const outputPlan = generationOutputPlanFromRun(props.run);
  const partialOutputs = readRecord(props.run?.partial_outputs) || readRecord(monitor?.partial_outputs) || {};
  const headline = latestMessage || terminalReason || nextStep || (active ? "Generation is running." : "No active generation right now.");
  const statusIcon = active ? (
    <Loader2 className="h-4 w-4 animate-spin text-emerald-700" />
  ) : status === "completed" ? (
    <Check className="h-4 w-4 text-emerald-700" />
  ) : status === "blocked" || status === "failed" ? (
    <X className="h-4 w-4 text-destructive" />
  ) : (
    <RefreshCw className="h-4 w-4 text-muted-foreground" />
  );

  return (
    <Card className={cn("mb-3 overflow-hidden", monitorCardTone(props.run), props.compact ? "" : "border-2")}>
      <CardHeader className={cn("gap-0", props.compact && "p-3 pb-2")}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2">
              {statusIcon}
              Generation monitor
            </CardTitle>
            <CardDescription className="truncate">{runId || "Latest backend run"}</CardDescription>
          </div>
          <Badge variant={active ? "secondary" : status === "blocked" || status === "failed" ? "outline" : "muted"}>{statusLabel}</Badge>
        </div>
      </CardHeader>
      <CardContent className={cn("space-y-3", props.compact && "p-3 pt-0")}>
        <div className="flex flex-wrap gap-2">
          <Badge variant={outputPlan.video.enabled && outputPlan.staticImages.enabled ? "secondary" : "outline"}>{outputPlan.label}</Badge>
          <Badge variant="secondary">Cost {costDisplay(costSummary)}</Badge>
          <Badge variant="muted">{String(costSummary?.request_count || 0)} requests</Badge>
          {!!Number(costSummary?.unknown_request_count || 0) && <Badge variant="outline">{String(costSummary?.unknown_request_count)} unknown cost</Badge>}
        </div>

        <GenerationOutputPlan plan={outputPlan} compact={props.compact} />
        {active && <GenerationPartialOutputs outputs={partialOutputs} compact={props.compact} />}

        <div>
          <div className="mb-1 flex items-center justify-between gap-3 text-xs">
            <span className="truncate font-medium">{stageLabel}</span>
            <span className="font-semibold">{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div className={cn("h-full rounded-full transition-all", active ? "bg-emerald-700" : "bg-primary")} style={{ width: `${progress}%` }} />
          </div>
        </div>

        <p className={cn("break-words text-sm leading-6", terminalReason ? "text-foreground" : "text-muted-foreground")}>{headline}</p>

        {!!nextStep && nextStep !== headline && (
          <div className="rounded-md border bg-white/70 px-3 py-2 text-xs leading-5 text-muted-foreground">
            <span className="font-semibold text-foreground">Next step: </span>
            {nextStep}
          </div>
        )}

        {!!blockers.length && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-destructive">Blockers</p>
            {blockers.slice(0, props.compact ? 2 : 4).map((blocker, index) => (
              <div key={`${String(blocker.source || "blocker")}-${index}`} className="rounded-md border bg-white/80 px-3 py-2 text-xs leading-5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{String(blocker.source || "provider")}</span>
                  <Badge variant="muted">{String(blocker.id || "failed")}</Badge>
                </div>
                <p className="mt-1 break-words text-muted-foreground">{String(blocker.reason || "Unknown reason")}</p>
              </div>
            ))}
          </div>
        )}

        {props.pollError && <p className="break-words text-xs text-destructive">{props.pollError}</p>}

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span className="text-xs text-muted-foreground">{updatedAt ? `Updated ${updatedAt}` : "Waiting for backend status"}</span>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="outline" onClick={props.onRefresh}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
            <Button
              type="button"
              size="sm"
              variant={canCancel ? "destructive" : "outline"}
              onClick={props.onCancel}
              disabled={!canCancel}
              title={canCancel ? "Zrusit aktivni generation run" : "Zruseni je dostupne jen kdyz run aktivne bezi"}
            >
              <X className="h-4 w-4" />
              Zrusit generovani
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function GenerationOutputPlan(props: {
  plan: GenerationOutputPlanInfo;
  compact?: boolean;
}) {
  return (
    <div className={cn("grid gap-2", props.compact ? "" : "sm:grid-cols-2")}>
      <OutputBranchCard branch={props.plan.video} icon={<Video className="h-4 w-4" />} compact={props.compact} />
      <OutputBranchCard branch={props.plan.staticImages} icon={<Images className="h-4 w-4" />} compact={props.compact} />
    </div>
  );
}

function GenerationPartialOutputs(props: {
  outputs: Record<string, unknown>;
  compact?: boolean;
}) {
  const images = recordList(props.outputs.images);
  const videos = recordList(props.outputs.videos);
  const imageCount = numberOrNull(props.outputs.image_count) ?? images.length;
  const videoCount = numberOrNull(props.outputs.video_count) ?? videos.length;
  const latest = String(props.outputs.latest_asset_updated_at || "");
  if (!imageCount && !videoCount) return null;

  return (
    <div className="rounded-md border border-emerald-200 bg-white/75 px-3 py-2">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold text-emerald-950">Prubezne vystupy</span>
        <div className="flex flex-wrap gap-2">
          {!!videoCount && <Badge variant="secondary">{videoCount} video</Badge>}
          {!!imageCount && <Badge variant="secondary">{imageCount} statik</Badge>}
        </div>
      </div>
      {!!images.length && (
        <div className={cn("grid gap-2", props.compact ? "grid-cols-3" : "grid-cols-4 sm:grid-cols-6")}>
          {images.slice(0, props.compact ? 3 : 6).map((asset, index) => {
            const url = mediaUrl(String(asset.url || ""));
            return (
              <a
                key={`${String(asset.name || "image")}-${index}`}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="block aspect-square overflow-hidden rounded-md border bg-muted"
                title={String(asset.name || "generated image")}
              >
                <img src={url} alt={String(asset.name || "Generated static image")} className="h-full w-full object-cover" />
              </a>
            );
          })}
        </div>
      )}
      {!!videos.length && !props.compact && (
        <div className="mt-2 flex flex-wrap gap-2">
          {videos.slice(0, 3).map((asset, index) => (
            <a
              key={`${String(asset.name || "video")}-${index}`}
              href={mediaUrl(String(asset.url || ""))}
              target="_blank"
              rel="noreferrer"
              className="rounded-md border bg-white px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
            >
              {String(asset.name || "video")}
            </a>
          ))}
        </div>
      )}
      {!!latest && <p className="mt-2 truncate text-xs text-muted-foreground">Posledni soubor {latest}</p>}
    </div>
  );
}

function OutputBranchCard(props: {
  branch: GenerationOutputBranch;
  icon: ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-md border bg-white/80 px-3 py-2",
        props.branch.enabled ? "border-emerald-200" : "border-muted bg-muted/30",
        outputBranchTone(props.branch.state),
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={cn("rounded-md border bg-white p-1", props.branch.enabled ? "text-emerald-800" : "text-muted-foreground")}>{props.icon}</span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">{props.branch.title}</span>
            <span className="block truncate text-xs text-muted-foreground">{props.branch.detail}</span>
          </span>
        </div>
        <Badge variant={props.branch.enabled ? "secondary" : "muted"}>{props.branch.badge}</Badge>
      </div>
      {!props.compact && props.branch.meta && <p className="mt-2 truncate text-xs text-muted-foreground">{props.branch.meta}</p>}
    </div>
  );
}

function AvatarWorkspace(props: {
  avatars: Avatar[];
  activeAvatarId: string;
  onSelect: (avatar: Avatar) => void;
  onCreate: () => void;
  onEdit: (avatar: Partial<Avatar>) => void;
  onMakeDefault: (avatar: Avatar) => void;
}) {
  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-5xl gap-4">
        <Card className="border-emerald-200 bg-emerald-50/40">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Avatar library</CardTitle>
                <CardDescription>Vytvor novy AI avatar nebo uprav existujici referenci pro UGC video.</CardDescription>
              </div>
              <Button onClick={props.onCreate}>
                <UserRound className="h-4 w-4" />
                New avatar
              </Button>
            </div>
          </CardHeader>
        </Card>

        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          <button
            type="button"
            onClick={props.onCreate}
            className="flex min-h-72 flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-white p-6 text-center transition hover:border-emerald-800 hover:bg-emerald-50/40"
          >
            <span className="rounded-full bg-emerald-100 p-3 text-emerald-900">
              <UserRound className="h-7 w-7" />
            </span>
            <span className="text-sm font-semibold">Create new avatar</span>
            <span className="max-w-64 text-xs leading-5 text-muted-foreground">
              Zalozi cisty draft s novym ID, personou, voice a volitelnym image uploadem.
            </span>
          </button>

          {props.avatars.map((avatar) => {
            const stats = avatar.stats || {};
            const active = props.activeAvatarId === avatar.id;
            return (
              <Card key={avatar.id} className={cn(active && "border-emerald-800 ring-1 ring-emerald-800")}>
                <CardHeader>
                  <div className="flex items-start gap-3">
                    <AvatarPreview avatar={avatar} size="lg" />
                    <div className="min-w-0 flex-1">
                      <CardTitle className="truncate">{avatar.name || avatar.id}</CardTitle>
                      <CardDescription className="truncate">{avatar.id}</CardDescription>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {avatar.is_default && <Badge>Default</Badge>}
                        {active && <Badge variant="secondary">Active</Badge>}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">{avatar.style || "No persona yet."}</p>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <MiniStat label="Creatives" value={numberish(stats.creative_count)} />
                    <MiniStat label="Videos" value={numberish(stats.video_count)} />
                    <MiniStat label="Rating" value={stats.avg_rating ? Number(stats.avg_rating).toFixed(1) : "-"} />
                  </div>
                  <div className="flex gap-2">
                    <Button className="flex-1" size="sm" onClick={() => props.onSelect(avatar)}>
                      <Check className="h-4 w-4" />
                      Use
                    </Button>
                    <Button className="flex-1" size="sm" variant="secondary" onClick={() => props.onEdit(avatar)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => props.onMakeDefault(avatar)}>
                      <Star className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </WorkspaceScroll>
  );
}

function BrandWorkspace(props: {
  companies: Company[];
  activeCompanyId: string;
  onSelect: (company: Company) => void;
  onCreate: () => void;
  onEdit: (company: Partial<Company>) => void;
  onMakeDefault: (company: Company) => void;
}) {
  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-5xl gap-4">
        <Card className="border-emerald-200 bg-emerald-50/40">
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Brand library</CardTitle>
                <CardDescription>Uloz brand, trh, voice a pravidla pro kvalitni ads kreativy.</CardDescription>
              </div>
              <Button onClick={props.onCreate}>
                <BriefcaseBusiness className="h-4 w-4" />
                New brand
              </Button>
            </div>
          </CardHeader>
        </Card>

        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          <button
            type="button"
            onClick={props.onCreate}
            className="flex min-h-72 flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-white p-6 text-center transition hover:border-emerald-800 hover:bg-emerald-50/40"
          >
            <span className="rounded-full bg-emerald-100 p-3 text-emerald-900">
              <BriefcaseBusiness className="h-7 w-7" />
            </span>
            <span className="text-sm font-semibold">Create brand context</span>
            <span className="max-w-64 text-xs leading-5 text-muted-foreground">
              Jednou nastav trh, brand voice, zakazane claimy a pravidla kreativ. Pak je pouzijes pro kazdou reklamu.
            </span>
          </button>

          {props.companies.map((company) => {
            const active = props.activeCompanyId === company.id;
            return (
              <Card key={company.id} className={cn(active && "border-emerald-800 ring-1 ring-emerald-800")}>
                <CardHeader>
                  <div className="flex items-start gap-3">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border bg-emerald-950 text-white">
                      <BriefcaseBusiness className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <CardTitle className="truncate">{company.name || company.id}</CardTitle>
                      <CardDescription className="truncate">{company.id}</CardDescription>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {company.is_default && <Badge>Default</Badge>}
                        {active && <Badge variant="secondary">Active</Badge>}
                        {company.ad_vertical && <Badge variant="outline">{company.ad_vertical}</Badge>}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">{company.positioning || company.audience || "No brand context yet."}</p>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <MiniStat label="Market" value={company.market || "-"} />
                    <MiniStat label="Lang" value={company.language || "-"} />
                    <MiniStat label="Channel" value={company.default_platform || "-"} />
                  </div>
                  <div className="flex gap-2">
                    <Button className="flex-1" size="sm" onClick={() => props.onSelect(company)}>
                      <Check className="h-4 w-4" />
                      Use
                    </Button>
                    <Button className="flex-1" size="sm" variant="secondary" onClick={() => props.onEdit(company)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => props.onMakeDefault(company)}>
                      <Star className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </WorkspaceScroll>
  );
}

function CreativeWorkspace(props: {
  creatives: Creative[];
  selectedCreativeId: string;
  onSelect: (creativeId: string) => void;
  onRate: (creative: Creative, status: CreativeRatingStatus, feedback?: CreativeRatingFeedback) => void;
}) {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [rejectDrafts, setRejectDrafts] = useState<Record<string, RejectDraft>>({});
  const reviewable = props.creatives.filter((creative) => !isNonReviewableCreative(creative));
  const hidden = props.creatives.filter(isNonReviewableCreative);
  const approved = reviewable.filter((creative) => creative.latest_rating_status === "approved");
  const rejected = reviewable.filter((creative) => creative.latest_rating_status === "rejected");
  const needsReview = reviewable.filter((creative) => !creative.latest_rating_status);
  const filtered = props.creatives.filter((creative) => {
    const nonReviewable = isNonReviewableCreative(creative);
    const rating = String(creative.latest_rating_status || "").toLowerCase();
    if (statusFilter === "reviewable" && nonReviewable) return false;
    if (statusFilter === "needs_review" && (nonReviewable || rating)) return false;
    if (statusFilter === "approved" && (nonReviewable || rating !== "approved")) return false;
    if (statusFilter === "rejected" && (nonReviewable || rating !== "rejected")) return false;
    if (statusFilter === "hidden" && !nonReviewable) return false;
    const haystack = `${creative.product_name} ${creative.creative_id} ${creative.angle} ${creative.type} ${creative.status} ${creative.latest_rating_status}`.toLowerCase();
    if (query && !haystack.includes(query.toLowerCase())) return false;
    if (type !== "all" && creative.type !== type) return false;
    return true;
  });
  const updateRejectDraft = (creativeId: string, patch: Partial<RejectDraft>) => {
    setRejectDrafts((current) => ({
      ...current,
      [creativeId]: { ...rejectDraftFor(current, creativeId), ...patch },
    }));
  };
  const submitReject = (creative: Creative) => {
    const draft = rejectDraftFor(rejectDrafts, creative.creative_id);
    props.onRate(creative, "rejected", { comment: draft.comment, reasons: draft.reasons });
    updateRejectDraft(creative.creative_id, { open: false, comment: "", reasons: [] });
  };

  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-[1600px] gap-4">
        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label="Review queue" value={needsReview.length} meta="failed/skipped hidden" />
          <MetricCard label="Approved" value={approved.length} meta="ready to reuse" />
          <MetricCard label="Rejected" value={rejected.length} meta="learning signal" />
          <MetricCard label="Hidden" value={hidden.length} meta="not in review" />
        </div>

        <div className="grid gap-2 rounded-lg border bg-white p-3 lg:grid-cols-[minmax(0,1fr)_180px_190px] lg:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input value={query} onChange={(event) => setQuery(event.target.value)} className="pl-9" placeholder="Search product, angle, ID..." />
          </div>
          <Select
            value={type}
            onChange={(event) => setType(event.target.value)}
            options={[
              { value: "all", label: "All assets" },
              { value: "video", label: "Video" },
              { value: "static_image", label: "Static image" },
              { value: "carousel_card", label: "Carousel" },
            ]}
          />
          <Select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            options={[
              { value: "all", label: "All statuses" },
              { value: "reviewable", label: "Reviewable only" },
              { value: "needs_review", label: "Needs review" },
              { value: "approved", label: "Approved" },
              { value: "rejected", label: "Rejected" },
              { value: "hidden", label: "Hidden failed/skipped" },
            ]}
          />
        </div>
        <div className="rounded-lg border bg-white px-3 py-2 text-xs leading-5 text-muted-foreground">
          Showing {filtered.length} of {props.creatives.length} creative-memory rows. {reviewable.length} have generated media for review;
          {hidden.length ? ` ${hidden.length} skipped, blocked, failed or empty rows stay visible as placeholders.` : " no hidden rows are present."}
        </div>

        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {filtered.map((creative) => {
            const nonReviewable = isNonReviewableCreative(creative);
            const selected = creative.creative_id === props.selectedCreativeId;
            const rejectDraft = rejectDraftFor(rejectDrafts, creative.creative_id);
            return (
              <Card
                key={creative.creative_id}
                className={cn(selected && "border-emerald-800 ring-1 ring-emerald-800", nonReviewable && "border-dashed bg-muted/40 opacity-80")}
              >
                <button
                  type="button"
                  onClick={() => props.onSelect(creative.creative_id)}
                  className="block w-full text-left"
                >
                  <CreativePreview creative={creative} />
                </button>
                <CardHeader>
                  <CardTitle className="truncate">{creative.product_name || "Creative"}</CardTitle>
                  <CardDescription className="truncate">{creative.creative_id}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">{creative.type || "type"}</Badge>
                    <Badge variant="secondary">{creative.angle || "angle"}</Badge>
                    <Badge variant={creative.latest_rating_status === "approved" ? "default" : "muted"}>
                      {creative.latest_rating_status || creative.status || "new"}
                    </Badge>
                    {nonReviewable && <Badge variant="outline">not reviewable</Badge>}
                  </div>
                  <KeyValueRows
                    rows={[
                      ["Market", `${creative.platform || "-"} / ${creative.market || "-"}`],
                      ["Rating", creative.latest_user_rating ? `${creative.latest_user_rating}/5` : "-"],
                      ["ROAS", creative.latest_roas ? String(creative.latest_roas) : "-"],
                    ]}
                  />
                  {nonReviewable ? (
                    <div className="rounded-md border bg-white/70 px-3 py-2 text-xs leading-5 text-muted-foreground">
                      {creativeUnavailableLabel(creative)}
                    </div>
                  ) : (
                    <>
                      {rejectDraft.open && (
                        <RejectFeedbackEditor
                          value={rejectDraft}
                          onChange={(patch) => updateRejectDraft(creative.creative_id, patch)}
                          compact
                        />
                      )}
                      <div className="flex gap-2">
                        <Button className="flex-1" size="sm" variant="secondary" onClick={() => props.onRate(creative, "approved")}>
                          <ThumbsUp className="h-4 w-4" />
                          Approve
                        </Button>
                        <Button
                          className="flex-1"
                          size="sm"
                          variant={rejectDraft.open ? "destructive" : "outline"}
                          onClick={() => (rejectDraft.open ? submitReject(creative) : updateRejectDraft(creative.creative_id, { open: true }))}
                        >
                          <ThumbsDown className="h-4 w-4" />
                          {rejectDraft.open ? "Save reject" : "Reject"}
                        </Button>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {!filtered.length && (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No creative assets match this view. Switch the status filter to All statuses to include skipped, blocked and empty rows.
            </CardContent>
          </Card>
        )}
      </div>
    </WorkspaceScroll>
  );
}

function PromptLabWorkspace(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  settings: PromptSettings | null;
  applyPromptDefaults: () => void;
}) {
  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-5xl gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>Content system prompt</CardTitle>
                <CardDescription>Globalni pravidla pro marketing, UGC a product fidelity</CardDescription>
              </div>
              <Button variant="secondary" size="sm" onClick={props.applyPromptDefaults}>
                <Wand2 className="h-4 w-4" />
                Load defaults
              </Button>
            </div>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Textarea
              value={props.form.content_prompt_system}
              onChange={(event) => props.update("content_prompt_system", event.target.value)}
              className="min-h-40"
              placeholder={props.settings?.content_prompt_system || "System prompt"}
            />
            <Textarea
              value={props.form.content_prompt_task}
              onChange={(event) => props.update("content_prompt_task", event.target.value)}
              className="min-h-32"
              placeholder={props.settings?.content_prompt_task || "Task prompt"}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Video prompt template</CardTitle>
            <CardDescription>UGC scene structure, avatar behavior and product proof</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Textarea
              value={props.form.base_video_prompt_template}
              onChange={(event) => props.update("base_video_prompt_template", event.target.value)}
              className="min-h-40"
              placeholder={props.settings?.base_video_prompt_template || "Base video prompt template"}
            />
            <Textarea
              value={props.form.ugc_video_extra_prompt}
              onChange={(event) => props.update("ugc_video_extra_prompt", event.target.value)}
              className="min-h-28"
              placeholder="Extra creative direction"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Negative prompt</CardTitle>
            <CardDescription>Safety, hand quality, text stability and product consistency constraints</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              value={props.form.negative_prompt}
              onChange={(event) => props.update("negative_prompt", event.target.value)}
              className="min-h-40"
              placeholder={props.settings?.negative_prompt || "Negative prompt"}
            />
          </CardContent>
        </Card>
      </div>
    </WorkspaceScroll>
  );
}

function AnalyticsWorkspace(props: { intelligence: IntelligenceSummary | null; learning: LearningSnapshot | null; creatives: Creative[] }) {
  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-5xl gap-4">
        <Card>
          <CardHeader>
            <CardTitle>RAG learning status</CardTitle>
            <CardDescription>{props.learning?.status || "loading"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm leading-6 text-muted-foreground">{props.learning?.recommendation || "No learning recommendation loaded."}</p>
            <TagCloud title="Prefer" tags={props.learning?.next_generation_bias?.prefer || props.learning?.winning_patterns || []} />
            <TagCloud title="Avoid" tags={props.learning?.next_generation_bias?.avoid || props.learning?.avoid_patterns || []} />
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Best hooks</CardTitle>
              <CardDescription>Patterns extracted from approved assets</CardDescription>
            </CardHeader>
            <CardContent>
              <TagCloud tags={props.intelligence?.best_hooks || []} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Performance leaders</CardTitle>
              <CardDescription>Creatives with performance records</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {(props.intelligence?.performance_leaders || props.creatives.filter((creative) => Number(creative.performance_count || 0) > 0))
                .slice(0, 8)
                .map((creative) => (
                  <SignalRow
                    key={creative.creative_id}
                    label={creative.product_name || creative.creative_id}
                    value={`ROAS ${creative.latest_roas || "-"}`}
                    meta={creative.angle || creative.type || ""}
                  />
                ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </WorkspaceScroll>
  );
}

function CostMonitorWorkspace(props: {
  runs: Array<Record<string, unknown>>;
  latestRun: Record<string, unknown> | null;
  onViewRun: (run: Record<string, unknown>) => void;
}) {
  const totals = costTotals(props.runs);
  const selectedId = String(props.latestRun?.run_id || "");
  const sortedRuns = props.runs.slice(0, 120);

  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-6xl gap-4">
        <div className="grid gap-3 md:grid-cols-4">
          <MetricCard label="Known spend" value={formatUsd(totals.known)} meta="OpenRouter reported" />
          <MetricCard label="Runs" value={props.runs.length} meta="stored generation runs" />
          <MetricCard label="Avg/run" value={formatUsd(totals.average)} meta="known cost only" />
          <MetricCard label="Unknown cost" value={totals.unknownRequests} meta="requests missing price" />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Cost monitor</CardTitle>
            <CardDescription>Run-level cost ledger for pricing, credits and future monetization.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {sortedRuns.map((run) => {
              const summary = costSummaryFromRun(run);
              const runId = String(run.run_id || "");
              const selected = runId && runId === selectedId;
              return (
                <button
                  key={runId || String(run.updated_at)}
                  type="button"
                  onClick={() => props.onViewRun(run)}
                  className={cn(
                    "grid w-full gap-2 rounded-md border px-3 py-3 text-left text-sm transition-colors hover:bg-muted md:grid-cols-[minmax(0,1.5fr)_110px_110px_110px_120px]",
                    selected && "border-emerald-800 ring-1 ring-emerald-800",
                  )}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{productNameFromRun(run) || runId || "Generation run"}</span>
                    <span className="block truncate text-xs text-muted-foreground">{runId}</span>
                  </span>
                  <span>
                    <span className="block text-xs text-muted-foreground">Status</span>
                    <Badge variant={String(run.status) === "completed" ? "secondary" : "outline"}>{String(run.status || "-")}</Badge>
                  </span>
                  <span>
                    <span className="block text-xs text-muted-foreground">Cost</span>
                    <span className="font-semibold">{costDisplay(summary)}</span>
                  </span>
                  <span>
                    <span className="block text-xs text-muted-foreground">Requests</span>
                    <span className="font-semibold">{String(summary?.request_count || 0)}</span>
                  </span>
                  <span>
                    <span className="block text-xs text-muted-foreground">Updated</span>
                    <span className="text-xs">{shortDate(run.updated_at)}</span>
                  </span>
                </button>
              );
            })}
            {!sortedRuns.length && <p className="py-8 text-center text-sm text-muted-foreground">No generation runs found yet.</p>}
          </CardContent>
        </Card>
      </div>
    </WorkspaceScroll>
  );
}

function SettingsWorkspace(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  avatarOptions: Array<{ value: string; label: string }>;
  providerCapabilities: Record<string, unknown> | null;
  settings: PromptSettings | null;
}) {
  return (
    <WorkspaceScroll>
      <div className="mx-auto grid max-w-6xl gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Campaign defaults</CardTitle>
            <CardDescription>Stejna pole se posilaji do `/generation-runs`</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <FieldSelect label="Avatar" value={props.form.avatar_id} onChange={(value) => props.update("avatar_id", value)} options={props.avatarOptions} />
            {settingRows.map((row) => (
              <FieldSelect
                key={row.key}
                label={row.label}
                value={props.form[row.key]}
                onChange={(value) => props.update(row.key, value)}
                options={row.options}
              />
            ))}
            <FieldSelect
              label="Vystup"
              value={props.form.generation_mode}
              onChange={(value) => props.update("generation_mode", value as CampaignForm["generation_mode"])}
              options={[
                { value: "both", label: "Video + statiky" },
                { value: "video", label: "Jen video" },
                { value: "static", label: "Jen statiky" },
              ]}
            />
            <FieldNumberInput
              label="UGC video length"
              value={props.form.video_length}
              onChange={(value) => props.update("video_length", value)}
              min={5}
              max={60}
              suffix="s"
            />
            <FieldNumberInput
              label="Static images"
              value={props.form.max_static_images}
              onChange={(value) => props.update("max_static_images", value)}
              min={1}
              max={20}
            />
            <FieldInput label="Image size" value={props.form.image_size} onChange={(value) => props.update("image_size", value)} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Models</CardTitle>
            <CardDescription>OpenRouter providers used by backend</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <FieldModelInput
              label="Prompt model"
              value={props.form.prompt_model}
              onChange={(value) => props.update("prompt_model", value)}
              options={promptModelOptions}
              hint="Pouziva se pro parser, product understanding, static prompt enhancer a self-critique."
            />
            <FieldModelInput
              label="UGC scenario model"
              value={props.form.ugc_scenario_model}
              onChange={(value) => props.update("ugc_scenario_model", value)}
              options={promptModelOptions}
              hint="Pouziva se pro prepis UGC scenare do prirozene mluvne reci pred video promptem."
            />
            <FieldModelInput
              label="Static scenario model"
              value={props.form.static_prompt_model}
              onChange={(value) => props.update("static_prompt_model", value)}
              options={promptModelOptions}
              hint="Pouziva se pro navrh statickych obrazkovych scenaru, hooku, overlay textu a promptu. Default je ChatGPT/GPT."
            />
            <FieldModelInput
              label="Image model"
              value={props.form.image_model}
              onChange={(value) => props.update("image_model", value)}
              options={imageModelOptions}
              hint="Pouziva se pro staticke obrazky pres image output."
            />
            <FieldModelInput
              label="Video model"
              value={props.form.seedance_model}
              onChange={(value) => props.update("seedance_model", value)}
              options={videoModelOptions}
              hint="Veo je video model pro OpenRouter /videos, ne staticky image model."
            />
            <FieldInput label="OpenRouter API key" value={props.form.openrouter_api_key} onChange={(value) => props.update("openrouter_api_key", value)} />
          </CardContent>
        </Card>

        <AgentWorkflowDiagram
          form={props.form}
          update={props.update}
          settings={props.settings}
          providerCapabilities={props.providerCapabilities}
        />
      </div>
    </WorkspaceScroll>
  );
}

function AgentWorkflowDiagram(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  settings: PromptSettings | null;
  providerCapabilities: Record<string, unknown> | null;
}) {
  const nodes = useMemo(() => buildWorkflowNodes(props.settings), [props.settings]);
  const [selectedId, setSelectedId] = useState("ugc_scenario_writer");
  const [graphOpen, setGraphOpen] = useState(false);
  const selected = nodes.find((node) => node.id === selectedId) || nodes[0];
  const edges = useMemo(() => buildWorkflowEdges(nodes), [nodes]);
  const connectedIds = useMemo(() => connectedNodeIds(nodes, selected?.id || ""), [nodes, selected?.id]);
  const guardrails = workflowGuardrails(props.settings);

  useEffect(() => {
    if (selected && nodes.some((node) => node.id === selected.id)) return;
    setSelectedId(nodes[0]?.id || "");
  }, [nodes, selected]);

  if (!selected) return null;

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Workflow map
              </CardTitle>
              <CardDescription>Samostatne velke graph okno pro agenty, modely a vazby v backendu.</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{nodes.length} agentu</Badge>
              <Badge variant="outline">{edges.length} vazeb</Badge>
              <Badge variant="outline">{guardrails.length} guardrails</Badge>
              <Button type="button" size="sm" onClick={() => setGraphOpen(true)}>
                <GitBranch className="h-4 w-4" />
                Open graph window
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-2 md:grid-cols-4">
            {(["prompt_model", "ugc_scenario_model", "image_model", "seedance_model"] as WorkflowModelKey[]).map((key) => {
              const target = nodes.find((node) => node.modelKey === key);
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    if (target) setSelectedId(target.id);
                    setGraphOpen(true);
                  }}
                  className="min-w-0 rounded-lg border bg-white px-3 py-2 text-left transition hover:border-foreground"
                >
                  <span className="block text-[11px] font-medium uppercase tracking-normal text-muted-foreground">{workflowModelLabel(key)}</span>
                  <span className="mt-1 block truncate font-mono text-xs text-foreground">{String(props.form[key] || "")}</span>
                </button>
              );
            })}
          </div>

          <div className="rounded-lg border bg-slate-50 p-4">
            <div className="grid gap-2 md:grid-cols-6">
              {workflowStageOrder.map((stage) => (
                <button
                  key={stage}
                  type="button"
                  onClick={() => {
                    const firstStageNode = nodes.find((node) => node.stage === stage);
                    if (firstStageNode) setSelectedId(firstStageNode.id);
                    setGraphOpen(true);
                  }}
                  className="rounded-lg border bg-white px-3 py-3 text-left transition hover:border-slate-900"
                >
                  <span className="block text-xs font-semibold">{stage}</span>
                  <span className="mt-1 block text-[11px] text-muted-foreground">{nodes.filter((node) => node.stage === stage).length} nodes</span>
                </button>
              ))}
            </div>
            <Button type="button" className="mt-4 w-full" onClick={() => setGraphOpen(true)}>
              <GitBranch className="h-4 w-4" />
              Open large workflow graph
            </Button>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {graphOpen && (
          <motion.div
            className="fixed inset-0 z-50 bg-slate-950/45 p-3 backdrop-blur-sm sm:p-5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="mx-auto flex h-full max-w-[1900px] flex-col overflow-hidden rounded-xl border bg-white shadow-2xl"
              initial={{ scale: 0.98, y: 12 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.98, y: 12 }}
            >
              <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
                <div>
                  <p className="text-sm font-semibold">Workflow graph</p>
                  <p className="text-xs text-muted-foreground">Velke samostatne okno bez praveho panelu. Tahni prazdne misto pro posun, zoom ovladas tlacitky nebo Ctrl + kolecko.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{nodes.length} agentu</Badge>
                  <Badge variant="outline">{edges.length} vazeb</Badge>
                  <Button type="button" variant="outline" size="sm" onClick={() => setGraphOpen(false)}>
                    <X className="h-4 w-4" />
                    Close
                  </Button>
                </div>
              </div>
              <div className="grid min-h-0 flex-1 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_390px]">
                <WorkflowGraphCanvas
                  nodes={nodes}
                  edges={edges}
                  selectedId={selected.id}
                  activeIds={connectedIds}
                  form={props.form}
                  onSelectNode={setSelectedId}
                  large
                />
                <WorkflowNodeDetail
                  node={selected}
                  nodes={nodes}
                  form={props.form}
                  update={props.update}
                  providerCapabilities={props.providerCapabilities}
                  onSelectNode={setSelectedId}
                  className="min-h-0 overflow-y-auto"
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </>
  );
}

function WorkflowGraphCanvas(props: {
  nodes: WorkflowNode[];
  edges: Array<{ from: string; to: string }>;
  selectedId: string;
  activeIds: Set<string>;
  form: CampaignForm;
  onSelectNode: (id: string) => void;
  large?: boolean;
}) {
  const nodeById = useMemo(() => new Map(props.nodes.map((node) => [node.id, node])), [props.nodes]);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const panStartRef = useRef<{ pointerId: number; x: number; y: number; panX: number; panY: number } | null>(null);
  const [zoom, setZoom] = useState(() => (props.large ? 0.78 : 0.62));
  const [pan, setPan] = useState(() => ({ x: props.large ? 30 : 18, y: props.large ? 28 : 18 }));
  const [isPanning, setIsPanning] = useState(false);

  const changeZoom = useCallback((delta: number) => {
    setZoom((current) => clampWorkflowZoom(current + delta));
  }, []);

  const resetView = useCallback(() => {
    setZoom(props.large ? 0.78 : 0.62);
    setPan({ x: props.large ? 30 : 18, y: props.large ? 28 : 18 });
  }, [props.large]);

  const fitView = useCallback(() => {
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) return;
    const padding = props.large ? 72 : 40;
    const nextZoom = clampWorkflowZoom(
      Math.min(
        (rect.width - padding) / workflowGraphCanvasWidth,
        (rect.height - padding) / workflowGraphCanvasHeight,
      ),
    );
    setZoom(nextZoom);
    setPan({
      x: Math.max(16, (rect.width - workflowGraphCanvasWidth * nextZoom) / 2),
      y: Math.max(16, (rect.height - workflowGraphCanvasHeight * nextZoom) / 2),
    });
  }, [props.large]);

  const handleWheel = useCallback((event: WheelEvent<HTMLDivElement>) => {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    changeZoom(event.deltaY > 0 ? -0.08 : 0.08);
  }, [changeZoom]);

  const handlePointerDown = useCallback((event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    const target = event.target as Element | null;
    if (target?.closest("[data-workflow-node]")) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    panStartRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      panX: pan.x,
      panY: pan.y,
    };
    setIsPanning(true);
  }, [pan.x, pan.y]);

  const handlePointerMove = useCallback((event: PointerEvent<HTMLDivElement>) => {
    const start = panStartRef.current;
    if (!start || start.pointerId !== event.pointerId) return;
    setPan({
      x: start.panX + event.clientX - start.x,
      y: start.panY + event.clientY - start.y,
    });
  }, []);

  const finishPanning = useCallback((event: PointerEvent<HTMLDivElement>) => {
    const start = panStartRef.current;
    if (!start || start.pointerId !== event.pointerId) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    panStartRef.current = null;
    setIsPanning(false);
  }, []);

  return (
    <div className={cn("rounded-lg border bg-slate-50 p-3", props.large && "flex min-h-0 flex-col")}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold">Agent graph</p>
          <p className="text-[11px] text-muted-foreground">Tahni prazdne misto pro posun. Ctrl + kolecko nebo tlacitka meni zoom.</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="flex items-center gap-1 rounded-lg border bg-white p-1 shadow-sm">
            <Button type="button" variant="ghost" size="sm" className="h-8 w-8 px-0" title="Zoom out" onClick={() => changeZoom(-0.1)}>
              <ZoomOut className="h-4 w-4" />
            </Button>
            <span className="min-w-12 text-center font-mono text-[11px] text-slate-600">{Math.round(zoom * 100)}%</span>
            <Button type="button" variant="ghost" size="sm" className="h-8 w-8 px-0" title="Zoom in" onClick={() => changeZoom(0.1)}>
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button type="button" variant="ghost" size="sm" title="Fit graph" onClick={fitView}>
              Fit
            </Button>
            <Button type="button" variant="ghost" size="sm" className="h-8 w-8 px-0" title="Reset view" onClick={resetView}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-1">
            {(["input", "agent", "model", "guard", "provider", "memory"] as WorkflowNodeKind[]).map((kind) => (
              <span key={kind} className="inline-flex items-center gap-1 rounded-full border bg-white px-2 py-1 text-[11px]">
                <span className={cn("h-2 w-2 rounded-full", workflowLegendDotClass(kind))} />
                {kind}
              </span>
            ))}
          </div>
        </div>
      </div>
      <div
        ref={viewportRef}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishPanning}
        onPointerCancel={finishPanning}
        onLostPointerCapture={() => {
          panStartRef.current = null;
          setIsPanning(false);
        }}
        className={cn(
          "relative overflow-hidden rounded-lg border bg-white touch-none select-none",
          props.large ? "h-full min-h-[560px]" : "h-[520px]",
          isPanning ? "cursor-grabbing" : "cursor-grab",
        )}
      >
        <div className="pointer-events-none absolute bottom-3 left-3 z-40 inline-flex items-center gap-2 rounded-lg border bg-white/90 px-2.5 py-1.5 text-[11px] text-slate-600 shadow-sm">
          <Move className="h-3.5 w-3.5" />
          Drag canvas
        </div>
        <div
          className="absolute left-0 top-0"
          style={{
            width: workflowGraphCanvasWidth,
            height: workflowGraphCanvasHeight,
            transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${zoom})`,
            transformOrigin: "0 0",
          }}
        >
          <div className="relative h-full w-full">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,rgba(15,23,42,0.10)_1px,transparent_0)] [background-size:22px_22px]" />
            {workflowGraphStageLanes.map((lane) => (
              <div
                key={lane.stage}
                className={cn("absolute bottom-3 top-3 rounded-lg border border-white/80", lane.tone)}
                style={{ left: lane.x + 8, width: lane.width - 16 }}
              >
                <div className="sticky top-2 z-20 mx-2 mt-2 rounded-md border bg-white/90 px-2 py-1 text-xs font-semibold shadow-sm">
                  {lane.stage}
                </div>
              </div>
            ))}
            <svg
              className="pointer-events-none absolute inset-0 z-10"
              width={workflowGraphCanvasWidth}
              height={workflowGraphCanvasHeight}
              viewBox={`0 0 ${workflowGraphCanvasWidth} ${workflowGraphCanvasHeight}`}
            >
              <defs>
                <marker id="workflow-arrow-muted" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="strokeWidth">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#CBD5E1" />
                </marker>
                <marker id="workflow-arrow-active" markerWidth="11" markerHeight="11" refX="9" refY="5.5" orient="auto" markerUnits="strokeWidth">
                  <path d="M 0 0 L 11 5.5 L 0 11 z" fill="#047857" />
                </marker>
              </defs>
              {props.edges.map((edge) => {
                const from = nodeById.get(edge.from);
                const to = nodeById.get(edge.to);
                if (!from || !to) return null;
                const active = props.activeIds.has(edge.from) && props.activeIds.has(edge.to);
                return (
                  <path
                    key={`${edge.from}-${edge.to}`}
                    d={workflowEdgePath(from, to)}
                    fill="none"
                    stroke={active ? "#047857" : "#CBD5E1"}
                    strokeWidth={active ? 3 : 1.5}
                    strokeOpacity={active ? 0.96 : 0.55}
                    markerEnd={active ? "url(#workflow-arrow-active)" : "url(#workflow-arrow-muted)"}
                  />
                );
              })}
            </svg>

            {props.nodes.map((node) => (
              <WorkflowGraphNode
                key={node.id}
                node={node}
                selected={node.id === props.selectedId}
                active={props.activeIds.has(node.id)}
                modelValue={workflowNodeModelValue(node, props.form)}
                onSelect={() => props.onSelectNode(node.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function WorkflowGraphNode(props: {
  node: WorkflowNode;
  selected: boolean;
  active: boolean;
  modelValue: string;
  onSelect: () => void;
}) {
  const Icon = props.node.icon;
  const position = workflowGraphPosition(props.node);
  return (
    <button
      type="button"
      data-workflow-node="true"
      onClick={props.onSelect}
      aria-pressed={props.selected}
      style={{
        left: position.x,
        top: position.y,
        width: workflowGraphNodeWidth,
        height: workflowGraphNodeHeight,
      }}
      className={cn(
        "absolute z-20 grid grid-rows-[auto_1fr_auto] rounded-lg border-2 bg-white p-3 text-left shadow-sm transition",
        workflowGraphNodeClass(props.node.kind),
        props.active && "shadow-md",
        props.selected && "scale-[1.03] border-slate-950 ring-4 ring-slate-950/10",
        !props.active && !props.selected && "opacity-75 hover:opacity-100",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className={cn("rounded-md p-1.5", workflowKindClass(props.node.kind))}>
          <Icon className="h-4 w-4" />
        </span>
        <Badge variant={props.node.modelKey ? "secondary" : props.node.readonlyModel ? "muted" : "outline"} className="px-1.5 py-0 text-[10px]">
          {props.node.modelKey ? workflowShortModelLabel(props.node.modelKey) : props.node.readonlyModel ? "config" : "rules"}
        </Badge>
      </div>
      <div className="mt-2 min-w-0">
        <p className="truncate text-xs font-semibold leading-4">{props.node.title}</p>
        <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{props.node.summary}</p>
      </div>
      <span className="mt-2 block truncate rounded-md bg-slate-100 px-2 py-1 font-mono text-[10px] text-slate-600">
        {props.modelValue || "deterministic"}
      </span>
    </button>
  );
}

function WorkflowNodeButton(props: {
  node: WorkflowNode;
  selected: boolean;
  connected: boolean;
  dimmed: boolean;
  modelValue: string;
  onSelect: () => void;
}) {
  const Icon = props.node.icon;
  return (
    <button
      type="button"
      onClick={props.onSelect}
      aria-pressed={props.selected}
      className={cn(
        "min-h-32 rounded-lg border bg-white p-3 text-left shadow-sm transition",
        props.selected && "border-foreground ring-2 ring-foreground/10",
        props.connected && !props.selected && "border-emerald-500 bg-emerald-50/70",
        props.dimmed && "opacity-60 hover:opacity-100",
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <span className={cn("rounded-md p-1.5", workflowKindClass(props.node.kind))}>
          <Icon className="h-4 w-4" />
        </span>
        <Badge variant={props.node.modelKey ? "secondary" : props.node.readonlyModel ? "muted" : "outline"}>
          {props.node.modelKey ? "model" : props.node.readonlyModel ? "config" : "rules"}
        </Badge>
      </div>
      <p className="text-xs font-semibold leading-4">{props.node.title}</p>
      <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{props.node.summary}</p>
      <span className="mt-2 block truncate rounded-md bg-muted px-2 py-1 font-mono text-[10px] text-muted-foreground">
        {props.modelValue || "deterministic"}
      </span>
    </button>
  );
}

function WorkflowNodeDetail(props: {
  node: WorkflowNode;
  nodes: WorkflowNode[];
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  providerCapabilities: Record<string, unknown> | null;
  onSelectNode: (id: string) => void;
  className?: string;
}) {
  const dependencies = props.node.dependsOn.map((id) => props.nodes.find((node) => node.id === id)).filter(Boolean) as WorkflowNode[];
  const downstream = props.nodes.filter((node) => node.dependsOn.includes(props.node.id));
  const inventory = props.node.inventory;

  return (
    <div className={cn("grid content-start gap-3 rounded-lg border bg-white p-4", props.className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{props.node.title}</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{props.node.summary}</p>
        </div>
        <Badge variant="outline">{props.node.stage}</Badge>
      </div>

      <WorkflowModelControl
        node={props.node}
        form={props.form}
        update={props.update}
        providerCapabilities={props.providerCapabilities}
      />

      <div className="grid gap-2">
        <p className="text-xs font-semibold">Inputs</p>
        <div className="flex flex-wrap gap-1">
          {dependencies.length ? (
            dependencies.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => props.onSelectNode(node.id)}
                className="rounded-full border bg-muted px-2 py-1 text-[11px] hover:border-foreground"
              >
                {node.title}
              </button>
            ))
          ) : (
            <Badge variant="muted">User input</Badge>
          )}
        </div>
      </div>

      <div className="grid gap-2">
        <p className="text-xs font-semibold">Outputs</p>
        <div className="flex flex-wrap gap-1">
          {props.node.outputs.map((item) => (
            <Badge key={item} variant="outline" className="max-w-full truncate">
              {item}
            </Badge>
          ))}
        </div>
      </div>

      <div className="grid gap-2">
        <p className="text-xs font-semibold">Editable / affected fields</p>
        <div className="flex flex-wrap gap-1">
          {props.node.fields.map((item) => (
            <Badge key={item} variant="muted" className="max-w-full truncate">
              {item}
            </Badge>
          ))}
        </div>
      </div>

      {downstream.length > 0 && (
        <div className="grid gap-2">
          <p className="text-xs font-semibold">Feeds into</p>
          <div className="flex flex-wrap gap-1">
            {downstream.map((node) => (
              <button
                key={node.id}
                type="button"
                onClick={() => props.onSelectNode(node.id)}
                className="rounded-full border bg-white px-2 py-1 text-[11px] hover:border-foreground"
              >
                {node.title}
              </button>
            ))}
          </div>
        </div>
      )}

      {inventory && (
        <div className="grid gap-2 rounded-md border bg-muted/40 p-3 text-xs leading-5">
          <p className="font-semibold">Backend inventory</p>
          <p className="text-muted-foreground">{String(inventory.backend_role || inventory.source || "")}</p>
          {Boolean(inventory.editable_in_ui) && (
            <p>
              <span className="font-medium">UI fields: </span>
              <span className="text-muted-foreground">{String(inventory.editable_in_ui)}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function WorkflowModelControl(props: {
  node: WorkflowNode;
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  providerCapabilities: Record<string, unknown> | null;
}) {
  if (!props.node.modelKey) {
    return (
      <div className="rounded-md border bg-muted/40 p-3 text-xs">
        <span className="block font-semibold">Model</span>
        <span className="mt-1 block truncate font-mono text-muted-foreground">{props.node.readonlyModel || "Deterministic backend rules"}</span>
      </div>
    );
  }
  const key = props.node.modelKey;
  return (
    <FieldModelInput
      label={workflowModelLabel(key)}
      value={String(props.form[key] || "")}
      onChange={(value) => props.update(key, value)}
      options={workflowModelOptions(key, props.providerCapabilities)}
      hint={workflowModelHint(key)}
    />
  );
}

function ProductReferenceCard(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  productFile: File | null;
  staticProductFiles: File[];
  setProductFile: (file: File | null) => void;
  setStaticProductFiles: React.Dispatch<React.SetStateAction<File[]>>;
  compact?: boolean;
}) {
  const videoMode = props.form.generation_mode !== "static";
  const hasDirectReference = isVideoReadyProductReference(props.form.product_reference_url);
  const hasUrl = Boolean(props.form.product_reference_url.trim());
  const invalidUrl = hasUrl && !hasDirectReference;
  const statusLabel = hasDirectReference ? "Video OK" : videoMode ? "Chybi pro video" : "Jen statiky";
  const statusVariant = hasDirectReference ? "secondary" : "outline";

  return (
    <Card className={cn("border-emerald-200 bg-emerald-50/35", props.compact && "mb-3")}>
      <CardHeader className={cn("pb-2", props.compact && "p-3 pb-2")}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-sm">Reference pro video</CardTitle>
            <CardDescription className="text-xs">
              Video model potrebuje verejnou direct visual URL. Lokalni upload zustava hlavne pro statiky a intake.
            </CardDescription>
          </div>
          <Badge variant={statusVariant}>{statusLabel}</Badge>
        </div>
      </CardHeader>
      <CardContent className={cn("grid gap-3", props.compact && "p-3 pt-0")}>
        <label className="grid gap-1 text-xs font-medium text-muted-foreground">
          Direct visual URL pro video
          <Input
            value={props.form.product_reference_url}
            onChange={(event) => props.update("product_reference_url", event.target.value)}
            placeholder="https://example.com/product.jpg"
          />
        </label>
        <div className={cn("grid gap-2", !props.compact && "sm:grid-cols-[1fr_auto] sm:items-end")}>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Lokalni visual reference
            <Input
              type="file"
              accept="image/*"
              onChange={(event) => props.setProductFile(event.target.files?.[0] || null)}
            />
          </label>
          {props.productFile && (
            <Button type="button" variant="ghost" size="sm" onClick={() => props.setProductFile(null)}>
              <X className="h-4 w-4" />
              Odebrat
            </Button>
          )}
        </div>
        <div className={cn("grid gap-2", !props.compact && "sm:grid-cols-[1fr_auto] sm:items-end")}>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Dalsi produktove fotky jen pro statiky / barvy
            <Input
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => props.setStaticProductFiles(Array.from(event.target.files || []).slice(0, 8))}
            />
          </label>
          {props.staticProductFiles.length > 0 && (
            <Button type="button" variant="ghost" size="sm" onClick={() => props.setStaticProductFiles([])}>
              <X className="h-4 w-4" />
              Odebrat varianty
            </Button>
          )}
        </div>
        <div className="rounded-md border bg-white/80 px-3 py-2 text-xs leading-5 text-muted-foreground">
          {hasDirectReference && "Video i statiky dostanou explicitni produktovou referenci."}
          {!hasDirectReference && videoMode && "Bez direct image URL video provider produkt neuvidi spolehlive. Vloz primo JPG/PNG/WebP/AVIF obrazek, ne produktovou stranku."}
          {!videoMode && !hasDirectReference && "Pro statiky staci lokalni upload nebo brief. Direct URL bude potreba az pro video."}
          {props.productFile && (
            <span className="block truncate font-medium text-foreground">Upload: {props.productFile.name}</span>
          )}
          {props.staticProductFiles.length > 0 && (
            <span className="block font-medium text-foreground">
              Staticke varianty: {props.staticProductFiles.map((file) => file.name).join(", ")}
            </span>
          )}
          {invalidUrl && <span className="block text-amber-700">Aktualni URL nevypada jako public direct image reference.</span>}
        </div>
      </CardContent>
    </Card>
  );
}

function CampaignPanel(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  companyOptions: Array<{ value: string; label: string }>;
  activeCompany?: Company;
  onCompanySelect: (companyId: string) => void;
  avatarOptions: Array<{ value: string; label: string }>;
  productFile: File | null;
  staticProductFiles: File[];
  setProductFile: (file: File | null) => void;
  setStaticProductFiles: React.Dispatch<React.SetStateAction<File[]>>;
  competitorFiles: File[];
  parserResult: ParserResult | null;
  runResult: Record<string, unknown> | null;
  latestRun: Record<string, unknown> | null;
  lastRunPollAt: string;
  runPollError: string;
  scenarioDrafts: ScenarioDraft[];
  approvedScenarioId: string;
  orchestrator: OrchestratorSnapshot | null;
  createScenarioDrafts: () => void;
  approveScenario: (draftId: string) => void;
  generate: () => void;
  onRefreshRun: () => void;
  onCancelRun: () => void;
  busy: boolean;
}) {
  const localProductVideoRisk = props.form.generation_mode !== "static" && !isVideoReadyProductReference(props.form.product_reference_url);
  const workflowSteps = useMemo(
    () =>
      orchestratorWorkflowSteps(props.orchestrator) ||
      chatWorkflowSteps(props.form, props.productFile, props.staticProductFiles, props.scenarioDrafts, props.approvedScenarioId),
    [props.orchestrator, props.form, props.productFile, props.staticProductFiles, props.scenarioDrafts, props.approvedScenarioId],
  );

  return (
    <>
      <div className="mb-4 rounded-lg border bg-white p-3 shadow-sm">
        <div className="flex items-center justify-between gap-3">
        <div>
            <p className="text-sm font-semibold">Mission stack</p>
            <p className="text-xs text-muted-foreground">Plan gate, references, brand, output</p>
        </div>
          <Button size="sm" onClick={props.generate} disabled={props.busy}>
          {props.busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImagePlus className="h-4 w-4" />}
          Generate
        </Button>
      </div>
      </div>

      <ChatWorkflowCard
        form={props.form}
        steps={workflowSteps}
        scenarioDrafts={props.scenarioDrafts}
        approvedScenarioId={props.approvedScenarioId}
        busy={props.busy}
        onCreateScenarioDrafts={props.createScenarioDrafts}
        onApproveScenario={props.approveScenario}
        onGenerate={props.generate}
        compact
      />

      <AvatarConsentCard
        checked={props.form.avatar_own_person_consent}
        onChange={(value) => props.update("avatar_own_person_consent", value)}
        compact
      />

      <ProductReferenceCard
        form={props.form}
        update={props.update}
        productFile={props.productFile}
        staticProductFiles={props.staticProductFiles}
        setProductFile={props.setProductFile}
        setStaticProductFiles={props.setStaticProductFiles}
        compact
      />

      {localProductVideoRisk && (
        <Card className="mb-3 border-amber-300 bg-amber-50/80">
          <CardContent className="space-y-2 p-3 text-xs leading-5">
            <div className="flex items-center gap-2">
              <Badge variant="outline">Video reference</Badge>
              <span className="font-semibold text-amber-950">UGC video potrebuje verejnou visual URL.</span>
            </div>
            <p className="text-amber-950/80">
              Lokalni upload zustane pouzitelny pro statiky, ale video provider potrebuje exact visual reference jako direct public image URL.
              Vloz primo JPG/PNG/WebP/AVIF obrazek nebo referencni vizual, ne dokumentaci nebo obecnou stranku.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="mb-4 grid gap-2">
        <FieldSelect label="Brand" value={props.form.company_id} onChange={props.onCompanySelect} options={props.companyOptions} />
        <FieldSelect label="Avatar" value={props.form.avatar_id} onChange={(value) => props.update("avatar_id", value)} options={props.avatarOptions} />
        {settingRows.map((row) => (
          <FieldSelect
            key={row.key}
            label={row.label}
            value={props.form[row.key]}
            onChange={(value) => props.update(row.key, value)}
            options={row.options}
          />
        ))}
        <FieldSelect
          label="Vystup"
          value={props.form.generation_mode}
          onChange={(value) => props.update("generation_mode", value as CampaignForm["generation_mode"])}
          options={[
            { value: "both", label: "Video + statiky" },
            { value: "video", label: "Jen video" },
            { value: "static", label: "Jen statiky" },
          ]}
        />
        <div className="grid grid-cols-2 gap-2">
          <FieldNumberInput
            label="Delka UGC videa"
            value={props.form.video_length}
            onChange={(value) => props.update("video_length", value)}
            min={5}
            max={60}
            suffix="s"
          />
          <FieldNumberInput
            label="Pocet statik"
            value={props.form.max_static_images}
            onChange={(value) => props.update("max_static_images", value)}
            min={1}
            max={20}
          />
        </div>
        <FieldModelInput
          label="Video model"
          value={props.form.seedance_model}
          onChange={(value) => props.update("seedance_model", value)}
          options={videoModelOptions}
          hint="Google Veo 3.1 Fast je dostupny pro video generovani."
        />
        <FieldModelInput
          label="Image model"
          value={props.form.image_model}
          onChange={(value) => props.update("image_model", value)}
          options={imageModelOptions}
          hint="Pro statiky nech tady image model; Veo patri do Video modelu."
        />
      </div>

      <GenerationMonitorCard
        run={props.latestRun}
        lastPollAt={props.lastRunPollAt}
        pollError={props.runPollError}
        onRefresh={props.onRefreshRun}
        onCancel={props.onCancelRun}
        compact
      />

      <BriefCard
        title="Brand context"
        rows={[
          ["Brand", props.activeCompany?.name || props.form.company_id || "ceka"],
          ["Vertical", props.form.ad_vertical || props.activeCompany?.ad_vertical || "ads"],
          ["Voice", props.activeCompany?.brand_voice || props.form.brand_context || "ceka"],
        ]}
      />
      <BriefCard
        title="Ad brief"
        rows={[
          ["Name", props.form.product_name || "ceka"],
          ["Info", props.form.product_info ? `${props.form.product_info.length} znaku` : "ceka"],
          ["Reference", props.form.product_reference_url || props.productFile?.name || "ceka"],
        ]}
      />
      <BriefCard
        title="Competitor strategy"
        rows={[
          ["Mode", props.form.competitor_strategy_enabled ? "on" : "off"],
          ["Brief", props.form.competitor_chat_brief ? `${props.form.competitor_chat_brief.length} znaku` : "ceka"],
          ["Images", String(props.competitorFiles.length)],
        ]}
      />
      <BriefCard
        title="Generation plan"
        rows={[
          ["Output", modeLabel(props.form.generation_mode)],
          ["UGC length", props.form.generation_mode === "static" ? "preskoceno" : `${props.form.video_length}s`],
          ["Static images", props.form.generation_mode === "video" ? "preskoceno" : props.form.max_static_images],
          ["Prompt model", props.form.prompt_model],
          ["Scenario model", props.form.ugc_scenario_model],
          ["Image model", props.form.generation_mode === "video" ? "preskoceno" : props.form.image_model],
          ["Video model", props.form.generation_mode === "static" ? "preskoceno" : props.form.seedance_model],
        ]}
      />

      <Card className="mb-3">
        <CardHeader>
          <CardTitle>Manual fields</CardTitle>
          <CardDescription>Rychla korekce pred odeslanim</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2">
          <Input value={props.form.product_name} onChange={(event) => props.update("product_name", event.target.value)} placeholder="Nazev produktu" />
          <Textarea value={props.form.product_info} onChange={(event) => props.update("product_info", event.target.value)} placeholder="Product notes" />
          <Textarea
            value={props.form.ugc_video_extra_prompt}
            onChange={(event) => props.update("ugc_video_extra_prompt", event.target.value)}
            placeholder="Rezie / kreativni instrukce"
          />
        </CardContent>
      </Card>

      {props.parserResult && (
        <Card className="mb-3">
          <CardHeader>
            <CardTitle>AI Brief Parser</CardTitle>
            <CardDescription>
              {props.parserResult.status} / {props.parserResult.parser_mode}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground">
            <p>Model: {props.parserResult.model}</p>
            <p>Warnings: {props.parserResult.warnings.length}</p>
            {!!props.parserResult.ai_error && <p>{props.parserResult.ai_error}</p>}
          </CardContent>
        </Card>
      )}

      {props.runResult && (
        <Card>
          <CardHeader>
            <CardTitle>Last run</CardTitle>
            <CardDescription>{String(props.runResult.status || props.runResult.run_id || "submitted")}</CardDescription>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            <code className="break-all">{String(props.runResult.run_id || "")}</code>
          </CardContent>
        </Card>
      )}
    </>
  );
}

function DashboardPanel(props: {
  dataStatus: string;
  intelligence: IntelligenceSummary | null;
  latestRun: Record<string, unknown> | null;
  lastRunPollAt: string;
  runPollError: string;
  learning: LearningSnapshot | null;
  onView: (view: AppView) => void;
  onRefreshRun: () => void;
  onCancelRun: () => void;
}) {
  return (
    <>
      <SideTitle title="Workspace status" subtitle={props.dataStatus} />
      <GenerationMonitorCard
        run={props.latestRun}
        lastPollAt={props.lastRunPollAt}
        pollError={props.runPollError}
        onRefresh={props.onRefreshRun}
        onCancel={props.onCancelRun}
        compact
      />
      <Card className="mb-3">
        <CardHeader>
          <CardTitle>Recommendation</CardTitle>
        </CardHeader>
        <CardContent className="text-sm leading-6 text-muted-foreground">{props.learning?.recommendation || "Zatim bez doporuceni."}</CardContent>
      </Card>
      <div className="grid gap-2">
        <Button onClick={() => props.onView("chat")}>Orchestrator</Button>
        <Button variant="secondary" onClick={() => props.onView("creatives")}>
          Creative review
        </Button>
      </div>
    </>
  );
}

function BrandEditorPanel(props: {
  draft: Partial<Company>;
  setDraft: React.Dispatch<React.SetStateAction<Partial<Company>>>;
  activeCompany?: Company;
  onCreate: () => void;
  dataBusy: boolean;
  saveCompanyDraft: () => void;
}) {
  const draft = props.draft.id ? props.draft : props.activeCompany || {};
  const setField = (key: keyof Company, value: string | string[]) => props.setDraft((current) => ({ ...draft, ...current, [key]: value }));
  const isNewDraft = Boolean(draft.id && draft.id !== props.activeCompany?.id);

  return (
    <>
      <SideTitle title={isNewDraft ? "New brand" : "Brand editor"} subtitle={isNewDraft ? "Ads context pro novy brand" : "Defaulty pro dalsi kampane"} />
      <Card className="mb-3">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>{isNewDraft ? "Create brand" : "Edit brand"}</CardTitle>
              <CardDescription>Tohle je pamet pro reklamy: trh, voice, pravidla a zakazane claimy.</CardDescription>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={props.onCreate}>
              <BriefcaseBusiness className="h-4 w-4" />
              New
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-2 pt-4">
          <FieldInput label="ID" value={draft.id || ""} onChange={(value) => setField("id", value)} />
          <FieldInput label="Brand name" value={draft.name || ""} onChange={(value) => setField("name", value)} />
          <FieldInput label="Ad vertical" value={draft.ad_vertical || ""} onChange={(value) => setField("ad_vertical", value)} />
          <FieldInput label="Business model" value={draft.business_model || ""} onChange={(value) => setField("business_model", value)} />
          <div className="grid grid-cols-3 gap-2">
            <FieldInput label="Market" value={draft.market || ""} onChange={(value) => setField("market", value.toUpperCase())} />
            <FieldInput label="Language" value={draft.language || ""} onChange={(value) => setField("language", value.toLowerCase())} />
            <FieldInput label="Default channel" value={draft.default_platform || ""} onChange={(value) => setField("default_platform", value.toLowerCase())} />
          </div>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Audience
            <Textarea value={draft.audience || ""} onChange={(event) => setField("audience", event.target.value)} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Positioning
            <Textarea value={draft.positioning || ""} onChange={(event) => setField("positioning", event.target.value)} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Brand voice
            <Textarea value={draft.brand_voice || ""} onChange={(event) => setField("brand_voice", event.target.value)} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Creative channels
            <Textarea value={listToLines(draft.creative_channels)} onChange={(event) => setField("creative_channels", linesToList(event.target.value))} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Categories / products handled by this brand
            <Textarea value={listToLines(draft.product_categories)} onChange={(event) => setField("product_categories", linesToList(event.target.value))} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Proof points for ads
            <Textarea value={listToLines(draft.proof_points)} onChange={(event) => setField("proof_points", linesToList(event.target.value))} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Creative quality rules
            <Textarea value={listToLines(draft.creative_quality_rules)} onChange={(event) => setField("creative_quality_rules", linesToList(event.target.value))} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Forbidden claims
            <Textarea value={listToLines(draft.forbidden_claims)} onChange={(event) => setField("forbidden_claims", linesToList(event.target.value))} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Compliance notes
            <Textarea value={draft.compliance_notes || ""} onChange={(event) => setField("compliance_notes", event.target.value)} />
          </label>
          <Button onClick={props.saveCompanyDraft} disabled={props.dataBusy}>
            {props.dataBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save brand
          </Button>
        </CardContent>
      </Card>
    </>
  );
}

function AvatarEditorPanel(props: {
  draft: Partial<Avatar>;
  setDraft: React.Dispatch<React.SetStateAction<Partial<Avatar>>>;
  imageFile: File | null;
  setImageFile: (file: File | null) => void;
  activeAvatar?: Avatar;
  consent: boolean;
  onConsentChange: (value: boolean) => void;
  onCreate: () => void;
  dataBusy: boolean;
  saveAvatarDraft: () => void;
}) {
  const draft = props.draft.id ? props.draft : props.activeAvatar || {};
  const setField = (key: keyof Avatar, value: string) => props.setDraft((current) => ({ ...draft, ...current, [key]: value }));
  const isNewDraft = Boolean(draft.id && draft.id !== props.activeAvatar?.id);

  return (
    <>
      <SideTitle title={isNewDraft ? "New avatar" : "Avatar editor"} subtitle={isNewDraft ? "Cisty draft pro novou personu" : "Nativni Next nastaveni"} />
      <AvatarConsentCard checked={props.consent} onChange={props.onConsentChange} />
      <Card className="mb-3">
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>{isNewDraft ? "Create avatar" : "Edit avatar"}</CardTitle>
              <CardDescription>{isNewDraft ? "Po ulozeni se avatar rovnou nastavi jako aktivni." : "Upravy se ulozi do avatar library."}</CardDescription>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={props.onCreate}>
              <UserRound className="h-4 w-4" />
              New
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-2 pt-4">
          <FieldInput label="ID" value={draft.id || ""} onChange={(value) => setField("id", value)} />
          <FieldInput label="Name" value={draft.name || ""} onChange={(value) => setField("name", value)} />
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Persona
            <Textarea value={draft.style || ""} onChange={(event) => setField("style", event.target.value)} />
          </label>
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Voice
            <Textarea value={draft.voice || ""} onChange={(event) => setField("voice", event.target.value)} />
          </label>
          <FieldInput label="Image URL" value={draft.image_url || ""} onChange={(value) => setField("image_url", value)} />
          <label className="grid gap-1 text-xs font-medium text-muted-foreground">
            Image upload
            <Input type="file" accept="image/*" onChange={(event) => props.setImageFile(event.target.files?.[0] || null)} />
          </label>
          {props.imageFile && <Badge variant="secondary">{props.imageFile.name}</Badge>}
          <Button onClick={props.saveAvatarDraft} disabled={props.dataBusy}>
            {props.dataBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save avatar
          </Button>
        </CardContent>
      </Card>
    </>
  );
}

function CreativeDetailPanel(props: {
  creative: Creative;
  dataBusy: boolean;
  onRate: (creative: Creative, status: CreativeRatingStatus, feedback?: CreativeRatingFeedback) => void;
  onSavePerformance: (creative: Creative, payload: Record<string, unknown>) => void;
}) {
  const [performance, setPerformance] = useState({
    ctr: props.creative.latest_ctr ? String(props.creative.latest_ctr) : "",
    cpc: props.creative.latest_cpc ? String(props.creative.latest_cpc) : "",
    cpa: props.creative.latest_cpa ? String(props.creative.latest_cpa) : "",
    roas: props.creative.latest_roas ? String(props.creative.latest_roas) : "",
    spend: props.creative.latest_spend ? String(props.creative.latest_spend) : "",
    date_range: "",
  });
  const [rejectDraft, setRejectDraft] = useState<RejectDraft>({ open: true, comment: "", reasons: [] });

  useEffect(() => {
    setPerformance({
      ctr: props.creative.latest_ctr ? String(props.creative.latest_ctr) : "",
      cpc: props.creative.latest_cpc ? String(props.creative.latest_cpc) : "",
      cpa: props.creative.latest_cpa ? String(props.creative.latest_cpa) : "",
      roas: props.creative.latest_roas ? String(props.creative.latest_roas) : "",
      spend: props.creative.latest_spend ? String(props.creative.latest_spend) : "",
      date_range: "",
    });
    setRejectDraft({ open: true, comment: "", reasons: [] });
  }, [props.creative]);

  const updatePerf = (key: keyof typeof performance, value: string) => setPerformance((current) => ({ ...current, [key]: value }));
  const nonReviewable = isNonReviewableCreative(props.creative);

  return (
    <>
      <SideTitle title="Creative detail" subtitle={props.creative.creative_id} />
      <CreativePreview creative={props.creative} compact />
      <BriefCard
        title="Metadata"
        rows={[
          ["Product", props.creative.product_name || "-"],
          ["Type", props.creative.type || "-"],
          ["Angle", props.creative.angle || "-"],
          ["Status", props.creative.latest_rating_status || props.creative.status || "-"],
          ["Avatar", props.creative.avatar_name || props.creative.avatar_id || "-"],
        ]}
      />
      {nonReviewable ? (
        <Card>
          <CardHeader>
            <CardTitle>Not reviewable</CardTitle>
            <CardDescription>{props.creative.status || "no generated media"}</CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted-foreground">{creativeUnavailableLabel(props.creative)}</CardContent>
        </Card>
      ) : (
        <>
          <div className="mb-3 grid grid-cols-2 gap-2">
            <Button variant="secondary" onClick={() => props.onRate(props.creative, "approved")} disabled={props.dataBusy}>
              <ThumbsUp className="h-4 w-4" />
              Approve
            </Button>
            <Button variant="outline" onClick={() => props.onRate(props.creative, "rejected", rejectDraft)} disabled={props.dataBusy}>
              <ThumbsDown className="h-4 w-4" />
              Reject
            </Button>
          </div>
          <RejectFeedbackEditor value={rejectDraft} onChange={(patch) => setRejectDraft((current) => ({ ...current, ...patch }))} />
          <Card>
            <CardHeader>
              <CardTitle>Performance</CardTitle>
              <CardDescription>Manual import z ads platformy</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-2">
              {(["ctr", "cpc", "cpa", "roas", "spend", "date_range"] as const).map((key) => (
                <FieldInput key={key} label={key.toUpperCase()} value={performance[key]} onChange={(value) => updatePerf(key, value)} />
              ))}
              <Button onClick={() => props.onSavePerformance(props.creative, performance)} disabled={props.dataBusy}>
                <Upload className="h-4 w-4" />
                Save performance
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}

function CreativeEmptyPanel(props: { creatives: Creative[] }) {
  const hidden = props.creatives.filter(isNonReviewableCreative).length;
  return (
    <>
      <SideTitle title="Creative detail" subtitle="No reviewable asset selected" />
      <Card>
        <CardHeader>
          <CardTitle>Review queue is clean</CardTitle>
          <CardDescription>{hidden ? `${hidden} failed/skipped assets are hidden` : "No creative selected"}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm leading-6 text-muted-foreground">
          Failed, skipped and empty generations are not treated as assets for approve/reject review. Switch the Creative sets status filter to Hidden failed/skipped only when you need to inspect them.
        </CardContent>
      </Card>
    </>
  );
}

function RejectFeedbackEditor(props: {
  value: RejectDraft;
  onChange: (patch: Partial<RejectDraft>) => void;
  compact?: boolean;
}) {
  const toggleReason = (reason: string) => {
    const selected = props.value.reasons.includes(reason);
    props.onChange({
      reasons: selected ? props.value.reasons.filter((item) => item !== reason) : [...props.value.reasons, reason],
    });
  };

  return (
    <div className={cn("rounded-md border bg-red-50/50 p-3", props.compact ? "space-y-2" : "mb-3 space-y-3")}>
      <div>
        <p className="text-xs font-semibold text-foreground">Duvod rejectu pro RAG</p>
        <p className="text-xs leading-5 text-muted-foreground">Cim konkretnejsi signal, tim lip se tomu dalsi generovani vyhne.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {rejectReasonOptions.map((reason) => {
          const selected = props.value.reasons.includes(reason.value);
          return (
            <Button
              key={reason.value}
              type="button"
              size="sm"
              variant={selected ? "destructive" : "outline"}
              onClick={() => toggleReason(reason.value)}
              className="h-7 rounded-full px-2 text-[11px]"
            >
              {reason.label}
            </Button>
          );
        })}
      </div>
      <Textarea
        value={props.value.comment}
        onChange={(event) => props.onChange({ comment: event.target.value })}
        className={cn("resize-none", props.compact ? "min-h-16 text-xs" : "min-h-24")}
        placeholder="Napr. text na produktu je rozpadly, ruka drzi produkt neprirozene, produkt zmenil tvar..."
      />
    </div>
  );
}

function PromptLabPanel(props: {
  settings: PromptSettings | null;
  providerCapabilities: Record<string, unknown> | null;
  applyPromptDefaults: () => void;
}) {
  return (
    <>
      <SideTitle title="Prompt sources" subtitle="Backend defaults + local overrides" />
      <Card className="mb-3">
        <CardHeader>
          <CardTitle>Defaults</CardTitle>
          <CardDescription>{props.settings ? "Loaded from backend" : "Not loaded"}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2">
          <Button onClick={props.applyPromptDefaults} variant="secondary">
            <Wand2 className="h-4 w-4" />
            Apply defaults
          </Button>
          <KeyValueRows
            rows={[
              ["Negative", props.settings?.negative_prompt ? `${props.settings.negative_prompt.length} chars` : "-"],
              ["System", props.settings?.content_prompt_system ? `${props.settings.content_prompt_system.length} chars` : "-"],
              ["Video", props.settings?.base_video_prompt_template ? `${props.settings.base_video_prompt_template.length} chars` : "-"],
            ]}
          />
        </CardContent>
      </Card>
      <ProviderMiniCard providerCapabilities={props.providerCapabilities} />
    </>
  );
}

function AnalyticsPanel(props: { learning: LearningSnapshot | null; intelligence: IntelligenceSummary | null }) {
  return (
    <>
      <SideTitle title="Learning signal" subtitle={props.learning?.status || "loading"} />
      <Card className="mb-3">
        <CardHeader>
          <CardTitle>Counts</CardTitle>
        </CardHeader>
        <CardContent>
          <KeyValueRows rows={Object.entries(props.learning?.counts || props.intelligence?.counts || {}).map(([key, value]) => [key, String(value)])} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Avoid</CardTitle>
        </CardHeader>
        <CardContent>
          <TagCloud tags={props.learning?.avoid_patterns || []} />
        </CardContent>
      </Card>
    </>
  );
}

function CostMonitorPanel(props: { runs: Array<Record<string, unknown>>; latestRun: Record<string, unknown> | null }) {
  const run = props.latestRun || props.runs[0] || null;
  const summary = costSummaryFromRun(run);
  const groups = readRecord(summary?.by_group);
  const components = costComponents(summary).filter((component) => Number(component.cost || 0) > 0);
  const totals = costTotals(props.runs);

  return (
    <>
      <SideTitle title="Cost detail" subtitle={run ? String(run.run_id || "") : "No run selected"} />
      <BriefCard
        title="Selected run"
        rows={[
          ["Product", productNameFromRun(run) || "-"],
          ["Status", String(run?.status || "-")],
          ["Known cost", costDisplay(summary)],
          ["Requests", String(summary?.request_count || 0)],
          ["Unknown requests", String(summary?.unknown_request_count || 0)],
        ]}
      />
      <Card className="mb-3">
        <CardHeader>
          <CardTitle>Cost groups</CardTitle>
          <CardDescription>OpenRouter-reported known spend</CardDescription>
        </CardHeader>
        <CardContent>
          <KeyValueRows
            rows={Object.entries(groups || {}).map(([group, value]) => {
              const record = readRecord(value);
              return [group, String(record?.known_cost_usd_display || formatUsd(record?.known_cost))];
            })}
          />
        </CardContent>
      </Card>
      <Card className="mb-3">
        <CardHeader>
          <CardTitle>Top components</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {components.slice(0, 8).map((component) => (
            <SignalRow
              key={`${String(component.component)}-${String(component.group)}`}
              label={String(component.component || "component")}
              value={String(component.cost_usd_display || formatUsd(component.cost))}
              meta={String(component.group || component.model || "")}
            />
          ))}
          {!components.length && <p className="text-sm text-muted-foreground">No known component cost for this run.</p>}
        </CardContent>
      </Card>
      <BriefCard
        title="Portfolio"
        rows={[
          ["Known spend", formatUsd(totals.known)],
          ["Runs", String(props.runs.length)],
          ["Avg/run", formatUsd(totals.average)],
        ]}
      />
    </>
  );
}

function SettingsPanel(props: {
  form: CampaignForm;
  update: <K extends keyof CampaignForm>(key: K, value: CampaignForm[K]) => void;
  dataStatus: string;
  providerCapabilities: Record<string, unknown> | null;
  settings: PromptSettings | null;
}) {
  const workflowNodes = buildWorkflowNodes(props.settings);
  return (
    <>
      <SideTitle title="Current config" subtitle={props.dataStatus} />
      <BriefCard
        title="Models"
        rows={[
          ["Prompt", props.form.prompt_model],
          ["Scenario", props.form.ugc_scenario_model],
          ["Image", props.form.image_model],
          ["Video", props.form.seedance_model],
        ]}
      />
      <BriefCard
        title="Workflow"
        rows={[
          ["Agents", String(workflowNodes.length)],
          ["Connections", String(buildWorkflowEdges(workflowNodes).length)],
          ["Guardrails", String(workflowGuardrails(props.settings).length)],
        ]}
      />
      <BriefCard
        title="Output"
        rows={[
          ["Mode", modeLabel(props.form.generation_mode)],
          ["Market", props.form.market],
          ["Language", props.form.language],
          ["Static images", props.form.max_static_images],
        ]}
      />
      <ProviderMiniCard providerCapabilities={props.providerCapabilities} />
    </>
  );
}

function WorkspaceScroll({ children }: { children: ReactNode }) {
  return <div className="chat-scroll flex-1 overflow-y-auto px-3 py-5 md:px-6">{children}</div>;
}

function SideTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <p className="text-sm font-semibold">{title}</p>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

function Chip({ children, icon, onClick }: { children: ReactNode; icon: ReactNode; onClick: () => void }) {
  return (
    <Button type="button" variant="outline" size="sm" onClick={onClick} className="h-7 rounded-full bg-white/80">
      {icon}
      {children}
    </Button>
  );
}

function BriefCard({ title, rows }: { title: string; rows: Array<[string, string]> }) {
  return (
    <Card className="mb-3">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <KeyValueRows rows={rows} />
      </CardContent>
    </Card>
  );
}

function AvatarConsentCard(props: { checked: boolean; onChange: (value: boolean) => void; compact?: boolean }) {
  return (
    <Card className={cn("mb-3 border-emerald-200 bg-emerald-50/40", !props.checked && "border-red-200 bg-red-50/50")}>
      <CardHeader className={props.compact ? "p-3 pb-2" : undefined}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>Autorizovaný AI avatar</CardTitle>
            <CardDescription>Souhlas pro reklamní použití podoby</CardDescription>
          </div>
          <Badge variant={props.checked ? "secondary" : "outline"}>{props.checked ? "Authorized" : "Needs consent"}</Badge>
        </div>
      </CardHeader>
      <CardContent className={cn("space-y-2", props.compact && "p-3 pt-0")}>
        <label className="flex items-start gap-3 rounded-md border bg-white/80 p-3 text-sm leading-6">
          <input
            type="checkbox"
            checked={props.checked}
            onChange={(event) => props.onChange(event.target.checked)}
            className="mt-1 h-4 w-4 accent-emerald-900"
          />
          <span className="min-w-0">
            <span className="block font-medium">
              Souhlasím s použitím mé podoby jako AI avatara pro tvorbu reklamních videí pro zvolený brand/projekt, včetně úprav, lip-syncu a
              generování nových scén.
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">
              Zapni jen pro svoji podobu nebo pro osobu/avatara, kde máš souhlas k reklamnímu použití.
            </span>
          </span>
        </label>
      </CardContent>
    </Card>
  );
}

function KeyValueRows({ rows }: { rows: Array<[string, string]> }) {
  return (
    <>
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-start justify-between gap-3 border-t pt-2 text-xs">
          <span className="text-muted-foreground">{label}</span>
          <span className="max-w-48 truncate text-right font-medium">{value}</span>
        </div>
      ))}
    </>
  );
}

function MetricCard({ label, value, meta }: { label: string; value: string | number; meta: string }) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{meta}</CardContent>
    </Card>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border bg-muted/30 px-2 py-2">
      <div className="font-semibold">{value}</div>
      <div className="text-muted-foreground">{label}</div>
    </div>
  );
}

function SignalRow({ label, value, meta }: { label: string; value: string; meta?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm">
      <span className="min-w-0">
        <span className="block truncate font-medium">{label}</span>
        {meta && <span className="block truncate text-xs text-muted-foreground">{meta}</span>}
      </span>
      <Badge variant="secondary">{value}</Badge>
    </div>
  );
}

function TagCloud({ title, tags }: { title?: string; tags: string[] }) {
  return (
    <div>
      {title && <p className="mb-2 text-xs font-medium text-muted-foreground">{title}</p>}
      <div className="flex flex-wrap gap-2">
        {tags.length ? tags.slice(0, 24).map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>) : <Badge variant="muted">empty</Badge>}
      </div>
    </div>
  );
}

function AvatarPreview({ avatar, size = "md" }: { avatar: Avatar; size?: "md" | "lg" }) {
  const image = mediaUrl(avatar.preview_url || avatar.image_url || "");
  const box = size === "lg" ? "h-16 w-16" : "h-10 w-10";
  return (
    <div className={cn("overflow-hidden rounded-md border bg-muted", box)}>
      {image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={image} alt={avatar.name || avatar.id} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <UserRound className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}

function CreativePreview({ creative, compact = false }: { creative: Creative; compact?: boolean }) {
  const asset = mediaUrl(creative.asset_url || "");
  const isVideo = creative.type === "video";
  const emptyLabel = creativeUnavailableLabel(creative);
  return (
    <div
      className={cn(
        "overflow-hidden rounded-t-lg border-b bg-muted",
        compact ? (isVideo ? "mb-3 aspect-video rounded-lg border" : "mb-3 aspect-square rounded-lg border") : "aspect-video",
      )}
    >
      {asset ? (
        isVideo ? (
          <video src={asset} className={cn("h-full w-full", compact ? "object-contain" : "object-cover")} controls={compact} muted />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={asset} alt={creative.product_name || creative.creative_id} className={cn("h-full w-full", compact ? "object-contain" : "object-cover")} />
        )
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
          <ImagePlus className="h-5 w-5" />
          <span className="px-3 text-center leading-5">{emptyLabel}</span>
        </div>
      )}
    </div>
  );
}

function ProviderMiniCard({ providerCapabilities }: { providerCapabilities: Record<string, unknown> | null }) {
  const imageModels = readRecord(providerCapabilities?.image_models);
  const videoModels = readRecord(providerCapabilities?.video_models);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Provider capabilities</CardTitle>
        <CardDescription>{providerCapabilities ? "Loaded" : "Not loaded"}</CardDescription>
      </CardHeader>
      <CardContent>
        <KeyValueRows
          rows={[
            ["Image models", String(Object.keys(imageModels || {}).length)],
            ["Video models", String(Object.keys(videoModels || {}).length)],
            ["Version", String(providerCapabilities?.version || "-")],
          ]}
        />
      </CardContent>
    </Card>
  );
}

function FieldInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function FieldModelInput({
  label,
  value,
  onChange,
  options,
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: ReadonlyArray<{ value: string; label: string }>;
  hint?: string;
}) {
  return (
    <label className="grid gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
      <span className="flex flex-wrap gap-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              "rounded-full border px-2 py-1 text-[11px] font-medium transition",
              value === option.value ? "border-emerald-700 bg-emerald-50 text-emerald-900" : "bg-white text-muted-foreground hover:border-foreground",
            )}
          >
            {option.label}
          </button>
        ))}
      </span>
      {hint && <span className="text-[11px] font-normal leading-4 text-muted-foreground">{hint}</span>}
    </label>
  );
}

function FieldNumberInput({
  label,
  value,
  onChange,
  min,
  max,
  suffix,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  min: number;
  max: number;
  suffix?: string;
}) {
  return (
    <label className="grid gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <span className="relative block">
        <Input
          type="number"
          min={min}
          max={max}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className={suffix ? "pr-8" : undefined}
        />
        {suffix && <span className="pointer-events-none absolute right-3 top-2.5 text-xs text-muted-foreground">{suffix}</span>}
      </span>
    </label>
  );
}

function FieldSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="grid gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <Select value={value} onChange={(event) => onChange(event.target.value)} options={options} />
    </label>
  );
}

function buildWorkflowNodes(settings: PromptSettings | null): WorkflowNode[] {
  const inventory = workflowInventoryMap(settings);
  return workflowNodeBlueprints.map((node) => ({
    ...node,
    inventory: inventory.get(node.inventoryLayer || node.title) || null,
  }));
}

function buildWorkflowEdges(nodes: WorkflowNode[]) {
  return nodes.flatMap((node) => node.dependsOn.map((from) => ({ from, to: node.id })));
}

function connectedNodeIds(nodes: WorkflowNode[], selectedId: string) {
  const connected = new Set<string>([selectedId]);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const upstream = (id: string) => {
    const node = nodeById.get(id);
    if (!node) return;
    node.dependsOn.forEach((dependencyId) => {
      if (connected.has(dependencyId)) return;
      connected.add(dependencyId);
      upstream(dependencyId);
    });
  };
  const downstream = (id: string) => {
    nodes
      .filter((node) => node.dependsOn.includes(id))
      .forEach((node) => {
        if (connected.has(node.id)) return;
        connected.add(node.id);
        downstream(node.id);
      });
  };
  upstream(selectedId);
  downstream(selectedId);
  return connected;
}

function workflowInventoryMap(settings: PromptSettings | null) {
  const map = new Map<string, Record<string, unknown>>();
  const inventory = readRecord(settings?.prompt_source_inventory);
  const layers = Array.isArray(inventory?.runtime_prompt_layers) ? inventory.runtime_prompt_layers : [];
  layers.forEach((layer) => {
    const record = readRecord(layer);
    const name = String(record?.layer || "");
    if (name && record) map.set(name, record);
  });
  return map;
}

function workflowGuardrails(settings: PromptSettings | null) {
  const inventory = readRecord(settings?.prompt_source_inventory);
  return Array.isArray(inventory?.guardrails) ? inventory.guardrails.map((item) => String(item)) : [];
}

function workflowNodeModelValue(node: WorkflowNode, form: CampaignForm) {
  if (node.modelKey) return String(form[node.modelKey] || "");
  return node.readonlyModel || "deterministic";
}

function workflowKindClass(kind: WorkflowNodeKind) {
  if (kind === "provider") return "bg-emerald-100 text-emerald-900";
  if (kind === "model") return "bg-blue-100 text-blue-900";
  if (kind === "guard") return "bg-amber-100 text-amber-900";
  if (kind === "memory") return "bg-violet-100 text-violet-900";
  if (kind === "qa") return "bg-slate-200 text-slate-900";
  if (kind === "input") return "bg-cyan-100 text-cyan-900";
  return "bg-muted text-foreground";
}

function workflowLegendDotClass(kind: WorkflowNodeKind) {
  if (kind === "provider") return "bg-emerald-500";
  if (kind === "model") return "bg-blue-500";
  if (kind === "guard") return "bg-amber-500";
  if (kind === "memory") return "bg-violet-500";
  if (kind === "qa") return "bg-slate-500";
  if (kind === "input") return "bg-cyan-500";
  return "bg-zinc-500";
}

function workflowGraphNodeClass(kind: WorkflowNodeKind) {
  if (kind === "provider") return "border-emerald-300 hover:border-emerald-700";
  if (kind === "model") return "border-blue-300 hover:border-blue-700";
  if (kind === "guard") return "border-amber-300 hover:border-amber-700";
  if (kind === "memory") return "border-violet-300 hover:border-violet-700";
  if (kind === "qa") return "border-slate-300 hover:border-slate-700";
  if (kind === "input") return "border-cyan-300 hover:border-cyan-700";
  return "border-zinc-300 hover:border-zinc-700";
}

function workflowShortModelLabel(key: WorkflowModelKey) {
  if (key === "prompt_model") return "prompt";
  if (key === "ugc_scenario_model") return "script";
  if (key === "static_prompt_model") return "static";
  if (key === "image_model") return "image";
  return "video";
}

function workflowGraphPosition(node: WorkflowNode) {
  return workflowGraphLayout[node.id] || { x: 24, y: 70 };
}

function clampWorkflowZoom(value: number) {
  return Math.min(workflowGraphMaxZoom, Math.max(workflowGraphMinZoom, Number(value.toFixed(2))));
}

function workflowEdgePath(from: WorkflowNode, to: WorkflowNode) {
  const fromPosition = workflowGraphPosition(from);
  const toPosition = workflowGraphPosition(to);
  const sameColumn = Math.abs(fromPosition.x - toPosition.x) < 24;
  if (sameColumn) {
    const sx = fromPosition.x + workflowGraphNodeWidth / 2;
    const sy = fromPosition.y + workflowGraphNodeHeight;
    const tx = toPosition.x + workflowGraphNodeWidth / 2;
    const ty = toPosition.y;
    const bend = Math.max(42, Math.abs(ty - sy) / 2);
    return `M ${sx} ${sy} C ${sx} ${sy + bend}, ${tx} ${ty - bend}, ${tx} ${ty}`;
  }
  const sx = fromPosition.x + workflowGraphNodeWidth;
  const sy = fromPosition.y + workflowGraphNodeHeight / 2;
  const tx = toPosition.x;
  const ty = toPosition.y + workflowGraphNodeHeight / 2;
  const bend = Math.max(74, Math.abs(tx - sx) / 2);
  return `M ${sx} ${sy} C ${sx + bend} ${sy}, ${tx - bend} ${ty}, ${tx} ${ty}`;
}

function workflowModelLabel(key: WorkflowModelKey) {
  if (key === "prompt_model") return "Prompt model";
  if (key === "ugc_scenario_model") return "UGC scenario model";
  if (key === "static_prompt_model") return "Static scenario model";
  if (key === "image_model") return "Image model";
  return "Video model";
}

function workflowModelHint(key: WorkflowModelKey) {
  if (key === "prompt_model") return "Shared prompt/refinement model for parser, product AI enrichment and critique.";
  if (key === "ugc_scenario_model") return "Scenario rewrite model. Default is ChatGPT/GPT for reliable spoken UGC scripts.";
  if (key === "static_prompt_model") return "Static image scenario and hook model. Default is ChatGPT/GPT for stable hooks and visual prompts.";
  if (key === "image_model") return "Static image provider model. Do not use video-only models here.";
  return "Video provider model for OpenRouter /videos. Veo belongs here, not in Image model.";
}

function workflowModelOptions(key: WorkflowModelKey, providerCapabilities: Record<string, unknown> | null) {
  if (key === "image_model") {
    return registryModelOptions(providerCapabilities?.image_models, imageModelOptions);
  }
  if (key === "seedance_model") {
    return registryModelOptions(providerCapabilities?.video_models, videoModelOptions);
  }
  return [...promptModelOptions];
}

function registryModelOptions(
  registryValue: unknown,
  fallback: ReadonlyArray<{ value: string; label: string }>,
) {
  const options = fallback.map((option) => ({ ...option }));
  const seen = new Set(options.map((option) => option.value));
  const registry = readRecord(registryValue);
  Object.keys(registry || {}).forEach((value) => {
    if (seen.has(value)) return;
    options.push({ value, label: modelLabelFromId(value) });
  });
  return options;
}

function modelLabelFromId(value: string) {
  const tail = value.split("/").pop() || value;
  return tail
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function avatarIdFromName(value: string) {
  const slug = value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48);
  return `${slug || "avatar"}_${Date.now().toString(36)}`;
}

function companyIdFromName(value: string) {
  const slug = value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return slug || `brand-${Date.now().toString(36)}`;
}

function listToLines(value: string[] | undefined) {
  return (value || []).join("\n");
}

function linesToList(value: string) {
  return cleanTextList(value.split(/\r?\n|,/g));
}

function cleanTextList(value: string[] | undefined) {
  return Array.from(new Set((value || []).map((item) => String(item || "").trim()).filter(Boolean))).slice(0, 20);
}

function firstLine(text: string) {
  const labeledName = productNameFromChatText(text);
  if (labeledName) return labeledName;
  return text
    .split(/\r?\n/)
    .map((line) => cleanProductNameCandidate(line))
    .find(Boolean)
    ?.slice(0, 120) || "";
}

function mergeFileList(current: File[], incoming: File[], limit: number) {
  const merged = [...current];
  for (const file of incoming) {
    const key = fileKey(file);
    const exists = merged.some((item) => fileKey(item) === key);
    if (!exists) merged.push(file);
  }
  return merged.slice(0, limit);
}

function fileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function parserSummaryText(result: ParserResult) {
  const draft = result.campaign_draft || {};
  const lines: string[] = [];
  const productName = compactParserValue(draft.product_name);
  const productReference = compactParserValue(draft.product_reference_url, 180);
  const productInfo = compactParserValue(draft.product_info, 180);
  const productCategory = compactParserValue(draft.product_category);
  const competitor = compactParserValue(draft.competitor_name || draft.competitor_url || draft.competitor_chat_brief, 160);
  const avatar = compactParserValue(draft.custom_avatar_name || draft.avatar_reference_url || draft.avatar_identity_note, 160);
  const direction = compactParserValue(draft.ugc_video_extra_prompt, 160);
  const settings = [
    draft.language ? `jazyk ${draft.language}` : "",
    draft.market ? `trh ${draft.market}` : "",
    draft.generation_mode ? modeLabel(String(draft.generation_mode)) : "",
  ].filter(Boolean);
  const attachmentRoles = result.attachment_roles || [];

  if (productName) lines.push(`Ad subject: ${productName}`);
  if (productReference) lines.push(`Reference: ${productReference}`);
  if (productCategory) lines.push(`Kategorie: ${productCategory}`);
  if (productInfo) lines.push(`Popis: ${productInfo}`);
  if (competitor) lines.push(`Konkurence: ${competitor}`);
  if (avatar) lines.push(`Avatar: ${avatar}`);
  if (direction) lines.push(`Rezie: ${direction}`);
  if (settings.length) lines.push(`Nastaveni: ${settings.join(" / ")}`);
  if (attachmentRoles.length) {
    const roleCounts = attachmentRoles.reduce<Record<string, number>>((counts, role) => {
      counts[role.role] = (counts[role.role] || 0) + 1;
      return counts;
    }, {});
    lines.push(
      `Prilohy: ${Object.entries(roleCounts)
        .map(([role, count]) => `${parserRoleLabel(role)} ${count}x`)
        .join(", ")}`,
    );
  }

  if (!lines.length) return "";
  const modelLine = result.model ? `\n\nParser: ${result.parser_mode || result.status || "auto"} / ${result.model}` : "";
  return `Rozpoznal jsem a propsal do kampane:\n${lines.map((line) => `- ${line}`).join("\n")}${modelLine}`;
}

function compactParserValue(value: unknown, limit = 120) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return "";
  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 3)).trim()}...`;
}

function parserRoleLabel(role: string) {
  if (role === "product") return "produkt";
  if (role === "competitor") return "konkurence";
  if (role === "avatar") return "avatar";
  if (role === "direction") return "rezie";
  return role;
}

function productNameFromChatText(text: string) {
  const match = String(text || "").match(
    /(?:^|\n)\s*(?:product\s*name|name|nazev\s*produktu|název\s*produktu|nazev|název|jmeno|jméno|produkt|product)\s*[:=\-–—]\s*([^\n]+)/i,
  );
  return cleanProductNameCandidate(match?.[1] || "");
}

function cleanProductNameCandidate(value: string) {
  const withoutTrailingLabels = String(value || "").replace(
    /\s+(?:product\s*url|url\s*produktu|produkt\s*url|link\s*produktu|url|link|popis|description|brief|notes|obrazek|obrázek|image)\s*[:=\-–—].*$/i,
    "",
  );
  const cleaned = withoutTrailingLabels
    .replace(/https?:\/\/[^\s<>'"]+/gi, "")
    .replace(/^\s*(?:product\s*name|name|nazev\s*produktu|název\s*produktu|nazev|název|jmeno|jméno|produkt|product)\s*[:=\-–—]\s*/i, "")
    .replace(/^[\s\-*#"'`]+|[\s\-*#"'`]+$/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return /^(product|produkt|name|nazev|název|jmeno|jméno|url|link)$/i.test(cleaned) ? "" : cleaned.slice(0, 120);
}

function nonEmptyPatch(current: CampaignForm, patch: Partial<CampaignForm>) {
  const result: Partial<CampaignForm> = {};
  for (const [key, value] of Object.entries(patch) as Array<[keyof CampaignForm, unknown]>) {
    if (value === "" || value == null || value === false) continue;
    if (["product_info", "competitor_chat_brief", "custom_avatar_persona", "avatar_identity_note", "ugc_video_extra_prompt"].includes(key)) {
      result[key] = appendBlock(String(current[key] || ""), String(value)) as never;
    } else {
      result[key] = value as never;
    }
  }
  return result;
}

function applyCompanyDefaults(form: CampaignForm, company: Company): CampaignForm {
  return {
    ...form,
    company_id: company.id || form.company_id,
    ad_vertical: company.ad_vertical || form.ad_vertical,
    market: company.market || form.market,
    language: company.language || form.language,
    platform: company.default_platform || form.platform,
    brand_context: company.context_text || form.brand_context,
    avatar_id: company.default_avatar_id || form.avatar_id,
  };
}

function normalizeCompanyDraft(company: Partial<Company>): Partial<Company> {
  return {
    ...company,
    id: company.id || companyIdFromName(company.name || "brand"),
    creative_channels: cleanTextList(company.creative_channels),
    product_categories: cleanTextList(company.product_categories),
    proof_points: cleanTextList(company.proof_points),
    forbidden_claims: cleanTextList(company.forbidden_claims),
    creative_quality_rules: cleanTextList(company.creative_quality_rules),
  };
}

function resetCampaignDraftForNewChat(current: CampaignForm): CampaignForm {
  return {
    ...current,
    product_name: "",
    product_info: "",
    product_category: "",
    product_reference_url: "",
    competitor_strategy_enabled: false,
    competitor_name: "",
    competitor_url: "",
    competitor_chat_brief: "",
    competitor_screenshot_notes: "",
    ugc_video_extra_prompt: "",
  };
}

function modeLabel(mode: string) {
  if (mode === "video") return "Jen video";
  if (mode === "static") return "Jen statiky";
  return "Video + statiky";
}

function generationEstimateText(form: CampaignForm) {
  const videoLength = Number(form.video_length) || 15;
  const staticCount = Number(form.max_static_images) || 0;
  if (form.generation_mode === "static") return staticCount > 8 ? "cca 2-5 minut" : "cca 1-3 minuty";
  if (form.generation_mode === "video") return videoLength > 20 ? "cca 6-12 minut" : "cca 4-8 minut";
  return videoLength > 20 || staticCount > 8 ? "cca 7-14 minut" : "cca 5-10 minut";
}

function chatWorkflowSteps(
  form: CampaignForm,
  productFile: File | null,
  staticProductFiles: File[],
  scenarioDrafts: ScenarioDraft[],
  approvedScenarioId: string,
): ChatWorkflowStep[] {
  const hasProduct = Boolean(form.product_info || form.product_reference_url || productFile || staticProductFiles.length);
  const hasBrand = Boolean(form.company_id || form.brand_context);
  const videoMode = form.generation_mode !== "static";
  const productReferenceReady = !videoMode || isVideoReadyProductReference(form.product_reference_url);
  const hasScenarioDrafts = scenarioDrafts.length > 0;
  const hasApprovedScenario = Boolean(approvedScenarioId && scenarioDrafts.some((scenario) => scenario.id === approvedScenarioId));
  const hasApprovedPlan = Boolean(hasApprovedScenario || form.ugc_video_extra_prompt.trim());
  const readyToGenerate = hasProduct && productReferenceReady && form.avatar_own_person_consent && hasApprovedPlan;

  return [
    {
      id: "brief",
      title: "Brief",
      detail: hasProduct && hasBrand ? "Brand a zadani reklamy jsou pripraveny." : "Ceka na text reklamy, brand, URL nebo obrazek.",
      state: hasProduct && hasBrand ? "done" : "active",
      meta: form.product_name || form.company_id || "",
    },
    {
      id: "strategy",
      title: "Strategy",
      detail: hasProduct && hasBrand ? "Orchestrator muze vybrat angle, hook a claim hranice." : "Nejdriv brief a brand.",
      state: hasProduct && hasBrand ? "done" : hasProduct ? "active" : "waiting",
      meta: form.platform || "",
    },
    {
      id: "plan",
      title: "Creative Plan",
      detail: hasApprovedPlan ? "Creative plan je propsany do rezie." : hasScenarioDrafts ? "Vyber jednu variantu." : "Priprav UGC scenare a staticke koncepty.",
      state: hasApprovedPlan ? "done" : hasScenarioDrafts ? "active" : hasProduct ? "waiting" : "waiting",
      meta: hasScenarioDrafts ? `${scenarioDrafts.length} varianty` : "UGC + static",
    },
    {
      id: "generate",
      title: "Generate",
      detail: readyToGenerate ? "Pripraveno spustit generation run." : productReferenceReady ? "Ceka na schvaleny plan." : "Video potrebuje public direct visual URL.",
      state: readyToGenerate ? "active" : productReferenceReady ? "waiting" : hasProduct ? "blocked" : "waiting",
      meta: modeLabel(form.generation_mode),
    },
    {
      id: "review",
      title: "Review",
      detail: "Po vystupu prijde kontrola kvality, learning a dalsi krok.",
      state: "waiting",
      meta: form.avatar_own_person_consent ? form.avatar_id || "" : "avatar consent",
    },
  ];
}

function chatWorkflowStepClass(state: ChatWorkflowStepState) {
  if (state === "done") return "border-emerald-200 bg-emerald-50/80";
  if (state === "active") return "border-blue-200 bg-blue-50/80";
  if (state === "blocked") return "border-amber-300 bg-amber-50/90";
  return "border-slate-200 bg-white";
}

function buildChatScenarioDrafts(form: CampaignForm, avatar: Avatar | undefined): ScenarioDraft[] {
  const language = scenarioLanguageCode(form.language);
  const productName = safeScenarioProductName(form);
  const productFact = scenarioProductFact(form.product_info);
  const avatarLine = avatar?.name ? `Avatar: ${avatar.name}.` : "";
  const createdAt = new Date().toISOString();
  const baseId = Date.now().toString(36);
  const apparelSuggestions = isApparelScenarioProduct(form)
    ? [mirrorSelfieTryOnScenario(baseId, language, productName, productFact, avatarLine, createdAt)]
    : [];

  if (language === "de") {
    return [
      ...apparelSuggestions,
      {
        id: `scenario-${baseId}-daily`,
        title: "Alltaglicher Hook",
        angle: "Problem -> echte Nutzung -> kurzer Kaufgrund",
        hook: `Ich wollte ${productName}, das nicht nur gut aussieht, sondern im Alltag Sinn macht.`,
        script: `Kurz und ehrlich: Ich zeige dir ${productName} so, wie ich es wirklich benutzen wurde. ${productFact ? `Wichtig aus dem Briefing: ${productFact}. ` : ""}${avatarLine} Erst sieht man mich mit dem Produkt, dann den wichtigsten Detailbeweis, danach eine normale Alltagsszene. Keine ubertriebene Werbung, eher eine klare Empfehlung.`,
        visualPlan: ["Avatar im ersten Bild", "Produkt in Hand", "Detailbeweis", "Alltagsszene", "kurzer Abschluss"],
        cta: `${productName} ansehen`,
        language: "de",
        created_at: createdAt,
      },
      {
        id: `scenario-${baseId}-proof`,
        title: "Detail Proof",
        angle: "Hook -> Nahaufnahme -> Nutzen -> CTA",
        hook: `Das Detail hier ist genau der Grund, warum mir ${productName} aufgefallen ist.`,
        script: `Ich starte direkt mit dem Produkt in der Hand und zeige nicht einfach eine schone Szene, sondern den Beweis. ${productFact ? `${productFact}. ` : ""}Dann kommt ein Close-up, eine kurze Bewegung mit dem Produkt und am Ende ein ruhiger Satz, warum es fur den Alltag passt.`,
        visualPlan: ["Hook mit Avatar", "Close-up", "Material/Form", "Nutzung", "CTA Satz"],
        cta: `${productName} fur deinen Alltag`,
        language: "de",
        created_at: createdAt,
      },
      {
        id: `scenario-${baseId}-lifestyle`,
        title: "Lifestyle Empfehlung",
        angle: "Creator Empfehlung -> Kontext -> Produkt bleibt Hauptfigur",
        hook: `Wenn du etwas suchst, das sofort ordentlich und hochwertig wirkt, schau dir ${productName} an.`,
        script: `Ich halte das Ganze sehr naturlich. Erst spreche ich direkt in die Kamera, dann zeige ich ${productName} in einer passenden Umgebung. ${productFact ? `Der klare Punkt ist: ${productFact}. ` : ""}Das Produkt bleibt in jedem Shot gleich, gleiche Farbe, gleiche Form, gleiche Proportionen.`,
        visualPlan: ["Creator Talking", "Produkt sichtbar", "Kontext", "Detail", "ruhiger Abschluss"],
        cta: `${productName} jetzt entdecken`,
        language: "de",
        created_at: createdAt,
      },
    ];
  }

  if (language === "en") {
    return [
      ...apparelSuggestions,
      {
        id: `scenario-${baseId}-daily`,
        title: "Everyday Hook",
        angle: "Problem -> real use -> simple buying reason",
        hook: `I wanted ${productName} that looks good, but actually makes sense in real life.`,
        script: `Quick honest take: I would show ${productName} like a normal creator, not like a glossy commercial. ${productFact ? `The important product note is: ${productFact}. ` : ""}${avatarLine} Start with the avatar holding the product, then show the main proof detail, then one natural everyday moment and a calm reason to care.`,
        visualPlan: ["Avatar first", "Product in hand", "Proof detail", "Real-life use", "Soft CTA"],
        cta: `Check out ${productName}`,
        language: "en",
        created_at: createdAt,
      },
      {
        id: `scenario-${baseId}-proof`,
        title: "Detail Proof",
        angle: "Hook -> close-up -> benefit -> CTA",
        hook: `This one detail is why ${productName} feels worth a closer look.`,
        script: `Open with the product already in hand. Keep the avatar visible, then cut to a clean close-up and show what makes the product useful. ${productFact ? `${productFact}. ` : ""}No random subtitles, no overacting, just a believable creator explaining why it fits the day.`,
        visualPlan: ["Avatar hook", "Close-up", "Material/form", "Use case", "CTA line"],
        cta: `${productName} for everyday use`,
        language: "en",
        created_at: createdAt,
      },
      {
        id: `scenario-${baseId}-lifestyle`,
        title: "Lifestyle Recommendation",
        angle: "Creator recommendation -> context -> product stays exact",
        hook: `If you want something that feels clean and practical, ${productName} is the kind of product I would look at.`,
        script: `Keep it relaxed. The avatar talks to camera first, then shows ${productName} in a category-appropriate setting. ${productFact ? `The key point from the brief is: ${productFact}. ` : ""}The product must stay exactly the same in every shot: same color, material, shape, size and proportions.`,
        visualPlan: ["Creator talking", "Product visible", "Context", "Detail", "Plain ending"],
        cta: `Take a look at ${productName}`,
        language: "en",
        created_at: createdAt,
      },
    ];
  }

  return [
    ...apparelSuggestions,
    {
      id: `scenario-${baseId}-daily`,
      title: "Kazdodenni hook",
      angle: "Problem -> realne pouziti -> jednoduchy duvod ke koupi",
      hook: `Chtel jsem ${productName}, ktery nevypada jen hezky, ale dava smysl i normalne pres den.`,
      script: `Hele, ukazal bych ${productName} uplne normalne, ne jako nablyskanou reklamu. ${productFact ? `Dulezita vec z briefu: ${productFact}. ` : ""}${avatarLine} Prvni zaber avatar s produktem v ruce, pak kratky detail, pak realna situace a na konci jednoducha veta, proc by me to zaujalo.`,
      visualPlan: ["Avatar v prvnim zaberu", "Produkt v ruce", "Detail produktu", "Realne pouziti", "kratke CTA"],
      cta: `Mrkni na ${productName}`,
      language: "cs",
      created_at: createdAt,
    },
    {
      id: `scenario-${baseId}-proof`,
      title: "Detail proof",
      angle: "Hook -> detail -> benefit -> CTA",
      hook: `Tohle je presne ten detail, kvuli kteremu ${productName} stoji za pozornost.`,
      script: `Zacal bych rovnou s produktem v ruce. Avatar zustane videt, pak strih na cisty detail a ukazku toho, proc je produkt prakticky. ${productFact ? `${productFact}. ` : ""}Bez nahodnych titulku, bez prehravani, spis jako kdyz to ukazujes kamaradovi a reknes, co je na tom fakt dobre.`,
      visualPlan: ["Avatar hook", "Close-up", "Material/tvar", "Pouziti", "CTA veta"],
      cta: `${productName} na kazdy den`,
      language: "cs",
      created_at: createdAt,
    },
    {
      id: `scenario-${baseId}-lifestyle`,
      title: "Lifestyle doporuceni",
      angle: "Doporuceni tvurce -> kontext -> produkt zustava hlavni",
      hook: `Jestli hledas neco, co pusobi ciste a prakticky, ${productName} bych si prohlidnul.`,
      script: `Cele to bude uvolnene. Avatar nejdriv promluvi do kamery, pak ukaze ${productName} v prostredi, ktere dava smysl podle kategorie produktu. ${productFact ? `Hlavni bod z briefu je: ${productFact}. ` : ""}Produkt musi zustat uplne stejny v kazdem zaberu: stejna barva, material, tvar, velikost i proporce.`,
      visualPlan: ["Avatar mluvi", "Produkt viditelny", "Kontext", "Detail", "klidny zaver"],
      cta: `Podivej se na ${productName}`,
      language: "cs",
      created_at: createdAt,
    },
  ];
}

function mirrorSelfieTryOnScenario(
  baseId: string,
  language: string,
  productName: string,
  productFact: string,
  avatarLine: string,
  createdAt: string,
): ScenarioDraft {
  if (language === "de") {
    return {
      id: `scenario-${baseId}-mirror-tryon`,
      title: "Mirror Selfie Try-on",
      angle: "natuerlicher Spiegel-Check -> Schnitt/Fit -> ruhige Empfehlung",
      hook: `Ich hatte nicht erwartet, dass ${productName} so gut sitzt.`,
      script: `Mirror selfie / try-on review, ca. 15 Sekunden. Die Creatorin haelt das Handy in der Hand und filmt ueber den Spiegel in einem einfachen Zimmer mit neutraler Wand. ${avatarLine} Sie startet nicht zu werblich, spricht ruhig zur Spiegelkamera, zeigt ${productName} aktiv am Koerper und macht eine kleine Drehung. ${productFact ? `Wichtiger Produktpunkt: ${productFact}. ` : ""}Ein fast durchgehender Take, weiches Tageslicht, kurze Saetze, wie eine Empfehlung an eine Freundin. Keine Luxus-Studio-Optik, keine Runway-Pose, kleine Imperfektion ist gut.`,
      visualPlan: ["mirror selfie", "phone in hand", "full-body try-on", "cut/waist/neckline", "one-take feel"],
      cta: `${productName} ansehen`,
      language: "de",
      created_at: createdAt,
    };
  }

  if (language === "en") {
    return {
      id: `scenario-${baseId}-mirror-tryon`,
      title: "Mirror Selfie Try-on",
      angle: "natural mirror check -> fit proof -> calm recommendation",
      hook: `I didn't expect ${productName} to fit this well.`,
      script: `Create an authentic UGC mirror selfie video, 15 to 20 seconds. A stylish woman stands in a simple bedroom in front of a mirror, filming herself with a smartphone. ${avatarLine} She is wearing ${productName} and naturally talks about how the cut and overall fit look on body, without sounding like a commercial. ${productFact ? `Important product note: ${productFact}. ` : ""}Vertical smartphone video, handheld mirror selfie, natural indoor lighting, plain neutral wall, minimal background, realistic movement, slight camera shake, casual gestures. She points to the waist, neckline, and overall fit. No studio lighting, no polished advertising style. Tone: confident, friendly, natural, relatable.`,
      visualPlan: ["mirror selfie", "simple bedroom", "phone in hand", "waist/neckline/fit", "real customer review"],
      cta: `Check out ${productName}`,
      language: "en",
      created_at: createdAt,
    };
  }

  return {
    id: `scenario-${baseId}-mirror-tryon`,
    title: "Zrcadlovy try-on",
    angle: "prirozeny mirror check -> proof strihu -> klidne doporuceni",
    hook: `Necekal jsem, ze ${productName} bude sedet tak dobre.`,
    script: `Mirror selfie / try-on review, cca 15 sekund. Tvurce drzi telefon v ruce a nataci pres zrcadlo v jednoduchem pokoji s neutralni stenou. ${avatarLine} Nezacinat moc reklamne. Mluvi klidne primo do zrcadlove kamery, aktivne ukazuje ${productName} na sobe, gestikuluje k outfitu a udela malou prirozenou otocku. ${productFact ? `Dulezity produktovy bod: ${productFact}. ` : ""}Skoro jeden souvisly zaber, mekke denni nebo interierove svetlo, kratke prirozene vety, jako doporuceni kamaradce. Zadny luxusni studio look, zadna runway poza, lehka nedokonalost je vyhoda.`,
    visualPlan: ["mirror selfie", "telefon v ruce", "full-body try-on", "strih/pas/vystrih", "one-take pocit"],
    cta: `Mrkni na ${productName}`,
    language: "cs",
    created_at: createdAt,
  };
}

function isApparelScenarioProduct(form: CampaignForm) {
  const text = [form.product_category, form.product_name, form.product_info].join(" ").toLowerCase();
  return [
    "apparel",
    "clothing",
    "dress",
    "jumpsuit",
    "overall",
    "overal",
    "outfit",
    "garment",
    "shirt",
    "top",
    "leggings",
    "trousers",
    "pants",
    "skirt",
    "saty",
    "obleceni",
    "odev",
  ].some((marker) => text.includes(marker));
}

function safeScenarioProductName(form: CampaignForm) {
  return (form.product_name || form.product_category || "tenhle produkt").trim().slice(0, 80);
}

function scenarioProductFact(productInfo: string) {
  const clean = String(productInfo || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!clean) return "";
  return clean.split(/[.!?]\s/)[0].slice(0, 180);
}

function scenarioLanguageCode(language: string) {
  const value = String(language || "").toLowerCase();
  if (value.startsWith("de") || value.includes("german")) return "de";
  if (value.startsWith("en") || value.includes("english")) return "en";
  return "cs";
}

function upsertApprovedScenarioPrompt(current: string, scenario: ScenarioDraft) {
  const withoutOld = String(current || "")
    .replace(/\n*=== CHAT APPROVED SCENARIO START ===[\s\S]*?=== CHAT APPROVED SCENARIO END ===\n*/g, "\n")
    .trim();
  const block = [
    "=== CHAT APPROVED SCENARIO START ===",
    `Use this approved orchestrator scenario as optional scene direction layered under the app's UGC skill rules.`,
    `Language: ${scenario.language}`,
    `Title: ${scenario.title}`,
    `Angle: ${scenario.angle}`,
    `Spoken hook: ${scenario.hook}`,
    `Script: ${scenario.script}`,
    `Visual plan: ${scenario.visualPlan.join(" -> ")}`,
    `CTA: ${scenario.cta}`,
    "Keep the exact product appearance from the product reference. Do not change material, shape, size, color, transparency, proportions, logo, or product type.",
    "Keep the avatar visible in the hook and closing scene. Do not render generated on-screen text; spoken audio carries the hook and message.",
    "=== CHAT APPROVED SCENARIO END ===",
  ].join("\n");
  return appendBlock(withoutOld, block);
}

function generationRunProblem(run: Record<string, unknown> | null): { message: string } | null {
  if (!run) return null;
  const monitor = readRecord(run.monitor);
  const finalOutput = readRecord(run.final_output);
  const status = String(monitor?.status || run.status || "").toLowerCase();
  const statusLabel = String(monitor?.status_label || run.status || status || "problem");
  const blockers = recordList(monitor?.blockers);
  const terminalReason = String(monitor?.terminal_reason || run.last_error || run.error || "").trim();
  const nextStep = String(monitor?.next_step || "").trim();
  const outputPlan = generationOutputPlanFromRun(run);
  const videoGeneration = readRecord(run.video_generation) || readRecord(finalOutput?.video_generation) || {};
  const staticGeneration = readRecord(run.static_image_generation) || readRecord(finalOutput?.static_image_generation) || {};
  const providerValidation = readRecord(run.provider_validation) || readRecord(finalOutput?.provider_validation) || {};
  const problemStates: GenerationOutputBranchState[] = ["blocked", "failed", "cancelled"];
  const branchProblems = [
    outputPlan.video.enabled && problemStates.includes(outputPlan.video.state)
      ? {
          title: outputPlan.video.title,
          state: outputPlan.video.badge,
          reason: String(videoGeneration.failure_reason || videoGeneration.error || outputPlan.video.detail || "").trim(),
        }
      : null,
    outputPlan.staticImages.enabled && problemStates.includes(outputPlan.staticImages.state)
      ? {
          title: outputPlan.staticImages.title,
          state: outputPlan.staticImages.badge,
          reason: String(staticGeneration.failure_reason || staticGeneration.error || outputPlan.staticImages.detail || "").trim(),
        }
      : null,
  ].filter((item): item is { title: string; state: string; reason: string } => Boolean(item));
  const providerStatus = String(providerValidation.status || "").toLowerCase();
  const providerProblem = ["blocked", "failed"].includes(providerStatus)
    ? String(providerValidation.reason || providerValidation.error || providerValidation.message || "Provider validation failed.").trim()
    : "";
  const terminalProblem = ["blocked", "failed", "cancelled"].includes(status);
  if (!terminalProblem && !blockers.length && !branchProblems.length && !providerProblem) return null;

  const productName = productNameFromRun(run);
  const runId = String(run.run_id || "");
  const assets = generatedRunAssets(run);
  const lines = [
    status === "cancelled"
      ? `Generovani bylo zruseno${productName ? ` pro ${productName}` : ""}.`
      : `Generovani skoncilo s problemem${productName ? ` pro ${productName}` : ""}.`,
    `Status: ${statusLabel}${runId ? ` / ${runId}` : ""}`,
  ];
  if (terminalReason) lines.push(`Problem: ${compactParserValue(terminalReason, 420)}`);
  if (providerProblem) lines.push(`Provider validation: ${compactParserValue(providerProblem, 420)}`);
  if (branchProblems.length) {
    lines.push(
      [
        "Vetve:",
        ...branchProblems.map((item) => `- ${item.title}: ${item.state}${item.reason ? ` - ${compactParserValue(item.reason, 260)}` : ""}`),
      ].join("\n"),
    );
  }
  if (blockers.length) {
    lines.push(
      [
        "Blockers:",
        ...blockers.slice(0, 5).map((blocker) => {
          const source = String(blocker.source || "workflow");
          const id = String(blocker.id || "blocked");
          const reason = compactParserValue(blocker.reason || "Unknown reason", 300);
          return `- ${source} / ${id}: ${reason}`;
        }),
      ].join("\n"),
    );
  }
  if (assets.imageCount || assets.videoCount) {
    lines.push(`Castecny vystup uz je dostupny v agent timeline: ${assets.videoCount} video / ${assets.imageCount} statik.`);
  }
  if (nextStep) lines.push(`Dalsi krok: ${compactParserValue(nextStep, 360)}`);
  return { message: lines.join("\n\n") };
}

function generatedRunAssets(run: Record<string, unknown> | null): {
  images: GeneratedChatAsset[];
  videos: GeneratedChatAsset[];
  imageCount: number;
  videoCount: number;
} {
  if (!run) return { images: [], videos: [], imageCount: 0, videoCount: 0 };
  const finalOutput = readRecord(run.final_output);
  const partialOutputs = readRecord(run.partial_outputs) || readRecord(readRecord(run.monitor)?.partial_outputs) || {};
  const staticGeneration = readRecord(run.static_image_generation) || readRecord(finalOutput?.static_image_generation) || {};
  const videoGeneration = readRecord(run.video_generation) || readRecord(finalOutput?.video_generation) || {};
  const images = uniqueGeneratedAssets([
    ...recordList(partialOutputs.images).map((asset) => ({
      type: "image" as const,
      url: String(asset.url || ""),
      name: String(asset.name || "Generated static image"),
      meta: String(asset.updated_at || ""),
    })),
    ...recordList(staticGeneration.image_assets).map((asset, index) => ({
      type: "image" as const,
      url: String(asset.image_url || asset.url || ""),
      name: staticAssetHook(asset, index),
      meta: staticAssetMeta(asset),
    })),
  ]).filter((asset) => asset.url);
  const videoUrl = String(videoGeneration.video_url || videoGeneration.url || "");
  const videos = uniqueGeneratedAssets([
    ...recordList(partialOutputs.videos).map((asset) => ({
      type: "video" as const,
      url: String(asset.url || ""),
      name: String(asset.name || "UGC video"),
      meta: String(asset.updated_at || ""),
    })),
    ...(videoUrl
      ? [
          {
            type: "video" as const,
            url: videoUrl,
            name: String(videoGeneration.filename || videoGeneration.job_id || "UGC video"),
            meta: String(videoGeneration.video_generation_status || ""),
          },
        ]
      : []),
  ]).filter((asset) => asset.url);
  return {
    images,
    videos,
    imageCount: numberOrNull(partialOutputs.image_count) ?? images.length,
    videoCount: numberOrNull(partialOutputs.video_count) ?? videos.length,
  };
}

function staticAssetHook(asset: Record<string, unknown>, index: number) {
  return (
    String(asset.display_hook || asset.overlay_text || asset.headline || "").trim()
    || String(asset.name || "").trim()
    || `Static image ${index + 1}`
  );
}

function staticAssetMeta(asset: Record<string, unknown>) {
  return [
    String(asset.creative_id || "").trim(),
    String(asset.set_id || "").trim(),
    String(asset.asset_type || "").trim(),
  ]
    .filter(Boolean)
    .join(" / ");
}

function uniqueGeneratedAssets(assets: GeneratedChatAsset[]) {
  const seen = new Set<string>();
  return assets.filter((asset) => {
    const key = asset.url || `${asset.type}-${asset.name}`;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function generationOutputPlanFromRun(run: Record<string, unknown> | null): GenerationOutputPlanInfo {
  if (!run) {
    return {
      mode: "",
      label: "Zatim bez runu",
      video: outputBranch("UGC video", false, "disabled", "Vypnuto", "Zatim neni nacteny run.", ""),
      staticImages: outputBranch("Staticke obrazky", false, "disabled", "Vypnuto", "Zatim neni nacteny run.", ""),
    };
  }
  const monitor = readRecord(run.monitor);
  const finalOutput = readRecord(run.final_output);
  const input = readRecord(run.input_snapshot) || readRecord(finalOutput?.user_input) || {};
  const userInput = readRecord(finalOutput?.user_input) || {};
  const videoGeneration = readRecord(run.video_generation) || readRecord(finalOutput?.video_generation) || {};
  const staticGeneration = readRecord(run.static_image_generation) || readRecord(finalOutput?.static_image_generation) || {};
  const partialOutputs = readRecord(run.partial_outputs) || readRecord(readRecord(run.monitor)?.partial_outputs) || {};
  const partialImageCount = numberOrNull(partialOutputs.image_count);
  const partialVideoCount = numberOrNull(partialOutputs.video_count);
  const videoPayload = readRecord(videoGeneration.submitted_payload);
  const rawMode = String(input.generation_mode || userInput.generation_mode || videoGeneration.generation_mode || staticGeneration.generation_mode || "");
  const mode = ["both", "video", "static"].includes(rawMode) ? rawMode : "both";
  const appMode = String(input.app_mode || userInput.app_mode || run.app_mode || "").toLowerCase();
  const explicitVideo = boolish(input.generate_video ?? userInput.generate_video);
  const explicitStatic = boolish(input.generate_static_images ?? userInput.generate_static_images);
  const maxStaticImages = numberOrNull(input.max_static_images ?? userInput.max_static_images ?? staticGeneration.max_images_requested);
  const financeMode = appMode === "finance_personal_brand" || appMode === "finance";
  const videoEnabled = financeMode ? true : explicitVideo ?? mode !== "static";
  const staticEnabled = financeMode ? false : explicitStatic ?? (mode !== "video" && maxStaticImages !== 0);
  const stage = String(monitor?.stage || run.current_stage || "").toLowerCase();
  const videoStatus = String(
    videoGeneration.video_generation_status || (partialVideoCount ? "completed" : stageStatusFromRun(run, "generating_video")),
  ).toLowerCase();
  const staticStatus = String(
    staticGeneration.image_generation_status || (stage === "generating_images" ? "generating_images" : stageStatusFromRun(run, "generating_images")),
  ).toLowerCase();
  const videoSkippedByMode = Boolean(videoGeneration.skipped_by_generation_mode) || mode === "static";
  const staticSkippedByMode = Boolean(staticGeneration.skipped_by_generation_mode) || financeMode || mode === "video";
  const videoState = outputBranchState({
    enabled: videoEnabled,
    status: videoStatus,
    skippedByMode: videoSkippedByMode,
    activeStage: stage === "generating_video",
    run,
  });
  const staticState = outputBranchState({
    enabled: staticEnabled,
    status: staticStatus,
    skippedByMode: staticSkippedByMode,
    activeStage: stage === "generating_images",
    run,
  });
  const videoModel = String(input.seedance_model || userInput.seedance_model || videoPayload?.model || "");
  const imageModel = String(input.image_model || userInput.image_model || staticGeneration.model || "");
  const videoLength = String(input.video_length || userInput.video_length || videoPayload?.duration || "");
  const selectedStatic = numberOrNull(staticGeneration.selected_creative_count);
  const generatedStatic = Array.isArray(staticGeneration.image_assets)
    ? staticGeneration.image_assets.length
    : numberOrNull(staticGeneration.generated_count) ?? partialImageCount;
  const requestedStatic = maxStaticImages ?? numberOrNull(staticGeneration.max_images_requested);
  return {
    mode,
    label: outputPlanLabel(videoEnabled, staticEnabled),
    video: outputBranch(
      "UGC video",
      videoEnabled,
      videoState,
      outputBranchBadge(videoState),
      outputBranchDetail("video", videoState),
      [videoModel, videoLength ? `${videoLength}s` : "", partialVideoCount ? `souboru ${partialVideoCount}` : ""].filter(Boolean).join(" / "),
    ),
    staticImages: outputBranch(
      "Staticke obrazky",
      staticEnabled,
      staticState,
      outputBranchBadge(staticState),
      outputBranchDetail("static", staticState),
      [
        imageModel,
        requestedStatic != null ? `limit ${requestedStatic}` : "",
        selectedStatic != null ? `vybrano ${selectedStatic}` : "",
        generatedStatic != null ? `hotovo ${generatedStatic}` : "",
      ]
        .filter(Boolean)
        .join(" / "),
    ),
  };
}

function stageStatusFromRun(run: Record<string, unknown> | null, stageName: string) {
  const stages = recordList(run?.stage_results);
  const match = [...stages].reverse().find((stage) => String(stage.stage || "").toLowerCase() === stageName);
  return String(match?.status || "");
}

function outputBranch(
  title: string,
  enabled: boolean,
  state: GenerationOutputBranchState,
  badge: string,
  detail: string,
  meta: string,
): GenerationOutputBranch {
  return { title, enabled, state, badge, detail, meta };
}

function outputPlanLabel(videoEnabled: boolean, staticEnabled: boolean) {
  if (videoEnabled && staticEnabled) return "Video + statiky aktivni";
  if (videoEnabled) return "Jen video aktivni";
  if (staticEnabled) return "Jen statiky aktivni";
  return "Vystupy vypnute";
}

function outputBranchState(args: {
  enabled: boolean;
  status: string;
  skippedByMode: boolean;
  activeStage: boolean;
  run: Record<string, unknown> | null;
}): GenerationOutputBranchState {
  if (!args.enabled) return "disabled";
  if (args.skippedByMode || args.status === "skipped") return "skipped";
  if (args.status === "completed") return "completed";
  if (args.status === "blocked") return "blocked";
  if (args.status === "failed") return "failed";
  if (args.status === "cancelled") return "cancelled";
  if (["generating_video", "generating_images", "running", "processing", "in_progress"].includes(args.status)) {
    if (args.activeStage && isRunActive(args.run)) return "active";
    return isRunActive(args.run) ? "queued" : "idle";
  }
  if (args.activeStage && isRunActive(args.run)) return "active";
  if (isRunActive(args.run)) return "queued";
  return "idle";
}

function outputBranchBadge(state: GenerationOutputBranchState) {
  const labels: Record<GenerationOutputBranchState, string> = {
    active: "Bezi",
    queued: "Ceka",
    completed: "Hotovo",
    blocked: "Blok",
    failed: "Error",
    cancelled: "Zruseno",
    skipped: "Preskoceno",
    disabled: "Vypnuto",
    idle: "Pripraveno",
  };
  return labels[state];
}

function outputBranchDetail(kind: "video" | "static", state: GenerationOutputBranchState) {
  const video: Record<GenerationOutputBranchState, string> = {
    active: "Video provider prave generuje UGC video.",
    queued: "Video je aktivovane a ceka na svuj krok.",
    completed: "Video vetev ma hotovy vystup.",
    blocked: "Video vetev byla zablokovana validaci.",
    failed: "Video vetev selhala u providera.",
    cancelled: "Video vetev byla zrusena.",
    skipped: "Video je preskocene podle zvoleneho rezimu.",
    disabled: "Video generovani neni pro tento run zapnute.",
    idle: "Video je zapnute, ale zatim nema provider status.",
  };
  const statics: Record<GenerationOutputBranchState, string> = {
    active: "Image provider prave generuje statiky.",
    queued: "Statiky jsou aktivovane a cekaji na svuj krok.",
    completed: "Staticka vetev ma hotove assety.",
    blocked: "Staticka vetev byla zablokovana validaci.",
    failed: "Staticka vetev selhala u providera.",
    cancelled: "Staticka vetev byla zrusena.",
    skipped: "Statiky jsou preskocene podle zvoleneho rezimu.",
    disabled: "Staticke obrazky nejsou pro tento run zapnute.",
    idle: "Statiky jsou zapnute, ale zatim nemaji provider status.",
  };
  return kind === "video" ? video[state] : statics[state];
}

function outputBranchTone(state: GenerationOutputBranchState) {
  if (state === "active") return "bg-emerald-50 border-emerald-300";
  if (state === "completed") return "bg-emerald-50/70 border-emerald-200";
  if (state === "queued" || state === "idle") return "bg-amber-50/60 border-amber-200";
  if (state === "blocked" || state === "failed") return "bg-red-50/70 border-red-200";
  if (state === "cancelled") return "bg-orange-50/70 border-orange-200";
  return "";
}

function boolish(value: unknown): boolean | undefined {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(normalized)) return true;
    if (["0", "false", "no", "off"].includes(normalized)) return false;
  }
  return undefined;
}

function numberOrNull(value: unknown): number | null {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function initialView(): AppView {
  if (typeof window === "undefined") return "chat";
  const requested = new URLSearchParams(window.location.search).get("view");
  return navItems.some((item) => item.id === requested) ? (requested as AppView) : "chat";
}

function replaceShellUrl(view: AppView) {
  if (typeof window === "undefined") return;
  window.history.replaceState(null, "", view === "chat" ? "/" : `/?view=${view}`);
}

function mediaUrl(value: string) {
  if (!value) return "";
  if (value.startsWith("/")) return `/api/backend${value}`;
  return value;
}

function isPublicHttpUrl(value: string) {
  try {
    const url = new URL(String(value || "").trim());
    return ["http:", "https:"].includes(url.protocol) && !["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  } catch {
    return false;
  }
}

function isDirectImageReferenceUrl(value: string) {
  const text = String(value || "").toLowerCase();
  return [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".gif",
    "format=jpg",
    "format=jpeg",
    "format=png",
    "format=webp",
    "format=avif",
    "image/",
  ].some((marker) => text.includes(marker));
}

function isVideoReadyProductReference(value: string) {
  return isPublicHttpUrl(value) && isDirectImageReferenceUrl(value);
}

function normalizeRunPayload(payload: Record<string, unknown> | null) {
  if (!payload) return null;
  return readRecord(payload.generation_run) || payload;
}

function clampProgress(value: unknown) {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function isRunActive(run: Record<string, unknown> | null) {
  if (!run) return false;
  const monitor = readRecord(run.monitor);
  if (typeof monitor?.is_active === "boolean") return monitor.is_active;
  const status = String(monitor?.status || run.status || "").toLowerCase();
  const stage = String(monitor?.stage || run.current_stage || "").toLowerCase();
  return ["queued", "running", "in_progress", "processing", "validating", "planning", "prompting", "generating_video", "generating_images", "qa", "saving"].some(
    (value) => status === value || stage === value,
  );
}

function canCancelRun(run: Record<string, unknown> | null) {
  if (!run) return false;
  const monitor = readRecord(run.monitor);
  if (typeof monitor?.can_cancel === "boolean") return monitor.can_cancel;
  return isRunActive(run);
}

function isNonReviewableCreative(creative: Creative) {
  const status = String(creative.status || "").toLowerCase();
  const ratingStatus = String(creative.latest_rating_status || "").toLowerCase();
  return !creative.asset_url || ["failed", "skipped", "blocked", "cancelled"].includes(status) || ["failed", "skipped", "blocked", "cancelled"].includes(ratingStatus);
}

function creativeUnavailableLabel(creative: Creative) {
  const status = String(creative.status || "").toLowerCase();
  const ratingStatus = String(creative.latest_rating_status || "").toLowerCase();
  if (status === "skipped") return "Skipped for this run; no media file was generated.";
  if (status === "blocked") return "Blocked by a guard; no media file was generated.";
  if (status === "failed") return "Generation failed; this row is kept for diagnostics.";
  if (status === "cancelled") return "Generation was cancelled before media was saved.";
  if (["failed", "skipped", "blocked", "cancelled"].includes(ratingStatus)) return `Rating/status is ${ratingStatus}; this row is not reviewable.`;
  if (!creative.asset_url) return "No media file was saved for this row.";
  return "This row is not reviewable.";
}

function rejectDraftFor(drafts: Record<string, RejectDraft>, creativeId: string): RejectDraft {
  return drafts[creativeId] || { open: false, comment: "", reasons: [] };
}

function monitorCardTone(run: Record<string, unknown> | null) {
  const monitor = readRecord(run?.monitor);
  const status = String(monitor?.status || run?.status || "").toLowerCase();
  if (isRunActive(run)) return "border-emerald-700/40 bg-emerald-50/50";
  if (status === "completed") return "border-emerald-200 bg-emerald-50/30";
  if (status === "blocked" || status === "failed") return "border-red-200 bg-red-50/50";
  if (status === "cancelled") return "border-amber-200 bg-amber-50/50";
  return "bg-white";
}

function recordList(value: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(value)) return [];
  return value.map((item) => readRecord(item)).filter((item): item is Record<string, unknown> => Boolean(item));
}

function mergeRunList(current: Array<Record<string, unknown>>, run: Record<string, unknown>) {
  const runId = String(run.run_id || "");
  if (!runId) return current;
  const without = current.filter((item) => String(item.run_id || "") !== runId);
  return [run, ...without].slice(0, 120);
}

function costSummaryFromRun(run: Record<string, unknown> | null) {
  if (!run) return null;
  return readRecord(run.cost_summary) || readRecord(run.session_cost_summary);
}

function costComponents(summary: Record<string, unknown> | null) {
  const components = summary?.components;
  if (!Array.isArray(components)) return [];
  return components.map((item) => readRecord(item)).filter((item): item is Record<string, unknown> => Boolean(item));
}

function costNumber(value: unknown) {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function costDisplay(summary: Record<string, unknown> | null) {
  if (!summary) return "$0";
  return String(summary.total_known_cost_usd_display || formatUsd(summary.total_known_cost));
}

function formatUsd(value: unknown) {
  const number = costNumber(value);
  return `$${number.toFixed(6).replace(/0+$/, "").replace(/\.$/, "")}`;
}

function costTotals(runs: Array<Record<string, unknown>>) {
  const known = runs.reduce((sum, run) => sum + costNumber(costSummaryFromRun(run)?.total_known_cost), 0);
  const pricedRuns = runs.filter((run) => costSummaryFromRun(run)).length;
  const unknownRequests = runs.reduce((sum, run) => sum + costNumber(costSummaryFromRun(run)?.unknown_request_count), 0);
  return {
    known,
    average: pricedRuns ? known / pricedRuns : 0,
    unknownRequests,
  };
}

function productNameFromRun(run: Record<string, unknown> | null) {
  if (!run) return "";
  const snapshot = readRecord(run.input_snapshot);
  return String(run.product_name || snapshot?.product_name || "");
}

function shortDate(value: unknown) {
  const text = String(value || "");
  if (!text) return "-";
  return text.replace("T", " ").replace("Z", "").slice(0, 16);
}

function numberish(value: unknown) {
  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim()) return value;
  return 0;
}

function readRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}
