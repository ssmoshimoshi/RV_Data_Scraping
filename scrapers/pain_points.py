import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re

def extract_packaging_pain_points(reviews: list) -> list[dict]:
    keywords = ['bocor', 'rembes', 'tumpah', 'robek', 'sobek', 'rusak', 'lembek', 'pecah', 'meleleh', 'bungkus', 'kemasan', 'plastik', 'cup', 'box', 'kotak', 'kantong', 'tutup', 'seal', 'dingin', 'hancur']
    pattern = re.compile('|'.join(keywords), re.IGNORECASE)
    results = []
    for review in reviews or []:
        if isinstance(review, str):
            text = review
            rating = None
            date = None
        elif isinstance(review, dict):
            text = review.get('text') or review.get('textTranslated') or review.get('comment', '')
            rating = review.get('rating') if review.get('rating') is not None else review.get('stars')
            date = review.get('date') or review.get('publishedAtDate')
        else:
            continue

        if not text:
            continue

        found = pattern.findall(text)
        if found:
            unique_found = sorted(list(set(k.lower() for k in found)))
            results.append({
                'review_text': text,
                'rating': rating,
                'date': date,
                'detected_keywords': unique_found,
                'sales_angle': 'RUANG VISUAL menyediakan solusi kemasan presisi dan anti-tumpah sesuai kebutuhan anda.'
            })
    return results

