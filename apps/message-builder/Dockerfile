# Heyaaashu Visual Content Studio — Production Multi-Stage Dockerfile

# Stage 1: Build Frontend Assets
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and scripts
COPY . .

# Build production bundle
ENV NODE_ENV=production
RUN npm run build

# Stage 2: Production Nginx Server
FROM nginx:alpine

# Copy compiled assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
