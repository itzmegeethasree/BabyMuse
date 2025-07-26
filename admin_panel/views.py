import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

from .forms import CategoryForm, MultiFileUploadForm, ProductForm, ProductVariantForm, ProductVariantFormSet
from shop.models import Category, Product, ProductImage, ProductVariant
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
from django.db.models import Sum, Q
import base64
from django.core.files.base import ContentFile


# from orders.models import Order, ORDER_STATUS, OrderItem, ReturnRequest
# from django.shortcuts import redirect, get_object_or_404
# import xlsxwriter
# from django.contrib.admin.views.decorators import staff_member_required
# from django.template.loader import render_to_string
# from django.utils.dateparse import parse_date
# from django.http import HttpResponse, FileResponse
# from shop.models import Product, Category, ProductImage
# from django.http import HttpResponse
# from .forms import ProductForm, CouponForm
# from shop.forms import CategoryForm, CategoryOfferForm, ProductOfferForm
# from io import BytesIO
# from django.core.files.base import ContentFile
# from PIL import Image
# import csv
# from django.core.exceptions import ObjectDoesNotExist
# from orders.models import Coupon
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas


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
    # total_products = Product.objects.count()
    # total_orders = Order.objects.count()
    # total_revenue = Order.objects.filter(status="paid").aggregate(
    #     total=Sum('total_price'))['total'] or 0
    # latest_orders = Order.objects.order_by('-created_at')[:5]
    return render(request, 'admin_panel/dashboard.html', {
        'total_users': total_users,
        # 'total_products': total_products,
        # 'total_orders': total_orders,
        # 'total_revenue': total_revenue,
        # 'latest_orders': latest_orders,
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
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(gender__icontains=search_query)
        )

    # Apply category filter
    if category_id:
        products = products.filter(category__id=category_id)

    products = products.order_by('-created_at')

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


@admin_login_required
def admin_add_product(request):
    if request.method == 'POST':
        product_form = ProductForm(request.POST)
        image_form = MultiFileUploadForm(request.POST, request.FILES)

        if product_form.is_valid():
            product = product_form.save(commit=False)
            variant_formset = ProductVariantFormSet(
                request.POST, instance=product)

            # Load cropped image data (base64) from hidden input
            cropped_images_data = request.POST.get('cropped_images_data')
            if cropped_images_data:
                cropped_images = json.loads(cropped_images_data)
                for idx, data_url in enumerate(cropped_images):
                    format, imgstr = data_url.split(';base64,')
                    ext = format.split('/')[-1]
                    image_data = ContentFile(base64.b64decode(
                        imgstr), name=f"product_image_{idx}.{ext}")

            if variant_formset.is_valid():
                if len(image_data) < 3:
                    messages.error(
                        request, "Please crop and upload at least 3 images.")
                else:
                    product.save()

                    # Handle cropped image saving
                    handle_cropped_images(product, image_data)

                    # Save variants
                    variant_formset.save()

                    messages.success(request, "Product added successfully.")
                    return redirect('admin_panel:product_list')
            else:
                messages.error(request, "Please correct the variant errors.")
        else:
            messages.error(request, "Please correct the product form errors.")
    else:
        product_form = ProductForm()
        image_form = MultiFileUploadForm()
        variant_formset = ProductVariantFormSet(instance=Product())

    return render(request, 'admin_panel/add_product.html', {
        'product_form': product_form,
        'image_form': image_form,
        'variant_formset': variant_formset,
        'title': "Add New Product"
    })


def handle_cropped_images(product_instance, cropped_data_list):
    for i, img_data in enumerate(cropped_data_list):
        format, imgstr = img_data.split(';base64,')
        ext = format.split('/')[-1]
        image_file = ContentFile(base64.b64decode(
            imgstr), name=f"product_{product_instance.id}_{i}.{ext}")
        ProductImage.objects.create(product=product_instance, image=image_file)


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
def change_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')

    valid_choices = dict(ORDER_STATUS).keys()

    if new_status in valid_choices:
        # Allow special transitions like Cancelled, Failed, etc.
        if order.status in ORDER_FLOW and new_status in ORDER_FLOW:
            current_index = ORDER_FLOW.index(order.status)
            new_index = ORDER_FLOW.index(new_status)

            if new_index < current_index:
                messages.warning(
                    request, "You can't move the status backward.")
                return redirect('admin_panel:admin_order_detail', order_id=order.id)

        # Restock if cancelled
        if order.status != 'Cancelled' and new_status == 'Cancelled':
            for item in order.orderitem_set.all():
                item.product.stock += item.quantity
                item.product.save()

        order.status = new_status
        order.save()
        messages.success(
            request, f"Order #{order.id} status updated to {new_status}")

    else:
        messages.error(request, "Invalid status selected.")

    return redirect('admin_panel:admin_order_detail', order_id=order.id)


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

    # Refund full order amount to user's wallet
    user.wallet_balance += order.total_price
    user.save()

    # Restock all products in the order
    for item in OrderItem.all():
        item.product.stock += item.quantity
        item.product.save()

    messages.success(
        request, f"₹{order.total_price} has been refunded to {user.username}'s wallet.")
    return redirect('admin_panel:admin_return_requests')


@admin_login_required
def admin_return_requests(request):
    return_requests = ReturnRequest.objects.select_related(
        'order__user').order_by('-created_at')
    return render(request, 'admin_panel/return_request.html', {'return_requests': return_requests})

# product management


def process_image(image_file):
    try:
        # Open the uploaded image
        img = Image.open(image_file)
        img = img.convert('RGB')

        img = img.resize((800, 800), Image.LANCZOS)

        buffer = BytesIO()
        img.save(fp=buffer, format='JPEG', quality=85)

        return ContentFile(buffer.getvalue(), name=image_file.name)

    except Exception as e:
        print(f"Image processing error: {e}")
        return None


@admin_login_required
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.filter(is_deleted=False)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        status = request.POST.get('status', 'Active')
        min_age = request.POST.get('min_age')
        max_age = request.POST.get('max_age')
        gender = request.POST.get('gender', 'Unisex')
        images = request.FILES.getlist('images')

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not category_id:
            errors.append("Category is required.")
        if not description:
            errors.append("Description is required.")
        if not price or not price.replace('.', '', 1).isdigit() or float(price) < 0:
            errors.append("Valid price is required.")
        if not stock or not stock.isdigit() or int(stock) < 0:
            errors.append("Valid stock is required.")
        if min_age and (not min_age.isdigit() or not (0 <= int(min_age) <= 36)):
            errors.append("Min age must be between 0 and 36 months.")
        if max_age and (not max_age.isdigit() or not (0 <= int(max_age) <= 36)):
            errors.append("Max age must be between 0 and 36 months.")
        if min_age and max_age and int(min_age) > int(max_age):
            errors.append("Min age cannot be greater than max age.")
        if gender not in ['Male', 'Female', 'Unisex']:
            errors.append("Invalid gender selected.")
        if images and len(images) != 3:
            errors.append(
                "If uploading new images, you must upload exactly 3 cropped images.")

        try:
            category = Category.objects.get(id=category_id)
        except (Category.DoesNotExist, ValueError, TypeError):
            errors.append("Invalid category selected.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'admin_panel/edit_product.html', {
                'product': product,
                'categories': categories
            })

        # Update product fields
        product.name = name
        product.category = category
        product.description = description
        product.price = price
        product.stock = stock
        product.status = status
        product.min_age = min_age or None
        product.max_age = max_age or None
        product.gender = gender
        product.save()

        # If new images uploaded, replace old images
        if images:
            product.images.all().delete()
            for image_file in images:
                ProductImage.objects.create(product=product, image=image_file)

        messages.success(request, "Product updated successfully!")
        return redirect('admin_panel:admin_products')

    return render(request, 'admin_panel/edit_product.html', {
        'product': product,
        'categories': categories
    })


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
