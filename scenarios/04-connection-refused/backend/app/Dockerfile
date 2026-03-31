FROM python:3.12-slim
WORKDIR /app
COPY main.py .
RUN useradd -r -u 1001 appuser
USER appuser
CMD ["python", "main.py"]
