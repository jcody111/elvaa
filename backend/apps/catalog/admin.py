from django.contrib import admin
from .models import Brand, Category, Product, ProductImage, ProductVariant, Review, Wishlist, InventoryMovement


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    # Variant edits must follow the same product-then-variant locking as checkout.
    readonly_fields = ('name', 'sku', 'price', 'stock', 'attributes')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'stock', 'is_active', 'is_featured')
    list_filter = ('category', 'is_active', 'is_featured', 'is_new')
    search_fields = ('name', 'sku')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]

    def get_readonly_fields(self, request, obj=None):
        return ('stock',) if obj else ()

    def has_delete_permission(self, request, obj=None):
        # Deletion through the API checks for open orders.
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and obj.stock:
            InventoryMovement.objects.create(product=obj, quantity_change=obj.stock,
                                             reason='Product created', actor=request.user)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'product_name_snapshot', 'variant_name_snapshot',
                    'quantity_change', 'reason', 'reference', 'actor')
    list_filter = ('reason', 'created_at')
    search_fields = ('product_name_snapshot', 'variant_name_snapshot', 'reference')
    readonly_fields = ('product', 'variant', 'product_name_snapshot', 'variant_name_snapshot',
                       'quantity_change', 'reason', 'reference', 'actor', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'display_order')
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Brand)
admin.site.register(Review)
admin.site.register(Wishlist)
