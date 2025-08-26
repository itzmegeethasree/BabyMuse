from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from shop.models import Product, ProductVariant
from user.models import Address


User = get_user_model()
ORDER_STATUS = [
    ('Pending', 'Pending'),
    ('Processing', 'Processing'),
    ('Shipped', 'Shipped'),
    ('Delivered', 'Delivered'),
    ('Completed', 'Completed')
]


class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount = models.DecimalField(
        max_digits=6, decimal_places=2)  # e.g. 10 or 10%
    # True = percentage, False = fixed
    is_percentage = models.BooleanField(default=False)

    active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    minimum_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    # Maximum number of times this coupon can be used
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Max times this coupon can be used")

    # Track how many times it's been used
    times_used = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Optional: Assign to specific user"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_expired(self):
        return timezone.now() > self.valid_to

    def status(self):
        now = timezone.now()
        if self.is_deleted or not self.active:
            return "Inactive"
        elif now < self.valid_from:
            return "Upcoming"
        elif now > self.valid_to:
            return "Expired"
        return "Active"

    def calculate_discount(self, order_total):
        """
        Returns the discount amount based on order_total and coupon settings.
        """
        if self.is_percentage:
            discount = order_total * (self.discount / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount

        return min(discount, order_total)  # Prevent exceeding total


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50, choices=ORDER_STATUS, default='Pending')
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, null=True)
    payment_method = models.CharField(max_length=20, default='COD')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    order_id = models.CharField(
        max_length=20, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.order_id:
            latest_id = Order.objects.count() + 1
            self.order_id = f"BM{latest_id:06d}"  # BM000001 style
        super().save(*args, **kwargs)

    def update_status_from_items(self):
        item_statuses = list(self.items.values_list('status', flat=True))
        unique_statuses = set(item_statuses)

        if not item_statuses:
            self.status = 'Pending'

        elif unique_statuses == {'Delivered'}:
            self.status = 'Delivered'

        elif unique_statuses == {'Completed'}:
            self.status = 'Completed'

        elif unique_statuses == {'Cancelled'}:
            self.status = 'Cancelled'

        elif unique_statuses == {'Returned'}:
            self.status = 'Returned'

        elif unique_statuses == {'Shipped'}:
            self.status = 'Shipped'

        elif unique_statuses == {'Processing'}:
            self.status = 'Processing'

        elif 'Returned' in unique_statuses and len(unique_statuses) > 1:
            self.status = 'Partially Returned'

        elif 'Cancelled' in unique_statuses and len(unique_statuses) > 1:
            self.status = 'Partially Cancelled'

        elif 'Delivered' in unique_statuses and len(unique_statuses) > 1:
            self.status = 'Partially Delivered'

        else:
            self.status = 'Processing'

        self.save(update_fields=['status'])

    def __str__(self):
        return f"Order #{self.order_id or self.id} - {self.user.username}"


class OrderItem(models.Model):
    STATUS_CHOICES = [('Pending', 'Pending'),
                      ('Processing', 'Processing'),
                      ('Shipped', 'Shipped'),
                      ('Delivered', 'Delivered'),
                      ('Cancelled', 'Cancelled'),
                      ('Returned', 'Returned'),
                      ('Completed', 'Completed')]
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='Pending')

    def subtotal(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.update_status_from_items()


class ReturnRequest(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='return_requests')
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    refunded_to_wallet = models.BooleanField(default=False)

    def __str__(self):
        return f"Return for Order {self.order.order_id} - Approved: {self.approved}"
