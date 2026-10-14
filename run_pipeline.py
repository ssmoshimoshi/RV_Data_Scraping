"""
RUANG VISUAL — Pipeline Runner
================================
Entry point utama untuk menjalankan scraping pipeline.
Referensi: intelligence_pipeline_prd.md §13

Cara Pakai:
    python run_pipeline.py gmaps --mode leads --limit 3
    python run_pipeline.py gmaps --mode competitors --limit 3
    python run_pipeline.py gmaps --mode all --limit 2
    python run_pipeline.py init-sheets

Catatan:
    Jalankan dari root project directory (DATA CALON CUSTOMER/).
    Pastikan virtual environment aktif: source scrapers/.venv/bin/activate
"""

import sys
import json
import subprocess
from pathlib import Path

# Pastikan project root ada di sys.path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def print_banner():
    print("=" * 60)
    print("  🏢 RUANG VISUAL — Market Intelligence Pipeline")
    print("  📍 Makassar, Sulawesi Selatan")
    print("=" * 60)


def print_help():
    print_banner()
    print()
    print("Cara pakai:")
    print("  python run_pipeline.py <module> [options]")
    print()
    print("Modules yang tersedia:")
    print("  all            Jalankan SELURUH pipeline & kirim rekap ke Telegram (Mode Cloud)")
    print("  gmaps          Google Maps scraper — Leads & Competitors (Module B)")
    print("  matrix         Competitor Intelligence & Strategy Matrix (Module F)")
    print("  instagram      Instagram Public Profile Scraper (Module C)")
    print("  tiktok         TikTok & Market Signals Trend Scraper (Module D)")
    print("  export-csv     Ekspor seluruh data terbaru ke format CSV")
    print("  init-sheets    Inisialisasi/update Google Sheets")
    print()
    print("Contoh:")
    print("  python run_pipeline.py all --limit 2 --notify-telegram")
    print("  python run_pipeline.py gmaps --mode leads --limit 3 --dry-run")
    print("  python run_pipeline.py gmaps --mode competitors --limit 3 --dry-run")
    print("  python run_pipeline.py matrix --dry-run")
    print("  python run_pipeline.py instagram --profiles ruangvisual.id --dry-run")
    print("  python run_pipeline.py tiktok --dry-run")
    print()


def run_gmaps():
    """Jalankan Google Maps scraper."""
    from scrapers.gmaps_scraper import main
    main()


def run_init_sheets():
    """Inisialisasi Google Sheets dengan tab baru jika perlu."""
    from scrapers.utils import get_logger, build_sheets_service, get_spreadsheet_id, append_rows_to_sheet

    log = get_logger("init")
    log.info("🔧 Menginisialisasi Google Sheets...")

    service = build_sheets_service()
    spreadsheet_id = get_spreadsheet_id()

    # Ambil sheets yang ada
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing = [s["properties"]["title"] for s in meta.get("sheets", [])]
    log.info(f"📄 Sheets yang ada: {existing}")

    # Sheets yang dibutuhkan sesuai PRD §12
    required_sheets = {
        "Radar Prospek": [
            "Entitas Bisnis", "Kategori Segmen", "Trigger Event",
            "Sumber Data", "Kontak", "Proyeksi Kebutuhan",
            "Skor Prospek", "Status Akuisisi", "URL Referensi",
            "Tanggal Scrape", "Catatan"
        ],
        "Matriks Kompetitor": [
            "Nama Kompetitor", "Fokus Layanan Utama", "Celah Kualitas",
            "Celah SOP/Admin", "Estimasi Kapasitas", "Estetika Visual",
            "Rating GMaps", "Jumlah Review", "Akun Instagram",
            "Website", "Harga Referensi", "Tanggal Update"
        ],
        "Market Signals": [
            "Signal", "Platform", "Metrik", "Relevansi", "URL", "Tanggal"
        ],
        "Scrape Log": [
            "Timestamp", "Module", "Platform", "Query",
            "Results Count", "Status", "Error Message", "Duration (sec)"
        ],
    }

    # Buat tabs yang belum ada
    requests = []
    for title in required_sheets:
        if title not in existing:
            log.info(f"  ➕ Membuat tab: '{title}'")
            requests.append({"addSheet": {"properties": {"title": title}}})

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()
        log.info("  ✅ Tab baru berhasil dibuat!")

    # Tulis header untuk tab yang belum ada headernya
    for title, headers in required_sheets.items():
        range_name = f"{title}!A1:Z1"
        current = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute().get("values", [])

        if not current:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{title}!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [headers]}
            ).execute()
            log.info(f"  📝 Header ditulis untuk '{title}'")
        else:
            log.info(f"  ℹ️  Header '{title}' sudah ada")

    log.info("\n🎉 Inisialisasi selesai!")


def run_matrix():
    """Jalankan Competitor Matrix Analyzer."""
    from scrapers.competitor_analyzer import main as matrix_main
    matrix_main()


def run_instagram():
    """Jalankan Instagram scraper."""
    from scrapers.instagram_scraper import main as ig_main
    ig_main()


def run_tiktok():
    """Jalankan TikTok & Market Signals scraper."""
    from scrapers.tiktok_scraper import main as tiktok_main
    tiktok_main()


def run_export_csv():
    """Ekspor seluruh data terbaru di data/processed ke file CSV yang siap dibuka di Excel/Numbers."""
    import csv
    from scrapers.utils import get_logger
    log = get_logger("export-csv")
    proc_dir = Path("data/processed")

    # 1. Leads to CSV
    leads_files = sorted(proc_dir.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if leads_files:
        with open(leads_files[0], "r", encoding="utf-8") as f:
            leads = json.load(f)
        csv_file = proc_dir / "leads_calon_customer.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Nama Bisnis", "Kategori", "Skor Prospek", "Status", "Alamat", "Telepon", "Website", "Rating", "Jumlah Ulasan", "Alasan Skor", "Link GMaps"])
            for l in leads:
                w.writerow([
                    l.get("nama_bisnis", ""),
                    l.get("kategori", ""),
                    l.get("skor", ""),
                    l.get("skor_label", ""),
                    l.get("alamat", ""),
                    l.get("telepon", ""),
                    l.get("website", ""),
                    l.get("rating", ""),
                    l.get("jumlah_review", ""),
                    l.get("skor_reasons", ""),
                    l.get("url_gmaps", ""),
                ])
        log.info(f"✅ Leads diekspor: {csv_file}")

    # 2. Competitor Matrix to CSV
    matrix_files = sorted(proc_dir.glob("competitor_matrix_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if matrix_files:
        with open(matrix_files[0], "r", encoding="utf-8") as f:
            matrix = json.load(f)
        csv_file = proc_dir / "matriks_kompetitor.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Nama Kompetitor", "Fokus Layanan", "Skala Kapasitas", "Rating GMaps", "Jumlah Review", "Kontak WhatsApp", "Celah Kualitas", "Celah Pelayanan & SOP", "Selling Point RUANG VISUAL"])
            for m in matrix:
                w.writerow([
                    m.get("nama_bisnis", ""),
                    m.get("fokus_layanan", ""),
                    m.get("estimasi_kapasitas", ""),
                    m.get("rating_gmaps", ""),
                    m.get("jumlah_review", ""),
                    m.get("telepon", ""),
                    m.get("celah_kualitas", ""),
                    m.get("celah_sop", ""),
                    m.get("selling_point_rv", ""),
                ])
        log.info(f"✅ Matriks Kompetitor diekspor: {csv_file}")

    # 3. Market Signals to CSV
    sig_files = sorted(proc_dir.glob("market_signals_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if sig_files:
        with open(sig_files[0], "r", encoding="utf-8") as f:
            sigs = json.load(f)
        csv_file = proc_dir / "sinyal_pasar.csv"
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Sinyal / Tren", "Platform", "Metrik", "Relevansi untuk RUANG VISUAL", "URL Referensi", "Tanggal"])
            for s in sigs:
                w.writerow([
                    s.get("signal", ""),
                    s.get("platform", ""),
                    s.get("metrik", ""),
                    s.get("relevansi", ""),
                    s.get("url", ""),
                    s.get("tanggal", ""),
                ])
        log.info(f"✅ Sinyal Pasar diekspor: {csv_file}")


def run_all(limit: int = 2, dry_run: bool = False, notify_telegram: bool = True):
    """
    Jalankan seluruh rangkaian pipeline secara end-to-end:
    1. Scrape Google Maps Leads (fresh targets di Makassar)
    2. Analisis Matriks Kompetitor Makassar
    3. Pindai TikTok & Tren Kebutuhan Cetak (Market Signals)
    4. Ekspor ke file CSV lokal
    5. Kirim ringkasan eksekutif ke Telegram Owner RUANG VISUAL
    """
    import time
    from datetime import datetime
    from scrapers.utils import get_logger, WITA, today_wita
    from scrapers.config import (
        GMAPS_LEAD_QUERIES,
        TIKTOK_KEYWORDS,
        PROCESSED_DIR,
    )
    from scrapers.gmaps_scraper import scrape_gmaps, process_leads, export_leads_to_sheet
    from scrapers.competitor_analyzer import analyze_all_competitors, export_matrix_to_sheet
    from scrapers.tiktok_scraper import scan_market_signals, export_signals_to_sheet
    from scrapers.telegram_notifier import send_pipeline_summary, send_error_alert

    log = get_logger("runner-all")
    start_time = time.time()
    log.info("🚀 MEMULAI EKSEKUSI PIPELINE LENGKAP RUANG VISUAL...")

    leads_count = 0
    hot_leads = []
    competitor_count = 0
    signals_count = 0

    # 1. Google Maps Leads
    try:
        log.info("\n--- [1/4] Scraping Fresh Leads (Google Maps) ---")
        raw_leads = scrape_gmaps(GMAPS_LEAD_QUERIES, max_queries=limit, mode="leads")
        if raw_leads:
            processed = process_leads(raw_leads)
            leads_only = [l for l in processed if l.get("kategori_kode") != "percetakan"]
            leads_count = len(leads_only)
            hot_leads = [l for l in leads_only if float(l.get("skor", 0)) >= 8.0]

            proc_path = PROCESSED_DIR / f"leads_scored_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(proc_path, "w", encoding="utf-8") as f:
                json.dump(leads_only, f, ensure_ascii=False, indent=2)

            if not dry_run:
                export_leads_to_sheet(leads_only)
            log.info(f"✅ Leads selesai: {leads_count} ditemukan ({len(hot_leads)} hot leads)")
    except Exception as e:
        log.error(f"❌ Error saat scraping leads: {e}")
        try:
            send_error_alert("Google Maps Scraper", str(e))
        except Exception:
            pass

    # Jika run ini tidak dapat hot leads baru, ambil dari cache terbaru untuk ringkasan Telegram
    if not hot_leads:
        recent_leads_files = sorted(PROCESSED_DIR.glob("leads_scored_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if recent_leads_files:
            try:
                with open(recent_leads_files[0], "r", encoding="utf-8") as f:
                    cached_leads = json.load(f)
                    hot_leads = [l for l in cached_leads if float(l.get("skor", 0)) >= 8.0]
                    if leads_count == 0:
                        leads_count = len(cached_leads)
            except Exception:
                pass

    # 2. Competitor Matrix
    try:
        log.info("\n--- [2/4] Menganalisis Matriks Kompetitor Makassar ---")
        comp_files = sorted(PROCESSED_DIR.glob("competitors_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if comp_files:
            with open(comp_files[0], "r", encoding="utf-8") as f:
                comps = json.load(f)
            matrix = analyze_all_competitors(comps)
            competitor_count = len(matrix)
            out_file = PROCESSED_DIR / f"competitor_matrix_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(matrix, f, ensure_ascii=False, indent=2)
            if not dry_run:
                export_matrix_to_sheet(matrix)
            log.info(f"✅ Matriks kompetitor selesai: {competitor_count} percetakan teranalisis")
    except Exception as e:
        log.error(f"❌ Error saat analisis kompetitor: {e}")
        try:
            send_error_alert("Competitor Matrix Analyzer", str(e))
        except Exception:
            pass

    # 3. Market Signals (TikTok Trends)
    try:
        log.info("\n--- [3/4] Memindai Tren Pasar (Market Signals) ---")
        signals = scan_market_signals(TIKTOK_KEYWORDS)
        signals_count = len(signals)
        sig_file = PROCESSED_DIR / f"market_signals_{datetime.now(WITA).strftime('%Y%m%d_%H%M%S')}.json"
        with open(sig_file, "w", encoding="utf-8") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        if not dry_run:
            export_signals_to_sheet(signals)
        log.info(f"✅ Sinyal pasar selesai: {signals_count} tren terpetakan")
    except Exception as e:
        log.error(f"❌ Error saat memindai tren pasar: {e}")
        try:
            send_error_alert("Market Signals Scraper", str(e))
        except Exception:
            pass

    # 4. Export CSV
    try:
        log.info("\n--- [4/4] Mengekspor Data ke CSV Lokal ---")
        run_export_csv()
    except Exception as e:
        log.warning(f"⚠️ Gagal ekspor CSV: {e}")

    duration = time.time() - start_time
    log.info(f"\n🎉 Seluruh rangkaian pipeline selesai dalam {duration:.1f} detik!")

    # 5. Kirim Telegram Notification
    if notify_telegram:
        log.info("📲 Mengirimkan laporan eksekutif ke Telegram...")
        try:
            send_pipeline_summary(
                total_leads=leads_count,
                hot_leads=hot_leads,
                total_competitors=competitor_count,
                total_signals=signals_count,
                duration_sec=duration,
                mode="Cloud Pipeline Automation",
            )
        except Exception as e:
            log.warning(f"⚠️ Gagal mengirim notifikasi Telegram: {e}")


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    module = sys.argv[1].lower()

    # Parse arguments untuk 'all'
    if module == "all":
        import argparse
        parser = argparse.ArgumentParser(description="RUANG VISUAL — Run All Pipeline")
        parser.add_argument("--limit", type=int, default=2, help="Batas query pencarian (default: 2)")
        parser.add_argument("--dry-run", action="store_true", help="Jalankan tanpa export ke Google Sheets")
        parser.add_argument("--notify-telegram", action="store_true", default=True, help="Kirim notifikasi Telegram")
        parser.add_argument("--no-telegram", dest="notify_telegram", action="store_false", help="Jangan kirim Telegram")
        args = parser.parse_args(sys.argv[2:])

        print_banner()
        run_all(limit=args.limit, dry_run=args.dry_run, notify_telegram=args.notify_telegram)
        return

    # Remove module name dari argv agar argparse di sub-module bekerja
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if module == "gmaps":
        print_banner()
        run_gmaps()
    elif module == "matrix":
        print_banner()
        run_matrix()
    elif module == "instagram":
        print_banner()
        run_instagram()
    elif module == "tiktok":
        print_banner()
        run_tiktok()
    elif module in ("export-csv", "csv"):
        print_banner()
        run_export_csv()
    elif module == "init-sheets":
        print_banner()
        run_init_sheets()
    elif module in ("help", "--help", "-h"):
        print_help()
    else:
        print(f"❌ Module tidak dikenal: '{module}'")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
