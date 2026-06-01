# Event Scheduling Platform


Production-ready, microservices-based event scheduling backend (calendar-style) with recurring events, occurrence modifications, and invitations.

**Designed for:** Rajendra Badgujar — Tech Lead Python System Design Assessment

## Features

- Event CRUD with title, description, organizer, start/end, timezone, participants, optional location
- Recurring events: daily, weekly, monthly, yearly, custom (`by_weekday`, `by_monthday`, `interval`)
- Occurrence edits: **single**, **future**, **all** scopes
- Invitations: accept, reject, tentative
- API Gateway with unified Swagger UI
- Private microservices (internal API key, not host-exposed)

## Quick Start (Docker)

```bash
cd /path/to/Inapp-Assessment
cp .env.example .env
docker compose up --build -d
```

Wait for health checks (~30–60s), then open:

| URL | Description |
|-----|-------------|
| http://localhost:8080/ | Test UI (web frontend) |
| http://localhost:8080/ui/ | Test UI (direct path) |
| http://localhost:8080/docs | Swagger UI (API Gateway) |
| http://localhost:8080/health | Gateway health |
| http://localhost:8080/redoc | ReDoc |

Internal services are **not** published to the host (only `api-gateway` port `8080`).

## Test UI (Frontend)

A simple browser UI is bundled with the API gateway:

1. Open http://localhost:8080/
2. **Users** tab — create users (IDs are saved in browser localStorage)
3. **Events** tab — create one-off or recurring events, load calendar range
4. **Invitations** tab — send invites and accept/reject/tentative

No separate frontend server or build step required.

## Example API Flow

### 1. Create users

```bash
curl -s -X POST http://localhost:8080/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"organizer@example.com","full_name":"Rajendra Badgujar"}'

curl -s -X POST http://localhost:8080/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"guest@example.com","full_name":"Guest User"}'
```

### 2. Create weekly recurring event (every Monday 10:00 UTC)

```bash
curl -s -X POST http://localhost:8080/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Standup",
    "description": "Weekly sync",
    "organizer_id": "<ORGANIZER_UUID>",
    "start_time": "2026-06-02T10:00:00Z",
    "end_time": "2026-06-02T10:30:00Z",
    "timezone": "UTC",
    "location": "https://meet.example.com/standup",
    "participant_ids": ["<GUEST_UUID>"],
    "recurrence_rule": {
      "frequency": "weekly",
      "interval": 1,
      "by_weekday": ["MO"],
      "count": 10
    }
  }'
```

### 3. List upcoming occurrences

```bash
curl -s "http://localhost:8080/api/v1/events?range_start=2026-06-01T00:00:00Z&range_end=2026-08-01T00:00:00Z&user_id=<ORGANIZER_UUID>"
```

### 4. Edit single occurrence (change time for one meeting)

```bash
curl -s -X PATCH "http://localhost:8080/api/v1/events/<SERIES_ID>/occurrences" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "single",
    "occurrence_start": "2026-06-09T10:00:00Z",
    "start_time": "2026-06-09T11:00:00Z",
    "end_time": "2026-06-09T11:30:00Z"
  }'
```

### 5. Send invitation & accept

```bash
curl -s -X POST http://localhost:8080/api/v1/invitations \
  -H "Content-Type: application/json" \
  -d '{
    "event_series_id": "<SERIES_ID>",
    "invitee_id": "<GUEST_UUID>",
    "invited_by": "<ORGANIZER_UUID>"
  }'

curl -s -X PATCH "http://localhost:8080/api/v1/invitations/<INVITATION_ID>/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "accepted"}'
```

## Services

| Service | Port (internal) | Database |
|---------|-----------------|----------|
| api-gateway | 8000 → **8080** host | — |
| user-service | 8001 | postgres-users |
| event-service | 8002 | postgres-events |
| invitation-service | 8003 | postgres-invitations |

## Configuration

Copy `.env.example` to `.env` and adjust values. All services read configuration from environment variables (no hardcoded secrets or URLs in application code).

Key variables:

- `INTERNAL_API_KEY` — shared by all services for internal calls
- `USER_SERVICE_URL`, `EVENT_SERVICE_URL`, `INVITATION_SERVICE_URL` — upstream URLs (API gateway)
- `USERS_DATABASE_URL`, `EVENTS_DATABASE_URL`, `INVITATIONS_DATABASE_URL` — per-service Postgres DSNs
- `CORS_ORIGINS`, `SERVE_FRONTEND`, `FRONTEND_DIR` — API gateway UI and CORS

See `.env.example` for the full list.

## System Design

See [ARCHITECTURE.md](./ARCHITECTURE.md) for:

- High-level architecture diagram
- Database schema
- Recurrence & exception strategy
- API design
- Scalability & edge cases

## Stop

```bash
docker compose down -v
```
