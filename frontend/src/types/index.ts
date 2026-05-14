export interface DocumentItem {
  id: number;
  file_name: string;
  title?: string | null;
  author?: string | null;
  year?: string | null;
  page_count: number;
  processed_pages: number;
  status: string;
  error?: string | null;
  created_at: string;
  processed_at?: string | null;
}

export interface PageItem {
  id: number;
  document_id: number;
  page_number: number;
  page_label?: string | null;
  text: string;
  ocr_used: number;
  text_length: number;
  image_path?: string | null;
}

export interface SearchResult {
  document_id: number;
  document_title?: string | null;
  file_name: string;
  page_number: number;
  matched_term: string;
  context: string;
  score: number;
  match_type: string;
  viewer_url: string;
}

export interface SearchResponse {
  query: string;
  mode: string;
  result_count: number;
  results: SearchResult[];
  notes?: string | null;
}

export interface Stats {
  document_count: number;
  page_count: number;
  indexed_pages: number;
  occurrence_count: number;
  chunk_count: number;
  embedded_chunks: number;
}

export interface SettingsStatus {
  llm_enabled: boolean;
  embedding_enabled: boolean;
  embedding_local_available: boolean;
  ocr_local_available: boolean;
  deepseek_ocr_enabled: boolean;
  llm_model: string;
  embedding_model: string;
  llm_api_base_url: string;
}
