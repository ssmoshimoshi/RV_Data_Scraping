import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import tempfile
import json
from scrapers.db_sqlite import init_db, upsert_lead, get_all_leads


class TestDBSQLite(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test_leads.sqlite'

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_db_creates_tables(self):
        init_db(self.db_path)
        self.assertTrue(self.db_path.exists())

    def test_upsert_lead_basic(self):
        init_db(self.db_path)
        
        lead_data = {
            'entity_id': 'test_001',
            'business_name': 'Test Kafe',
            'target_sector': 'fnb_hospitality',
            'primary_service_pillar': 'Labeling Produk & Stiker',
            'category_raw': 'kafe',
            'whatsapp_number': '628123456789',
            'is_wa_valid': 1,
            'is_commercial': 1,
            'locations': {
                'place_id': 'place_001',
                'address_full': 'Jl. Somba Opu 123',
                'district_area': 'Makassar Utara',
                'city': 'makassar',
                'sales_cluster': 'cluster_a',
                'latitude': -8.6705,
                'longitude': 119.4144,
            },
            'digital_footprints': {
                'website_url': 'https://kafe-test.com',
                'gmaps_rating': 4.5,
                'gmaps_reviews_count': 120,
                'instagram_handle': '@kafe_test',
                'instagram_followers': 500,
            },
            'commercial_intelligence': {
                'lead_score': 75,
                'priority_tier': 'Tier B',
                'score_legitimacy': 20,
                'score_velocity': 15,
                'score_turnover': 20,
                'score_budget': 20,
                'detected_service_needs': ['label_stiker', 'kemasan_botol'],
                'recommended_products': 'Stiker Label Botol, Mug Souvenir',
                'est_order_value_idr': 5000000,
            },
            'outreach_logs': {
                'outreach_status': 'Belum Dihubungi',
                'whatsapp_pitch': 'Halo Kak, kami vendor printing...',
            }
        }
        
        result = upsert_lead(lead_data, self.db_path)
        self.assertTrue(result)

    def test_get_all_leads_returns_list(self):
        init_db(self.db_path)
        
        lead_data = {
            'entity_id': 'test_002',
            'business_name': 'Test Sekolah',
            'target_sector': 'education',
            'primary_service_pillar': 'Institusi, Sekolah & Kantor',
            'category_raw': 'sekolah',
            'locations': {'district_area': 'Makassar Tengah'},
            'digital_footprints': {},
            'commercial_intelligence': {'lead_score': 60},
            'outreach_logs': {'outreach_status': 'Belum Dihubungi'},
        }
        
        upsert_lead(lead_data, self.db_path)
        
        leads = get_all_leads(self.db_path)
        self.assertIsInstance(leads, list)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['entity_id'], 'test_002')
        self.assertEqual(leads[0]['business_name'], 'Test Sekolah')

    def test_upsert_lead_update_existing(self):
        init_db(self.db_path)
        
        lead_v1 = {
            'entity_id': 'test_003',
            'business_name': 'Distro V1',
            'target_sector': 'retail_apparel',
            'primary_service_pillar': 'Konveksi & Sablon Tekstil',
            'locations': {'district_area': 'Somba Opu'},
            'digital_footprints': {},
            'commercial_intelligence': {'lead_score': 50},
            'outreach_logs': {'outreach_status': 'Belum Dihubungi'},
        }
        
        upsert_lead(lead_v1, self.db_path)
        leads = get_all_leads(self.db_path)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['lead_score'], 50)
        
        lead_v2 = {
            'entity_id': 'test_003',
            'business_name': 'Distro V2 Updated',
            'target_sector': 'retail_apparel',
            'primary_service_pillar': 'Konveksi & Sablon Tekstil',
            'locations': {'district_area': 'Somba Opu'},
            'digital_footprints': {},
            'commercial_intelligence': {'lead_score': 75},
            'outreach_logs': {'outreach_status': 'Sudah Dihubungi'},
        }
        
        upsert_lead(lead_v2, self.db_path)
        leads = get_all_leads(self.db_path)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['lead_score'], 75)
        self.assertEqual(leads[0]['business_name'], 'Distro V2 Updated')

    def test_json_fields_parsed_correctly(self):
        init_db(self.db_path)
        
        lead_data = {
            'entity_id': 'test_004',
            'business_name': 'Event Organizer',
            'target_sector': 'event_community',
            'primary_service_pillar': 'Merchandise & Souvenir Custom',
            'locations': {
                'district_area': 'Tamalanrea',
                'opening_hours_json': {'monday': '09:00-17:00', 'sunday': 'closed'},
            },
            'digital_footprints': {
                'review_snippets_json': ['Pelayanan sangat baik', 'Hasil printing memuaskan'],
                'meta_ads_data_json': {'campaign_id': 'camp_001', 'status': 'active'},
            },
            'commercial_intelligence': {
                'detected_service_needs': ['sablon_kaos', 'ganci_uv', 'pin_peniti'],
                'service_pain_points': ['Harga kurang kompetitif', 'Lead time lama'],
            },
            'outreach_logs': {},
        }
        
        upsert_lead(lead_data, self.db_path)
        leads = get_all_leads(self.db_path)
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        
        self.assertIsInstance(lead['opening_hours_json'], dict)
        self.assertIsInstance(lead['review_snippets_json'], list)
        self.assertIsInstance(lead['meta_ads_data_json'], dict)
        self.assertIsInstance(lead['detected_service_needs'], list)

    def test_rescrape_preserves_sales_outreach_notes(self):
        init_db(self.db_path)

        # 1. Pipeline pertama menyimpan lead baru
        initial_lead = {
            'entity_id': 'test_crm_001',
            'business_name': 'Kedai Kopi Panakkukang',
            'target_sector': 'fnb_hospitality',
            'primary_service_pillar': 'label_sticker',
            'outreach_logs': {
                'outreach_status': 'Belum Dihubungi',
                'sales_notes': '',
            }
        }
        upsert_lead(initial_lead, self.db_path)

        # 2. Tim sales memperbarui status dan catatan
        updated_lead = {
            'entity_id': 'test_crm_001',
            'business_name': 'Kedai Kopi Panakkukang',
            'target_sector': 'fnb_hospitality',
            'primary_service_pillar': 'label_sticker',
            'outreach_logs': {
                'outreach_status': 'Tertarik',
                'sales_notes': 'Minta dikirimkan sampel cup 16oz dan paper bag hari Jumat.',
                'contacted_at': '2026-10-27T10:00:00',
            }
        }
        upsert_lead(updated_lead, self.db_path)

        # Verifikasi status sudah terupdate
        leads = get_all_leads(self.db_path)
        self.assertEqual(leads[0]['outreach_status'], 'Tertarik')
        self.assertIn('sampel cup', leads[0]['sales_notes'])

        # 3. Pipeline scraping dijalankan ulang dengan status default 'Belum Dihubungi' dan catatan kosong
        pipeline_rescrape = {
            'entity_id': 'test_crm_001',
            'business_name': 'Kedai Kopi Panakkukang (Refreshed)',
            'target_sector': 'fnb_hospitality',
            'primary_service_pillar': 'label_sticker',
            'outreach_logs': {
                'outreach_status': 'Belum Dihubungi',
                'sales_notes': '',
            }
        }
        upsert_lead(pipeline_rescrape, self.db_path)

        # 4. Verifikasi bahwa catatan dan status sales TIDAK terhapus
        leads_after = get_all_leads(self.db_path)
        self.assertEqual(len(leads_after), 1)
        self.assertEqual(leads_after[0]['business_name'], 'Kedai Kopi Panakkukang (Refreshed)')
        self.assertEqual(leads_after[0]['outreach_status'], 'Tertarik')
        self.assertEqual(leads_after[0]['sales_notes'], 'Minta dikirimkan sampel cup 16oz dan paper bag hari Jumat.')
        self.assertEqual(leads_after[0]['contacted_at'], '2026-10-27T10:00:00')


class TestManualOverride(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test_leads.sqlite'

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_update_manual_override_upserts_and_flows_to_get_all_leads(self):
        from scrapers.db_sqlite import update_manual_override
        init_db(self.db_path)
        upsert_lead({
            'entity_id': 'test_override_001',
            'business_name': 'Kopi Override',
            'target_sector': 'fnb_beverage',
            'primary_service_pillar': 'label_sticker',
            'commercial_intelligence': {'lead_score': 40, 'priority_tier': 'Tier D'},
        }, self.db_path)

        ok = update_manual_override('test_override_001', 'Tier A', 91, 'Survei lokasi ramai', True, self.db_path)
        self.assertTrue(ok)

        leads = get_all_leads(self.db_path)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['manual_tier'], 'Tier A')
        self.assertEqual(leads[0]['manual_score'], 91)
        self.assertEqual(leads[0]['manual_notes'], 'Survei lokasi ramai')
        self.assertEqual(leads[0]['is_manual_override'], 1)
        # Skor otomatis tidak boleh tertimpa di level database
        self.assertEqual(leads[0]['lead_score'], 40)

    def test_update_manual_override_creates_row_for_new_entity(self):
        from scrapers.db_sqlite import update_manual_override
        init_db(self.db_path)

        ok = update_manual_override('ent_baru', 'Tier B', 70, '', True, self.db_path)
        self.assertTrue(ok)

        ok_clear = update_manual_override('ent_baru', '', None, '', False, self.db_path)
        self.assertTrue(ok_clear)


if __name__ == '__main__':
    unittest.main()
