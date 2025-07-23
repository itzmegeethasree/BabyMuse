from datetime import date
from django import forms
from .models import Address, BabyProfile
import re
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    firstname = forms.CharField(max_length=30, label="First Name")
    lastname = forms.CharField(
        max_length=30, required=False, label="Last Name")
    phone = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^(?!(\d)\1{9})(\+91)?[6-9]\d{9}$',
                message="Enter a valid Indian phone number"
            )
        ]
    )
    email = forms.EmailField(required=True)
    referral_code = forms.CharField(max_length=100, required=False)

    class Meta:
        model = CustomUser
        fields = ("username", "firstname", "lastname", "email",
                  "phone", "password1", "password2", "referral_code")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["firstname"]
        user.last_name = self.cleaned_data["lastname"]
        user.phone = self.cleaned_data["phone"]
        user.email = self.cleaned_data["email"]
        user.referral_code = self.cleaned_data.get("referral_code") or " "

        # Optionally handle referred_by logic here (based on referral_code)

        if commit:
            user.save()
        return user


def validate_image(image):
    file_size = image.size
    max_size = 2 * 1024 * 1024  # 2MB
    if file_size > max_size:
        raise ValidationError("Profile image must be under 2MB.")
    if not image.content_type.startswith("image/"):
        raise ValidationError("File must be an image.")


class CustomUserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)
    phone = forms.CharField(
        max_length=15,
        required=False,
        validators=[
            RegexValidator(
                regex=r'^(?!(\d)\1{9})(\+91)?[6-9]\d{9}$',
                message="Enter a valid Indian phone number"
            )
        ]
    )
    profile_image = forms.ImageField(
        required=False, validators=[validate_image])

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_image']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_id = self.instance.id
        if CustomUser.objects.filter(email=email).exclude(id=user_id).exists():
            raise ValidationError("This email is already in use.")
        return email


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'name', 'phone', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'is_default'
        ]

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        if len(name) < 3 or len(name) > 50:
            raise forms.ValidationError("Name must be 3–50 characters.")
        if not re.match(r'^[A-Za-z\s]+$', name):
            raise forms.ValidationError(
                "Name must only contain letters and spaces.")
        return name.title()

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.match(r'^[6-9]\d{9}$', phone):
            raise forms.ValidationError(
                "Enter a valid 10-digit Indian mobile number starting with 6-9.")
        if phone == phone[0] * 10:
            raise forms.ValidationError(
                "Phone number cannot have all same digits.")
        return phone

    def clean_postal_code(self):
        postal_code = self.cleaned_data.get('postal_code', '').strip()
        if not re.match(r'^\d{6}$', postal_code):
            raise forms.ValidationError(
                "Postal code must be exactly 6 digits.")
        if postal_code in ['000000', '111111', '999999']:
            raise forms.ValidationError("Enter a valid postal code.")
        if postal_code == postal_code[0] * 6:
            raise forms.ValidationError(
                "Postal code cannot have all same digits.")
        return postal_code

    def clean_address_line1(self):
        address1 = self.cleaned_data.get('address_line1', '').strip()
        if len(address1) < 5:
            raise forms.ValidationError(
                "Address Line 1 must be at least 5 characters.")
        return address1

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not re.match(r'^[A-Za-z\s]{2,}$', city):
            raise forms.ValidationError(
                "Enter a valid city name (letters only).")
        return city.title()

    def clean_state(self):
        state = self.cleaned_data.get('state', '').strip()
        if not re.match(r'^[A-Za-z\s]{2,}$', state):
            raise forms.ValidationError(
                "Enter a valid state name (letters only).")
        return state.title()


class BabyProfileForm(forms.ModelForm):
    class Meta:
        model = BabyProfile
        fields = ['baby_name', 'baby_dob', 'baby_gender',
                  'birth_weight', 'birth_height', 'notes']

        widgets = {
            'baby_dob': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_baby_name(self):
        name = self.cleaned_data.get('baby_name')
        if not name:
            raise forms.ValidationError("Baby name is required.")
        if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
            raise forms.ValidationError(
                "Name must contain only letters, spaces, apostrophes, or hyphens.")
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters.")
        return name.strip()

    def clean_baby_dob(self):
        dob = self.cleaned_data.get('baby_dob')
        if not dob:
            raise forms.ValidationError("Date of birth is required.")
        if dob > date.today():
            raise forms.ValidationError(
                "Date of birth cannot be in the future.")
        return dob

    def clean_notes(self):
        notes = self.cleaned_data.get('notes')
        if notes and len(notes) > 500:
            raise forms.ValidationError("Notes cannot exceed 500 characters.")
        return notes

    def clean_birth_weight(self):
        weight = self.cleaned_data.get('birth_weight')
        if weight is not None and (weight < 0.5 or weight > 6.0):
            raise forms.ValidationError(
                "Birth weight must be between 0.5kg and 6kg.")
        return weight

    def clean_birth_height(self):
        height = self.cleaned_data.get('birth_height')
        if height is not None and (height < 10 or height > 70):
            raise forms.ValidationError(
                "Birth height must be between 10cm and 70cm.")
        return height
