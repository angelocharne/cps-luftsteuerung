import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

app = FastAPI()

DATA_FILE = Path("/app/data/sensor_data.json")

@app.get("/sensor-data")
def sensor_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Keine Sensordaten vorhanden"
            )

        # letzten Eintrag zurückgeben
        latest_sensor_data = data[-1]

        return latest_sensor_data

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="JSON-Datei nicht gefunden"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Fehlerhafte JSON-Datei"
        )



@app.get("/")
def home():
    return {"status": "API läuft"}

@app.get("/health")
def health():
    return {"ok": True}