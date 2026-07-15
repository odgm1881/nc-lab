import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Дев-сервер проксирует /api на бэкенд FastAPI (по умолчанию :8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
