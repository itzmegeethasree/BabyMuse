from django.urls import path
from . import views

urlpatterns = [

    # 🛍️ Shop Pages
    path('', views.shop_view, name='shop'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/', views.ajax_add_to_wishlist,
         name='ajax_add_to_wishlist'),
    path('wishlist/remove/', views.ajax_remove_from_wishlist,
         name='ajax_remove_from_wishlist'),
    path("add-to-wishlist-direct/", views.direct_add_to_wishlist,
         name="direct_add_to_wishlist"),

    # Cart
    path("add-to-cart-direct/", views.direct_add_to_cart,
         name="direct_add_to_cart"),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    path('cart/remove/', views.ajax_remove_from_cart,
         name='ajax_remove_from_cart'),
    path('cart/update/<int:variant_id>/', views.ajax_update_cart_quantity,
         name='ajax_update_cart_quantity'),
    path('cart/data/', views.ajax_cart_data, name='ajax_cart_data'),

]
