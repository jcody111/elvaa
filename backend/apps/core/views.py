from datetime import timedelta
from django.conf import settings
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from apps.accounts.permissions import role_perm
from apps.orders.models import Order
from apps.catalog.models import Product
from apps.accounts.models import User
from .models import StoreSettings,AuditLog
class StoreSettingsSerializer(serializers.ModelSerializer):
    class Meta: model=StoreSettings; fields=['store_name','currency','tax_rate','shipping_flat','free_shipping_threshold']
    def validate_currency(self,value):
        if value != 'EUR': raise serializers.ValidationError('Only EUR is currently supported.')
        return value
class StoreSettingsResponseSerializer(StoreSettingsSerializer):
    manual_checkout_enabled=serializers.BooleanField(read_only=True)
    stripe_checkout_enabled=serializers.BooleanField(read_only=True)
    class Meta(StoreSettingsSerializer.Meta):
        fields=StoreSettingsSerializer.Meta.fields+['manual_checkout_enabled','stripe_checkout_enabled']

class HealthResponseSerializer(serializers.Serializer):
    status=serializers.CharField()
    service=serializers.CharField()

class RevenueTrendSerializer(serializers.Serializer):
    day=serializers.DateField()
    total=serializers.FloatField()

class RecentOrderStatsSerializer(serializers.Serializer):
    id=serializers.IntegerField()
    order_number=serializers.CharField()
    total=serializers.FloatField()
    status=serializers.CharField()
    payment_status=serializers.CharField()
    created_at=serializers.DateTimeField()

class DashboardStatsSerializer(serializers.Serializer):
    revenue_last_30d=serializers.CharField()
    total_orders=serializers.IntegerField()
    pending_orders=serializers.IntegerField()
    completed_orders=serializers.IntegerField()
    total_customers=serializers.IntegerField()
    total_products=serializers.IntegerField()
    low_stock=serializers.IntegerField()
    revenue_trend=RevenueTrendSerializer(many=True)
    recent_orders=RecentOrderStatsSerializer(many=True)

@extend_schema(responses=HealthResponseSerializer)
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request): return Response({'status':'ok','service':'ELVAA API'})
@extend_schema(responses=DashboardStatsSerializer)
@api_view(['GET'])
@permission_classes([role_perm('reports')])
def dashboard_stats(request):
    last30=timezone.now()-timedelta(days=30)
    paid=Order.objects.filter(payment_status='paid')
    revenue=paid.filter(created_at__gte=last30).aggregate(total=Sum('total'))['total'] or 0
    trend=list(paid.filter(created_at__gte=last30).annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('total')).order_by('day'))
    return Response({'revenue_last_30d':str(revenue),'total_orders':Order.objects.count(),
        'pending_orders':Order.objects.filter(status='pending').count(),'completed_orders':Order.objects.filter(status__in=['delivered','completed']).count(),
        'total_customers':User.objects.filter(role='customer').count(),'total_products':Product.objects.count(),
        'low_stock':Product.objects.filter(stock__lte=5,is_active=True).count(), 'revenue_trend':trend,
        'recent_orders':list(Order.objects.order_by('-created_at')[:8].values('id','order_number','total','status','payment_status','created_at'))})
@extend_schema(methods=['GET'],responses=StoreSettingsResponseSerializer)
@extend_schema(methods=['PUT'],request=StoreSettingsSerializer,responses=StoreSettingsResponseSerializer)
@api_view(['GET','PUT'])
@permission_classes([AllowAny])
def store_settings(request):
    s,_=StoreSettings.objects.get_or_create(pk=1)
    if request.method=='PUT':
        if not role_perm('settings')().has_permission(request,None): return Response({'detail':'Forbidden.'},status=403)
        ser=StoreSettingsSerializer(s,data=request.data,partial=True); ser.is_valid(raise_exception=True); ser.save()
        AuditLog.objects.create(user=request.user,action='store_settings_updated',model_name='StoreSettings',object_id=str(s.pk))
    return Response({**StoreSettingsSerializer(s).data,'manual_checkout_enabled':getattr(settings,'ALLOW_DEMO_CHECKOUT',False),'stripe_checkout_enabled':getattr(settings,'STRIPE_ENABLED',False)})
