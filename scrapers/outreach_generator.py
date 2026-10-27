import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import urllib.parse

from scrapers.lead_scoring import classify_category

_TEMPLATE_PAIN_POINT = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin Kak, kami membaca ulasan pelanggan mengenai kendala kemasan {issue} pada pesanan outlet Kakak di area {district}. "
    "Kebetulan kami vendor kemasan lokal di Makassar yang fokus memproduksi bahan kemasan tebal dan anti-bocor. "
    "Boleh kami antarkan sampel fisik bahan kemasan kami langsung ke outlet untuk dicoba?"
)

_TEMPLATE_EDUCATION = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin Kak, untuk kebutuhan rapor, ID card siswa, spanduk PPDB, atau brosur penerimaan siswa baru saat ini cetak di mana? "
    "Kebetulan kami vendor cetak lokal di Makassar yang melayani sekolah/madrasah dengan hasil berkualitas tinggi dan harga terjangkau. "
    "Ada promo sampel gratis untuk institusi pendidikan area {district}. Boleh kami kirimkan penawaran dan sampelnya?"
)

_TEMPLATE_CORPORATE_LEGAL = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin Kak, untuk kebutuhan map berkas, stempel flash otomatis, lanyard, atau banner acara kantor saat ini Bapak/Ibu gunakan dari mana? "
    "Kebetulan kami vendor profesional printing lokal di Makassar dengan layanan korporat terpercaya. "
    "Tersedia customisasi khusus untuk kebutuhan kantor hukum dan notaris. Boleh kami antarkan penawaran ke kantor Kakak?"
)

_TEMPLATE_EVENT_COMMUNITY = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin Kak, untuk kebutuhan sablon kaos panitia, ganci akrilik UV laser cut, pin peniti, atau spanduk event saat ini bekerja sama dengan vendor mana? "
    "Kebetulan kami spesialis printing dan merchandise komunitas/event lokal di Makassar dengan pengalaman banyak acara. "
    "Ada penawaran khusus untuk panitia dan komunitas area {district}. Boleh kami diskusi kebutuhan acara Kakak?"
)

_TEMPLATE_RETAIL_APPAREL = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL Makassar. "
    "Izin tanya Kak, untuk pengiriman pakaian {name} saat ini sudah pakai polymailer cetak logo atau sablon DTF 24s/30s berkualitas tinggi? "
    "Kebetulan kami spesialis printing dan packaging lokal di Makassar dengan hasil premium dan tahan lama. "
    "Ada promo sampel gratis hangtag tebal dan polymailer untuk distro dan butik area {district}. Boleh kami drop sampel ke toko Kakak?"
)

_TEMPLATE_FNB_HOSPITALITY = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin tanya Kak, untuk kemasan {name} (seperti paper cup atau box) serta label stiker botol/toples saat ini cetak dari mana? "
    "Kebetulan kami vendor cetak hospitality dan packaging lokal di Makassar dengan produk tahan air dan desain menarik. "
    "Ada sampel gratis untuk kafe dan resto area {district}. Boleh kami antarkan sampel langsung ke outlet?"
)

_TEMPLATE_SKINCARE = (
    "Halo Kak {name}, salam dari RUANG VISUAL Makassar. "
    "Izin tanya Kak, untuk kemasan produk {name} seperti stiker segel botol dan box lipat saat ini cetak di mana? "
    "Kebetulan kami vendor lokal Makassar dengan stiker tahan air/serum dan kami ingin kirimkan sampel bahan cetak gratis ke klinik. "
    "Boleh kami kirimkan katalog dan sampelnya?"
)

_TEMPLATE_GENERAL = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin tanya Kak, untuk kebutuhan promosi, kemasan, atau merchandise bisnis Kakak saat ini cetak di mana? "
    "Kebetulan kami vendor printing dan merchandise lokal di Makassar dengan layanan lengkap dan harga kompetitif. "
    "Ada penawaran khusus dan sampel gratis untuk usaha baru di area {district}. Boleh kami kirimkan katalog lengkap?"
)

_EDUCATION_CATEGORIES = {
    'education', 'sekolah', 'madrasah', 'pesantren', 'sma', 'smk', 'smp', 'sd', 'bimbel',
    'yayasan_pendidikan', 'universitas', 'kampus',
}
_CORPORATE_LEGAL_CATEGORIES = {
    'corporate_legal', 'law', 'lawyer', 'legal', 'notaris', 'ppat', 'kantor_hukum', 'advokat',
}
_EVENT_COMMUNITY_CATEGORIES = {
    'event_community', 'event', 'wedding', 'organizer', 'eo', 'festival', 'komunitas',
}
_FNB_HOSPITALITY_CATEGORIES = {
    'fnb_hospitality', 'fnb_food_resto', 'fnb_beverage', 'fnb_bakery', 'fnb_catering', 'fnb_snack',
}
_RETAIL_APPAREL_CATEGORIES = {
    'retail_apparel', 'fashion_retail', 'fashion_boutique', 'fashion_hijab', 'distro', 'butik',
}
_SKINCARE_CATEGORIES = {
    'beauty_skincare', 'skincare_clinic', 'skincare_beauty', 'beauty_salon', 'skincare', 'klinik_kecantikan',
}

_RECOMMENDED = {
    'education': 'Map Raport Korpel, ID Card Siswa, Spanduk PPDB, Brosur A3+',
    'corporate_legal': 'Map Berkas Folio, Stempel Flash Otomatis, Lanyard Tissue, Roll-Up Banner',
    'event_community': 'Sablon Kaos DTF Panitia, Ganci Akrilik UV 3mm, PIN Peniti, Spanduk Flexy',
    'retail_apparel': 'Polymailer Custom, Hangtag Tebal, Sablon Kaos DTF, Tote Bag Kanvas, Tas Spunbond Sablon, Stiker Vinyl',
    'fashion': 'Polymailer Custom, Hangtag Tebal, Tissue Paper',
    'fashion_retail': 'Polymailer Custom, Hangtag Tebal, Sablon Kaos DTF, Tote Bag Kanvas',
    'fnb_hospitality': 'Paper Cup 8oz/12oz, Lunch Box L, Paper Bag, Stiker Label Botol/Toples, Seragam Kaos Barista, Mug Souvenir, Spanduk',
    'fnb': 'Paper Cup 8oz/12oz, Lunch Box L, Paper Bag',
    'fnb_beverage': 'Paper Cup 8oz/12oz, Lunch Box L, Paper Bag',
    'fnb_food_resto': 'Paper Cup 8oz/12oz, Lunch Box L, Paper Bag',
    'beauty_skincare': 'Stiker Segel Tahan Air, Box Lipat, Amplop Kraft, Label Botol Custom',
    'skincare': 'Stiker Segel Tahan Air, Box Lipat, Amplop Kraft',
    'general': 'Stiker Segel Vinyl Serbaguna, Paper Bag Belanja, Nota NCR, Spanduk Promo',
}

_PAIN_ISSUE_GROUPS = (
    (('bocor', 'rembes', 'tumpah'), 'bocor/rembes'),
    (('penyok', 'tipis'), 'mudah penyok'),
    (('rusak', 'pecah'), 'mudah rusak'),
)

def _collect_pain_text(pain_points) -> str:
    if isinstance(pain_points, str):
        return pain_points.lower()
    if isinstance(pain_points, list):
        parts = []
        for item in pain_points:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get('review_text') or ''))
                parts.extend(str(k) for k in item.get('detected_keywords') or [])
        return ' '.join(parts).lower()
    return ''

def detect_pain_issue(dossier: dict):
    sources = [dossier.get('packaging_pain_points')]
    sources.extend(rec.get('packaging_pain_points') for rec in dossier.get('records', []) if isinstance(rec, dict))
    for source in sources:
        text = _collect_pain_text(source)
        if not text:
            continue
        for keywords, issue in _PAIN_ISSUE_GROUPS:
            if any(k in text for k in keywords):
                return issue
    return None


def _resolve_sector(category: str, dossier: dict = None) -> str:
    if category in ('fnb', 'fnb_beverage', 'fnb_food_resto'):
        return 'fnb_hospitality'
    if category in ('fashion', 'fashion_retail'):
        return 'retail_apparel'
    if category in ('skincare', 'beauty_skincare'):
        return 'beauty_skincare'
    if category in _EDUCATION_CATEGORIES:
        return 'education'
    if category in _CORPORATE_LEGAL_CATEGORIES:
        return 'corporate_legal'
    if category in _EVENT_COMMUNITY_CATEGORIES:
        return 'event_community'
    if category in _RETAIL_APPAREL_CATEGORIES:
        return 'retail_apparel'
    if category in _FNB_HOSPITALITY_CATEGORIES:
        return 'fnb_hospitality'
    if category in _SKINCARE_CATEGORIES:
        return 'beauty_skincare'
    if dossier:
        sec = dossier.get('sector')
        if sec in ('education', 'corporate_legal', 'event_community', 'retail_apparel', 'fnb_hospitality', 'beauty_skincare', 'general'):
            return sec
        for rec in dossier.get('records', []):
            if isinstance(rec, dict) and rec.get('sector') in ('education', 'corporate_legal', 'event_community', 'retail_apparel', 'fnb_hospitality', 'beauty_skincare', 'general'):
                return rec['sector']
    return 'general'


def generate_whatsapp_pitch(dossier: dict) -> str:
    name = dossier.get('business_name') or 'Bapak/Ibu'
    district = str(dossier.get('district_area') or dossier.get('city') or 'Makassar').title()
    issue = detect_pain_issue(dossier)
    if issue:
        return _TEMPLATE_PAIN_POINT.format(name=name, issue=issue, district=district)
    category = dossier.get('category') or classify_category(
        name, dossier.get('biography', ''), []
    )
    sector = _resolve_sector(category, dossier)
    template = {
        'education': _TEMPLATE_EDUCATION,
        'corporate_legal': _TEMPLATE_CORPORATE_LEGAL,
        'event_community': _TEMPLATE_EVENT_COMMUNITY,
        'retail_apparel': _TEMPLATE_RETAIL_APPAREL,
        'fnb_hospitality': _TEMPLATE_FNB_HOSPITALITY,
        'beauty_skincare': _TEMPLATE_SKINCARE,
        'general': _TEMPLATE_GENERAL,
    }.get(sector, _TEMPLATE_GENERAL)
    return template.format(name=name, district=district)


def recommended_products(dossier: dict) -> str:
    category = dossier.get('category') or classify_category(
        dossier.get('business_name', ''), dossier.get('biography', ''), []
    )
    if category in _RECOMMENDED:
        return _RECOMMENDED[category]
    sector = _resolve_sector(category, dossier)
    return _RECOMMENDED.get(sector, _RECOMMENDED['general'])


def generate_whatsapp_click_url(phone: str, pitch: str) -> str:
    digits = ''.join(c for c in (phone or '') if c.isdigit())
    if not digits:
        return ''
    return f"https://wa.me/{digits}?text={urllib.parse.quote(pitch)}"


# Alias penamaan resmi untuk menghindari ambiguitas impor dengan scrapers.lead_scoring
generate_outreach_pitch = generate_whatsapp_pitch
