from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

ADMIN_ROLE = 'Admin'
SALES_ROLE = 'Sales'
INVENTORY_ROLE = 'Inventory'
FINANCE_ROLE = 'Finance'
HR_ROLE = 'HR'
SUPPORT_ROLE = 'Support'

ROLE_SEQUENCE = (
    ADMIN_ROLE,
    SALES_ROLE,
    INVENTORY_ROLE,
    FINANCE_ROLE,
    HR_ROLE,
    SUPPORT_ROLE,
)


def get_user_roles(user):
    """Return the set of role names currently assigned to the user."""
    if not user or not getattr(user, 'is_authenticated', False):
        return set()

    roles = set()
    if user.is_superuser:
        roles.add(ADMIN_ROLE)

    for role_name in ROLE_SEQUENCE:
        if user.groups.filter(name=role_name).exists():
            roles.add(role_name)

    return roles


def user_has_role(user, role_name):
    return role_name in get_user_roles(user)


def user_has_any_role(user, *role_names):
    if not user or not getattr(user, 'is_active', False):
        return False
    if not role_names:
        return False
    return any(user_has_role(user, role_name) for role_name in role_names)


def ensure_default_roles():
    """Create default ERP roles if they do not already exist."""
    created = []
    for role_name in ROLE_SEQUENCE:
        group, was_created = Group.objects.get_or_create(name=role_name)
        if was_created:
            created.append(role_name)
    return created


def is_admin(user):
    return user.is_active and user_has_any_role(user, ADMIN_ROLE)


def is_sales_or_admin(user):
    return user.is_active and user_has_any_role(user, ADMIN_ROLE, SALES_ROLE)


def is_inventory_or_admin(user):
    return user.is_active and user_has_any_role(user, ADMIN_ROLE, INVENTORY_ROLE)


def is_finance_or_admin(user):
    return user.is_active and user_has_any_role(user, ADMIN_ROLE, FINANCE_ROLE)


def is_hr_or_admin(user):
    return user.is_active and user_has_any_role(user, ADMIN_ROLE, HR_ROLE)


def require_role(*allowed_roles):
    """Return a decorator that grants access to users assigned to one of the allowed roles."""
    allowed_roles = tuple(allowed_roles or (ADMIN_ROLE,))

    def decorator(view_func):
        def check_perms(user):
            if user_has_any_role(user, *allowed_roles):
                return True
            raise PermissionDenied
        return user_passes_test(check_perms)(view_func)

    return decorator


def admin_required(view_func):
    """Decorator for views that checks that the user is an admin."""
    return require_role(ADMIN_ROLE)(view_func)


def sales_or_admin_required(view_func):
    """Decorator for views that checks that the user is an admin or in Sales group."""
    return require_role(ADMIN_ROLE, SALES_ROLE)(view_func)


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)


class SalesOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_sales_or_admin(self.request.user)


class InventoryOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_inventory_or_admin(self.request.user)


class FinanceOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_finance_or_admin(self.request.user)


class HrOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_hr_or_admin(self.request.user)
