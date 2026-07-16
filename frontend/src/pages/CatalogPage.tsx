import { InboxOutlined } from '@ant-design/icons'
import { App, Button, Card, Empty, Input, Segmented, Table } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { listCards, validateCard } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import { StatusTag } from '../components/StatusTag'
import type { Card as CardType, CardStatus } from '../types'

const STATUS_OPTIONS = [
  { value: '', label: 'Все' },
  { value: 'draft', label: 'Черновики' },
  { value: 'valid', label: 'Валидны' },
  { value: 'error', label: 'Ошибки' },
  { value: 'published', label: 'Опубликованы' },
]

export function CatalogPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [rows, setRows] = useState<CardType[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const status = params.get('status') ?? ''

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await listCards({ status: status || undefined, search: search || undefined, limit: 200 })
      setRows(r.items)
      setTotal(r.total)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [status, search, message])

  useEffect(() => {
    void load()
  }, [load])

  const onValidate = async (id: string) => {
    try {
      const r = await validateCard(id)
      if (r.result.is_valid) message.success('Карточка валидна')
      else message.warning(`Найдено ошибок: ${r.result.errors.length}`)
      void load()
    } catch (e) {
      message.error(errorMessage(e))
    }
  }

  return (
    <div>
      <PageHeader
        title="Каталог карточек"
        subtitle={`Всего карточек: ${total}. Нажмите на строку, чтобы открыть и отредактировать карточку.`}
        extra={<Button type="primary" onClick={() => navigate('/variations')}>Создать вариации</Button>}
      />

      <Card styles={{ body: { padding: 0 } }}>
        <div
          style={{
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            padding: 16,
            borderBottom: '1px solid var(--hairline)',
          }}
        >
          <Segmented
            value={status}
            options={STATUS_OPTIONS}
            onChange={(v) => setParams(v ? { status: String(v) } : {})}
          />
          <Input.Search
            placeholder="Поиск по имени, артикулу, GTIN"
            allowClear
            style={{ width: 320, maxWidth: '100%' }}
            onSearch={(v) => setSearch(v)}
          />
        </div>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={rows}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          locale={{
            emptyText: (
              <Empty
                image={<InboxOutlined style={{ fontSize: 40, color: 'var(--faint)' }} />}
                description={
                  <span style={{ color: 'var(--muted)' }}>
                    Карточек пока нет — импортируйте номенклатуру или создайте вариации
                  </span>
                }
                style={{ padding: '32px 0' }}
              >
                <Button type="primary" onClick={() => navigate('/import')}>
                  Импортировать
                </Button>
              </Empty>
            ),
          }}
          onRow={(r) => ({ onClick: () => navigate(`/catalog/${r.id}`), style: { cursor: 'pointer' } })}
          columns={[
            {
              title: 'Наименование',
              dataIndex: 'name',
              render: (name, r) => (
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--ink)' }}>{name || '—'}</div>
                  <div style={{ fontSize: 12, color: 'var(--faint)', fontFamily: 'var(--font-mono)' }}>
                    {r.vendor_code}
                  </div>
                </div>
              ),
            },
            { title: 'Категория', dataIndex: 'category_code', width: 110, render: (c) => c ?? '—' },
            {
              title: 'GTIN',
              dataIndex: 'gtin',
              width: 160,
              render: (g) =>
                g ? <span style={{ fontFamily: 'var(--font-mono)' }}>{g}</span> : <span style={{ color: 'var(--faint)' }}>—</span>,
            },
            {
              title: 'Статус',
              dataIndex: 'status',
              width: 150,
              render: (s: CardStatus) => <StatusTag status={s} />,
            },
            {
              title: 'Замечания',
              dataIndex: 'validation_issues',
              width: 110,
              render: (issues: CardType['validation_issues']) =>
                issues.length ? (
                  <span style={{ color: 'var(--error)', fontWeight: 600 }}>{issues.length}</span>
                ) : (
                  <span style={{ color: 'var(--faint)' }}>—</span>
                ),
            },
            {
              title: '',
              width: 130,
              render: (_, r) => (
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation()
                    void onValidate(r.id)
                  }}
                >
                  Валидировать
                </Button>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
