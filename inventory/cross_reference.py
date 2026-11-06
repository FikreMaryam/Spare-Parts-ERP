import re
from typing import List, Dict, Any
from django.db.models import Q
from .models import Product, PartSubstitute


def parse_alternate_numbers(raw_str: str) -> List[str]:
    """Parse comma, semicolon, space, or slash-separated alternate OEM numbers."""
    if not raw_str:
        return []
    parts = re.split(r'[,;\s/|]+', raw_str)
    return [p.strip().upper() for p in parts if p.strip()]


def get_product_cross_references(product: Product) -> Dict[str, Any]:
    """
    Returns complete cross-reference information for a spare part:
    - Primary OEM number
    - Alternate / Superseded OEM part numbers
    - Interchangeable OEM & Aftermarket substitutes (Denso, Bosch, Aisin, etc.)
    - Compatible diagrams
    """
    alternates = parse_alternate_numbers(product.alternate_numbers)
    
    # Direct substitutes where this product is the original
    direct_subs = (
        PartSubstitute.objects.filter(original_product=product)
        .select_related("substitute_product", "substitute_product__category")
    )
    # Reverse substitutes where other products can substitute this one
    reverse_subs = (
        PartSubstitute.objects.filter(substitute_product=product)
        .select_related("original_product", "original_product__category")
    )

    substitute_list = []
    for s in direct_subs:
        substitute_list.append({
            "product": s.substitute_product,
            "substitute_type": s.get_substitute_type_display(),
            "type_code": s.substitute_type,
            "relationship": "Substitute for Original",
            "notes": s.notes,
        })
    for s in reverse_subs:
        if s.original_product not in [x["product"] for x in substitute_list]:
            substitute_list.append({
                "product": s.original_product,
                "substitute_type": s.get_substitute_type_display(),
                "type_code": s.substitute_type,
                "relationship": "Interchangeable Original",
                "notes": s.notes,
            })

    # Diagram callouts if available
    callouts = product.callouts.select_related("diagram", "diagram__car_model").all()

    return {
        "primary_oem": product.part_number,
        "is_genuine": product.is_genuine,
        "manufacturer": product.manufacturer_brand or product.brand,
        "alternate_numbers": alternates,
        "substitutes": substitute_list,
        "substitutes_count": len(substitute_list),
        "diagram_callouts": callouts,
    }


def find_parts_with_cross_reference(q: str, base_queryset=None):
    """
    Performs comprehensive spare parts search across OEM codes, alternate part numbers,
    and aftermarket substitutes. Returns products annotated with match metadata.
    """
    q_str = (q or "").strip()
    if not q_str:
        return base_queryset or Product.objects.all()

    clean_q = re.sub(r'[\s\-_/.]', '', q_str).upper()
    queryset = base_queryset if base_queryset is not None else Product.objects.all()

    # Search conditions
    cond = (
        Q(name__icontains=q_str)
        | Q(sku__icontains=q_str)
        | Q(part_number__icontains=q_str)
        | Q(brand__icontains=q_str)
        | Q(alternate_numbers__icontains=q_str)
        | Q(vehicle_application__icontains=q_str)
        | Q(purpose__icontains=q_str)
        | Q(compatibilities__name__icontains=q_str)
        | Q(compatibilities__make__name__icontains=q_str)
        | Q(compatibilities__chassis_prefixes__icontains=q_str)
        | Q(substitutes__substitute_product__part_number__icontains=q_str)
        | Q(substitute_for__original_product__part_number__icontains=q_str)
    )

    products = list(queryset.filter(cond).distinct())

    # Annotate matching reason for each product
    for p in products:
        p_clean_part = re.sub(r'[\s\-_/.]', '', p.part_number or "").upper()
        p_clean_sku = re.sub(r'[\s\-_/.]', '', p.sku or "").upper()
        p_alternates = [re.sub(r'[\s\-_/.]', '', alt).upper() for alt in parse_alternate_numbers(p.alternate_numbers)]

        if clean_q and (clean_q == p_clean_part or clean_q in p_clean_part):
            p.match_badge = "OEM Exact Match"
            p.is_cross_referenced = False
        elif clean_q and (clean_q == p_clean_sku or clean_q in p_clean_sku):
            p.match_badge = "SKU Match"
            p.is_cross_referenced = False
        elif any(clean_q == alt or clean_q in alt for alt in p_alternates):
            p.match_badge = f"🔄 Cross-Referenced (Alternate OEM #{q_str})"
            p.is_cross_referenced = True
            p.matched_oem_code = q_str
        elif any(clean_q in re.sub(r'[\s\-_/.]', '', cm.chassis_prefixes or '').upper() for cm in p.compatibilities.all()):
            p.match_badge = "🚗 Chassis / Frame Match"
            p.is_cross_referenced = False
        else:
            p.match_badge = None
            p.is_cross_referenced = False

    return products
