import { Tag } from 'antd'

import type { CardStatus } from '../types'

const MAP: Record<CardStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: 'Черновик' },
  validating: { color: 'processing', label: 'Валидация' },
  valid: { color: 'success', label: 'Валидна' },
  error: { color: 'error', label: 'Ошибки' },
  published: { color: 'blue', label: 'Опубликована' },
}

export function StatusTag({ status }: { status: CardStatus }) {
  const s = MAP[status] ?? { color: 'default', label: status }
  return <Tag color={s.color}>{s.label}</Tag>
}
