import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

app = FastAPI()

DATA_FILE = Path("/app/data/sensor_data.json")

@app.get("/sensor-data")
def sensor_data():
    print("DEBUG: Route aufgerufen")
    print("DEBUG: Pfad =", DATA_FILE)

    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="JSON-Datei nicht gefunden")

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except Exception as e:
        print("💥 FEHLER:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "API läuft"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug/files")
def debug_files():
    import os
    return os.listdir("/app/data")