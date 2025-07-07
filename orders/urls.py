from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkouts/', views.checkout_view, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('order/', views.order_list_view, name='order'),
    path('order_detail/<int:order_id>/',
         views.order_detail_view, name='order_detail'),
    path('order_cancel/<int:order_id>/',
         views.cancel_order, name='order_cancel'),
    path('return/<int:order_id>/', views.return_order, name='return_order'),
    path('invoice/<int:order_id>/',
         views.download_invoice, name='download_invoice'),
    path('razorpay/success/', views.razorpay_success, name='razorpay_success'),
    path('payment-failed/<int:order_id>/',
         views.payment_failed_view, name='payment_failed'),
    path('payment-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),








]
