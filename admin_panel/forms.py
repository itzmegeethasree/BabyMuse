from django.forms import inlineformset_factory
from core.models import Banner
from shop.models import Product, ProductVariant, Category, VariantOption
from django import forms
from .widgets import MultiFileInput
from orders.models import Coupon
import re
from django.utils.text import slugify


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'parent',
                  'offer_percentage', 'is_active']

    def clean_name(self):
        name = self.cleaned_data['name']
        if not name or not isinstance(name, str):
            raise forms.ValidationError(
                "Category name is required and must be a string .")
        if len(name.strip()) < 3:
            raise forms.ValidationError(
                "Category name must be at least 3 characters.")
        if not re.search(r"^[a-zA-Z]", name):
            raise forms.ValidationError(
                "Name can contains atleast one character.")

        return name.strip()

    def clean_description(self):
        desc = self.cleaned_data.get('description', '')
        if desc and len(desc.strip()) < 5:
            raise forms.ValidationError(
                "Description must be at least 5 characters if provided.")
        return desc.strip()

    def clean_offer_percentage(self):
        offer = self.cleaned_data.get('offer_percentage', 0)
        if offer < 0 or offer > 100:
            raise forms.ValidationError("Offer must be between 0 and 100%.")
        return offer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter out deleted categories from parent field
        self.fields['parent'].queryset = Category.objects.filter(
            is_deleted=False)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category',  'description',
            'min_age', 'max_age', 'gender',
            'is_featured', 'is_listed', 'status', 'product_offer_percentage'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'description': forms.Textarea(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'category': forms.Select(attrs={
                'class': 'border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-400'
            }),
            'min_age': forms.NumberInput(attrs={'class': 'border border-gray-300 rounded focus:ring-blue-400'}),
            'max_age': forms.NumberInput(attrs={'class': 'border border-gray-300 rounded focus:ring-blue-400'}),
            'gender': forms.Select(attrs={'class': 'border border-gray-300 rounded  focus:ring-blue-400'}),
            'product_offer_percentage': forms.NumberInput(attrs={'class': 'border border-gray-300 rounded focus:ring-blue-400'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name.replace(" ", "").isalpha():
            raise forms.ValidationError(
                "Product name must only contain letters and spaces.")
        return name

    def clean_min_age(self):
        min_age = self.cleaned_data.get('min_age')
        if min_age < 0 or min_age > 34:
            raise forms.ValidationError("age must be between 0 and 34 months")
        return min_age

    def clean_max_age(self):
        max_age = self.cleaned_data.get('min_age')
        if max_age < 0 or max_age > 34:
            raise forms.ValidationError("age must be between 0 and 34 months.")
        return max_age


class MultiFileUploadForm(forms.Form):
    images = forms.FileField(
        widget=MultiFileInput,
        required=True
    )

    def clean_images(self):
        files = self.files.getlist('images')
        if len(files) < 3:
            raise forms.ValidationError("Please upload at least 3 images.")
        return files


class ProductVariantForm(forms.ModelForm):
    options = forms.ModelMultipleChoiceField(
        queryset=VariantOption.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = ProductVariant
        fields = ['options', 'sku', 'price', 'stock']


ProductVariantFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductVariant,
    form=ProductVariantForm,
    extra=1,
    can_delete=True
)


class VariantComboForm(forms.Form):
    size = forms.ModelChoiceField(queryset=VariantOption.objects.none())
    color = forms.ModelChoiceField(queryset=VariantOption.objects.none())
    sku = forms.CharField(required=False)
    price = forms.DecimalField()
    stock = forms.IntegerField()

    def __init__(self, *args, size_qs=None, color_qs=None, existing_combos=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Use size_qs and color_qs to set queryset for fields if needed
        if size_qs is not None:
            self.fields['size'].queryset = size_qs
        if color_qs is not None:
            self.fields['color'].queryset = color_qs
        self.existing_combos = existing_combos if existing_combos is not None else set()

    def clean(self):
        cleaned = super().clean()
        size = cleaned.get('size')
        color = cleaned.get('color')
        sku = cleaned.get('sku')
        # Pass product_id in initial if needed
        product_id = self.initial.get('product_id')

        # Check for duplicate variant combination
        combo_key = f"{size.id}-{color.id}" if size and color else None
        if combo_key and combo_key in self.existing_combos:
            raise forms.ValidationError(
                "Duplicate variant combination (size/color) detected.")
        self.existing_combos.add(combo_key)

        # Generate SKU if missing
        name = self.initial.get('product_name', '')
        if not sku:
            base = slugify(name)[:6]
            sku = f"{base}-{size.value[:2].upper()}-{color.value[:2].upper()}"
            cleaned['sku'] = sku

        # Check SKU uniqueness for this product, excluding current variant if editing
        if sku and product_id:
            # Try to get the current variant id from initial (if editing)
            current_variant_id = self.initial.get('variant_id')
            qs = ProductVariant.objects.filter(product_id=product_id, sku=sku)
            if current_variant_id:
                qs = qs.exclude(id=current_variant_id)
            if qs.exists():
                raise forms.ValidationError(
                    f"SKU '{sku}' already exists for this product.")

        return cleaned


class ProductOfferForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category',
                  'product_offer_percentage']


class CategoryOfferForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name',  'parent', 'offer_percentage']


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


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ['title', 'image', 'link',
                  'is_active', 'age_min', 'age_max', 'gender']

    def clean(self):
        cleaned_data = super().clean()
        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        if age_min and age_max and age_min > age_max:
            raise forms.ValidationError(
                "Minimum age cannot be greater than maximum age.")
        return cleaned_data
