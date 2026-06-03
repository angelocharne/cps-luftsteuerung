import csv
from pathlib import Path
from fastapi import FastAPI, HTTPException

app = FastAPI()

# Pfad auf die neue CSV-Datei ändern
DATA_FILE = Path("/app/data/sensor_data.csv")

tags_metadata = [
    {
        "name": "test",
        "description": "testing api point",
    },
    {
        "name": "items",
        "description": "Manage items. So _fancy_ they have their own docs.",
        "externalDocs": {
            "description": "Items external docs",
            "url": "https://fastapi.tiangolo.com/",
        },
    },
]

@app.get("/sensor-data")
def sensor_data():
    print("DEBUG: Route aufgerufen")
    print("DEBUG: Pfad =", DATA_FILE)

    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV-Datei nicht gefunden")

    try:
        # CSV-Datei einlesen
        with open(DATA_FILE, mode="r", encoding="utf-8") as f:
            # csv.DictReader nutzt automatisch die erste Zeile der CSV als Schlüssel (Keys)
            reader = csv.DictReader(f)

            # Wandelt alle Zeilen in eine Liste von Dictionaries um
            data = list(reader)

        # Gibst du eine Liste von dicts zurück, macht FastAPI automatisch JSON daraus
        # Falls in der CSV nur eine einzelne Zeile (ein Sensorwert) steht und dein
        # Logger exakt ein Objekt erwartet, nutze stattdessen: return data[0]
        return data

    except Exception as e:
        print("💥 FEHLER:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api-test", tags=["test"])
def home():
    return {"status": "API läuft"}

@app.get("/debug/files")
def debug_files():
    import os
    return os.listdir("/app/data")

@app.get("/health")
def health():
    return {"ok": True}