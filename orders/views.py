import traceback
from .models import Order, OrderItem
from django.shortcuts import get_object_or_404, redirect, render
from datetime import timezone
import json
from django.shortcuts import render, redirect, get_object_or_404

from shop.models import CartItem
from user.models import Address, Wallet, WalletTransaction
from orders.models import Order, OrderItem, ReturnRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.db.models import Q
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.paginator import Paginator


from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from shop.models import CartItem

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST


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
from utils.coupon import validate_coupon


from decimal import Decimal
from django.utils import timezone


from decimal import Decimal
from django.utils import timezone
from utils.coupon import validate_coupon
from orders.models import Coupon
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings


@login_required
def checkout_view(request):
    user = request.user
    cart_items = CartItem.objects.filter(
        user=user).select_related('product_variant', 'product_variant__product')

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('shop')

    # Check product availability
    unavailable_products = []
    for item in cart_items:
        variant = item.product_variant
        product = variant.product
        if not variant or variant.stock < item.quantity or product.is_deleted:
            unavailable_products.append(
                variant.product.name if variant else "Unknown product")

    if unavailable_products:
        messages.error(
            request, f"The following items are unavailable: {', '.join(unavailable_products)}")
        return redirect('cart')

    # Price calculation
    subtotal = sum(item.product_variant.get_offer_price()
                   * item.quantity for item in cart_items)
    shipping = Decimal('50.00') if subtotal < 500 else Decimal('0.00')
    tax = subtotal * Decimal('0.05')
    discount = Decimal('0.00')
    coupon_obj = None

    coupon_code = request.session.get('applied_coupon')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            result, error = validate_coupon(coupon.code, subtotal)
            if not error:
                coupon_obj = result['coupon']
                discount = result['discount']
        except Exception:
            pass

    total = subtotal + shipping + tax - discount

    addresses = Address.objects.filter(user=user)
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST' and 'place_order' in request.POST:
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
            payment_method=payment_method,
            status="Pending",
            is_paid=False,
            coupon=coupon_obj,
            discount_amount=discount,
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product_variant.product,
                product_variant=item.product_variant,
                quantity=item.quantity,
                price=item.product_variant.get_offer_price(),
            )

        if payment_method == 'COD':
            order.is_paid = True
            order.save()
            if order.coupon:
                order.coupon.times_used += 1
                order.coupon.save()

            for item in cart_items:
                item.product_variant.stock -= item.quantity
                item.product_variant.save()

            cart_items.delete()
            request.session.pop('applied_coupon', None)
            request.session.pop('discount', None)

            return redirect('orders:order_success', order_id=order.id)
        
        elif payment_method == 'WALLET':
            wallet=Wallet.objects.get(user=user)
            if wallet.balance >= total:
                wallet.balance -= total
                wallet.save()
                order.is_paid = True
                order.payment_method = 'Wallet'
                order.save()

                if order.coupon:
                    order.coupon.times_used += 1
                    order.coupon.save()
                #wallet transaction
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=total,
                    transaction_type='Debit',
                    reason=f'paymentfor order #{order.id}',
                    related_order=order
                )

                for item in cart_items:
                    item.product_variant.stock -= item.quantity
                    item.product_variant.save()

                cart_items.delete()
                request.session.pop('applied_coupon', None)
                request.session.pop('discount', None)

                return redirect('orders:order_success', order_id=order.id)
            else:
                messages.error(request, "Insufficient wallet balance.")
                return redirect('orders:checkout')

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
                "razorpay_order_id": razorpay_order['id'],
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": int(total * 100),
                "user_email": user.email,
                "user_name": user.get_full_name(),
            })

    return render(request, 'order/checkout.html', {
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'discount': discount,
        'total': total,
        'coupon_code': request.session.get('applied_coupon', '')
    })




@require_POST
@login_required
def ajax_apply_coupon(request):
    try:
        code = request.POST.get('coupon_code', '').strip()
        user = request.user

        cart_items = CartItem.objects.filter(user=user).select_related('product_variant', 'product_variant__product')

        subtotal = sum(
            Decimal(item.product_variant.get_offer_price()) * item.quantity
            for item in cart_items
            if item.product_variant and hasattr(item.product_variant, 'get_offer_price')
        )

        shipping = Decimal('50.00') if subtotal < Decimal('1000.00') else Decimal('0.00')
        tax = subtotal * Decimal('0.05')
        discount = Decimal('0.00')
        coupon_code = ""
        coupon_msg = ""
        success = False

        result, error = validate_coupon(code, subtotal)
        if error:
            coupon_msg = error
        elif result:
            coupon_obj = result['coupon']
            if coupon_obj.usage_limit is not None and coupon_obj.times_used >= coupon_obj.usage_limit:
                coupon_msg = "This coupon has reached its usage limit."
            else:
                discount = Decimal(str(result['discount']))
                coupon_code = coupon_obj.code
                coupon_msg = f"Coupon '{coupon_obj.code}' applied successfully!"
                request.session['applied_coupon'] = coupon_code
                request.session['discount'] = float(discount)  # Store as float for session safety
                success = True

        total = subtotal + shipping + tax - discount

        return JsonResponse({
            "success": success,
            "msg": coupon_msg,
            "discount": "%.2f" % float(discount),
            "total": "%.2f" % float(total),
            "coupon_code": coupon_code,
        })

    except Exception as e:
        print("Coupon AJAX error:", str(e))
        traceback.print_exc()
        return JsonResponse({"success": False, "msg": "Server error occurred."})

@csrf_exempt
@login_required
def razorpay_success(request):
    data = json.loads(request.body)

    try:
        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })

        order = Order.objects.get(id=data['order_id'], user=request.user)

        order.is_paid = True
        order.status = "Confirmed"
        order.save()
        
        if order.coupon:
            order.coupon.times_used += 1
            order.coupon.save()

        for item in order.items.select_related('product'):
            if item.product:
                item.product_variant.stock -= item.quantity
                item.product.save()

        CartItem.objects.filter(user=request.user).delete()

        return JsonResponse({
            'status': 'success',
            'order_id': order.id,
            'redirect_url': f"/orders/success/{order.id}/"
        })

    except razorpay.errors.SignatureVerificationError:
        order = Order.objects.filter(id=data.get(
            'order_id'), user=request.user).first()
        if order:
            order.status = "Failed"
            order.save()

        return JsonResponse({
            'status': 'failure',
            'order_id': data.get('order_id'),
            'redirect_url': f"/orders/payment_failed/{data.get('order_id')}/"
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'status': 'failure',
            'order_id': data.get('order_id'),

            'message': 'Order not found',
            'redirect_url': "/orders/payment_failed/{order_id}/"
        })


@csrf_exempt
@login_required
def mark_payment_failed(request):
    if request.method == "POST":
        data = json.loads(request.body)
        order_id = data.get('order_id')

        try:
            order = Order.objects.get(id=order_id, user=request.user)
            order.status = "Failed"
            order.save()

            return JsonResponse({
                "status": "failed",
                "redirect_url": f"/orders/payment_failed/{order_id}/"
            })
        except Order.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Order not found",
                "redirect_url": f"/orders/payment_failed/{order_id}/"
            }, status=404)


@login_required
def payment_failed_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order/payment_failed.html', {'order': order})


@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    unavailable_items = []

    # Go through OrderItems (using related_name='items') and get related Product via ProductVariant
    for item in order.items.select_related('product_variant__product'):
        product = item.product_variant.product

        if not product or product.is_deleted or item.product_variant.stock < item.quantity:
            unavailable_items.append({
                'name': product.name if product else "Unknown Product",
                'ordered_qty': item.quantity,
                'available_stock': item.product_variant.stock if product else 0,
                'status': (
                    "Unlisted" if product and product.is_deleted else
                    "Out of Stock" if not product or item.product_variant.stock == 0 else
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
        orders = orders.filter(
            Q(id__icontains=query) | Q(status__icontains=query)
        )

    orders = orders.order_by('-created_at')  # Newest first

    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'order/order.html', {'orders': page_obj})


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)

    return render(request, 'order/order_detail.html', {
        'order': order,
        'items': items,
    })


@login_required
def cancel_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    if item.status not in ['Pending', 'Processing']:
        messages.error(request, "This item cannot be cancelled.")
        return redirect('orders:order_detail', order_id=item.order.id)

    if request.method == 'POST':
        reason_select = request.POST.get('reason_select', '')
        reason_text = request.POST.get('reason_text', '')
        reason = f"{reason_select} - {reason_text}".strip(" -")
        item.status = 'Cancelled'
        item.product_variant.stock += item.quantity
        item.product_variant.save()
        item.save()
        item.order.update_status_from_items()

        if item.order.payment_method != 'COD':
            user = request.user
            user.wallet.balance += item.subtotal()
            user.wallet.save()
            messages.success(
                request, f"Item cancelled and ₹{item.subtotal()} refunded to your wallet.")
        else:
            messages.success(
                request, "Item cancelled. No refund needed for COD orders.")

        return redirect('orders:order_detail', order_id=item.order.id)
    orderid = item.order.id
    return render(request, 'order/cancel_order_item.html', {'item': item, 'orderid': orderid})


@login_required
def order_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Only allow cancellation if all items are still cancellable
    cancellable_statuses = ['Pending', 'Processing']
    if not all(item.status in cancellable_statuses for item in order.items.all()):
        messages.error(
            request, "Some items have already been shipped or delivered. Full cancellation not allowed.")
        return redirect('orders:order_detail', order_id=order.id)

    if request.method == 'POST':
        reason_select = request.POST.get('reason_select', '')
        reason_text = request.POST.get('reason_text', '')
        reason = f"{reason_select} - {reason_text}".strip(" -")
        total_refund = 0

        for item in order.items.all():
            item.status = 'Cancelled'
            item.product_variant.stock += item.quantity
            item.product_variant.save()
            total_refund += item.subtotal()
            item.save()

        order.status = 'Cancelled'
        order.save()

        if order.payment_method != 'COD':
            user = request.user
            user.wallet.balance += total_refund
            user.save()
            messages.success(
                request, f"Order #{order.id} cancelled. ₹{total_refund} refunded to your wallet.")
        else:
            messages.success(
                request, f"Order #{order.id} cancelled. No refund needed for COD orders.")

        return redirect('orders:order_list')

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

    # Only allow full return if all items are delivered and not already returned
    if not all(item.status == 'Delivered' for item in order.items.all()):
        messages.error(request, "Only fully delivered orders can be returned.")
        return redirect('orders:order_detail', order_id=order.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a return reason.")
        else:
            # Create a return request and mark items as returned
            ReturnRequest.objects.create(order=order, reason=reason)
            for item in order.items.all():
                item.status = 'Returned'
                item.save()
            order.update_status_from_items()
            messages.success(
                request, "Return request submitted for the entire order.")
            return redirect('orders:order_detail', order_id=order.id)

    return render(request, 'order/return_order.html', {'order': order})


@login_required
def return_order_item(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)

    if item.status != 'Delivered':
        messages.error(request, "Only delivered items can be returned.")
        return redirect('orders:order_detail', order_id=item.order.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a return reason.")
        else:
            item.status = 'Returned'
            item.save()
            ReturnRequest.objects.create(order=item.order, reason=reason)
            item.order.update_status_from_items()
            messages.success(
                request, f"Return request submitted for item #{item.id}.")
            return redirect('orders:order_detail', order_id=item.order.id)

    return render(request, 'order/return_order_item.html', {'item': item})


def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    template_path = 'order/invoice.html'
    context = {'order': order,
               'items':order.items.all()}

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
