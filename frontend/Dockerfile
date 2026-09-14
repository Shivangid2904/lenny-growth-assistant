# Stage 1: Build the Vite React application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for better layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Pass build-time environment variables
# Note: Vite bakes VITE_* variables into the JS bundle at build time.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Copy frontend source code
COPY . .

# Run production build
RUN npm run build

# Stage 2: Serve using high-performance Nginx reverse proxy
FROM nginx:alpine

# Replace default Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built production assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Container healthcheck
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
