"""
RUANG VISUAL — Shared Configuration
=====================================
Semua konfigurasi queries, keywords, delays, dan scoring rules.
Referensi: intelligence_pipeline_prd.md §7-§11
"""

from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
SCRAPERS_DIR = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Buat direktori data jika belum ada
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ─── Rate Limiting ────────────────────────────────────────────────────────────
# WAJIB dipatuhi — lihat PRD §3 System Constraints
GMAPS_DELAY_SECONDS = (3, 5)        # Random delay antara 3-5 detik
INSTAGRAM_DELAY_SECONDS = (5, 10)   # Random delay antara 5-10 detik
TIKTOK_DELAY_SECONDS = (5, 10)      # Random delay antara 5-10 detik

INSTAGRAM_MAX_PAGES_PER_SESSION = 15
TIKTOK_MAX_PAGES_PER_SESSION = 15

# ─── Google Maps Queries (PRD §7) ────────────────────────────────────────────

GMAPS_LEAD_QUERIES = [
    # F&B (prioritas tinggi — sering butuh menu, banner, packaging)
    "cafe baru Makassar",
    "restoran baru Makassar",
    "kedai kopi Makassar",
    "catering Makassar",

    # Retail & UMKM
    "toko baru Makassar",
    "UMKM Makassar",
    "oleh-oleh khas Makassar",

    # Event & Jasa
    "event organizer Makassar",
    "wedding organizer Makassar",
    "jasa fotografi Makassar",

    # Instansi & Kantor
    "kantor baru Makassar",
    "coworking space Makassar",
    "klinik baru Makassar",
]

GMAPS_COMPETITOR_QUERIES = [
    "percetakan Makassar",
    "digital printing Makassar",
    "cetak banner Makassar",
    "cetak stiker Makassar",
    "cetak kartu nama Makassar",
    "percetakan offset Makassar",
    "printing Makassar",
]

# ─── Instagram Config (PRD §8) ───────────────────────────────────────────────

IG_HASHTAGS = [
    "percetakanmakassar",
    "cetakmakassar",
    "printingmakassar",
    "stikermakassar",
    "bannermakassar",
    "cetakmurah",
    "digitalprinting",
    "percetakan",
]

# ─── TikTok Config (PRD §9) ──────────────────────────────────────────────────

TIKTOK_KEYWORDS = [
    "percetakan Makassar",
    "cetak stiker",
    "digital printing",
    "packaging custom",
    "cetak banner",
    "printing murah",
    "usaha percetakan",
]

# ─── Lead Scoring Rules (PRD §10) ────────────────────────────────────────────

SCORING_RULES = {
    # Faktor Positif (tambah skor)
    "ada_nomor_telepon":         2,
    "ada_website":               1,
    "ada_akun_instagram":        1,
    "kategori_fnb":              3,
    "kategori_eo":               3,
    "kategori_retail":           2,
    "kategori_instansi":         2,
    "bisnis_baru_6bulan":        2,
    "bisnis_baru_3bulan":        3,
    "rating_dibawah_4":          1,
    "lokasi_makassar_kota":      1,

    # Faktor Negatif (kurangi skor)
    "sudah_punya_branding_kuat": -2,
    "franchise_nasional":        -3,
}

SCORE_LABELS = {
    (8, 10): "HOT",
    (5, 7):  "WARM",
    (3, 4):  "COOL",
    (1, 2):  "COLD",
}

# ─── Competitor Review Keywords (PRD §11) ────────────────────────────────────

QUALITY_KEYWORDS = [
    "warna meleset", "warna beda", "kualitas jelek", "buram", "pudar",
    "tipis", "sobek", "tidak rapi", "berantakan", "luntur", "garis",
    "kualitas buruk", "hasil jelek", "tidak bagus",
]

SOP_KEYWORDS = [
    "lambat", "lama", "admin tidak respon", "susah dihubungi",
    "tidak tepat waktu", "telat", "salah cetak", "salah ukuran",
    "tidak ramah", "ribet", "prosesnya lama", "respon lambat",
    "tidak profesional", "mengecewakan",
]

# ─── Kategori Bisnis Mapping ─────────────────────────────────────────────────
# Digunakan untuk auto-detect kategori dari nama/tipe bisnis Google Maps

CATEGORY_MAP = {
    "fnb": [
        "restaurant", "restoran", "cafe", "kafe", "kedai", "coffee",
        "kopi", "warung", "bakery", "catering", "food", "makan",
        "kuliner", "bar", "bistro", "pizzeria", "sushi",
    ],
    "eo": [
        "event", "wedding", "organizer", "wo ", "eo ", "planner",
        "dekorasi", "decoration",
    ],
    "retail": [
        "toko", "shop", "store", "butik", "boutique", "oleh-oleh",
        "souvenir", "gift", "fashion", "clothing",
    ],
    "instansi": [
        "kantor", "office", "klinik", "clinic", "rumah sakit",
        "hospital", "sekolah", "school", "universitas", "coworking",
    ],
    "percetakan": [
        "percetakan", "printing", "cetak", "print", "digital print",
        "offset", "sablon", "konveksi",
    ],
}

# ─── Franchise / Brand Nasional (untuk scoring negatif) ──────────────────────

FRANCHISE_BRANDS = [
    "kopi kenangan", "janji jiwa", "fore coffee", "starbucks",
    "mcdonald", "kfc", "pizza hut", "burger king", "jco",
    "mixue", "haus", "chatime", "gojek", "grab", "tokopedia",
    "indomaret", "alfamart", "alfamidi",
]
