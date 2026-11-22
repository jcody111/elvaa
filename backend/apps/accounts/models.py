from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES=[('super_admin','Super Administrator'),('store_admin','Store Administrator'),
                  ('product_manager','Product Manager'),('order_manager','Order Manager'),
                  ('content_manager','Content Manager'),('customer','Customer')]
    email=models.EmailField(unique=True)
    email_verified=models.BooleanField(default=False)
    role=models.CharField(max_length=30,choices=ROLE_CHOICES,default='customer')
    phone=models.CharField(max_length=30,blank=True)
    auth_version=models.PositiveBigIntegerField(default=0,editable=False)
    def __str__(self): return self.username

class Profile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='profile')
    avatar=models.ImageField(upload_to='avatars/',blank=True,null=True)
    bio=models.TextField(blank=True)

class Address(models.Model):
    ADDRESS_TYPES=[('shipping','Shipping'),('billing','Billing')]
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='addresses')
    type=models.CharField(max_length=20,choices=ADDRESS_TYPES,default='shipping')
    full_name=models.CharField(max_length=120)
    street=models.CharField(max_length=255)
    city=models.CharField(max_length=120)
    postal_code=models.CharField(max_length=20)
    country=models.CharField(max_length=120)
    is_default=models.BooleanField(default=False)
    class Meta: ordering=['-is_default','id']
