FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Run as non-root
RUN useradd -r -u 1001 appuser
USER appuser

CMD ["python", "main.py"]
