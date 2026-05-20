import os
import time
import json
import board
import busio
import RPi.GPIO as GPIO
import adafruit_bme280.basic as adafruit_bme280
from datetime import datetime, timedelta

SENSOR_ID       = os.getenv("SENSOR_ID", "1")
SENSOR_NAME     = os.getenv("SENSOR_NAME", "BME280")
SENSOR_LOCATION = os.getenv("SENSOR_LOCATION", "Serverraum")
INTERVAL        = int(os.getenv("SENSOR_INTERVAL", "10"))
DATA_PATH       = os.getenv("DATA_PATH", "/app/data/sensor_data.json")
TEMP_THRESHOLD  = float(os.getenv("TEMP_THRESHOLD", "27.0"))
RELAY_PIN       = int(os.getenv("RELAY_PIN", "17"))

# GPIO einrichten
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.HIGH)  # Relais standardmäßig aus

# Sensor einrichten
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)

print(f"Sensor '{SENSOR_NAME}' gestartet. Schwellenwert: {TEMP_THRESHOLD}°C")

try:
    while True:
        # Vorhandene Daten laden
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r") as f:
                historie = json.load(f)
        else:
            historie = []

        # Temperatur messen
        jetzt = datetime.now()
        temperature = round(sensor.temperature, 2)

        # Relais steuern
        if temperature >= TEMP_THRESHOLD:
            GPIO.output(RELAY_PIN, GPIO.LOW)   # Relais AN
            relay_status = "AN"
            print(f"⚠️  Temperatur {temperature}°C >= {TEMP_THRESHOLD}°C → Lüfter AN")
        else:
            GPIO.output(RELAY_PIN, GPIO.HIGH)  # Relais AUS
            relay_status = "AUS"
            print(f"✅  Temperatur {temperature}°C < {TEMP_THRESHOLD}°C → Lüfter AUS")

        # Eintrag erstellen
        eintrag = {
            "sensor_id": SENSOR_ID,
            "name": SENSOR_NAME,
            "location": SENSOR_LOCATION,
            "temperature": temperature,
            "relay": relay_status,
            "timestamp": jetzt.strftime("%Y-%m-%dT%H:%M:%S")
        }
        historie.append(eintrag)

        # Einträge älter als 24h löschen
        grenze = jetzt - timedelta(hours=24)
        historie = [
            e for e in historie
            if datetime.strptime(e["timestamp"], "%Y-%m-%dT%H:%M:%S") > grenze
        ]

        # JSON speichern
        with open(DATA_PATH, "w") as f:
            json.dump(historie, f, indent=2)

        time.sleep(INTERVAL)

finally:
    GPIO.output(RELAY_PIN, GPIO.HIGH)  # Relais aus bei Programmende
    GPIO.cleanup()