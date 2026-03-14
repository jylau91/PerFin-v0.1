# PerFin v0.1 — Implementation Plan

## Overview
Personal finance app that parses Singapore bank/credit card PDF statements,
categorises transactions with Claude AI, and displays a dashboard + analysis.

## Stack
| Layer | Choice | Reason |
|---|---|---|
| Frontend | Next.js 14 (TypeScript) | App Router, RSC, fast DX |
| Backend | FastAPI (Python 3.12) | Async, pairs well with monopoly-core |
| PDF parser | `monopoly-core` PyPI lib | Native support for DBS, OCBC, UOB, Maybank |
| AI categorisation | Claude API (`claude-haiku-4-5`) | Fast & cheap per-transaction, batch mode |
| Database | PostgreSQL + SQLAlchemy (async) | Persistent, relational |
| ORM migrations | Alembic | Schema versioning |
| Charts | Recharts | React-native charting |
| Styling | Tailwind CSS + shadcn/ui | Consistent, accessible UI |
| Containerisation | Docker Compose | One-command local dev |

---

## Project Structure
```
PerFin-v0.1/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, lifespan
│   │   ├── database.py           # Async SQLAlchemy engine + session
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── schemas.py            # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── statements.py     # POST /statements (upload + parse)
│   │   │   ├── transactions.py   # GET/PATCH /transactions
│   │   │   └── analysis.py       # GET /analysis/* (aggregations)
│   │   └── services/
│   │       ├── parser.py         # monopoly-core wrapper
│   │       └── categoriser.py    # Claude API batch categoriser
│   ├── alembic/                  # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx          # Dashboard (charts + KPIs)
│   │   │   ├── upload/page.tsx   # PDF upload flow
│   │   │   └── transactions/page.tsx # Transaction table + filter
│   │   ├── components/
│   │   │   ├── charts/           # SpendingPie, MonthlyBar, TrendLine
│   │   │   ├── ui/               # shadcn primitives
│   │   │   └── TransactionTable.tsx
│   │   └── lib/
│   │       └── api.ts            # Typed API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml            # postgres + backend + frontend
└── README.md
```

---

## Database Schema
```sql
-- statements: one row per uploaded PDF
statements (id, bank, account_type, period_start, period_end,
            filename, uploaded_at)

-- transactions: parsed rows from statements
transactions (id, statement_id FK, date, description, amount,
              balance, polarity, category, raw_category, reviewed)

-- categories: canonical list of spending categories
categories (id, name, colour, icon)
```

---

## API Endpoints
| Method | Path | Description |
|---|---|---|
| POST | `/statements` | Upload PDF → parse → AI-categorise → persist |
| GET | `/statements` | List all uploaded statements |
| DELETE | `/statements/{id}` | Remove statement + its transactions |
| GET | `/transactions` | List transactions (filter by date, bank, category) |
| PATCH | `/transactions/{id}` | Override category manually |
| GET | `/analysis/summary` | Totals by category for a date range |
| GET | `/analysis/monthly` | Month-by-month spend breakdown |
| GET | `/analysis/top-merchants` | Top N merchants by spend |

---

## Key Implementation Details

### PDF Parsing (`parser.py`)
- Accept uploaded PDF bytes, write to temp file
- Call `monopoly-core` `Pipeline` to extract transactions
- Return list of `RawTransaction` dicts (date, description, amount, balance, polarity)
- Auto-detect bank (DBS/POSB, OCBC, UOB, Maybank) via monopoly's `BankDetector`

### AI Categorisation (`categoriser.py`)
- Batch all new transaction descriptions (≤100 per request) into a single Claude API call
- System prompt defines categories: Food & Drink, Transport, Shopping, Groceries,
  Healthcare, Entertainment, Bills & Utilities, Travel, Education, Income, Other
- Model: `claude-haiku-4-5-20251001` (fast, low-cost for classification)
- Parse structured JSON response `[{"description": ..., "category": ...}]`
- Store both `raw_category` (AI output) and `category` (user-overridable)

### Dashboard (Next.js)
- **KPI cards**: Total spend this month, largest category, number of transactions
- **Spending by category**: Donut chart (Recharts)
- **Monthly trend**: Bar chart (last 6 months)
- **Recent transactions**: Last 10 rows with category badge
- Date range picker to filter all views

### Upload Flow
1. User drags/drops or selects PDF(s)
2. Frontend POSTs to `/statements` with multipart form
3. Backend parses → categorises → returns summary
4. User redirected to dashboard with new data visible

---

## Implementation Steps (in order)

1. **Repo scaffolding** — docker-compose, .env.example, .gitignore
2. **Backend foundation** — FastAPI app, DB models, Alembic init
3. **Parser service** — monopoly-core integration + tests
4. **Categoriser service** — Claude API batching
5. **API routers** — statements, transactions, analysis
6. **Frontend scaffold** — Next.js app, Tailwind, shadcn/ui
7. **Upload page** — drag-and-drop PDF upload
8. **Dashboard** — KPI cards + charts wired to API
9. **Transactions page** — table with filters + category override
10. **Docker Compose** — tie everything together
11. **README** — setup instructions
