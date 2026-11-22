from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from .choices import ORDER_STATUSES
import uuid
class ShippingMethod(models.Model):
    name=models.CharField(max_length=120)
    price=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0)])
    estimated_days=models.CharField(max_length=50,blank=True)
    is_active=models.BooleanField(default=True)
    free_over_threshold=models.BooleanField(default=False)
    def __str__(self): return self.name
class Order(models.Model):
    STATUS=ORDER_STATUSES
    order_number=models.CharField(max_length=32,unique=True,editable=False)
    checkout_key=models.UUIDField(unique=True,null=True,blank=True,editable=False)
    request_fingerprint=models.CharField(max_length=64,blank=True,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='orders')
    email=models.EmailField()
    status=models.CharField(max_length=20,choices=STATUS,default='pending')
    subtotal=models.DecimalField(max_digits=12,decimal_places=2,default='0')
    discount=models.DecimalField(max_digits=12,decimal_places=2,default='0')
    shipping=models.DecimalField(max_digits=12,decimal_places=2,default='0')
    tax=models.DecimalField(max_digits=12,decimal_places=2,default='0',help_text='Tax included in total')
    total=models.DecimalField(max_digits=12,decimal_places=2,default='0')
    shipping_address=models.JSONField(default=dict,blank=True)
    billing_address=models.JSONField(default=dict,blank=True)
    shipping_method=models.ForeignKey(ShippingMethod,on_delete=models.SET_NULL,null=True,blank=True)
    coupon_code=models.CharField(max_length=50,blank=True)
    payment_method=models.CharField(max_length=50,default='manual')
    payment_status=models.CharField(max_length=20,default='unpaid')
    tracking_number=models.CharField(max_length=100,blank=True)
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-created_at']; indexes=[models.Index(fields=['status','created_at'])]
    def save(self,*args,**kwargs):
        if not self.order_number: self.order_number='ELV-'+uuid.uuid4().hex[:10].upper()
        super().save(*args,**kwargs)
    def __str__(self): return self.order_number
class OrderItem(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    product=models.ForeignKey('catalog.Product',on_delete=models.SET_NULL,null=True,blank=True)
    variant=models.ForeignKey('catalog.ProductVariant',on_delete=models.SET_NULL,null=True,blank=True)
    name=models.CharField(max_length=255)
    variant_name=models.CharField(max_length=120,blank=True)
    sku=models.CharField(max_length=64,blank=True)
    quantity=models.PositiveIntegerField(default=1)
    unit_price=models.DecimalField(max_digits=10,decimal_places=2)
    total=models.DecimalField(max_digits=12,decimal_places=2)
class Payment(models.Model):
    order=models.ForeignKey(Order,on_delete=models.CASCADE,related_name='payments')
    provider=models.CharField(max_length=50,default='manual')
    amount=models.DecimalField(max_digits=12,decimal_places=2)
    amount_refunded=models.DecimalField(max_digits=12,decimal_places=2,default='0')
    status=models.CharField(max_length=30,default='pending')
    transaction_id=models.CharField(max_length=120,blank=True)
    checkout_session_id=models.CharField(max_length=255,blank=True)
    checkout_url=models.CharField(max_length=1000,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class PaymentEvent(models.Model):
    provider=models.CharField(max_length=30,default='stripe')
    event_id=models.CharField(max_length=255,unique=True)
    event_type=models.CharField(max_length=120)
    processed_at=models.DateTimeField(auto_now_add=True)
