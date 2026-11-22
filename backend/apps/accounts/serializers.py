from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Address
User=get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True,trim_whitespace=False)
    class Meta: model=User; fields=['id','username','email','password','first_name','last_name']
    def validate_email(self,value):
        value=value.lower().strip()
        if User.objects.filter(email__iexact=value).exists(): raise serializers.ValidationError('An account with this email already exists.')
        return value
    def validate(self,attrs):
        try: password_validation.validate_password(attrs.get('password'),User(username=attrs.get('username'),email=attrs.get('email')))
        except DjangoValidationError as exc: raise serializers.ValidationError({'password':list(exc.messages)})
        return attrs
    def create(self,validated_data): return User.objects.create_user(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['id','username','email','first_name','last_name','role','phone','is_staff','is_superuser','date_joined','email_verified']
        read_only_fields=['id','username','role','is_staff','is_superuser','date_joined','email_verified']
    def validate_email(self,value):
        value=value.lower().strip()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=value).exists(): raise serializers.ValidationError('Email is already in use.')
        return value
    def update(self,instance,validated_data):
        if 'email' in validated_data and validated_data['email'] != instance.email: instance.email_verified=False
        return super().update(instance,validated_data)

class AddressSerializer(serializers.ModelSerializer):
    class Meta: model=Address; fields='__all__'; read_only_fields=['user']

class CustomerAdminSerializer(serializers.ModelSerializer):
    order_count=serializers.IntegerField(read_only=True)
    paid_order_value=serializers.DecimalField(max_digits=14,decimal_places=2,read_only=True)
    class Meta:
        model=User
        fields=['id','username','email','first_name','last_name','phone','date_joined','email_verified','is_active','order_count','paid_order_value']
        read_only_fields=fields

class CustomerStatusSerializer(serializers.Serializer):
    expected_active=serializers.BooleanField(help_text='Status last observed by the staff member.')
    is_active=serializers.BooleanField()

# Request/response contracts for function-based account endpoints.
class DetailResponseSerializer(serializers.Serializer):
    detail=serializers.CharField()

class CsrfResponseSerializer(DetailResponseSerializer):
    has_session=serializers.BooleanField()

class LoginRequestSerializer(serializers.Serializer):
    username=serializers.CharField()
    password=serializers.CharField(write_only=True,trim_whitespace=False)

class LoginResponseSerializer(serializers.Serializer):
    access=serializers.CharField()
    user=UserSerializer()

class RefreshRequestSerializer(serializers.Serializer):
    refresh=serializers.CharField(required=False,write_only=True,help_text='Optional; normally supplied as an HttpOnly cookie.')

class EmailRequestSerializer(serializers.Serializer):
    email=serializers.EmailField()

class ResetPasswordRequestSerializer(serializers.Serializer):
    uid=serializers.CharField()
    token=serializers.CharField()
    password=serializers.CharField(write_only=True,trim_whitespace=False,max_length=128)

class VerifyEmailRequestSerializer(serializers.Serializer):
    token=serializers.CharField()

class ChangePasswordRequestSerializer(serializers.Serializer):
    current_password=serializers.CharField(write_only=True,trim_whitespace=False,max_length=128)
    new_password=serializers.CharField(write_only=True,trim_whitespace=False,max_length=128)
