import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from inventory.models import (
    CarMake, CarModel, Category, Supplier, Product, Warehouse,
    AssemblyCategory, AssemblyDiagram, DiagramCallout, PartSubstitute
)

class Command(BaseCommand):
    help = "Seed realistic Partsouq/Amayama OEM parts catalog data, diagrams, VIN mappings, and substitutes for single shop"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Partsouq/Amayama Data Seeding..."))

        # 1. Warehouse & Supplier
        main_wh, _ = Warehouse.objects.get_or_create(
            name="Main Shop Warehouse",
            defaults={"location": "Zone A, Main Floor", "description": "Primary spare parts storage"}
        )
        supplier_oem, _ = Supplier.objects.get_or_create(
            name="Japan OEM Direct Parts Co.",
            defaults={"contact": "+81-3-5555-0199"}
        )
        supplier_aftermarket, _ = Supplier.objects.get_or_create(
            name="Euro-Asian Auto Spares Ltd",
            defaults={"contact": "+49-89-9876-5432"}
        )

        # 2. Inventory Categories
        cat_engine, _ = Category.objects.get_or_create(name="Engine Components")
        cat_brakes, _ = Category.objects.get_or_create(name="Brake System")
        cat_suspension, _ = Category.objects.get_or_create(name="Suspension & Steering")
        cat_filter, _ = Category.objects.get_or_create(name="Filters & Maintenance")

        # 3. Assembly Categories (Partsouq Groups)
        asm_cats_data = [
            ("Engine & Fuel System", "engine-fuel", "fa-cogs", "Cylinder head, oil pan, fuel injectors, timing belt"),
            ("Powertrain & Transmission", "transmission", "fa-sliders-h", "Gearbox, clutch, driveshaft, differential"),
            ("Axle & Suspension", "suspension", "fa-car-side", "Control arms, shock absorbers, wheel hubs, springs"),
            ("Brake System", "brakes", "fa-stop-circle", "Brake pads, rotors, calipers, brake lines, master cylinder"),
            ("Steering Linkage & Column", "steering", "fa-dharmachakra", "Steering rack, tie rod ends, power steering pump"),
            ("Electrical & Ignition", "electrical", "fa-bolt", "Alternator, starter motor, spark plugs, sensors, lights"),
            ("Body & Trim", "body", "fa-car", "Bumper, grille, headlights, doors, mirrors"),
            ("Heating & Air Conditioning", "heating-ac", "fa-snowflake", "AC compressor, radiator, blower motor, condenser"),
        ]

        asm_cat_objs = {}
        for name, slug, icon, desc in asm_cats_data:
            obj, _ = AssemblyCategory.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "icon": icon, "description": desc}
            )
            asm_cat_objs[slug] = obj

        # 4. Car Makes & Models with Chassis Prefixes (VIN Lookup)
        makes_data = [
            ("TOYOTA", [
                ("Land Cruiser Prado 150", 2009, 2023, "1GR-FE 4.0L V6", "GRJ150,KDJ150,TRJ150,JTEBU25J,VZN130"),
                ("Hilux Vigo / Revo", 2015, 2024, "1GD-FTV 2.8L Diesel", "GUN126,GUN135,KUN26,MRO"),
                ("Corolla Altis", 2014, 2022, "2ZR-FE 1.8L", "ZRE172,ZRE212,JT111"),
                ("Camry XV50/XV70", 2012, 2023, "2AR-FE 2.5L", "ASV50,AXVA70,4T1"),
            ]),
            ("NISSAN", [
                ("Patrol Y62", 2010, 2023, "VK56VD 5.6L V8", "Y62,TESY62,JN8"),
                ("Navara D23 / NP300", 2015, 2024, "YS23DDTT 2.3L TT", "D23,D40,MNK"),
            ]),
            ("HONDA", [
                ("CR-V Gen 5", 2017, 2023, "L15B7 1.5L Turbo", "RW1,RW2,5J6"),
                ("Civic FC/FK", 2016, 2021, "K20C2 2.0L / 1.5T", "FC1,FK7,1HG"),
            ]),
            ("MITSUBISHI", [
                ("Pajero Montero V90", 2006, 2021, "6G75 3.8L V6", "V93,V97,V98,JMB"),
            ]),
            ("HYUNDAI", [
                ("Tucson TL/NX4", 2016, 2024, "G4NA 2.0L / 1.6T", "TL,NX4,KMH"),
            ]),
            ("BMW", [
                ("3 Series G20", 2019, 2024, "B48 2.0L Turbo", "G20,G21,WBA"),
            ])
        ]

        car_models_dict = {}
        for make_name, models_list in makes_data:
            make_obj, _ = CarMake.objects.get_or_create(name=make_name)
            for m_name, y_from, y_to, engine, chassis in models_list:
                c_model, _ = CarModel.objects.get_or_create(
                    make=make_obj,
                    name=m_name,
                    year_from=y_from,
                    year_to=y_to,
                    defaults={"engine_type": engine, "chassis_prefixes": chassis}
                )
                car_models_dict[f"{make_name}_{m_name}"] = c_model

        prado = car_models_dict.get("TOYOTA_Land Cruiser Prado 150")
        hilux = car_models_dict.get("TOYOTA_Hilux Vigo / Revo")
        patrol = car_models_dict.get("NISSAN_Patrol Y62")

        # 5. Products (OEM & Genuine Spare Parts)
        products_data = [
            {
                "sku": "TY-90915-YZZD1",
                "part_number": "90915-YZZD1",
                "alternate_numbers": "90915-20003, 90915-03002, C-110",
                "name": "Engine Oil Filter Genuine Toyota V6/V8",
                "brand": "Toyota OEM",
                "manufacturer_brand": "Toyota Genuine Parts",
                "is_genuine": True,
                "category": cat_filter,
                "quantity": 45,
                "reorder_level": 10,
                "cost_price": 5.50,
                "selling_price": 12.00,
                "wholesale_price": 9.50,
                "shelf_bin": "Shelf A-01-B1",
                "location": "Aisle 1, Shelf A",
                "purpose": "ENGINE LUBRICATION OIL FILTER",
                "vehicle_application": "Toyota Land Cruiser Prado 150 4.0L, Hilux 2.7L, Fortuner, FJ Cruiser"
            },
            {
                "sku": "DN-150-1002",
                "part_number": "150-1002",
                "alternate_numbers": "90915-YZZD1-DN",
                "name": "Denso First Time Fit Oil Filter",
                "brand": "Denso Japan",
                "manufacturer_brand": "Denso",
                "is_genuine": False,
                "category": cat_filter,
                "quantity": 30,
                "reorder_level": 5,
                "cost_price": 3.80,
                "selling_price": 8.50,
                "wholesale_price": 6.50,
                "shelf_bin": "Shelf A-01-B2",
                "location": "Aisle 1, Shelf A",
                "purpose": "AFTERMARKET OIL FILTER",
                "vehicle_application": "Toyota Prado, Hilux, Fortuner, Tacoma"
            },
            {
                "sku": "TY-04465-35290",
                "part_number": "04465-35290",
                "alternate_numbers": "04465-60270, 04465-60320, D1303",
                "name": "Front Disc Brake Pads Set Genuine",
                "brand": "Toyota OEM",
                "manufacturer_brand": "Advics / Toyota OEM",
                "is_genuine": True,
                "category": cat_brakes,
                "quantity": 18,
                "reorder_level": 4,
                "cost_price": 42.00,
                "selling_price": 75.00,
                "wholesale_price": 62.00,
                "shelf_bin": "Shelf B-04-C1",
                "location": "Aisle 2, Shelf B",
                "purpose": "FRONT WHEEL BRAKE PADS",
                "vehicle_application": "Toyota Prado 150 2009-2023, Hilux Revo 4WD, 4Runner"
            },
            {
                "sku": "AK-AKD1303",
                "part_number": "AN-733WK",
                "alternate_numbers": "04465-35290-AK, D1303-AK",
                "name": "Akebono Ceramic Front Brake Pads",
                "brand": "Akebono Japan",
                "manufacturer_brand": "Akebono Brake Industry",
                "is_genuine": False,
                "category": cat_brakes,
                "quantity": 25,
                "reorder_level": 6,
                "cost_price": 28.00,
                "selling_price": 52.00,
                "wholesale_price": 42.00,
                "shelf_bin": "Shelf B-04-C2",
                "location": "Aisle 2, Shelf B",
                "purpose": "CERAMIC BRAKE PADS AFTERMARKET",
                "vehicle_application": "Toyota Prado 150, Hilux Revo 4WD"
            },
            {
                "sku": "TY-43512-60191",
                "part_number": "43512-60191",
                "alternate_numbers": "43512-60190, 09.A334.11",
                "name": "Front Vented Brake Rotor Disc",
                "brand": "Toyota OEM",
                "manufacturer_brand": "Toyota Genuine",
                "is_genuine": True,
                "category": cat_brakes,
                "quantity": 12,
                "reorder_level": 3,
                "cost_price": 55.00,
                "selling_price": 98.00,
                "wholesale_price": 80.00,
                "shelf_bin": "Floor Heavy B-01",
                "location": "Aisle 2, Heavy Bay B",
                "purpose": "FRONT BRAKE ROTOR DISC",
                "vehicle_application": "Toyota Prado 150 / 120, Lexus GX460"
            },
            {
                "sku": "KYB-349024",
                "part_number": "48530-69445",
                "alternate_numbers": "349024, 48530-60130",
                "name": "KYB Excel-G Rear Gas Shock Absorber",
                "brand": "KYB Japan",
                "manufacturer_brand": "KYB Corporation",
                "is_genuine": False,
                "category": cat_suspension,
                "quantity": 16,
                "reorder_level": 4,
                "cost_price": 38.00,
                "selling_price": 68.00,
                "wholesale_price": 54.00,
                "shelf_bin": "Shelf S-02-A",
                "location": "Suspension Bay S",
                "purpose": "REAR SUSPENSION SHOCK ABSORBER",
                "vehicle_application": "Toyota Land Cruiser Prado 150 / 120"
            },
            {
                "sku": "TY-90919-01191",
                "part_number": "90919-01191",
                "alternate_numbers": "SK20HR11, 3421",
                "name": "Denso Iridium Spark Plug Genuine",
                "brand": "Toyota OEM",
                "manufacturer_brand": "Denso Japan / Toyota OEM",
                "is_genuine": True,
                "category": cat_engine,
                "quantity": 60,
                "reorder_level": 12,
                "cost_price": 7.00,
                "selling_price": 14.50,
                "wholesale_price": 11.50,
                "shelf_bin": "Bin E-03",
                "location": "Small Parts Bin E",
                "purpose": "ENGINE IGNITION SPARK PLUG",
                "vehicle_application": "Toyota Prado 150 4.0L 1GR-FE, Camry 2.5L, Rav4"
            },
            {
                "sku": "TY-16100-39466",
                "part_number": "16100-39466",
                "alternate_numbers": "16100-39465, WPT-140",
                "name": "Engine Water Pump Assembly 1GR-FE",
                "brand": "AISIN / Toyota OEM",
                "manufacturer_brand": "AISIN Seiki",
                "is_genuine": True,
                "category": cat_engine,
                "quantity": 8,
                "reorder_level": 2,
                "cost_price": 68.00,
                "selling_price": 125.00,
                "wholesale_price": 105.00,
                "shelf_bin": "Shelf E-08",
                "location": "Engine Parts Rack",
                "purpose": "ENGINE COOLING WATER PUMP ASSEMBLY",
                "vehicle_application": "Toyota Land Cruiser Prado 150 1GR-FE 4.0L V6"
            },
            {
                "sku": "NS-16546-3HA0A",
                "part_number": "16546-3HA0A",
                "alternate_numbers": "16546-V0100, AF-902",
                "name": "Engine Air Filter Genuine Nissan Patrol Y62",
                "brand": "Nissan OEM",
                "manufacturer_brand": "Nissan Genuine",
                "is_genuine": True,
                "category": cat_filter,
                "quantity": 22,
                "reorder_level": 5,
                "cost_price": 14.00,
                "selling_price": 28.00,
                "wholesale_price": 22.00,
                "shelf_bin": "Shelf N-01-A",
                "location": "Nissan Bay N",
                "purpose": "AIR CLEANER FILTER ELEMENT",
                "vehicle_application": "Nissan Patrol Y62 VK56VD 5.6L V8"
            }
        ]

        created_products = {}
        for pdata in products_data:
            prod, _ = Product.objects.get_or_create(
                sku=pdata["sku"],
                defaults=pdata
            )
            created_products[prod.part_number] = prod

            # Add compatibilities
            if prado and "Prado" in pdata["vehicle_application"]:
                prod.compatibilities.add(prado)
            if hilux and "Hilux" in pdata["vehicle_application"]:
                prod.compatibilities.add(hilux)
            if patrol and "Patrol" in pdata["vehicle_application"]:
                prod.compatibilities.add(patrol)

        # 6. Part Substitutes (Cross references)
        prod_oem_filter = created_products.get("90915-YZZD1")
        prod_denso_filter = created_products.get("150-1002")
        if prod_oem_filter and prod_denso_filter:
            PartSubstitute.objects.get_or_create(
                original_product=prod_oem_filter,
                substitute_product=prod_denso_filter,
                defaults={"substitute_type": "OEM", "notes": "Denso Japanese Direct OEM supplier fitment"}
            )

        prod_oem_pads = created_products.get("04465-35290")
        prod_akebono_pads = created_products.get("AN-733WK")
        if prod_oem_pads and prod_akebono_pads:
            PartSubstitute.objects.get_or_create(
                original_product=prod_oem_pads,
                substitute_product=prod_akebono_pads,
                defaults={"substitute_type": "AFTERMARKET", "notes": "Premium Japanese Akebono Ceramic Pads"}
            )

        # 7. Assembly Diagrams (Exploded Schematics)
        if prado:
            # Diagram 1: Cylinder Block & Engine Lubrication
            diag_engine, _ = AssemblyDiagram.objects.get_or_create(
                car_model=prado,
                category=asm_cat_objs["engine-fuel"],
                diagram_code="11-01",
                defaults={
                    "title": "CYLINDER BLOCK & OIL PAN (1GR-FE)",
                    "description": "Exploded schematic diagram showing engine block, oil filter, water pump assembly, and gaskets."
                }
            )

            # Add callouts with coordinates
            callouts_engine = [
                ("1", "90915-YZZD1", "Engine Oil Filter Element", 38.5, 42.0, 10.0, 7.0, 1),
                ("2", "16100-39466", "Water Pump Assembly", 65.0, 30.0, 12.0, 8.0, 1),
                ("3", "90919-01191", "Spark Plug Set (Iridium)", 25.0, 22.0, 8.0, 6.0, 6),
                ("4", "11115-31050", "Cylinder Head Gasket Right", 48.0, 18.0, 14.0, 5.0, 1),
                ("5", "12101-31080", "Engine Oil Pan Sub-Assembly", 45.0, 78.0, 16.0, 9.0, 1),
            ]

            for c_num, p_num, p_name, x, y, w, h, qty in callouts_engine:
                prod = created_products.get(p_num)
                DiagramCallout.objects.get_or_create(
                    diagram=diag_engine,
                    callout_number=c_num,
                    defaults={
                        "product": prod,
                        "part_number": p_num,
                        "part_name": p_name,
                        "x_percent": x,
                        "y_percent": y,
                        "width_percent": w,
                        "height_percent": h,
                        "required_qty": qty
                    }
                )

            # Diagram 2: Front Axle & Brake Caliper
            diag_brakes, _ = AssemblyDiagram.objects.get_or_create(
                car_model=prado,
                category=asm_cat_objs["brakes"],
                diagram_code="47-01",
                defaults={
                    "title": "FRONT AXLE & BRAKE CALIPER / ROTOR",
                    "description": "Exploded schematic diagram for front disc brake caliper, pads kit, rotor disc, and hub assembly."
                }
            )

            callouts_brakes = [
                ("47730", "04465-35290", "Front Disc Brake Pad Kit (4 Pcs)", 30.0, 45.0, 14.0, 8.0, 1),
                ("43512", "43512-60191", "Front Vented Brake Rotor Disc", 62.0, 50.0, 15.0, 10.0, 2),
                ("48530", "48530-69445", "KYB Rear/Front Shock Absorber Assembly", 82.0, 28.0, 10.0, 14.0, 2),
            ]

            for c_num, p_num, p_name, x, y, w, h, qty in callouts_brakes:
                prod = created_products.get(p_num)
                DiagramCallout.objects.get_or_create(
                    diagram=diag_brakes,
                    callout_number=c_num,
                    defaults={
                        "product": prod,
                        "part_number": p_num,
                        "part_name": p_name,
                        "x_percent": x,
                        "y_percent": y,
                        "width_percent": w,
                        "height_percent": h,
                        "required_qty": qty
                    }
                )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Partsouq/Amayama catalog, VIN mappings, assembly schematics, callout coordinates, and OEM parts!"))
