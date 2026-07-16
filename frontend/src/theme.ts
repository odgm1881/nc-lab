// Токены синхронны с src/styles/global.css. Один акцент (teal), единая шкала
// радиусов, системный шрифт, тонированные тени.
// Экспортируется без строгой аннотации ThemeConfig, чтобы не зависеть от точного
// набора component-token ключей конкретной версии Ant Design.
const FONT =
  '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", Arial, system-ui, sans-serif'

export const theme = {
  token: {
    colorPrimary: '#0f766e',
    colorInfo: '#0f766e',
    colorSuccess: '#16a34a',
    colorError: '#e11d48',
    colorWarning: '#d97706',
    colorTextBase: '#0f172a',
    colorBgLayout: '#f5f7f9',
    colorBorderSecondary: '#eef1f5',
    colorBorder: '#e6eaf0',
    borderRadius: 10,
    borderRadiusLG: 14,
    borderRadiusSM: 8,
    fontFamily: FONT,
    fontSize: 14,
    controlHeight: 38,
    lineHeight: 1.6,
    boxShadow: '0 4px 14px -3px rgba(15,23,42,0.10), 0 2px 6px -2px rgba(15,23,42,0.06)',
    boxShadowSecondary: '0 1px 2px rgba(15,23,42,0.06), 0 1px 3px rgba(15,23,42,0.08)',
    wireframe: false,
  },
  components: {
    Button: { fontWeight: 600, controlHeight: 38, controlHeightLG: 44 },
    Card: { borderRadiusLG: 14, paddingLG: 22 },
    Input: { controlHeight: 40 },
    Select: { controlHeight: 40 },
    Table: {
      headerBg: '#fbfcfd',
      headerColor: '#64748b',
      rowHoverBg: '#f6f8fa',
      borderColor: '#eef1f5',
      cellPaddingBlock: 14,
    },
    Menu: {
      darkItemBg: 'transparent',
      darkItemColor: '#93a1b5',
      darkItemHoverBg: 'rgba(255,255,255,0.05)',
      darkItemHoverColor: '#eef2f8',
      darkItemSelectedBg: 'rgba(13,148,136,0.18)',
      darkItemSelectedColor: '#5eead4',
    },
    Segmented: { trackBg: '#eef1f5', itemSelectedBg: '#ffffff' },
    Layout: { bodyBg: '#f5f7f9', headerBg: '#ffffff', siderBg: '#0d1521' },
  },
}
