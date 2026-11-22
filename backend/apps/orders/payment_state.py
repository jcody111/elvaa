"""Apply validated provider state while holding a consistent order/payment lock order."""
from decimal import Decimal
from django.db import transaction
from apps.core.models import AuditLog
from .models import Order, Payment
from .services import release_unpaid_reservation


class PaymentStateError(Exception):
    pass


def validate_session(order, payment, session):
    if not isinstance(session, dict):
        raise PaymentStateError('Invalid payment session.')
    meta=session.get('metadata') or {}
    if not isinstance(meta, dict) or str(meta.get('order_id'))!=str(order.pk) or meta.get('order_number')!=order.order_number:
        raise PaymentStateError('Payment reference mismatch.')
    session_id=session.get('id')
    if not isinstance(session_id,str) or not session_id or session.get('client_reference_id')!=order.order_number:
        raise PaymentStateError('Payment reference mismatch.')
    if payment.checkout_session_id and payment.checkout_session_id!=session_id:
        raise PaymentStateError('Payment session mismatch.')
    if (session.get('currency') or '').lower()!='eur' or session.get('amount_total')!=int(order.total*100):
        raise PaymentStateError('Payment amount mismatch.')


def apply_session_event(event_type, session, event_id='', source='webhook'):
    """Apply a signed event or an authenticated Stripe API retrieval.

    Call inside transaction.atomic(). Only provider-confirmed expiration releases
    stock; an asynchronous payment that is still pending does not.
    """
    meta=session.get('metadata') or {} if isinstance(session,dict) else {}
    order_id=meta.get('order_id') if isinstance(meta,dict) else None
    try:
        order=Order.objects.select_for_update().get(pk=order_id,payment_method='stripe')
    except (Order.DoesNotExist,ValueError,TypeError):
        raise PaymentStateError('Order not found.')
    payment=Payment.objects.select_for_update().filter(order=order,provider='stripe').first()
    if not payment:
        raise PaymentStateError('Payment not found.')
    validate_session(order,payment,session)
    payment_status=session.get('payment_status')
    if payment_status not in ('paid','unpaid'):
        raise PaymentStateError('Invalid payment status.')
    if not payment.checkout_session_id:
        payment.checkout_session_id=session['id']
        payment.save(update_fields=['checkout_session_id','updated_at'])
    if event_type in ('checkout.session.expired','checkout.session.async_payment_failed'):
        if payment_status!='unpaid':
            raise PaymentStateError('Paid session cannot release its reservation.')
        if release_unpaid_reservation(order,'Payment session expired'):
            payment.status='expired';payment.save(update_fields=['status','updated_at'])
    elif event_type in ('checkout.session.completed','checkout.session.async_payment_succeeded') and payment_status=='paid' and order.payment_status=='unpaid':
        intent=session.get('payment_intent')
        if not isinstance(intent,str) or not intent:
            raise PaymentStateError('Invalid payment intent.')
        # Paid after a prior release (or an inconsistent state) requires manual review.
        order.status='paid' if order.status=='pending' else 'payment_review'
        order.payment_status='paid';order.save(update_fields=['status','payment_status','updated_at'])
        payment.status='paid';payment.transaction_id=intent
        payment.save(update_fields=['status','transaction_id','updated_at'])
        AuditLog.objects.create(action='stripe_payment_confirmed',model_name='Order',object_id=str(order.pk),details={'event_id':event_id,'source':source})
    return order,payment


def apply_refund_event(charge,event_id=''):
    """Apply monotonic refund state; never automatically return stock."""
    intent=charge.get('payment_intent') if isinstance(charge,dict) else None
    identity=Payment.objects.filter(provider='stripe',transaction_id=intent).values('pk','order_id').first() if isinstance(intent,str) and intent else None
    if not identity:
        if isinstance(charge,dict) and (charge.get('metadata') or {}).get('order_id'):
            raise PaymentStateError('Payment not yet recorded.')
        return
    # Session and refund handling both lock Order first, then Payment.
    order=Order.objects.select_for_update().get(pk=identity['order_id'])
    payment=Payment.objects.select_for_update().get(pk=identity['pk'])
    if payment.transaction_id!=intent or payment.status not in ('paid','partially_refunded','refunded'):
        raise PaymentStateError('Payment not yet confirmed.')
    if (charge.get('currency') or '').lower()!='eur' or charge.get('amount')!=int(payment.amount*100):
        raise PaymentStateError('Refund amount mismatch.')
    cents=charge.get('amount_refunded',0)
    if not isinstance(cents,int) or isinstance(cents,bool) or cents<0 or cents>int(payment.amount*100):
        raise PaymentStateError('Invalid refunded amount.')
    refunded=Decimal(cents)/100
    if refunded>payment.amount_refunded:
        fully_refunded=refunded==payment.amount
        payment.amount_refunded=refunded;payment.status='refunded' if fully_refunded else 'partially_refunded'
        payment.save(update_fields=['amount_refunded','status','updated_at'])
        order.payment_status=payment.status
        if fully_refunded: order.status='refunded'
        order.save(update_fields=['status','payment_status','updated_at'])
        AuditLog.objects.create(action='stripe_refund_recorded',model_name='Order',object_id=str(order.pk),details={'event_id':event_id})
