from django.conf import settings
from django.utils.text import slugify
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator


User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    offer_percentage = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.parent:
            return f"{self.parent} → {self.name}"
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True)
    description = models.TextField(default='No description provided')
    min_age = models.PositiveIntegerField(
        null=True, blank=True, help_text="Minimum age in months (0-36)")
    max_age = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum age in months (0-36)")
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Unisex', 'Unisex')],
        default='Unisex'
    )
    brand = models.ForeignKey(
        'Brand', on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=[(
        'Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    product_offer_percentage = models.PositiveIntegerField(
        default=0)
    views = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_listed = models.BooleanField(default=True)

    def get_offer_price(self):
        product_offer = self.product_offer_percentage
        category_offer = self.category.offer_percentage if self.category else 0
        best_offer = max(product_offer, category_offer)
        return self.price - (self.price * best_offer / 100)

    def get_active_offer(self):
        product_offer = self.product_offer_percentage
        category_offer = self.category.offer_percentage if self.category else 0
        if product_offer >= category_offer:
            return ('Product Offer', product_offer)
        return ('Category Offer', category_offer)

    def __str__(self):
        return self.name

    @property
    def total_stock(self):
        return sum(variant.stock for variant in self.variants.all())

    @property
    def primary_image(self):
        first_image = self.images.first()
        return first_image.image.url if first_image else '/static/images/default-img.jpg'


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')

    def save(self, *args, **kwargs):
        # Save original first to get file path
        super().save(*args, **kwargs)


class VariantAttribute(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class VariantOption(models.Model):
    attribute = models.ForeignKey(
        VariantAttribute, on_delete=models.CASCADE, related_name='options')
    value = models.CharField(max_length=50)

    class Meta:
        unique_together = ('attribute', 'value')

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='variants')
    options = models.ManyToManyField(VariantOption)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(
        upload_to='variant_images/', blank=True, null=True)

    class Meta:
        unique_together = ('product', 'sku')

    def __str__(self):
        return f"{self.product.name} - {', '.join([opt.value for opt in self.options.all()])}"

    def get_offer_price(self):
        product_offer = self.product.product_offer_percentage
        category_offer = self.product.category.offer_percentage if self.product.category else 0
        best_offer = max(product_offer, category_offer)
        return self.price - (self.price * best_offer / 100)


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)
    variant = models.ForeignKey(
        ProductVariant, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('user', 'variant')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name='cart_items')
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.quantity * self.product_variant.get_offer_price()

    def __str__(self):
        return f"{self.quantity} x {self.product_variant} ({self.user.email})"

    class Meta:
        unique_together = ('user', 'product_variant')
        ordering = ['-added_at']


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=5, validators=[
                                 MinValueValidator(1), MaxValueValidator(5)])


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
