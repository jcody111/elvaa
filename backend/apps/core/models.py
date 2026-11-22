from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator,MaxValueValidator
class AuditLog(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    action=models.CharField(max_length=100)
    model_name=models.CharField(max_length=100,blank=True)
    object_id=models.CharField(max_length=100,blank=True)
    details=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']
class StoreSettings(models.Model):
    store_name=models.CharField(max_length=120,default='ELVAA')
    currency=models.CharField(max_length=10,default='EUR')
    tax_rate=models.DecimalField(max_digits=5,decimal_places=2,default='19.00',validators=[MinValueValidator(0),MaxValueValidator(100)])
    shipping_flat=models.DecimalField(max_digits=10,decimal_places=2,default='6.90',validators=[MinValueValidator(0)])
    free_shipping_threshold=models.DecimalField(max_digits=10,decimal_places=2,default='150.00',validators=[MinValueValidator(0)])
    updated_at=models.DateTimeField(auto_now=True)
