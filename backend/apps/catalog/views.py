import django_filters
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q, Sum, Subquery, OuterRef, IntegerField, Value
from django.db.models.functions import Coalesce
from apps.orders.models import OrderItem
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.accounts.permissions import role_perm, user_has_perm
from apps.core.models import AuditLog
from .models import Brand, Category, Product, ProductImage, ProductVariant, Review, Wishlist, InventoryMovement
from .serializers import (BrandSerializer,CategorySerializer,ProductSerializer,ProductImageUploadSerializer,
                          ProductVariantSerializer,ReviewSerializer,WishlistSerializer,InventoryMovementSerializer,InventoryAdjustmentSerializer)

def audit(request,action,obj):
    AuditLog.objects.create(user=request.user if request.user.is_authenticated else None,action=action,
                            model_name=obj.__class__.__name__,object_id=str(obj.pk))

class StaffWriteMixin:
    def get_permissions(self):
        if self.action in ['list','retrieve']: return [AllowAny()]
        return [role_perm('products')()]
    def perform_create(self,serializer):
        obj=serializer.save(); audit(self.request,'create',obj)
    def perform_update(self,serializer):
        obj=serializer.save(); audit(self.request,'update',obj)
    def perform_destroy(self,instance):
        audit(self.request,'delete',instance); instance.delete()

class BrandViewSet(StaffWriteMixin,viewsets.ModelViewSet):
    queryset=Brand.objects.all().order_by('name'); serializer_class=BrandSerializer
class CategoryViewSet(StaffWriteMixin,viewsets.ModelViewSet):
    serializer_class=CategorySerializer; lookup_field='slug'
    def get_queryset(self):
        qs=Category.objects.all()
        if not user_has_perm(self.request.user,'products'): qs=qs.filter(is_active=True)
        return qs

class ProductFilter(django_filters.FilterSet):
    category=django_filters.CharFilter(method='filter_category')
    brand=django_filters.CharFilter(method='filter_brand')
    min_price=django_filters.NumberFilter(field_name='price',lookup_expr='gte')
    max_price=django_filters.NumberFilter(field_name='price',lookup_expr='lte')
    in_stock=django_filters.BooleanFilter(method='filter_stock')
    def filter_category(self,qs,name,value):
        return qs.filter(Q(category_id=int(value)) | Q(category__parent_id=int(value))) if value.isdigit() else qs.filter(Q(category__slug=value) | Q(category__parent__slug=value))
    def filter_brand(self,qs,name,value):
        return qs.filter(brand_id=int(value)) if value.isdigit() else qs.filter(brand__slug=value)
    def filter_stock(self,qs,name,value): return qs.filter(stock__gt=0) if value else qs.filter(stock=0)
    class Meta: model=Product; fields=['category','brand','is_featured','is_new','is_active','min_price','max_price','in_stock']

class ProductViewSet(StaffWriteMixin,viewsets.ModelViewSet):
    serializer_class=ProductSerializer; lookup_field='slug'
    filter_backends=[DjangoFilterBackend,filters.SearchFilter,filters.OrderingFilter]
    filterset_class=ProductFilter; search_fields=['name','description','sku','category__name','brand__name']
    ordering_fields=['price','created_at','name','review_count','sold_count']; ordering=['-created_at']
    @transaction.atomic
    def perform_create(self,serializer):
        obj=serializer.save();audit(self.request,'create',obj)
        if obj.stock: InventoryMovement.objects.create(product=obj,quantity_change=obj.stock,reason='Product created',actor=self.request.user)
    @transaction.atomic
    def perform_destroy(self,instance):
        # Checkout locks products first. Locking here prevents a reservation from
        # slipping between the open-order check and deletion.
        locked=get_object_or_404(Product.objects.select_for_update(),pk=instance.pk)
        if OrderItem.objects.filter(product=locked,order__status__in=['pending','paid','processing','payment_review']).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail':'This product has open orders. Disable it instead of deleting it.'})
        audit(self.request,'delete',locked);locked.delete()
    @transaction.atomic
    def perform_update(self,serializer):
        locked=get_object_or_404(Product.objects.select_for_update(),pk=serializer.instance.pk);before=locked.stock
        serializer.instance=locked;obj=serializer.save();audit(self.request,'update',obj)
        if obj.stock!=before: InventoryMovement.objects.create(product=obj,quantity_change=obj.stock-before,reason='Product stock edited',actor=self.request.user)
    def get_queryset(self):
        paid_units=OrderItem.objects.filter(product_id=OuterRef('pk'),order__payment_status='paid').values('product_id').annotate(total=Sum('quantity')).values('total')
        qs=Product.objects.select_related('category','brand').prefetch_related('images','variants').annotate(
            sold_count=Coalesce(Subquery(paid_units,output_field=IntegerField()),Value(0)),
            avg_rating=Avg('reviews__rating',filter=Q(reviews__is_approved=True)),
            review_count=Count('reviews',filter=Q(reviews__is_approved=True),distinct=True))
        if not user_has_perm(self.request.user,'products'): qs=qs.filter(is_active=True)
        return qs

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset=ProductImage.objects.all(); serializer_class=ProductImageUploadSerializer
    permission_classes=[role_perm('products')]
class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset=ProductVariant.objects.all(); serializer_class=ProductVariantSerializer
    permission_classes=[role_perm('products')]
    @transaction.atomic
    def perform_create(self,serializer):
        product=get_object_or_404(Product.objects.select_for_update(),pk=serializer.validated_data['product'].pk)
        obj=serializer.save(product=product);audit(self.request,'create',obj)
        if obj.stock: InventoryMovement.objects.create(product=product,variant=obj,quantity_change=obj.stock,reason='Variant created',actor=self.request.user)
    @transaction.atomic
    def perform_update(self,serializer):
        get_object_or_404(Product.objects.select_for_update(),pk=serializer.instance.product_id)
        locked=get_object_or_404(ProductVariant.objects.select_for_update(),pk=serializer.instance.pk)
        serializer.instance=locked;obj=serializer.save();audit(self.request,'update',obj)
    @transaction.atomic
    def perform_destroy(self,instance):
        get_object_or_404(Product.objects.select_for_update(),pk=instance.product_id)
        locked=get_object_or_404(ProductVariant.objects.select_for_update(),pk=instance.pk)
        if OrderItem.objects.filter(variant=locked,order__status__in=['pending','paid','processing','payment_review']).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail':'This variant has open orders and cannot be deleted.'})
        audit(self.request,'delete',locked);locked.delete()

class InventoryMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset=InventoryMovement.objects.select_related('product','variant','actor').all()
    serializer_class=InventoryMovementSerializer; permission_classes=[role_perm('products')]

@extend_schema(request=InventoryAdjustmentSerializer, responses={200:InventoryMovementSerializer, 409:OpenApiResponse(description='Stock changed since last observed.')}, description='Set product or variant stock only if expected_stock matches the current quantity.')
@api_view(['POST'])
@permission_classes([role_perm('products')])
def adjust_inventory(request):
    serializer=InventoryAdjustmentSerializer(data=request.data);serializer.is_valid(raise_exception=True);data=serializer.validated_data
    with transaction.atomic():
        product=Product.objects.select_for_update().filter(pk=data['product_id']).first()
        if not product: return Response({'detail':'Product not found.'},status=404)
        variant=None
        if data.get('variant_id'):
            variant=ProductVariant.objects.select_for_update().filter(pk=data['variant_id'],product=product).first()
            if not variant: return Response({'detail':'Variant not found for this product.'},status=404)
        target=variant or product;old=target.stock
        if old!=data['expected_stock']:
            return Response({'detail':'Stock changed since it was selected. Refresh the current quantity before adjusting.','current_stock':old},status=status.HTTP_409_CONFLICT)
        target.stock=data['new_stock'];target.save(update_fields=['stock'])
        movement=InventoryMovement.objects.create(product=product,variant=variant,quantity_change=target.stock-old,reason=data['reason'],actor=request.user)
        audit(request,'inventory_adjustment',product)
    return Response(InventoryMovementSerializer(movement).data)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class=ReviewSerializer
    def get_permissions(self): return [AllowAny()] if self.action in ['list','retrieve'] else [IsAuthenticated()]
    def get_queryset(self):
        qs=Review.objects.filter(is_approved=True).select_related('user')
        product=self.request.query_params.get('product')
        return qs.filter(product_id=product) if product and product.isdigit() else qs
    def perform_create(self,serializer): serializer.save(user=self.request.user)
    def get_object(self):
        obj=super().get_object()
        if self.action not in ['list','retrieve'] and obj.user_id!=self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        return obj
class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class=WishlistSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        if not self.request.user.is_authenticated: return Wishlist.objects.none()
        return Wishlist.objects.filter(user=self.request.user).select_related('product','product__brand','product__category').prefetch_related('product__images','product__variants')
    def create(self,request,*args,**kwargs):
        serializer=self.get_serializer(data=request.data); serializer.is_valid(raise_exception=True)
        obj,created=Wishlist.objects.get_or_create(user=request.user,product=serializer.validated_data['product'])
        return Response(self.get_serializer(obj).data,status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    def perform_update(self,serializer):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed('PUT')

@extend_schema(responses=ProductSerializer(many=True))
@api_view(['GET'])
@permission_classes([AllowAny])
def related_products(request,slug):
    p=Product.objects.filter(slug=slug,is_active=True).first()
    if not p: return Response({'detail':'Product not found.'},status=404)
    rel=Product.objects.filter(category=p.category,is_active=True).exclude(pk=p.pk).select_related('category','brand').prefetch_related('images','variants')[:8]
    return Response(ProductSerializer(rel,many=True,context={'request':request}).data)
