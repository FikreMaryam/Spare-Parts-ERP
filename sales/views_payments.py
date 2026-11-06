import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone

from .models import PaymentTransaction, Sale, Customer


def parse_payment_sms(raw_text: str):
    """
    Intelligent parser for Ethiopian mobile money and banking SMS notifications.
    Supports:
    - Telebirr (Ethio Telecom)
    - CBE Birr / CBE Mobile Banking
    - Awash Birr / Dashen Bank / Amole
    """
    text = (raw_text or "").strip()
    result = {
        "provider": "TELEBIRR",
        "reference": "",
        "amount": 0.0,
        "payer_phone": "",
        "payer_name": "",
        "raw_text": text,
    }
    if not text:
        return result

    upper_text = text.upper()

    # 1. Identify Provider
    if "TELEBIRR" in upper_text or "ETHIO TELECOM" in upper_text or re.search(r'\b(?:CK|CI)[0-9A-Z]{6,}', upper_text):
        result["provider"] = "TELEBIRR"
    elif "CBE BIRR" in upper_text or "CBEBIRR" in upper_text:
        result["provider"] = "CBE_BIRR"
    elif "COMMERCIAL BANK OF ETHIOPIA" in upper_text or "CBE" in upper_text or "FT" in upper_text:
        result["provider"] = "CBE_TRANSFER"
    elif "AWASH" in upper_text:
        result["provider"] = "AWASH_BIRR"
    elif "DASHEN" in upper_text or "AMOLE" in upper_text:
        result["provider"] = "DASHEN_AMOLE"
    else:
        result["provider"] = "BANK_OTHER"

    # 2. Extract Amount (ETB / Birr)
    # Examples: "received ETB 1,500.00", "credited with 450.00 ETB", "Amount: 2500 ETB"
    amount_match = re.search(r'(?:ETB|BIRR|AMOUNT|ብር)\s*[:.]?\s*([0-9,]+(?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
    if not amount_match:
        amount_match = re.search(r'([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:ETB|BIRR|ብር)', text, re.IGNORECASE)
    if amount_match:
        try:
            amt_str = amount_match.group(1).replace(',', '')
            result["amount"] = float(amt_str)
        except ValueError:
            result["amount"] = 0.0

    # 3. Extract Transaction Reference Code
    # Examples: "Transaction ID: CK79812456", "Ref No: FT2610214590", "Trans No. CI04..."
    ref_match = re.search(r'(?:TXN|TRANS(?:ACTION)?(?:\s*ID|\s*NO)?|REF(?:ERENCE)?(?:\s*NO)?)\s*[:.]?\s*([A-Z0-9]{6,25})', text, re.IGNORECASE)
    if ref_match:
        result["reference"] = ref_match.group(1).strip().upper()
    else:
        # Check standalone patterns like CK..., FT..., or 10-12 digit codes
        code_match = re.search(r'\b([A-Z]{1,3}[0-9]{6,16})\b', text)
        if code_match:
            result["reference"] = code_match.group(1).strip().upper()

    # 4. Extract Payer Phone Number
    # Examples: "from 0911234567", "from 251911234567"
    phone_match = re.search(r'(?:FROM|CUSTOMER|SENDER)?\s*(?:[+]?251|0)(9\d{8}|7\d{8})', text, re.IGNORECASE)
    if phone_match:
        result["payer_phone"] = "0" + phone_match.group(1)

    # 5. Extract Payer Name (if present e.g. "from ABEBE KEBEDE")
    name_match = re.search(r'FROM\s+([A-Z\s]{3,35})(?:\s+ON|\s+WITH|\s+TEL|\s+PHONE|\.|\,)', upper_text)
    if name_match:
        result["payer_name"] = name_match.group(1).strip()

    return result


@login_required
def payment_list(request):
    """
    Automated Mobile Money & Electronic Bank Payment Reconciliation Hub.
    Lists and reconciles Telebirr, CBE Birr, and Bank transfers against Sales Invoices.
    """
    payments = PaymentTransaction.objects.select_related("sale", "sale__customer", "verified_by")

    # Filters
    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        payments = payments.filter(status=status_filter)

    provider_filter = request.GET.get("provider", "").strip()
    if provider_filter:
        payments = payments.filter(provider=provider_filter)

    q = request.GET.get("q", "").strip()
    if q:
        payments = payments.filter(
            Q(transaction_reference__icontains=q)
            | Q(payer_phone__icontains=q)
            | Q(payer_name__icontains=q)
            | Q(sale__fs_number__icontains=q)
        )

    # Summary KPI Totals
    total_received = payments.filter(status__in=["VERIFIED", "RECONCILED"]).aggregate(s=Sum("amount"))["s"] or 0.0
    pending_reconciliation = payments.filter(status="VERIFIED", sale__isnull=True).count()
    reconciled_count = payments.filter(status="RECONCILED").count()

    paginator = Paginator(payments, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # Unmatched recent sales for quick 1-click reconciliation dropdown
    unmatched_sales = Sale.objects.filter(
        payment_method__in=["TELEBIRR", "CBE_BIRR", "TRANSFER"],
        payment_transactions__isnull=True
    ).order_by("-date")[:30]

    return render(request, "sales/payment_list.html", {
        "payments": page_obj,
        "page_obj": page_obj,
        "total_received": total_received,
        "pending_reconciliation": pending_reconciliation,
        "reconciled_count": reconciled_count,
        "status_filter": status_filter,
        "provider_filter": provider_filter,
        "unmatched_sales": unmatched_sales,
        "search_query": q,
    })


@login_required
def payment_record(request):
    """
    Manual record entry or auto-parser for incoming Telebirr, CBE, or bank payments.
    """
    if request.method == "POST":
        sms_text = request.POST.get("raw_sms", "").strip()
        
        # If user pasted SMS, run auto-parser
        if sms_text and not request.POST.get("reference"):
            parsed = parse_payment_sms(sms_text)
            provider = parsed["provider"]
            reference = parsed["reference"]
            amount = parsed["amount"]
            payer_phone = parsed["payer_phone"]
            payer_name = parsed["payer_name"]
        else:
            provider = request.POST.get("provider", "TELEBIRR")
            reference = request.POST.get("reference", "").strip().upper()
            try:
                amount = float(request.POST.get("amount", "0"))
            except ValueError:
                amount = 0.0
            payer_phone = request.POST.get("payer_phone", "").strip()
            payer_name = request.POST.get("payer_name", "").strip()

        sale_id = request.POST.get("sale_id", "").strip()
        matched_sale = None
        if sale_id.isdigit():
            matched_sale = Sale.objects.filter(id=int(sale_id)).first()

        if not reference:
            messages.error(request, "A valid Transaction Reference Number or SMS code is required.")
            return redirect("payment_list")

        # Anti-fraud check: Prevent duplicate transaction reference
        if PaymentTransaction.objects.filter(transaction_reference=reference).exists():
            messages.error(request, f"Transaction Ref '{reference}' is already recorded in the system! Duplicate payment rejected.")
            return redirect("payment_list")

        status = "RECONCILED" if matched_sale else "VERIFIED"
        payment = PaymentTransaction.objects.create(
            provider=provider,
            transaction_reference=reference,
            amount=amount,
            payer_phone=payer_phone,
            payer_name=payer_name,
            sale=matched_sale,
            status=status,
            verified_by=request.user,
            raw_sms_text=sms_text,
            notes=request.POST.get("notes", "").strip(),
        )

        if matched_sale:
            messages.success(request, f"✓ Payment of {amount:,.2f} ETB (Ref: {reference}) recorded and matched to Sale #{matched_sale.id} ({matched_sale.fs_number})!")
        else:
            messages.success(request, f"✓ Payment of {amount:,.2f} ETB (Ref: {reference}) recorded successfully! Ready for reconciliation.")

        return redirect("payment_list")

    return redirect("payment_list")


@login_required
def payment_reconcile(request, pk):
    """Match an unlinked payment transaction to an existing sale invoice."""
    payment = get_object_or_404(PaymentTransaction, pk=pk)
    if request.method == "POST":
        sale_id = request.POST.get("sale_id", "").strip()
        if sale_id.isdigit():
            sale = Sale.objects.filter(id=int(sale_id)).first()
            if sale:
                payment.sale = sale
                payment.status = "RECONCILED"
                payment.save()
                messages.success(request, f"✓ Transaction {payment.transaction_reference} successfully reconciled to Sale #{sale.id} ({sale.fs_number}).")
            else:
                messages.error(request, "Selected sale was not found.")
        else:
            messages.error(request, "Invalid sale ID provided.")
    return redirect("payment_list")


@login_required
def payment_verify_api(request):
    """
    Quick AJAX endpoint used during POS / Cart checkout to verify
    whether an entered transaction reference has already been used or recorded.
    """
    ref = (request.GET.get("ref") or request.POST.get("ref") or "").strip().upper()
    if not ref:
        return JsonResponse({"valid": False, "error": "Reference empty"})

    existing = PaymentTransaction.objects.filter(transaction_reference=ref).first()
    if existing:
        if existing.sale:
            return JsonResponse({
                "valid": False,
                "used": True,
                "error": f"Ref '{ref}' has already been used for Sale #{existing.sale.id} on {existing.received_at.strftime('%Y-%m-%d')}! Cannot reuse.",
            })
        else:
            return JsonResponse({
                "valid": True,
                "pre_recorded": True,
                "amount": existing.amount,
                "provider": existing.get_provider_display(),
                "payer_phone": existing.payer_phone,
                "message": f"Pre-recorded payment found: {existing.amount:,.2f} ETB via {existing.get_provider_display()}.",
            })

    return JsonResponse({
        "valid": True,
        "pre_recorded": False,
        "message": f"Transaction reference '{ref}' is valid and available for recording.",
    })
