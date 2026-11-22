from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
router=DefaultRouter()
router.register('addresses',views.AddressViewSet,basename='address')
router.register('admin/users',views.UserAdminViewSet,basename='admin-user')
urlpatterns=[path('register/',views.RegisterView.as_view()),path('login/',views.LoginView.as_view()),
 path('refresh/',views.CookieRefreshView.as_view()),path('logout/',views.LogoutView.as_view()),
 path('csrf/',views.csrf),path('me/',views.MeView.as_view()),
 path('forgot-password/',views.ForgotPasswordView.as_view()),path('reset-password/',views.ResetPasswordView.as_view()),
 path('verify-email/',views.VerifyEmailView.as_view()),path('send-verification/',views.SendVerificationView.as_view()),
 path('change-password/',views.ChangePasswordView.as_view()),path('',include(router.urls))]
