FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 2137

CMD ["python", "app.py", "--mqtt-host", "mosquitto", "--mqtt-port", "1883", "--status-app", "http://statuses:2138"]