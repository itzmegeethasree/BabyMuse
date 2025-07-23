from django import forms
from shop.models import Product
from .widgets import MultiFileInput
from orders.models import Coupon


class ProductForm(forms.ModelForm):
    images = forms.FileField(
        widget=MultiFileInput(attrs={'multiple': True}),
        required=True,
        label="Product Images"
    )

    class Meta:
        model = Product
        fields = ['name', 'category', 'description',
                  'price', 'stock', 'status']

    def clean_images(self):
        images = self.files.getlist('images')
        if len(images) != 3:
            raise forms.ValidationError("Please upload exactly 3 images.")
        return images


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'discount', 'is_percentage',
            'minimum_amount', 'max_discount_amount',
            'valid_from', 'valid_to', 'active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'w-full border p-2 rounded'}),
            'discount': forms.NumberInput(attrs={'class': 'w-full border p-2 rounded'}),
            'is_percentage': forms.CheckboxInput(attrs={'class': 'h-4 w-4'}),
            'minimum_amount': forms.NumberInput(attrs={'class': 'w-full border p-2 rounded'}),
            'max_discount_amount': forms.NumberInput(attrs={'class': 'w-full border p-2 rounded'}),
            'valid_from': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full border p-2 rounded'
            }),
            'valid_to': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full border p-2 rounded'
            }),
            'active': forms.CheckboxInput(attrs={'class': 'h-4 w-4'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        discount = cleaned_data.get("discount")
        is_percentage = cleaned_data.get("is_percentage")
        max_discount_amount = cleaned_data.get("max_discount_amount")

        if is_percentage and (discount > 100 or discount <= 0):
            self.add_error(
                "discount", "Percentage discount must be between 0 and 100.")

        if is_percentage and not max_discount_amount:
            self.add_error(
                "max_discount_amount", "Maximum discount amount is required for percentage coupons.")

        valid_from = cleaned_data.get("valid_from")
        valid_to = cleaned_data.get("valid_to")
        if valid_from and valid_to and valid_to <= valid_from:
            self.add_error("valid_to", "Valid to must be after valid from.")
