import { Alert, Collapse, Form, InputNumber } from 'antd'

export interface PilotBaselineValues {
  baseline_time_per_card_minutes?: number | null
  baseline_first_pass_rate?: number | null
  baseline_return_rate?: number | null
  baseline_labor_minutes_per_card?: number | null
  baseline_cost_per_card?: number | null
  operator_hourly_cost?: number | null
}

const fullWidth = { width: '100%' }

export function PilotBaselineFields() {
  return (
    <Collapse
      ghost
      items={[
        {
          key: 'baseline',
          label: 'Исходные показатели «до пилота»',
          children: (
            <>
              <Alert
                type="info"
                showIcon
                title="Заполните известные значения"
                description="Система сопоставит их с фактическими данными выборки. Незаданные показатели можно добавить позже."
                style={{ marginBottom: 16 }}
              />
              <div className="pilot-baseline-form-grid">
                <Form.Item name="baseline_time_per_card_minutes" label="Время на карточку, мин">
                  <InputNumber min={0} precision={1} style={fullWidth} />
                </Form.Item>
                <Form.Item name="baseline_first_pass_rate" label="Первый проход, %">
                  <InputNumber min={0} max={100} precision={1} style={fullWidth} />
                </Form.Item>
                <Form.Item name="baseline_return_rate" label="Возвраты, %">
                  <InputNumber min={0} max={100} precision={1} style={fullWidth} />
                </Form.Item>
                <Form.Item name="baseline_labor_minutes_per_card" label="Трудозатраты, мин/карточку">
                  <InputNumber min={0} precision={1} style={fullWidth} />
                </Form.Item>
                <Form.Item name="baseline_cost_per_card" label="Стоимость карточки, ₽">
                  <InputNumber min={0} precision={2} style={fullWidth} />
                </Form.Item>
                <Form.Item
                  name="operator_hourly_cost"
                  label="Стоимость часа оператора, ₽"
                  extra="Нужна для расчёта фактической стоимости."
                >
                  <InputNumber min={0} precision={2} style={fullWidth} />
                </Form.Item>
              </div>
            </>
          ),
        },
      ]}
    />
  )
}
