// ============================================================
// AI Study Companion — frontend configuration
// One place to change the backend URL for deployment, instead of
// hard-coding localhost across multiple files.
// ============================================================

const APP_CONFIG = {
  // Change this when deploying the backend somewhere other than local dev.
  API_BASE_URL: "http://localhost:8000",

  // Keep this in sync with backend/config.py's MAX_FILE_SIZE (MAX_FILE_SIZE_MB
  // in .env). The backend is the source of truth; this just lets the
  // frontend reject an oversized file before uploading it.
  MAX_FILE_BYTES: 10 * 1024 * 1024, // 10MB

  ALLOWED_EXTENSIONS: [".pdf", ".txt", ".docx"],
};
