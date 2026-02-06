from django.shortcuts import render, redirect
from store.models import Product
from .models import Cart, CartItem

# Private function to get the session key (the "Cart ID")
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart