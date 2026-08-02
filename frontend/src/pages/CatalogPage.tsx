import { CheckCircleOutlined, DownloadOutlined, EditOutlined, InboxOutlined, RightOutlined } from '@ant-design/icons'
import { App, Button, Card, Empty, Form, Input, Modal, Segmented, Select, Space, Table, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import type { Key } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { bulkUpdateCards, exportCards, listCards, listModels, validateAll } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import { StatusTag } from '../components/StatusTag'
import type { Card as CardType, CardStatus, ModelGroup } from '../types'

const STATUS_OPTIONS = [
  { value: '', label: 'Все' },
  { value: 'valid', label: 'Валидны' },
  { value: 'error', label: 'Ошибки' },
  { value: 'draft', label: 'Черновики' },
  { value: 'published', label: 'Готовы к публикации' },
]

const COUNT_META: Record<string, { color: string; label: string }> = {
  valid: { color: 'var(--success)', label: 'валидны' },
  error: { color: 'var(--error)', label: 'ошибки' },
  draft: { color: '#64748b', label: 'черновики' },
  published: { color: 'var(--accent)', label: 'готово' },
  validating: { color: 'var(--info)', label: 'валидация' },
}

function CountChips({ counts }: { counts: Record<string, number> }) {
  const order = ['error', 'draft', 'valid', 'published', 'validating']
  const present = order.filter((k) => counts[k])
  if (!present.length) return <span style={{ color: 'var(--faint)' }}>—</span>
  return (
    <Space size={6} wrap>
      {present.map((k) => (
        <span
          key={k}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12.5, color: 'var(--text)' }}
        >
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: COUNT_META[k].color }} />
          <b style={{ fontVariantNumeric: 'tabular-nums' }}>{counts[k]}</b> {COUNT_META[k].label}
        </span>
      ))}
    </Space>
  )
}

export function CatalogPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  const [view, setView] = useState<'models' | 'list'>('models')
  const [modelFilter, setModelFilter] = useState<string | null>(null)
  const [models, setModels] = useState<ModelGroup[]>([])
  const [rows, setRows] = useState<CardType[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [validating, setValidating] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<Key[]>([])
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkForm] = Form.useForm()
  const status = params.get('status') ?? ''

  const loadModels = useCallback(async () => {
    setLoading(true)
    try {
      setModels((await listModels(search || undefined)).items)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [search, message])

  const loadList = useCallback(async () => {
    setLoading(true)
    try {
      const r = await listCards({
        status: status || undefined,
        name: modelFilter || undefined,
        search: search || undefined,
        limit: 200,
      })
      setRows(r.items)
      setTotal(r.total)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [status, modelFilter, search, message])

  useEffect(() => {
    if (view === 'models') void loadModels()
    else void loadList()
  }, [view, loadModels, loadList])

  useEffect(() => {
    setSelectedIds([])
  }, [view, status, modelFilter, search])

  const onValidateAll = async () => {
    setValidating(true)
    try {
      const r = await validateAll()
      message.success(`Провалидировано: ${r.validated}. Валидных: ${r.valid}, с ошибками: ${r.error}`)
      if (view === 'models') void loadModels()
      else void loadList()
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setValidating(false)
    }
  }

  const openModel = (name: string) => {
    setModelFilter(name)
    setParams({})
    setView('list')
  }

  const onExport = async () => {
    try {
      const blob = await exportCards({
        ids: selectedIds.length ? selectedIds.map(String) : undefined,
        status: status || undefined,
        name: modelFilter || undefined,
        search: search || undefined,
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'cards-export.csv'
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      message.error(errorMessage(e))
    }
  }

  const onBulkUpdate = async () => {
    try {
      const values = await bulkForm.validateFields()
      const result = await bulkUpdateCards({ ids: selectedIds.map(String), ...values })
      message.success(`Обновлено карточек: ${result.updated}`)
      setBulkOpen(false)
      setSelectedIds([])
      bulkForm.resetFields()
      void loadList()
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return
      message.error(errorMessage(e))
    }
  }

  return (
    <div>
      <PageHeader
        title="Каталог карточек"
        subtitle="Карточки сгруппированы по модели товара — вариации одной модели не смешиваются с другими."
        extra={
          <>
            <Button icon={<CheckCircleOutlined />} loading={validating} onClick={onValidateAll}>
              Провалидировать всё
            </Button>
            {view === 'list' && (
              <Button icon={<DownloadOutlined />} onClick={onExport}>
                {selectedIds.length ? `Экспорт (${selectedIds.length})` : 'Экспорт'}
              </Button>
            )}
            {view === 'list' && selectedIds.length > 0 && (
              <Button icon={<EditOutlined />} onClick={() => setBulkOpen(true)}>
                Изменить ({selectedIds.length})
              </Button>
            )}
            <Button type="primary" onClick={() => navigate('/variations')}>
              Создать вариации
            </Button>
          </>
        }
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
          <Space size={12} wrap>
            <Segmented
              value={view}
              onChange={(v) => {
                setView(v as 'models' | 'list')
                if (v === 'models') setModelFilter(null)
              }}
              options={[
                { label: 'Модели', value: 'models' },
                { label: 'Все карточки', value: 'list' },
              ]}
            />
            {view === 'list' && (
              <Segmented
                value={status}
                options={STATUS_OPTIONS}
                onChange={(v) => setParams(v ? { status: String(v) } : {})}
              />
            )}
            {view === 'list' && modelFilter && (
              <Tag closable onClose={() => setModelFilter(null)} color="cyan">
                Модель: {modelFilter}
              </Tag>
            )}
          </Space>
          <Input.Search
            placeholder={view === 'models' ? 'Поиск модели' : 'Поиск: имя, артикул, GTIN'}
            allowClear
            style={{ width: 300, maxWidth: '100%' }}
            onSearch={(v) => setSearch(v)}
          />
        </div>

        {view === 'models' ? (
          <Table
            rowKey="name"
            loading={loading}
            dataSource={models}
            pagination={{ pageSize: 20, hideOnSinglePage: true }}
            locale={{
              emptyText: (
                <Empty
                  image={<InboxOutlined style={{ fontSize: 40, color: 'var(--faint)' }} />}
                  description={<span style={{ color: 'var(--muted)' }}>Моделей пока нет</span>}
                  style={{ padding: '32px 0' }}
                >
                  <Button type="primary" onClick={() => navigate('/import')}>
                    Импортировать
                  </Button>
                </Empty>
              ),
            }}
            onRow={(m) => ({ onClick: () => openModel(m.name), style: { cursor: 'pointer' } })}
            columns={[
              {
                title: 'Модель',
                dataIndex: 'name',
                render: (name) => <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{name}</span>,
              },
              { title: 'Категория', dataIndex: 'category_code', width: 110, render: (c) => c ?? '—' },
              {
                title: 'Вариаций',
                dataIndex: 'total',
                width: 100,
                render: (t) => <b style={{ fontVariantNumeric: 'tabular-nums' }}>{t}</b>,
              },
              {
                title: 'Статусы',
                render: (_, m) => <CountChips counts={m.counts} />,
              },
              {
                title: '',
                width: 110,
                render: () => (
                  <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
                    Открыть <RightOutlined style={{ fontSize: 11 }} />
                  </span>
                ),
              },
            ]}
          />
        ) : (
          <Table
            rowKey="id"
            loading={loading}
            dataSource={rows}
            rowSelection={{ selectedRowKeys: selectedIds, onChange: setSelectedIds }}
            pagination={{ pageSize: 20, hideOnSinglePage: true }}
            locale={{
              emptyText: (
                <Empty
                  description={<span style={{ color: 'var(--muted)' }}>Карточек нет</span>}
                  style={{ padding: '32px 0' }}
                />
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
                  g ? (
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{g}</span>
                  ) : (
                    <span style={{ color: 'var(--faint)' }}>—</span>
                  ),
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
            ]}
            footer={() => <span style={{ color: 'var(--muted)' }}>Всего: {total}</span>}
          />
        )}
      </Card>
      <Modal
        title={`Массовое редактирование — ${selectedIds.length} карточек`}
        open={bulkOpen}
        onCancel={() => setBulkOpen(false)}
        onOk={onBulkUpdate}
        okText="Применить"
      >
        <Form form={bulkForm} layout="vertical">
          <Form.Item name="category_code" label="Категория ТН ВЭД">
            <Input placeholder="Оставьте пустым, чтобы не менять" />
          </Form.Item>
          <Form.Item name="data_source" label="Источник данных">
            <Select
              allowClear
              options={[
                { value: 'manual', label: 'Ручной ввод' },
                { value: 'excel', label: 'Excel' },
                { value: 'csv', label: 'CSV' },
                { value: 'onec', label: '1С' },
              ]}
            />
          </Form.Item>
          <Form.Item name="service_comment" label="Служебный комментарий">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
