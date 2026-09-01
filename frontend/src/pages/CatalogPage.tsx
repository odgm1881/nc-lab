import { CheckCircleOutlined, DeleteOutlined, DownloadOutlined, EditOutlined, InboxOutlined, RightOutlined, SaveOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Empty, Form, Input, Modal, Segmented, Select, Space, Table, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import type { Key } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { bulkUpdateCards, exportCards, listCards, listModels, validateAll } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
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

interface SavedCatalogFilter {
  id: string
  name: string
  view: 'models' | 'list'
  status: string
  issue: string
  search: string
}

function readSavedFilters(): SavedCatalogFilter[] {
  try {
    return JSON.parse(localStorage.getItem('nklab_catalog_filters') ?? '[]') as SavedCatalogFilter[]
  } catch {
    return []
  }
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
  const { user } = useAuth()
  const canEdit = user?.role !== 'viewer'
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  const [view, setView] = useState<'models' | 'list'>(
    params.get('status') || params.get('issue') ? 'list' : 'models',
  )
  const [modelFilter, setModelFilter] = useState<string | null>(null)
  const [models, setModels] = useState<ModelGroup[]>([])
  const [rows, setRows] = useState<CardType[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [validating, setValidating] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<Key[]>([])
  const [bulkOpen, setBulkOpen] = useState(false)
  const [saveFilterOpen, setSaveFilterOpen] = useState(false)
  const [savedFilters, setSavedFilters] = useState<SavedCatalogFilter[]>(readSavedFilters)
  const [savedFilterId, setSavedFilterId] = useState<string>()
  const [bulkForm] = Form.useForm()
  const [saveFilterForm] = Form.useForm()
  const status = params.get('status') ?? ''
  const issueCode = params.get('issue') ?? ''

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
      const result = await listCards({
        status: status || undefined,
        name: modelFilter || undefined,
        search: search || undefined,
        limit: issueCode ? 500 : 200,
      })
      const filtered = issueCode
        ? result.items.filter((card) => card.validation_issues.some((issue) => issue.code === issueCode))
        : result.items
      setRows(filtered)
      setTotal(issueCode ? filtered.length : result.total)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [status, modelFilter, search, issueCode, message])

  useEffect(() => {
    if (view === 'models') void loadModels()
    else void loadList()
  }, [view, loadModels, loadList])

  useEffect(() => {
    setSelectedIds([])
  }, [view, status, modelFilter, search, issueCode])

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
      const attributeKeys = ['item_type', 'composition', 'gender', 'age_group', 'brand', 'country']
      const attributes = Object.fromEntries(
        attributeKeys
          .map((key) => [key, values[`attr_${key}`]])
          .filter(([, value]) => value !== undefined && value !== ''),
      )
      const result = await bulkUpdateCards({
        ids: selectedIds.map(String),
        category_code: values.category_code || undefined,
        data_source: values.data_source || undefined,
        service_comment: values.service_comment || undefined,
        attributes: Object.keys(attributes).length ? attributes : undefined,
      })
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

  const persistFilters = (next: SavedCatalogFilter[]) => {
    setSavedFilters(next)
    localStorage.setItem('nklab_catalog_filters', JSON.stringify(next))
  }

  const saveCurrentFilter = async () => {
    try {
      const values = await saveFilterForm.validateFields()
      const saved: SavedCatalogFilter = {
        id: String(Date.now()),
        name: values.name.trim(),
        view,
        status,
        issue: issueCode,
        search,
      }
      persistFilters([...savedFilters, saved])
      setSavedFilterId(saved.id)
      setSaveFilterOpen(false)
      saveFilterForm.resetFields()
      message.success('Фильтр сохранён')
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    }
  }

  const applySavedFilter = (id: string) => {
    const saved = savedFilters.find((item) => item.id === id)
    setSavedFilterId(id)
    if (!saved) return
    setView(saved.view)
    setSearch(saved.search)
    setModelFilter(null)
    setParams({
      ...(saved.status ? { status: saved.status } : {}),
      ...(saved.issue ? { issue: saved.issue } : {}),
    })
  }

  const deleteSavedFilter = () => {
    if (!savedFilterId) return
    persistFilters(savedFilters.filter((item) => item.id !== savedFilterId))
    setSavedFilterId(undefined)
    message.success('Сохранённый фильтр удалён')
  }

  return (
    <div>
      <PageHeader
        title="Каталог карточек"
        subtitle="Карточки сгруппированы по модели товара — вариации одной модели не смешиваются с другими."
        extra={
          <>
            {canEdit && (
              <Button icon={<CheckCircleOutlined />} loading={validating} onClick={onValidateAll}>
                Провалидировать всё
              </Button>
            )}
            {view === 'list' && (
              <Button icon={<DownloadOutlined />} onClick={onExport}>
                {selectedIds.length ? `Экспорт (${selectedIds.length})` : 'Экспорт'}
              </Button>
            )}
            {canEdit && view === 'list' && selectedIds.length > 0 && (
              <Button icon={<EditOutlined />} onClick={() => setBulkOpen(true)}>
                Изменить ({selectedIds.length})
              </Button>
            )}
            {canEdit && <Button type="primary" onClick={() => navigate('/variations')}>Создать вариации</Button>}
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
            {view === 'list' && issueCode && (
              <Tag
                closable
                color="error"
                onClose={() => setParams(status ? { status } : {})}
              >
                Ошибка: {issueCode}
              </Tag>
            )}
            <Select
              allowClear
              aria-label="Сохранённые фильтры"
              placeholder="Сохранённые фильтры"
              value={savedFilterId}
              onChange={(value) => {
                if (value) applySavedFilter(value)
                else setSavedFilterId(undefined)
              }}
              style={{ minWidth: 190 }}
              options={savedFilters.map((filter) => ({ value: filter.id, label: filter.name }))}
              notFoundContent="Нет сохранённых фильтров"
            />
            <Button icon={<SaveOutlined />} onClick={() => setSaveFilterOpen(true)}>
              Сохранить фильтр
            </Button>
            <Button
              icon={<DeleteOutlined />}
              aria-label="Удалить выбранный сохранённый фильтр"
              disabled={!savedFilterId}
              onClick={deleteSavedFilter}
            />
          </Space>
          <Input.Search
            placeholder={view === 'models' ? 'Поиск модели' : 'Поиск: имя, артикул, GTIN'}
            allowClear
            value={search}
            style={{ width: 300, maxWidth: '100%' }}
            onChange={(event) => {
              if (!event.target.value) setSearch('')
            }}
            onSearch={(v) => setSearch(v)}
          />
        </div>

        {view === 'list' && issueCode && rows.length > 0 && (
          <Alert
            type="info"
            showIcon
            title={`Найдено карточек с ошибкой ${issueCode}: ${rows.length}`}
            description="Выберите все карточки и примените массовое исправление одинаковых полей."
            action={
              <Button onClick={() => setSelectedIds(rows.map((row) => row.id))}>
                Выбрать все
              </Button>
            }
            style={{ margin: 16 }}
          />
        )}

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
                  {canEdit && (
                    <Button type="primary" onClick={() => navigate('/import')}>Импортировать</Button>
                  )}
                </Empty>
              ),
            }}
            scroll={{ x: 760 }}
            columns={[
              {
                title: 'Модель',
                dataIndex: 'name',
                render: (name) => (
                  <Button type="link" style={{ padding: 0 }} onClick={() => openModel(name)}>
                    {name}
                  </Button>
                ),
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
                render: (_, model) => (
                  <Button type="link" onClick={() => openModel(model.name)}>
                    Открыть <RightOutlined aria-hidden style={{ fontSize: 11 }} />
                  </Button>
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
                >
                  <Button
                    type="primary"
                    onClick={() => {
                      setSearch('')
                      setParams({})
                      navigate('/import')
                    }}
                  >
                    Импортировать карточки
                  </Button>
                </Empty>
              ),
            }}
            scroll={{ x: 840 }}
            columns={[
              {
                title: 'Наименование',
                dataIndex: 'name',
                render: (name, r) => (
                  <div>
                    <Button type="link" style={{ padding: 0 }} onClick={() => navigate(`/catalog/${r.id}`)}>
                      {name || '—'}
                    </Button>
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
        title={`Массовое редактирование · выбрано: ${selectedIds.length}`}
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
          <Form.Item name="attr_item_type" label="Вид изделия">
            <Input placeholder="Применить ко всем выбранным карточкам" />
          </Form.Item>
          <Form.Item name="attr_composition" label="Состав сырья">
            <Input placeholder="Например, хлопок 100%" />
          </Form.Item>
          <Form.Item name="attr_gender" label="Пол">
            <Input />
          </Form.Item>
          <Form.Item name="attr_age_group" label="Возрастная группа">
            <Input />
          </Form.Item>
          <Form.Item name="attr_brand" label="Бренд">
            <Input />
          </Form.Item>
          <Form.Item name="attr_country" label="Страна производства">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title="Сохранить текущий фильтр"
        open={saveFilterOpen}
        onCancel={() => setSaveFilterOpen(false)}
        onOk={() => void saveCurrentFilter()}
        okText="Сохранить"
        cancelText="Отмена"
        destroyOnHidden
      >
        <Form form={saveFilterForm} layout="vertical" requiredMark="optional">
          <Form.Item
            name="name"
            label="Название фильтра"
            rules={[{ required: true, whitespace: true, message: 'Укажите название фильтра' }]}
          >
            <Input placeholder="Например, Ошибки GTIN" autoFocus maxLength={80} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
