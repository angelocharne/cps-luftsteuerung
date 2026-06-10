import smbus2
import bme280
import time
import os
import json
import csv
from pathlib import Path
from datetime import datetime

# WICHTIG: Pfade auf dem ECHTEN Pi (wo Docker seine Volumes spiegelt!)
# Passe "/home/ben/cps-luftsteuerung/data" an, falls dein Shared-Ordner anders heißt
CONTROL_FILE = Path("/home/ben/cps-luftsteuerung/data/control.json")
DATA_FILE = Path("/home/ben/cps-luftsteuerung/data/sensor_data.csv")

# Ordner erstellen, falls noch nicht vorhanden
CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)

# BME280 Setup
port = 1
address = 0x77
bus = smbus2.SMBus(port)
calibration_params = bme280.load_calibration_params(bus, address)

print("BME280 Controller läuft und wartet auf API-Befehle...")

while True:
    mode = "auto"

    # 1. Modus aus der geteilten JSON-Datei lesen
    if CONTROL_FILE.exists():
        try:
            config = json.loads(CONTROL_FILE.read_text())
            mode = config.get("mode", "auto")
        except Exception as e:
            print("Fehler beim Lesen der Kontroll-Datei:", e)

    # 2. Sensor auslesen
    data = bme280.sample(bus, address, calibration_params)
    temp = data.temperature
    drehzahl = 0.0

    # 3. Hardware-Entscheidung (Reine GPIO-Macht liegt beim Host-Skript!)
    if mode == "on":
        relay_status = "AN"
        drehzahl = 100.0
        os.system("gpioset gpiochip0 17=0")
    elif mode == "off":
        relay_status = "AUS"
        drehzahl = 0.0
        os.system("gpioset gpiochip0 17=1")
    else:  # auto
        if temp > 30:
            relay_status = "AN"
            drehzahl = 100.0
            os.system("gpioset gpiochip0 17=0")
        else:
            relay_status = "AUS"
            drehzahl = 0.0
            os.system("gpioset gpiochip0 17=1")

    print(f"[{mode.upper()}] Temp: {temp:.2f}°C | Relais: {relay_status}")

    # 4. In CSV schreiben (damit FastAPI & InfluxDB es lesen können)
    try:
        file_exists = DATA_FILE.exists()
        with open(DATA_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["sensor_id", "name", "location", "temperature", "relay", "drehzahl_prozent", "timestamp"])

            writer.writerow([
                "1", "BME280", "Serverraum",
                f"{temp:.2f}", relay_status, f"{drehzahl:.1f}",
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            ])
    except Exception as e:
        print("Fehler beim Schreiben der CSV:", e)

    time.sleep(2)