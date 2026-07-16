# syntax=docker/dockerfile:1
# Сборка фронтенда и отдача статики через nginx (nginx проксирует /api на бэкенд).
FROM node:22-alpine AS build
WORKDIR /app
# Кэш npm через BuildKit — повторные сборки не перекачивают пакеты.
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
