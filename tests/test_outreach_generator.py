import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import unittest
from scrapers.outreach_generator import generate_whatsapp_pitch, generate_whatsapp_click_url, recommended_products

EMOJI_PATTERN = re.compile(
    r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2B00-\u2BFF\uFE0F]'
)


class TestGenerateWhatsappPitch(unittest.TestCase):

    def test_fnb_pitch_contains_name_and_district(self):
        dossier = {
            'business_name': 'Warung Coto Daeng',
            'city': 'Makassar',
            'district_area': 'Panakkukang',
            'category': 'fnb_food_resto',
        }
        pitch = generate_whatsapp_pitch(dossier)
        self.assertIn('Warung Coto Daeng', pitch)
        self.assertIn('Panakkukang', pitch)
        self.assertIn('sampel', pitch)
        self.assertIn('outlet', pitch)

    def test_fashion_pitch_contains_polymailer(self):
        dossier = {
            'business_name': 'Butik Anaya',
            'district_area': 'Rappocini',
            'category': 'fashion_boutique',
        }
        pitch = generate_whatsapp_pitch(dossier)
        self.assertIn('Butik Anaya', pitch)
        self.assertIn('Rappocini', pitch)
        self.assertIn('polymailer', pitch)
        self.assertIn('hangtag', pitch)

    def test_skincare_pitch_contains_stiker(self):
        dossier = {
            'business_name': 'Klinik Cantik Makassar',
            'district_area': 'Tamalanrea',
            'category': 'skincare_clinic',
        }
        pitch = generate_whatsapp_pitch(dossier)
        self.assertIn('Klinik Cantik Makassar', pitch)
        self.assertIn('stiker', pitch)
        self.assertIn('klinik', pitch)

    def test_beauty_skincare_category_recognized(self):
        dossier = {
            'business_name': 'Aura Glow Skincare',
            'district_area': 'Panakkukang',
            'category': 'beauty_skincare',
        }
        pitch = generate_whatsapp_pitch(dossier)
        self.assertIn('Aura Glow Skincare', pitch)
        self.assertIn('stiker', pitch)
        products = recommended_products(dossier)
        self.assertIn('Stiker Segel Tahan Air', products)

    def test_pitch_is_short(self):
        dossier = {
            'business_name': 'Squid Coffee',
            'district_area': 'Panakkukang',
            'category': 'fnb_beverage',
        }
        pitch = generate_whatsapp_pitch(dossier)
        self.assertLess(len(pitch), 600)

    def test_no_emoji_in_pitch(self):
        for category, name in [
            ('fnb_food_resto', 'Toko A'),
            ('fashion_boutique', 'Toko B'),
            ('skincare_clinic', 'Toko C'),
        ]:
            pitch = generate_whatsapp_pitch({
                'business_name': name, 'category': category, 'district_area': 'Panakkukang'
            })
            self.assertIsNone(EMOJI_PATTERN.search(pitch), f"Emoji di pitch: {pitch}")

    def test_fallback_to_fnb_for_unknown_category(self):
        dossier = {
            'business_name': 'Toko XYZ',
            'district_area': 'Mariso',
            'category': 'unknown_sector',
        }
        pitch = generate_whatsapp_pitch(dossier)
        self.assertIn('sampel', pitch)


class TestGenerateWhatsappClickUrl(unittest.TestCase):

    def test_valid_phone_produces_wa_me_url(self):
        url = generate_whatsapp_click_url('6281234567890', 'Halo Kak')
        self.assertTrue(url.startswith('https://wa.me/6281234567890'))
        self.assertIn('text=', url)

    def test_pitch_is_url_encoded(self):
        url = generate_whatsapp_click_url('6281234567890', 'Halo Kak Test')
        self.assertNotIn(' ', url)

    def test_empty_phone_returns_empty_string(self):
        url = generate_whatsapp_click_url('', 'Halo')
        self.assertEqual(url, '')

    def test_none_phone_returns_empty_string(self):
        url = generate_whatsapp_click_url(None, 'Halo')
        self.assertEqual(url, '')


class TestRecommendedProducts(unittest.TestCase):

    def test_fnb_products(self):
        result = recommended_products({'category': 'fnb_food_resto'})
        self.assertIn('Paper Cup', result)

    def test_fashion_products(self):
        result = recommended_products({'category': 'fashion_boutique'})
        self.assertIn('Polymailer', result)

    def test_skincare_products(self):
        result = recommended_products({'category': 'skincare_clinic'})
        self.assertIn('Stiker', result)


if __name__ == '__main__':
    unittest.main()
