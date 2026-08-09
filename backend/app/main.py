from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.study_plan import router as study_plan_router
from backend.app.api.upload import router as upload_router
from backend.config import settings

app = FastAPI(
    title="AI Study Companion",
    version="1.0.0",
)

# Dev-friendly CORS: the frontend (files/*.html) is opened as static files /
# served from a different origin than the FastAPI backend. Origins are
# configurable via CORS_ORIGINS in .env; do not widen this to "*" in
# production without documenting why.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(study_plan_router)


@app.get("/")
def home():
    return {"message": "AI Study Companion Backend Running!"}
