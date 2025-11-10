// Configuration types
export interface MultiQueryConfig {
  enabled: boolean;
  num_queries: number;
}

export interface RAGFusionConfig {
  enabled: boolean;
  num_queries: number;
  rrf_k: number;
}

export interface DecompositionConfig {
  enabled: boolean;
  mode: "recursive" | "individual";
  max_sub_questions: number;
}

export interface StepBackConfig {
  enabled: boolean;
  include_original: boolean;
}

export interface HyDEConfig {
  enabled: boolean;
}

export interface RerankingConfig {
  enabled: boolean;
  provider: "cohere" | "custom";
  top_k: number;
  top_n: number;
}

export interface RAGConfig {
  chunk_size: number;
  chunk_overlap: number;
  retrieval_k: number;
  temperature: number;
  model_name: string;
  multi_query: MultiQueryConfig;
  rag_fusion: RAGFusionConfig;
  decomposition: DecompositionConfig;
  step_back: StepBackConfig;
  hyde: HyDEConfig;
  reranking: RerankingConfig;
}

// Query types
export interface Source {
  document_id: string;
  page_title: string;
  notebook_name: string;
  section_name: string;
  content_snippet: string;
  relevance_score: number;
  url: string;
}

export interface ResponseMetadata {
  techniques_used: string[];
  latency_ms: number;
  tokens_used?: number;
  cost_usd?: number;
  timestamp: string;
  model_name: string;
  retrieval_k: number;
}

export interface ImageReference {
page_id: string;
page_title: string;
image_index: number;
image_path: string;
public_url: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  metadata: ResponseMetadata;
  images?: ImageReference[];
}

export interface QueryRequest {
  question: string;
  config?: RAGConfig;
  session_id?: string;
}

// Index types
export interface IndexStats {
  total_documents: number;
  collection_name: string;
  persist_directory: string;
}

export interface SyncResponse {
  status: string;
  documents_processed: number;
  documents_added: number;
  documents_updated: number;
  documents_skipped: number;
  chunks_created: number;
  message: string;
}

// Conversation types for chat interface
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: ResponseMetadata;
  sources?: Source[];
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  config?: RAGConfig;
}

// Data Source types
export interface Notebook {
  id: string;
  displayName: string;
  createdDateTime?: string;
  lastModifiedDateTime?: string;
}

export interface Section {
  id: string;
  displayName: string;
  parentNotebook?: {
    id: string;
    displayName: string;
  };
}

export interface Page {
  id: string;
  title: string;
  lastModifiedDateTime?: string;
  contentUrl?: string;
}

export interface SyncHistory {
  timestamp: Date;
  status: 'success' | 'error';
  documentsAdded: number;
  documentsUpdated: number;
  documentsSkipped: number;
  chunksCreated: number;
  message: string;
}
