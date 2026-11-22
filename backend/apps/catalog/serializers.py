from rest_framework import serializers
from .models import Brand, Category, Product, ProductImage, ProductVariant, Review, Wishlist

class BrandSerializer(serializers.ModelSerializer):
    class Meta: model=Brand; fields='__all__'
class CategorySerializer(serializers.ModelSerializer):
    image_display=serializers.SerializerMethodField()
    class Meta: model=Category; fields='__all__'
    def get_image_display(self,obj) -> str: return obj.image.url if obj.image else obj.image_url
    def validate_parent(self,value):
        current=value
        while current:
            if self.instance and current.pk==self.instance.pk: raise serializers.ValidationError('A category cannot be its own ancestor.')
            current=current.parent
        return value
class ProductImageSerializer(serializers.ModelSerializer):
    image=serializers.SerializerMethodField()
    class Meta: model=ProductImage; fields=['id','image','alt','display_order']
    def get_image(self,obj) -> str: return obj.image.url if obj.image else obj.image_url
class ProductImageUploadSerializer(serializers.ModelSerializer):
    class Meta: model=ProductImage; fields=['id','product','image','image_url','alt','display_order']
    def validate_image(self,value):
        if value and value.size>5*1024*1024: raise serializers.ValidationError('Image must be 5 MB or smaller.')
        if value and value.content_type not in ['image/jpeg','image/png','image/webp']: raise serializers.ValidationError('Use a JPEG, PNG, or WebP image.')
        return value
    def validate_image_url(self,value):
        if value and not (value.startswith('/images/') or value.startswith('https://')): raise serializers.ValidationError('Use a local /images/ path or HTTPS URL.')
        return value
class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta: model=ProductVariant; fields=['id','product','name','sku','price','stock','attributes']
    def validate_product(self,value):
        if self.instance and self.instance.product_id!=value.id: raise serializers.ValidationError('A variant cannot be moved to another product.')
        return value
    def validate(self,attrs):
        if self.instance and 'stock' in attrs:
            raise serializers.ValidationError({'stock':'Use an inventory adjustment to change existing stock.'})
        return attrs
class ReviewSerializer(serializers.ModelSerializer):
    username=serializers.CharField(source='user.first_name',read_only=True)
    class Meta:
        model=Review; fields=['id','product','username','rating','title','body','is_approved','created_at']; read_only_fields=['is_approved','created_at']
    def validate(self,attrs):
        user=self.context['request'].user
        if user.is_authenticated and Review.objects.filter(product=attrs.get('product'),user=user).exists(): raise serializers.ValidationError('You have already reviewed this product.')
        return attrs
class ProductSerializer(serializers.ModelSerializer):
    images=ProductImageSerializer(many=True,read_only=True)
    variants=ProductVariantSerializer(many=True,read_only=True)
    brand_name=serializers.CharField(source='brand.name',read_only=True,default='ELVAA')
    category_name=serializers.CharField(source='category.name',read_only=True,default='')
    category_slug=serializers.CharField(source='category.slug',read_only=True,default='')
    avg_rating=serializers.FloatField(read_only=True,allow_null=True)
    review_count=serializers.IntegerField(read_only=True,default=0)
    sold_count=serializers.IntegerField(read_only=True,default=0)
    class Meta: model=Product; fields='__all__'
    def validate(self,attrs):
        if self.instance and 'stock' in attrs:
            raise serializers.ValidationError({'stock':'Use an inventory adjustment to change existing stock.'})
        price=attrs.get('price',getattr(self.instance,'price',None)); compare=attrs.get('compare_at_price',getattr(self.instance,'compare_at_price',None))
        if price is not None and compare is not None and compare<price: raise serializers.ValidationError({'compare_at_price':'Compare-at price cannot be below the sale price.'})
        return attrs
class WishlistSerializer(serializers.ModelSerializer):
    product_detail=ProductSerializer(source='product',read_only=True)
    class Meta: model=Wishlist; fields=['id','product','product_detail','created_at']; read_only_fields=['id','created_at']

class InventoryMovementSerializer(serializers.ModelSerializer):
    product_name=serializers.CharField(source='product_name_snapshot',read_only=True)
    variant_name=serializers.CharField(source='variant_name_snapshot',read_only=True,default='')
    actor_name=serializers.CharField(source='actor.username',read_only=True,default='System')
    class Meta:
        from .models import InventoryMovement
        model=InventoryMovement
        fields=['id','product','product_name','variant','variant_name','quantity_change','reason','reference','actor_name','created_at']
        read_only_fields=fields
class InventoryAdjustmentSerializer(serializers.Serializer):
    product_id=serializers.IntegerField(min_value=1)
    variant_id=serializers.IntegerField(required=False,allow_null=True,min_value=1)
    expected_stock=serializers.IntegerField(min_value=0,help_text='Quantity last observed by the operator. A mismatch returns HTTP 409.')
    new_stock=serializers.IntegerField(min_value=0,max_value=1000000)
    reason=serializers.CharField(min_length=3,max_length=120)
