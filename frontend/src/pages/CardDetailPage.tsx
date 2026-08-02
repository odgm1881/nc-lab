import { ArrowLeftOutlined, CheckCircleFilled } from '@ant-design/icons'
import { App, Button, Card, Col, Form, Input, Row, Select, Timeline, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { cardHistory, getCard, markCardReady, updateCard, validateCard } from '../api/endpoints'
import { IssueList } from '../components/IssueList'
import { SectionLabel } from '../components/SectionLabel'
import { StatusTag } from '../components/StatusTag'
import type { AuditEvent, Card as CardType } from '../types'

const ATTR_FIELDS = [
  ['item_type', 'Вид изделия'],
  ['composition', 'Состав сырья'],
  ['size', 'Размер'],
  ['color', 'Цвет'],
  ['gender', 'Пол'],
  ['age_group', 'Возрастная группа'],
  ['brand', 'Бренд'],
  ['country', 'Страна'],
]

const RD_TYPES = [
  { value: 'declaration', label: 'Декларация соответствия' },
  { value: 'certificate', label: 'Сертификат соответствия' },
  { value: 'refusal_letter', label: 'Отказное письмо' },
]

export function CardDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [card, setCard] = useState<CardType | null>(null)
  const [history, setHistory] = useState<AuditEvent[]>([])
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    const [loadedCard, loadedHistory] = await Promise.all([getCard(id), cardHistory(id)])
    setCard(loadedCard)
    setHistory(loadedHistory)
  }, [id])

  useEffect(() => {
    load().catch((e) => message.error(errorMessage(e)))
  }, [load, message])

  useEffect(() => {
    if (!card) return
    form.setFieldsValue({
      name: card.name,
      vendor_code: card.vendor_code,
      category_code: card.category_code,
      gtin: card.gtin,
      ...Object.fromEntries(ATTR_FIELDS.map(([k]) => [`attr_${k}`, card.attributes[k] ?? ''])),
      rd_type: card.rd_data.type ?? undefined,
      rd_number: card.rd_data.number ?? '',
      rd_date: card.rd_data.date ?? '',
      rd_valid_until: card.rd_data.valid_until ?? '',
      package_type: card.packaging.type ?? '',
      units_per_package: card.packaging.units_per_package ?? '',
      package_weight_g: card.packaging.weight_g ?? '',
      data_source: card.data_source,
      service_comment: card.service_comment ?? '',
    })
  }, [card, form])

  const collect = () => {
    const v = form.getFieldsValue()
    const attributes: Record<string, string> = {}
    ATTR_FIELDS.forEach(([k]) => {
      if (v[`attr_${k}`]) attributes[k] = v[`attr_${k}`]
    })
    const rd_data: Record<string, string> = {}
    if (v.rd_type) rd_data.type = v.rd_type
    if (v.rd_number) rd_data.number = v.rd_number
    if (v.rd_date) rd_data.date = v.rd_date
    if (v.rd_valid_until) rd_data.valid_until = v.rd_valid_until
    const packaging: Record<string, string | number> = {}
    if (v.package_type) packaging.type = v.package_type
    if (v.units_per_package) packaging.units_per_package = Number(v.units_per_package)
    if (v.package_weight_g) packaging.weight_g = Number(v.package_weight_g)
    return {
      name: v.name,
      vendor_code: v.vendor_code,
      category_code: v.category_code || null,
      gtin: v.gtin || null,
      attributes,
      rd_data,
      packaging,
      data_source: v.data_source || 'manual',
      service_comment: v.service_comment || null,
    }
  }

  const onSave = async () => {
    if (!id) return
    setBusy(true)
    try {
      setCard(await updateCard(id, collect() as Partial<CardType>))
      setHistory(await cardHistory(id))
      message.success('Сохранено (статус сброшен в черновик)')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onValidate = async () => {
    if (!id) return
    setBusy(true)
    try {
      await updateCard(id, collect() as Partial<CardType>)
      const r = await validateCard(id)
      setCard(r.card)
      setHistory(await cardHistory(id))
      if (r.result.is_valid) message.success('Карточка валидна')
      else message.warning(`Ошибок: ${r.result.errors.length}`)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onMarkReady = async () => {
    if (!id) return
    setBusy(true)
    try {
      setCard(await markCardReady(id))
      setHistory(await cardHistory(id))
      message.success('Карточка готова к публикации')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  if (!card) return null

  // Связь панели валидации с полями: подсвечиваем поля, по которым есть ошибки.
  const errorFields = new Set(
    card.validation_issues.filter((i) => i.severity === 'error').map((i) => i.field ?? ''),
  )
  const rdMissing = errorFields.has('rd_data')
  const attrStatus = (k: string) => (errorFields.has(k) ? 'error' : undefined)
  const rdStatus = (k: string) => (rdMissing || errorFields.has(`rd_data.${k}`) ? 'error' : undefined)
  const errorCount = card.validation_issues.filter((i) => i.severity === 'error').length

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/catalog')}
        style={{ marginBottom: 14 }}
      >
        Каталог
      </Button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>{card.name || card.vendor_code}</h1>
        <StatusTag status={card.status} />
        <span style={{ color: 'var(--faint)', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
          {card.vendor_code}
        </span>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={15}>
          <Card title="Карточка" styles={{ body: { paddingBottom: 0 } }}>
            <Form form={form} layout="vertical" requiredMark={false}>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="name" label="Наименование">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="vendor_code" label="Артикул">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="category_code" label="Категория (ТН ВЭД)" validateStatus={attrStatus('category_code')}>
                    <Input placeholder="6109" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="gtin"
                    label="GTIN"
                    tooltip="Необратим. Проверяется до заказа кодов."
                    validateStatus={errorFields.has('gtin') ? 'error' : undefined}
                  >
                    <Input placeholder="4600000000015" style={{ fontFamily: 'var(--font-mono)' }} />
                  </Form.Item>
                </Col>
              </Row>

              <SectionLabel hint="Используется для прослеживаемости">Источник и комментарии</SectionLabel>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="data_source" label="Источник данных">
                    <Select
                      options={[
                        { value: 'manual', label: 'Ручной ввод' },
                        { value: 'excel', label: 'Excel' },
                        { value: 'csv', label: 'CSV' },
                        { value: 'onec', label: '1С' },
                        { value: 'variations', label: 'Конструктор вариаций' },
                      ]}
                    />
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="service_comment" label="Служебный комментарий">
                    <Input.TextArea rows={3} maxLength={4000} showCount />
                  </Form.Item>
                </Col>
              </Row>

              <SectionLabel hint="Логистические данные карточки">Упаковка</SectionLabel>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="package_type" label="Тип упаковки">
                    <Input placeholder="короб" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="units_per_package" label="Единиц в упаковке">
                    <Input type="number" min={1} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="package_weight_g" label="Вес, г">
                    <Input type="number" min={0} />
                  </Form.Item>
                </Col>
              </Row>

              <SectionLabel hint="Обязательны для одежды">Атрибуты категории</SectionLabel>
              <Row gutter={16}>
                {ATTR_FIELDS.map(([k, label]) => (
                  <Col span={12} key={k}>
                    <Form.Item name={`attr_${k}`} label={label} validateStatus={attrStatus(k)}>
                      <Input />
                    </Form.Item>
                  </Col>
                ))}
              </Row>

              <SectionLabel hint="Проверяется до заказа кодов">Разрешительная документация</SectionLabel>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="rd_type" label="Тип" validateStatus={rdStatus('type')}>
                    <Select allowClear options={RD_TYPES} placeholder="Выберите тип" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_number" label="Номер" validateStatus={rdStatus('number')}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_date" label="Дата (ГГГГ-ММ-ДД)" validateStatus={rdStatus('date')}>
                    <Input placeholder="2026-02-01" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_valid_until" label="Действует до (ГГГГ-ММ-ДД)" validateStatus={rdStatus('valid_until')}>
                    <Input placeholder="2029-02-01" />
                  </Form.Item>
                </Col>
              </Row>
            </Form>

            {/* Нижняя панель действий */}
            <div
              style={{
                display: 'flex',
                gap: 10,
                flexWrap: 'wrap',
                margin: '4px -22px 0',
                padding: '16px 22px',
                borderTop: '1px solid var(--hairline)',
                background: 'var(--surface-2)',
                borderBottomLeftRadius: 'var(--r-lg)',
                borderBottomRightRadius: 'var(--r-lg)',
              }}
            >
              <Button onClick={onSave} loading={busy}>
                Сохранить
              </Button>
              <Button type="primary" onClick={onValidate} loading={busy}>
                Сохранить и валидировать
              </Button>
              <Button onClick={onMarkReady} loading={busy} disabled={card.status !== 'valid'}>
                Готово к публикации
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <div style={{ position: 'sticky', top: 16 }}>
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span>Результат валидации</span>
                  {errorCount > 0 ? (
                    <span className="pill pill--error">{errorCount}</span>
                  ) : (
                    <CheckCircleFilled style={{ color: 'var(--success)' }} />
                  )}
                </div>
              }
            >
              <IssueList issues={card.validation_issues} />
              {card.ruleset_version && (
                <Typography.Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                  Правила {card.ruleset_version} · справочники {card.reference_data_version}
                </Typography.Text>
              )}
              {errorCount > 0 && (
                <p style={{ marginTop: 14, marginBottom: 0, fontSize: 12.5, color: 'var(--muted)' }}>
                  Поля с ошибками подсвечены в форме слева. Исправьте и нажмите «Сохранить и
                  валидировать».
                </p>
              )}
            </Card>
            <Card title="История изменений" style={{ marginTop: 16 }}>
              <Timeline
                items={history.slice(0, 30).map((event) => ({
                  children: (
                    <div>
                      <div style={{ fontWeight: 600 }}>{event.action}</div>
                      <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                        {new Date(event.created_at).toLocaleString('ru-RU')}
                        {event.correlation_id ? ` · ${event.correlation_id.slice(0, 8)}` : ''}
                      </div>
                    </div>
                  ),
                }))}
              />
            </Card>
          </div>
        </Col>
      </Row>
    </div>
  )
}
