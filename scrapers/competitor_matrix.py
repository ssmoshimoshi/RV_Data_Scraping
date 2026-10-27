import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from scrapers.sync_hermes import send_webhook_payload

QUALITY_KEYWORDS = {
    "luntur": "Tinta sablon/cetak mudah luntur jika terkena cairan atau gesekan",
    "pudar": "Warna cetak cepat memudar tidak tahan lama",
    "buram": "Resolusi cetak kurang tajam dan teks berbayang",
    "salah potong": "Salah potong atau hasil pisau pond tidak presisi dan ukuran bergeser",
    "pecah": "File gambar/vektor pecah saat dicetak pada media besar",
    "lem lepas": "Lem finishing box kemasan atau stiker mudah lepas",
    "sobek": "Ketebalan bahan tipis dan mudah sobek saat pengemasan",
    "warna berbeda": "Warna hasil cetak meleset jauh dari file desain digital",
    "melengkung": "Kertas stiker atau box melengkung saat kena suhu dingin",
}

SERVICE_KEYWORDS = {
    "telat": "Pengerjaan telat dan sering melewati tenggat waktu yang dijanjikan",
    "molor": "Jadwal pengambilan barang sering diundur tanpa kepastian",
    "antrean lama": "Antrean order padat dan tidak ada prioritas pengerjaan kilat",
    "admin slow": "Admin WhatsApp sangat lambat membalas pesan konsultasi",
    "tidak ramah": "Pelayanan front office kurang komunikatif terhadap revisi",
    "minimal order": "Batas minimal pemesanan (MOQ) terlalu tinggi bagi UMKM pemula",
    "salah hitung": "Kuantitas barang saat diterima kurang dari nota pemesanan",
    "tidak ada garansi": "Tidak ada jaminan ganti rugi jika terjadi cacat produksi",
}

MAKASSAR_PRINTING_COMPETITORS = [
    {
        "name": "Percetakan Bua Kana Makassar",
        "focus": "Offset Printing, Brosur Massal & Kalender",
        "scale": "Kapasitas Skala Besar (Pabrik / Offset)",
        "rating": 4.1,
        "reviews_count": 310,
        "place_id": "ChIJ_buakana_mks_001",
        "address": "Jl. Bua Kana No. 24, Makassar",
        "whatsapp": "628114201111",
        "maps_url": "https://maps.google.com/?q=-5.1481,119.4285",
        "sample_negative_reviews": [
            "Pengerjaan kalender molor 5 hari dari janji, padahal sudah mau akhir tahun.",
            "Warna biru brosur agak luntur waktu kena air hujan dan warna meleset dari desain awal.",
            "Admin sangat slow response kalau ditanya progres pengerjaan lewat WhatsApp."
        ]
    },
    {
        "name": "Percetakan New Pettarani Grafika",
        "focus": "Spanduk Banner, Roll Banner, Stiker Kromo",
        "scale": "Skala Menengah (Digital Printing Outdoor)",
        "rating": 3.9,
        "reviews_count": 185,
        "place_id": "ChIJ_pettarani_grafika_002",
        "address": "Jl. A. P. Pettarani No. 42, Makassar",
        "whatsapp": "6282190882222",
        "maps_url": "https://maps.google.com/?q=-5.1522,119.4358",
        "sample_negative_reviews": [
            "Stiker botol minuman saya lem lepas waktu masuk kulkas chiller, kecewa.",
            "Hasil potongan stiker die cut miring dan potongannya tidak rata.",
            "Antrean pengerjaan sangat lama, antrean bertumpuk di workshop."
        ]
    },
    {
        "name": "Percetakan Panakkukang Digital Press",
        "focus": "Box Makanan, Packaging Karton, Digital A3+",
        "scale": "Skala Menengah (Kemasan & Box)",
        "rating": 4.2,
        "reviews_count": 240,
        "place_id": "ChIJ_panakkukang_press_003",
        "address": "Jl. Pengayoman Ruko Mirah No. 8, Panakkukang, Makassar",
        "whatsapp": "6285255443333",
        "maps_url": "https://maps.google.com/?q=-5.1465,119.4450",
        "sample_negative_reviews": [
            "Minimal order kemasan box makanan harus 1000 pcs, berat untuk resto baru.",
            "Waktu selesai sering molor kalau lagi ramai pesanan akhir pekan.",
            "Bahan kertas ivory box terasa lebih tipis dari sampel yang diperlihatkan."
        ]
    },
    {
        "name": "Percetakan Somba Opu Offset",
        "focus": "Nota NCR, Map Berkas, Undangan Hardcover",
        "scale": "Skala Besar (Offset Tradisional)",
        "rating": 4.0,
        "reviews_count": 160,
        "place_id": "ChIJ_sombaopu_offset_004",
        "address": "Jl. Somba Opu No. 88, Ujung Pandang, Makassar",
        "whatsapp": "6281342664444",
        "maps_url": "https://maps.google.com/?q=-5.1390,119.4082",
        "sample_negative_reviews": [
            "Tidak melayani sablon cup plastik atau sleeve cup kopi kekinian.",
            "Proses proofing warna sangat lambat, harus datang bolak balik ke toko fisik.",
            "Admin tidak menyediakan layanan kirim langsung ke lokasi usaha."
        ]
    },
    {
        "name": "Percetakan Cendrawasih Express Printing",
        "focus": "Cetak Dokumen Kilat, Jilid Skripsi, Kartu Nama",
        "scale": "Skala Kecil (Retail Cepat)",
        "rating": 3.8,
        "reviews_count": 130,
        "place_id": "ChIJ_cendrawasih_express_005",
        "address": "Jl. Cendrawasih No. 115, Mariso, Makassar",
        "whatsapp": "6281244775555",
        "maps_url": "https://maps.google.com/?q=-5.1610,119.4120",
        "sample_negative_reviews": [
            "Tinta cetak digital bergaris-garis tipis dan warna terlihat pudar.",
            "Tidak ada garansi cetak ulang kalau hasil cetak cacat, customer disuruh bayar lagi.",
            "Bahan stiker cepat rusak dan sobek kalau kena minyak makanan."
        ]
    },
    {
        "name": "Percetakan Daya Mandiri Grafika",
        "focus": "Sablon Plastik, Sablon Paper Cup, Spanduk Kain",
        "scale": "Skala Menengah (Sablon Kemasan)",
        "rating": 3.9,
        "reviews_count": 175,
        "place_id": "ChIJ_daya_mandiri_006",
        "address": "Jl. Perintis Kemerdekaan Km. 11, Tamalanrea, Makassar",
        "whatsapp": "6282348996666",
        "maps_url": "https://maps.google.com/?q=-5.1320,119.4890",
        "sample_negative_reviews": [
            "Sablon cup dingin 16oz tintanya luntur di tangan waktu es mencair.",
            "Font logo yang kecil pecah dan tidak terbaca jelas di permukaan cup.",
            "Janji pengerjaan 7 hari kerja melar jadi 14 hari kerja."
        ]
    }
]


def extract_competitor_weaknesses(review_texts: List[str]) -> Dict[str, List[str]]:
    combined_text = " ".join(review_texts).lower()
    
    quality_findings = []
    for kw, desc in QUALITY_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", combined_text):
            quality_findings.append(desc)

    service_findings = []
    for kw, desc in SERVICE_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", combined_text):
            service_findings.append(desc)

    return {
        "quality": quality_findings or ["Toleransi presisi warna dan daya rekat lem finishing perlu ditingkatkan"],
        "service": service_findings or ["Waktu tunggu antrean dan kepastian jadwal penyelesaian order sering bergeser"]
    }


def generate_ruang_visual_counter_pitch(quality_weaknesses: List[str], service_weaknesses: List[str]) -> str:
    pitch_points = []
    
    q_str = " ".join(quality_weaknesses).lower()
    s_str = " ".join(service_weaknesses).lower()

    if "luntur" in q_str or "pudar" in q_str or "daya rekat" in q_str or "lepas" in q_str:
        pitch_points.append("Garansi cetak ulang 100% bebas biaya dengan standar tinta anti luntur food-grade dan perekat waterproof")
    else:
        pitch_points.append("Akurasi warna terkalibrasi profil cetak CMYK digital dengan hasil konsisten tiap batch")

    if "telat" in s_str or "molor" in s_str or "jadwal" in s_str or "tenggat" in s_str:
        pitch_points.append("Komitmen ketepatan waktu selesai (SLA tegas dengan kompensasi keterlambatan)")
    elif "minimal order" in s_str:
        pitch_points.append("Fleksibilitas MOQ ramah UMKM mulai kuantiti uji coba awal")
    else:
        pitch_points.append("Layanan pendampingan desain dan proofing fisik sebelum produksi massal")

    return "; ".join(pitch_points)


def format_competitor_for_hermes(comp: Dict[str, Any]) -> List[str]:
    raw_reviews = comp.get("sample_negative_reviews") or []
    weaknesses = extract_competitor_weaknesses(raw_reviews)
    
    quality_str = " | ".join(weaknesses["quality"])
    service_str = " | ".join(weaknesses["service"])
    selling_point = generate_ruang_visual_counter_pitch(weaknesses["quality"], weaknesses["service"])
    
    wa = comp.get("whatsapp", "-")
    wa_link = f"https://wa.me/{wa}" if wa and wa != "-" else "-"
    rating_str = f"{comp.get('rating', 4.0)} ({comp.get('reviews_count', 0)} ulasan)"
    today_str = datetime.now().strftime("%Y-%m-%d")

    return [
        comp.get("name", "Percetakan"),
        comp.get("focus", "Cetak Umum"),
        comp.get("scale", "Skala Menengah"),
        rating_str,
        wa,
        wa_link,
        quality_str,
        service_str,
        selling_point,
        comp.get("maps_url", "-"),
        today_str,
    ]


def sync_competitor_matrix_to_hermes(
    competitors: Optional[List[Dict[str, Any]]] = None,
    sheet_name: str = "Matriks Kompetitor",
    clear_first: bool = False,
    dry_run: bool = False,
    webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    target_competitors = competitors if competitors is not None else MAKASSAR_PRINTING_COMPETITORS
    rows = [format_competitor_for_hermes(c) for c in target_competitors]

    if dry_run:
        return {
            "status": "dry_run",
            "sheet_name": sheet_name,
            "clear_first": clear_first,
            "rows_count": len(rows),
            "sample_rows": rows[:2],
        }

    if clear_first:
        send_webhook_payload({"sheet_name": sheet_name, "action": "clear_data", "rows": []}, webhook_url=webhook_url)

    resp = send_webhook_payload({"sheet_name": sheet_name, "action": "append", "rows": rows}, webhook_url=webhook_url)
    return {
        "status": "success",
        "sheet_name": sheet_name,
        "rows_count": len(rows),
        "webhook_response": resp,
    }


def main():
    parser = argparse.ArgumentParser(description="Analisis dan Sinkronisasi Matriks Kompetitor Percetakan Makassar ke Google Sheets Hermes")
    parser.add_argument("--dry-run", action="store_true", help="Uji coba format tanpa menulis ke Google Sheets")
    parser.add_argument("--clear-first", action="store_true", help="Kosongkan data lama sebelum mengunggah")
    parser.add_argument("--limit", type=int, default=0, help="Batasi jumlah kompetitor yang disinkronkan")
    args = parser.parse_args()

    comps = MAKASSAR_PRINTING_COMPETITORS[:args.limit] if args.limit > 0 else MAKASSAR_PRINTING_COMPETITORS
    print(f"Memulai sinkronisasi Matriks Kompetitor Makassar ke Google Sheets (Total: {len(comps)} percetakan)...")
    
    result = sync_competitor_matrix_to_hermes(
        competitors=comps,
        clear_first=args.clear_first,
        dry_run=args.dry_run
    )
    
    print(f"Status: {result.get('status')} | Jumlah baris: {result.get('rows_count')}")
    if args.dry_run:
        print("Sampel baris pertama:")
        print(json.dumps(result.get("sample_rows", [])[0], indent=2, ensure_ascii=False))
    else:
        print(f"Respons Webhook: {result.get('webhook_response')}")


if __name__ == "__main__":
    main()
