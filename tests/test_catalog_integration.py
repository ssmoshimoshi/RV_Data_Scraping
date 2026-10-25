import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json
import unittest
from scrapers.sync_catalog import CATALOG_OUTPUT_FILE, load_cached_catalog


class TestCatalogIntegration(unittest.TestCase):

    def setUp(self):
        self.catalog_path = CATALOG_OUTPUT_FILE
        self.assertTrue(self.catalog_path.exists(), f"Berkas katalog tidak ditemukan: {self.catalog_path}")
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            self.catalog_data = json.load(f)

    def test_catalog_file_structure(self):
        self.assertIsInstance(self.catalog_data, dict)
        self.assertIn('product_templates', self.catalog_data)
        self.assertIn('master_items', self.catalog_data)
        self.assertIn('synced_at', self.catalog_data)

    def test_product_templates_count_and_active_status(self):
        templates = self.catalog_data.get('product_templates', [])
        self.assertEqual(len(templates), 16, f"Jumlah template produk diharapkan 16, didapat {len(templates)}")

        inactive_templates = [t for t in templates if not t.get('is_active')]
        self.assertEqual(len(inactive_templates), 0, f"Ditemukan template tidak aktif: {inactive_templates}")

    def test_required_product_templates_present(self):
        templates = self.catalog_data.get('product_templates', [])
        template_names = [t.get('name', '').lower() for t in templates]

        # Validasi Ganci UV Akrilik
        has_ganci = any('ganci uv akrilik' in name for name in template_names)
        self.assertTrue(has_ganci, "Template 'Ganci UV Akrilik' tidak ditemukan dalam katalog.")

        # Validasi Spanduk Flexy Korea
        has_spanduk = any('spanduk flexy korea' in name for name in template_names)
        self.assertTrue(has_spanduk, "Template 'Spanduk Flexy Korea' tidak ditemukan dalam katalog.")

        # Validasi Sablon DTF
        has_sablon_dtf = any('sablon' in name and 'dtf' in name for name in template_names)
        self.assertTrue(has_sablon_dtf, "Template 'Sablon DTF' tidak ditemukan dalam katalog.")

    def test_master_items_count_and_structure(self):
        items = self.catalog_data.get('master_items', [])
        self.assertEqual(len(items), 100, f"Jumlah master items diharapkan 100, didapat {len(items)}")

        # Pastikan setiap item memiliki atribut dasar
        for item in items:
            self.assertIn('id', item)
            self.assertIn('name', item)
            self.assertIn('itemCode', item)
            self.assertIn('type', item)

    def test_load_cached_catalog_helper(self):
        cached = load_cached_catalog(self.catalog_path)
        self.assertIsInstance(cached, dict)
        self.assertEqual(len(cached.get('product_templates', [])), 16)
        self.assertEqual(len(cached.get('master_items', [])), 100)


if __name__ == '__main__':
    unittest.main()
