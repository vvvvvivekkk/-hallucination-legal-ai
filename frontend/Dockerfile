# syntax=docker/dockerfile:1
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build

FROM nginx:1.27-alpine AS runner
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/.next/standalone ./
COPY nginx.conf /etc/nginx/conf.d/default.conf
ENV HOSTNAME=0.0.0.0
ENV PORT=3001
EXPOSE 3000
CMD ["sh", "-c", "node server.js & exec nginx -g 'daemon off;'"]
