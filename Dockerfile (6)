FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "paho-mqtt>=2.0" pillow numpy opencv-python-headless pandas
COPY shared /app/shared
COPY edge /app/edge
COPY data /app/data
ENV CENTRES_FILE=/app/data/centres.json
CMD ["python", "edge/run_fleet.py"]
