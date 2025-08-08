from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.db.models import Avg

from .models import Product, Category, Wishlist, CartItem, Review, ProductVariant


from django.db.models import Min, Q


def shop_view(request):
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')
    sort_by = request.GET.get('sort', '')

    # Base queryset with only active, non-deleted products
    products = Product.objects.filter(status='Active', is_deleted=False)
    products = products.annotate(min_variant_price=Min('variants__price'))

    # Search by product name
    if search_query:
        products = products.filter(name__icontains=search_query)

    # Filter by category
    if category_id:
        products = products.filter(category__id=category_id)

    # Filter by variant price range
    if price_min.isdigit() and price_max.isdigit():
        products = products.filter(
            min_variant_price__gte=price_min,
            min_variant_price__lte=price_max
        )

    # Sorting
    if sort_by == "price_low":
        products = products.order_by('min_variant_price')
    elif sort_by == "price_high":
        products = products.order_by('-min_variant_price')
    elif sort_by == "name_asc":
        products = products.order_by('name')
    elif sort_by == "name_desc":
        products = products.order_by('-name')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    for product in page_obj:
        default_variant = product.variants.filter(
            stock__gt=0, product__status='Active').order_by('price').first()
        product.default_variant_id = default_variant.id if default_variant else None
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
        product = Product.objects.prefetch_related(
            'images', 'variants__options__attribute').get(pk=pk)

        if product.status != 'Active':
            messages.error(request, "This product is currently unavailable.")
            return redirect('shop')

        reviews = Review.objects.filter(
            product=product).order_by('-created_at')
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        total_reviews = reviews.count()

        # Collect variants with size/color
        variants = []
        for variant in product.variants.all():
            size = variant.options.filter(attribute__name='Size').first()
            color = variant.options.filter(attribute__name='Color').first()
            if size and color:
                variants.append({
                    'id': variant.id,
                    'size': size.value,
                    'color': color.value,
                    'price': float(variant.price),
                    'stock': variant.stock
                })
        unique_sizes = sorted(set(v['size'] for v in variants))
        unique_colors = sorted(set(v['color'] for v in variants))

        context = {
            'product': product,
            'images': product.images.all(),
            'variants': variants,
            'reviews': reviews,
            'avg_rating': round(avg_rating, 1) if avg_rating else 0,
            'review_count': total_reviews,
            'unique_sizes': unique_sizes,
            'unique_colors': unique_colors,

        }
        return render(request, 'shop/product_detail.html', context)

    except Product.DoesNotExist:
        messages.error(request, "Product not found or has been removed.")
        return redirect('shop')


# ------------------- WISHLIST --------------------
@require_POST
@login_required
def direct_add_to_wishlist(request):
    variant_id = request.POST.get('variant_id')
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        Wishlist.objects.get_or_create(
            user=request.user,
            product=variant.product,
            variant=variant
        )
        messages.success(request, "Added to wishlist!")
    except ProductVariant.DoesNotExist:
        messages.error(request, "Variant not found.")
    return redirect('shop')


@login_required
def wishlist_view(request):
    search_query = request.GET.get('q', '')

    wishlist_items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related('product', 'variant')
        .prefetch_related('variant__options__attribute')
    )

    # Filter by search (by product name)
    if search_query:
        wishlist_items = wishlist_items.filter(
            Q(product__name__icontains=search_query)
        )

    paginator = Paginator(wishlist_items, 6)  # 6 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'shop/wishlist.html', {
        'wishlist_items': page_obj,
        'search_query': search_query,
        'page_obj': page_obj,
    })


@login_required
@require_POST
def ajax_add_to_wishlist(request):
    variant_id = request.POST.get('variant_id')
    if not variant_id:
        return JsonResponse({'status': 'error', 'message': 'Variant ID missing'}, status=400)

    try:
        variant = ProductVariant.objects.select_related(
            'product').get(id=variant_id)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Variant not found'}, status=404)

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=variant.product,
        variant=variant
    )

    wish_count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse({
        'status': 'added' if created else 'exists',
        'wishlist_count': wish_count
    })


@login_required
@require_POST
def ajax_remove_from_wishlist(request):
    data = json.loads(request.body)
    variant_id = data.get("variant_id")

    if not variant_id:
        return JsonResponse({"status": "error", "message": "Variant ID missing"}, status=400)

    Wishlist.objects.filter(user=request.user, variant_id=variant_id).delete()

    wish_count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse({
        "status": "success",
        "message": "Removed from wishlist",
        "wishlist_count": wish_count
    })

# -------------------- CART ----------------------


@require_POST
@login_required
def direct_add_to_cart(request):
    variant_id = request.POST.get('variant_id')
    try:
        variant = ProductVariant.objects.get(id=variant_id)
        if variant.stock < 1:
            messages.error(request, "This item is out of stock.")
            return redirect('shop')

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product_variant=variant
        )
        if not created:
            if cart_item.quantity >= variant.stock:
                messages.warning(request, "Stock limit reached.")
            else:
                cart_item.quantity += 1
                cart_item.save()
        messages.success(request, "Added to cart!")
    except ProductVariant.DoesNotExist:
        messages.error(request, "Variant not found.")
    return redirect('shop')


@login_required
def cart_view(request):
    search_query = request.GET.get('q', '').strip()

    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product_variant', 'product_variant__product')

    if search_query:
        cart_items = cart_items.filter(
            Q(product_variant__product__name__icontains=search_query)
        )

    for item in cart_items:
        item.total_price = item.quantity * item.product_variant.get_offer_price()

    total_price = round(sum(item.total_price for item in cart_items), 2)

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'search_query': search_query
    })


@login_required
@require_POST
def ajax_add_to_cart(request):
    variant_id = request.POST.get('variant_id')
    if not variant_id:
        return JsonResponse({'status': 'error', 'message': 'Missing variant'}, status=400)

    try:
        variant = ProductVariant.objects.get(pk=variant_id)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Variant not found'}, status=404)

    if variant.stock < 1:
        return JsonResponse({'status': 'error', 'message': 'Out of stock'})

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product_variant=variant
    )

    if not created:
        if cart_item.quantity >= variant.stock:
            return JsonResponse({'status': 'error', 'message': 'Stock limit reached'})
        cart_item.quantity += 1
        cart_item.save()

    cart_count = CartItem.objects.filter(user=request.user).count()

    return JsonResponse({'status': 'success', 'cart_count': cart_count})


@login_required
@require_POST
def ajax_remove_from_cart(request):
    data = json.loads(request.body)
    product_id = data.get("product_id")
    try:
        item = CartItem.objects.get(user=request.user, product_id=product_id)
        item.delete()
        total_price = sum(
            i.quantity * i.product.price for i in CartItem.objects.filter(user=request.user)
        )
        return JsonResponse({"status": "success", "message": "Item removed from cart", "new_total_price": total_price})
    except CartItem.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found"})


@require_POST
@login_required
def ajax_update_cart_quantity(request, variant_id):
    try:
        quantity = int(request.POST.get('quantity', 1))

        cart_item = CartItem.objects.get(
            user=request.user, product_variant_id=variant_id)

        if quantity < 1:
            cart_item.delete()
            total_price = sum(
                i.quantity * i.product_variant.get_offer_price()
                for i in CartItem.objects.filter(user=request.user)
            )
            return JsonResponse({
                "status": "removed",
                "message": "Item removed from cart",
                "new_total": total_price
            })

        if quantity > cart_item.product_variant.stock:
            return JsonResponse({
                "status": "error",
                "message": f"Only {cart_item.product_variant.stock} in stock."
            })

        cart_item.quantity = quantity
        cart_item.save()

        total_price = sum(
            i.quantity * i.product_variant.get_offer_price()
            for i in CartItem.objects.filter(user=request.user)
        )

        return JsonResponse({
            "status": "success",
            "message": f"Quantity updated for {cart_item.product_variant.product.name}.",
            "item_total": cart_item.quantity * cart_item.product_variant.get_offer_price(),
            "unit_price": cart_item.product_variant.get_offer_price(),
            "new_total": total_price
        })

    except CartItem.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Item not found in your cart."})
    except ValueError:
        return JsonResponse({"status": "error", "message": "Invalid quantity."})


@login_required
def ajax_cart_data(request):
    cart_items = CartItem.objects.filter(
        user=request.user).select_related('product_variant', 'product_variant__product')
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
