from django.utils import timezone
from orders.models import Coupon

def validate_coupon(code, cart_total):
    try:
        coupon = Coupon.objects.get(
            code__iexact=code, active=True, is_deleted=False
        )
    except Coupon.DoesNotExist:
        return None, "Invalid coupon code."

    now = timezone.now()

    # Check validity period
    if not (coupon.valid_from <= now <= coupon.valid_to):
        return None, "This coupon is not valid at this time."

    # Check minimum cart amount
    if cart_total < coupon.minimum_amount:
        return None, f"Minimum order amount for this coupon is ₹{coupon.minimum_amount}."

    # Check usage limit
    if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
        return None, "This coupon has reached its usage limit."

    # Calculate discount
    if coupon.is_percentage:
        discount = (coupon.discount / 100) * cart_total
        if coupon.max_discount_amount:
            discount = min(discount, coupon.max_discount_amount)
    else:
        discount = coupon.discount

    return {
        'coupon': coupon,
        'discount': round(min(discount, cart_total), 2)
    }, None