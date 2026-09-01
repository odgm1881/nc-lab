import { ArrowLeftOutlined, CheckCircleFilled, CommentOutlined, DownloadOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Col, Form, Input, List, Modal, Row, Select, Space, Steps, Tag, Timeline, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import {
  cardHistory,
  addTaskComment,
  createTask,
  downloadNkPayload,
  getCard,
  listMyTasks,
  listTaskComments,
  markCardReady,
  prepareNkExchange,
  updateCard,
  validateCard,
} from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { IssueList } from '../components/IssueList'
import { SectionLabel } from '../components/SectionLabel'
import { StatusTag } from '../components/StatusTag'
import type { AuditEvent, Card as CardType, OperatorTask, TaskComment } from '../types'

const ATTR_FIELDS = [
  ['item_type', 'Вид изделия'],
  ['composition', 'Состав сырья'],
  ['size', 'Размер'],
  ['color', 'Цвет'],
  ['gender', 'Пол'],
  ['age_group', 'Возрастная группа'],
  ['brand', 'Бренд'],
  ['country', 'Страна'],
]

const RD_TYPES = [
  { value: 'declaration', label: 'Декларация соответствия' },
  { value: 'certificate', label: 'Сертификат соответствия' },
  { value: 'refusal_letter', label: 'Отказное письмо' },
]

function escalationCategory(card: CardType): string {
  const codes = card.validation_issues.map((issue) => issue.code)
  if (codes.some((code) => code.startsWith('CATEGORY'))) return 'category'
  if (codes.some((code) => code.startsWith('GTIN'))) return 'gtin'
  if (codes.some((code) => code.startsWith('RD_'))) return 'rd'
  if (codes.some((code) => code.startsWith('ATTR'))) return 'attributes'
  return 'other'
}

export function CardDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const { user } = useAuth()
  const canEdit = user?.role !== 'viewer'
  const [form] = Form.useForm()
  const [taskForm] = Form.useForm()
  const [card, setCard] = useState<CardType | null>(null)
  const [history, setHistory] = useState<AuditEvent[]>([])
  const [tasks, setTasks] = useState<OperatorTask[]>([])
  const [taskDetail, setTaskDetail] = useState<OperatorTask | null>(null)
  const [taskComments, setTaskComments] = useState<TaskComment[]>([])
  const [busy, setBusy] = useState(false)
  const [taskOpen, setTaskOpen] = useState(false)
  const [commentForm] = Form.useForm()

  const load = useCallback(async () => {
    if (!id) return
    const [loadedCard, loadedHistory, loadedTasks] = await Promise.all([
      getCard(id),
      cardHistory(id),
      listMyTasks(id),
    ])
    setCard(loadedCard)
    setHistory(loadedHistory)
    setTasks(loadedTasks.items)
  }, [id])

  useEffect(() => {
    load().catch((e) => message.error(errorMessage(e)))
  }, [load, message])

  useEffect(() => {
    if (!card) return
    form.setFieldsValue({
      name: card.name,
      vendor_code: card.vendor_code,
      category_code: card.category_code,
      gtin: card.gtin,
      ...Object.fromEntries(ATTR_FIELDS.map(([k]) => [`attr_${k}`, card.attributes[k] ?? ''])),
      rd_type: card.rd_data.type ?? undefined,
      rd_number: card.rd_data.number ?? '',
      rd_date: card.rd_data.date ?? '',
      rd_valid_until: card.rd_data.valid_until ?? '',
      package_type: card.packaging.type ?? '',
      units_per_package: card.packaging.units_per_package ?? '',
      package_weight_g: card.packaging.weight_g ?? '',
      data_source: card.data_source,
      service_comment: card.service_comment ?? '',
    })
  }, [card, form])

  const collect = () => {
    const v = form.getFieldsValue()
    const attributes: Record<string, string> = {}
    ATTR_FIELDS.forEach(([k]) => {
      if (v[`attr_${k}`]) attributes[k] = v[`attr_${k}`]
    })
    const rd_data: Record<string, string> = {}
    if (v.rd_type) rd_data.type = v.rd_type
    if (v.rd_number) rd_data.number = v.rd_number
    if (v.rd_date) rd_data.date = v.rd_date
    if (v.rd_valid_until) rd_data.valid_until = v.rd_valid_until
    const packaging: Record<string, string | number> = {}
    if (v.package_type) packaging.type = v.package_type
    if (v.units_per_package) packaging.units_per_package = Number(v.units_per_package)
    if (v.package_weight_g) packaging.weight_g = Number(v.package_weight_g)
    return {
      name: v.name,
      vendor_code: v.vendor_code,
      category_code: v.category_code || null,
      gtin: v.gtin || null,
      attributes,
      rd_data,
      packaging,
      data_source: v.data_source || 'manual',
      service_comment: v.service_comment || null,
    }
  }

  const onSave = async () => {
    if (!id) return
    setBusy(true)
    try {
      setCard(await updateCard(id, collect() as Partial<CardType>))
      setHistory(await cardHistory(id))
      message.success('Сохранено (статус сброшен в черновик)')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onValidate = async () => {
    if (!id) return
    setBusy(true)
    try {
      await updateCard(id, collect() as Partial<CardType>)
      const r = await validateCard(id)
      setCard(r.card)
      setHistory(await cardHistory(id))
      if (r.result.is_valid) message.success('Карточка валидна')
      else message.warning(`Ошибок: ${r.result.errors.length}`)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onMarkReady = async () => {
    if (!id) return
    setBusy(true)
    try {
      setCard(await markCardReady(id))
      setHistory(await cardHistory(id))
      message.success('Карточка готова к публикации')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onPrepareNkPackage = async () => {
    if (!id || !card) return
    setBusy(true)
    try {
      const key = `card-${id}-${card.updated_at}`.slice(0, 120)
      const exchange = await prepareNkExchange(id, key)
      const blob = await downloadNkPayload(exchange.id)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `nk-${card.vendor_code || id}.json`
      anchor.click()
      URL.revokeObjectURL(url)
      message.success('Пакет НК сформирован и записан в журнал обмена')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onEscalate = async () => {
    if (!id || !card) return
    try {
      const values = await taskForm.validateFields()
      setBusy(true)
      await createTask({
        card_id: id,
        title: values.title,
        category: values.category,
        escalation_reason: values.escalation_reason,
        note: values.note || undefined,
        due_at: values.due_at ? new Date(values.due_at).toISOString() : undefined,
        priority: values.priority,
      })
      setTaskOpen(false)
      taskForm.resetFields()
      setTasks((await listMyTasks(id)).items)
      message.success('Карточка передана оператору')
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error(errorMessage(error))
    } finally {
      setBusy(false)
    }
  }

  const openTaskDiscussion = async (task: OperatorTask) => {
    try {
      setTaskDetail(task)
      setTaskComments(await listTaskComments(task.id))
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const sendTaskComment = async () => {
    if (!taskDetail) return
    try {
      const values = await commentForm.validateFields()
      const comment = await addTaskComment(taskDetail.id, values.message)
      setTaskComments((current) => [...current, comment])
      commentForm.resetFields()
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    }
  }

  if (!card) return null

  // Связь панели валидации с полями: подсвечиваем поля, по которым есть ошибки.
  const errorFields = new Set(
    card.validation_issues.filter((i) => i.severity === 'error').map((i) => i.field ?? ''),
  )
  const rdMissing = errorFields.has('rd_data')
  const attrStatus = (k: string) => (errorFields.has(k) ? 'error' : undefined)
  const rdStatus = (k: string) => (rdMissing || errorFields.has(`rd_data.${k}`) ? 'error' : undefined)
  const errorCount = card.validation_issues.filter((i) => i.severity === 'error').length
  const requiredAttributes = ['item_type', 'composition', 'size', 'color', 'gender', 'age_group']
  const preparationChecks = [
    Boolean(card.name && card.vendor_code && card.category_code),
    requiredAttributes.every((key) => Boolean(card.attributes[key])),
    Boolean(card.gtin),
    Boolean(card.rd_data.type && card.rd_data.number && card.rd_data.date && card.rd_data.valid_until),
    card.status === 'valid' || card.status === 'published',
  ]
  const firstIncomplete = preparationChecks.findIndex((done) => !done)
  const currentPreparationStep = firstIncomplete === -1 ? 4 : firstIncomplete

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/catalog')}
        style={{ marginBottom: 14 }}
      >
        Каталог
      </Button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>{card.name || card.vendor_code}</h1>
        <StatusTag status={card.status} />
        <span style={{ color: 'var(--faint)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
          {card.vendor_code}
        </span>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Steps
          current={currentPreparationStep}
          responsive
          items={['Основное', 'Атрибуты', 'GTIN', 'РД', 'Валидация'].map((title, index) => ({
            title,
            status: preparationChecks[index]
              ? 'finish'
              : index === currentPreparationStep
                ? 'process'
                : 'wait',
          }))}
        />
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={15}>
          <Card title="Карточка" styles={{ body: { paddingBottom: 0 } }}>
            <Form form={form} layout="vertical" requiredMark={false} disabled={!canEdit}>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="name" label="Наименование">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="vendor_code" label="Артикул">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="category_code" label="Категория (ТН ВЭД)" validateStatus={attrStatus('category_code')}>
                    <Input placeholder="6109" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="gtin"
                    label="GTIN"
                    tooltip="Необратим. Проверяется до заказа кодов."
                    validateStatus={errorFields.has('gtin') ? 'error' : undefined}
                  >
                    <Input placeholder="4600000000015" style={{ fontFamily: 'var(--font-mono)' }} />
                  </Form.Item>
                </Col>
              </Row>

              <SectionLabel hint="Используется для прослеживаемости">Источник и комментарии</SectionLabel>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="data_source" label="Источник данных">
                    <Select
                      options={[
                        { value: 'manual', label: 'Ручной ввод' },
                        { value: 'excel', label: 'Excel' },
                        { value: 'csv', label: 'CSV' },
                        { value: 'onec', label: '1С' },
                        { value: 'variations', label: 'Конструктор вариаций' },
                      ]}
                    />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="service_comment" label="Служебный комментарий">
                    <Input.TextArea rows={3} maxLength={4000} showCount />
                  </Form.Item>
                </Col>
              </Row>

              <SectionLabel hint="Логистические данные карточки">Упаковка</SectionLabel>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="package_type" label="Тип упаковки">
                    <Input placeholder="короб" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="units_per_package" label="Единиц в упаковке">
                    <Input type="number" min={1} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="package_weight_g" label="Вес, г">
                    <Input type="number" min={0} />
                  </Form.Item>
                </Col>
              </Row>

              <SectionLabel hint="Обязательны для одежды">Атрибуты категории</SectionLabel>
              <Row gutter={16}>
                {ATTR_FIELDS.map(([k, label]) => (
                  <Col span={12} key={k}>
                    <Form.Item name={`attr_${k}`} label={label} validateStatus={attrStatus(k)}>
                      <Input />
                    </Form.Item>
                  </Col>
                ))}
              </Row>

              <SectionLabel hint="Проверяется до заказа кодов">Разрешительная документация</SectionLabel>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="rd_type" label="Тип" validateStatus={rdStatus('type')}>
                    <Select allowClear options={RD_TYPES} placeholder="Выберите тип" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_number" label="Номер" validateStatus={rdStatus('number')}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_date" label="Дата (ГГГГ-ММ-ДД)" validateStatus={rdStatus('date')}>
                    <Input placeholder="2026-02-01" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_valid_until" label="Действует до (ГГГГ-ММ-ДД)" validateStatus={rdStatus('valid_until')}>
                    <Input placeholder="2029-02-01" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>

            {/* Нижняя панель действий */}
            <div
              style={{
                display: 'flex',
                gap: 10,
                flexWrap: 'wrap',
                margin: '4px -22px 0',
                padding: '16px 22px',
                borderTop: '1px solid var(--hairline)',
                background: 'var(--surface-2)',
                borderBottomLeftRadius: 'var(--r-lg)',
                borderBottomRightRadius: 'var(--r-lg)',
              }}
            >
              {canEdit && (
                <>
                  <Button onClick={onSave} loading={busy}>Сохранить</Button>
                  <Button type="primary" onClick={onValidate} loading={busy}>Сохранить и валидировать</Button>
                  <Button onClick={onMarkReady} loading={busy} disabled={card.status !== 'valid'}>Готово к публикации</Button>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={onPrepareNkPackage}
                    loading={busy}
                    disabled={card.status !== 'published'}
                  >
                    Скачать пакет НК
                  </Button>
                </>
              )}
              {errorCount > 0 && (
                <Button danger onClick={() => setTaskOpen(true)}>
                  Передать оператору
                </Button>
              )}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <div style={{ position: 'sticky', top: 16 }}>
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span>Результат валидации</span>
                  {errorCount > 0 ? (
                    <span className="pill pill--error">{errorCount}</span>
                  ) : (
                    <CheckCircleFilled style={{ color: 'var(--success)' }} />
                  )}
                </div>
              }
            >
              <IssueList issues={card.validation_issues} />
              {card.ruleset_version && (
                <Typography.Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                  Правила {card.ruleset_version} · справочники {card.reference_data_version}
                </Typography.Text>
              )}
              {errorCount > 0 && (
                <p style={{ marginTop: 14, marginBottom: 0, fontSize: 12.5, color: 'var(--muted)' }}>
                  Поля с ошибками подсвечены в форме слева. Исправьте и нажмите «Сохранить и
                  валидировать».
                </p>
              )}
            </Card>
            <Card title="История изменений" style={{ marginTop: 16 }}>
              <Timeline
                items={history.slice(0, 30).map((event) => ({
                  content: (
                    <div>
                      <div style={{ fontWeight: 600 }}>{event.action}</div>
                      <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                        {new Date(event.created_at).toLocaleString('ru-RU')}
                        {event.correlation_id ? ` · ${event.correlation_id.slice(0, 8)}` : ''}
                      </div>
                    </div>
                  ),
                }))}
              />
            </Card>
            <Card title={`Обращения оператору · ${tasks.length}`} style={{ marginTop: 16 }}>
              {tasks.some((task) => task.status === 'waiting_client') && (
                <Alert
                  type="warning"
                  showIcon
                  title="Оператор ждёт уточнение"
                  description="Откройте обсуждение задачи и ответьте на вопрос."
                  style={{ marginBottom: 12 }}
                />
              )}
              <List
                size="small"
                dataSource={tasks}
                locale={{ emptyText: 'Обращений по карточке нет' }}
                renderItem={(task) => (
                  <List.Item
                    actions={[
                      <Button
                        key="discussion"
                        type="link"
                        icon={<CommentOutlined />}
                        onClick={() => void openTaskDiscussion(task)}
                      >
                        Обсуждение
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={task.title}
                      description={
                        <Space size={4} wrap>
                          <Tag>
                            {task.status === 'resolved'
                              ? 'Решено'
                              : task.status === 'in_progress'
                                ? 'В работе'
                                : task.status === 'waiting_client'
                                  ? 'Ожидает ответа'
                                  : 'Открыта'}
                          </Tag>
                          {task.resolution && <span>Результат: {task.resolution}</span>}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </div>
        </Col>
      </Row>
      <Modal
        title={taskDetail?.title ?? 'Обсуждение с оператором'}
        open={Boolean(taskDetail)}
        onCancel={() => setTaskDetail(null)}
        footer={null}
        destroyOnHidden
      >
        <List
          dataSource={taskComments}
          locale={{ emptyText: 'Сообщений пока нет' }}
          renderItem={(comment) => (
            <List.Item>
              <List.Item.Meta
                title={
                  <Space>
                    <span>{comment.author_name}</span>
                    <Tag>{comment.author_role === 'client' ? 'Клиент' : 'Оператор'}</Tag>
                  </Space>
                }
                description={
                  <>
                    <div style={{ color: 'var(--text)', whiteSpace: 'pre-wrap' }}>{comment.message}</div>
                    <div style={{ marginTop: 4 }}>{new Date(comment.created_at).toLocaleString('ru-RU')}</div>
                  </>
                }
              />
            </List.Item>
          )}
        />
        <Form form={commentForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="message"
            label="Ответ оператору"
            rules={[{ required: true, whitespace: true, message: 'Введите сообщение' }]}
          >
            <Input.TextArea rows={3} maxLength={4000} showCount />
          </Form.Item>
          <Button type="primary" onClick={() => void sendTaskComment()}>
            Отправить
          </Button>
        </Form>
      </Modal>
      <Modal
        title="Передать карточку оператору"
        open={taskOpen}
        okText="Создать задачу"
        cancelText="Отмена"
        confirmLoading={busy}
        onOk={() => void onEscalate()}
        onCancel={() => setTaskOpen(false)}
        destroyOnHidden
      >
        <Form
          form={taskForm}
          layout="vertical"
          requiredMark="optional"
          initialValues={{
            title: `Проверить: ${card.name || card.vendor_code}`,
            escalation_reason: card.validation_issues
              .filter((issue) => issue.severity === 'error')
              .map((issue) => `${issue.code}: ${issue.message}`)
              .join('\n'),
            category: escalationCategory(card),
            priority: 2,
          }}
        >
          <Form.Item name="title" label="Задача" rules={[{ required: true, message: 'Укажите задачу' }]}>
            <Input maxLength={255} autoFocus />
          </Form.Item>
          <Form.Item name="category" label="Категория обращения">
            <Select
              options={[
                { value: 'attributes', label: 'Атрибуты' },
                { value: 'gtin', label: 'GTIN' },
                { value: 'rd', label: 'Разрешительные документы' },
                { value: 'category', label: 'Категория товара' },
                { value: 'integration', label: 'Интеграция' },
                { value: 'other', label: 'Другое' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="escalation_reason"
            label="Причина передачи"
            rules={[{ required: true, message: 'Опишите спорный вопрос' }]}
          >
            <Input.TextArea rows={4} maxLength={2000} showCount />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="priority" label="Приоритет">
                <Select
                  options={[
                    { value: 1, label: 'Низкий' },
                    { value: 2, label: 'Обычный' },
                    { value: 3, label: 'Высокий' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="due_at" label="Срок решения">
                <Input type="datetime-local" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="note" label="Дополнительный контекст">
            <Input.TextArea rows={2} maxLength={4000} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
