import os
import time
import board
import busio
import adafruit_bme280.basic as adafruit_bme280
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL   = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
INFLUX_ORG   = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
INFLUX_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")
INTERVAL     = int(os.getenv("SENSOR_INTERVAL", "10"))

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Starte Messung...")

while True:
    temperature = sensor.temperature
    humidity    = sensor.humidity
    pressure    = sensor.pressure

    point = (
        Point("umgebung")
        .field("temperatur", temperature)
        .field("luftfeuchtigkeit", humidity)
        .field("luftdruck", pressure)
    )

    write_api.write(bucket=INFLUX_BUCKET, record=point)
    print(f"Temp: {temperature:.1f}°C  Feuchte: {humidity:.1f}%  Druck: {pressure:.1f}hPa")

    time.sleep(INTERVAL)
