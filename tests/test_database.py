import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from unittest.mock import MagicMock, patch
from scrapers.database import insert_lead, get_supabase_client, batch_upsert_dossiers


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
        lead = {'business_name': 'Test Lead'}
        success, msg = insert_lead(lead, score=50, dry_run=False)
        self.assertFalse(success)
        self.assertIn('SUPABASE', msg)

    def test_batch_upsert_dry_run_returns_correct_count(self):
        dossiers = [
            {'entity_id': 'ent_0001', 'business_name': 'Toko A', 'category': 'fnb_food_resto'},
            {'entity_id': 'ent_0002', 'business_name': 'Toko B', 'category': 'general_commercial'},
            {'entity_id': 'ent_0003', 'business_name': 'Toko C', 'category': 'fnb_food_resto'},
        ]
        count, msg = batch_upsert_dossiers(dossiers, dry_run=True)
        self.assertEqual(count, 3)
        self.assertIn('simulasi berhasil', msg)

    def test_batch_upsert_no_credentials_returns_zero(self):
        dossiers = [{'entity_id': 'ent_0001', 'business_name': 'Toko A'}]
        count, msg = batch_upsert_dossiers(dossiers, dry_run=False)
        self.assertEqual(count, 0)
        self.assertIn('SUPABASE', msg)

    def test_batch_upsert_with_mock_client(self):
        dossiers = [
            {'entity_id': 'ent_0001', 'business_name': 'Warung Makan Asri', 'category': 'fnb_food_resto',
             'city': 'Makassar', 'whatsapp_number': '6281234567890', 'lead_score': 82,
             'priority_tier': 'Tier A', 'estimated_monthly_units': 200,
             'estimated_monthly_value_idr': 4000000, 'packaging_pain_points': ['kardus tipis'],
             'whatsapp_pitch': 'Halo...', 'platforms': ['google_maps', 'tiktok']},
        ]
        mock_client = MagicMock()
        mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        with patch('scrapers.database.get_supabase_client', return_value=mock_client):
            count, msg = batch_upsert_dossiers(dossiers, dry_run=False)

        self.assertEqual(count, 1)
        mock_client.table.assert_called_with("leads")
        mock_client.table.return_value.upsert.assert_called_once()


if __name__ == '__main__':
    unittest.main()
