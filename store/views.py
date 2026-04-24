from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from inventory.models import Product, Category
from sales.models import Customer, Sale, SaleItem

def product_list(request):
    products = Product.objects.filter(quantity__gt=0).select_related('category')
    categories = Category.objects.all()
    q = request.GET.get('q', '')
    category_id = request.GET.get('category')
    if q:
        products = products.filter(name__icontains=q)
    if category_id:
        products = products.filter(category_id=category_id)
    cart_count = sum(request.session.get('cart', {}).values())
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'q': q,
        'selected_category': category_id,
        'cart_count': cart_count,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, quantity__gt=0)
    cart_count = sum(request.session.get('cart', {}).values())
    return render(request, 'store/product_detail.html', {'product': product, 'cart_count': cart_count})

def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, quantity__gt=0)
    cart = request.session.get('cart', {})
    qty = int(request.GET.get('quantity', 1))
    cart[str(pk)] = cart.get(str(pk), 0) + qty
    if cart[str(pk)] > product.quantity:
        cart[str(pk)] = product.quantity
        messages.warning(request, f"Only {product.quantity} available in stock.")
    request.session['cart'] = cart
    messages.success(request, f"Added {qty} x {product.name} to cart.")
    return redirect('store:cart')

def cart_view(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    for pk, qty in cart.items():
        try:
            prod = Product.objects.get(pk=pk)
            if qty > prod.quantity:
                qty = prod.quantity
                cart[pk] = qty
            subtotal = prod.selling_price * qty
            items.append({'product': prod, 'qty': qty, 'subtotal': subtotal})
            total += subtotal
        except Product.DoesNotExist:
            del cart[pk]
    request.session['cart'] = cart
    return render(request, 'store/cart.html', {'items': items, 'total': total})

def update_cart(request, pk):
    cart = request.session.get('cart', {})
    if request.method in ['POST', 'GET']:
        qty = int(request.POST.get('quantity', request.GET.get('quantity', 0)))
        if qty > 0:
            try:
                prod = Product.objects.get(pk=pk)
                if qty > prod.quantity:
                    qty = prod.quantity
                    messages.warning(request, f"Adjusted to available stock: {qty}")
                cart[str(pk)] = qty
            except Product.DoesNotExist:
                pass
        else:
            cart.pop(str(pk), None)
        request.session['cart'] = cart
    return redirect('store:cart')

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('store:product_list')
    
    items = []
    total = 0
    for pk, qty in cart.items():
        try:
            prod = Product.objects.get(pk=pk)
            if qty > prod.quantity:
                messages.error(request, f"Insufficient stock for {prod.name}.")
                return redirect('store:cart')
            subtotal = prod.selling_price * qty
            items.append({'product': prod, 'qty': qty, 'subtotal': subtotal})
            total += subtotal
        except Product.DoesNotExist:
            messages.error(request, "Some items are no longer available.")
            return redirect('store:cart')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        payment_method = request.POST.get('payment_method', 'CASH')
        
        if not name:
            messages.error(request, "Name is required.")
            return redirect('store:checkout')
        
        # Create customer
        customer = Customer.objects.create(name=name, phone=phone, email=email, address=address)
        
        # Create sale
        with transaction.atomic():
            sale = Sale.objects.create(payment_method=payment_method, customer=customer, total_amount=total, status='PENDING')
            for item in items:
                prod = item['product']
                qty = item['qty']
                price = prod.selling_price
                cost_price = prod.cost_price
                SaleItem.objects.create(sale=sale, product=prod, quantity=qty, price=price, cost_price=cost_price)
                # Note: Inventory will be deducted when order is approved in ERP
                # prod.quantity -= qty
                # prod.save()
        
        # Clear cart
        request.session['cart'] = {}
        messages.success(request, f"Order placed successfully! Order ID: {sale.id}")
        return redirect('store:product_list')
    
    return render(request, 'store/checkout.html', {'items': items, 'total': total})
