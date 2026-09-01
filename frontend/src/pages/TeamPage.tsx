import { PlusOutlined, TeamOutlined } from '@ant-design/icons'
import { App, Button, Card, Empty, Form, Input, Modal, Select, Table, Tag } from 'antd'
import { useCallback, useEffect, useState } from 'react'

import { errorMessage } from '../api/client'
import { createTeamUser, listTeamUsers, updateTeamUserRole } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/PageHeader'
import type { User } from '../types'

type TeamRole = 'client_admin' | 'editor' | 'viewer'

const ROLE_META: Record<string, { label: string; color: string }> = {
  client: { label: 'Владелец', color: 'blue' },
  client_admin: { label: 'Администратор', color: 'blue' },
  editor: { label: 'Редактор', color: 'success' },
  viewer: { label: 'Наблюдатель', color: 'default' },
}

const roleOptions = [
  { value: 'client_admin', label: 'Администратор' },
  { value: 'editor', label: 'Редактор' },
  { value: 'viewer', label: 'Наблюдатель' },
]

interface CreateValues {
  email: string
  password: string
  full_name?: string
  role: TeamRole
}

export function TeamPage() {
  const { message } = App.useApp()
  const { user: currentUser } = useAuth()
  const [form] = Form.useForm<CreateValues>()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [open, setOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setUsers(await listTeamUsers())
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
    form.setFieldsValue({ role: 'editor' })
    setOpen(true)
  }

  const create = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      await createTeamUser({
        email: values.email,
        password: values.password,
        full_name: values.full_name || '',
        role: values.role,
      })
      message.success('Пользователь добавлен')
      setOpen(false)
      form.resetFields()
      await load()
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return
      message.error(errorMessage(error))
    } finally {
      setSaving(false)
    }
  }

  const changeRole = async (user: User, role: TeamRole) => {
    try {
      await updateTeamUserRole(user.id, role)
      message.success('Роль обновлена')
      await load()
    } catch (error) {
      message.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="Команда и права доступа"
        subtitle="Администраторы управляют командой, редакторы изменяют данные, наблюдатели работают только в режиме просмотра."
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreate}>
            Добавить пользователя
          </Button>
        }
      />

      <Card styles={{ body: { padding: 0 } }}>
        <Table<User>
          rowKey="id"
          loading={loading}
          dataSource={users}
          pagination={false}
          locale={{
            emptyText: (
              <Empty
                image={<TeamOutlined aria-hidden style={{ fontSize: 42, color: 'var(--faint)' }} />}
                description="В команде пока нет пользователей"
              />
            ),
          }}
          columns={[
            {
              title: 'Пользователь',
              render: (_, user) => (
                <div>
                  <strong>{user.full_name || 'Без имени'}</strong>
                  <div className="team-secondary">{user.email}</div>
                </div>
              ),
            },
            {
              title: 'Текущая роль', dataIndex: 'role', width: 180,
              render: (role: string) => <Tag color={ROLE_META[role]?.color}>{ROLE_META[role]?.label || role}</Tag>,
            },
            {
              title: 'Изменить роль', width: 220,
              render: (_, user) => user.role === 'client' ? (
                <span className="team-secondary">Основной владелец</span>
              ) : (
                <Select
                  aria-label={`Роль пользователя ${user.email}`}
                  value={user.role as TeamRole}
                  options={roleOptions}
                  disabled={user.id === currentUser?.id}
                  style={{ width: '100%' }}
                  onChange={(role: TeamRole) => void changeRole(user, role)}
                />
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="Новый пользователь"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => void create()}
        okText="Добавить"
        cancelText="Отмена"
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item name="full_name" label="Имя">
            <Input maxLength={255} autoFocus />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email', message: 'Укажите корректный email' }]}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="password" label="Временный пароль" rules={[{ required: true, min: 6, message: 'Минимум 6 символов' }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select options={roleOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
