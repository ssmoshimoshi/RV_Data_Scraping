"""
RUANG VISUAL — Lead Scoring Engine (Module E)
===============================================
Rule-based scoring untuk setiap lead. Skor 1-10.
Referensi: intelligence_pipeline_prd.md §10
"""

from scrapers.config import (
    SCORING_RULES, SCORE_LABELS,
    CATEGORY_MAP, FRANCHISE_BRANDS,
)
from scrapers.utils import get_logger

log = get_logger("lead-scorer")


def detect_category(name: str, gmaps_types: str = "", bio: str = "") -> str:
    """
    Auto-detect kategori bisnis dari nama, tipe Google Maps, atau bio IG.
    Returns: 'fnb', 'eo', 'retail', 'instansi', 'percetakan', atau 'lainnya'
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


def calculate_score(lead: dict) -> tuple[int, list[str]]:
    """
    Hitung skor prospek berdasarkan SCORING_RULES.

    Args:
        lead: dict dengan keys:
            - nama_bisnis (str)
            - kategori (str): 'fnb', 'eo', 'retail', 'instansi', dll
            - telepon (str)
            - website (str)
            - instagram (str)
            - rating (float)
            - is_new_3months (bool)
            - is_new_6months (bool)
            - lokasi_makassar_kota (bool)

    Returns:
        (score: int, reasons: list[str])
    """
    score = 0
    reasons = []

    # --- Kontak ---
    if lead.get("telepon"):
        score += SCORING_RULES["ada_nomor_telepon"]
        reasons.append("+2 ada telepon")

    if lead.get("website"):
        score += SCORING_RULES["ada_website"]
        reasons.append("+1 ada website")

    if lead.get("instagram"):
        score += SCORING_RULES["ada_akun_instagram"]
        reasons.append("+1 ada Instagram")

    # --- Kategori ---
    kategori = lead.get("kategori", "lainnya")
    if kategori == "fnb":
        score += SCORING_RULES["kategori_fnb"]
        reasons.append("+3 F&B")
    elif kategori == "eo":
        score += SCORING_RULES["kategori_eo"]
        reasons.append("+3 Event Organizer")
    elif kategori == "retail":
        score += SCORING_RULES["kategori_retail"]
        reasons.append("+2 Retail")
    elif kategori == "instansi":
        score += SCORING_RULES["kategori_instansi"]
        reasons.append("+2 Instansi/Kantor")

    # --- Usia Bisnis ---
    if lead.get("is_new_3months"):
        score += SCORING_RULES["bisnis_baru_3bulan"]
        reasons.append("+3 bisnis baru <3 bulan")
    elif lead.get("is_new_6months"):
        score += SCORING_RULES["bisnis_baru_6bulan"]
        reasons.append("+2 bisnis baru <6 bulan")

    # --- Rating ---
    rating = lead.get("rating", 0)
    if 0 < rating < 4.0:
        score += SCORING_RULES["rating_dibawah_4"]
        reasons.append("+1 rating <4.0")

    # --- Lokasi ---
    if lead.get("lokasi_makassar_kota"):
        score += SCORING_RULES["lokasi_makassar_kota"]
        reasons.append("+1 lokasi Makassar Kota")

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


def score_and_format(lead: dict) -> dict:
    """
    Hitung skor dan tambahkan ke lead dict.
    Returns lead dict dengan tambahan keys: skor, skor_label, skor_reasons
    """
    score, reasons = calculate_score(lead)
    lead["skor"] = score
    lead["skor_label"] = get_score_label(score)
    lead["skor_reasons"] = "; ".join(reasons)
    return lead
