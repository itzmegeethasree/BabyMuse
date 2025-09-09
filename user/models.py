from datetime import date
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
import random
from django.conf import settings
from django.utils.crypto import get_random_string


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_image = models.ImageField(
        upload_to='profile_images/', blank=True, null=True)

    referral_code = models.CharField(
        max_length=100, blank=True, null=True )
    referred_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_unique_referral_code()
        super().save(*args, **kwargs)

    def generate_unique_referral_code(self):
        code = get_random_string(5).upper()
        while CustomUser.objects.filter(referral_code=code).exists():
            code = get_random_string(5).upper()
        return code


class BabyProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, related_name='babies')
    baby_name = models.CharField(max_length=100, blank=True, null=True)
    baby_dob = models.DateField(blank=True, null=True)
    baby_gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        blank=True, null=True
    )
    birth_weight = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    birth_height = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def age_in_months(self):
        if self.baby_dob:
            delta = date.today() - self.baby_dob
            return delta.days // 30
        return None
    def __str__(self):
        return self.baby_name or "Unnamed Baby"



class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line1 = models.TextField()
    address_line2 = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet"


class WalletTransaction(models.Model):
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    TRANSACTION_TYPES = (
        ('Credit', 'Credit'),
        ('Debit', 'Debit'),
    )
    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTION_TYPES)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    related_order = models.ForeignKey(
        'orders.Order', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"
