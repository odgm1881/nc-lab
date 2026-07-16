import {
  AppstoreOutlined,
  DashboardOutlined,
  ImportOutlined,
  LogoutOutlined,
  ProfileOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { Avatar, Dropdown } from 'antd'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { Brand } from './Brand'

const NAV = [
  { key: '/', icon: <DashboardOutlined />, label: 'Обзор' },
  { key: '/import', icon: <ImportOutlined />, label: 'Импорт' },
  { key: '/variations', icon: <AppstoreOutlined />, label: 'Вариации' },
  { key: '/catalog', icon: <ProfileOutlined />, label: 'Каталог' },
]

const OPERATOR_NAV = { key: '/operator', icon: <ToolOutlined />, label: 'Консоль оператора' }

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [scrolled, setScrolled] = useState(false)
  const isOperator = user?.role === 'operator' || user?.role === 'admin'

  const items = isOperator ? [...NAV, OPERATOR_NAV] : NAV

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

  const roleLabel = isOperator ? 'Оператор' : 'Клиент'

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'var(--side-w, 248px) 1fr', height: '100vh' }}>
      {/* --- сайдбар: тёмный «структурный» слой (apple §12) --- */}
      <aside
        style={{
          background: 'linear-gradient(180deg, var(--side-bg-2), var(--side-bg))',
          borderRight: '1px solid var(--side-hairline)',
          display: 'flex',
          flexDirection: 'column',
          padding: '18px 12px',
          gap: 4,
        }}
      >
        <div style={{ padding: '6px 10px 18px' }}>
          <Brand dark />
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {items.map((item) => {
            const on = active === item.key
            return (
              <button
                key={item.key}
                onClick={() => navigate(item.key)}
                className="tap"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '10px 12px',
                  border: 'none',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: on ? 600 : 500,
                  color: on ? '#5eead4' : 'var(--side-muted)',
                  background: on ? 'var(--side-active)' : 'transparent',
                  transition: 'background 160ms var(--ease-out), color 160ms var(--ease-out)',
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => {
                  if (!on) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
                }}
                onMouseLeave={(e) => {
                  if (!on) e.currentTarget.style.background = 'transparent'
                }}
              >
                <span style={{ fontSize: 17, display: 'inline-flex' }}>{item.icon}</span>
                {item.label}
              </button>
            )
          })}
        </nav>

        <div style={{ marginTop: 'auto', padding: '0 6px' }}>
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
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <header
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
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>
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
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
                {user?.full_name || user?.email}
              </span>
            </button>
          </Dropdown>
        </header>

        <main id="content-scroll" style={{ overflow: 'auto', flex: 1 }}>
          <div key={location.pathname} className="rise" style={{ maxWidth: 1240, margin: '0 auto', padding: '28px' }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
