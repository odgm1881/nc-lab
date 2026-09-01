// Функции-обёртки над эндпоинтами бэкенда. Без лишних абстракций.
import { api } from './client'
import type {
  Card,
  CardList,
  CardValidateResponse,
  AuditEvent,
  ImportCommit,
  ImportJob,
  ImportPreview,
  MappingProfile,
  ModelsList,
  NkExchange,
  NkExchangeBulkResult,
  NkExchangeList,
  NkExchangeQueueSummary,
  NkIntegrationStatus,
  OperatorTask,
  PilotMetrics,
  PilotDetail,
  PilotList,
  TaskList,
  TaskComment,
  User,
  ValidateAllResult,
  ValidationResult,
  ValidationRuleSet,
  ValidationRuleSetList,
  VariationPreview,
} from '../types'

// --- auth ---
export const login = (email: string, password: string) =>
  api.post<{ access_token: string }>('/auth/login', { email, password }).then((r) => r.data)

export const register = (payload: {
  email: string
  password: string
  full_name: string
  client_name: string
  inn?: string
}) => api.post<User>('/auth/register', payload).then((r) => r.data)

export const me = () => api.get<User>('/auth/me').then((r) => r.data)

export const listTeamUsers = () => api.get<User[]>('/auth/users').then((r) => r.data)

export const createTeamUser = (payload: {
  email: string
  password: string
  full_name: string
  role: 'client_admin' | 'editor' | 'viewer'
}) => api.post<User>('/auth/users', payload).then((r) => r.data)

export const updateTeamUserRole = (
  userId: string,
  role: 'client_admin' | 'editor' | 'viewer',
) => api.patch<User>(`/auth/users/${userId}/role`, { role }).then((r) => r.data)

// --- версии правил валидации ---
export const listValidationRuleSets = () =>
  api.get<ValidationRuleSetList>('/validation/rulesets').then((r) => r.data)

export const createValidationRuleSet = (payload: {
  version: string
  title: string
  category_codes: string[]
  source_reference: string
  change_summary: string
  effective_from: string
  effective_to?: string | null
}) => api.post<ValidationRuleSet>('/validation/rulesets', payload).then((r) => r.data)

export const approveValidationRuleSet = (id: string, expertName?: string) =>
  api
    .post<ValidationRuleSet>(`/validation/rulesets/${id}/approve`, {
      expert_name: expertName || null,
    })
    .then((r) => r.data)

export const retireValidationRuleSet = (id: string) =>
  api.post<ValidationRuleSet>(`/validation/rulesets/${id}/retire`).then((r) => r.data)

export const validationRuleSetHistory = (id: string) =>
  api.get<AuditEvent[]>(`/validation/rulesets/${id}/history`).then((r) => r.data)

// --- cards ---
export const listCards = (params: {
  status?: string
  category_code?: string
  name?: string
  search?: string
  limit?: number
  offset?: number
}) => api.get<CardList>('/cards', { params }).then((r) => r.data)

export const listModels = (search?: string) =>
  api.get<ModelsList>('/cards/models', { params: { search } }).then((r) => r.data)

export const validateAll = () =>
  api.post<ValidateAllResult>('/cards/validate-all').then((r) => r.data)

export const getCard = (id: string) => api.get<Card>(`/cards/${id}`).then((r) => r.data)

export const createCard = (payload: Partial<Card>) =>
  api.post<Card>('/cards', payload).then((r) => r.data)

export const updateCard = (id: string, payload: Partial<Card>) =>
  api.patch<Card>(`/cards/${id}`, payload).then((r) => r.data)

export const deleteCard = (id: string) => api.delete(`/cards/${id}`).then((r) => r.data)

export const validateCard = (id: string) =>
  api.post<CardValidateResponse>(`/cards/${id}/validate`).then((r) => r.data)

export const markCardReady = (id: string) =>
  api.post<Card>(`/cards/${id}/ready`).then((r) => r.data)

export const buildFromVariations = (payload: {
  name: string
  base_vendor_code: string
  category_code?: string
  common_attributes: Record<string, string>
  rd_data: Record<string, string>
  colors: string[]
  sizes: string[]
  genders: string[]
  completeness: string[]
}) =>
  api
    .post<{ created: number; cards: Card[] }>('/cards/build-from-variations', payload)
    .then((r) => r.data)

export const cardHistory = (id: string) =>
  api.get<AuditEvent[]>(`/cards/${id}/history`).then((r) => r.data)

export const bulkUpdateCards = (payload: {
  ids: string[]
  category_code?: string
  data_source?: string
  service_comment?: string
  attributes?: Record<string, string>
  packaging?: Record<string, string>
}) => api.patch<{ updated: number }>('/cards/bulk', payload).then((r) => r.data)

export const exportCards = (payload: {
  ids?: string[]
  status?: string
  name?: string
  search?: string
}) => api.post<Blob>('/cards/export', payload, { responseType: 'blob' }).then((r) => r.data)

// --- файловый / sandbox-обмен с Национальным каталогом ---
export const prepareNkExchange = (cardId: string, idempotencyKey: string) =>
  api
    .post<NkExchange>('/integration/nk/exchanges', {
      card_id: cardId,
      mode: 'file',
      idempotency_key: idempotencyKey,
    })
    .then((r) => r.data)

export const downloadNkPayload = (exchangeId: string) =>
  api
    .get<Blob>(`/integration/nk/exchanges/${exchangeId}/payload`, { responseType: 'blob' })
    .then((r) => r.data)

export const nkIntegrationStatus = () =>
  api.get<NkIntegrationStatus>('/integration/nk/status').then((r) => r.data)

export const sendNkExchange = (cardId: string, idempotencyKey: string) =>
  api
    .post<NkExchange>('/integration/nk/exchanges', {
      card_id: cardId,
      mode: 'api',
      idempotency_key: idempotencyKey,
    })
    .then((r) => r.data)

export const refreshNkExchange = (exchangeId: string) =>
  api.post<NkExchange>(`/integration/nk/exchanges/${exchangeId}/refresh`).then((r) => r.data)

export const listNkExchanges = (params?: {
  status?: string
  reconciliation_status?: string
  limit?: number
  offset?: number
}) => api.get<NkExchangeList>('/integration/nk/exchanges', { params }).then((r) => r.data)

export const retryNkExchange = (exchangeId: string) =>
  api.post<NkExchange>(`/integration/nk/exchanges/${exchangeId}/retry`).then((r) => r.data)

export const reconcileNkExchange = (exchangeId: string) =>
  api.post<NkExchange>(`/integration/nk/exchanges/${exchangeId}/reconcile`).then((r) => r.data)

export const retryDueNkExchanges = (limit = 100) =>
  api
    .post<NkExchangeBulkResult>('/integration/nk/exchanges-queue/retry-due', null, {
      params: { limit },
    })
    .then((r) => r.data)

export const nkExchangeQueueSummary = () =>
  api
    .get<NkExchangeQueueSummary>('/integration/nk/exchanges-queue/summary')
    .then((r) => r.data)

// --- variations ---
export const previewVariations = (payload: {
  base_vendor_code: string
  colors: string[]
  sizes: string[]
  genders: string[]
  completeness: string[]
}) => api.post<VariationPreview>('/variations/preview', payload).then((r) => r.data)

// --- validation / gtin / rd (разовые проверки) ---
export const checkValidation = (payload: {
  category_code?: string
  gtin?: string
  attributes: Record<string, unknown>
  rd_data: Record<string, unknown>
}) => api.post<ValidationResult>('/validation/check', payload).then((r) => r.data)

export const checkGtin = (gtin: string) =>
  api.post<{ valid: boolean; message: string }>('/gtin/check', { gtin }).then((r) => r.data)

// --- import ---
export const importPreview = (file: File, source?: string, profileId?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (source) form.append('source', source)
  if (profileId) form.append('profile_id', profileId)
  return api
    .post<ImportPreview>('/import/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const importCommit = (file: File, source?: string, profileId?: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('create_cards', 'true')
  if (source) form.append('source', source)
  if (profileId) form.append('profile_id', profileId)
  return api
    .post<ImportCommit>('/import/commit', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const listMappingProfiles = () =>
  api.get<MappingProfile[]>('/import/mapping-profiles').then((r) => r.data)

export const createMappingProfile = (payload: {
  name: string
  source: 'excel' | 'csv' | 'onec'
  mapping: Record<string, string>
}) => api.post<MappingProfile>('/import/mapping-profiles', payload).then((r) => r.data)

export const deleteMappingProfile = (id: string) => api.delete(`/import/mapping-profiles/${id}`)

export const downloadImportErrorReport = (jobId: string) =>
  api
    .get<Blob>(`/import/jobs/${jobId}/error-report`, { responseType: 'blob' })
    .then((r) => r.data)

export const listImportJobs = () => api.get<ImportJob[]>('/import/jobs').then((r) => r.data)

// --- operator ---
export const listTasks = (params?: {
  status?: string
  client_id?: string
  assignee_id?: string
  overdue?: boolean
  sort_by?: 'priority' | 'due_at' | 'created_at'
  sort_order?: 'asc' | 'desc'
}) => api.get<TaskList>('/operator/tasks', { params }).then((r) => r.data)

export const listMyTasks = (cardId?: string) =>
  api.get<TaskList>('/operator/my-tasks', { params: { card_id: cardId } }).then((r) => r.data)

export const updateTask = (
  id: string,
  payload: {
    status?: string
    category?: string
    priority?: number
    note?: string | null
    assignee_id?: string | null
    escalation_reason?: string | null
    resolution?: string | null
    due_at?: string | null
  },
) => api.patch<OperatorTask>(`/operator/tasks/${id}`, payload).then((r) => r.data)

export const createTask = (payload: {
  card_id?: string
  title: string
  category?: string
  note?: string
  escalation_reason?: string
  due_at?: string
  priority?: number
}) => api.post<OperatorTask>('/operator/tasks', payload).then((r) => r.data)

export const bulkAssignTasks = (ids: string[], assigneeId: string) =>
  api
    .patch<{ updated: number }>('/operator/tasks/bulk-assign', {
      ids,
      assignee_id: assigneeId,
    })
    .then((r) => r.data)

export const listTaskComments = (id: string) =>
  api.get<TaskComment[]>(`/operator/tasks/${id}/comments`).then((r) => r.data)

export const addTaskComment = (id: string, message: string) =>
  api.post<TaskComment>(`/operator/tasks/${id}/comments`, { message }).then((r) => r.data)

export const taskHistory = (id: string) =>
  api.get<AuditEvent[]>(`/operator/tasks/${id}/history`).then((r) => r.data)

// --- пилотные KPI ---
export const getPilotMetrics = () =>
  api.get<PilotMetrics>('/pilot/metrics').then((r) => r.data)

export const downloadPilotMetrics = () =>
  api.get<Blob>('/pilot/metrics.csv', { responseType: 'blob' }).then((r) => r.data)

// --- управляемые пилоты ---
export interface PilotPayload {
  name: string
  description?: string | null
  sample_target?: number
  planned_start_date?: string | null
  planned_end_date?: string | null
  responsible?: string
  participants?: string[]
  baseline_time_per_card_minutes?: number | null
  baseline_first_pass_rate?: number | null
  baseline_return_rate?: number | null
  baseline_labor_minutes_per_card?: number | null
  baseline_cost_per_card?: number | null
  operator_hourly_cost?: number | null
}

export const listPilots = () => api.get<PilotList>('/pilots').then((r) => r.data)

export const getPilot = (id: string) =>
  api.get<PilotDetail>(`/pilots/${id}`).then((r) => r.data)

export const createPilot = (payload: PilotPayload) =>
  api.post<PilotDetail>('/pilots', payload).then((r) => r.data)

export const updatePilot = (id: string, payload: Partial<PilotPayload>) =>
  api.patch<PilotDetail>(`/pilots/${id}`, payload).then((r) => r.data)

export const addPilotCards = (id: string, cardIds: string[]) =>
  api.post<PilotDetail>(`/pilots/${id}/cards`, { card_ids: cardIds }).then((r) => r.data)

export const removePilotCard = (id: string, cardId: string) =>
  api.delete<PilotDetail>(`/pilots/${id}/cards/${cardId}`).then((r) => r.data)

export const startPilot = (id: string) =>
  api.post<PilotDetail>(`/pilots/${id}/start`).then((r) => r.data)

export const completePilot = (id: string) =>
  api.post<PilotDetail>(`/pilots/${id}/complete`).then((r) => r.data)

export const downloadPilotReport = (id: string) =>
  api.get<Blob>(`/pilots/${id}/report.csv`, { responseType: 'blob' }).then((r) => r.data)
