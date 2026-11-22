from urllib.parse import urlsplit, parse_qs
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import User, Address

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user=User.objects.create_user(username='alice',email='alice@example.com',password='CedarHills!5729')
        self.client=APIClient(enforce_csrf_checks=True)
    def test_registration_validates_password_and_forces_customer_role(self):
        weak=self.client.post('/api/v1/auth/register/',{'username':'bob','email':'bob@example.com','password':'12345678','role':'super_admin'},format='json')
        self.assertEqual(weak.status_code,400)
        good=self.client.post('/api/v1/auth/register/',{'username':'bob','email':'bob@example.com','password':'StrongMountain!5729','role':'super_admin','is_staff':True},format='json')
        self.assertEqual(good.status_code,201)
        bob=User.objects.get(username='bob'); self.assertEqual(bob.role,'customer'); self.assertFalse(bob.is_staff)
        self.assertNotEqual(bob.password,'StrongMountain!5729')
    def test_user_cannot_escalate_own_privileges(self):
        self.client.force_authenticate(self.user)
        r=self.client.patch('/api/v1/auth/me/',{'role':'super_admin','is_staff':True,'is_superuser':True,'first_name':'Alice'},format='json')
        self.assertEqual(r.status_code,200); self.user.refresh_from_db()
        self.assertEqual(self.user.role,'customer'); self.assertFalse(self.user.is_staff); self.assertFalse(self.user.is_superuser)
        self.assertEqual(self.user.first_name,'Alice')
    def test_cookie_login_rotation_csrf_and_logout(self):
        self.client.get('/api/v1/auth/csrf/')
        csrf=self.client.cookies['csrftoken'].value
        body={'username':'alice','password':'CedarHills!5729'}
        self.assertEqual(self.client.post('/api/v1/auth/login/',body,format='json').status_code,403)
        login=self.client.post('/api/v1/auth/login/',body,format='json',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(login.status_code,200); self.assertIn('access',login.data); self.assertNotIn('refresh',login.data)
        self.assertTrue(login.cookies['elvaa_refresh']['httponly'])
        old=self.client.cookies['elvaa_refresh'].value
        self.assertEqual(self.client.post('/api/v1/auth/refresh/',{},format='json').status_code,403)
        rotated=self.client.post('/api/v1/auth/refresh/',{},format='json',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(rotated.status_code,200); self.assertNotEqual(old,self.client.cookies['elvaa_refresh'].value)
        stale=APIClient(enforce_csrf_checks=True);stale.get('/api/v1/auth/csrf/');stale.cookies['elvaa_refresh']=old
        r=stale.post('/api/v1/auth/refresh/',{},format='json',HTTP_X_CSRFTOKEN=stale.cookies['csrftoken'].value)
        self.assertEqual(r.status_code,401)
        current=self.client.cookies['elvaa_refresh'].value
        logout=self.client.post('/api/v1/auth/logout/',{},format='json',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(logout.status_code,204)
        stale.cookies['elvaa_refresh']=current
        r=stale.post('/api/v1/auth/refresh/',{},format='json',HTTP_X_CSRFTOKEN=stale.cookies['csrftoken'].value)
        self.assertEqual(r.status_code,401)
    def test_password_reset_sends_generic_response_and_changes_password(self):
        r=self.client.post('/api/v1/auth/forgot-password/',{'email':'alice@example.com'},format='json')
        self.assertEqual(r.status_code,200); self.assertEqual(len(mail.outbox),1)
        link=mail.outbox[0].body.split()[-1]; params=parse_qs(urlsplit(link).query)
        reset=self.client.post('/api/v1/auth/reset-password/',{'uid':params['uid'][0],'token':params['token'][0],'password':'FreshMountain!6329'},format='json')
        self.assertEqual(reset.status_code,200); self.user.refresh_from_db(); self.assertTrue(self.user.check_password('FreshMountain!6329'))
        again=self.client.post('/api/v1/auth/reset-password/',{'uid':params['uid'][0],'token':params['token'][0],'password':'FreshMountain!6329'},format='json')
        self.assertEqual(again.status_code,400)
    def test_password_change_revokes_existing_access_and_refresh_tokens(self):
        self.client.get('/api/v1/auth/csrf/');csrf=self.client.cookies['csrftoken'].value
        login=self.client.post('/api/v1/auth/login/',{'username':'alice','password':'CedarHills!5729'},format='json',HTTP_X_CSRFTOKEN=csrf)
        access=login.data['access'];self.client.credentials(HTTP_AUTHORIZATION='Bearer '+access)
        changed=self.client.post('/api/v1/auth/change-password/',{'current_password':'CedarHills!5729','new_password':'NewForest!6329'},format='json')
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code,401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/v1/auth/refresh/',{},format='json',HTTP_X_CSRFTOKEN=csrf).status_code,401)
        self.user.refresh_from_db();self.assertEqual(self.user.auth_version,1)

    def test_addresses_are_scoped_to_owner(self):
        other=User.objects.create_user(username='other',email='other@example.com',password='CedarHills!5729')
        a=Address.objects.create(user=other,full_name='Other',street='One Street',city='Berlin',postal_code='10115',country='Germany')
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(f'/api/v1/auth/addresses/{a.id}/').status_code,404)
        r=self.client.get('/api/v1/auth/addresses/');self.assertEqual(r.data['count'],0)


class CustomerAdministrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.customer=User.objects.create_user(username='buyer',email='buyer@example.com',password='CedarHills!5729')
        self.manager=User.objects.create_user(username='store-manager',email='store-manager@example.com',password='CedarHills!5729',role='store_admin')
        self.other_staff=User.objects.create_user(username='order-manager',email='orders@example.com',password='CedarHills!5729',role='order_manager')
        self.client=APIClient()

    def test_customer_list_history_and_totals_are_role_scoped(self):
        from apps.orders.models import Order
        from decimal import Decimal
        Order.objects.create(user=self.customer,email=self.customer.email,total=Decimal('42.00'),status='paid',payment_status='paid')
        Order.objects.create(user=self.customer,email=self.customer.email,total=Decimal('10.00'),status='pending',payment_status='unpaid')
        Order.objects.create(user=None,email=self.customer.email,total=Decimal('90.00'),status='paid',payment_status='paid')
        self.client.force_authenticate(self.other_staff)
        self.assertEqual(self.client.get('/api/v1/auth/admin/users/').status_code,403)
        self.assertEqual(self.client.get(f'/api/v1/auth/admin/users/{self.customer.id}/orders/').status_code,403)
        self.client.force_authenticate(self.manager)
        r=self.client.get('/api/v1/auth/admin/users/',{'search':'buyer@example.com'})
        self.assertEqual(r.status_code,200);self.assertEqual(r.data['count'],1)
        self.assertEqual(r.data['results'][0]['order_count'],2);self.assertEqual(r.data['results'][0]['paid_order_value'],'42.00')
        orders=self.client.get(f'/api/v1/auth/admin/users/{self.customer.id}/orders/')
        self.assertEqual(orders.data['count'],2)
        self.assertEqual(self.client.get(f'/api/v1/auth/admin/users/{self.manager.id}/').status_code,404)

    def test_deactivation_blocks_active_access_and_blacklists_refresh(self):
        customer_client=APIClient(enforce_csrf_checks=True)
        customer_client.get('/api/v1/auth/csrf/');csrf=customer_client.cookies['csrftoken'].value
        login=customer_client.post('/api/v1/auth/login/',{'username':'buyer','password':'CedarHills!5729'},format='json',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(login.status_code,200);access=login.data['access']
        customer_client.credentials(HTTP_AUTHORIZATION='Bearer '+access)
        self.assertEqual(customer_client.get('/api/v1/auth/me/').status_code,200)
        self.client.force_authenticate(self.manager)
        path=f'/api/v1/auth/admin/users/{self.customer.id}/status/'
        r=self.client.post(path,{'expected_active':True,'is_active':False},format='json')
        self.assertEqual(r.status_code,200);self.assertFalse(r.data['is_active'])
        self.assertEqual(customer_client.get('/api/v1/auth/me/').status_code,401)
        customer_client.credentials()
        self.assertEqual(customer_client.post('/api/v1/auth/refresh/',{},format='json',HTTP_X_CSRFTOKEN=csrf).status_code,401)
        self.assertEqual(self.client.post(path,{'expected_active':True,'is_active':False},format='json').status_code,409)
        self.assertEqual(self.client.post(path,{'expected_active':False,'is_active':True},format='json').status_code,200)
        self.assertEqual(customer_client.post('/api/v1/auth/refresh/',{},format='json',HTTP_X_CSRFTOKEN=csrf).status_code,401)
        customer_client.credentials(HTTP_AUTHORIZATION='Bearer '+access)
        self.assertEqual(customer_client.get('/api/v1/auth/me/').status_code,401)
        customer_client.credentials()
        relogin=customer_client.post('/api/v1/auth/login/',{'username':'buyer','password':'CedarHills!5729'},format='json',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(relogin.status_code,200)
        from apps.core.models import AuditLog
        self.assertEqual(AuditLog.objects.filter(action='customer_status_changed',object_id=str(self.customer.id)).count(),2)

    def test_customer_tools_cannot_change_staff_or_self_escalate(self):
        self.client.force_authenticate(self.customer)
        path=f'/api/v1/auth/admin/users/{self.customer.id}/status/'
        self.assertEqual(self.client.post(path,{'expected_active':True,'is_active':False},format='json').status_code,403)
        self.client.force_authenticate(self.manager)
        staff_path=f'/api/v1/auth/admin/users/{self.other_staff.id}/status/'
        self.assertEqual(self.client.post(staff_path,{'expected_active':True,'is_active':False},format='json').status_code,404)
        self.other_staff.refresh_from_db();self.assertTrue(self.other_staff.is_active)
        self.assertEqual(self.client.patch(f'/api/v1/auth/admin/users/{self.customer.id}/',{'role':'super_admin'},format='json').status_code,405)

    def test_django_admin_deactivation_and_password_form_revoke_sessions(self):
        from django.contrib import admin
        from types import SimpleNamespace
        from .admin import UserAdmin,RevokingAdminPasswordChangeForm
        admin_user=User.objects.create_superuser(username='super-test',email='super-test@example.com',password='CedarHills!5729')
        target=User.objects.get(pk=self.customer.pk);target.is_active=False
        UserAdmin(User,admin.site).save_model(SimpleNamespace(user=admin_user),target,None,True)
        target.refresh_from_db();self.assertEqual((target.is_active,target.auth_version),(False,1))
        target.is_active=True;target.save(update_fields=['is_active'])
        form=RevokingAdminPasswordChangeForm(target,{'password1':'FreshForest!6329','password2':'FreshForest!6329','usable_password':'true'})
        self.assertTrue(form.is_valid(),form.errors)
        form.save();target.refresh_from_db()
        self.assertEqual(target.auth_version,2);self.assertTrue(target.check_password('FreshForest!6329'))
