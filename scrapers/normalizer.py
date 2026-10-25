import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import urllib.parse
from typing import Optional


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
