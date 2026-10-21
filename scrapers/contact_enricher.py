"""
RUANG VISUAL - Contact Enricher & Phone Classifier Module
=========================================================
Modul pengayaan data kontak, klasifikasi telepon seluler/WhatsApp vs PSTN kantor Makassar,
estimasi skala volume kebutuhan cetak, dan pemetaan klaster wilayah kanvasing.
Bebas emoji sesuai aturan operasional RUANG VISUAL.
"""

import re
import urllib.parse
from typing import Dict, Any, Tuple


# ─── 1. KLASIFIKASI & NORMALISASI NOMOR TELEPON ──────────────────────────────
def classify_phone_number(raw_phone: str) -> Dict[str, Any]:
    """
    Menganalisis nomor telepon dan mengklasifikasikannya ke dalam:
    - 'whatsapp': Nomor HP seluler Indonesia (08xx, +628xx, 628xx)
    - 'landline': Nomor telepon kabel kantor Makassar (0411-xxx, (0411) xxx)
    - 'none': Tidak ada nomor telepon
    """
    if not raw_phone or str(raw_phone).strip() in ("", "-", "None"):
        return {
            "type": "none",
            "clean_number": "",
            "formatted": "-",
            "is_wa_ready": False,
            "wa_link": "-",
            "label": "Tanpa Telepon"
        }

    digits = re.sub(r"\D", "", str(raw_phone))

    # Cek nomor seluler Indonesia (WhatsApp Ready)
    # Awalan: 08..., 628..., +628...
    if digits.startswith("628") and len(digits) in range(10, 15):
        clean_wa = digits
        formatted = "0" + clean_wa[2:]
        return {
            "type": "whatsapp",
            "clean_number": clean_wa,
            "formatted": formatted,
            "is_wa_ready": True,
            "wa_link": f'=HYPERLINK("https://wa.me/{clean_wa}", "Chat WA")',
            "label": "WhatsApp Ready"
        }
    elif digits.startswith("08") and len(digits) in range(10, 14):
        clean_wa = "62" + digits[1:]
        return {
            "type": "whatsapp",
            "clean_number": clean_wa,
            "formatted": digits,
            "is_wa_ready": True,
            "wa_link": f'=HYPERLINK("https://wa.me/{clean_wa}", "Chat WA")',
            "label": "WhatsApp Ready"
        }
    elif digits.startswith("8") and len(digits) in range(9, 13):
        clean_wa = "62" + digits
        return {
            "type": "whatsapp",
            "clean_number": clean_wa,
            "formatted": "0" + digits,
            "is_wa_ready": True,
            "wa_link": f'=HYPERLINK("https://wa.me/{clean_wa}", "Chat WA")',
            "label": "WhatsApp Ready"
        }

    # Cek nomor telepon kabel Makassar (PSTN kode area 0411)
    if digits.startswith("0411") or digits.startswith("411") or (digits.startswith("62411")):
        # Nomor kabel tidak bisa langsung di-WA
        if digits.startswith("62411"):
            local_num = "0411-" + digits[5:]
        elif digits.startswith("0411"):
            local_num = "0411-" + digits[4:]
        else:
            local_num = "0411-" + digits[3:]

        return {
            "type": "landline",
            "clean_number": digits,
            "formatted": local_num,
            "is_wa_ready": False,
            "wa_link": "-",
            "label": "Telepon Kantor PSTN"
        }

    # Format lain yang tidak memenuhi kriteria seluler
    return {
        "type": "unknown",
        "clean_number": digits,
        "formatted": str(raw_phone).strip(),
        "is_wa_ready": False,
        "wa_link": "-",
        "label": "Nomor Lainnya"
    }


# ─── 2. ESTIMATOR SKALA BISNIS & ESTIMASI VOLUME CETAK ───────────────────────
def estimate_business_scale(reviews: int, rating: float, category: str) -> Dict[str, str]:
    """
    Memperkirakan skala bisnis calon customer dan volume potensi cetak B2B:
    - Tier 1: Enterprise / High Volume (>80 review, kategori prioritas seperti F&B, Developer, Emas)
    - Tier 2: Medium Volume (20-80 review atau kategori menengah seperti Butik, EO)
    - Tier 3: Entry / Low Volume (<20 review atau kantor perorangan)
    """
    reviews = int(reviews or 0)
    rating = float(rating or 0.0)
    category = str(category or "").lower()

    high_demand_categories = ["fnb", "property", "emas_jewelry", "klinik_estetika"]
    medium_demand_categories = ["fashion_butik", "eo", "retail", "kantor_agensi"]

    if reviews >= 80 or (reviews >= 40 and category in high_demand_categories):
        tier = "Tier 1 (High Volume)"
        proyeksi_cetak = "Kebutuhan Rutin Skala Besar: Box packaging offset, kalender dinding eksklusif, seragam polo/lanyard, katalog company profile tebal, banner promo bertempo cepat."
    elif reviews >= 20 or category in medium_demand_categories:
        tier = "Tier 2 (Medium Volume)"
        proyeksi_cetak = "Kebutuhan Berkala: Stiker vinyl doff/glossy untuk kemasan, daftar menu akrilik meja, paper bag sablon, X-banner promosi toko, kartu garansi."
    else:
        tier = "Tier 3 (Entry Volume)"
        proyeksi_cetak = "Kebutuhan Esensial: Kartu nama staf, stempel flash tahan air, nota bon rangkap (NCR), kop surat resmi, stiker pengaman barcode."

    return {
        "tier": tier,
        "proyeksi_cetak": proyeksi_cetak
    }


# ─── 3. DETEKSI KLASTER KANVASING MAKASSAR ──────────────────────────────────
MAKASSAR_CLUSTERS = {
    "Klaster A (Pettarani - Rappocini)": [
        "pettarani", "rappocini", "bua kana", "mapala", "karunrung", "tidung", "ballaparang"
    ],
    "Klaster B (Panakkukang - Boulevard)": [
        "panakkukang", "boulevard", "pengayoman", "adjakang", "todopuli", "pandang"
    ],
    "Klaster C (Hertasning - Aroepala)": [
        "hertasning", "aroepala", "minasa upa", "aeropala", "tun abdul razak"
    ],
    "Klaster D (Sentra Somba Opu - Losari)": [
        "somba opu", "losari", "ujung pandang", "penghibur", "ahmad yani", "patimura"
    ],
    "Klaster E (Alauddin - Veteran)": [
        "alauddin", "veteran selatan", "veteran utara", "pa'baeng-baeng", "kumala"
    ]
}

def detect_makassar_cluster(address: str, business_name: str = "") -> str:
    """
    Mendeteksi klaster zonasi geografis untuk pengelompokan rute kunjungan tim sales lapangan.
    """
    full_text = f"{address} {business_name}".lower()
    for cluster_name, keywords in MAKASSAR_CLUSTERS.items():
        if any(kw in full_text for kw in keywords):
            return cluster_name
    return "Makassar Wilayah Lainnya"


# ─── 4. FUNGSI ENRICHMENT UTAMA ──────────────────────────────────────────────
def enrich_lead_record(lead: dict) -> dict:
    """
    Memperkaya record prospek dengan klasifikasi kontak, skala bisnis, dan klaster rute.
    """
    raw_phone = lead.get("telepon", "")
    phone_info = classify_phone_number(raw_phone)

    lead["kontak_tipe"] = phone_info["type"]
    lead["telepon_bersih"] = phone_info["clean_number"]
    lead["no_whatsapp"] = phone_info["clean_number"] if phone_info["is_wa_ready"] else ""
    lead["telepon_terformat"] = phone_info["formatted"]
    lead["is_wa_ready"] = phone_info["is_wa_ready"]
    lead["wa_link"] = phone_info["wa_link"]
    lead["label_kontak"] = phone_info["label"]

    # Perbarui proyeksi kebutuhan cetak berbasis estimasi skala
    scale_info = estimate_business_scale(
        reviews=lead.get("jumlah_review", 0),
        rating=lead.get("rating", 0.0),
        category=lead.get("kategori_kode", "")
    )
    lead["tier_bisnis"] = scale_info["tier"]
    if not lead.get("proyeksi_kebutuhan") or lead.get("proyeksi_kebutuhan") == "Banner dan Media Promosi":
        lead["proyeksi_kebutuhan"] = scale_info["proyeksi_cetak"]

    # Deteksi klaster kanvasing
    lead["klaster_wilayah"] = detect_makassar_cluster(
        address=lead.get("alamat", ""),
        business_name=lead.get("nama_bisnis", "")
    )

    return lead
