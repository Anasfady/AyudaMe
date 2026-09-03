from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="AyudaMe")


class NoCacheStaticFiles(StaticFiles):
    """Serve static files without browser caching.

    The frontend is plain ES modules loaded straight from disk, so a cached
    copy in the browser silently keeps running old code after a deploy.
    """

    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


app.mount(
    "/frontend", NoCacheStaticFiles(directory=BASE_DIR / "frontend"), name="frontend"
)
app.mount("/data", NoCacheStaticFiles(directory=BASE_DIR / "data"), name="data")

@app.get("/")
def root():
    return RedirectResponse(url="/frontend/pages/mapa.html")

@app.get("/health")
def health():
    return {"status": "ok"}