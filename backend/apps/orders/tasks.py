from celery import shared_task
from .reconciliation import reconcile_stale_stripe_orders


@shared_task(ignore_result=True)
def reconcile_stale_payments():
    return reconcile_stale_stripe_orders(limit=100)
