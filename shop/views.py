
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Product, Category
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist, CartItem, Product
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json


def product_list(request):
    categories = Category.objects.all()

    # Get selected category from query params
    selected_category_id = request.GET.get('category')

    # Filter products
    if selected_category_id:
        products = Product.objects.filter(category__id=selected_category_id)
    else:
        products = Product.objects.all()

    # Set up pagination
    paginator = Paginator(products, 9)  # Show 9 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'shop/shop.html', {
        'categories': categories,
        'products': page_obj,  # products will be paginated
    })


def shop_view(request):
    print("shop view")
    products = Product.objects.filter(status='Active')

    # --- Filters ---
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    sort_by = request.GET.get('sort', '')

    # Search
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Filter by category
    if category_id:
        products = products.filter(category__id=category_id)

    # Filter by price
    if price_min.isdigit() and price_max.isdigit():
        products = products.filter(price__gte=price_min, price__lte=price_max)

    # Sorting
    if sort_by == "price_low":
        products = products.order_by('price')
    elif sort_by == "price_high":
        products = products.order_by('-price')
    elif sort_by == "name_asc":
        products = products.order_by('name')
    elif sort_by == "name_desc":
        products = products.order_by('-name')

    # Pagination
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'categories': Category.objects.all(),
        'selected_category': category_id,
        'price_min': price_min,
        'price_max': price_max,
        'sort_by': sort_by,
    }

    return render(request, 'shop/shop.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    images = product.images.all()
    return render(request, 'shop/product_detail.html', {'product': product, 'images': images})


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product').prefetch_related('product__images')

    # wishlist_items = Wishlist.objects.filter(
    #     user=request.user).select_related('product')
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    messages.success(request, "Added to wishlist.")
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, "Removed from wishlist.")
    return redirect('wishlist')


# Cart Views

@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related(
        'product').prefetch_related('product__images')

    # Add total per item and total cart price
    for item in cart_items:
        item.total_price = item.quantity * item.product.price

    total_price = sum(item.total_price for item in cart_items)

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
    })


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user, product=product)

    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, "Added to Cart.")

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def remove_from_cart(request, product_id):
    CartItem.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, "Removed from cart.")
    return redirect('cart')


@login_required
def update_cart_quantity(request, product_id):
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1:
                messages.error(request, "Quantity must be at least 1.")
                return redirect('cart')

            cart_item = CartItem.objects.get(
                user=request.user, product_id=product_id)
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(
                request, f"Quantity updated for {cart_item.product.name}.")
        except CartItem.DoesNotExist:
            messages.error(request, "Item not found in your cart.")
        except ValueError:
            messages.error(request, "Invalid quantity entered.")

    return redirect('cart')


@require_POST
@login_required
def ajax_add_to_cart(request):
    product_id = request.POST.get('product_id')
    try:
        product = Product.objects.get(id=product_id)
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, product=product)
        if not created:
            cart_item.quantity += 1
            cart_item.save()

        cart_count = CartItem.objects.filter(user=request.user).count()

        return JsonResponse({'status': 'success', 'cart_count': cart_count})
    except Product.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Product not found'})


# @login_required
def ajax_add_to_wishlist(request):
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user, product=product)
        return JsonResponse({'status': 'added' if created else 'exists'})


@require_POST
@login_required
def remove_from_cart_ajax(request):
    data = json.loads(request.body)
    product_id = data.get("product_id")

    try:
        item = CartItem.objects.get(user=request.user, product_id=product_id)
        item.delete()
        return JsonResponse({"status": "success", "message": "Item removed from cart"})
    except CartItem.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found"})
