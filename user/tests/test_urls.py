from django.test import SimpleTestCase
from django.urls import reverse, resolve
from user import views

class UserURLsTest(SimpleTestCase):

    def test_user_register_url(self):
        url = reverse('user:user_register')
        self.assertEqual(resolve(url).func, views.user_register)

    def test_user_login_url(self):
        url = reverse('user:user_login')
        self.assertEqual(resolve(url).func, views.user_login)

    def test_user_logout_url(self):
        url = reverse('user:user_logout')
        self.assertEqual(resolve(url).func, views.user_logout)

    def test_signup_request_url(self):
        url = reverse('user:signup_request')
        self.assertEqual(resolve(url).func, views.otp_signup_request)

    def test_verify_otp_url(self):
        url = reverse('user:verify_otp')
        self.assertEqual(resolve(url).func, views.otp_verify)

    def test_resend_otp_url(self):
        url = reverse('user:resend_otp')
        self.assertEqual(resolve(url).func, views.resend_otp)

    def test_signup_url(self):
        url = reverse('user:signup')
        self.assertEqual(resolve(url).func, views.signup)

    def test_profile_url(self):
        url = reverse('user:profile')
        self.assertEqual(resolve(url).func, views.profile_view)

    def test_edit_profile_url(self):
        url = reverse('user:edit_profile')
        self.assertEqual(resolve(url).func, views.edit_profile)

    def test_verify_email_otp_url(self):
        url = reverse('user:verify_email_otp')
        self.assertEqual(resolve(url).func, views.verify_email_otp)

    def test_forgot_password_url(self):
        url = reverse('user:forgot_password')
        self.assertEqual(resolve(url).func, views.forgot_password)

    def test_verify_reset_otp_url(self):
        url = reverse('user:verify_reset_otp')
        self.assertEqual(resolve(url).func, views.verify_reset_otp)

    def test_resend_reset_otp_url(self):
        url = reverse('user:resend_reset_otp')
        self.assertEqual(resolve(url).func, views.resend_reset_otp)

    def test_reset_password_url(self):
        url = reverse('user:reset_password')
        self.assertEqual(resolve(url).func, views.reset_password)

    def test_change_password_url(self):
        url = reverse('user:change_password')
        self.assertEqual(resolve(url).func, views.change_password)

    def test_forgot_password1_url(self):
        url = reverse('user:forgot_password1')
        self.assertEqual(resolve(url).func, views.otp_signup_request)

    def test_address_book_url(self):
        url = reverse('user:address_book')
        self.assertEqual(resolve(url).func, views.address_book)

    def test_add_address_url(self):
        url = reverse('user:add_address')
        self.assertEqual(resolve(url).func, views.add_address)

    def test_edit_address_url(self):
        url = reverse('user:edit_address', args=[1])
        self.assertEqual(resolve(url).func, views.edit_address)

    def test_delete_address_url(self):
        url = reverse('user:delete_address', args=[1])
        self.assertEqual(resolve(url).func, views.delete_address)

    def test_add_baby_profile_url(self):
        url = reverse('user:add_baby_profile')
        self.assertEqual(resolve(url).func, views.add_baby_profile)

    def test_edit_baby_profile_url(self):
        url = reverse('user:edit_baby_profile', args=[1])
        self.assertEqual(resolve(url).func, views.edit_baby_profile)

    def test_delete_baby_profile_url(self):
        url = reverse('user:delete_baby_profile', args=[1])
        self.assertEqual(resolve(url).func, views.delete_baby_profile)

    def test_user_wallet_url(self):
        url = reverse('user:user_wallet')
        self.assertEqual(resolve(url).func, views.user_wallet_view)

    def test_create_wallet_order_url(self):
        url = reverse('user:create_order')
        self.assertEqual(resolve(url).func, views.create_wallet_order)

    def test_wallet_payment_success_url(self):
        url = reverse('user:payment_success')
        self.assertEqual(resolve(url).func, views.wallet_payment_success)