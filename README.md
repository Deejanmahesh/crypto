# Crypto Market Data & Analytics Application

A small full-stack application that ingests cryptocurrency market data, exposes
it through a REST API with analytics, runs a rule-based trading strategy, and
visualises everything in a web dashboard.

Built for the **Python Full-Stack** technical task.

---

## Tech stack

| Layer            | Choice                                                        |
| ---------------- | ------------------------------------------------------------- |
| Backend          | Python 3.12, **FastAPI** (async), **Pydantic v2**             |
| ORM / DB         | **SQLAlchemy 2 (async)** + asyncpg → **PostgreSQL**           |
| Data / analytics | **pandas**, **numpy**                                         |
| Background jobs  | **APScheduler** (in-process interval job)                     |
| Frontend         | **Next.js 14** (App Router, TypeScript), Tailwind, Recharts   |
| Data source      | **CoinGecko** public API (no key required)                    |
| Orchestration    | Docker Compose (Postgres + backend + frontend)                |

---

## Quick start (Docker — recommended)

Requires Docker Desktop.

```bash
git clone https://github.com/Deejanmahesh/crypto.git
cd crypto
docker compose up --build
```

Then open:

- **Frontend dashboard** → http://localhost:3000
- **API docs (Swagger)** → http://localhost:8000/docs

On first boot the backend creates its tables, fetches the top-10 assets, and
backfills ~30 days of hourly history from CoinGecko (this runs in the
background, so the API is available immediately and data appears within a
minute or two). A scheduled job then refreshes prices every 10 minutes.

To stop and wipe the database volume:

```bash
docker compose down -v
```

---

## Running the backend locally (without Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

cp .env.example .env              # then edit DATABASE_URL if needed
uvicorn app.main:app --reload
```

The default `.env` points at the Docker Postgres on `localhost:5432`. For a
**zero-setup** run you can switch to SQLite by editing `.env`:

```
DATABASE_URL=sqlite+aiosqlite:///./crypto.db
```

### Running the frontend locally

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### Running the tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

---

## API reference

| Method | Endpoint                          | Description                                        |
| ------ | --------------------------------- | -------------------------------------------------- |
| GET    | `/markets`                        | Tracked assets + latest price/volume               |
| GET    | `/prices?symbol=BTC`              | Latest price/volume for one symbol                 |
| GET    | `/history?symbol=BTC&limit=100`   | Historical snapshots (oldest → newest)             |
| GET    | `/analytics?window=24`            | Price/volume % change, momentum and ranking        |
| GET    | `/strategy/list`                  | Registered strategy names                          |
| POST   | `/strategy/run`                   | Run a strategy, persist BUY/SELL/HOLD signals      |
| GET    | `/strategy/results?symbol=BTC`    | Most recent persisted signals                      |
| POST   | `/ingest?with_history=true`       | Manually trigger a data refresh                    |
| GET    | `/health`                         | Liveness probe                                     |

Example strategy run:

```bash
curl -X POST http://localhost:8000/strategy/run \
  -H "Content-Type: application/json" \
  -d '{"strategy":"ma_crossover","params":{"short_window":7,"long_window":21,"mode":"state"}}'
```

---

## Architecture overview

```
                  ┌─────────────────────────────────────────────┐
   CoinGecko ───▶ │ ingestion.py        (httpx client)           │
   public API     │   • ingest_markets  → assets + snapshot      │
                  │   • backfill_history→ historical snapshots    │
                  └───────────────┬─────────────────────────────┘
                                  │ writes
                                  ▼
                          ┌───────────────┐      scheduler.py
                          │  PostgreSQL    │◀──── APScheduler (every 10 min)
                          │  assets        │
                          │  price_snapshots│
                          │  strategy_results│
                          └───────┬────────┘
                                  │ reads
        ┌─────────────────────────┼──────────────────────────┐
        ▼                         ▼                           ▼
  analytics/compute.py      strategy/ (pluggable)        routers/ (FastAPI)
  pandas + numpy            base + registry              markets / analytics / strategy
        └─────────────────────────┴──────────────────────────┘
                                  │  REST (JSON, CORS)
                                  ▼
                       Next.js dashboard (Recharts)
```

**Backend layout** (`backend/app/`):

- `config.py` — env-driven settings (`pydantic-settings`).
- `db.py` — async engine, session factory, table creation.
- `models.py` — `Asset`, `PriceSnapshot`, `StrategyResult`.
- `schemas.py` — Pydantic request/response models.
- `coingecko.py` — async CoinGecko client.
- `ingestion.py` — fetch + idempotent persistence.
- `scheduler.py` — APScheduler background refresh.
- `crud.py` — shared query helpers.
- `analytics/compute.py` — pure pandas/numpy functions (easy to test).
- `strategy/` — `base.Strategy` interface + `registry` + `ma_crossover`.
- `strategy_service.py` — loads history, runs a strategy, persists results.
- `routers/` — `markets`, `analytics`, `strategy`.
- `main.py` — app wiring, startup ingestion, lifespan.

The analytics and strategy code is deliberately decoupled from the database:
the functions take plain sequences, and the service/router layers handle I/O.
This keeps the core logic isolated, extensible and unit-testable.

---

## Strategy explanation

**Moving-average crossover** (`ma_crossover`).

It compares a short-window simple moving average (SMA) against a long-window
SMA of the price series and emits **BUY / SELL / HOLD**.

Two modes (selectable in the UI or via `params.mode`):

- **`state`** (default): `BUY` while the short SMA is above the long SMA,
  `SELL` while below, `HOLD` when they're within a tolerance band. Produces an
  actionable signal on every run — good for a live dashboard.
- **`crossover`**: only emits `BUY`/`SELL` on the bar where the lines actually
  cross (golden / death cross); `HOLD` otherwise. Lower-frequency, more
  conservative.

Parameters: `short_window` (default 7), `long_window` (default 21), `mode`,
`tolerance`. Each result stores the computed MAs, spread and latest price for
transparency.

**Extending it:** add a new file under `app/strategy/`, subclass `Strategy`,
implement `run(prices, params)`, and decorate it with `@register`. It becomes
available at `/strategy/list` and runnable via `/strategy/run` with no other
changes.

---

## Analytics

For each asset, over a configurable window (number of recent snapshots):

- **Price % change** — change between the value `window` points ago and the latest.
- **Volume % change** — same calculation on volume.
- **Momentum** — slope of a linear fit over the window, normalised by mean
  price (positive = uptrend, negative = downtrend).
- **Ranking** — assets ranked by price change (rank 1 = best performer).

---

## Assumptions & limitations

- **Top 10 by market cap** are tracked (configurable via `TOP_N_ASSETS`).
- History is **backfilled from CoinGecko** on startup so analytics/strategy have
  data immediately; CoinGecko returns hourly granularity for a 30-day range.
- The CoinGecko **free tier is rate-limited** (~5–15 calls/min). Backfill sleeps
  between coin calls; an optional Demo API key (`COINGECKO_API_KEY`) raises the
  limit.
- Writes are **idempotent** via a unique `(asset_id, timestamp)` constraint, so
  restarts/re-ingests never duplicate rows.
- The strategy is **educational**, not financial advice — no fees, slippage,
  position sizing or backtest P&L.
- Auth, pagination and migrations (Alembic) are out of scope for this task;
  tables are created on startup via `create_all`.

---

## Possible improvements

- Add WebSocket / Binance live streaming for sub-minute updates.
- Persist a full backtest (equity curve, win rate) alongside the latest signal.
- Add Alembic migrations and seed/fixture data.
- More indicators (RSI, MACD, Bollinger) and a strategy-comparison view.
- Caching layer (Redis) and a dedicated Celery/RQ worker for heavier jobs.
- Auth + per-user watchlists; pagination on history endpoints.
- E2E tests (Playwright) and API integration tests against a test DB.
