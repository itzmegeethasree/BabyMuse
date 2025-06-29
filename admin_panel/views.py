from shop.models import ORDER_STATUS, Product, Order, Category, ProductImage, OrderItem, ReturnRequest
from .models import AdminUser
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model
from .forms import ProductForm
from shop.forms import CategoryForm
from .decorators import admin_login_required
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
import random
import string
import csv
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_POST


User = get_user_model()

# Create default admin user
if not AdminUser.objects.filter(username='admin123').exists():
    admin = AdminUser(username='admin123', password=make_password(
        'admin123'), email='geethu1140@gmail.com')
    admin.save()
    print("Admin user created.")
else:
    print("Admin user already exists.")


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

    # ✅ Handle CSV Export
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

    # Pagination for HTML view
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'admin_panel/orders.html', {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
    })


@admin_login_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    context = {
        'order': order,
        'order_items': order_items,
        'status_choices': ORDER_STATUS,

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
    if new_status in dict(ORDER_STATUS).keys():
        order.status = new_status
        order.save()
        messages.success(
            request, f"Order #{order.id} status changed to {new_status}")
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
        return redirect('admin_return_requests')

    # Mark the return as approved
    return_request.approved = True
    return_request.save()

    # Refund full order amount to user's wallet
    user.wallet_balance += order.total_price
    user.save()

    # Restock all products in the order
    for item in order.items.all():
        item.product.stock += item.quantity
        item.product.save()

    messages.success(
        request, f"₹{order.total_price} has been refunded to {user.username}'s wallet.")
    return redirect('admin_return_requests')


@admin_login_required
def admin_return_requests(request):
    return_requests = ReturnRequest.objects.select_related(
        'order__user').order_by('-created_at')
    return render(request, 'admin_panel/return_requests.html', {'return_requests': return_requests})

# product management


@admin_login_required
def admin_products(request):
    products = Product.objects.filter(is_deleted=False).select_related(
        'category').order_by('-created_at')
    categories = Category.objects.filter(is_deleted=False)
    paginator = Paginator(products, 10)  # 10 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/products.html', {
        'products': products,
        'categories': categories,
        'page_obj': page_obj
    })


@admin_login_required
def admin_add_product(request):
    categories = Category.objects.filter(is_deleted=False)

    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        status = request.POST.get('status')
        images = request.FILES.getlist('images')

        if not all([name, category_id, description, price, stock, status]):
            messages.error(request, "Please fill out all required fields.")
            return render(request, 'admin_panel/add_product.html', {
                'categories': categories
            })

        if len(images) != 3:
            messages.error(request, "Please upload exactly 3 images.")
            return render(request, 'admin_panel/add_product.html', {
                'categories': categories
            })

        try:
            category = Category.objects.get(id=category_id)
        except ObjectDoesNotExist:
            messages.error(request, "Invalid category selected.")
            return render(request, 'admin_panel/add_product.html', {
                'categories': categories
            })

        # Create product
        product = Product.objects.create(
            name=name,
            category=category,
            description=description,
            price=price,
            stock=stock,
            status=status,
        )

        #  Save product images
        for image_file in images:
            ProductImage.objects.create(product=product, image=image_file)

        messages.success(request, "Product added successfully!")
        return redirect('admin_panel:admin_products')

    return render(request, 'admin_panel/add_product.html', {'categories': categories})


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
    product = get_object_or_404(Product, id=product_id, is_deleted=False)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            images = request.FILES.getlist('images')
            if images:
                for img in images:
                    processed = process_image(img)
                    if processed:
                        ProductImage.objects.create(
                            product=product, image=processed)
            messages.success(request, "Product updated successfully.")
            return redirect('admin_panel:admin_products')
    else:
        form = ProductForm(instance=product)

    categories = Category.objects.filter(
        parent__isnull=True, is_deleted=False).prefetch_related('subcategories')

    return render(request, 'admin_panel/edit_product.html', {
        'form': form,
        'product': product,
        'categories': categories
    })


@admin_login_required
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = True
    product.save()
    messages.success(request, "Product deleted successfully.")
    return redirect('admin_panel:admin_products')

# category Management


@admin_login_required
def category_list(request):
    categories = Category.objects.all()
    paginator = Paginator(categories, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/category_list.html', {'page_obj': page_obj})


@admin_login_required
def add_category(request):

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('admin_panel:admin_category_list')
    else:
        form = CategoryForm()
    categories = Category.objects.filter(
        parent__isnull=True)

    return render(request, 'admin_panel/add_category.html', {'form': form, 'categories': categories})


@admin_login_required
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated.')
            return redirect('admin_panel:admin_category_list')
    else:
        form = CategoryForm(instance=category)
    categories = Category.objects.filter(
        parent__isnull=True).exclude(id=category.id)
    return render(request, 'admin_panel/edit_category.html', {'form': form, 'categories': categories})


@admin_login_required
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('admin_panel:admin_category_list')

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
