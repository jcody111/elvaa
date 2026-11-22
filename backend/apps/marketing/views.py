import uuid
from datetime import timedelta
from django.core import signing
from django.db import transaction,IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets,status,mixins
from rest_framework.decorators import api_view,permission_classes,throttle_classes,action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema,OpenApiResponse
from apps.accounts.permissions import role_perm,user_has_perm
from apps.core.models import AuditLog
from apps.orders.models import Order
from .models import Coupon,NewsletterSubscriber,Banner,ContactMessage
from .serializers import (CouponSerializer,NewsletterSerializer,BannerSerializer,ContactSerializer,
                          NewsletterTokenSerializer,NewsletterDetailSerializer)
from .newsletters import CONFIRM_SALT,UNSUBSCRIBE_SALT,send_confirmation,send_welcome


class CouponViewSet(viewsets.ModelViewSet):
    queryset=Coupon.objects.all().order_by('code'); serializer_class=CouponSerializer; permission_classes=[role_perm('marketing')]
    search_fields=['code']

    def perform_create(self,serializer):
        try:
            with transaction.atomic():
                coupon=serializer.save()
                AuditLog.objects.create(user=self.request.user,action='coupon_created',model_name='Coupon',object_id=str(coupon.pk))
        except IntegrityError:
            raise ValidationError({'code':'This code already exists.'})

    def perform_update(self,serializer):
        try:
            with transaction.atomic():
                coupon=get_object_or_404(Coupon.objects.select_for_update(),pk=serializer.instance.pk)
                new_code=serializer.validated_data.get('code',coupon.code)
                if new_code.casefold()!=coupon.code.casefold() and Order.objects.filter(coupon_code__iexact=coupon.code,status='pending',payment_status='unpaid').exists():
                    raise ValidationError({'code':'A code with pending reservations cannot be renamed.'})
                # Recheck cross-field rules against the locked, current row: another
                # request may have changed a different field since validation.
                kind=serializer.validated_data.get('discount_type',coupon.discount_type)
                value=serializer.validated_data.get('discount_value',coupon.discount_value)
                if kind=='percent' and value>100:
                    raise ValidationError({'discount_value':'Percentage cannot exceed 100.'})
                serializer.instance=coupon;coupon=serializer.save()
                AuditLog.objects.create(user=self.request.user,action='coupon_updated',model_name='Coupon',object_id=str(coupon.pk))
        except IntegrityError:
            raise ValidationError({'code':'This code already exists.'})

    @transaction.atomic
    def perform_destroy(self,instance):
        coupon=get_object_or_404(Coupon.objects.select_for_update(),pk=instance.pk)
        if Order.objects.filter(coupon_code__iexact=coupon.code,status='pending',payment_status='unpaid').exists():
            raise ValidationError({'detail':'This code has pending reservations. Deactivate it instead.'})
        AuditLog.objects.create(user=self.request.user,action='coupon_deleted',model_name='Coupon',object_id=str(coupon.pk))
        coupon.delete()


class NewsletterViewSet(mixins.CreateModelMixin,mixins.ListModelMixin,mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    queryset=NewsletterSubscriber.objects.all().order_by('-created_at','-id')
    serializer_class=NewsletterSerializer
    search_fields=['email']
    def get_permissions(self): return [AllowAny()] if self.action=='create' else [role_perm('marketing')()]
    def get_throttles(self):
        if self.action=='create':
            self.throttle_scope='newsletter'
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @extend_schema(request=NewsletterSerializer,responses={200:NewsletterDetailSerializer},description='Request double opt-in. The response is the same for existing and new addresses.')
    def create(self,request,*args,**kwargs):
        serializer=self.get_serializer(data=request.data);serializer.is_valid(raise_exception=True)
        email=serializer.validated_data['email']
        with transaction.atomic():
            subscriber=NewsletterSubscriber.objects.select_for_update().filter(email__iexact=email).first()
            if not subscriber:
                subscriber,_=NewsletterSubscriber.objects.select_for_update().get_or_create(email=email,defaults={'is_active':False})
            now=timezone.now()
            if not subscriber.is_active and (not subscriber.confirmation_sent_at or subscriber.confirmation_sent_at<=now-timedelta(minutes=5)):
                subscriber.confirmation_nonce=uuid.uuid4();subscriber.confirmation_sent_at=now
                subscriber.save(update_fields=['confirmation_nonce','confirmation_sent_at'])
                transaction.on_commit(lambda sid=subscriber.pk,nonce=subscriber.confirmation_nonce:send_confirmation(sid,nonce))
        return Response({'detail':'If eligible, please check your inbox for a confirmation link.'})

    @extend_schema(operation_id='newsletter_staff_unsubscribe',request=None,responses=NewsletterDetailSerializer,description='Marketing staff may unsubscribe an address; only the recipient can confirm a new subscription.')
    @action(detail=True,methods=['post'],url_path='unsubscribe')
    def staff_unsubscribe(self,request,pk=None):
        candidate=self.get_object()
        with transaction.atomic():
            subscriber=NewsletterSubscriber.objects.select_for_update().get(pk=candidate.pk)
            unsubscribe_subscriber(subscriber,actor=request.user)
        return Response({'detail':'Subscriber unsubscribed.'})


def unsubscribe_subscriber(subscriber,actor=None):
    """Caller holds subscriber row lock. Invalidate any outstanding confirmation link."""
    if subscriber.is_active or subscriber.confirmation_sent_at:
        subscriber.is_active=False;subscriber.unsubscribed_at=timezone.now()
        subscriber.confirmation_nonce=uuid.uuid4();subscriber.confirmation_sent_at=None
        subscriber.save(update_fields=['is_active','unsubscribed_at','confirmation_nonce','confirmation_sent_at'])
        AuditLog.objects.create(user=actor,action='newsletter_unsubscribed',model_name='NewsletterSubscriber',object_id=str(subscriber.pk))


@extend_schema(request=NewsletterTokenSerializer,responses={200:NewsletterDetailSerializer,400:OpenApiResponse(description='Invalid or expired confirmation link')})
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def confirm_newsletter(request):
    serializer=NewsletterTokenSerializer(data=request.data);serializer.is_valid(raise_exception=True)
    try:
        data=signing.loads(serializer.validated_data['token'],salt=CONFIRM_SALT,max_age=48*60*60)
        subscriber_id=int(data['id']);nonce=uuid.UUID(data['nonce'])
    except (signing.BadSignature,KeyError,TypeError,ValueError):
        return Response({'detail':'This confirmation link is invalid or has expired.'},status=400)
    with transaction.atomic():
        subscriber=NewsletterSubscriber.objects.select_for_update().filter(pk=subscriber_id,confirmation_nonce=nonce).first()
        if not subscriber: return Response({'detail':'This confirmation link is invalid or has expired.'},status=400)
        if not subscriber.is_active:
            subscriber.is_active=True;subscriber.confirmed_at=timezone.now();subscriber.confirmation_sent_at=None
            subscriber.save(update_fields=['is_active','confirmed_at','confirmation_sent_at'])
            AuditLog.objects.create(action='newsletter_confirmed',model_name='NewsletterSubscriber',object_id=str(subscriber.pk),details={'method':'email_double_opt_in'})
            transaction.on_commit(lambda sid=subscriber.pk,n=subscriber.confirmation_nonce:send_welcome(sid,n))
    return Response({'detail':'Your newsletter subscription is confirmed.'})
confirm_newsletter.cls.throttle_scope='newsletter'


@extend_schema(request=NewsletterTokenSerializer,responses={200:NewsletterDetailSerializer,400:OpenApiResponse(description='Invalid unsubscribe link')})
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def unsubscribe_newsletter(request):
    serializer=NewsletterTokenSerializer(data=request.data);serializer.is_valid(raise_exception=True)
    try:
        data=signing.loads(serializer.validated_data['token'],salt=UNSUBSCRIBE_SALT)
        subscriber_id=int(data['id']);email=data['email']
        if not isinstance(email,str): raise ValueError()
    except (signing.BadSignature,KeyError,TypeError,ValueError):
        return Response({'detail':'This unsubscribe link is invalid.'},status=400)
    with transaction.atomic():
        subscriber=NewsletterSubscriber.objects.select_for_update().filter(pk=subscriber_id,email=email).first()
        if not subscriber: return Response({'detail':'This unsubscribe link is invalid.'},status=400)
        unsubscribe_subscriber(subscriber)
    return Response({'detail':'You have been unsubscribed from the ELVAA newsletter.'})
unsubscribe_newsletter.cls.throttle_scope='newsletter'


class BannerViewSet(viewsets.ModelViewSet):
    serializer_class=BannerSerializer
    def get_queryset(self): return Banner.objects.all().order_by('display_order') if user_has_perm(self.request.user,'marketing') else Banner.objects.filter(is_active=True).order_by('display_order')
    def get_permissions(self): return [AllowAny()] if self.action in ['list','retrieve'] else [role_perm('marketing')()]


class ContactViewSet(viewsets.ModelViewSet):
    queryset=ContactMessage.objects.all(); serializer_class=ContactSerializer
    throttle_classes=[ScopedRateThrottle]; throttle_scope='contact'
    def get_permissions(self): return [AllowAny()] if self.action=='create' else [role_perm('content')()]
    def create(self,request,*args,**kwargs):
        serializer=self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True); serializer.save()
        return Response({'detail':'Your message has been received.'},status=status.HTTP_201_CREATED)
