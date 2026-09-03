from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="AyudaMe")

app.mount("/frontend", StaticFiles(directory=BASE_DIR / "frontend"), name="frontend")
app.mount("/data", StaticFiles(directory=BASE_DIR / "data"), name="data")

@app.get("/")
def root():
    return RedirectResponse(url="/frontend/pages/mapa.html")

@app.get("/health")
def health():
    return {"status": "ok"}