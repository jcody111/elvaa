import json
from django.core.management.base import BaseCommand,CommandError
from apps.orders.reconciliation import reconcile_stale_stripe_orders


class Command(BaseCommand):
    help='Reconcile a bounded batch of stale Stripe sessions; ambiguous sessions remain reserved.'

    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=100,help='Maximum known sessions to check (1–1000).')

    def handle(self,*args,**options):
        limit=options['limit']
        if not 1<=limit<=1000: raise CommandError('Limit must be between 1 and 1000.')
        self.stdout.write(json.dumps(reconcile_stale_stripe_orders(limit=limit),sort_keys=True))
