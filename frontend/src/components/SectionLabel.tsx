import type { ReactNode } from 'react'

// Левый заголовок секции: мелкая «бровь» + хайрлайн-линия вправо. Аккуратнее
// центрированного Divider, задаёт ритм внутри форм.
export function SectionLabel({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '26px 0 16px' }}>
      <span className="eyebrow" style={{ color: 'var(--accent)', whiteSpace: 'nowrap' }}>
        {children}
      </span>
      <span style={{ flex: 1, height: 1, background: 'var(--hairline)' }} />
      {hint && <span style={{ fontSize: 12, color: 'var(--faint)', whiteSpace: 'nowrap' }}>{hint}</span>}
    </div>
  )
}
