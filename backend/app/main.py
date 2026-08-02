from fastapi import FastAPI

app = FastAPI(
    title="AI Study Companion",
    version="1.0.0",
    description="Backend API for AI Study Companion"
)


@app.get("/")
def home():
    return {
        "message": "AI Study Companion Backend Running Successfully!"
    }