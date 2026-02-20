import { API_BASE } from "./constants";
import type {
  ChatRequest,
  ChatResponse,
  SearchRequest,
  SearchResponse,
  HealthResponse,
} from "./types";

class APIError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "APIError";
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new APIError(body || res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  chat(data: ChatRequest): Promise<ChatResponse> {
    return request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  search(data: SearchRequest): Promise<SearchResponse> {
    return request<SearchResponse>("/search", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },
};
