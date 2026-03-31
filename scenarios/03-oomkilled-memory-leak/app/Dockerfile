FROM golang:1.22-alpine AS builder

WORKDIR /build

COPY go.mod ./
COPY *.go ./

RUN go build -o server .

# ── Final stage ──────────────────────────────────────────────────────────────
FROM alpine:3.20

WORKDIR /app

COPY --from=builder /build/server .

# Run as non-root
RUN adduser -D -u 1001 appuser
USER appuser

EXPOSE 8080
CMD ["/app/server"]
