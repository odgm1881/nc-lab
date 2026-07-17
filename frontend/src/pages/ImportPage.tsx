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
        subtitle="Excel (.xlsx) или CSV. Заголовки распознаются автоматически: Наименование, Артикул, Категория, GTIN, Цвет, Размер, Пол, Состав, Тип РД, Номер РД, Дата РД…"
      />

      <Card>
        <Upload.Dragger
          accept=".xlsx,.csv"
          maxCount={1}
          beforeUpload={(f) => {
            void onPreview(f)
            return false
          }}
          showUploadList={false}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Перетащите файл сюда или нажмите для выбора</p>
          <p className="ant-upload-hint">Файл разбирается на строки, но не сохраняется до подтверждения</p>
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
