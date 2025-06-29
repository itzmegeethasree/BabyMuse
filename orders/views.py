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
from shop.models import CartItem, Address  # Adjust import paths as needed


@login_required
def checkout_view(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('shop:shop')

    addresses = Address.objects.filter(user=user)

    # Calculate price breakdown (common for both GET and POST)
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = Decimal('50.00') if subtotal < 1000 else Decimal('0.00')
    discount = Decimal('0.00')  # If you add coupon logic later, update here
    tax = subtotal * Decimal('0.05')
    total = subtotal + tax + shipping - discount

    if request.method == 'POST':
        selected_address_id = request.POST.get('address')
        address = get_object_or_404(Address, id=selected_address_id, user=user)

        # Create order
        order = Order.objects.create(
            user=user,
            address=address,
            payment_method='COD',
            total_price=total
        )

        # Create order items and update stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            item.product.stock -= item.quantity
            item.product.save()

        # Clear cart after placing order
        cart_items.delete()

        # namespace check
        return redirect('orders:order_success', order_id=order.id)

    # GET request: show checkout form
    context = {
        'cart_items': cart_items,
        'addresses': addresses,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'discount': discount,
        'total': total
    }
    return render(request, 'order/checkout.html', context)


@login_required
def order_success(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)
    return render(request, 'order/order_success.html', {'order': order})


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
