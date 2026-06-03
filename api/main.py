import csv, json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

DATA_FILE    = Path("/app/data/sensor_data.csv")
CONTROL_FILE = Path("/app/data/control.json")

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

# ==========================================
# ROUTE 1: Gibt die Daten als JSON aus (für dein Logger-Skript)
# ==========================================
@app.get("/sensor-data")
def sensor_data_json():
    print("DEBUG: JSON-Route aufgerufen")

    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV-Datei nicht gefunden")

    try:
        # CSV einlesen und in Dictionary/JSON umwandeln
        with open(DATA_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data = list(reader)

        # Wenn dein Logger nur ein einzelnes Objekt erwartet (wie vorher),
        # data[-1] greift immer zielsicher auf den allerletzten Eintrag der Liste zu!
        return data[-1]

    except Exception as e:
        print("💥 FEHLER:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# ROUTE 2: Gibt die reine CSV-Datei aus (Neuer Endpunkt)
# ==========================================
@app.get("/sensor-data/csv", response_class=FileResponse)
def sensor_data_csv():
    print("DEBUG: CSV-Route aufgerufen")

    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV-Datei nicht gefunden")

    # Gibt die Datei direkt als CSV-Download an den Aufrufer zurück
    return FileResponse(path=DATA_FILE, media_type="text/csv", filename="sensor_data.csv")

@app.get("/fanStart")
def login():
    return {"status": "start"}

@app.get("/fanStop")
def login():
    return {"status": "stop"}

@app.get("/login")
def login():
    return {"user": "admin"; "pw": "12345678"}


# ==========================================
# ROUTE 3: Lüfter manuell steuern (on / off / auto)
# ==========================================
@app.post("/fan/override/{state}")
def fan_override(state: str):
    if state not in ("on", "off", "auto"):
        raise HTTPException(status_code=400, detail="Nur: on, off, auto")
    CONTROL_FILE.write_text(json.dumps({"override": state}))
    return {"override": state}

@app.get("/fan/override")
def fan_override_status():
    if not CONTROL_FILE.exists():
        return {"override": "auto"}
    return json.loads(CONTROL_FILE.read_text())

# ==========================================
# WEITERE DEBUG- UND TEST-ROUTEN
# ==========================================
@app.get("/api-test", tags=["test"])
def home():
    return {"status": "API läuft"}

@app.get("/debug/files", tags=["test"])
def debug_files():
    import os
    return os.listdir("/app/data")

@app.get("/health")
def health():
    return {"ok": True}