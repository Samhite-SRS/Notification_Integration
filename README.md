# Notification_Integration

A Notification Management Application that lets a user send a message across
**Teams, Email and Slack** from one form, tracks delivery status per channel,
retries failures, and accepts delivery-confirmation callbacks via a webhook.

Built to the "Notification Management Application (Teams • Email • Slack)"
spec: FastAPI backend + MySQL (no ORM — raw SQL via PyMySQL) + a static
HTML/CSS/JS frontend, with a provider-adapter layer so the service never
talks to a vendor SDK directly.

```
Frontend (static HTML/JS)  --fetch-->  FastAPI API layer  -->  Notification Service
                                                                     |
                                                     +---------------+---------------+
                                                     |               |               |
                                               Teams Provider   Slack Provider  Email Provider
                                               (Power Automate)  (Slack SDK)     (SMTP)
                                                     |               |               |
                                                     +-------- MockProvider --------+
                                                        (auto fallback when a
                                                         channel's credentials
                                                         aren't configured)

                                    Repository / Database Layer (raw SQL, PyMySQL)
                                                     |
                                                   MySQL
```

## Project layout

```
Notification_Integration/
├── docker-compose.yml            # one-command stack: MySQL + Backend + Frontend
├── Backend/
│   ├── main.py                  # FastAPI entrypoint (CORS, DB init, router)
│   ├── requirements.txt
│   ├── .env.example             # copy to .env and fill in real credentials
│   ├── Dockerfile
│   ├── schema.sql                # raw MySQL DDL - the single source of truth for the schema
│   ├── app/
│   │   ├── config.py             # Settings (env-driven)
│   │   ├── db.py                 # PyMySQL connection management (no ORM)
│   │   ├── security.py           # webhook secret comparison, redaction
│   │   ├── schemas.py            # Pydantic request/response models
│   │   ├── models/                # plain dataclasses (Notification, NotificationDelivery)
│   │   ├── repositories/          # the only place raw SQL is written
│   │   ├── providers/             # Teams / Slack / Email adapters + Mock + factory
│   │   ├── services/               # NotificationService, retry policy
│   │   ├── webhooks/                # provider callback normalization
│   │   └── api/                     # FastAPI routes
│   └── tests/                        # pytest suite (offline, MockProvider only)
└── Frontend/
    ├── Dockerfile
    ├── index.html                    # Send Notification form
    ├── dashboard.html                # stats + recent notifications
    ├── History.html                  # search/filter notification history
    ├── config.js                     # API_BASE_URL
    └── common.js                     # shared fetch helpers used by all 3 pages
```

## Running it with Docker (recommended for a quick demo)

```bash
cp Backend/.env.example Backend/.env   # edit with real credentials, or leave blank for Mock
docker compose up --build
```

Starts MySQL + the backend + the frontend together, in one command:

- Frontend: `http://localhost:5500/index.html`
- Backend docs: `http://localhost:8000/docs`

This MySQL is a fresh, empty database living in its own Docker volume,
separate from any MySQL you run natively — no local MySQL install needed.
`Backend/.env`'s `MYSQL_*` values are ignored under Docker (the compose file
always points the backend at its own `mysql` service instead); everything
else in that file — Teams/Slack/SMTP credentials, retry settings, webhook
secret — is used exactly as it would be running natively. The backend
container bind-mounts `Backend/`, so editing the code on your machine still
hot-reloads it, same as `uvicorn --reload`. See `docker-compose.yml` for
details, including how to override the MySQL root password.

Stop everything with `docker compose down` (add `-v` to also delete the
MySQL data volume and start fresh next time).

## Running the backend (without Docker)

```bash
cd Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit with real credentials, or leave blank for Mock

uvicorn main:app --reload --port 8000
```

This requires a MySQL server to already be running (see below) — on startup
the app connects via PyMySQL and creates its tables automatically if they
don't exist yet (raw `CREATE TABLE IF NOT EXISTS`, no migration tool). Visit
`http://localhost:8000/docs` for interactive Swagger docs.

### Database — MySQL only, no ORM

There is no SQLite fallback and no SQLAlchemy: every read and write goes
through raw SQL in `app/repositories/notification_repository.py`, executed
via PyMySQL (`app/db.py`). A running MySQL server is required.

1. Install and start MySQL (e.g. on macOS: `brew install mysql && brew services start mysql`).
2. Create the database:
   ```sql
   CREATE DATABASE IF NOT EXISTS notification_db CHARACTER SET utf8mb4;
   ```
   (or run `Backend/schema.sql` directly, which creates both the database and
   the two tables in one step — either way, the app will create the tables
   itself on first boot if they don't already exist).
3. Set these in `.env`:
   ```
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your-password
   MYSQL_DATABASE=notification_db
   ```

### Provider credentials (all optional — Mock is the default)

Every channel falls back to `MockProvider` (always succeeds, no network call)
until its own credentials are set in `.env`, so the whole app — including the
demo below — runs with zero external accounts configured:

| Channel | Env vars | Notes |
|---|---|---|
| Teams | `TEAMS_WEBHOOK_URL` | Power Automate / Teams incoming webhook |
| Slack | `SLACK_BOT_TOKEN` | Bot token with `chat:write`, `im:write`, `users:read`, `users:read.email` |
| Email | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SENDER_EMAIL` | Any SMTP provider (Gmail example in `.env.example`) |

Set `FORCE_MOCK_PROVIDERS=true` to force every channel to Mock even if
credentials are present (handy for demos/CI).

### Running the frontend

The frontend is plain static HTML/CSS/JS — no build step. Serve it with any
static file server and open it in a browser, e.g.:

```bash
cd Frontend
python3 -m http.server 5500
# then open http://localhost:5500/index.html
```

If the backend runs somewhere other than `http://localhost:8000`, edit
`Frontend/config.js` (`window.API_BASE_URL`). CORS is controlled by
`CORS_ORIGINS` in the backend's `.env` (`*` by default, which is fine for
local development).

### Demo flow

1. Start the backend (`uvicorn main:app --reload --port 8000`) and the
   frontend static server, both with default settings — no credentials
   needed, everything sends through `MockProvider`.
2. Open `index.html`, check one or more channels, fill in a destination for
   each, and send. Each channel's delivery status is echoed back in the form.
3. Open `dashboard.html` to see the total/delivered/pending/failed counters
   and the most recent notifications update live from `/api/stats` and
   `/api/notifications`.
4. Open `History.html` to search and filter every delivery.
5. To see a retry in action, configure `FORCE_MOCK_PROVIDERS=false` with an
   intentionally wrong `TEAMS_WEBHOOK_URL` (or similar) so a real send fails,
   then call `POST /api/notifications/{id}/retry`.

## API summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness check |
| POST | `/api/notifications` | create a notification and send it on every requested channel |
| GET | `/api/notifications` | list/search/filter (`channel`, `status`, `q`, `limit`, `offset`) |
| GET | `/api/notifications/{id}` | fetch one notification + its per-channel deliveries |
| POST | `/api/notifications/{id}/retry` | re-attempt every `FAILED` delivery, bounded by `RETRY_MAX_ATTEMPTS` |
| POST | `/api/webhooks/{provider}` | delivery-confirmation callback (`X-Webhook-Secret` header required); idempotent |
| GET | `/api/stats` | total/pending/delivered/failed counts (backs the dashboard) |

Example create request:

```json
{
  "title": "Deploy finished",
  "message": "Build #42 deployed to prod",
  "channels": {
    "teams": [{ "destination": "ops-channel" }],
    "slack": [{ "destination": "#engineering" }],
    "email": [{ "recipient": "team@example.com", "subject": "Deploy done" }]
  }
}
```

## Design notes

- **Provider abstraction:** `NotificationProvider` (an ABC in
  `app/providers/base.py`) is the only interface the service layer knows
  about. `app/providers/factory.py` decides Teams/Slack/Email vs. Mock per
  channel based on whether that channel's credentials are configured — the
  service and API layers never change.
- **Independent per-channel status:** one `NotificationDelivery` row per
  (notification, channel, destination), so one channel failing never affects
  another.
- **Bounded retry with backoff:** `app/services/retry.py` retries only
  failures the adapter marks `retryable` (timeouts, 5xx, rate limits) with
  exponential backoff, up to `RETRY_MAX_ATTEMPTS`. Non-retryable failures
  (bad credentials, invalid destination) fail immediately.
- **Idempotent webhook:** `POST /api/webhooks/{provider}` is protected by a
  shared-secret header, ignores callbacks for unknown message ids without
  erroring, no-ops on a duplicate status, and never lets a stale `FAILED`
  callback overwrite an already-`DELIVERED` status.
- **Cross-notification threading:** repeated notifications sent to the same
  (channel, destination) pair land in one running conversation instead of as
  separate, unrelated messages. A `channel_threads` table (see
  `schema.sql`) stores one "anchor" per (channel, destination) — a Slack
  `thread_ts` or an Email `Message-ID` — the first time a message is sent
  there. Every later send to that same destination looks up the anchor
  first and passes it to the provider: Slack replies in-thread (`thread_ts`),
  Email sets `In-Reply-To`/`References` and prefixes the subject with "Re: ".
  Teams intentionally ignores this (see `app/providers/teams/provider.py`) —
  a Teams 1:1 chat is already one continuous conversation, so there is
  nothing to thread. The anchor is "first write wins": once saved for a
  destination it is never overwritten, so every later message threads off
  the original root.

## Tests

Tests run against a dedicated MySQL database (`notification_test_db`),
never the dev database — every test drops and recreates the tables
first. Create it once:

```sql
CREATE DATABASE IF NOT EXISTS notification_test_db CHARACTER SET utf8mb4;
```

Then run:

```bash
cd Backend
source .venv/bin/activate
MYSQL_PASSWORD=your-password pytest -q
```

(`MYSQL_HOST`/`MYSQL_PORT`/`MYSQL_USER` default to `127.0.0.1`/`3306`/`root` —
override the same way if yours differ.) `FORCE_MOCK_PROVIDERS=true` is set
automatically by the test suite, so no real Teams/Slack/SMTP credentials or
network access are needed — the 30 tests cover the API
(create/list/filter/stats/404s), bounded retry/backoff behavior,
provider-factory fallback, webhook security/idempotency, and cross-notification
threading (`tests/test_threading.py`), all against a real MySQL schema.
