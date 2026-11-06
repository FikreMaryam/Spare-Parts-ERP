from getpass import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django_tenants.utils import tenant_context

from customers.models import Client, Domain


class Command(BaseCommand):
    help = "Create the first shop and its administrator for LAN or hosted deployment."

    def handle(self, *args, **options):
        is_render = bool(os.getenv("RENDER_EXTERNAL_HOSTNAME"))
        host = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("LAN_IP")
        if not host:
            raise CommandError("Set RENDER_EXTERNAL_HOSTNAME or LAN_IP before creating the shop.")

        if Client.objects.exclude(schema_name="public").exists():
            raise CommandError("A shop tenant already exists; refusing to create another.")

        shop_name = input("Shop name: ").strip()
        if not shop_name:
            raise CommandError("Shop name cannot be empty.")

        schema_name = slugify(
            input("Shop ID (letters, numbers, hyphens): ").strip()
        ).replace("-", "_")
        if not schema_name or schema_name == "public" or len(schema_name) > 63:
            raise CommandError("Choose a valid shop ID other than 'public' (maximum 63 characters).")

        username = input("Administrator username: ").strip()
        email = input("Administrator email: ").strip()
        password = getpass("Administrator password: ")
        password_confirmation = getpass("Confirm password: ")
        if password != password_confirmation:
            raise CommandError("The passwords did not match.")

        User = get_user_model()
        user = User(username=username, email=email)
        try:
            validate_password(password, user=user)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error

        tenant = Client(schema_name=schema_name, name=shop_name)
        tenant.save()
        Domain.objects.create(domain=host, tenant=tenant, is_primary=True)

        with tenant_context(tenant):
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Shop created. Open {'https' if is_render else 'http'}://{host}"
            f"{'' if is_render else ':8000'}/login/ and sign in as {username}."
        ))
