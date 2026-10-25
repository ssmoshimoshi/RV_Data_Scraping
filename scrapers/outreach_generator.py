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

_TEMPLATE_FNB = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin tanya Kak, untuk kemasan {name} (seperti paper cup atau box) saat ini pakai sablon custom atau masih polos? "
    "Kebetulan kami vendor cetak kemasan lokal di Makassar dan sedang bagi sampel bahan gratis untuk resto/kafe area {district}. "
    "Boleh kami antarkan sampel fisiknya ke outlet?"
)

_TEMPLATE_FASHION = (
    "Halo Kak {name}, salam dari RUANG VISUAL Makassar. "
    "Izin tanya Kak, untuk pengiriman pakaian {name} saat ini sudah pakai polymailer cetak logo atau plastik polos? "
    "Kebetulan kami vendor kemasan lokal di Makassar dan ada promo sampel gratis hangtag tebal dan polymailer untuk butik area {district}. "
    "Boleh kami drop sampelnya ke toko?"
)

_TEMPLATE_SKINCARE = (
    "Halo Kak {name}, salam dari RUANG VISUAL Makassar. "
    "Izin tanya Kak, untuk kemasan produk {name} seperti stiker segel botol dan box lipat saat ini cetak di mana? "
    "Kebetulan kami vendor lokal Makassar dengan stiker tahan air/serum dan kami ingin kirimkan sampel bahan cetak gratis ke klinik. "
    "Boleh kami kirimkan katalog dan sampelnya?"
)

_TEMPLATE_GENERAL = (
    "Halo Kak {name}, salam dari tim RUANG VISUAL di Makassar. "
    "Izin tanya Kak, untuk kemasan dan label produk {name} saat ini cetak di mana? "
    "Kebetulan kami vendor cetak lokal di Makassar dengan produk stiker label kemasan tahan air dan paper bag belanja serbaguna. "
    "Ada opsi pengantaran sampel bahan cetak gratis ke outlet di area {district}. "
    "Boleh kami antarkan sampelnya?"
)

_FNB_CATEGORIES = {
    'fnb_food_resto', 'fnb_beverage', 'fnb_bakery', 'fnb_catering', 'fnb_snack',
}
_FASHION_CATEGORIES = {
    'fashion_retail', 'fashion_boutique', 'fashion_hijab',
}
_SKINCARE_CATEGORIES = {
    'beauty_skincare', 'skincare_clinic', 'skincare_beauty', 'beauty_salon', 'skincare',
}

_RECOMMENDED = {
    'fnb': 'Paper Cup 8oz/12oz, Lunch Box L, Paper Bag',
    'fashion': 'Polymailer Custom, Hangtag Tebal, Tissue Paper',
    'skincare': 'Stiker Segel Tahan Air, Box Lipat, Amplop Kraft',
    'general': 'Stiker Segel Vinyl Serbaguna, Paper Bag Belanja, Nota NCR',
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
    if category in _FNB_CATEGORIES:
        return 'fnb'
    if category in _FASHION_CATEGORIES:
        return 'fashion'
    if category in _SKINCARE_CATEGORIES:
        return 'skincare'
    if dossier:
        sec = dossier.get('sector')
        if sec in ('fnb', 'fashion', 'skincare', 'general'):
            return sec
        for rec in dossier.get('records', []):
            if isinstance(rec, dict) and rec.get('sector') in ('fnb', 'fashion', 'skincare', 'general'):
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
        'fnb': _TEMPLATE_FNB,
        'fashion': _TEMPLATE_FASHION,
        'skincare': _TEMPLATE_SKINCARE,
        'general': _TEMPLATE_GENERAL,
    }[sector]
    return template.format(name=name, district=district)


def recommended_products(dossier: dict) -> str:
    category = dossier.get('category') or classify_category(
        dossier.get('business_name', ''), dossier.get('biography', ''), []
    )
    return _RECOMMENDED.get(_resolve_sector(category, dossier), _RECOMMENDED['general'])


def generate_whatsapp_click_url(phone: str, pitch: str) -> str:
    digits = ''.join(c for c in (phone or '') if c.isdigit())
    if not digits:
        return ''
    return f"https://wa.me/{digits}?text={urllib.parse.quote(pitch)}"
