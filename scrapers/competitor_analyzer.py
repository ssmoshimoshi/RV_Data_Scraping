"""
RUANG VISUAL — Competitor Matrix & Intelligence Analyzer (Module F)
=====================================================================
Menganalisis kompetitor percetakan di Makassar untuk memetakan:
- Celah kualitas (Quality gaps)
- Celah SOP/Admin & pelayanan (Service gaps)
- Estimasi skala kapasitas
- Selling points diferensiasi untuk RUANG VISUAL

Referensi: intelligence_pipeline_prd.md §11 & §12 Sheet 2
"""

import json
import time
import argparse
from datetime import datetime
from pathlib import Path

from scrapers.config import (
    QUALITY_KEYWORDS,
    SOP_KEYWORDS,
    PROCESSED_DIR,
    RAW_DIR,
)
from scrapers.utils import (
    get_logger,
    today_wita,
    now_wita,
    append_rows_to_sheet,
    WITA,
)

log = get_logger("competitor-analyzer")


def analyze_single_competitor(comp: dict) -> dict:
    """
    Analisis satu kompetitor berdasarkan data metrik, kontak, dan ulasan.
    """
    nama = comp.get("nama_bisnis", "Unknown")
    rating = float(comp.get("rating", 0.0))
    reviews = int(comp.get("jumlah_review", 0))
    phone = comp.get("telepon", "")
    web = comp.get("website", "")
    alamat = comp.get("alamat", "")

    # 1. Estimasi Kapasitas & Skala Operasional
    if reviews >= 500:
        kapasitas = f"Skala Besar ({reviews} ulasan, volume tinggi)"
    elif reviews >= 100:
        kapasitas = f"Skala Menengah ({reviews} ulasan, volume moderat)"
    elif reviews >= 20:
        kapasitas = f"Skala Berkembang ({reviews} ulasan)"
    else:
        kapasitas = f"Skala Kecil / Baru ({reviews} ulasan)"

    # 2. Fokus Layanan Utama (Inferred dari nama & spesialisasi)
    nama_lower = nama.lower()
    if "digital" in nama_lower:
        layanan = "Digital Printing, Banner, Sticker, Cetak Cepat"
    elif "offset" in nama_lower:
        layanan = "Percetakan Offset, Brosur Massal, Kemasan Box"
    elif "toko" in nama_lower or "store" in nama_lower:
        layanan = "Retail Printing, Fotokopi, Jilid, Alat Tulis"
    elif "sablon" in nama_lower or "konveksi" in nama_lower:
        layanan = "Sablon Kaos, Merchandise, Spanduk Kain"
    else:
        layanan = "Percetakan Umum, Banner, Kartu Nama, Brosur"

    # 3. Analisis Celah Kualitas & Celah SOP/Admin
    celah_kualitas = []
    celah_sop = []
    selling_points = []

    if rating < 4.5 and reviews > 10:
        celah_kualitas.append(f"Rating rendah ({rating}/5.0) — risiko deviasi warna/finishing")
        celah_sop.append("Indikasi ketidakpuasan customer pada ketepatan waktu/admin")
        selling_points.append("Tawarkan garansi cetak ulang & proofing warna presisi")
    elif rating < 4.8 and reviews > 50:
        celah_kualitas.append(f"Rating {rating}/5.0 — kualitas standar, rentan saat overload")
        celah_sop.append("Potensi antrean panjang saat jam sibuk")
        selling_points.append("Tawarkan prioritas pengerjaan kilat & sistem order online")
    else:
        celah_kualitas.append("Kualitas dinilai baik oleh customer")
        celah_sop.append("Pelayanan stabil")
        selling_points.append("Menangkan dengan harga bundling merchandise & packaging kreatif")

    if not phone:
        celah_sop.append("Akses kontak WhatsApp langsung tidak ditampilkan di publik")
        selling_points.append("Kemudahan konsultasi via fast-response WhatsApp")
    else:
        celah_sop.append(f"Tersedia kontak langsung ({phone})")

    return {
        "nama_bisnis": nama,
        "fokus_layanan": layanan,
        "celah_kualitas": "; ".join(celah_kualitas),
        "celah_sop": "; ".join(celah_sop),
        "estimasi_kapasitas": kapasitas,
        "estetika_visual": "Perlu audit portofolio IG",
        "rating_gmaps": str(rating),
        "jumlah_review": str(reviews),
        "telepon": phone,
        "website": web,
        "alamat": alamat,
        "selling_point_rv": "; ".join(selling_points),
        "tanggal_update": today_wita(),
    }


def analyze_all_competitors(competitors: list[dict]) -> list[dict]:
    """
    Analisis seluruh daftar kompetitor dan urutkan berdasarkan urgensi persaingan.
    """
    matrix = [analyze_single_competitor(c) for c in competitors]
    # Urutkan dari review terbanyak (market share terbesar)
    matrix.sort(key=lambda x: int(x["jumlah_review"]), reverse=True)
    return matrix


HEADERS_MATRIKS_KOMPETITOR = [
    "Nama Percetakan", "Fokus Layanan Utama", "Kapasitas / Skala",
    "Rating & Ulasan", "No. WhatsApp", "Link WA", "Celah Kualitas",
    "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL", "Website / Maps", "Tanggal Update"
]


def format_wa_hyperlink(phone: str) -> str:
    if not phone:
        return "-"
    clean = "".join([c for c in phone if c.isdigit()])
    if clean.startswith("08"):
        clean = "62" + clean[1:]
    elif clean.startswith("8"):
        clean = "62" + clean
    return f'=HYPERLINK("https://wa.me/{clean}", "Chat WA")' if clean else "-"


def format_link_hyperlink(url: str, label: str = "Buka Web") -> str:
    if not url or url == "-":
        return "-"
    return f'=HYPERLINK("{url}", "{label}")'


def export_matrix_to_sheet(matrix: list[dict], action: str = "append"):
    """Export Matriks Kompetitor lengkap ke Google Sheets."""
    rows = []
    for m in matrix:
        phone = m.get("telepon", "").strip()
        wa_link = format_wa_hyperlink(phone)
        web_or_map = m.get("website", "") or m.get("url_gmaps", "")
        web_link = format_link_hyperlink(web_or_map, "Buka Web") if web_or_map else "-"
        rating_str = f"{m.get('rating_gmaps', '0.0')} ({m.get('jumlah_review', '0')} ulasan)"

        row = [
            m.get("nama_bisnis", ""),              # A: Nama Percetakan
            m.get("fokus_layanan", ""),            # B: Fokus Layanan Utama
            m.get("estimasi_kapasitas", ""),       # C: Kapasitas / Skala
            rating_str,                            # D: Rating & Ulasan
            phone or "-",                          # E: No. WhatsApp
            wa_link,                               # F: Link WA
            m.get("celah_kualitas", "-"),          # G: Celah Kualitas
            m.get("celah_sop", "-"),               # H: Celah Pelayanan & SOP
            m.get("selling_point_rv", "-"),        # I: Selling Point RUANG VISUAL
            web_link,                              # J: Website / Maps
            m.get("tanggal_update", today_wita()), # K: Tanggal Update
        ]
        rows.append(row)

    try:
        append_rows_to_sheet("Matriks Kompetitor", rows, action=action, headers=HEADERS_MATRIKS_KOMPETITOR)
        log.info(f"{len(rows)} baris berhasil di-export ke 'Matriks Kompetitor'")
    except Exception as e:
        log.warning(f"Belum bisa export ke Google Sheets: {e}")
        log.info("Matriks kompetitor tetap tersimpan di folder data/processed/")


def main():
    parser = argparse.ArgumentParser(
        description="RUANG VISUAL — Competitor Matrix Analyzer (Module F)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="Path ke file JSON competitors (default: file terbaru di data/processed/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya tampilkan analisis di terminal dan simpan JSON lokal",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("RUANG VISUAL - Competitor Matrix & Intelligence")
    log.info("=" * 60)

    # Cari file competitors terbaru jika tidak dispesifikasikan
    input_file = args.input
    if not input_file:
        files = list(PROCESSED_DIR.glob("competitors_*.json"))
        if not files:
            log.error("[ERROR] Tidak ditemukan file data kompetitor di data/processed/!")
            log.info("   Jalankan dulu: python run_pipeline.py gmaps --mode competitors")
            return
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        input_file = str(files[0])

    log.info(f"Membaca data kompetitor dari: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        competitors = json.load(f)

    log.info(f"Menganalisis {len(competitors)} kompetitor percetakan...")
    matrix = analyze_all_competitors(competitors)

    out_file = PROCESSED_DIR / f"competitor_matrix_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)
    log.info(f"Matriks kompetitor tersimpan: {out_file}")

    log.info("\nTOP 5 KOMPETITOR UTAMA DAN STRATEGI MENANG RUANG VISUAL:")
    for i, m in enumerate(matrix[:5], 1):
        log.info(f"\n[{i}] {m['nama_bisnis']}")
        log.info(f"    Rating: {m['rating_gmaps']}/5.0 ({m['jumlah_review']} ulasan) | Kontak: {m['telepon'] or '-'}")
        log.info(f"    Kapasitas : {m['estimasi_kapasitas']}")
        log.info(f"    Celah SOP : {m['celah_sop']}")
        log.info(f"    Selling Point RV: {m['selling_point_rv']}")

    if not args.dry_run:
        export_matrix_to_sheet(matrix)

    log.info("\nSelesai.")


if __name__ == "__main__":
    main()
