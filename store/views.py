from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from inventory.models import Product, Category
from sales.models import Sale, SaleItem, Customer

def product_list(request):
    products = Product.objects.filter(quantity__gt=0).select_related('category')
    categories = Category.objects.all()
    q = request.GET.get('q', '')
    category_id = request.GET.get('category')
    if q:
        products = products.filter(name__icontains=q)
    if category_id:
        products = products.filter(category_id=category_id)
    cart_count = sum(request.session.get('store_cart', {}).values())
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'q': q,
        'selected_category': category_id,
        'cart_count': cart_count,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, quantity__gt=0)
    cart_count = sum(request.session.get('store_cart', {}).values())
    return render(request, 'store/product_detail.html', {'product': product, 'cart_count': cart_count})

def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, quantity__gt=0)
    cart = request.session.get('store_cart', {})
    cart[str(pk)] = cart.get(str(pk), 0) + 1
    if cart[str(pk)] > product.quantity:
        cart[str(pk)] = product.quantity
        messages.warning(request, f"Only {product.quantity} available in stock.")
    request.session['store_cart'] = cart
    messages.success(request, f"Added {product.name} to cart.")
    return redirect('product_detail', pk=pk)

def cart_view(request):
    cart = request.session.get('store_cart', {})
    products = []
    total = 0
    for pk, qty in cart.items():
        try:
            prod = Product.objects.get(pk=pk)
            if qty > prod.quantity:
                qty = prod.quantity
                cart[pk] = qty
            products.append((prod, qty))
            total += prod.selling_price * qty
        except Product.DoesNotExist:
            del cart[pk]
    request.session['store_cart'] = cart
    return render(request, 'store/cart.html', {'products': products, 'total': total})

def update_cart(request, pk):
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 0))
        cart = request.session.get('store_cart', {})
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
        request.session['store_cart'] = cart
    return redirect('cart')

def checkout(request):
    cart = request.session.get('store_cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('store_home')
    
    products = []
    total = 0
    for pk, qty in cart.items():
        try:
            prod = Product.objects.get(pk=pk)
            if qty > prod.quantity:
                messages.error(request, f"Insufficient stock for {prod.name}.")
                return redirect('cart')
            products.append((prod, qty))
            total += prod.selling_price * qty
        except Product.DoesNotExist:
            messages.error(request, "Some items are no longer available.")
            return redirect('cart')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        with transaction.atomic():
            # Create or get customer
            customer, created = Customer.objects.get_or_create(
                email=email,
                defaults={'name': name, 'phone': phone, 'address': address}
            )
            if not created:
                customer.name = name
                customer.phone = phone
                customer.address = address
                customer.save()
            
            # Create sale
            sale = Sale.objects.create(
                payment_method='ONLINE',
                total_amount=total,
                customer=customer
            )
            
            for prod, qty in products:
                SaleItem.objects.create(
                    sale=sale,
                    product=prod,
                    quantity=qty,
                    price=prod.selling_price,
                    cost_price=prod.cost_price
                )
                # Reduce stock
                prod.quantity -= qty
                prod.save()
            
            # Award loyalty points
            sale.award_loyalty_points()
            
            # Clear cart
            request.session['store_cart'] = {}
            
            messages.success(request, f"Order placed successfully! Order ID: {sale.id}")
            return redirect('order_success', sale_id=sale.id)
    
    return render(request, 'store/checkout.html', {'products': products, 'total': total})

def order_success(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    return render(request, 'store/order_success.html', {'sale': sale})
