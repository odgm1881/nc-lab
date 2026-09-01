import type { ReactNode } from 'react'

// Единая шапка страницы: заголовок + подзаголовок слева, действия справа.
export function PageHeader({
  title,
  subtitle,
  extra,
}: {
  title: string
  subtitle?: ReactNode
  extra?: ReactNode
}) {
  return (
    <div
      className="page-header"
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        gap: 16,
        flexWrap: 'wrap',
        marginBottom: 20,
      }}
    >
      <div>
        <h1 style={{ margin: 0, fontSize: 24, lineHeight: 1.2 }}>{title}</h1>
        {subtitle && (
          <p style={{ margin: '6px 0 0', color: 'var(--muted)', fontSize: 14, maxWidth: '70ch' }}>
            {subtitle}
          </p>
        )}
      </div>
      {extra && <div className="page-header-actions">{extra}</div>}
    </div>
  )
}
