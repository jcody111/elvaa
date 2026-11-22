from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from .models import Category,Brand,Product,ProductVariant,Review,Wishlist

class CatalogTests(TestCase):
    def setUp(self):
        cache.clear();self.client=APIClient()
        self.customer=User.objects.create_user(username='customer',email='customer@example.com',password='CedarHills!5729')
        self.manager=User.objects.create_user(username='manager',email='manager@example.com',password='CedarHills!5729',role='product_manager')
        self.root=Category.objects.create(name='Clothing',slug='clothing')
        self.cat=Category.objects.create(name='Tailoring',slug='tailoring',parent=self.root)
        self.brand=Brand.objects.create(name='ELVAA',slug='elvaa')
        self.p=Product.objects.create(name='A jacket',slug='a-jacket',sku='A1',price='100.00',stock=5,category=self.cat,brand=self.brand,is_featured=True)
        self.hidden=Product.objects.create(name='Hidden',slug='hidden',sku='B1',price='200.00',stock=0,category=self.cat,is_active=False)
    def test_public_filters_search_and_parent_category(self):
        r=self.client.get('/api/v1/products/',{'category':'clothing','min_price':'90','max_price':'110','in_stock':'true'})
        self.assertEqual(r.status_code,200); self.assertEqual(r.data['count'],1); self.assertEqual(r.data['results'][0]['slug'],'a-jacket')
        self.assertEqual(self.client.get('/api/v1/products/hidden/').status_code,404)
        self.assertEqual(self.client.get('/api/v1/products/',{'search':'jacket'}).data['count'],1)
    def test_product_writes_require_backend_role(self):
        payload={'name':'New piece','sku':'NEW1','price':'49.00','stock':4}
        self.assertIn(self.client.post('/api/v1/products/',payload,format='json').status_code,[401,403])
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post('/api/v1/products/',payload,format='json').status_code,403)
        self.client.force_authenticate(self.manager)
        r=self.client.post('/api/v1/products/',payload,format='json');self.assertEqual(r.status_code,201)
        self.assertTrue(Product.objects.filter(slug='new-piece').exists())
        self.assertEqual(self.client.get('/api/v1/products/hidden/').status_code,200)
        self.assertEqual(self.client.get('/api/v1/admin/stats/').status_code,403)
    def test_only_approved_reviews_count(self):
        Review.objects.create(product=self.p,user=self.customer,rating=5,is_approved=False)
        r=self.client.get('/api/v1/products/a-jacket/');self.assertEqual(r.data['review_count'],0);self.assertIsNone(r.data['avg_rating'])
        Review.objects.filter(product=self.p).update(is_approved=True)
        r=self.client.get('/api/v1/products/a-jacket/');self.assertEqual(r.data['review_count'],1);self.assertEqual(r.data['avg_rating'],5.0)
    def test_wishlist_is_private_and_idempotent(self):
        self.client.force_authenticate(self.customer)
        a=self.client.post('/api/v1/wishlist/',{'product':self.p.id},format='json')
        b=self.client.post('/api/v1/wishlist/',{'product':self.p.id},format='json')
        self.assertEqual(a.status_code,201);self.assertEqual(b.status_code,200);self.assertEqual(Wishlist.objects.count(),1)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get(f'/api/v1/wishlist/{a.data["id"]}/').status_code,404)
    def test_category_hierarchy_rejects_cycle(self):
        self.client.force_authenticate(self.manager)
        r=self.client.patch('/api/v1/categories/clothing/',{'parent':self.cat.id},format='json')
        self.assertEqual(r.status_code,400)
    def test_inventory_adjustment_requires_role_and_retains_history(self):
        from .models import InventoryMovement
        body={'product_id':self.p.id,'expected_stock':5,'new_stock':7,'reason':'Counted stock'}
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.post('/api/v1/inventory-adjustments/',body,format='json').status_code,403)
        self.client.force_authenticate(self.manager)
        r=self.client.post('/api/v1/inventory-adjustments/',body,format='json')
        self.assertEqual(r.status_code,200);self.p.refresh_from_db();self.assertEqual(self.p.stock,7);self.assertEqual(r.data['quantity_change'],2)
        stale=self.client.post('/api/v1/inventory-adjustments/',body,format='json')
        self.assertEqual(stale.status_code,409);self.assertEqual(stale.data['current_stock'],7)
        self.assertEqual(InventoryMovement.objects.filter(reason='Counted stock').count(),1)
        self.assertEqual(self.client.post('/api/v1/inventory-adjustments/',{**body,'expected_stock':7,'new_stock':-1},format='json').status_code,400)
        self.assertEqual(self.client.post('/api/v1/inventory-adjustments/',{k:v for k,v in body.items() if k!='expected_stock'},format='json').status_code,400)
        self.assertEqual(self.client.delete('/api/v1/products/a-jacket/').status_code,204)
        movement=InventoryMovement.objects.get(reason='Counted stock');self.assertIsNone(movement.product);self.assertEqual(movement.product_name_snapshot,'A jacket')

    def test_existing_stock_can_only_be_changed_with_expected_quantity(self):
        variant=ProductVariant.objects.create(product=self.p,name='M',sku='A1-M',stock=4)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.patch('/api/v1/products/a-jacket/',{'stock':99},format='json').status_code,400)
        self.assertEqual(self.client.patch(f'/api/v1/product-variants/{variant.id}/',{'stock':99},format='json').status_code,400)
        self.assertEqual(self.client.patch('/api/v1/products/a-jacket/',{'description':'Updated'},format='json').status_code,200)
        body={'product_id':self.p.id,'variant_id':variant.id,'expected_stock':4,'new_stock':6,'reason':'Stock count'}
        self.assertEqual(self.client.post('/api/v1/inventory-adjustments/',body,format='json').status_code,200)
        self.assertEqual(self.client.post('/api/v1/inventory-adjustments/',body,format='json').status_code,409)
        self.p.refresh_from_db();variant.refresh_from_db();self.assertEqual((self.p.stock,variant.stock),(5,6))

    def test_staff_catalog_search_includes_hidden_products_and_paginates(self):
        for i in range(26):
            Product.objects.create(name=f'Inventory piece {i:02}',sku=f'INV-{i:02}',slug=f'inventory-piece-{i:02}',price='10.00',stock=2,is_active=i!=25)
        self.client.force_authenticate(self.manager)
        first=self.client.get('/api/v1/products/',{'search':'Inventory piece','ordering':'name','page':1})
        second=self.client.get('/api/v1/products/',{'search':'Inventory piece','ordering':'name','page':2})
        self.assertEqual(first.data['count'],26);self.assertTrue(first.data['next']);self.assertEqual(len(second.data['results']),2)
        self.assertIn('inventory-piece-25',[p['slug'] for p in second.data['results']])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/products/',{'search':'Inventory piece'}).data['count'],25)

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection,connections,close_old_connections
from django.test import TransactionTestCase


@skipUnless(connection.vendor=='postgresql','Row-lock concurrency requires PostgreSQL.')
class ConcurrentInventoryTests(TransactionTestCase):
    def test_two_adjustments_from_same_observed_stock_cannot_overwrite_each_other(self):
        from .models import InventoryMovement
        cache.clear()
        manager=User.objects.create_user(username='inv-manager',email='inv@example.com',password='CedarHills!5729',role='product_manager')
        product=Product.objects.create(name='Stock test',sku='STOCK-TEST',slug='stock-test',price='20.00',stock=5)
        barrier=Barrier(2)
        def adjust(new_stock):
            close_old_connections();client=APIClient();client.force_authenticate(manager);barrier.wait(timeout=10)
            try:
                return client.post('/api/v1/inventory-adjustments/',{'product_id':product.id,'expected_stock':5,'new_stock':new_stock,'reason':'Concurrent count'},format='json').status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=sorted(pool.map(adjust,[7,8]))
        self.assertEqual(statuses,[200,409])
        product.refresh_from_db();self.assertIn(product.stock,[7,8])
        self.assertEqual(InventoryMovement.objects.filter(reason='Concurrent count').count(),1)
