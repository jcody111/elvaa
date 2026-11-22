from django.core.management.base import BaseCommand
from django.db import transaction
from apps.catalog.models import Brand, Category, Product, ProductImage, ProductVariant
from apps.core.models import StoreSettings
from apps.orders.models import ShippingMethod
from apps.marketing.models import Coupon

PRODUCTS = [
    {'name':'The Studio Blazer','slug':'the-studio-blazer','sku':'ELV-BL-001','category':'tailoring','price':'189.00',
     'description':'A softly structured blazer with an effortless drape. Designed with a relaxed shoulder, considered proportions, and a timeless single-breasted closure.',
     'specifications':{'Colour':'Oat','Material':'Wool blend','Fit':'Relaxed','Care':'Dry clean only'},'image':'the-studio-blazer.jpg','featured':True,'new':False,'sizes':['XS','S','M','L']},
    {'name':'The Cashmere Knit','slug':'the-cashmere-knit','sku':'ELV-KN-001','category':'knitwear','price':'149.00',
     'description':'The kind of knit you reach for again and again. Soft, warm and beautifully simple, with a relaxed silhouette and fine ribbed details.',
     'specifications':{'Colour':'Ivory','Material':'Cashmere blend','Fit':'Relaxed','Care':'Hand wash cold'},'image':'the-cashmere-knit.jpg','featured':True,'new':True,'sizes':['XS','S','M','L']},
    {'name':'The Tailored Trouser','slug':'the-tailored-trouser','sku':'ELV-TR-001','category':'tailoring','price':'128.00',
     'description':'Fluid, full-length tailoring for every day. A considered high waist and wide-leg shape bring ease to a polished silhouette.',
     'specifications':{'Colour':'Chocolate','Material':'Wool blend','Fit':'Wide leg','Care':'Dry clean only'},'image':'the-tailored-trouser.jpg','featured':True,'new':False,'sizes':['XS','S','M','L']},
    {'name':'The Everyday Tote','slug':'the-everyday-tote','sku':'ELV-BG-001','category':'accessories','price':'198.00',
     'description':'A quiet statement in rich chocolate leather. Thoughtfully proportioned to hold your daily essentials, with graceful curved handles.',
     'specifications':{'Colour':'Chocolate','Material':'Leather','Dimensions':'32 × 27 × 12 cm','Care':'Wipe with a soft cloth'},'image':'the-everyday-tote.jpg','featured':True,'new':True,'sizes':[]},
    {'name':'The Wool Coat','slug':'the-wool-coat','sku':'ELV-CO-001','category':'outerwear','price':'248.00',
     'description':'A beautifully uncomplicated layer for cooler days. This longline wool-blend coat is cut to be worn season after season.',
     'specifications':{'Colour':'Taupe','Material':'Wool blend','Fit':'Relaxed','Care':'Dry clean only'},'image':'the-wool-coat.jpg','featured':False,'new':True,'sizes':['XS','S','M','L']},
    {'name':'The Poplin Shirt','slug':'the-poplin-shirt','sku':'ELV-SH-001','category':'clothing','price':'98.00',
     'description':'Crisp cotton poplin, reimagined for every day. A slightly oversized silhouette makes this wardrobe essential endlessly versatile.',
     'specifications':{'Colour':'Ivory','Material':'Cotton','Fit':'Relaxed','Care':'Machine wash cold'},'image':'the-poplin-shirt.jpg','featured':False,'new':True,'sizes':['XS','S','M','L']},
]

class Command(BaseCommand):
    help='Add optional demonstration catalogue content without overwriting existing products.'
    @transaction.atomic
    def handle(self,*args,**options):
        brand,_=Brand.objects.get_or_create(slug='elvaa-studio',defaults={'name':'ELVAA Studio'})
        clothing,_=Category.objects.get_or_create(slug='clothing',defaults={'name':'Clothing','display_order':1,'image_url':'/images/collection-essentials.jpg'})
        cats={'clothing':clothing}
        for slug,name,order in [('tailoring','Tailoring',2),('knitwear','Knitwear',3),('outerwear','Outerwear',4)]:
            cats[slug],_=Category.objects.get_or_create(slug=slug,defaults={'name':name,'parent':clothing,'display_order':order})
        cats['accessories'],_=Category.objects.get_or_create(slug='accessories',defaults={'name':'Accessories','display_order':5,'image_url':'/images/collection-accessories.jpg'})
        for item in PRODUCTS:
            p,created=Product.objects.get_or_create(slug=item['slug'],defaults={
                'name':item['name'],'sku':item['sku'],'category':cats[item['category']],'brand':brand,'price':item['price'],
                'description':item['description'],'specifications':item['specifications'],
                'stock':len(item['sizes'])*8 if item['sizes'] else 24,'is_active':True,
                'is_featured':item['featured'],'is_new':item['new'],'meta_title':f"{item['name']} | ELVAA"})
            if created:
                ProductImage.objects.create(product=p,image_url='/images/'+item['image'],alt=item['name'])
                for size in item['sizes']:
                    ProductVariant.objects.create(product=p,name=size,sku=f"{item['sku']}-{size}",stock=8,attributes={'size':size,'colour':item['specifications']['Colour']})
        StoreSettings.objects.get_or_create(pk=1,defaults={'free_shipping_threshold':'150.00','shipping_flat':'6.90','tax_rate':'19.00'})
        ShippingMethod.objects.get_or_create(name='Standard delivery',defaults={'price':'6.90','estimated_days':'3–5 business days','free_over_threshold':True})
        ShippingMethod.objects.get_or_create(name='Express delivery',defaults={'price':'12.90','estimated_days':'1–2 business days','free_over_threshold':False})
        if not Coupon.objects.filter(code__iexact='WELCOME10').exists():
            Coupon.objects.get_or_create(code='WELCOME10',defaults={'discount_type':'percent','discount_value':'10.00'})
        self.stdout.write(self.style.SUCCESS('Optional demo catalogue is ready.'))
