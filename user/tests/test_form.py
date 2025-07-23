from django.test import TestCase
from user.forms import BabyProfileForm
from datetime import date


class BabyProfileFormTests(TestCase):
    def test_valid_data(self):
        form = BabyProfileForm(data={
            'name': 'Baby John',
            'date_of_birth': '2023-05-01',
            'notes': 'Healthy baby'
        })
        self.assertTrue(form.is_valid())

    def test_name_required(self):
        form = BabyProfileForm(data={
            'date_of_birth': '2023-01-01'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_date_in_future_invalid(self):
        future_date = date.today().replace(year=date.today().year + 1)
        form = BabyProfileForm(data={
            'name': 'Baby X',
            'date_of_birth': future_date
        })
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)
