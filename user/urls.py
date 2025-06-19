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



]
