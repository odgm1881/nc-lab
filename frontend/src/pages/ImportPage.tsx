import { InboxOutlined } from '@ant-design/icons'
import { App, Button, Card, Space, Table, Tag, Upload } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import { importCommit, importPreview } from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import type { ImportPreview } from '../types'

export function ImportPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [busy, setBusy] = useState(false)

  const onPreview = async (f: File) => {
    setBusy(true)
    try {
      setFile(f)
      setPreview(await importPreview(f))
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onCommit = async () => {
    if (!file) return
    setBusy(true)
    try {
      const res = await importCommit(file)
      message.success(
        `Импортировано строк: ${res.rows_total}, создано и автоматически провалидировано карточек: ${res.cards_created}`,
      )
      navigate('/catalog')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Импорт номенклатуры"
        subtitle="Загрузите ассортимент из Excel или CSV — система разберёт строки, создаст карточки и сразу их провалидирует."
        extra={
          <Space size={6}>
            <Tag>.xlsx</Tag>
            <Tag>.csv</Tag>
            <Tag>1С</Tag>
          </Space>
        }
      />

      {/* Мини-гайд из трёх шагов */}
      <div
        className="stagger"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 12,
          marginBottom: 16,
        }}
      >
        {[
          ['1', 'Загрузите файл', 'Excel/CSV с колонками номенклатуры'],
          ['2', 'Проверьте разбор', 'Предпросмотр распознанных строк'],
          ['3', 'Создайте карточки', 'Автоматическая валидация статусов'],
        ].map(([n, t, d]) => (
          <div
            key={n}
            style={{
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
              background: 'var(--surface)',
              border: '1px solid var(--hairline)',
              borderRadius: 'var(--r-lg)',
              padding: 16,
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            <span
              style={{
                flexShrink: 0,
                width: 26,
                height: 26,
                borderRadius: '50%',
                background: 'var(--accent-soft)',
                color: 'var(--accent)',
                display: 'grid',
                placeItems: 'center',
                fontWeight: 700,
                fontSize: 13,
              }}
            >
              {n}
            </span>
            <span>
              <span style={{ display: 'block', fontWeight: 600, color: 'var(--ink)', fontSize: 14 }}>{t}</span>
              <span style={{ display: 'block', color: 'var(--muted)', fontSize: 12.5, lineHeight: 1.5 }}>{d}</span>
            </span>
          </div>
        ))}
      </div>

      <Card>
        <Upload.Dragger
          accept=".xlsx,.csv"
          maxCount={1}
          beforeUpload={(f) => {
            void onPreview(f)
            return false
          }}
          showUploadList={false}
          disabled={busy}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Перетащите файл сюда или нажмите для выбора</p>
          <p className="ant-upload-hint">
            Распознаются: Наименование, Артикул, Категория, GTIN, Вид изделия, Цвет, Размер, Пол,
            Состав, Возрастная группа, Тип/Номер/Дата РД. Файл не сохраняется до подтверждения.
          </p>
        </Upload.Dragger>
      </Card>

      {preview && (
        <Card
          style={{ marginTop: 16 }}
          title={
            <Space>
              Распознано строк: <Tag color="blue">{preview.rows_total}</Tag>
              Источник: <Tag>{preview.source}</Tag>
            </Space>
          }
          extra={
            <Button type="primary" onClick={onCommit} loading={busy} disabled={preview.rows_total === 0}>
              Создать карточки-черновики
            </Button>
          }
        >
          <Table
            size="small"
            rowKey={(_, i) => String(i)}
            pagination={{ pageSize: 10 }}
            dataSource={preview.rows}
            columns={[
              { title: 'Наименование', dataIndex: 'name' },
              { title: 'Артикул', dataIndex: 'vendor_code' },
              { title: 'Категория', dataIndex: 'category_code' },
              { title: 'GTIN', dataIndex: 'gtin', render: (g) => g ?? <Tag>нет</Tag> },
              {
                title: 'Цвет / Размер',
                render: (_, r) => [r.attributes.color, r.attributes.size].filter(Boolean).join(' / '),
              },
              {
                title: 'РД',
                render: (_, r) => (r.rd_data.type ? <Tag color="green">{r.rd_data.type}</Tag> : <Tag>нет</Tag>),
              },
            ]}
          />
        </Card>
      )}
    </div>
  )
}
