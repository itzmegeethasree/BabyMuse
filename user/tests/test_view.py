from django.test import TestCase, Client
from django.urls import reverse
from user.models import CustomUser, BabyProfile
from datetime import date


class BabyProfileViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            email='test@example.com', password='testpass')
        self.client.login(email='test@example.com', password='testpass')

    def test_baby_profile_list_view(self):
        response = self.client.get(reverse('user:baby_profile_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user/baby_profile_list.html')

    def test_add_baby_profile(self):
        response = self.client.post(reverse('user:add_baby_profile'), {
            'name': 'New Baby',
            'date_of_birth': '2022-05-05',
            'notes': 'Loves to giggle'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect
        self.assertTrue(BabyProfile.objects.filter(name='New Baby').exists())

    def test_delete_baby_profile(self):
        baby = BabyProfile.objects.create(
            user=self.user, name='Temp Baby', date_of_birth=date(2022, 1, 1))
        response = self.client.post(
            reverse('user:delete_baby_profile', args=[baby.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BabyProfile.objects.filter(id=baby.id).exists())
