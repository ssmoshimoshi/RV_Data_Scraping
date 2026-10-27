import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import sqlite3
import tempfile
from scrapers import lead_engine


class TestLeadScoring(unittest.TestCase):
    
    def test_calculate_lead_score_high(self):
        lead = {
            'business_name': 'Kopi Kenangan',
            'category': 'Cafe & Coffee Shop',
            'phone': '082394567890',
            'website': 'https://kopikenangan.com',
            'rating': 4.5,
            'reviews_count': 120,
            'opening_hours': '08:00-22:00'
        }
        score = lead_engine.calculate_lead_score(lead)
        self.assertGreaterEqual(score, 70)
        self.assertLessEqual(score, 100)
    
    def test_calculate_lead_score_low(self):
        lead = {
            'business_name': 'Toko Kecil',
            'category': 'Unknown',
            'phone': '041123456',
            'website': '',
            'rating': 0.0,
            'reviews_count': 0,
            'opening_hours': ''
        }
        score = lead_engine.calculate_lead_score(lead)
        self.assertLess(score, 70)
    
    def test_calculate_lead_score_proportional_reviews(self):
        lead_25_reviews = {
            'business_name': 'Cafe Test',
            'category': 'Coffee Shop',
            'phone': '082111111111',
            'website': '',
            'rating': 4.2,
            'reviews_count': 25,
            'opening_hours': '09:00-21:00'
        }
        score = lead_engine.calculate_lead_score(lead_25_reviews)
        self.assertGreaterEqual(score, 65)
        
        lead_10_reviews = {
            'business_name': 'Cafe Test',
            'category': 'Coffee Shop',
            'phone': '082111111111',
            'website': '',
            'rating': 4.2,
            'reviews_count': 10,
            'opening_hours': '09:00-21:00'
        }
        score_10 = lead_engine.calculate_lead_score(lead_10_reviews)
        
        self.assertGreater(score, score_10)
    
    def test_calculate_lead_score_fnb_boost(self):
        lead_fnb = {
            'business_name': 'Kopi Test',
            'category': 'Coffee Shop',
            'phone': '082111111111',
            'website': '',
            'rating': 4.2,
            'reviews_count': 40,
            'opening_hours': '10:00-22:00'
        }
        score_fnb = lead_engine.calculate_lead_score(lead_fnb)
        
        lead_other = {
            'business_name': 'Toko Test',
            'category': 'Hardware Store',
            'phone': '082111111111',
            'website': '',
            'rating': 4.2,
            'reviews_count': 40,
            'opening_hours': '10:00-22:00'
        }
        score_other = lead_engine.calculate_lead_score(lead_other)
        
        self.assertGreater(score_fnb, score_other)


class TestPrintNeedAnalysis(unittest.TestCase):
    
    def test_analyze_post_needs_menu(self):
        posts = [
            {
                'caption': 'Menu baru kami launching hari ini!',
                'hashtags': ['#menubaru', '#launching']
            }
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertTrue(any('menu' in n.lower() or 'banner' in n.lower() for n in needs))
    
    def test_analyze_post_needs_packaging(self):
        posts = [
            {
                'caption': 'Sekarang tersedia takeaway dengan packaging baru',
                'hashtags': ['#takeaway', '#packaging']
            }
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertTrue(any('stiker' in n.lower() or 'box' in n.lower() or 'bag' in n.lower() for n in needs))
    
    def test_analyze_post_needs_promo(self):
        posts = [
            {
                'caption': 'Promo diskon 50% untuk semua menu!',
                'hashtags': ['#promo', '#diskon']
            }
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertTrue(any('flyer' in n.lower() or 'voucher' in n.lower() for n in needs))
    
    def test_analyze_post_needs_event(self):
        posts = [
            {
                'caption': 'Live music event this weekend!',
                'hashtags': ['#event', '#livemusic']
            }
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertTrue(any('backdrop' in n.lower() or 'spanduk' in n.lower() or 'banner' in n.lower() for n in needs))
    
    def test_analyze_post_needs_membership(self):
        posts = [
            {
                'caption': 'Daftar member sekarang dan dapatkan benefit eksklusif',
                'hashtags': ['#member', '#loyalty']
            }
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertTrue(any('kartu' in n.lower() or 'member' in n.lower() for n in needs))
    
    def test_analyze_post_needs_multiple_categories(self):
        posts = [
            {'caption': 'Menu baru launching', 'hashtags': []},
            {'caption': 'Promo diskon hari ini', 'hashtags': []},
            {'caption': 'Event weekend', 'hashtags': []},
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertGreater(len(needs), 3)
    
    def test_analyze_post_needs_no_match(self):
        posts = [
            {'caption': 'Just a regular post', 'hashtags': ['#random']}
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertEqual(len(needs), 0)
    
    def test_analyze_post_needs_none_hashtags(self):
        posts = [
            {'caption': None, 'hashtags': None},
            {'caption': 'Menu baru launching', 'hashtags': None}
        ]
        needs = lead_engine.analyze_post_needs(posts)
        self.assertTrue(any('menu' in n.lower() or 'banner' in n.lower() for n in needs))


class TestBusinessAccountFilter(unittest.TestCase):
    
    def test_filter_business_accounts_by_type(self):
        accounts = [
            {'username': 'biz_account', 'account_type': 'Business', 'bio': 'Regular text'},
            {'username': 'creator_account', 'account_type': 'Creator', 'bio': 'Content creator'},
            {'username': 'personal_account', 'account_type': 'Personal', 'bio': 'Just me'}
        ]
        filtered = lead_engine.filter_business_accounts(accounts)
        self.assertEqual(len(filtered), 2)
        usernames = [a['username'] for a in filtered]
        self.assertIn('biz_account', usernames)
        self.assertIn('creator_account', usernames)
    
    def test_filter_business_accounts_by_bio(self):
        accounts = [
            {'username': 'shop_owner', 'account_type': 'Personal', 'bio': 'Owner @myshop, order via WA 08123'},
            {'username': 'regular_person', 'account_type': 'Personal', 'bio': 'Travel enthusiast'},
            {'username': 'cafe_admin', 'account_type': 'Personal', 'bio': 'Admin @mycafe, kontak CS untuk order'}
        ]
        filtered = lead_engine.filter_business_accounts(accounts)
        self.assertEqual(len(filtered), 2)
        usernames = [a['username'] for a in filtered]
        self.assertIn('shop_owner', usernames)
        self.assertIn('cafe_admin', usernames)
    
    def test_filter_business_accounts_mixed(self):
        accounts = [
            {'username': 'biz1', 'account_type': 'Business', 'bio': 'Official store'},
            {'username': 'personal_with_biz_bio', 'account_type': 'Personal', 'bio': 'Open order, katalog lengkap'},
            {'username': 'pure_personal', 'account_type': 'Personal', 'bio': 'Living my best life'},
            {'username': 'creator1', 'account_type': 'Creator', 'bio': 'Influencer'}
        ]
        filtered = lead_engine.filter_business_accounts(accounts)
        self.assertEqual(len(filtered), 3)
    
    def test_filter_business_accounts_none_bio(self):
        accounts = [
            {'username': 'biz_with_none_bio', 'account_type': 'Business', 'bio': None},
            {'username': 'personal_none_bio', 'account_type': 'Personal', 'bio': None},
            {'username': 'personal_with_commercial', 'account_type': 'Personal', 'bio': 'Order via WA'}
        ]
        filtered = lead_engine.filter_business_accounts(accounts)
        self.assertEqual(len(filtered), 2)
        usernames = [a['username'] for a in filtered]
        self.assertIn('biz_with_none_bio', usernames)
        self.assertIn('personal_with_commercial', usernames)


class TestDatabaseOperations(unittest.TestCase):
    
    def setUp(self):
        self.original_db = lead_engine.DB_PATH
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        lead_engine.DB_PATH = Path(self.temp_db.name)
    
    def tearDown(self):
        lead_engine.DB_PATH = self.original_db
        try:
            Path(self.temp_db.name).unlink()
        except:
            pass
    
    def test_save_and_retrieve_lead(self):
        lead = {
            'business_name': 'Test Cafe',
            'category': 'Coffee Shop',
            'sector': 'fnb',
            'phone': '082123456789',
            'website': 'https://test.com',
            'rating': 4.5,
            'reviews_count': 100,
            'opening_hours': '09:00-21:00',
            'score': 85
        }
        lead_id = lead_engine.save_lead_to_db(lead, dry_run=False)
        self.assertTrue(lead_id.startswith('LD-'))
        
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['business_name'], 'Test Cafe')
        self.assertEqual(retrieved['score'], 85)
    
    def test_update_lead_field(self):
        lead = {
            'business_name': 'Test Restaurant',
            'category': 'Restaurant',
            'sector': 'fnb',
            'phone': '082111111111',
            'score': 70
        }
        lead_id = lead_engine.save_lead_to_db(lead, dry_run=False)
        
        success = lead_engine.update_lead_field(lead_id, 'phone', '082999999999')
        self.assertTrue(success)
        
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['phone'], '082999999999')
    
    def test_update_lead_field_with_alias(self):
        lead = {
            'business_name': 'Test Cafe',
            'category': 'Coffee Shop',
            'sector': 'fnb',
            'phone': '082111111111',
            'address': 'Jl. Lama 123',
            'score': 75
        }
        lead_id = lead_engine.save_lead_to_db(lead, dry_run=False)
        
        success_nama = lead_engine.update_lead_field(lead_id, 'nama', 'Kopi Baru')
        self.assertTrue(success_nama)
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['business_name'], 'Kopi Baru')
        
        success_alamat = lead_engine.update_lead_field(lead_id, 'alamat', 'Jl. Baru 456')
        self.assertTrue(success_alamat)
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['address'], 'Jl. Baru 456')
        
        success_telepon = lead_engine.update_lead_field(lead_id, 'telepon', '082333333333')
        self.assertTrue(success_telepon)
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['phone'], '082333333333')
        
        success_wa = lead_engine.update_lead_field(lead_id, 'wa', '62812345678')
        self.assertTrue(success_wa)
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['whatsapp'], '62812345678')
    
    def test_link_instagram_to_lead(self):
        lead = {
            'business_name': 'Test Salon',
            'category': 'Beauty Salon',
            'sector': 'klinik_salon',
            'score': 75
        }
        lead_id = lead_engine.save_lead_to_db(lead, dry_run=False)
        
        success = lead_engine.link_instagram_to_lead(lead_id, 'testsalon.ig')
        self.assertTrue(success)
        
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['instagram_handle'], 'testsalon.ig')
    
    def test_drop_lead(self):
        lead = {
            'business_name': 'Test Shop',
            'category': 'Retail',
            'sector': 'retail_fashion',
            'score': 65
        }
        lead_id = lead_engine.save_lead_to_db(lead, dry_run=False)
        
        success = lead_engine.drop_lead(lead_id, 'bukan target pasar')
        self.assertTrue(success)
        
        retrieved = lead_engine.get_lead_by_id(lead_id)
        self.assertEqual(retrieved['status'], 'dropped')
    
    def test_generate_sequential_lead_ids(self):
        leads_data = [
            {'business_name': f'Test Business {i}', 'category': 'Test', 'score': 70}
            for i in range(3)
        ]
        
        ids = []
        for lead in leads_data:
            lead_id = lead_engine.save_lead_to_db(lead, dry_run=False)
            ids.append(lead_id)
        
        self.assertEqual(len(ids), 3)
        self.assertTrue(all(lid.startswith('LD-') for lid in ids))
        
        nums = [int(lid.split('-')[1]) for lid in ids]
        self.assertEqual(nums[1], nums[0] + 1)
        self.assertEqual(nums[2], nums[1] + 1)


if __name__ == '__main__':
    unittest.main()
