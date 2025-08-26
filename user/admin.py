from django.contrib import admin
from .models import CustomUser, WalletTransaction, Wallet,Address,BabyProfile

admin.site.register(CustomUser)
admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(Address)
admin.site.register(BabyProfile)