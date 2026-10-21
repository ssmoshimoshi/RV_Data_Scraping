"""
RUANG VISUAL - Lead Scoring Engine (Module E)
===============================================
Rule-based scoring untuk setiap lead. Skor 1-10.
Mendukung pembobotan kedekatan geografis workshop RV dan ekspansi 9 sektor bisnis.
Referensi: intelligence_pipeline_prd.md §10
"""

import urllib.parse
from scrapers.config import (
    SCORING_RULES, SCORE_LABELS,
    CATEGORY_MAP, FRANCHISE_BRANDS,
    RV_NEARBY_KEYWORDS,
)
from scrapers.contact_enricher import classify_phone_number, enrich_lead_record
from scrapers.utils import get_logger

log = get_logger("lead-scorer")


def detect_category(name: str, gmaps_types: str = "", bio: str = "") -> str:
    """
    Auto-detect kategori bisnis dari nama, tipe Google Maps, atau bio IG.
    Returns salah satu dari 9 kategori:
    'property', 'emas_jewelry', 'kantor_agensi', 'klinik_estetika',
    'fashion_butik', 'fnb', 'eo', 'pendidikan', 'retail', atau 'lainnya'.
    """
    text = f"{name} {gmaps_types} {bio}".lower()

    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in text:
                return category

    return "lainnya"


def is_franchise(name: str) -> bool:
    """Cek apakah bisnis adalah franchise nasional."""
    name_lower = name.lower()
    return any(brand in name_lower for brand in FRANCHISE_BRANDS)


def is_near_rv(address: str, name: str = "", query: str = "") -> bool:
    """Cek apakah lokasi berada di radius dekat workshop RUANG VISUAL (Rappocini / Bua Kana)."""
    text = f"{address} {name} {query}".lower()
    return any(kw in text for kw in RV_NEARBY_KEYWORDS)


def calculate_score(lead: dict) -> tuple[int, list[str]]:
    """
    Hitung skor prospek berdasarkan SCORING_RULES.
    """
    score = 0
    reasons = []

    # --- Kontak & Validitas Komunikasi ---
    phone_info = classify_phone_number(lead.get("telepon", ""))
    if phone_info["is_wa_ready"]:
        score += 3
        reasons.append("+3 nomor WhatsApp aktif (Outreach Siap)")
    elif phone_info["type"] == "landline":
        score += 1
        reasons.append("+1 telepon kantor PSTN")

    if lead.get("website"):
        score += SCORING_RULES["ada_website"]
        reasons.append("+1 ada website")

    if lead.get("instagram"):
        score += SCORING_RULES["ada_akun_instagram"]
        reasons.append("+1 ada Instagram")

    # --- Kategori (9 Sektor Ekspansi) ---
    kategori = lead.get("kategori", "lainnya")
    if kategori == "property":
        score += SCORING_RULES["kategori_property"]
        reasons.append("+3 Property & Developer")
    elif kategori == "emas_jewelry":
        score += SCORING_RULES["kategori_emas_jewelry"]
        reasons.append("+3 Toko Emas & Jewelry")
    elif kategori == "kantor_agensi":
        score += SCORING_RULES["kategori_kantor_agensi"]
        reasons.append("+3 Kantor & Agensi")
    elif kategori == "klinik_estetika":
        score += SCORING_RULES["kategori_klinik_estetika"]
        reasons.append("+3 Klinik Estetika & Skincare")
    elif kategori == "fnb":
        score += SCORING_RULES["kategori_fnb"]
        reasons.append("+3 F&B / Kuliner")
    elif kategori == "eo":
        score += SCORING_RULES["kategori_eo"]
        reasons.append("+3 Event & Wedding Organizer")
    elif kategori == "fashion_butik":
        score += SCORING_RULES["kategori_fashion_butik"]
        reasons.append("+2 Fashion & Butik")
    elif kategori == "retail":
        score += SCORING_RULES["kategori_retail"]
        reasons.append("+2 Retail")
    elif kategori == "pendidikan":
        score += SCORING_RULES["kategori_pendidikan"]
        reasons.append("+2 Pendidikan")

    # --- Kedekatan Geografis (Radius Workshop) ---
    if lead.get("lokasi_dekat_rv"):
        score += SCORING_RULES["lokasi_dekat_rv"]
        reasons.append("+2 dekat workshop RV")
    elif lead.get("lokasi_makassar_kota"):
        score += SCORING_RULES["lokasi_makassar_kota"]
        reasons.append("+1 Makassar Kota")

    # --- Usia Bisnis ---
    if lead.get("is_new_3months"):
        score += SCORING_RULES["bisnis_baru_3bulan"]
        reasons.append("+3 bisnis baru <3 bulan")
    elif lead.get("is_new_6months"):
        score += SCORING_RULES["bisnis_baru_6bulan"]
        reasons.append("+2 bisnis baru <6 bulan")

    # --- Kondisi Rating ---
    rating = lead.get("rating", 0)
    if 0 < rating < 4.0:
        score += SCORING_RULES["rating_dibawah_4"]
        reasons.append("+1 rating <4.0")

    # --- Faktor Negatif ---
    if is_franchise(lead.get("nama_bisnis", "")):
        score += SCORING_RULES["franchise_nasional"]
        reasons.append("-3 franchise nasional")

    # Clamp skor ke 1-10
    score = max(1, min(10, score))

    return score, reasons


def get_score_label(score: int) -> str:
    """Dapatkan label skor (HOT/WARM/COOL/COLD)."""
    for (low, high), label in SCORE_LABELS.items():
        if low <= score <= high:
            return label
    return "COLD"


def generate_whatsapp_pitch(lead: dict) -> str:
    """
    Generate personalized WhatsApp pitch message based on business category.
    Returns URL-encoded message text ready for wa.me link.
    """
    nama_bisnis = lead.get("nama_bisnis", "")
    kategori = lead.get("kategori", "lainnya").lower()
    lokasi = lead.get("alamat", "Makassar")
    
    # Salam pembuka
    greeting = f"Halo Tim {nama_bisnis}, salam hangat dari Ruang Visual Makassar."
    
    # Penawaran spesifik berdasarkan kategori
    if kategori in ["fnb", "kuliner", "cafe", "resto", "restoran"]:
        pitch = (
            "Kami menawarkan solusi cetak khusus untuk bisnis kuliner: "
            "Stiker segel kemasan anti-minyak tahan panas, buku menu laminasi doff waterproof, "
            "standing banner promo harian, dan kemasan paper bag food grade dengan desain eksklusif."
        )
    
    elif kategori in ["kantor_agensi", "konsultan", "notaris", "developer"]:
        pitch = (
            "Kami menawarkan paket cetak profesional untuk kantor: "
            "Company profile eksklusif dengan finishing lux, kop surat & amplop formal, "
            "kartu nama hotprint/emboss premium, dan map presentasi full color dengan embossing logo."
        )
    
    elif kategori in ["eo", "event", "wedding", "studio"]:
        pitch = (
            "Kami spesialis cetak kilat untuk kebutuhan event: "
            "Backdrop premium dengan garansi warna presisi, standing roll-up banner portable, "
            "photobook album wedding eksklusif, plakat akrilik kilat 24 jam, dan undangan cetak tebal bertekstur."
        )
    
    elif kategori in ["fashion_butik", "retail", "toko"]:
        pitch = (
            "Kami menyediakan solusi branding retail: "
            "Hangtag pakaian tebal bertekstur dengan tali warna custom, shopping bag cetak offset glossy, "
            "nota transaksi 2-3 ply NCR custom design, dan stiker label produk waterproof."
        )
    
    elif kategori in ["property", "developer"]:
        pitch = (
            "Kami menawarkan paket cetak property: "
            "Brosur offset A4 glossy 150gsm, X-banner promo unit ready stock, "
            "site plan cetak plotter besar format, dan spanduk kawasan dengan grommets kuat."
        )
    
    elif kategori in ["emas_jewelry", "toko_emas"]:
        pitch = (
            "Kami menawarkan solusi cetak premium untuk toko emas: "
            "Kartu garansi emas laminasi doff anti-pemalsuan, box packaging mewah dengan hotprint gold, "
            "shopping bag art paper eksklusif, dan standing banner display promosi."
        )
    
    elif kategori in ["klinik_estetika", "klinik", "dental"]:
        pitch = (
            "Kami menawarkan paket cetak medis profesional: "
            "Brosur treatment laminasi doff hygienis, X-banner promo paket perawatan, "
            "kartu member PVC cetak dengan barcode, dan poster edukasi kesehatan waterproof."
        )
    
    elif kategori in ["pendidikan", "sekolah", "kursus"]:
        pitch = (
            "Kami menawarkan solusi cetak pendidikan: "
            "Sertifikat cetak tebal dengan border elegan, banner pendaftaran siswa baru tahan outdoor, "
            "buku panduan siswa jilid rapi, dan ID card siswa PVC dengan teknologi cetak presisi."
        )
    
    else:
        pitch = (
            "Kami menawarkan berbagai solusi cetak untuk kebutuhan bisnis Anda: "
            "Banner indoor/outdoor tahan cuci, kartu nama premium dengan berbagai finishing, "
            "brosur & flyer full color glossy, stiker custom berbagai bahan, dan packaging kreatif."
        )
    
    # Penutup
    closing = (
        f"Kami berlokasi dekat area {lokasi} dengan layanan antar gratis area Makassar. "
        "Konsultasi desain GRATIS dan bisa kirim sampel cetak ke lokasi Anda. "
        "Boleh chat untuk tanya detail harga dan lihat portofolio hasil cetak kami?"
    )
    
    full_message = f"{greeting}\n\n{pitch}\n\n{closing}"
    
    # URL encode the message
    encoded_message = urllib.parse.quote(full_message)
    
    return encoded_message


def score_and_format(lead: dict = None, **kwargs) -> dict:
    """
    Hitung skor dan tambahkan ke lead dict.
    Mendukung argumen berupa dictionary atau keyword arguments.
    Returns lead dict dengan tambahan keys: skor, skor_label, skor_reasons, tier_bisnis, klaster_wilayah
    """
    if lead is None:
        lead = dict(kwargs)
    elif kwargs:
        lead.update(kwargs)
    lead = enrich_lead_record(lead)
    score, reasons = calculate_score(lead)
    lead["skor"] = score
    base_label = get_score_label(score)

    if lead.get("is_wa_ready"):
        lead["skor_label"] = f"{base_label} (WA)"
        # Generate personalized WhatsApp pitch link
        phone_clean = lead.get("no_whatsapp", "") or lead.get("telepon_bersih", "")
        if phone_clean:
            lead["no_whatsapp"] = phone_clean
            pitch_message = generate_whatsapp_pitch(lead)
            lead["whatsapp_link"] = f"https://wa.me/{phone_clean}?text={pitch_message}"
    elif lead.get("kontak_tipe") == "landline":
        lead["skor_label"] = f"{base_label} (Telp)"
    else:
        lead["skor_label"] = f"{base_label} (No Kontak)"

    lead["skor_reasons"] = "; ".join(reasons)
    return lead
