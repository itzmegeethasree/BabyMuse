from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Wallet

@receiver(post_save, sender=CustomUser)
def handle_new_user_setup(sender, instance, created, **kwargs):
    if created:
        # Create wallet
        Wallet.objects.create(user=instance)

        # Assign referral code if missing
        if not instance.referral_code:
            referral_code = instance.generate_unique_referral_code()
            CustomUser.objects.filter(pk=instance.pk).update(referral_code=referral_code)