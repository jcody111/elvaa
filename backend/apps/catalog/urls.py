from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
router=DefaultRouter()
router.register('brands',views.BrandViewSet,basename='brand')
router.register('categories',views.CategoryViewSet,basename='category')
router.register('products',views.ProductViewSet,basename='product')
router.register('product-images',views.ProductImageViewSet,basename='product-image')
router.register('product-variants',views.ProductVariantViewSet,basename='product-variant')
router.register('reviews',views.ReviewViewSet,basename='review')
router.register('wishlist',views.WishlistViewSet,basename='wishlist')
router.register('inventory-movements',views.InventoryMovementViewSet,basename='inventory-movement')
urlpatterns=[path('products/<slug:slug>/related/',views.related_products),path('inventory-adjustments/',views.adjust_inventory),path('',include(router.urls))]
