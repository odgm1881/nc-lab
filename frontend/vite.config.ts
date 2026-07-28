import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Дев-сервер проксирует /api на бэкенд FastAPI (по умолчанию :8000).
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        onlyExplicitManualChunks: true,
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('/@ant-design/icons')) return 'ant-icons'
          if (id.includes('/antd/')) return 'antd'
          if (id.includes('/@rc-component/') || id.includes('/rc-')) return 'rc-components'
          if (id.includes('/@ant-design/cssinjs')) return 'ant-styles'
          return undefined
        },
      },
    },
  },
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
