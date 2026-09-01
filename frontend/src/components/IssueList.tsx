import { CheckCircleOutlined } from '@ant-design/icons'
import { Alert, Empty, Tag } from 'antd'

import type { Issue } from '../types'

export function IssueList({ issues }: { issues: Issue[] }) {
  if (issues.length === 0) {
    return (
      <Alert
        type="success"
        showIcon
        icon={<CheckCircleOutlined />}
        title="Замечаний нет — карточка готова к публикации."
      />
    )
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {issues.length === 0 && <Empty description="Нет замечаний" />}
      {issues.map((issue, idx) => (
        <div
          key={idx}
          style={{ display: 'flex', alignItems: 'flex-start', gap: 8, paddingBottom: 8, borderBottom: '1px solid #f0f0f0' }}
        >
          <Tag color={issue.severity === 'error' ? 'error' : 'warning'}>
            {issue.severity === 'error' ? 'Ошибка' : 'Предупреждение'}
          </Tag>
          <span style={{ flex: 1 }}>{issue.message}</span>
          <Tag>{issue.code}</Tag>
        </div>
      ))}
    </div>
  )
}
