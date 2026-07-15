import {
  AppstoreOutlined,
  DashboardOutlined,
  ImportOutlined,
  LogoutOutlined,
  ProfileOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { Button, Layout, Menu, Tag, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

const { Header, Sider, Content } = Layout

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isOperator = user?.role === 'operator' || user?.role === 'admin'

  const items = [
    { key: '/', icon: <DashboardOutlined />, label: 'Обзор' },
    { key: '/import', icon: <ImportOutlined />, label: 'Импорт' },
    { key: '/variations', icon: <AppstoreOutlined />, label: 'Вариации' },
    { key: '/catalog', icon: <ProfileOutlined />, label: 'Каталог' },
    ...(isOperator ? [{ key: '/operator', icon: <ToolOutlined />, label: 'Консоль оператора' }] : []),
  ]

  const selectedKey =
    items
      .map((i) => i.key)
      .filter((k) => location.pathname === k || (k !== '/' && location.pathname.startsWith(k)))
      .sort((a, b) => b.length - a.length)[0] ?? '/'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" breakpoint="lg" collapsedWidth="0" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px 20px', fontWeight: 700, fontSize: 18, color: '#1668dc' }}>
          НК-ЛАБ
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={items}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Typography.Text type="secondary">
            Подготовка и валидация карточек НК до заказа кодов
          </Typography.Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Tag color={isOperator ? 'geekblue' : 'green'}>{user?.role}</Tag>
            <Typography.Text>{user?.full_name || user?.email}</Typography.Text>
            <Button icon={<LogoutOutlined />} onClick={signOut} size="small">
              Выйти
            </Button>
          </div>
        </Header>
        <Content style={{ margin: 24 }}>{children}</Content>
      </Layout>
    </Layout>
  )
}
