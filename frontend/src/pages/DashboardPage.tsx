import {
  ArrowRightOutlined,
  AppstoreOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  FileTextOutlined,
  ImportOutlined,
  ProfileOutlined,
  SendOutlined,
} from '@ant-design/icons'
import { Card, Progress, Skeleton } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listCards } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import type { CardStatus } from '../types'

interface Tile {
  key: CardStatus | 'all'
  label: string
  icon: React.ReactNode
  color: string
  tint: string
}

const TILES: Tile[] = [
  { key: 'all', label: 'Всего карточек', icon: <FileTextOutlined />, color: '#0f766e', tint: 'var(--accent-soft)' },
  { key: 'draft', label: 'Черновики', icon: <ProfileOutlined />, color: '#475569', tint: '#eef1f5' },
  { key: 'error', label: 'С ошибками', icon: <CloseCircleFilled />, color: '#e11d48', tint: 'var(--error-soft)' },
  { key: 'valid', label: 'Валидны', icon: <CheckCircleFilled />, color: '#16a34a', tint: 'var(--success-soft)' },
  { key: 'published', label: 'Опубликованы', icon: <SendOutlined />, color: '#0f766e', tint: 'var(--accent-soft)' },
]

const STEPS: { key: CardStatus; label: string; color: string }[] = [
  { key: 'draft', label: 'Черновик', color: '#94a3b8' },
  { key: 'error', label: 'Ошибки', color: '#e11d48' },
  { key: 'valid', label: 'Валидны', color: '#16a34a' },
  { key: 'published', label: 'Опубликованы', color: '#0f766e' },
]

const QUICK = [
  {
    to: '/import',
    icon: <ImportOutlined />,
    title: 'Импорт номенклатуры',
    desc: 'Загрузите Excel/CSV/1С — система разберёт строки и создаст черновики.',
  },
  {
    to: '/variations',
    icon: <AppstoreOutlined />,
    title: 'Построить вариации',
    desc: 'Цвет × размер × пол → отдельные SKU и карточки (1 GTIN = 1 карточка).',
  },
  {
    to: '/catalog',
    icon: <ProfileOutlined />,
    title: 'Проверить и опубликовать',
    desc: 'Заполните GTIN и РД, прогоните валидацию, опубликуйте в НК.',
  },
]

export function DashboardPage() {
  const [counts, setCounts] = useState<Record<string, number> | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const keys: (CardStatus | 'all')[] = ['all', 'draft', 'error', 'valid', 'published', 'validating']
    Promise.all(
      keys.map((k) =>
        listCards({ status: k === 'all' ? undefined : k, limit: 1 }).then((r) => [k, r.total] as const),
      ),
    ).then((pairs) => setCounts(Object.fromEntries(pairs)))
  }, [])

  const total = counts?.all ?? 0
  const ready = (counts?.valid ?? 0) + (counts?.published ?? 0)
  const readyPct = total ? Math.round((ready / total) * 100) : 0

  return (
    <div>
      <PageHeader
        title="Обзор каталога"
        subtitle="Цепочка НК → GTIN → РД → коды. Задача — довести карточки до статуса «Валидна» и опубликовать до заказа кодов маркировки."
      />

      {/* --- стат-тайлы --- */}
      <div
        className="stagger"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 14,
          marginBottom: 18,
        }}
      >
        {TILES.map((t) => (
          <div
            key={t.key}
            className="lift tap"
            onClick={() => navigate(t.key === 'all' ? '/catalog' : `/catalog?status=${t.key}`)}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: 18,
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 'var(--r-md)',
                background: t.tint,
                color: t.color,
                display: 'grid',
                placeItems: 'center',
                fontSize: 18,
                marginBottom: 14,
              }}
            >
              {t.icon}
            </div>
            <div style={{ fontSize: 13, color: 'var(--muted)' }}>{t.label}</div>
            {counts ? (
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--ink)', fontVariantNumeric: 'tabular-nums', lineHeight: 1.2 }}>
                {t.key === 'all' ? total : counts[t.key] ?? 0}
              </div>
            ) : (
              <Skeleton.Button active size="small" style={{ width: 48, height: 30, marginTop: 4 }} />
            )}
          </div>
        ))}
      </div>

      {/* --- конвейер готовности + быстрый старт --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) minmax(0, 1fr)', gap: 16 }}>
        <Card title="Конвейер готовности" styles={{ body: { paddingTop: 18 } }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 }}>
            <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--ink)' }}>{readyPct}%</span>
            <span style={{ color: 'var(--muted)', fontSize: 14 }}>карточек готовы или опубликованы</span>
          </div>
          <Progress
            percent={readyPct}
            showInfo={false}
            strokeColor={{ from: '#14b8a6', to: '#0f766e' }}
            railColor="#eef1f5"
          />
          <div style={{ display: 'flex', gap: 10, marginTop: 20, flexWrap: 'wrap' }}>
            {STEPS.map((s) => (
              <div
                key={s.key}
                style={{
                  flex: '1 1 120px',
                  border: '1px solid var(--hairline)',
                  borderRadius: 'var(--r-md)',
                  padding: '12px 14px',
                  background: 'var(--surface-2)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.color }} />
                  <span style={{ fontSize: 13, color: 'var(--muted)' }}>{s.label}</span>
                </div>
                <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--ink)', marginTop: 4, fontVariantNumeric: 'tabular-nums' }}>
                  {counts ? counts[s.key] ?? 0 : '—'}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="С чего начать" styles={{ body: { padding: 8 } }}>
          {QUICK.map((q) => (
            <button
              key={q.to}
              className="tap"
              onClick={() => navigate(q.to)}
              style={{
                display: 'flex',
                width: '100%',
                gap: 14,
                alignItems: 'center',
                textAlign: 'left',
                padding: '14px',
                border: 'none',
                background: 'transparent',
                borderRadius: 'var(--r-md)',
                cursor: 'pointer',
                transition: 'background 160ms var(--ease-out)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-2)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <span
                style={{
                  flexShrink: 0,
                  width: 38,
                  height: 38,
                  borderRadius: 'var(--r-md)',
                  background: 'var(--accent-soft)',
                  color: 'var(--accent)',
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: 17,
                }}
              >
                {q.icon}
              </span>
              <span style={{ flex: 1, minWidth: 0 }}>
                <span style={{ display: 'block', fontWeight: 600, color: 'var(--ink)', fontSize: 14 }}>{q.title}</span>
                <span style={{ display: 'block', color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.5 }}>{q.desc}</span>
              </span>
              <ArrowRightOutlined style={{ color: 'var(--faint)' }} />
            </button>
          ))}
        </Card>
      </div>
    </div>
  )
}
