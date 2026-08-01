# ---------- Stage 1: build the static Vite bundle ----------
# Build context is the PROJECT ROOT (see docker/frontend/docker-compose.yml)
# so this Dockerfile can reach both frontend/ (the app source) and
# docker/frontend/nginx.conf (its own config) in one build context.
FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

ARG VITE_API_URL=http://13.61.196.238:30080/api


RUN npm run build

# ---------- Stage 2: serve the built files with Nginx ----------
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:80/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
