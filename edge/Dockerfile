FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# When the container boots, it simulates the national fleet of edge nodes
CMD ["python", "run_fleet.py"]