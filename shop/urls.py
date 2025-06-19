from django.urls import path
from . import views
urlpatterns = [
    path('', views.shop_view, name='shop'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/',
         views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/',
         views.remove_from_wishlist, name='remove_from_wishlist'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/',
         views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/',
         views.update_cart_quantity, name='update_cart_quantity'),
    path('ajax/add-to-cart/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    path('ajax/add-to-wishlist/', views.ajax_add_to_wishlist,
         name='ajax_add_to_wishlist'),
    path('remove-from-cart-ajax/', views.remove_from_cart_ajax,
         name='remove_from_cart_ajax'),


]
