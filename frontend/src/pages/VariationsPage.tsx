import { App, Button, Card, Col, Form, Input, Row, Table, Tag } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { buildFromVariations, previewVariations } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import { SectionLabel } from '../components/SectionLabel'
import type { VariationPreview } from '../types'

// Ввод осей через запятую -> массив.
const toList = (v?: string) =>
  (v ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

export function VariationsPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [preview, setPreview] = useState<VariationPreview | null>(null)
  const [saving, setSaving] = useState(false)

  const values = () => {
    const v = form.getFieldsValue()
    return {
      base_vendor_code: v.base_vendor_code || 'SKU',
      colors: toList(v.colors),
      sizes: toList(v.sizes),
      genders: toList(v.genders),
      completeness: toList(v.completeness),
    }
  }

  const onPreview = async () => {
    try {
      setPreview(await previewVariations(values()))
    } catch (e) {
      message.error(errorMessage(e))
    }
  }

  const onBuild = async () => {
    const v = form.getFieldsValue()
    if (!v.name) {
      message.warning('Укажите наименование модели')
      return
    }
    setSaving(true)
    try {
      const res = await buildFromVariations({
        name: v.name,
        base_vendor_code: v.base_vendor_code || 'SKU',
        category_code: v.category_code || undefined,
        common_attributes: {
          ...(v.item_type ? { item_type: v.item_type } : {}),
          ...(v.composition ? { composition: v.composition } : {}),
          ...(v.age_group ? { age_group: v.age_group } : {}),
        },
        rd_data: {},
        colors: toList(v.colors),
        sizes: toList(v.sizes),
        genders: toList(v.genders),
        completeness: toList(v.completeness),
      })
      message.success(`Создано и провалидировано карточек: ${res.created}`)
      navigate('/catalog')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Построение вариаций"
        subtitle="Модель раскрывается декартовым произведением осей. Каждая комбинация — отдельный SKU и отдельная карточка НК (правило легпрома 1 GTIN = 1 карточка)."
      />

      <Card styles={{ body: { paddingBottom: 0 } }}>
        <Form form={form} layout="vertical" requiredMark={false} initialValues={{ base_vendor_code: 'TSHIRT-01' }}>
          <SectionLabel>Модель</SectionLabel>
          <Row gutter={16}>
            <Col xs={24} md={10}>
              <Form.Item name="name" label="Наименование модели">
                <Input placeholder="Футболка базовая" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="base_vendor_code" label="Базовый артикул">
                <Input placeholder="TSHIRT-01" />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="category_code" label="Категория (ТН ВЭД)">
                <Input placeholder="6109" />
              </Form.Item>
            </Col>
          </Row>

          <SectionLabel hint="Значения через запятую">Оси вариаций</SectionLabel>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item name="colors" label="Цвета">
                <Input placeholder="чёрный, белый, синий" />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="sizes" label="Размеры">
                <Input placeholder="S, M, L, XL" />
              </Form.Item>
            </Col>
            <Col xs={24} md={5}>
              <Form.Item name="genders" label="Пол">
                <Input placeholder="мужской" />
              </Form.Item>
            </Col>
            <Col xs={24} md={5}>
              <Form.Item name="completeness" label="Комплектность">
                <Input placeholder="штука" />
              </Form.Item>
            </Col>
          </Row>

          <SectionLabel hint="Применяются ко всем SKU модели">Общие атрибуты</SectionLabel>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item name="item_type" label="Вид изделия">
                <Input placeholder="футболка" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="composition" label="Состав">
                <Input placeholder="хлопок 100%" />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="age_group" label="Возрастная группа">
                <Input placeholder="взрослая" />
              </Form.Item>
            </Col>
          </Row>
        </Form>

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
          <Button onClick={onPreview}>Предпросмотр</Button>
          <Button type="primary" onClick={onBuild} loading={saving}>
            Создать карточки
          </Button>
        </div>
      </Card>

      {preview && (
        <Card style={{ marginTop: 16 }} title={<>Будет создано SKU: <Tag color="blue">{preview.count}</Tag></>}>
          <Table
            size="small"
            rowKey="sku"
            pagination={{ pageSize: 10 }}
            dataSource={preview.variations}
            columns={[
              { title: 'Артикул SKU', dataIndex: 'sku' },
              { title: 'Цвет', dataIndex: 'color' },
              { title: 'Размер', dataIndex: 'size' },
              { title: 'Пол', dataIndex: 'gender' },
              { title: 'Комплектность', dataIndex: 'completeness' },
            ]}
          />
        </Card>
      )}
    </div>
  )
}
