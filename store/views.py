from django.shortcuts import render, get_object_or_404
from inventory.models import Product, Category

def product_list(request):
    products = Product.objects.filter(quantity__gt=0).select_related('category')
    categories = Category.objects.all()
    q = request.GET.get('q', '')
    category_id = request.GET.get('category')
    if q:
        products = products.filter(name__icontains=q)
    if category_id:
        products = products.filter(category_id=category_id)
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'q': q,
        'selected_category': category_id,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, quantity__gt=0)
    return render(request, 'store/product_detail.html', {'product': product})
