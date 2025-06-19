from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from PIL import Image
import os
from django.core.files.base import ContentFile
from io import BytesIO


User = get_user_model()


ORDER_STATUS = [
    ('Pending', 'Pending'),
    ('Processing', 'Processing'),
    ('Shipped', 'Shipped'),
    ('Delivered', 'Delivered'),
    ('Cancelled', 'Cancelled'),
    ('Paid', 'Paid'),
]


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True)
    description = models.TextField(default='No description provided')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=[(
        'Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        first_image = self.images.first()
        return first_image.image.url if first_image else '/static/images/default-img.jpg'


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')

    def save(self, *args, **kwargs):
        # Save original first
        super().save(*args, **kwargs)

        # Open the uploaded image
        img_path = self.image.path
        img = Image.open(img_path)

        # Define desired size and crop center
        desired_size = (600, 600)
        img = self.crop_center(img)
        img = img.resize(desired_size, Image.ANTIALIAS)

        # Save it back to the same file
        img.save(img_path)

    def crop_center(self, img):
        width, height = img.size
        new_edge = min(width, height)  # Crop to square
        left = (width - new_edge) // 2
        top = (height - new_edge) // 2
        right = (width + new_edge) // 2
        bottom = (height + new_edge) // 2
        return img.crop((left, top, right, bottom))


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50, choices=ORDER_STATUS, default='Pending')
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.user.email})"

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']
