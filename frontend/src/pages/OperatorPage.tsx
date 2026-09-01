import {
  ClockCircleOutlined,
  CommentOutlined,
  RollbackOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import {
  Alert,
  App,
  Button,
  Card,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Segmented,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Timeline,
} from 'antd'
import type { Key } from 'react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import {
  addTaskComment,
  bulkAssignTasks,
  listCards,
  listTaskComments,
  listTasks,
  taskHistory,
  updateTask,
} from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PageHeader'
import { StatusTag } from '../components/StatusTag'
import type { AuditEvent, Card as CardType, OperatorTask, TaskComment } from '../types'

const PRIORITY: Record<number, { color: string; label: string }> = {
  1: { color: 'default', label: 'Низкий' },
  2: { color: 'blue', label: 'Обычный' },
  3: { color: 'red', label: 'Высокий' },
}

const CATEGORY: Record<string, string> = {
  attributes: 'Атрибуты',
  gtin: 'GTIN',
  rd: 'Разрешительные документы',
  category: 'Категория товара',
  integration: 'Интеграция',
  other: 'Другое',
}

const STATUS: Record<OperatorTask['status'], { label: string; color: string }> = {
  open: { label: 'Открыта', color: 'default' },
  in_progress: { label: 'В работе', color: 'blue' },
  waiting_client: { label: 'Ожидает клиента', color: 'warning' },
  resolved: { label: 'Решено', color: 'success' },
}

type TaskFilter = 'all' | OperatorTask['status'] | 'overdue'

export function OperatorPage() {
  const { message } = App.useApp()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'tasks' | 'errors'>('tasks')
  const [taskFilter, setTaskFilter] = useState<TaskFilter>('all')
  const [sortBy, setSortBy] = useState<'priority' | 'due_at' | 'created_at'>('priority')
  const [tasks, setTasks] = useState<OperatorTask[]>([])
  const [overdueCount, setOverdueCount] = useState(0)
  const [errorCards, setErrorCards] = useState<CardType[]>([])
  const [selectedIds, setSelectedIds] = useState<Key[]>([])
  const [selectedTask, setSelectedTask] = useState<OperatorTask | null>(null)
  const [comments, setComments] = useState<TaskComment[]>([])
  const [history, setHistory] = useState<AuditEvent[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [resolutionOpen, setResolutionOpen] = useState(false)
  const [returnOpen, setReturnOpen] = useState(false)
  const [resolutionForm] = Form.useForm()
  const [returnForm] = Form.useForm()
  const [commentForm] = Form.useForm()

  const load = useCallback(async () => {
    try {
      const taskParams =
        taskFilter === 'all'
          ? { sort_by: sortBy }
          : taskFilter === 'overdue'
            ? { overdue: true, sort_by: sortBy }
            : { status: taskFilter, sort_by: sortBy }
      const [taskResult, overdueResult, cardsResult] = await Promise.all([
        listTasks(taskParams),
        listTasks({ overdue: true }),
        listCards({ status: 'error', limit: 200 }),
      ])
      setTasks(taskResult.items)
      setOverdueCount(overdueResult.total)
      setErrorCards(cardsResult.items)
    } catch (error) {
      message.error(errorMessage(error))
    }
  }, [message, sortBy, taskFilter])

  useEffect(() => {
    void load()
  }, [load])

  const takeTask = async (task: OperatorTask) => {
    try {
      await updateTask(task.id, { status: 'in_progress', assignee_id: user?.id ?? null })
      message.success('Задача взята в работу')
      void load()
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const assignSelected = async () => {
    if (!user || !selectedIds.length) return
    try {
      const result = await bulkAssignTasks(selectedIds.map(String), user.id)
      message.success(`Назначено задач: ${result.updated}`)
      setSelectedIds([])
      void load()
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  const openTask = async (task: OperatorTask) => {
    setSelectedTask(task)
    setDetailLoading(true)
    try {
      const [loadedComments, loadedHistory] = await Promise.all([
        listTaskComments(task.id),
        taskHistory(task.id),
      ])
      setComments(loadedComments)
      setHistory(loadedHistory)
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setDetailLoading(false)
    }
  }

  const sendComment = async () => {
    if (!selectedTask) return
    try {
      const values = await commentForm.validateFields()
      const comment = await addTaskComment(selectedTask.id, values.message)
      setComments((current) => [...current, comment])
      commentForm.resetFields()
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    }
  }

  const openResolution = (task: OperatorTask) => {
    setSelectedTask(task)
    resolutionForm.setFieldsValue({ resolution: task.resolution ?? '' })
    setResolutionOpen(true)
  }

  const resolveTask = async () => {
    if (!selectedTask) return
    try {
      const values = await resolutionForm.validateFields()
      await updateTask(selectedTask.id, {
        status: 'resolved',
        resolution: values.resolution,
        assignee_id: selectedTask.assignee_id || user?.id || null,
      })
      setResolutionOpen(false)
      setSelectedTask(null)
      resolutionForm.resetFields()
      message.success('Результат сохранён, задача решена')
      void load()
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    }
  }

  const returnToClient = async () => {
    if (!selectedTask) return
    try {
      const values = await returnForm.validateFields()
      await addTaskComment(selectedTask.id, values.message)
      await updateTask(selectedTask.id, { status: 'waiting_client' })
      setReturnOpen(false)
      setSelectedTask(null)
      returnForm.resetFields()
      message.success('Задача возвращена клиенту с уточнением')
      void load()
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="Консоль оператора"
        subtitle="Очередь обращений, переписка с клиентом, история решений и контроль сроков."
      />

      {overdueCount > 0 && (
        <Alert
          type="error"
          showIcon
          title={`Просрочено задач: ${overdueCount}`}
          description="Откройте фильтр «Просроченные» и обработайте задачи с истёкшим сроком."
          action={<Button onClick={() => setTaskFilter('overdue')}>Показать</Button>}
          style={{ marginBottom: 16 }}
        />
      )}

      <Segmented
        value={tab}
        onChange={(value) => setTab(value as 'tasks' | 'errors')}
        options={[
          { label: `Задачи (${tasks.length})`, value: 'tasks' },
          { label: `Карточки с ошибками (${errorCards.length})`, value: 'errors' },
        ]}
        style={{ marginBottom: 16 }}
      />

      {tab === 'errors' ? (
        <Card>
          <Table<CardType>
            rowKey="id"
            dataSource={errorCards}
            scroll={{ x: 780 }}
            pagination={{ pageSize: 20 }}
            locale={{ emptyText: <Empty description="Карточек с ошибками нет" /> }}
            columns={[
              {
                title: 'Наименование',
                dataIndex: 'name',
                render: (name: string, card) => (
                  <Button type="link" onClick={() => navigate(`/catalog/${card.id}`)}>
                    {name || card.vendor_code}
                  </Button>
                ),
              },
              { title: 'Артикул', dataIndex: 'vendor_code' },
              { title: 'GTIN', dataIndex: 'gtin', render: (value) => value ?? '—' },
              { title: 'Статус', dataIndex: 'status', render: (status) => <StatusTag status={status} /> },
              {
                title: 'Замечания',
                render: (_, card) => (
                  <Space size={4} wrap>
                    {card.validation_issues.slice(0, 4).map((issue) => (
                      <Tag key={`${issue.code}-${issue.field}`} color={issue.severity === 'error' ? 'error' : 'warning'}>
                        {issue.code}
                      </Tag>
                    ))}
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      ) : (
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
            <Segmented
              value={taskFilter}
              onChange={(value) => setTaskFilter(value as TaskFilter)}
              options={[
                { label: 'Все', value: 'all' },
                { label: 'Открытые', value: 'open' },
                { label: 'В работе', value: 'in_progress' },
                { label: 'Ожидают клиента', value: 'waiting_client' },
                { label: 'Просроченные', value: 'overdue' },
                { label: 'Решённые', value: 'resolved' },
              ]}
            />
            <Space wrap>
              <Select
                aria-label="Сортировка задач"
                value={sortBy}
                onChange={setSortBy}
                style={{ width: 190 }}
                options={[
                  { value: 'priority', label: 'По приоритету' },
                  { value: 'due_at', label: 'По сроку' },
                  { value: 'created_at', label: 'По дате создания' },
                ]}
              />
              <Button
                icon={<UserAddOutlined />}
                disabled={!selectedIds.length}
                onClick={() => void assignSelected()}
              >
                Назначить мне ({selectedIds.length})
              </Button>
            </Space>
          </div>
          <Table<OperatorTask>
            rowKey="id"
            dataSource={tasks}
            scroll={{ x: 1080 }}
            rowSelection={{ selectedRowKeys: selectedIds, onChange: setSelectedIds }}
            pagination={{ pageSize: 20 }}
            locale={{ emptyText: <Empty description="В этой очереди задач нет" /> }}
            columns={[
              {
                title: 'Задача',
                dataIndex: 'title',
                render: (title: string, task) => (
                  <div style={{ maxWidth: 430 }}>
                    <Button type="link" onClick={() => void openTask(task)} style={{ padding: 0 }}>
                      {title}
                    </Button>
                    <div style={{ marginTop: 3 }}>
                      <Tag>{CATEGORY[task.category] ?? task.category}</Tag>
                    </div>
                    {task.escalation_reason && (
                      <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 4 }}>
                        {task.escalation_reason}
                      </div>
                    )}
                  </div>
                ),
              },
              {
                title: 'Приоритет',
                dataIndex: 'priority',
                width: 115,
                render: (priority: number) => <Tag color={PRIORITY[priority]?.color}>{PRIORITY[priority]?.label}</Tag>,
              },
              {
                title: 'Срок',
                dataIndex: 'due_at',
                width: 180,
                render: (dueAt: string | null, task) =>
                  dueAt ? (
                    <Space direction="vertical" size={2}>
                      <span>{new Date(dueAt).toLocaleString('ru-RU')}</span>
                      {task.is_overdue && <Tag color="error">Просрочено</Tag>}
                    </Space>
                  ) : (
                    '—'
                  ),
              },
              {
                title: 'Статус',
                dataIndex: 'status',
                width: 150,
                render: (status: OperatorTask['status']) => (
                  <Tag color={STATUS[status].color}>{STATUS[status].label}</Tag>
                ),
              },
              {
                title: 'Действия',
                width: 270,
                render: (_, task) => (
                  <Space wrap>
                    <Button size="small" icon={<CommentOutlined />} onClick={() => void openTask(task)}>
                      Обсуждение
                    </Button>
                    {task.status !== 'resolved' && task.status !== 'in_progress' && (
                      <Button size="small" onClick={() => void takeTask(task)}>
                        В работу
                      </Button>
                    )}
                    {task.status !== 'resolved' && (
                      <Button size="small" type="primary" onClick={() => openResolution(task)}>
                        Решено
                      </Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      )}

      <Modal
        title={selectedTask?.title ?? 'Задача'}
        open={Boolean(selectedTask) && !resolutionOpen && !returnOpen}
        onCancel={() => setSelectedTask(null)}
        footer={
          selectedTask && selectedTask.status !== 'resolved'
            ? [
                <Button key="return" icon={<RollbackOutlined />} onClick={() => setReturnOpen(true)}>
                  Вернуть клиенту
                </Button>,
                <Button key="close" onClick={() => setSelectedTask(null)}>
                  Закрыть
                </Button>,
              ]
            : undefined
        }
        width={720}
        destroyOnHidden
      >
        <Tabs
          items={[
            {
              key: 'comments',
              label: `Обсуждение (${comments.length})`,
              children: (
                <div aria-busy={detailLoading}>
                  <List
                    loading={detailLoading}
                    dataSource={comments}
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
                      label="Новое сообщение"
                      rules={[{ required: true, whitespace: true, message: 'Введите сообщение' }]}
                    >
                      <Input.TextArea rows={3} maxLength={4000} showCount />
                    </Form.Item>
                    <Button type="primary" onClick={() => void sendComment()}>
                      Отправить
                    </Button>
                  </Form>
                </div>
              ),
            },
            {
              key: 'history',
              label: 'История',
              children: (
                <Timeline
                  pending={detailLoading ? 'Загрузка…' : undefined}
                  items={history.map((event) => ({
                    dot: <ClockCircleOutlined />,
                    content: (
                      <div>
                        <strong>{event.action}</strong>
                        <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                          {new Date(event.created_at).toLocaleString('ru-RU')}
                        </div>
                      </div>
                    ),
                  }))}
                />
              ),
            },
          ]}
        />
      </Modal>

      <Modal
        title="Результат решения"
        open={resolutionOpen}
        okText="Сохранить и завершить"
        cancelText="Отмена"
        onOk={() => void resolveTask()}
        onCancel={() => setResolutionOpen(false)}
        destroyOnHidden
      >
        <Form form={resolutionForm} layout="vertical" requiredMark="optional">
          <Form.Item
            name="resolution"
            label="Что проверено и какое решение принято"
            rules={[{ required: true, whitespace: true, message: 'Зафиксируйте результат решения' }]}
          >
            <Input.TextArea rows={5} maxLength={4000} showCount autoFocus />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Вернуть задачу клиенту"
        open={returnOpen}
        okText="Отправить уточнение"
        cancelText="Отмена"
        onOk={() => void returnToClient()}
        onCancel={() => setReturnOpen(false)}
        destroyOnHidden
      >
        <Form form={returnForm} layout="vertical" requiredMark="optional">
          <Form.Item
            name="message"
            label="Что необходимо уточнить"
            rules={[{ required: true, whitespace: true, message: 'Укажите, что требуется от клиента' }]}
          >
            <Input.TextArea rows={4} maxLength={4000} showCount autoFocus />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
