import {
  AppstoreOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  ImportOutlined,
  LinkOutlined,
  LogoutOutlined,
  ProfileOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Avatar, Dropdown } from 'antd'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Brand } from './Brand'

const NAV = [
  { key: '/', icon: <DashboardOutlined />, label: 'Обзор' },
  { key: '/pilots', icon: <ExperimentOutlined />, label: 'Пилоты' },
  { key: '/import', icon: <ImportOutlined />, label: 'Импорт' },
  { key: '/variations', icon: <AppstoreOutlined />, label: 'Вариации' },
  { key: '/catalog', icon: <ProfileOutlined />, label: 'Каталог' },
  { key: '/integration', icon: <LinkOutlined />, label: 'Интеграция НК' },
]

const OPERATOR_NAV = { key: '/operator', icon: <ToolOutlined />, label: 'Консоль оператора' }
const RULES_NAV = { key: '/validation-rules', icon: <SafetyCertificateOutlined />, label: 'Правила валидации' }
const TEAM_NAV = { key: '/team', icon: <TeamOutlined />, label: 'Команда' }

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [scrolled, setScrolled] = useState(false)
  const isOperator = user?.role === 'operator' || user?.role === 'admin'
  const canEdit = user?.role !== 'viewer'
  const canManageTeam = Boolean(
    user?.client_id && ['client', 'client_admin', 'admin'].includes(user.role),
  )

  const baseItems = canEdit ? NAV : NAV.filter((item) => !['/import', '/variations'].includes(item.key))
  const items = [
    ...baseItems,
    ...(isOperator ? [OPERATOR_NAV, RULES_NAV] : []),
    ...(canManageTeam ? [TEAM_NAV] : []),
  ]

  const active =
    items
      .map((i) => i.key)
      .filter((k) => location.pathname === k || (k !== '/' && location.pathname.startsWith(k)))
      .sort((a, b) => b.length - a.length)[0] ?? '/'

  useEffect(() => {
    const el = document.getElementById('content-scroll')
    if (!el) return
    const onScroll = () => setScrolled(el.scrollTop > 4)
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  const roleLabel = {
    client: 'Владелец', client_admin: 'Администратор', editor: 'Редактор', viewer: 'Наблюдатель',
    operator: 'Оператор', admin: 'Администратор платформы',
  }[user?.role || 'viewer']

  return (
    <div className="app-shell">
      {/* --- сайдбар: тёмный «структурный» слой (apple §12) --- */}
      <aside
        className="app-sidebar"
        style={{
          background: 'linear-gradient(180deg, var(--side-bg-2), var(--side-bg))',
          borderRight: '1px solid var(--side-hairline)',
          display: 'flex',
          flexDirection: 'column',
          padding: '18px 14px',
          gap: 4,
        }}
      >
        <div className="app-sidebar-brand" style={{ padding: '6px 10px 20px' }}>
          <Brand dark />
        </div>

        <div
          className="eyebrow app-sidebar-eyebrow"
          style={{ padding: '0 12px 8px', color: 'rgba(147,161,181,0.7)' }}
        >
          Навигация
        </div>

        <nav className="app-nav">
          {items.map((item) => {
            const on = active === item.key
            return (
              <button
                key={item.key}
                onClick={() => navigate(item.key)}
                className={`app-nav-button tap${on ? ' app-nav-button--active' : ''}`}
              >
                <span className="app-nav-button__icon">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="app-sidebar-footer" style={{ marginTop: 'auto', padding: '0 6px' }}>
          <div
            style={{
              fontSize: 12,
              color: 'var(--side-muted)',
              lineHeight: 1.5,
              padding: '12px',
              borderRadius: 'var(--r-md)',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--side-hairline)',
            }}
          >
            Этап 1 · MVP
            <br />
            Валидация карточек до заказа кодов
          </div>
        </div>
      </aside>

      {/* --- основная область --- */}
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, minHeight: 0 }}>
        <header
          className="app-header"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            padding: '0 28px',
            height: 64,
            background: 'rgba(255,255,255,0.72)',
            backdropFilter: 'blur(12px) saturate(180%)',
            WebkitBackdropFilter: 'blur(12px) saturate(180%)',
            borderBottom: scrolled ? '1px solid var(--hairline)' : '1px solid transparent',
            boxShadow: scrolled ? '0 1px 0 rgba(15,23,42,0.04)' : 'none',
            transition: 'border-color 200ms var(--ease-out), box-shadow 200ms var(--ease-out)',
          }}
        >
          <div className="app-header-context" style={{ color: 'var(--muted)', fontSize: 13 }}>
            Национальный каталог · маркировка одежды
          </div>

          <Dropdown
            menu={{
              items: [
                { key: 'role', label: `Роль: ${roleLabel}`, disabled: true },
                { type: 'divider' },
                { key: 'out', icon: <LogoutOutlined />, label: 'Выйти', onClick: signOut },
              ],
            }}
            trigger={['click']}
          >
            <button
              className="tap"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '5px 10px 5px 6px',
                border: '1px solid var(--hairline)',
                borderRadius: 'var(--r-pill)',
                background: 'var(--surface)',
                cursor: 'pointer',
                boxShadow: 'var(--shadow-xs)',
              }}
            >
              <Avatar size={28} style={{ background: 'var(--accent)', fontSize: 13 }}>
                {(user?.full_name || user?.email || '?').slice(0, 1).toUpperCase()}
              </Avatar>
              <span className="app-user-label" style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
                {user?.full_name || user?.email}
              </span>
            </button>
          </Dropdown>
        </header>

        <main
          id="content-scroll"
          className="app-canvas"
          style={{ overflow: 'auto', flex: 1, minHeight: 0 }}
        >
          <div key={location.pathname} className="rise app-content" style={{ maxWidth: 1240, margin: '0 auto' }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
