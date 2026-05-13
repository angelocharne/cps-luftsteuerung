import os
import time
import RPi.GPIO as GPIO
import board
import busio
import adafruit_bme280.basic as adafruit_bme280
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from fastapi import FastAPI

SENSOR_ID       = os.getenv("SENSOR_ID", "1")
SENSOR_NAME     = os.getenv("SENSOR_NAME", "BME280")
SENSOR_LOCATION = os.getenv("SENSOR_LOCATION", "Serverraum")
INTERVAL        = int(os.getenv("SENSOR_INTERVAL", "10"))

INFLUX_URL    = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
INFLUX_ORG    = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
INFLUX_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")

GPIO.setmode(GPIO.BCM)

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print(f"Sensor '{SENSOR_NAME}' ({SENSOR_ID}) @ {SENSOR_LOCATION} gestartet.")

# Warten bis InfluxDB bereit ist
while True:
    try:
        health = client.health()
        if health.status == "pass":
            print("InfluxDB bereit.")
            break
    except Exception:
        print("Warte auf InfluxDB...")
    time.sleep(3)

try:
    while True:
        temperature = sensor.temperature

        point = (
            Point("temperature_reading")
            .tag("sensor_id", SENSOR_ID)
            .tag("name", SENSOR_NAME)
            .tag("location", SENSOR_LOCATION)
            .field("temperature", temperature)
        )

        write_api.write(bucket=INFLUX_BUCKET, record=point)
        print(f"{SENSOR_NAME} @ {SENSOR_LOCATION}: {temperature:.2f}°C")

        time.sleep(INTERVAL)
finally:
    GPIO.cleanup()

app = FastAPI()


@app.get("/")
def home():
    return {"message": "FastAPI läuft"}