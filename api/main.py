import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

app = FastAPI()

DATA_FILE = Path("/data/sensor_data.json")

@app.get("/sensor-data")
def sensor_data():
    print("🔍 /sensor-data wurde aufgerufen")

    print(f"📂 Prüfe Datei: {DATA_FILE}")

    if not DATA_FILE.exists():
        print("❌ Datei nicht gefunden!")
        raise HTTPException(status_code=404, detail="JSON-Datei nicht gefunden")

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        print(f"📊 Datensätze geladen: {len(data)}")

        if not data:
            print("⚠️ Datei ist leer")
            raise HTTPException(status_code=404, detail="Keine Daten vorhanden")

        latest = data[-1]

        print(f"✅ Letzter Eintrag: {latest}")

        return {
            "status": "ok",
            "count": len(data),
            "latest": latest
        }

    except json.JSONDecodeError as e:
        print(f"💥 JSON Fehler: {e}")
        raise HTTPException(status_code=500, detail="Ungültige JSON-Datei")

    except Exception as e:
        print(f"💥 Unerwarteter Fehler: {e}")
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