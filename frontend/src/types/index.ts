// ---- Auth Types ----
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  avatar_url: string | null;
  oauth_provider: string | null;
  created_at: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserWithToken {
  user: User;
  tokens: Tokens;
}

// ---- Survey Types ----
export type SurveyStatus =
  | "pending"
  | "query_expansion"
  | "paper_retrieval"
  | "formatting"
  | "survey_generation"
  | "completed"
  | "failed";

export interface Survey {
  id: string;
  topic: string;
  status: SurveyStatus;
  progress: number;
  paper_count: number;
  expanded_queries: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface SurveyDetail extends Survey {
  survey_markdown: string | null;
  bibliography: Record<string, unknown> | null;
  taxonomy: Record<string, unknown> | null;
}

export interface SurveyList {
  surveys: Survey[];
  total: number;
}

// ---- Paper Types ----
export interface Paper {
  id: string;
  title: string;
  authors: string[] | null;
  abstract: string | null;
  year: number | null;
  venue: string | null;
  doi: string | null;
  arxiv_id: string | null;
  url: string | null;
  pdf_url: string | null;
  source: string;
  citation_count: number;
  relevance_score: number;
  ieee_number: number | null;
  ieee_citation: string | null;
  summary: string | null;
  cluster_label: string | null;
  cluster_id: number | null;
  created_at: string;
}

export interface PaperList {
  papers: Paper[];
  total: number;
}

// ---- Chat Types ----
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  cited_papers?: Record<string, unknown>[];
  sources?: string[];
  timestamp: string;
}

export interface ChatResponse {
  answer: string;
  cited_papers: Record<string, unknown>[];
  sources: string[];
}

// ---- WebSocket Types ----
export interface ProgressEvent {
  survey_id: string;
  status: SurveyStatus;
  progress: number;
  message: string;
  data?: Record<string, unknown>;
}
