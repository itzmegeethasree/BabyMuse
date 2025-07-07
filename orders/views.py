from datetime import timezone
import json
from django.shortcuts import render, redirect, get_object_or_404

from shop.models import CartItem, Product, ReturnRequest
from user.models import Address
from shop.models import Order, OrderItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from shop.models import Order, OrderItem
from shop.models import CartItem, Address

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
import razorpay
from .models import Coupon
from shop.models import Order, OrderItem, CartItem, Address


@login_required
def checkout_view(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user).select_related('product')

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('shop')

    # Product check
    unavailable_products = []
    for item in cart_items:
        product = item.product
        if not product or product.stock < item.quantity or product.is_deleted:
            unavailable_products.append(product.name)

    if unavailable_products:
        messages.error(
            request, f"The following items are unavailable: {', '.join(unavailable_products)}")
        return redirect('shop:cart')
    applied_coupon = None
    discount = Decimal('0.00')

    if 'applied_coupon' in request.session:
        try:
            applied_coupon = Coupon.objects.get(
                code=request.session['applied_coupon'], active=True)
            if applied_coupon.valid_from <= timezone.now() <= applied_coupon.valid_to and subtotal >= applied_coupon.minimum_amount:
                if applied_coupon.is_percentage:
                    discount = subtotal * \
                        (applied_coupon.discount / Decimal('100'))
                else:
                    discount = applied_coupon.discount
            else:
                del request.session['applied_coupon']
        except Coupon.DoesNotExist:
            pass

    # Pricing
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = Decimal('50.00') if subtotal < 1000 else Decimal('0.00')
    tax = subtotal * Decimal('0.05')
    discount = Decimal('0.00')
    total = subtotal + shipping + tax - discount

    addresses = Address.objects.filter(user=user)
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':
        selected_address_id = request.POST.get('address')
        payment_method = request.POST.get('payment_method')

        if not selected_address_id or not payment_method:
            messages.error(
                request, "Please select address and payment method.")
            return redirect('orders:checkout')

        address = get_object_or_404(Address, id=selected_address_id, user=user)

        order = Order.objects.create(
            user=user,
            address=address,
            total_price=total,
            payment_method=payment_method
        )

        if payment_method == 'COD':
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
                item.product.stock -= item.quantity
                item.product.save()

            cart_items.delete()
            return redirect('orders:order_success', order_id=order.id)

        elif payment_method == 'RAZORPAY':
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create({
                "amount": int(total * 100),
                "currency": "INR",
                "payment_capture": 1
            })

            order.razorpay_order_id = razorpay_order['id']
            order.save()

            return render(request, "order/razorpay_payment.html", {
                "order": order,
                "cart_items": cart_items,
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": int(total * 100),
                "user_email": user.email,
                "user_name": user.get_full_name(),
            })

    return render(request, 'order/checkout.html', {
        'cart_items': cart_items,
        'addresses': addresses,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'discount': discount,
        'total': total,
        'default_address': default_address
    })


@csrf_exempt
@login_required
def razorpay_success(request):
    data = json.loads(request.body)

    try:
        # Initialize Razorpay client
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        # Step 1: Verify Razorpay Signature
        params_dict = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }
        client.utility.verify_payment_signature(params_dict)

        # Step 2: Fetch order
        order = Order.objects.get(id=data['order_id'], user=request.user)

        # Step 3: Mark as paid and confirmed
        order.is_paid = True
        order.status = "Confirmed"
        order.save()

        # Step 4: Process cart to order items
        cart_items = CartItem.objects.filter(
            user=request.user).select_related('product')
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()

        cart_items.delete()

        # Step 5: Return success with redirect URL
        return JsonResponse({
            'status': 'success',
            'order_id': order.id,
            'redirect_url': f"/orders/success/{order.id}/"
        })

    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({
            'status': 'failure',
            'order_id': data.get('order_id'),
            'redirect_url': f"/orders/payment-failed/?order_id={data.get('order_id')}"
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'status': 'failure',
            'message': 'Order not found',
            'redirect_url': "/orders/payment-failed/"
        })


@csrf_exempt
def razorpay_webhook(request):
    if request.method == "POST":
        try:
            payload = request.body
            received_signature = request.headers.get('X-Razorpay-Signature')

            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Optional: use a webhook secret if you defined one
            # webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
            # client.utility.verify_webhook_signature(payload, received_signature, webhook_secret)

            data = json.loads(payload)

            # Process the event
            if data.get('event') == "payment.failed":
                razorpay_order_id = data['payload']['payment']['entity']['order_id']
                order = Order.objects.filter(
                    razorpay_order_id=razorpay_order_id).first()
                if order:
                    order.status = "Failed"
                    order.save()

            elif data.get('event') == "payment.captured":
                razorpay_order_id = data['payload']['payment']['entity']['order_id']
                order = Order.objects.filter(
                    razorpay_order_id=razorpay_order_id).first()
                if order:
                    order.status = "Confirmed"
                    order.is_paid = True
                    order.save()

            return HttpResponse(status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return HttpResponse("Invalid request", status=400)


@login_required
def payment_failed_view(request):
    order_id = request.GET.get('order_id')
    if not order_id:
        messages.error(request, "Invalid request.")
        return redirect('shop')

    return render(request, 'order/payment_failed.html', {'order_id': order_id})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    unavailable_items = []

    # Check for stock or product deletion after order placement
    for item in order.orderitem_set.select_related('product').all():
        product = item.product

        if not product or product.is_deleted or product.stock < item.quantity:
            unavailable_items.append({
                'name': product.name if product else "Unknown Product",
                'ordered_qty': item.quantity,
                'available_stock': product.stock if product else 0,
                'status': (
                    "Unlisted" if product and product.is_deleted else
                    "Out of Stock" if not product or product.stock == 0 else
                    "Limited Stock"
                )
            })

    context = {
        'order': order,
        'unavailable_items': unavailable_items
    }

    return render(request, 'order/order_success.html', context)


@login_required
def order_list_view(request):
    query = request.GET.get('q')
    orders = Order.objects.filter(user=request.user)

    if query:
        orders = orders.filter(id__icontains=query)

    return render(request, 'order/order.html', {'orders': orders})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)

    return render(request, 'order/order_detail.html', {
        'order': order,
        'items': items,
    })


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        order.status = 'Cancelled'
        order.save()

        # Increment stock
        for item in order.orderitem_set.all():
            item.product.stock += item.quantity
            item.product.save()

        messages.success(request, f"Order #{order.id} cancelled successfully.")
        return redirect('orders:order')

    return render(request, 'order/cancel_order.html', {'order': order})


def search_orders(request):
    query = request.GET.get('q')
    orders = Order.objects.filter(user=request.user)

    if query:
        orders = orders.filter(
            Q(id__icontains=query) | Q(status__icontains=query)
        )

    return render(request, 'order/order.html', {'orders': orders})


@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status != 'Delivered':
        messages.error(request, "Only delivered orders can be returned.")
        return redirect('orders:order_detail', order_id=order.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a return reason.")
        else:
            ReturnRequest.objects.create(order=order, reason=reason)
            messages.success(request, "Return request submitted successfully.")
            return redirect('orders:order_detail', order_id=order.id)

    return render(request, 'order/return_order.html', {'order': order})


def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template_path = 'order/invoice.html'
    context = {'order': order}

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_Order_{order.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)
    return response


@login_required
def apply_coupon(request):
    code = request.POST.get('coupon_code', '').strip()
    try:
        coupon = Coupon.objects.get(code__iexact=code, active=True)
        request.session['applied_coupon'] = coupon.code
        messages.success(request, f"Coupon '{coupon.code}' applied.")
    except Coupon.DoesNotExist:
        messages.error(request, "Invalid or expired coupon.")
    return redirect('orders:checkout')


@login_required
def remove_coupon(request):
    if 'applied_coupon' in request.session:
        del request.session['applied_coupon']
        messages.info(request, "Coupon removed.")
    return redirect('orders:checkout')
