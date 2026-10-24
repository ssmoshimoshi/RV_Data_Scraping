import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re

def extract_packaging_pain_points(reviews: list[dict]) -> list[dict]:
    keywords = ['bocor', 'rembes', 'tumpah', 'robek', 'sobek', 'rusak', 'lembek', 'pecah', 'meleleh', 'bungkus', 'kemasan', 'plastik', 'cup', 'box', 'kotak', 'kantong', 'tutup', 'seal', 'dingin', 'hancur']
    pattern = re.compile('|'.join(keywords), re.IGNORECASE)
    results = []
    for review in reviews:
        text = review.get('text', '')
        found = pattern.findall(text)
        if found:
            unique_found = list(set(found))
            results.append({
                'review_text': text,
                'rating': review.get('rating'),
                'date': review.get('date'),
                'detected_keywords': unique_found,
                'sales_angle': 'RUANG VISUAL menyediakan solusi kemasan presisi dan anti-tumpah sesuai kebutuhan anda.'
            })
    return results
