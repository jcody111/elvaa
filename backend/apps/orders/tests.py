from datetime import timedelta
from django.core.cache import cache
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.catalog.models import Product,ProductVariant
from apps.core.models import StoreSettings
from apps.marketing.models import Coupon
from .models import Order,ShippingMethod

@override_settings(ALLOW_DEMO_CHECKOUT=True)
class CheckoutTests(TestCase):
    def setUp(self):
        cache.clear();self.client=APIClient()
        self.user=User.objects.create_user(username='customer',email='user@example.com',password='CedarHills!5729')
        self.other=User.objects.create_user(username='other',email='other@example.com',password='CedarHills!5729')
        self.manager=User.objects.create_user(username='orders',email='orders@example.com',password='CedarHills!5729',role='order_manager')
        self.product=Product.objects.create(name='Coat',sku='COAT',slug='coat',price='100.00',stock=10,is_active=True)
        self.variant=ProductVariant.objects.create(product=self.product,name='M',sku='COAT-M',stock=10)
        self.shipping=ShippingMethod.objects.create(name='Standard',price='6.90',free_over_threshold=True)
        StoreSettings.objects.create(pk=1,free_shipping_threshold='150.00',tax_rate='19.00')
        self.coupon=Coupon.objects.create(code='WELCOME10',discount_type='percent',discount_value='10.00')
        self.line={'product_id':self.product.id,'variant_id':self.variant.id,'quantity':1}
        self.address={'full_name':'A User','street':'Demo street 1','city':'Berlin','postal_code':'10115','country':'Germany'}
    def checkout_body(self,**updates):
        return {'email':'user@example.com','items':[self.line],'shipping_address':self.address,'shipping_method_id':self.shipping.id,'payment_method':'manual',**updates}
    def test_rejects_empty_negative_invalid_and_excess_quantities(self):
        for items in [[],[{**self.line,'quantity':-1}],[{**self.line,'quantity':0}], [{**self.line,'variant_id':999}], [{**self.line,'quantity':8},{**self.line,'quantity':8}]]:
            r=self.client.post('/api/v1/checkout/',self.checkout_body(items=items),format='json')
            self.assertEqual(r.status_code,400,items)
        self.product.refresh_from_db();self.variant.refresh_from_db();self.assertEqual(self.product.stock,10);self.assertEqual(self.variant.stock,10);self.assertEqual(Order.objects.count(),0)
    def test_quote_uses_server_prices_and_discount(self):
        r=self.client.post('/api/v1/cart/quote/',{'items':[{**self.line,'price':'0.01'}],'coupon_code':'WELCOME10'},format='json')
        self.assertEqual(r.status_code,200);self.assertEqual(r.data['subtotal'],'100.00');self.assertEqual(r.data['discount'],'10.00');self.assertEqual(r.data['total'],'96.90')
    def test_expired_coupon_does_not_reserve_stock(self):
        self.coupon.expires_at=timezone.now()-timedelta(days=1);self.coupon.save()
        r=self.client.post('/api/v1/checkout/',self.checkout_body(coupon_code='WELCOME10'),format='json')
        self.assertEqual(r.status_code,400);self.product.refresh_from_db();self.assertEqual(self.product.stock,10)
    def test_order_is_unpaid_owner_scoped_and_cancellation_restores_stock(self):
        self.client.force_authenticate(self.user)
        r=self.client.post('/api/v1/checkout/',self.checkout_body(coupon_code='WELCOME10'),format='json')
        self.assertEqual(r.status_code,201);self.assertEqual(r.data['payment_status'],'unpaid');self.assertEqual(r.data['total'],'96.90')
        order_id=r.data['id'];self.product.refresh_from_db();self.variant.refresh_from_db();self.assertEqual(self.product.stock,9);self.assertEqual(self.variant.stock,9)
        self.assertEqual(self.client.patch(f'/api/v1/orders/{order_id}/',{'status':'paid'},format='json').status_code,405)
        self.client.force_authenticate(self.other);self.assertEqual(self.client.get(f'/api/v1/orders/{order_id}/').status_code,404)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f'/api/v1/orders/{order_id}/status/',{'status':'shipped'},format='json').status_code,400)
        self.assertEqual(self.client.post(f'/api/v1/orders/{order_id}/status/',{'status':'cancelled'},format='json').status_code,200)
        self.client.post(f'/api/v1/orders/{order_id}/status/',{'status':'cancelled'},format='json')
        self.product.refresh_from_db();self.variant.refresh_from_db();self.assertEqual(self.product.stock,10);self.assertEqual(self.variant.stock,10)
    def test_checkout_key_cancellation_is_owner_scoped_and_idempotent(self):
        key=str(uuid.uuid4())
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/v1/checkout/',self.checkout_body(idempotency_key=key),format='json').status_code,201)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':key},format='json').status_code,404)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':key},format='json').status_code,404)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':str(uuid.uuid1())},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':key},format='json').status_code,200)
        self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':key},format='json').status_code,200)
        self.product.refresh_from_db();self.variant.refresh_from_db();self.assertEqual((self.product.stock,self.variant.stock),(10,10))
        self.assertEqual(Payment.objects.get(order__checkout_key=key).status,'cancelled')

    def test_order_transitions_do_not_allow_unpaid_or_terminal_orders_to_be_reopened(self):
        r=self.client.post('/api/v1/checkout/',self.checkout_body(),format='json');order=Order.objects.get(pk=r.data['id'])
        self.client.force_authenticate(self.manager)
        path=f'/api/v1/orders/{order.id}/status/'
        for target in ('paid','processing','shipped'):
            self.assertEqual(self.client.post(path,{'status':target},format='json').status_code,400)
        Order.objects.filter(pk=order.pk).update(status='paid',payment_status='paid')
        self.assertEqual(self.client.post(path,{'status':'shipped'},format='json').status_code,400)
        for target in ('processing','shipped','delivered','completed'):
            self.assertEqual(self.client.post(path,{'status':target},format='json').status_code,200)
        self.assertEqual(self.client.post(path,{'status':'pending'},format='json').status_code,400)
        Order.objects.filter(pk=order.pk).update(status='refunded',payment_status='refunded')
        self.assertEqual(self.client.post(path,{'status':'processing'},format='json').status_code,400)

    def test_django_admin_cannot_modify_order_or_payment_state(self):
        r=self.client.post('/api/v1/checkout/',self.checkout_body(),format='json')
        order=Order.objects.get(pk=r.data['id']);payment=Payment.objects.get(order=order)
        admin=User.objects.create_superuser(username='read-only-admin',email='admin-read@example.com',password='CedarHills!5729')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(f'/admin/orders/order/{order.id}/change/').status_code,200)
        for path in (f'/admin/orders/order/{order.id}/change/',f'/admin/orders/payment/{payment.id}/change/',f'/admin/orders/order/{order.id}/delete/'):
            self.assertEqual(self.client.post(path,{'status':'paid','payment_status':'paid'}).status_code,403)
        self.assertEqual(self.client.get('/admin/orders/order/add/').status_code,403)
        order.refresh_from_db();payment.refresh_from_db();self.assertEqual((order.status,order.payment_status,payment.status),('pending','unpaid','pending'))

    def test_catalog_cannot_delete_reserved_product_or_variant(self):
        r=self.client.post('/api/v1/checkout/',self.checkout_body(),format='json')
        catalog_manager=User.objects.create_user(username='catalog',email='catalog@example.com',password='CedarHills!5729',role='product_manager')
        self.client.force_authenticate(catalog_manager)
        self.assertEqual(self.client.delete('/api/v1/products/coat/').status_code,400)
        self.assertEqual(self.client.delete(f'/api/v1/product-variants/{self.variant.id}/').status_code,400)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f'/api/v1/orders/{r.data["id"]}/status/',{'status':'cancelled'},format='json').status_code,200)
        self.client.force_authenticate(catalog_manager)
        self.assertEqual(self.client.delete(f'/api/v1/product-variants/{self.variant.id}/').status_code,204)
        self.assertEqual(self.client.delete('/api/v1/products/coat/').status_code,204)

    @override_settings(ALLOW_DEMO_CHECKOUT=False)
    def test_checkout_is_disabled_without_provider(self):
        self.assertEqual(self.client.post('/api/v1/checkout/',self.checkout_body(),format='json').status_code,503)

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import patch
from types import SimpleNamespace
from .models import Payment,PaymentEvent
from .payments import PaymentProviderError,StripeHostedCheckout

@override_settings(ALLOW_DEMO_CHECKOUT=False,STRIPE_ENABLED=True,STRIPE_SECRET_KEY='sk_test_example',STRIPE_WEBHOOK_SECRET='whsec_example',FRONTEND_URL='https://shop.example.com')
class StripeCheckoutTests(TestCase):
    def setUp(self):
        cache.clear();self.client=APIClient()
        self.product=Product.objects.create(name='Knit',sku='KNIT',slug='knit',price='100.00',stock=5,is_active=True)
        self.variant=ProductVariant.objects.create(product=self.product,name='M',sku='KNIT-M',stock=5)
        self.shipping=ShippingMethod.objects.create(name='Standard',price='6.90',free_over_threshold=True)
        StoreSettings.objects.create(pk=1,free_shipping_threshold='150.00',tax_rate='19.00')
        self.coupon=Coupon.objects.create(code='WELCOME10',discount_type='percent',discount_value='10.00')
        self.key=str(uuid.uuid4())
        self.body={'email':'pay@example.com','items':[{'product_id':self.product.id,'variant_id':self.variant.id,'quantity':1}],
                   'shipping_method_id':self.shipping.id,'shipping_address':{'full_name':'Test Buyer','street':'Test street 1','city':'Berlin','postal_code':'10115','country':'Germany'},
                   'payment_method':'stripe','idempotency_key':self.key,'coupon_code':'WELCOME10'}
    def create_order(self):
        with patch('apps.orders.views.get_payment_provider') as factory:
            factory.return_value.create_checkout.return_value=('cs_test_123','https://checkout.stripe.com/c/pay/test')
            response=self.client.post('/api/v1/checkout/',self.body,format='json')
            return response
    def signed_event(self,event,secret='whsec_example'):
        payload=json.dumps(event,separators=(',',':')).encode();ts=int(time.time())
        signed=f'{ts}.'.encode()+payload
        signature=hmac.new(secret.encode(),signed,hashlib.sha256).hexdigest()
        return self.client.generic('POST','/api/v1/payments/stripe/webhook/',payload,content_type='application/json',HTTP_STRIPE_SIGNATURE=f't={ts},v1={signature}')
    def session_event(self,order,event_id='evt_1',event_type='checkout.session.completed',payment_status='paid'):
        return {'id':event_id,'type':event_type,'data':{'object':{'id':'cs_test_123','client_reference_id':order.order_number,
            'metadata':{'order_id':str(order.id),'order_number':order.order_number},'currency':'eur','amount_total':int(order.total*100),
            'payment_status':payment_status,'payment_intent':'pi_test_123'}}}
    def test_hosted_checkout_reserves_once_and_rejects_key_reuse(self):
        with patch('apps.orders.views.get_payment_provider') as factory:
            factory.return_value.create_checkout.return_value=('cs_test_123','https://checkout.stripe.com/c/pay/test')
            first=self.client.post('/api/v1/checkout/',self.body,format='json')
            self.assertEqual(first.status_code,201);self.assertEqual(first.data['payment_status'],'unpaid');self.assertTrue(first.data['checkout_url'].startswith('https://checkout.stripe.com/'))
            second=self.client.post('/api/v1/checkout/',self.body,format='json')
            self.assertEqual(second.status_code,200);self.assertEqual(first.data['id'],second.data['id']);factory.return_value.create_checkout.assert_called_once()
        self.product.refresh_from_db();self.variant.refresh_from_db();self.assertEqual(self.product.stock,4);self.assertEqual(self.variant.stock,4);self.assertEqual(Order.objects.count(),1)
        changed={**self.body,'items':[{**self.body['items'][0],'quantity':2}]}
        self.assertEqual(self.client.post('/api/v1/checkout/',changed,format='json').status_code,409)
    def test_provider_failure_retry_keeps_one_reservation(self):
        with patch('apps.orders.views.get_payment_provider') as factory:
            factory.return_value.create_checkout.side_effect=[PaymentProviderError('offline'),('cs_test_123','https://checkout.stripe.com/c/pay/test')]
            first=self.client.post('/api/v1/checkout/',self.body,format='json');self.assertEqual(first.status_code,503)
            second=self.client.post('/api/v1/checkout/',self.body,format='json');self.assertEqual(second.status_code,200)
        self.product.refresh_from_db();self.assertEqual(self.product.stock,4);self.assertEqual(Order.objects.count(),1)
    def test_signed_paid_webhook_is_idempotent_and_verifies_amount(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        event=self.session_event(order)
        self.assertEqual(self.signed_event(event,secret='wrong').status_code,400)
        bad=self.session_event(order,'evt_bad');bad['data']['object']['amount_total']=1
        self.assertEqual(self.signed_event(bad).status_code,400)
        order.refresh_from_db();self.assertEqual(order.payment_status,'unpaid')
        self.assertEqual(self.signed_event(event).status_code,200);self.assertEqual(self.signed_event(event).status_code,200)
        order.refresh_from_db();payment=Payment.objects.get(order=order)
        self.assertEqual((order.status,order.payment_status),('paid','paid'));self.assertEqual(payment.transaction_id,'pi_test_123');self.assertEqual(PaymentEvent.objects.filter(event_id='evt_1').count(),1)
    def test_expiry_releases_stock_once_and_late_payment_requires_review(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        event=self.session_event(order,'evt_expired','checkout.session.expired','unpaid')
        self.assertEqual(self.signed_event(event).status_code,200);self.assertEqual(self.signed_event(event).status_code,200)
        self.product.refresh_from_db();self.variant.refresh_from_db();self.coupon.refresh_from_db();order.refresh_from_db()
        self.assertEqual((self.product.stock,self.variant.stock,self.coupon.used_count),(5,5,0));self.assertEqual(order.status,'cancelled')
        late=self.session_event(order,'evt_late');self.assertEqual(self.signed_event(late).status_code,200)
        order.refresh_from_db();self.assertEqual((order.status,order.payment_status),('payment_review','paid'))
    def test_refund_event_never_restocks_automatically(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id']);self.signed_event(self.session_event(order))
        event={'id':'evt_refund','type':'charge.refunded','data':{'object':{'payment_intent':'pi_test_123','currency':'eur','amount':int(order.total*100),'amount_refunded':int(order.total*100)}}}
        self.assertEqual(self.signed_event(event).status_code,200);order.refresh_from_db();self.product.refresh_from_db()
        self.assertEqual((order.status,order.payment_status),('refunded','refunded'));self.assertEqual(self.product.stock,4)
        old_partial={'id':'evt_old_partial','type':'charge.refunded','data':{'object':{'payment_intent':'pi_test_123','currency':'eur','amount':int(order.total*100),'amount_refunded':100}}}
        self.assertEqual(self.signed_event(old_partial).status_code,200)
        self.assertEqual(self.signed_event(self.session_event(order,'evt_paid_again')).status_code,200)
        order.refresh_from_db();self.assertEqual(order.payment_status,'refunded')
    def test_provider_rejects_non_stripe_redirects(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        with patch('stripe.checkout.Session.create',return_value=SimpleNamespace(id='cs_test',url='https://evil.example/pay')):
            with self.assertRaises(PaymentProviderError): StripeHostedCheckout().create_checkout(order)
    def test_provider_passes_server_total_and_stable_idempotency_key(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        with patch('stripe.checkout.Session.create',return_value=SimpleNamespace(id='cs_test',url='https://checkout.stripe.com/c/pay/test')) as create:
            session,url=StripeHostedCheckout().create_checkout(order)
        args=create.call_args.kwargs
        self.assertEqual(session,'cs_test');self.assertEqual(args['idempotency_key'],str(order.checkout_key))
        self.assertEqual(args['line_items'][0]['price_data']['unit_amount'],int(order.total*100))
        self.assertEqual(args['expires_at'],int(order.created_at.timestamp())+3600)

    def retrieved_session(self,order,session_status='open',payment_status='unpaid'):
        obj=self.session_event(order,payment_status=payment_status)['data']['object']
        return {**obj,'status':session_status}

    def test_staff_recheck_is_authorized_and_never_expires_an_open_session(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        customer=User.objects.create_user(username='pay-customer',email='pay-customer@example.com',password='CedarHills!5729')
        manager=User.objects.create_user(username='pay-manager',email='pay-manager@example.com',password='CedarHills!5729',role='order_manager')
        self.client.force_authenticate(customer)
        self.assertEqual(self.client.post(f'/api/v1/orders/{order.id}/reconcile/',{},format='json').status_code,403)
        self.client.force_authenticate(manager)
        with patch('apps.orders.reconciliation.get_payment_provider') as factory:
            factory.return_value.retrieve_checkout.return_value=self.retrieved_session(order,'open')
            r=self.client.post(f'/api/v1/orders/{order.id}/reconcile/',{},format='json')
            self.assertEqual((r.status_code,r.data['result']),(200,'open'))
            factory.return_value.expire_checkout.assert_not_called()
        self.product.refresh_from_db();self.assertEqual(self.product.stock,4)

    def test_customer_cancellation_expires_session_before_releasing_stock(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        opened=self.retrieved_session(order,'open');expired=self.retrieved_session(order,'expired')
        with patch('apps.orders.reconciliation.get_payment_provider') as factory:
            provider=factory.return_value;provider.retrieve_checkout.return_value=opened;provider.expire_checkout.return_value=expired
            r=self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json')
            self.assertEqual(r.status_code,200);self.assertEqual(r.data,{'status':'cancelled'})
            provider.expire_checkout.assert_called_once_with('cs_test_123',order.checkout_key)
            self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json').status_code,200)
        order.refresh_from_db();self.product.refresh_from_db();self.variant.refresh_from_db();self.coupon.refresh_from_db()
        self.assertEqual((order.status,self.product.stock,self.variant.stock,self.coupon.used_count),('cancelled',5,5,0))
        self.assertEqual(Payment.objects.get(order=order).status,'expired')

    def test_customer_cancellation_never_releases_unknown_or_pending_payment(self):
        with patch('apps.orders.views.get_payment_provider') as factory:
            factory.return_value.create_checkout.side_effect=PaymentProviderError('timeout')
            self.assertEqual(self.client.post('/api/v1/checkout/',self.body,format='json').status_code,503)
        order=Order.objects.get(checkout_key=self.key)
        self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json').status_code,409)
        self.product.refresh_from_db();self.assertEqual(self.product.stock,4)
        payment=Payment.objects.get(order=order);payment.checkout_session_id='cs_test_123';payment.save()
        with patch('apps.orders.reconciliation.get_payment_provider') as factory:
            provider=factory.return_value;provider.retrieve_checkout.return_value=self.retrieved_session(order,'complete','unpaid')
            r=self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json')
            self.assertEqual(r.status_code,409);provider.expire_checkout.assert_not_called()
        order.refresh_from_db();self.product.refresh_from_db();self.assertEqual((order.status,self.product.stock),('pending',4))

    def test_cancellation_racing_success_confirms_payment_without_restocking(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        with patch('apps.orders.reconciliation.get_payment_provider') as factory:
            provider=factory.return_value
            provider.retrieve_checkout.side_effect=[self.retrieved_session(order,'open'),self.retrieved_session(order,'complete','paid')]
            provider.expire_checkout.side_effect=PaymentProviderError('already complete')
            r=self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json')
            self.assertEqual(r.status_code,409)
        order.refresh_from_db();self.product.refresh_from_db();self.assertEqual((order.status,order.payment_status,self.product.stock),('paid','paid',4))
        retried=self.client.post('/api/v1/checkout/',self.body,format='json')
        self.assertEqual(retried.status_code,200);self.assertNotIn('checkout_url',retried.data)

    def test_cancellation_rejects_mismatched_provider_data_and_outage(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        bad=self.retrieved_session(order);bad['metadata']['order_number']='different'
        with patch('apps.orders.reconciliation.get_payment_provider') as factory:
            provider=factory.return_value;provider.retrieve_checkout.return_value=bad
            self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json').status_code,503)
            provider.expire_checkout.assert_not_called()
            provider.retrieve_checkout.side_effect=PaymentProviderError('offline')
            self.assertEqual(self.client.post('/api/v1/checkout/cancel/',{'idempotency_key':self.key},format='json').status_code,503)
        order.refresh_from_db();self.product.refresh_from_db();self.assertEqual((order.status,self.product.stock),('pending',4))

    def test_stale_reconciliation_checks_known_sessions_but_keeps_unknown_ones(self):
        from .reconciliation import reconcile_stale_stripe_orders
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        second_body={**self.body,'idempotency_key':str(uuid.uuid4()),'email':'second@example.com'}
        with patch('apps.orders.views.get_payment_provider') as factory:
            factory.return_value.create_checkout.side_effect=PaymentProviderError('timeout')
            self.assertEqual(self.client.post('/api/v1/checkout/',second_body,format='json').status_code,503)
        unknown=Order.objects.get(checkout_key=second_body['idempotency_key'])
        Order.objects.filter(pk__in=[order.pk,unknown.pk]).update(created_at=timezone.now()-timedelta(hours=2))
        with patch('apps.orders.reconciliation.get_payment_provider') as factory:
            factory.return_value.retrieve_checkout.return_value=self.retrieved_session(order,'expired')
            result=reconcile_stale_stripe_orders()
        self.assertEqual(result['cancelled'],1);self.assertEqual(result['unknown'],1)
        order.refresh_from_db();unknown.refresh_from_db();self.product.refresh_from_db()
        self.assertEqual((order.status,unknown.status,self.product.stock),('cancelled','pending',4))
        self.assertEqual(reconcile_stale_stripe_orders()['unknown'],1)

    def test_stale_checkout_does_not_return_an_old_payable_url(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now()-timedelta(hours=2))
        with patch('apps.orders.views.get_payment_provider') as factory:
            retried=self.client.post('/api/v1/checkout/',self.body,format='json')
            self.assertEqual(retried.status_code,409);self.assertNotIn('checkout_url',retried.data)
            factory.assert_not_called()

    def test_expired_event_claiming_paid_does_not_release_stock(self):
        response=self.create_order();order=Order.objects.get(pk=response.data['id'])
        event=self.session_event(order,'evt_bad_expiry','checkout.session.expired','paid')
        self.assertEqual(self.signed_event(event).status_code,400)
        order.refresh_from_db();self.product.refresh_from_db();self.assertEqual((order.status,self.product.stock),('pending',4))

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection,connections,close_old_connections
from django.test import TransactionTestCase

@skipUnless(connection.vendor=='postgresql','Row-lock concurrency requires PostgreSQL.')
@override_settings(ALLOW_DEMO_CHECKOUT=True)
class ConcurrentCheckoutTests(TransactionTestCase):
    def test_two_buyers_cannot_oversell_the_last_variant(self):
        cache.clear()
        product=Product.objects.create(name='Last piece',sku='LAST',slug='last-piece',price='30.00',stock=1)
        variant=ProductVariant.objects.create(product=product,name='M',sku='LAST-M',stock=1)
        shipping=ShippingMethod.objects.create(name='Standard',price='6.90')
        StoreSettings.objects.create(pk=1,free_shipping_threshold='150.00',tax_rate='19.00')
        barrier=Barrier(2)
        def buyer(n):
            close_old_connections();client=APIClient();barrier.wait(timeout=10)
            body={'email':f'buyer{n}@example.com','items':[{'product_id':product.id,'variant_id':variant.id,'quantity':1}],
                  'shipping_method_id':shipping.id,'shipping_address':{'full_name':'Buyer','street':'Test street 1','city':'Berlin','postal_code':'10115','country':'Germany'},'payment_method':'manual'}
            try: return client.post('/api/v1/checkout/',body,format='json').status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: statuses=sorted(pool.map(buyer,[1,2]))
        self.assertEqual(statuses,[201,400]);product.refresh_from_db();variant.refresh_from_db()
        self.assertEqual((product.stock,variant.stock),(0,0));self.assertEqual(Order.objects.count(),1)

    def test_concurrent_product_deletion_and_checkout_cannot_both_succeed(self):
        cache.clear()
        manager=User.objects.create_user(username='catalog-race',email='catalog-race@example.com',password='CedarHills!5729',role='product_manager')
        product=Product.objects.create(name='Delete race',sku='DELETE-RACE',slug='delete-race',price='30.00',stock=1)
        shipping=ShippingMethod.objects.create(name='Standard',price='6.90')
        StoreSettings.objects.create(pk=1,free_shipping_threshold='150.00',tax_rate='19.00')
        barrier=Barrier(2)
        def operation(kind):
            close_old_connections();client=APIClient();barrier.wait(timeout=10)
            try:
                if kind=='delete':
                    client.force_authenticate(manager)
                    return client.delete('/api/v1/products/delete-race/').status_code
                body={'email':'race@example.com','items':[{'product_id':product.id,'quantity':1}],
                      'shipping_method_id':shipping.id,'shipping_address':{'full_name':'Buyer','street':'Test street 1','city':'Berlin','postal_code':'10115','country':'Germany'},'payment_method':'manual'}
                return client.post('/api/v1/checkout/',body,format='json').status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(operation,['delete','checkout']))
        self.assertIn(tuple(result),[(204,400),(400,201)])
        if result[1]==201:
            self.assertTrue(Product.objects.filter(pk=product.pk).exists())
            self.assertEqual(Order.objects.count(),1)
        else:
            self.assertFalse(Product.objects.filter(pk=product.pk).exists())
