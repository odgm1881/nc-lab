import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  DownloadOutlined,
  EditOutlined,
  LockOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
} from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import {
  addPilotCards,
  completePilot,
  downloadPilotReport,
  getPilot,
  listCards,
  removePilotCard,
  startPilot,
  updatePilot,
} from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PageHeader'
import { PilotBaselineFields, type PilotBaselineValues } from '../components/PilotBaselineFields'
import { StatusTag } from '../components/StatusTag'
import type { Card as CardType, PilotDetail, PilotStatus } from '../types'

const STATUS_META: Record<PilotStatus, { label: string; color: string }> = {
  preparation: { label: 'Подготовка', color: 'default' },
  running: { label: 'Проводится', color: 'processing' },
  completed: { label: 'Завершён', color: 'success' },
}

interface EditValues extends PilotBaselineValues {
  name: string
  description?: string
  sample_target: number
  period?: [Dayjs, Dayjs]
  responsible?: string
  participants?: string
}

function people(value?: string): string[] {
  return (value ?? '')
    .split(/[\n,;]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function PilotDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { message, modal } = App.useApp()
  const { user } = useAuth()
  const canEdit = user?.role !== 'viewer'
  const [editForm] = Form.useForm<EditValues>()
  const [pilot, setPilot] = useState<PilotDetail | null>(null)
  const [catalog, setCatalog] = useState<CardType[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editOpen, setEditOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const detail = await getPilot(id)
      setPilot(detail)
      if (detail.status === 'preparation') {
        setCatalog((await listCards({ limit: 500 })).items)
      }
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [id, message])

  useEffect(() => {
    void load()
  }, [load])

  const availableCards = useMemo(() => {
    const included = new Set(pilot?.cards.map((card) => card.id) ?? [])
    return catalog.filter((card) => !included.has(card.id))
  }, [catalog, pilot])

  const addCards = async () => {
    if (!selected.length) return
    setSaving(true)
    try {
      setPilot(await addPilotCards(id, selected))
      setSelected([])
      message.success(`Добавлено карточек: ${selected.length}`)
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  const removeCard = async (cardId: string) => {
    try {
      setPilot(await removePilotCard(id, cardId))
      message.success('Карточка удалена из выборки')
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const confirmStart = () => {
    modal.confirm({
      title: 'Зафиксировать выборку и запустить пилот?',
      content: 'После запуска добавлять и удалять карточки из выборки будет нельзя.',
      okText: 'Запустить пилот',
      cancelText: 'Отмена',
      icon: <LockOutlined />,
      onOk: async () => {
        setPilot(await startPilot(id))
        message.success('Пилот запущен, выборка зафиксирована')
      },
    })
  }

  const confirmComplete = () => {
    modal.confirm({
      title: 'Завершить пилот?',
      content: 'Система зафиксирует дату завершения и сохранит итоговые показатели.',
      okText: 'Завершить',
      cancelText: 'Отмена',
      onOk: async () => {
        setPilot(await completePilot(id))
        message.success('Пилот завершён')
      },
    })
  }

  const download = async () => {
    try {
      const blob = await downloadPilotReport(id)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `pilot-${id}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const showEdit = () => {
    if (!pilot) return
    editForm.setFieldsValue({
      name: pilot.name,
      description: pilot.description ?? undefined,
      sample_target: pilot.sample_target,
      period:
        pilot.planned_start_date && pilot.planned_end_date
          ? [dayjs(pilot.planned_start_date), dayjs(pilot.planned_end_date)]
          : undefined,
      responsible: pilot.responsible,
      participants: pilot.participants.join('\n'),
      baseline_time_per_card_minutes: pilot.baseline_time_per_card_minutes,
      baseline_first_pass_rate: pilot.baseline_first_pass_rate,
      baseline_return_rate: pilot.baseline_return_rate,
      baseline_labor_minutes_per_card: pilot.baseline_labor_minutes_per_card,
      baseline_cost_per_card: pilot.baseline_cost_per_card,
      operator_hourly_cost: pilot.operator_hourly_cost,
    })
    setEditOpen(true)
  }

  const saveMetadata = async () => {
    try {
      const values = await editForm.validateFields()
      setSaving(true)
      setPilot(
        await updatePilot(id, {
          name: values.name,
          description: values.description || null,
          sample_target: values.sample_target,
          planned_start_date: values.period?.[0].format('YYYY-MM-DD') ?? null,
          planned_end_date: values.period?.[1].format('YYYY-MM-DD') ?? null,
          responsible: values.responsible || '',
          participants: people(values.participants),
          baseline_time_per_card_minutes: values.baseline_time_per_card_minutes ?? null,
          baseline_first_pass_rate: values.baseline_first_pass_rate ?? null,
          baseline_return_rate: values.baseline_return_rate ?? null,
          baseline_labor_minutes_per_card: values.baseline_labor_minutes_per_card ?? null,
          baseline_cost_per_card: values.baseline_cost_per_card ?? null,
          operator_hourly_cost: values.operator_hourly_cost ?? null,
        }),
      )
      setEditOpen(false)
      message.success('Данные пилота обновлены')
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  if (loading || !pilot) {
    return <Skeleton active paragraph={{ rows: 12 }} />
  }

  const progress = Math.min(100, Math.round((pilot.cards_count / pilot.sample_target) * 100))
  const metrics = pilot.metrics
  const effectRows = [
    {
      key: 'time', label: 'Время на карточку', baseline: pilot.effect.baseline_time_per_card_minutes,
      actual: pilot.effect.actual_time_per_card_minutes, unit: ' мин', change: pilot.effect.time_reduction_rate,
      changeLabel: 'сокращение', inverse: false,
    },
    {
      key: 'first-pass', label: 'Валидны с первого прохода', baseline: pilot.effect.baseline_first_pass_rate,
      actual: pilot.effect.actual_first_pass_rate, unit: '%', change: pilot.effect.first_pass_change_points,
      changeLabel: 'п. п.', inverse: false,
    },
    {
      key: 'returns', label: 'Возвраты', baseline: pilot.effect.baseline_return_rate,
      actual: pilot.effect.actual_return_rate, unit: '%', change: pilot.effect.return_rate_change_points,
      changeLabel: 'п. п.', inverse: true,
    },
    {
      key: 'labor', label: 'Трудозатраты на карточку', baseline: pilot.effect.baseline_labor_minutes_per_card,
      actual: pilot.effect.actual_labor_minutes_per_card, unit: ' мин', change: pilot.effect.labor_reduction_rate,
      changeLabel: 'сокращение', inverse: false,
    },
    {
      key: 'cost', label: 'Стоимость карточки', baseline: pilot.effect.baseline_cost_per_card,
      actual: pilot.effect.actual_cost_per_card, unit: ' ₽', change: pilot.effect.cost_saving_rate,
      changeLabel: 'экономия', inverse: false,
    },
  ]

  return (
    <div>
      <PageHeader
        title={pilot.name}
        subtitle={pilot.description || 'Управляемая выборка карточек и отдельные KPI пилота.'}
        extra={
          <>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/pilots')}>
              Все пилоты
            </Button>
            {canEdit && <Button icon={<EditOutlined />} onClick={showEdit}>Изменить</Button>}
            <Button icon={<DownloadOutlined />} onClick={() => void download()}>
              Отчёт CSV
            </Button>
            {canEdit && pilot.status === 'preparation' && (
              <Button type="primary" icon={<LockOutlined />} onClick={confirmStart}>
                Запустить
              </Button>
            )}
            {canEdit && pilot.status === 'running' && (
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={confirmComplete}>
                Завершить
              </Button>
            )}
          </>
        }
      />

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, lg: 4 }} size="small">
          <Descriptions.Item label="Состояние">
            <Tag color={STATUS_META[pilot.status].color}>{STATUS_META[pilot.status].label}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Ответственный">{pilot.responsible || 'Не назначен'}</Descriptions.Item>
          <Descriptions.Item label="Период">
            {pilot.planned_start_date || pilot.planned_end_date
              ? `${pilot.planned_start_date ?? '—'} — ${pilot.planned_end_date ?? '—'}`
              : 'Не задан'}
          </Descriptions.Item>
          <Descriptions.Item label="Участники">
            {pilot.participants.length ? pilot.participants.join(', ') : 'Не указаны'}
          </Descriptions.Item>
        </Descriptions>
        <div style={{ marginTop: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 6 }}>
            <span style={{ color: 'var(--muted)' }}>Размер выборки</span>
            <strong className="num">
              {pilot.cards_count} / {pilot.sample_target}
            </strong>
          </div>
          <Progress percent={progress} status={pilot.cards_count >= pilot.sample_target ? 'success' : 'normal'} />
        </div>
      </Card>

      <Card title="KPI этой выборки" style={{ marginBottom: 16 }}>
        <div className="pilot-metrics-grid">
          {[
            ['Готовность карточек', metrics.readiness_rate, '%'],
            ['Валидны с первого прохода', metrics.first_pass_validation_rate, '%'],
            ['Медиана до готовности', metrics.median_time_to_ready_minutes, ' мин'],
            ['Задачи оператора решены', metrics.operator_resolution_rate, '%'],
          ].map(([label, value, suffix]) => (
            <div className="pilot-metric" key={String(label)}>
              <span>{label}</span>
              <strong className="num">{value == null ? '—' : `${value}${suffix}`}</strong>
            </div>
          ))}
        </div>
        {metrics.notes.length > 0 && (
          <Alert
            type="info"
            showIcon
            title="Состояние выборки"
            description={metrics.notes.join(' ')}
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      <Card
        title="Фактический эффект пилота"
        extra={
          <span className="pilot-effect-count num">
            Измерено {pilot.effect.measured_indicators} из {pilot.effect.total_indicators}
          </span>
        }
        style={{ marginBottom: 16 }}
      >
        <div className="pilot-effect-table-wrap">
          <table className="pilot-effect-table">
            <thead>
              <tr>
                <th scope="col">Показатель</th>
                <th scope="col">До пилота</th>
                <th scope="col">Фактически</th>
                <th scope="col">Изменение</th>
              </tr>
            </thead>
            <tbody>
              {effectRows.map((row) => {
                const favourable = row.change != null && (row.inverse ? row.change < 0 : row.change > 0)
                return (
                  <tr key={row.key}>
                    <th scope="row">{row.label}</th>
                    <td className="num">{row.baseline == null ? '—' : `${row.baseline}${row.unit}`}</td>
                    <td className="num">{row.actual == null ? '—' : `${row.actual}${row.unit}`}</td>
                    <td>
                      {row.change == null ? (
                        <span className="pilot-effect-empty">Недостаточно данных</span>
                      ) : (
                        <Tag color={favourable ? 'success' : row.change === 0 ? 'default' : 'warning'}>
                          {row.change > 0 ? '+' : ''}{row.change}
                          {row.changeLabel === 'п. п.' ? ' п. п.' : `% ${row.changeLabel}`}
                        </Tag>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {pilot.effect.measured_indicators < pilot.effect.total_indicators && (
          <Alert
            type="info"
            showIcon
            title="Эффект рассчитан частично"
            description="Добавьте исходные значения в параметрах пилота и накопите фактические операции по выборке."
            action={canEdit ? <Button size="small" onClick={showEdit}>Добавить исходные данные</Button> : undefined}
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {canEdit && pilot.status === 'preparation' && (
        <Card title="Добавить карточки в выборку" style={{ marginBottom: 16 }}>
          <Space.Compact style={{ width: '100%' }}>
            <Select
              mode="multiple"
              value={selected}
              onChange={setSelected}
              placeholder="Выберите карточки каталога"
              optionFilterProp="label"
              maxTagCount="responsive"
              style={{ flex: 1 }}
              options={availableCards.map((card) => ({
                value: card.id,
                label: `${card.name || 'Без названия'} · ${card.vendor_code || 'без артикула'}`,
              }))}
              notFoundContent="Все карточки уже добавлены"
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!selected.length}
              loading={saving}
              onClick={() => void addCards()}
            >
              Добавить
            </Button>
          </Space.Compact>
        </Card>
      )}

      <Card title={`Карточки пилота · ${pilot.cards_count}`} styles={{ body: { padding: 0 } }}>
        <Table<CardType>
          rowKey="id"
          dataSource={pilot.cards}
          scroll={{ x: 760 }}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          locale={{
            emptyText: (
              <Empty description="Выборка пока пуста">
                {pilot.status === 'preparation' && <span>Выберите карточки в блоке выше.</span>}
              </Empty>
            ),
          }}
          columns={[
            {
              title: 'Карточка',
              dataIndex: 'name',
              render: (name: string, card) => (
                <Button type="link" style={{ padding: 0 }} onClick={() => navigate(`/catalog/${card.id}`)}>
                  {name || 'Без названия'}
                </Button>
              ),
            },
            { title: 'Артикул', dataIndex: 'vendor_code', width: 150, render: (value: string) => value || '—' },
            { title: 'GTIN', dataIndex: 'gtin', width: 160, render: (value: string | null) => value || '—' },
            { title: 'Статус', dataIndex: 'status', width: 170, render: (status) => <StatusTag status={status} /> },
            ...(canEdit && pilot.status === 'preparation'
              ? [
                  {
                    title: '',
                    width: 100,
                    render: (_: unknown, card: CardType) => (
                      <Popconfirm
                        title="Убрать карточку из выборки?"
                        okText="Убрать"
                        cancelText="Отмена"
                        onConfirm={() => void removeCard(card.id)}
                      >
                        <Button danger type="link">
                          Убрать
                        </Button>
                      </Popconfirm>
                    ),
                  },
                ]
              : []),
          ]}
        />
      </Card>

      <Modal
        title="Параметры пилота"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={() => void saveMetadata()}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical" requiredMark="optional">
          <Form.Item name="name" label="Название" rules={[{ required: true, min: 2, message: 'Укажите название' }]}>
            <Input autoFocus />
          </Form.Item>
          <Form.Item name="description" label="Цель и описание">
            <Input.TextArea rows={3} maxLength={4000} showCount />
          </Form.Item>
          <Form.Item name="sample_target" label="Целевой размер выборки" rules={[{ required: true }]}>
            <InputNumber min={1} max={5000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="period" label="Плановый период">
            <DatePicker.RangePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
          </Form.Item>
          <Form.Item name="responsible" label="Ответственный">
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="participants" label="Участники" extra="По одному участнику на строку.">
            <Input.TextArea rows={3} />
          </Form.Item>
          <PilotBaselineFields />
        </Form>
      </Modal>
    </div>
  )
}
