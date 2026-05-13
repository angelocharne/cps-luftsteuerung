import os
import time
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL    = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUX_TOKEN  = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN")
INFLUX_ORG    = os.getenv("DOCKER_INFLUXDB_INIT_ORG")
INFLUX_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET")

print(f"Verbinde mit InfluxDB: {INFLUX_URL}")
print(f"  Org:    {INFLUX_ORG}")
print(f"  Bucket: {INFLUX_BUCKET}")

# Warten bis InfluxDB bereit ist
while True:
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        health = client.health()
        if health.status == "pass":
            print("InfluxDB erreichbar!")
            break
    except Exception as e:
        print(f"InfluxDB noch nicht bereit: {e}")
    time.sleep(3)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api  = client.query_api()

# Testpunkt schreiben
point = Point("verbindungstest").field("status", 1)
write_api.write(bucket=INFLUX_BUCKET, record=point)
print("Testpunkt erfolgreich geschrieben.")

# Testpunkt lesen
query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1m) |> filter(fn: (r) => r._measurement == "verbindungstest")'
result = query_api.query(query)
if result:
    print("Testpunkt erfolgreich gelesen. InfluxDB funktioniert korrekt.")
else:
    print("WARNUNG: Testpunkt konnte nicht gelesen werden.")

print("Setup abgeschlossen. Container laeuft.")
while True:
    time.sleep(60)
