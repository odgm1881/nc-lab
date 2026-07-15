import { Card, Col, Row, Statistic, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listCards } from '../api/endpoints'
import type { CardStatus } from '../types'

const STATUSES: { key: CardStatus; label: string; color: string }[] = [
  { key: 'draft', label: 'Черновики', color: '#8c8c8c' },
  { key: 'error', label: 'С ошибками', color: '#cf1322' },
  { key: 'valid', label: 'Валидны', color: '#389e0d' },
  { key: 'published', label: 'Опубликованы', color: '#1668dc' },
]

export function DashboardPage() {
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [total, setTotal] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    listCards({ limit: 1 }).then((r) => setTotal(r.total))
    STATUSES.forEach((s) =>
      listCards({ status: s.key, limit: 1 }).then((r) =>
        setCounts((c) => ({ ...c, [s.key]: r.total })),
      ),
    )
  }, [])

  return (
    <div>
      <Typography.Title level={4}>Обзор каталога</Typography.Title>
      <Typography.Paragraph type="secondary">
        Цепочка НК → GTIN → РД → коды. Задача — довести карточки до статуса «Валидна» и
        опубликовать до заказа кодов маркировки.
      </Typography.Paragraph>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={4}>
          <Card>
            <Statistic title="Всего карточек" value={total} />
          </Card>
        </Col>
        {STATUSES.map((s) => (
          <Col xs={24} sm={12} md={5} key={s.key}>
            <Card hoverable onClick={() => navigate(`/catalog?status=${s.key}`)}>
              <Statistic
                title={s.label}
                value={counts[s.key] ?? 0}
                styles={{ content: { color: s.color } }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="С чего начать">
        <Typography.Paragraph>
          1. <b>Импорт</b> — загрузите номенклатуру из Excel/CSV/1С, система разберёт строки.
        </Typography.Paragraph>
        <Typography.Paragraph>
          2. <b>Вариации</b> — раскройте модель в SKU (цвет × размер × пол × комплектность):
          каждая комбинация станет отдельной карточкой (правило легпрома 1 GTIN = 1 карточка).
        </Typography.Paragraph>
        <Typography.Paragraph>
          3. <b>Каталог</b> — заполните GTIN и РД, прогоните валидацию и опубликуйте.
        </Typography.Paragraph>
      </Card>
    </div>
  )
}
