# syntax=docker/dockerfile:1
# Сборка фронтенда и отдача статики + прокси /api маленьким Node-сервером.
# Оба этапа на node:22-alpine → нужен только один базовый образ (меньше загрузок
# из реестра, устойчивее к сетевым таймаутам).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
COPY --from=build /app/server.mjs ./server.mjs
EXPOSE 80
CMD ["node", "server.mjs"]
