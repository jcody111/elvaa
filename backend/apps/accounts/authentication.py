from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class VersionedJWTAuthentication(JWTAuthentication):
    """Invalidate already-issued access tokens when the account version changes."""
    def get_user(self,validated_token):
        user=super().get_user(validated_token)
        # Old tokens without this claim are compatible only with version zero.
        if validated_token.get('auth_version',0)!=user.auth_version:
            raise AuthenticationFailed('Session has been revoked.',code='session_revoked')
        return user
