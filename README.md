# DocLite — Backend (FastAPI)

The Python/FastAPI backend for **DocLite**, a lightweight collaborative document
editor. This repo is deployed standalone on **Northflank** (Docker); the React
frontend lives in a separate repo and is deployed on **Vercel**.

- Frontend repo: https://github.com/satwik-gupta/doclite-ui
- Architecture, role model, and design notes: see `ARCHITECTURE.md`.

## Tech
FastAPI · SQLAlchemy 2 · Pydantic v2 · SQLite · JWT (python-jose + passlib) ·
Starlette WebSockets · python-docx / markdown (import) · markdownify / reportlab
(export) · pytest.

## API surface (all under `/api`, plus `/ws/documents/{id}`)
Auth (`/api/auth/login`, `/api/auth/me`), documents CRUD, import, versions, export
(`/md`, `/pdf`), comments, suggestions, sharing, users search, health
(`/api/health`). Interactive docs at `/docs`.

---

## Run locally

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   |   *nix: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/api/health
```

Tables are created and demo users seeded automatically on startup.

## Tests

```bash
pip install -r requirements.txt
pytest            # 23 tests
```

## Run with Docker locally

```bash
docker build -t doclite-backend .
docker run -p 8000:8000 -e DOCLITE_SECRET_KEY=dev doclite-backend
```

---

## Deploy on Northflank

1. **Create the service**
   - Northflank → **Create new → Service → Deployment** (or *Combined service* to
     build from this repo).
   - **Source:** connect GitHub and pick `satwik-gupta/doclite-backend`, branch `main`.
   - **Build:** *Dockerfile*, path `/Dockerfile` (repo root). No build args needed.
2. **Networking / port**
   - Add a **public port `8000`**, protocol **HTTP**, and enable the public DNS.
     Northflank gives you a URL like `https://<service>--<project>.code.run`.
   - Health check path: `/api/health`.
3. **Environment variables** (Service → *Environment*)
   | Key | Value |
   |-----|-------|
   | `DOCLITE_SECRET_KEY` | a long random string |
   | `DOCLITE_SEED_ON_STARTUP` | `true` |
   | `DOCLITE_CORS_ORIGINS` | `https://doclite-ui.vercel.app` (your Vercel URL; optional — regex below already covers `*.vercel.app`) |
   | `DOCLITE_CORS_ORIGIN_REGEX` | `https://([a-z0-9-]+\.)*vercel\.app` (default; leave as-is) |
   | `DOCLITE_DATABASE_URL` | `sqlite:////data/doclite.db` (default in the image) |
4. **Persistence (recommended)**
   - Attach a **persistent volume** mounted at **`/data`** so documents survive
     redeploys. Without it the app still works, but data resets on each deploy and
     the demo users are re-seeded.
5. **Deploy** and wait for the health check to go green. Verify:
   ```bash
   curl https://<your-northflank-url>/api/health     # {"status":"ok","app":"DocLite"}
   ```

> **Note on WebSockets:** the public URL is HTTPS, so the frontend connects to
> `wss://<your-northflank-url>/ws/documents/{id}`. Northflank's HTTP port supports
> WebSocket upgrades automatically.

## Seeded demo accounts
All share the password **`password123`** (login by username or email):
`alice` (owner of the sample doc), `bob` (editor), `carol` (commenter),
`dave` (viewer).
