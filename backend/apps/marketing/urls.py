from django.urls import path,include
from rest_framework.routers import DefaultRouter
from . import views
router=DefaultRouter()
router.register('coupons',views.CouponViewSet,basename='coupon')
router.register('newsletter',views.NewsletterViewSet,basename='newsletter')
router.register('banners',views.BannerViewSet,basename='banner')
router.register('contact',views.ContactViewSet,basename='contact')
urlpatterns=[path('newsletter/confirm/',views.confirm_newsletter),path('newsletter/unsubscribe/',views.unsubscribe_newsletter),path('',include(router.urls))]
