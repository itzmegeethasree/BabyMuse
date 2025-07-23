from django.test import SimpleTestCase
from django.urls import reverse, resolve
from user.views import (
    BabyProfileListView, AddBabyProfileView, DeleteBabyProfileView
)


class UserURLsTest(SimpleTestCase):
    def test_baby_profile_list_url_resolves(self):
        url = reverse('user:baby_profile_list')
        self.assertEqual(resolve(url).func.view_class, BabyProfileListView)

    def test_add_baby_profile_url_resolves(self):
        url = reverse('user:add_baby_profile')
        self.assertEqual(resolve(url).func.view_class, AddBabyProfileView)

    def test_delete_baby_profile_url_resolves(self):
        url = reverse('user:delete_baby_profile', args=[1])
        self.assertEqual(resolve(url).func.view_class, DeleteBabyProfileView)
