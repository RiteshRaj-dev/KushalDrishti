FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY backend/app /app/app
COPY dashboard /app/dashboard
COPY data /app/data
ENV CENTRES_FILE=/app/data/centres.json DASHBOARD_DIR=/app/dashboard EVIDENCE_DIR=/evidence
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
