from django.test import TestCase
from user.models import (
    CustomUser, BabyProfile, Address, Wallet, WalletTransaction
)
from datetime import date
from decimal import Decimal

class CustomUserModelTests(TestCase):
    def test_user_creation_and_referral_code(self):
        user = CustomUser.objects.create_user(
            username='geetha',
            email='geetha@example.com',
            password='securepass'
        )
        self.assertTrue(user.referral_code)
        self.assertEqual(user.email, 'geetha@example.com')
        self.assertIsNone(user.referred_by)
        self.assertTrue(hasattr(user, 'wallet'))  # Signal-created wallet

    def test_referral_relationship(self):
        referrer = CustomUser.objects.create_user(
            username='referrer',
            email='ref@example.com',
            password='pass'
        )
        referred = CustomUser.objects.create_user(
            username='referred',
            email='referred@example.com',
            password='pass',
            referred_by=referrer
        )
        self.assertEqual(referred.referred_by, referrer)
        self.assertIn(referred, referrer.referrals.all())


class BabyProfileModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='parentuser',
            email='parent@example.com',
            password='pass'
        )

    def test_baby_profile_creation_and_age(self):
        baby = BabyProfile.objects.create(
            user=self.user,
            baby_name='Baby Muse',
            baby_dob=date(2023, 1, 1),
            baby_gender='Female',
            birth_weight=3.2,
            birth_height=50.0,
            notes='Sleeps well'
        )
        self.assertEqual(baby.user, self.user)
        self.assertEqual(baby.baby_name, 'Baby Muse')
        self.assertEqual(baby.age_in_months(), (date.today() - baby.baby_dob).days // 30)

    def test_baby_profile_str(self):
        baby = BabyProfile.objects.create(user=self.user, baby_name='Tiny Star')
        self.assertEqual(str(baby), 'Tiny Star')


class AddressModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='addressuser',
            email='addressuser@example.com',
            password='pass'
        )

    def test_address_creation(self):
        address = Address.objects.create(
            user=self.user,
            name='Geetha S',
            phone='9876543210',
            address_line1='123 Baby Street',
            address_line2='Near Park',
            city='Kottakkal',
            state='Kerala',
            postal_code='676503',
            is_default=True
        )
        self.assertEqual(address.user, self.user)
        self.assertTrue(address.is_default)
        self.assertEqual(address.city, 'Kottakkal')


class WalletModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='walletuser',
            email='walletuser@example.com',
            password='pass'
        )

    def test_wallet_created_by_signal(self):
        self.assertTrue(hasattr(self.user, 'wallet'))
        self.assertEqual(self.user.wallet.balance, Decimal('0.00'))

    def test_wallet_str(self):
        wallet = self.user.wallet
        wallet.balance = Decimal('250.00')
        wallet.save()
        self.assertEqual(str(wallet), f"{self.user.username}'s Wallet")
        self.assertEqual(wallet.balance, Decimal('250.00'))


class WalletTransactionModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='transuser',
            email='transuser@example.com',
            password='pass'
        )
        self.wallet = self.user.wallet
        self.wallet.balance = Decimal('500.00')
        self.wallet.save()

    def test_wallet_transaction_creation(self):
        txn = WalletTransaction.objects.create(
            wallet=self.wallet,
            amount=Decimal('100.00'),
            transaction_type='Debit',
            reason='Purchase'
        )
        self.assertEqual(txn.wallet, self.wallet)
        self.assertEqual(txn.transaction_type, 'Debit')
        self.assertEqual(str(txn), 'Debit - 100.00')