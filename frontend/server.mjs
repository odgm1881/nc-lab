// Крошечный статик-сервер + reverse-proxy без зависимостей.
// Отдаёт собранный SPA из ./dist и проксирует /api на бэкенд (сервис api).
// Нужен только образ node:22-alpine — nginx в контейнере не требуется.
import http from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'

const PORT = Number(process.env.PORT || 80)
const UPSTREAM = new URL(process.env.API_UPSTREAM || 'http://api:8000')
const DIST = fileURLToPath(new URL('./dist/', import.meta.url))
const INDEX = join(DIST, 'index.html')

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.map': 'application/json',
}

function proxy(req, res) {
  const upstream = http.request(
    {
      host: UPSTREAM.hostname,
      port: UPSTREAM.port || 80,
      method: req.method,
      path: req.url,
      headers: { ...req.headers, host: UPSTREAM.host },
    },
    (pr) => {
      res.writeHead(pr.statusCode || 502, pr.headers)
      pr.pipe(res)
    },
  )
  upstream.on('error', () => {
    res.writeHead(502, { 'content-type': 'text/plain' })
    res.end('upstream unavailable')
  })
  req.pipe(upstream)
}

async function serveStatic(req, res) {
  try {
    const path = decodeURIComponent((req.url || '/').split('?')[0])
    let file = normalize(join(DIST, path === '/' ? '/index.html' : path))
    if (!file.startsWith(DIST)) {
      res.writeHead(403)
      res.end()
      return
    }
    const info = await stat(file).catch(() => null)
    if (!info || info.isDirectory()) file = INDEX // SPA-фолбэк на index.html
    const data = await readFile(file)
    res.writeHead(200, { 'content-type': MIME[extname(file)] || 'application/octet-stream' })
    res.end(data)
  } catch {
    // маршрут React Router → отдаём index.html
    const data = await readFile(INDEX).catch(() => null)
    if (data) {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
      res.end(data)
    } else {
      res.writeHead(404)
      res.end('not found')
    }
  }
}

http
  .createServer((req, res) => {
    if ((req.url || '').startsWith('/api')) proxy(req, res)
    else serveStatic(req, res)
  })
  .listen(PORT, () => console.log(`web on :${PORT} → ${UPSTREAM.href}`))
