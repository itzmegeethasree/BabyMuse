from django.urls import path
from . import views
app_name = 'user'

urlpatterns = [
    path('register/', views.user_register, name='user_register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('otp-signup/', views.otp_signup_request, name='signup_request'),
    path('verify-otp/', views.otp_verify, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('profile/verify-email-otp/',
         views.verify_email_otp, name='verify_email_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('resend-reset-otp/', views.resend_reset_otp, name='resend_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),


    path('change-password/', views.change_password, name='change_password'),
    path('forgot/', views.otp_signup_request, name='forgot_password1'),

    path('address/', views.address_book, name='address_book'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/edit/<int:address_id>/',
         views.edit_address, name='edit_address'),
    path('address/delete/<int:id>/', views.delete_address, name='delete_address'),
    path('baby-profile/add/', views.add_baby_profile, name='add_baby_profile'),
    path('baby-profile/<int:pk>/edit/',
         views.edit_baby_profile, name='edit_baby_profile'),
    path('baby-profile/<int:pk>/delete/',
         views.delete_baby_profile, name='delete_baby_profile'),
    path('wallet/', views.user_wallet_view, name='user_wallet'),
    path('wallet_add/', views.create_wallet_order, name='create_order'),
    path('wallet_payment_success/',
         views.wallet_payment_success, name='payment_success')




]
