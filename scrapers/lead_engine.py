import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from scrapers.normalizer import normalize_whatsapp

DB_PATH = PROJECT_ROOT / 'data' / 'leads.sqlite'

TARGET_SECTORS = {
    'fnb': 30,
    'klinik_salon': 30,
    'retail_fashion': 30,
    'event_eo': 20,
    'kantor_notaris': 20
}

CATEGORY_RULES = {
    'fnb': r'(kopi|coffee|cafe|kafe|resto|restaurant|kuliner|food|makan|catering|bakery|cake|minuman|drink|juice|tea|boba)',
    'klinik_salon': r'(klinik|clinic|salon|beauty|spa|kecantikan|skincare|facial|perawatan)',
    'retail_fashion': r'(fashion|clothing|baju|pakaian|butik|boutique|hijab|gamis)',
    'event_eo': r'(event|organizer|eo|wedding|nikah|acara|dekor|decoration|photography|photo|studio)',
    'kantor_notaris': r'(notaris|ppat|konsultan|law|hukum|legal)'
}

PRINT_NEED_RULES = {
    'menu': {
        'triggers': r'(menu baru|varian baru|launching|launching product|new menu|produk baru)',
        'products': ['Buku menu', 'Tent card meja', 'Standing banner', 'X-banner', 'Poster dinding']
    },
    'packaging': {
        'triggers': r'(takeaway|take away|packaging|kemasan|botol|cup|paper bag|box|dus)',
        'products': ['Stiker label vinyl anti air', 'Box kardus custom', 'Paper bag sablon', 'Cup sleeve', 'Greaseproof paper']
    },
    'promo': {
        'triggers': r'(promo|diskon|discount|voucher|sale|special price|flash sale)',
        'products': ['Flyer promosi', 'Voucher fisik bernomor seri', 'Poster A3 promo', 'Stiker diskon']
    },
    'event': {
        'triggers': r'(event|live music|workshop|bazaar|grand opening|soft opening|festival|bazar)',
        'products': ['Backdrop panggung', 'Tiket gelang', 'Spanduk rentang', 'Standing banner outdoor', 'ID card peserta']
    },
    'membership': {
        'triggers': r'(member|membership|loyalty|seragam|uniform|staff|karyawan)',
        'products': ['Kartu member PVC', 'Seragam sablon', 'Nota kwitansi', 'ID card karyawan', 'Name tag']
    }
}

BIO_COMMERCIAL_REGEX = re.compile(
    r'(wa|whatsapp|order via|cs:|kontak|admin|official|store|shop|boutique|cafe|resto|bengkel|'
    r'studio|clinic|salon|kue|catering|open order|open po|pengiriman|katalog|pricelist|price list)',
    re.IGNORECASE
)


def calculate_lead_score(lead: Dict) -> int:
    score = 0
    
    wa_valid = normalize_whatsapp(lead.get('phone', '')) is not None
    has_website = bool(lead.get('website'))
    
    if wa_valid:
        score += 15
    if has_website:
        score += 15
    
    reviews = lead.get('reviews_count', 0)
    rating = lead.get('rating', 0.0)
    has_hours = bool(lead.get('opening_hours'))
    
    if reviews >= 50:
        score += 20
    elif reviews > 0:
        score += int((reviews / 50) * 20)
    if 4.0 <= rating < 5.0:
        score += 10
    if has_hours:
        score += 10
    
    category_lower = (lead.get('category') or '').lower()
    matched_sector = None
    
    priority_order = ['fnb', 'klinik_salon', 'retail_fashion', 'event_eo', 'kantor_notaris']
    for sector in priority_order:
        if re.search(CATEGORY_RULES[sector], category_lower, re.IGNORECASE):
            matched_sector = sector
            break
    
    if matched_sector in ['fnb', 'klinik_salon', 'retail_fashion']:
        score += 30
    elif matched_sector in ['event_eo', 'kantor_notaris']:
        score += 20
    else:
        score += 10
    
    return min(score, 100)


def generate_lead_id(conn: sqlite3.Connection) -> str:
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(CAST(SUBSTR(lead_id, 4) AS INTEGER)) FROM leads")
    row = cursor.fetchone()
    last_num = row[0] if row and row[0] else 0
    return f"LD-{last_num + 1:04d}"


def analyze_post_needs(posts: List[Dict]) -> List[str]:
    recommendations = []
    seen_categories = set()
    
    for post in posts[:5]:
        raw_tags = post.get('hashtags') or []
        caption = (post.get('caption') or '') + ' ' + ' '.join(raw_tags)
        caption_lower = caption.lower()
        
        for need_cat, rules in PRINT_NEED_RULES.items():
            if need_cat in seen_categories:
                continue
            if re.search(rules['triggers'], caption_lower, re.IGNORECASE):
                recommendations.extend(rules['products'])
                seen_categories.add(need_cat)
    
    return list(dict.fromkeys(recommendations))


def filter_business_accounts(accounts: List[Dict]) -> List[Dict]:
    filtered = []
    for acc in accounts:
        is_biz_type = acc.get('account_type') in ['Business', 'Creator']
        bio = acc.get('bio') or ''
        has_commercial_bio = BIO_COMMERCIAL_REGEX.search(bio) is not None
        
        if is_biz_type or has_commercial_bio:
            filtered.append(acc)
    
    return filtered


def save_lead_to_db(lead: Dict, dry_run: bool = False) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            lead_id TEXT PRIMARY KEY,
            business_name TEXT NOT NULL,
            category TEXT,
            sector TEXT,
            phone TEXT,
            whatsapp TEXT,
            website TEXT,
            address TEXT,
            rating REAL,
            reviews_count INTEGER,
            opening_hours TEXT,
            score INTEGER,
            instagram_handle TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    lead_id = generate_lead_id(conn)
    
    if not dry_run:
        cursor.execute("""
            INSERT INTO leads (lead_id, business_name, category, sector, phone, whatsapp, 
                               website, address, rating, reviews_count, opening_hours, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_id,
            lead['business_name'],
            lead.get('category'),
            lead.get('sector'),
            lead.get('phone'),
            normalize_whatsapp(lead.get('phone', '')),
            lead.get('website'),
            lead.get('address'),
            lead.get('rating', 0.0),
            lead.get('reviews_count', 0),
            lead.get('opening_hours'),
            lead.get('score', 0)
        ))
        conn.commit()
    
    conn.close()
    return lead_id


def get_top_daily_leads(limit: int = 10) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM leads 
        WHERE DATE(created_at) = DATE('now')
        ORDER BY score DESC, rating DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_lead_field(lead_id: str, field: str, value: str) -> bool:
    field_aliases = {
        'nama': 'business_name',
        'name': 'business_name',
        'alamat': 'address',
        'telepon': 'phone',
        'telp': 'phone',
        'wa': 'whatsapp'
    }
    normalized_field = field_aliases.get(field.lower(), field.lower())
    
    allowed_fields = ['business_name', 'phone', 'whatsapp', 'address', 'website']
    if normalized_field not in allowed_fields:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"""
        UPDATE leads 
        SET {normalized_field} = ?, updated_at = CURRENT_TIMESTAMP
        WHERE lead_id = ?
    """, (value, lead_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def drop_lead(lead_id: str, reason: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE leads 
        SET status = 'dropped', updated_at = CURRENT_TIMESTAMP
        WHERE lead_id = ?
    """, (lead_id,))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def link_instagram_to_lead(lead_id: str, instagram_handle: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE leads 
        SET instagram_handle = ?, updated_at = CURRENT_TIMESTAMP
        WHERE lead_id = ?
    """, (instagram_handle, lead_id))
    
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return success


def get_lead_by_id(lead_id: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Lead Engine RUANG VISUAL')
    parser.add_argument('--mode', choices=['score', 'analyze', 'filter'], default='score')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    
    if args.mode == 'score':
        test_lead = {
            'business_name': 'Kopi Kenangan Panakkukang',
            'category': 'Cafe & Coffee Shop',
            'phone': '082394567890',
            'website': 'https://kopikenangan.com',
            'rating': 4.5,
            'reviews_count': 120,
            'opening_hours': '08:00-22:00'
        }
        score = calculate_lead_score(test_lead)
        print(f"Score: {score}")
        
        if not args.dry_run:
            test_lead['score'] = score
            lead_id = save_lead_to_db(test_lead, dry_run=False)
            print(f"Lead ID: {lead_id}")
        else:
            print("Dry run mode - tidak menyimpan ke database")
    
    elif args.mode == 'analyze':
        test_posts = [
            {'caption': 'Menu baru kami! Coba varian kopi terbaru', 'hashtags': ['#menubaru', '#kopi']},
            {'caption': 'Promo spesial diskon 50% untuk member setia', 'hashtags': ['#promo', '#diskon']}
        ]
        needs = analyze_post_needs(test_posts)
        print(f"Rekomendasi: {needs}")
    
    elif args.mode == 'filter':
        test_accounts = [
            {'username': 'john_personal', 'account_type': 'Personal', 'bio': 'Just a regular guy'},
            {'username': 'cafe_kita', 'account_type': 'Business', 'bio': 'Official account, order via WA'},
            {'username': 'jane_doe', 'account_type': 'Personal', 'bio': 'Owner @butik_cantik, CS: 0812345'}
        ]
        filtered = filter_business_accounts(test_accounts)
        print(f"Filtered: {[a['username'] for a in filtered]}")
