import smbus2
import bme280
import time
import os
import json
import csv
from pathlib import Path
from datetime import datetime

# Pfade (ggf. an deine Docker-Struktur anpassen)
CONTROL_FILE = Path("/app/data/fan_control.json")
DATA_FILE = Path("/app/data/sensor_data.csv")

# BME280 Setup
port = 1
address = 0x77
bus = smbus2.SMBus(port)
calibration_params = bme280.load_calibration_params(bus, address)

print("Fan-Controller gestartet (Auto/Manuell-Modus)...")

while True:
    # 1. Standard-Modus ist 'auto'
    mode = "auto"

    # 2. Wunsch-Modus aus der Steuerdatei auslesen
    if CONTROL_FILE.exists():
        try:
            config = json.loads(CONTROL_FILE.read_text())
            mode = config.get("mode", "auto")
        except Exception as e:
            print("Fehler beim Lesen der Kontroll-Datei:", e)

    # 3. Sensorwerte auslesen
    data = bme280.sample(bus, address, calibration_params)
    temp = data.temperature

    # Standard-Drehzahl (Beispielwert für die CSV)
    drehzahl = 0.0

    # 4. Logik für die 3 Funktionen (auto / manuell an / manuell aus)
    if mode == "on":
        # Funktion: Manuell AN
        relay_status = "AN"
        drehzahl = 100.0
        os.system("gpioset gpiochip0 17=0")
        print(f"[{mode.upper()}] Temp: {temp:.2f}°C | Lüfter erzwungen EIN")

    elif mode == "off":
        # Funktion: Manuell AUS
        relay_status = "AUS"
        drehzahl = 0.0
        os.system("gpioset gpiochip0 17=1")
        print(f"[{mode.upper()}] Temp: {temp:.2f}°C | Lüfter erzwungen AUS")

    else:
        # Funktion: Automatik (temp > 30)
        if temp > 30:
            relay_status = "AN"
            drehzahl = 100.0
            os.system("gpioset gpiochip0 17=0")
        else:
            relay_status = "AUS"
            drehzahl = 0.0
            os.system("gpioset gpiochip0 17=1")
        print(f"[{mode.upper()}] Temp: {temp:.2f}°C | Lüfter-Status: {relay_status}")

    # 5. Daten in die CSV-Datei schreiben (für die Influx/FastAPI-Pipeline)
    try:
        file_exists = DATA_FILE.exists()
        with open(DATA_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["sensor_id", "name", "location", "temperature", "relay", "drehzahl_prozent", "timestamp"])

            writer.writerow([
                "1",
                "BME280",
                "Serverraum",
                f"{temp:.2f}",
                relay_status,
                f"{drehzahl:.1f}",
                datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            ])
    except Exception as e:
        print("Fehler beim Schreiben der CSV:", e)

    time.sleep(2)