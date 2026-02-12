from django.shortcuts import render, redirect
from django.http import HttpResponse
from carts.models import CartItem, Cart
from .forms import OrderForm
from .models import Order
import datetime
import json
from django.http import JsonResponse
from .models import Order, Payment, OrderProduct
from store.models import Product
from carts.models import CartItem
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from carts.views import _cart_id  # <--- Ensure this import exists

def place_order(request, total=0, quantity=0):
    current_user = request.user

    # --- FIX 1: Fetch items by SESSION (Cart), not USER ---
    # We use the _cart_id helper to find the correct cart
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    except Cart.DoesNotExist:
        cart_items = []

    cart_count = cart_items.count()
    
    # DEBUG PRINT 1
    print("Cart Count is:", cart_count)

    if cart_count <= 0:
        return redirect('store')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        
        if form.is_valid():
            # Store data
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = 0
            data.tax = 0
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate Order Number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # Calculate Order Total
            # --- FIX 2: Use the same cart_items list we fetched at the top ---
            for item in cart_items:
                total += (item.product.price * item.quantity)
                quantity += item.quantity
            
            tax = (2 * total)/100
            grand_total = total + tax
            
            data.order_total = grand_total
            data.tax = tax
            data.save()
            
            # --- FIX 3: Fetch the order using the ID we just created ---
            # (Fetching by user/order_number can be buggy if multiple orders exist)
            order = Order.objects.get(id=data.id) 
            
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
        
        else:
            # DEBUG PRINT 2: Show why the form failed
            print("Form is INVALID:", form.errors)
            return redirect('checkout') # Redirect back to fix errors

    return redirect('checkout')
    
def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])

    # 1. Store Transaction Details inside Payment model
    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        amount_paid = order.order_total,
        status = body['status'],
    )
    payment.save()

    # 2. Update the Order model (Mark as Ordered)
    order.payment = payment
    order.is_ordered = True
    order.save()

    # 3. Move the Cart Items to Order Product table
    cart_items = CartItem.objects.filter(user=request.user)

    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()

        # 4. Reduce the quantity of the sold products
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    # 5. Clear Cart
    CartItem.objects.filter(user=request.user).delete()

    # 6. Send data back to JS callback so it can redirect us
    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }
    return JsonResponse(data)    

def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity

        payment = Payment.objects.get(payment_id=transID)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'orders/order_complete.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')