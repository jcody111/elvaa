import hashlib
import json
import logging
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import F
from django.utils import timezone
from rest_framework import viewsets,status,filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.decorators import api_view,permission_classes,throttle_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema,OpenApiResponse
from apps.accounts.permissions import role_perm,user_has_perm
from apps.core.models import AuditLog
from apps.catalog.models import Product,ProductVariant,InventoryMovement
from apps.marketing.models import Coupon
from .models import Order,OrderItem,ShippingMethod,Payment
from .serializers import OrderSerializer,ShippingMethodSerializer,QuoteSerializer,CheckoutSerializer,QuoteResponseSerializer,CheckoutResponseSerializer,OrderStatusUpdateSerializer,CheckoutCancelSerializer,CheckoutCancelResponseSerializer,ReconcileResponseSerializer
from .services import calculate_cart,quote_output,release_unpaid_reservation
from .payments import get_payment_provider,PaymentProviderError
from .payment_state import PaymentStateError
from .reconciliation import reconcile_stripe_order
logger=logging.getLogger(__name__)

class ShippingMethodViewSet(viewsets.ModelViewSet):
    serializer_class=ShippingMethodSerializer
    def get_queryset(self): return (ShippingMethod.objects.all() if user_has_perm(self.request.user,'settings') else ShippingMethod.objects.filter(is_active=True)).order_by('price','id')
    def get_permissions(self): return [AllowAny()] if self.action in ['list','retrieve'] else [role_perm('settings')()]
class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=OrderSerializer; permission_classes=[IsAuthenticated]
    filter_backends=[DjangoFilterBackend,filters.SearchFilter,filters.OrderingFilter]
    filterset_fields=['status','payment_status','payment_method']
    search_fields=['order_number','email','items__sku']
    ordering_fields=['created_at','total'];ordering=['-created_at']
    def get_queryset(self):
        qs=Order.objects.prefetch_related('items')
        if not self.request.user.is_authenticated: return qs.none()
        return qs if user_has_perm(self.request.user,'orders') else qs.filter(user=self.request.user)

@extend_schema(request=QuoteSerializer,responses={200:QuoteResponseSerializer},description='Calculate a cart against current database prices and stock without placing an order.')
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def quote(request):
    s=QuoteSerializer(data=request.data);s.is_valid(raise_exception=True)
    return Response(quote_output(calculate_cart(s.validated_data)))
quote.cls.throttle_scope='checkout'

def request_fingerprint(data,user):
    payload={k:v for k,v in data.items() if k!='idempotency_key'}
    payload={'data':payload,'user_id':user.id if user.is_authenticated else None}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()

def reserve_order(data,user,fingerprint):
    """Reserve stock once, with a unique checkout key; never hold DB locks across a gateway call."""
    key=data.get('idempotency_key')
    try:
        with transaction.atomic():
            existing=Order.objects.select_for_update().filter(checkout_key=key).first() if key else None
            if existing: return existing,False
            q=calculate_cart(data,lock=True)
            if data['payment_method']=='stripe' and q['total']<Decimal('0.50'):
                raise ValidationError({'detail':'The order total is below the minimum supported by the payment provider.'})
            order=Order.objects.create(user=user if user.is_authenticated else None,email=data['email'],
                checkout_key=key,request_fingerprint=fingerprint,
                subtotal=q['subtotal'],discount=q['discount'],shipping=q['shipping'],tax=q['tax'],total=q['total'],
                shipping_address=data['shipping_address'],billing_address=data['shipping_address'],shipping_method=q['shipping_method'],
                coupon_code=q['coupon'].code if q['coupon'] else '',payment_method=data['payment_method'],status='pending',payment_status='unpaid')
            for line in q['lines']:
                p=line['product'];v=line['variant'];qty=line['quantity']
                OrderItem.objects.create(order=order,product=p,variant=v,name=p.name,variant_name=v.name if v else '',
                    sku=v.sku if v else p.sku,quantity=qty,unit_price=line['price'],total=line['price']*qty)
                Product.objects.filter(pk=p.pk).update(stock=F('stock')-qty)
                InventoryMovement.objects.create(product=p,quantity_change=-qty,reason='Order reserved',reference=order.order_number,actor=user if user.is_authenticated else None)
                if v:
                    ProductVariant.objects.filter(pk=v.pk).update(stock=F('stock')-qty)
                    InventoryMovement.objects.create(product=p,variant=v,quantity_change=-qty,reason='Order reserved',reference=order.order_number,actor=user if user.is_authenticated else None)
            if q['coupon']: q['coupon'].used_count=F('used_count')+1;q['coupon'].save(update_fields=['used_count'])
            Payment.objects.create(order=order,provider=data['payment_method'],amount=q['total'],status='pending')
            AuditLog.objects.create(user=user if user.is_authenticated else None,action='checkout_created',model_name='Order',object_id=str(order.pk))
            return order,True
    except IntegrityError:
        # A concurrent request may have inserted the same idempotency key.
        if key:
            existing=Order.objects.filter(checkout_key=key).first()
            if existing: return existing,False
        raise

@extend_schema(request=CheckoutSerializer,responses={200:CheckoutResponseSerializer,201:CheckoutResponseSerializer,503:OpenApiResponse(description='Payment provider unavailable')},description='Reserve stock and create either a hosted Stripe session or an explicitly enabled unpaid demo order. Stripe responses additionally include checkout_url.')
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def create_order(request):
    s=CheckoutSerializer(data=request.data);s.is_valid(raise_exception=True);data=s.validated_data
    method=data['payment_method']
    if method=='manual' and not settings.ALLOW_DEMO_CHECKOUT:
        return Response({'detail':'Demo checkout is disabled.'},status=503)
    if method=='stripe' and not settings.STRIPE_ENABLED:
        return Response({'detail':'Payment provider is not configured.'},status=503)
    fingerprint=request_fingerprint(data,request.user)
    order,created=reserve_order(data,request.user,fingerprint)
    if order.request_fingerprint!=fingerprint:
        return Response({'detail':'This checkout key was already used for a different request.'},status=409)
    if order.status in ['cancelled','refunded','payment_review']:
        return Response({'detail':'This checkout session can no longer be used.'},status=409)
    if method=='stripe':
        if order.payment_status not in ('unpaid','paid'):
            return Response({'detail':'This payment requires reconciliation.'},status=409)
        if order.payment_status=='unpaid':
            if timezone.now()>=order.created_at+timedelta(hours=1):
                return Response({'detail':'This checkout is no longer available. Cancel or reconcile it before starting another.'},status=409)
            payment=order.payments.get(provider='stripe')
            if not payment.checkout_url:
                try:
                    # Identical retries use the same Stripe idempotency key; do not hold database locks over the network.
                    session_id,url=get_payment_provider('stripe').create_checkout(order)
                except PaymentProviderError:
                    order.refresh_from_db()
                    if order.payment_status=='paid':
                        return Response(OrderSerializer(order).data,status=status.HTTP_200_OK)
                    logger.warning('Hosted checkout initialization failed for order %s',order.order_number)
                    return Response({'detail':'Payment service unavailable. Please retry this checkout without changing the details.','order_number':order.order_number},status=503)
                with transaction.atomic():
                    order=Order.objects.select_for_update().get(pk=order.pk)
                    payment=Payment.objects.select_for_update().get(pk=payment.pk)
                    if payment.checkout_session_id and payment.checkout_session_id!=session_id:
                        logger.error('Conflicting hosted sessions for order %s',order.order_number)
                        return Response({'detail':'Payment session requires reconciliation.'},status=409)
                    payment.checkout_session_id=session_id;payment.checkout_url=url
                    payment.save(update_fields=['checkout_session_id','checkout_url','updated_at'])
            else:
                order.refresh_from_db();payment.refresh_from_db()
            if order.status in ('cancelled','refunded','payment_review'):
                return Response({'detail':'This checkout session can no longer be used.'},status=409)
            if order.payment_status=='unpaid':
                if timezone.now()>=order.created_at+timedelta(hours=1):
                    return Response({'detail':'This checkout is no longer available. Cancel or reconcile it before starting another.'},status=409)
                output=OrderSerializer(order).data;output['checkout_url']=payment.checkout_url
                return Response(output,status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            if order.payment_status!='paid':
                return Response({'detail':'This payment requires reconciliation.'},status=409)
    return Response(OrderSerializer(order).data,status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
create_order.cls.throttle_scope='checkout'


@extend_schema(request=CheckoutCancelSerializer,responses={200:CheckoutCancelResponseSerializer,409:OpenApiResponse(description='Payment cannot safely be cancelled'),503:OpenApiResponse(description='Provider unavailable')},description='Cancel an unpaid checkout using its secret UUID4 key. Stripe reservations are released only after provider-confirmed expiration.')
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def cancel_checkout(request):
    serializer=CheckoutCancelSerializer(data=request.data);serializer.is_valid(raise_exception=True)
    order=Order.objects.filter(checkout_key=serializer.validated_data['idempotency_key']).first()
    if not order or (order.user_id and (not request.user.is_authenticated or order.user_id!=request.user.id)):
        return Response({'detail':'Checkout not found.'},status=404)
    if order.payment_method=='manual':
        with transaction.atomic():
            order=Order.objects.select_for_update().get(pk=order.pk)
            if order.status=='cancelled': return Response({'status':'cancelled'})
            if not release_unpaid_reservation(order,'Checkout cancelled',request.user if request.user.is_authenticated else None):
                return Response({'detail':'This checkout can no longer be cancelled.'},status=409)
            Payment.objects.filter(order=order,provider='manual',status='pending').update(status='cancelled')
        return Response({'status':'cancelled'})
    if order.payment_method!='stripe' or not settings.STRIPE_ENABLED:
        return Response({'detail':'Payment service is unavailable. Your reservation has not been released.'},status=503)
    try:
        result=reconcile_stripe_order(order.pk,expire_open=True)
    except (PaymentProviderError,PaymentStateError) as exc:
        logger.warning('Checkout cancellation needs reconciliation for order %s: %s',order.order_number,type(exc).__name__)
        return Response({'detail':'Payment state could not be confirmed. Your reservation has not been released; retry or contact support.'},status=503)
    if result=='cancelled': return Response({'status':'cancelled'})
    if result=='paid': return Response({'detail':'Payment has already been confirmed. Contact support before placing another order.'},status=409)
    if result=='unknown': return Response({'detail':'The payment session could not be identified. Contact support before starting another checkout.'},status=409)
    if result=='async_pending': return Response({'detail':'Payment is still processing. Contact support before starting another checkout.'},status=409)
    return Response({'detail':'The payment could not yet be cancelled. Please retry or contact support.'},status=409)
cancel_checkout.cls.throttle_scope='checkout'


@extend_schema(request=None,responses={200:ReconcileResponseSerializer,503:OpenApiResponse(description='Payment provider unavailable')},description='Order manager: retrieve provider state without expiring an open checkout.')
@api_view(['POST'])
@permission_classes([role_perm('orders')])
@throttle_classes([ScopedRateThrottle])
def reconcile_order(request,pk):
    order=Order.objects.filter(pk=pk).first()
    if not order: return Response({'detail':'Order not found.'},status=404)
    if order.payment_method!='stripe': return Response({'detail':'This is not a Stripe order.'},status=400)
    if not settings.STRIPE_ENABLED: return Response({'detail':'Payment service is not configured.'},status=503)
    try:
        result=reconcile_stripe_order(order.pk)
    except (PaymentProviderError,PaymentStateError) as exc:
        logger.warning('Staff reconciliation needs attention for order %s: %s',order.order_number,type(exc).__name__)
        return Response({'detail':'Payment state could not be confirmed. The reservation was not released.'},status=503)
    AuditLog.objects.create(user=request.user,action='stripe_reconciliation_requested',model_name='Order',object_id=str(order.pk),details={'result':result})
    return Response({'result':result})
reconcile_order.cls.throttle_scope='checkout'

ORDER_STATUS_TRANSITIONS={
    'pending':{'pending','cancelled'},
    'paid':{'paid','processing'},
    'processing':{'processing','shipped'},
    'shipped':{'shipped','delivered'},
    'delivered':{'delivered','completed'},
    'completed':{'completed'},
    'cancelled':{'cancelled'},
}

@extend_schema(request=OrderStatusUpdateSerializer,responses={200:OrderSerializer,400:OpenApiResponse(description='Invalid or unsafe order transition')})
@api_view(['POST'])
@permission_classes([role_perm('orders')])
def update_order_status(request,pk):
    serializer=OrderStatusUpdateSerializer(data=request.data);serializer.is_valid(raise_exception=True)
    data=serializer.validated_data;new_status=data['status']
    with transaction.atomic():
        order=Order.objects.select_for_update().filter(pk=pk).first()
        if not order: return Response({'detail':'Order not found.'},status=404)
        if order.status in ('payment_review','refunded'):
            return Response({'detail':'This order requires payment reconciliation and cannot be changed here.'},status=400)
        if new_status not in ORDER_STATUS_TRANSITIONS.get(order.status,set()):
            return Response({'detail':f'Cannot move an order from {order.status} to {new_status}.'},status=400)
        if new_status in ('processing','shipped','delivered','completed') and order.payment_status!='paid':
            return Response({'detail':'An unpaid or refunded order cannot be fulfilled.'},status=400)
        if order.status=='cancelled':
            return Response(OrderSerializer(order).data)
        old=order.status
        if new_status=='cancelled':
            if order.payment_method=='stripe' or order.payment_status!='unpaid':
                return Response({'detail':'Stripe orders must be expired or refunded through the payment provider.'},status=400)
            if not release_unpaid_reservation(order,'Order cancelled',request.user):
                return Response({'detail':'This reservation can no longer be cancelled.'},status=400)
            Payment.objects.filter(order=order,provider='manual',status='pending').update(status='cancelled')
        else:
            order.status=new_status
        if 'tracking_number' in data: order.tracking_number=data['tracking_number']
        order.save(update_fields=['status','tracking_number','updated_at'])
        AuditLog.objects.create(user=request.user,action='order_status_changed',model_name='Order',object_id=str(order.pk),details={'from':old,'to':new_status})
    return Response(OrderSerializer(order).data)
