from fastapi import APIRouter, UploadFile, File
import os

from app.services.parser import extract_text
from app.services.chunking import chunk_text

router = APIRouter()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract text from the document
    text = extract_text(file_path)

    # Split extracted text into chunks
    chunks = chunk_text(text)

    # Return response
    return {
        "filename": file.filename,
        "characters": len(text),
        "total_chunks": len(chunks),
        "chunks": chunks
    }