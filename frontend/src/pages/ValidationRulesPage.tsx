import {
  CheckCircleOutlined,
  HistoryOutlined,
  PlusOutlined,
  StopOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App,
  Button,
  Card,
  DatePicker,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Timeline,
} from 'antd'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import {
  approveValidationRuleSet,
  createValidationRuleSet,
  listValidationRuleSets,
  retireValidationRuleSet,
  validationRuleSetHistory,
} from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import type { AuditEvent, ValidationRuleSet, ValidationRuleSetStatus } from '../types'

const STATUS_META: Record<ValidationRuleSetStatus, { label: string; color: string }> = {
  draft: { label: 'Черновик', color: 'default' },
  approved: { label: 'Утверждена', color: 'success' },
  retired: { label: 'Архив', color: 'warning' },
}

const EVENT_LABELS: Record<string, string> = {
  'validation_ruleset.created': 'Версия создана',
  'validation_ruleset.approved': 'Версия утверждена',
  'validation_ruleset.retired': 'Версия архивирована',
}

interface FormValues {
  version: string
  title: string
  categories?: string
  source_reference: string
  change_summary?: string
  period: [Dayjs, Dayjs | null]
  expert_name?: string
}

function categories(value?: string): string[] {
  return (value ?? '')
    .split(/[\n,;]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function ValidationRulesPage() {
  const { message } = App.useApp()
  const [form] = Form.useForm<FormValues>()
  const [items, setItems] = useState<ValidationRuleSet[]>([])
  const [history, setHistory] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyTitle, setHistoryTitle] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems((await listValidationRuleSets()).items)
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
    form.setFieldsValue({ period: [dayjs(), null] })
    setCreateOpen(true)
  }

  const create = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      await createValidationRuleSet({
        version: values.version,
        title: values.title,
        category_codes: categories(values.categories),
        source_reference: values.source_reference,
        change_summary: values.change_summary || '',
        effective_from: values.period[0].format('YYYY-MM-DD'),
        effective_to: values.period[1]?.format('YYYY-MM-DD') ?? null,
      })
      message.success('Черновик версии создан')
      setCreateOpen(false)
      form.resetFields()
      await load()
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  const approve = async (item: ValidationRuleSet) => {
    try {
      await approveValidationRuleSet(item.id)
      message.success(`Версия ${item.version} утверждена`)
      await load()
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const retire = async (item: ValidationRuleSet) => {
    try {
      await retireValidationRuleSet(item.id)
      message.success(`Версия ${item.version} перенесена в архив`)
      await load()
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const showHistory = async (item: ValidationRuleSet) => {
    try {
      setHistoryTitle(`История версии ${item.version}`)
      setHistory(await validationRuleSetHistory(item.id))
      setHistoryOpen(true)
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="Версии правил валидации"
        subtitle="Фиксируйте источник требований, категории, срок действия и экспертное утверждение каждой версии."
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreate}>
            Новая версия
          </Button>
        }
      />

      <Alert
        type="info"
        showIcon
        title="Как выбирается версия"
        description="При проверке карточки применяется последняя утверждённая версия, действующая на текущую дату и подходящая её категории. Номер сохраняется в карточке и истории проверки."
        style={{ marginBottom: 16 }}
      />

      <Card styles={{ body: { padding: 0 } }}>
        <Table<ValidationRuleSet>
          rowKey="id"
          loading={loading}
          dataSource={items}
          scroll={{ x: 1100 }}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          locale={{
            emptyText: (
              <Empty description="Управляемых версий пока нет">
                <Button type="primary" onClick={showCreate}>Создать первую версию</Button>
              </Empty>
            ),
          }}
          columns={[
            {
              title: 'Версия', dataIndex: 'version', width: 110,
              render: (value: string) => <strong className="num">{value}</strong>,
            },
            {
              title: 'Описание', dataIndex: 'title',
              render: (title: string, item) => (
                <div>
                  <strong>{title}</strong>
                  <div className="ruleset-secondary">{item.change_summary || 'Без описания изменений'}</div>
                </div>
              ),
            },
            {
              title: 'Категории', dataIndex: 'category_codes', width: 170,
              render: (values: string[]) => values.length ? values.map((value) => <Tag key={value}>{value}</Tag>) : 'Все',
            },
            {
              title: 'Действует', width: 210,
              render: (_, item) => `${item.effective_from ?? '—'} — ${item.effective_to ?? 'без ограничения'}`,
            },
            {
              title: 'Состояние', dataIndex: 'status', width: 130,
              render: (status: ValidationRuleSetStatus) => <Tag color={STATUS_META[status].color}>{STATUS_META[status].label}</Tag>,
            },
            {
              title: 'Эксперт', dataIndex: 'approved_by_name', width: 170,
              render: (value: string | null) => value || '—',
            },
            {
              title: 'Действия', width: 250, fixed: 'right',
              render: (_, item) => (
                <Space wrap>
                  <Button icon={<HistoryOutlined />} onClick={() => void showHistory(item)}>История</Button>
                  {item.status === 'draft' && (
                    <Popconfirm
                      title={`Утвердить версию ${item.version}?`}
                      description="После утверждения она будет автоматически применяться к подходящим карточкам."
                      okText="Утвердить"
                      cancelText="Отмена"
                      onConfirm={() => void approve(item)}
                    >
                      <Button type="primary" icon={<CheckCircleOutlined />}>Утвердить</Button>
                    </Popconfirm>
                  )}
                  {item.status === 'approved' && (
                    <Popconfirm
                      title={`Архивировать версию ${item.version}?`}
                      description="Новые проверки перестанут использовать эту версию."
                      okText="В архив"
                      cancelText="Отмена"
                      onConfirm={() => void retire(item)}
                    >
                      <Button icon={<StopOutlined />}>В архив</Button>
                    </Popconfirm>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Новая версия правил"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => void create()}
        okText="Создать черновик"
        cancelText="Отмена"
        confirmLoading={saving}
        width={680}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <div className="ruleset-form-grid">
            <Form.Item
              name="version"
              label="Номер версии"
              rules={[
                { required: true, message: 'Укажите версию' },
                { pattern: /^\d+\.\d+\.\d+$/, message: 'Формат: 2.0.0' },
              ]}
            >
              <Input placeholder="2.0.0" autoFocus />
            </Form.Item>
            <Form.Item name="period" label="Срок действия" rules={[{ required: true, message: 'Укажите дату начала' }]}>
              <DatePicker.RangePicker allowEmpty={[false, true]} style={{ width: '100%' }} format="DD.MM.YYYY" />
            </Form.Item>
          </div>
          <Form.Item name="title" label="Название" rules={[{ required: true, min: 2, message: 'Укажите название' }]}>
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="categories" label="Категории" extra="Коды через запятую или с новой строки. Оставьте пустым для всех категорий.">
            <Input.TextArea rows={2} placeholder="6201, 6202" />
          </Form.Item>
          <Form.Item name="source_reference" label="Источник требований" rules={[{ required: true, min: 3, message: 'Укажите документ или источник' }]}>
            <Input.TextArea rows={2} maxLength={4000} showCount />
          </Form.Item>
          <Form.Item name="change_summary" label="Что изменилось">
            <Input.TextArea rows={3} maxLength={4000} showCount />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={historyTitle} open={historyOpen} onCancel={() => setHistoryOpen(false)} footer={null}>
        {history.length ? (
          <Timeline
            items={history.map((event) => ({
              color: event.action.endsWith('approved') ? 'green' : event.action.endsWith('retired') ? 'orange' : 'blue',
              children: (
                <div>
                  <strong>{EVENT_LABELS[event.action] || event.action}</strong>
                  <div className="ruleset-secondary">{dayjs(event.created_at).format('DD.MM.YYYY HH:mm')}</div>
                </div>
              ),
            }))}
          />
        ) : <Empty description="История пуста" />}
      </Modal>
    </div>
  )
}
