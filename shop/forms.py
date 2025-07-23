
from django import forms
from shop.models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'parent', 'is_active']


class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'product_offer_percentage']


class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'offer_percentage']
