from django.contrib import admin
from shop.models import VariantAttribute,VariantOption

# Register your models here.
admin.site.register(VariantAttribute)
admin.site.register(VariantOption)