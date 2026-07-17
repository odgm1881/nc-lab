// Функции-обёртки над эндпоинтами бэкенда. Без лишних абстракций.
import { api } from './client'
import type {
  Card,
  CardList,
  CardValidateResponse,
  ImportCommit,
  ImportPreview,
  ModelsList,
  TaskList,
  User,
  ValidateAllResult,
  ValidationResult,
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

export const publishCard = (id: string) =>
  api.post<Card>(`/cards/${id}/publish`).then((r) => r.data)

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
export const importPreview = (file: File, source?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (source) form.append('source', source)
  return api
    .post<ImportPreview>('/import/preview', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

export const importCommit = (file: File, source?: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('create_cards', 'true')
  if (source) form.append('source', source)
  return api
    .post<ImportCommit>('/import/commit', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data)
}

// --- operator ---
export const listTasks = (status?: string) =>
  api.get<TaskList>('/operator/tasks', { params: { status } }).then((r) => r.data)

export const updateTask = (
  id: string,
  payload: { status?: string; priority?: number; note?: string },
) => api.patch(`/operator/tasks/${id}`, payload).then((r) => r.data)

export const createTask = (payload: { card_id?: string; title: string; priority?: number }) =>
  api.post('/operator/tasks', payload).then((r) => r.data)
