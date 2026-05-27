import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

app = FastAPI()

DATA_FILE = Path("/sensor_data.json")


@app.get("/sensor-data")
def sensor_data():
    import os

    path = "/app/data"

    files = os.listdir(path)

    return {
        "files": files,
        "exists": "sensor_data.json" in files
    }

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