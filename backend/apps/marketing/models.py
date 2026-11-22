from django.db import models
from django.db.models.functions import Lower
from django.core.validators import MinValueValidator
import uuid
class Coupon(models.Model):
    code=models.CharField(max_length=50,unique=True)
    discount_type=models.CharField(max_length=20,choices=[('percent','Percent'),('fixed','Fixed amount')])
    discount_value=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0)])
    minimum_order=models.DecimalField(max_digits=10,decimal_places=2,default=0,validators=[MinValueValidator(0)])
    is_active=models.BooleanField(default=True)
    expires_at=models.DateTimeField(null=True,blank=True)
    usage_limit=models.PositiveIntegerField(null=True,blank=True)
    used_count=models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[models.UniqueConstraint(Lower('code'),name='coupon_code_case_insensitive_unique')]
    def save(self,*args,**kwargs):
        self.code=self.code.strip().upper()
        super().save(*args,**kwargs)
    def __str__(self): return self.code
class NewsletterSubscriber(models.Model):
    email=models.EmailField(unique=True)
    is_active=models.BooleanField(default=False)
    confirmation_nonce=models.UUIDField(default=uuid.uuid4,editable=False)
    confirmation_sent_at=models.DateTimeField(null=True,blank=True)
    confirmed_at=models.DateTimeField(null=True,blank=True)
    unsubscribed_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
class Banner(models.Model):
    title=models.CharField(max_length=255)
    subtitle=models.CharField(max_length=255,blank=True)
    image=models.ImageField(upload_to='banners/',blank=True,null=True)
    link=models.CharField(max_length=500,blank=True)
    position=models.CharField(max_length=50,default='hero')
    is_active=models.BooleanField(default=True)
    display_order=models.PositiveIntegerField(default=0)
class ContactMessage(models.Model):
    name=models.CharField(max_length=120)
    email=models.EmailField()
    subject=models.CharField(max_length=200,blank=True)
    message=models.TextField(max_length=5000)
    created_at=models.DateTimeField(auto_now_add=True)
    is_resolved=models.BooleanField(default=False)
    class Meta: ordering=['-created_at']
