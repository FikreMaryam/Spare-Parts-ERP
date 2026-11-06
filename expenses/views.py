import csv
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .models import Expense
from .forms import ExpenseForm

class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    ordering = ['-date', '-id']

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip()
        start_date = self.request.GET.get('start_date', '').strip()
        end_date = self.request.GET.get('end_date', '').strip()

        if query:
            qs = qs.filter(title__icontains=query)
        if category:
            qs = qs.filter(category=category)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # Calculate totals for filtered query
        total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0.0
        context['total_amount'] = total_amount
        context['expense_count'] = queryset.count()
        context['categories'] = Expense.CATEGORY_CHOICES

        # Calculate category breakdown
        category_breakdown = {}
        for cat_code, cat_label in Expense.CATEGORY_CHOICES:
            cat_sum = queryset.filter(category=cat_code).aggregate(total=Sum('amount'))['total'] or 0.0
            category_breakdown[cat_code] = {
                'label': cat_label,
                'amount': cat_sum,
                'percentage': round((cat_sum / total_amount * 100), 1) if total_amount > 0 else 0
            }
        context['category_breakdown'] = category_breakdown

        # Retain filter params in context
        context['current_q'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_start_date'] = self.request.GET.get('start_date', '')
        context['current_end_date'] = self.request.GET.get('end_date', '')
        return context

class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'generic_form.html'
    success_url = reverse_lazy('expense_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Expense'
        return context

class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'generic_form.html'
    success_url = reverse_lazy('expense_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Expense'
        return context

class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('expense_list')

@login_required
def export_expenses_csv(request):
    """Export filtered or all expenses to a CSV spreadsheet."""
    qs = Expense.objects.all().order_by('-date', '-id')
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if query:
        qs = qs.filter(title__icontains=query)
    if category:
        qs = qs.filter(category=category)
    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Category', 'Amount', 'Date'])

    for e in qs:
        writer.writerow([e.id, e.title, e.get_category_display(), f"{e.amount:.2f}", e.date])

    return response



