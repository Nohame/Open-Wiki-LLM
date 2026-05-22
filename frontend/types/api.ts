export interface WikiPageSummary {
  slug: string
  title: string
  type: string
  status: string
  confidence: string
  sources: string[]
  updated_at: string
  tags: string[]
}

export interface WikiPage extends WikiPageSummary {
  content: string
  stale: boolean
}

export interface SearchResult {
  slug: string
  title: string
  snippet: string
  score: number
}

export interface AnswerResponse {
  answer: string
  mode: string
  sources: string[]
}

export interface IngestResult {
  slug: string
  raw_path: string
  wiki_path: string
  title: string
  pages_updated: string[]
  concepts_created: string[]
  entities_created: string[]
  stale_marked: string[]
}

export interface PageReferences {
  slug: string
  references: string[]
  referenced_by: string[]
}

export interface LogResponse {
  content: string
}

export type AnswerMode = 'validated_only' | 'strict' | 'draft' | 'source_only'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

export interface OllamaConfig {
  base_url: string
  model: string
  vision_model: string
}

export interface OpenAIConfig {
  api_key: string
  model: string
  vision_model: string
}

export interface GeminiConfig {
  api_key: string
  model: string
  vision_model: string
}

export interface AnthropicConfig {
  api_key: string
  model: string
  vision_model: string
}

export interface CustomConfig {
  base_url: string
  api_key: string
  model: string
  vision_model: string
}

export interface LLMConfig {
  provider: 'ollama' | 'openai' | 'gemini' | 'anthropic' | 'custom'
  ollama: OllamaConfig
  openai: OpenAIConfig
  gemini: GeminiConfig
  anthropic: AnthropicConfig
  custom: CustomConfig
}

export interface IngestConfig {
  max_text_chars: number
}

export interface AppSettings {
  llm: LLMConfig
  ingest: IngestConfig
}
