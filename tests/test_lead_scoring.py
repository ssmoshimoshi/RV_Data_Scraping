import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from datetime import datetime, timedelta
from scrapers.lead_scoring import (
    calculate_score,
    calculate_4_pillars_score,
    qualify_lead,
    classify_category,
    infer_product_needs,
    generate_whatsapp_pitch,
    estimate_packaging_volume_and_value,
    is_non_commercial
)


class TestQualifyLead(unittest.TestCase):
    
    def test_qualify_active_with_contact(self):
        lead = {
            'last_post_date': (datetime.now() - timedelta(days=5)).isoformat(),
            'whatsapp_number': '6281234567890',
            'biography': 'Cafe and resto'
        }
        qualified, reason = qualify_lead(lead)
        self.assertTrue(qualified)
        self.assertEqual(reason, 'Qualified')
    
    def test_disqualify_inactive_over_30_days(self):
        lead = {
            'last_post_date': (datetime.now() - timedelta(days=35)).isoformat(),
            'whatsapp_number': '6281234567890'
        }
        qualified, reason = qualify_lead(lead)
        self.assertFalse(qualified)
        self.assertIn('Inactive', reason)
    
    def test_disqualify_no_contact(self):
        lead = {
            'last_post_date': (datetime.now() - timedelta(days=5)).isoformat(),
            'biography': 'Coffee shop'
        }
        qualified, reason = qualify_lead(lead)
        self.assertFalse(qualified)
        self.assertIn('No contact', reason)
    
    def test_disqualify_non_commercial(self):
        lead = {
            'last_post_date': (datetime.now() - timedelta(days=5)).isoformat(),
            'whatsapp_number': '6281234567890',
            'biography': 'This is my personal diary'
        }
        qualified, reason = qualify_lead(lead)
        self.assertFalse(qualified)
        self.assertIn('Non-commercial', reason)


class TestCalculateScore(unittest.TestCase):
    
    def test_score_with_whatsapp(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=2)).isoformat(),
            'latitude': -6.9175,
            'longitude': 107.6191,
            'is_ad_active': True,
            'followers_count': 5000
        }
        score = calculate_score(lead)
        self.assertEqual(score, 100)
    
    def test_score_with_phone_only(self):
        lead = {
            'phone_number': '021-12345678',
            'last_post_date': (datetime.now() - timedelta(days=2)).isoformat()
        }
        score = calculate_score(lead)
        self.assertEqual(score, 40)
    
    def test_score_with_email_only(self):
        lead = {
            'email': 'info@example.com',
            'last_post_date': (datetime.now() - timedelta(days=2)).isoformat()
        }
        score = calculate_score(lead)
        self.assertEqual(score, 30)
    
    def test_score_keaktifan_3_days(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=3)).isoformat()
        }
        score = calculate_score(lead)
        self.assertGreaterEqual(score, 55)
    
    def test_score_keaktifan_7_days(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=7)).isoformat()
        }
        score = calculate_score(lead)
        self.assertGreaterEqual(score, 50)
    
    def test_score_keaktifan_14_days(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=14)).isoformat()
        }
        score = calculate_score(lead)
        self.assertGreaterEqual(score, 45)
    
    def test_score_keaktifan_30_days(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=30)).isoformat()
        }
        score = calculate_score(lead)
        self.assertGreaterEqual(score, 40)
    
    def test_score_keaktifan_over_30_days_zero(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=35)).isoformat()
        }
        score = calculate_score(lead)
        self.assertEqual(score, 30)
    
    def test_score_lokasi_with_coordinates(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'latitude': -6.9175,
            'longitude': 107.6191
        }
        score = calculate_score(lead)
        self.assertEqual(score, 50)
    
    def test_score_lokasi_address_only(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'address_full': 'Jl. Sudirman No. 123',
            'city': 'Bandung'
        }
        score = calculate_score(lead)
        self.assertEqual(score, 40)
    
    def test_score_anggaran_ad_active(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'is_ad_active': True
        }
        score = calculate_score(lead)
        self.assertEqual(score, 45)
    
    def test_score_anggaran_paid_domain(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'external_website_url': 'https://cafekopi.com'
        }
        score = calculate_score(lead)
        self.assertEqual(score, 40)
    
    def test_score_anggaran_free_domain_excluded(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'external_website_url': 'https://linktr.ee/cafekopi'
        }
        score = calculate_score(lead)
        self.assertEqual(score, 30)
    
    def test_score_skala_sweet_spot(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'followers_count': 5000
        }
        score = calculate_score(lead)
        self.assertEqual(score, 40)
    
    def test_score_skala_small(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'followers_count': 750
        }
        score = calculate_score(lead)
        self.assertEqual(score, 35)
    
    def test_score_skala_mega(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'followers_count': 150000
        }
        score = calculate_score(lead)
        self.assertEqual(score, 33)
    
    def test_score_cap_at_100(self):
        lead = {
            'whatsapp_number': '6281234567890',
            'last_post_date': (datetime.now() - timedelta(days=1)).isoformat(),
            'latitude': -6.9175,
            'longitude': 107.6191,
            'is_ad_active': True,
            'followers_count': 10000,
            'address_full': 'Jl. Sudirman',
            'city': 'Jakarta'
        }
        score = calculate_score(lead)
        self.assertEqual(score, 100)


class TestClassifyCategory(unittest.TestCase):
    
    def test_classify_fnb_beverage(self):
        category = classify_category('Kopi Kenangan', 'Best coffee in town', ['New menu drink'])
        self.assertEqual(category, 'fnb_beverage')
    
    def test_classify_fnb_food(self):
        category = classify_category('Resto Sedap', 'Restaurant & catering', ['Menu spesial'])
        self.assertEqual(category, 'fnb_food_resto')
    
    def test_classify_fashion(self):
        category = classify_category('Fashion Store', 'Baju dan hijab modern', [])
        self.assertEqual(category, 'fashion_retail')
    
    def test_classify_beauty(self):
        category = classify_category('Beauty Clinic', 'Skincare and makeup', [])
        self.assertEqual(category, 'beauty_skincare')
    
    def test_classify_general_no_match(self):
        category = classify_category('Unknown Business', 'No specific keywords', [])
        self.assertEqual(category, 'general_commercial')


class TestInferProductNeeds(unittest.TestCase):

    def test_fnb_beverage(self):
        res = infer_product_needs('fnb_beverage', 'Kopi Kenangan', 'best coffee')
        self.assertIn('Paper Cup Hot 8oz/12oz', res['recommended_products'])
        self.assertTrue(res['materials_finishing'])
        self.assertTrue(res['value_proposition'])

    def test_unknown_defaults_general(self):
        res = infer_product_needs('nope', 'X', 'y')
        self.assertIn('Cetak Stiker Vinyl A3+ (Kiss Cut/Die Cut)', res['recommended_products'])

    def test_local_keywords_classification(self):
        self.assertEqual(classify_category('Ayam Geprek Beraasa', '', []), 'fnb_food_resto')
        self.assertEqual(classify_category('GEPREK GOLD CHICK', '', []), 'fnb_food_resto')
        self.assertEqual(classify_category('Sop Konro Bawakaraeng', '', []), 'fnb_food_resto')
        self.assertEqual(classify_category('Butik eLeS Makassar Official', '', []), 'fashion_retail')
        self.assertEqual(classify_category('Shafira Boulevard Makassar', 'butik muslim', []), 'fashion_retail')

    def test_non_commercial_filtering(self):
        self.assertTrue(is_non_commercial('SPPG KEC MARISO', ''))
        self.assertTrue(is_non_commercial('Kantor Lurah Masale', ''))
        self.assertTrue(is_non_commercial('Dinas Pendidikan Kota Makassar', ''))
        self.assertFalse(is_non_commercial('Kantor Notaris Hj. Siti', ''))
        self.assertFalse(is_non_commercial('Ayam Geprek Beraasa', ''))

    def test_no_emoji(self):
        res = infer_product_needs('fashion_retail', 'Butik', 'baju')
        for v in res.values():
            self.assertNotIn('emoji', str(v).lower())


class TestGenerateWhatsAppPitch(unittest.TestCase):

    def test_with_wa(self):
        lead = {'business_name': 'Kopi A', 'whatsapp_number': '628123', 'category': 'fnb_beverage'}
        res = generate_whatsapp_pitch(lead)
        self.assertIsNotNone(res)
        self.assertIn('pitch_text', res)
        self.assertIn('wa_link', res)
        self.assertTrue(res['wa_link'].startswith('https://wa.me/628123'))

    def test_without_wa_returns_none(self):
        lead = {'business_name': 'Kopi A', 'category': 'fnb_beverage'}
        self.assertIsNone(generate_whatsapp_pitch(lead))

    def test_normalize_zero_prefix(self):
        lead = {'business_name': 'X', 'whatsapp_number': '08123', 'category': 'general_commercial'}
        res = generate_whatsapp_pitch(lead)
        self.assertTrue(res['wa_link'].startswith('https://wa.me/628123'))


class TestCalculate4PillarsScore(unittest.TestCase):

    def test_full_scoring_fnb(self):
        lead = {
            'business_name': 'Kopi Janji',
            'category': 'fnb_beverage',
            'google_maps_place_id': 'place_123',
            'address_full': 'Jl. Veteran No. 10, Makassar',
            'rating': 4.7,
            'last_post_date': (datetime.now() - timedelta(days=2)).isoformat(),
            'is_ad_active': True,
        }
        res = calculate_4_pillars_score(lead)
        self.assertEqual(res['score_legitimacy'], 25)
        self.assertEqual(res['score_velocity'], 25)
        self.assertEqual(res['score_turnover'], 30)
        self.assertEqual(res['score_budget'], 20)
        self.assertEqual(res['score_total'], 100)
        self.assertIn('Kekuatan utama:', res['reason_summary'])
        self.assertIn('memiliki fisik terverifikasi', res['reason_summary'])

    def test_turnover_by_category(self):
        categories_expected = {
            'fnb_beverage': 30,
            'fnb_food_resto': 30,
            'fashion_retail': 30,
            'beauty_skincare': 30,
            'event_service': 25,
            'new_store_opening': 25,
            'corporate_legal': 20,
            'general_commercial': 15,
        }
        for cat, expected in categories_expected.items():
            lead = {'category': cat}
            res = calculate_4_pillars_score(lead)
            self.assertEqual(res['score_turnover'], expected)

    def test_budget_scoring_paid_website(self):
        lead = {'external_website_url': 'https://kopibintang.co.id'}
        res = calculate_4_pillars_score(lead)
        self.assertEqual(res['score_budget'], 10)

    def test_budget_scoring_free_website(self):
        lead = {'external_website_url': 'https://linktr.ee/kopibintang'}
        res = calculate_4_pillars_score(lead)
        self.assertEqual(res['score_budget'], 0)


class TestEstimatePackagingVolumeAndValue(unittest.TestCase):

    def test_estimate_fnb_beverage(self):
        lead = {'category': 'fnb_beverage', 'followers_count': 2000}
        res = estimate_packaging_volume_and_value(lead)
        self.assertEqual(res['restock_cycle_days'], 30)
        self.assertGreaterEqual(res['est_monthly_units_min'], 1500)
        self.assertLessEqual(res['est_monthly_value_max_idr'], 5400000)
        self.assertEqual(res['priority_commercial_tier'], 'Tier 1 (High Value)')

    def test_estimate_general_fallback(self):
        lead = {'category': 'unknown', 'followers_count': 100}
        res = estimate_packaging_volume_and_value(lead)
        self.assertEqual(res['priority_commercial_tier'], 'Tier 3 (Standard)')
        self.assertEqual(res['restock_cycle_days'], 30)


if __name__ == '__main__':
    unittest.main()
