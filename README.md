# Fidant Usage Analytics API

Usage analytics backend for Fidant.AI — tracks daily AI assistant turn consumption per user across subscription tiers.

## Repository Structure

| Branch | Contents |
|--------|----------|
| `main` | FastAPI backend + Prisma schema |
| `frontend` | React dashboard (UsageStats component) |

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Prisma Client Python (v0.15), SQLite
- **Frontend**: React 19, Recharts, Axios

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Prisma CLI and frontend)

### Backend Setup

1. Clone the repo and install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Copy the environment file and set your database path:

```bash
cp .env.example .env
```

The default `DATABASE_URL` in `.env.example` points to `./prisma/dev.db` (SQLite). No changes needed for local development.

3. Push the schema to the database and generate the Prisma client:

```bash
# Use the Python CLI — NOT npx prisma (see note below)
python -m prisma db push
```

4. Seed the database with a demo user and sample events:

```bash
python prisma/seed.py
```

This creates a `starter` plan user with `id=1`, matching the `AUTH_TOKEN="1"` hardcoded in the frontend.

5. Start the server:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API is now available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

### Frontend Setup

Switch to the `frontend` branch:

```bash
git checkout frontend
cd frontend  # if running from repo root
npm install
npm start
```

Frontend runs at `http://localhost:3000`.

---

## Running the Full Stack

Once both backend and frontend are running, open `http://localhost:3000` in your browser. The dashboard will load automatically using `Bearer 1` as the demo token.

To test the API directly:

```bash
# Get 7-day stats for user id=1
curl http://localhost:8000/api/usage/stats?days=7 \
  -H "Authorization: Bearer 1"

# Get 30-day stats
curl "http://localhost:8000/api/usage/stats?days=30" \
  -H "Authorization: Bearer 1"

# Trigger a 400 (invalid days param)
curl "http://localhost:8000/api/usage/stats?days=0" \
  -H "Authorization: Bearer 1"

# Trigger a 401 (missing auth)
curl http://localhost:8000/api/usage/stats
```

Or use the interactive Swagger UI at `http://localhost:8000/docs`.

---

## API Reference

### `GET /api/usage/stats?days=7`

Returns usage analytics for the authenticated user.

**Query parameters**

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `days` | integer | `7` | min `1`, max `90` |

**Authentication**

Pass the user ID as a Bearer token (demo mode):

```
Authorization: Bearer 1
```

**Example response**

```json
{
  "plan": "starter",
  "daily_limit": 30,
  "period": { "from": "2026-03-27", "to": "2026-04-02" },
  "days": [
    {
      "date": "2026-04-02",
      "committed": 12,
      "reserved": 2,
      "limit": 30,
      "utilization": 0.4
    }
  ],
  "summary": {
    "total_committed": 87,
    "avg_daily": 12.4,
    "peak_day": { "date": "2026-03-30", "count": 28 },
    "current_streak": 5
  }
}
```

**Error responses**

| Status | Condition |
|--------|-----------|
| `401` | Missing/invalid Authorization header or user not found |
| `400` | `days` parameter out of range (FastAPI validation) |
| `404` | Route not found |

All errors follow the format: `{ "error": "<code>", "message": "<description>" }`

---

## Plan Limits

| Tier | Daily limit |
|------|-------------|
| `starter` | 30 turns |
| `pro` | 100 turns |
| `executive` | 500 turns |

---

## Caching Strategy

The stats endpoint uses a `daily_usage_cache` table to avoid scanning raw events on every request:

- **Past days**: served from cache if the entry was computed within the last 5 minutes; otherwise recomputed from raw events and the cache is upserted.
- **Today**: always computed live since data is still changing.

This means the first request for a date range is slightly slower (raw scan), but subsequent requests for the same past days are fast cache reads.

---

## Prisma CLI Note

This project uses `prisma-client-py` v0.15 (Python) alongside the Prisma JS CLI v7. These two have conflicting schema requirements:

- JS CLI v7 expects `url` to be in `prisma.config.ts`
- Python client v0.15 requires `url` in `schema.prisma`

**Always use the Python CLI for database operations:**

```bash
python -m prisma db push      # apply schema changes
python -m prisma generate     # regenerate the Python client
```

Do not use `npx prisma db push` or `npx prisma generate` — they will fail.

---

## Assumptions

- **Auth is simplified for demo purposes.** The `Authorization: Bearer <user_id>` scheme is intentional for this exercise. A production implementation would use signed JWTs (e.g., via `python-jose`), verify the signature against a secret key, and extract the subject claim.
- **SQLite for local development.** The schema uses SQLite to keep setup friction minimal. The Prisma schema is compatible with PostgreSQL — switching requires only changing the `provider` in `schema.prisma` and updating `DATABASE_URL`.
- **`@db.VarChar` removed.** The original spec included `@db.VarChar` annotations on string fields. SQLite does not support native types, so these were removed. On PostgreSQL they would be added back.
- **Average is computed over the full period.** `avg_daily` divides total committed turns by the number of requested days (including zero-activity days), not just active days. This reflects true usage density.
- **Streak counts from today backwards.** A streak is the number of consecutive days ending today where at least one turn was committed. A day with zero commits breaks the streak.
- **Cache TTL is 5 minutes.** Past-day aggregates are considered fresh for 5 minutes. This is configurable via `CACHE_STALE_MINUTES` in `usage.py`.

---

## What I Would Do Differently With More Time

- **Real JWT authentication** — integrate `python-jose` with RS256 signing, token expiry, and refresh token flow.
- **PostgreSQL in production** — SQLite is fine for local dev but a real deployment would use Postgres with connection pooling (PgBouncer or Prisma Accelerate).
- **Upgrade prisma-client-py** — the Python client v0.15 is significantly behind the JS ecosystem. Evaluating alternatives (SQLAlchemy + Alembic, or waiting for official Prisma Python support in v7) would be a priority.
- **Background cache warming** — instead of lazy cache population on first request, a background task (APScheduler or Celery) could pre-aggregate yesterday's data at midnight.
- **Pagination on raw event queries** — `find_many` without a limit is fine for the current scale but would need cursor-based pagination for users with large event histories.
- **Tests** — unit tests for `_compute_day` and `_get_day_cached` with mocked Prisma, and integration tests against a test SQLite database.
- **Environment-based CORS** — the allowed origin is hardcoded to `localhost:3000`. In production this should come from an environment variable.
