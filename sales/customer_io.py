import csv
import io
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect

from .models import Customer


CUSTOMER_CSV_FIELDS = (
    "name",
    "company_name",
    "tin_number",
    "vat_number",
    "phone",
    "email",
    "address",
    "credit_limit",
)


def _spreadsheet_safe(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


@login_required
def customer_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="customers.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(CUSTOMER_CSV_FIELDS)
    for customer in Customer.objects.order_by("name", "id").iterator():
        writer.writerow([_spreadsheet_safe(getattr(customer, field)) for field in CUSTOMER_CSV_FIELDS])
    return response


@login_required
def customer_import(request):
    if request.method != "POST":
        return redirect("customer_list")

    upload = request.FILES.get("file")
    if not upload:
        messages.error(request, "Choose a CSV file to import.")
        return redirect("customer_list")
    if upload.size > 5 * 1024 * 1024:
        messages.error(request, "The customer CSV file must be 5 MB or smaller.")
        return redirect("customer_list")

    try:
        content = upload.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content, newline=""))
        if not reader.fieldnames:
            raise ValueError("The CSV file is empty or missing its header row.")
        headers = {
            " ".join((header or "").strip().casefold().replace("_", " ").split()): header
            for header in reader.fieldnames
        }
        name_header = headers.get("name") or headers.get("contact person / customer name")
        if not name_header:
            raise ValueError("The CSV must include a 'name' column.")

        created = 0
        skipped = 0
        errors = []
        for row_number, row in enumerate(reader, start=2):
            if row_number > 10002:
                errors.append("Import stopped after 10,000 rows.")
                break

            name = (row.get(name_header) or "").strip()
            if not name:
                if any(value for value in row.values() if value):
                    errors.append(f"Row {row_number}: name is required.")
                continue

            def field_value(field):
                header = headers.get(field.replace("_", " "))
                return (row.get(header) or "").strip() if header else ""

            company_name = field_value("company_name")
            tin_number = field_value("tin_number")
            vat_number = field_value("vat_number")
            phone = field_value("phone")
            email = field_value("email")
            address = field_value("address")
            raw_credit_limit = field_value("credit_limit")
            try:
                credit_limit = Decimal(raw_credit_limit or "0")
                if not credit_limit.is_finite() or credit_limit < 0:
                    raise InvalidOperation
            except InvalidOperation:
                errors.append(f"Row {row_number}: credit_limit must be a non-negative number.")
                continue

            duplicate = (
                Customer.objects.filter(tin_number__iexact=tin_number).exclude(tin_number="").exists()
                if tin_number else False
            )
            duplicate = duplicate or (
                Customer.objects.filter(email__iexact=email).exclude(email="").exists()
                if email else False
            )
            duplicate = duplicate or (
                Customer.objects.filter(name__iexact=name, phone__iexact=phone).exists()
                if phone else False
            )
            if duplicate:
                skipped += 1
                continue

            try:
                with transaction.atomic():
                    customer = Customer(
                        name=name[:100],
                        company_name=company_name[:150],
                        tin_number=tin_number[:50],
                        vat_number=vat_number[:50],
                        phone=phone[:50],
                        email=email[:254],
                        address=address,
                        credit_limit=credit_limit,
                    )
                    customer.full_clean()
                    customer.save()
                created += 1
            except (ValidationError, ValueError, InvalidOperation) as exc:
                errors.append(f"Row {row_number}: customer could not be saved ({exc}).")

    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        messages.error(request, f"Could not import customers: {exc}")
        return redirect("customer_list")

    messages.success(request, f"Imported {created} customer(s); skipped {skipped} duplicate(s).")
    if errors:
        messages.warning(request, "Import issues: " + " ".join(errors[:10]))
    return redirect("customer_list")
