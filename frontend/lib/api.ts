import type { Avatar, CampaignForm, ChatItem, Company, Creative, IntelligenceSummary, LearningSnapshot, OrchestratorSnapshot, ParserResult, PromptSettings } from "@/lib/types";

export async function apiJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.error || data.reason || `HTTP ${response.status}`);
  }
  return data as T;
}

export function parserPayload(items: ChatItem[], form: CampaignForm) {
  return {
    chatBriefItems: items.map((item) => ({
      id: item.id,
      text: item.text,
      urls: item.urls,
      file_count: item.files.length,
      file_names: item.files.map((file) => file.name || "image"),
      applied_as: item.applied_as,
    })),
    current_form: form,
    openrouter_api_key: form.openrouter_api_key,
    prompt_model: form.prompt_model,
  };
}

export async function parseChatBrief(items: ChatItem[], form: CampaignForm): Promise<ParserResult> {
  return apiJson<ParserResult>("/api/backend/chat-brief-parser", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parserPayload(items, form)),
  });
}

export async function startGeneration(form: CampaignForm, productFile: File | null, staticProductFiles: File[], competitorFiles: File[]) {
  const body = new FormData();
  Object.entries(form).forEach(([key, value]) => {
    body.set(key, typeof value === "boolean" ? String(value) : String(value ?? ""));
  });
  body.set("generate_static_images", "true");
  body.set("testimonial_mode", "false");
  body.set("idempotency_key", `next-chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  if (productFile) body.set("product_image", productFile);
  staticProductFiles.forEach((file) => body.append("product_static_images", file));
  competitorFiles.forEach((file) => body.append("competitor_screenshots", file));
  return apiJson<Record<string, unknown>>("/api/backend/generation-runs", {
    method: "POST",
    body,
  });
}

export async function getAvatars() {
  return apiJson<{ avatars: Avatar[]; default_avatar_id?: string; stats?: Record<string, unknown> }>("/api/backend/avatars");
}

export async function getCompanies() {
  return apiJson<{ companies: Company[]; default_company_id?: string }>("/api/backend/companies");
}

export async function getOrchestrator() {
  return apiJson<OrchestratorSnapshot>("/api/backend/orchestrator");
}

export async function saveCompany(profile: Partial<Company> & { id?: string }) {
  return apiJson<{ status: string; company: Company }>("/api/backend/companies", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
}

export async function makeDefaultCompany(companyId: string) {
  return apiJson<{ status: string; company: Company; default_company_id: string }>(`/api/backend/companies/${encodeURIComponent(companyId)}/default`, {
    method: "POST",
  });
}

export async function saveAvatar(profile: Partial<Avatar> & { id?: string }) {
  return apiJson<{ status: string; avatar: Avatar }>("/api/backend/avatars", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
}

export async function uploadAvatarProfile(profile: Partial<Avatar> & { id?: string }, imageFile: File | null) {
  const body = new FormData();
  body.set("id", profile.id || "");
  body.set("avatar_id", profile.id || "");
  body.set("name", profile.name || "");
  body.set("style", profile.style || "");
  body.set("voice", profile.voice || "");
  body.set("image_url", profile.image_url || "");
  if (profile.is_default) body.set("is_default", "true");
  if (imageFile) body.set("avatar_image", imageFile);
  return apiJson<{ status: string; avatar: Avatar }>("/api/backend/avatars/upload", {
    method: "POST",
    body,
  });
}

export async function makeDefaultAvatar(avatarId: string) {
  return apiJson<{ status: string; avatar: Avatar; default_avatar_id: string }>(`/api/backend/avatars/${encodeURIComponent(avatarId)}/default`, {
    method: "POST",
  });
}

export async function getCreatives(limit = 80) {
  return apiJson<{ count: number; creatives: Creative[] }>(`/api/backend/creative-memory/creatives?limit=${limit}`);
}

export async function saveCreativeRating(payload: Record<string, unknown>) {
  return apiJson<Record<string, unknown>>("/api/backend/creative-rating", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function saveCreativePerformance(payload: Record<string, unknown>) {
  return apiJson<Record<string, unknown>>("/api/backend/performance-import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getLatestRun() {
  return apiJson<Record<string, unknown>>("/api/backend/generation-runs/latest");
}

export async function getGenerationRuns(limit = 80) {
  return apiJson<{ status: string; count: number; runs: Array<Record<string, unknown>>; total_known_cost_usd_display?: string; total_known_cost?: number }>(
    `/api/backend/generation-runs?limit=${limit}`,
  );
}

export async function getGenerationRun(runId: string) {
  return apiJson<Record<string, unknown>>(`/api/backend/generation-runs/${encodeURIComponent(runId)}`);
}

export async function cancelGenerationRun(runId: string) {
  return apiJson<Record<string, unknown>>(`/api/backend/generation-runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
  });
}

export async function getPromptSettings() {
  return apiJson<PromptSettings>("/api/backend/prompt-settings");
}

export async function getCreativeIntelligence() {
  return apiJson<IntelligenceSummary>("/api/backend/creative-intelligence");
}

export async function getLearningSnapshot() {
  return apiJson<LearningSnapshot>("/api/backend/creative-memory/learning");
}

export async function getProviderCapabilities() {
  return apiJson<Record<string, unknown>>("/api/backend/provider-capabilities");
}
