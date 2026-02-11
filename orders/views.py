from django.shortcuts import render, redirect
from django.http import HttpResponse
from carts.models import CartItem, Cart
from .forms import OrderForm
from .models import Order
import datetime

def place_order(request, total=0, quantity=0):
    current_user = request.user

    # 1. If the cart count is <= 0, redirect to store.
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    # 2. Handle the POST request
    if request.method == 'POST':
        form = OrderForm(request.POST)
        
        if form.is_valid():
            # Store all the billing info inside Order table
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
            data.order_total = 0 # Placeholder, we calculate below
            data.tax = 0         # Placeholder
            data.ip = request.META.get('REMOTE_ADDR')
            data.save() # Save to generate an ID

            # 3. Generate Order Number (Year + Month + Day + ID)
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d")
            
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # 4. Calculate Order Total
            cart_items = CartItem.objects.filter(user=current_user)
            for item in cart_items:
                total += (item.product.price * item.quantity)
                quantity += item.quantity
            
            tax = (2 * total)/100
            grand_total = total + tax
            
            data.order_total = grand_total
            data.tax = tax
            data.save()

            # 5. Send order data to the next page (Payment)
            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
            
    else:
        return redirect('checkout')