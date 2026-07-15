import { App, Button, Card, Input, Select, Space, Table, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { listCards, validateCard } from '../api/endpoints'
import { StatusTag } from '../components/StatusTag'
import type { Card as CardType, CardStatus } from '../types'

const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'draft', label: 'Черновик' },
  { value: 'valid', label: 'Валидна' },
  { value: 'error', label: 'Ошибки' },
  { value: 'published', label: 'Опубликована' },
]

export function CatalogPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const [rows, setRows] = useState<CardType[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
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
      <Typography.Title level={4}>Каталог карточек</Typography.Title>
      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            value={status}
            style={{ width: 180 }}
            options={STATUS_OPTIONS}
            onChange={(v) => setParams(v ? { status: v } : {})}
          />
          <Input.Search
            placeholder="Поиск по имени, артикулу, GTIN"
            allowClear
            style={{ width: 320 }}
            onSearch={(v) => setSearch(v)}
          />
          <Typography.Text type="secondary">Всего: {total}</Typography.Text>
        </Space>

        <Table
          rowKey="id"
          loading={loading}
          dataSource={rows}
          pagination={{ pageSize: 20 }}
          onRow={(r) => ({ onClick: () => navigate(`/catalog/${r.id}`), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Наименование', dataIndex: 'name' },
            { title: 'Артикул', dataIndex: 'vendor_code' },
            { title: 'Категория', dataIndex: 'category_code' },
            { title: 'GTIN', dataIndex: 'gtin', render: (g) => g ?? '—' },
            { title: 'Статус', dataIndex: 'status', render: (s: CardStatus) => <StatusTag status={s} /> },
            {
              title: 'Замечания',
              render: (_, r) => (r.validation_issues.length ? r.validation_issues.length : '—'),
            },
            {
              title: 'Действия',
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
