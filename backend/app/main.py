from fastapi import FastAPI

from app.api.upload import router as upload_router

app = FastAPI(
    title="AI Study Companion",
    version="1.0.0"
)

app.include_router(upload_router)


@app.get("/")
def home():
    return {
        "message": "AI Study Companion Backend Running!"
    }