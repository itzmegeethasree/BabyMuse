from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
import re
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import EmailOTP
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme


User = get_user_model()


def user_login(request):
    next_url = request.GET.get('next', '')  # from ?next=/cart/ etc.

    # Show toast before login form if redirected
    if next_url:
        if 'wishlist' in next_url:
            messages.warning(
                request, "🔒 Please log in to access your wishlist.")
        elif 'cart' in next_url:
            messages.warning(request, "🛒 Please log in to access your cart.")

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, "Both username and password are required.")
            return redirect('user:user_login')

        auth_user = authenticate(username=username, password=password)
        if auth_user:
            login(request, auth_user)

            # Safe redirect (prevents open redirect attacks)
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            else:
                return redirect('home')
        else:
            messages.error(request, "Invalid credentials")

    return render(request, 'user/login.html', {'next': next_url})


def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[@$!%*?&]", password):
        return False
    return True


def user_register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username:
            messages.error(request, "Username is required.")
            return redirect('user:user_register')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('user:user_register')

        if not is_strong_password(password):
            messages.error(
                request, "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character.")
            return redirect('user:user_register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('user:user_register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('user:user_register')

        user = User.objects.create_user(
            username=username, email=email, password=password)
        user.backend = 'django.contrib.auth.backends.ModelBackend'  # fix added here
        login(request, user)
        return redirect('home')

    return render(request, 'user/register.html')


def user_logout(request):
    logout(request)
    return redirect('home')


def send_otp(email):
    otp_obj, _ = EmailOTP.objects.get_or_create(email=email)
    otp_obj.generate_otp()

    send_mail(
        subject='Your OTP for BabyMuse Signup',
        message=f'Your OTP is {otp_obj.otp}',
        from_email='your_email@gmail.com',
        recipient_list=[email],
    )


def otp_signup_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        send_otp(email)
        request.session['email'] = email
        return redirect('user:verify_otp')
    return render(request, 'user/otp_request.html')


def otp_verify(request):
    email = request.session.get('email')
    otp_record = None  # <-- define it here

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        try:
            otp_record = EmailOTP.objects.get(email=email)
            if otp_record.otp == entered_otp:
                return redirect('user:set_password')
            else:
                messages.error(request, 'Invalid OTP')
        except EmailOTP.DoesNotExist:
            messages.error(request, 'No OTP sent. Please try again.')
            return redirect('user:otp_signup_request')

    # This block was throwing the error — check only if otp_record exists
    if otp_record and timezone.now() - otp_record.created_at > timedelta(minutes=5):
        messages.error(request, 'OTP expired. Please request again.')
        otp_record.delete()
        return redirect('user:otp_signup_request')

    return render(request, 'user/otp_verify.html')


def resend_otp(request):
    email = request.session.get('email')
    if email:
        send_otp(email)
        messages.success(request, 'OTP resent successfully!')
    return redirect('user:verify_otp')


def set_password(request):
    email = request.session.get('email')
    if not email:
        messages.error(request, 'Session expired or email not found.')
        return redirect('user:signup_request')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return redirect('user:set_password')

        if not is_strong_password(password):
            messages.error(request, "Weak password.")
            return redirect('user:set_password')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'User already exists.')
            return redirect('user:user_login')

        user = User.objects.create_user(
            username=username, email=email, password=password)
        login(request, user)
        messages.success(request, 'Account created successfully.')
        return redirect('home')

    return render(request, 'user/set_password.html')


@login_required
def profile_view(request):
    return render(request, 'user/profile.html', {'user': request.user})
