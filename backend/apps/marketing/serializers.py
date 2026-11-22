import re
from rest_framework import serializers
from .models import Coupon,NewsletterSubscriber,Banner,ContactMessage
class CouponSerializer(serializers.ModelSerializer):
    class Meta: model=Coupon; fields='__all__'; read_only_fields=['used_count']
    def validate_code(self,value):
        value=value.strip().upper()
        if len(value)>50 or not re.fullmatch(r'[A-Z0-9_-]+',value):
            raise serializers.ValidationError('Use letters, numbers, hyphens or underscores.')
        duplicates=Coupon.objects.filter(code__iexact=value)
        if self.instance: duplicates=duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists(): raise serializers.ValidationError('This code already exists.')
        return value
    def validate(self,data):
        kind=data.get('discount_type',getattr(self.instance,'discount_type',None)); value=data.get('discount_value',getattr(self.instance,'discount_value',0))
        if kind=='percent' and value>100: raise serializers.ValidationError({'discount_value':'Percentage cannot exceed 100.'})
        return data
class NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model=NewsletterSubscriber
        fields=['id','email','is_active','confirmation_sent_at','confirmed_at','unsubscribed_at','created_at']
        read_only_fields=['id','is_active','confirmation_sent_at','confirmed_at','unsubscribed_at','created_at']
        extra_kwargs={'email':{'validators':[]}}
    def validate_email(self,value): return value.strip().lower()

class NewsletterTokenSerializer(serializers.Serializer):
    token=serializers.CharField(max_length=2048)

class NewsletterDetailSerializer(serializers.Serializer):
    detail=serializers.CharField()
class BannerSerializer(serializers.ModelSerializer):
    class Meta: model=Banner; fields='__all__'
class ContactSerializer(serializers.ModelSerializer):
    class Meta: model=ContactMessage; fields=['name','email','subject','message']
