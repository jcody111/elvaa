# Deployment guide

**This is deployment preparation, not a claim of production readiness.** Read [STATUS.md](STATUS.md) and [PAYMENTS.md](PAYMENTS.md) before a launch.

## Next.js and Django on Vercel Services

1. Import the Git repository and leave **Root Directory** at the repository root, where `vercel.json` lives. Use the **Services** framework preset if the dashboard asks you to select a preset. Clear custom Install, Build and Output Directory overrides from previous attempts. Vercel builds Next.js in `frontend` and discovers Django through `backend/manage.py`.
2. Keep **Automatically expose System Environment Variables** enabled. Set `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY`, and the Redis connection settings in [backend/.env.example](../backend/.env.example) for each environment. Connect Neon to supply `DATABASE_URL`, or set the `POSTGRES_*` variables for a PostgreSQL endpoint reachable from Vercel. Use the provider's pooled endpoint for requests and preserve its TLS options. Set `USE_SQLITE=False`. Use separate database connections for Preview and Production.
3. Set `DJANGO_ALLOWED_HOSTS` to each custom storefront hostname and `CSRF_TRUSTED_ORIGINS` to the corresponding HTTPS origins. Django also uses the exact Vercel-generated hostnames exposed by the platform. Set `FRONTEND_URL` to the public HTTPS storefront origin used in email and checkout return links. Set `NEXT_PUBLIC_SITE_URL` to the canonical public origin if you have a custom domain. Vercel injects `BACKEND_INTERNAL_URL` into the frontend functions. Leave `API_UPSTREAM` unset in this configuration.
4. Run `python manage.py migrate` from `backend` using the target database's credentials before serving traffic. Use Neon's direct connection string for migrations when available. Run migrations once per release from a trusted machine or CI job with database access. For a new demo database, `python manage.py seed` adds sample products. `collectstatic` runs during the Django build.
5. For image uploads, configure the `MEDIA_S3_*` bucket, credentials and region in [backend/.env.example](../backend/.env.example). Set `MEDIA_S3_ENDPOINT_URL` for an S3-compatible provider that requires a custom endpoint. Migrate existing uploaded files to the bucket using their existing object keys. The default Vercel Functions request limit is 4.5 MB including multipart overhead. Use images of 4 MB or less on Vercel. Seeded `/images/` assets are bundled with Next.js.
6. Keep the Celery worker and exactly one beat scheduler running separately with the same production database, broker and Stripe settings if using Stripe reconciliation. Configure SMTP before relying on account or newsletter emails. The Stripe webhook URL on the shared domain is `/api/v1/payments/stripe/webhook/`.
7. After deploy, check `/api/v1/health/` for a JSON response and `/api/v1/products/` for database connectivity. Open `/shop` and a product page, then verify sign-in and session refresh on the deployed domain. The storefront admin lives at `/admin`.

## Frontend on Vercel with an independent Django API

1. Set **Root Directory** to `frontend` and choose **Next.js**. Use the preset defaults for Install, Build and Output Directory.
2. Set `API_UPSTREAM=https://api.example.com` to the public API origin and `NEXT_PUBLIC_SITE_URL` to the storefront origin. Next.js forwards same-origin `/api/` and `/media/` requests. Redeploy after changing the API origin because Next.js compiles the rewrites at build time.
3. Follow the Django hosting instructions below. Include the storefront HTTPS origin in Django's `CSRF_TRUSTED_ORIGINS` and set `FRONTEND_URL` to that origin.

## Django API on a VPS/cloud host

1. Provision a Python 3.12+ or Docker host, managed PostgreSQL, Redis and persistent/object media storage. Start with `backend/.env.example` in a secret manager; use a long unique `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, precise `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, and `FRONTEND_URL=https://shop.example.com`.
2. Configure `POSTGRES_*` and `REDIS_URL` / `CELERY_BROKER_URL`. Use TLS and network isolation appropriate to the providers. Review the migration notes below and take a tested backup; then run `python manage.py migrate`, `python manage.py collectstatic --noinput`, and create a superuser securely.
3. Run Gunicorn behind a reverse proxy with HTTPS; set `X-Forwarded-Proto` correctly and expose only required ports. WhiteNoise can serve collected static files. Django does **not** serve uploaded media in production: configure a separate, access-controlled media origin or reverse-proxy location, with safe upload scanning and correct content types.
4. Run a Celery worker and exactly one beat scheduler against the configured Redis broker; monitor failures and stale/unknown payment sessions. The scheduled reconciliation task does nothing until Stripe is configured and does not resolve ambiguous sessions automatically. See [PAYMENTS.md](PAYMENTS.md).
5. Configure and verify real SMTP delivery as described below. Configure monitoring, backups, log retention, secret rotation and recovery procedures. Redis-backed rate limiting must be shared across API workers.
6. Create DNS records for the storefront and API, issue TLS certificates and test cross-origin/CSRF behavior via the deployed frontend. Set HSTS only after HTTPS is verified on all affected hosts.

The included Compose file is a **local-development** reference; its images have not been built or validated as a hardened production deployment here. Do not expose PostgreSQL or Redis publicly. Its development `.env` uses HTTP and `DJANGO_DEBUG=True`; never reuse those defaults in production.

## Newsletter migrations and delivery

- **Back up first.** Migration `marketing.0002` deactivates existing active newsletter addresses that have no recorded confirmation. It retains their addresses but they must request and confirm a new subscription. The migration's data operation is intentionally not reversed automatically.
- Migration `marketing.0003` enforces case-insensitive coupon-code uniqueness and stops if older data contains collisions. Before deployment, inspect `SELECT lower(code), count(*) FROM marketing_coupon GROUP BY lower(code) HAVING count(*) > 1;`. Reconcile any collisions manually with an operator: preserve usage counts and examine pending unpaid orders before changing or deleting codes. Do not blindly merge or release reservations. Take and verify a backup, then apply the migration.
- Set `FRONTEND_URL` to the public **HTTPS** storefront origin, not an API or internal container URL. Email links use this origin and put signed tokens in URL fragments; users must press a button to confirm or unsubscribe. Check that both `/newsletter/confirm` and `/newsletter/unsubscribe` load through the public storefront.
- Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_TIMEOUT` (seconds; default 10), and `DEFAULT_FROM_EMAIL` for your provider. Store credentials in a secret manager and configure the sender domain's authentication. Verify delivery, links, spam placement and unsubscribe with real test mailboxes. No real SMTP provider was tested in this environment.
- Sending currently occurs synchronously after commit, with no durable retry/outbox. Failures are logged, and the public response remains generic; an attempted confirmation is not proof of delivery. Eligible inactive addresses may request another link after five minutes. Add monitored, durable delivery and bounce handling before accepting real subscriptions. Do not log signed tokens or retain test messages unnecessarily.
- The development console backend prints messages and links to process output; it does not deliver email and must not be used for real subscribers. The optional test SMTP sink described in the README is only for disposable, synthetic addresses.

## Before launch

- Replace demonstration products, images, shipping terms and legal drafts with approved content.
- Review VAT, delivery regions, returns, consumer law, privacy and email consent with qualified advisers. Implement data-subject rights, retention and legally appropriate consent records.
- Perform a security review, accessibility and cross-browser testing, load testing, media scanning, backup/restore and incident-response exercises.
- Configure and verify Stripe in test mode end-to-end before considering live keys; see [PAYMENTS.md](PAYMENTS.md). Demo checkout must be disabled.
- Confirm webhooks, abandoned reservations, refunds, customer notifications and operational reconciliation are handled. Current gaps are listed in [STATUS.md](STATUS.md).
