import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import urllib.parse
from typing import Optional, Tuple


MOBILE_PREFIXES = {
    '62811', '62812', '62813', '62821', '62822', '62852', '62853',
    '62814', '62815', '62816', '62855', '62856', '62857', '62858',
    '62817', '62818', '62819', '62859', '62877', '62878',
    '62895', '62896', '62897', '62898', '62899',
    '62881', '62882', '62883', '62884', '62885', '62886', '62887', '62888', '62889',
}

# shortcut: kode area PSTN Indonesia tidak ada yang berawalan 08, jadi 0[2-79] aman membedakan telepon kabel dari seluler
PSTN_PATTERNS = [
    r'^0411',
    r'^62411',
    r'^0[2-79]',
]


def is_landline(raw_number: str) -> bool:
    if not raw_number:
        return False
    digits = re.sub(r'[^\d]', '', raw_number)
    return digits.startswith('0411') or digits.startswith('62411')


def normalize_whatsapp(raw_number: str) -> Optional[str]:
    if not raw_number:
        return None

    if is_landline(raw_number):
        return None

    cleaned = re.sub(r'[^\d+]', '', raw_number)

    if cleaned.startswith('+62'):
        cleaned = cleaned[3:]
    elif cleaned.startswith('62'):
        cleaned = cleaned[2:]
    elif cleaned.startswith('08'):
        cleaned = cleaned[1:]
    elif cleaned.startswith('8'):
        pass
    else:
        return None

    if not cleaned.startswith('8'):
        return None

    if not (9 <= len(cleaned) <= 13):
        return None

    return f"62{cleaned}"


def extract_whatsapp_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    m = re.search(r'wa\.me/(\d{7,15})', url)
    if m:
        return normalize_whatsapp(m.group(1))
    decoded = urllib.parse.unquote(url)
    m = re.search(r'(?:phone|wa)=(\d{7,15})', decoded)
    if m:
        return normalize_whatsapp(m.group(1))
    return None


def normalize_address(raw_address: str) -> dict:
    if not raw_address:
        return {
            'address_full': '',
            'district_area': '',
            'city': ''
        }
    
    address_full = ' '.join(raw_address.split())
    address_full = re.sub(r'\d{5}', '', address_full)
    address_full = ' '.join(address_full.split())
    
    city_patterns = [
        r'(?:Kota|Kab\.|Kabupaten)\s+([A-Za-z\s]+)',
        r',\s*([A-Za-z\s]+)$'
    ]
    
    city = ''
    for pattern in city_patterns:
        match = re.search(pattern, address_full, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            break
    
    district_patterns = [
        r'(?:Kelurahan|Kel\.)\s+([A-Za-z\s]+?)(?:,|\s+(?:Kec\.|Kecamatan))',
        r'(?:Kecamatan|Kec\.)\s+([A-Za-z\s]+?)(?:,|$)',
        r',\s*([A-Za-z\s]+),\s*[A-Za-z\s]+$'
    ]
    
    district_area = ''
    for pattern in district_patterns:
        match = re.search(pattern, address_full, re.IGNORECASE)
        if match:
            district_area = match.group(1).strip()
            break
    
    return {
        'address_full': address_full,
        'district_area': district_area,
        'city': city
    }


def validate_whatsapp_number(raw_phone: str) -> Tuple[bool, Optional[str]]:
    if not raw_phone:
        return False, None

    digits = re.sub(r'[^\d]', '', raw_phone)

    if not digits:
        return False, None

    for pattern in PSTN_PATTERNS:
        if re.match(pattern, digits):
            return False, None

    if digits.startswith('62'):
        normalized = digits
    elif digits.startswith('0'):
        normalized = '62' + digits[1:]
    elif digits.startswith('8'):
        normalized = '62' + digits
    else:
        return False, None

    if not (10 <= len(normalized) <= 14):
        return False, None

    if normalized[:5] in MOBILE_PREFIXES:
        return True, normalized

    return False, None

