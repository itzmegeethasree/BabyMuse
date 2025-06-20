from django import template

register = template.Library()


@register.filter
def equals_str(val1, val2):
    return str(val1) == str(val2)
