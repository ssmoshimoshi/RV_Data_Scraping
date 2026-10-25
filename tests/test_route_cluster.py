import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest

from scrapers.route_cluster import (
    assign_sales_cluster,
    KORIDOR_PANAKKUKANG,
    KORIDOR_RAPPOCINI,
    KORIDOR_UJUNG_PANDANG,
    KORIDOR_TAMALANREA,
    KORIDOR_MARISO_MAMAJANG,
    DEFAULT_CLUSTER,
)


class TestAssignSalesCluster(unittest.TestCase):

    def test_boulevard_to_panakkukang(self):
        self.assertEqual(assign_sales_cluster('Jl. Boulevard No. 12', ''), 'Koridor Panakkukang')

    def test_hertasning_to_rappocini(self):
        self.assertEqual(assign_sales_cluster('Jl. Hertasning', ''), 'Koridor Rappocini')

    def test_hertasning_baru_to_panakkukang(self):
        self.assertEqual(assign_sales_cluster('Jl. Hertasning Baru No. 3', ''), 'Koridor Panakkukang')

    def test_district_only_match(self):
        self.assertEqual(assign_sales_cluster('', 'Rappocini'), 'Koridor Rappocini')

    def test_somba_opu_to_ujung_pandang(self):
        self.assertEqual(assign_sales_cluster('Jl. Somba Opu No. 5', ''), 'Koridor Ujung Pandang')

    def test_perintis_to_tamalanrea(self):
        self.assertEqual(assign_sales_cluster('Jl. Perintis Kemerdekaan Km. 10', ''), 'Koridor Tamalanrea')

    def test_cendrawasih_to_mariso_mamajang(self):
        self.assertEqual(assign_sales_cluster('Jl. Cendrawasih No. 8', ''), 'Koridor Mariso Mamajang')

    def test_unknown_address_fallback(self):
        self.assertEqual(assign_sales_cluster('Jl. Entah Dimana No. 99', 'Entah'), DEFAULT_CLUSTER)

    def test_empty_inputs_fallback(self):
        self.assertEqual(assign_sales_cluster('', ''), DEFAULT_CLUSTER)
        self.assertEqual(assign_sales_cluster(None, None), DEFAULT_CLUSTER)

    def test_case_insensitive(self):
        self.assertEqual(assign_sales_cluster('JL. BOULEVARD No. 12', 'PANAKKUKANG'), 'Koridor Panakkukang')

    def test_all_keywords_mapped(self):
        for kw in KORIDOR_PANAKKUKANG:
            self.assertEqual(assign_sales_cluster(f'Jl. {kw.title()}', ''), 'Koridor Panakkukang')
        for kw in KORIDOR_RAPPOCINI:
            self.assertEqual(assign_sales_cluster(f'Jl. {kw.title()}', ''), 'Koridor Rappocini')
        for kw in KORIDOR_UJUNG_PANDANG:
            self.assertEqual(assign_sales_cluster(f'Jl. {kw.title()}', ''), 'Koridor Ujung Pandang')
        for kw in KORIDOR_TAMALANREA:
            self.assertEqual(assign_sales_cluster(f'Jl. {kw.title()}', ''), 'Koridor Tamalanrea')
        for kw in KORIDOR_MARISO_MAMAJANG:
            self.assertEqual(assign_sales_cluster(f'Jl. {kw.title()}', ''), 'Koridor Mariso Mamajang')


if __name__ == '__main__':
    unittest.main()
