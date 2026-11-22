"""Conservative Stripe reconciliation. Never release an ambiguous reservation."""
from collections import Counter
from datetime import timedelta
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Order,Payment
from .payments import get_payment_provider,PaymentProviderError
from .payment_state import PaymentStateError,validate_session,apply_session_event

logger=logging.getLogger(__name__)


def reconcile_stripe_order(order_id,expire_open=False):
    """Retrieve authoritative state without holding database locks across network calls.

    Only a validated, provider-confirmed expired session releases stock. Open,
    asynchronous, unknown, and failed retrievals remain reserved. An explicit
    customer cancellation may request Stripe to expire an open session first.
    """
    order=Order.objects.filter(pk=order_id,payment_method='stripe').first()
    if not order: raise PaymentStateError('Order not found.')
    payment=Payment.objects.filter(order=order,provider='stripe').first()
    if not payment: raise PaymentStateError('Payment not found.')
    if order.status=='payment_review': return 'review'
    if order.status=='cancelled': return 'cancelled'
    if order.payment_status!='unpaid': return 'paid' if order.payment_status=='paid' else 'review'
    if order.status!='pending': return 'review'
    if not payment.checkout_session_id: return 'unknown'
    provider=get_payment_provider('stripe')
    session=provider.retrieve_checkout(payment.checkout_session_id)
    validate_session(order,payment,session)
    if expire_open and session.get('status')=='open':
        try:
            session=provider.expire_checkout(payment.checkout_session_id,order.checkout_key)
        except PaymentProviderError:
            # Expiration can race a completed payment or time out. Ask Stripe;
            # if that is also unavailable we retain the reservation.
            session=provider.retrieve_checkout(payment.checkout_session_id)
        validate_session(order,payment,session)
    session_status=session.get('status');payment_status=session.get('payment_status')
    if session_status=='expired' and payment_status=='unpaid':
        event_type='checkout.session.expired'
    elif session_status=='complete' and payment_status=='paid':
        event_type='checkout.session.completed'
    elif session_status in ('open','complete') and payment_status=='unpaid':
        return 'open' if session_status=='open' else 'async_pending'
    else:
        raise PaymentStateError('Unexpected provider session state.')
    with transaction.atomic():
        current,_=apply_session_event(event_type,session,source='reconciliation')
        if current.status=='cancelled': return 'cancelled'
        if current.status=='payment_review': return 'review'
        if current.payment_status=='paid': return 'paid'
        return 'pending'


def reconcile_stale_stripe_orders(limit=100):
    """Process a bounded, fair batch of known old sessions; report unknowns."""
    if not settings.STRIPE_ENABLED: return {'disabled':1}
    cutoff=timezone.now()-timedelta(minutes=65)
    base=Payment.objects.filter(provider='stripe',status='pending',order__payment_method='stripe',
        order__status='pending',order__payment_status='unpaid',order__created_at__lte=cutoff)
    unknown=base.filter(checkout_session_id='').count()
    result=Counter(unknown=unknown)
    for payment in base.exclude(checkout_session_id='').order_by('updated_at','id')[:limit]:
        try:
            result[reconcile_stripe_order(payment.order_id)]+=1
        except (PaymentProviderError,PaymentStateError) as exc:
            result['error']+=1
            logger.warning('Stripe reconciliation needs attention for order %s: %s',payment.order.order_number,type(exc).__name__)
        finally:
            # Rotate unsuccessful/open sessions to the back of the next batch.
            Payment.objects.filter(pk=payment.pk).update(updated_at=timezone.now())
    if unknown:
        logger.warning('%s stale Stripe reservation(s) have no known session ID; manual investigation required.',unknown)
    return dict(result)
