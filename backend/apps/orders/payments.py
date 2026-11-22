"""Hosted payment provider boundary. Card details never pass through ELVAA."""
from abc import ABC, abstractmethod
from urllib.parse import urlparse, quote
import stripe
from django.conf import settings

class PaymentProviderError(Exception):
    pass

class PaymentProvider(ABC):
    @abstractmethod
    def create_checkout(self,order):
        """Return (external session id, hosted URL); use order.checkout_key for retries."""
        raise NotImplementedError

class StripeHostedCheckout(PaymentProvider):
    def create_checkout(self,order):
        if not settings.STRIPE_ENABLED or not order.checkout_key:
            raise PaymentProviderError('Stripe is not configured.')
        try:
            session=stripe.checkout.Session.create(
                api_key=settings.STRIPE_SECRET_KEY,
                idempotency_key=str(order.checkout_key),
                mode='payment',
                customer_email=order.email,
                client_reference_id=order.order_number,
                expires_at=int(order.created_at.timestamp())+3600,
                metadata={'order_id':str(order.id),'order_number':order.order_number},
                payment_intent_data={'metadata':{'order_id':str(order.id),'order_number':order.order_number}},
                line_items=[{'price_data':{'currency':'eur','product_data':{'name':f'ELVAA order {order.order_number}'},
                                            'unit_amount':int(order.total*100)},'quantity':1}],
                success_url=f"{settings.FRONTEND_URL}/checkout/success?order={quote(order.order_number)}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/checkout/cancel?order={quote(order.order_number)}",
            )
            url=session.url; session_id=session.id
        except Exception as exc:
            raise PaymentProviderError('Unable to initialize hosted checkout.') from exc
        parsed=urlparse(url or '')
        if parsed.scheme!='https' or parsed.hostname!='checkout.stripe.com' or not session_id:
            raise PaymentProviderError('Invalid hosted checkout response.')
        return session_id,url

    def retrieve_checkout(self,session_id):
        if not settings.STRIPE_ENABLED or not session_id:
            raise PaymentProviderError('Stripe session is unavailable.')
        try:
            return stripe.checkout.Session.retrieve(session_id,api_key=settings.STRIPE_SECRET_KEY).to_dict()
        except Exception as exc:
            raise PaymentProviderError('Unable to retrieve hosted checkout.') from exc

    def expire_checkout(self,session_id,checkout_key):
        if not settings.STRIPE_ENABLED or not session_id or not checkout_key:
            raise PaymentProviderError('Stripe session is unavailable.')
        try:
            return stripe.checkout.Session.expire(session_id,api_key=settings.STRIPE_SECRET_KEY,
                idempotency_key=f'cancel-{checkout_key}').to_dict()
        except Exception as exc:
            raise PaymentProviderError('Unable to expire hosted checkout.') from exc

def get_payment_provider(name):
    if name=='stripe': return StripeHostedCheckout()
    raise PaymentProviderError('Unsupported payment provider.')
