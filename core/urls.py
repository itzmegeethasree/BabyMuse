from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('search/', views.search, name='search'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq-bot/', views.faq_bot_response, name='faq_bot_response'),



]
