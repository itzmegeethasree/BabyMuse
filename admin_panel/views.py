
from shop.models import Product, Order
from .models import AdminUser
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import Sum, Q
from shop.models import Product, Category
from django.contrib.auth import get_user_model
import random
import string
import csv
from .forms import ProductForm
from io import BytesIO
from django.core.files.base import ContentFile
from shop.models import ProductImage

from PIL import Image


User = get_user_model()

# When creating admin user manually
if not AdminUser.objects.filter(username='admin123').exists():
    admin = AdminUser(
        username='admin123',
        password=make_password('admin123'),
        email='geethu1140@gmail.com'
    )
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
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Incorrect password")
        except AdminUser.DoesNotExist:
            messages.error(request, "Admin user not found")
    return render(request, 'admin_panel/login.html')


def admin_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            return redirect('custom_admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


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
            return redirect('custom_admin_login')
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

    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'latest_orders': latest_orders,
    }
    return render(request, 'admin_panel/dashboard.html', context)


def admin_profile(request):
    admin_id = request.session.get('admin_id')
    if not admin_id:
        return redirect('custom_admin_login')
    admin_user = get_object_or_404(AdminUser, id=admin_id)
    return render(request, 'admin_panel/profile.html', {'admin_user': admin_user})


def change_admin_password(request):
    admin_id = request.session.get('admin_id')
    if not admin_id:
        return redirect('custom_admin_login')
    admin_user = AdminUser.objects.get(id=admin_id)

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
            return redirect('admin_profile')
    return render(request, 'admin_panel/change_password.html')


def admin_orders(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    orders = Order.objects.all()

    if query:
        orders = orders.filter(Q(order_id__icontains=query)
                               | Q(user__name__icontains=query))
    if status_filter:
        orders = orders.filter(status=status_filter)

    orders = orders.order_by('-created_at')
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'User', 'Amount',
                        'Status', 'Payment Method', 'Date'])
        for order in orders:
            writer.writerow([order.order_id, order.user.name, order.total_amount,
                             order.status, order.payment_method,
                             order.created_at.strftime('%Y-%m-%d %H:%M')])
        return response

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_panel/orders.html', {'page_obj': page_obj, 'query': query, 'status_filter': status_filter})


@login_required(login_url='custom_admin_login')
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin_panel/order_detail.html', {'order': order})


# @login_required(login_url='admin_login')
def admin_products(request):
    query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')

    # Only fetch products that are not soft deleted
    products = Product.objects.filter(
        is_deleted=False).select_related('category')

    # Apply search filter
    if query:
        products = products.filter(Q(name__icontains=query))

    # Apply category filter
    if category_filter:
        products = products.filter(category_id=category_filter)

    # Paginate results
    paginator = Paginator(products.order_by('-created_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(is_deleted=False)

    return render(
        request,
        'admin_panel/products.html',
        {
            'page_obj': page_obj,
            'query': query,
            'category_filter': category_filter,
            'categories': categories
        }
    )


# @login_required(login_url='admin_login')
def admin_add_product(request):
    categories = Category.objects.filter(is_deleted=False)

    if request.method == 'POST':
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        status = request.POST.get('status')

        image_files = request.FILES.getlist('images')

        if len(image_files) < 3:
            messages.error(request, "Please upload at least 3 images.")
            return render(request, 'admin_panel/add_product.html', {'categories': categories})

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
            return render(request, 'admin_panel/add_product.html', {'categories': categories})

        # Create the product
        product = Product.objects.create(
            name=name,
            category=category,
            description=description,
            price=price,
            stock=stock,
            status=status,
        )

        # Image processing
        def process_image(image_file):
            img = Image.open(image_file)
            img = img.convert('RGB')
            img = img.resize((800, 800))
            buffer = BytesIO()
            img.save(fp=buffer, format='JPEG')
            return ContentFile(buffer.getvalue(), name=image_file.name)

        for image_file in image_files[:3]:  # Limit to 3 images
            processed = process_image(image_file)
            if processed:
                product_image = ProductImage(product=product)
                product_image.image.save(image_file.name, processed)

        messages.success(request, "Product added successfully!")
        return redirect('admin_products')

    return render(request, 'admin_panel/add_product.html', {'categories': categories})


def process_image(image_file):
    img = Image.open(image_file)
    img = img.convert('RGB')
    # or use ImageOps.fit(img, (800, 800)) for cropping
    img = img.resize((800, 800))
    buffer = BytesIO()
    img.save(fp=buffer, format='JPEG')
    return ContentFile(buffer.getvalue(), name=image_file.name)


# @login_required(login_url='admin_login')
def admin_edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.filter(is_deleted=False)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.status = request.POST.get('status')

        try:
            category = Category.objects.get(id=request.POST.get('category'))
            product.category = category
        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
            return render(request, 'admin_panel/edit_product.html', {'product': product, 'categories': categories})

        # Save basic info
        product.save()

        # Handle new uploaded images
        image_files = request.FILES.getlist('images')

        def process_image(image_file):
            img = Image.open(image_file)
            img = img.convert('RGB')
            img = img.resize((800, 800))
            buffer = BytesIO()
            img.save(fp=buffer, format='JPEG')
            return ContentFile(buffer.getvalue(), name=image_file.name)

        if image_files:
            # Optional: delete existing images first if needed
            product.images.all().delete()

            for image_file in image_files[:3]:  # limit to 3 images
                processed = process_image(image_file)
                if processed:
                    ProductImage.objects.create(
                        product=product, image=processed)

        messages.success(request, "Product updated successfully.")
        return redirect('admin_products')

    return render(request, 'admin_panel/edit_product.html', {
        'product': product,
        'categories': categories
    })

# views.py


# @login_required(login_url='admin_login')
def admin_delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = True
    product.save()
    messages.success(request, "Product deleted successfully.")
    return redirect('admin_products')


def admin_category_list(request):
    categories = Category.objects.all().order_by('-created_at')
    paginator = Paginator(categories, 10)  # Show 10 categories per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/category_list.html', {'page_obj': page_obj})


def admin_add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if name:
            Category.objects.create(name=name, description=description)
            messages.success(request, 'Category added successfully!')
            return redirect('admin_category_list')
        else:
            messages.error(request, 'Name is required.')

    return render(request, 'admin_panel/add_category.html')


def admin_edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        category.name = name
        category.description = description
        category.save()

        messages.success(request, 'Category updated successfully!')
        return redirect('admin_category_list')

    return render(request, 'admin_panel/edit_category.html', {'category': category})


def admin_delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('admin_category_list')

    return render(request, 'admin_panel/delete_category.html', {'category': category})
# adminpanel/views.py


def admin_customer_list(request):
    query = request.GET.get('q', '')
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')

    if query:
        customers = customers.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin_panel/customer_list.html', {
        'page_obj': page_obj,
        'query': query,
    })


def admin_view_customer(request, customer_id):
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    return render(request, 'admin_panel/view_customer.html', {'customer': customer})
