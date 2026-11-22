# API overview

Base: `/api/v1/`. Interactive OpenAPI is at `/api/schema/` and `/api/docs/`. The Next.js frontend proxies `/api/` to the independent backend. Paginated lists return `count`, `next`, `previous` and `results` (24 per page by default).

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/health/` | Public | Health check |
| GET | `/auth/csrf/` | Public | Set CSRF cookie; indicate whether a refresh cookie exists |
| POST | `/auth/register/`, `/auth/login/` | Public; login requires CSRF | Create customer / return access token and set HttpOnly refresh cookie |
| POST | `/auth/refresh/`, `/auth/logout/` | Cookie + CSRF | Rotate or blacklist refresh token |
| GET/PATCH | `/auth/me/` | Customer | Own profile; roles and staff flags are read-only |
| POST | `/auth/forgot-password/`, `/auth/reset-password/`, `/auth/verify-email/`, `/auth/change-password/` | Public or authenticated as appropriate | Account recovery and verification |
| GET/POST/PATCH/DELETE | `/auth/addresses/` | Customer | Own saved addresses |
| GET | `/auth/admin/users/`, `/auth/admin/users/{id}/orders/` | Customer-management role | Customer-only list and account-linked order history |
| POST | `/auth/admin/users/{id}/status/` | Customer-management role | Activate/deactivate a customer with optimistic status checking; staff accounts excluded |
| GET | `/products/`, `/products/{slug}/` | Public | Catalog; filters: category, brand, `min_price`, `max_price`, `in_stock`, `is_new`, `is_featured`, `search`, `ordering`, `page` |
| GET | `/categories/`, `/brands/`, `/products/{slug}/related/` | Public | Taxonomy and related products |
| GET/POST/DELETE | `/wishlist/` | Customer | Own saved products |
| GET/POST | `/reviews/` | Public read / signed-in write | Reviews are moderated before public display |
| POST | `/cart/quote/` | Public | Validate stock and calculate current totals without reserving |
| POST | `/checkout/` | Public or customer | Reserve stock and create an unpaid demo order or hosted Stripe session when enabled |
| POST | `/checkout/cancel/` | Checkout-key holder; owner also required for signed-in orders | Cancel a pending checkout only after safe provider confirmation |
| POST | `/payments/stripe/webhook/` | Stripe signature | Verify provider events and update payment/order/reservation state |
| GET | `/orders/` | Customer / order manager | Own orders or all orders for a manager; supports `search`, `status`, `payment_status`, `payment_method`, `ordering` and `page` |
| POST | `/orders/{id}/status/`, `/orders/{id}/reconcile/` | Order manager | Safe status/tracking transition or Stripe provider recheck |
| GET | `/inventory-movements/` | Product manager | Inventory history |
| POST | `/inventory-adjustments/` | Product manager | Set product or variant stock using the last-observed quantity; records the change |
| POST | `/newsletter/` | Public | Request email confirmation; generic response, not an immediate subscription |
| POST | `/newsletter/confirm/`, `/newsletter/unsubscribe/` | Signed-link holder | Explicitly confirm or unsubscribe with a token in the request body |
| GET | `/newsletter/`, `/newsletter/{id}/` | Marketing role | Search/list or view subscriber consent status |
| POST | `/newsletter/{id}/unsubscribe/` | Marketing role | Unsubscribe and invalidate an outstanding confirmation; staff cannot directly activate |
| GET/POST/PATCH/DELETE | `/coupons/`, `/coupons/{id}/` | Marketing role | Search and manage discount codes; reservation safeguards apply |
| POST | `/contact/` | Public | Save a contact message |
| GET | `/admin/stats/`, `/reports/orders.csv/`, `/reports/orders.xlsx/` | Reports role | Paid revenue summary and date-filtered exports |
| GET/PUT | `/settings/store/` | Public read / settings role write | Store settings and payment availability flags |

## Newsletter and coupons

Send `{"email":"person@example.com"}` to `POST /newsletter/`. Valid requests return the same generic 200 response whether the address is new or already active. New addresses remain inactive. A signed confirmation link is sent to eligible inactive addresses, at most once per five minutes; this is an attempt timestamp, not proof of delivery. Each new link invalidates the preceding confirmation link. The link expires after 48 hours. The frontend reads the token from the URL fragment and sends `{"token":"<signed token>"}` only after the recipient presses the confirmation button. A successful confirmation records its timestamp and sends a welcome email with an unsubscribe link. The same explicit POST pattern is used to unsubscribe; unsubscribe invalidates outstanding confirmation links and is safe to repeat. Unsubscribe links are not time-limited. Do not log or share tokens.

The newsletter endpoints share a scoped rate limit (20 requests per hour per anonymous client IP or authenticated user). They require a real, configured email backend for delivery. Staff subscriber records include `is_active`, `confirmation_sent_at`, `confirmed_at` and `unsubscribed_at`; only confirmed addresses are active. A migration deactivates legacy subscribers without recorded confirmation. Email delivery is synchronous and has no durable retry queue; see [DEPLOYMENT.md](DEPLOYMENT.md).

Coupon codes accepted through the API are normalized to uppercase and unique case-insensitively. A pending unpaid order prevents its coupon from being renamed or deleted; deactivate the code instead. `used_count` includes reserved uses as well as completed uses, and cancellation of an unpaid reservation decrements it. A paid refund does not automatically restore coupon usage.

## Other operational details

For an inventory adjustment, send e.g. `{"product_id": 12, "variant_id": null, "expected_stock": 5, "new_stock": 7, "reason": "Physical count"}`. HTTP 409 means another operation changed stock; reload before retrying. Product/variant stock may be supplied on creation, but updates to existing stock must use this endpoint.

For customer status changes send `{"expected_active": true, "is_active": false}`; stale state returns HTTP 409. Deactivation blocks the account and revokes existing access/refresh sessions. Orders shown in the customer view belong to that account; guest orders are not linked by email.

A checkout key must be a random UUID4. Treat it as a secret: it authorizes guest cancellation and must not appear in URLs or logs. A cancellation request is `{"idempotency_key": "<your checkout UUID>"}`. Unknown or unresolved provider state never releases stock automatically. See [PAYMENTS.md](PAYMENTS.md).

Cookies are scoped to `/api/v1/auth/`. Call `GET /auth/csrf/` then send the `csrftoken` cookie value in `X-CSRFToken` for login, refresh and logout. Never send card data to ELVAA.
