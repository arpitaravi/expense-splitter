# Deploy (free): Render (API + Postgres) + Vercel (frontend) + Cloudinary (receipts) + Brevo (emails)

## 1. Code on GitHub
Push this folder to a GitHub repo (`.gitignore` already excludes venv/node_modules).

## 2. Render (backend)
New → Blueprint → pick the repo (`render.yaml`). Fill the env vars it asks for:
`ALLOWED_HOSTS` (your Render host, no https), `CORS_ORIGINS` + `FRONTEND_URL` (your Vercel URL),
`CSRF_TRUSTED_ORIGINS` (Vercel URL + Render URL, with https://). Fill Vercel's URL after step 3 and redeploy.

## 3. Vercel (frontend)
Import repo → Root Directory `frontend` → env `VITE_API_URL=https://<render-host>/api`
(+ `VITE_DEMO=1` for the "Try demo account" button) → Deploy.

## 4. Demo data
Render → splitter-api → Shell → `python manage.py seed_demo`
(users `asha`, `ravi`, `meena`, password `demo12345`; no emails are sent for demo data).

## 5. Receipts (optional) - Cloudinary
Free account → copy `CLOUDINARY_URL` into Render env.

## 6. Real emails (invites, password reset, digests) - Brevo
Render's free tier **blocks SMTP ports (25/465/587)**, so Gmail SMTP will not work there. The app sends
mail through Brevo's HTTPS API instead:
1. Create a free Brevo account → *SMTP & API* → create an **API key** → Render env `BREVO_API_KEY`.
2. Brevo → *Senders* → add + verify your email → Render env `DEFAULT_FROM_EMAIL=<that email>`.
3. Redeploy, then use *Members → Send invites* or *Forgot password* to test.
Free plan has a daily send limit; check Brevo's current limits. (Locally, with no key set, emails print in the terminal.)

## 7. Recurring expenses & weekly digest on free hosting (no Celery)
Free hosting has no background worker, so a tiny scheduler calls the API once a day:
1. Render env `CRON_TOKEN` (the blueprint generates one) → copy its value.
2. GitHub repo → Settings → Secrets → Actions: add `API_URL` (`https://<render-host>`) and `CRON_TOKEN`.
3. `.github/workflows/daily-cron.yml` now runs daily (06:00 IST). Test: Actions tab → *Daily jobs* → Run workflow.
Missed days are caught up within the same month. Users can also press **Add now** on any recurring expense.

## 8. Check
`https://<render-host>/api/health/` → `{"status":"ok"}` · `/api/docs/` → Swagger.

Notes: Render free web services sleep after inactivity (first request ~30-50 s) and the free Postgres expires
after ~30 days. With a paid plan + Redis you can run Celery (`CELERY_ENABLED=1`, `REDIS_URL`) instead of step 7.
