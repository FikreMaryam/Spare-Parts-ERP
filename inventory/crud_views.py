from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from core.permissions import AdminRequiredMixin, SalesOrAdminRequiredMixin
from .models import Product, Warehouse, Category, CarMake, CarModel, Supplier

# Base classes to keep it DRY
class AdminCRUDMixin(AdminRequiredMixin):
    template_name = 'generic_form.html'

class AdminDeleteMixin(AdminRequiredMixin):
    template_name = 'confirm_delete.html'

# --- Product ---
class ProductCreateView(AdminCRUDMixin, CreateView):
    model = Product
    fields = '__all__'
    success_url = reverse_lazy('product_list')

class ProductUpdateView(AdminCRUDMixin, UpdateView):
    model = Product
    fields = '__all__'
    success_url = reverse_lazy('product_list')

class ProductDeleteView(AdminDeleteMixin, DeleteView):
    model = Product
    success_url = reverse_lazy('product_list')

# --- Warehouse ---
class WarehouseCreateView(AdminCRUDMixin, CreateView):
    model = Warehouse
    fields = ['name', 'location', 'description']
    success_url = reverse_lazy('warehouse_list')

class WarehouseUpdateView(AdminCRUDMixin, UpdateView):
    model = Warehouse
    fields = ['name', 'location', 'description']
    success_url = reverse_lazy('warehouse_list')

class WarehouseDeleteView(AdminDeleteMixin, DeleteView):
    model = Warehouse
    success_url = reverse_lazy('warehouse_list')

# Generic List View for other models
class GenericListView(SalesOrAdminRequiredMixin, ListView):
    template_name = 'generic_list.html'
    context_object_name = 'objects'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['model_name'] = self.model._meta.verbose_name.title()
        ctx['create_url_name'] = f"{self.model._meta.model_name}_create"
        ctx['update_url_name'] = f"{self.model._meta.model_name}_update"
        ctx['delete_url_name'] = f"{self.model._meta.model_name}_delete"
        return ctx

# --- Category ---
class CategoryListView(GenericListView):
    model = Category
class CategoryCreateView(AdminCRUDMixin, CreateView):
    model = Category
    fields = ['name']
    success_url = reverse_lazy('category_list')
class CategoryUpdateView(AdminCRUDMixin, UpdateView):
    model = Category
    fields = ['name']
    success_url = reverse_lazy('category_list')
class CategoryDeleteView(AdminDeleteMixin, DeleteView):
    model = Category
    success_url = reverse_lazy('category_list')

# --- CarMake ---
class CarMakeListView(GenericListView):
    model = CarMake
class CarMakeCreateView(AdminCRUDMixin, CreateView):
    model = CarMake
    fields = ['name']
    success_url = reverse_lazy('carmake_list')
class CarMakeUpdateView(AdminCRUDMixin, UpdateView):
    model = CarMake
    fields = ['name']
    success_url = reverse_lazy('carmake_list')
class CarMakeDeleteView(AdminDeleteMixin, DeleteView):
    model = CarMake
    success_url = reverse_lazy('carmake_list')

# --- CarModel ---
class CarModelListView(GenericListView):
    model = CarModel
class CarModelCreateView(AdminCRUDMixin, CreateView):
    model = CarModel
    fields = ['make', 'name', 'year_from', 'year_to', 'engine_type', 'chassis_prefixes']
    success_url = reverse_lazy('carmodel_list')
class CarModelUpdateView(AdminCRUDMixin, UpdateView):
    model = CarModel
    fields = ['make', 'name', 'year_from', 'year_to', 'engine_type', 'chassis_prefixes']
    success_url = reverse_lazy('carmodel_list')
class CarModelDeleteView(AdminDeleteMixin, DeleteView):
    model = CarModel
    success_url = reverse_lazy('carmodel_list')

# --- Supplier ---
class SupplierListView(GenericListView):
    model = Supplier
class SupplierCreateView(AdminCRUDMixin, CreateView):
    model = Supplier
    fields = ['name', 'contact']
    success_url = reverse_lazy('supplier_list')
class SupplierUpdateView(AdminCRUDMixin, UpdateView):
    model = Supplier
    fields = ['name', 'contact']
    success_url = reverse_lazy('supplier_list')
class SupplierDeleteView(AdminDeleteMixin, DeleteView):
    model = Supplier
    success_url = reverse_lazy('supplier_list')
