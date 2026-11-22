# Implementation status

ELVAA is a **development preview, not a production-ready store**. The sample catalogue, imagery and legal pages are demonstration content.

## Implemented in this preview

- Responsive editorial storefront; PostgreSQL-backed catalogue, search, category/brand/price/stock filters, sorting, pagination, quick view, variants, guest/account wishlist, cart quotes and multi-step checkout.
- Registration, login/logout, rotated HttpOnly refresh cookies, password reset, email verification, profile, addresses, account-linked orders and moderated reviews. Password changes and account deactivation revoke prior access and refresh tokens. Actual email delivery requires a configured email backend; verification is not mandatory for login.
- Server-side roles and staff screens for product/category CRUD, image upload, variants, inventory search/pagination, guarded stock adjustments and movement history, searchable order details/status/tracking, customer status and account-linked purchase history, coupons/subscribers, reports and limited settings/analytics. Paid customer value currently includes only fully paid orders, not partial refunds or guest orders.
- Newsletter double opt-in: new requests remain inactive until a recipient deliberately confirms a signed email link; consent and unsubscribe timestamps and audit events are recorded. Confirmation links expire after 48 hours; a welcome email includes an unsubscribe link. Staff can search and unsubscribe addresses but cannot directly activate them. Existing subscribers without recorded confirmation are deactivated by migration `marketing.0002`.
- Marketing staff can create, deactivate or delete discount codes; pending unpaid reservations block renaming or deleting their code. Code uniqueness is case-insensitive. Django-admin coupon and subscriber views are read-only; use the staff API/dashboard for changes.
- Atomic stock reservations and compare-and-set inventory adjustments. Pending orders prevent product/variant deletion; stock changes and order/payment state cannot be bypassed through the ordinary Django-admin edit screens.
- Optional Stripe-hosted Checkout, signed webhook processing, provider-confirmed cancellation, a staff payment recheck, and a conservative scheduled reconciliation job for known stale Stripe sessions. An explicitly enabled demo checkout creates **unpaid** orders. **No real Stripe test-mode or live transaction has been performed.**
- PostgreSQL migrations, OpenAPI schema, local Docker/Compose definitions, deployment examples and tests. Redis/Celery job delivery was exercised locally with Stripe disabled; the preview itself does not run a persistent worker or scheduler.

## Still required before production

- Configure and verify real SMTP delivery, authentication, bounce handling and deliverability for password recovery, verification and newsletter messages. Local newsletter end-to-end testing used a disposable SMTP sink, not a real mail provider. Newsletter emails are currently sent synchronously after database commit, without a durable queue or automatic retry; monitor failures and add reliable delivery before launch. A confirmation timestamp and method are recorded, but no consent-text/policy version is stored. There is no campaign-sending tool.
- Real Stripe test-mode end-to-end verification, monitoring and operational reconciliation. Unknown sessions after ambiguous provider failures remain reserved and require investigation; asynchronous pending payments are not automatically released. In-dashboard refunds, invoices, order-confirmation email, carrier integrations and a complete returns workflow are not implemented.
- Comprehensive tax/currency/region support (currently EUR and a simple VAT-inclusive estimate), shipping and fraud controls, business policies and legally reviewed GDPR/consumer disclosures. Data-subject rights workflows and legally sufficient consent/retention processes still need implementation and review.
- Advanced administration: complete customer-support workflows, campaign scheduling and banner editor, a content/blog CMS, granular settings and notifications, complete sales/customer/product analytics and richer charts. Some underlying models or Django-admin views exist but are not complete workflows.
- Production-grade media storage/scanning, CSP, penetration testing, an accessibility audit, performance/load tests, multi-tab refresh/concurrency testing, observability, backups, disaster recovery and incident procedures.
- Docker image builds and Vercel deployment have not been executed here. The local preview and its transient development database are not a production deployment.

Tests cover backend authorization, JWT/CSRF and revocation, stock/order concurrency, payment signature/idempotency/reconciliation with mocked provider calls, newsletter consent, inventory and reports, plus selected frontend unit and desktop/mobile browser paths. Passing tests do not certify production readiness.
