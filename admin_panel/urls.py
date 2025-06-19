from django.urls import path
from . import views
appname = 'admin_panel'
urlpatterns = [
    path('login/', views.custom_admin_login, name='custom_admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('forgot-password/', views.admin_forgot_password,
         name='admin_forgot_password'),
    path('profile/', views.admin_profile, name='admin_profile'),
    path('change-password/', views.change_admin_password,
         name='admin_change_password'),
    path('orders/', views.admin_orders, name='admin_orders'),
    path('orders/<int:order_id>/', views.admin_order_detail,
         name='admin_order_detail'),
    path('products/', views.admin_products, name='admin_products'),
    path('products/new/', views.admin_add_product, name='admin_add_product'),
    path('products/<int:product_id>/edit/',
         views.admin_edit_product, name='admin_edit_product'),
    path('products/<int:product_id>/delete/',
         views.admin_delete_product, name='admin_delete_product'),

    path('categories/', views.admin_category_list, name='admin_category_list'),
    path('categories/add/', views.admin_add_category, name='admin_add_category'),
    path('categories/edit/<int:category_id>/',
         views.admin_edit_category, name='admin_edit_category'),
    path('categories/delete/<int:category_id>/',
         views.admin_delete_category, name='admin_delete_category'),
    path('customers/', views.admin_customer_list, name='admin_customer_list'),
    path('customers/<int:customer_id>/',
         views.admin_view_customer, name='admin_view_customer'),








]
