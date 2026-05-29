export type GenerationMode = "both" | "video" | "static";

export type CampaignForm = {
  app_mode: "ecommerce";
  company_id: string;
  ad_vertical: string;
  brand_context: string;
  product_name: string;
  product_info: string;
  product_category: string;
  product_reference_url: string;
  competitor_strategy_enabled: boolean;
  competitor_name: string;
  competitor_url: string;
  competitor_chat_brief: string;
  competitor_screenshot_notes: string;
  avatar_id: string;
  custom_avatar_name: string;
  custom_avatar_persona: string;
  custom_avatar_voice: string;
  avatar_identity_note: string;
  avatar_reference_url: string;
  avatar_own_person_consent: boolean;
  use_avatar_image_reference: boolean;
  platform: string;
  market: string;
  language: string;
  generation_mode: GenerationMode;
  video_length: string;
  seedance_model: string;
  prompt_model: string;
  ugc_scenario_model: string;
  static_prompt_model: string;
  image_model: string;
  max_static_images: string;
  image_size: string;
  openrouter_api_key: string;
  negative_prompt: string;
  content_prompt_system: string;
  content_prompt_task: string;
  base_video_prompt_template: string;
  ugc_video_extra_prompt: string;
  background_consistency: string;
  environment_override: boolean;
  preserve_original_scene_layout: boolean;
  category_prompt_handbag: string;
  category_prompt_shoes: string;
  category_prompt_apparel: string;
};

export type Company = {
  id: string;
  name?: string;
  ad_vertical?: string;
  business_model?: string;
  market?: string;
  language?: string;
  default_platform?: string;
  creative_channels?: string[];
  product_categories?: string[];
  audience?: string;
  positioning?: string;
  brand_voice?: string;
  proof_points?: string[];
  forbidden_claims?: string[];
  creative_quality_rules?: string[];
  compliance_notes?: string;
  landing_page_url?: string;
  website_url?: string;
  default_avatar_id?: string;
  notes?: string;
  context_text?: string;
  is_default?: boolean;
};

export type Avatar = {
  id: string;
  name?: string;
  style?: string;
  voice?: string;
  image_url?: string;
  preview_url?: string;
  is_default?: boolean;
  stats?: Record<string, unknown>;
  local_image_only?: boolean;
};

export type Creative = {
  creative_id: string;
  set_id?: string | null;
  type?: string | null;
  angle?: string | null;
  status?: string | null;
  asset_url?: string | null;
  model_used?: string | null;
  generation_cost?: number | null;
  created_at?: string | null;
  campaign_id?: string | null;
  platform?: string | null;
  market?: string | null;
  workspace?: string | null;
  app_mode?: string | null;
  product_id?: string | null;
  product_name?: string | null;
  category?: string | null;
  latest_rating_status?: string | null;
  latest_user_rating?: number | null;
  rating_count?: number | null;
  performance_count?: number | null;
  latest_ctr?: number | null;
  latest_cpc?: number | null;
  latest_cpa?: number | null;
  latest_roas?: number | null;
  latest_spend?: number | null;
  avatar_id?: string | null;
  avatar_name?: string | null;
  avatar_image_url?: string | null;
};

export type ChatItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
  urls: string[];
  files: File[];
  applied_as: string[];
  created_at: string;
};

export type ParserResult = {
  version: string;
  status: string;
  parser_mode: string;
  model: string;
  campaign_draft: Partial<CampaignForm>;
  attachment_roles: Array<{ item_id: string; role: "product" | "competitor" | "avatar" | "direction"; reason: string }>;
  warnings: string[];
  ai_error?: string;
};

export type PromptSettings = {
  negative_prompt?: string;
  content_prompt_system?: string;
  content_prompt_task?: string;
  base_video_prompt_template?: string;
  environment_control_defaults?: Record<string, unknown>;
  prompt_source_inventory?: Record<string, unknown>;
  category_prompt_presets?: Record<string, string>;
};

export type IntelligenceSummary = {
  counts?: Record<string, number>;
  learning_loop?: {
    status?: string;
    steps?: Array<{ step: string; status: string }>;
  };
  best_performing_angles?: Array<Record<string, unknown>>;
  best_hooks?: string[];
  best_avatars?: Array<Record<string, unknown>>;
  prompt_recommendations?: string[];
  recent_creatives?: Creative[];
  performance_leaders?: Creative[];
};

export type LearningSnapshot = {
  status?: string;
  counts?: Record<string, number>;
  winning_patterns?: string[];
  avoid_patterns?: string[];
  recommendation?: string;
  next_generation_bias?: {
    prefer?: string[];
    avoid?: string[];
  };
};
