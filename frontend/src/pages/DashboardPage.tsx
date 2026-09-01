import {
  ArrowRightOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  DownloadOutlined,
  FileTextOutlined,
  ImportOutlined,
  ProfileOutlined,
  SendOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons'
import { Alert, App, Button, Card, Modal, Skeleton, Steps, Tag } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { downloadPilotMetrics, getPilotMetrics, listCards } from '../api/endpoints'
import { errorMessage } from '../api/client'
import { PageHeader } from '../components/PageHeader'
import type { CardStatus, PilotMetrics } from '../types'

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
  { key: 'published', label: 'Готовы к публикации', icon: <SendOutlined />, color: '#0f766e', tint: 'var(--accent-soft)' },
]

const STEPS: { key: CardStatus; label: string; color: string }[] = [
  { key: 'error', label: 'Ошибки', color: '#e11d48' },
  { key: 'draft', label: 'Черновики', color: '#94a3b8' },
  { key: 'valid', label: 'Валидны', color: '#16a34a' },
  { key: 'published', label: 'Готовы к публикации', color: '#0f766e' },
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
    title: 'Проверить и подготовить',
    desc: 'Заполните GTIN и РД, прогоните валидацию, отметьте готовность к публикации.',
  },
]

export function DashboardPage() {
  const { message } = App.useApp()
  const [counts, setCounts] = useState<Record<string, number> | null>(null)
  const [pilot, setPilot] = useState<PilotMetrics | null>(null)
  const [onboardingOpen, setOnboardingOpen] = useState(false)
  const [onboardingStep, setOnboardingStep] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    const keys: (CardStatus | 'all')[] = ['all', 'draft', 'error', 'valid', 'published', 'validating']
    void Promise.all([
      Promise.all(
        keys.map((k) =>
          listCards({ status: k === 'all' ? undefined : k, limit: 1 }).then(
            (r) => [k, r.total] as const,
          ),
        ),
      ),
      getPilotMetrics(),
    ])
      .then(([pairs, pilotMetrics]) => {
        setCounts(Object.fromEntries(pairs))
        setPilot(pilotMetrics)
        if (
          Number(Object.fromEntries(pairs).all ?? 0) === 0
          && localStorage.getItem('nklab_onboarding_done') !== '1'
        ) {
          setOnboardingOpen(true)
        }
      })
      .catch((error) => message.error(errorMessage(error)))
  }, [message])

  const downloadMetrics = async () => {
    try {
      const blob = await downloadPilotMetrics()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'pilot-metrics.csv'
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const total = counts?.all ?? 0
  const ready = (counts?.valid ?? 0) + (counts?.published ?? 0)
  const readyPct = total ? Math.round((ready / total) * 100) : 0

  const finishOnboarding = () => {
    localStorage.setItem('nklab_onboarding_done', '1')
    setOnboardingOpen(false)
    navigate('/import')
  }

  return (
    <div>
      <PageHeader
        title="Обзор каталога"
        subtitle="Цепочка НК → GTIN → РД → коды. Задача — довести карточки до внутреннего статуса «Готова к публикации» до заказа кодов маркировки."
        extra={
          <Button icon={<QuestionCircleOutlined />} onClick={() => setOnboardingOpen(true)}>
            Как начать
          </Button>
        }
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
          <button
            key={t.key}
            className="lift tap"
            type="button"
            onClick={() => navigate(t.key === 'all' ? '/catalog' : `/catalog?status=${t.key}`)}
            style={{
              position: 'relative',
              background: 'var(--surface)',
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: '18px 18px 18px 20px',
              cursor: 'pointer',
              width: '100%',
              textAlign: 'left',
              boxShadow: `var(--shadow-sm), inset 3px 0 0 ${t.color}`,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 14,
              }}
            >
              <span style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 500 }}>{t.label}</span>
              <span
                aria-hidden
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 'var(--r-md)',
                  background: t.tint,
                  color: t.color,
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: 16,
                }}
              >
                {t.icon}
              </span>
            </div>
            {counts ? (
              <div
                className="num"
                style={{ fontSize: 30, fontWeight: 700, color: 'var(--ink)', lineHeight: 1.1, letterSpacing: '-0.02em' }}
              >
                {t.key === 'all' ? total : counts[t.key] ?? 0}
              </div>
            ) : (
              <Skeleton.Button active size="small" style={{ width: 48, height: 30 }} />
            )}
          </button>
        ))}
      </div>

      {/* --- конвейер готовности + быстрый старт --- */}
      <div className="dashboard-workflow-grid">
        <Card title="Конвейер готовности" styles={{ body: { paddingTop: 18 } }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 }}>
            <span style={{ fontSize: 32, fontWeight: 700, color: 'var(--ink)' }}>{readyPct}%</span>
            <span style={{ color: 'var(--muted)', fontSize: 14 }}>карточек валидны или готовы к публикации</span>
          </div>
          {/* Пропорциональная составная шкала статусов каталога */}
          <div
            role="img"
            aria-label={`Готовность каталога: ${readyPct}%`}
            style={{
              display: 'flex',
              height: 12,
              borderRadius: 999,
              overflow: 'hidden',
              background: '#eef1f5',
              marginTop: 10,
              boxShadow: 'inset 0 0 0 1px rgba(15,23,42,0.04)',
            }}
          >
            {STEPS.filter((s) => (counts?.[s.key] ?? 0) > 0).map((s) => (
              <div
                key={s.key}
                title={`${s.label}: ${counts?.[s.key] ?? 0}`}
                style={{ flex: `${counts?.[s.key] ?? 0} 0 0`, minWidth: 6, background: s.color }}
              />
            ))}
          </div>

          {/* Легенда с counts */}
          <div style={{ display: 'flex', gap: 20, marginTop: 18, flexWrap: 'wrap' }}>
            {STEPS.map((s) => (
              <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ width: 9, height: 9, borderRadius: 3, background: s.color }} />
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>{s.label}</span>
                <b className="num" style={{ fontSize: 14, color: 'var(--ink)' }}>
                  {counts ? counts[s.key] ?? 0 : '—'}
                </b>
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

      <Card
        title={
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <BarChartOutlined aria-hidden />
            KPI пилота
          </span>
        }
        extra={
          <Button icon={<DownloadOutlined />} onClick={() => void downloadMetrics()}>
            Скачать CSV
          </Button>
        }
        style={{ marginTop: 16 }}
        aria-busy={!pilot}
      >
        {pilot ? (
          <>
            <div className="pilot-metrics-grid">
              {[
                ['Успешный импорт', pilot.import_success_rate, '%'],
                ['Валидны с первого прохода', pilot.first_pass_validation_rate, '%'],
                ['Медиана до готовности', pilot.median_time_to_ready_minutes, ' мин'],
                ['Задачи оператора решены', pilot.operator_resolution_rate, '%'],
              ].map(([label, value, suffix]) => (
                <div className="pilot-metric" key={String(label)}>
                  <span>{label}</span>
                  <strong className="num">
                    {value == null ? '—' : `${value}${suffix}`}
                  </strong>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
              <Tag color={pilot.pilot_sample_reached ? 'success' : 'processing'}>
                Выборка: {pilot.cards_total} / {pilot.pilot_sample_target}
              </Tag>
              {pilot.overdue_operator_tasks > 0 && (
                <Tag color="error">Просрочено задач: {pilot.overdue_operator_tasks}</Tag>
              )}
              {pilot.top_issue_codes.slice(0, 4).map((issue) => (
                <Button
                  key={issue.code}
                  size="small"
                  onClick={() => navigate(`/catalog?status=error&issue=${encodeURIComponent(issue.code)}`)}
                >
                  {issue.code}: {issue.count}
                </Button>
              ))}
            </div>
            {pilot.notes.length > 0 && (
              <Alert
                type="info"
                showIcon
                title="Что нужно для репрезентативного среза"
                description={pilot.notes.join(' ')}
                style={{ marginTop: 16 }}
              />
            )}
          </>
        ) : (
          <Skeleton active paragraph={{ rows: 2 }} />
        )}
      </Card>
      <Modal
        title="Первый запуск НК-ЛАБ"
        open={onboardingOpen}
        onCancel={() => setOnboardingOpen(false)}
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
            <Button disabled={onboardingStep === 0} onClick={() => setOnboardingStep((step) => step - 1)}>
              Назад
            </Button>
            {onboardingStep < 2 ? (
              <Button type="primary" onClick={() => setOnboardingStep((step) => step + 1)}>
                Далее
              </Button>
            ) : (
              <Button type="primary" onClick={finishOnboarding}>
                Перейти к импорту
              </Button>
            )}
          </div>
        }
        destroyOnHidden
      >
        <Steps
          current={onboardingStep}
          size="small"
          items={[
            { title: 'Загрузить данные' },
            { title: 'Исправить ошибки' },
            { title: 'Запустить пилот' },
          ]}
          style={{ marginBottom: 24 }}
        />
        {[
          {
            title: 'Начните с импорта номенклатуры',
            text: 'Загрузите Excel, CSV или CommerceML 1С. Перед созданием карточек система покажет предпросмотр распознанных строк.',
          },
          {
            title: 'Доведите карточки до готовности',
            text: 'Откройте карточки с ошибками, заполните атрибуты, GTIN и РД. Одинаковые поля можно исправлять массово в каталоге.',
          },
          {
            title: 'Зафиксируйте измеримую выборку',
            text: 'Создайте пилот, добавьте карточки и запустите его. После запуска состав выборки фиксируется, а KPI считаются отдельно.',
          },
        ].map((item, index) =>
          index === onboardingStep ? (
            <div key={item.title}>
              <h2 style={{ fontSize: 20, marginBottom: 8 }}>{item.title}</h2>
              <p style={{ color: 'var(--muted)', lineHeight: 1.65, margin: 0 }}>{item.text}</p>
            </div>
          ) : null,
        )}
      </Modal>
    </div>
  )
}
