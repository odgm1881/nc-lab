import { ArrowLeftOutlined, CheckCircleFilled } from '@ant-design/icons'
import { App, Button, Card, Col, Form, Input, Row, Select } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { getCard, publishCard, updateCard, validateCard } from '../api/endpoints'
import { IssueList } from '../components/IssueList'
import { SectionLabel } from '../components/SectionLabel'
import { StatusTag } from '../components/StatusTag'
import type { Card as CardType } from '../types'

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
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setCard(await getCard(id))
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
    return {
      name: v.name,
      vendor_code: v.vendor_code,
      category_code: v.category_code || null,
      gtin: v.gtin || null,
      attributes,
      rd_data,
    }
  }

  const onSave = async () => {
    if (!id) return
    setBusy(true)
    try {
      setCard(await updateCard(id, collect() as Partial<CardType>))
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
      if (r.result.is_valid) message.success('Карточка валидна')
      else message.warning(`Ошибок: ${r.result.errors.length}`)
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onPublish = async () => {
    if (!id) return
    setBusy(true)
    try {
      setCard(await publishCard(id))
      message.success('Опубликовано в НК')
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
              <Button onClick={onPublish} loading={busy} disabled={card.status !== 'valid'}>
                Опубликовать в НК
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
              {errorCount > 0 && (
                <p style={{ marginTop: 14, marginBottom: 0, fontSize: 12.5, color: 'var(--muted)' }}>
                  Поля с ошибками подсвечены в форме слева. Исправьте и нажмите «Сохранить и
                  валидировать».
                </p>
              )}
            </Card>
          </div>
        </Col>
      </Row>
    </div>
  )
}
