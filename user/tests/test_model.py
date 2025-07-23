from django.test import TestCase
from user.models import BabyProfile, CustomUser
from datetime import date


class BabyProfileModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='test@example.com', password='testpass')

    def test_create_baby_profile(self):
        baby = BabyProfile.objects.create(
            user=self.user,
            name='Baby Alice',
            date_of_birth=date(2022, 8, 20),
            notes='Loves toys'
        )
        self.assertEqual(str(baby), 'Baby Alice')
        self.assertEqual(baby.user.email, 'test@example.com')
