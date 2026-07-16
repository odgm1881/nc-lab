import { App, Button, Form, Input, Segmented } from 'antd'
import { useState } from 'react'

import { errorMessage } from '../api/client'
import { register } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../components/Brand'

const CHAIN = ['Нац. каталог', 'GTIN', 'РД', 'Коды маркировки']

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
    <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 1fr', minHeight: '100vh' }}>
      {/* --- левая брендовая панель --- */}
      <div
        className="login-brand"
        style={{
          position: 'relative',
          overflow: 'hidden',
          background: 'radial-gradient(120% 120% at 0% 0%, #123b39 0%, #0d1521 55%)',
          color: '#eef2f8',
          padding: '48px 56px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}
      >
        {/* мягкое teal-свечение */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            width: 520,
            height: 520,
            right: -160,
            top: -120,
            background: 'radial-gradient(circle, rgba(20,184,166,0.28), transparent 60%)',
            filter: 'blur(20px)',
          }}
        />
        <Brand dark size={34} />

        <div style={{ position: 'relative', maxWidth: 460 }}>
          <h1 style={{ color: '#fff', fontSize: 40, lineHeight: 1.08, margin: 0, letterSpacing: '-0.03em' }}>
            Карточки, которые проходят с первого раза
          </h1>
          <p style={{ color: '#aab6c6', fontSize: 16, lineHeight: 1.6, marginTop: 16 }}>
            Проверяем атрибуты, вариации, GTIN и РД <b style={{ color: '#5eead4' }}>до</b> заказа
            кодов. Меньше возвратов на доработку, спокойная поставка в срок.
          </p>

          {/* цепочка НК → GTIN → РД → коды */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 28, flexWrap: 'wrap' }}>
            {CHAIN.map((step, i) => (
              <span key={step} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <span
                  style={{
                    padding: '6px 12px',
                    borderRadius: 'var(--r-pill)',
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.10)',
                    fontSize: 13,
                    fontWeight: 600,
                    color: '#cbd5e1',
                  }}
                >
                  {step}
                </span>
                {i < CHAIN.length - 1 && <span style={{ color: '#3f5468' }}>→</span>}
              </span>
            ))}
          </div>
        </div>

        <div style={{ position: 'relative', display: 'flex', gap: 28 }}>
          {[
            ['1 GTIN', '= 1 карточка'],
            ['3 пилота', 'этап 1'],
            ['300–500', 'карточек'],
          ].map(([a, b]) => (
            <div key={a}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#fff' }}>{a}</div>
              <div style={{ fontSize: 13, color: '#8595a8' }}>{b}</div>
            </div>
          ))}
        </div>
      </div>

      {/* --- правая форма --- */}
      <div style={{ display: 'grid', placeItems: 'center', padding: 24, background: 'var(--bg)' }}>
        <div className="rise" style={{ width: '100%', maxWidth: 380 }}>
          <h2 style={{ fontSize: 22, margin: '0 0 4px' }}>
            {mode === 'login' ? 'Вход в кабинет' : 'Регистрация'}
          </h2>
          <p style={{ color: 'var(--muted)', margin: '0 0 20px', fontSize: 14 }}>
            {mode === 'login'
              ? 'Войдите, чтобы продолжить работу с карточками.'
              : 'Создайте организацию и первого пользователя.'}
          </p>

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
            <Form
              layout="vertical"
              onFinish={onLogin}
              requiredMark={false}
              initialValues={{ email: 'client@nk-lab.ru', password: 'password' }}
            >
              <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
                <Input size="large" placeholder="client@nk-lab.ru" />
              </Form.Item>
              <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
                <Input.Password size="large" placeholder="••••••••" />
              </Form.Item>
              <Button type="primary" htmlType="submit" size="large" block loading={loading}>
                Войти
              </Button>
              <div
                style={{
                  marginTop: 16,
                  padding: '10px 12px',
                  borderRadius: 'var(--r-md)',
                  background: 'var(--accent-soft)',
                  color: 'var(--accent-strong)',
                  fontSize: 12.5,
                  lineHeight: 1.6,
                }}
              >
                Демо: <b>client@nk-lab.ru</b> / password — клиент
                <br />
                <b>operator@nk-lab.ru</b> / password — оператор
              </div>
            </Form>
          ) : (
            <Form layout="vertical" onFinish={onRegister} requiredMark={false}>
              <Form.Item name="client_name" label="Организация" rules={[{ required: true }]}>
                <Input size="large" placeholder="ООО «Импортёр»" />
              </Form.Item>
              <Form.Item name="full_name" label="Имя">
                <Input size="large" placeholder="Иван Иванов" />
              </Form.Item>
              <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
                <Input size="large" />
              </Form.Item>
              <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 6 }]}>
                <Input.Password size="large" />
              </Form.Item>
              <Button type="primary" htmlType="submit" size="large" block loading={loading}>
                Создать аккаунт
              </Button>
            </Form>
          )}
        </div>
      </div>
    </div>
  )
}
