import csv
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

DATA_FILE    = Path("/app/data/sensor_data.csv")
CONTROL_FILE = Path("/app/data/control.json")

# ==========================================
# REINE DATEN-ROUTEN
# ==========================================
@app.get("/sensor-data")
def sensor_data_json():
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV-Datei nicht gefunden")
    try:
        with open(DATA_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data = list(reader)
        return data[-1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensor-data/csv", response_class=FileResponse)
def sensor_data_csv():
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="CSV-Datei nicht gefunden")
    return FileResponse(path=DATA_FILE, media_type="text/csv", filename="sensor_data.csv")

# ==========================================
# VEREINHEITLICHTE LÜFTER-STEUERUNG
# ==========================================
@app.get("/fanStart")
@app.post("/fan/override/on")
def fan_start():
    CONTROL_FILE.write_text(json.dumps({"mode": "on"}))
    return {"status": "success", "mode": "on", "message": "Lüfter manuell gestartet"}

@app.get("/fanStop")
@app.post("/fan/override/off")
def fan_stop():
    CONTROL_FILE.write_text(json.dumps({"mode": "off"}))
    return {"status": "success", "mode": "off", "message": "Lüfter manuell gestoppt"}

@app.get("/fanAuto")
@app.post("/fan/override/auto")
def fan_auto():
    CONTROL_FILE.write_text(json.dumps({"mode": "auto"}))
    return {"status": "success", "mode": "auto", "message": "Automatikmodus aktiviert"}

@app.get("/fanStatus")
@app.get("/fan/override")
def fan_status():
    configured_mode = "auto"
    if CONTROL_FILE.exists():
        try:
            configured_mode = json.loads(CONTROL_FILE.read_text()).get("mode", "auto")
        except:
            pass

    actual_relay_state = "UNKNOWN"
    current_temp = None

    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                data = list(reader)
                if data:
                    actual_relay_state = data[-1].get("relay", "UNKNOWN")
                    current_temp = data[-1].get("temperature")
        except:
            pass

    return {
        "mode": configured_mode,
        "relay_state": actual_relay_state,
        "current_temperature": current_temp
    }