export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "user" | "admin";
  is_active: boolean;
  avatar_url?: string | null;
  preferences?: Record<string, unknown>;
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface SourceChunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  doc_title: string;
  section_number?: string;
  page?: number;
  score: number;
  rank?: number;
  [key: string]: unknown;
}

export interface Citation {
  id: string;
  chunk_id: string;
  doc_title: string;
  section_number?: string;
  page?: number;
  text: string;
  source_index?: number;
  verified: boolean;
  overlap?: number;
  [key: string]: unknown;
}

export interface VerificationReport {
  verified_citations: number;
  unverified_citations: number;
  missing_citations: number;
  average_overlap: number;
  verdict: "verified" | "partially_verified" | "unverified";
  details?: Record<string, unknown>;
}

export interface HallucinationFinding {
  category: string;
  severity: "low" | "medium" | "high";
  detail: string;
  sentence?: string;
  evidence_score?: number;
}

export interface HallucinationReport {
  score: number;
  verdict: "low" | "medium" | "high";
  findings: HallucinationFinding[];
}

export interface ConfidenceReport {
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  context_recall: number;
  overall: number;
}

export interface Conversation {
  id: string;
  title: string;
  is_pinned: boolean;
  model?: string | null;
  collection?: string | null;
  created_at: string;
  updated_at: string;
  last_message_at?: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources: SourceChunk[];
  citations: Citation[];
  verification?: VerificationReport | null;
  hallucination?: HallucinationReport | null;
  confidence?: ConfidenceReport | null;
  quality_score: number;
  latency_ms: number;
  tokens: number;
  created_at: string;
}

export interface ChatMessage {
  id?: string | null;
  conversation_id?: string | null;
  role: "user" | "assistant" | "system";
  content: string;
  sources: SourceChunk[];
  citations: Citation[];
  verification?: VerificationReport | null;
  hallucination?: HallucinationReport | null;
  confidence?: ConfidenceReport | null;
  quality_score: number;
  latency_ms: number;
  tokens: number;
  created_at?: string | null;
  streaming?: boolean;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ShareView {
  id: string;
  title: string;
  messages: Message[];
  created_at?: string;
  updated_at?: string;
}

export interface Job {
  job_id: string;
  kind: string;
  status: string;
  progress: number;
  message?: string;
  error?: string;
  stats?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SearchHit {
  chunk_id: string;
  doc_id: string;
  score: number;
  text: string;
  summary?: string | null;
  metadata: Record<string, unknown>;
  dense_score?: number | null;
  lexical_score?: number | null;
}

export interface SystemStats {
  users: number;
  conversations: number;
  messages: number;
  qdrant_points: number;
  uptime_seconds: number;
}
