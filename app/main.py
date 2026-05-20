import os
import time
import json
import board
import busio
import adafruit_bme280.basic as adafruit_bme280
from datetime import datetime, timedelta

SENSOR_ID       = os.getenv("SENSOR_ID", "1")
SENSOR_NAME     = os.getenv("SENSOR_NAME", "BME280")
SENSOR_LOCATION = os.getenv("SENSOR_LOCATION", "Serverraum")
INTERVAL        = int(os.getenv("SENSOR_INTERVAL", "10"))
DATA_PATH       = os.getenv("DATA_PATH", "/app/data/sensor_data.json")

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)

print(f"Sensor '{SENSOR_NAME}' gestartet.")

while True:
    # Vorhandene Daten laden
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            historie = json.load(f)
    else:
        historie = []

    # Neuen Messwert hinzufügen
    jetzt = datetime.now()
    eintrag = {
        "sensor_id": SENSOR_ID,
        "name": SENSOR_NAME,
        "location": SENSOR_LOCATION,
        "temperature": round(sensor.temperature, 2),
        "timestamp": jetzt.strftime("%Y-%m-%dT%H:%M:%S")
    }
    historie.append(eintrag)

    # Einträge älter als 24h löschen
    grenze = jetzt - timedelta(hours=24)
    historie = [
        e for e in historie
        if datetime.strptime(e["timestamp"], "%Y-%m-%dT%H:%M:%S") > grenze
    ]

    # Zurückschreiben
    with open(DATA_PATH, "w") as f:
        json.dump(historie, f, indent=2)

    print(f"{SENSOR_NAME} @ {SENSOR_LOCATION}: {eintrag['temperature']}°C")
    time.sleep(INTERVAL)