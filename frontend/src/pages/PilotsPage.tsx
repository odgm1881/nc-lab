import {
  ArrowRightOutlined,
  ExperimentOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { App, Button, Card, DatePicker, Empty, Form, Input, InputNumber, Modal, Table, Tag } from 'antd'
import type { Dayjs } from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { createPilot, listPilots } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PageHeader'
import { PilotBaselineFields, type PilotBaselineValues } from '../components/PilotBaselineFields'
import type { Pilot, PilotStatus } from '../types'

const STATUS_META: Record<PilotStatus, { label: string; color: string }> = {
  preparation: { label: 'Подготовка', color: 'default' },
  running: { label: 'Проводится', color: 'processing' },
  completed: { label: 'Завершён', color: 'success' },
}

interface PilotFormValues extends PilotBaselineValues {
  name: string
  description?: string
  sample_target: number
  period?: [Dayjs, Dayjs]
  responsible?: string
  participants?: string
}

function participantList(value?: string): string[] {
  return (value ?? '')
    .split(/[\n,;]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function PilotsPage() {
  const { message } = App.useApp()
  const { user } = useAuth()
  const canEdit = user?.role !== 'viewer'
  const navigate = useNavigate()
  const [form] = Form.useForm<PilotFormValues>()
  const [pilots, setPilots] = useState<Pilot[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [open, setOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setPilots((await listPilots()).items)
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setLoading(false)
    }
  }, [message])

  useEffect(() => {
    void load()
  }, [load])

  const showCreate = () => {
    form.setFieldsValue({
      sample_target: 50,
      responsible: user?.full_name || user?.email || '',
    })
    setOpen(true)
  }

  const submit = async () => {
    try {
      const values = await form.validateFields()
      setCreating(true)
      const pilot = await createPilot({
        name: values.name,
        description: values.description || null,
        sample_target: values.sample_target,
        planned_start_date: values.period?.[0].format('YYYY-MM-DD') ?? null,
        planned_end_date: values.period?.[1].format('YYYY-MM-DD') ?? null,
        responsible: values.responsible || '',
        participants: participantList(values.participants),
        baseline_time_per_card_minutes: values.baseline_time_per_card_minutes ?? null,
        baseline_first_pass_rate: values.baseline_first_pass_rate ?? null,
        baseline_return_rate: values.baseline_return_rate ?? null,
        baseline_labor_minutes_per_card: values.baseline_labor_minutes_per_card ?? null,
        baseline_cost_per_card: values.baseline_cost_per_card ?? null,
        operator_hourly_cost: values.operator_hourly_cost ?? null,
      })
      message.success('Пилот создан')
      setOpen(false)
      form.resetFields()
      navigate(`/pilots/${pilot.id}`)
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Пилотные запуски"
        subtitle="Фиксируйте выборку карточек, участников и период, чтобы KPI каждого пилота считались отдельно."
        extra={canEdit ? (
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreate}>
            Создать пилот
          </Button>
        ) : undefined}
      />

      <Card styles={{ body: { padding: 0 } }}>
        <Table<Pilot>
          rowKey="id"
          loading={loading}
          dataSource={pilots}
          scroll={{ x: 900 }}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          locale={{
            emptyText: (
              <Empty
                image={<ExperimentOutlined aria-hidden style={{ fontSize: 42, color: 'var(--faint)' }} />}
                description="Пилотных запусков пока нет"
                style={{ padding: '36px 0' }}
              >
                {canEdit && (
                  <Button type="primary" onClick={showCreate}>Создать первый пилот</Button>
                )}
              </Empty>
            ),
          }}
          columns={[
            {
              title: 'Пилот',
              dataIndex: 'name',
              render: (name: string, pilot) => (
                <div>
                  <Button type="link" onClick={() => navigate(`/pilots/${pilot.id}`)} style={{ padding: 0 }}>
                    {name}
                  </Button>
                  {pilot.description && (
                    <div style={{ color: 'var(--muted)', fontSize: 12.5, maxWidth: 420 }}>
                      {pilot.description}
                    </div>
                  )}
                </div>
              ),
            },
            {
              title: 'Состояние',
              dataIndex: 'status',
              width: 140,
              render: (status: PilotStatus) => (
                <Tag color={STATUS_META[status].color}>{STATUS_META[status].label}</Tag>
              ),
            },
            {
              title: 'Выборка',
              width: 130,
              render: (_, pilot) => (
                <span className="num">
                  {pilot.cards_count} / {pilot.sample_target}
                </span>
              ),
            },
            {
              title: 'Ответственный',
              dataIndex: 'responsible',
              width: 190,
              render: (value: string) => value || '—',
            },
            {
              title: 'Период',
              width: 210,
              render: (_, pilot) =>
                pilot.planned_start_date || pilot.planned_end_date
                  ? `${pilot.planned_start_date ?? '—'} — ${pilot.planned_end_date ?? '—'}`
                  : 'Не задан',
            },
            {
              title: '',
              width: 54,
              render: (_, pilot) => (
                <Button
                  type="text"
                  icon={<ArrowRightOutlined />}
                  aria-label={`Открыть пилот «${pilot.name}»`}
                  onClick={() => navigate(`/pilots/${pilot.id}`)}
                />
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Новый пилот"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => void submit()}
        okText="Создать"
        cancelText="Отмена"
        confirmLoading={creating}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item
            name="name"
            label="Название"
            rules={[{ required: true, min: 2, message: 'Укажите название пилота' }]}
          >
            <Input placeholder="Например, Пилот августа" autoFocus />
          </Form.Item>
          <Form.Item name="description" label="Цель и описание">
            <Input.TextArea rows={3} maxLength={4000} showCount />
          </Form.Item>
          <Form.Item
            name="sample_target"
            label="Целевой размер выборки"
            rules={[{ required: true, message: 'Укажите размер выборки' }]}
          >
            <InputNumber min={1} max={5000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="period" label="Плановый период">
            <DatePicker.RangePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
          </Form.Item>
          <Form.Item name="responsible" label="Ответственный">
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item
            name="participants"
            label="Участники"
            extra="Введите имена или email через запятую либо с новой строки."
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <PilotBaselineFields />
        </Form>
      </Modal>
    </div>
  )
}
