import type { CardStatus } from '../types'

const LABEL: Record<CardStatus, string> = {
  draft: 'Черновик',
  validating: 'Валидация',
  valid: 'Валидна',
  error: 'Ошибки',
  published: 'Готова к публикации',
}

// Мягкая статус-пилюля (фон-тинт + цветной текст + точка). Класс .pill в global.css.
export function StatusTag({ status }: { status: CardStatus }) {
  return <span className={`pill pill--${status}`}>{LABEL[status] ?? status}</span>
}
