# Architecture and authorization

## Applications

The Next.js frontend and Django backend are independent deployments. The browser calls same-origin `/api/v1/...`; Next.js rewrites requests server-side to `API_UPSTREAM`. PostgreSQL stores core data. Redis can provide a shared Django cache and Celery broker. A worker plus one beat scheduler run conservative stale-Stripe-session reconciliation; they must be deployed and monitored separately where Compose is not used.

Authentication uses a 15-minute access JWT in browser memory and a rotating HttpOnly, SameSite=Lax refresh cookie. Login, refresh and logout use a CSRF cookie/header. Password changes, password resets and account deactivation increment a server-side authentication version and revoke prior access and refresh tokens, including after reactivation. Logout blacklists the current refresh token; a previously issued access token can remain valid until expiry. The Django admin password-change/deactivation paths also revoke existing tokens.

Guest wishlists and carts are stored on the device; wishlist entries are merged after sign-in. Prices, coupons, shipping and stock are recalculated on the server. Guest orders are not automatically attached to an account by matching email.

## Backend roles

| Role | Backend areas |
|---|---|
| Super administrator / Django superuser | All API areas |
| Store administrator | Products, orders, customers, marketing, settings, reports and content |
| Product manager | Products, categories, variants, images and inventory |
| Order manager | Orders, status/tracking and provider rechecks |
| Content manager | Marketing and contact messages |
| Customer | Own profile, addresses, orders, reviews and wishlist |

Django enforces these checks; frontend navigation is not a security boundary. Customer tools exclude staff and superuser accounts. A Django superuser can assign roles through Django admin. Django admin also requires Django `is_staff` and appropriate Django permissions; API roles do not automatically grant them. Order, payment, order-item and inventory-movement records are read-only in Django admin so its normal forms cannot bypass transactional state changes.

## Inventory and orders

Product and variant stock are tracked separately and both are checked at checkout. PostgreSQL row locks, stable product-then-variant lock ordering and atomic transactions protect reservations and releases. Existing stock is changed through the inventory adjustment endpoint with the last-observed quantity; a stale value returns HTTP 409. Movement history records adjustments, reservations and releases and retains names after deletion. SQLite does not have equivalent row-lock guarantees.

Quotes do not reserve stock. Checkout recalculates prices and creates an unpaid pending order; a random UUID4 key prevents duplicate reservations on retries. Demo orders stay unpaid. Fulfillment progresses through allowed states only after confirmed payment. Stripe expiration or failed asynchronous payment releases a pending reservation once; a late payment after release requires manual review. Refunds do not automatically restock items. See [PAYMENTS.md](PAYMENTS.md) for reconciliation limitations and operational requirements.

Money is currently EUR and treated as VAT-inclusive. The configurable tax percentage is an estimate, not a jurisdiction-aware tax engine. Standard shipping can become free at a configured discounted-order threshold.
