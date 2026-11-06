from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from inventory.models import (
    Product, Category, CarMake, CarModel,
    AssemblyCategory, AssemblyDiagram, DiagramCallout, PartSubstitute
)
from sales.models import Customer, Sale, SaleItem


def partsouq_catalog(request):
    """Partsouq & Amayama main catalog portal landing page."""
    makes = CarMake.objects.all().prefetch_related('models')
    assembly_categories = AssemblyCategory.objects.all()
    featured_products = Product.objects.prefetch_related('compatibilities', 'compatibilities__make').filter(quantity__gt=0, is_genuine=True)[:8]
    cart_count = sum(request.session.get('cart', {}).values())

    all_models = CarModel.objects.select_related('make').all()
    # Get recent diagrams
    diagrams = AssemblyDiagram.objects.select_related('car_model', 'category')[:6]

    return render(request, 'store/partsouq_catalog.html', {
        'makes': makes,
        'all_models': all_models,
        'assembly_categories': assembly_categories,
        'featured_products': featured_products,
        'diagrams': diagrams,
        'cart_count': cart_count,
    })


def vin_lookup(request):
    """VIN / Frame Number Decoder Search."""
    query = request.GET.get('vin', '').strip()
    cart_count = sum(request.session.get('cart', {}).values())
    matched_models = []

    if query:
        # Search using chassis_prefixes or name/make match
        for model in CarModel.objects.select_related('make').all():
            if model.matches_chassis(query):
                matched_models.append(model)
        
        # Fallback keyword match if no direct prefix match
        if not matched_models:
            matched_models = list(CarModel.objects.select_related('make').filter(
                Q(name__icontains=query) | Q(make__name__icontains=query) | Q(chassis_prefixes__icontains=query)
            ))

    assembly_categories = AssemblyCategory.objects.all()

    return render(request, 'store/vin_lookup_results.html', {
        'query': query,
        'matched_models': matched_models,
        'assembly_categories': assembly_categories,
        'cart_count': cart_count,
    })


def vehicle_categories(request, model_id):
    """Browse Assembly Categories and Schematics for a Car Model."""
    car_model = get_object_or_404(CarModel.objects.select_related('make'), pk=model_id)
    assembly_categories = AssemblyCategory.objects.all()

    # Diagrams for this car model grouped by category
    diagrams = AssemblyDiagram.objects.filter(car_model=car_model).select_related('category')
    cart_count = sum(request.session.get('cart', {}).values())

    selected_cat_id = request.GET.get('category')
    if selected_cat_id:
        diagrams = diagrams.filter(category_id=selected_cat_id)

    return render(request, 'store/vehicle_categories.html', {
        'car_model': car_model,
        'assembly_categories': assembly_categories,
        'diagrams': diagrams,
        'selected_category_id': selected_cat_id,
        'cart_count': cart_count,
    })


def diagram_detail(request, pk):
    """Interactive Partsouq Exploded Schematic Diagram View."""
    diagram = get_object_or_404(
        AssemblyDiagram.objects.select_related('car_model', 'car_model__make', 'category'),
        pk=pk
    )
    callouts = diagram.callouts.select_related('product', 'product__category').all()
    cart_count = sum(request.session.get('cart', {}).values())

    return render(request, 'store/diagram_detail.html', {
        'diagram': diagram,
        'callouts': callouts,
        'cart_count': cart_count,
    })


def oem_search(request):
    """Search by OEM Part Number, Description, or Brand, filtered by Car Model."""
    query = request.GET.get('q', '').strip()
    model_id = request.GET.get('car_model', '').strip()
    make_id = request.GET.get('make', '').strip()

    products = Product.objects.prefetch_related('compatibilities', 'compatibilities__make').select_related('category').all()

    selected_model = None
    selected_make = None

    if make_id:
        try:
            selected_make = CarMake.objects.get(pk=make_id)
            products = products.filter(
                Q(compatibilities__make_id=make_id) |
                Q(vehicle_application__icontains=selected_make.name)
            ).distinct()
        except (CarMake.DoesNotExist, ValueError):
            pass

    if model_id:
        try:
            selected_model = CarModel.objects.select_related('make').get(pk=model_id)
            products = products.filter(
                Q(compatibilities__id=model_id) |
                Q(vehicle_application__icontains=selected_model.name) |
                Q(vehicle_application__icontains=selected_model.make.name)
            ).distinct()
        except (CarModel.DoesNotExist, ValueError):
            pass

    if query:
        products = products.filter(
            Q(part_number__icontains=query) |
            Q(alternate_numbers__icontains=query) |
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(brand__icontains=query) |
            Q(vehicle_application__icontains=query)
        ).distinct()

    all_makes = CarMake.objects.all().prefetch_related('models')
    all_models = CarModel.objects.select_related('make').all()
    cart_count = sum(request.session.get('cart', {}).values())

    return render(request, 'store/oem_search_results.html', {
        'query': query,
        'products': products,
        'selected_model': selected_model,
        'selected_make': selected_make,
        'selected_model_id': model_id,
        'selected_make_id': make_id,
        'all_makes': all_makes,
        'all_models': all_models,
        'cart_count': cart_count,
    })


def oem_part_detail(request, pk):
    """OEM Part Detail Page with Genuine / Aftermarket Substitutes & Fitment list."""
    product = get_object_or_404(Product.objects.prefetch_related('compatibilities', 'compatibilities__make'), pk=pk)
    substitutes = PartSubstitute.objects.filter(original_product=product).select_related('substitute_product')
    reverse_substitutes = PartSubstitute.objects.filter(substitute_product=product).select_related('original_product')

    compatibilities = product.compatibilities.select_related('make').all()
    cart_count = sum(request.session.get('cart', {}).values())

    return render(request, 'store/oem_part_detail.html', {
        'product': product,
        'substitutes': substitutes,
        'reverse_substitutes': reverse_substitutes,
        'compatibilities': compatibilities,
        'cart_count': cart_count,
    })


def product_list(request):
    return partsouq_catalog(request)


def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = request.session.get('cart', {})
    qty = int(request.GET.get('quantity', 1))
    cart[str(pk)] = cart.get(str(pk), 0) + qty
    if product.quantity > 0 and cart[str(pk)] > product.quantity:
        cart[str(pk)] = product.quantity
        messages.warning(request, f"Adjusted to available stock for {product.name}.")
    request.session['cart'] = cart
    messages.success(request, f"✓ Added {qty} x {product.name} to your shopping cart!")
    
    referer = request.META.get('HTTP_REFERER')
    if referer and 'cart' not in referer:
        return redirect(referer)
    return redirect('store:partsouq_catalog')


def cart_view(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    for pk, qty in cart.items():
        try:
            prod = Product.objects.get(pk=pk)
            if prod.quantity > 0 and qty > prod.quantity:
                qty = prod.quantity
                cart[pk] = qty
            subtotal = prod.selling_price * qty
            items.append({'product': prod, 'qty': qty, 'subtotal': subtotal})
            total += subtotal
        except Product.DoesNotExist:
            del cart[pk]
    request.session['cart'] = cart
    return render(request, 'store/cart.html', {'items': items, 'total': total, 'cart_count': sum(cart.values())})


def update_cart(request, pk):
    cart = request.session.get('cart', {})
    if request.method in ['POST', 'GET']:
        qty = int(request.POST.get('quantity', request.GET.get('quantity', 0)))
        if qty > 0:
            try:
                prod = Product.objects.get(pk=pk)
                if prod.quantity > 0 and qty > prod.quantity:
                    qty = prod.quantity
                    messages.warning(request, "Adjusted to available stock.")
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
        return redirect('store:partsouq_catalog')
    
    items = []
    total = 0
    for pk, qty in cart.items():
        try:
            prod = Product.objects.get(pk=pk)
            subtotal = prod.selling_price * qty
            items.append({'product': prod, 'qty': qty, 'subtotal': subtotal})
            total += subtotal
        except Product.DoesNotExist:
            messages.error(request, "Some items are no longer available.")
            return redirect('store:cart')
    
    # Retrieve customer profile from session if available
    saved_customer_id = request.session.get('customer_id')
    saved_customer = None
    if saved_customer_id:
        try:
            saved_customer = Customer.objects.get(pk=saved_customer_id)
        except Customer.DoesNotExist:
            saved_customer = None

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        payment_method = request.POST.get('payment_method', 'CASH')
        
        if not name:
            messages.error(request, "Full Name is required for your customer account.")
            return redirect('store:checkout')

        if not phone:
            messages.error(request, "Phone number is required so shop staff can contact you to confirm your order.")
            return redirect('store:checkout')
        
        customer, created = Customer.objects.get_or_create(
            phone=phone,
            defaults={'name': name, 'email': email, 'address': address}
        )
        if not created:
            customer.name = name
            if email: customer.email = email
            if address: customer.address = address
            customer.save()
        
        # Save customer account in session
        request.session['customer_id'] = customer.id
        request.session['customer_name'] = customer.name
        request.session['customer_phone'] = customer.phone

        with transaction.atomic():
            sale = Sale.objects.create(
                payment_method=payment_method,
                customer=customer,
                total_amount=total,
                status='PENDING'
            )
            from inventory.models import StockMovement
            for item in items:
                prod = item['product']
                qty = item['qty']
                price = prod.selling_price
                cost_price = prod.cost_price
                SaleItem.objects.create(
                    sale=sale,
                    product=prod,
                    quantity=qty,
                    price=price,
                    cost_price=cost_price
                )
                if prod.quantity >= qty:
                    prod.quantity -= qty
                    prod.save()

                StockMovement.objects.create(
                    product=prod,
                    quantity=-qty,
                    movement_type="sale",
                    reference=f"Online Store Order #{sale.id} ({customer.name})"
                )
        
        request.session['cart'] = {}
        messages.success(request, f"Online order #{sale.id} placed successfully! Your order is pending approval by FETAN SPARE PARTS staff.")
        return redirect('store:partsouq_catalog')
    
    return render(request, 'store/checkout.html', {
        'items': items,
        'total': total,
        'cart_count': sum(cart.values()),
        'saved_customer': saved_customer,
    })


def about_us(request):
    """About Us page for FETAN SPARE PARTS."""
    cart_count = sum(request.session.get('cart', {}).values())
    return render(request, 'store/about.html', {
        'cart_count': cart_count,
        'company_name': 'FETAN SPARE PARTS',
        'address': 'Teklehaymanot Addis Hope Building House number G22',
        'city': 'Addis Ababa, Ethiopia',
    })

