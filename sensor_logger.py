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
API_URLS = [
    "http://172.30.7.11:8000/sensor-data",  # Primäre IP
    "http://172.16.7.11:8000/sensor-data"   # Fallback IP
]

# 3. Discord Alarm Setup
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1514229720902799511/n-SfQW_Zrd1Eey6dI6Qi1FT-Rw0WbMBJC6rcCnATEorSFjyT1Db1Mc9WDsvlo2_1a4VZ"
ALARM_TEMP = 30.0

# Dein gewünschter Giphy-Link
ALARM_GIF = "https://images-ext-1.discordapp.net/external/oUjqRSNYdVu9QUgN1n_Yayau0EbbrelvHooKDXXIwuY/https/media0.giphy.com/media/v1.Y2lkPTczYjhmN2IxMGUxamY3M2Q1aWJucGoyZHVwMXJ1Y2M5dWdtYmt3ZXAxd3d6MzM1biZlcD12MV9naWZzX2dpZklkJmN0PWc/xT0Gqz4x4eLd5gDtaU/giphy.mp4"

# ==========================================
# PROGRAMM-LOGIK
# ==========================================

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("Starte Daten-Logger mit Discord-Alarm & GIF. Drücke STRG+C zum Beenden.")

# Verhindert, dass Discord jede Sekunde zugespammt wird
alarm_aktiv = False

while True:
    try:
        data = None

        # 1. APIs nacheinander abfragen
        for url in API_URLS:
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.RequestException:
                print(f"[{time.strftime('%H:%M:%S')}] Warnung: API {url} nicht erreichbar. Versuche nächste...")

        # 2. Wenn mindestens eine API geantwortet hat
        if data:
            aktuelle_temp = float(data["temperature"])

            # --------------------------------------------------
            # ALARM LOGIK (Discord mit GIF)
            # --------------------------------------------------
            if aktuelle_temp >= ALARM_TEMP and not alarm_aktiv:
                # Payload für Discord zusammenbauen (inklusive GIF-Link)
                payload = {
                    "content": (
                        f"🚨 **ALARM!** Die Temperatur im **{data['location']}** "
                        f"(Sensor: {data['name']}) ist kritisch!\n"
                        f"**Aktuell: {aktuelle_temp}°C**\n{ALARM_GIF}"
                    )
                }

                try:
                    requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
                    print(f"[{data['timestamp']}] 🚨 DISCORD ALARM MIT GIF GESENDET! Temperatur: {aktuelle_temp}°C")
                    alarm_aktiv = True
                except Exception as e:
                    print(f"Fehler beim Senden an Discord: {e}")

            elif aktuelle_temp < (ALARM_TEMP - 1.0) and alarm_aktiv:
                entwarnung_payload = {
                    "content": f"✅ **Entwarnung:** Die Temperatur im {data['location']} hat sich normalisiert ({aktuelle_temp}°C)."
                }
                try:
                    requests.post(DISCORD_WEBHOOK_URL, json=entwarnung_payload, timeout=5)
                except:
                    pass

                print(f"[{time.strftime('%H:%M:%S')}] ✅ Temperatur hat sich normalisiert. Alarm wieder scharf.")
                alarm_aktiv = False
            # --------------------------------------------------

            # Datenpunkt für InfluxDB zusammenbauen
            point = Point("raumklima") \
                .tag("sensor_id", data["sensor_id"]) \
                .tag("name", data["name"]) \
                .tag("location", data["location"]) \
                .field("temperature", aktuelle_temp) \
                .field("relay", data["relay"]) \
                .field("drehzahl", float(data["drehzahl_prozent"]))

            # In die Datenbank schreiben
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print(f"[{data['timestamp']}] Gespeichert: {aktuelle_temp}°C, Drehzahl: {data['drehzahl_prozent']}%, Relais: {data['relay']}")

        else:
            print(f"[{time.strftime('%H:%M:%S')}] Fehler: Keine der konfigurierten APIs konnte erreicht werden!")

    except Exception as e:
        print(f"Allgemeiner Fehler: {e}")

    # 3. Eine Sekunde warten
    time.sleep(1)