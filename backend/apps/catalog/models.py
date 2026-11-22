from django.db import models
from django.core.validators import MinValueValidator,MaxValueValidator
from django.utils.text import slugify

class Brand(models.Model):
    name=models.CharField(max_length=120,unique=True)
    slug=models.SlugField(unique=True,blank=True)
    def save(self,*args,**kwargs): self.slug=self.slug or slugify(self.name); super().save(*args,**kwargs)
    def __str__(self): return self.name

class Category(models.Model):
    name=models.CharField(max_length=120)
    slug=models.SlugField(unique=True,blank=True)
    parent=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='children')
    image=models.ImageField(upload_to='categories/',blank=True,null=True)
    image_url=models.CharField(max_length=500,blank=True)
    display_order=models.PositiveIntegerField(default=0)
    is_active=models.BooleanField(default=True)
    class Meta: ordering=['display_order','name']; verbose_name_plural='categories'
    def save(self,*args,**kwargs): self.slug=self.slug or slugify(self.name); super().save(*args,**kwargs)
    def __str__(self): return self.name

class Product(models.Model):
    name=models.CharField(max_length=255)
    slug=models.SlugField(unique=True,blank=True)
    brand=models.ForeignKey(Brand,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
    category=models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,blank=True,related_name='products')
    description=models.TextField(blank=True)
    specifications=models.JSONField(default=dict,blank=True)
    price=models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0)])
    compare_at_price=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    stock=models.PositiveIntegerField(default=0)
    sku=models.CharField(max_length=64,unique=True)
    is_active=models.BooleanField(default=True)
    is_featured=models.BooleanField(default=False)
    is_new=models.BooleanField(default=False)
    meta_title=models.CharField(max_length=255,blank=True)
    meta_description=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-created_at']; indexes=[models.Index(fields=['is_active','is_featured']),models.Index(fields=['category','is_active'])]
    def save(self,*args,**kwargs): self.slug=self.slug or slugify(self.name); super().save(*args,**kwargs)
    def __str__(self): return self.name

class ProductImage(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='images')
    image=models.ImageField(upload_to='products/',blank=True,null=True)
    image_url=models.CharField(max_length=500,blank=True,help_text='Relative asset path or public HTTPS image URL.')
    alt=models.CharField(max_length=255,blank=True)
    display_order=models.PositiveIntegerField(default=0)
    class Meta: ordering=['display_order','id']
    def __str__(self): return f'{self.product.name} image'

class ProductVariant(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='variants')
    name=models.CharField(max_length=120)
    sku=models.CharField(max_length=64,unique=True)
    price=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    stock=models.PositiveIntegerField(default=0)
    attributes=models.JSONField(default=dict,blank=True)
    class Meta: ordering=['id']; constraints=[models.UniqueConstraint(fields=['product','name'],name='unique_variant_name_per_product')]
    def __str__(self): return f'{self.product.name} — {self.name}'

class Review(models.Model):
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='reviews')
    user=models.ForeignKey('accounts.User',on_delete=models.CASCADE)
    rating=models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    title=models.CharField(max_length=255,blank=True)
    body=models.TextField(blank=True)
    is_approved=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']; constraints=[models.UniqueConstraint(fields=['product','user'],name='one_review_per_product_user')]

class Wishlist(models.Model):
    user=models.ForeignKey('accounts.User',on_delete=models.CASCADE,related_name='wishlist')
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name='wishlisted_by')
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']; constraints=[models.UniqueConstraint(fields=['user','product'],name='one_wishlist_product_per_user')]

class InventoryMovement(models.Model):
    product=models.ForeignKey(Product,on_delete=models.SET_NULL,null=True,blank=True,related_name='inventory_movements')
    variant=models.ForeignKey(ProductVariant,on_delete=models.SET_NULL,null=True,blank=True,related_name='inventory_movements')
    product_name_snapshot=models.CharField(max_length=255,blank=True)
    variant_name_snapshot=models.CharField(max_length=120,blank=True)
    quantity_change=models.IntegerField()
    reason=models.CharField(max_length=120)
    reference=models.CharField(max_length=100,blank=True)
    actor=models.ForeignKey('accounts.User',on_delete=models.SET_NULL,null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']; indexes=[models.Index(fields=['product','created_at'])]
    def save(self,*args,**kwargs):
        if self.product_id and not self.product_name_snapshot: self.product_name_snapshot=self.product.name
        if self.variant_id and not self.variant_name_snapshot: self.variant_name_snapshot=self.variant.name
        super().save(*args,**kwargs)
