import time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
from django.core import mail,signing
from django.core.cache import cache
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.core.models import AuditLog
from .models import NewsletterSubscriber,ContactMessage
from .newsletters import CONFIRM_SALT,confirmation_token,unsubscribe_token


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',FRONTEND_URL='https://shop.example.com')
class MarketingTests(TestCase):
    def setUp(self): cache.clear();self.client=APIClient()

    def test_newsletter_requires_confirmation_and_can_unsubscribe(self):
        with self.captureOnCommitCallbacks(execute=True):
            first=self.client.post('/api/v1/newsletter/',{'email':'TEST@example.com'},format='json')
            second=self.client.post('/api/v1/newsletter/',{'email':'test@example.com'},format='json')
        self.assertEqual((first.status_code,second.status_code),(200,200));self.assertEqual(first.data,second.data)
        subscriber=NewsletterSubscriber.objects.get(email='test@example.com')
        self.assertFalse(subscriber.is_active);self.assertEqual(len(mail.outbox),1)
        link=mail.outbox[0].body.split('https://shop.example.com')[1].split()[0]
        self.assertIn('/newsletter/confirm#token=',link)
        token=parse_qs(urlsplit('https://shop.example.com'+link).fragment)['token'][0]
        with self.captureOnCommitCallbacks(execute=True):
            confirmed=self.client.post('/api/v1/newsletter/confirm/',{'token':token},format='json')
            repeated=self.client.post('/api/v1/newsletter/confirm/',{'token':token},format='json')
        self.assertEqual((confirmed.status_code,repeated.status_code),(200,200))
        subscriber.refresh_from_db();self.assertTrue(subscriber.is_active);self.assertIsNotNone(subscriber.confirmed_at)
        self.assertEqual(len(mail.outbox),2);self.assertEqual(AuditLog.objects.filter(action='newsletter_confirmed').count(),1)
        self.assertIn('/newsletter/unsubscribe#token=',mail.outbox[1].body)
        unsubscribe=unsubscribe_token(subscriber)
        self.assertEqual(self.client.post('/api/v1/newsletter/unsubscribe/',{'token':unsubscribe},format='json').status_code,200)
        self.assertEqual(self.client.post('/api/v1/newsletter/unsubscribe/',{'token':unsubscribe},format='json').status_code,200)
        subscriber.refresh_from_db();self.assertFalse(subscriber.is_active);self.assertIsNotNone(subscriber.unsubscribed_at)
        self.assertEqual(self.client.post('/api/v1/newsletter/confirm/',{'token':token},format='json').status_code,400)
        self.assertEqual(AuditLog.objects.filter(action='newsletter_unsubscribed').count(),1)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post('/api/v1/newsletter/',{'email':'test@example.com'},format='json').status_code,200)
        subscriber.refresh_from_db();self.assertFalse(subscriber.is_active);self.assertEqual(len(mail.outbox),3)
        self.assertNotEqual(confirmation_token(subscriber),token)

    def test_newsletter_invalid_expired_links_and_private_staff_tools(self):
        subscriber=NewsletterSubscriber.objects.create(email='pending@example.com')
        with patch('django.core.signing.time.time',return_value=time.time()-timedelta(days=3).total_seconds()):
            expired=signing.dumps({'id':subscriber.pk,'nonce':str(subscriber.confirmation_nonce)},salt=CONFIRM_SALT,compress=True)
        self.assertEqual(self.client.post('/api/v1/newsletter/confirm/',{'token':expired},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/v1/newsletter/unsubscribe/',{'token':'forged'},format='json').status_code,400)
        self.assertIn(self.client.get('/api/v1/newsletter/').status_code,[401,403])
        staff=User.objects.create_user(username='marketing',email='marketing@example.com',password='CedarHills!5729',role='content_manager')
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.get('/api/v1/newsletter/').status_code,200)
        self.assertEqual(self.client.patch(f'/api/v1/newsletter/{subscriber.pk}/',{'is_active':True},format='json').status_code,405)
        self.assertEqual(self.client.post(f'/api/v1/newsletter/{subscriber.pk}/unsubscribe/',{},format='json').status_code,200)
        subscriber.refresh_from_db();self.assertFalse(subscriber.is_active)

    def test_newsletter_confirmation_email_failure_does_not_activate(self):
        with patch('apps.marketing.newsletters.send_mail',return_value=0):
            with self.captureOnCommitCallbacks(execute=True):
                r=self.client.post('/api/v1/newsletter/',{'email':'offline@example.com'},format='json')
        self.assertEqual(r.status_code,200);self.assertFalse(NewsletterSubscriber.objects.get(email='offline@example.com').is_active)

    def test_coupon_codes_are_unique_case_insensitively_and_pending_reservations_are_protected(self):
        from django.db import IntegrityError,transaction
        from apps.orders.models import Order
        from .models import Coupon
        staff=User.objects.create_user(username='promo',email='promo@example.com',password='CedarHills!5729',role='content_manager')
        self.client.force_authenticate(staff)
        created=self.client.post('/api/v1/coupons/',{'code':'welcome','discount_type':'percent','discount_value':'10'},format='json')
        self.assertEqual(created.status_code,201);self.assertEqual(created.data['code'],'WELCOME')
        self.assertEqual(self.client.post('/api/v1/coupons/',{'code':'WeLcOmE','discount_type':'percent','discount_value':'5'},format='json').status_code,400)
        with self.assertRaises(IntegrityError):
            with transaction.atomic(): Coupon.objects.bulk_create([Coupon(code='welcome',discount_type='percent',discount_value='5')])
        order=Order.objects.create(email='buyer@example.com',coupon_code='WELCOME',status='pending',payment_status='unpaid')
        url=f'/api/v1/coupons/{created.data["id"]}/'
        self.assertEqual(self.client.patch(url,{'code':'NEWCODE'},format='json').status_code,400)
        self.assertEqual(self.client.delete(url).status_code,400)
        self.assertEqual(self.client.patch(url,{'is_active':False},format='json').status_code,200)
        order.status='cancelled';order.save(update_fields=['status'])
        self.assertEqual(self.client.patch(url,{'code':'NEWCODE'},format='json').status_code,200)
        self.assertEqual(self.client.delete(url).status_code,204)

    def test_coupon_update_rechecks_cross_field_rules_against_the_locked_row(self):
        from types import SimpleNamespace
        from rest_framework.exceptions import ValidationError
        from .models import Coupon
        from .serializers import CouponSerializer
        from .views import CouponViewSet
        staff=User.objects.create_user(username='promo2',email='promo2@example.com',password='CedarHills!5729',role='content_manager')
        coupon=Coupon.objects.create(code='SAFE',discount_type='fixed',discount_value='50')
        coupon.refresh_from_db()
        serializer=CouponSerializer(coupon,data={'discount_type':'percent'},partial=True)
        self.assertTrue(serializer.is_valid(),serializer.errors)
        # Simulate a different request committing after serializer validation.
        Coupon.objects.filter(pk=coupon.pk).update(discount_value='120')
        view=CouponViewSet();view.request=SimpleNamespace(user=staff)
        with self.assertRaises(ValidationError): view.perform_update(serializer)
        coupon.refresh_from_db()
        self.assertEqual((coupon.discount_type,str(coupon.discount_value)),('fixed','120.00'))

    def test_demo_seed_preserves_an_existing_code_with_different_case(self):
        from io import StringIO
        from django.core.management import call_command
        from .models import Coupon
        Coupon.objects.bulk_create([Coupon(code='welcome10',discount_type='percent',discount_value='7')])
        call_command('seed',stdout=StringIO())
        self.assertEqual(Coupon.objects.filter(code__iexact='WELCOME10').count(),1)
        self.assertEqual(str(Coupon.objects.get(code='welcome10').discount_value),'7.00')

    def test_coupon_django_admin_is_read_only(self):
        from django.contrib import admin
        from .models import Coupon
        model_admin=admin.site._registry[Coupon]
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))

    def test_contact_persists_valid_message(self):
        r=self.client.post('/api/v1/contact/',{'name':'Customer','email':'c@example.com','message':'Hello'},format='json')
        self.assertEqual(r.status_code,201);self.assertEqual(ContactMessage.objects.count(),1)
        self.assertIn(self.client.get('/api/v1/contact/').status_code,[401,403])
