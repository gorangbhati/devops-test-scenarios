FROM python:3.12-slim
WORKDIR /app
COPY main.py .
RUN useradd -r -u 1001 appuser
USER appuser
EXPOSE 8080
CMD ["python", "main.py"]
