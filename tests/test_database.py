import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from scrapers.database import insert_lead, get_supabase_client


class TestDatabaseModule(unittest.TestCase):
    
    def test_dry_run_insert(self):
        lead = {
            'business_name': 'Warung Kopi Uji Coba',
            'platform': 'google_maps',
            'whatsapp_number': '6281234567890'
        }
        success, msg = insert_lead(lead, score=85, dry_run=True)
        self.assertTrue(success)
        self.assertIn('DRY RUN', msg)
        self.assertIn('Warung Kopi Uji Coba', msg)
    
    def test_missing_credentials_handling(self):
        # Pastikan jika env SUPABASE belum diset, modul tidak crash melainkan mengembalikan error terkelola
        lead = {'business_name': 'Test Lead'}
        success, msg = insert_lead(lead, score=50, dry_run=False)
        self.assertFalse(success)
        self.assertIn('SUPABASE', msg)


if __name__ == '__main__':
    unittest.main()
