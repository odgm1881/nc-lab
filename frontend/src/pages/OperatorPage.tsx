import { App, Button, Card, Segmented, Space, Table, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { listCards, listTasks, updateTask } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import { StatusTag } from '../components/StatusTag'
import type { Card as CardType, OperatorTask } from '../types'

const PRIORITY: Record<number, { color: string; label: string }> = {
  1: { color: 'default', label: 'Низкий' },
  2: { color: 'blue', label: 'Обычный' },
  3: { color: 'red', label: 'Высокий' },
}

export function OperatorPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'tasks' | 'errors'>('errors')
  const [tasks, setTasks] = useState<OperatorTask[]>([])
  const [errorCards, setErrorCards] = useState<CardType[]>([])

  const load = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([listTasks(), listCards({ status: 'error', limit: 200 })])
      setTasks(t.items)
      setErrorCards(c.items)
    } catch (e) {
      message.error(errorMessage(e))
    }
  }, [message])

  useEffect(() => {
    void load()
  }, [load])

  const setStatus = async (id: string, status: string) => {
    try {
      await updateTask(id, { status })
      message.success('Обновлено')
      void load()
    } catch (e) {
      message.error(errorMessage(e))
    }
  }

  return (
    <div>
      <PageHeader
        title="Консоль оператора"
        subtitle="Спорные карточки и очередь задач. Оператор берёт задачу, решает и меняет статус."
      />

      <Segmented
        value={tab}
        onChange={(v) => setTab(v as 'tasks' | 'errors')}
        options={[
          { label: `Карточки с ошибками (${errorCards.length})`, value: 'errors' },
          { label: `Задачи (${tasks.length})`, value: 'tasks' },
        ]}
        style={{ marginBottom: 16 }}
      />

      {tab === 'errors' ? (
        <Card>
          <Table
            rowKey="id"
            dataSource={errorCards}
            pagination={{ pageSize: 20 }}
            onRow={(r) => ({ onClick: () => navigate(`/catalog/${r.id}`), style: { cursor: 'pointer' } })}
            columns={[
              { title: 'Наименование', dataIndex: 'name' },
              { title: 'Артикул', dataIndex: 'vendor_code' },
              { title: 'GTIN', dataIndex: 'gtin', render: (g) => g ?? '—' },
              { title: 'Статус', dataIndex: 'status', render: (s) => <StatusTag status={s} /> },
              {
                title: 'Замечания',
                render: (_, r) => (
                  <Space size={4} wrap>
                    {r.validation_issues.slice(0, 4).map((i, idx) => (
                      <Tag key={idx} color={i.severity === 'error' ? 'error' : 'warning'}>
                        {i.code}
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
          <Table
            rowKey="id"
            dataSource={tasks}
            pagination={{ pageSize: 20 }}
            columns={[
              { title: 'Задача', dataIndex: 'title' },
              {
                title: 'Приоритет',
                dataIndex: 'priority',
                render: (p: number) => <Tag color={PRIORITY[p]?.color}>{PRIORITY[p]?.label}</Tag>,
              },
              { title: 'Статус', dataIndex: 'status' },
              {
                title: 'Действия',
                render: (_, r) => (
                  <Space>
                    {r.status !== 'in_progress' && (
                      <Button size="small" onClick={() => setStatus(r.id, 'in_progress')}>
                        В работу
                      </Button>
                    )}
                    {r.status !== 'resolved' && (
                      <Button size="small" type="primary" onClick={() => setStatus(r.id, 'resolved')}>
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
    </div>
  )
}
