from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from user.models import BabyProfile, CustomUser, Address, WalletTransaction
from orders.models import Coupon
from django.utils import timezone
from datetime import timedelta

class UserViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='geetha',
            email='geetha@example.com',
            password='securepass'
        )
        self.client.login(username='geetha', password='securepass')

    def test_profile_view_generates_referral_code(self):
        self.user.referral_code = ''
        self.user.save()
        response = self.client.get(reverse('user:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.referral_code)
        self.assertEqual(response.status_code, 200)

    def test_change_password_success(self):
        response = self.client.post(reverse('user:change_password'), {
            'old_password': 'securepass',
            'new_password': 'newsecurepass',
            'confirm_password': 'newsecurepass'
        })
        self.assertRedirects(response, reverse('user:user_login'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newsecurepass'))

    def test_change_password_mismatch(self):
        response = self.client.post(reverse('user:change_password'), {
            'old_password': 'securepass',
            'new_password': 'newpass',
            'confirm_password': 'wrongpass'
        })
        self.assertContains(response, "New passwords do not match.")

    def test_edit_profile_triggers_email_otp(self):
        response = self.client.post(reverse('user:edit_profile'), {
            'first_name': 'Geetha',
            'last_name': 'Sree',
            'email': 'new@example.com',
            'phone': '9876543210'
        })
        session = self.client.session
        self.assertIn('email_otp', session)
        self.assertRedirects(response, reverse('user:verify_email_otp'))

    def test_verify_email_otp_success(self):
        session = self.client.session
        session['email_otp'] = '123456'
        session['new_email'] = 'verified@example.com'
        session['otp_sent_time'] = timezone.now().isoformat()
        session.save()

        response = self.client.post(reverse('user:verify_email_otp'), {
            'otp': '123456'
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'verified@example.com')
        self.assertRedirects(response, reverse('user:edit_profile'))

    def test_add_address_valid(self):
        response = self.client.post(reverse('user:add_address'), {
            'name': 'Geetha S',
            'phone': '9876543210',
            'address_line1': '123 Baby Street',
            'address_line2': 'Near Park',
            'city': 'Kottakkal',
            'state': 'Kerala',
            'postal_code': '676503',
            'is_default': True
        })
        self.assertRedirects(response, reverse('user:address_book'))
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)

    def test_edit_address(self):
        address = Address.objects.create(
            user=self.user,
            name='Old Name',
            phone='9876543210',
            address_line1='Old Street',
            city='Old City',
            state='Old State',
            postal_code='676503'
        )
        response = self.client.post(reverse('user:edit_address', args=[address.id]), {
            'name': 'New Name',
            'phone': '9876543210',
            'address_line1': 'New Street',
            'city': 'New City',
            'state': 'New State',
            'postal_code': '676503'
        })
        address.refresh_from_db()
        self.assertEqual(address.name, 'New Name')

    def test_delete_address(self):
        address = Address.objects.create(
            user=self.user,
            name='To Delete',
            phone='9876543210',
            address_line1='Street',
            city='City',
            state='State',
            postal_code='676503'
        )
        response = self.client.post(reverse('user:delete_address', args=[address.id]))
        self.assertRedirects(response, reverse('user:address_book'))
        self.assertFalse(Address.objects.filter(id=address.id).exists())

    def test_forgot_password_sets_session(self):
        response = self.client.post(reverse('user:forgot_password'), {
            'email': 'geetha@example.com'
        })
        session = self.client.session
        self.assertIn('reset_email', session)
        self.assertIn('reset_otp', session)
        self.assertRedirects(response, reverse('user:verify_reset_otp'))

    def test_verify_reset_otp_success(self):
        session = self.client.session
        session['reset_email'] = 'geetha@example.com'
        session['reset_otp'] = '654321'
        session['otp_expiry'] = (timezone.now() + timedelta(minutes=1)).isoformat()
        session.save()

        response = self.client.post(reverse('user:verify_reset_otp'), {
            'otp': '654321'
        })
        self.assertRedirects(response, reverse('user:reset_password'))

    def test_reset_password_success(self):
        session = self.client.session
        session['reset_email'] = 'geetha@example.com'
        session.save()

        response = self.client.post(reverse('user:reset_password'), {
            'password1': 'newpass123',
            'password2': 'newpass123'
        })
        self.assertRedirects(response, reverse('user:user_login'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))



class BabyProfileAndWalletTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='geetha',
            email='geetha@example.com',
            password='securepass'
        )
        self.client.login(username='geetha', password='securepass')

    def test_add_baby_profile(self):
        response = self.client.post(reverse('user:add_baby_profile'), {
            'baby_name': 'Baby Muse',
            'baby_dob': '2023-01-01',
            'baby_gender': 'Female',
            'birth_weight': 3.2,
            'birth_height': 50.0,
            'notes': 'Sleeps peacefully'
        })
        self.assertRedirects(response, reverse('user:profile'))
        self.assertEqual(BabyProfile.objects.filter(user=self.user).count(), 1)

    def test_edit_baby_profile(self):
        baby = BabyProfile.objects.create(
            user=self.user,
            baby_name='Old Name',
            baby_dob='2023-01-01'
        )
        response = self.client.post(reverse('user:edit_baby_profile', args=[baby.id]), {
            'baby_name': 'New Name',
            'baby_dob': '2023-01-01',
            'baby_gender': 'Female',
            'birth_weight': 3.0,
            'birth_height': 48.0
        })
        baby.refresh_from_db()
        self.assertEqual(baby.baby_name, 'New Name')

    def test_delete_baby_profile(self):
        baby = BabyProfile.objects.create(
            user=self.user,
            baby_name='To Delete',
            baby_dob='2023-01-01'
        )
        response = self.client.post(reverse('user:delete_baby_profile', args=[baby.id]))
        self.assertRedirects(response, reverse('user:profile'))
        self.assertFalse(BabyProfile.objects.filter(id=baby.id).exists())

    def test_user_wallet_view(self):
        response = self.client.get(reverse('user:user_wallet'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('wallet', response.context)
        self.assertIn('transactions', response.context)
        self.assertEqual(response.context['wallet'].user, self.user)

    @patch('razorpay.Client')
    def test_create_wallet_order(self, mock_client_class):
        mock_client_instance = mock_client_class.return_value
        mock_client_instance.order.create.return_value = {'id': 'order_xyz'}

        response = self.client.post(reverse('user:create_order'), {
        'amount': '500'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['order_id'], 'order_xyz')
        self.assertEqual(response.json()['amount'], 50000)

    def test_wallet_payment_success(self):
        response = self.client.post(reverse('user:payment_success'), {
            'payment_id': 'pay_123',
            'amount': '10000'  # paise
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

        self.user.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.balance, Decimal('100.00'))

        txn = WalletTransaction.objects.filter(wallet=self.user.wallet).first()
        self.assertEqual(txn.amount, Decimal('100.00'))
        self.assertEqual(txn.transaction_type, 'Credit')