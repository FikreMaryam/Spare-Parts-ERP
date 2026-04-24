from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Creates the default RBAC groups like "Sales" with basic configuration.'

    def handle(self, *args, **kwargs):
        # Create Sales group
        sales_group, created = Group.objects.get_or_create(name='Sales')
        if created:
            self.stdout.write(self.style.SUCCESS('Successfully created Sales group.'))
        else:
            self.stdout.write(self.style.WARNING('Sales group already exists.'))
        
        # In a fully fleshed out granular Django permission setup, we would append
        # specific Model permissions here (e.g., view_product, add_customer). 
        # However, our RBAC leverages custom decorators (@admin_required and @sales_or_admin_required)
        # which check group membership instead of granular Model permissions.
        # Thus, merely ensuring the Group exists is sufficient.
