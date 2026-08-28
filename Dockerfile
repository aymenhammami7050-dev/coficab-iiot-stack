FROM python:3.11-slim

WORKDIR /app

COPY plc_simulator.py .

RUN pip install --no-cache-dir paho-mqtt

CMD ["python", "-u", "plc_simulator.py"]
