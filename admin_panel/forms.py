from django import forms
from shop.models import Product
from .widgets import MultiFileInput  # import the custom widget

class ProductForm(forms.ModelForm):
    images = forms.FileField(widget=MultiFileInput(), required=True)

    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'stock', 'status']

    def clean_images(self):
        images = self.files.getlist('images')
        if len(images) != 3:
            raise forms.ValidationError("Please upload exactly 3 images.")
        return images
