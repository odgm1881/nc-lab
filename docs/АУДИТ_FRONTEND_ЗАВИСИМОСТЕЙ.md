# Аудит frontend-зависимостей

Дата проверки: 28 июля 2026.

`npm audit` обнаружил две уязвимости высокой серьёзности в ветке React Router 7.
Автоматический `npm audit fix --force` не применялся: он предлагает несовместимые
между собой версии при актуальном наборе advisory.

Принятое решение: временно зафиксирован `react-router-dom@6.30.3`. Используемые
проектом API (`BrowserRouter`, `Routes`, `Route`, `Navigate`, `useNavigate`,
`useParams`) совместимы. После изменения:

- high: 0;
- critical: 0;
- moderate: 2.

Остаточные advisory относятся к open redirect/SSR hydration. Приложение является
клиентским SPA, не использует SSR, actions/loaders и не передаёт пользовательские
URL в `navigate`, поэтому риск принят временно. CI блокирует новые high/critical
уязвимости командой `npm audit --omit=dev --audit-level=high`.

Обновить React Router следует после появления версии без известных high-рисков и
после регрессионной проверки маршрутов авторизации, каталога и карточки.
