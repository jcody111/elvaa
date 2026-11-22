# Payments and reconciliation

ELVAA offers an **optional Stripe-hosted Checkout adapter**. Card details are entered on Stripe's hosted page, never collected or stored by ELVAA. Stripe is disabled unless both `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are configured on the backend. The separate `ALLOW_DEMO_CHECKOUT=True` option creates explicitly **unpaid** demo orders; leave it off for a live store.

**No real Stripe account, test-mode payment or live transaction has been exercised in this workspace.** Provider calls are mocked in automated tests and signed webhook handling is tested locally. Do not enable live payments until you have verified the entire integration and business/legal requirements.

## Configure and verify in test mode

1. Put Stripe test secrets and `FRONTEND_URL=https://shop.example.com` in backend secret storage. Do not put secrets in frontend variables, source control or chat.
2. Configure Stripe to send signed events to `https://api.example.com/api/v1/payments/stripe/webhook/`: `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired` and `charge.refunded`.
3. Run a Celery worker and **exactly one** Celery beat scheduler against the same Redis broker. The included Compose reference defines both; external deployments must provide them independently. The scheduled task runs every five minutes and considers pending Stripe orders at least 65 minutes old. A local command is available: `python manage.py reconcile_stripe_orders --limit 100` (up to 1,000 per run).
4. Test successful payment, retries, browser abandonment, session expiry, cancellation races, delayed/asynchronous methods, duplicate and out-of-order webhooks, partial/full refunds, provider outages and webhook delivery recovery using Stripe test mode. Verify order, stock, coupon, payment and audit records against Stripe.

## Lifecycle and safeguards

- Checkout recalculates totals and atomically reserves stock. A UUID4 checkout key is used both for idempotent retries and as a **secret cancellation capability**; keep it out of URLs and logs. A signed-in order can only be cancelled by that account. The hosted session is configured to expire about one hour after order creation.
- The browser accepts only HTTPS `checkout.stripe.com` redirects. It does not create a fresh checkout after an ambiguous prior attempt until the prior unpaid session is confirmed cancelled.
- The cancellation endpoint asks Stripe to expire an open session; stock is released only after authenticated provider confirmation of expiration or a verified failure event. A completed payment is recorded rather than cancelled. An asynchronous payment still processing remains reserved.
- Signed events and API reconciliation validate session, order metadata, EUR currency and total. Events are idempotent. A late successful payment after stock release becomes `payment_review`; refunds update payment status monotonically and **do not** automatically restock returned items.
- Staff can use **Recheck payment** on a pending Stripe order without expiring an open session. Provider refunds are still initiated in Stripe, not in the ELVAA dashboard.

## Operational limitations

- The scheduled job checks only sessions whose Stripe session ID is recorded. A timeout during session creation can leave a reservation with **no known session ID**; it is reported in logs and left reserved. Investigate the order number/metadata in Stripe and reconcile manually. Never release stock merely because a network call timed out.
- Open sessions, delayed payments, unexpected provider data and provider outages remain reserved for a later retry or manual investigation. The job is deliberately conservative, not a complete abandoned-cart or dispute-management system. Monitor its logs and alerts; a disabled/missing worker or scheduler means no automatic reconciliation.
- Stripe idempotency, simultaneous browser tabs, webhook ordering and operational recovery still require real-provider testing. A late payment or inconsistent state needs a documented manual `payment_review`/refund procedure; there is no dashboard override.
- The hosted checkout uses one aggregate order amount. VAT is an estimate, not jurisdiction-aware tax. Shipping/returns, invoices, order emails, fraud controls, accounting and consumer-law compliance require separate implementation and review.
