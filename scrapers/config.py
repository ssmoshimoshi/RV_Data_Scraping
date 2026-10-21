"""
RUANG VISUAL - Shared Configuration
=====================================
Semua konfigurasi queries, keywords, delays, dan scoring rules.
Mendukung pencarian berbasis radius dari titik pusat workshop:
Bua Kana, Rappocini, Makassar (-5.1567, 119.4339)
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

# ─── Titik Pusat Workshop RUANG VISUAL (Epicenter) ───────────────────────────
RV_LATITUDE = -5.1566941
RV_LONGITUDE = 119.4338932
RV_LOCATION_NAME = "Bua Kana, Rappocini, Makassar"

# Kata kunci area sekitar titik pusat untuk pemberian bonus kedekatan lokasi (+2 skor)
RV_NEARBY_KEYWORDS = [
    "rappocini", "bua kana", "pettarani", "hertasning",
    "tidung", "ballaparang", "karunrung", "mapala",
    "minasa upa", "alauddin", "veteran selatan", "emmy saelan",
]

# ─── Rate Limiting ────────────────────────────────────────────────────────────
GMAPS_DELAY_SECONDS = (3, 5)        # Random delay antara 3-5 detik
INSTAGRAM_DELAY_SECONDS = (5, 10)   # Random delay antara 5-10 detik
TIKTOK_DELAY_SECONDS = (5, 10)      # Random delay antara 5-10 detik
FB_DELAY_SECONDS = (4, 7)          # Random delay antara 4-7 detik

INSTAGRAM_MAX_PAGES_PER_SESSION = 15
TIKTOK_MAX_PAGES_PER_SESSION = 15
FB_MAX_ITEMS_PER_SESSION = 20

# ─── Google Maps Queries Berbasis Ring & Sektor ──────────────────────────────
# Disusun dari ring terdekat dari workshop RUANG VISUAL (Bua Kana, Rappocini) meluas ke koridor bisnis utama
GMAPS_LEAD_QUERIES = [
    # RING 1: Radius Inti (0 - 2 km: Bua Kana, Rappocini, Pettarani Selatan, Hertasning Awal)
    "kantor konsultan Jl AP Pettarani Makassar",
    "agensi Jl AP Pettarani Makassar",
    "developer perumahan Hertasning Makassar",
    "kantor pemasaran perumahan Makassar",
    "toko emas Veteran Makassar",
    "klinik kecantikan Hertasning Makassar",
    "cafe Rappocini Makassar",
    "restoran Hertasning Makassar",
    "notaris Rappocini Makassar",
    "butik Hertasning Makassar",
    "coffee shop Pettarani Makassar",

    # RING 2: Koridor Bisnis Utama (2 - 4 km: Panakkukang, Boulevard, Pengayoman, Alauddin)
    "kantor Panakkukang Makassar",
    "coworking space Panakkukang Makassar",
    "cafe Boulevard Makassar",
    "restoran Pengayoman Makassar",
    "butik Pengayoman Makassar",
    "event organizer Panakkukang Makassar",
    "wedding organizer Makassar",
    "dental clinic Makassar",
    "sekolah swasta Makassar",
    "toko oleh-oleh Makassar",

    # RING 3: Sentra Perdagangan & Heritage (4 - 7 km: Somba Opu, Losari, Ujung Pandang)
    "toko emas Somba Opu Makassar",
    "toko perhiasan Makassar",
    "wedding venue Makassar",
    "studio foto Makassar",
    "hotel resto Losari Makassar",
    
    # RING 4: Ekspansi Sektor Bisnis Baru (Distribusi, Event, Advertising)
    "kantor distributor Makassar",
    "toko perlengkapan event Makassar",
    "agensi periklanan Makassar",
    
    # RING 5: UMKM Lokal Mandiri - Kuliner Khas Makassar
    "coto makassar",
    "pallubasa makassar",
    "ikan bakar makassar",
    "cafe kopi makassar",
    "bakery makassar",
    "rumah makan makassar",
    
    # RING 6: Oleh-Oleh & Souvenir Khas
    "oleh oleh khas makassar",
    "jalangkote makassar",
    "otak otak makassar",
    "sirup markisa makassar",
    "kue tradisional makassar",
    
    # RING 7: Fashion & Konveksi Lokal
    "butik hijab makassar",
    "distro makassar",
    "konveksi baju makassar",
    "jahit baju makassar",
    
    # RING 8: Skincare & Klinik Kecantikan Lokal
    "klinik kecantikan makassar",
    "skincare makassar",
    "dental clinic makassar",
    "klinik gigi makassar",
    
    # RING 9: Toko Emas & Perhiasan Lokal
    "toko emas somba opu makassar",
    "toko perhiasan makassar",
    
    # RING 10: Event & Wedding Organizer
    "wedding organizer makassar",
    "event organizer makassar",
    "wo makassar",
    "eo makassar",
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

GMAPS_TREND_QUERIES = [
    "toko packaging Makassar",
    "toko kemasan Makassar",
    "supplier stiker Makassar",
    "toko bahan printing Makassar",
    "grosir box makanan Makassar",
    "supplier hampers Makassar",
    "toko label produk Makassar",
    "perlengkapan branding Makassar",
]

# ─── Facebook Marketplace Makassar Config ─────────────────────────────────────
FB_MARKETPLACE_BASE_URL = "https://www.facebook.com/marketplace/makassar/search?query="

FB_LEAD_QUERIES = [
    "kue kering makassar",
    "frozen food makassar",
    "catering makassar",
    "hampers makassar",
    "snack makassar",
    "bakery makassar",
    "butik makassar",
    "hijab makassar",
    "skincare makassar",
]

FB_COMPETITOR_QUERIES = [
    "cetak banner makassar",
    "cetak stiker makassar",
    "cetak undangan makassar",
    "percetakan makassar",
    "spanduk makassar",
    "sablon makassar",
    "nota bon makassar",
]

# ─── Instagram Config ────────────────────────────────────────────────────────
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

IG_COMPETITOR_TARGETS = [
    "ruangvisual.id",
    "cahayaprintingmks",
    "primagrafika.mks",
    "bintangprintingmakassar",
    "percetakanmakassar_official",
]

IG_LEAD_DORK_QUERIES = [
    'site:instagram.com "Makassar" ("wa.me" OR "08") ("kuliner" OR "cafe" OR "resto")',
    'site:instagram.com "Makassar" ("wa.me" OR "08") ("klinik" OR "skincare" OR "aesthetic")',
    'site:instagram.com "Makassar" ("wa.me" OR "08") ("butik" OR "fashion" OR "hijab")',
    'site:instagram.com "Makassar" ("wa.me" OR "08") ("developer" OR "perumahan" OR "cluster")',
    'site:instagram.com "Makassar" ("wa.me" OR "08") ("wedding organizer" OR "wo makassar")',
]

# ─── TikTok Config ───────────────────────────────────────────────────────────
TIKTOK_LEAD_KEYWORDS = [
    "usaha baru makassar",
    "kuliner makassar",
    "cafe makassar",
    "umkm makassar",
    "jualan makassar",
    "butik makassar",
]

TIKTOK_COMPETITOR_KEYWORDS = [
    "percetakan makassar",
    "cetak makassar",
    "sablon makassar",
    "digital printing makassar",
]

TIKTOK_TREND_KEYWORDS = [
    "stiker hologram",
    "stiker die cut waterproof",
    "box packaging custom",
    "tumbler uv print",
    "standing pouch sablon",
    "hangtag baju tebal",
    "undangan akrilik aesthetic",
]

TIKTOK_KEYWORDS = TIKTOK_COMPETITOR_KEYWORDS + TIKTOK_TREND_KEYWORDS

# ─── Threads Config ──────────────────────────────────────────────────────────
THREADS_DELAY_SECONDS = (5, 10)
THREADS_MAX_PAGES_PER_SESSION = 15

THREADS_LEAD_KEYWORDS = [
    "usaha baru makassar",
    "bisnis makassar",
    "kuliner makassar",
    "cafe makassar buka",
    "umkm makassar",
    "brand lokal makassar",
    "frozen food makassar",
    "klinik baru makassar",
]

THREADS_COMPETITOR_KEYWORDS = [
    "percetakan makassar",
    "cetak murah makassar",
    "digital printing makassar",
    "sablon makassar",
    "cetak banner makassar",
    "cetak stiker makassar",
]

THREADS_TREND_KEYWORDS = [
    "packaging viral",
    "stiker aesthetic",
    "box kemasan custom",
    "label produk",
    "branding umkm",
    "desain kemasan",
    "standing pouch custom",
]

# ─── Lead Scoring Rules ──────────────────────────────────────────────────────
SCORING_RULES = {
    # Faktor Positif
    "ada_nomor_telepon":         2,
    "ada_website":               1,
    "ada_akun_instagram":        1,

    # Bobot Kategori Sektor
    "kategori_property":         3,
    "kategori_emas_jewelry":     3,
    "kategori_kantor_agensi":    3,
    "kategori_klinik_estetika":  3,
    "kategori_fnb":              3,
    "kategori_eo":               3,
    "kategori_fashion_butik":    2,
    "kategori_retail":           2,
    "kategori_pendidikan":       2,

    # Bobot Kedekatan Geografis (Radius Terdekat Workshop)
    "lokasi_dekat_rv":           2,   # Bonus jika berada di Bua Kana/Rappocini/Pettarani/Hertasning
    "lokasi_makassar_kota":      1,

    # Usia Bisnis & Kondisi Review
    "bisnis_baru_6bulan":        2,
    "bisnis_baru_3bulan":        3,
    "rating_dibawah_4":          1,

    # Faktor Negatif
    "sudah_punya_branding_kuat": -2,
    "franchise_nasional":        -3,
}

SCORE_LABELS = {
    (8, 10): "HOT",
    (5, 7):  "WARM",
    (3, 4):  "COOL",
    (1, 2):  "COLD",
}

# ─── Competitor Review Keywords ──────────────────────────────────────────────
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

# ─── Kategori Bisnis Mapping (Ekspansi 9 Sektor) ──────────────────────────────
CATEGORY_MAP = {
    "property": [
        "developer", "perumahan", "property", "properti", "cluster",
        "residence", "real estate", "agen properti", "kavling", "graha",
    ],
    "emas_jewelry": [
        "toko emas", "emas", "jewelry", "perhiasan", "jewellery",
        "berlian", "permata", "gold", "logam mulia",
    ],
    "kantor_agensi": [
        "kantor", "office", "agency", "agensi", "konsultan", "consultant",
        "notaris", "lawyer", "hukum", "advokat", "asuransi", "finance",
        "leasing", "bumn", "coworking", "arsitek", "studio desain",
    ],
    "klinik_estetika": [
        "klinik", "clinic", "aesthetic", "estetika", "skincare",
        "beauty", "kecantikan", "dokter gigi", "dental", "salon",
        "barbershop", "spa", "dermatology",
    ],
    "fashion_butik": [
        "butik", "boutique", "hijab", "busana", "fashion", "distro",
        "pakaian", "baju", "kebaya", "gamis", "sepatu", "tas",
    ],
    "fnb": [
        "restaurant", "restoran", "cafe", "kafe", "kedai", "coffee",
        "kopi", "warung", "bakery", "catering", "food", "makan",
        "kuliner", "bar", "bistro", "pizzeria", "sushi", "mie", "dapur",
    ],
    "eo": [
        "event", "wedding", "organizer", "wo ", "eo ", "planner",
        "dekorasi", "decoration", "fotografi", "studio foto", "photobooth",
    ],
    "pendidikan": [
        "sekolah", "school", "bimbel", "kursus", "akademi", "academy",
        "preschool", "tk ", "universitas", "kampus", "les ",
    ],
    "retail": [
        "toko", "shop", "store", "oleh-oleh", "souvenir", "gift",
        "mart", "minimarket", "swalayan", "supermarket",
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
