import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from inventory.models import (
    CarMake, CarModel, Category, Product, Warehouse,
    Supplier, PartSubstitute, StockMovement, Purchase, PurchaseItem,
    AssemblyCategory
)

@transaction.atomic
def seed_data():
    print("[*] Starting inventory seeding...")

    # 1. Warehouses
    print("[*] Creating warehouses...")
    wh_main, _ = Warehouse.objects.get_or_create(
        name="Main Central Warehouse",
        defaults={
            "location": "Aisle A-D, Building 1",
            "description": "Primary storage for fast-moving spare parts, filters, and brake components."
        }
    )
    wh_annex, _ = Warehouse.objects.get_or_create(
        name="Bulk Storage Annex",
        defaults={
            "location": "Warehouse Block B",
            "description": "Heavy suspension parts, body components, and drum oils."
        }
    )
    wh_shop, _ = Warehouse.objects.get_or_create(
        name="Retail Counter Racks",
        defaults={
            "location": "Front Counter Display Area",
            "description": "Immediate over-the-counter sales inventory."
        }
    )

    # 2. Suppliers
    print("[*] Creating suppliers...")
    sup_denso, _ = Supplier.objects.get_or_create(name="Denso Automotive Parts Distributor", defaults={"contact": "+1 (555) 234-5678 / sales@denso-dist.com"})
    sup_toyota, _ = Supplier.objects.get_or_create(name="Toyota Genuine OEM Supply", defaults={"contact": "+1 (555) 345-6789 / oem-orders@toyotaparts.net"})
    sup_bosch, _ = Supplier.objects.get_or_create(name="Bosch Auto Parts Regional Agency", defaults={"contact": "+1 (555) 456-7890 / support@bosch-supply.com"})
    sup_kyb, _ = Supplier.objects.get_or_create(name="KYB Suspension Industry Co.", defaults={"contact": "+1 (555) 567-8901 / orders@kyb-suspension.com"})
    sup_brembo, _ = Supplier.objects.get_or_create(name="Brembo Brake Systems Global", defaults={"contact": "+1 (555) 678-9012 / b2b@brembo-brakes.com"})
    sup_555, _ = Supplier.objects.get_or_create(name="Sankei 555 Steering & Suspension Japan", defaults={"contact": "+1 (555) 789-0123 / info@sankei555.jp"})
    sup_ngk, _ = Supplier.objects.get_or_create(name="NGK Spark Plug & Sensor Co.", defaults={"contact": "+1 (555) 890-1234 / trade@ngk-spark.com"})
    sup_aisin, _ = Supplier.objects.get_or_create(name="AISIN Seiki Drivetrain Products", defaults={"contact": "+1 (555) 901-2345 / contact@aisin-parts.com"})

    # 3. Categories
    print("[*] Creating categories...")
    categories_data = [
        "Braking System",
        "Filtration",
        "Suspension & Steering",
        "Engine & Mechanical",
        "Transmission & Drivetrain",
        "Electrical & Ignition",
        "Cooling & Heating",
        "Belts, Pulleys & Timing",
        "Fuel & Air Intake",
        "Exhaust & Emissions",
        "Body & Lighting",
        "Lubricants & Fluids",
    ]
    categories = {}
    for cat_name in categories_data:
        cat_obj, _ = Category.objects.get_or_create(name=cat_name)
        categories[cat_name] = cat_obj

    # Assembly categories (for diagrams if used)
    for ac_name, slug, icon in [
        ("Engine & Fuel System", "engine-fuel", "fa-cogs"),
        ("Power Train & Chassis", "powertrain-chassis", "fa-truck-monster"),
        ("Brake & Suspension", "brake-suspension", "fa-car-crash"),
        ("Electrical & Wiring", "electrical", "fa-bolt"),
    ]:
        AssemblyCategory.objects.get_or_create(slug=slug, defaults={"name": ac_name, "icon": icon})

    # 4. Car Makes & Models (Compatibilities)
    print("[*] Creating Car Makes and Car Models (compatibilities)...")
    makes_and_models = {
        "Toyota": [
            {
                "name": "Corolla",
                "year_from": 2007,
                "year_to": 2013,
                "engine_type": "1.8L 2ZR-FE / 1.6L 1ZR-FE",
                "chassis_prefixes": "ZRE151, ZRE152, NZE141, CE140"
            },
            {
                "name": "Corolla",
                "year_from": 2014,
                "year_to": 2019,
                "engine_type": "1.8L 2ZR-FAE / 1.6L 1ZR-FAE",
                "chassis_prefixes": "ZRE172, ZRE182, NRE180"
            },
            {
                "name": "Corolla",
                "year_from": 2020,
                "year_to": 2026,
                "engine_type": "1.8L Hybrid 2ZR-FXE / 2.0L M20A-FKS",
                "chassis_prefixes": "ZRE210, ZRE212, MZEA12, ZWE211"
            },
            {
                "name": "Hilux Vigo",
                "year_from": 2005,
                "year_to": 2015,
                "engine_type": "2.5L 2KD-FTV / 3.0L 1KD-FTV / 2.7L 2TR-FE",
                "chassis_prefixes": "KUN25, KUN26, KUN35, TGN26"
            },
            {
                "name": "Hilux Revo",
                "year_from": 2015,
                "year_to": 2025,
                "engine_type": "2.4L 2GD-FTV / 2.8L 1GD-FTV / 2.7L 2TR-FE",
                "chassis_prefixes": "GUN125, GUN126, GUN135, TGN126"
            },
            {
                "name": "Land Cruiser Prado 150",
                "year_from": 2009,
                "year_to": 2024,
                "engine_type": "2.8L 1GD-FTV / 3.0L 1KD-FTV / 4.0L 1GR-FE",
                "chassis_prefixes": "TRJ150, GRJ150, KDJ150, GDJ150"
            },
            {
                "name": "Land Cruiser 200",
                "year_from": 2007,
                "year_to": 2021,
                "engine_type": "4.5L V8 1VD-FTV / 4.7L V8 2UZ-FE / 5.7L 3UR-FE",
                "chassis_prefixes": "VDJ200, UZJ200, URJ200, URJ202"
            },
            {
                "name": "Land Cruiser 300",
                "year_from": 2021,
                "year_to": 2026,
                "engine_type": "3.3L Twin-Turbo Diesel F33A / 3.5L Twin-Turbo V35A",
                "chassis_prefixes": "FJA300, VJA300"
            },
            {
                "name": "RAV4",
                "year_from": 2013,
                "year_to": 2018,
                "engine_type": "2.0L 3ZR-FAE / 2.5L 2AR-FE",
                "chassis_prefixes": "ZSA44, ASA42, ASA44, ALA49"
            },
            {
                "name": "RAV4",
                "year_from": 2019,
                "year_to": 2025,
                "engine_type": "2.5L Hybrid A25A-FXS / 2.0L M20A-FKS",
                "chassis_prefixes": "AXAH52, AXAH54, MXAA52, MXAA54"
            },
            {
                "name": "Yaris / Vitz",
                "year_from": 2011,
                "year_to": 2020,
                "engine_type": "1.3L 1NR-FE / 1.5L 1NZ-FE",
                "chassis_prefixes": "NSP130, NCP131, KSP130, NHP130"
            },
            {
                "name": "Camry",
                "year_from": 2012,
                "year_to": 2017,
                "engine_type": "2.5L 2AR-FE / 3.5L 2GR-FE",
                "chassis_prefixes": "ASV50, AVV50, GSV50"
            },
            {
                "name": "Camry",
                "year_from": 2018,
                "year_to": 2025,
                "engine_type": "2.5L Dynamic Force A25A-FKS / 2.5L Hybrid",
                "chassis_prefixes": "ASV70, AXVH70, GSV70"
            },
        ],
        "Nissan": [
            {
                "name": "Patrol Y61",
                "year_from": 1997,
                "year_to": 2016,
                "engine_type": "3.0L Di ZD30 / 4.8L TB48DE",
                "chassis_prefixes": "Y61, ZD30, TB48"
            },
            {
                "name": "Patrol Y62",
                "year_from": 2010,
                "year_to": 2024,
                "engine_type": "4.0L V6 VQ40DE / 5.6L V8 VK56VD",
                "chassis_prefixes": "Y62, VQ40, VK56"
            },
            {
                "name": "Navara D40",
                "year_from": 2005,
                "year_to": 2015,
                "engine_type": "2.5L dCi YD25DDTi / 4.0L V6 VQ40DE",
                "chassis_prefixes": "D40, YD25, VCK40"
            },
            {
                "name": "Navara NP300 / D23",
                "year_from": 2015,
                "year_to": 2024,
                "engine_type": "2.3L dCi Twin-Turbo YS23DDTT / 2.5L QR25DE",
                "chassis_prefixes": "D23, YS23, QR25"
            },
            {
                "name": "X-Trail T31",
                "year_from": 2007,
                "year_to": 2013,
                "engine_type": "2.0L MR20DE / 2.5L QR25DE",
                "chassis_prefixes": "T31, NT31, TNT31"
            },
            {
                "name": "X-Trail T32",
                "year_from": 2014,
                "year_to": 2021,
                "engine_type": "2.0L MR20DD / 2.5L QR25DE / 1.6 dCi",
                "chassis_prefixes": "T32, NT32, HT32, HNT32"
            },
            {
                "name": "Sunny / Versa",
                "year_from": 2011,
                "year_to": 2020,
                "engine_type": "1.5L HR15DE",
                "chassis_prefixes": "N17, N17K, SC11"
            },
        ],
        "Hyundai": [
            {
                "name": "Tucson LM",
                "year_from": 2010,
                "year_to": 2015,
                "engine_type": "2.0L Theta II / 2.0L CRDi D4HA",
                "chassis_prefixes": "LM, EL, TM"
            },
            {
                "name": "Tucson TL",
                "year_from": 2016,
                "year_to": 2020,
                "engine_type": "2.0L Nu MPI / 1.6T GDI / 2.0L CRDi",
                "chassis_prefixes": "TL, TLE"
            },
            {
                "name": "Tucson NX4",
                "year_from": 2021,
                "year_to": 2026,
                "engine_type": "2.0L Smartstream / 1.6T Hybrid",
                "chassis_prefixes": "NX4, NX4A, NX4E"
            },
            {
                "name": "Santa Fe DM",
                "year_from": 2012,
                "year_to": 2018,
                "engine_type": "2.2L CRDi D4HB / 2.4L Theta II",
                "chassis_prefixes": "DM, NC"
            },
            {
                "name": "Santa Fe TM",
                "year_from": 2018,
                "year_to": 2024,
                "engine_type": "2.2L Smartstream D / 2.5L Smartstream G",
                "chassis_prefixes": "TM, TMA"
            },
            {
                "name": "Elantra MD",
                "year_from": 2011,
                "year_to": 2016,
                "engine_type": "1.6L Gamma / 1.8L Nu MPI",
                "chassis_prefixes": "MD, UD, JK"
            },
            {
                "name": "Elantra AD",
                "year_from": 2016,
                "year_to": 2020,
                "engine_type": "1.6L Gamma / 2.0L Nu MPI",
                "chassis_prefixes": "AD, ADA"
            },
            {
                "name": "Accent RB",
                "year_from": 2011,
                "year_to": 2017,
                "engine_type": "1.4L / 1.6L Gamma MPI",
                "chassis_prefixes": "RB, SB"
            },
            {
                "name": "Accent HC",
                "year_from": 2018,
                "year_to": 2023,
                "engine_type": "1.4L Kappa / 1.6L Gamma II",
                "chassis_prefixes": "HC, YC"
            },
        ],
        "Kia": [
            {
                "name": "Sportage SL",
                "year_from": 2010,
                "year_to": 2015,
                "engine_type": "2.0L Nu / 2.0L CRDi D4HA",
                "chassis_prefixes": "SL, SLS"
            },
            {
                "name": "Sportage QL",
                "year_from": 2016,
                "year_to": 2021,
                "engine_type": "2.0L Nu MPI / 1.6T GDI",
                "chassis_prefixes": "QL, QLE"
            },
            {
                "name": "Sorento UM",
                "year_from": 2015,
                "year_to": 2020,
                "engine_type": "2.2L CRDi D4HB / 3.3L V6 Lambda II",
                "chassis_prefixes": "UM, UMA"
            },
            {
                "name": "Cerato / Forte YD",
                "year_from": 2013,
                "year_to": 2018,
                "engine_type": "1.6L Gamma / 2.0L Nu MPI",
                "chassis_prefixes": "YD, YDA"
            },
        ],
        "Honda": [
            {
                "name": "Civic 9th Gen",
                "year_from": 2012,
                "year_to": 2015,
                "engine_type": "1.8L i-VTEC R18Z / 2.0L K20",
                "chassis_prefixes": "FB2, FG3, FB4"
            },
            {
                "name": "Civic 10th Gen",
                "year_from": 2016,
                "year_to": 2021,
                "engine_type": "1.5L VTEC Turbo L15B7 / 2.0L K20C2",
                "chassis_prefixes": "FC1, FC2, FK7"
            },
            {
                "name": "CR-V RM",
                "year_from": 2012,
                "year_to": 2016,
                "engine_type": "2.0L R20A / 2.4L K24Z",
                "chassis_prefixes": "RM1, RM3, RM4"
            },
            {
                "name": "CR-V RW",
                "year_from": 2017,
                "year_to": 2022,
                "engine_type": "1.5L VTEC Turbo L15BE / 2.0L Hybrid",
                "chassis_prefixes": "RW1, RW2, RT5, RT6"
            },
            {
                "name": "Accord CR",
                "year_from": 2013,
                "year_to": 2017,
                "engine_type": "2.4L Earth Dreams K24W / 3.5L V6",
                "chassis_prefixes": "CR2, CR3, CR6"
            },
        ],
        "Mitsubishi": [
            {
                "name": "L200 / Triton KB",
                "year_from": 2006,
                "year_to": 2015,
                "engine_type": "2.5L DI-D Common Rail 4D56",
                "chassis_prefixes": "KB4T, KB8T, KA4T"
            },
            {
                "name": "L200 / Triton KL",
                "year_from": 2015,
                "year_to": 2024,
                "engine_type": "2.4L MIVEC Clean Diesel 4N15",
                "chassis_prefixes": "KL1T, KL2T, KK1T"
            },
            {
                "name": "Pajero / Montero V90",
                "year_from": 2006,
                "year_to": 2021,
                "engine_type": "3.2L DI-D 4M41 / 3.8L V6 6G75 / 3.5L 6G74",
                "chassis_prefixes": "V98W, V97W, V93W, V88W"
            },
            {
                "name": "Outlander GF",
                "year_from": 2013,
                "year_to": 2021,
                "engine_type": "2.0L 4B11 / 2.4L 4B12 MIVEC",
                "chassis_prefixes": "GF7W, GF8W, GG2W"
            },
        ],
        "Isuzu": [
            {
                "name": "D-Max RT50",
                "year_from": 2012,
                "year_to": 2019,
                "engine_type": "3.0L Ddi iTEQ 4JJ1-TCX / 2.5L 4JK1-TCX",
                "chassis_prefixes": "RT50, RT85, TFS85, TFR85"
            },
            {
                "name": "D-Max RG01",
                "year_from": 2020,
                "year_to": 2026,
                "engine_type": "3.0L Ddi Blue Power 4JJ3-TCX / 1.9L RZ4E",
                "chassis_prefixes": "RG01, RG10, TFS40, TFR40"
            },
        ],
        "Ford": [
            {
                "name": "Ranger T6",
                "year_from": 2011,
                "year_to": 2022,
                "engine_type": "2.2L Duratorq TDCi / 3.2L 5-Cyl TDCi / 2.0L Bi-Turbo",
                "chassis_prefixes": "T6, PX, PX2, PX3"
            },
            {
                "name": "Everest U375",
                "year_from": 2015,
                "year_to": 2022,
                "engine_type": "2.2L TDCi / 3.2L TDCi / 2.0L Bi-Turbo Panther",
                "chassis_prefixes": "U375, UA, UA2"
            },
        ]
    }

    car_models_map = {}
    for make_name, models_list in makes_and_models.items():
        make_obj, _ = CarMake.objects.get_or_create(name=make_name)
        for m in models_list:
            cm_obj, _ = CarModel.objects.get_or_create(
                make=make_obj,
                name=m["name"],
                year_from=m["year_from"],
                year_to=m["year_to"],
                defaults={
                    "engine_type": m["engine_type"],
                    "chassis_prefixes": m["chassis_prefixes"]
                }
            )
            key = f"{make_name} {m['name']} ({m['year_from']}-{m['year_to']})"
            car_models_map[key] = cm_obj
            # also short key
            car_models_map[f"{make_name} {m['name']}"] = cm_obj

    print(f"[+] Created {len(car_models_map)} car model configurations across {len(makes_and_models)} manufacturers.")

    # 5. Products across all categories
    print("[*] Creating realistic spare parts products with car compatibilities...")

    products_spec = [
        # --- BRAKING SYSTEM ---
        {
            "sku": "BRK-PAD-TY-001",
            "part_number": "04465-02220",
            "name": "Front Ceramic Brake Pads Set",
            "brand": "Toyota OEM",
            "category": "Braking System",
            "quantity": 35,
            "reorder_level": 10,
            "cost_price": 28.50,
            "selling_price": 48.00,
            "wholesale_price": 38.00,
            "location": "Aisle A-01",
            "shelf_bin": "A-01-02",
            "purpose": "Front Axle Friction Disc Braking",
            "vehicle_application": "Toyota Corolla (2007-2019) 1.6L/1.8L [ZRE152, ZRE172]",
            "alternate_numbers": "04465-YZZE1, 04465-02240, D1210-8331, FDB1892",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Advics",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)"]
        },
        {
            "sku": "BRK-PAD-TY-002",
            "part_number": "P83082",
            "name": "Front Premium Low-Metallic Brake Pads Set",
            "brand": "Brembo",
            "category": "Braking System",
            "quantity": 25,
            "reorder_level": 8,
            "cost_price": 22.00,
            "selling_price": 36.50,
            "wholesale_price": 30.00,
            "location": "Aisle A-01",
            "shelf_bin": "A-01-03",
            "purpose": "High Performance Front Braking Pads",
            "vehicle_application": "Toyota Corolla (2007-2019) [ZRE152, ZRE172]",
            "alternate_numbers": "04465-02220, 04465-YZZE1, 04465-02240",
            "is_genuine": False,
            "manufacturer_brand": "Brembo Italy",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)"]
        },
        {
            "sku": "BRK-PAD-HLX-001",
            "part_number": "04465-0K280",
            "name": "Front Heavy-Duty Brake Pads Set",
            "brand": "Toyota OEM",
            "category": "Braking System",
            "quantity": 28,
            "reorder_level": 8,
            "cost_price": 42.00,
            "selling_price": 68.00,
            "wholesale_price": 55.00,
            "location": "Aisle A-01",
            "shelf_bin": "A-01-06",
            "purpose": "Front Caliper Friction Braking for Pickups/SUVs",
            "vehicle_application": "Toyota Hilux Revo (2015-2025), Hilux Vigo (2005-2015), Fortuner [GUN125, GUN126, KUN26]",
            "alternate_numbers": "04465-0K090, 04465-0K340, D1739-8964",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)"]
        },
        {
            "sku": "BRK-ROT-HLX-001",
            "part_number": "43512-0K060",
            "name": "Front Vented Brake Disc Rotor (Pair)",
            "brand": "Brembo",
            "category": "Braking System",
            "quantity": 14,
            "reorder_level": 4,
            "cost_price": 65.00,
            "selling_price": 105.00,
            "wholesale_price": 85.00,
            "location": "Aisle A-02",
            "shelf_bin": "A-02-01",
            "purpose": "Front Wheel Braking Rotor (297mm Vented)",
            "vehicle_application": "Toyota Hilux Vigo / Revo 4WD & Pre-Runner [KUN26, GUN126]",
            "alternate_numbers": "43512-0K070, 09.B828.11",
            "is_genuine": False,
            "manufacturer_brand": "Brembo",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)"]
        },
        {
            "sku": "BRK-PAD-HY-001",
            "part_number": "58101-D3A00",
            "name": "Front Brake Pads Set",
            "brand": "Bosch",
            "category": "Braking System",
            "quantity": 20,
            "reorder_level": 6,
            "cost_price": 24.00,
            "selling_price": 39.50,
            "wholesale_price": 32.00,
            "location": "Aisle A-01",
            "shelf_bin": "A-01-08",
            "purpose": "Front Axle Disc Friction Braking",
            "vehicle_application": "Hyundai Tucson TL (2016-2020), Kia Sportage QL (2016-2021)",
            "alternate_numbers": "58101-D7A00, 0986AB2425",
            "is_genuine": False,
            "manufacturer_brand": "Bosch Automotive",
            "compatible_models": ["Hyundai Tucson TL (2016-2020)", "Kia Sportage QL (2016-2021)"]
        },

        # --- FILTRATION ---
        {
            "sku": "FLT-OIL-TY-001",
            "part_number": "90915-YZZE1",
            "name": "Spin-On Engine Oil Filter",
            "brand": "Toyota OEM",
            "category": "Filtration",
            "quantity": 120,
            "reorder_level": 25,
            "cost_price": 3.80,
            "selling_price": 7.50,
            "wholesale_price": 5.50,
            "location": "Aisle B-01",
            "shelf_bin": "B-01-01",
            "purpose": "Engine Lubricant Filtration & Anti-Drainback",
            "vehicle_application": "Toyota Corolla (2007-2026), Yaris (2011-2020), RAV4 2.0L [ZRE152, ZRE172, NSP130]",
            "alternate_numbers": "90915-10003, 90915-YZZE2, W68/3, PH4967",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Denso",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota Corolla (2020-2026)", "Toyota Yaris / Vitz (2011-2020)"]
        },
        {
            "sku": "FLT-OIL-TY-002",
            "part_number": "04152-YZZA6",
            "name": "Cartridge Engine Oil Filter Element",
            "brand": "Toyota OEM",
            "category": "Filtration",
            "quantity": 90,
            "reorder_level": 20,
            "cost_price": 4.20,
            "selling_price": 8.50,
            "wholesale_price": 6.20,
            "location": "Aisle B-01",
            "shelf_bin": "B-01-02",
            "purpose": "Engine Oil Filtration with Replacement O-Rings",
            "vehicle_application": "Toyota Corolla 1.8L 2ZR-FE, RAV4 2.5L, Camry 2.5L [ZRE172, ASA42, ASV50]",
            "alternate_numbers": "04152-37010, HU6006z, CH10358ECO",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM",
            "compatible_models": ["Toyota Corolla (2014-2019)", "Toyota RAV4 (2013-2018)", "Toyota Camry (2012-2017)"]
        },
        {
            "sku": "FLT-OIL-DSL-001",
            "part_number": "90915-YZZD2",
            "name": "Diesel Heavy-Duty Oil Filter",
            "brand": "Toyota OEM",
            "category": "Filtration",
            "quantity": 75,
            "reorder_level": 15,
            "cost_price": 6.50,
            "selling_price": 12.00,
            "wholesale_price": 9.00,
            "location": "Aisle B-01",
            "shelf_bin": "B-01-05",
            "purpose": "Turbo Diesel Engine Oil Filtration",
            "vehicle_application": "Toyota Hilux Vigo, Revo, Land Cruiser Prado 150 1KD/2KD/1GD/2GD [KUN26, GUN126, GDJ150]",
            "alternate_numbers": "90915-20003, 90915-YZZD4, W719/45",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Denso",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)", "Toyota Land Cruiser Prado 150 (2009-2024)"]
        },
        {
            "sku": "FLT-AIR-TY-001",
            "part_number": "17801-21050",
            "name": "Engine Air Intake Filter",
            "brand": "Denso",
            "category": "Filtration",
            "quantity": 50,
            "reorder_level": 12,
            "cost_price": 6.00,
            "selling_price": 12.50,
            "wholesale_price": 9.50,
            "location": "Aisle B-02",
            "shelf_bin": "B-02-01",
            "purpose": "Combustion Air Dust & Particle Filter",
            "vehicle_application": "Toyota Corolla (2007-2019), Yaris (2011-2020) [ZRE152, ZRE172, NSP130]",
            "alternate_numbers": "17801-0D060, C24005, WA9584",
            "is_genuine": False,
            "manufacturer_brand": "Denso Japan",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota Yaris / Vitz (2011-2020)"]
        },
        {
            "sku": "FLT-FUEL-HLX-001",
            "part_number": "23390-0L070",
            "name": "Diesel Fuel Filter Element with Water Sensor Ring",
            "brand": "Toyota OEM",
            "category": "Filtration",
            "quantity": 60,
            "reorder_level": 15,
            "cost_price": 9.50,
            "selling_price": 18.00,
            "wholesale_price": 14.00,
            "location": "Aisle B-02",
            "shelf_bin": "B-02-04",
            "purpose": "Common-Rail Diesel Injector Protection & Moisture Separation",
            "vehicle_application": "Toyota Hilux Vigo / Revo, Fortuner, Prado 150 [KUN26, GUN126, KDJ150]",
            "alternate_numbers": "23390-0L041, 23390-YZZA1, KX457D",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)", "Toyota Land Cruiser Prado 150 (2009-2024)"]
        },
        {
            "sku": "FLT-CAB-UNV-001",
            "part_number": "87139-52040",
            "name": "Activated Carbon Cabin Air Filter",
            "brand": "Bosch",
            "category": "Filtration",
            "quantity": 40,
            "reorder_level": 10,
            "cost_price": 5.50,
            "selling_price": 11.50,
            "wholesale_price": 8.50,
            "location": "Aisle B-03",
            "shelf_bin": "B-03-02",
            "purpose": "A/C Interior Air Pollen & Odor Filtration",
            "vehicle_application": "Toyota Corolla, Camry, RAV4, Hilux, Land Cruiser [ZRE152, ASV50, GUN126, VDJ200]",
            "alternate_numbers": "87139-30040, 87139-02020, CUK1919, 0986AF5098",
            "is_genuine": False,
            "manufacturer_brand": "Bosch",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota Camry (2012-2017)", "Toyota Hilux Revo (2015-2025)", "Toyota Land Cruiser 200 (2007-2021)"]
        },

        # --- SUSPENSION & STEERING ---
        {
            "sku": "SUS-SHK-TY-001",
            "part_number": "339114",
            "name": "Front Right Excel-G Gas Shock Absorber",
            "brand": "KYB",
            "category": "Suspension & Steering",
            "quantity": 12,
            "reorder_level": 4,
            "cost_price": 54.00,
            "selling_price": 88.00,
            "wholesale_price": 72.00,
            "location": "Aisle C-01",
            "shelf_bin": "C-01-02",
            "purpose": "Front Right Suspension Damper Strut",
            "vehicle_application": "Toyota Corolla (2007-2013) 1.6L/1.8L [ZRE151, ZRE152]",
            "alternate_numbers": "48510-09L10, 48510-12A00, 339115 (LH)",
            "is_genuine": False,
            "manufacturer_brand": "KYB Japan",
            "compatible_models": ["Toyota Corolla (2007-2013)"]
        },
        {
            "sku": "SUS-SHK-TY-002",
            "part_number": "339115",
            "name": "Front Left Excel-G Gas Shock Absorber",
            "brand": "KYB",
            "category": "Suspension & Steering",
            "quantity": 12,
            "reorder_level": 4,
            "cost_price": 54.00,
            "selling_price": 88.00,
            "wholesale_price": 72.00,
            "location": "Aisle C-01",
            "shelf_bin": "C-01-03",
            "purpose": "Front Left Suspension Damper Strut",
            "vehicle_application": "Toyota Corolla (2007-2013) 1.6L/1.8L [ZRE151, ZRE152]",
            "alternate_numbers": "48520-09L10, 48520-12A00",
            "is_genuine": False,
            "manufacturer_brand": "KYB Japan",
            "compatible_models": ["Toyota Corolla (2007-2013)"]
        },
        {
            "sku": "SUS-SHK-HLX-001",
            "part_number": "48510-09W30",
            "name": "Front Coilover Shock Absorber Strut",
            "brand": "Toyota OEM",
            "category": "Suspension & Steering",
            "quantity": 10,
            "reorder_level": 2,
            "cost_price": 82.00,
            "selling_price": 135.00,
            "wholesale_price": 110.00,
            "location": "Aisle C-02",
            "shelf_bin": "C-02-01",
            "purpose": "Heavy Duty 4x4 Front Suspension Damper",
            "vehicle_application": "Toyota Hilux Revo (2015-2025) 4WD / PreRunner [GUN125, GUN126]",
            "alternate_numbers": "48510-0K260, 341398",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Tokico",
            "compatible_models": ["Toyota Hilux Revo (2015-2025)"]
        },
        {
            "sku": "STEER-LNK-TY-001",
            "part_number": "SL-3640",
            "name": "Front Stabilizer Sway Bar Link Rod (Pair)",
            "brand": "555 Sankei",
            "category": "Suspension & Steering",
            "quantity": 30,
            "reorder_level": 6,
            "cost_price": 14.50,
            "selling_price": 26.00,
            "wholesale_price": 20.00,
            "location": "Aisle C-03",
            "shelf_bin": "C-03-01",
            "purpose": "Anti-Roll Sway Bar to Strut Connection",
            "vehicle_application": "Toyota Corolla (2007-2019), RAV4 (2013-2018) [ZRE152, ZRE172, ACA33]",
            "alternate_numbers": "48820-47010, 48820-02070, CLTS-14",
            "is_genuine": False,
            "manufacturer_brand": "Sankei 555 Japan",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota RAV4 (2013-2018)"]
        },
        {
            "sku": "STEER-TIE-TY-001",
            "part_number": "SE-3641",
            "name": "Outer Steering Tie Rod End",
            "brand": "555 Sankei",
            "category": "Suspension & Steering",
            "quantity": 24,
            "reorder_level": 6,
            "cost_price": 12.00,
            "selling_price": 22.50,
            "wholesale_price": 17.00,
            "location": "Aisle C-03",
            "shelf_bin": "C-03-04",
            "purpose": "Steering Rack to Steering Knuckle Joint",
            "vehicle_application": "Toyota Corolla (2007-2019) [ZRE152, ZRE172]",
            "alternate_numbers": "45046-09251, 45046-19265, CET-117",
            "is_genuine": False,
            "manufacturer_brand": "Sankei 555 Japan",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)"]
        },
        {
            "sku": "STEER-BLJ-HLX-001",
            "part_number": "SB-3881",
            "name": "Lower Suspension Ball Joint",
            "brand": "555 Sankei",
            "category": "Suspension & Steering",
            "quantity": 20,
            "reorder_level": 6,
            "cost_price": 18.50,
            "selling_price": 34.00,
            "wholesale_price": 26.00,
            "location": "Aisle C-03",
            "shelf_bin": "C-03-08",
            "purpose": "Lower Control Arm Pivot Joint",
            "vehicle_application": "Toyota Hilux Vigo, Revo, Fortuner [KUN26, GUN126]",
            "alternate_numbers": "43330-09510, 43330-0K040, CBT-82",
            "is_genuine": False,
            "manufacturer_brand": "Sankei 555 Japan",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)"]
        },

        # --- ELECTRICAL & IGNITION ---
        {
            "sku": "IGN-SPK-IR-001",
            "part_number": "SC20HR11",
            "name": "Iridium Long-Life Spark Plug (Set of 4)",
            "brand": "Denso",
            "category": "Electrical & Ignition",
            "quantity": 60,
            "reorder_level": 15,
            "cost_price": 22.00,
            "selling_price": 42.00,
            "wholesale_price": 32.00,
            "location": "Aisle D-01",
            "shelf_bin": "D-01-01",
            "purpose": "High-Efficiency Ignition for Dual VVT-i Engines",
            "vehicle_application": "Toyota Corolla 1.8L 2ZR-FE, Yaris 1NZ-FE, Prius 2ZR-FXE [ZRE152, ZRE172, ZWE211]",
            "alternate_numbers": "90919-01253, 90919-01275, ILKAR7B11, 3444",
            "is_genuine": True,
            "manufacturer_brand": "Denso Iridium Japan",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota Corolla (2020-2026)", "Toyota Yaris / Vitz (2011-2020)"]
        },
        {
            "sku": "IGN-COIL-TY-001",
            "part_number": "90919-02258",
            "name": "Direct Engine Ignition Coil",
            "brand": "Denso",
            "category": "Electrical & Ignition",
            "quantity": 18,
            "reorder_level": 4,
            "cost_price": 32.00,
            "selling_price": 58.00,
            "wholesale_price": 45.00,
            "location": "Aisle D-01",
            "shelf_bin": "D-01-03",
            "purpose": "Individual Cylinder High Voltage Spark Generation",
            "vehicle_application": "Toyota Corolla (2007-2019) 1.8L 2ZR, RAV4 2.0L [ZRE152, ZRE172, ZSA44]",
            "alternate_numbers": "90919-02252, 099700-1160, GN10341",
            "is_genuine": True,
            "manufacturer_brand": "Denso OEM",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota RAV4 (2013-2018)"]
        },
        {
            "sku": "ELEC-ALT-HLX-001",
            "part_number": "27060-0L080",
            "name": "Heavy Duty 12V 100A Alternator",
            "brand": "Denso",
            "category": "Electrical & Ignition",
            "quantity": 6,
            "reorder_level": 2,
            "cost_price": 165.00,
            "selling_price": 260.00,
            "wholesale_price": 215.00,
            "location": "Aisle D-02",
            "shelf_bin": "D-02-01",
            "purpose": "Engine Electric Battery Charging & Power Supply",
            "vehicle_application": "Toyota Hilux Vigo 2.5D/3.0D, Fortuner [KUN25, KUN26]",
            "alternate_numbers": "104210-9010, DRA0615",
            "is_genuine": True,
            "manufacturer_brand": "Denso OEM",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)"]
        },
        {
            "sku": "ELEC-STR-HLX-001",
            "part_number": "28100-0L070",
            "name": "Diesel Starter Motor 12V 2.2kW",
            "brand": "Bosch",
            "category": "Electrical & Ignition",
            "quantity": 5,
            "reorder_level": 2,
            "cost_price": 140.00,
            "selling_price": 225.00,
            "wholesale_price": 185.00,
            "location": "Aisle D-02",
            "shelf_bin": "D-02-04",
            "purpose": "Engine Cranking High Torque Starter",
            "vehicle_application": "Toyota Hilux Vigo, Revo 1KD/2KD/1GD/2GD [KUN26, GUN126]",
            "alternate_numbers": "428000-0270, 0986022830",
            "is_genuine": False,
            "manufacturer_brand": "Bosch Automotive",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)"]
        },

        # --- COOLING & HEATING ---
        {
            "sku": "COOL-PMP-TY-001",
            "part_number": "16100-39466",
            "name": "Engine Water Pump with Gasket",
            "brand": "AISIN",
            "category": "Cooling & Heating",
            "quantity": 14,
            "reorder_level": 4,
            "cost_price": 38.00,
            "selling_price": 65.00,
            "wholesale_price": 52.00,
            "location": "Aisle E-01",
            "shelf_bin": "E-01-01",
            "purpose": "Coolant Circulation & Temperature Regulation",
            "vehicle_application": "Toyota Corolla 1.8L 2ZR-FE / 1.6L 1ZR [ZRE152, ZRE172]",
            "alternate_numbers": "WPT-140, 16100-39465, VKPC91845",
            "is_genuine": True,
            "manufacturer_brand": "AISIN Japan OEM",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)"]
        },
        {
            "sku": "COOL-RAD-HLX-001",
            "part_number": "16400-0L140",
            "name": "Aluminum Core Engine Radiator Assembly",
            "brand": "Denso",
            "category": "Cooling & Heating",
            "quantity": 8,
            "reorder_level": 2,
            "cost_price": 95.00,
            "selling_price": 160.00,
            "wholesale_price": 130.00,
            "location": "Aisle E-02",
            "shelf_bin": "E-02-02",
            "purpose": "Engine Coolant Heat Dissipation",
            "vehicle_application": "Toyota Hilux Vigo 2.5D / 3.0D Manual/Auto [KUN25, KUN26]",
            "alternate_numbers": "DRM50041, 16400-0C200",
            "is_genuine": False,
            "manufacturer_brand": "Denso Radiators",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)"]
        },
        {
            "sku": "COOL-THM-UNV-001",
            "part_number": "90916-03129",
            "name": "Engine Coolant Thermostat (82°C)",
            "brand": "Toyota OEM",
            "category": "Cooling & Heating",
            "quantity": 30,
            "reorder_level": 8,
            "cost_price": 11.50,
            "selling_price": 22.00,
            "wholesale_price": 16.50,
            "location": "Aisle E-01",
            "shelf_bin": "E-01-04",
            "purpose": "Engine Operating Temperature Regulator",
            "vehicle_application": "Toyota Corolla, Camry, RAV4, Hilux [ZRE152, ASV50, KUN26]",
            "alternate_numbers": "90916-03140, TH-25082G",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Tama",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota Camry (2012-2017)", "Toyota Hilux Vigo (2005-2015)"]
        },

        # --- TRANSMISSION & DRIVETRAIN ---
        {
            "sku": "TRN-CLT-HLX-001",
            "part_number": "KT-312",
            "name": "3-Piece Heavy-Duty Clutch Kit (Cover, Disc & Release Bearing)",
            "brand": "AISIN",
            "category": "Transmission & Drivetrain",
            "quantity": 8,
            "reorder_level": 2,
            "cost_price": 145.00,
            "selling_price": 235.00,
            "wholesale_price": 190.00,
            "location": "Aisle F-01",
            "shelf_bin": "F-01-01",
            "purpose": "Manual Transmission Clutch Coupling (260mm / 21 Spline)",
            "vehicle_application": "Toyota Hilux Vigo & Revo 2.5D / 2.4D / 3.0D [KUN25, KUN26, GUN125]",
            "alternate_numbers": "31210-0K070, 31250-0K204, 31230-71060, TYK2231",
            "is_genuine": True,
            "manufacturer_brand": "AISIN Japan OEM",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Hilux Revo (2015-2025)"]
        },
        {
            "sku": "TRN-CV-TY-001",
            "part_number": "43410-02580",
            "name": "Front Right Complete Drive CV Axle Shaft",
            "brand": "Toyota OEM",
            "category": "Transmission & Drivetrain",
            "quantity": 6,
            "reorder_level": 2,
            "cost_price": 88.00,
            "selling_price": 148.00,
            "wholesale_price": 120.00,
            "location": "Aisle F-02",
            "shelf_bin": "F-02-03",
            "purpose": "Front Wheel Power Delivery CV Joint & Axle",
            "vehicle_application": "Toyota Corolla (2007-2019) 1.6L/1.8L Automatic [ZRE152, ZRE172]",
            "alternate_numbers": "43410-02A40, TO-8-251",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)"]
        },

        # --- BELTS, PULLEYS & TIMING ---
        {
            "sku": "BLT-SRP-TY-001",
            "part_number": "6PK1230",
            "name": "EPDM V-Ribbed Serpentine Auxiliary Belt",
            "brand": "Bosch",
            "category": "Belts, Pulleys & Timing",
            "quantity": 40,
            "reorder_level": 10,
            "cost_price": 11.00,
            "selling_price": 21.00,
            "wholesale_price": 16.00,
            "location": "Aisle G-01",
            "shelf_bin": "G-01-02",
            "purpose": "Alternator & Water Pump Drive Belt",
            "vehicle_application": "Toyota Corolla (2007-2019) 1.8L 2ZR-FE [ZRE152, ZRE172]",
            "alternate_numbers": "90916-02685, 90916-02708, 6PK1228",
            "is_genuine": False,
            "manufacturer_brand": "Bosch",
            "compatible_models": ["Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)"]
        },
        {
            "sku": "BLT-TMG-HLX-001",
            "part_number": "13568-39016",
            "name": "Camshaft Timing Belt (97 Teeth)",
            "brand": "Toyota OEM",
            "category": "Belts, Pulleys & Timing",
            "quantity": 25,
            "reorder_level": 6,
            "cost_price": 26.00,
            "selling_price": 48.00,
            "wholesale_price": 38.00,
            "location": "Aisle G-01",
            "shelf_bin": "G-01-05",
            "purpose": "Engine Camshaft / Crankshaft Synchronization",
            "vehicle_application": "Toyota Hilux Vigo, Prado 150, Fortuner 1KD-FTV / 2KD-FTV [KUN26, KDJ150]",
            "alternate_numbers": "13568-39015, CT1080, 97YU25",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Mitsuboshi",
            "compatible_models": ["Toyota Hilux Vigo (2005-2015)", "Toyota Land Cruiser Prado 150 (2009-2024)"]
        },

        # --- NISSAN & HYUNDAI PARTS ---
        {
            "sku": "FLT-OIL-NIS-001",
            "part_number": "15208-65F0A",
            "name": "Engine Oil Filter",
            "brand": "Nissan OEM",
            "category": "Filtration",
            "quantity": 55,
            "reorder_level": 12,
            "cost_price": 4.00,
            "selling_price": 8.00,
            "wholesale_price": 6.00,
            "location": "Aisle B-01",
            "shelf_bin": "B-01-08",
            "purpose": "Engine Oil Cleanliness & Flow Regulator",
            "vehicle_application": "Nissan Sunny, X-Trail, Qashqai, Navara QR25/MR20 [N17, T31, T32, D23]",
            "alternate_numbers": "15208-9F60A, W67/1, PH6607",
            "is_genuine": True,
            "manufacturer_brand": "Nissan OEM",
            "compatible_models": ["Nissan Sunny / Versa (2011-2020)", "Nissan X-Trail T31 (2007-2013)", "Nissan X-Trail T32 (2014-2021)"]
        },
        {
            "sku": "BRK-PAD-NIS-001",
            "part_number": "D1060-4CA0A",
            "name": "Front Disc Brake Pads Set",
            "brand": "Brembo",
            "category": "Braking System",
            "quantity": 22,
            "reorder_level": 6,
            "cost_price": 26.00,
            "selling_price": 44.00,
            "wholesale_price": 35.00,
            "location": "Aisle A-01",
            "shelf_bin": "A-01-10",
            "purpose": "Front Wheel Stopping Power",
            "vehicle_application": "Nissan X-Trail T32 (2014-2021), Qashqai J11 [T32, NT32]",
            "alternate_numbers": "D1060-4BA0A, P56098",
            "is_genuine": False,
            "manufacturer_brand": "Brembo Italy",
            "compatible_models": ["Nissan X-Trail T32 (2014-2021)"]
        },
        {
            "sku": "FLT-OIL-HY-001",
            "part_number": "26300-35505",
            "name": "OEM Engine Oil Filter",
            "brand": "Hyundai OEM",
            "category": "Filtration",
            "quantity": 80,
            "reorder_level": 18,
            "cost_price": 3.90,
            "selling_price": 8.00,
            "wholesale_price": 5.80,
            "location": "Aisle B-01",
            "shelf_bin": "B-01-12",
            "purpose": "Engine Oil Contaminant Filtration",
            "vehicle_application": "Hyundai Elantra, Tucson, Accent, Kia Sportage, Cerato, Rio [MD, AD, TL, RB, QL, YD]",
            "alternate_numbers": "26300-35504, 26300-35503, W811/80",
            "is_genuine": True,
            "manufacturer_brand": "Hyundai Mobis OEM",
            "compatible_models": [
                "Hyundai Elantra MD (2011-2016)", "Hyundai Elantra AD (2016-2020)",
                "Hyundai Tucson TL (2016-2020)", "Hyundai Accent RB (2011-2017)",
                "Kia Sportage QL (2016-2021)", "Kia Cerato / Forte YD (2013-2018)"
            ]
        },
        {
            "sku": "BRK-PAD-HON-001",
            "part_number": "45022-TR0-A01",
            "name": "Front Disc Brake Pads Set",
            "brand": "Bosch",
            "category": "Braking System",
            "quantity": 18,
            "reorder_level": 5,
            "cost_price": 25.00,
            "selling_price": 42.00,
            "wholesale_price": 34.00,
            "location": "Aisle A-01",
            "shelf_bin": "A-01-14",
            "purpose": "Front Axle Low Dust Braking",
            "vehicle_application": "Honda Civic 9th / 10th Gen (2012-2021), CR-V [FB2, FC1, RM1]",
            "alternate_numbers": "45022-TR0-A02, 0986AB2082",
            "is_genuine": False,
            "manufacturer_brand": "Bosch",
            "compatible_models": ["Honda Civic 9th Gen (2012-2015)", "Honda Civic 10th Gen (2016-2021)", "Honda CR-V RM (2012-2016)"]
        },
        {
            "sku": "FLT-FUEL-MIT-001",
            "part_number": "1770A053",
            "name": "Diesel Fuel Filter Assembly",
            "brand": "Mitsubishi OEM",
            "category": "Filtration",
            "quantity": 30,
            "reorder_level": 8,
            "cost_price": 14.00,
            "selling_price": 26.00,
            "wholesale_price": 20.00,
            "location": "Aisle B-02",
            "shelf_bin": "B-02-08",
            "purpose": "Diesel Fuel System Particulate Filter",
            "vehicle_application": "Mitsubishi L200 / Triton 4D56 / 4N15, Pajero V98W [KB4T, KL1T, V98W]",
            "alternate_numbers": "1770A233, KC101/1",
            "is_genuine": True,
            "manufacturer_brand": "Mitsubishi Motors OEM",
            "compatible_models": ["Mitsubishi L200 / Triton KB (2006-2015)", "Mitsubishi L200 / Triton KL (2015-2024)", "Mitsubishi Pajero / Montero V90 (2006-2021)"]
        },
        {
            "sku": "LUB-ENG-5W30-001",
            "part_number": "08880-80845",
            "name": "Fully Synthetic Engine Oil 5W-30 SN/CF (4 Liters)",
            "brand": "Toyota OEM",
            "category": "Lubricants & Fluids",
            "quantity": 45,
            "reorder_level": 12,
            "cost_price": 24.00,
            "selling_price": 38.00,
            "wholesale_price": 31.00,
            "location": "Aisle H-01",
            "shelf_bin": "H-01-01",
            "purpose": "Full Synthetic Multi-Grade Engine Lubricant",
            "vehicle_application": "All Toyota Petrol & Light Diesel Models (Corolla, Camry, RAV4, Yaris, Hilux)",
            "alternate_numbers": "08880-83389, 08880-80375",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Idemitsu",
            "compatible_models": [
                "Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)", "Toyota Corolla (2020-2026)",
                "Toyota Camry (2012-2017)", "Toyota Camry (2018-2025)", "Toyota RAV4 (2013-2018)",
                "Toyota RAV4 (2019-2025)", "Toyota Yaris / Vitz (2011-2020)", "Toyota Hilux Revo (2015-2025)"
            ]
        },
        {
            "sku": "LUB-ATF-WS-001",
            "part_number": "08886-02305",
            "name": "Automatic Transmission Fluid ATF WS (4 Liters)",
            "brand": "Toyota OEM",
            "category": "Lubricants & Fluids",
            "quantity": 25,
            "reorder_level": 6,
            "cost_price": 32.00,
            "selling_price": 52.00,
            "wholesale_price": 42.00,
            "location": "Aisle H-01",
            "shelf_bin": "H-01-04",
            "purpose": "Low Viscosity Automatic Gearbox Fluid",
            "vehicle_application": "Toyota Automatic & Sequential Gearboxes (Corolla, Hilux, Land Cruiser, Camry)",
            "alternate_numbers": "08886-81210, JWS3324",
            "is_genuine": True,
            "manufacturer_brand": "Toyota OEM / Mobil",
            "compatible_models": [
                "Toyota Corolla (2007-2013)", "Toyota Corolla (2014-2019)",
                "Toyota Camry (2012-2017)", "Toyota Hilux Revo (2015-2025)",
                "Toyota Land Cruiser Prado 150 (2009-2024)", "Toyota Land Cruiser 200 (2007-2021)"
            ]
        }
    ]

    created_products = {}
    for p_data in products_spec:
        cat = categories.get(p_data["category"])
        compat_names = p_data.pop("compatible_models", [])

        prod, created = Product.objects.get_or_create(
            sku=p_data["sku"],
            defaults={
                "part_number": p_data["part_number"],
                "name": p_data["name"],
                "brand": p_data["brand"],
                "category": cat,
                "quantity": p_data["quantity"],
                "reorder_level": p_data["reorder_level"],
                "cost_price": p_data["cost_price"],
                "selling_price": p_data["selling_price"],
                "wholesale_price": p_data["wholesale_price"],
                "location": p_data["location"],
                "shelf_bin": p_data["shelf_bin"],
                "purpose": p_data["purpose"],
                "vehicle_application": p_data["vehicle_application"],
                "alternate_numbers": p_data["alternate_numbers"],
                "is_genuine": p_data["is_genuine"],
                "manufacturer_brand": p_data["manufacturer_brand"],
            }
        )
        created_products[p_data["sku"]] = prod

        # Link compatibilities
        for cm_name in compat_names:
            cm = car_models_map.get(cm_name)
            if cm:
                prod.compatibilities.add(cm)

        # Initial stock movement
        StockMovement.objects.create(
            product=prod,
            quantity=p_data["quantity"],
            movement_type="adjustment",
            reference="Initial Inventory Setup",
            warehouse=wh_main
        )

    print(f"[+] Successfully created and linked {len(created_products)} spare parts products.")

    # 6. Part Substitutes
    print("[*] Linking OEM and Aftermarket Part Substitutes...")
    # Genuine Corolla brake pads <-> Brembo aftermarket pads
    p_corolla_oem = created_products.get("BRK-PAD-TY-001")
    p_corolla_brembo = created_products.get("BRK-PAD-TY-002")
    if p_corolla_oem and p_corolla_brembo:
        PartSubstitute.objects.get_or_create(
            original_product=p_corolla_oem,
            substitute_product=p_corolla_brembo,
            defaults={
                "substitute_type": "AFTERMARKET",
                "notes": "Direct Brembo low-dust aftermarket replacement for 04465-02220"
            }
        )
        PartSubstitute.objects.get_or_create(
            original_product=p_corolla_brembo,
            substitute_product=p_corolla_oem,
            defaults={
                "substitute_type": "OEM",
                "notes": "Genuine Toyota OEM replacement for Brembo P83082"
            }
        )

    # 7. Sample Initial Purchase Record
    print("[*] Creating initial stock purchase record...")
    purchase = Purchase.objects.create(
        supplier=sup_toyota,
        warehouse=wh_main,
        invoice_number="INV-2026-TOY-001",
        notes="Initial stock intake: Toyota Genuine fast-moving filters, brake pads, and fluids.",
        total_amount=0.0
    )
    total_pur = 0.0
    for sku in ["BRK-PAD-TY-001", "FLT-OIL-TY-001", "FLT-OIL-DSL-001", "FLT-FUEL-HLX-001", "LUB-ENG-5W30-001"]:
        prod = created_products.get(sku)
        if prod:
            qty = 15
            unit_cost = prod.cost_price
            PurchaseItem.objects.create(
                purchase=purchase,
                product=prod,
                quantity=qty,
                unit_cost=unit_cost
            )
            total_pur += qty * unit_cost
    purchase.total_amount = total_pur
    purchase.save()

    print(f"[+] Initial purchase #{purchase.id} logged (${total_pur:.2f}).")
    print("[✔] Inventory seeding completed successfully!")

if __name__ == '__main__':
    seed_data()
