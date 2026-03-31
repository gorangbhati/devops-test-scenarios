FROM node:20-slim

WORKDIR /app

# Copy package files and install production dependencies only
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Copy source
COPY src/ ./src/

# Run as non-root
RUN useradd -r -u 1001 appuser
USER appuser

EXPOSE 3000
CMD ["node", "src/server.js"]
