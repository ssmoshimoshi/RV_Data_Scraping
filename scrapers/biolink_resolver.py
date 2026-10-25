import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from scrapers.normalizer import normalize_whatsapp

SUPPORTED_BIOLINK_DOMAINS = (
    'linktr.ee',
    'desty.page',
    'taplink.cc',
    'beacons.ai',
    'bio.site',
    'biolinky.co',
)

_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

_WA_PATTERNS = (
    re.compile(r'wa\.me/([0-9]+)'),
    re.compile(r'api\.whatsapp\.com/send\?phone=([0-9]+)'),
    re.compile(r'(?:phone|wa)=([0-9]+)'),
)

def is_biolink_url(url: str) -> bool:
    if not url:
        return False
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == d or host.endswith('.' + d) for d in SUPPORTED_BIOLINK_DOMAINS)

def extract_whatsapp_from_html(html_text: str) -> Optional[str]:
    for pattern in _WA_PATTERNS:
        for match in pattern.finditer(html_text or ''):
            wa = normalize_whatsapp(match.group(1))
            if wa:
                return wa
    return None

def resolve_biolink_whatsapp(url: str, timeout: int = 5) -> Optional[str]:
    if not is_biolink_url(url):
        return None
    try:
        request = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, 'status', 200)
            if status != 200:
                return None
            html_text = response.read().decode('utf-8', errors='ignore')
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    return extract_whatsapp_from_html(html_text)

def main():
    parser = argparse.ArgumentParser(description='RUANG VISUAL Biolink Deep-Resolver')
    parser.add_argument('--mode', choices=['resolve'], default='resolve', help='Mode operasi resolver')
    parser.add_argument('--limit', type=int, default=1, help='Jumlah URL maksimal yang diproses')
    parser.add_argument('--url', help='URL biolink yang akan diresolusi')
    parser.add_argument('--dry-run', action='store_true', help='Tampilkan hasil tanpa permintaan jaringan')
    args = parser.parse_args()

    url = args.url or ''
    if args.dry_run:
        print(f"Mode dry-run aktif: URL {url!r} | biolink didukung: {is_biolink_url(url)}")
        print('Tidak ada permintaan jaringan yang dilakukan.')
        return

    wa = resolve_biolink_whatsapp(url)
    print(f"URL: {url}")
    print(f"WhatsApp ternormalisasi: {wa or '-'}")

if __name__ == '__main__':
    main()
