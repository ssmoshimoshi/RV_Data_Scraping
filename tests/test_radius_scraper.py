import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
import json
import tempfile
from scrapers.radius_scraper import (
    haversine_distance,
    load_state,
    save_state,
    process_place,
    LAT_ORIGIN,
    LON_ORIGIN
)


class TestRadiusScraper(unittest.TestCase):
    
    def test_haversine_distance_same_point(self):
        distance = haversine_distance(LAT_ORIGIN, LON_ORIGIN, LAT_ORIGIN, LON_ORIGIN)
        self.assertAlmostEqual(distance, 0.0, places=2)
    
    def test_haversine_distance_known_points(self):
        lat1, lon1 = -5.1575, 119.4353
        lat2, lon2 = -5.1475, 119.4453
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        self.assertGreater(distance, 0)
        self.assertLess(distance, 2)
    
    def test_state_persistence(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        original_state_file = Path(__file__).resolve().parent.parent / "data" / "search_state.json"
        
        import scrapers.radius_scraper as rs
        rs.STATE_FILE = temp_path
        
        test_state = {
            "center_lat": LAT_ORIGIN,
            "center_lon": LON_ORIGIN,
            "current_radius_km": 2,
            "current_sector_index": 3,
            "completed_sectors_in_radius": ["fnb_hospitality", "retail_apparel"],
            "seen_place_ids": ["test_id_1", "test_id_2"],
            "last_scraped_at": "2026-10-28T10:00:00Z"
        }
        
        save_state(test_state)
        loaded_state = load_state()
        
        self.assertEqual(loaded_state['current_radius_km'], 2)
        self.assertEqual(loaded_state['current_sector_index'], 3)
        self.assertEqual(len(loaded_state['completed_sectors_in_radius']), 2)
        self.assertEqual(len(loaded_state['seen_place_ids']), 2)
        
        temp_path.unlink()
        rs.STATE_FILE = original_state_file
    
    def test_radius_expansion_logic(self):
        state = {
            "current_radius_km": 1,
            "current_sector_index": 5,
            "completed_sectors_in_radius": ["fnb_hospitality", "retail_apparel", "beauty_skincare", "corporate_legal", "event_wedding"]
        }
        
        sector_count = 5
        if state['current_sector_index'] >= sector_count:
            state['current_radius_km'] += 1
            state['current_sector_index'] = 0
            state['completed_sectors_in_radius'] = []
        
        self.assertEqual(state['current_radius_km'], 2)
        self.assertEqual(state['current_sector_index'], 0)
        self.assertEqual(len(state['completed_sectors_in_radius']), 0)
    
    def test_process_place_basic(self):
        place = {
            'place_id': 'test_place_123',
            'name': 'Kafe Test',
            'vicinity': 'Jl. Test No. 123',
            'geometry': {
                'location': {
                    'lat': -5.158,
                    'lng': 119.436
                }
            }
        }
        
        details = {
            'formatted_address': 'Jl. Test No. 123, Makassar',
            'formatted_phone_number': '+62 812-3456-7890'
        }
        
        lead = process_place(place, details, LAT_ORIGIN, LON_ORIGIN, 'fnb_hospitality')
        
        self.assertIsNotNone(lead)
        self.assertEqual(lead['place_id'], 'test_place_123')
        self.assertEqual(lead['business_name'], 'Kafe Test')
        self.assertEqual(lead['category'], 'fnb_hospitality')
        self.assertIsNotNone(lead['whatsapp'])
        self.assertGreaterEqual(lead['lead_score'], 0)
        self.assertLess(lead['distance_km'], 1)
    
    def test_process_place_without_details(self):
        place = {
            'place_id': 'test_place_456',
            'name': 'Restoran Test',
            'vicinity': 'Jl. Minimal',
            'geometry': {
                'location': {
                    'lat': -5.157,
                    'lng': 119.435
                }
            }
        }
        
        lead = process_place(place, None, LAT_ORIGIN, LON_ORIGIN, 'fnb_hospitality')
        
        self.assertIsNotNone(lead)
        self.assertEqual(lead['business_name'], 'Restoran Test')
        self.assertIsNone(lead['whatsapp'])
        self.assertIsNotNone(lead['address'])

    def test_save_lead_deduplicates_by_whatsapp_and_name(self):
        import scrapers.radius_scraper as rs
        from scrapers.db_sqlite import get_all_leads, init_db as init_rel_db
        
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as f:
            temp_db = Path(f.name)
        
        orig_db = rs.LEADS_DB
        rs.LEADS_DB = temp_db
        init_rel_db(temp_db)
        rs.init_db()
        
        try:
            lead1 = {
                'place_id': 'place_orig_001',
                'business_name': 'Kopi Senja Bahagia',
                'category': 'fnb_hospitality',
                'whatsapp': '628111222333',
                'found_at': '2026-10-29T12:00:00Z'
            }
            rs.save_lead(lead1)
            
            leads_1 = get_all_leads(temp_db)
            self.assertEqual(len(leads_1), 1)
            first_entity_id = leads_1[0]['entity_id']
            
            lead2 = {
                'place_id': 'place_diff_999',
                'business_name': 'kopi senja bahagia',
                'category': 'fnb_hospitality',
                'whatsapp': '628111222333',
                'found_at': '2026-10-29T13:00:00Z'
            }
            rs.save_lead(lead2)
            
            leads_2 = get_all_leads(temp_db)
            self.assertEqual(len(leads_2), 1)
            self.assertEqual(leads_2[0]['entity_id'], first_entity_id)

            # Test save_lead with dict address (handling edge case)
            lead_dict_address = {
                'place_id': 'place_dict_addr',
                'business_name': 'Bakery Manis',
                'category': 'fnb_hospitality',
                'address': {'address_full': 'Jl. Veteran No. 10', 'city': 'Makassar'},
                'whatsapp': '628999888777',
                'found_at': '2026-10-29T14:00:00Z'
            }
            save_ok = rs.save_lead(lead_dict_address)
            self.assertTrue(save_ok)
            leads_3 = get_all_leads(temp_db)
            self.assertEqual(len(leads_3), 2)
        finally:
            rs.LEADS_DB = orig_db
            try:
                temp_db.unlink()
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()

