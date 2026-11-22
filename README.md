# ELVAA

A premium fashion-commerce **development preview** with independent Next.js and Django applications. The repository contains real catalog, account, wishlist, inventory, order, and staff-management APIs backed by PostgreSQL. The current implementation is **not yet production-ready**: see [implementation status](docs/STATUS.md) and [payment limitations](docs/PAYMENTS.md) before accepting real customers or money.

## What is here

- `frontend/`: Next.js 16, TypeScript, Tailwind, TanStack Query, Zustand, React Hook Form, Zod and Lucide. The storefront and staff dashboard are separately deployable on Vercel.
- `backend/`: Django 5.2 LTS, DRF, PostgreSQL models/migrations, role checks, JWT rotation, inventory movements and an optional Stripe-hosted checkout adapter.
- `docker-compose.yml`: local PostgreSQL, Redis, Django, Celery worker and scheduler, and Next.js. The scheduled job conservatively rechecks stale Stripe sessions when Stripe is configured.
- `docs/`: architecture, API, deployment, payment and remaining-work guides.

The sample catalogue and campaign images are demonstration content. Seed data is **opt-in**, not a substitute for the database. Newsletter signup uses email double opt-in, but the development console backend does not deliver mail; real delivery requires configured SMTP.

## Local start with Docker

1. Install Docker and Compose. From this directory:
   ```bash
   cp .env.example .env
   # Change the local password and secret. Keep DJANGO_DEBUG=True for plain HTTP local use.
   docker compose up --build -d
   docker compose exec backend python manage.py seed
   docker compose exec backend python manage.py createsuperuser
   ```
2. Open `http://localhost:3000`. API docs: `http://localhost:8000/api/docs/`. Django admin: `http://localhost:8000/admin/`.
3. To try **unpaid demo checkout**, explicitly set `ALLOW_DEMO_CHECKOUT=True` in `.env` and recreate the backend: `docker compose up -d --force-recreate backend`. This does not collect payment and must remain off on a live store.
4. Sign in with the superuser on `/account` to access `/admin`. Staff roles are granted server-side by a superuser; see [architecture](docs/ARCHITECTURE.md).

To stop: `docker compose down`. Add `-v` only if you intend to delete the local database and uploaded media.

## Local start without Docker

Use Python 3.12+ and Node 20.9+. PostgreSQL is recommended; SQLite is a **development-only** fallback.

```bash
# Terminal 1 — API with local SQLite and an optional sample catalogue
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
USE_SQLITE=True python manage.py migrate
USE_SQLITE=True python manage.py seed
USE_SQLITE=True python manage.py createsuperuser
USE_SQLITE=True ALLOW_DEMO_CHECKOUT=True python manage.py runserver 0.0.0.0:8000

# Terminal 2 — storefront
cd frontend
npm ci
npm run dev -- --hostname 0.0.0.0
```

For PostgreSQL set `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_PORT` rather than `USE_SQLITE=True`. The Next.js server proxies same-origin `/api/` and `/media/` requests to `API_UPSTREAM`; the browser never needs to call a local backend address directly.

## Tests and checks

```bash
cd backend
USE_SQLITE=True python manage.py test                 # PostgreSQL row-lock tests are skipped on SQLite
# Or set the POSTGRES_* variables to run the full suite on PostgreSQL.

cd ../frontend
npm ci
npm run lint
npm run typecheck
npm test
# With the seeded API and storefront running:
npx playwright install chromium
npm run test:e2e
# Optional staff/demo browser tests mutate a DISPOSABLE database and leave audit/history records:
ELVAA_E2E_STAFF_USERNAME=... ELVAA_E2E_STAFF_PASSWORD=... ELVAA_E2E_DEMO_CHECKOUT=1 npm run test:e2e
# A production build requires an explicit server-side API origin:
API_UPSTREAM=http://127.0.0.1:8000 NEXT_PUBLIC_SITE_URL=http://localhost:3000 npm run build
```

### Optional newsletter browser test

Use **only a disposable database and synthetic addresses**. The test SMTP sink writes email and signed tokens to a local private directory; it is not a mail service and must never be deployed or exposed publicly.

```bash
# Terminal 1, from backend/:
pip install -r requirements-dev.txt
python tools/test_smtp_sink.py --directory /tmp/elvaa-test-mail --port 1025

# Terminal 2, from backend/: run the API with the disposable database
USE_SQLITE=True EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
  EMAIL_HOST=127.0.0.1 EMAIL_PORT=1025 EMAIL_USE_TLS=False \
  FRONTEND_URL=http://localhost:3000 python manage.py runserver 0.0.0.0:8000

# Terminal 3, from frontend/, with the storefront already running:
ELVAA_E2E_MAIL_DIR=/tmp/elvaa-test-mail npx playwright test tests/e2e/newsletter.spec.ts
```

Stop the sink and remove the disposable mailbox after testing. For PostgreSQL, set the `POSTGRES_*` variables instead of `USE_SQLITE=True`. Newsletter messages are delivered synchronously without a durable retry queue; see [deployment guidance](docs/DEPLOYMENT.md) before accepting real subscribers.

## Deployment and security

- [Vercel + Django deployment](docs/DEPLOYMENT.md)
- [Architecture and permissions](docs/ARCHITECTURE.md)
- [REST API](docs/API.md), plus generated OpenAPI at `/api/schema/` and Swagger at `/api/docs/`
- [Stripe setup, limitations and reconciliation](docs/PAYMENTS.md)
- [Implemented features and remaining work](docs/STATUS.md)

Keep production credentials in environment variables or a secret manager, never in the repository. Do not launch with the sample legal text, demo checkout, development secret, local media handling, or unverified payment configuration.
