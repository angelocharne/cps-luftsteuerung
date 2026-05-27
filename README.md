# 🌬️ CPS Luftsteuerung

Automatische Lüftersteuerung für den Raspberry Pi – temperaturbasiert, containerisiert, mit REST-API.

---

## Überblick

Das System liest kontinuierlich die Temperatur (z. B. vom BME280-Sensor) und steuert daraufhin einen Lüfter über **GPIO-Relais** und **Hardware-PWM**. Alle Messwerte werden lokal gespeichert und über eine REST-API bereitgestellt.

```
Temperatur (BME280 / Mock / Datei)
        │
        ▼
  Schwellenwert überschritten?
  ├─ Nein → Relais AUS, PWM 0 %
  └─ Ja   → Relais AN, PWM 30–100 % (proportional)
        │
        ▼
  JSON-Verlauf  →  FastAPI  →  InfluxDB
```

---

## Stack

| Komponente       | Technologie                      |
|------------------|----------------------------------|
| Sensorlogik      | Python (sysfs GPIO + I²C)        |
| REST-API         | FastAPI + Uvicorn                |
| Zeitreihendaten  | InfluxDB 2.7                     |
| Deployment       | Docker Compose                   |
| Hardware         | Raspberry Pi, BME280, PWM-Lüfter |

---

## Schnellstart

### 1 · Raspberry Pi vorbereiten

```bash
ssh <user>@<ip-adresse>
sudo apt update && sudo apt upgrade -y
sudo apt install git docker.io docker-compose-plugin -y
```

### 2 · Repository klonen

```bash
git clone https://github.com/angelocharne/cps-luftsteuerung.git
cd cps-luftsteuerung
```

### 3 · Konfiguration

```bash
cp .env.example .env
# .env nach Bedarf anpassen
```

### 4 · Starten

```bash
sudo docker compose up -d
```

| Dienst    | Adresse                     |
|-----------|-----------------------------|
| REST-API  | `http://<pi-ip>:8000`       |
| InfluxDB  | `http://<pi-ip>:8086`       |

---

## Umgebungsvariablen

| Variable           | Standard                     | Beschreibung                             |
|--------------------|------------------------------|------------------------------------------|
| `SENSOR_NAME`      | `BME280`                     | Anzeigename des Sensors                  |
| `SENSOR_LOCATION`  | `Serverraum`                 | Standort                                 |
| `SENSOR_INTERVAL`  | `10`                         | Messintervall in Sekunden                |
| `TEMP_THRESHOLD`   | `27.0`                       | Schwellenwert in °C (Lüfter ein)         |
| `TEMP_SOURCE`      | `mock`                       | `mock` · `bme280` · `file` · `command`   |
| `TEMP_MOCK_VALUE`  | `28.5`                       | Fester Wert im Mock-Modus                |
| `HARDWARE_ENABLED` | `true`                       | `false` = reiner Software-Modus          |
| `RELAY_PIN`        | `17`                         | BCM-Pin des Relais                       |
| `PWM_PIN`          | `18`                         | BCM-Pin für Hardware-PWM (18 oder 19)    |
| `PWM_FREQ`         | `25000`                      | PWM-Frequenz in Hz                       |
| `DATA_PATH`        | `/app/data/sensor_data.json` | Pfad zur Verlaufsdatei                   |

---

## Lüfterkurve

| Temperatur        | Drehzahl                            |
|-------------------|-------------------------------------|
| < Schwellenwert   | 0 % (aus)                           |
| = Schwellenwert   | 30 %                                |
| 35 °C             | 100 %                               |
| > 35 °C           | 100 %                               |

Zwischen Schwellenwert und 35 °C wird die Drehzahl **linear interpoliert**.

---

## Projektstruktur

```
.
├── app/               # Sensorlogik & Lüftersteuerung
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── api/               # FastAPI REST-Endpunkte
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── data/              # JSON-Verlauf (wird zur Laufzeit erstellt)
├── docker-compose.yaml
└── .env.example
```

---

## Entwicklung ohne Hardware

```bash
# In .env setzen:
HARDWARE_ENABLED=false
TEMP_SOURCE=mock
TEMP_MOCK_VALUE=30.0
```

Dann direkt lokal testen:

```bash
cd app && python main.py
```

---

## Lizenz

Schulprojekt – keine Lizenz.
