// Типы контрактов — синхронны с Pydantic-схемами бэкенда.

export type CardStatus = 'draft' | 'validating' | 'valid' | 'error' | 'published'

export interface User {
  id: string
  email: string
  full_name: string
  role: 'client' | 'operator' | 'admin'
  client_id: string | null
}

export interface Issue {
  code: string
  severity: 'error' | 'warning' | 'info'
  message: string
  field?: string | null
}

export interface Card {
  id: string
  client_id: string
  name: string
  vendor_code: string
  category_code: string | null
  gtin: string | null
  status: CardStatus
  attributes: Record<string, unknown>
  rd_data: Record<string, unknown>
  validation_issues: Issue[]
  created_at: string
  updated_at: string
}

export interface CardList {
  items: Card[]
  total: number
}

export interface ValidationResult {
  is_valid: boolean
  errors: Issue[]
  warnings: Issue[]
  issues: Issue[]
}

export interface CardValidateResponse {
  card: Card
  result: ValidationResult
}

export interface VariationPreview {
  count: number
  variations: {
    sku: string
    color?: string | null
    size?: string | null
    gender?: string | null
    completeness?: string | null
  }[]
}

export interface NomenclatureRow {
  name: string
  vendor_code: string
  category_code: string | null
  gtin: string | null
  attributes: Record<string, string>
  rd_data: Record<string, string>
}

export interface ImportPreview {
  source: string
  rows_total: number
  rows: NomenclatureRow[]
}

export interface ImportCommit {
  job_id: string
  source: string
  rows_total: number
  cards_created: number
}

export interface OperatorTask {
  id: string
  client_id: string
  card_id: string | null
  title: string
  note: string | null
  priority: number
  status: 'open' | 'in_progress' | 'resolved'
  assignee_id: string | null
  created_at: string
  updated_at: string
}

export interface TaskList {
  items: OperatorTask[]
  total: number
}
