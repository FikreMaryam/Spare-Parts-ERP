import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from inventory.models import CarMake, CarModel

more_cars = {
    "Lexus": [
        ("IS 200/300 XE10", 1999, 2005, "2.0L 1G-FE / 3.0L 2JZ-GE", "GXE10, JCE10"),
        ("IS 250/350 XE20", 2005, 2013, "2.5L 4GR-FSE / 3.5L 2GR-FSE V6", "GSE20, GSE21"),
        ("IS 250/300/350 XE30", 2013, 2024, "2.0L Turbo 8AR-FTS / 3.5L 2GR-FKS", "ASE30, GSE31"),
        ("ES 300/330 XV30", 2001, 2006, "3.0L 1MZ-FE / 3.3L 3MZ-FE V6", "MCV30, MCV31"),
        ("ES 350 XV40", 2006, 2012, "3.5L 2GR-FE V6", "GSV40"),
        ("ES 350/300h XV60", 2012, 2018, "3.5L 2GR-FE / 2.5L Hybrid 2AR-FXE", "GSV60, AVV60"),
        ("ES 350/300h XZ10", 2018, 2026, "3.5L 2GR-FKS / 2.5L Hybrid A25A-FXS", "GSZ10, AXZH10"),
        ("GS 300/430 S160", 1998, 2005, "3.0L 2JZ-GE / 4.3L V8 3UZ-FE", "JZS160, UZS161"),
        ("GS 300/350/460 S190", 2005, 2011, "3.0L 3GR-FSE / 3.5L 2GR / 4.6L 1UR-FSE", "GRS190, GRS191, URS190"),
        ("GS 250/350 L10", 2012, 2020, "2.5L 4GR-FSE / 3.5L 2GR-FKS V6", "GRL10, GRL11"),
        ("LS 400 XF10/XF20", 1990, 2000, "4.0L V8 1UZ-FE", "UCF10, UCF20"),
        ("LS 430 XF30", 2000, 2006, "4.3L V8 3UZ-FE", "UCF30"),
        ("LS 460 XF40", 2006, 2017, "4.6L V8 1UR-FSE / 1UR-FE", "USF40, USF41"),
        ("LS 500 XF50", 2017, 2026, "3.5L V6 Twin-Turbo V35A-FTS / 3.5L Hybrid", "VXFA50, GVF50"),
        ("RX 300 XU10", 1998, 2003, "3.0L V6 1MZ-FE", "MCU10, MCU15"),
        ("RX 300/330/350 XU30", 2003, 2008, "3.0L 1MZ / 3.3L 3MZ / 3.5L 2GR-FE", "MCU35, GSU35"),
        ("RX 350/450h AL10", 2009, 2015, "3.5L 2GR-FE / 3.5L Hybrid 2GR-FXE", "GGL15, GYL15"),
        ("RX 350/450h AL20", 2015, 2022, "3.5L 2GR-FKS / 3.5L Hybrid 2GR-FXS", "GGL25, GYL25"),
        ("RX 350/500h ALA10", 2022, 2026, "2.4L Turbo T24A-FTS / 2.5L Hybrid", "TALA10, TALH17"),
        ("GX 470 J120", 2002, 2009, "4.7L V8 2UZ-FE", "UZJ120"),
        ("GX 460 J150", 2009, 2023, "4.6L V8 1UR-FE", "URJ150"),
        ("GX 550 J250", 2024, 2026, "3.4L Twin-Turbo V6 V35A-FTS", "VJA250"),
        ("LX 470 J100", 1998, 2007, "4.7L V8 2UZ-FE", "UZJ100"),
        ("LX 570 J200", 2007, 2021, "5.7L V8 3UR-FE", "URJ201"),
        ("LX 600 / LX 500d J300", 2021, 2026, "3.5L Twin-Turbo V35A / 3.3L Diesel F33A", "VJA310, FJA310"),
        ("NX 200t / NX 300 AZ10", 2014, 2021, "2.0L Turbo 8AR-FTS / 2.5L Hybrid 2AR", "AGZ10, AYZ10"),
        ("NX 250 / NX 350 AZ20", 2021, 2026, "2.5L A25A / 2.4L Turbo T24A", "AAZA20, TAZA25"),
        ("UX 200 / 250h ZA10", 2018, 2026, "2.0L Dynamic Force M20A-FKS / Hybrid", "MZAA10, MZAH10"),
    ],
    "Volvo": [
        ("S60 Gen 1", 2000, 2009, "2.0T, 2.4, 2.5T, D5 2.4D 5-Cylinder", "P24"),
        ("S60 Gen 2", 2010, 2018, "T4 1.6T, T5 2.0T, T6 3.0T, D3, D4, D5", "Y20"),
        ("S60 Gen 3", 2018, 2026, "T5, T6, T8 Recharge 2.0L Drive-E B4, B5", "SPA"),
        ("S80 Gen 1", 1998, 2006, "2.4, 2.9, 2.5T, D5 2.4D", "TS"),
        ("S80 Gen 2", 2006, 2016, "2.5T, 3.2 i6, 4.4L V8, D5 2.4D", "AS"),
        ("S90 Gen 2", 2016, 2026, "T5, T6, B5, D4, D5 Drive-E 2.0L", "SPA"),
        ("XC60 Gen 1", 2008, 2017, "2.0T, 3.0T T6, 3.2, D4, D5 2.4D", "DZ"),
        ("XC60 Gen 2", 2017, 2026, "T5, T6, B5, B6, T8 Recharge, D4, D5", "UZ"),
        ("XC90 Gen 1", 2002, 2014, "2.5T B5254T, 3.2 i6, 4.4L V8 B8444S, D5 2.4D", "275"),
        ("XC90 Gen 2", 2015, 2026, "T6 2.0L Supercharged/Turbo, T8 Recharge, B5, B6", "256"),
        ("XC40", 2017, 2026, "T3 1.5T 3-Cyl, T4, T5 2.0T, B4, B5, D3, D4", "XZ"),
        ("V40 / V40 Cross Country", 2012, 2019, "T2, T3, T4, T5, D2, D3, D4", "525, 526"),
    ],
    "GMC": [
        ("Sierra 1500 GMT800", 1999, 2006, "4.8L, 5.3L, 6.0L Vortec V8", "GMT800"),
        ("Sierra 1500 GMT900", 2007, 2013, "4.8L, 5.3L, 6.2L Vortec V8", "GMT900"),
        ("Sierra 1500 K2XX", 2014, 2018, "4.3L V6 / 5.3L / 6.2L EcoTec3 V8", "K2XX"),
        ("Sierra 1500 T1XX", 2019, 2026, "2.7L Turbo / 5.3L / 6.2L / 3.0L Duramax", "T1XX"),
        ("Sierra 2500/3500 HD", 2011, 2019, "6.0L Vortec / 6.6L Duramax Diesel LML/L5P", "GMT900HD, K2HD"),
        ("Yukon / Yukon XL GMT800", 2000, 2006, "4.8L, 5.3L, 6.0L Vortec V8", "GMT800"),
        ("Yukon / Yukon XL GMT900", 2007, 2014, "5.3L, 6.2L Vortec V8", "GMT900"),
        ("Yukon / Yukon XL K2XX", 2015, 2020, "5.3L, 6.2L EcoTec3 V8", "K2XX"),
        ("Yukon / Yukon XL T1XX", 2021, 2026, "5.3L, 6.2L / 3.0L Duramax Turbo-Diesel", "T1XX"),
        ("Acadia Gen 1", 2007, 2016, "3.6L High Feature V6 LLT/LFX", "GMT968"),
        ("Acadia Gen 2", 2017, 2023, "2.5L LCV / 2.0L Turbo / 3.6L V6 LGX", "C1XX"),
        ("Terrain Gen 1", 2010, 2017, "2.4L Ecotec / 3.0L, 3.6L V6", "Theta"),
        ("Terrain Gen 2", 2018, 2024, "1.5L Turbo / 2.0L Turbo / 1.6L Diesel", "D2XX"),
        ("Savana Van", 2003, 2024, "4.8L, 5.3L, 6.0L Vortec / 6.6L Duramax", "GMT610"),
    ],
    "Dodge": [
        ("RAM 1500 Gen 3", 2002, 2008, "3.7L PowerTech, 4.7L V8, 5.7L HEMI V8", "DR, DH"),
        ("RAM 1500 Gen 4 / Classic", 2009, 2024, "3.6L Pentastar, 4.7L, 5.7L HEMI, 3.0L EcoDiesel", "DS"),
        ("RAM 1500 Gen 5 DT", 2019, 2026, "3.6L eTorque / 5.7L HEMI eTorque / 3.0L EcoDiesel", "DT"),
        ("RAM 2500/3500 HD", 2010, 2024, "5.7L, 6.4L HEMI / 6.7L Cummins Turbo Diesel", "DJ, D2"),
        ("Charger LX", 2006, 2010, "2.7L, 3.5L V6, 5.7L HEMI V8, 6.1L SRT8", "LX"),
        ("Charger LD", 2011, 2023, "3.6L Pentastar, 5.7L HEMI, 6.4L 392, 6.2L Hellcat", "LD"),
        ("Challenger LC/LA", 2008, 2023, "3.6L Pentastar, 5.7L HEMI, 6.4L SRT, 6.2L Hellcat", "LC, LA"),
        ("Durango HB", 2004, 2009, "3.7L, 4.7L, 5.7L HEMI V8", "HB"),
        ("Durango WD", 2011, 2024, "3.6L Pentastar / 5.7L HEMI / 6.4L SRT", "WD"),
        ("Journey JC", 2008, 2020, "2.4L World Gas / 2.7L, 3.5L, 3.6L Pentastar V6", "JC"),
    ],
    "Fiat": [
        ("500 / 500C", 2007, 2024, "0.9L TwinAir, 1.2L FIRE, 1.4L 16V, 1.3L MultiJet", "312"),
        ("500X", 2014, 2024, "1.4L MultiAir, 1.3L FireFly, 1.6L / 2.0L MultiJet", "334"),
        ("Punto / Grande Punto / Evo", 2005, 2018, "1.2L, 1.4L FIRE, 1.4L T-Jet, 1.3L MultiJet", "199"),
        ("Tipo / Egea", 2015, 2024, "1.4L FIRE, 1.0L FireFly, 1.3L / 1.6L MultiJet", "356"),
        ("Doblo Gen 1", 2000, 2010, "1.2L, 1.6L Petrol / 1.3L, 1.9L JTD/MultiJet", "223"),
        ("Doblo Gen 2", 2010, 2022, "1.4L Petrol / 1.3L, 1.6L, 2.0L MultiJet Diesel", "263"),
        ("Ducato Van 244", 2002, 2006, "2.0L, 2.3L, 2.8L JTD Diesel", "244"),
        ("Ducato Van 250/290", 2006, 2026, "2.0L, 2.2L, 2.3L, 3.0L MultiJet Turbo Diesel", "250, 290"),
        ("Fiorino / Qubo", 2007, 2024, "1.4L Fire / 1.3L MultiJet Diesel", "225"),
    ],
    "Daihatsu": [
        ("Terios / Taruna J100", 1997, 2005, "1.3L HC-EJ, K3-VE", "J100, J102"),
        ("Terios J200", 2006, 2017, "1.5L 3SZ-VE", "J200, J210"),
        ("Terios / Rush F800", 2017, 2026, "1.5L 2NR-VE Dual VVT-i", "F800"),
        ("Sirion / Boon M300", 2004, 2011, "1.0L 1KR-FE / 1.3L K3-VE", "M300, M301"),
        ("Sirion M600", 2011, 2018, "1.3L 1NR-VE", "M600"),
        ("Gran Max Van / Pickup", 2007, 2026, "1.3L K3-DE / 1.5L 3SZ-VE / 2NR-VE", "S400, S401, S402"),
        ("Hijet Truck / Van S200/S500", 1999, 2026, "0.66L EF-SE, KF-VE", "S200, S500"),
        ("Delta Truck V-Series", 1995, 2006, "3.0L 14B / 3.7L 11B Diesel", "V116, V118"),
        ("Rocky / Taft A200", 2019, 2026, "1.0L Turbo 1KR-VET / 1.2L WA-VE", "A200S, A201S"),
    ],
    "Infiniti": [
        ("G35 / G37 / Q40 V35/V36", 2003, 2015, "3.5L VQ35DE / 3.7L VQ37VHR V6", "V35, V36, CV36"),
        ("Q50 V37", 2013, 2024, "2.0L Turbo M274 / 3.7L VQ37 / 3.0L Twin-Turbo VR30", "V37"),
        ("QX50 / EX35 J50", 2007, 2017, "3.5L VQ35HR / 3.7L VQ37VHR", "J50"),
        ("QX50 QX55 J55", 2018, 2024, "2.0L VC-Turbo KR20DDET", "J55"),
        ("QX56 / QX80 JA60", 2004, 2010, "5.6L V8 VK56DE", "JA60"),
        ("QX80 Z62", 2010, 2024, "5.6L V8 VK56VD", "Z62"),
        ("QX60 / JX35 L50", 2012, 2020, "3.5L V6 VQ35DE, VQ35DD", "L50"),
        ("FX35 / FX50 / QX70 S51", 2008, 2017, "3.5L VQ35HR, 3.7L VQ37 / 5.0L V8 VK50VE", "S51"),
    ],
    "Acura": [
        ("MDX YD1", 2001, 2006, "3.5L V6 J35A", "YD1"),
        ("MDX YD2", 2007, 2013, "3.7L V6 J37A", "YD2"),
        ("MDX YD3", 2014, 2020, "3.5L V6 J35Y", "YD3"),
        ("MDX YD4", 2021, 2026, "3.5L V6 J35Y / 3.0L Turbo V6", "YD4"),
        ("RDX TB1", 2006, 2012, "2.3L Turbo K23A1", "TB1"),
        ("RDX TB3", 2013, 2018, "3.5L V6 J35Z", "TB3"),
        ("RDX TC1", 2018, 2024, "2.0L Turbo VTEC K20C4", "TC1"),
        ("TL UA6/UA7", 2004, 2008, "3.2L J32A / 3.5L J35A V6", "UA6, UA7"),
        ("TL UA8/UA9", 2009, 2014, "3.5L J35Z / 3.7L J37A V6", "UA8, UA9"),
        ("TSX CL9/CU2", 2004, 2014, "2.4L i-VTEC K24A2, K24Z3", "CL9, CU2"),
    ],
    "Geely": [
        ("Emgrand 7 / EC7", 2009, 2021, "1.5L JLY-4G15 / 1.8L JLY-4G18", "EC7, FE-1"),
        ("Emgrand 4th Gen", 2021, 2026, "1.5L JLC-4G15B", "SS11"),
        ("Coolray / Binyue SX11", 2018, 2026, "1.5L Turbo 3-Cyl JLH-3G15TD / 1.5L 4-Cyl", "SX11"),
        ("Tugella / Xingyue FY11", 2019, 2026, "2.0L Turbo Drive-E JLH-4G20TD", "FY11"),
        ("Monjaro / Xingyue L KX11", 2021, 2026, "2.0L Turbo Drive-E / 1.5L Hybrid", "KX11"),
        ("Azkarra / Boyue NL-3", 2016, 2024, "1.8L Turbo JLE-4G18TD / 1.5L Mild Hybrid", "NL-3"),
        ("Okavango / Haoyue VX11", 2020, 2026, "1.5L Turbo Mild Hybrid / 2.0L Turbo", "VX11"),
        ("GX3 Pro", 2017, 2026, "1.5L JLC-4G15", "V4"),
    ],
    "Chery": [
        ("Tiggo 2 / 2 Pro", 2016, 2026, "1.5L Acteco SQRD4G15B / 1.0L Turbo", "T13"),
        ("Tiggo 4 / 4 Pro", 2017, 2026, "1.5L Acteco / 1.5L Turbo SQRE4T15C", "T17"),
        ("Tiggo 7 / 7 Pro", 2016, 2026, "1.5L Turbo / 1.6L TGDI SQRF4J16", "T1E"),
        ("Tiggo 8 / 8 Pro / Max", 2018, 2026, "1.6L TGDI SQRF4J16 / 2.0L TGDI SQRF4J20", "T1D"),
        ("Arrizo 5 / 5 Plus", 2016, 2026, "1.5L SQRE4G15B / 1.5L Turbo", "M1A"),
        ("Arrizo 6 / Pro", 2018, 2026, "1.5L Turbo SQRE4T15C", "M1DF"),
        ("Arrizo 8", 2022, 2026, "1.6L TGDI / 2.0L TGDI", "M1E"),
    ],
    "Haval": [
        ("Haval H6 Gen 1", 2011, 2017, "1.5L Turbo GW4G15B / 2.0L Turbo GW4C20 / 2.0D", "H6-1"),
        ("Haval H6 Gen 2", 2017, 2021, "1.5L GDIT GW4B15 / 2.0L GDIT GW4C20B", "H6-2"),
        ("Haval H6 Gen 3", 2020, 2026, "1.5L GDIT / 2.0L GDIT GW4N20 / 1.5T Hybrid", "H6-3"),
        ("Haval Jolion", 2020, 2026, "1.5L Turbo GW4G15K / 1.5L Hybrid", "Jolion"),
        ("Haval H9 Gen 1", 2014, 2023, "2.0L Turbo GW4C20 / 2.0L Bi-Turbo Diesel", "H9-1"),
        ("GWM Poer / P-Series Pickup", 2019, 2026, "2.0L Turbo GW4C20B / 2.0L Diesel GW4D20M", "P01"),
        ("GWM Steed / Wingle 5/7", 2010, 2024, "2.0L Diesel GW4D20 / 2.4L 4G69 Petrol", "W5, W7"),
        ("Tank 300", 2020, 2026, "2.0L Turbo E20CB / 2.0L Hybrid", "P03"),
        ("Tank 500", 2021, 2026, "3.0L Twin-Turbo V6 E30Z / 2.0L Hybrid", "P05"),
    ],
    "MG": [
        ("MG ZS / ZS EV", 2017, 2026, "1.5L NSE Plus / 1.3L Turbo / EV", "ZS11"),
        ("MG HS", 2018, 2024, "1.5L Mega Tech Turbo / 2.0L Turbo", "AS23"),
        ("MG RX5", 2018, 2024, "1.5L Turbo / 2.0L Turbo", "RX5"),
        ("MG 5", 2019, 2026, "1.5L SAIC 15S4C", "AP12"),
        ("MG 6 Gen 2", 2017, 2024, "1.5L Turbo Mega Tech 15E4E", "IP32"),
        ("MG GT", 2021, 2026, "1.5L / 1.5L Turbo Mega Tech", "GT2"),
        ("MG T60 / Extender Pickup", 2017, 2024, "2.0L Turbo Diesel SAIC SC20M / 2.8L", "T60"),
    ],
    "BYD": [
        ("Song Plus DM-i / EV", 2020, 2026, "1.5L Xiaoyun Hybrid / EV", "SongPlus"),
        ("Tang DM / EV", 2018, 2026, "2.0T / 1.5T DM-p / Dual Motor EV", "Tang"),
        ("Han DM / EV", 2020, 2026, "1.5T DM-i / 380kW Dual Motor EV", "Han"),
        ("Qin Plus DM-i / EV", 2021, 2026, "1.5L High Efficiency Hybrid / Blade EV", "QinPlus"),
        ("Atto 3 / Yuan Plus", 2022, 2026, "Permanent Magnet Sync Motor 150kW", "YuanPlus"),
        ("Dolphin", 2021, 2026, "70kW / 130kW e-Platform 3.0", "Dolphin"),
        ("Seal", 2022, 2026, "Rear & All Wheel Drive CTB EV", "Seal"),
    ],
    "Toyota": [
        ("Starlet EP91", 1996, 1999, "1.3L 4E-FE", "EP91"),
        ("Echo / Platz XP10", 1999, 2005, "1.3L 2NZ-FE / 1.5L 1NZ-FE", "NCP10, NCP12"),
        ("Belta XP90", 2005, 2012, "1.3L 2SZ-FE / 1.5L 1NZ-FE", "SCP92, NCP96"),
        ("Passo M700", 2016, 2023, "1.0L 1KR-FE", "M700A"),
        ("Voxy / Noah R70", 2007, 2014, "2.0L Valvematic 3ZR-FAE", "ZRR70, ZRR75"),
        ("Voxy / Noah R80", 2014, 2021, "2.0L 3ZR-FAE / 1.8L Hybrid 2ZR-FXE", "ZRR80, ZWR80"),
        ("Voxy / Noah R90", 2022, 2026, "2.0L Dynamic Force M20A-FKS / 1.8L Hybrid", "MZRA90, ZWR90"),
        ("Alphard / Vellfire AH20", 2008, 2015, "2.4L 2AZ-FE / 3.5L 2GR-FE V6", "ANH20, GGH20"),
        ("Alphard / Vellfire AH30", 2015, 2023, "2.5L 2AR-FE / 3.5L 2GR-FKS V6", "AGH30, GGH30"),
        ("Alphard / Vellfire AH40", 2023, 2026, "2.5L Dynamic Force A25A / 2.4L Turbo", "AAHH40, TAHA40"),
        ("Sienta XP170", 2015, 2022, "1.5L 2NR-FKE / 1.5L Hybrid 1NZ-FXE", "NSP170, NHP170"),
        ("Harrier XU30", 2003, 2013, "2.4L 2AZ / 3.0L 1MZ / 3.5L 2GR", "ACU30, MCU30, GSU30"),
        ("Harrier XU60", 2013, 2020, "2.0L 3ZR-FAE / 2.0L Turbo 8AR-FTS / 2.5L Hybrid", "ZSU60, ASU60, AVU65"),
        ("Harrier XU80", 2020, 2026, "2.0L M20A-FKS / 2.5L Hybrid A25A", "MXUA80, AXUH80"),
        ("Mark X GRX120", 2004, 2009, "2.5L 4GR-FSE / 3.0L 3GR-FSE V6", "GRX120, GRX121"),
        ("Mark X GRX130", 2009, 2019, "2.5L 4GR-FSE / 3.5L 2GR-FSE V6", "GRX130, GRX133"),
        ("Corona Premio T210", 1996, 2001, "1.6L 4A-FE / 1.8L 7A-FE / 2.0L 3S-FE / 2.0D", "AT210, AT211, ST210, CT210"),
        ("Carina E / T190", 1992, 1997, "1.6L 4A-FE / 2.0L 3S-FE / 2.0L 2C Diesel", "AT190, ST191, CT190"),
        ("Crown S180 (Zero Crown)", 2003, 2008, "2.5L 4GR / 3.0L 3GR / 3.5L 2GR V6", "GRS180, GRS182"),
        ("Crown S200", 2008, 2012, "2.5L 4GR / 3.5L 2GR / 4.6L V8 1UR-FSE", "GRS200, GRS204, URS206"),
        ("Crown S210", 2012, 2018, "2.5L 4GR / 2.0L Turbo 8AR / 2.5L Hybrid 2AR", "GRS210, ARS210, AWS210"),
    ],
    "Nissan": [
        ("Serena C25", 2005, 2010, "2.0L MR20DE", "C25, CC25"),
        ("Serena C26", 2010, 2016, "2.0L MR20DD S-HYBRID", "C26, FC26"),
        ("Serena C27", 2016, 2022, "2.0L MR20DD / 1.2L e-POWER HR12DE", "C27, GC27, HFC27"),
        ("Serena C28", 2022, 2026, "2.0L MR20DD / 1.4L e-POWER HR14DDe", "C28, FC28"),
        ("Terra D23 SUV", 2018, 2026, "2.5L QR25DE / 2.3L Twin-Turbo YS23DDTT", "D23B"),
        ("AD Van / Wingroad Y11", 1999, 2008, "1.5L QG15DE / 1.8L QG18DE / 2.2L YD22", "VY11, WFY11"),
        ("AD Van / NV150 Y12", 2006, 2024, "1.2L CR12DE / 1.5L HR15DE / 1.6L HR16DE", "VY12, VZNY12"),
        ("Cefiro A32", 1994, 1998, "2.0L, 2.5L, 3.0L V6 VQ20, VQ25, VQ30", "A32"),
        ("Cefiro A33", 1998, 2004, "2.0L, 2.5L, 3.0L V6 VQ20DE, VQ25DD, VQ30DE", "A33"),
        ("Sylphy G11", 2005, 2012, "1.5L HR15DE / 2.0L MR20DE", "G11, KG11"),
        ("Sylphy B17", 2012, 2019, "1.6L HR16DE / 1.8L MRA8DE", "B17"),
        ("Sylphy B18", 2019, 2026, "1.6L HR16DE / 1.2L e-POWER", "B18"),
        ("Bluebird U14", 1996, 2001, "1.8L QG18DE / 2.0L SR20DE", "QU14, HU14"),
        ("Dualis J10", 2007, 2014, "2.0L MR20DE", "J10, KJ10"),
    ],
    "Hyundai": [
        ("Matrix FC", 2001, 2010, "1.6L Alpha G4ED / 1.8L Beta / 1.5L CRDi D3EA", "FC"),
        ("Atos / Amica MX", 1997, 2008, "1.0L G4HC / 1.1L G4HG Epsilon", "MX"),
        ("Getz TB", 2002, 2011, "1.1L G4HD / 1.3L, 1.4L G4EE / 1.6L G4ED / 1.5D", "TB"),
        ("i10 PA", 2007, 2013, "1.1L Epsilon G4HG / 1.2L Kappa G4LA", "PA"),
        ("i10 IA/BA", 2013, 2019, "1.0L Kappa / 1.2L Kappa II G4LA", "IA, BA"),
        ("i10 AC3", 2019, 2026, "1.0L MPi / 1.2L MPi G4LF", "AC3"),
        ("i20 PB", 2008, 2014, "1.2L Kappa G4LA / 1.4L Gamma G4FA / 1.4L CRDi", "PB"),
        ("i20 GB/IB", 2014, 2020, "1.2L Kappa / 1.4L Gamma / 1.0L T-GDI", "GB, IB"),
        ("i20 BC3", 2020, 2026, "1.2L MPi / 1.0L T-GDI Smartstream", "BC3"),
        ("i30 FD", 2007, 2012, "1.4L, 1.6L Gamma / 2.0L Beta / 1.6L CRDi D4FB", "FD"),
        ("i30 GD", 2012, 2017, "1.4L, 1.6L Gamma GDI / 1.6L CRDi D4FB", "GD"),
        ("i30 PD", 2017, 2024, "1.0T, 1.4T T-GDI / 1.5L / 1.6L Smartstream D", "PD"),
        ("Terracan HP", 2001, 2007, "2.9L CRDi J3 / 2.5L D4BH / 3.5L V6 Sigma", "HP"),
        ("Trajet FO", 1999, 2008, "2.0L Beta / 2.7L V6 Delta / 2.0L CRDi D4EA", "FO"),
        ("Galloper II", 1997, 2003, "2.5L Turbo Diesel D4BH / 3.0L V6 G6AT", "JK"),
    ],
    "Kia": [
        ("Carens / Rondo RS", 1999, 2006, "1.8L, 2.0L Beta / 2.0L CRDi D4EA", "RS"),
        ("Carens / Rondo UN", 2006, 2013, "2.0L Theta / 2.7L V6 Mu / 2.0L CRDi D4EA", "UN"),
        ("Carens RP", 2013, 2019, "1.6L GDI / 2.0L Nu MPI / 1.7L CRDi D4FD", "RP"),
        ("Carens KY", 2022, 2026, "1.5L Smartstream / 1.4T / 1.5L CRDi", "KY"),
        ("Bongo Truck 3rd Gen", 2004, 2026, "2.5L CRDi D4CB / 2.7L J2 / 2.9L J3 Diesel", "PU"),
        ("Telluride ON", 2019, 2026, "3.8L V6 Lambda II Atkinson G6DN", "ON"),
        ("Mohave / Borrego HM", 2008, 2024, "3.0L V6 S-Engine CRDi D6EB / 4.6L V8", "HM"),
        ("Sonet QY", 2020, 2026, "1.2L Kappa / 1.0L Turbo / 1.5L CRDi", "QY"),
    ]
}

@transaction.atomic
def run():
    print("[*] Adding expanded vehicles to the database...")
    total_added_models = 0
    total_makes = 0

    for make_name, models in more_cars.items():
        make_obj, _ = CarMake.objects.get_or_create(name=make_name)
        total_makes += 1
        for m_name, y_from, y_to, eng, chassis in models:
            cm_obj, created = CarModel.objects.get_or_create(
                make=make_obj,
                name=m_name,
                year_from=y_from,
                year_to=y_to,
                defaults={
                    "engine_type": eng,
                    "chassis_prefixes": chassis
                }
            )
            if not created:
                cm_obj.engine_type = eng
                cm_obj.chassis_prefixes = chassis
                cm_obj.save()
            total_added_models += 1

    final_makes = CarMake.objects.count()
    final_models = CarModel.objects.count()
    print(f"[+] Total in DB: {final_makes} Car Makes and {final_models} Car Models.")

if __name__ == '__main__':
    run()
