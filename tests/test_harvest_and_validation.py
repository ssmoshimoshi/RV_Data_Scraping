import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from scrapers.normalizer import validate_whatsapp_number, normalize_whatsapp
from scrapers.harvest_makassar import build_queries


class TestValidateWhatsAppNumber(unittest.TestCase):
    def test_valid_telkomsel_prefix(self):
        is_valid, normalized = validate_whatsapp_number('62811234567890')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62811234567890')

    def test_valid_indosat_prefix(self):
        is_valid, normalized = validate_whatsapp_number('62852123456789')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62852123456789')

    def test_valid_xl_axiata_prefix(self):
        is_valid, normalized = validate_whatsapp_number('62877123456789')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62877123456789')

    def test_valid_three_prefix(self):
        is_valid, normalized = validate_whatsapp_number('62895123456789')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62895123456789')

    def test_valid_smartfren_prefix(self):
        is_valid, normalized = validate_whatsapp_number('62881123456789')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62881123456789')

    def test_normalize_08_prefix(self):
        is_valid, normalized = validate_whatsapp_number('08111234567')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '628111234567')

    def test_normalize_0_prefix(self):
        is_valid, normalized = validate_whatsapp_number('0811123456789')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62811123456789')

    def test_normalize_plus62(self):
        is_valid, normalized = validate_whatsapp_number('+62811234567890')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62811234567890')

    def test_reject_makassar_pstn_0411(self):
        is_valid, normalized = validate_whatsapp_number('04111234567')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_makassar_pstn_62411(self):
        is_valid, normalized = validate_whatsapp_number('624111234567')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_jakarta_landline_021(self):
        is_valid, normalized = validate_whatsapp_number('02112345678')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_bandung_landline_022(self):
        is_valid, normalized = validate_whatsapp_number('02212345678')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_too_short(self):
        is_valid, normalized = validate_whatsapp_number('6281123')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_too_long(self):
        is_valid, normalized = validate_whatsapp_number('628112345678901234')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_invalid_prefix_628(self):
        is_valid, normalized = validate_whatsapp_number('628001234567')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_empty(self):
        is_valid, normalized = validate_whatsapp_number('')
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_reject_none(self):
        is_valid, normalized = validate_whatsapp_number(None)
        self.assertFalse(is_valid)
        self.assertIsNone(normalized)

    def test_handle_special_characters(self):
        is_valid, normalized = validate_whatsapp_number('+62 (811) 234-567-890')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '62811234567890')

    def test_handle_spaces_and_dashes(self):
        is_valid, normalized = validate_whatsapp_number('0811 1234 5678')
        self.assertTrue(is_valid)
        self.assertEqual(normalized, '6281112345678')


class TestHarvestMakassarQueries(unittest.TestCase):
    def test_build_queries_fnb_hospitality(self):
        queries = build_queries('fnb_hospitality')
        self.assertGreater(len(queries), 0)
        query_strs = [q[2] for q in queries]
        self.assertTrue(any('cafe' in q.lower() for q in query_strs))
        self.assertTrue(any('makassar' in q.lower() for q in query_strs))

    def test_build_queries_education(self):
        queries = build_queries('education')
        self.assertGreater(len(queries), 0)
        query_strs = [q[2] for q in queries]
        self.assertTrue(any('sekolah' in q.lower() for q in query_strs))
        self.assertTrue(any('pesantren' in q.lower() for q in query_strs))

    def test_build_queries_corporate_legal(self):
        queries = build_queries('corporate_legal')
        self.assertGreater(len(queries), 0)
        query_strs = [q[2] for q in queries]
        self.assertTrue(any('notaris' in q.lower() or 'hukum' in q.lower() for q in query_strs))

    def test_build_queries_event_community(self):
        queries = build_queries('event_community')
        self.assertGreater(len(queries), 0)
        query_strs = [q[2] for q in queries]
        self.assertTrue(any('event' in q.lower() or 'organizer' in q.lower() for q in query_strs))

    def test_build_queries_retail_apparel(self):
        queries = build_queries('retail_apparel')
        self.assertGreater(len(queries), 0)
        query_strs = [q[2] for q in queries]
        self.assertTrue(any('distro' in q.lower() or 'baju' in q.lower() for q in query_strs))

    def test_build_queries_all(self):
        queries = build_queries('all')
        self.assertGreater(len(queries), 0)
        sectors_in_queries = set(q[0] for q in queries)
        self.assertGreaterEqual(len(sectors_in_queries), 6)

    def test_query_structure(self):
        queries = build_queries('education')
        for sector, district, query_str in queries:
            self.assertIsInstance(sector, str)
            self.assertIsInstance(district, str)
            self.assertIsInstance(query_str, str)
            self.assertGreater(len(sector), 0)
            self.assertGreater(len(district), 0)
            self.assertGreater(len(query_str), 0)

    def test_district_coverage(self):
        queries = build_queries('all')
        districts = set(q[1] for q in queries)
        expected_districts = {'Panakkukang', 'Rappocini', 'Tamalanrea', 'Ujung Pandang', 'Mariso', 'Biringkanaya'}
        self.assertEqual(districts, expected_districts)


class TestNormalizeWhatsAppCompat(unittest.TestCase):
    def test_normalize_whatsapp_still_works(self):
        result = normalize_whatsapp('0811234567890')
        self.assertEqual(result, '62811234567890')

    def test_normalize_rejects_landline(self):
        result = normalize_whatsapp('04111234567')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
