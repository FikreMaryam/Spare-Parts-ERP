from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def is_admin(user):
    return user.is_active and user.is_superuser

def is_sales_or_admin(user):
    if not user.is_active:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name='Sales').exists()

def admin_required(view_func):
    """Decorator for views that checks that the user is an admin."""
    def check_perms(user):
        if is_admin(user):
            return True
        raise PermissionDenied
    return user_passes_test(check_perms)(view_func)

def sales_or_admin_required(view_func):
    """Decorator for views that checks that the user is an admin or in Sales group."""
    def check_perms(user):
        if is_sales_or_admin(user):
            return True
        raise PermissionDenied
    return user_passes_test(check_perms)(view_func)

# Helper class mixins for generic CBVs
from django.contrib.auth.mixins import UserPassesTestMixin

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)

class SalesOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_sales_or_admin(self.request.user)
