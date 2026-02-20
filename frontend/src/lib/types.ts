// ============================================================
// API Types (mirror backend Pydantic models)
// ============================================================

export interface SourceInfo {
  title: string;
  source_file: string;
  context_header: string;
  relevance: string;
  source_type: string;
  document: string;
  score: number;
  chunk_id: string;
  statute_numbers: string;
  case_citations: string;
}

export interface ResponseFlags {
  LOW_CONFIDENCE: boolean;
  OUTDATED_POSSIBLE: boolean;
  JURISDICTION_NOTE: boolean;
  USE_OF_FORCE_CAUTION: boolean;
}

export interface ChatRequest {
  query: string;
  session_id?: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceInfo[];
  confidence_score: number;
  flags: ResponseFlags;
  disclaimer: string;
}

export interface SearchRequest {
  query: string;
  n_results: number;
}

export interface SearchResult {
  id: string;
  document: string;
  metadata: Record<string, unknown>;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  enhanced_query: Record<string, unknown>;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  collection_count: number;
}

// ============================================================
// Application Types
// ============================================================

export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  sources?: SourceInfo[];
  confidence_score?: number;
  flags?: ResponseFlags;
  disclaimer?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  session_id: string;
  created_at: number;
  updated_at: number;
}

export interface QuickAction {
  id: string;
  label: string;
  query: string;
  icon: string;
  description: string;
}
