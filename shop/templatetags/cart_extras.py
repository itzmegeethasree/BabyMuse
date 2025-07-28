# shop/templatetags/cart_extras.py
import json
from django import template
from decimal import Decimal


register = template.Library()


@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def equals(val1, val2):
    """Returns True if val1 == val2 (as string), else False."""
    return str(val1) == str(val2)


@register.filter
def jsonify(queryset):
    from decimal import Decimal

    def handle_decimal(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return obj

    return json.dumps(list(queryset.values()), default=handle_decimal)
