from django.contrib import admin
from .models import Order,OrderItem,ShippingMethod,Payment,PaymentEvent


class ReadOnlyAdmin(admin.ModelAdmin):
    """Protect stock and provider state from bypassing transactional APIs."""
    def has_add_permission(self,request):
        return False

    def has_change_permission(self,request,obj=None):
        return False

    def has_delete_permission(self,request,obj=None):
        return False

    def get_readonly_fields(self,request,obj=None):
        excluded=set(self.exclude or ())
        return tuple(field.name for field in self.model._meta.fields if field.name not in excluded)


@admin.register(Order)
class OrderAdmin(ReadOnlyAdmin):
    exclude=('checkout_key','request_fingerprint')
    list_display=('order_number','email','status','payment_status','total','created_at')
    list_filter=('status','payment_status','payment_method')
    search_fields=('order_number','email')


@admin.register(OrderItem)
class OrderItemAdmin(ReadOnlyAdmin):
    list_display=('order','name','variant_name','quantity','unit_price')
    search_fields=('order__order_number','name','sku')


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    exclude=('checkout_url',)
    list_display=('order','provider','amount','amount_refunded','status','updated_at')
    list_filter=('provider','status')
    search_fields=('order__order_number','transaction_id','checkout_session_id')


@admin.register(PaymentEvent)
class PaymentEventAdmin(ReadOnlyAdmin):
    list_display=('event_id','event_type','processed_at')
    search_fields=('event_id','event_type')


admin.site.register(ShippingMethod)
