from rest_framework import serializers
from .models import Order,OrderItem,ShippingMethod,Payment
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta: model=OrderItem; fields=['id','product','variant','name','variant_name','sku','quantity','unit_price','total']
class OrderSerializer(serializers.ModelSerializer):
    items=OrderItemSerializer(many=True,read_only=True)
    class Meta: model=Order; exclude=['checkout_key','request_fingerprint']; read_only_fields=[f.name for f in Order._meta.fields]
class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta: model=ShippingMethod; fields='__all__'
class CartLineSerializer(serializers.Serializer):
    product_id=serializers.IntegerField(min_value=1)
    variant_id=serializers.IntegerField(min_value=1,required=False,allow_null=True)
    quantity=serializers.IntegerField(min_value=1,max_value=20)
class QuoteSerializer(serializers.Serializer):
    items=CartLineSerializer(many=True,allow_empty=False,max_length=40)
    shipping_method_id=serializers.IntegerField(required=False,allow_null=True,min_value=1)
    coupon_code=serializers.CharField(required=False,allow_blank=True,max_length=50,default='')
class ShippingAddressSerializer(serializers.Serializer):
    full_name=serializers.CharField(max_length=120)
    street=serializers.CharField(max_length=255)
    city=serializers.CharField(max_length=120)
    postal_code=serializers.CharField(max_length=20)
    country=serializers.CharField(max_length=120)
class CheckoutSerializer(QuoteSerializer):
    email=serializers.EmailField()
    shipping_address=ShippingAddressSerializer()
    payment_method=serializers.ChoiceField(choices=['manual','stripe'])
    idempotency_key=serializers.UUIDField(required=False)
    def validate(self,attrs):
        key=attrs.get('idempotency_key')
        if attrs.get('payment_method')=='stripe' and not key: raise serializers.ValidationError({'idempotency_key':'A unique checkout key is required.'})
        if key and key.version!=4: raise serializers.ValidationError({'idempotency_key':'Use a randomly generated UUID4 checkout key.'})
        return attrs

class CheckoutCancelSerializer(serializers.Serializer):
    idempotency_key=serializers.UUIDField()
    def validate_idempotency_key(self,value):
        if value.version!=4: raise serializers.ValidationError('Use a randomly generated UUID4 checkout key.')
        return value

class CheckoutCancelResponseSerializer(serializers.Serializer):
    status=serializers.ChoiceField(choices=['cancelled'])

class QuoteLineResponseSerializer(serializers.Serializer):
    product_id=serializers.IntegerField()
    variant_id=serializers.IntegerField(allow_null=True)
    name=serializers.CharField()
    variant=serializers.CharField(allow_blank=True)
    quantity=serializers.IntegerField()
    unit_price=serializers.DecimalField(max_digits=10,decimal_places=2)
class QuoteResponseSerializer(serializers.Serializer):
    items=QuoteLineResponseSerializer(many=True)
    subtotal=serializers.DecimalField(max_digits=12,decimal_places=2)
    discount=serializers.DecimalField(max_digits=12,decimal_places=2)
    shipping=serializers.DecimalField(max_digits=12,decimal_places=2)
    tax_included=serializers.DecimalField(max_digits=12,decimal_places=2)
    total=serializers.DecimalField(max_digits=12,decimal_places=2)
    currency=serializers.CharField()
    shipping_method_id=serializers.IntegerField()

class CheckoutResponseSerializer(OrderSerializer):
    checkout_url=serializers.URLField(required=False,read_only=True,help_text='Present for a pending Stripe-hosted checkout.')
    class Meta(OrderSerializer.Meta): pass

class OrderStatusUpdateSerializer(serializers.Serializer):
    status=serializers.ChoiceField(choices=Order.STATUS)
    tracking_number=serializers.CharField(max_length=100,required=False,allow_blank=True)

class ReconcileResponseSerializer(serializers.Serializer):
    result=serializers.ChoiceField(choices=['cancelled','paid','review','unknown','open','async_pending','pending'])
