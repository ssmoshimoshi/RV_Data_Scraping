import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from scrapers.pain_points import extract_packaging_pain_points

class TestPainPoints(unittest.TestCase):
    def test_extract_packaging_pain_points(self):
        reviews = [
            {'text': 'Kopi enak tapi tutupnya bocor dan tumpah semua.', 'rating': 2},
            {'text': 'Makanan lezat, tempat bersih.', 'rating': 5},
            {'text': 'Kemasan plastik pecah, bungkus rusak.', 'rating': 1}
        ]
        result = extract_packaging_pain_points(reviews)
        self.assertEqual(len(result), 2)
        self.assertIn('bocor', result[0]['detected_keywords'])
        self.assertIn('tumpah', result[0]['detected_keywords'])
        self.assertIn('pecah', result[1]['detected_keywords'])
        self.assertIn('bungkus', result[1]['detected_keywords'])
        self.assertTrue('sales_angle' in result[0])

if __name__ == '__main__':
    unittest.main()
