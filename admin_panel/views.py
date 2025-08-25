from user.models import WalletTransaction
from core.models import Banner
from orders.models import OrderItem, ORDER_STATUS
from admin_panel.decorators import admin_login_required
from django.shortcuts import get_object_or_404, redirect
import csv
from django.http import HttpResponse
from orders.models import ORDER_STATUS, Coupon, Order, OrderItem, ReturnRequest
from .forms import BannerForm, CouponForm, ProductForm, ProductOfferForm, VariantComboForm, CategoryOfferForm
from django.utils.text import slugify
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from .forms import CategoryForm, ProductForm, VariantComboForm
from shop.models import Category, Product, ProductImage, ProductVariant, VariantOption, VariantAttribute
from .models import AdminUser
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from .decorators import admin_login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Prefetch
import base64
from django.core.files.base import ContentFile
import xlsxwriter
from django.utils.dateparse import parse_date
from django.http import HttpResponse, FileResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


User = get_user_model()

# Create default admin user
if not AdminUser.objects.filter(username='admin123').exists():
    admin = AdminUser(username='admin123', password=make_password(
        'admin123'), email='geethu1140@gmail.com')
    admin.save()
    print("Admin user created.")
else:
    print("Admin user already exists.")

# login


def custom_admin_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        try:
            admin = AdminUser.objects.get(username=username)
            if check_password(password, admin.password):
                request.session['admin_id'] = admin.id
                return redirect('admin_panel:admin_dashboard')
            else:
                messages.error(request, "Incorrect password")
        except AdminUser.DoesNotExist:
            messages.error(request, "Admin user not found")

    return render(request, 'admin_panel/login.html')


def generate_temp_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def admin_forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']
        try:
            admin = AdminUser.objects.get(email=email)
            temp_password = generate_temp_password()
            admin.password = make_password(temp_password)
            admin.save()

            send_mail(
                'BabyMuse Admin - Temporary Password',
                f'Your temporary password is: {temp_password}\nPlease login and change it immediately.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            messages.success(request, "Temporary password sent to your email.")
            return redirect('admin_panel:custom_admin_login')
        except AdminUser.DoesNotExist:
            messages.error(request, "Email not found.")
    return render(request, 'admin_panel/forgot_password.html')


@admin_login_required
def admin_dashboard(request):
    total_users = User.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status="paid").aggregate(
        total=Sum('total_price'))['total'] or 0
    latest_orders = Order.objects.order_by('-created_at')[:5]
    return render(request, 'admin_panel/dashboard.html', {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'latest_orders': latest_orders,
    })


@admin_login_required
def admin_profile(request):
    admin_user = get_object_or_404(AdminUser, id=request.session['admin_id'])
    return render(request, 'admin_panel/profile.html', {'admin_user': admin_user})


@admin_login_required
def change_admin_password(request):
    admin_user = AdminUser.objects.get(id=request.session['admin_id'])
    if request.method == "POST":
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(current_password, admin_user.password):
            messages.error(request, "Current password is incorrect")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match")
        else:
            admin_user.password = make_password(new_password)
            admin_user.save()
            messages.success(request, "Password updated successfully")
            return redirect('admin_panel:admin_profile')
    return render(request, 'admin_panel/change_password.html')


# customer management


@admin_login_required
def admin_customer_list(request):
    query = request.GET.get('q', '')
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')
    if query:
        customers = customers.filter(Q(username__icontains=query) | Q(
            email__icontains=query) | Q(phone__icontains=query))
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_panel/customer_list.html', {'page_obj': page_obj, 'query': query, 'customers': customers})


@admin_login_required
def admin_view_customer(request, customer_id):
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    return render(request, 'admin_panel/view_customer.html', {'customer': customer})


def custom_admin_logout(request):
    request.session.flush()
    return redirect('admin_panel:custom_admin_login')


@require_POST
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    status = "unblocked" if user.is_active else "blocked"
    messages.success(request, f"User {user.username} has been {status}.")
    return redirect('admin_panel:admin_customer_list')


# category management/
@admin_login_required
def category_list(request):
    search_query = request.GET.get('q', '')
    categories = Category.objects.filter(is_deleted=False)

    if search_query:
        categories = categories.filter(Q(name__icontains=search_query))

    categories = categories.order_by('-created_at')
    paginator = Paginator(categories, 10)
    page = request.GET.get('page')
    categories = paginator.get_page(page)

    return render(request, 'admin_panel/category_list.html', {
        'categories': categories,
        'search_query': search_query
    })


@admin_login_required
def add_category(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Category added successfully.")
        return redirect('admin_panel:category_list')
    return render(request, 'admin_panel/category_form.html', {'form': form, 'title': 'Add Category'})


@admin_login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk, is_deleted=False)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect('admin_panel:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin_panel/category_form.html', {'form': form, 'title': 'Edit Category'})


@admin_login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.is_deleted = True
    category.save()
    messages.success(request, "Category deleted.")
    return redirect('admin_panel:category_list')


# product management


@admin_login_required
def admin_products(request):
    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category', '')

    products = Product.objects.all()

    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(gender__icontains=search_query)
        )

    # Apply category filter
    if category_id:
        products = products.filter(category__id=category_id)

    # Optimize DB hits
    products = products.select_related('category').prefetch_related(
        Prefetch('variants', queryset=ProductVariant.objects.only('stock'))
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # All categories for dropdown
    categories = Category.objects.filter(is_deleted=False)

    return render(request, 'admin_panel/products.html', {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
    })


def parse_variants_from_post(post_data):
    rows = {}
    for key in post_data:
        if key.startswith("variants["):
            row = key.split('[')[1].split(']')[0]
            field = key.split('[')[2].split(']')[0]
            rows.setdefault(row, {})[field] = post_data[key]
    return list(rows.values())


def save_product_and_variants(request, product, is_edit, size_qs, color_qs):
    form = ProductForm(request.POST, instance=product)
    cropped_images_data = request.POST.get('cropped_images_data')
    new_images = json.loads(cropped_images_data) if cropped_images_data else []

    variant_data = parse_variants_from_post(request.POST)
    existing_combos = set()
    variant_forms = [
        VariantComboForm(
            data=row,
            initial={
                'product_name': request.POST.get('name', ''),
                'product_id': product.id if product else None,
                'variant_id': row.get('variant_id')
            },
            size_qs=size_qs,
            color_qs=color_qs,
            existing_combos=existing_combos
        )
        for row in variant_data
    ]

    if form.is_valid() and all(f.is_valid() for f in variant_forms):
        if not is_edit and len(new_images) < 3:
            messages.error(
                request, "Please crop and upload at least 3 images.")
            return None, form, variant_forms

        product = form.save()

        # Get IDs of images to keep
        keep_image_ids = request.POST.getlist('keep_image_ids')
        cropped_images_data = request.POST.get('cropped_images_data')
        new_images = []

        if cropped_images_data:
            images_data = json.loads(cropped_images_data)
            for idx, img_str in enumerate(images_data):
                format, imgstr = img_str.split(';base64,')
                ext = format.split('/')[-1]
                new_images.append(ContentFile(base64.b64decode(
                    imgstr), name=f'cropped{idx+1}.{ext}'))

        total_images = len(keep_image_ids) + len(new_images)
        if total_images == 0:
            messages.error(
                request, "At least one product image must be kept or uploaded.")
            return None, form, variant_forms
        elif total_images > 3:
            messages.error(
                request, "You cannot have more than 3 images in total.")
            return None, form, variant_forms

        # Delete images NOT in keep_image_ids
        product.images.exclude(id__in=keep_image_ids).delete()
        # Add new images
        for image_file in new_images:
            ProductImage.objects.create(product=product, image=image_file)

        submitted_keys = set()
        for form in variant_forms:
            size = form.cleaned_data['size']
            color = form.cleaned_data['color']
            sku = form.cleaned_data['sku']
            price = form.cleaned_data['price']
            stock = form.cleaned_data['stock']
            variant_id = form.initial.get('variant_id')

            # Try to find existing variant by size/color
            existing_variant = None
            if variant_id:
                existing_variant = product.variants.filter(
                    id=variant_id).first()
            else:
                existing_variant = product.variants.filter(
                    options=size
                ).filter(
                    options=color
                ).first()

            if existing_variant:
                # When checking for SKU uniqueness
                if ProductVariant.objects.filter(product=product, sku=sku).exclude(id=existing_variant.id).exists():
                    form.add_error(
                        'sku', f"SKU '{sku}' already exists for this product.")
                    continue
                existing_variant.sku = sku
                existing_variant.price = price
                existing_variant.stock = stock
                existing_variant.save()
            else:
                # Check for SKU uniqueness for new variant
                if ProductVariant.objects.filter(product=product, sku=sku).exists():
                    form.add_error(
                        'sku', f"SKU '{sku}' already exists for this product.")
                    continue
                variant = ProductVariant.objects.create(
                    product=product, sku=sku, price=price, stock=stock)
                variant.options.set([size, color])

            submitted_keys.add((size.id, color.id))

        # Delete variants not present in submitted_keys
        for variant in product.variants.all():
            size = variant.options.filter(attribute__name='Size').first()
            color = variant.options.filter(attribute__name='Color').first()
            if size and color and (size.id, color.id) not in submitted_keys:
                variant.delete()

        return product, None, None
    else:
        return None, form, variant_forms


@admin_login_required
def admin_product_form(request, product_id=None):
    if product_id:
        product = get_object_or_404(Product, pk=product_id)
        is_edit = True
    else:
        product = None
        is_edit = False

    size_attr = VariantAttribute.objects.get(name__iexact='Size')
    color_attr = VariantAttribute.objects.get(name__iexact='Color')
    size_qs, color_qs = size_attr.options.all(), color_attr.options.all()

    if request.method == 'POST':
        product_obj, errors_form, errors_variants = save_product_and_variants(
            request, product, is_edit, size_qs, color_qs)
        if product_obj:
            messages.success(
                request, f"Product {'updated' if is_edit else 'added'} successfully.")
            return redirect('admin_panel:admin_products')
        messages.error(request, "Please correct the errors below.")
        return render(request, 'admin_panel/product_form.html', {
            'product_form': errors_form,
            'size_options': size_qs,
            'color_options': color_qs,
            'variant_forms': errors_variants,
            'is_edit': is_edit,
            'product': product,
            'existingVariants': get_existing_variant_data(product) if product else [],
        })

    return render(request, 'admin_panel/product_form.html', {
        'product_form': ProductForm(instance=product),
        'size_options': size_qs,
        'color_options': color_qs,
        'is_edit': is_edit,
        'product': product,
        'existingVariants': get_existing_variant_data(product) if product else [],
    })


def get_existing_variant_data(product):
    variants = []
    for variant in product.variants.all():
        size = variant.options.filter(attribute__name='Size').first()
        color = variant.options.filter(attribute__name='Color').first()
        if size and color:
            variants.append({
                'id': variant.id,
                'size_id': size.id,
                'size_label': size.value,
                'color_id': color.id,
                'color_label': color.value,
                'sku': variant.sku,
                'price': float(variant.price),
                'stock': variant.stock
            })
    return variants


def handle_cropped_images(product, cropped_data_list):
    for i, img_data in enumerate(cropped_data_list):
        format, imgstr = img_data.split(';base64,')
        ext = format.split('/')[-1]
        image_file = ContentFile(base64.b64decode(
            imgstr), name=f"product_{product.id}_{i}.{ext}")
        ProductImage.objects.create(product=product, image=image_file)

# order management


@admin_login_required
def admin_orders(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    export_csv = request.GET.get('export') == 'csv'

    # Fetch & filter orders
    orders = Order.objects.select_related('user').all()

    if query:
        orders = orders.filter(
            Q(id__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )

    if status_filter:
        orders = orders.filter(status=status_filter)

    orders = orders.order_by('-created_at')

    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Order ID', 'User', 'Amount',
            'Status', 'Payment Method', 'Date'
        ])

        for order in orders:
            user_name = order.user.get_full_name() or order.user.username
            writer.writerow([
                order.id,
                user_name,
                order.total_price,
                order.status,
                order.payment_method,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
            ])

        return response

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/orders.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
    })


ORDER_FLOW = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Completed']


@admin_login_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items,
        'status_choices': ORDER_STATUS,
        'order_flow': ORDER_FLOW,

    }
    return render(request, 'admin_panel/order_details.html', context)


@admin_login_required
def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    context = {'order': order, 'order_items': order_items}
    return render(request, 'admin_panel/order_invoice.html', context)


@admin_login_required
@require_POST
def change_item_status(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    new_status = request.POST.get('status')
    reason = request.POST.get('reason', '').strip()  # Optional reason field

    valid_choices = dict(ORDER_STATUS).keys()

    if new_status in valid_choices:
        # Prevent backward transitions if using ORDER_FLOW
        if item.status in ORDER_FLOW and new_status in ORDER_FLOW:
            current_index = ORDER_FLOW.index(item.status)
            new_index = ORDER_FLOW.index(new_status)

            if new_index < current_index:
                messages.warning(
                    request, "You can't move the item status backward.")
                return redirect('admin_panel:admin_order_detail', order_id=item.order.id)

        # Restock logic only if item is being cancelled and wasn't already
        if item.status not in ['Cancelled', 'Returned'] and new_status == 'Cancelled':
            item.product_variant.stock += item.quantity
            item.product_variant.save()

        # Update item status and optional reason
        previous_status = item.status
        item.status = new_status
        if reason:
            item.status_reason = reason  # If you have a field like this
        item.save()

        # Recalculate overall order status
        item.order.update_status_from_items()

        messages.success(
            request, f"Item #{item.id} status updated to {new_status}")
    else:
        messages.error(request, "Invalid status selected.")

    return redirect('admin_panel:admin_order_detail', order_id=item.order.id)


@admin_login_required
@admin_login_required
def verify_return_request(request, return_id):
    return_request = get_object_or_404(ReturnRequest, id=return_id)
    order = return_request.order
    user = order.user

    if return_request.approved:
        messages.info(
            request, "This return request has already been verified.")
        return redirect('admin_panel:admin_return_requests')

    # Mark the return as approved
    return_request.approved = True
    return_request.save()

    # Get returned items
    returned_items = order.items.filter(status='Returned')
    if not returned_items.exists():
        messages.error(request, "No items marked as returned in this order.")
        return redirect('admin_panel:admin_return_requests')

    # Calculate refund amount
    refund_amount = sum(item.subtotal() for item in returned_items)

    # Refund to wallet
    wallet = user.wallet
    wallet.balance += refund_amount
    wallet.save()

    # Log wallet transaction
    WalletTransaction.objects.create(
        wallet=wallet,
        amount=refund_amount,
        transaction_type='Credit',
        reason='Refund for returned items',
        related_order=order
    )

    # Restock items
    for item in returned_items:
        item.product_variant.stock += item.quantity
        item.product_variant.save()

    messages.success(
        request,
        f"₹{refund_amount} has been refunded to {user.username}'s wallet for returned items."
    )
    return redirect('admin_panel:admin_return_requests')


@admin_login_required
def admin_return_requests(request):
    return_requests = ReturnRequest.objects.select_related(
        'order__user').prefetch_related('order__items').order_by('-created_at')
    return render(request, 'admin_panel/return_request.html', {'return_requests': return_requests})

# product management


@admin_login_required
def admin_toggle_product_visibility(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = not product.is_deleted
    product.save()
    status = "listed" if not product.is_deleted else "unlisted"
    messages.success(request, f"Product successfully {status}.")
    return redirect('admin_panel:admin_products')

# coupon management


def coupon_list(request):
    query = request.GET.get('q')
    coupons = Coupon.objects.filter(is_deleted=False)

    if query:
        coupons = coupons.filter(Q(code__icontains=query))

    coupons = coupons.order_by('-created_at')
    paginator = Paginator(coupons, 10)
    page = request.GET.get('page')
    coupons = paginator.get_page(page)

    return render(request, 'admin_panel/coupon_list.html', {'coupons': coupons})


def coupon_create(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully.")
            return redirect('admin_panel:admin-coupon-list')
    else:
        form = CouponForm()

    return render(request, 'admin_panel/coupon_form.html', {'form': form})


def coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated successfully.")
            return redirect('admin_panel:admin-coupon-list')
    else:
        form = CouponForm(instance=coupon)

    return render(request, 'admin_panel/coupon_form.html', {'form': form})


def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.is_deleted = True
    coupon.save()
    messages.warning(request, "Coupon deleted (soft delete).")
    return redirect('admin_panel:admin-coupon-list')
# offer management


def product_offer_list(request):
    products = Product.objects.filter(
        is_deleted=False)
    return render(request, 'admin_panel/product_offer_list.html', {'products': products})


def update_product_offer(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductOfferForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('admin_panel:product_offer_list')
    else:
        form = ProductOfferForm(instance=product)
    return render(request, 'admin_panel/update_product_offer.html', {'form': form})


def category_offer_list(request):
    categories = Category.objects.all()
    return render(request, 'admin_panel/category_offer_list.html', {'categories': categories})


def update_category_offer(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('admin_panel:category_offer_list')
    else:
        form = CategoryOfferForm(instance=category)
    return render(request, 'admin_panel/update_category_offer.html', {'form': form})

# reports


@admin_login_required
def sales_report_view(request):
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    orders = Order.objects.filter(status='Delivered')

    if from_date and to_date:
        from_date = parse_date(from_date)
        to_date = parse_date(to_date)
        orders = orders.filter(created_at__date__range=(from_date, to_date))

    total_orders = Order.objects.filter(status='Delivered').count()
    total_price = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_discount = orders.aggregate(Sum('discount_amount'))[
        'discount_amount__sum'] or 0

    context = {
        'orders': orders,
        'total_orders': total_orders,
        'total_price': total_price,
        'total_discount': total_discount,
        'from': request.GET.get('from', ''),
        'to': request.GET.get('to', ''),
    }
    return render(request, 'admin_panel/sales_report.html', context)


@admin_login_required
def download_sales_report_pdf(request):
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')

    orders = Order.objects.filter(status='Delivered')
    if from_date and to_date:
        from_date = parse_date(from_date)
        to_date = parse_date(to_date)
        orders = orders.filter(created_at__date__range=(from_date, to_date))

    # PDF setup
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "📄 BabyMuse Sales Report")
    y -= 30

    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"From: {from_date}   To: {to_date}")
    y -= 30

    p.drawString(
        50, y, "Order ID | Customer | Date | Total ₹ | Discount ₹ | Payment")
    y -= 20
    p.line(50, y, width - 50, y)
    y -= 20

    for order in orders:
        if y < 100:
            p.showPage()
            y = height - 50

        p.drawString(
            50, y, f"{order.id} | {order.user.username} | {order.created_at.date()} | ₹{order.total_price} | ₹{order.discount_amount} | {order.payment_method}")
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename="sales_report.pdf")


@admin_login_required
def download_sales_report_excel(request):
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    orders = Order.objects.filter(status='Delivered')

    if from_date and to_date:
        from_date = parse_date(from_date)
        to_date = parse_date(to_date)
        orders = orders.filter(created_at__date__range=(from_date, to_date))

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Sales Report")

    headers = ['Order ID', 'Customer', 'Date',
               'Total Amount', 'Discount', 'Payment Method']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    for row, order in enumerate(orders, start=1):
        worksheet.write(row, 0, order.id)
        worksheet.write(row, 1, order.user.username)
        worksheet.write(row, 2, order.created_at.strftime('%Y-%m-%d'))
        worksheet.write(row, 3, float(order.total_price))
        worksheet.write(row, 4, float(order.discount_amount))
        worksheet.write(row, 5, order.payment_method)

    workbook.close()
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename='sales_report.xlsx')

# Banners


@admin_login_required
def banner_list(request):
    banners = Banner.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/banner_list.html', {'banners': banners})


@admin_login_required
def banner_create(request):
    form = BannerForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('admin_panel:banner_list')
    return render(request, 'admin_panel/banner_form.html', {'form': form, 'action': 'Create'})


@admin_login_required
def banner_edit(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    form = BannerForm(request.POST or None,
                      request.FILES or None, instance=banner)
    if form.is_valid():
        form.save()
        return redirect('admin_panel:banner_list')
    return render(request, 'admin_panel/banner_form.html', {'form': form, 'action': 'Edit', 'banner': banner})


@admin_login_required
def banner_delete(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)
    banner.delete()
    return redirect('admin_panel:banner_list')

# wallet


@admin_login_required
def wallet_transaction_list(request):
    transactions = WalletTransaction.objects.select_related(
        'wallet__user').order_by('-created_at')
    return render(request, 'admin_panel/wallet_transaction_list.html', {'transactions': transactions})


@admin_login_required
def wallet_transaction_detail(request, tx_id):
    tx = get_object_or_404(WalletTransaction, id=tx_id)
    return render(request, 'admin_panel/wallet_transaction_detail.html', {'tx': tx})
