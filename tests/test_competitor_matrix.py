import unittest
from scrapers.competitor_matrix import (
    MAKASSAR_PRINTING_COMPETITORS,
    extract_competitor_weaknesses,
    generate_ruang_visual_counter_pitch,
    format_competitor_for_hermes,
    sync_competitor_matrix_to_hermes
)


class TestCompetitorMatrix(unittest.TestCase):

    def test_format_competitor_for_hermes_has_11_columns(self):
        comp = MAKASSAR_PRINTING_COMPETITORS[0]
        row = format_competitor_for_hermes(comp)
        self.assertEqual(len(row), 11)
        self.assertEqual(row[0], "Percetakan Bua Kana Makassar")
        self.assertTrue(row[4].startswith("628"))
        self.assertTrue(row[5].startswith("https://wa.me/"))
        self.assertTrue(len(row[6]) > 0)
        self.assertTrue(len(row[7]) > 0)
        self.assertTrue(len(row[8]) > 0)
        self.assertTrue(len(row[10]) == 10)

    def test_extract_competitor_weaknesses_quality_and_service(self):
        sample_reviews = [
            "Warna sablon luntur saat terkena air.",
            "Waktu penyelesaian sering molor dan telat seminggu.",
            "Hasil potong stiker salah potong dan bergeser."
        ]
        weaknesses = extract_competitor_weaknesses(sample_reviews)
        self.assertTrue(any("luntur" in w.lower() for w in weaknesses["quality"]))
        self.assertTrue(any("salah potong" in w.lower() for w in weaknesses["quality"]))
        self.assertTrue(any("tenggat" in w.lower() or "jadwal" in w.lower() for w in weaknesses["service"]))

    def test_generate_ruang_visual_counter_pitch(self):
        q = ["Tinta sablon/cetak mudah luntur jika terkena cairan"]
        s = ["Pengerjaan sering melewati tenggat waktu yang dijanjikan"]
        pitch = generate_ruang_visual_counter_pitch(q, s)
        self.assertIn("Garansi cetak ulang 100%", pitch)
        self.assertIn("SLA tegas", pitch)

    def test_sync_competitor_matrix_dry_run(self):
        res = sync_competitor_matrix_to_hermes(dry_run=True)
        self.assertEqual(res.get("status"), "dry_run")
        self.assertEqual(res.get("sheet_name"), "Matriks Kompetitor")
        self.assertEqual(res.get("rows_count"), len(MAKASSAR_PRINTING_COMPETITORS))
        self.assertEqual(len(res.get("sample_rows", [])), 2)
        self.assertEqual(len(res["sample_rows"][0]), 11)

    def test_makassar_competitor_dataset_integrity(self):
        self.assertTrue(len(MAKASSAR_PRINTING_COMPETITORS) >= 5)
        for comp in MAKASSAR_PRINTING_COMPETITORS:
            self.assertIn("name", comp)
            self.assertIn("focus", comp)
            self.assertIn("rating", comp)
            self.assertIn("place_id", comp)
            self.assertIn("whatsapp", comp)
            self.assertTrue(comp["rating"] >= 3.0 and comp["rating"] <= 5.0)


if __name__ == "__main__":
    unittest.main()
