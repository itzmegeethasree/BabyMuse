import base64
from decimal import Decimal

from django.http import JsonResponse
from .forms import AddressForm, BabyProfileForm, CustomUserCreationForm, CustomUserUpdateForm
import uuid
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
import re
import random
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.timezone import now, timedelta
from datetime import timezone as dt_timezone
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from orders.models import Coupon
from .models import Address, BabyProfile, WalletTransaction
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError


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
        email = request.POST.get('email', '').strip()

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect('user:user_register')

        user = User.objects.create_user(
            email=email,
        )

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return redirect('user_login')

    return render(request, 'user/register.html')


def user_logout(request):
    logout(request)
    return redirect('home')


def otp_signup_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if User.objects.filter(email=email).exists():
            messages.error(request, "email already registered.")
            return redirect('user:signup_request')

        otp = str(random.randint(100000, 999999))
        request.session['reset_email'] = email
        request.session['reset_otp'] = otp
        request.session['otp_expiry'] = (
            timezone.now() + timedelta(minutes=2)).isoformat()
        print(f"🔐 OTP for {email} is: {otp}")

    # send_mail(
    #     subject='Your OTP for BabyMuse Signup',
    #     message=f'Your OTP is {otp_obj.otp}',
    #     from_email='your_email@gmail.com',
    #     recipient_list=[email],
    # )

        return redirect('user:verify_otp')
    return render(request, 'user/otp_request.html')


def otp_verify(request):
    expiry_str = request.session.get('otp_expiry')
    expiry_time = timezone.datetime.fromisoformat(expiry_str)
    time_left = (expiry_time - timezone.now()).total_seconds()
    if time_left < 0:
        time_left = 0
    if request.method == 'POST':
        entered_otp = request.POST['otp']
        if entered_otp == request.session.get('reset_otp'):
            return redirect('user:signup')
        else:
            messages.error(request, 'Incorrect OTP.')
    return render(request, 'user/otp_verify.html', {'time_left': int(time_left)})


def resend_otp(request):
    email = request.session.get('reset_email')
    if email:
        try:
            otp = str(random.randint(100000, 999999))
            request.session['reset_otp'] = otp
            request.session['otp_expiry'] = (
                timezone.now() + timedelta(minutes=1)).isoformat()
            print(f"📧 Email register resend OTP for {email} is: {otp}")
            messages.success(request, 'New OTP sent.')
        except:
            messages.error(request, 'Failed to resend OTP.')
    return redirect('user:verify_otp')


def signup(request):
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Session expired or email not found.')
        return redirect('user:signup_request')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = email  # Set from session
            user.username = form.cleaned_data['username']

            # Check referral code
            referral_code = form.cleaned_data.get('referral_code')
            if referral_code:
                try:
                    referrer = User.objects.get(referral_code=referral_code)
                    user.referred_by = referrer
                except User.DoesNotExist:
                    messages.warning(request, "Invalid referral code entered.")
                    # Proceed without assigning referrer

            user.save()

            # Referral reward
            if user.referred_by:
                Coupon.objects.create(
                    code=f"REF-{user.referred_by.id}-{uuid.uuid4().hex[:5].upper()}",
                    discount=100,  
                    is_percentage=False,  
                    valid_from=timezone.now(),
                    valid_to=timezone.now() + timedelta(days=5),
                    active=True,
                    user=user.referred_by,
                    minimum_amount=0,  
                    usage_limit=1,     
                    max_discount_amount=None  
                )

            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('user:user_login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()

    return render(request, 'user/signup.html', {'form': form})


@login_required
def profile_view(request):
    user = request.user

    # Ensure referral code is generated
    if not user.referral_code:
        user.save()  # triggers referral code generation via model's save()
    my_coupons = Coupon.objects.filter(user=user, is_deleted=False)
    addresses = Address.objects.filter(user=user)
    baby_profiles = user.babies.all()
    return render(request, 'user/profile.html', {
        'user': user,
        'my_coupons': my_coupons,
        'addresses': addresses,
        'baby_profiles': baby_profiles,
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
            return redirect('user:user_login')

    return render(request, 'user/change_password.html')


@login_required
def edit_profile(request):
    user = request.user
    if request.method == "POST":
        original_email = user.email
        form = CustomUserUpdateForm(request.POST, request.FILES, instance=user)

        if form.is_valid():
            new_email = form.cleaned_data.get('email')

            # Temporarily set the original email back before saving non-email fields
            if new_email and new_email != original_email:
                form.instance.email = original_email  # Prevent email change now

            form.save()  # Save other changes (name, image, etc.)

            if new_email and new_email != original_email:
                otp = str(random.randint(100000, 999999))
                request.session['email_otp'] = otp
                request.session['new_email'] = new_email
                request.session['otp_sent_time'] = timezone.now().isoformat()

                print(f"📧 OTP for {new_email}: {otp}")
                messages.info(
                    request, f"We've sent an OTP to {new_email}. Please verify to update your email."
                )
                return redirect("user:verify_email_otp")

            messages.success(request, "Profile updated successfully.")
            return redirect("user:edit_profile")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserUpdateForm(instance=user)

    return render(request, "user/edit_profile.html", {"form": form})


def verify_email_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("email_otp")
        new_email = request.session.get("new_email")

        if not session_otp or not new_email:
            messages.error(
                request, "Session expired or invalid. Please try again.")
            return redirect("user:edit_profile")

        if entered_otp == session_otp:
            user = request.user
            user.email = new_email
            user.save()

            # Clean up session
            del request.session['email_otp']
            del request.session['new_email']
            del request.session['otp_sent_time']

            messages.success(
                request, "Email updated and verified successfully.")
            return redirect("user:edit_profile")
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    # Handle GET or failed POST
    remaining_seconds = 0
    otp_sent_time = request.session.get("otp_sent_time")

    if otp_sent_time:
        now = timezone.now()
        sent_time = timezone.datetime.fromisoformat(
            otp_sent_time).replace(tzinfo=dt_timezone.utc)
        elapsed = (now - sent_time).total_seconds()
        remaining_seconds = max(0, 60 - int(elapsed))

    return render(request, "user/verify_email_otp.html", {
        "remaining_seconds": remaining_seconds
    })


@login_required
def resend_email_otp(request):
    new_email = request.session.get('new_email')
    if not new_email:
        messages.error(request, "No email found to resend OTP.")
        return redirect('user:edit_profile')

    otp = str(random.randint(100000, 999999))
    request.session['email_otp'] = otp
    request.session['otp_sent_time'] = timezone.now().isoformat()

    print(f"🔁 Resent OTP for {new_email}: {otp}")
    # TODO: Send OTP via email

    messages.success(request, f"OTP resent to {new_email}.")
    return redirect('user:verify_email_otp')


@login_required
def address_book(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'user/address_book.html', {'addresses': addresses})


@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            if address.is_default:
                Address.objects.filter(
                    user=request.user, is_default=True).update(is_default=False)

            address.save()
            messages.success(request, "Address added successfully.")
            return redirect('user:address_book')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AddressForm()

    return render(request, 'user/add_address.html', {
        'form': form,
        'title': '➕ Add Address',
    })


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            updated_address = form.save(commit=False)
            updated_address.user = request.user

            # Handle default address update
            if updated_address.is_default:
                Address.objects.filter(user=request.user, is_default=True).exclude(
                    id=address.id).update(is_default=False)

            updated_address.save()
            messages.success(request, "Address updated successfully.")
            return redirect('user:address_book')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = AddressForm(instance=address)

    return render(request, 'user/add_address.html', {
        'form': form,
        'title': '✏️ Edit Address',
    })


@login_required
@require_POST
def delete_address(request, id):
    Address.objects.filter(id=id, user=request.user).delete()
    messages.success(request, "Address deleted.")
    return redirect('user:address_book')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            request.session['reset_email'] = email
            request.session['reset_otp'] = otp
            request.session['otp_expiry'] = (
                timezone.now() + timedelta(minutes=1)).isoformat()
            print(f"📧 Email change OTP for {email} is: {otp}")

            # send_mail(
            #     'Your BabyMuse Password Reset OTP',
            #     f'Hello {user.first_name},\n\nYour OTP for password reset is: {otp}\n\nThis OTP is valid for 2 minutes.',
            #     'noreply@babymuse.com',
            #     [email],
            #     fail_silently=False,
            # )
            return redirect('user:verify_reset_otp')
        except User.DoesNotExist:
            messages.error(request, "No user found with this email.")
    return render(request, 'user/forgot_password.html')

# Step 2: OTP Verification


def verify_reset_otp(request):
    expiry_str = request.session.get('otp_expiry')
    expiry_time = timezone.datetime.fromisoformat(expiry_str)
    time_left = (expiry_time - timezone.now()).total_seconds()
    if time_left < 0:
        time_left = 0
    if request.method == 'POST':
        entered_otp = request.POST['otp']
        if entered_otp == request.session.get('reset_otp'):
            return redirect('user:reset_password')
        else:
            messages.error(request, 'Incorrect OTP.')
    return render(request, 'user/verify_reset_otp.html', {'time_left': int(time_left)})

# Step 3: Resend OTP


def resend_reset_otp(request):
    email = request.session.get('reset_email')
    if email:
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            request.session['reset_otp'] = otp
            request.session['otp_expiry'] = (
                timezone.now() + timedelta(minutes=1)).isoformat()
            print(f"📧 Email change OTP for {email} is: {otp}")

            # send_mail(
            #     'Your New OTP for BabyMuse Password Reset',
            #     f'Hello {user.first_name},\n\nYour new OTP is: {otp}\n\nIt is valid for 2 minutes.',
            #     'noreply@babymuse.com',
            #     [email],
            #     fail_silently=False,
            # )
            messages.success(request, 'New OTP sent.')
        except:
            messages.error(request, 'Failed to resend OTP.')
    return redirect('user:verify_reset_otp')

# Step 4: Password Reset


def reset_password(request):
    if request.method == 'POST':
        pwd1 = request.POST['password1']
        pwd2 = request.POST['password2']
        if pwd1 != pwd2:
            messages.error(request, "Passwords don't match.")
        else:
            try:
                user = User.objects.get(
                    email=request.session.get('reset_email'))
                user.set_password(pwd1)
                user.save()
                messages.success(request, 'Password reset successfully.')
                return redirect('user:user_login')
            except:
                messages.error(request, 'Something went wrong.')
    return render(request, 'user/reset_password.html')
# baby profile


@login_required
def add_baby_profile(request):
    if request.method == 'POST':
        form = BabyProfileForm(request.POST)
        if form.is_valid():
            baby = form.save(commit=False)
            baby.user = request.user
            baby.save()
            messages.success(request, 'Baby profile added successfully.')

            return redirect('user:profile')
    else:
        form = BabyProfileForm()
    return render(request, 'user/baby_profile_form.html', {'form': form, 'title': 'Add Baby Profile'})


@login_required
def edit_baby_profile(request, pk):
    baby = get_object_or_404(BabyProfile, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BabyProfileForm(request.POST, instance=baby)
        if form.is_valid():
            form.save()
            return redirect('user:profile')
    else:
        form = BabyProfileForm(instance=baby)
    return render(request, 'user/baby_profile_form.html', {'form': form, 'title': 'Edit Baby Profile'})


@login_required
def delete_baby_profile(request, pk):
    baby = get_object_or_404(BabyProfile, pk=pk, user=request.user)
    if request.method == 'POST':
        baby.delete()
        return redirect('user:profile')
    return render(request, 'user/baby_profile_confirm_delete.html', {'baby': baby})


@login_required
def user_wallet_view(request):
    wallet = request.user.wallet
    transactions = wallet.transactions.order_by('-created_at')
    return render(request, 'user/wallet.html', {'wallet': wallet,
                                                'transactions': transactions,
                                                'razor_pay_key_id': settings.RAZORPAY_KEY_ID})


def create_wallet_order(request):
    amount = int(request.POST.get('amount')) * 100  # Razorpay uses paise
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order = client.order.create({
        'amount': amount,
        'currency': 'INR',
        'payment_capture': '1'
    })
    return JsonResponse({'order_id': order['id'], 'amount': amount})


@csrf_exempt
@login_required
def wallet_payment_success(request):
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        amount = int(request.POST.get('amount'))  # in paise

        # Optional: verify payment with Razorpay API
        # razorpay_client.payment.fetch(payment_id)

        wallet = request.user.wallet
        wallet.balance += Decimal(str(amount)) / \
            Decimal(100)  # convert paise to rupees
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='Credit',
            amount=amount / 100,
            reason='Wallet Top-up'
        )

        return JsonResponse({'status': 'success'})
