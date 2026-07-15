import { ArrowLeftOutlined } from '@ant-design/icons'
import { App, Button, Card, Col, Divider, Form, Input, Row, Select, Space, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { getCard, publishCard, updateCard, validateCard } from '../api/endpoints'
import { IssueList } from '../components/IssueList'
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
    const c = await getCard(id)
    setCard(c)
    form.setFieldsValue({
      name: c.name,
      vendor_code: c.vendor_code,
      category_code: c.category_code,
      gtin: c.gtin,
      ...Object.fromEntries(ATTR_FIELDS.map(([k]) => [`attr_${k}`, c.attributes[k] ?? ''])),
      rd_type: c.rd_data.type ?? undefined,
      rd_number: c.rd_data.number ?? '',
      rd_date: c.rd_data.date ?? '',
      rd_valid_until: c.rd_data.valid_until ?? '',
    })
  }, [id, form])

  useEffect(() => {
    load().catch((e) => message.error(errorMessage(e)))
  }, [load, message])

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
      void load()
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

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/catalog')}>
          Каталог
        </Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {card.name || card.vendor_code}
        </Typography.Title>
        <StatusTag status={card.status} />
      </Space>

      <Row gutter={16}>
        <Col xs={24} lg={15}>
          <Card title="Карточка">
            <Form form={form} layout="vertical">
              <Row gutter={12}>
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
                  <Form.Item name="category_code" label="Категория (ТН ВЭД)">
                    <Input placeholder="6109" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="gtin" label="GTIN" tooltip="Необратим. Проверяется до заказа кодов.">
                    <Input placeholder="4600000000015" />
                  </Form.Item>
                </Col>
              </Row>

              <Divider>Атрибуты категории</Divider>
              <Row gutter={12}>
                {ATTR_FIELDS.map(([k, label]) => (
                  <Col span={12} key={k}>
                    <Form.Item name={`attr_${k}`} label={label}>
                      <Input />
                    </Form.Item>
                  </Col>
                ))}
              </Row>

              <Divider>Разрешительная документация (РД)</Divider>
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="rd_type" label="Тип">
                    <Select allowClear options={RD_TYPES} placeholder="Выберите тип" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_number" label="Номер">
                    <Input />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_date" label="Дата (ГГГГ-ММ-ДД)">
                    <Input placeholder="2026-02-01" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="rd_valid_until" label="Действует до (ГГГГ-ММ-ДД)">
                    <Input placeholder="2029-02-01" />
                  </Form.Item>
                </Col>
              </Row>

              <Space>
                <Button onClick={onSave} loading={busy}>
                  Сохранить
                </Button>
                <Button type="primary" onClick={onValidate} loading={busy}>
                  Сохранить и валидировать
                </Button>
                <Button
                  onClick={onPublish}
                  loading={busy}
                  disabled={card.status !== 'valid'}
                >
                  Опубликовать в НК
                </Button>
              </Space>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <Card title="Результат валидации">
            <IssueList issues={card.validation_issues} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
