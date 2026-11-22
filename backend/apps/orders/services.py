from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.catalog.models import Product,ProductVariant
from apps.marketing.models import Coupon
from apps.core.models import StoreSettings
from .models import ShippingMethod

MONEY=Decimal('0.01')
def calculate_cart(data,lock=False):
    """Price and validate every line against the database; never trust client prices."""
    quantities=defaultdict(int)
    for line in data['items']:
        quantities[(line['product_id'],line.get('variant_id'))]+=line['quantity']
    if any(q>20 for q in quantities.values()): raise ValidationError({'items':'Maximum quantity per item is 20.'})
    ids={pid for pid,_ in quantities}
    product_qs=Product.objects.filter(pk__in=ids,is_active=True).order_by('pk')
    if lock: product_qs=product_qs.select_for_update()
    products={p.id:p for p in product_qs}
    if len(products)!=len(ids): raise ValidationError({'items':'One or more products are unavailable.'})
    variant_qs=ProductVariant.objects.filter(product_id__in=ids).order_by('pk')
    if lock: variant_qs=variant_qs.select_for_update()
    variants=list(variant_qs); variants_by_id={v.id:v for v in variants}
    products_with_variants={v.product_id for v in variants}
    product_totals=defaultdict(int); lines=[]; subtotal=Decimal('0')
    for (pid,vid),qty in quantities.items():
        p=products[pid]; v=variants_by_id.get(vid) if vid else None
        if pid in products_with_variants and not v: raise ValidationError({'items':f'Please choose an option for {p.name}.'})
        if vid and (not v or v.product_id!=pid): raise ValidationError({'items':f'Invalid option for {p.name}.'})
        if v and v.stock<qty: raise ValidationError({'items':f'Not enough stock for {p.name} ({v.name}).'})
        product_totals[pid]+=qty
        price=(v.price if v and v.price is not None else p.price)
        subtotal+=price*qty
        lines.append({'product':p,'variant':v,'quantity':qty,'price':price})
    for pid,qty in product_totals.items():
        if products[pid].stock<qty: raise ValidationError({'items':f'Not enough stock for {products[pid].name}.'})
    store,_=StoreSettings.objects.get_or_create(pk=1)
    shipping_id=data.get('shipping_method_id')
    shipping_qs=ShippingMethod.objects.filter(is_active=True)
    method=shipping_qs.filter(pk=shipping_id).first() if shipping_id else shipping_qs.order_by('price','id').first()
    if not method: raise ValidationError({'shipping_method_id':'Please select a valid delivery method.'})
    discount=Decimal('0'); coupon=None
    code=data.get('coupon_code','').strip()
    if code:
        cq=Coupon.objects.filter(code__iexact=code,is_active=True)
        if lock: cq=cq.select_for_update()
        coupon=cq.first()
        if not coupon or (coupon.expires_at and coupon.expires_at<=timezone.now()) or (coupon.usage_limit is not None and coupon.used_count>=coupon.usage_limit):
            raise ValidationError({'coupon_code':'This code is invalid or has expired.'})
        if subtotal<coupon.minimum_order: raise ValidationError({'coupon_code':'The minimum order value for this code has not been reached.'})
        if coupon.discount_type=='percent': discount=(subtotal*min(coupon.discount_value,Decimal('100'))/100).quantize(MONEY,rounding=ROUND_HALF_UP)
        else: discount=min(coupon.discount_value,subtotal)
    discounted=subtotal-discount
    shipping=Decimal('0') if method.free_over_threshold and discounted>=store.free_shipping_threshold else method.price
    total=discounted+shipping
    tax=(total-total/(Decimal('1')+store.tax_rate/100)).quantize(MONEY,rounding=ROUND_HALF_UP) if store.tax_rate else Decimal('0')
    return {'lines':lines,'subtotal':subtotal,'discount':discount,'shipping':shipping,'tax':tax,'total':total,
            'shipping_method':method,'coupon':coupon}

def quote_output(q):
    return {'items':[{'product_id':line['product'].id,'variant_id':line['variant'].id if line['variant'] else None,
                      'name':line['product'].name,'variant':line['variant'].name if line['variant'] else '',
                      'quantity':line['quantity'],'unit_price':str(line['price'])} for line in q['lines']],
            'subtotal':str(q['subtotal']),'discount':str(q['discount']),'shipping':str(q['shipping']),
            'tax_included':str(q['tax']),'total':str(q['total']),'currency':'EUR',
            'shipping_method_id':q['shipping_method'].id}


def release_unpaid_reservation(order, reason, actor=None):
    """Release a pending order exactly once while its Order row is locked.

    Acquire product locks in ascending order, then variant locks, like checkout.
    Callers must already be inside transaction.atomic() and hold the order lock.
    """
    from django.db.models import F
    from apps.catalog.models import InventoryMovement
    from apps.core.models import AuditLog
    if order.status != 'pending' or order.payment_status != 'unpaid':
        return False
    product_quantities=defaultdict(int)
    variant_quantities=defaultdict(int)
    variant_products={}
    for item in order.items.all():
        if item.product_id:
            product_quantities[item.product_id]+=item.quantity
        if item.variant_id and item.product_id:
            variant_quantities[item.variant_id]+=item.quantity
            variant_products[item.variant_id]=item.product_id
    for product_id,quantity in sorted(product_quantities.items()):
        if Product.objects.filter(pk=product_id).update(stock=F('stock')+quantity):
            InventoryMovement.objects.create(product_id=product_id,quantity_change=quantity,reason=reason,reference=order.order_number,actor=actor)
    for variant_id,quantity in sorted(variant_quantities.items()):
        if ProductVariant.objects.filter(pk=variant_id).update(stock=F('stock')+quantity):
            InventoryMovement.objects.create(product_id=variant_products[variant_id],variant_id=variant_id,quantity_change=quantity,reason=reason,reference=order.order_number,actor=actor)
    if order.coupon_code:
        Coupon.objects.filter(code__iexact=order.coupon_code,used_count__gt=0).update(used_count=F('used_count')-1)
    order.status='cancelled'
    order.save(update_fields=['status','updated_at'])
    AuditLog.objects.create(user=actor,action='reservation_released',model_name='Order',object_id=str(order.pk),details={'reason':reason})
    return True
