# Code Analysis — Crypto Market Data & Analytics App

This document is a deep analysis of **both the frontend and backend** code. For
each layer it explains *what it does*, *how it works*, *its strengths*, and
*what needs attention (issues / risks)*.

> **Project in one line:** Fetch top-10 crypto data from CoinGecko → store it in
> Postgres → expose analytics + an MA-crossover trading strategy through a
> FastAPI REST API → visualise it as tables and charts in a Next.js dashboard.

---

## 1. Tech stack summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | FastAPI (async) | 0.115.6 |
| Validation | Pydantic v2 + pydantic-settings | 2.10.4 / 2.7.0 |
| ORM / DB | SQLAlchemy 2 (async) + asyncpg → PostgreSQL | 2.0.36 |
| Dev DB option | aiosqlite (SQLite) | 0.20.0 |
| HTTP client | httpx (async) | 0.28.1 |
| Analytics | pandas + numpy | 2.2.3 / 2.2.1 |
| Background job | APScheduler (in-process) | 3.11.0 |
| Frontend | Next.js 14 (App Router, TS) | 14.2.35 |
| Charts | Recharts | 2.13.3 |
| Styling | Tailwind CSS | 3.4.14 |
| Orchestration | Docker Compose (db + backend + frontend) | — |
| Data source | CoinGecko public API (key optional) | — |

**Key design principle:** the core logic (analytics + strategy) never touches
the DB — it only consumes `list[float]`. All DB reads/writes live in the service
+ router layers. This makes the core trivially unit-testable and easy to extend.

---

## 2. Architecture & data flow

```
                  ┌──────────────────────────────────────────────┐
   CoinGecko ───▶ │ ingestion.py  (httpx client + retry/backoff)  │
   public API     │   • ingest_markets   → assets + live snapshot │
                  │   • backfill_history → ~30 days hourly history│
                  └───────────────┬──────────────────────────────┘
                                  │ writes (idempotent)
                                  ▼
                          ┌────────────────────┐    scheduler.py
                          │   PostgreSQL        │◀── APScheduler (every 10 min)
                          │   • assets          │
                          │   • price_snapshots │
                          │   • strategy_results│
                          └────────┬───────────┘
                                   │ reads (crud.py)
        ┌──────────────────────────┼───────────────────────────┐
        ▼                          ▼                            ▼
  analytics/compute.py      strategy/ (pluggable)         routers/ (FastAPI)
  (pure pandas/numpy)       base + registry + ma_crossover  markets/analytics/strategy
        └──────────────────────────┴───────────────────────────┘
                                   │  REST (JSON, CORS-protected)
                                   ▼
                        Next.js dashboard (tables + Recharts)
                        polls every 30s
```

**Request lifecycle example (`GET /analytics?window=24`):**
1. `routers/analytics.py` → `crud.get_assets()` loads all tracked assets.
2. For each asset, `crud.get_history(symbol, limit=window+1)` reads from the DB.
3. The price/volume lists are passed to `compute_asset_metrics()` (pure function).
4. `rank_assets()` ranks them, then the result is serialised via the Pydantic
   `AnalyticsOut` schema and returned.

---

## 3. Backend deep-dive (file-by-file)

### `app/config.py` — Settings
- Loads config from env / `.env` via `pydantic-settings`.
- Defaults: Postgres URL, CoinGecko base URL, `top_n_assets=10`, `history_days=30`,
  `ingest_interval_minutes=10`, `ingest_on_startup=True`.
- The `cors_origin_list` property splits a comma-separated string into a list.
- `@lru_cache` makes settings a cached singleton — a good pattern.

### `app/db.py` — Async engine
- `create_async_engine` + `async_sessionmaker` (with `expire_on_commit=False`).
- `init_db()` → `Base.metadata.create_all` (creates tables on startup).
- `get_session()` → FastAPI dependency that yields a per-request session.
- ⚠️ **Note:** No migrations (no Alembic). Only `create_all` — schema changes must
  be handled manually. (Fine for a task, but an improvement for production.)

### `app/models.py` — 3 ORM tables
- `Asset` — `coingecko_id` (unique), `symbol`, `name`, `market_cap_rank`.
- `PriceSnapshot` — a **UniqueConstraint** on `(asset_id, timestamp)` → idempotent writes.
  `symbol` is also stored redundantly (denormalised, for faster queries).
- `StrategyResult` — `signal`, `params` (JSON), `details` (JSON), `created_at`.
- Uses modern SQLAlchemy 2 `Mapped[]` typing — clean.
- ✅ Timezone-aware `utcnow()` is a good choice.

### `app/coingecko.py` — API client
- Wraps 2 endpoints with `httpx.AsyncClient`: `/coins/markets`, `/coins/{id}/market_chart`.
- **Retry/backoff** logic: exponential backoff (2s → 4s → 8s…) on 429 / 5xx,
  honouring the `Retry-After` header. Important for the free-tier rate limit.
- ⚠️ **Minor:** A new `AsyncClient` is created on every `_get` call — this misses
  connection pooling. Using a shared client (or `app.state`) would be more efficient.

### `app/ingestion.py` — Fetch + persist
- `ingest_markets()` → upserts top-N assets + writes a current snapshot (timestamp truncated to whole seconds).
- `backfill_history()` → loads ~30 days of hourly history per asset, inserted idempotently.
- **Idempotency strategy:** before inserting, it loads existing timestamps into a set
  via `_existing_timestamps()` and skips duplicates — portable (works on both Postgres
  and SQLite, no dialect-specific upsert).
- Sleeps `asyncio.sleep(2.5)` between coin calls to respect the rate limit.
- ⚠️ **Scaling concern:** `_existing_timestamps` loads **all** of an asset's timestamps
  into memory as a set. With months/years of data this grows large. A time-range filter
  (e.g. `timestamp >= cutoff`) would be better.

### `app/crud.py` — Query helpers
- `get_assets` (ordered by rank, nulls last), `get_asset_by_symbol`, `get_latest_snapshot`,
  `get_history` (fetches the latest N, then reverses to chronological order).
- Clean separation — routers/services all reuse these, so SQL isn't duplicated.

### `app/scheduler.py` — Background refresh
- `AsyncIOScheduler` (UTC) → runs `ingest_markets` every 10 min.
- `start_scheduler` / `stop_scheduler` are called from the lifespan.
- ⚠️ **Single-process only:** in-process scheduler. If the backend is scaled to multiple
  replicas, each replica would ingest separately (duplicate work). Production would need
  Celery/RQ or an external cron + lock.

### `app/analytics/compute.py` — Pure analytics ⭐
- `pct_change(values, window)` — % change between the value `window` points ago and the latest.
  Handles edge cases: insufficient data → None, base==0 → None, window clamping.
- `momentum(values, window)` — linear-fit slope via `np.polyfit`, normalised by the mean
  price and expressed as a %. Positive = uptrend.
- `compute_asset_metrics` — bundles all the metrics together.
- `rank_assets` — sorts by price_change descending, None last.
- ✅ **Best part of the codebase:** purely functional, no I/O — trivial to test.

### `app/strategy/` — Pluggable strategy system ⭐
- `base.py` — `Signal` enum (BUY/SELL/HOLD), `StrategySignal` dataclass,
  abstract `Strategy` (`run()` + `resolve_params()` for merging defaults).
- `registry.py` — the `@register` decorator instantiates the class and stores it in a dict.
  Provides `get_strategy`, `list_strategies`.
- `ma_crossover.py` — short SMA vs long SMA.
  - **`state` mode:** short > long → BUY, short < long → SELL, within tolerance band → HOLD.
  - **`crossover` mode:** BUY/SELL only on the actual cross bar (golden/death cross).
  - Validation: `short_window < long_window` else raises `ValueError`.
  - Insufficient data → HOLD with a reason.
  - `details` includes short_ma, long_ma, spread_pct, latest_price for transparency.
- ✅ **Extensibility:** add a new strategy → new file + subclass + `@register`. It
  automatically appears in `/strategy/list` with no other changes. Clean Open/Closed principle.

### `app/strategy_service.py` — Service layer
- Loads history from the DB → runs the strategy → persists results (commit + refresh).
- `STRATEGY_HISTORY_LIMIT = 500`.
- The "glue" layer connecting pure strategy code to the DB.

### `app/routers/` — REST endpoints
- `markets.py` — `/markets`, `/prices`, `/history`, `/ingest`.
- `analytics.py` — `/analytics` (window param, validated 1–1000).
- `strategy.py` — `/strategy/list`, `/strategy/run`, `/strategy/results`.
- Error handling: unknown symbol/strategy → 404, bad params → 400. Clean HTTP semantics.
- Query params validated with Pydantic `Query(..., ge=, le=)`.

### `app/main.py` — App wiring
- In `lifespan`: `init_db()` → background `_initial_ingest()` (asyncio task, doesn't block
  startup) → `start_scheduler()`.
- CORS middleware pulls origins from settings.
- ⚠️ CORS: `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True` — origin
  is restricted (`localhost:3000`), so it's fine now. But the wildcard methods + credentials
  combo is a bit loose for production. Keep the origin strict.

### `tests/` — Unit tests
- `test_analytics.py` — 11 tests: pct_change, momentum, ranking, edge cases.
- `test_strategy.py` — 8 tests: registry, BUY/SELL/HOLD modes, validation, golden cross.
- ✅ Only pure functions are tested — fast, no DB needed.
- ⚠️ **Gap:** No router / API integration tests, no ingestion tests, no frontend tests.

---

## 4. Frontend deep-dive (file-by-file)

### `app/layout.tsx` — Root layout
- Metadata + global CSS. Simple. Slate-based dark theme.

### `app/page.tsx` — Main dashboard (client component) ⭐
- State: markets, selected symbol, history, analytics, strategyResults, running, error.
- `loadMarkets`, `loadAnalytics`, `loadStrategyResults` — memoised with `useCallback`.
- **Polling:** a 30s `setInterval` refreshes markets + analytics (to reflect scheduled ingests).
- When the selected asset changes, history reloads (separate `useEffect`).
- `runStrategy` → POST + sets the result.
- ✅ Cleanup: the interval is properly cleared with `clearInterval`.
- ⚠️ Error handling is basic (`setError(String(e))`). Each fetch has its own error handling
  and one failure doesn't block another section (good), but the UI only shows a single
  global error bar — not granular.

### `lib/api.ts` — API client
- `API_URL` is env-driven (`NEXT_PUBLIC_API_URL`, default localhost:8000).
- `getJSON` helper — `cache: "no-store"` (always fresh), throws on error.
- `getMarkets`, `getHistory`, `getAnalytics`, `getStrategyResults`, `runStrategy`.
- ✅ Centralised and typed (generics). Clean.

### `lib/types.ts` — TypeScript types
- Interfaces matching the backend Pydantic schemas (Market, Snapshot, History,
  AnalyticsItem, StrategyResult, etc.).
- ⚠️ **Maintenance risk:** maintained manually — if the backend schema changes, these need
  manual sync. (Could use OpenAPI codegen — an improvement.)

### `lib/format.ts` — Formatting helpers
- `fmtUsd` (handles precision for small values), `fmtCompact` (1.2M style),
  `fmtPct` (+/- sign + color), `pctColor` (green/red), `signalColor` (BUY/SELL/HOLD chip).
- ✅ Reusable, presentation logic centralised.

### `components/MarketTable.tsx`
- Asset table, row click → select. Empty state message ("ingestion may still be running").
- Highlights the selected row.

### `components/PriceChart.tsx`
- Recharts: Area chart (price) + Bar chart (volume).
- Custom tick format (M/D), tooltip, gradient fill. Handles empty state.

### `components/AnalyticsTable.tsx`
- Rank, asset, price, price Δ%, volume Δ%, momentum — color-coded.

### `components/StrategyPanel.tsx`
- Inputs: short MA, long MA, mode (state/crossover). Run button (disabled while running).
- Result cards — signal chip + spread% / insufficient-data note.
- ⚠️ **Minor:** uses index in `key={`${r.symbol}-${i}`}` — symbol is unique so
  `key={r.symbol}` would be better. Functionally fine though.
- ⚠️ No client-side validation (short < long) — the backend throws a 400, but there's no
  inline feedback for the user.

---

## 5. Strengths ✅

1. **Clean layered architecture** — config / db / models / crud / service / router are
   separated. Single responsibility is well followed.
2. **Pure core logic** — analytics + strategy are DB-independent → trivially testable.
3. **Pluggable strategy pattern** — registry + decorator, Open/Closed principle.
4. **Idempotent ingestion** — unique constraint + existence check → restart-safe, no
   duplicate rows. DB-portable (no dialect-specific upsert).
5. **Resilient API client** — retry/backoff, honours Retry-After, continues with other
   assets on partial failure.
6. **Non-blocking startup** — initial ingest runs as a background task; the API is
   immediately available.
7. **Type safety** — Pydantic v2 backend + TypeScript frontend, end to end.
8. **Good docs** — detailed README + IMPLEMENTATION_GUIDE.
9. **Dockerised** — `docker compose up` runs the full stack, with a healthcheck.

---

## 6. Issues & risks ⚠️

### Correctness / robustness
- **No DB migrations** — only `create_all`; production schema evolution needs Alembic.
- **Scheduler is single-process** — a multi-replica deploy would cause duplicate ingestion.
- **`_existing_timestamps` is unbounded** — loads all of an asset's timestamps into memory;
  a scaling issue as data grows. Add a time-window filter.
- **CoinGecko client is per-call** — no connection reuse; a shared client would be better.

### Security
- **CORS** — origin is restricted (good), but the `allow_methods/headers=["*"]` +
  `allow_credentials=True` combo should be tightened for production.
- **No auth / rate limiting** — `/ingest`, `/strategy/run` etc. are open. A public deploy
  could be abused (e.g. triggering CoinGecko calls). Fine for internal/demo use.
- **Secrets in compose** — Postgres credentials are plain-text in `docker-compose.yml`
  (fine for demo, but production needs a secrets manager / env file).
- **No input-sanitisation issues found** — using the SQLAlchemy ORM means no SQL injection
  risk, params are bound. ✅

### Testing / quality
- **No integration tests** — no router / DB / ingestion coverage.
- **No frontend tests** — no component/E2E (Playwright).
- **Types manually synced** — risk of backend ↔ frontend schema drift. OpenAPI codegen
  recommended.

### Minor / polish
- No client-side validation in the strategy form (short < long).
- `StrategyPanel` uses index in the list key.
- Basic error UX (single global error bar).

---

## 7. Recommended improvements (priority order)

| Priority | Improvement | Why |
|----------|------------|-----|
| 🔴 High | Add Alembic migrations | Production schema safety |
| 🔴 High | Auth or rate-limit on `/ingest`, `/strategy/run` | Prevent abuse |
| 🟠 Med | Time-window filter in `_existing_timestamps` | Memory/scaling |
| 🟠 Med | Shared httpx client (connection pooling) | Performance |
| 🟠 Med | API integration tests (test DB) | Confidence |
| 🟢 Low | OpenAPI → TS type codegen | Schema sync |
| 🟢 Low | Client-side validation + better error UX | UX |
| 🟢 Low | More indicators (RSI/MACD), backtest P&L | Feature depth |
| 🟢 Low | Redis cache + Celery worker | Heavier jobs |
| 🟢 Low | WebSocket / Binance live stream | Sub-minute updates |

---

## 8. Overall assessment

**Quality: very good.** For a technical-task / portfolio project this is
**well-above-average** code. The architecture is cleanly layered, the core logic is pure
and well-tested, the strategy system is genuinely extensible, and ingestion is idempotent
and resilient. Type safety runs end to end.

**Production readiness:** ~70%. The main gaps are migrations, auth/rate-limiting,
multi-process scheduling, and integration tests. Fixing those four would make it
near-production-ready.

**Best files:** `analytics/compute.py`, the `strategy/` package (clean, testable, extensible).
**Needs the most attention:** `scheduler.py` (scaling), `ingestion.py`
(`_existing_timestamps`), `main.py` CORS config.

---

*Generated by code analysis — frontend (Next.js 14) + backend (FastAPI) full review.*
