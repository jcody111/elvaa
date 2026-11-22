"""Double-opt-in newsletter links. Secrets stay out of server URL query logs."""
import logging
from urllib.parse import quote
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from .models import NewsletterSubscriber

logger=logging.getLogger(__name__)
CONFIRM_SALT='elvaa-newsletter-confirm-v1'
UNSUBSCRIBE_SALT='elvaa-newsletter-unsubscribe-v1'


def confirmation_token(subscriber):
    return signing.dumps({'id':subscriber.pk,'nonce':str(subscriber.confirmation_nonce)},salt=CONFIRM_SALT,compress=True)


def unsubscribe_token(subscriber):
    return signing.dumps({'id':subscriber.pk,'email':subscriber.email},salt=UNSUBSCRIBE_SALT,compress=True)


def confirmation_url(subscriber):
    return f"{settings.FRONTEND_URL}/newsletter/confirm#token={quote(confirmation_token(subscriber),safe='')}"


def unsubscribe_url(subscriber):
    return f"{settings.FRONTEND_URL}/newsletter/unsubscribe#token={quote(unsubscribe_token(subscriber),safe='')}"


def send_confirmation(subscriber_id,nonce):
    subscriber=NewsletterSubscriber.objects.filter(pk=subscriber_id,is_active=False,confirmation_nonce=nonce).first()
    if not subscriber: return
    try:
        delivered=send_mail('Confirm your ELVAA newsletter subscription',
            f"Please confirm that you want to receive ELVAA emails by opening this link and pressing Confirm:\n\n{confirmation_url(subscriber)}\n\nThis link expires in 48 hours. If you did not request this, you can ignore this email.",
            settings.DEFAULT_FROM_EMAIL,[subscriber.email],fail_silently=True)
    except Exception as exc:
        logger.warning('Newsletter confirmation email failed for subscriber %s: %s',subscriber_id,type(exc).__name__)
        return
    if not delivered: logger.warning('Newsletter confirmation email could not be delivered for subscriber %s',subscriber_id)


def send_welcome(subscriber_id,nonce):
    subscriber=NewsletterSubscriber.objects.filter(pk=subscriber_id,is_active=True,confirmation_nonce=nonce).first()
    if not subscriber: return
    try:
        delivered=send_mail('You are subscribed to ELVAA',
            f"Your newsletter subscription is confirmed. You can unsubscribe at any time:\n\n{unsubscribe_url(subscriber)}",
            settings.DEFAULT_FROM_EMAIL,[subscriber.email],fail_silently=True)
    except Exception as exc:
        logger.warning('Newsletter welcome email failed for subscriber %s: %s',subscriber_id,type(exc).__name__)
        return
    if not delivered: logger.warning('Newsletter welcome email could not be delivered for subscriber %s',subscriber_id)
