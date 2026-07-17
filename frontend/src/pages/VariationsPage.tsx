import { App, Button, Card, Divider, Form, Input, Space, Table, Tag } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { buildFromVariations, previewVariations } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
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

      <Card>
        <Form form={form} layout="vertical" initialValues={{ base_vendor_code: 'TSHIRT-01' }}>
          <Space size="large" wrap>
            <Form.Item name="name" label="Наименование модели" style={{ minWidth: 240 }}>
              <Input placeholder="Футболка базовая" />
            </Form.Item>
            <Form.Item name="base_vendor_code" label="Базовый артикул" style={{ minWidth: 180 }}>
              <Input placeholder="TSHIRT-01" />
            </Form.Item>
            <Form.Item name="category_code" label="Категория (ТН ВЭД)" style={{ minWidth: 160 }}>
              <Input placeholder="6109" />
            </Form.Item>
          </Space>
          <Space size="large" wrap>
            <Form.Item name="colors" label="Цвета (через запятую)" style={{ minWidth: 240 }}>
              <Input placeholder="чёрный, белый, синий" />
            </Form.Item>
            <Form.Item name="sizes" label="Размеры" style={{ minWidth: 200 }}>
              <Input placeholder="S, M, L, XL" />
            </Form.Item>
            <Form.Item name="genders" label="Пол" style={{ minWidth: 160 }}>
              <Input placeholder="мужской" />
            </Form.Item>
            <Form.Item name="completeness" label="Комплектность" style={{ minWidth: 160 }}>
              <Input placeholder="штука" />
            </Form.Item>
          </Space>

          <Divider>Общие атрибуты (для всех SKU)</Divider>
          <Space size="large" wrap>
            <Form.Item name="item_type" label="Вид изделия" style={{ minWidth: 200 }}>
              <Input placeholder="футболка" />
            </Form.Item>
            <Form.Item name="composition" label="Состав" style={{ minWidth: 200 }}>
              <Input placeholder="хлопок 100%" />
            </Form.Item>
            <Form.Item name="age_group" label="Возрастная группа" style={{ minWidth: 180 }}>
              <Input placeholder="взрослая" />
            </Form.Item>
          </Space>

          <Space>
            <Button onClick={onPreview}>Предпросмотр</Button>
            <Button type="primary" onClick={onBuild} loading={saving}>
              Создать карточки
            </Button>
          </Space>
        </Form>
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
