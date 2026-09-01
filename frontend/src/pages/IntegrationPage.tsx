import {
  DownloadOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { Alert, App, Button, Card, Empty, Select, Space, Table, Tag } from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import {
  downloadNkPayload,
  listNkExchanges,
  nkExchangeQueueSummary,
  reconcileNkExchange,
  refreshNkExchange,
  retryDueNkExchanges,
  retryNkExchange,
} from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PageHeader'
import type { NkExchange, NkExchangeQueueSummary } from '../types'

const STATUS_META: Record<NkExchange['status'], { label: string; color: string }> = {
  pending: { label: 'Ожидает', color: 'default' },
  prepared: { label: 'Пакет готов', color: 'blue' },
  processing: { label: 'Обрабатывается', color: 'processing' },
  succeeded: { label: 'Завершено', color: 'success' },
  failed: { label: 'Ошибка', color: 'error' },
}

const RECONCILIATION_META: Record<NkExchange['reconciliation_status'], { label: string; color: string }> = {
  not_checked: { label: 'Не сверено', color: 'default' },
  in_sync: { label: 'Синхронно', color: 'success' },
  stale_payload: { label: 'Карточка изменилась', color: 'warning' },
  remote_pending: { label: 'Ожидает НК', color: 'processing' },
  remote_failed: { label: 'Ошибка НК', color: 'error' },
  card_missing: { label: 'Карточка удалена', color: 'error' },
}

const emptySummary: NkExchangeQueueSummary = {
  total: 0,
  failed: 0,
  retry_due: 0,
  processing: 0,
  stale_payload: 0,
}

export function IntegrationPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const { user } = useAuth()
  const canEdit = user?.role !== 'viewer'
  const [items, setItems] = useState<NkExchange[]>([])
  const [summary, setSummary] = useState(emptySummary)
  const [status, setStatus] = useState<string>()
  const [reconciliation, setReconciliation] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [actingId, setActingId] = useState<string>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [list, queue] = await Promise.all([
        listNkExchanges({ status, reconciliation_status: reconciliation, limit: 500 }),
        nkExchangeQueueSummary(),
      ])
      setItems(list.items)
      setSummary(queue)
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [message, reconciliation, status])

  useEffect(() => {
    void load()
  }, [load])

  const act = async (item: NkExchange, action: 'retry' | 'refresh' | 'reconcile') => {
    setActingId(item.id)
    try {
      if (action === 'retry') await retryNkExchange(item.id)
      if (action === 'refresh') await refreshNkExchange(item.id)
      if (action === 'reconcile') await reconcileNkExchange(item.id)
      message.success(action === 'reconcile' ? 'Состояние сверено' : 'Операция обновлена')
      await load()
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setActingId(undefined)
    }
  }

  const retryDue = async () => {
    setActingId('retry-due')
    try {
      const result = await retryDueNkExchanges()
      message.success(`Обработано повторно: ${result.processed}`)
      await load()
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setActingId(undefined)
    }
  }

  const download = async (item: NkExchange) => {
    try {
      const blob = await downloadNkPayload(item.id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `nk-${item.id}.json`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="Обмен с Национальным каталогом"
        subtitle="Контролируйте отправки, повторные попытки, очередь ошибок и расхождения с текущими карточками."
        extra={canEdit ? (
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            disabled={!summary.retry_due}
            loading={actingId === 'retry-due'}
            onClick={() => void retryDue()}
          >
            Повторить готовые · {summary.retry_due}
          </Button>
        ) : undefined}
      />

      <div className="integration-summary-grid">
        {[
          ['Всего операций', summary.total],
          ['Ошибок', summary.failed],
          ['Ожидают НК', summary.processing],
          ['Карточка изменилась', summary.stale_payload],
        ].map(([label, value]) => (
          <Card size="small" key={String(label)}>
            <div className="integration-summary-item">
              <span>{label}</span>
              <strong className="num">{value}</strong>
            </div>
          </Card>
        ))}
      </div>

      {summary.failed > 0 && (
        <Alert
          type="warning"
          showIcon
          title={`В очереди ошибок: ${summary.failed}`}
          description="Повторяемые сбои получают время следующей попытки. Ошибки маппинга требуют исправления данных или настроек перед ручным повтором."
          style={{ marginBottom: 16 }}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            value={status}
            allowClear
            placeholder="Все состояния"
            style={{ width: 190 }}
            onChange={setStatus}
            options={Object.entries(STATUS_META).map(([value, meta]) => ({ value, label: meta.label }))}
          />
          <Select
            value={reconciliation}
            allowClear
            placeholder="Все результаты сверки"
            style={{ width: 220 }}
            onChange={setReconciliation}
            options={Object.entries(RECONCILIATION_META).map(([value, meta]) => ({ value, label: meta.label }))}
          />
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>Обновить</Button>
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }}>
        <Table<NkExchange>
          rowKey="id"
          loading={loading}
          dataSource={items}
          scroll={{ x: 1250 }}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          locale={{
            emptyText: (
              <Empty description="Операций обмена нет">
                <Button onClick={() => navigate('/catalog')}>Открыть каталог</Button>
              </Empty>
            ),
          }}
          columns={[
            {
              title: 'Карточка', dataIndex: 'card_id', width: 150,
              render: (value: string) => <Button type="link" onClick={() => navigate(`/catalog/${value}`)}>{value.slice(0, 10)}…</Button>,
            },
            { title: 'Режим', dataIndex: 'mode', width: 90, render: (value: string) => value.toUpperCase() },
            {
              title: 'Состояние', dataIndex: 'status', width: 150,
              render: (value: NkExchange['status']) => <Tag color={STATUS_META[value].color}>{STATUS_META[value].label}</Tag>,
            },
            {
              title: 'Сверка', dataIndex: 'reconciliation_status', width: 190,
              render: (value: NkExchange['reconciliation_status']) => <Tag color={RECONCILIATION_META[value].color}>{RECONCILIATION_META[value].label}</Tag>,
            },
            {
              title: 'Попытки', dataIndex: 'attempts', width: 100,
              render: (value: number, item) => (
                <div className="num">
                  {value}
                  {item.next_retry_at && <div className="integration-secondary">следующая {dayjs(item.next_retry_at).format('DD.MM HH:mm')}</div>}
                </div>
              ),
            },
            {
              title: 'Ошибка', dataIndex: 'error',
              render: (value: string | null, item) => value ? (
                <div>
                  <strong>{item.error_code || 'Ошибка обмена'}</strong>
                  <div className="integration-secondary">{value}</div>
                </div>
              ) : '—',
            },
            {
              title: 'Создано', dataIndex: 'created_at', width: 150,
              render: (value: string) => dayjs(value).format('DD.MM.YYYY HH:mm'),
            },
            {
              title: 'Действия', width: 310, fixed: 'right',
              render: (_, item) => (
                <Space wrap>
                  {canEdit && <Button icon={<SyncOutlined />} loading={actingId === item.id} onClick={() => void act(item, 'reconcile')}>Сверить</Button>}
                  {canEdit && (item.status === 'failed' || item.status === 'prepared') && (
                    <Button onClick={() => void act(item, 'retry')}>Повторить</Button>
                  )}
                  {canEdit && item.mode === 'api' && item.external_id && (item.status === 'processing' || item.status === 'failed') && (
                    <Button onClick={() => void act(item, 'refresh')}>Статус НК</Button>
                  )}
                  <Button icon={<DownloadOutlined />} aria-label="Скачать JSON-пакет" onClick={() => void download(item)} />
                </Space>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
