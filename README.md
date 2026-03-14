# PerFin v0.1

Personal finance app that parses Singapore bank PDF statements, categorises
spending with Claude AI, and presents a dashboard + analysis.

## Supported Banks

- DBS / POSB
- OCBC
- UOB
- Maybank

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.12 |
| PDF Parsing | `monopoly-core` |
| AI Categorisation | Claude claude-haiku-4-5 (Anthropic) |
| Database | PostgreSQL (async SQLAlchemy) |
| Dev containers | Docker Compose |

---

## Quick Start (Local Dev with Docker)

### 1. Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)

### 2. Clone & configure

```bash
git clone <repo-url>
cd PerFin-v0.1
cp .env.example .env
```

Edit `.env` and set your **Anthropic API key**:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 3. Start everything

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Local Development (without Docker)

### Backend

**System dependencies** (Ubuntu/Debian):

```bash
sudo apt-get install gcc libpoppler-cpp-dev pkg-config poppler-utils
```

**Python setup:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Run:**

```bash
# Make sure PostgreSQL is running locally (or use Docker just for Postgres):
docker compose up postgres -d

cp ../.env .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp ../.env .env.local   # or set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Production PostgreSQL (Free Tier)

### Option A — Neon (Recommended, no credit card)

1. Sign up at https://neon.tech
2. Create a project → copy the connection string
3. Update `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>.neon.tech/neondb?sslmode=require
   ```

### Option B — Supabase

1. Sign up at https://supabase.com
2. Go to **Settings → Database → Connection string → URI**
3. Replace `postgresql://` with `postgresql+asyncpg://` and add `?sslmode=require`

### Option C — Railway

1. Sign up at https://railway.app
2. Add a PostgreSQL plugin → copy the `DATABASE_URL`
3. Prefix driver: `postgresql+asyncpg://...`

---

## Usage

1. Open http://localhost:3000/upload
2. Drag and drop a PDF statement from DBS/POSB, OCBC, UOB, or Maybank
3. Transactions are parsed and AI-categorised automatically
4. View the **Dashboard** for charts and KPIs
5. Open **Transactions** to review, filter, and override categories

---

## API Reference

Interactive docs at http://localhost:8000/docs

| Endpoint | Description |
|---|---|
| `POST /statements` | Upload PDF, parse, and categorise |
| `GET /statements` | List all uploaded statements |
| `DELETE /statements/{id}` | Delete statement and its transactions |
| `GET /transactions` | Filter transactions by category, date range |
| `PATCH /transactions/{id}` | Override transaction category |
| `GET /analysis/summary` | Totals by category |
| `GET /analysis/monthly` | Month-by-month breakdown |
| `GET /analysis/top-merchants` | Top merchants by spend |

---

## Project Structure

```
PerFin-v0.1/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings (reads .env)
│   │   ├── database.py          # Async SQLAlchemy
│   │   ├── models.py            # ORM models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── statements.py    # Upload + parse
│   │   │   ├── transactions.py  # CRUD
│   │   │   └── analysis.py      # Aggregations
│   │   └── services/
│   │       ├── parser.py        # monopoly-core wrapper
│   │       └── categoriser.py   # Claude AI categoriser
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Dashboard
│   │   ├── upload/page.tsx      # PDF upload
│   │   └── transactions/page.tsx
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   └── charts/
│   │       ├── SpendingDonut.tsx
│   │       └── MonthlyBar.tsx
│   └── lib/api.ts               # Typed API client
├── docker-compose.yml
├── .env.example
└── README.md
```
