import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load service account key when running locally
key_path = Path(__file__).parent.parent / "secrets" / "signal-key.json"
if key_path.exists():
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(key_path))

from routers import dimensions, plan, pos, forecast, exceptions, acquisition, reconciliation

app = FastAPI(title="SIGNAL API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dimensions.router)
app.include_router(plan.router)
app.include_router(pos.router)
app.include_router(forecast.router)
app.include_router(exceptions.router)
app.include_router(acquisition.router)
app.include_router(reconciliation.router)


@app.get("/health")
def health():
    return {"status": "ok", "project": "signal-499604"}
