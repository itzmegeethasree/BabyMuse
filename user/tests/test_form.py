from django.test import TestCase
from user.forms import (
    CustomUserCreationForm, CustomUserUpdateForm,
    AddressForm, BabyProfileForm
)
from user.models import CustomUser
from datetime import date, timedelta
from django.core.files.uploadedfile import SimpleUploadedFile


class CustomUserCreationFormTests(TestCase):
    def test_valid_user_creation(self):
        form = CustomUserCreationForm(data={
            'username': 'geetha',
            'firstname': 'Geetha',
            'lastname': 'Sree',
            'email': 'geetha@example.com',
            'phone': '9876543210',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'referral_code': 'REF123'
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.first_name, 'Geetha')
        self.assertEqual(user.phone, '9876543210')

    def test_invalid_phone(self):
        form = CustomUserCreationForm(data={
            'username': 'geetha',
            'firstname': 'Geetha',
            'email': 'geetha@example.com',
            'phone': '1111111111',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)


class CustomUserUpdateFormTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='updateuser',
            email='update@example.com',
            password='pass'
        )

    def test_valid_update(self):
        form = CustomUserUpdateForm(data={
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'new@example.com',
            'phone': '9876543210'
        }, instance=self.user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()
        self.assertEqual(updated_user.email, 'new@example.com')

    def test_duplicate_email(self):
        CustomUser.objects.create_user(
            username='otheruser',
            email='taken@example.com',
            password='pass'
        )
        form = CustomUserUpdateForm(data={
            'first_name': 'Test',
            'email': 'taken@example.com',
            'phone': '9876543210'
        }, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_invalid_image(self):
        fake_file = SimpleUploadedFile("test.txt", b"not an image", content_type="text/plain")
        form = CustomUserUpdateForm(data={
            'first_name': 'Test',
            'email': 'valid@example.com',
            'phone': '9876543210'
        }, files={'profile_image': fake_file}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('profile_image', form.errors)


class AddressFormTests(TestCase):
    def test_valid_address(self):
        form = AddressForm(data={
            'name': 'Geetha S',
            'phone': '9876543210',
            'address_line1': '123 Baby Street',
            'address_line2': 'Near Park',
            'city': 'Kottakkal',
            'state': 'Kerala',
            'postal_code': '676503',
            'is_default': True
        })
        self.assertTrue(form.is_valid())

    def test_invalid_postal_code(self):
        form = AddressForm(data={
            'name': 'Geetha',
            'phone': '9876543210',
            'address_line1': '123 Street',
            'city': 'City',
            'state': 'State',
            'postal_code': '111111'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('postal_code', form.errors)

    def test_invalid_name(self):
        form = AddressForm(data={
            'name': '12',
            'phone': '9876543210',
            'address_line1': '123 Street',
            'city': 'City',
            'state': 'State',
            'postal_code': '676503'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class BabyProfileFormTests(TestCase):
    def test_valid_baby_profile(self):
        form = BabyProfileForm(data={
            'baby_name': 'Baby Muse',
            'baby_dob': '2023-01-01',
            'baby_gender': 'Female',
            'birth_weight': 3.2,
            'birth_height': 50.0,
            'notes': 'Sleeps well'
        })
        self.assertTrue(form.is_valid())

    def test_future_dob(self):
        future_date = (date.today() + timedelta(days=30)).isoformat()
        form = BabyProfileForm(data={
            'baby_name': 'Future Baby',
            'baby_dob': future_date
        })
        self.assertFalse(form.is_valid())
        self.assertIn('baby_dob', form.errors)

    def test_invalid_weight(self):
        form = BabyProfileForm(data={
            'baby_name': 'Heavy Baby',
            'baby_dob': '2023-01-01',
            'birth_weight': 7.0
        })
        self.assertFalse(form.is_valid())
        self.assertIn('birth_weight', form.errors)

    def test_invalid_height(self):
        form = BabyProfileForm(data={
            'baby_name': 'Tiny Baby',
            'baby_dob': '2023-01-01',
            'birth_height': 5.0
        })
        self.assertFalse(form.is_valid())
        self.assertIn('birth_height', form.errors)