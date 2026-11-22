import stripe
from django.conf import settings
from django.db import transaction,IntegrityError
from rest_framework.decorators import api_view,authentication_classes,permission_classes,throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema,OpenApiResponse,OpenApiParameter
from .models import PaymentEvent
from .payment_state import PaymentStateError,apply_session_event,apply_refund_event


@extend_schema(request=None,parameters=[OpenApiParameter('Stripe-Signature',str,OpenApiParameter.HEADER,required=True)],responses={200:OpenApiResponse(description='Webhook accepted'),400:OpenApiResponse(description='Invalid signature or inconsistent payment')},description='Stripe-signed webhook. Configure the endpoint secret on the server.')
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([])
def stripe_webhook(request):
    if not settings.STRIPE_ENABLED: return Response({'detail':'Payment provider not configured.'},status=503)
    signature=request.headers.get('Stripe-Signature','')
    try: event=stripe.Webhook.construct_event(request.body,signature,settings.STRIPE_WEBHOOK_SECRET).to_dict()
    except (ValueError,stripe.SignatureVerificationError): return Response({'detail':'Invalid webhook signature.'},status=400)
    event_id=event.get('id');event_type=event.get('type');data=event.get('data')
    obj=data.get('object') if isinstance(data,dict) else None
    if not event_id or not event_type or not isinstance(obj,dict): return Response({'detail':'Invalid event.'},status=400)
    if PaymentEvent.objects.filter(event_id=event_id).exists(): return Response({'received':True})
    try:
        with transaction.atomic():
            if event_type in ('checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.expired','checkout.session.async_payment_failed'):
                apply_session_event(event_type,obj,event_id=event_id)
            elif event_type=='charge.refunded':
                apply_refund_event(obj,event_id=event_id)
            PaymentEvent.objects.create(event_id=event_id,event_type=event_type)
    except PaymentStateError as exc:
        return Response({'detail':str(exc)},status=400)
    except IntegrityError:
        # Concurrent duplicate delivery: all writes in the losing transaction roll back.
        if PaymentEvent.objects.filter(event_id=event_id).exists(): return Response({'received':True})
        raise
    return Response({'received':True})
