from difflib import get_close_matches
from django.http import JsonResponse
from django.shortcuts import render
from shop.models import Product
from .models import FAQ, Banner
from user.models import BabyProfile
from django.db.models import Q


def home_view(request):
    customized = False
    product_data = []
    has_baby_profile = False
    babies = None

    if request.user.is_authenticated:
        babies = request.user.babies.all()
        has_baby_profile = babies.exists()

        if has_baby_profile:
            # Filter products based on baby profiles
            age_gender_filters = []
            for baby in babies:
                age = baby.age_in_months()
                gender = baby.baby_gender
                age_gender_filters.append(
                    Q(min_age__isnull=True, max_age__isnull=True, gender='Unisex') |
                    Q(min_age__lte=age, max_age__gte=age, gender__in=[gender, 'Unisex'])
                )

            products_query = Q()
            for f in age_gender_filters:
                products_query |= f

            products = Product.objects.filter(status='Active').filter(products_query).distinct()

            # Filter banners based on baby profile
            all_banners = Banner.objects.filter(is_active=True)
            personalized_banners = set()

            for baby in babies:
                for banner in all_banners:
                    if banner.is_suitable_for(baby):
                        personalized_banners.add(banner)

            banners = list(personalized_banners)
            customized = True

        else:
            # No baby profile: show generic products and all banners
            products = Product.objects.filter(status='Active')[:6]
            banners = Banner.objects.filter(is_active=True)

    else:
        # Anonymous user: show generic products and all banners
        products = Product.objects.filter(status='Active')[:6]
        banners = Banner.objects.filter(is_active=True)

    # Enrich products with default variant and price
    for product in products:
        variant = product.get_default_variant()
        price = variant.get_offer_price() if variant else product.min_offer_price
        product_data.append({
            'product': product,
            'variant': variant,
            'price': price,
        })

    return render(request, 'core/home.html', {
        'products': product_data,
        'banners': banners,
        'customized': customized,
        'has_baby_profile': has_baby_profile,
        'baby': babies.first() if has_baby_profile else None,
    })

def search(request):
    query = request.GET.get('query', '')
    results = []
    return render(request, 'core/search_results.html', {
        'query': query,
        'results': results
    })


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    return render(request, 'core/contact.html')

#FAQ ChatBot


def faq_bot_response(request):
    query = request.GET.get('q', '').strip()
    questions = FAQ.objects.filter(is_active=True).values_list('question', flat=True)
    match = get_close_matches(query, questions, n=1, cutoff=0.6)
    if match:
        answer = FAQ.objects.get(question=match[0]).answer
        return JsonResponse({'answer': answer})
    return JsonResponse({'answer': "Sorry, I couldn't find an answer. Would you like to talk to support?"})
