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
    path('set-password/', views.set_password, name='set_password'),
    path('profile/', views.profile_view, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('profile/verify-email-otp/',
         views.verify_email_otp, name='verify_email_otp'),

    path('change-password/', views.change_password, name='change_password'),
    path('forgot/', views.otp_signup_request, name='forgot_password'),

    path('address/', views.address_book, name='address_book'),
    path('address/add/', views.add_address, name='add_address'),
    path('address/edit/<int:id>/', views.edit_address, name='edit_address'),
    path('address/delete/<int:id>/', views.delete_address, name='delete_address'),




]
