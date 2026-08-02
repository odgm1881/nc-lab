import { InboxOutlined } from '@ant-design/icons'
import { App, Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Upload } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import {
  createMappingProfile,
  deleteMappingProfile,
  downloadImportErrorReport,
  importCommit,
  importPreview,
  listImportJobs,
  listMappingProfiles,
} from '../api/endpoints'
import { PageHeader } from '../components/PageHeader'
import type { ImportCommit, ImportJob, ImportPreview, MappingProfile } from '../types'

export function ImportPage() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const [profiles, setProfiles] = useState<MappingProfile[]>([])
  const [profileId, setProfileId] = useState<string>()
  const [profileOpen, setProfileOpen] = useState(false)
  const [lastCommit, setLastCommit] = useState<ImportCommit | null>(null)
  const [jobs, setJobs] = useState<ImportJob[]>([])
  const [profileForm] = Form.useForm()

  const loadProfiles = async () => setProfiles(await listMappingProfiles())
  const loadJobs = async () => setJobs(await listImportJobs())

  useEffect(() => {
    Promise.all([loadProfiles(), loadJobs()]).catch((e) => message.error(errorMessage(e)))
  }, [message])

  const onPreview = async (f: File) => {
    setBusy(true)
    try {
      setFile(f)
      setLastCommit(null)
      setPreview(await importPreview(f, undefined, profileId))
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
      const res = await importCommit(file, undefined, profileId)
      setLastCommit(res)
      await loadJobs()
      message.success(
        `Создано карточек: ${res.cards_created}; без ошибок: ${res.rows_success}; с ошибками: ${res.rows_error}`,
      )
      if (res.rows_error === 0) navigate('/catalog')
    } catch (e) {
      message.error(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const onCreateProfile = async () => {
    try {
      const values = await profileForm.validateFields()
      let mapping: Record<string, string>
      try {
        mapping = JSON.parse(values.mapping_json) as Record<string, string>
      } catch {
        message.error('Сопоставление должно быть корректным JSON-объектом')
        return
      }
      const profile = await createMappingProfile({
        name: values.name,
        source: values.source,
        mapping,
      })
      await loadProfiles()
      setProfileId(profile.id)
      setProfileOpen(false)
      profileForm.resetFields()
      message.success('Профиль сопоставления сохранён')
    } catch (e) {
      if (e && typeof e === 'object' && 'errorFields' in e) return
      message.error(errorMessage(e))
    }
  }

  const onDeleteProfile = async () => {
    if (!profileId) return
    try {
      await deleteMappingProfile(profileId)
      setProfileId(undefined)
      await loadProfiles()
      message.success('Профиль удалён')
    } catch (e) {
      message.error(errorMessage(e))
    }
  }

  const onDownloadReport = async (jobId = lastCommit?.job_id) => {
    if (!jobId) return
    try {
      const blob = await downloadImportErrorReport(jobId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `import-errors-${jobId.slice(0, 8)}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      message.error(errorMessage(e))
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
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            allowClear
            placeholder="Профиль сопоставления колонок"
            value={profileId}
            onChange={setProfileId}
            style={{ minWidth: 280 }}
            options={profiles.map((profile) => ({ value: profile.id, label: profile.name }))}
          />
          <Button onClick={() => setProfileOpen(true)}>Сохранить новый профиль</Button>
          <Button danger disabled={!profileId} onClick={onDeleteProfile}>
            Удалить выбранный
          </Button>
        </Space>
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
      {lastCommit && lastCommit.rows_error > 0 && (
        <Card style={{ marginTop: 16 }} title="Протокол импорта">
          <Space wrap>
            <Tag color="green">Без ошибок: {lastCommit.rows_success}</Tag>
            <Tag color="red">С ошибками: {lastCommit.rows_error}</Tag>
            <Button onClick={() => void onDownloadReport()}>Скачать отчёт ошибок CSV</Button>
            <Button type="primary" onClick={() => navigate('/catalog')}>
              Открыть созданные карточки
            </Button>
          </Space>
        </Card>
      )}
      {jobs.length > 0 && (
        <Card style={{ marginTop: 16 }} title="История импортов">
          <Table
            size="small"
            rowKey="id"
            dataSource={jobs}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: 'Файл', dataIndex: 'filename' },
              {
                title: 'Дата',
                dataIndex: 'created_at',
                render: (value: string) => new Date(value).toLocaleString('ru-RU'),
              },
              { title: 'Строк', dataIndex: 'rows_total', width: 80 },
              { title: 'Без ошибок', dataIndex: 'rows_success', width: 110 },
              { title: 'С ошибками', dataIndex: 'rows_error', width: 110 },
              {
                title: '',
                width: 160,
                render: (_, job: ImportJob) =>
                  job.rows_error > 0 ? (
                    <Button size="small" onClick={() => void onDownloadReport(job.id)}>
                      Скачать отчёт
                    </Button>
                  ) : null,
              },
            ]}
          />
        </Card>
      )}
      <Modal
        title="Новый профиль сопоставления"
        open={profileOpen}
        onCancel={() => setProfileOpen(false)}
        onOk={onCreateProfile}
        okText="Сохранить"
      >
        <Form
          form={profileForm}
          layout="vertical"
          initialValues={{
            source: 'csv',
            mapping_json: '{\n  "Название товара": "name",\n  "Код товара": "vendor_code"\n}',
          }}
        >
          <Form.Item name="name" label="Название профиля" rules={[{ required: true }]}>
            <Input placeholder="Выгрузка 1С — пилот №1" />
          </Form.Item>
          <Form.Item name="source" label="Источник" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'excel', label: 'Excel' },
                { value: 'csv', label: 'CSV' },
                { value: 'onec', label: '1С CSV' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="mapping_json"
            label="Колонка файла → поле НК ЛАБ"
            rules={[{ required: true }]}
            extra="Допустимые поля: name, vendor_code, category_code, gtin, color, size, composition и rd_*"
          >
            <Input.TextArea rows={8} style={{ fontFamily: 'var(--font-mono)' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
