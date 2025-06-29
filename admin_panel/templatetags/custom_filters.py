from django import template

register = template.Library()


@register.filter
def equals_id(val1, val2):
    return str(val1) == str(val2)


@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
