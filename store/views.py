from django.shortcuts import render, get_object_or_404
from .models import Product, Category

def store(request, category_slug=None):
    categories = None
    products = None

    if category_slug != None:
        # Filter by Category
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
        product_count = products.count()
    else:
        # Show All
        products = Product.objects.all().filter(is_available=True)
        product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)

def product_detail(request, category_slug, product_slug):
    try:
        # 1. Get the product ensuring it exists in that specific category
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
    except Exception as e:
        raise e # Or redirect to 404 page

    context = {
        'single_product': single_product,
    }
    return render(request, 'store/product_detail.html', context)