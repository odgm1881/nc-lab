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
  packaging: Record<string, unknown>
  data_source: string
  service_comment: string | null
  ruleset_version: string | null
  reference_data_version: string | null
  created_at: string
  updated_at: string
}

export interface CardList {
  items: Card[]
  total: number
}

export interface ValidationResult {
  ruleset_version: string
  reference_data_version: string
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
  rows_success: number
  rows_error: number
}

export interface ImportJob {
  id: string
  filename: string
  source: string
  status: string
  rows_total: number
  cards_created: number
  rows_success: number
  rows_error: number
  error: string | null
  created_at: string
}

export interface MappingProfile {
  id: string
  name: string
  source: 'excel' | 'csv' | 'onec'
  mapping: Record<string, string>
  created_at: string
  updated_at: string
}

export interface AuditEvent {
  id: string
  actor_id: string | null
  action: string
  entity_type: string
  entity_id: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  details: Record<string, unknown>
  correlation_id: string | null
  created_at: string
}

export interface NkExchange {
  id: string
  client_id: string
  card_id: string
  idempotency_key: string
  mode: 'file' | 'mock'
  status: 'pending' | 'prepared' | 'succeeded' | 'failed'
  response_payload: Record<string, unknown>
  error: string | null
  attempts: number
  created_at: string
  updated_at: string
}

export interface ModelGroup {
  name: string
  category_code: string | null
  total: number
  counts: Record<string, number>
}

export interface ModelsList {
  items: ModelGroup[]
}

export interface ValidateAllResult {
  validated: number
  valid: number
  error: number
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
