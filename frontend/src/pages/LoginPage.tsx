import { App, Button, Card, Form, Input, Segmented, Typography } from 'antd'
import { useState } from 'react'

import { errorMessage } from '../api/client'
import { register } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { signIn } = useAuth()
  const { message } = App.useApp()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)

  const onLogin = async (v: { email: string; password: string }) => {
    setLoading(true)
    try {
      await signIn(v.email, v.password)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const onRegister = async (v: {
    email: string
    password: string
    full_name: string
    client_name: string
  }) => {
    setLoading(true)
    try {
      await register(v)
      await signIn(v.email, v.password)
      message.success('Аккаунт создан')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', background: '#f5f5f5' }}>
      <Card style={{ width: 420 }}>
        <Typography.Title level={3} style={{ textAlign: 'center', color: '#1668dc' }}>
          НК-ЛАБ
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          Карточки Национального каталога и маркировки одежды
        </Typography.Paragraph>

        <Segmented
          block
          value={mode}
          onChange={(v) => setMode(v as 'login' | 'register')}
          options={[
            { label: 'Вход', value: 'login' },
            { label: 'Регистрация', value: 'register' },
          ]}
          style={{ marginBottom: 20 }}
        />

        {mode === 'login' ? (
          <Form layout="vertical" onFinish={onLogin} initialValues={{ email: 'client@nk-lab.ru', password: 'password' }}>
            <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
              <Input placeholder="client@nk-lab.ru" />
            </Form.Item>
            <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
              <Input.Password placeholder="password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              Войти
            </Button>
            <Typography.Paragraph type="secondary" style={{ marginTop: 12, fontSize: 12 }}>
              Демо: client@nk-lab.ru / password (клиент), operator@nk-lab.ru / password (оператор)
            </Typography.Paragraph>
          </Form>
        ) : (
          <Form layout="vertical" onFinish={onRegister}>
            <Form.Item name="client_name" label="Организация" rules={[{ required: true }]}>
              <Input placeholder="ООО Импортёр" />
            </Form.Item>
            <Form.Item name="full_name" label="Имя">
              <Input placeholder="Иван Иванов" />
            </Form.Item>
            <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
              <Input />
            </Form.Item>
            <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 6 }]}>
              <Input.Password />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              Создать аккаунт
            </Button>
          </Form>
        )}
      </Card>
    </div>
  )
}
