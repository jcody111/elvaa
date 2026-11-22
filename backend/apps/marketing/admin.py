from django.contrib import admin
from .models import Coupon,NewsletterSubscriber,Banner,ContactMessage


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display=('email','is_active','confirmed_at','unsubscribed_at','created_at')
    list_filter=('is_active','confirmed_at')
    search_fields=('email',)
    exclude=('confirmation_nonce',)
    readonly_fields=('email','is_active','confirmation_sent_at','confirmed_at','unsubscribed_at','created_at')

    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display=('code','discount_type','discount_value','is_active','used_count')
    search_fields=('code',)
    readonly_fields=('code','discount_type','discount_value','minimum_order','is_active','expires_at','usage_limit','used_count')
    # Use the staff API for writes: it locks rows and protects reservations.
    # A normal admin save would overwrite used_count from a stale form instance.
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False


admin.site.register(Banner)
admin.site.register(ContactMessage)
