import time
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================================
# KONFIGURATION
# ==========================================

# 1. InfluxDB Setup
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "ePSlqhv-o245_IAGgSkAFL0EK5Bis9kGJ4zYtc9E2xJ2lK5J30pKEy849AnVexQcpwxglKGtC8qNZa6Aa_B9RA=="
INFLUX_ORG = "pi"
INFLUX_BUCKET = "sensor"

# 2. API Setup (mit Fallback-Liste)
# Das Skript probiert diese URLs von oben nach unten durch.
API_URLS = [
    "http://172.30.7.11:8000/sensor-data",  # Primäre IP
    "http://172.16.7.11:8000/sensor-data"  # Fallback IP
]

# ==========================================
# PROGRAMM-LOGIK
# ==========================================

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Starte Daten-Logger mit Fallback-Funktion. Drücke STRG+C zum Beenden.")

while True:
    try:
        data = None

        # 1. APIs nacheinander abfragen
        for url in API_URLS:
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()

                # Wenn wir hier ankommen, hat der Abruf geklappt!
                # 'break' beendet die for-Schleife, der Fallback wird ignoriert.
                break

            except requests.exceptions.RequestException:
                # Zeigt eine Warnung, probiert aber sofort die nächste URL in der Liste
                print(f"[{time.strftime('%H:%M:%S')}] Warnung: API {url} nicht erreichbar. Versuche nächste...")

        # 2. Wenn mindestens eine API geantwortet hat (data ist nicht leer)
        if data:
            point = Point("raumklima") \
                .tag("sensor_id", data["sensor_id"]) \
                .tag("name", data["name"]) \
                .tag("location", data["location"]) \
                .field("temperature", float(data["temperature"])) \
                .field("relay", data["relay"]) \
                .field("drehzahl_prozent", int(data["drehzahl_prozent"]))

            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print(f"[{data['timestamp']}] Gespeichert: {data['temperature']}°C, Relais: {data['relay']}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Fehler: Keine der konfigurierten APIs konnte erreicht werden!")

    except Exception as e:
        print(f"Allgemeiner Fehler: {e}")

    # 3. Eine Sekunde warten
    time.sleep(1)