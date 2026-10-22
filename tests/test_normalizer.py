import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from scrapers.normalizer import normalize_whatsapp, normalize_address


class TestNormalizeWhatsApp(unittest.TestCase):
    
    def test_valid_whatsapp_with_plus62(self):
        self.assertEqual(normalize_whatsapp('+6281234567890'), '6281234567890')
    
    def test_valid_whatsapp_with_62(self):
        self.assertEqual(normalize_whatsapp('6281234567890'), '6281234567890')
    
    def test_valid_whatsapp_with_08(self):
        self.assertEqual(normalize_whatsapp('081234567890'), '6281234567890')
    
    def test_valid_whatsapp_with_8(self):
        self.assertEqual(normalize_whatsapp('81234567890'), '6281234567890')
    
    def test_valid_10_digit_number(self):
        self.assertEqual(normalize_whatsapp('0811223344'), '62811223344')
    
    def test_valid_with_special_chars(self):
        self.assertEqual(normalize_whatsapp('+62 812-3456-7890'), '6281234567890')
    
    def test_invalid_pstn_jakarta(self):
        self.assertIsNone(normalize_whatsapp('021-12345678'))
    
    def test_invalid_pstn_bandung(self):
        self.assertIsNone(normalize_whatsapp('022-87654321'))
    
    def test_invalid_too_short(self):
        self.assertIsNone(normalize_whatsapp('0812345'))
    
    def test_invalid_too_long(self):
        self.assertIsNone(normalize_whatsapp('081234567890123456'))
    
    def test_invalid_not_starting_with_8(self):
        self.assertIsNone(normalize_whatsapp('0712345678'))
    
    def test_empty_input(self):
        self.assertIsNone(normalize_whatsapp(''))
    
    def test_none_input(self):
        self.assertIsNone(normalize_whatsapp(None))


class TestNormalizeAddress(unittest.TestCase):
    
    def test_full_address_with_kota(self):
        result = normalize_address('Jl. Sudirman No. 123, Kota Bandung, 40111')
        self.assertEqual(result['city'], 'Bandung')
        self.assertIn('Sudirman', result['address_full'])
        self.assertNotIn('40111', result['address_full'])
    
    def test_address_with_kabupaten(self):
        result = normalize_address('Desa Cibiru, Kabupaten Bandung Barat')
        self.assertEqual(result['city'], 'Bandung Barat')
    
    def test_address_with_kecamatan(self):
        result = normalize_address('Jl. Raya, Kecamatan Cimahi Selatan, Kota Cimahi')
        self.assertEqual(result['district_area'], 'Cimahi Selatan')
        self.assertEqual(result['city'], 'Cimahi')
    
    def test_address_with_abbreviated_kec(self):
        result = normalize_address('Jl. Ahmad Yani, Kec. Coblong, Kota Bandung')
        self.assertEqual(result['district_area'], 'Coblong')
    
    def test_address_with_kelurahan(self):
        result = normalize_address('Kelurahan Dago, Kecamatan Coblong')
        self.assertEqual(result['district_area'], 'Dago')
    
    def test_address_with_kel_abbreviated(self):
        result = normalize_address('Kel. Lebak Gede, Kec. Coblong')
        self.assertEqual(result['district_area'], 'Lebak Gede')
    
    def test_simple_address_comma_separated(self):
        result = normalize_address('Jl. Merdeka, Malang')
        self.assertEqual(result['city'], 'Malang')
    
    def test_empty_address(self):
        result = normalize_address('')
        self.assertEqual(result['address_full'], '')
        self.assertEqual(result['city'], '')
        self.assertEqual(result['district_area'], '')
    
    def test_none_address(self):
        result = normalize_address(None)
        self.assertEqual(result['address_full'], '')


if __name__ == '__main__':
    unittest.main()
