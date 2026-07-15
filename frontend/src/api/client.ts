// Тонкий axios-клиент. Токен подставляется интерцептором из localStorage.
import axios from 'axios'

export const TOKEN_KEY = 'nklab_token'

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Достаём человекочитаемое сообщение об ошибке из ответа бэкенда.
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { error?: { message?: string }; detail?: unknown }
    if (data?.error?.message) return data.error.message
    if (typeof data?.detail === 'string') return data.detail
    return err.message
  }
  return 'Неизвестная ошибка'
}
