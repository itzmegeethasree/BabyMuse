from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.db.models import Avg

from .models import Product, Category, Wishlist, CartItem, Review


def shop_view(request):
    products = Product.objects.filter(status='Active')

    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    sort_by = request.GET.get('sort', '')

    if search_query:
        products = products.filter(name__icontains=search_query)
    if category_id:
        products = products.filter(category__id=category_id)
    if price_min.isdigit() and price_max.isdigit():
        products = products.filter(price__gte=price_min, price__lte=price_max)

    if sort_by == "price_low":
        products = products.order_by('price')
    elif sort_by == "price_high":
        products = products.order_by('-price')
    elif sort_by == "name_asc":
        products = products.order_by('name')
    elif sort_by == "name_desc":
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')

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
    try:
        product = Product.objects.prefetch_related('images').get(pk=pk)

        if product.status != 'Active':
            messages.error(request, "This product is currently unavailable.")
            return redirect('shop')

        reviews = Review.objects.filter(
            product=product).order_by('-created_at')

        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        total_reviews = reviews.count()

        context = {
            'product': product,
            'images': product.images.all(),  # 👈 needed for thumbnails
            'reviews': reviews,
            'avg_rating': round(avg_rating, 1) if avg_rating is not None else 0,
            'review_count': total_reviews,  # 👈 renamed for template clarity
        }
        return render(request, 'shop/product_detail.html', context)

    except Product.DoesNotExist:
        messages.error(request, "Product not found or has been removed.")
        return redirect('shop')


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product').prefetch_related('product__images')

    # wishlist_items = Wishlist.objects.filter(
    #     user=request.user).select_related('product')
    return render(request, 'shop/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
@require_POST
def ajax_add_to_wishlist(request):
    product_id = request.POST.get('product_id')
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user, product=product)
    return JsonResponse({'status': 'added' if created else 'exists'})


@login_required
@require_POST
def ajax_remove_from_wishlist(request):
    data = json.loads(request.body)
    product_id = data.get("product_id")
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    return JsonResponse({"status": "success", "message": "Removed from wishlist"})


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
@require_POST
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


@login_required
@require_POST
def ajax_remove_from_cart(request):
    data = json.loads(request.body)
    product_id = data.get("product_id")
    try:
        item = CartItem.objects.get(user=request.user, product_id=product_id)
        item.delete()
        return JsonResponse({"status": "success", "message": "Item removed from cart"})
    except CartItem.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found"})


@require_POST
@login_required
def ajax_update_cart_quantity(request, product_id):
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            return JsonResponse({"status": "error", "message": "Quantity must be at least 1."})

        cart_item = CartItem.objects.get(
            user=request.user, product_id=product_id)
        cart_item.quantity = quantity
        cart_item.save()

        total_price = sum(
            item.quantity * item.product.price for item in CartItem.objects.filter(user=request.user)
        )

        return JsonResponse({
            "status": "success",
            "message": f"Quantity updated for {cart_item.product.name}.",
            "item_total": cart_item.quantity * cart_item.product.price,
            "unit_price": cart_item.product.price,
            "new_total": total_price
        })
    except CartItem.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found in your cart."})
    except ValueError:
        return JsonResponse({"status": "error", "message": "Invalid quantity."})


@login_required
def ajax_cart_data(request):
    cart_items = CartItem.objects.filter(
        user=request.user).select_related('product')
    data = []
    total_price = 0

    for item in cart_items:
        price = item.quantity * item.product.price
        total_price += price
        data.append({
            'id': item.product.id,
            'name': item.product.name,
            'price': item.product.price,
            'quantity': item.quantity,
            'total': price,
        })

    return JsonResponse({"status": "success", "items": data, "total_price": total_price})
