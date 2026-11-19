# 💸 Group Expense Splitter

Splitwise-style app: add shared expenses, see who owes whom, and settle with the **fewest payments**.

**Stack:** Django + DRF + SimpleJWT + PostgreSQL · Celery + Redis · React + React Router + TanStack Query + Tailwind + Recharts · Docker · GitHub Actions

## Live demo
- App: _add your Vercel URL_  · API docs: _add your Render URL_`/api/docs/`
- Demo login: click **Try demo account** (`asha` / `demo12345`)

## Highlights
- Integer-paise money model with deterministic remainder distribution (4 split types)
- Greedy two-heap debt simplification (≤ n−1 payments), `sum(balances) == 0` invariant tested
- Receiver-confirmed settlements, soft deletes, optimistic locking (409 on stale edits), full audit log
- Group-scoped permissions (404 for non-members), JWT auth, rate limiting, 28 backend tests + CI
- Recurring expenses (UI + catch-up scheduler), email invites + WhatsApp share, leave/remove members (only when settled),
  password reset, profile, paginated lists, one-click "I paid", dashboard with totals across groups
- Production setup: WhiteNoise, HTTPS hardening, Cloudinary receipts, Render blueprint, Vercel SPA config

## Run it

**Everything with Docker**
```bash
docker compose up --build
# app: http://localhost:5173   API docs: http://localhost:8000/api/docs/
```

**Locally (SQLite, no Docker)**
```bash
cd backend && pip install -r requirements.txt
python manage.py migrate && python manage.py runserver     # :8000
cd ../frontend && npm install && npm run dev                 # :5173
```
Celery (optional locally): `celery -A config worker -l info` and `celery -A config beat -l info`.

## Tests
```bash
cd backend && pytest        # splits, simplification invariant, API flow, permissions, concurrency
cd frontend && npm test
```

## Design decisions (interview notes)
| Topic | Decision |
|---|---|
| Money | Integer **paise** everywhere; the UI converts at the edge. No floats. |
| Remainders | `distribute()` floors each share, then gives leftover paise one-by-one to participants in ascending user-id order → deterministic, always sums exactly to the total. |
| Split types | equal / exact / percent / shares, all validated server-side (`services/splits.py`). Percent uses basis points (max 2 decimals). |
| Atomicity | Expense + splits + activity log written in one `transaction.atomic()`. Emails are queued with `on_commit`. |
| Balances | `net = paid − owed`, adjusted by **accepted** settlements. Invariant `sum(net) == 0` is tested. |
| Simplification | Greedy with two heaps: O(n log n), ≤ n−1 payments. Optimal minimum is NP-hard (subset-sum-like) so this is the practical approximation. |
| Settlements | "I paid Ravi ₹500" is **pending** until the receiver confirms (prevents false claims). |
| Edits/deletes | Soft delete, `version` field + `select_for_update` → stale edits get **409**. Every change writes an `ActivityLog` row with before/after. |
| Permissions | All group endpoints go through `GroupScoped`; non-members get **404** (no existence leak). |
| Celery | New-expense email, Monday "you owe ₹X" digest, daily `RecurringExpense` generator (idempotent per day). |

## API (see `/api/docs/` for full schema)
```
POST /api/auth/register/ · /auth/token/ · /auth/token/refresh/
GET/POST /api/groups/                 POST /api/groups/join/ {invite_code}
GET  /api/groups/{id}/
GET/POST /api/groups/{id}/expenses/   GET/PUT/DELETE /api/groups/{id}/expenses/{eid}/
POST /api/groups/{id}/expenses/{eid}/receipt/   (JPG/PNG/PDF ≤5MB; S3 if AWS_STORAGE_BUCKET_NAME set)
GET  /api/groups/{id}/balances/       → net balances + suggested_payments
GET/POST /api/groups/{id}/settlements/   POST .../settlements/{sid}/respond/ {action: accept|reject}
GET  /api/groups/{id}/activity/ · /insights/
POST /api/groups/{id}/invite/ {emails} · /leave/      DELETE /api/groups/{id}/members/{uid}/   (creator only)
GET/POST /api/groups/{id}/recurring/   PATCH/DELETE .../recurring/{rid}/   POST .../recurring/{rid}/run/
GET /api/summary/ · GET/PATCH /api/auth/me/ · POST /api/auth/change-password/ · /auth/password-reset/ (+ /confirm/)
POST /api/cron/daily/   (X-Cron-Token header; recurring expenses + Monday digest)
```
Example expense body:
```json
{"payer": 1, "amount_paise": 100000, "description": "Dinner", "date": "2026-11-18",
 "category": "food", "split_type": "percent",
 "participants": [{"user": 1, "value": 50}, {"user": 2, "value": 30}, {"user": 3, "value": 20}]}
```

## Deploy
See **DEPLOY.md** for the free Render + Vercel + Cloudinary walkthrough. Details:
- **Backend → Render/Railway:** use `backend/Dockerfile`; add Postgres + Redis; set `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `FRONTEND_URL`, `POSTGRES_*`, `REDIS_URL`, email + (optional) `AWS_*`. Run a second service with `celery -A config worker -B -l info`.
- **Frontend → Vercel:** root `frontend`, build `npm run build`, output `dist`, env `VITE_API_URL=https://<api>/api`.

## Not included (ideas for extension)
Django Channels live updates, multi-currency, push notifications.
