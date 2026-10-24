import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timedelta
from typing import Optional, Tuple


NON_COMMERCIAL_KEYWORDS = ['personal', 'pribadi', 'private', 'family', 'keluarga', 'my life', 'diary']
FREE_DOMAIN_PATTERNS = ['linktr.ee', 'bit.ly', 'bio.link', 'blogspot', 'wordpress.com', 'wix.com', 'carrd.co']

CATEGORY_KEYWORDS = {
    'fnb_beverage': ['kopi', 'coffee', 'cafe', 'minuman', 'drink', 'juice', 'tea', 'boba', 'milk'],
    'fnb_food_resto': ['resto', 'restaurant', 'kuliner', 'food', 'makan', 'catering', 'bakery', 'cake'],
    'fashion_retail': ['fashion', 'clothing', 'baju', 'hijab', 'dress', 'outfit', 'store', 'boutique'],
    'beauty_skincare': ['beauty', 'skincare', 'kosmetik', 'makeup', 'salon', 'kecantikan', 'clinic'],
    'corporate_legal': ['law', 'lawyer', 'legal', 'notaris', 'konsultan', 'corporate', 'advisory'],
    'event_service': ['event', 'wedding', 'organizer', 'eo', 'decoration', 'photography', 'video'],
    'new_store_opening': ['grand opening', 'new store', 'baru buka', 'coming soon', 'soft opening'],
    'general_commercial': ['bisnis', 'usaha', 'jasa', 'service', 'produk', 'toko', 'umkm']
}


def qualify_lead(lead: dict) -> Tuple[bool, str]:
    last_post_date = lead.get('last_post_date')
    if last_post_date:
        if isinstance(last_post_date, str):
            try:
                last_post_date = datetime.fromisoformat(last_post_date.replace('Z', '+00:00'))
            except:
                return False, "Invalid date format"
        
        if last_post_date:
            days_ago = (datetime.now() - last_post_date).days
            if days_ago > 30:
                return False, "Inactive account (last post > 30 days)"
    
    whatsapp = lead.get('whatsapp_number')
    phone = lead.get('phone_number')
    email = lead.get('email')
    
    if not whatsapp and not phone and not email:
        return False, "No contact information"
    
    biography = lead.get('biography', '').lower()
    business_name = lead.get('business_name', '').lower()
    
    for keyword in NON_COMMERCIAL_KEYWORDS:
        if keyword in biography or keyword in business_name:
            return False, "Non-commercial/personal account"
    
    return True, "Qualified"


def classify_category(business_name: str, biography: str, caption_samples: list[str]) -> str:
    text = f"{business_name} {biography} {' '.join(caption_samples or [])}".lower()
    
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[category] = score
    
    if max(scores.values()) == 0:
        return 'general_commercial'
    
    return max(scores, key=scores.get)


def calculate_score(lead: dict) -> int:
    score = 0
    
    # S_kontak (maks 30)
    whatsapp = lead.get('whatsapp_number')
    phone = lead.get('phone_number')
    email = lead.get('email')
    
    if whatsapp:
        score += 30
    elif phone:
        score += 15
    elif email:
        score += 5
    
    # S_keaktifan (maks 25)
    last_post_date = lead.get('last_post_date')
    if last_post_date:
        if isinstance(last_post_date, str):
            try:
                last_post_date = datetime.fromisoformat(last_post_date.replace('Z', '+00:00'))
            except:
                last_post_date = None
        
        if last_post_date:
            days_ago = (datetime.now() - last_post_date).days
            if days_ago <= 3:
                score += 25
            elif days_ago <= 7:
                score += 20
            elif days_ago <= 14:
                score += 15
            elif days_ago <= 30:
                score += 10
    
    # S_lokasi (maks 20)
    latitude = lead.get('latitude')
    longitude = lead.get('longitude')
    address = lead.get('address_full', '')
    city = lead.get('city', '')
    
    if latitude and longitude:
        score += 20
    elif address or city:
        score += 10
    
    # S_anggaran (maks 15)
    is_ad_active = lead.get('is_ad_active', False)
    external_website = lead.get('external_website_url', '')
    
    if is_ad_active:
        score += 15
    elif external_website:
        is_free_domain = any(domain in external_website.lower() for domain in FREE_DOMAIN_PATTERNS)
        if not is_free_domain:
            score += 10
    
    # S_skala (maks 10)
    followers = lead.get('followers_count', 0)
    if 1000 <= followers <= 50000:
        score += 10
    elif 500 <= followers < 1000:
        score += 5
    elif followers > 100000:
        score += 3
    
    return min(score, 100)


PRODUCT_MATRIX = {
    'fnb_beverage': {
        'products': ['Paper Cup Hot 8oz/12oz', 'Cup Cold PET/PP', 'Cup Sleeve Kraft', 'Coaster', 'Buku Menu Meja', 'Stiker Segel Toples'],
        'materials': 'Kraft PE Coating anti-rembes, Sablon presisi 1-4 warna, Ivory 300gsm laminasi doff anti-air',
        'value_prop': 'Desain estetik kekinian, tahan embun es dan panas kopi, menjaga aroma kopi tetap prima.',
    },
    'fnb_food_resto': {
        'products': ['Paper Lunch Box Formed (M/L)', 'Food Pail', 'Wrapping Paper Makanan Custom', 'Paper Bag Takeaway'],
        'materials': 'Brown Kraft / Ivory Food Grade 290gsm, Tinta bersertifikasi FDA',
        'value_prop': 'Kemasan higienis berstandar food-grade, tidak bocor kuah/minyak, branding mewah.',
    },
    'fashion_retail': {
        'products': ['Hangtag Baju Tebal', 'Thank You Card', 'Polymailer Cetak Logo', 'Shopping Bag / Paper Bag Tali Kur'],
        'materials': 'Art Carton 360gsm/400gsm, Laminasi Doff Velvet, Hotprint Foil Emas/Perak, Emboss',
        'value_prop': 'Meningkatkan gengsi pakaian, membuat harga jual baju terlihat layak dihargai mahal.',
    },
    'beauty_skincare': {
        'products': ['Stiker Segel Botol Jar', 'Box Lipat Skincare Kosmetik', 'Brosur Panduan Perawatan Lipat 3'],
        'materials': 'Vinyl Glossy White / Transparan Camel, Duplex/Ivory 310gsm + UV Spot',
        'value_prop': 'Stiker tahan gores dan tidak pudar terkena minyak/cairan kimia serum.',
    },
    'new_store_opening': {
        'products': ['Signage Akrilik Toko', 'Neon Box LED Custom', 'Stiker Kaca One-Way Vision', 'Spanduk Kain Banner Outdoor', 'X/Y-Banner'],
        'materials': 'Flexi Jerman 510gsm, Stiker Ritrama + Laminating UV, Akrilik Marga Cipta 3mm',
        'value_prop': 'Pengerjaan kilat siap sebelum hari pembukaan resmi, warna tajam terbaca jauh.',
    },
    'corporate_legal': {
        'products': ['Map Berkas Folder Dokumen', 'Nota / Surat Jalan NCR 2-4 Ply', 'ID Card PVC + Lanyard', 'Sertifikat'],
        'materials': 'Art Carton 310gsm laminasi satu sisi, Kertas NCR Carbonless, PVC tebal 0.76mm',
        'value_prop': 'Citra formal kredibel, kerapian jilid arsip hukum.',
    },
    'event_service': {
        'products': ['Spanduk Kain Banner Outdoor', 'X/Y-Banner', 'Stiker Kaca One-Way Vision'],
        'materials': 'Flexi Jerman 510gsm outdoor tahan cuaca',
        'value_prop': 'Pengerjaan kilat, warna cetak tajam untuk acara.',
    },
    'general_commercial': {
        'products': ['Paper Bag Custom', 'Stiker Logo', 'Brosur Lipat 3'],
        'materials': 'Art Carton 310gsm, Laminasi Doff',
        'value_prop': 'Branding profesional untuk bisnis Anda.',
    },
}


def infer_product_needs(category: str, business_name: str, biography: str) -> dict:
    data = PRODUCT_MATRIX.get(category, PRODUCT_MATRIX['general_commercial'])
    return {
        'recommended_products': list(data['products']),
        'materials_finishing': data['materials'],
        'value_proposition': data['value_prop'],
    }


def generate_whatsapp_pitch(lead: dict) -> Optional[dict]:
    wa = lead.get('whatsapp_number') or lead.get('phone_number')
    if not wa:
        return None
    digits = ''.join(c for c in str(wa) if c.isdigit())
    if not digits:
        return None
    if not digits.startswith('62'):
        if digits.startswith('0'):
            digits = '62' + digits[1:]
        elif len(digits) >= 9:
            digits = '62' + digits
    name = lead.get('business_name', 'Bapak/Ibu')
    category = lead.get('category', 'general_commercial')
    needs = infer_product_needs(category, name, lead.get('biography', ''))
    products = ', '.join(needs['recommended_products'][:3])
    pitch = (
        f"Halo {name}, kami dari RUANG VISUAL menyediakan cetak {products} "
        f"untuk mendukung branding usaha Anda. {needs['value_proposition']} "
        "Apakah boleh kami kirimkan penawaran harga?"
    )
    import urllib.parse
    link = f"https://wa.me/{digits}?text={urllib.parse.quote(pitch)}"
    return {'pitch_text': pitch, 'wa_link': link}
