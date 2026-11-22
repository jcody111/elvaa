from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.db import transaction
from django.db.models import Count, Sum, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from rest_framework import viewsets, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, throttle_classes, action
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken
from .permissions import role_perm
from .serializers import (RegisterSerializer, UserSerializer, AddressSerializer, CustomerAdminSerializer, CustomerStatusSerializer,
    DetailResponseSerializer,CsrfResponseSerializer,LoginRequestSerializer,LoginResponseSerializer,RefreshRequestSerializer,
    EmailRequestSerializer,ResetPasswordRequestSerializer,VerifyEmailRequestSerializer,ChangePasswordRequestSerializer)
from .tokens import VersionedTokenObtainPairSerializer, VersionedTokenRefreshSerializer
from .security import blacklist_refresh_tokens
from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.core.models import AuditLog
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from .models import Address
User=get_user_model()

def set_refresh_cookie(response,token):
    response.set_cookie(settings.JWT_COOKIE_NAME,token,max_age=7*24*60*60,httponly=True,
                        secure=settings.JWT_COOKIE_SECURE,samesite='Lax',path=settings.JWT_COOKIE_PATH)
    return response

def send_verification(user):
    token=signing.dumps({'id':user.pk,'email':user.email},salt='elvaa-email-verification')
    link=f'{settings.FRONTEND_URL}/verify-email?token={token}'
    send_mail('Verify your ELVAA email',f'Please verify your email: {link}',settings.DEFAULT_FROM_EMAIL,[user.email],fail_silently=True)

class RegisterView(generics.CreateAPIView):
    queryset=User.objects.all(); serializer_class=RegisterSerializer; permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    def perform_create(self, serializer):
        user=serializer.save()
        transaction.on_commit(lambda: send_verification(user))

@method_decorator(csrf_protect,name='dispatch')
class LoginView(TokenObtainPairView):
    serializer_class=VersionedTokenObtainPairSerializer
    throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=LoginRequestSerializer,responses={200:LoginResponseSerializer},description='Returns an access token and sets an HttpOnly refresh cookie. CSRF header required.')
    def post(self,request,*args,**kwargs):
        response=super().post(request,*args,**kwargs)
        if response.status_code==200:
            refresh=response.data.pop('refresh')
            user=User.objects.get(username=request.data.get('username',''))
            response.data['user']=UserSerializer(user).data
            set_refresh_cookie(response,refresh)
        return response

@method_decorator(csrf_protect,name='dispatch')
class CookieRefreshView(TokenRefreshView):
    serializer_class=VersionedTokenRefreshSerializer
    throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=RefreshRequestSerializer,responses={200:LoginResponseSerializer},description='Rotate the refresh cookie and return a new access token. CSRF header required.')
    def post(self,request,*args,**kwargs):
        refresh=request.COOKIES.get(settings.JWT_COOKIE_NAME) or request.data.get('refresh')
        if not refresh: return Response({'detail':'No refresh token.'},status=401)
        serializer=self.get_serializer(data={'refresh':refresh})
        try: serializer.is_valid(raise_exception=True)
        except TokenError as exc: raise InvalidToken(str(exc))
        data=serializer.validated_data
        access=data['access']
        try:
            user_id=RefreshToken(data.get('refresh',refresh)).get('user_id')
            user=User.objects.get(pk=user_id,is_active=True)
        except (TokenError,User.DoesNotExist): return Response({'detail':'Session expired.'},status=401)
        response=Response({'access':access,'user':UserSerializer(user).data})
        if data.get('refresh'): set_refresh_cookie(response,data['refresh'])
        return response

@method_decorator(csrf_protect,name='dispatch')
class LogoutView(APIView):
    permission_classes=[AllowAny]
    @extend_schema(request=None,responses={204:None},description='Blacklist the refresh cookie and clear it. CSRF header required.')
    def post(self,request):
        token=request.COOKIES.get(settings.JWT_COOKIE_NAME)
        if token:
            try: RefreshToken(token).blacklist()
            except TokenError: pass
        response=Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.JWT_COOKIE_NAME,path=settings.JWT_COOKIE_PATH,samesite='Lax')
        return response

@extend_schema(responses=CsrfResponseSerializer,description='Set a CSRF cookie and report whether a refresh cookie is present.')
@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request): return Response({'detail':'CSRF cookie set','has_session':bool(request.COOKIES.get(settings.JWT_COOKIE_NAME))})

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class=UserSerializer; permission_classes=[IsAuthenticated]
    def get_object(self): return self.request.user

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class=AddressSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        if not self.request.user.is_authenticated: return Address.objects.none()
        return Address.objects.filter(user=self.request.user)
    @transaction.atomic
    def perform_create(self,serializer):
        if serializer.validated_data.get('is_default'): Address.objects.filter(user=self.request.user,is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)
    @transaction.atomic
    def perform_update(self,serializer):
        if serializer.validated_data.get('is_default'): Address.objects.filter(user=self.request.user,is_default=True).exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()

class UserAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=CustomerAdminSerializer
    permission_classes=[role_perm('customers')]; search_fields=['username','email','first_name','last_name']

    def get_queryset(self):
        # Staff accounts and superusers cannot be managed through the customer tools.
        return User.objects.filter(role='customer',is_staff=False,is_superuser=False).annotate(
            order_count=Count('orders',distinct=True),
            paid_order_value=Coalesce(Sum('orders__total',filter=Q(orders__payment_status='paid')),
                Value(Decimal('0.00')),output_field=DecimalField(max_digits=14,decimal_places=2))
        ).order_by('-date_joined','-id')

    @extend_schema(responses=OrderSerializer(many=True),description='Orders attached to this customer account; guest orders are not linked by email.')
    @action(detail=True,methods=['get'],url_path='orders')
    def orders(self,request,pk=None):
        customer=self.get_object()
        orders=Order.objects.filter(user=customer).prefetch_related('items').order_by('-created_at','-id')
        page=self.paginate_queryset(orders)
        if page is not None: return self.get_paginated_response(OrderSerializer(page,many=True).data)
        return Response(OrderSerializer(orders,many=True).data)

    @extend_schema(request=CustomerStatusSerializer,responses={200:CustomerAdminSerializer,409:OpenApiResponse(description='Customer status changed since it was observed.')})
    @action(detail=True,methods=['post'],url_path='status')
    def status(self,request,pk=None):
        serializer=CustomerStatusSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        data=serializer.validated_data
        if not str(pk).isdigit(): return Response({'detail':'Customer not found.'},status=404)
        with transaction.atomic():
            user=User.objects.select_for_update().filter(pk=pk,role='customer',is_staff=False,is_superuser=False).first()
            if not user: return Response({'detail':'Customer not found.'},status=404)
            if user.is_active!=data['expected_active']:
                return Response({'detail':'Customer status changed. Refresh before making another change.'},status=409)
            if user.is_active!=data['is_active']:
                old=user.is_active;user.is_active=data['is_active']
                fields=['is_active']
                if not user.is_active:
                    user.auth_version+=1;fields.append('auth_version')
                user.save(update_fields=fields)
                if not user.is_active: blacklist_refresh_tokens(user)
                AuditLog.objects.create(user=request.user,action='customer_status_changed',model_name='User',object_id=str(user.pk),details={'from':old,'to':user.is_active})
        return Response(CustomerAdminSerializer(self.get_queryset().get(pk=user.pk)).data)

class ForgotPasswordView(APIView):
    permission_classes=[AllowAny]; throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=EmailRequestSerializer,responses=DetailResponseSerializer)
    def post(self,request):
        email=str(request.data.get('email','')).strip()
        user=User.objects.filter(email__iexact=email,is_active=True).first()
        if user:
            uid=urlsafe_base64_encode(force_bytes(user.pk)); token=default_token_generator.make_token(user)
            link=f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
            send_mail('Reset your ELVAA password',f'Reset your password using this link: {link}',settings.DEFAULT_FROM_EMAIL,[user.email],fail_silently=True)
        return Response({'detail':'If an account exists, a reset link has been sent.'})

class ResetPasswordView(APIView):
    permission_classes=[AllowAny]; throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=ResetPasswordRequestSerializer,responses=DetailResponseSerializer)
    def post(self,request):
        token=request.data.get('token','');password=request.data.get('password','')
        if not isinstance(token,str) or not isinstance(password,str) or len(password)>128:
            return Response({'detail':'Invalid reset request.'},status=400)
        try: user_id=force_str(urlsafe_base64_decode(request.data.get('uid','')))
        except Exception: return Response({'detail':'Invalid or expired link.'},status=400)
        with transaction.atomic():
            try: user=User.objects.select_for_update().get(pk=user_id,is_active=True)
            except (User.DoesNotExist,ValueError,TypeError): return Response({'detail':'Invalid or expired link.'},status=400)
            if not default_token_generator.check_token(user,token): return Response({'detail':'Invalid or expired link.'},status=400)
            try: password_validation.validate_password(password,user)
            except Exception as e: return Response({'detail':list(e.messages)},status=400)
            user.set_password(password);user.auth_version+=1;user.save(update_fields=['password','auth_version'])
            blacklist_refresh_tokens(user)
        return Response({'detail':'Password updated.'})

class VerifyEmailView(APIView):
    permission_classes=[AllowAny]; throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=VerifyEmailRequestSerializer,responses=DetailResponseSerializer)
    def post(self,request):
        try:
            payload=signing.loads(request.data.get('token',''),salt='elvaa-email-verification',max_age=60*60*24*3)
            user=User.objects.get(pk=payload['id'],email=payload['email'])
        except (signing.BadSignature,User.DoesNotExist,KeyError): return Response({'detail':'Invalid or expired verification link.'},status=400)
        user.email_verified=True; user.save(update_fields=['email_verified'])
        return Response({'detail':'Email verified.'})

class ChangePasswordView(APIView):
    permission_classes=[IsAuthenticated]
    throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=ChangePasswordRequestSerializer,responses=DetailResponseSerializer)
    def post(self,request):
        current=request.data.get('current_password','');password=request.data.get('new_password','')
        if not isinstance(current,str) or not isinstance(password,str) or len(password)>128 or len(current)>128:
            return Response({'detail':'Invalid password request.'},status=400)
        with transaction.atomic():
            user=User.objects.select_for_update().filter(pk=request.user.pk,is_active=True).first()
            if not user: return Response({'detail':'Session is no longer active.'},status=401)
            if not user.check_password(current):
                return Response({'current_password':['Current password is incorrect.']},status=400)
            try: password_validation.validate_password(password,user)
            except Exception as e: return Response({'new_password':list(e.messages)},status=400)
            user.set_password(password);user.auth_version+=1;user.save(update_fields=['password','auth_version'])
            blacklist_refresh_tokens(user)
        return Response({'detail':'Password updated. Please sign in again.'})

class SendVerificationView(APIView):
    permission_classes=[IsAuthenticated]
    throttle_classes=[ScopedRateThrottle]; throttle_scope='auth'
    @extend_schema(request=None,responses=DetailResponseSerializer)
    def post(self,request):
        if not request.user.email_verified: send_verification(request.user)
        return Response({'detail':'If verification is needed, an email has been sent.'})
