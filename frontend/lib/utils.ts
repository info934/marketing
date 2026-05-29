import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function appendBlock(current: string | undefined, next: string | undefined) {
  const clean = String(next || "").trim();
  if (!clean) return current || "";
  const existing = String(current || "").trim();
  return existing ? `${existing}\n\n${clean}` : clean;
}

export function urlsFromText(text: string) {
  return Array.from(new Set((text.match(/https?:\/\/\S+/g) || []).map(cleanUrlCandidate).filter(Boolean)));
}

export function directImageUrlsFromText(text: string) {
  return urlsFromText(text).filter(isDirectImageUrl);
}

export function isDirectImageUrl(value: string) {
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

function cleanUrlCandidate(value: string) {
  let url = value.trim().replace(/^["'<]+/, "");
  while (/[.,;:!?'">`\]]$/.test(url)) {
    url = url.slice(0, -1);
  }
  while (url.endsWith(")") && countChar(url, ")") > countChar(url, "(")) {
    url = url.slice(0, -1);
  }
  return url;
}

function countChar(value: string, char: string) {
  return Array.from(value).filter((item) => item === char).length;
}
