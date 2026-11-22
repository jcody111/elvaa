from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.orders.models import Order
class CoreTests(TestCase):
    def setUp(self): cache.clear();self.client=APIClient()
    def test_health(self): self.assertEqual(self.client.get('/api/v1/health/').status_code,200)
    def test_reports_require_role_and_escape_formula_cells(self):
        u=User.objects.create_user(username='customer',email='a@example.com',password='CedarHills!5729')
        staff=User.objects.create_user(username='admin',email='admin@example.com',password='CedarHills!5729',role='store_admin')
        Order.objects.create(email='=SUM(A1)@example.com',total='10.00')
        self.client.force_authenticate(u);self.assertEqual(self.client.get('/api/v1/reports/orders.csv/').status_code,403)
        self.client.force_authenticate(staff);r=self.client.get('/api/v1/reports/orders.csv/')
        self.assertEqual(r.status_code,200);self.assertIn("'=SUM(A1)@example.com",r.content.decode())
        self.assertEqual(self.client.get('/api/v1/reports/orders.xlsx/').status_code,200)
    def test_formula_sanitization_handles_leading_whitespace(self):
        from .reports import safe
        for value in ('=1+1','  =1+1','\t+SUM(A1)','\ufeff@danger','\rtext','\ntext'):
            self.assertTrue(safe(value).startswith("'"),value)
        self.assertEqual(safe('normal@example.com'),'normal@example.com')

    def test_schema_documents_authentication_and_inventory_contract(self):
        import yaml
        response=self.client.get('/api/schema/')
        self.assertEqual(response.status_code,200)
        schema=yaml.safe_load(response.content)
        self.assertEqual(schema['components']['securitySchemes']['jwtAuth']['scheme'],'bearer')
        self.assertEqual(schema['paths']['/api/v1/orders/']['get']['security'],[{'jwtAuth':[]}])
        self.assertIn('expected_stock',schema['components']['schemas']['InventoryAdjustment']['required'])
        self.assertIn('/api/v1/checkout/cancel/',schema['paths'])

    def test_public_cannot_modify_settings(self):
        self.assertEqual(self.client.put('/api/v1/settings/store/',{'currency':'USD'},format='json').status_code,403)
