from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API läuft"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/temperature")
def health():
    return {"temperature": "20 Grad"}