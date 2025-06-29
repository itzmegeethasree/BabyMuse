from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
import re
import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import EmailOTP, Profile, Address
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST


User = get_user_model()


def user_login(request):
    next_url = request.GET.get('next', '')

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
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return redirect('user_login')

    return render(request, 'user/register.html')


def user_logout(request):
    logout(request)
    return redirect('home')


def send_otp(email):
    otp_obj, _ = EmailOTP.objects.get_or_create(email=email)
    otp_obj.generate_otp()

    print(f"🔐 OTP for {email} is: {otp_obj.otp}")

    # send_mail(
    #     subject='Your OTP for BabyMuse Signup',
    #     message=f'Your OTP is {otp_obj.otp}',
    #     from_email='your_email@gmail.com',
    #     recipient_list=[email],
    # )


def otp_signup_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        send_otp(email)
        request.session['email'] = email
        return redirect('user:verify_otp')
    return render(request, 'user/otp_request.html')


def otp_verify(request):
    email = request.session.get('email')
    otp_record = None

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
            username=username, email=email, password=password
        )
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        messages.success(request, 'Account created successfully.')
        return redirect('home')

    return render(request, 'user/set_password.html')


@login_required
def profile_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    addresses = Address.objects.filter(user=user)
    return render(request, 'user/profile.html', {
        'user': user,
        'profile': profile,
        'addresses': addresses,
    })


@login_required
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, "Old password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif len(new_password) < 6:
            messages.error(
                request, "New password must be at least 6 characters long.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(
                request, request.user)
            messages.success(request, "Password updated successfully.")
            return redirect('user:profile')

    return render(request, 'user/change_password.html')


@login_required
def edit_profile(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        # User model fields
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        new_email = request.POST.get('email')
        phone = request.POST.get('phone')
        profile_image = request.FILES.get('profile_image')

        # Profile model fields
        baby_name = request.POST.get('baby_name')
        baby_dob = request.POST.get('baby_dob')
        baby_gender = request.POST.get('baby_gender')

        # Update user fields (except email for now)
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        if profile_image:
            user.profile_image = profile_image

        # Update profile fields
        profile.baby_name = baby_name
        profile.baby_gender = baby_gender
        profile.baby_dob = baby_dob if baby_dob else None

        if new_email and new_email != user.email:
            otp = str(random.randint(100000, 999999))
            request.session['pending_email'] = new_email
            request.session['email_otp'] = otp
            # Simulate send
            print(f"📧 Email change OTP for {new_email} is: {otp}")

            # send_mail(
            #     subject='Verify Your New Email - BabyMuse',
            #     message=f'Your OTP for verifying the new email is: {otp}',
            #     from_email='noreply@babymuse.com',
            #     recipient_list=[new_email],
            #     fail_silently=False,
            # )

            messages.info(
                request, f'OTP sent to {new_email}. Please verify to update your email.')
            return redirect('user:verify_email_otp')

        user.save()
        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('user:profile')

    return render(request, 'user/edit_profile.html', {
        'user': user,
        'profile': profile
    })


@login_required
def verify_email_otp(request):
    if request.method == 'POST':
        input_otp = request.POST.get('otp')
        session_otp = request.session.get('email_otp')
        new_email = request.session.get('pending_email')

        if input_otp == session_otp and new_email:
            request.user.email = new_email
            request.user.save()

            # Clean up session
            request.session.pop('email_otp', None)
            request.session.pop('pending_email', None)

            messages.success(request, "✅ Email updated successfully.")
            return redirect('user:profile')
        else:
            messages.error(request, "❌ Invalid OTP. Please try again.")

    return render(request, 'user/verify_email_otp.html')


@login_required
def address_book(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'user/address_book.html', {'addresses': addresses})


@login_required
def add_address(request):
    if request.method == 'POST':
        Address.objects.create(
            user=request.user,
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            address_line1=request.POST.get('address_line1'),
            address_line2=request.POST.get('address_line2'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            postal_code=request.POST.get('postal_code'),
            is_default='is_default' in request.POST
        )
        messages.success(request, "Address added successfully!")
        return redirect('user:address_book')
    return render(request, 'user/add_address.html', {
        'title': '➕ Add Address',
        'address': {}
    })


@login_required
def edit_address(request, id):
    address = Address.objects.get(id=id, user=request.user)

    if request.method == 'POST':
        address.name = request.POST.get('name')
        address.phone = request.POST.get('phone')
        address.address_line1 = request.POST.get('address_line1')
        address.address_line2 = request.POST.get('address_line2')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        address.is_default = 'is_default' in request.POST
        address.save()

        messages.success(request, "Address updated successfully!")
        return redirect('user:address_book')

    return render(request, 'user/add_address.html', {
        'title': '✏️ Edit Address',
        'address': address
    })


@login_required
@require_POST
def delete_address(request, id):
    Address.objects.filter(id=id, user=request.user).delete()
    messages.success(request, "Address deleted.")
    return redirect('user:address_book')
