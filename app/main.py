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
PWM_PIN         = int(os.getenv("PWM_PIN", "18"))
PWM_FREQ        = int(os.getenv("PWM_FREQ", "25"))

# GPIO einrichten
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(PWM_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.HIGH)  # Relais standardmäßig aus

# PWM einrichten
pwm = GPIO.PWM(PWM_PIN, PWM_FREQ)
pwm.start(0)  # 0% Drehzahl

# Sensor einrichten
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c)

def berechne_drehzahl(temp):
    """Berechnet PWM Duty Cycle basierend auf Temperatur"""
    if temp < TEMP_THRESHOLD:
        return 0
    elif temp >= 35:
        return 100
    else:
        # Linear zwischen 27°C (30%) und 35°C (100%)
        drehzahl = 30 + (temp - TEMP_THRESHOLD) * (70 / (35 - TEMP_THRESHOLD))
        return round(min(drehzahl, 100), 1)

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
        drehzahl = berechne_drehzahl(temperature)

        # Relais und PWM steuern
        if temperature >= TEMP_THRESHOLD:
            GPIO.output(RELAY_PIN, GPIO.LOW)   # Relais AN
            pwm.ChangeDutyCycle(drehzahl)
            print(f"⚠️  {temperature}°C → Lüfter AN @ {drehzahl}%")
        else:
            GPIO.output(RELAY_PIN, GPIO.HIGH)  # Relais AUS
            pwm.ChangeDutyCycle(0)
            print(f"✅  {temperature}°C → Lüfter AUS")

        # Eintrag erstellen
        eintrag = {
            "sensor_id": SENSOR_ID,
            "name": SENSOR_NAME,
            "location": SENSOR_LOCATION,
            "temperature": temperature,
            "relay": "AN" if temperature >= TEMP_THRESHOLD else "AUS",
            "drehzahl_prozent": drehzahl,
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
    pwm.stop()
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    GPIO.cleanup()