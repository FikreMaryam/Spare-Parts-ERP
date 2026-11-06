import re
from typing import Dict, Any, Optional
from django.utils.html import escape
from .models import Product, CarModel, CarMake, PartSubstitute


def normalize_code(code: str) -> str:
    """Strip whitespace, dashes, spaces, and uppercase code."""
    if not code:
        return ""
    return re.sub(r'[\s\-_/.]', '', str(code)).upper()


def decode_vin_or_chassis(raw_query: str) -> Dict[str, Any]:
    """
    Analyzes a 17-character VIN or Chassis/Frame number to extract potential
    chassis codes, manufacturer, and model hints.
    """
    clean = normalize_code(raw_query)
    info = {
        "raw": raw_query.strip(),
        "clean": clean,
        "is_17_char_vin": len(clean) == 17,
        "wmi": clean[:3] if len(clean) >= 3 else "",
        "vds": clean[3:8] if len(clean) >= 8 else "",
        "chassis_candidates": set(),
        "make_hint": None,
    }

    if not clean:
        return info

    # Always consider the full input and partial sub-strings as candidate codes
    info["chassis_candidates"].add(clean)

    # 17-char VIN heuristics
    if len(clean) == 17:
        # Common WMIs in Ethiopia
        wmi_map = {
            "JTD": "Toyota", "JTE": "Toyota", "JTM": "Toyota", "JT1": "Toyota",
            "AHT": "Toyota", "MR0": "Toyota", "MHF": "Toyota", "4T1": "Toyota",
            "5TD": "Toyota", "JN1": "Nissan", "JN6": "Nissan", "KMH": "Hyundai",
            "KNA": "Kia", "KND": "Kia", "WBA": "BMW", "WBS": "BMW",
            "WDB": "Mercedes-Benz", "WDD": "Mercedes-Benz", "VF1": "Renault",
            "VF3": "Peugeot", "SAL": "Land Rover", "SALL": "Land Rover",
            "WAU": "Audi", "WVW": "Volkswagen", "JM1": "Mazda",
            "MA3": "Suzuki", "TSM": "Suzuki", "LFV": "FAW", "LVS": "Chery"
        }
        for wmi, make_name in wmi_map.items():
            if clean.startswith(wmi):
                info["make_hint"] = make_name
                break

        # In Toyota/Japanese VINs, characters 4-8 (VDS) often encode body/chassis
        # e.g., JTDKN3DU... (Corolla), AHTER32G... (Hilux)
        vds = clean[3:8]
        info["chassis_candidates"].add(vds)
        # also 4-9
        info["chassis_candidates"].add(clean[3:9])
        # last 6 digits are serial/frame
        info["chassis_candidates"].add(clean[9:])

    # Frame numbers like NZE141-1029381 or KUN25-50123
    if "-" in raw_query:
        prefix_part = raw_query.split("-")[0].strip().upper()
        info["chassis_candidates"].add(prefix_part)

    return info


def verify_product_fitment(product: Product, vin_or_query: str = "", car_model_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Evaluates whether a spare part fits the specified vehicle VIN or selected model.
    Checks direct compatibilities, chassis prefixes, vehicle application notes,
    and available interchangeable part substitutes.
    """
    vin_or_query = (vin_or_query or "").strip()
    
    # Target CarModel if specified directly
    target_model = None
    if car_model_id:
        try:
            target_model = CarModel.objects.select_related("make").get(id=car_model_id)
        except CarModel.DoesNotExist:
            target_model = None

    compatibilities = list(product.compatibilities.select_related("make").all())

    # Case 1: Specific CarModel selected from dropdown
    if target_model:
        is_direct_match = any(cm.id == target_model.id for cm in compatibilities)
        if is_direct_match:
            return {
                "fits": True,
                "status": "EXACT_FIT",
                "badge_class": "badge-fit-exact",
                "badge_text": "✓ EXACT FIT GUARANTEED / ተስማሚ ዕቃ ነው",
                "matched_vehicle": f"{target_model.make.name} {target_model.name} ({target_model.year_from or ''}–{target_model.year_to or 'Present'})",
                "detail": f"Directly engineered for {target_model}.",
                "icon": "✓",
            }

        # Check vehicle application text fallback
        if target_model.name.lower() in product.vehicle_application.lower() or (
            target_model.make.name.lower() in product.vehicle_application.lower()
        ):
            return {
                "fits": True,
                "status": "APPLICATION_MATCH",
                "badge_class": "badge-fit-exact",
                "badge_text": "✓ VERIFIED FIT / ተስማሚ ነው",
                "matched_vehicle": f"{target_model.make.name} {target_model.name}",
                "detail": f"Matched via vehicle application catalog: '{product.vehicle_application}'.",
                "icon": "✓",
            }

        # Check if an available substitute part fits this model
        for sub in product.substitutes.select_related("substitute_product").all():
            sub_prod = sub.substitute_product
            if sub_prod.compatibilities.filter(id=target_model.id).exists():
                return {
                    "fits": True,
                    "status": "SUBSTITUTE_FIT",
                    "badge_class": "badge-fit-substitute",
                    "badge_text": f"🔄 SUBSTITUTE AVAILABLE / ተለዋጭ ዕቃ አለው ({sub.get_substitute_type_display()})",
                    "matched_vehicle": f"{target_model.make.name} {target_model.name}",
                    "detail": f"Interchangeable with part #{sub_prod.part_number} ({sub_prod.name}).",
                    "substitute_part_id": sub_prod.id,
                    "substitute_part_number": sub_prod.part_number,
                    "icon": "🔄",
                }

        return {
            "fits": False,
            "status": "NO_FIT",
            "badge_class": "badge-fit-none",
            "badge_text": "⚠️ DOES NOT FIT / ለዚህ መኪና አይመጥንም",
            "matched_vehicle": f"{target_model.make.name} {target_model.name}",
            "detail": f"This part is not registered as compatible with {target_model}.",
            "icon": "⚠️",
        }

    # Case 2: VIN or Chassis string entered
    if vin_or_query:
        vin_info = decode_vin_or_chassis(vin_or_query)
        clean_vin = vin_info["clean"]
        candidates = vin_info["chassis_candidates"]

        # 1. Check direct chassis prefixes on compatible models
        for cm in compatibilities:
            # Check model's chassis prefixes (e.g. "KUN25, KUN26")
            prefixes = [p.strip().upper() for p in (cm.chassis_prefixes or "").split(",") if p.strip()]
            for pref in prefixes:
                clean_pref = normalize_code(pref)
                if not clean_pref:
                    continue
                # Match if prefix in candidates or clean_vin starts with/contains prefix
                if (
                    clean_pref in clean_vin
                    or clean_vin.startswith(clean_pref)
                    or any(clean_pref in c for c in candidates)
                ):
                    return {
                        "fits": True,
                        "status": "EXACT_FIT",
                        "badge_class": "badge-fit-exact",
                        "badge_text": "✓ EXACT FIT GUARANTEED / ተስማሚ ዕቃ ነው",
                        "matched_vehicle": f"{cm.make.name} {cm.name} ({cm.year_from or ''}–{cm.year_to or 'Present'})",
                        "detail": f"Verified by chassis code: '{pref}' from VIN/Frame: {escape(vin_or_query)}.",
                        "matched_model_id": cm.id,
                        "icon": "✓",
                    }

        # 2. Check model name / make match if user typed model name (e.g. "Hilux" or "Corolla")
        query_upper = vin_or_query.upper()
        for cm in compatibilities:
            if cm.name.upper() in query_upper or query_upper in cm.name.upper():
                return {
                    "fits": True,
                    "status": "EXACT_FIT",
                    "badge_class": "badge-fit-exact",
                    "badge_text": "✓ VERIFIED FIT / ተስማሚ ነው",
                    "matched_vehicle": f"{cm.make.name} {cm.name}",
                    "detail": f"Model '{cm.name}' matches query criteria.",
                    "matched_model_id": cm.id,
                    "icon": "✓",
                }

        # 3. Check vehicle application text
        app_text = (product.vehicle_application or "").upper()
        if app_text and (query_upper in app_text or any(c in app_text for c in candidates if len(c) >= 4)):
            return {
                "fits": True,
                "status": "APPLICATION_MATCH",
                "badge_class": "badge-fit-exact",
                "badge_text": "✓ COMPATIBLE BY APPLICATION / ተስማሚ ዕቃ",
                "matched_vehicle": product.vehicle_application,
                "detail": f"Matched vehicle application record: {product.vehicle_application}.",
                "icon": "✓",
            }

        # 4. Check if any substitute fits
        for sub in product.substitutes.select_related("substitute_product").all():
            sub_res = verify_product_fitment(sub.substitute_product, vin_or_query=vin_or_query)
            if sub_res.get("fits"):
                return {
                    "fits": True,
                    "status": "SUBSTITUTE_FIT",
                    "badge_class": "badge-fit-substitute",
                    "badge_text": f"🔄 INTERCHANGEABLE SUBSTITUTE / ተለዋጭ ዕቃ አለው",
                    "matched_vehicle": sub_res.get("matched_vehicle"),
                    "detail": f"Original #{product.part_number} has verified substitute #{sub.substitute_product.part_number} ({sub.substitute_product.name}).",
                    "substitute_part_id": sub.substitute_product.id,
                    "substitute_part_number": sub.substitute_product.part_number,
                    "icon": "🔄",
                }

        return {
            "fits": False,
            "status": "NO_FIT",
            "badge_class": "badge-fit-none",
            "badge_text": "⚠️ UNVERIFIED / ለዚህ ቪን ቁጥር አልተረጋገጠም",
            "matched_vehicle": vin_or_query,
            "detail": f"No compatibility record found for VIN/Chassis '{escape(vin_or_query)}' with this part.",
            "icon": "⚠️",
        }

    # No VIN or model specified
    return {
        "fits": None,
        "status": "UNCHECKED",
        "badge_class": "badge-fit-neutral",
        "badge_text": "🔍 Verify Fitment with VIN or Car Model",
        "matched_vehicle": "",
        "detail": "Enter VIN, chassis number, or select vehicle model to verify compatibility.",
        "icon": "🚗",
    }
