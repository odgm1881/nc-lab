// Типы контрактов — синхронны с Pydantic-схемами бэкенда.

export type CardStatus = 'draft' | 'validating' | 'valid' | 'error' | 'published'

export interface User {
  id: string
  email: string
  full_name: string
  role: 'client' | 'client_admin' | 'editor' | 'viewer' | 'operator' | 'admin'
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

export type ValidationRuleSetStatus = 'draft' | 'approved' | 'retired'

export interface ValidationRuleSet {
  id: string
  version: string
  title: string
  status: ValidationRuleSetStatus
  category_codes: string[]
  rule_names: string[]
  source_reference: string
  change_summary: string
  effective_from: string | null
  effective_to: string | null
  created_by: string
  approved_by: string | null
  approved_by_name: string | null
  approved_at: string | null
  created_at: string
  updated_at: string
}

export interface ValidationRuleSetList {
  items: ValidationRuleSet[]
  total: number
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
  request_fingerprint: string
  mode: 'file' | 'mock' | 'api'
  status: 'pending' | 'prepared' | 'processing' | 'succeeded' | 'failed'
  request_payload: Record<string, unknown>
  response_payload: Record<string, unknown>
  error: string | null
  error_code: string | null
  external_id: string | null
  correlation_id: string | null
  attempts: number
  retryable: boolean
  next_retry_at: string | null
  duration_ms: number | null
  last_attempt_at: string | null
  reconciliation_status: 'not_checked' | 'in_sync' | 'stale_payload' | 'remote_pending' | 'remote_failed' | 'card_missing'
  last_reconciled_at: string | null
  created_at: string
  updated_at: string
}

export interface NkExchangeList {
  items: NkExchange[]
  total: number
}

export interface NkExchangeQueueSummary {
  total: number
  failed: number
  retry_due: number
  processing: number
  stale_payload: number
}

export interface NkExchangeBulkResult {
  processed: number
  succeeded: number
  failed: number
  items: NkExchange[]
}

export interface NkIntegrationStatus {
  api_enabled: boolean
  base_url: string
  auth_method: 'api_key' | 'bearer' | 'none'
  attribute_mappings: number
  category_mappings: number
  file_mode_available: boolean
  mock_mode_available: boolean
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
  category: 'attributes' | 'gtin' | 'rd' | 'category' | 'integration' | 'other'
  note: string | null
  escalation_reason: string | null
  resolution: string | null
  priority: number
  status: 'open' | 'in_progress' | 'waiting_client' | 'resolved'
  assignee_id: string | null
  started_at: string | null
  due_at: string | null
  resolved_at: string | null
  returned_at: string | null
  is_overdue: boolean
  created_at: string
  updated_at: string
}

export interface TaskComment {
  id: string
  task_id: string
  author_id: string
  author_role: 'client' | 'operator' | 'admin'
  author_name: string
  message: string
  created_at: string
}

export interface TaskList {
  items: OperatorTask[]
  total: number
}

export interface PilotMetrics {
  generated_at: string
  cards_total: number
  cards_ready: number
  readiness_rate: number
  imported_rows_total: number
  imported_rows_without_errors: number
  import_success_rate: number | null
  imported_cards_first_pass_valid: number
  imported_cards_total: number
  first_pass_validation_rate: number | null
  median_time_to_ready_minutes: number | null
  operator_tasks_total: number
  operator_tasks_resolved: number
  operator_tasks_returned: number
  operator_return_rate: number | null
  operator_resolution_rate: number | null
  median_operator_resolution_minutes: number | null
  overdue_operator_tasks: number
  top_issue_codes: { code: string; count: number }[]
  pilot_sample_target: number
  pilot_sample_reached: boolean
  notes: string[]
}

export type PilotStatus = 'preparation' | 'running' | 'completed'

export interface Pilot {
  id: string
  client_id: string
  name: string
  description: string | null
  status: PilotStatus
  sample_target: number
  planned_start_date: string | null
  planned_end_date: string | null
  responsible: string
  participants: string[]
  baseline_time_per_card_minutes: number | null
  baseline_first_pass_rate: number | null
  baseline_return_rate: number | null
  baseline_labor_minutes_per_card: number | null
  baseline_cost_per_card: number | null
  operator_hourly_cost: number | null
  cards_count: number
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface PilotDetail extends Pilot {
  cards: Card[]
  metrics: PilotMetrics
  effect: PilotEffect
}

export interface PilotEffect {
  baseline_time_per_card_minutes: number | null
  actual_time_per_card_minutes: number | null
  time_reduction_rate: number | null
  baseline_first_pass_rate: number | null
  actual_first_pass_rate: number | null
  first_pass_change_points: number | null
  baseline_return_rate: number | null
  actual_return_rate: number | null
  return_rate_change_points: number | null
  baseline_labor_minutes_per_card: number | null
  actual_labor_minutes_per_card: number | null
  labor_reduction_rate: number | null
  baseline_cost_per_card: number | null
  actual_cost_per_card: number | null
  cost_saving_rate: number | null
  measured_indicators: number
  total_indicators: number
}

export interface PilotList {
  items: Pilot[]
  total: number
}
