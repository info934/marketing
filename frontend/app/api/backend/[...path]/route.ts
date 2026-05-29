import { NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_WORKFLOW_BACKEND_URL || "http://127.0.0.1:8001";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const target = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  const init: RequestInit = {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  };
  const response = await fetch(target, init);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}
