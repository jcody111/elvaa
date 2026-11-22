from django.urls import path,include
from rest_framework.routers import DefaultRouter
from . import views,webhooks
router=DefaultRouter()
router.register('orders',views.OrderViewSet,basename='order')
router.register('shipping-methods',views.ShippingMethodViewSet,basename='shipping')
urlpatterns=[path('orders/<int:pk>/status/',views.update_order_status),path('orders/<int:pk>/reconcile/',views.reconcile_order),path('cart/quote/',views.quote),
 path('checkout/',views.create_order),path('checkout/cancel/',views.cancel_checkout),path('payments/stripe/webhook/',webhooks.stripe_webhook),path('',include(router.urls))]
