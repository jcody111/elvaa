from rest_framework_simplejwt.token_blacklist.models import OutstandingToken,BlacklistedToken


def blacklist_refresh_tokens(user):
    ids=OutstandingToken.objects.filter(user=user).values_list('id',flat=True)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token_id=pk) for pk in ids],ignore_conflicts=True)
