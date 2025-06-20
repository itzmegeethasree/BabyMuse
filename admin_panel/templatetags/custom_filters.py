from django import template

register = template.Library()


@register.filter
def equals_id(val1, val2):
    return str(val1) == str(val2)
