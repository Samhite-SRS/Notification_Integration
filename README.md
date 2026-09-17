# Notification_Integration

A Notification Management Application that lets a user send a message across
**Teams, Email and Slack** from one form, tracks delivery status per channel,
retries failures, and accepts delivery-confirmation callbacks via a webhook.

Built to the "Notification Management Application (Teams • Email • Slack)"
spec: FastAPI backend + MySQL (SQLite for local dev) + a static HTML/CSS/JS
frontend, with a provider-adapter layer so the service never talks to a
vendor SDK directly.

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

                                          Repository / Database Layer (SQLAlchemy)
                                                     |
                                          MySQL (prod) / SQLite (local MVP)
```

## Project layout

```
Notification_Integration/
├── Backend/
│   ├── main.py                  # FastAPI entrypoint (CORS, DB init, router)
│   ├── requirements.txt
│   ├── .env.example             # copy to .env and fill in real credentials
│   ├── schema.sql                # raw MySQL DDL (mirrors the ORM models)
│   ├── app/
│   │   ├── config.py             # Settings (env-driven)
│   │   ├── db.py                 # SQLAlchemy engine/session
│   │   ├── security.py           # webhook secret comparison, redaction
│   │   ├── schemas.py            # Pydantic request/response models
│   │   ├── models/                # ORM models (Notification, NotificationDelivery)
│   │   ├── repositories/          # all direct DB access
│   │   ├── providers/             # Teams / Slack / Email adapters + Mock + factory
│   │   ├── services/               # NotificationService, retry policy
│   │   ├── webhooks/                # provider callback normalization
│   │   └── api/                     # FastAPI routes
│   └── tests/                        # pytest suite (offline, MockProvider only)
└── Frontend/
    ├── index.html                    # Send Notification form
    ├── dashboard.html                # stats + recent notifications
    ├── History.html                  # search/filter notification history
    ├── config.js                     # API_BASE_URL
    └── common.js                     # shared fetch helpers used by all 3 pages
```

## Running the backend

```bash
cd Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit with real credentials, or leave blank for Mock

uvicorn main:app --reload --port 8000
```

On startup the app creates its tables automatically (`Base.metadata.create_all`),
so no migration step is required for the SQLite path. Visit
`http://localhost:8000/docs` for interactive Swagger docs.

### Database

- **Local / MVP (default):** `DATABASE_URL=sqlite:///./notification.db` — zero
  setup, a file appears next to `main.py`.
- **MySQL:** set `DATABASE_URL=mysql+pymysql://user:password@host:3306/notification_db`
  in `.env`, then either let the app create the tables on first boot, or run
  `Backend/schema.sql` directly against MySQL first (both define the same two
  tables: `notifications`, `notification_deliveries`).

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

## Tests

```bash
cd Backend
source .venv/bin/activate
pytest -q
```

The suite runs fully offline against a throwaway SQLite file with
`FORCE_MOCK_PROVIDERS=true`, covering the API (create/list/filter/stats/404s),
bounded retry/backoff behavior, provider-factory fallback, and webhook
security/idempotency.
