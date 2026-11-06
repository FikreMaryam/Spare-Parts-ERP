from django.core.management.base import BaseCommand
from core.permissions import ensure_default_roles, ROLE_SEQUENCE

class Command(BaseCommand):
    help = 'Creates the default ERP roles needed for the access control model.'

    def handle(self, *args, **kwargs):
        created = ensure_default_roles()
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created ERP roles: {", ".join(created)}'))
        else:
            self.stdout.write(self.style.WARNING('ERP roles already exist.'))

        self.stdout.write(self.style.HTTP_INFO(f'Available roles: {", ".join(ROLE_SEQUENCE)}'))
