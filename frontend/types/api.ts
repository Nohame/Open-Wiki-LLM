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
}

export type AnswerMode = 'validated_only' | 'strict' | 'draft' | 'source_only'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}
