// Брендовый знак: скруглённый тайл с «галочкой-проверкой» (валидация — суть продукта).
// Простой геометрический мономарк (допустимо по taste-skill), без hand-rolled иллюстраций.

export function BrandMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
      <defs>
        <linearGradient id="nk-mark" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#14b8a6" />
          <stop offset="1" stopColor="#0f766e" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="9" fill="url(#nk-mark)" />
      <path
        d="M9 16.5l4.2 4.2L23 11"
        stroke="#fff"
        strokeWidth="2.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <rect x="1.5" y="1.5" width="29" height="29" rx="8.5" stroke="rgba(255,255,255,0.16)" />
    </svg>
  )
}

export function Brand({ size = 30, dark = false }: { size?: number; dark?: boolean }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <BrandMark size={size} />
      <span
        style={{
          fontWeight: 700,
          fontSize: 16,
          letterSpacing: '0.02em',
          color: dark ? '#eef2f8' : 'var(--ink)',
        }}
      >
        НК<span style={{ color: '#14b8a6' }}>·</span>ЛАБ
      </span>
    </span>
  )
}
