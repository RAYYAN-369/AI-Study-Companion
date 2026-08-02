from fastapi import APIRouter, UploadFile, File
from app.services.parser import extract_text
import os

router = APIRouter()

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = extract_text(file_path)

    return {
        "filename": file.filename,
        "characters": len(text),
        "text": text
    }