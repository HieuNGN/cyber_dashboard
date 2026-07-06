FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user for k3s/security
RUN useradd -m -u 1000 dashboard && \
    mkdir -p /app/data && \
    chown -R dashboard:dashboard /app
USER dashboard

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/dashboard.db
ENV HOST=0.0.0.0
ENV PORT=8080

CMD ["python", "main.py"]
