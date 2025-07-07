from django.urls import path
from . import views
from .views import toggle_user_status


app_name = 'admin_panel'

urlpatterns = [
    # Auth
    path('login/', views.custom_admin_login, name='custom_admin_login'),
    path('logout/', views.custom_admin_logout,
         name='custom_admin_logout'),
    path('forgot-password/', views.admin_forgot_password,
         name='admin_forgot_password'),

    # Dashboard & Profile
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('profile/', views.admin_profile, name='admin_profile'),
    path('change-password/', views.change_admin_password,
         name='admin_change_password'),

    # Orders
    path('orders/', views.admin_orders, name='admin_orders'),
    path('orders/<int:order_id>/', views.admin_order_detail,
         name='admin_order_detail'),
    path('orders/<int:order_id>/invoice/',
         views.order_invoice, name='admin_order_invoice'),
    path('orders/<int:order_id>/change-status/',
         views.change_order_status, name='admin_change_order_status'),
    path('returns/', views.admin_return_requests, name='admin_return_requests'),
    path('returns/<int:return_id>/verify/',
         views.verify_return_request, name='verify_return_request'),




    # Products
    path('products/', views.admin_products, name='admin_products'),
    path('products/new/', views.admin_add_product, name='admin_add_product'),
    path('products/<int:product_id>/edit/',
         views.admin_edit_product, name='admin_edit_product'),
    path('products/<int:product_id>/toggle/',
         views.admin_toggle_product_visibility, name='admin_toggle_product'),

    # Categories
    path('categories/', views.category_list, name='admin_category_list'),
    path('categories/add/', views.add_category, name='admin_add_category'),
    path('categories/edit/<int:category_id>/',
         views.edit_category, name='admin_edit_category'),
    path('categories/delete/<int:category_id>/',
         views.delete_category, name='admin_delete_category'),

    # Customers
    path('customers/', views.admin_customer_list, name='admin_customer_list'),
    path('customers/<int:customer_id>/',
         views.admin_view_customer, name='admin_view_customer'),
    path('users/<int:user_id>/toggle/',
         toggle_user_status, name='toggle_user_status'),

]
