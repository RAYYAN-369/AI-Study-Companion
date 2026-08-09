# Setup Guide

This guide covers three things: getting your API keys, running the backend
directly with Python, and (optionally) running Qdrant locally with Docker
instead of using Qdrant Cloud.

---

## 1. Get your API keys

### Groq API key
1. Go to **console.groq.com** and sign up / log in.
2. Open **API Keys** → **Create API Key**.
3. Copy it — you won't be able to see it again after closing the dialog.

### Qdrant — pick ONE of these two options

**Option A — Qdrant Cloud (no Docker, easiest)**
1. Go to **cloud.qdrant.io** and sign up (email, Google, or GitHub).
2. Click **Create Free Cluster**, pick a name and region.
3. Copy the **API key** shown right after creation — it's only shown once.
4. On the cluster page, copy the **Cluster URL** too.
5. Free clusters auto-suspend after a week of inactivity and are deleted after
   four weeks — reopen the cluster page occasionally if you're not using it
   daily, or reactivate it before a demo.

**Option B — Local Qdrant via Docker** (see section 3 below if you've never
used Docker). No API key needed for local Qdrant by default.

---

## 2. Configure and run the backend

```bash
cd AI-Study-Companion
pip install -r backend/requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
GROQ_API_KEY=your_groq_key

# If using Qdrant Cloud (Option A):
QDRANT_URL=https://xyz-example.cloud-region.cloud-provider.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_key

# If using local Docker Qdrant (Option B) instead, use this and leave the key blank:
# QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=
```

Start the backend:

```bash
uvicorn backend.app.main:app --reload
```

Confirm it's up:

```bash
curl http://localhost:8000/
```

Serve the frontend (separate terminal):

```bash
python -m http.server 5500 --directory files
```

Open `http://localhost:5500/upload.html` in your browser.

---

## 3. Running Qdrant locally with Docker (only needed for Option B)

If you've never used Docker, here's the whole thing from zero.

### What Docker actually is, in one sentence
Docker lets you run a piece of software (like the Qdrant database) in an
isolated "container" on your machine, without installing it directly onto
your OS — you just tell Docker "run this image" and it handles everything.

### Step 1 — Install Docker Desktop
1. Go to **docker.com/products/docker-desktop** and download the installer
   for your OS (Windows / macOS / Linux).
2. Run the installer, accept the defaults, restart your computer if it asks.
3. Open Docker Desktop once — it needs to be running in the background
   whenever you want to use Docker commands. You'll see a whale icon in your
   system tray/menu bar when it's ready.
4. Verify it worked by opening a terminal and running:
   ```bash
   docker --version
   ```
   You should see a version number, not an error.

### Step 2 — Run Qdrant with the provided `docker-compose.yml`
This repo includes a `docker-compose.yml` at the project root that starts a
local Qdrant instance for you — you don't need to write any Docker commands
yourself.

From the project root:

```bash
docker compose up -d
```

What this does:
- `docker compose` reads `docker-compose.yml` in the current folder.
- `up` starts the service(s) defined in it (just Qdrant here).
- `-d` runs it in the background ("detached") so your terminal is free.

Check it's running:

```bash
docker compose ps
```

You should see a `qdrant` container listed as `running`/`healthy`.

Test it directly:

```bash
curl http://localhost:6333/
```

You should get back a small JSON response like
`{"title":"qdrant - vector search engine", ...}`.

### Step 3 — Point your `.env` at it

```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

(Local Docker Qdrant has no API key by default — that's fine for local dev,
never expose this setup to the public internet without adding one.)

### Step 4 — Stopping it later

```bash
docker compose down
```

This stops and removes the container, but your data stays safe because
`docker-compose.yml` uses a named volume (`qdrant_storage`) — starting it
again with `docker compose up -d` will pick up where you left off. If you
ever want to wipe the data and start clean:

```bash
docker compose down -v
```

(the `-v` also removes the volume).

### Common issues

| Problem | Fix |
|---|---|
| `docker: command not found` | Docker Desktop isn't installed or isn't on your PATH — reinstall and restart your terminal. |
| `Cannot connect to the Docker daemon` | Docker Desktop isn't running — open the app first. |
| `port 6333 already in use` | Something else (maybe an earlier Qdrant) is already using that port — run `docker compose down` first, or stop the other process. |
| Backend can't reach Qdrant | Make sure `docker compose ps` shows it running, and that `.env` has `QDRANT_URL=http://localhost:6333` (not `https`, no trailing slash issues). |

---

## 4. Running the tests

```bash
python -m pytest              # unit + endpoint tests — mocked, no credentials or Docker needed
python test_pipeline.py       # real smoke test — needs a working QDRANT_URL and GROQ_API_KEY
```

`test_pipeline.py` writes to `study_companion_test`, a separate Qdrant
collection from the real one, so it's safe to run repeatedly.
