from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer,TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class VersionedTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls,user):
        token=super().get_token(user)
        token['auth_version']=user.auth_version
        return token


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self,attrs):
        token=RefreshToken(attrs['refresh'])
        User=get_user_model()
        try:
            user=User.objects.get(pk=token.get('user_id'),is_active=True)
        except (User.DoesNotExist,ValueError,TypeError):
            raise InvalidToken('Session is no longer active.')
        if token.get('auth_version',0)!=user.auth_version:
            raise InvalidToken('Session has been revoked.')
        try:
            return super().validate(attrs)
        except User.DoesNotExist:
            raise InvalidToken('Session is no longer active.')
